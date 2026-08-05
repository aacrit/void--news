"""
ig_export.py - build the manual-upload bundle for a social generate run.

As of 2026-08-05 the Void social pipeline is GENERATE-ONLY: nothing auto-posts.
After a generate run (ig_generator -> ig_capture -> ig_caption) this script
collects that run's ig_posts rows (draft rows with image_urls + caption) and
writes a dated, self-contained bundle to ./social_out/ that the CEO downloads
(the workflow uploads it as an artifact) and uploads by hand:

    social_out/<YYYY-MM-DD>/<product>/<NN>-<slug>/
        slide-1.png slide-2.png slide-3.png   # downloaded from the ig-renders bucket
        caption-instagram.txt                  # full caption + hashtags
        caption-x.txt                          # <= 280 chars
        caption-bluesky.txt                    # <= 300 chars
        intent.txt                             # the director's note
    social_out/<YYYY-MM-DD>/index.html         # previews every post, all 3 platforms

`product` maps from pillar: history -> history, weekly -> weekly,
vision/method/example -> news. `<NN>` is the 2-digit order in the day's run.

Nothing here posts anything. Reads only: DB rows via supabase_client, images
via the public ig-renders bucket URLs already on each row.

Usage:
    python -m pipeline.social.ig_export                     # today's (UTC) draft posts
    python -m pipeline.social.ig_export --date 2026-08-05   # a specific run day
    python -m pipeline.social.ig_export --post-id <uuid>    # one post
    python -m pipeline.social.ig_export --limit 3 --out-dir ./social_out

Environment:
    SUPABASE_URL / KEY   existing pipeline vars (read-only use here)
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.supabase_client import supabase  # noqa: E402

try:
    import requests  # noqa: E402
except ImportError:  # pragma: no cover - requests is a hard pipeline dep
    requests = None  # type: ignore

# Reuse the caption module's variant derivation so exported X/Bluesky copy is
# never blank on older rows or when migration 074 has not been applied yet.
from social.ig_caption import (  # noqa: E402
    X_MAX_CHARS,
    BLUESKY_MAX_CHARS,
    _derive_variant_from_caption,
    NEUTRAL_INTENT,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_OUT_DIR = Path("social_out")

PILLAR_PRODUCT = {
    "vision": "news",
    "method": "news",
    "example": "news",
    "history": "history",
    "weekly": "weekly",
    # retired launch pillars still map to news
    "receipt": "news",
    "brief": "news",
    "bts": "news",
    "heatmap": "news",
}

PRODUCT_LABEL = {"news": "Void News", "history": "Void History", "weekly": "Void Weekly"}

# Loose Void palette for the internal preview (brass on ink/cream).
BRASS = "#946B15"
INK = "#1a1714"
CREAM = "#f4efe6"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(text: str, max_len: int = 48) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text or "post"


def _first_spec(specs: Any) -> dict:
    if isinstance(specs, list) and specs and isinstance(specs[0], dict):
        return specs[0]
    return {}


def _derive_title(pillar: str, specs: Any) -> str:
    """A human title for the folder slug + preview heading, from slide 0."""
    s0 = _first_spec(specs)
    if pillar == "weekly":
        issue = s0.get("issue_number")
        head = (s0.get("headline") or "").strip()
        if issue and head:
            return f"Issue {issue}: {head}"
        if head:
            return head
        if issue:
            return f"Weekly Issue {issue}"
    if pillar == "example":
        return (s0.get("headline") or s0.get("topic") or "").strip() or "Today's story"
    if pillar == "method":
        return (s0.get("headline") or s0.get("axis_name") or "").strip() or "How the score works"
    # vision / history / fallback
    head = (s0.get("headline") or "").strip()
    return head or pillar.replace("_", " ").title()


def _instagram_text(caption: str, hashtags: list[str]) -> str:
    caption = (caption or "").strip()
    tags = [h.lstrip("#").strip() for h in (hashtags or []) if isinstance(h, str) and h.strip()]
    if tags:
        return f"{caption}\n\n" + " ".join("#" + t for t in tags)
    return caption


def _x_text(row: dict) -> str:
    val = (row.get("caption_x") or "").strip()
    if val:
        return val
    return _derive_variant_from_caption(row.get("caption") or "", X_MAX_CHARS)


def _bluesky_text(row: dict) -> str:
    val = (row.get("caption_bluesky") or "").strip()
    if val:
        return val
    return _derive_variant_from_caption(row.get("caption") or "", BLUESKY_MAX_CHARS)


def _intent_text(row: dict) -> str:
    return (row.get("intent") or "").strip() or NEUTRAL_INTENT


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

_SELECT = (
    "id, created_at, scheduled_for, pillar, state, slide_specs, "
    "caption, hashtags, caption_x, caption_bluesky, intent, image_urls"
)
_LEGACY_SELECT = (
    "id, created_at, scheduled_for, pillar, state, slide_specs, "
    "caption, hashtags, image_urls"
)


def _fetch(date_str: str | None, post_id: str | None, limit: int | None) -> list[dict]:
    def _run(select: str) -> list[dict]:
        q = supabase.table("ig_posts").select(select)
        if post_id:
            q = q.eq("id", post_id)
        else:
            q = q.eq("state", "draft")
            if date_str:
                q = q.gte("created_at", f"{date_str}T00:00:00Z").lte(
                    "created_at", f"{date_str}T23:59:59Z"
                )
        q = q.order("scheduled_for", desc=False).order("created_at", desc=False)
        if limit:
            q = q.limit(limit)
        return (q.execute().data) or []

    try:
        return _run(_SELECT)
    except Exception as e:
        # Migration 074 not applied -> variant columns absent. Fall back.
        msg = str(e).lower()
        if "caption_x" in msg or "caption_bluesky" in msg or "intent" in msg or "column" in msg:
            print("  [export] variant columns absent (migration 074 unapplied); using legacy select + derived variants")
            return _run(_LEGACY_SELECT)
        raise


def _download(url: str, dest: Path) -> bool:
    if requests is None:
        print("  [export] requests not installed; cannot download images")
        return False
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        return True
    except Exception as e:
        print(f"  [export] download failed {url}: {e}")
        return False


# ---------------------------------------------------------------------------
# Bundle writing
# ---------------------------------------------------------------------------

def _write_post_dir(
    post_dir: Path, row: dict, ig_text: str, x_text: str, bsky_text: str, intent: str
) -> list[str]:
    """Write the four text files + download slides. Returns local slide filenames."""
    post_dir.mkdir(parents=True, exist_ok=True)
    (post_dir / "caption-instagram.txt").write_text(ig_text + "\n", encoding="utf-8")
    (post_dir / "caption-x.txt").write_text(x_text + "\n", encoding="utf-8")
    (post_dir / "caption-bluesky.txt").write_text(bsky_text + "\n", encoding="utf-8")
    (post_dir / "intent.txt").write_text(intent + "\n", encoding="utf-8")

    slide_files: list[str] = []
    for i, url in enumerate(row.get("image_urls") or [], start=1):
        if not url:
            continue
        fname = f"slide-{i}.png"
        if _download(url, post_dir / fname):
            slide_files.append(fname)
    return slide_files


def _render_index(date_str: str, posts: list[dict]) -> str:
    """Self-contained internal preview page. Void palette, per-post slide
    thumbnails + Instagram/X/Bluesky columns + a visible INTENT callout."""
    esc = html.escape

    def _same_note(a: str, b: str, label: str) -> str:
        if a.strip() and a.strip() == b.strip():
            return f'<p class="same">Identical to {esc(label)} text.</p>'
        return ""

    cards = []
    for p in posts:
        thumbs = "".join(
            f'<img src="{esc(rel)}" alt="slide {i + 1}" loading="lazy">'
            for i, rel in enumerate(p["slide_rels"])
        ) or '<p class="warn">No slide images bundled.</p>'

        ig, x, bsky, intent = p["ig_text"], p["x_text"], p["bsky_text"], p["intent"]
        x_same = _same_note(x, ig, "Instagram")
        bsky_same = _same_note(bsky, ig, "Instagram") or _same_note(bsky, x, "X")

        cards.append(f"""
    <article class="post">
      <header>
        <span class="badge">{esc(p['product_label'])}</span>
        <span class="nn">#{p['nn']}</span>
        <h2>{esc(p['title'])}</h2>
        <span class="pillar">{esc(p['pillar'])}</span>
      </header>
      <div class="intent"><strong>INTENT</strong> {esc(intent)}</div>
      <div class="thumbs">{thumbs}</div>
      <div class="platforms">
        <section class="col ig">
          <h3>Instagram <span class="len">{len(ig)} chars, {p['tag_count']} tags</span></h3>
          <pre>{esc(ig)}</pre>
        </section>
        <section class="col x">
          <h3>X / Twitter <span class="len">{len(x)}/280</span></h3>
          {x_same}
          <pre>{esc(x)}</pre>
        </section>
        <section class="col bsky">
          <h3>Bluesky <span class="len">{len(bsky)}/300</span></h3>
          {bsky_same}
          <pre>{esc(bsky)}</pre>
        </section>
      </div>
      <p class="folder">Folder: <code>{esc(p['folder'])}</code></p>
    </article>""")

    body = "\n".join(cards) if cards else '<p class="warn">No posts bundled for this run.</p>'

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Void Social bundle — {esc(date_str)}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 2rem 1.25rem 4rem;
    background: {CREAM}; color: {INK};
    font-family: Inter, -apple-system, Segoe UI, Roboto, sans-serif;
    line-height: 1.5;
  }}
  h1 {{ font-family: "Playfair Display", Georgia, serif; font-size: 2rem; margin: 0 0 .25rem; }}
  .lede {{ color: #6b6257; margin: 0 0 2rem; }}
  .post {{
    max-width: 1100px; margin: 0 auto 2.5rem; padding: 1.5rem;
    background: #fff; border: 1px solid #e2d9c8; border-radius: 10px;
  }}
  .post > header {{ display: flex; align-items: baseline; gap: .75rem; flex-wrap: wrap; margin-bottom: .75rem; }}
  .badge {{ background: {BRASS}; color: #fff; font-size: .7rem; letter-spacing: .08em;
    text-transform: uppercase; padding: .2rem .55rem; border-radius: 4px; }}
  .nn {{ font-family: "IBM Plex Mono", monospace; color: {BRASS}; font-weight: 700; }}
  .post h2 {{ font-family: "Playfair Display", Georgia, serif; font-size: 1.35rem; margin: 0; flex: 1 1 100%; }}
  .pillar {{ font-size: .75rem; color: #8a8073; text-transform: uppercase; letter-spacing: .05em; }}
  .intent {{ background: #fbf5e6; border-left: 3px solid {BRASS}; padding: .6rem .9rem;
    margin: 0 0 1rem; font-style: italic; }}
  .intent strong {{ font-style: normal; color: {BRASS}; letter-spacing: .06em; margin-right: .4rem; }}
  .thumbs {{ display: flex; gap: .6rem; flex-wrap: wrap; margin-bottom: 1.1rem; }}
  .thumbs img {{ width: 168px; height: 210px; object-fit: cover; border: 1px solid #ddd2bf;
    border-radius: 6px; background: #efe7d6; }}
  .platforms {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }}
  .col h3 {{ font-size: .85rem; margin: 0 0 .4rem; display: flex; justify-content: space-between;
    align-items: baseline; border-bottom: 1px solid #eadfce; padding-bottom: .3rem; }}
  .len {{ font-family: "IBM Plex Mono", monospace; font-size: .7rem; color: #9a9080; font-weight: 400; }}
  pre {{ white-space: pre-wrap; word-wrap: break-word; font-family: "IBM Plex Mono", monospace;
    font-size: .78rem; background: #faf6ee; border: 1px solid #ece2d1; border-radius: 6px;
    padding: .7rem; margin: 0; }}
  .same {{ margin: 0 0 .4rem; font-size: .72rem; color: {BRASS}; }}
  .folder {{ margin: 1rem 0 0; font-size: .72rem; color: #9a9080; }}
  .folder code {{ font-family: "IBM Plex Mono", monospace; }}
  .warn {{ color: #a3341f; font-style: italic; }}
  @media (max-width: 760px) {{ .platforms {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
  <h1>Void Social — manual upload bundle</h1>
  <p class="lede">Run day {esc(date_str)}. {len(posts)} post(s). Nothing was posted. Pick a caption per platform,
  add your personal touch to match the INTENT, then upload the slide images and paste the copy by hand.</p>
  {body}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def export_bundle(
    date_str: str | None = None,
    post_id: str | None = None,
    limit: int | None = None,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> int:
    """Build the dated bundle. Returns the number of posts bundled."""
    day = date_str or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = _fetch(date_str, post_id, limit)

    # Only rows that actually have rendered images + a caption are uploadable.
    usable = [r for r in rows if (r.get("image_urls") and r.get("caption"))]
    skipped = len(rows) - len(usable)
    if skipped:
        print(f"  [export] skipping {skipped} row(s) missing image_urls or caption")
    if not usable:
        print(f"  [export] nothing to bundle for {day}")
        return 0

    root = out_dir / day
    root.mkdir(parents=True, exist_ok=True)

    previews: list[dict] = []
    for idx, row in enumerate(usable, start=1):
        pillar = row.get("pillar") or "vision"
        product = PILLAR_PRODUCT.get(pillar, "news")
        title = _derive_title(pillar, row.get("slide_specs"))
        nn = f"{idx:02d}"
        slug = _slugify(title)
        rel_folder = f"{product}/{nn}-{slug}"
        post_dir = root / product / f"{nn}-{slug}"

        ig_text = _instagram_text(row.get("caption") or "", row.get("hashtags") or [])
        x_text = _x_text(row)
        bsky_text = _bluesky_text(row)
        intent = _intent_text(row)

        slide_files = _write_post_dir(post_dir, row, ig_text, x_text, bsky_text, intent)
        print(
            f"  [export] {nn} {product}/{slug}: {len(slide_files)} slide(s), "
            f"ig={len(ig_text)}c x={len(x_text)}c bsky={len(bsky_text)}c"
        )

        previews.append({
            "nn": nn,
            "pillar": pillar,
            "product_label": PRODUCT_LABEL.get(product, product),
            "title": title,
            "folder": rel_folder,
            "slide_rels": [f"{rel_folder}/{f}" for f in slide_files],
            "ig_text": ig_text,
            "x_text": x_text,
            "bsky_text": bsky_text,
            "intent": intent,
            "tag_count": len(row.get("hashtags") or []),
        })

    index_path = root / "index.html"
    index_path.write_text(_render_index(day, previews), encoding="utf-8")
    print(f"  [export] wrote {index_path} ({len(previews)} post(s))")
    return len(previews)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the manual-upload social bundle.")
    parser.add_argument("--date", default=None, help="run day YYYY-MM-DD (default: today UTC)")
    parser.add_argument("--post-id", default=None, help="bundle a single post by id")
    parser.add_argument("--limit", type=int, default=None, help="max posts to bundle")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="output root (default ./social_out)")
    args = parser.parse_args()

    n = export_bundle(
        date_str=args.date,
        post_id=args.post_id,
        limit=args.limit,
        out_dir=Path(args.out_dir),
    )
    print(f"  [export] done. {n} post(s) bundled.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
