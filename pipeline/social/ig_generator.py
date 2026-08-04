"""
ig_generator.py - Build the next Void social post draft(s).

Three tracks, one locked slide_specs contract (the single source of truth is
frontend/app/lib/supabase-server.ts `SlideSpec`). Every post is a 3-slide
carousel - hook -> substance -> cta - discriminated by `kind`, and the
frontend renders EXACTLY these shapes.

Tracks (CLI `--track`):
  void    (default) the daily trio: one VISION, one METHOD, one EXAMPLE post.
  history           one HISTORY post (optionally pinned with `--event <slug>`).
  weekly            one WEEKLY post from the latest weekly_digests issue.

The capture (Playwright) + caption (Gemini flash-lite) steps take each draft
row from here. State machine: draft -> rendering -> draft -> captioning ->
draft -> (admin) approved -> posted.

Usage:
    python -m pipeline.social.ig_generator                              # void trio
    python -m pipeline.social.ig_generator --track void
    python -m pipeline.social.ig_generator --track history
    python -m pipeline.social.ig_generator --track history --event partition-of-india
    python -m pipeline.social.ig_generator --track weekly
    python -m pipeline.social.ig_generator --when 2026-08-04T13:30:00Z
    python -m pipeline.social.ig_generator --track void --dry-run       # print, no insert

Environment:
    SUPABASE_URL / KEY      existing pipeline vars
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone, date, time as dtime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.supabase_client import supabase  # noqa: E402

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # type: ignore

REPO_ROOT = Path(__file__).resolve().parents[2]
HISTORY_EVENTS_DIR = REPO_ROOT / "data" / "history" / "events"

# We schedule at 13:30 UTC year-round (~8:30-9:30 AM ET); the publisher
# tolerates ±1h drift. The void trio staggers across the day so the three
# drafts don't all target the same minute.
POST_HOUR_UTC = 13
POST_MINUTE_UTC = 30
VOID_TRIO_STAGGER_HOURS = 3

# CTA destinations. All live under the news.voidvision.org domain.
URL_HOME = "news.voidvision.org"
URL_HISTORY = "news.voidvision.org/history"
URL_WEEKLY = "news.voidvision.org/weekly"


# ---------------------------------------------------------------------------
# Copy hygiene - no em/en dashes, never the "void --news" / "void --history"
# tokens (the brand is "Void News" / "Void History"). Applied to every spec
# before insert/print so DB-sourced dynamic text can't leak a banned token.
# ---------------------------------------------------------------------------

_DASH_RE = re.compile(r"\s*[—–]\s*")


def _scrub_text(s: str) -> str:
    s = _DASH_RE.sub(", ", s)
    for bad, good in (
        ("void --news", "Void News"),
        ("void--news", "Void News"),
        ("void --history", "Void History"),
        ("void--history", "Void History"),
    ):
        s = s.replace(bad, good)
    return re.sub(r"  +", " ", s).strip()


def _scrub(obj: Any) -> Any:
    if isinstance(obj, str):
        return _scrub_text(obj)
    if isinstance(obj, list):
        return [_scrub(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _scrub(v) for k, v in obj.items()}
    return obj


def _rotation_day_index(epoch: date, modulo: int) -> int:
    """Deterministic daily rotation. Day == epoch -> 0 (the flagship entry)."""
    today = datetime.now(timezone.utc).date()
    return (today - epoch).days % modulo


# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------

def _next_post_datetime(now_utc: datetime | None = None) -> datetime:
    """Next 13:30 UTC strictly after now (today, or tomorrow if already past)."""
    now = now_utc or datetime.now(timezone.utc)
    target = datetime.combine(
        now.date(), dtime(POST_HOUR_UTC, POST_MINUTE_UTC, tzinfo=timezone.utc)
    )
    if target <= now:
        target += timedelta(days=1)
    return target


def _insert_draft(row: dict[str, Any]) -> str | None:
    try:
        res = supabase.table("ig_posts").insert(row).execute()
        if res.data:
            return res.data[0]["id"]
    except Exception as e:
        print(f"  [error] insert draft: {e}")
    return None


# ===========================================================================
# VISION - evergreen manifesto (hook -> stance -> cta)
# Sourced from the About page (AboutMission.tsx) + onboarding BEATS
# (frontend/app/film/data.ts). Entry 0 is the flagship / launch post.
# ===========================================================================

VISION_EPOCH = date(2026, 8, 4)  # launch day -> rotation index 0 (flagship)

# Rotating hook provocations about the algorithmic feed. Entry 0 is the
# strongest (the launch post uses it). Rotation advances one entry per day so
# the daily VISION post is not identical two days running.
VISION_HOOKS: list[dict[str, str]] = [
    {  # 0 - flagship
        "kicker": "Same stories. Same order. For everyone.",
        "headline": "Two people open the same news app and see two different worlds.",
    },
    {
        "kicker": "A front page, not a feed",
        "headline": "A newspaper prints one front page for everyone. Your feed prints a different one for each of us.",
    },
    {
        "kicker": "Ranked by coverage, not clicks",
        "headline": "The feed learned what keeps you scrolling. It never learned what matters.",
    },
    {
        "kicker": "The spin is the story",
        "headline": "Read one paper and you never see the tilt. Read a hundred and the tilt is all you see.",
    },
    {
        "kicker": "No account, no tracking, no price",
        "headline": "When the news is free and it knows your name, you are the product. We never learn it.",
    },
    {
        "kicker": "Fifty stories, chosen once",
        "headline": "Endless scroll was built to hold your attention, not to end your day informed.",
    },
    {
        "kicker": "Measured, not asserted",
        "headline": "Every story here carries a bias score traced to the words on the page. No opinion, no black box.",
    },
]

# Locked core principle (the stance slide body).
VISION_STANCE_BODY = (
    "One front page. The same stories, in the same order, for everyone. "
    "Ranked once a day by how widely a story is covered, not by clicks."
)
VISION_STANCE_HEADLINE = "A front page, not a feed."
VISION_STANCE_KICKER = "Our stance"

# CTA sign-offs rotate alongside the hook so the closer varies too.
VISION_SIGNOFFS = [
    "See through the void.",
    "One front page. Every side.",
    "The news, measured.",
]


def _vision_specs() -> list[dict[str, Any]]:
    idx = _rotation_day_index(VISION_EPOCH, len(VISION_HOOKS))
    hook = VISION_HOOKS[idx]
    signoff = VISION_SIGNOFFS[idx % len(VISION_SIGNOFFS)]
    return [
        {
            "kind": "vision",
            "variant": "hook",
            "kicker": hook["kicker"],
            "headline": hook["headline"],
        },
        {
            "kind": "vision",
            "variant": "stance",
            "kicker": VISION_STANCE_KICKER,
            "headline": VISION_STANCE_HEADLINE,
            "body": VISION_STANCE_BODY,
        },
        {
            "kind": "vision",
            "variant": "cta",
            "headline": signoff,
            "url": URL_HOME,
        },
    ]


# ===========================================================================
# METHOD - evergreen bias explainer (hook -> sample -> cta)
# Mirrors SIX_AXES + RANKING_SIGNALS from frontend/app/film/data.ts (kept in
# lockstep; do not re-invent). The per-axis sample sentence + score +
# lean_label + principle are IG-specific and live only here.
# ===========================================================================

# Mirror of film/data.ts SIX_AXES (name / brief / signals) - single Python
# reflection of the canonical axis definitions.
SIX_AXES: list[dict[str, str]] = [
    {
        "name": "Political Lean",
        "brief": "Where the article's language falls, left to right.",
        "signals": "Keyword lexicons, entity sentiment (NER + TextBlob), framing phrases, length-adaptive source-baseline blending.",
    },
    {
        "name": "Sensationalism",
        "brief": "How much urgency is inflated beyond the facts.",
        "signals": "Clickbait patterns, superlative density, TextBlob extremity, partisan-attack density.",
    },
    {
        "name": "Opinion vs. Reporting",
        "brief": "Whether it reports facts or argues a position.",
        "signals": "First-person pronouns, subjectivity, attribution density, value judgments, rhetorical questions.",
    },
    {
        "name": "Factual Rigor",
        "brief": "How thoroughly it cites named sources and data.",
        "signals": "Named sources via NER + attribution verbs, org citations, data patterns, direct quotes.",
    },
    {
        "name": "Framing",
        "brief": "Whether word choices nudge the reader.",
        "signals": "50+ charged synonym pairs, omission detection, headline-body divergence, passive voice.",
    },
    {
        "name": "Outlet Tracking",
        "brief": "How each outlet covers each topic over time.",
        "signals": "Per-topic per-outlet EMA with adaptive alpha, stored across pipeline runs.",
    },
]

# Mirror of film/data.ts RANKING_SIGNALS (the bias-blind importance ranker's
# nine weighted contributors + soft-news gate). Kept here in lockstep with the
# frontend so the numbers can't drift; surfaced in the METHOD hook line.
RANKING_SIGNALS: list[dict[str, Any]] = [
    {"name": "Source breadth", "weight": 20},
    {"name": "Story maturity", "weight": 16},
    {"name": "Tier diversity", "weight": 13},
    {"name": "Consequentiality", "weight": 10},
    {"name": "Institutional authority", "weight": 8},
    {"name": "Factual density", "weight": 8},
    {"name": "Divergence", "weight": 7},
    {"name": "Perspective diversity", "weight": 6},
    {"name": "Geographic impact", "weight": 6},
]
RANKING_GATE = "Soft-news category gate (0.78x)"

# Per-axis demonstration sample. `phrases` are located in `text` at build time
# (str.find) so the char-offset highlights the frontend <mark>s can never drift
# from the sentence. `score` is a 0..100 chip value, `lean_label` its caption.
AXIS_SAMPLES: dict[str, dict[str, Any]] = {
    "Political Lean": {
        "text": "The administration defended the crackdown as necessary to restore order.",
        "phrases": ["administration", "crackdown", "restore order"],
        "score": 63,
        "lean_label": "Center-right",
        "principle": "Per article, not per outlet.",
    },
    "Sensationalism": {
        "text": "The unprecedented move sent shockwaves through the entire industry.",
        "phrases": ["unprecedented", "shockwaves", "entire"],
        "score": 78,
        "lean_label": "Inflated",
        "principle": "Fact density beats verb intensity.",
    },
    "Opinion vs. Reporting": {
        "text": "I believe the ruling should have come sooner. Don't you agree?",
        "phrases": ["I believe", "should have", "Don't you agree"],
        "score": 82,
        "lean_label": "Opinion",
        "principle": "Both have a place. Confusing them is the failure.",
    },
    "Factual Rigor": {
        "text": "Treasury Secretary Janet Yellen told reporters at the G7 summit that 2.3% GDP growth was expected.",
        "phrases": ["Treasury Secretary Janet Yellen", "reporters", "2.3% GDP growth"],
        "score": 88,
        "lean_label": "Well-sourced",
        "principle": "Named sources are accountable. Vague ones are not.",
    },
    "Framing": {
        "text": "Protesters clashed with police. Police dispersed the crowd.",
        "phrases": ["clashed with", "dispersed the crowd"],
        "score": 55,
        "lean_label": "Charged",
        "principle": "Same incident. Different verb. Different reader.",
    },
    "Outlet Tracking": {
        "text": "Fox News on immigration averaged lean 68 over 30 days. CNN averaged 35.",
        "phrases": ["Fox News", "68", "CNN", "35"],
        "score": 50,
        "lean_label": "Tracked",
        "principle": "Behavior over time beats labels on the door.",
    },
}

METHOD_EPOCH = date(2026, 8, 4)  # day 0 -> Political Lean (the launch axis)


def _mark(text: str, phrases: list[str]) -> list[dict[str, int]]:
    """Resolve each phrase to a {start,end} char range via str.find, so the
    offsets always match the exact sentence. Missing phrases are skipped."""
    highlights: list[dict[str, int]] = []
    for ph in phrases:
        start = text.find(ph)
        if start < 0:
            continue
        highlights.append({"start": start, "end": start + len(ph)})
    highlights.sort(key=lambda h: h["start"])
    return highlights


def _method_specs(axis_choice: str | None = None) -> list[dict[str, Any]]:
    if axis_choice:
        axis = next(
            (a for a in SIX_AXES if axis_choice.lower() in a["name"].lower()),
            SIX_AXES[0],
        )
    else:
        axis = SIX_AXES[_rotation_day_index(METHOD_EPOCH, len(SIX_AXES))]

    name = axis["name"]
    smp = AXIS_SAMPLES.get(name, AXIS_SAMPLES["Political Lean"])
    top_signal = RANKING_SIGNALS[0]

    return [
        {
            "kind": "method",
            "variant": "hook",
            "kicker": "How Void scores bias",
            "headline": "Bias is not the outlet. It is the words.",
        },
        {
            "kind": "method",
            "variant": "sample",
            "axis_name": name,
            "sample": {
                "text": smp["text"],
                "highlights": _mark(smp["text"], smp["phrases"]),
            },
            "score": smp["score"],
            "lean_label": smp["lean_label"],
            "principle": smp["principle"],
        },
        {
            "kind": "method",
            "variant": "cta",
            "headline": "Rule based. Traceable. Every score shows its math.",
            "url": URL_HOME,
            # Not rendered on-slide, but records that the ranker mirror stays in
            # lockstep (top signal + soft-news gate) for provenance.
            "_ranking_top_signal": f"{top_signal['name']} ({top_signal['weight']})",
            "_ranking_gate": RANKING_GATE,
        },
    ]


# ===========================================================================
# EXAMPLE - dynamic, the real top story across outlets (hook -> spectrum -> cta)
# ===========================================================================

# 7-point sources.political_lean_baseline label -> 0-100 lean score, used as a
# fallback when an article has no per-article bias score. Each value lands in
# the matching _lean_band() bucket; "varies" is omitted (article is skipped).
_BASELINE_LEAN_SCORE: dict[str, int] = {
    "far-left": 12,
    "left": 30,
    "center-left": 42,
    "center": 50,
    "center-right": 58,
    "right": 70,
    "far-right": 88,
}


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


def _select_example_cluster() -> tuple[str, list[dict[str, Any]], int, list[int]] | None:
    """Highest-coverage cluster from the last 48h with >=3 outlets spanning
    >=2 lean bands. Returns (title, headlines[4-6 best-spread], source_count,
    lean_values[all article leans for the KDE ridge])."""
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
        print(f"  [warn] example: cluster query failed: {e}")
        return None

    for cluster in clusters:
        if cluster.get("source_count", 0) < 3:
            continue
        cid = cluster["id"]
        try:
            articles = (
                supabase.table("cluster_articles")
                .select(
                    "article:articles(title, source:sources(name, political_lean_baseline), bias_scores(political_lean))"
                )
                .eq("cluster_id", cid)
                .execute()
                .data
                or []
            )
        except Exception as e:
            print(f"  [warn] example: article query failed: {e}")
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
                lean = _BASELINE_LEAN_SCORE.get(
                    (src.get("political_lean_baseline") or "").strip().lower()
                )
            if lean is None:
                continue
            lean = int(lean)
            bands_seen.add(_lean_band(lean))
            src = a.get("source") or {}
            headlines.append(
                {
                    "outlet": (src.get("name") or "Unknown")[:32],
                    "lean_score": lean,
                    "headline": (a.get("title") or "").strip()[:140],
                }
            )

        if len(bands_seen) < 2 or len(headlines) < 3:
            continue

        headlines.sort(key=lambda h: h["lean_score"])
        # Full per-article lean distribution (0-100) for the KDE ridge on the
        # spectrum slide, captured BEFORE the display down-sample below.
        lean_values = [h["lean_score"] for h in headlines]

        # 3-4 best-spread outlets across the lean axis (the labeled rows). Kept
        # small so the breakdown list clears the bottom-right stamp on the
        # spectrum slide; the KDE ridge still uses the FULL lean distribution.
        target = min(4, max(3, len(headlines)))
        if len(headlines) > target:
            step = len(headlines) / target
            headlines = [headlines[int(i * step)] for i in range(target)]

        title = (cluster.get("title") or "Today's top story").strip()[:100]
        source_count = int(cluster.get("source_count") or len(headlines))
        return title, headlines, source_count, lean_values

    print("  [warn] example: no eligible cluster found")
    return None


def _short_topic(title: str, budget: int = 34) -> str:
    """A short kicker label from the story title: whole words up to `budget`
    chars (never a mid-word cut)."""
    out: list[str] = []
    used = 0
    for w in title.split():
        add = len(w) + (1 if out else 0)
        if used + add > budget and out:
            break
        out.append(w)
        used += add
    label = " ".join(out) if out else title[:budget]
    return label.strip()


def _example_specs() -> list[dict[str, Any]] | None:
    selected = _select_example_cluster()
    if not selected:
        return None
    title, headlines, source_count, lean_values = selected
    topic = _short_topic(title)
    return [
        {
            "kind": "example",
            "variant": "hook",
            "topic": topic,
            "headline": title,
            "outlet_count": source_count,
        },
        {
            "kind": "example",
            "variant": "spectrum",
            "topic": topic,
            "headlines": headlines,
            "lean_values": lean_values,
        },
        {
            "kind": "example",
            "variant": "cta",
            "headline": "The full breakdown is on the front page.",
            "url": URL_HOME,
        },
    ]


# ===========================================================================
# HISTORY - one archival event, many accounts (hook -> perspectives -> cta)
# ===========================================================================

# Stable preferred order - events known to be strong show-don't-tell.
_HISTORY_PREFERRED = [
    "partition-of-india", "tiananmen-square", "cuban-missile-crisis",
    "hiroshima-nagasaki", "rwandan-genocide", "fall-of-berlin-wall",
    "iranian-revolution", "the-holocaust", "transatlantic-slave-trade",
    "haitian-revolution", "indian-independence-movement",
]


def _posted_history_slugs() -> set[str]:
    slugs: set[str] = set()
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
                if isinstance(s, dict) and s.get("event_slug"):
                    slugs.add(s["event_slug"])
    except Exception:
        pass
    return slugs


def _pick_history_event(event_slug: str | None) -> Path | None:
    if not HISTORY_EVENTS_DIR.is_dir():
        print("  [warn] history: events dir missing")
        return None

    if event_slug:
        p = HISTORY_EVENTS_DIR / f"{event_slug}.yaml"
        if p.exists():
            return p
        print(f"  [warn] history: event '{event_slug}' not found")
        return None

    posted = _posted_history_slugs()
    for slug in _HISTORY_PREFERRED:
        p = HISTORY_EVENTS_DIR / f"{slug}.yaml"
        if p.exists() and slug not in posted:
            return p
    for p in sorted(HISTORY_EVENTS_DIR.glob("*.yaml")):
        if p.stem not in posted:
            return p
    print("  [warn] history: no fresh event to post")
    return None


def _perspective_voice(p: dict[str, Any]) -> str:
    """A one-line account of a historiographic viewpoint. Prefers a concise key
    argument, then the narrative's opening sentence, then a notable quote."""
    ka = p.get("key_arguments")
    if isinstance(ka, list) and ka and isinstance(ka[0], str) and ka[0].strip():
        return ka[0].strip()
    for key in ("voice", "argument", "opening_sentence"):
        v = p.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    narr = p.get("narrative")
    if isinstance(narr, str) and narr.strip():
        return _first_sentence(narr, 220)
    quotes = p.get("notable_quotes")
    if isinstance(quotes, list) and quotes:
        q = quotes[0]
        if isinstance(q, dict) and (q.get("text") or "").strip():
            return q["text"].strip()
        if isinstance(q, str) and q.strip():
            return q.strip()
    para = p.get("paragraphs")
    if isinstance(para, list) and para and isinstance(para[0], str):
        return para[0].strip()
    return ""


