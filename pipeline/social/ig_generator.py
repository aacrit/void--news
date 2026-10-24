"""
ig_generator.py - Build the next Void social post draft(s).

Three tracks, one locked slide_specs contract (the single source of truth is
frontend/app/lib/supabase-server.ts `SlideSpec`). Every post is a 3-slide
carousel - hook -> substance -> cta - discriminated by `kind`, and the
frontend renders EXACTLY these shapes.

Tracks (CLI `--track`):
  void          (default) the daily trio: one VISION, one METHOD, one EXAMPLE.
  vision-series fable's six debut Vision posts (data/social/debut_vision_series
                .json) in ONE run. Each is a full vision carousel built from its
                eyebrow/hook/substance/cta, with caption + per-platform variants
                + intent PRE-FILLED verbatim, so the Gemini caption pass skips
                them (it only touches caption IS NULL). capture + export then
                render + bundle all six.
  history       one HISTORY post (optionally pinned with `--event <slug>`).
  weekly        one WEEKLY post from the latest weekly_digests issue.

The capture (Playwright) + caption (Gemini flash-lite) steps take each draft
row from here. State machine: draft -> rendering -> draft -> captioning ->
draft -> (admin) approved -> posted.

Usage:
    python -m pipeline.social.ig_generator                              # void trio
    python -m pipeline.social.ig_generator --track void
    python -m pipeline.social.ig_generator --track vision-series        # 6 debut Visions
    python -m pipeline.social.ig_generator --track history
    python -m pipeline.social.ig_generator --track history --event partition-of-india
    python -m pipeline.social.ig_generator --track weekly
    python -m pipeline.social.ig_generator --when 2026-08-04T13:30:00Z
    python -m pipeline.social.ig_generator --track void --dry-run       # print, no insert

Environment:
    SUPABASE_URL / KEY      existing pipeline vars
    SOCIAL_NOTE             optional free-text steer for THIS batch (topic /
                            tone); best-effort soft signal.
    SOCIAL_VISION_HOOK      optional override for the VISION post's slide 1
                            (and optionally slides 2/3). Format:
                            "HEADLINE || SUBSTANCE || CTA" (pipe-separated;
                            missing parts fall back to the normal rotation).
                            Empty/unset = the VISION_HOOKS rotation, unchanged.
"""

from __future__ import annotations

import argparse
import json
import os
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


_VARIANT_COLS = ("caption_x", "caption_bluesky", "intent")


def _insert_draft(row: dict[str, Any]) -> str | None:
    try:
        res = supabase.table("ig_posts").insert(row).execute()
        if res.data:
            return res.data[0]["id"]
    except Exception as e:
        msg = str(e).lower()
        # Migration 074 (caption_x / caption_bluesky / intent) not applied yet:
        # retry without those columns so the caption still lands. ig_export then
        # derives the X/Bluesky variants from the IG caption. Rows without those
        # columns are unaffected (default behavior unchanged).
        if any(c in row for c in _VARIANT_COLS) and (
            "column" in msg or any(c in msg for c in _VARIANT_COLS)
        ):
            slim = {k: v for k, v in row.items() if k not in _VARIANT_COLS}
            print(f"  [warn] variant columns missing (apply migration 074); inserting caption only: {e}")
            try:
                res = supabase.table("ig_posts").insert(slim).execute()
                if res.data:
                    return res.data[0]["id"]
            except Exception as e2:
                print(f"  [error] insert draft (slim fallback): {e2}")
                return None
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


def _vision_hook_override() -> dict[str, str | None] | None:
    """Parse SOCIAL_VISION_HOOK (a custom debut hook). Format is pipe-separated
    "HEADLINE || SUBSTANCE || CTA"; any missing/blank part falls back to the
    normal rotation. Empty/unset -> None (rotation unchanged)."""
    raw = (os.environ.get("SOCIAL_VISION_HOOK") or "").strip()
    if not raw:
        return None
    parts = [p.strip() for p in raw.split("||")]
    return {
        "headline": parts[0] if len(parts) > 0 and parts[0] else None,
        "substance": parts[1] if len(parts) > 1 and parts[1] else None,
        "cta": parts[2] if len(parts) > 2 and parts[2] else None,
    }


