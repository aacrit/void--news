"""
ig_generator.py — Build the next IG post draft row.

Daily cron entry. Decides whether a post is due in the next 48h. If yes,
picks a pillar (rotation: 4 receipt / 2 method / 2 history / 2 brief per
8-post cycle), pulls source data from Supabase + filesystem, writes a draft
ig_posts row with slide_specs populated. The capture + caption modules
then take it from there.

Special mode: --launch-slot N seeds the 10 launch posts directly with the
content specified in the plan.

Usage:
    python -m pipeline.social.ig_generator                       # auto pick
    python -m pipeline.social.ig_generator --launch-slot 1       # seed launch #1
    python -m pipeline.social.ig_generator --seed-all-launch     # seed all 10
    python -m pipeline.social.ig_generator --pillar receipt      # force pillar
    python -m pipeline.social.ig_generator --when 2026-05-19T13:30:00Z

Environment:
    SUPABASE_URL / KEY      existing pipeline vars
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone, time as dtime
from pathlib import Path
from typing import Any, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.supabase_client import supabase  # noqa: E402

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore

REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORY_EVENTS_DIR = REPO_ROOT / "data" / "history" / "events"

# 8:30 AM ET ≈ 13:30 UTC during summer time, 12:30 UTC in winter.
# We schedule at 13:30 UTC year-round; the publisher tolerates ±1h drift.
POST_HOUR_UTC = 13
POST_MINUTE_UTC = 30

# Rotation week: 8 posts over 4 weeks (Mon + Thu) = receipt receipt method
# history brief receipt method history.
ROTATION = ["receipt", "receipt", "method", "history", "brief", "receipt", "method", "history"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _next_post_datetime(now_utc: datetime | None = None) -> datetime:
    """Next Monday or Thursday at 13:30 UTC strictly after now."""
    now = now_utc or datetime.now(timezone.utc)
    target_time = dtime(POST_HOUR_UTC, POST_MINUTE_UTC, tzinfo=timezone.utc)
    # Monday=0, Thursday=3
    for delta in range(0, 8):
        candidate_date = now.date() + timedelta(days=delta)
        candidate = datetime.combine(candidate_date, target_time)
        if candidate.weekday() not in (0, 3):
            continue
        if candidate > now:
            return candidate
    return datetime.combine(now.date() + timedelta(days=7), target_time)


def _existing_slot_count(week_anchor: datetime) -> int:
    """How many posts already scheduled in the 7-day window."""
    start = (week_anchor - timedelta(days=7)).isoformat()
    end = (week_anchor + timedelta(days=7)).isoformat()
    res = (
        supabase.table("ig_posts")
        .select("id")
        .gte("scheduled_for", start)
        .lte("scheduled_for", end)
        .execute()
    )
    return len(res.data or [])


def _insert_draft(row: dict[str, Any]) -> str | None:
    try:
        res = supabase.table("ig_posts").insert(row).execute()
        if res.data:
            return res.data[0]["id"]
    except Exception as e:
        print(f"  [error] insert draft: {e}")
    return None


def _existing_launch_slot(slot: int) -> bool:
    res = supabase.table("ig_posts").select("id").eq("launch_slot", slot).limit(1).execute()
    return bool(res.data)


# ---------------------------------------------------------------------------
# Pillar generators — each returns slide_specs list[dict]
# ---------------------------------------------------------------------------

def _gen_receipt(topic_hint: str | None = None) -> list[dict[str, Any]] | None:
    """Pick the highest-coverage cluster from the last 48h with ≥3 outlets
    across ≥2 lean bands. Pull article headlines + lean scores."""

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()

    try:
        clusters = (
            supabase.table("story_clusters")
            .select("id, title, source_count")
            .gte("first_published", cutoff)
            .order("source_count", desc=True)
            .limit(20)
            .execute()
            .data
            or []
        )
    except Exception as e:
        print(f"  [warn] receipt: cluster query failed: {e}")
        return None

    for cluster in clusters:
        if cluster.get("source_count", 0) < 3:
            continue
        cid = cluster["id"]
        try:
            articles = (
                supabase.table("cluster_articles")
                .select(
                    "article:articles(title, source:sources(name, lean_label, lean_score), bias_scores(political_lean))"
                )
                .eq("cluster_id", cid)
                .execute()
                .data
                or []
            )
        except Exception as e:
            print(f"  [warn] receipt: article query failed: {e}")
            continue

        headlines: list[dict[str, Any]] = []
        bands_seen: set[int] = set()
        for row in articles:
            a = row.get("article") or {}
            if not a:
                continue
            bias = a.get("bias_scores")
            if isinstance(bias, list):
                bias = bias[0] if bias else None
            lean = (bias or {}).get("political_lean")
            if lean is None:
                src = a.get("source") or {}
                lean = src.get("lean_score")
            if lean is None:
                continue
            lean = int(lean)
            bands_seen.add(_lean_band(lean))
            src = a.get("source") or {}
            headlines.append(
                {
                    "outlet": src.get("name", "Unknown")[:32],
                    "lean_score": lean,
                    "headline": (a.get("title") or "").strip()[:140],
                }
            )

        if len(bands_seen) < 2:
            continue
        if len(headlines) < 3:
            continue

        # 5 best-spread headlines
        headlines.sort(key=lambda h: h["lean_score"])
        if len(headlines) > 5:
            step = len(headlines) / 5
            headlines = [headlines[int(i * step)] for i in range(5)]

        topic = (cluster.get("title") or topic_hint or "today").strip()[:80]
        return [
            {
                "kind": "receipt",
                "topic": topic,
                "headlines": headlines,
                "caption": f"{len(headlines)} outlets. Same story.",
            }
        ]

    print("  [warn] receipt: no eligible cluster found")
    return None


def _lean_band(score: int) -> int:
    if score <= 25:
        return 0
    if score <= 42:
        return 1
    if score <= 58:
        return 2
    if score <= 75:
        return 3
    return 4


def _gen_method(axis_choice: str | None = None) -> list[dict[str, Any]]:
    """Round-robin through the six axes.
    Axis content is canonical (mirrors film/data.ts SIX_AXES)."""

    AXES = [
        {
            "axis_name": "Political Lean",
            "brief": "Where the article falls on the spectrum.",
            "signals": "Keyword lexicons, NER entity sentiment, framing phrases, sparsity-weighted source baseline blending.",
            "sample": {
                "text": "The administration defended the crackdown as necessary to restore order.",
                "highlights": [
                    {"start": 4, "end": 18},   # administration
                    {"start": 27, "end": 36},  # crackdown
                    {"start": 55, "end": 68},  # restore order
                ],
            },
            "principle": "Per article, not per outlet.",
        },
        {
            "axis_name": "Sensationalism",
            "brief": "How much urgency is inflated beyond the facts.",
            "signals": "Clickbait patterns, superlative density, TextBlob extremity, partisan attack density (capped 30 pts).",
            "sample": {
                "text": "The unprecedented move sent shockwaves through the entire industry.",
                "highlights": [
                    {"start": 4, "end": 18},   # unprecedented
                    {"start": 28, "end": 38},  # shockwaves
                    {"start": 51, "end": 57},  # entire
                ],
            },
            "principle": "Fact density beats verb intensity.",
        },
        {
            "axis_name": "Opinion vs Reporting",
            "brief": "Whether it reports facts or argues a position.",
            "signals": "First-person pronouns, subjectivity score, attribution density (24 investigative patterns), rhetorical questions.",
            "sample": {
                "text": "I believe the decision should have been made earlier. Don't you agree?",
                "highlights": [
                    {"start": 0, "end": 9},
                    {"start": 23, "end": 39},
                    {"start": 54, "end": 70},
                ],
            },
            "principle": "Both have a place. Confusing them is the failure.",
        },
        {
            "axis_name": "Factual Rigor",
            "brief": "How thoroughly it cites named sources and data.",
            "signals": "Named sources via NER + attribution verbs, org citations, data patterns, direct quotes, vague-source penalty.",
            "sample": {
                "text": "Treasury Secretary Janet Yellen told reporters at the G7 summit that 2.3% GDP growth was expected.",
                "highlights": [
                    {"start": 0, "end": 30},
                    {"start": 54, "end": 63},
                    {"start": 69, "end": 87},
                ],
            },
            "principle": "Named sources are accountable; vague ones are not.",
        },
        {
            "axis_name": "Framing",
            "brief": "Whether word choices nudge the reader.",
            "signals": "50+ charged synonym pairs, cluster-aware omission detection, headline-body divergence, passive voice (capped 30).",
            "sample": {
                "text": "Protesters clashed with police. Police dispersed the crowd.",
                "highlights": [
                    {"start": 11, "end": 23},
                    {"start": 39, "end": 49},
                ],
            },
            "principle": "Same incident. Different verb. Different reader.",
        },
        {
            "axis_name": "Outlet Tracking",
            "brief": "How each outlet covers each topic over time.",
            "signals": "Per-topic per-outlet EMA with adaptive alpha. Stored across pipeline runs.",
            "sample": {
                "text": "Fox News on immigration: lean 68 avg over 30 days. CNN: lean 35 avg.",
                "highlights": [
                    {"start": 25, "end": 31},
                    {"start": 56, "end": 62},
                ],
            },
            "principle": "Behavior over time beats labels on the door.",
        },
    ]

    if axis_choice:
        chosen = next((a for a in AXES if axis_choice.lower() in a["axis_name"].lower()), AXES[0])
    else:
        chosen = AXES[_rotation_index() % len(AXES)]

    slides: list[dict[str, Any]] = [
        {
            "kind": "method",
            "axis_name": chosen["axis_name"],
            "brief": chosen["brief"],
            "signals": chosen["signals"],
            "sample": chosen["sample"],
            "principle": chosen["principle"],
        }
    ]
    return slides


def _gen_history() -> list[dict[str, Any]] | None:
    """Pick a history event YAML with show-don't-tell-grade prose.
    Build a 5-slide carousel: lead fact, three perspectives, CTA."""

    if yaml is None:
        print("  [warn] history: PyYAML not installed")
        return None
    if not HISTORY_EVENTS_DIR.is_dir():
        print("  [warn] history: events dir missing")
        return None

    posted_slugs = set()
    try:
        res = (
            supabase.table("ig_posts")
            .select("slide_specs")
            .eq("pillar", "history")
            .execute()
            .data
            or []
        )
        for row in res:
            specs = row.get("slide_specs") or []
            for s in specs if isinstance(specs, list) else []:
                if isinstance(s, dict):
                    slug = s.get("event_slug")
                    if slug:
                        posted_slugs.add(slug)
    except Exception:
        pass

    # Stable preferred order — events known to be strong show-don't-tell
    PREFERRED = [
        "partition-of-india", "tiananmen-square", "cuban-missile-crisis",
        "hiroshima-nagasaki", "rwandan-genocide", "fall-of-berlin-wall",
        "iranian-revolution", "the-holocaust", "transatlantic-slave-trade",
        "haitian-revolution", "indian-independence-movement",
    ]

    candidates: list[Path] = []
    for slug in PREFERRED:
        p = HISTORY_EVENTS_DIR / f"{slug}.yaml"
        if p.exists() and slug not in posted_slugs:
            candidates.append(p)

    # Fall back to anything else in the directory
    if not candidates:
        for p in sorted(HISTORY_EVENTS_DIR.glob("*.yaml")):
            if p.stem not in posted_slugs:
                candidates.append(p)
                break

    if not candidates:
        print("  [warn] history: no fresh event to post")
        return None

    path = candidates[0]
    try:
        event = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        print(f"  [warn] history: yaml parse {path}: {e}")
        return None

    slug = event.get("slug", path.stem)
    title = event.get("title") or slug.replace("-", " ").title()
    date_display = event.get("date_display") or str(event.get("date_sort") or "")

    # Lead fact: first sentence of summary, cleaned.
    summary = (event.get("summary") or "").strip()
    lead = summary.split(". ")[0].strip().rstrip(".") + "." if summary else title

    perspectives_raw = event.get("perspectives") or []
    perspectives: list[dict[str, str]] = []
    if isinstance(perspectives_raw, list):
        for p in perspectives_raw[:3]:
            if not isinstance(p, dict):
                continue
            lens = (p.get("lens_name") or p.get("lens") or p.get("name") or "").strip()
            voice = (p.get("voice") or p.get("argument") or p.get("opening_sentence") or "").strip()
            if not voice and isinstance(p.get("paragraphs"), list) and p["paragraphs"]:
                voice = (p["paragraphs"][0] or "").strip()
            if lens and voice:
                perspectives.append({"lens": lens[:64], "voice": voice[:280]})

    slides: list[dict[str, Any]] = [
        {
            "kind": "history",
            "event_slug": slug,
            "date": date_display,
            "lead_fact": lead[:280],
        }
    ]
    for p in perspectives:
        slides.append(
            {
                "kind": "history",
                "event_slug": slug,
                "date": date_display,
                "perspective": p,
            }
        )
    if len(slides) > 1:
        slides[-1]["cta"] = "void --history"

    return slides


def _gen_brief_pullquote() -> list[dict[str, Any]] | None:
    """Pull a high-impact sentence from the last 7 daily briefs."""

    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    try:
        briefs = (
            supabase.table("daily_briefs")
            .select("opinion_text, tldr_text, opinion_headline, tldr_headline, edition, created_at")
            .gte("created_at", cutoff)
            .order("created_at", desc=True)
            .limit(7)
            .execute()
            .data
            or []
        )
    except Exception as e:
        print(f"  [warn] brief: query failed: {e}")
        return None

    # Score sentences by length and concrete-noun density (approx).
    candidates: list[tuple[float, str, str]] = []  # score, text, date
    for b in briefs:
        for field in ("opinion_text", "tldr_text"):
            text = (b.get(field) or "").strip()
            if not text:
                continue
            for sent in _split_sentences(text):
                if len(sent) < 60 or len(sent) > 220:
                    continue
                score = _impact_score(sent)
                candidates.append((score, sent, b.get("created_at", "")[:10]))

    if not candidates:
        print("  [warn] brief: no sentences eligible")
        return None

    candidates.sort(reverse=True)
    best = candidates[0]
    return [
        {
            "kind": "brief",
            "variant": "pullquote",
            "content": best[1],
            "attribution": f"void --news daily brief, {best[2]}",
        }
    ]


def _split_sentences(text: str) -> Iterable[str]:
    import re
    # Light sentence splitter — good enough for editorial prose.
    parts = re.split(r"(?<=[.!?])\s+", text)
    for p in parts:
        s = p.strip()
        if s:
            yield s


def _impact_score(sent: str) -> float:
    import re
    word_count = len(re.findall(r"\b\w+\b", sent))
    if word_count == 0:
        return 0.0
    long_words = sum(1 for w in re.findall(r"\b\w+\b", sent) if len(w) >= 7)
    digits = len(re.findall(r"\d", sent))
    proper = len(re.findall(r"\b[A-Z][a-z]+", sent))
    return (long_words / word_count) * 10 + digits * 1.5 + proper * 0.5


# ---------------------------------------------------------------------------
# Launch slot definitions
# ---------------------------------------------------------------------------

DIVERGENT_HEADLINES = [
    {"outlet": "Reuters", "lean_score": 48, "headline": "US and China resume trade talks amid tariff tensions"},
    {"outlet": "Fox News", "lean_score": 72, "headline": "Trump administration takes hard line as China trade talks restart"},
    {"outlet": "The Guardian", "lean_score": 38, "headline": "Trade war uncertainty looms as US-China negotiations resume"},
    {"outlet": "Al Jazeera", "lean_score": 35, "headline": "Global markets brace as superpowers return to negotiating table"},
    {"outlet": "New York Post", "lean_score": 74, "headline": "Biden caves to China pressure, agrees to new round of trade talks"},
]


def _launch_slides(slot: int) -> tuple[str, list[dict[str, Any]]]:
    """Return (pillar, slide_specs) for one of the 10 launch posts."""
    if slot == 1:
        return "brief", [
            {
                "kind": "brief",
                "variant": "manifesto",
                "content": "Same stories. Same order. For everyone.",
                "attribution": "void --news. Bias scored per article, not per outlet. No accounts, no tracking, free forever.",
            }
        ]
    if slot == 2:
        return "receipt", [
            {
                "kind": "receipt",
                "topic": "US-China trade",
                "headlines": DIVERGENT_HEADLINES,
                "caption": "Same trade story. Five outlets. Five framings.",
            }
        ]
    if slot == 3:
        return "method", _gen_method("Political Lean")
    if slot == 4:
        receipt = _gen_receipt()
        if not receipt:
            # Curated fallback — guarantees the launch slot exists.
            return "receipt", [
                {
                    "kind": "receipt",
                    "topic": "Headline vs body",
                    "headlines": [
                        {"outlet": "Headline", "lean_score": 71, "headline": "The same story, headline framing: 71"},
                        {"outlet": "Body text", "lean_score": 48, "headline": "The same story, body framing: 48"},
                    ],
                    "caption": "Editors write headlines for clicks. We score both.",
                }
            ]
        return "receipt", receipt
    if slot == 5:
        # History — Partition has the strongest opening fact already.
        hist = _gen_history_for("partition-of-india")
        if hist:
            return "history", hist
        return "history", [
            {
                "kind": "history",
                "event_slug": "partition-of-india",
                "date": "August 14-15, 1947",
                "lead_fact": "A lawyer who'd never been to India drew the border in five weeks. 15 million crossed it.",
            }
        ]
    if slot == 6:
        return "heatmap", [
            {
                "kind": "heatmap",
                "topic": "Coverage of [topic of the week]",
                "countries": [
                    {"code": "US", "lean": 52, "source_count": 43},
                    {"code": "UK", "lean": 46, "source_count": 28},
                    {"code": "IN", "lean": 49, "source_count": 25},
                    {"code": "DE", "lean": 44, "source_count": 18},
                    {"code": "JP", "lean": 51, "source_count": 14},
                    {"code": "BR", "lean": 47, "source_count": 12},
                    {"code": "ZA", "lean": 42, "source_count": 9},
                    {"code": "AU", "lean": 53, "source_count": 9},
                ],
                "caption": "1,013 sources. 158 countries. One topic.",
            }
        ]
    if slot == 7:
        brief = _gen_brief_pullquote()
        if not brief:
            return "brief", [
                {
                    "kind": "brief",
                    "variant": "pullquote",
                    "content": "The brief reports on the world, not on the coverage of the world.",
                    "attribution": "void --news daily brief",
                }
            ]
        return "brief", brief
    if slot == 8:
        return "method", _gen_method("Unscored")  # falls back to first axis
    if slot == 9:
        receipt = _gen_receipt()
        return "receipt", receipt or [
            {
                "kind": "receipt",
                "topic": "Protest vs police",
                "headlines": [
                    {"outlet": "Far-left outlet", "lean_score": 14, "headline": "Protesters clashed with police"},
                    {"outlet": "Centrist outlet", "lean_score": 50, "headline": "Police and protesters clashed"},
                    {"outlet": "Far-right outlet", "lean_score": 88, "headline": "Police dispersed the crowd"},
                ],
            }
        ]
    if slot == 10:
        hist = _gen_history_for("iranian-revolution") or _gen_history()
        return "history", hist or []

    raise ValueError(f"Unknown launch slot {slot}")


def _gen_history_for(slug: str) -> list[dict[str, Any]] | None:
    """History-by-slug variant. Used by the launch slots."""
    if yaml is None:
        return None
    path = HISTORY_EVENTS_DIR / f"{slug}.yaml"
    if not path.exists():
        return None
    try:
        event = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None

    title = event.get("title") or slug.replace("-", " ").title()
    date_display = event.get("date_display") or str(event.get("date_sort") or "")
    summary = (event.get("summary") or "").strip()
    lead = summary.split(". ")[0].strip().rstrip(".") + "." if summary else title

    perspectives_raw = event.get("perspectives") or []
    perspectives: list[dict[str, str]] = []
    if isinstance(perspectives_raw, list):
        for p in perspectives_raw[:3]:
            if not isinstance(p, dict):
                continue
            lens = (p.get("lens_name") or p.get("lens") or p.get("name") or "").strip()
            voice = (p.get("voice") or p.get("argument") or p.get("opening_sentence") or "").strip()
            if not voice and isinstance(p.get("paragraphs"), list) and p["paragraphs"]:
                voice = (p["paragraphs"][0] or "").strip()
            if lens and voice:
                perspectives.append({"lens": lens[:64], "voice": voice[:280]})

    slides: list[dict[str, Any]] = [
        {"kind": "history", "event_slug": slug, "date": date_display, "lead_fact": lead[:280]}
    ]
    for p in perspectives:
        slides.append({"kind": "history", "event_slug": slug, "date": date_display, "perspective": p})
    return slides


def _rotation_index() -> int:
    """Stable index into ROTATION based on completed post count."""
    try:
        res = supabase.table("ig_posts").select("id", count="exact").not_.is_("posted_at", "null").execute()
        return int(getattr(res, "count", 0) or 0)
    except Exception:
        return 0


def _pillar_for_next() -> str:
    idx = _rotation_index() % len(ROTATION)
    return ROTATION[idx]


def _dispatch_pillar(pillar: str) -> list[dict[str, Any]] | None:
    if pillar == "receipt":
        return _gen_receipt()
    if pillar == "method":
        return _gen_method()
    if pillar == "history":
        return _gen_history()
    if pillar == "brief":
        return _gen_brief_pullquote()
    return None


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------

def seed_launch_slot(slot: int, when: datetime | None = None) -> str | None:
    if _existing_launch_slot(slot):
        print(f"  [generator] launch slot {slot} already exists, skipping")
        return None
    pillar, slides = _launch_slides(slot)
    if not slides:
        print(f"  [generator] launch slot {slot}: no slides produced")
        return None

    scheduled = when or _launch_default_when(slot)
    row = {
        "state": "draft",
        "scheduled_for": scheduled.isoformat(),
        "pillar": pillar,
        "surface": "feed",
        "launch_slot": slot,
        "slide_specs": slides,
    }
    pid = _insert_draft(row)
    if pid:
        print(f"  [generator] launch slot {slot} → {pid} ({pillar}, {len(slides)} slides)")
    return pid


def _launch_default_when(slot: int) -> datetime:
    """Map launch slot 1..10 to a Mon/Thu starting Mon next week.
    Slot 1 → Mon W1, slot 2 → Thu W1, …, slot 10 → Thu W5."""
    base = _next_post_datetime()
    # Walk forward (slot-1) post-days.
    posts_seen = 0
    cursor = base
    while posts_seen < (slot - 1):
        cursor = cursor + timedelta(days=1)
        if cursor.weekday() in (0, 3):
            posts_seen += 1
    return cursor


def generate_next(when: datetime | None = None, force_pillar: str | None = None) -> str | None:
    scheduled = when or _next_post_datetime()
    pillar = force_pillar or _pillar_for_next()
    slides = _dispatch_pillar(pillar)

    if not slides:
        # If the data-driven path failed, fall back to a method post (always works).
        if pillar != "method":
            print(f"  [generator] {pillar} fell through, falling back to method")
            pillar = "method"
            slides = _gen_method()
        if not slides:
            return None

    row = {
        "state": "draft",
        "scheduled_for": scheduled.isoformat(),
        "pillar": pillar,
        "surface": "feed",
        "slide_specs": slides,
    }
    pid = _insert_draft(row)
    if pid:
        print(f"  [generator] {pillar} draft → {pid} ({len(slides)} slides) for {scheduled.isoformat()}")
    return pid


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--launch-slot", type=int, default=None, help="1..10")
    parser.add_argument("--seed-all-launch", action="store_true")
    parser.add_argument("--pillar", default=None, choices=["receipt", "method", "history", "brief", "heatmap"])
    parser.add_argument("--when", default=None, help="ISO datetime; default = next Mon/Thu 13:30 UTC")
    args = parser.parse_args()

    when: datetime | None = None
    if args.when:
        when = datetime.fromisoformat(args.when.replace("Z", "+00:00"))

    if args.seed_all_launch:
        for slot in range(1, 11):
            seed_launch_slot(slot)
        return 0

    if args.launch_slot is not None:
        seed_launch_slot(args.launch_slot, when=when)
        return 0

    generate_next(when=when, force_pillar=args.pillar)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