def _history_specs(event_slug: str | None = None) -> list[dict[str, Any]] | None:
    if yaml is None:
        print("  [warn] history: PyYAML not installed")
        return None
    path = _pick_history_event(event_slug)
    if not path:
        return None
    try:
        event = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as e:
        print(f"  [warn] history: yaml parse {path}: {e}")
        return None

    slug = event.get("slug", path.stem)
    title = event.get("title") or slug.replace("-", " ").title()
    date_display = event.get("date_display") or str(event.get("date_sort") or "")

    perspectives_raw = event.get("perspectives") or []
    perspectives: list[dict[str, str]] = []
    if isinstance(perspectives_raw, list):
        for p in perspectives_raw[:4]:
            if not isinstance(p, dict):
                continue
            lens = (
                p.get("viewpoint") or p.get("lens_name")
                or p.get("lens") or p.get("name") or ""
            ).strip()
            voice = _perspective_voice(p)
            if lens and voice:
                perspectives.append({"lens": lens[:64], "voice": voice[:220]})

    return [
        {
            "kind": "history",
            "variant": "hook",
            "event_slug": slug,
            "date": date_display,
            "headline": title[:100],
        },
        {
            "kind": "history",
            "variant": "perspectives",
            "event_slug": slug,
            "perspectives": perspectives,
        },
        {
            "kind": "history",
            "variant": "cta",
            "event_slug": slug,
            "headline": "Read the full record.",
            "url": URL_HISTORY,
        },
    ]