def _vision_specs() -> list[dict[str, Any]]:
    idx = _rotation_day_index(VISION_EPOCH, len(VISION_HOOKS))
    hook = VISION_HOOKS[idx]
    signoff = VISION_SIGNOFFS[idx % len(VISION_SIGNOFFS)]

    # Optional debut-hook override (env). Only the parts supplied are replaced;
    # the rest stay on the deterministic rotation, so an unset var is a no-op.
    ov = _vision_hook_override()
    hook_headline = hook["headline"]
    stance_body = VISION_STANCE_BODY
    cta_headline = signoff
    if ov:
        if ov["headline"]:
            hook_headline = ov["headline"]
        if ov["substance"]:
            stance_body = ov["substance"]
        if ov["cta"]:
            cta_headline = ov["cta"]
        print(
            "  [vision] SOCIAL_VISION_HOOK override applied "
            f"(headline={'y' if ov['headline'] else 'n'}, "
            f"substance={'y' if ov['substance'] else 'n'}, "
            f"cta={'y' if ov['cta'] else 'n'})"
        )

    return [
        {
            "kind": "vision",
            "variant": "hook",
            "kicker": hook["kicker"],
            "headline": hook_headline,
        },
        {
            "kind": "vision",
            "variant": "stance",
            "kicker": VISION_STANCE_KICKER,
            "headline": VISION_STANCE_HEADLINE,
            "body": stance_body,
        },
        {
            "kind": "vision",
            "variant": "cta",
            "headline": cta_headline,
            "url": URL_HOME,
        },
    ]


# ===========================================================================
# VISION SERIES - fable's six debut Vision posts, rendered in ONE run.
#
# A curated content bank (data/social/debut_vision_series.json) of six distinct
# Vision posts. Each renders through the SAME Vision.tsx template as the daily
# rotation (hook -> stance -> cta), built from its own eyebrow/hook/substance/
# cta, with caption + per-platform variants + intent PRE-FILLED verbatim. The
# caption fields are inserted straight onto the row, so ig_caption.py (which
# only touches rows with caption IS NULL) skips them: no Gemini call, fable's
# exact copy preserved. capture + export then render + bundle all six.
#
# On-slide text is trimmed to fit the template gracefully; the FULL prose always
# survives in the pre-filled caption.
# ===========================================================================

_SERIES_JSON = REPO_ROOT / "data" / "social" / "debut_vision_series.json"

# On-slide budgets. Only what is RENDERED onto the slide is capped; the full
# substance / CTA prose lives in the caption. Sentence-aware (whole sentences
# only, never a mid-sentence cut), matching the short editorial rhythm the
# Vision template is designed for.
_SERIES_STANCE_BODY_MAX = 240   # ig-vision__body: 46px column, ~20ch wide
_SERIES_CTA_LINE_MAX = 95       # ig-cta__line: 62px sign-off, ~16ch wide

_URL_TAIL_RE = re.compile(r"\s*news\.voidvision\.org\s*$", re.IGNORECASE)
# Sentence terminator: . ! or ? plus an optional closing quote, at a word
# boundary. The debut copy has no abbreviations, so no special-casing is needed.
_SENTENCE_END_RE = re.compile(r"[.!?][\"'’”]?(?=\s|$)")


def _split_sentences(text: str) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    out: list[str] = []
    start = 0
    for m in _SENTENCE_END_RE.finditer(text):
        out.append(text[start:m.end()].strip())
        start = m.end()
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return [s for s in out if s]


def _fit_sentences(text: str, budget: int) -> str:
    """Keep whole sentences while the running length stays within `budget`.
    Always keeps at least the first sentence (even if it alone exceeds budget),
    so the on-slide line is never empty and never cut mid-sentence."""
    sentences = _split_sentences(text)
    if not sentences:
        return (text or "").strip()
    kept = [sentences[0]]
    total = len(sentences[0])
    for s in sentences[1:]:
        if total + 1 + len(s) > budget:
            break
        kept.append(s)
        total += 1 + len(s)
    return " ".join(kept)


