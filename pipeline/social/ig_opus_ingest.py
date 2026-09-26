"""
ig_opus_ingest.py - insert Opus-authored Void social posts, no Gemini.

The "Opus authors, the pipeline renders" path. This is the sibling of
ig_generator.py's `vision-series` track, but general: instead of Gemini writing
the captions after the fact, a committed JSON (data/social/opus_batch.json)
carries the FINISHED editorial copy - on-slide text AND the Instagram / X /
Bluesky captions + intent - and this script only maps each post to the locked
slide_specs contract and inserts the ig_posts row. Nothing here calls an LLM.

Each JSON post declares a `pillar`:
  vision   -> a hook/stance/cta prose carousel rendered by Vision.tsx
  method   -> the SAME hook/stance/cta prose carousel (kind='vision' so it
              routes to Vision.tsx; the render template is chosen by slide.kind,
              not by pillar). pillar stays 'method' for categorization/export.
  example  -> a hook/spectrum/cta carousel rendered by Example.tsx. The spectrum
              outlets are fetched LIVE from Supabase by `cluster_id` using the
              exact same query/shape ig_generator uses for the Example spectrum
              (per-article lean, [0:4] recognizable distinct-score outlets), so
              the money slide shows the real cross-outlet spread.

The captions ride on the row verbatim (caption / caption_x / caption_bluesky /
intent), which makes the downstream Gemini caption pass a no-op for these rows
(ig_caption selects `caption IS NULL`). In the opus workflow path that step is
skipped entirely; even if it ran, it would find nothing to do.

Usage:
    python -m pipeline.social.ig_opus_ingest                    # insert the batch
    python -m pipeline.social.ig_opus_ingest --batch path.json  # a custom batch
    python -m pipeline.social.ig_opus_ingest --dry-run          # print, no insert
    python -m pipeline.social.ig_opus_ingest --when 2026-08-11T13:30:00Z

Environment:
    SUPABASE_URL / KEY   existing pipeline vars (read for the Example spectrum,
                         write for the ig_posts insert).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.supabase_client import supabase  # noqa: E402

# Reuse the locked slide_specs builders + copy hygiene + insert path from the
# Gemini generator so the render templates receive byte-identical shapes. Only
# the AUTHOR of the copy changes (Opus, via JSON), never the contract.
from social.ig_generator import (  # noqa: E402
    URL_HOME,
    _emit,
    _next_post_datetime,
    _fit_sentences,
    _strip_trailing_url,
    _gather_cluster_outlets,
    _ontopic_outlets,
    _select_display_outlets,
    _SERIES_STANCE_BODY_MAX,
    _SERIES_CTA_LINE_MAX,
    _EXAMPLE_DISPLAY_TARGET,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BATCH = REPO_ROOT / "data" / "social" / "opus_batch.json"

# Distinct scheduled_for per post so ig_export orders the bundle 1..N.
STAGGER_MINUTES = 30


# ---------------------------------------------------------------------------
# Batch loading
# ---------------------------------------------------------------------------

def _load_batch(path: Path) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    posts = data.get("posts") if isinstance(data, dict) else data
    return [p for p in (posts or []) if isinstance(p, dict)]


# ---------------------------------------------------------------------------
# vision / method: prose hook -> stance -> cta (rendered by Vision.tsx)
#
# kind is 'vision' for BOTH pillars because the render template is selected by
# slide.kind (IgSlideClient switch), and the method post's middle slide is prose
# (kicker + body), which is the VisionSlideSpec stance shape - NOT the Method
# template's sample/axis-highlight shape. Only what is RENDERED on-slide is fit
# to the template budget; the full prose survives in the caption.
# ---------------------------------------------------------------------------

def _vision_slide_specs(post: dict[str, Any]) -> list[dict[str, Any]]:
    hook = post.get("hook") or {}
    stance = post.get("stance") or {}
    cta = post.get("cta") or {}

    body = _fit_sentences((stance.get("body") or "").strip(), _SERIES_STANCE_BODY_MAX)
    cta_line = _fit_sentences(
        _strip_trailing_url(cta.get("headline") or ""), _SERIES_CTA_LINE_MAX
    )

    stance_spec: dict[str, Any] = {
        "kind": "vision",
        "variant": "stance",
        "kicker": (stance.get("kicker") or "").strip(),
        "body": body,
    }
    # Vision.tsx renders the stance headline only when present; the Opus vision +
    # method posts intentionally omit it (kicker + rule + body column).
    stance_headline = (stance.get("headline") or "").strip()
    if stance_headline:
        stance_spec["headline"] = stance_headline

    return [
        {
            "kind": "vision",
            "variant": "hook",
            "kicker": (hook.get("kicker") or "").strip(),
            "headline": (hook.get("headline") or "").strip(),
        },
        stance_spec,
        {
            "kind": "vision",
            "variant": "cta",
            "headline": cta_line,
            "url": (cta.get("url") or URL_HOME).strip(),
        },
    ]


# ---------------------------------------------------------------------------
# example: hook -> spectrum -> cta (rendered by Example.tsx)
#
# The spectrum outlets come from the live cluster (cluster_id), using the exact
# selection ig_generator uses: gather every article's outlet + resolved lean,
# drop over-merge outliers, collapse ties to one outlet per distinct lean score
# keeping the more recognizable outlet, keep the two extremes, then [0:4] for the
# slide. lean_values (the full on-topic distribution) drives the KDE ridge.
# ---------------------------------------------------------------------------

def _fetch_cluster_meta(cid: str) -> dict[str, Any] | None:
    try:
        rows = (
            supabase.table("story_clusters")
            .select("id, title, source_count")
            .eq("id", cid)
            .limit(1)
            .execute()
            .data
            or []
        )
        return rows[0] if rows else None
    except Exception as e:
        print(f"  [opus] cluster meta query failed for {cid}: {e}")
        return None


def _example_slide_specs(
    post: dict[str, Any],
) -> tuple[list[dict[str, Any]], int, int, int]:
    """Return (specs, fetched_outlets, displayed_outlets, outlet_count)."""
    cid = (post.get("cluster_id") or "").strip()
    hook = post.get("hook") or {}
    spectrum = post.get("spectrum") or {}
    cta = post.get("cta") or {}

    topic = (hook.get("kicker") or "").strip()
    meta = _fetch_cluster_meta(cid) if cid else None
    cluster_title = (meta or {}).get("title") or hook.get("headline") or ""
    live_source_count = int((meta or {}).get("source_count") or 0)

    raw = _gather_cluster_outlets(cid) if cid else []
    fetched = len(raw)
    ontopic = _ontopic_outlets(cluster_title, raw) if raw else []
    display = _select_display_outlets(ontopic, _EXAMPLE_DISPLAY_TARGET)[
        :_EXAMPLE_DISPLAY_TARGET
    ]
    headlines = [
        {"outlet": o["outlet"], "lean_score": o["lean_score"], "headline": o["headline"]}
        for o in display
    ]
    lean_values = sorted(o["lean_score"] for o in ontopic)

    # The hook count matches the kicker copy ("52 OUTLETS"): prefer the authored
    # count, fall back to the live cluster source_count, then the displayed set.
    outlet_count = int(post.get("outlet_count") or live_source_count or len(headlines))

    spectrum_spec: dict[str, Any] = {
        "kind": "example",
        "variant": "spectrum",
        "topic": topic,
        "headlines": headlines,
        "lean_values": lean_values,
    }
    # Preserve the Opus editorial context. Example.tsx does not render this
    # (the money slide is the ridge + outlets); the full prose lives in the
    # caption. Kept for provenance / a future template slot.
    context = (spectrum.get("body") or "").strip()
    if context:
        spectrum_spec["context"] = context

    specs = [
        {
            "kind": "example",
            "variant": "hook",
            "topic": topic,
            "headline": (hook.get("headline") or "").strip(),
            "outlet_count": outlet_count,
        },
        spectrum_spec,
        {
            "kind": "example",
            "variant": "cta",
            "headline": (cta.get("headline") or "").strip(),
            "url": (cta.get("url") or URL_HOME).strip(),
        },
    ]
    return specs, fetched, len(headlines), outlet_count


# ---------------------------------------------------------------------------
# Pre-filled caption columns (inserted verbatim; never scrubbed, never Gemini)
# ---------------------------------------------------------------------------

def _caption_extra(post: dict[str, Any]) -> dict[str, Any]:
    """The Opus caption columns. `caption_instagram` already carries its hashtags
    inline on its last line, so `hashtags` is left EMPTY to stop ig_export from
    re-appending a second hashtag block. A non-null `caption` is what makes the
    Gemini caption pass skip the row (ig_caption selects `caption IS NULL`)."""
    return {
        "caption": (post.get("caption_instagram") or "").strip(),
        "hashtags": [],
        "caption_x": (post.get("caption_x") or "").strip(),
        "caption_bluesky": (post.get("caption_bluesky") or "").strip(),
        "intent": (post.get("intent") or "").strip(),
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run(batch_path: Path, when: datetime | None, dry_run: bool) -> int:
    try:
        posts = _load_batch(batch_path)
    except Exception as e:
        print(f"  [opus] could not load {batch_path}: {e}")
        return 0
    if not posts:
        print(f"  [opus] no posts in {batch_path}")
        return 0

    base = when or _next_post_datetime()
    made = 0
    for i, post in enumerate(posts):
        pillar = (post.get("pillar") or "vision").strip().lower()
        slug = post.get("slug") or f"post-{i + 1}"
        scheduled = base + timedelta(minutes=i * STAGGER_MINUTES)

        if pillar == "example":
            specs, fetched, displayed, outlet_count = _example_slide_specs(post)
            print(
                f"  [opus] {i + 1}/{len(posts)} {pillar} {slug}: "
                f"cluster fetched {fetched} outlet(s), displaying {displayed}, "
                f"hook count {outlet_count}"
            )
            if fetched == 0:
                print(
                    f"  [opus] [warn] {slug}: cluster {post.get('cluster_id')} returned "
                    "0 outlets (likely rolled out of the clustering window); the "
                    "spectrum slide will render without an outlet spread"
                )
        else:
            specs = _vision_slide_specs(post)
            print(f"  [opus] {i + 1}/{len(posts)} {pillar} {slug}")

        extra = _caption_extra(post)
        if _emit(pillar, specs, scheduled, dry_run, extra=extra):
            made += 1

    if not dry_run:
        print(
            f"  [opus] {made}/{len(posts)} Opus draft(s) inserted "
            "(captions pre-filled; Gemini caption pass will skip them)"
        )
    return made


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Insert Opus-authored Void social posts (no Gemini)."
    )
    parser.add_argument(
        "--batch",
        default=str(DEFAULT_BATCH),
        help="path to the Opus batch JSON (default data/social/opus_batch.json)",
    )
    parser.add_argument(
        "--when",
        default=None,
        help="ISO datetime for scheduled_for; default = next 13:30 UTC",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the slide_specs + caption columns and exit without inserting",
    )
    args = parser.parse_args()

    when: datetime | None = None
    if args.when:
        when = datetime.fromisoformat(args.when.replace("Z", "+00:00"))

    run(Path(args.batch), when, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