# ===========================================================================
# WEEKLY - the latest issue in review (hook -> stories -> cta)
# ===========================================================================

def _first_sentence(text: str, limit: int = 160) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    first = re.split(r"(?<=[.!?])\s+", text)[0].strip()
    return first[:limit].rstrip()


def _weekly_specs() -> list[dict[str, Any]] | None:
    try:
        rows = (
            supabase.table("weekly_digests")
            .select(
                "issue_number, cover_headline, cover_text, recap_stories, bias_report_data, edition, created_at"
            )
            .order("created_at", desc=True)
            .limit(5)
            .execute()
            .data
            or []
        )
    except Exception as e:
        print(f"  [warn] weekly: query failed: {e}")
        return None

    if not rows:
        print("  [warn] weekly: no digest rows")
        return None

    # Prefer the world edition; fall back to the newest of any edition.
    digest = next((r for r in rows if (r.get("edition") or "") == "world"), rows[0])

    issue_number = digest.get("issue_number")
    cover_headline = (digest.get("cover_headline") or "This week on Void").strip()[:120]

    # Deck: standfirst from the lead cover story's opening sentence.
    deck = ""
    cover_text = digest.get("cover_text") or []
    if isinstance(cover_text, str):
        try:
            cover_text = json.loads(cover_text)
        except Exception:
            cover_text = []
    if isinstance(cover_text, list) and cover_text:
        lead = cover_text[0] if isinstance(cover_text[0], dict) else {}
        deck = _first_sentence(lead.get("text") or "")

    # Stories: most-contested (from bias_report_data.most_polarized) first,
    # then fill from the week recap. Dedupe by headline text; cap 5.
    stories: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add(headline: str, tag: str | None) -> None:
        h = (headline or "").strip()
        if not h:
            return
        key = h.lower()
        if key in seen or len(stories) >= 5:
            return
        seen.add(key)
        row: dict[str, Any] = {"headline": h[:120]}
        if tag:
            row["tag"] = tag[:32]
        stories.append(row)

    brd = digest.get("bias_report_data") or {}
    if isinstance(brd, str):
        try:
            brd = json.loads(brd)
        except Exception:
            brd = {}
    for mp in (brd.get("most_polarized") or [])[:2] if isinstance(brd, dict) else []:
        if isinstance(mp, dict):
            _add(mp.get("headline", ""), "Most contested")

    recap = digest.get("recap_stories") or []
    if isinstance(recap, str):
        try:
            recap = json.loads(recap)
        except Exception:
            recap = []
    if isinstance(recap, list):
        for s in recap:
            if isinstance(s, dict):
                _add(s.get("headline", ""), (s.get("section") or None))

    if not stories:
        print("  [warn] weekly: no stories resolved; posting hook + cta only")

    return [
        {
            "kind": "weekly",
            "variant": "hook",
            "issue_number": issue_number,
            "headline": cover_headline,
            "deck": deck,
        },
        {
            "kind": "weekly",
            "variant": "stories",
            "stories": stories,
        },
        {
            "kind": "weekly",
            "variant": "cta",
            "headline": "Read the edition.",
            "url": URL_WEEKLY,
        },
    ]