def _strip_trailing_url(text: str) -> str:
    """Drop a trailing 'news.voidvision.org' so the CTA line does not duplicate
    the URL the CTA slide renders in its own field. The sentence's terminal
    period is preserved (only whitespace before the URL is consumed)."""
    return _URL_TAIL_RE.sub("", (text or "").strip()).strip()


def _load_debut_vision_series() -> list[dict[str, Any]]:
    with open(_SERIES_JSON, encoding="utf-8") as f:
        data = json.load(f)
    posts = data.get("posts") if isinstance(data, dict) else data
    return list(posts or [])


def _debut_vision_series_specs(post: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the three vision slide_specs (hook -> stance -> cta) from one
    debut post. Shape matches VisionSlideSpec in supabase-server.ts exactly:
    hook {kicker, headline}, stance {kicker, body}, cta {headline, url}."""
    eyebrow = (post.get("eyebrow") or "").strip()
    hook = (post.get("hook") or "").strip()
    body = _fit_sentences((post.get("substance") or "").strip(), _SERIES_STANCE_BODY_MAX)
    cta_line = _fit_sentences(_strip_trailing_url(post.get("cta") or ""), _SERIES_CTA_LINE_MAX)
    return [
        {"kind": "vision", "variant": "hook", "kicker": eyebrow, "headline": hook},
        # stance: headline intentionally omitted so the template renders the
        # kicker + rule + substance column (Vision.tsx guards `spec.headline`).
        {"kind": "vision", "variant": "stance", "kicker": eyebrow, "body": body},
        {"kind": "vision", "variant": "cta", "headline": cta_line, "url": URL_HOME},
    ]


def _debut_vision_series_extra(post: dict[str, Any]) -> dict[str, Any]:
    """The pre-filled caption columns for a debut post. caption_instagram is
    inserted whole (fable's hashtags already live inline on its last line), so
    `hashtags` is left EMPTY to stop ig_export re-appending them. Pre-filling
    `caption` is what makes ig_caption.py skip the row (it selects caption IS
    NULL). Text is inserted verbatim, never scrubbed."""
    return {
        "caption": (post.get("caption_instagram") or "").strip(),
        "hashtags": [],
        "caption_x": (post.get("caption_x") or "").strip(),
        "caption_bluesky": (post.get("caption_bluesky") or "").strip(),
        "intent": (post.get("intent") or "").strip(),
    }


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


# Operator-note keyword matching. Common words that would match almost any
# headline are ignored so the steer only fires on a real topic word.
_NOTE_STOPWORDS = {
    "lead", "with", "story", "stories", "less", "more", "calm", "tone",
    "focus", "angle", "theme", "make", "keep", "than", "that", "this",
    "them", "then", "into", "from", "about", "over", "punchy", "factual",
    "emphasis", "register", "emotional", "please", "batch", "post",
}


def _operator_note() -> str:
    """Optional free-text steer for THIS batch (workflow `note` input, threaded
    as SOCIAL_NOTE). Best-effort soft signal only; empty/unset -> no effect."""
    return (os.environ.get("SOCIAL_NOTE") or "").strip()


def _note_keywords(note: str) -> list[str]:
    words = re.findall(r"[a-z0-9]{4,}", (note or "").lower())
    return [w for w in words if w not in _NOTE_STOPWORDS]


def _note_matches(title: str, kws: list[str]) -> bool:
    if not kws:
        return False
    t = (title or "").lower()
    return any(k in t for k in kws)


# ---------------------------------------------------------------------------
# EXAMPLE outlet recognizability. The Example spectrum must show KNOWN outlets
# at distinct scores, not obscure single-market feeds. Majorness ranks a source
# so ties collapse to the more recognizable outlet and the displayed set favors
# names a reader will recognize.
#   3 = globally recognized brand (name allowlist)
#   2 = us_major tier
#   1 = international tier
#   0 = independent / obscure
# "Recognizable" for the display floor = majorness >= _MAJOR_DISPLAY_MIN (2).
# ---------------------------------------------------------------------------
_MAJOR_OUTLET_NAMES = frozenset({
    "bbc", "reuters", "associated press", "ap news", "al jazeera", "guardian",
    "deutsche welle", "france 24", "france24", "nhk", "cnn", "fox news",
    "new york times", "washington post", "wall street journal", "npr",
    "bloomberg", "politico", "economist", "financial times", "sky news",
    "cnbc", "abc news", "cbs news", "nbc news", "msnbc", "usa today",
    "newsweek", "the hill", "axios", "afp", "agence france", "the times",
    "los angeles times", "the telegraph", "the independent", "vox",
    "the atlantic", "pbs", "breitbart", "national review", "the daily beast",
    "huffpost", "the intercept", "propublica", "the new yorker",
})

_MAJORNESS_BRAND = 3
_MAJORNESS_US_MAJOR = 2
_MAJORNESS_INTL = 1
_MAJORNESS_INDIE = 0
_MAJOR_DISPLAY_MIN = 2  # us_major tier or brand-listed counts as "recognizable"

# Example selection knobs.
_EXAMPLE_CRED_FLOOR = 5       # min cluster source_count for a "strict" pick
_EXAMPLE_MIN_MAJOR = 3        # min recognizable outlets in the displayed set
_EXAMPLE_DISPLAY_TARGET = 4   # outlets rendered on the spectrum slide (Example.tsx slices [0:4])

# COHERENCE gate knobs. The disagreement score ranks a cluster "contested"
# whenever its article leans span left..right, but an OVER-MERGED bag of
# unrelated stories ALSO spans (unrelated events carry unrelated leans), so a
# bag can top the ranking and defeat the whole Example concept (ONE event, many
# framings). Before contestedness is considered, a candidate must prove its
# DISPLAYED outlets cover the SAME event: a single core content-stem must recur
# across a strong majority of the displayed headlines, every displayed outlet
# must connect to that shared core, and the displayed headlines must overlap
# pairwise above a floor. Judged on the displayed HEADLINES (Porter stems), not
# the cluster's bridge title (which mirrors a bag's fragments and would
# manufacture a phantom core).
_COH_CORE_SHARE = 2          # a stem is part of the event "core" only if >= this many displayed headlines carry it
_COH_DOMINANCE_MIN = 0.60    # the single most-shared core stem must appear in >= this fraction of displayed headlines
_COH_PAIRWISE_MIN = 0.08     # mean pairwise stemmed-headline Jaccard floor across the displayed set

# Title tokenization for off-topic outlier detection (over-merged clusters).
_TITLE_STOPWORDS = frozenset({
    "the", "and", "for", "with", "from", "into", "over", "after", "before",
    "under", "about", "amid", "amidst", "says", "said", "will", "would",
    "could", "should", "has", "have", "had", "are", "was", "were", "been",
    "its", "his", "her", "their", "new", "how", "why", "what", "when",
    "where", "who", "this", "that", "these", "those", "than", "then",
    "live", "update", "updates", "report", "reports", "amp", "news",
})


def _outlet_majorness(name: str, tier: str | None) -> int:
    n = (name or "").lower()
    if any(b in n for b in _MAJOR_OUTLET_NAMES):
        return _MAJORNESS_BRAND
    if tier == "us_major":
        return _MAJORNESS_US_MAJOR
    if tier == "international":
        return _MAJORNESS_INTL
    return _MAJORNESS_INDIE


def _title_tokens(title: str) -> set[str]:
    return {
        w for w in re.findall(r"[a-z0-9]{4,}", (title or "").lower())
        if w not in _TITLE_STOPWORDS
    }


def _ontopic_outlets(
    cluster_title: str, outlets: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Drop obvious outliers from an over-merged cluster. Core topic tokens =
    the cluster title's content words plus any content word shared by >=2
    article titles; an article is on-topic if its title shares >=1 core token.
    Never strips below 3 outlets (a thin/odd core set must not gut a real
    cluster) and no-ops when there is nothing to compare against."""
    if len(outlets) < 4:
        return outlets
    from collections import Counter

    freq: Counter[str] = Counter()
    for o in outlets:
        freq.update(_title_tokens(o.get("headline") or ""))
    shared = {t for t, c in freq.items() if c >= 2}
    core = _title_tokens(cluster_title) | shared
    if not core:
        return outlets
    kept = [o for o in outlets if _title_tokens(o.get("headline") or "") & core]
    if len(kept) < 3:
        return outlets
    if len(kept) < len(outlets):
        print(
            f"  [example] dropped {len(outlets) - len(kept)} off-topic "
            f"outlier(s) from an over-merged cluster"
        )
    return kept


def _cluster_disagreement(
    lean_values: list[int], bias_diversity: Any
) -> float:
    """Score genuine left-right contestedness. Prefers the pipeline's stored
    polarization index (rev-49 bias aggregation) and takes the max of it and a
    locally recomputed polarization, then adds a spread term and a both-wings
    bonus. A one-sided cluster (all-left or all-center) scores near 0 no matter
    how many sources it has, so disagreement beats coverage volume."""
    if not lean_values:
        return 0.0
    lo, hi = min(lean_values), max(lean_values)
    spread = hi - lo
    n = len(lean_values)
    left = sum(1 for v in lean_values if v <= 42)
    right = sum(1 for v in lean_values if v >= 58)
    pol_local = 100.0 * (2.0 * min(left, right) / n) if n else 0.0
    pol_stored = 0.0
    if isinstance(bias_diversity, dict):
        try:
            pol_stored = float(bias_diversity.get("polarization") or 0)
        except (TypeError, ValueError):
            pol_stored = 0.0
    polarization = max(pol_local, pol_stored)
    both = 20.0 if (left > 0 and right > 0) else 0.0
    return polarization + 0.5 * spread + both


# ---------------------------------------------------------------------------
# Single-event coherence (the anti-"bag" gate).
# ---------------------------------------------------------------------------
_UNSET = object()
_STEMS_FN_CACHED: Any = _UNSET


def _stems_fn():
    """Lazy, cached handle to clustering's canonical title stemmer
    (_title_word_stems: Porter stem + shared stopwords). Reused so coherence
    judges headlines with the exact lens the upstream clusterer used. Returns
    None if clustering (spaCy/nltk) cannot be imported; callers fall back to the
    local 4+ char tokenizer."""
    global _STEMS_FN_CACHED
    if _STEMS_FN_CACHED is _UNSET:
        try:
            from clustering.story_cluster import _title_word_stems
            _STEMS_FN_CACHED = _title_word_stems
        except Exception:
            _STEMS_FN_CACHED = None
    return _STEMS_FN_CACHED


def _headline_stems(text: str) -> set[str]:
    """Content-word stems of a headline. Prefers clustering's Porter-stem
    pipeline; falls back to the local content tokens so coherence still computes
    when clustering can't load."""
    fn = _stems_fn()
    if fn is not None:
        try:
            return fn(text or "")
        except Exception:
            pass
    return _title_tokens(text or "")


def _cluster_coherence(
    display: list[dict[str, Any]]
) -> tuple[bool, float]:
    """Decide whether the DISPLAYED outlets cover ONE event, and score how
    tightly. Returns (coherent, coherence_score in 0..1).

    The event "core" = content stems carried by >= _COH_CORE_SHARE (2) of the
    displayed headlines. A cluster is COHERENT iff ALL of:
      (1) core is non-empty AND its single most-shared stem appears in
          >= _COH_DOMINANCE_MIN (60%) of the displayed headlines. A genuine
          single event has one dominant locus every outlet keeps naming; a bag
          (four unrelated events) has no stem shared by even two headlines, and
          a two-topic merge ({boatx2, ufcx2}) has a core but no stem spanning a
          majority, so both fail here.
      (2) every displayed outlet shares >= 1 stem with the core, so no displayed
          row is an off-event outlier.
      (3) mean pairwise stemmed-headline Jaccard >= _COH_PAIRWISE_MIN.

    Judged only on the displayed headlines (the cluster's bridge title is
    excluded on purpose: a bag's title mirrors its fragments and would fabricate
    a core). coherence_score = 0.6*core_dominance + 0.4*mean_pairwise, used to
    rank the coherent pool when the selector degrades.
    """
    n = len(display)
    if n < 2:
        return False, 0.0
    from collections import Counter

    stem_sets = [_headline_stems(o.get("headline") or "") for o in display]
    freq: Counter[str] = Counter()
    for s in stem_sets:
        freq.update(s)
    core = {t for t, c in freq.items() if c >= _COH_CORE_SHARE}
    if not core:
        return False, 0.0

    top_core_count = max(freq[t] for t in core)
    core_dominance = top_core_count / n
    all_connect = all((s & core) for s in stem_sets)

    pair_sum = 0.0
    pair_n = 0
    for i in range(n):
        for j in range(i + 1, n):
            a, b = stem_sets[i], stem_sets[j]
            uni = len(a | b)
            pair_sum += (len(a & b) / uni) if uni else 0.0
            pair_n += 1
    mean_pairwise = (pair_sum / pair_n) if pair_n else 0.0

    coherent = (
        core_dominance >= _COH_DOMINANCE_MIN
        and all_connect
        and mean_pairwise >= _COH_PAIRWISE_MIN
    )
    score = 0.6 * core_dominance + 0.4 * mean_pairwise
    return coherent, score


def _select_display_outlets(
    candidates: list[dict[str, Any]], target: int = _EXAMPLE_DISPLAY_TARGET
) -> list[dict[str, Any]]:
    """Choose the outlets to DISPLAY on the spectrum slide:
      (a) collapse ties to ONE outlet per distinct lean score, keeping the more
          recognizable outlet (no two rows ever share a score);
      (b) if still over budget, always keep the two lean extremes (max visible
          range + both wings) and fill the interior preferring major outlets.
    Returns outlets sorted left -> right."""
    best_by_score: dict[int, dict[str, Any]] = {}
    for o in candidates:
        s = o["lean_score"]
        cur = best_by_score.get(s)
        if cur is None or o["majorness"] > cur["majorness"]:
            best_by_score[s] = o
    pool = sorted(best_by_score.values(), key=lambda o: o["lean_score"])
    if len(pool) <= target:
        return pool

    left_end, right_end = pool[0], pool[-1]
    picked = [left_end, right_end]
    picked_ids = {id(left_end), id(right_end)}
    interior = [o for o in pool if id(o) not in picked_ids]
    interior.sort(key=lambda o: (-o["majorness"], o["lean_score"]))
    for o in interior:
        if len(picked) >= target:
            break
        picked.append(o)
    picked.sort(key=lambda o: o["lean_score"])
    return picked


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


def _gather_cluster_outlets(cid: str) -> list[dict[str, Any]]:
    """All articles in a cluster with a resolvable political lean, as outlet
    rows {outlet, lean_score, headline, majorness}. Lean prefers the per-article
    bias score, falling back to the source's 7-point baseline."""
    try:
        articles = (
            supabase.table("cluster_articles")
            .select(
                "article:articles(title, source:sources(name, tier, political_lean_baseline), bias_scores(political_lean))"
            )
            .eq("cluster_id", cid)
            .execute()
            .data
            or []
        )
    except Exception as e:
        print(f"  [warn] example: article query failed: {e}")
        return []

    out: list[dict[str, Any]] = []
    for row in articles:
        a = row.get("article") or {}
        if not a:
            continue
        bias = a.get("bias_scores")
        if isinstance(bias, list):
            bias = bias[0] if bias else None
        lean = (bias or {}).get("political_lean")
        src = a.get("source") or {}
        if lean is None:
            lean = _BASELINE_LEAN_SCORE.get(
                (src.get("political_lean_baseline") or "").strip().lower()
            )
        if lean is None:
            continue
        out.append(
            {
                "outlet": (src.get("name") or "Unknown")[:32],
                "lean_score": int(lean),
                "headline": (a.get("title") or "").strip()[:140],
                "majorness": _outlet_majorness(src.get("name") or "", src.get("tier")),
            }
        )
    return out


def _select_example_cluster() -> tuple[str, list[dict[str, Any]], int, list[int]] | None:
    """Pick the Example cluster by genuine LEFT-RIGHT DISAGREEMENT, not coverage
    volume. Among clusters from the last 48h, rank by a contestedness score
    (stored polarization + lean spread + both-wings bonus) above source_count,
    keeping a modest credibility floor and requiring a clean spread of
    recognizable, distinct-score outlets. Returns (title, headlines[displayed
    outlets], source_count, lean_values[on-topic article leans for the KDE ridge]).
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    try:
        clusters = (
            supabase.table("story_clusters")
            .select("id, title, source_count, bias_diversity")
            .gte("first_published", cutoff)
            .order("source_count", desc=True)
            .limit(30)
            .execute()
            .data
            or []
        )
    except Exception as e:
        print(f"  [warn] example: cluster query failed: {e}")
        return None

    # Operator note: a title match dominates the disagreement score (a huge
    # bonus) so the steer still wins, while the MOST contested matching cluster
    # is chosen among matches. No note / no match -> pure disagreement ranking.
    note = _operator_note()
    kws = _note_keywords(note) if note else []

    entries: list[dict[str, Any]] = []
    for cluster in clusters:
        sc = int(cluster.get("source_count") or 0)
        if sc < 3:
            continue
        cid = cluster["id"]
        raw = _gather_cluster_outlets(cid)
        if len(raw) < 3:
            continue
        ontopic = _ontopic_outlets(cluster.get("title") or "", raw)
        if len(ontopic) < 3:
            continue
        display = _select_display_outlets(ontopic)
        if len(display) < 3:
            continue
        bands = {_lean_band(o["lean_score"]) for o in display}
        if len(bands) < 2:
            continue

        has_left = any(o["lean_score"] <= 42 for o in display)
        has_right = any(o["lean_score"] >= 58 for o in display)
        spans = has_left and has_right
        major_ct = sum(1 for o in display if o["majorness"] >= _MAJOR_DISPLAY_MIN)
        lean_values = sorted(o["lean_score"] for o in ontopic)
        score = _cluster_disagreement(lean_values, cluster.get("bias_diversity"))
        matched = _note_matches(cluster.get("title") or "", kws)
        strict = sc >= _EXAMPLE_CRED_FLOOR and spans and major_ct >= _EXAMPLE_MIN_MAJOR
        # Single-event coherence GATE: does the DISPLAYED set actually cover one
        # event? A high-disagreement over-merged bag is rejected here.
        coherent, coherence_score = _cluster_coherence(display)

        entries.append(
            {
                "cluster": cluster,
                "display": display,
                "lean_values": lean_values,
                "score": score,
                "strict": strict,
                "spans": spans,
                "matched": matched,
                "coherent": coherent,
                "coherence_score": coherence_score,
                "source_count": sc,
            }
        )

    if not entries:
        print("  [warn] example: no eligible cluster found")
        return None

    # Operator note is authoritative: if it matched any candidate, restrict the
    # search to matched clusters (still picking the most contested / cleanest
    # among them). No note / no match -> the full eligible set.
    matched_entries = [e for e in entries if e["matched"]]
    search = matched_entries or entries

    # COHERENCE GATE (applied before contestedness). A candidate only qualifies
    # if its displayed outlets demonstrably cover the SAME event; an over-merged
    # bag is rejected here even when its unrelated leans score "contested". The
    # operator note cannot override this: a bag must never ship.
    coherent_search = [e for e in search if e["coherent"]]
    if not coherent_search:
        print(
            "  [example] no COHERENT cluster among candidates "
            f"({len(search)} eligible, all look over-merged); skipping Example"
        )
        return None

    # Among the COHERENT set: prefer a strict pick (credible + both wings +
    # recognizable spread); then a cluster that at least spans left and right.
    # If NO coherent cluster is contested, DEGRADE to the best coherent cluster
    # (still the most contested / most coherent among them) and log it. Within
    # the chosen tier, disagreement wins, source_count breaks ties.
    strict_pool = [e for e in coherent_search if e["strict"]]
    spanning_pool = [e for e in coherent_search if e["spans"]]
    degraded = not (strict_pool or spanning_pool)
    if degraded:
        # No contested coherent cluster; pick the best coherent one. Keep the
        # disagreement ranking primary, breaking ties toward the tightest event.
        best = max(
            coherent_search,
            key=lambda e: (e["score"], e["coherence_score"], e["source_count"]),
        )
        tier = "coherent-degraded"
    else:
        pool = strict_pool or spanning_pool
        best = max(pool, key=lambda e: (e["score"], e["source_count"]))
        tier = "strict" if best in strict_pool else "spanning"

    if matched_entries:
        print(f"  [example] operator note steered selection (keywords: {', '.join(kws[:6])})")
    if degraded:
        print(
            "  [example] DEGRADED: no coherent+contested cluster; falling back to "
            f"best coherent (coherence={best['coherence_score']:.2f})"
        )
    print(
        f"  [example] selected by disagreement (tier={tier}, score={best['score']:.1f}, "
        f"sources={best['source_count']}, outlets={len(best['display'])}, "
        f"coherence={best['coherence_score']:.2f})"
    )

    cluster = best["cluster"]
    title = (cluster.get("title") or "Today's top story").strip()[:100]
    source_count = int(cluster.get("source_count") or len(best["display"]))
    headlines = [
        {"outlet": o["outlet"], "lean_score": o["lean_score"], "headline": o["headline"]}
        for o in best["display"]
    ]
    return title, headlines, source_count, best["lean_values"]


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
        for p in perspectives_raw[:3]:
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
    extra: dict[str, Any] | None = None,
) -> str | None:
    """Insert one draft row. `extra` merges pre-filled columns (e.g. a verbatim
    caption + per-platform variants + intent) onto the row AFTER slide_specs are
    scrubbed; extra values are inserted verbatim (never scrubbed) so pre-filled
    editorial copy is preserved byte-for-byte. A pre-filled `caption` also makes
    the caption pass skip the row (ig_caption selects caption IS NULL)."""
    if not specs:
        print(f"  [generator] {pillar}: no specs produced, skipping")
        return None
    specs = _scrub(specs)
    if dry_run:
        print(f"\n  [dry-run] {pillar} ({len(specs)} slides) @ {scheduled.isoformat()}")
        print(json.dumps(specs, indent=2, ensure_ascii=False))
        if extra:
            cap = extra.get("caption") or ""
            print(
                f"  [dry-run] {pillar} pre-filled columns: {sorted(extra.keys())} "
                f"(caption {len(cap)}c, x {len(extra.get('caption_x') or '')}c, "
                f"bsky {len(extra.get('caption_bluesky') or '')}c) "
                f"-> caption pass will SKIP this row"
            )
        return None
    row: dict[str, Any] = {
        "state": "draft",
        "scheduled_for": scheduled.isoformat(),
        "pillar": pillar,
        "surface": "feed",
        "slide_specs": specs,
    }
    if extra:
        row.update(extra)
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


VISION_SERIES_STAGGER_MINUTES = 30  # distinct scheduled_for per post so the
#                                     export bundle orders them 1..6.


def run_vision_series(when: datetime | None, dry_run: bool) -> int:
    """Render fable's six debut Vision posts in ONE run. Each is a full vision
    carousel with caption + variants + intent pre-filled verbatim, so the Gemini
    caption pass is skipped and capture + export bundle all six for manual
    upload."""
    try:
        posts = _load_debut_vision_series()
    except Exception as e:
        print(f"  [vision-series] could not load {_SERIES_JSON}: {e}")
        return 0
    if not posts:
        print("  [vision-series] no posts in series data")
        return 0

    base = when or _next_post_datetime()
    made = 0
    for i, post in enumerate(posts):
        scheduled = base + timedelta(minutes=i * VISION_SERIES_STAGGER_MINUTES)
        specs = _debut_vision_series_specs(post)
        extra = _debut_vision_series_extra(post)
        slug = post.get("slug") or f"post-{i + 1}"
        print(f"  [vision-series] {i + 1}/{len(posts)} {slug}")
        if _emit("vision", specs, scheduled, dry_run, extra=extra):
            made += 1
    if not dry_run:
        print(
            f"  [vision-series] {made}/{len(posts)} debut Vision draft(s) inserted "
            f"(captions pre-filled; caption pass will skip them)"
        )
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
        choices=["void", "vision-series", "history", "weekly"],
        help="void (daily trio, default) | vision-series (fable's six debut "
        "Vision posts, captions pre-filled) | history | weekly",
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
    elif args.track == "vision-series":
        run_vision_series(when, args.dry_run)
    else:
        run_void(when, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