# ===========================================================================
# Track orchestration
# ===========================================================================

def _emit(
    pillar: str,
    specs: list[dict[str, Any]] | None,
    scheduled: datetime,
    dry_run: bool,
) -> str | None:
    if not specs:
        print(f"  [generator] {pillar}: no specs produced, skipping")
        return None
    specs = _scrub(specs)
    if dry_run:
        print(f"\n  [dry-run] {pillar} ({len(specs)} slides) @ {scheduled.isoformat()}")
        print(json.dumps(specs, indent=2, ensure_ascii=False))
        return None
    row = {
        "state": "draft",
        "scheduled_for": scheduled.isoformat(),
        "pillar": pillar,
        "surface": "feed",
        "slide_specs": specs,
    }
    pid = _insert_draft(row)
    if pid:
        variants = ",".join(str(s.get("variant")) for s in specs)
        print(f"  [generator] {pillar} draft -> {pid} ({variants}) for {scheduled.isoformat()}")
    return pid


def run_void(when: datetime | None, dry_run: bool) -> int:
    """Daily trio: VISION, METHOD, EXAMPLE. Staggered across the day."""
    base = when or _next_post_datetime()
    posts: list[tuple[str, list[dict[str, Any]] | None]] = [
        ("vision", _vision_specs()),
        ("method", _method_specs()),
        ("example", _example_specs()),
    ]
    made = 0
    for i, (pillar, specs) in enumerate(posts):
        scheduled = base + timedelta(hours=i * VOID_TRIO_STAGGER_HOURS)
        if _emit(pillar, specs, scheduled, dry_run):
            made += 1
    return made


def run_history(when: datetime | None, event_slug: str | None, dry_run: bool) -> int:
    scheduled = when or _next_post_datetime()
    return 1 if _emit("history", _history_specs(event_slug), scheduled, dry_run) else 0


def run_weekly(when: datetime | None, dry_run: bool) -> int:
    scheduled = when or _next_post_datetime()
    return 1 if _emit("weekly", _weekly_specs(), scheduled, dry_run) else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Void social post drafts.")
    parser.add_argument(
        "--track",
        default="void",
        choices=["void", "history", "weekly"],
        help="void (daily trio, default) | history | weekly",
    )
    parser.add_argument(
        "--event",
        default=None,
        help="history track only: pin a specific event slug",
    )
    parser.add_argument(
        "--when",
        default=None,
        help="ISO datetime for scheduled_for; default = next 13:30 UTC",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the slide_specs and exit without inserting",
    )
    args = parser.parse_args()

    when: datetime | None = None
    if args.when:
        when = datetime.fromisoformat(args.when.replace("Z", "+00:00"))

    if args.track == "history":
        run_history(when, args.event, args.dry_run)
    elif args.track == "weekly":
        run_weekly(when, args.dry_run)
    else:
        run_void(when, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
