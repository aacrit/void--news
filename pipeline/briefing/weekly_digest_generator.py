"""
Weekly Digest generator for void --weekly.

A full magazine-format weekly, independent of daily briefs:

  SECTIONS:
  1. THE COVER (2 deep-dive stories with daily timeline showing how each
     story evolved through the week — Monday through Sunday)
  2. THE OPINIONS (5-6 topics × 1 lean voice each, rotating through the
     void voice crew: left/center-left/center/center-right/right)
  3. THE TECH BRIEF (one technology/AI/digital story of the week)
  4. THE SPORTS PAGE (one sports-as-culture story of the week)
  5. THE BIAS REPORT (rule-based: most polarized, most sensationalized,
     coverage blind spots, lean trends)
  6. THE WEEK IN BRIEF (8-10 additional stories, 200 words each)
  7. AUDIO: void --onair WEEKLY (15-20 min magazine-pace broadcast)

Data: story_clusters + daily_briefs (TL;DR signals) + cluster_archive.
Story selection uses cross-cluster TF-IDF linking + daily brief signal aggregation.
Budget: ~25-30 Gemini calls per edition, well within 1500 RPD.
Schedule: Sunday 6 AM CST (12:00 UTC).
"""

import os
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from utils.supabase_client import supabase
from briefing.weekly_parse import (  # pure: no DB, no LLM, no network
    build_weekly_row, clean_headline, parse_essay, parse_recap,
    looks_like_headline, weekly_window,
    banned_terms, drop_terms, enforce, enforce_recap, retry_suffix, strip_dashes,
    word_count, ground_text, ground_quotes, cut_slop_sentences, sized_spec,
    length_after_cut, row_corpus, source_words,
)
from utils.prohibited_terms import strip_significance
from summarizer.gemini_client import (
    generate_json as gemini_generate_json,
    generate_text as gemini_generate_text,
    is_available as gemini_is_available,
    _FLASH_MODEL,
)

try:
    from summarizer.claude_client import (
        generate_json as claude_generate_json,
        is_available as claude_is_available,
    )
except ImportError:
    def claude_generate_json(*a, **kw): return None
    def claude_is_available(): return False

# Groq retired 2026-06-24; Gemini Flash is the sole digest LLM.

from briefing.voice_rotation import get_voices_for_today, get_opinion_host

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.cluster import AgglomerativeClustering
    import numpy as np
    _SKLEARN_AVAILABLE = True
except ImportError:
    _SKLEARN_AVAILABLE = False
from briefing.audio_producer import produce_audio
from media.image_search import find_cover_image_for_cluster

# ---------------------------------------------------------------------------
# Single-feed mode (rev 46 collapse-editions): the regional editions were
# deleted; only "world" has clusters, so iterating the old list burned three
# fetch-0-and-skip passes per weekly run.
EDITIONS = ["world"]
WEEK_RECAP_COUNT = 10
BRIEF_THUMB_COUNT = 3   # Commons lookups for Week in Brief thumbnails
OPINION_COUNT = 6
COVER_STORIES = 2
COVER_MIN_WORDS = 800

# Opinion voice rotation — one lean per topic, cycling through perspectives
OPINION_LEANS = ["left", "center-right", "center-left", "right", "center", "left"]

OPINION_VOICE_CONFIGS = {
    "left": {
        "perspective": "progressive",
        "instruction": "Write from the perspective of affected communities and systemic causes. Lead with human impact. Channel the voice of a writer who sees policy through the lens of who gets hurt first.",
        "tradition": "progressive",
    },
    "center-left": {
        "perspective": "liberal reformist",
        "instruction": "Write from the perspective of institutional reform and evidence-based policy. Lead with what research shows. Channel a pragmatic liberal who believes in government but demands it work better.",
        "tradition": "liberal",
    },
    "center": {
        "perspective": "pragmatic centrist",
        "instruction": "Write from the perspective of tradeoffs and institutional stability. Lead with competing legitimate interests. Channel a voice that sees both sides and argues for the least-bad option.",
        "tradition": "pragmatic",
    },
    "center-right": {
        "perspective": "market-oriented conservative",
        "instruction": "Write from the perspective of economic incentives and unintended consequences. Lead with costs and market signals. Channel a voice that respects free enterprise and limited government.",
        "tradition": "fiscal conservative",
    },
    "right": {
        "perspective": "traditional conservative",
        "instruction": "Write from the perspective of precedent, sovereignty, and cultural continuity. Lead with what has worked before. Channel a voice that values order, tradition, and national interest.",
        "tradition": "conservative",
    },
}

# PROHIBITED_TERMS moved to weekly_parse, alongside the check that enforces it.
# It was defined here, checked at exactly ONE of six generation sites, and the
# other five prompts told the model its output would be "REJECTED" by nothing.

#: Every essay section's word brief, in one place, so the prompt and the check
#: cannot drift. `COVER_MIN_WORDS = 800` already existed and was read by nothing.
ESSAY_SPECS = {
    "cover":     {"min_words": COVER_MIN_WORDS, "max_words": 1200},
    "opinion":   {"min_words": 400, "max_words": 600},
    "tech":      {"min_words": 500, "max_words": 700},
    "sports":    {"min_words": 400, "max_words": 600},
    "editorial": {"min_words": 450, "max_words": 650},
    "brief":     {"min_words": 55,  "max_words": 75},
}

# Decision 5 (CEO, 2026-10-02): the Technology and Sports & Culture departments
# are SUSPENDED until each has a sourced corpus. Neither was ever written from
# the week as printed: both read the raw cluster pool, both were handed a title
# and a summary and asked for 500 words, and Issue #26's Sports & Culture page
# was a German election essay with no sport in it and no source for its lede.
# The selection code stays, with its category match fixed (below), so the
# departments can return behind this switch once a sourced corpus exists.
WEEKLY_DEPARTMENTS = os.environ.get("VOID_WEEKLY_DEPARTMENTS", "0") == "1"

# The categorizer's taxonomy is LOWERCASE (`auto_categorize.py`: general,
# politics, conflict, economy, environment, health, science, culture). These
# sets were written in title case ("Technology", "Sports", "Culture"), so the
# label match missed on every cluster ever stored and both departments fell
# through to substring keywords. Compared lowercased now.
TECH_CATEGORIES = frozenset({"technology", "tech", "science", "ai", "cybersecurity", "space"})
SPORTS_CATEGORIES = frozenset({"sports", "sport", "culture"})


def _category(c):
    return str(c.get("category") or "").strip().lower()

# Flash has a shared 20-requests-a-DAY free cap and the daily pipeline already
# spends ~13 of it. A regeneration is one more request, so the flash sections
# draw from a budget while flash-lite (high RPD) retries freely. Without this a
# bad Sunday could spend four extra flash calls and silently fail the daily
# brief the next morning.
_FLASH_RETRY_BUDGET = [2]


def _may_retry(model):
    if model != _FLASH_MODEL:
        return True
    if _FLASH_RETRY_BUDGET[0] <= 0:
        return False
    _FLASH_RETRY_BUDGET[0] -= 1
    return True

# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------
def _smart_generate(prompt, system_instruction=None, max_output_tokens=8192, model=None):
    """Gemini ($0) is the sole digest LLM. Claude (2026-06-22) and Groq
    (2026-06-24) are retired; on failure the caller degrades to rule-based.
    `model` selects the Gemini tier: pass `_FLASH_MODEL` for the flagship
    sections (cover essays + week recap); leave None for the flash-lite default
    (opinions / tech / sports / audio). Flagship-only flash keeps the Sunday run
    within flash's shared 20-RPD free cap (the daily pipeline already spends ~13).
    Returns (result_dict, gen_label)."""
    if claude_is_available():
        result = claude_generate_json(
            prompt, system_instruction=system_instruction,
            count_call=False, max_output_tokens=max_output_tokens,
        )
        if result:
            return result, "claude-sonnet"

    if gemini_is_available():
        result = gemini_generate_json(
            prompt, system_instruction=system_instruction,
            count_call=False, max_output_tokens=max_output_tokens, model=model,
        )
        if result:
            return result, ("gemini-flash" if model == _FLASH_MODEL else "gemini-flash-lite")

    return None, "none"


def _smart_generate_text(prompt, system_instruction=None, max_output_tokens=8192, model=None):
    """Plain-text Gemini generation (no JSON) for the single long weekly audio
    script — JSON-escaping a ~3000-word script with embedded opinion quotes is
    fragile (one stray quote drops the whole result). Returns the script string,
    or None on failure (caller degrades to no audio)."""
    if gemini_is_available():
        return gemini_generate_text(
            prompt, system_instruction=system_instruction,
            count_call=False, max_output_tokens=max_output_tokens, model=model,
        )
    return None


# ---------------------------------------------------------------------------
# Plain-text essay generation + parsing
#
# The cover/opinion/tech/sports/recap essays were generated as JSON, but Gemini
# intermittently emits long prose with an unescaped quote or stray newline that
# breaks json.loads (e.g. "Unterminated string", "Expecting ',' delimiter"),
# dropping the whole section to a stub. These helpers generate PLAIN TEXT in a
# tolerant, self-describing layout and parse out the same keys the callers
# consume — the pattern already used for the audio script and editor's note.
# No JSON, so prose with any punctuation is safe; no extra LLM calls.
# ---------------------------------------------------------------------------

# _clean_headline / _parse_essay / _parse_recap now live in weekly_parse, which
# imports re + datetime and nothing else, so tests can reach them without the
# supabase_client import wall. The names are aliased so callers are unchanged.
_clean_headline = clean_headline
_parse_essay = parse_essay


def _gen_essay(prompt, system, model=None, max_output_tokens=4096,
               want_numbers=False, spec=None, label="essay"):
    """Generate a {headline, text[, numbers]} essay, measured against its spec.

    Returns (result_or_None, calls_made). The spec is checked, ONE regeneration
    is attempted naming the findings, and whichever attempt is cleaner ships
    when the remaining findings are about LENGTH: a missing department reads
    worse than a long one. A kill-list verb, noun or scaffolding opener that
    survives the regeneration cuts its SENTENCE (`cut_slop_sentences`): the
    word cannot be deleted from its sentence by code, but the sentence can be
    deleted whole, and dropping the piece over one word cost 3 of 5 columns on
    2026-09-27. The prose is dash-stripped and significance-stripped either
    way. Length is checked again by the caller AFTER grounding and the source
    check (`length_after_cut`), because those cuts are what decide it.
    """
    spec = spec or {}
    best, best_findings, calls = None, None, 0
    # The words that DROP a piece, told to the writer before it writes, not
    # after (every prompt above names only its own short list).
    system = (system or "") + _SLOP_PROMPT_LINE

    for attempt in range(2):
        raw = _smart_generate_text(
            prompt if attempt == 0 else prompt + retry_suffix(best_findings),
            system_instruction=system,
            max_output_tokens=max_output_tokens, model=model,
        )
        calls += 1
        result = _parse_essay(raw, want_numbers=want_numbers)
        if not (result and isinstance(result, dict) and result.get("text")):
            if attempt == 1 or not _may_retry(model):
                break
            best_findings = ["it returned nothing usable"]
            continue

        result["text"] = strip_significance(strip_dashes(result["text"]))
        if result.get("headline"):
            result["headline"] = strip_significance(strip_dashes(result["headline"]))
        findings = enforce(result["text"], **spec)

        if not findings:
            if attempt:
                print(f"    [{label}] clean on regeneration")
            return result, calls
        if best is None or len(findings) < len(best_findings):
            best, best_findings = result, findings
        if attempt == 1:
            break
        if not _may_retry(model):
            print(f"    [{label}] {best_findings[0]} — no flash budget to regenerate")
            break
        print(f"    [{label}] rejected: {'; '.join(findings)} — regenerating")

    if best is not None:
        # The kill list cuts the SENTENCE that carries it, not the piece
        # (P1-18). A headline that carries one is discarded and the caller
        # names the piece from its story, as it does for an empty headline.
        if drop_terms(best.get("headline")):
            print(f"    [{label}] headline cut for {drop_terms(best.get('headline'))}")
            best["headline"] = ""
        kept, cut = cut_slop_sentences(best["text"])
        for sent, terms in cut:
            print(f"    [{label}] cut for {', '.join(repr(t) for t in terms)}: {sent[:100]}")
        if not (kept or "").strip():
            print(f"    [{label}] DROPPED: nothing left once the kill-list sentences were cut")
            return None, calls
        best["text"] = kept
        if best_findings:
            print(f"    [{label}] shipped with {len(best_findings)} finding(s): {'; '.join(best_findings)}")
    return best, calls


# Defined here, inside the slice tests/test_weekly.py execs, so the function
# and the list it appends travel together.
from utils.prohibited_terms import SLOP_PROMPT_WORDS  # noqa: E402
_SLOP_PROMPT_LINE = (
    "\n\nNEVER USE these words or phrases in any form; a piece that carries one is "
    "dropped from the issue: " + ", ".join(f'"{w}"' for w in SLOP_PROMPT_WORDS) + "."
)


_parse_recap = parse_recap


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
# The colophon prints `total_clusters` as a COUNT ("in 500 story clusters") and
# The Week in Bias prints it again ("across 500 stories this week"), so it has
# to be one. A single .limit(500) returned exactly 500 on BOTH archived issues
# (#23: 500/2109, #26: 500/2355) — a query cap published as a measurement, two
# for two. `total_articles` is summed over those same capped rows, so that
# number was a floor too. Paged now, with a ceiling that is FLAGGED rather than
# silently applied, which is the shape `_fetch_bias_stats` was given in rev 71
# and this query was missed.
_CLUSTER_PAGE = 500
_CLUSTER_MAX = 20000


def _fetch_week_clusters(edition, week_start, week_end):
    """Fetch clusters for the edition within date range, sorted by importance.

    Returns `(clusters, truncated)`. `truncated` is True only when the read
    stopped short of the week, so the page can say "more than" instead of
    printing a ceiling as a count.
    """
    clusters = []
    try:
        while True:
            page = supabase.table("story_clusters").select(
                "id,title,summary,consensus_points,divergence_points,"
                "category,source_count,headline_rank,divergence_score,bias_diversity,"
                "sections,created_at,first_published,last_updated,"
                "cached_image_url,cached_image_attribution"
            ).contains("sections", [edition]).gte(
                "created_at", week_start.isoformat()
            ).lte(
                "created_at", week_end.isoformat()
            ).order("headline_rank", desc=True).range(
                len(clusters), len(clusters) + _CLUSTER_PAGE - 1
            ).execute()
            rows = page.data or []
            clusters.extend(rows)
            if len(rows) < _CLUSTER_PAGE:
                return clusters, False
            if len(clusters) >= _CLUSTER_MAX:
                return clusters, True
    except Exception as e:
        print(f"  [weekly:{edition}] cluster query failed: {e}")
        # A read that died part-way is a floor, not a count. Only an empty
        # result is honestly empty.
        return clusters, bool(clusters)


def _fetch_week_printed(week_start, week_end):
    """The week as Void printed it: every day's front page, from the record.

    `story_clusters` is pruned to two days by step 8c.1, so a Sunday read of
    it held Friday and Saturday plus whatever junk survived the purge. The
    09-27 issue led its second cover with a Spanish local crime cluster of
    127 "sources" that never reached the front page, and its recap could only
    ever span one or two dates. `printed_stories` is the permanent top-20 of
    each day, every row through Stage 2 with its summary, and it keeps ten
    days, so a Sunday (or a backfill a few days late) sees the whole week.

    Rows are returned in the cluster shape the rest of this module reads, with
    `id` the source cluster id (what daily briefs list in top_cluster_ids)
    and `printed_on` the day it ran.
    """
    lo = week_start.strftime("%Y-%m-%d") if hasattr(week_start, "strftime") else str(week_start)[:10]
    hi = week_end.strftime("%Y-%m-%d") if hasattr(week_end, "strftime") else str(week_end)[:10]
    try:
        rows = (
            supabase.table("printed_stories")
            .select("*")
            .gte("printed_on", lo)
            .lte("printed_on", hi)
            .order("printed_on")
            .execute()
        ).data or []
    except Exception as e:
        print(f"  [weekly] printed_stories read failed: {e}")
        return []
    out = []
    for r in rows:
        summary = r.get("summary")
        if not isinstance(summary, str) or not summary.strip():
            continue  # nothing to ground a sentence on
        out.append({
            "id": r.get("source_cluster_id") or r.get("id"),
            "title": r.get("title") or "",
            "summary": summary,
            "consensus_points": r.get("consensus_points") or [],
            "divergence_points": r.get("divergence_points") or [],
            "category": r.get("category"),
            "source_count": r.get("source_count") or 0,
            # rank_world is the score the front page was ordered by
            "headline_rank": r.get("rank_world") or r.get("headline_rank") or 0,
            "divergence_score": r.get("divergence_score") or 0,
            "bias_diversity": r.get("bias_diversity") or {},
            "sections": ["world"],
            "created_at": r.get("created_at"),
            "first_published": r.get("first_published"),
            "last_updated": r.get("printed_on"),
            "printed_on": r.get("printed_on"),
            "story_thread_id": r.get("story_thread_id"),
            "edition_position": r.get("edition_position"),
        })
    return out


def _one_per_thread(rows):
    """The printed rows with one row per story thread: its best-covered day."""
    best = {}
    for r in rows:
        key = r.get("story_thread_id") or r.get("id")
        if key not in best or (r.get("source_count") or 0) > (best[key].get("source_count") or 0):
            best[key] = r
    return sorted(best.values(), key=lambda r: r.get("headline_rank") or 0, reverse=True)


# The Week in Bias prints `total_scored` as a COUNT, so it has to be one. A
# single .limit(3000) returned exactly 3000 on Issue #26 — a truncated query
# cap being published as a measurement, in the one section whose whole job is
# to be honest about measurement. Paged, with a ceiling that is flagged rather
# than silently applied.
_BIAS_PAGE = 1000
_BIAS_MAX = 60000


def _fetch_bias_stats(edition, week_start, week_end):
    """Aggregate bias stats for the week."""
    try:
        scores = []
        truncated = False
        while True:
            page = supabase.table("bias_scores").select(
                "political_lean,sensationalism,opinion_fact,factual_rigor,framing,confidence"
            ).gte("analyzed_at", week_start.isoformat()).lte(
                "analyzed_at", week_end.isoformat()
            ).range(len(scores), len(scores) + _BIAS_PAGE - 1).execute()
            rows = page.data or []
            scores.extend(rows)
            if len(rows) < _BIAS_PAGE:
                break
            if len(scores) >= _BIAS_MAX:
                truncated = True
                break

        if not scores:
            return None
        leans = [s["political_lean"] for s in scores if s.get("political_lean") is not None]
        sensations = [s["sensationalism"] for s in scores if s.get("sensationalism") is not None]
        rigors = [s["factual_rigor"] for s in scores if s.get("factual_rigor") is not None]

        return {
            "total_scored": len(scores),
            # True only when the ceiling was hit, so the page can say "at least"
            # instead of stating a cap as a count.
            "truncated": truncated,
            "avg_lean": round(sum(leans) / max(len(leans), 1), 1),
            "avg_sensationalism": round(sum(sensations) / max(len(sensations), 1), 1),
            "avg_rigor": round(sum(rigors) / max(len(rigors), 1), 1),
            "lean_std": round(
                (sum((x - sum(leans) / len(leans)) ** 2 for x in leans) / max(len(leans), 1)) ** 0.5, 1
            ) if len(leans) > 1 else 0,
        }
    except Exception as e:
        print(f"  [weekly:{edition}] bias stats failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Section generators
# ---------------------------------------------------------------------------

# ── SECTION 1: THE COVER (2 deep-dive stories with daily timeline) ──

COVER_SYSTEM = """You are the lead writer for Void Weekly, a magazine-style news digest.
Write in the register of The Economist or The Atlantic: measured, analytical,
mechanism-focused. Juxtapose concrete facts. Never assert significance.

SHOW, DON'T TELL (CARDINAL RULE):
Never tell the reader that something matters. Show it with a specific number,
name, date, or action and let the reader conclude. Use active voice and concrete
subjects. Cut abstraction: "a substantial influx of tens of thousands of
individuals" becomes "tens of thousands crossed"; "was approaching a state of
near-complete return to its prior configuration" becomes "had nearly all gone
home". Prefer the plain word to the bureaucratic one.

ARRIVE LATE, LEAVE EARLY:
Open on a concrete image or a hard fact, already mid-action. No throat-clearing,
no scene-setting preamble, no "The story began when...". The first sentence must
land a specific fact, not announce that a situation existed. Cut when the point
lands.

You will receive a DATA TIMELINE showing real cluster creation dates and titles.
Use it as the chronological skeleton and weave those dates and developments into
FLOWING PROSE. Do NOT invent events not shown.
Every fact MUST appear in the provided articles. Do not supplement with prior knowledge.
Never reference outlet names, "coverage," "sources," or "reporting patterns."
Synthesize the facts; do not narrate where they came from.

BANNED (output containing these is REJECTED): "notable", "significant", "it
should be noted", "interestingly", "crucially", "here's what you need to know",
"in conclusion", "a testament to", "should chill".

OUTPUT FORMAT — plain text only, no JSON, no Markdown:
- Line 1: the headline only (no label, no quotes, no Markdown).
- Then a blank line.
- Then the essay, at the length the prompt gives, in flowing prose paragraphs separated by blank
  lines. No bulleted or numbered lists, no "TIMELINE" section, no headings,
  no asterisks or bold/italic markers.
- Then a line containing only NUMBERS, then 3 to 5 lines of "value | context",
  each a figure that already appears in the essay above. The value is the
  figure alone ("15 million", "$4.2 billion", "446 of 495"); the context is a
  short phrase naming what it counts. No sentences, no other text."""


# ---------------------------------------------------------------------------
# STORY THREADING ENGINE — links related clusters across the week
# ---------------------------------------------------------------------------
STOP_WORDS = {"the","a","an","in","on","at","to","for","of","and","as","is",
              "by","with","that","this","from","has","was","are","were","been",
              "its","it","be","not","but","or","no","new","says","said","after"}


def _link_story_threads(clusters):
    """Link related clusters into story threads using TF-IDF similarity.

    Returns list of thread dicts sorted by size (largest first):
    {
        "clusters": [...],        # chronologically ordered
        "lead_cluster": {...},    # highest headline_rank in thread
        "title": str,
        "daily_appearances": int, # unique days
        "edition_spread": set,
        "cumulative_sources": int,
        "peak_rank": float,
        "total_divergence": float,
    }
    """
    if not clusters or len(clusters) < 2:
        return [{"clusters": clusters, "lead_cluster": clusters[0] if clusters else {},
                 "title": clusters[0].get("title", "") if clusters else "",
                 "daily_appearances": 1, "edition_spread": set(), "cumulative_sources": 0,
                 "peak_rank": 0, "total_divergence": 0}] if clusters else []

    if _SKLEARN_AVAILABLE and len(clusters) >= 3:
        return _link_threads_tfidf(clusters)
    return _link_threads_keyword(clusters)


def _link_threads_tfidf(clusters):
    """TF-IDF based thread linking (preferred, needs sklearn)."""
    docs = [f"{c.get('title', '')} {(c.get('summary') or '')[:200]}" for c in clusters]
    try:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=5000, ngram_range=(1, 2))
        tfidf = vectorizer.fit_transform(docs)
        sim = cosine_similarity(tfidf)
        dist = 1 - sim
        dist[dist < 0] = 0

        model = AgglomerativeClustering(
            n_clusters=None, distance_threshold=0.70,
            metric="precomputed", linkage="average",
        )
        labels = model.fit_predict(dist)
    except Exception:
        return _link_threads_keyword(clusters)

    groups = {}
    for i, label in enumerate(labels):
        groups.setdefault(label, []).append(clusters[i])

    # Deliberately NOT joined on printed_stories.story_thread_id: on the week
    # of 2026-09-21 the daily threader filed "Trump Hails 'Great Friendship'
    # With Xi Jinping" under the White House media-ban story, and the cover
    # writer is handed every member as a dated timeline. A thread split in two
    # understates a story; a thread joined wrongly states a false connection.
    return _build_threads(groups)


def _link_threads_keyword(clusters):
    """Fallback keyword-overlap linking."""
    assigned = set()
    groups = {}
    gid = 0
    for i, c in enumerate(clusters):
        if i in assigned:
            continue
        groups[gid] = [c]
        assigned.add(i)
        c_words = set(c.get("title", "").lower().split()) - STOP_WORDS
        for j, other in enumerate(clusters):
            if j in assigned:
                continue
            o_words = set(other.get("title", "").lower().split()) - STOP_WORDS
            if len(c_words & o_words) >= 3:
                groups[gid].append(other)
                assigned.add(j)
        gid += 1
    return _build_threads(groups)


def _build_threads(groups):
    """Convert cluster groups into scored thread dicts."""
    threads = []
    for _, thread_clusters in groups.items():
        thread_clusters.sort(key=lambda c: c.get("first_published") or c.get("created_at") or "")
        lead = max(thread_clusters, key=lambda c: c.get("headline_rank", 0))
        days = set()
        editions = set()
        for c in thread_clusters:
            # A printed row counts the day it RAN; first_published is when
            # the earliest article appeared, which a three-day story shares.
            fp = c.get("printed_on") or c.get("first_published") or c.get("created_at")
            if fp:
                days.add(fp[:10])
            for s in (c.get("sections") or []):
                editions.add(s)
        threads.append({
            "clusters": thread_clusters,
            "lead_cluster": lead,
            "title": lead.get("title", ""),
            "daily_appearances": len(days),
            "edition_spread": editions,
            "cumulative_sources": sum(c.get("source_count", 0) for c in thread_clusters),
            "peak_rank": max(c.get("headline_rank", 0) for c in thread_clusters),
            "total_divergence": sum(c.get("divergence_score", 0) for c in thread_clusters),
            "brief_mentions": 0,
        })
    threads.sort(key=lambda t: t["cumulative_sources"], reverse=True)
    return threads


def _score_weekly_threads(threads, brief_signals, edition):
    """Score threads by weekly dominance using 6-signal formula."""
    # Match brief signals to threads
    for thread in threads:
        title_words = set(thread["title"].lower().split()) - STOP_WORDS
        mentions = 0
        thread_ids = {c.get("id") for c in thread["clusters"]}
        for brief in brief_signals:
            brief_ids = set(brief.get("top_cluster_ids") or [])
            if thread_ids & brief_ids:
                mentions += 1
                continue
            headline = (brief.get("tldr_headline") or "").lower()
            h_words = set(headline.split()) - STOP_WORDS
            if len(title_words & h_words) >= 2:
                mentions += 1
        thread["brief_mentions"] = mentions

    if not threads:
        return []

    mx = lambda key: max((t[key] for t in threads), default=1) or 1
    mx_ed = max((len(t["edition_spread"]) for t in threads), default=1) or 1

    for t in threads:
        t["weekly_score"] = (
            (t["daily_appearances"] / mx("daily_appearances")) * 0.25 +
            (t["cumulative_sources"] / mx("cumulative_sources")) * 0.20 +
            (t["brief_mentions"] / mx("brief_mentions")) * 0.20 +
            (t["peak_rank"] / mx("peak_rank")) * 0.15 +
            (len(t["edition_spread"]) / mx_ed) * 0.10 +
            (t["total_divergence"] / mx("total_divergence")) * 0.10
        )

    threads.sort(key=lambda t: t["weekly_score"], reverse=True)

    # Dedup: top 2 must be different stories
    selected = []
    word_sets = []
    for t in threads:
        words = set(t["title"].lower().split()[:6])
        if any(len(words & e) > 2 for e in word_sets):
            continue
        selected.append(t)
        word_sets.append(words)
        if len(selected) >= COVER_STORIES:
            break
    return selected


def _build_data_timeline(thread):
    """Build timeline from actual cluster timestamps. No Gemini. Pure data."""
    entries = []
    for c in thread["clusters"]:
        fp = c.get("first_published") or c.get("created_at")
        if not fp:
            continue
        try:
            dt = datetime.fromisoformat(fp.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        entries.append({
            "date": dt.strftime("%a %b %d"),
            "date_iso": fp[:10],
            "title": c.get("title", "Untitled"),
            "source_count": c.get("source_count", 0),
            "cluster_id": c.get("id"),
        })

    entries.sort(key=lambda e: (e["date_iso"], -e["source_count"]))

    # Max 2 entries per day
    final = []
    day_counts = {}
    for e in entries:
        d = e["date_iso"]
        day_counts[d] = day_counts.get(d, 0) + 1
        if day_counts[d] <= 2:
            final.append(e)
    return final


def _fetch_brief_signals(edition, week_start, week_end):
    """Fetch daily TL;DR briefs for the week as story selection signal."""
    try:
        result = supabase.table("daily_briefs").select(
            "tldr_headline,created_at,top_cluster_ids"
        ).eq("edition", edition).gte(
            "created_at", week_start.isoformat()
        ).lte(
            "created_at", week_end.isoformat()
        ).order("created_at", desc=True).execute()
        return result.data or []
    except Exception as e:
        print(f"  [weekly:{edition}] brief signal query failed: {e}")
        return []


def _fetch_daily_opinions(edition, week_start, week_end):
    """Fetch the week's daily brief rows, oldest first.

    TWO consumers, one query. The weekly editorial reads the days that ARGUED
    something (it must not restate any of them; it argues the week-length
    through-line no single day could see), and `_week_days` reads every day
    that ran a brief at all, for the day-by-day rail. Filtering here would have
    cost a second query to get the days back.
    """
    try:
        result = supabase.table("daily_briefs").select(
            "tldr_headline,opinion_headline,opinion_text,opinion_lean,created_at"
        ).eq("edition", edition).gte(
            "created_at", week_start.isoformat()
        ).lte(
            "created_at", week_end.isoformat()
        ).order("created_at", desc=False).execute()
        return list(result.data or [])
    except Exception as e:
        print(f"  [weekly:{edition}] daily opinion query failed: {e}")
        return []


def _week_days(daily_rows, week_start, week_end):
    """The week, day by day, from rows already in hand.

    These `daily_briefs` rows are fetched as prompt context for the weekly
    editorial and then discarded. Keeping one line per day costs nothing and
    gives the issue the one piece of furniture only a weekly can print: the
    SHAPE of the week, seven headlines in order, rather than seven separate
    front pages the reader has to remember.

    One row per calendar day, the first brief of that day, so a day with a
    morning and an evening edition does not take two slots.
    """
    seen, out = set(), []
    for r in daily_rows or []:
        day = (r.get("created_at") or "")[:10]
        headline = (r.get("tldr_headline") or "").strip()
        if not day or not headline or day in seen:
            continue
        seen.add(day)
        out.append({
            "date": day,
            "headline": strip_dashes(headline),
            "lean": r.get("opinion_lean"),
        })
    return sorted(out, key=lambda d: d["date"])


def _generate_cover_stories(threads, edition):
    """Generate 2 cover stories from scored threads with data-driven timelines."""
    covers = []
    calls = 0

    for i, thread in enumerate(threads[:COVER_STORIES]):
        lead = thread["lead_cluster"]
        timeline = _build_data_timeline(thread)

        timeline_ctx = "\n".join(
            f"  {e['date']}: {e['title']} ({e['source_count']} sources)"
            for e in timeline
        )
        # Every printed row of the thread IN FULL: summary, consensus and
        # divergence for each day, not the titles of the days after the lead
        # (P1-18). The brief is then sized to those words, so a thread printed
        # once gets a short cover rather than a padded one.
        related_ctx = row_corpus(thread["clusters"])
        spec = sized_spec(ESSAY_SPECS["cover"], source_words(thread["clusters"]))
        if spec is None:
            print(f"    Cover {i+1}: '{lead.get('title', '')[:50]}' has too little "
                  f"printed text to write from; skipped")
            continue

        prompt = (
            f"Write a deep-dive cover story for Void Weekly ({edition} edition).\n\n"
            f"MAIN STORY: {lead.get('title', 'Untitled')}\n"
            f"Total sources across the week: {thread['cumulative_sources']}\n"
            f"Days active: {thread['daily_appearances']}\n"
            f"Summary: {lead.get('summary', '')}\n"
            f"Key agreements: {json.dumps(lead.get('consensus_points', []))}\n"
            f"Key disagreements: {json.dumps(lead.get('divergence_points', []))}\n\n"
            f"DATA TIMELINE (real dates, real clusters):\n{timeline_ctx}\n\n"
            f"EVERY PRINTED STORY IN THIS THREAD, IN FULL:\n{related_ctx}\n\n"
            f"Write a {spec['min_words']}-{spec['max_words']} word analytical essay "
            f"in flowing prose, weaving these real dates into the narrative. If the "
            f"stories above carry less, write less: a short essay is acceptable, a "
            f"padded one is not.\n"
            f"Quote only words that appear inside quotation marks above, exactly as "
            f"they appear there. Everything else is paraphrase, without quotation marks.\n"
            f"Do NOT invent events not shown above. Do NOT output a bulleted "
            f"timeline, a section titled TIMELINE, lists, or any Markdown headings."
        )

        result, used = _gen_essay(
            prompt, COVER_SYSTEM, model=_FLASH_MODEL, max_output_tokens=8192,
            want_numbers=True, spec=spec, label=f"cover {i+1}",
        )
        calls += used
        if result and isinstance(result, dict):
            result["_spec"] = spec
            # parse_essay leaves the headline empty when line 1 was prose, so
            # the essay keeps its lede. Name the feature from the cluster
            # rather than setting a paragraph at display size.
            if not result.get("headline"):
                result["headline"] = lead.get("title", "")
            result["cluster_id"] = lead.get("id")
            # The reported headline, kept beside the editorial one. The image
            # lookup needs a subject an encyclopedia indexes, and a cover
            # headline is written to be read rather than searched.
            result["cluster_title"] = lead.get("title", "")
            result["timeline"] = timeline
            result["thread_cluster_ids"] = [c.get("id") for c in thread["clusters"]]
            # The threading engine computes these over 500 clusters and then
            # drops them on the floor: they picked two headlines and were
            # garbage-collected. "This story ran 6 days across 47 sources" is
            # the one standfirst stat a WEEKLY can print that a daily cannot,
            # and `CoverOpening` already has a slot that today sums the
            # timeline's source counts instead, double-counting an outlet that
            # covered the story twice.
            result["days_active"] = thread.get("daily_appearances")
            result["week_sources"] = thread.get("cumulative_sources")
            covers.append(result)
            print(f"    Cover {i+1}: {result.get('headline', '?')[:60]}... ({len(result.get('text','').split())} words)")
        else:
            # Fallback — degrade to the thread's lead cluster verbatim.
            # (Was `cluster.get(...)`, an undefined name: the kill-switch
            # path crashed the whole weekly run with a NameError exactly
            # when both LLMs were unavailable.)
            covers.append({
                "headline": lead.get("title", ""),
                "text": lead.get("summary", ""),
                "timeline": [],
                "numbers": [],
                "cluster_id": lead.get("id"),
                "cluster_title": lead.get("title", ""),
                "_fallback": True,
            })
        time.sleep(3)

    return covers, calls


# ── SECTION 2: THE OPINIONS (5-6 topics × 1 voice each) ──

OPINION_SYSTEM = """You are a {perspective} columnist for Void Weekly.
Write a {min_words}-{max_words} word opinion essay; if the stories carry less, write less, never pad. {instruction}
Every fact MUST appear in the provided articles. Do not supplement with prior knowledge.
Argue only from facts in the provided stories. Historical parallels, other countries and 'patterns' are not permitted unless a provided article states them.

Your essay should:
- Take a clear position informed by {tradition} values
- Use specific facts, names, and numbers from the story
- Acknowledge the strongest counterargument in one sentence
- End with a concrete prediction or recommendation

SHOW, DON'T TELL: Argue through evidence, not adjectives. Never announce that a
fact is damning or that a number is shocking; state the fact or the number and
let it land. Do not reach for told-not-shown flourishes like "a brutal testament
to" or "a number that should chill any civilized observer". Give the number and
trust the reader. Open mid-argument on a concrete detail, not on a grand
abstraction. Active voice. No throat-clearing.

BANNED (output is REJECTED if present): "notable", "significant", "it should be
noted", "interestingly", "crucially", "in conclusion", "a testament to", "should
chill".

OUTPUT FORMAT — plain text only, no JSON, no Markdown:
Line 1 is the headline only (no label, no quotes). Then a blank line. Then the
{min_words}-{max_words} word essay in flowing prose. Quote only words that appear inside
quotation marks in the provided stories, exactly as they appear there."""


def _generate_opinions(top_threads, all_threads, edition):
    """Generate 5 opinions: 2 opposing on cover story, 3 on other important topics.

    The reader sees a genuine dialectic on the #1 story (progressive vs conservative)
    plus diverse perspectives on other key stories.
    """
    opinions = []
    calls = 0
    openers = []

    # Build opinion plan: 2 opposing on #1, then 3 on other stories
    plan = []  # list of (cluster_dict, lean_str)

    # First 2: opposing voices on cover story #1
    if top_threads:
        lead = top_threads[0]["lead_cluster"]
        plan.append((lead, "left", top_threads[0]))
        plan.append((lead, "right", top_threads[0]))

    # Third: center voice on cover story #2
    if len(top_threads) > 1:
        second = top_threads[1]["lead_cluster"]
        plan.append((second, "center", top_threads[1]))

    # Remaining: other important threads not in cover
    cover_ids = set()
    for t in top_threads:
        for c in t["clusters"]:
            cover_ids.add(c.get("id"))
    other = [t for t in all_threads if t.get("lead_cluster", {}).get("id") not in cover_ids]
    lean_cycle = ["center-left", "center-right"]
    for i, thread in enumerate(other[:2]):
        plan.append((thread["lead_cluster"], lean_cycle[i % 2], thread))

    for i, (cluster, lean, thread) in enumerate(plan):
        voice = OPINION_VOICE_CONFIGS.get(lean, OPINION_VOICE_CONFIGS["center"])
        is_paired = i < 2 and len(plan) >= 2
        # The column is written from every printed day of its thread, and its
        # brief is sized to those words (P1-18), as the cover's is.
        rows = (thread or {}).get("clusters") or [cluster]
        spec = sized_spec(ESSAY_SPECS["opinion"], source_words(rows))
        if spec is None:
            print(f"    Opinion {i+1} ({lean}): too little printed text to argue from; skipped")
            continue
        system = OPINION_SYSTEM.format(**voice, **spec)
        if is_paired:
            opposing = "conservative" if lean == "left" else "progressive"
            system += f"\n\nThis is a PAIRED opinion. A {opposing} columnist writes about the same story. Your reader sees both side by side."

        prompt = (
            f"Write a {voice['perspective']} opinion essay for Void Weekly ({edition}).\n\n"
            f"Topic: {cluster.get('title', 'Untitled')}\n\n"
            f"EVERY PRINTED STORY ON THIS TOPIC, IN FULL:\n{row_corpus(rows)}\n"
        )
        # The five opinion calls run in isolation, with no idea what the others
        # wrote, which is how "The ink is barely dry" came to open two
        # different essays in one issue.
        if openers:
            prompt += (
                "\nColumns already written for this issue open with:\n"
                + "\n".join(f"  {o}..." for o in openers)
                + "\nOpen differently. Do not reuse their first move.\n"
            )

        result, used = _gen_essay(
            prompt, system, max_output_tokens=4096,
            spec=spec, label=f"opinion {i+1} ({lean})",
        )
        calls += used

        if result and isinstance(result, dict):
            result["_spec"] = spec
            if not result.get("headline"):
                result["headline"] = cluster.get("title", "")
            openers.append(" ".join((result.get("text") or "").split()[:14]))
            result["lean"] = lean
            result["topic"] = cluster.get("title", "")
            result["cluster_id"] = cluster.get("id")
            result["paired"] = is_paired
            opinions.append(result)
            print(f"    Opinion {i+1} ({lean}): {result.get('headline', '?')[:50]}...")
        time.sleep(2)

    return opinions, calls


def _attach_art(essay, cluster):
    """One freely-licensed picture per department.

    The departments carry `image_url`, `image_caption` and `image_attribution`
    in the schema and in the component, and nothing ever called a lookup for
    them — so a 164 KB magazine shipped with exactly one photograph in it. The
    lookup is the same one Week in Brief uses.
    """
    if not cluster.get("id"):
        return
    try:
        found = find_cover_image_for_cluster(
            cluster["id"], essay.get("headline", ""), supabase_client=supabase,
            # The essay headline is written to be read; the cluster title is the
            # plain news headline the story was reported under and is what an
            # encyclopedia actually indexes. Try the first, fall back to the
            # second.
            alt_title=cluster.get("title", ""),
        )
    except Exception as e:
        print(f"    [weekly] department art lookup failed: {e}")
        return
    if found:
        essay["image_url"] = found["url"]
        if found.get("attribution"):
            essay["image_attribution"] = found["attribution"]
        if found.get("caption"):
            essay["image_caption"] = found["caption"]


# ── SECTION 3: TECH BRIEF ──

TECH_SYSTEM = """You are the technology correspondent for Void Weekly. Write a
analysis, at the length the prompt gives, of this week's most important technology story.
Focus on mechanism and implication, not hype. Think Ars Technica meets The Economist.
Every fact MUST appear in the provided articles. Do not supplement with prior knowledge.

BANNED: "game-changing", "revolutionary", "notable", "significant", "disrupting".

OUTPUT FORMAT — plain text only, no JSON, no Markdown:
Line 1 is the headline only (no label, no quotes). Then a blank line. Then the
analysis in flowing prose."""


def _generate_tech_brief(clusters, edition):
    """Find the top tech story and write a brief."""
    tech_clusters = [c for c in clusters if _category(c) in TECH_CATEGORIES]

    if not tech_clusters:
        # Fallback: look for tech keywords in titles
        tech_clusters = [
            c for c in clusters
            if any(kw in (c.get("title", "") or "").lower()
                   for kw in ["ai ", "tech", "cyber", "google", "apple", "microsoft",
                              "meta", "openai", "chip", "quantum", "robot", "space"])
        ]

    if not tech_clusters:
        return None, 0

    top_tech = tech_clusters[0]
    spec = sized_spec(ESSAY_SPECS["tech"], source_words([top_tech]))
    if spec is None:
        return None, 0
    prompt = (
        f"Write a tech brief for Void Weekly ({edition}), "
        f"{spec['min_words']}-{spec['max_words']} words; if the story carries less, write less.\n\n"
        f"THE STORY, IN FULL:\n{row_corpus([top_tech])}\n"
    )

    result, calls = _gen_essay(prompt, TECH_SYSTEM, max_output_tokens=4096,
                               spec=spec, label="tech")
    if result:
        result["_spec"] = spec
        if not result.get("headline"):
            result["headline"] = top_tech.get("title", "")
        result["cluster_id"] = top_tech.get("id")
        _attach_art(result, top_tech)
    return result, calls


# ── SECTION 4: SPORTS PAGE ──

SPORTS_SYSTEM = """You are the sports-and-culture correspondent for Void Weekly.
Write a piece, at the length the prompt gives, about this week's top sports story — but through the
lens of culture, politics, or economics. Sports as a mirror of society.
Think of how The New Yorker covers sports: the game is the entry point, the
story is about something larger.
Every fact MUST appear in the provided articles. Do not supplement with prior knowledge.

OUTPUT FORMAT — plain text only, no JSON, no Markdown:
Line 1 is the headline only (no label, no quotes). Then a blank line. Then the
piece in flowing prose."""


# THE CATEGORY LABEL IS NOT EVIDENCE. Issue #26 filed a German federal election
# under Sports & Culture: the cluster carried the label, `_generate_sports` read
# the label and nothing else, and a correspondent was told to write about it
# through "the lens of culture, politics, or economics" — which it duly did, at
# 500 words, on a page headed Sports & Culture. The label comes from a
# categorizer that can be wrong; the cluster's own words cannot be wrong about
# what the cluster says. So the words decide, and the label only nominates.
_SPORT_TERMS = (
    "nba", "nfl", "nhl", "mlb", "fifa", "uefa", "ioc", "olympic", "olympics",
    "paralympic", "world cup", "premier league", "champions league", "la liga",
    "serie a", "bundesliga", "formula 1", "formula one", "grand prix",
    "wimbledon", "us open", "french open", "australian open", "ryder cup",
    "super bowl", "world series", "ashes", "ipl",
    "football", "soccer", "basketball", "baseball", "cricket", "rugby",
    "tennis", "golf", "boxing", "mma", "ufc", "hockey", "cycling", "marathon",
    "athletics", "swimming", "gymnastics", "skiing", "surfing", "esports",
    "athlete", "athletes", "footballer", "striker", "goalkeeper", "midfielder",
    "quarterback", "batsman", "bowler", "sprinter", "boxer", "wrestler",
    "coach", "manager", "squad", "roster", "lineup", "dugout", "bench",
    "stadium", "arena", "pitch", "dressing room", "locker room",
    "tournament", "championship", "playoff", "playoffs", "semi-final",
    "semifinal", "quarter-final", "quarterfinal", "knockout", "league title",
    "medal", "medals", "gold medal", "podium", "doping", "transfer fee",
    "matchday", "fixture", "kick-off", "kickoff", "halftime", "full-time",
)
_CULTURE_TERMS = (
    "film", "films", "movie", "movies", "cinema", "box office", "screenplay",
    "documentary", "director", "filmmaker", "actor", "actress", "cast",
    "premiere", "festival", "cannes", "sundance", "venice film", "berlinale",
    "oscar", "oscars", "academy award", "bafta", "golden globe", "emmy",
    "album", "albums", "single", "song", "songs", "band", "singer",
    "songwriter", "rapper", "concert", "tour dates", "grammy", "grammys",
    "billboard", "streaming chart", "record label", "symphony", "orchestra",
    "opera", "ballet", "choreograph",
    "novel", "novels", "author", "novelist", "poet", "poetry", "memoir",
    "bestseller", "publisher", "booker prize", "pulitzer", "nobel prize in literature",
    "museum", "gallery", "exhibition", "curator", "painting", "sculpture",
    "biennale", "retrospective",
    "theatre", "theater", "broadway", "west end", "playwright", "stage play",
    "television series", "tv series", "sitcom", "miniseries", "season finale",
    "video game", "comic book", "fashion week", "couture", "runway show",
)
# A title that announces hard news is hard news, whatever the categorizer said.
# This only blocks the WEAKER evidence (terms found in the summary alone); a
# sport or culture term in the title still wins, so "Olympic boycott clears
# parliament" is still eligible.
_HARD_NEWS_TERMS = (
    "election", "elections", "electoral", "referendum", "parliament",
    "parliamentary", "chancellor", "president", "prime minister", "cabinet",
    "coalition", "ballot", "voters", "polls close", "impeach", "indictment",
    "coup", "airstrike", "air strike", "missile", "ceasefire", "troops",
    "invasion", "war", "genocide", "hostages", "sanctions", "tariff",
    "tariffs", "inflation", "interest rate", "central bank", "earthquake",
    "hurricane", "wildfire", "outbreak", "pandemic", "shooting", "bombing",
    "far-right", "far right",
)


def _term_hits(text, terms):
    """Distinct terms present in `text`, matched on word boundaries.

    Substring matching would score "war" inside "warm-up" and "ipl" inside
    "multiple". Every term here is whole-word or whole-phrase.
    """
    low = f" {(text or '').lower()} "
    for ch in "\n\t\r":
        low = low.replace(ch, " ")
    for ch in ".,;:!?()[]{}\"'“”‘’/\\|":
        low = low.replace(ch, " ")
    low = " ".join(low.split())
    low = f" {low} "
    return {t for t in terms if f" {t} " in low}


def _is_sport_or_culture(cluster):
    """Does this cluster's OWN TEXT say it is about sport or culture?

    Title evidence is decisive. Summary-only evidence needs two distinct terms,
    and is refused outright when the headline is plainly hard news, because one
    stray mention of "war" or "stadium" inside a political summary is not a
    sports page.
    """
    title = cluster.get("title") or ""
    summary = cluster.get("summary") or ""
    terms = _SPORT_TERMS + _CULTURE_TERMS

    if _term_hits(title, terms):
        return True
    if _term_hits(title, _HARD_NEWS_TERMS):
        return False
    return len(_term_hits(summary, terms)) >= 2


def _generate_sports(clusters, edition):
    """Find the top sports story and write a culture piece."""
    labelled = [c for c in clusters if _category(c) in SPORTS_CATEGORIES]
    labelled_ids = {id(c) for c in labelled}
    sports_clusters = [c for c in labelled if _is_sport_or_culture(c)]

    if not sports_clusters:
        sports_clusters = [c for c in clusters
                           if id(c) not in labelled_ids and _is_sport_or_culture(c)]

    if not sports_clusters:
        # Silence beats a plausible-looking wrong answer. A week with no sport
        # and no culture in it runs without the department.
        if labelled:
            print(f"    {len(labelled)} cluster(s) carried the label and failed "
                  f"the content gate, so no Sports & Culture piece this week")
        return None, 0

    top = sports_clusters[0]
    spec = sized_spec(ESSAY_SPECS["sports"], source_words([top]))
    if spec is None:
        return None, 0
    prompt = (
        f"Write a sports-as-culture piece for Void Weekly ({edition}), "
        f"{spec['min_words']}-{spec['max_words']} words; if the story carries less, write less.\n\n"
        f"THE STORY, IN FULL:\n{row_corpus([top])}\n"
    )

    result, calls = _gen_essay(prompt, SPORTS_SYSTEM, max_output_tokens=4096,
                               spec=spec, label="sports")
    if result:
        result["_spec"] = spec
        if not result.get("headline"):
            result["headline"] = top.get("title", "")
        result["cluster_id"] = top.get("id")
        _attach_art(result, top)
    return result, calls


# ── SECTION 5: BIAS REPORT (rule-based, $0) ──

def _generate_bias_report(clusters, bias_stats, edition, clusters_truncated=False):
    """Rule-based bias report from aggregate data.

    `clusters_truncated` rides on the returned dict rather than inside `stats`,
    because it is true independently of whether the bias scorer returned
    anything, and a half-built `stats` object would render as NaN on the page.
    """
    if not clusters or not bias_stats:
        # Even with no bias stats the colophon still prints the cluster and
        # article counts, so the flag has to survive this exit.
        return ("Insufficient data for this week's bias report.",
                {"clusters_truncated": True} if clusters_truncated else {})

    polarized = sorted(clusters, key=lambda c: c.get("divergence_score", 0), reverse=True)[:5]
    scored_hedge = "more than " if bias_stats.get("truncated") else ""
    cluster_hedge = "more than " if clusters_truncated else ""

    lines = [
        f"This week's {edition} edition scored {scored_hedge}{bias_stats['total_scored']:,} "
        f"articles across {cluster_hedge}{len(clusters)} story clusters.",
        "",
        f"Coverage lean: {bias_stats['avg_lean']}/100 "
        f"({'left-of-center' if bias_stats['avg_lean'] < 45 else 'center' if bias_stats['avg_lean'] < 55 else 'right-of-center'}).",
        # The dash ban applies to this file's prose too. `repair_weekly_snapshot`
        # has been stripping this one em dash out of every published issue and
        # the next run put it straight back.
        f"Lean spread: {bias_stats['lean_std']}, "
        f"{'tight consensus' if bias_stats['lean_std'] < 15 else 'healthy diversity' if bias_stats['lean_std'] < 25 else 'deep polarization'}.",
        f"Factual rigor: {bias_stats['avg_rigor']}/100.",
        f"Sensationalism: {bias_stats['avg_sensationalism']}/100.",
        "",
        "Most polarized stories:",
    ]
    for c in polarized[:3]:
        lines.append(f"  — {c.get('title', '?')} (divergence: {c.get('divergence_score', 0):.0f}, {c.get('source_count', 0)} sources)")

    return "\n".join(lines), {
        "most_polarized": [{"title": c.get("title"), "divergence": c.get("divergence_score", 0)} for c in polarized[:5]],
        "stats": bias_stats,
        # True only when the cluster read stopped short of the week. The page
        # then says "more than" for the story count and for the article total
        # summed from those same rows.
        "clusters_truncated": clusters_truncated,
    }


# ── SECTION 6: WEEK IN BRIEF (8-10 additional stories) ──

RECAP_SYSTEM = """You are an editor for Void Weekly. Write 55-75 word briefs.

Three sentences, each a fact the story gives: what happened, who did it or who
it lands on, and the next fact the story carries (a number, a date, a response).
Never say what an event signals, demonstrates, highlights or means; if the story
does not say it, leave it out, and write two sentences rather than guess a third.
This is a Week in Brief column, not a second feature well. A fourth sentence
belongs elsewhere in the issue; two sentences is a headline with a comma in it,
and any brief under 55 words is carrying one fact where it owes three. Lead
with the concrete fact. Use specific names and numbers.
Every fact MUST appear in the provided articles. Do not supplement with prior knowledge.
Never reference outlet names, "coverage," "sources," or "reporting patterns."

BANNED: "notable", "significant", "it should be noted", "interestingly".

OUTPUT FORMAT — plain text only, no JSON, no Markdown. For EACH story, output a
block in this exact shape:
###
<headline on one line>
<55-75 word brief in flowing prose>

Separate every story with a line containing only ### before it. No other
headings, labels, or Markdown."""


def _spread_over_week(clusters, count):
    """Pick `count` stories that span the week, not the loudest single day.

    THE SECTION WHOSE PREMISE IS THE WEEK CONTAINED NO WEEK. The old line was
    `clusters[:count]` off a query sorted by `headline_rank DESC`, and all ten
    published items matched daily-feed headlines from ONE date. A weekly recap
    that is Saturday's front page re-summarised is the largest "duplicates the
    daily feed" defect in the product.

    Round-robin by day, strongest first within each day, so a quiet Tuesday is
    represented before a loud Saturday gets its third slot. Falls back to plain
    rank order when the rows carry no usable dates.
    """
    by_day = {}
    for c in clusters:
        day = (c.get("printed_on") or c.get("first_published") or c.get("created_at") or "")[:10]
        by_day.setdefault(day, []).append(c)
    if len(by_day) <= 1:
        return clusters[:count]

    picked, days = [], sorted(by_day)
    while len(picked) < count:
        took = False
        for d in days:
            if by_day[d]:
                picked.append(by_day[d].pop(0))
                took = True
                if len(picked) == count:
                    break
        if not took:
            break
    return picked


def _generate_week_recap(clusters, edition, skip_ids=None):
    """Generate recap for remaining stories not covered elsewhere."""
    skip = set(skip_ids or [])
    remaining = _spread_over_week(
        [c for c in clusters if c.get("id") not in skip], WEEK_RECAP_COUNT,
    )

    if not remaining:
        return None, 0

    days = sorted({(c.get("printed_on") or c.get("first_published") or c.get("created_at") or "")[:10]
                   for c in remaining} - {""})
    print(f"    [brief] {len(remaining)} stories across {len(days)} day(s) of the week")

    # Each brief is written from its printed row IN FULL. The summary used to
    # be cut at 300 characters, which left the writer two sentences to make
    # three from, and the third was the guess ("signals a crackdown",
    # "signifies the high level of diplomatic engagement") that Issue #26's
    # correction removed.
    stories_text = "\n".join(
        f"--- Story {i+1} ---\n"
        f"{row_corpus([c])}\n"
        f"Category: {c.get('category', 'General')}"
        for i, c in enumerate(remaining)
    )

    prompt = f"Write 55-75 word briefs for these {len(remaining)} stories ({edition} edition):\n\n{stories_text}"

    # One retry for the whole column: it is a single call covering ten items,
    # and the spec was itself the bug here. RECAP_SYSTEM asked for 150-200 words
    # and the model obeyed exactly, which is why every published brief runs
    # ~1,000 characters in a three-column block designed for 65-word items.
    parsed, calls, findings = None, 0, []
    for attempt in range(2):
        # FLASH-LITE, not flash, and this is an improvement rather than a
        # concession. Sharing Sunday with the daily pipeline leaves ~7 of the
        # 20-a-day flash cap, and the flagship work is the two cover essays
        # plus the editorial. The recap is ten 55-to-75 word briefs, which is
        # exactly the shape flash-lite is good at — and because flash-lite has
        # a high RPD, the enforcement pass below can regenerate freely instead
        # of drawing on a budget of two. More retries on the smaller model
        # beats one retry on the larger one for copy this short.
        raw = _smart_generate_text(
            prompt if attempt == 0 else prompt + retry_suffix(findings),
            system_instruction=RECAP_SYSTEM,
        )
        calls += 1
        parsed = _parse_recap(raw)
        items = (parsed or {}).get("stories") or []
        if not items:
            break

        for story in items:
            story["summary"] = strip_significance(strip_dashes(story.get("summary", "")))
            story["headline"] = strip_significance(strip_dashes(story.get("headline", "")))

        # The band lives in `weekly_parse`, the pure core, so it is reachable
        # from a test that does not import this module. That is the whole
        # reason the core exists: the length rule that shipped nine of ten
        # briefs under the floor was unreachable from any gate while it sat
        # inline here.
        findings = enforce_recap(items, **ESSAY_SPECS["brief"])
        if not findings:
            if attempt:
                print("    [brief] clean on regeneration")
            break
        if attempt == 1:
            print(f"    [brief] shipped with: {'; '.join(findings)}")
            break
        print(f"    [brief] rejected: {'; '.join(findings)} — regenerating")

    # Re-attach the cluster identity that _parse_recap drops so each recap story
    # can surface the daily pipeline's already-cached WebP. The parsed stories
    # follow the same order as `remaining`; zip stops at the shortest, so a
    # count mismatch (e.g. the model merged or dropped a block) is safe.
    if parsed and parsed.get("stories"):
        for i, (story, cluster) in enumerate(zip(parsed["stories"], remaining)):
            if not story.get("headline"):
                story["headline"] = cluster.get("title", "")
            # Department kicker. The cluster already carries a category and the
            # frontend type already declares `section`; nothing ever copied it
            # across, so every brief item rendered unlabelled.
            if cluster.get("category"):
                story["section"] = cluster["category"]
            # The identity is in hand at exactly this line and was dropped, so
            # no brief item could ever link to its own /story/<id>/ page.
            story["cluster_id"] = cluster.get("id")
            # Thumbnails for the top 3 only. This used to read
            # `cached_image_url`, written by the cluster_image_cacher that rev
            # 60 RETIRED on copyright grounds, so it has been null on every row
            # since and .wk-brief__thumb has never rendered. Ten Commons
            # round-trips for ten thumbnails is not worth the run time.
            if i < BRIEF_THUMB_COUNT and cluster.get("id"):
                found = find_cover_image_for_cluster(
                    cluster["id"], story.get("headline", ""), supabase_client=supabase,
                    alt_title=cluster.get("title", ""),
                )
                if found:
                    story["image_url"] = found["url"]
                    if found.get("attribution"):
                        story["image_attribution"] = found["attribution"]
                    if found.get("caption"):
                        story["image_caption"] = found["caption"]
        # A kill-list verb or noun that survives the column's one regeneration
        # cuts its SENTENCE, the same rule `_gen_essay` applies to a piece. A
        # headline that carries one is replaced by the printed title; a brief
        # with nothing left once its sentences are cut is dropped.
        titles = {c.get("id"): c.get("title", "") for c in remaining}
        kept = []
        for story in parsed["stories"]:
            if drop_terms(story.get("headline")):
                story["headline"] = titles.get(story.get("cluster_id")) or ""
            text, cut = cut_slop_sentences(story.get("summary") or "")
            for sent, terms in cut:
                print(f"    [brief] cut for {', '.join(repr(t) for t in terms)}: {sent[:80]}")
            if not text.strip() or not story.get("headline"):
                print(f"    [brief] DROPPED {story.get('headline', '')[:50]!r}: nothing left")
                continue
            story["summary"] = text
            kept.append(story)
        parsed["stories"] = kept
    return parsed, calls



# ── SECTION 7: AUDIO — "The Argument", the Sunday edition ──

# The weekly was the last thing in the product still on the 2026-06 stack: one
# Gemini call writing free A:/B: dialogue into the legacy edge-tts path, two
# voices that every other edition also uses, no voice chain, no limiter, no
# loudnorm, UNMASTERED MONO, no chapters, no sidecar, not in the podcast feed
# and no validators. Three things in it were inert rather than merely dated:
# `_WEEKLY_TTS_PREAMBLE` (23 lines of pacing instructions) is assigned and read
# only by the PARKED Gemini TTS path; `WEEKLY_VOICE_PAIR` maps "The Editor" and
# "The Correspondent" through `_GEMINI_TO_EDGE_VOICE` to the same two edge
# voices, a label over an identical signal chain; and the prompt FORBADE
# segment markers ("NO [SEGMENT] headers. Raw dialogue only."), which is the
# single line that made a timeline, chapters and per-segment music impossible.
#
# All of that is kept, unchanged, as the fallback. A weekly that cannot be
# validated still ships a show.


def _after_cut(kind, pieces):
    """The pieces that can still ship once grounding and the source check are done.

    Each piece is measured against the brief it was WRITTEN to (`_spec`, sized
    to its sources), or the section's own brief when it has none. A piece
    under half its floor is a fragment and goes; anything above that ships at
    whatever length the sources left it. A fallback cover (the lead summary,
    no model) is not an essay and is left to the content floor further down.
    """
    out = []
    for i, p in enumerate(pieces or []):
        if not p:
            continue
        if p.get("_fallback"):
            out.append(p)
            continue
        why = length_after_cut(p.get("text") or "", p.get("_spec") or ESSAY_SPECS.get(kind))
        if why:
            print(f"    [length] {kind} {i + 1} dropped: {why}")
            continue
        out.append(p)
    return out


def _cover_core(c):
    """A cover feature's TEXT and structure, with no picture and no network.

    Split out because `_issue_view` needs the cover shape to build the audio
    rundown, and the only function that produced it was nested inside
    `generate_weekly_digest` — defined 960 lines below the module-level
    function calling it, and below the call site too. That is the
    `NameError: name '_cover_item' is not defined` that killed the first
    launch run AFTER every essay had been written and paid for.

    Keeping the image lookup out of here is the other half of the fix: it
    makes a network call per feature, and the rundown does not read images,
    so sharing `_cover_item` would have doubled those lookups to produce
    fields nothing downstream uses.
    """
    return {
        "headline": c.get("headline", ""),
        "text": c.get("text", ""),
        "timeline": c.get("timeline", []),
        "numbers": c.get("numbers", []),
        "cluster_id": c.get("cluster_id"),
        # The plain news headline the story was reported under, kept beside the
        # editorial one because the image lookup needs a searchable subject and
        # a cover headline is written to be read. "Greenland's Arctic Calculus"
        # names no subject any encyclopedia indexes.
        "cluster_title": c.get("cluster_title") or c.get("title", ""),
        "days_active": c.get("days_active"),
        "week_sources": c.get("week_sources"),
    }


def _issue_view(edition, week_start, week_end, issue_number, covers, opinions,
                tech, sports, recap, bias_data, weekly_opinion):
    """The issue as the PAGE will carry it, built before the row is written.

    The rundown and its validators read the published shape, not the
    generator's locals, so the programme is checked against the same object a
    reader gets. `_opinion_items` is what gives the bench its `pair_id`, and
    W-01 cannot check a column it cannot find.
    """
    from briefing.weekly_parse import DEPARTMENTS, _department_item, _opinion_items
    essays = {"tech": tech, "sports": sports}
    departments = [d for d in (_department_item(slug, label, essays.get(slug))
                               for slug, label in DEPARTMENTS) if d]
    return {
        "edition": edition,
        "issue_number": issue_number,
        "week_start": week_start.strftime("%Y-%m-%d") if hasattr(week_start, "strftime") else week_start,
        "week_end": week_end.strftime("%Y-%m-%d") if hasattr(week_end, "strftime") else week_end,
        "cover_headline": (covers[0].get("headline") if covers else "") or "",
        "cover_text": [_cover_core(c) for c in covers],
        "opinions": _opinion_items(opinions, issue_number),
        "departments": departments or [],
        "recap_stories": (recap or {}).get("stories", []),
        "bias_report_data": bias_data or {},
        "opinion_text": (weekly_opinion or {}).get("opinion_text"),
        "opinion_headline": (weekly_opinion or {}).get("opinion_headline"),
    }


def _produce_argument(issue: dict, edition: str):
    """Render the Sunday edition. Returns (result, calls) or (None, calls).

    Returns None on ANY failure. There is no longer a fallback: the caller
    raises. The reasoning for rejecting a bad rundown stands, and is why this
    still refuses rather than shipping it: an essay that runs forty words long
    is worth shipping, but a bench line the published column does not contain
    is words put in a columnist's mouth.

    What changed is what happens next. The legacy two-voice read used to run
    silently in its place, so a format that had never once produced a scheduled
    episode looked like a format that worked, and the published row said "Three
    voices" over a mono 24 kHz file nobody had mastered. A degraded artifact
    published as the real one is worse than no artifact.

    Every return below names its own cause. An import error, a rejected
    rundown and a render crash are three different problems and must not
    collapse into one line in a log nobody reads.
    """
    if os.environ.get("VOID_WEEKLY_AUDIO_FORMAT", "1").strip() == "0":
        print("    [weekly-audio] VOID_WEEKLY_AUDIO_FORMAT=0; audio parked by kill switch")
        return None, 0
    try:
        from briefing import weekly_rundown
        from briefing.weekly_producer import produce as produce_argument
        from briefing.audio_producer import _write_audio_static
    except Exception as e:
        print(f"    [weekly-audio] IMPORT FAILED: {e}")
        return None, 0

    script_text, findings, calls = weekly_rundown.generate(issue, _smart_generate_text)
    if not script_text:
        for f in findings:
            print(f"    [weekly-audio] {f.id} {f.segment}: {f.detail[:110]}")
        print("    [weekly-audio] RUNDOWN REJECTED by the validators above")
        return None, calls

    # Validated first, stripped second: the L: and R: lines were selected from
    # columns that are already significance-free, so only Void's own E: lines
    # can change here, and W-01's selection check has already passed on them.
    script_text = strip_significance(script_text)

    import tempfile
    out = Path(tempfile.mkdtemp(prefix="void-weekly-audio-"))
    try:
        rendered = produce_argument(script_text, issue, out, stem="weekly")
    except Exception as e:
        print(f"    [weekly-audio] RENDER FAILED: {e}")
        return None, calls
    if not rendered:
        return None, calls

    mp3 = Path(rendered["path"])
    sidecar = Path(rendered["sidecar"])
    url = _write_audio_static(
        mp3.read_bytes(), f"weekly-{edition}",
        # The key is a SUFFIX, not a filename: `_write_audio_static`
        # writes f"{stem}{suffix}", so passing `sidecar.name` here
        # produced `2026-09-20-pmweekly.chapters.json` and a
        # `latestweekly.chapters.json` beside it. Every other caller
        # passes the suffix (radio_producer.py:1195).
        sidecars={".chapters.json": sidecar.read_bytes()},
    )
    if not url:
        print("    [weekly-audio] could not write the file into the deploy tree")
        return None, calls
    rendered["audio_url"] = url
    rendered["script"] = script_text
    return rendered, calls


# ── SECTION 7b: the legacy two-voice read (fallback only) ──

# ---------------------------------------------------------------------------
# Weekly-specific voice pair for the LEGACY read: two registers, no hosts.
# The host roster these once named ("The Editor", "The Correspondent") was
# retired with the Gemini TTS path; the names lived on here and in a
# production prompt long after the product had no hosts (brand audit F-06).
# What remains is the register: voice A synthesizes and frames, voice B
# delivers facts with weight and patience. Institutional "we", evidence first
# and then the argument, and every segment ends on the tension rather than a
# summary. The pair does not rotate.
# ---------------------------------------------------------------------------
WEEKLY_VOICE_PAIR = {
    "host_a": {
        "id": "Sadaltager",
        "name": "Voice A",
        "register": "synthesizes and frames; evidence first, then the argument",
        "key": "editor",
        "gender": "male",
        "google_label": "knowledgeable",
        "trait": (
            "The senior voice. Synthesizes, contextualizes, places today's news in "
            "the arc of the week or the decade. Identifies the through-line across "
            "stories. Comfortable with silence. The voice that provides perspective "
            "— not prediction, but framing that helps the listener think."
        ),
        "tts_preamble": (
            "Knowledgeable, warm authority. Senior editorial voice. Comfortable pace "
            "with weight behind each sentence. Slight warmth — the voice of someone "
            "who has seen this before. Measured gravitas."
        ),
    },
    "host_b": {
        "id": "Achernar",
        "name": "Voice B",
        "register": "delivers facts with weight and patience; ends on the tension",
        "key": "correspondent",
        "gender": "female",
        "google_label": "informative",
        "trait": (
            "Measured authority. Lets facts land with their own weight. Short "
            "declarative sentences. Pauses after key facts to let them register. "
            "Trusts proximity to reveal the pattern — places two facts next to each "
            "other without editorializing."
        ),
        "tts_preamble": (
            "Low, steady, deliberate. BBC World Service gravitas. Pauses after key "
            "facts — not for drama, but for weight. Calm authority — never raises "
            "voice. Precision over speed."
        ),
    },
}

# Weekly TTS preamble — slower, more spacious than daily.
_WEEKLY_TTS_PREAMBLE = (
    "Audio Profile: Two senior journalists recording a Sunday magazine broadcast. "
    "This is NOT a breaking-news bulletin. The pace is slower, more reflective — "
    "the rhythm of a long-form conversation between two people who have spent the "
    "week inside the stories and are now making sense of them.\n\n"
    "Scene: A wood-paneled studio on a Sunday morning. Coffee. No monitors. No urgency. "
    "These two sit across from each other with notes and memory. The energy is "
    "contemplative — they are here to understand, not to update.\n\n"
    "Director's Notes: Magazine pace. Each speaker takes their time. Individual turns "
    "run 30 to 60 seconds — full paragraphs, not volleys. Pauses between speakers are "
    "real pauses, a full breath beat, not rapid-fire handoffs. Em dashes create "
    "thinking-out-loud pivots. Ellipses trail into reflection. Paragraph breaks "
    "between segments produce a deliberate scene change. The tone is two colleagues "
    "in no hurry, turning the week over in their hands.\n\n"
    "Speaker One: Knowledgeable, warm authority. Senior editorial voice. Comfortable "
    "pace — slower than daily broadcast. Weight behind each sentence. The voice of "
    "someone who has seen this before and wants to explain what it means. Longer "
    "sentences that build to a point. Comfortable with silence.\n\n"
    "Speaker Two: Low, steady, unhurried. BBC World Service gravitas. Deliberate "
    "pauses after key facts. Places two observations next to each other and lets "
    "the silence do the work. When he adds context, it lands like a footnote — "
    "precise, clarifying, never competing."
)


AUDIO_SYSTEM = """\
You are writing On Air Weekly, the Sunday magazine broadcast from Void News. \
This is a 15-minute long-form conversation, NOT a breaking-news update. Two hosts: \
A (the senior editor) and B (the foreign correspondent). They have spent the week \
reading everything. Now they sit down and make sense of it.

FORMAT: A: and B: tags only. NO [MUSIC], NO [TRANSITION], NO stage directions, \
NO segment markers, NO [SEGMENT] headers. Raw dialogue only.

---

PACE AND REGISTER:

This is The Economist's podcast, not CNN's morning show. Magazine pace means:
- Individual turns run 3-5 sentences (40-80 words). A speaks for 30-60 seconds \
at a time. B responds with 20-40 seconds of analysis. This is a CONVERSATION, \
not a volley.
- Between major topics, leave a blank line (paragraph break). The TTS reads this \
as a scene-change pause — a full breath beat.
- Use em dashes (—) mid-sentence for thinking-out-loud pivots: "The vote was \
Thursday — three days after the leak, which changes the calculus."
- Use ellipses (...) for deliberate trailing: "And the precedent that sets..."
- Short sentences after long ones create emphasis. "That changed Tuesday." lands \
harder after a 30-word explanation.
- Names, numbers, dates, places always. Attribute to institutions and officials.
- Every fact MUST appear in the provided articles. Do not supplement with prior knowledge.

WRONG (daily-brief pace): A reports 3 sentences. B reacts 2 sentences. Repeat.
RIGHT (magazine pace): A develops a thought across 4-5 sentences, building to \
a point. B responds with a new angle or counter-fact, also developed across \
3-4 sentences. They are two minds working through the material together.

---

STRUCTURE (target: 2500-3000 words total):

1. COLD OPEN (~120 words, ~35 sec)
   A grounds the listener first, in the composed, lightly formal cadence of The \
   Economist — unhurried, assured: "From void news. Today is {TODAY_LABEL}. On this \
   week's edition..." then one clause previewing what the week held. ONLY THEN does \
   A hook the listener with the week's defining tension in one dramatic sentence.
   B adds the second dimension — the fact that complicates the obvious reading.
   Example tone: "This was the week the trade war stopped being theoretical." / \
   "And the week both sides discovered their threat had the same price tag."

2. COVER STORY #1 — DEEP DIVE (~800-1000 words, ~5-6 min)
   The week's dominant story. A and B discuss it IN DEPTH, referencing:
   - The DATA TIMELINE: specific dates and events from the week (provided below).
     Reference these dates naturally: "By Wednesday..." / "That Friday number — \
     $4.2 billion — was the one that moved markets."
   - How the story evolved: what changed from Monday to Sunday.
   - What the numbers tell us that the headlines missed.
   - The structural question underneath the surface narrative.
   Turns are LONG here. A might speak for 60+ words tracing a cause-effect chain. \
   B might respond with 50 words of historical parallel or counter-data.

3. COVER STORY #2 — SECOND STORY (~400-500 words, ~2-3 min)
   Briefer treatment. A introduces the essential facts. B provides the dimension \
   the first telling missed — the cost, the precedent, the affected population.

4. OPINION SPOTLIGHT (~300-400 words, ~2 min)
   A reads a KEY EXCERPT from one of the week's opinion pieces (progressive or \
   conservative — pick the most provocative). A does not summarize — A READS \
   a striking passage of 2-3 sentences, then says which perspective it came from.
   B reacts with the strongest counter-argument from the opposing perspective.
   This is the most conversational segment — genuine intellectual engagement \
   with a position they may or may not share.

5. THE WEEK OTHERWISE (~400-500 words, ~2-3 min)
   Quick hits on 3-4 other stories from the week that didn't make the cover.
   A takes one, B takes one, A takes one. Each gets 80-120 words — enough for \
   the essential fact and one "why it matters" sentence. Pace picks up slightly \
   here — crisper transitions, shorter turns.

6. CLOSE (~100-150 words, ~30 sec)
   B offers a forward-looking thought about next week — what to watch, what \
   question remains unanswered. Not prediction — orientation. "The vote is \
   Thursday. The math hasn't changed. But the politics have."
   A signs off: "From void news, this was the weekly. We'll be back next Sunday."

---

DIALOGUE RULES:

- A and B are EQUALS. Both contribute facts, both provide analysis. A leads \
stories and introduces segments. B adds the dimension A didn't cover — counter-data, \
historical parallel, structural context, the affected population. B is NOT a \
reactor — B is a co-reporter with different instincts.
- Disagreement is expressed through additional facts, NEVER through contradiction. \
WRONG: "I disagree." RIGHT: "The Q3 data shows the opposite — 2.1% contraction."
- NO backchannel filler. NEVER as standalone lines: "Mm.", "Right.", "Indeed.", \
"Good point.", "Absolutely.", "Interesting.", "Exactly.", "Great question."
- NO meta-framing. BANNED sentence openers: "That's the tension...", \
"Which tells you...", "Here's why...", "What's interesting is...", \
"The question is...", "Let's go to...", "Now to...", "Worth noting...", \
"The key here...", "The bigger picture...", "This isn't just..."
- Instead, start every line with the FACT: the name, the number, the place, \
the date, the institution.
- NO scaffolding. Never announce what you're about to discuss. Jump straight \
to the first fact.

MAGAZINE-PACE TRANSITION PHRASES (use naturally, not as templates):
- "This week, the story that kept coming back..."
- "Step back for a moment..."
- "The number that tells the story..."
- "What both sides agree on — and where the argument breaks..."
- "By Thursday, the picture had changed..."
- "That's the surface reading. Underneath..."
- "The week started with... By Friday..."

BANNED WORDS/PHRASES (hard kill):
"notable", "significant", "unprecedented", "comprehensive", "pivotal", \
"landscape", "robust", "nuanced", "game-changing", "paves the way", \
"sends a clear message", "delve", "navigate", "underscores", "multifaceted", \
"it should be noted", "interestingly", "crucially", "in conclusion"

---

FIRST LINE: A: From void news. Today is {TODAY_LABEL}. On this week's edition, the weekly for {WEEK_LABEL}.
LAST LINE: A: From void news, this was the weekly. We'll be back next Sunday.

OUTPUT: the script ONLY, as plain text. Every line starts with "A:" or "B:". \
No JSON, no markdown fences, no preamble or commentary — just the spoken script.
"""


def _generate_audio(covers, opinions, tech, sports, recap, bias_data, edition,
                    week_start=None, week_end=None):
    """Generate the weekly audio broadcast script.

    Unlike the daily brief audio, the weekly script:
    - Includes data timelines so hosts can reference real dates
    - Includes full opinion excerpts with lean labels for the opinion spotlight
    - Includes bias report highlights (most polarized story, lean spread)
    - Targets 2500-3000 words for ~15 min at magazine pace
    """
    # Week label for sign-on
    week_label = ""
    if week_start and week_end:
        if hasattr(week_start, 'strftime'):
            week_label = f"{week_start.strftime('%B %d')} through {week_end.strftime('%B %d, %Y')}"
        else:
            week_label = f"{week_start} through {week_end}"
    else:
        week_label = "this week"

    # Air date for the Economist-style grounding intro ("Today is ...").
    today_label = datetime.now(timezone.utc).strftime("%A, %B %-d")

    # --- Cover stories with data timelines ---
    cover_blocks = []
    for i, c in enumerate(covers):
        block = f"COVER STORY {i+1}: {c.get('headline', '?')}\n"
        # Include the full essay text (truncated to 1200 words for prompt budget)
        text = c.get('text', '')
        text_words = text.split()
        if len(text_words) > 1200:
            text = ' '.join(text_words[:1200]) + '...'
        block += f"Essay:\n{text}\n"

        # Data timeline — real dates and events for hosts to reference
        timeline = c.get('timeline', [])
        if timeline:
            block += "\nDATA TIMELINE (use these real dates in dialogue):\n"
            for entry in timeline:
                block += f"  {entry.get('date', '?')}: {entry.get('title', '?')} ({entry.get('source_count', 0)} sources)\n"

        # Key numbers
        numbers = c.get('numbers', [])
        if numbers and isinstance(numbers, list):
            block += "\nKEY NUMBERS:\n"
            for n in numbers[:5]:
                if isinstance(n, dict):
                    block += f"  {n.get('stat', '?')} — {n.get('context', '')}\n"

        cover_blocks.append(block)

    cover_context = "\n\n".join(cover_blocks)

    # --- Opinion excerpts with lean labels for spotlight segment ---
    opinion_blocks = []
    if opinions:
        for o in opinions[:4]:
            lean = o.get('lean', '?')
            topic = o.get('topic', '?')
            text = o.get('text', '')
            # Include more text for the opinion spotlight — hosts need to quote from it
            text_words = text.split()
            if len(text_words) > 300:
                text = ' '.join(text_words[:300]) + '...'
            perspective = OPINION_VOICE_CONFIGS.get(lean, {}).get('perspective', lean)
            opinion_blocks.append(
                f"OPINION ({perspective} perspective on: {topic}):\n"
                f"Lean: {lean}\n"
                f"Headline: {o.get('headline', '?')}\n"
                f"Text: {text}"
            )
    opinion_context = "\n\n".join(opinion_blocks) if opinion_blocks else "No opinions available."

    # --- Bias report highlights ---
    bias_context = ""
    if bias_data and isinstance(bias_data, dict):
        stats = bias_data.get('stats', {})
        polarized = bias_data.get('most_polarized', [])
        lines = []
        if stats:
            lines.append(f"Coverage lean this week: {stats.get('avg_lean', '?')}/100")
            lines.append(f"Lean spread (std dev): {stats.get('lean_std', '?')}")
            lines.append(f"Average factual rigor: {stats.get('avg_rigor', '?')}/100")
            lines.append(f"Average sensationalism: {stats.get('avg_sensationalism', '?')}/100")
        if polarized:
            lines.append("Most polarized stories this week:")
            for p in polarized[:3]:
                lines.append(f"  - {p.get('title', '?')} (divergence score: {p.get('divergence', 0):.0f})")
        bias_context = "\n".join(lines)

    # --- Tech and sports quick-hit context ---
    tech_context = ""
    if tech and isinstance(tech, dict):
        tech_text = tech.get('text', '')[:300]
        tech_context = f"TECH STORY: {tech.get('headline', '?')}\n{tech_text}"

    sports_context = ""
    if sports and isinstance(sports, dict):
        sports_text = sports.get('text', '')[:300]
        sports_context = f"SPORTS STORY: {sports.get('headline', '?')}\n{sports_text}"

    # --- Recap stories for "The Week Otherwise" ---
    recap_context = ""
    if recap and isinstance(recap, dict):
        stories = recap.get('stories', [])
        if stories:
            recap_lines = []
            for s in stories[:5]:
                recap_lines.append(f"- {s.get('headline', '?')}: {s.get('summary', '')[:150]}")
            recap_context = "OTHER STORIES THIS WEEK:\n" + "\n".join(recap_lines)

    # --- Build the system instruction with week label ---
    system = AUDIO_SYSTEM.replace("{WEEK_LABEL}", week_label).replace("{TODAY_LABEL}", today_label)

    # --- Assemble the user prompt ---
    prompt = (
        f"Write On Air Weekly for the {edition} edition.\n"
        f"Week: {week_label}\n\n"
        f"{'=' * 60}\n"
        f"COVER STORIES (for deep-dive segments):\n\n{cover_context}\n\n"
        f"{'=' * 60}\n"
        f"OPINIONS (for opinion spotlight — pick the most provocative to quote):\n\n{opinion_context}\n\n"
        f"{'=' * 60}\n"
    )

    if bias_context:
        prompt += f"BIAS REPORT (reference selectively — the lean spread or most polarized story):\n{bias_context}\n\n"

    if tech_context or sports_context:
        prompt += f"QUICK HITS (for 'The Week Otherwise'):\n"
        if tech_context:
            prompt += f"{tech_context}\n\n"
        if sports_context:
            prompt += f"{sports_context}\n\n"

    if recap_context:
        prompt += f"{recap_context}\n\n"

    prompt += (
        f"{'=' * 60}\n"
        f"Generate the full 2500-3000 word magazine-pace script.\n"
        f"Remember: longer turns (40-80 words each), paragraph breaks between "
        f"segments, real dates from the data timelines, and one direct quote "
        f"from the opinion section."
    )

    # Single ~3000-word field with embedded opinion quotes — generate as PLAIN
    # TEXT so a stray quote can't break a JSON wrapper (the prior failure mode:
    # "Gemini JSON parse failed -> No audio script generated").
    script = _smart_generate_text(prompt, system_instruction=system, max_output_tokens=8192)
    if script and script.strip():
        # Significance words go; the dashes stay, they are breath marks here.
        return {"script": strip_significance(script.strip())}, 1
    return None, 1


# ---------------------------------------------------------------------------
# SECTION 6.5: THE WEEKLY EDITORIAL (one argued week-in-review column)
# Mirrors the daily void --opinion, but argues the through-line that only
# becomes visible at the week's length — and is told NOT to restate any of the
# week's daily columns (fed in as context). Opinion TEXT runs on flagship flash;
# the spoken monologue runs on flash-lite (plain text, to avoid json.loads
# fragility on a long em-dash/quote-heavy script).
# ---------------------------------------------------------------------------
_WEEKLY_LEAN_CYCLE = ["left", "center", "right"]
_WEEKLY_LEAN_LABELS = {"left": "progressive", "center": "pragmatic", "right": "conservative"}


def _get_week_lean(issue_number):
    """Rotate the weekly editorial's lens by issue number (mirrors the daily's
    day-of-year rotation). Successive weeks cycle left -> center -> right."""
    return _WEEKLY_LEAN_CYCLE[int(issue_number) % 3]


_WEEKLY_OPINION_LEAN_INSTRUCTIONS = {
    "left": """\
Today's lens: PROGRESSIVE. Argue from principles of collective welfare, institutional \
accountability, systemic equity, and the expansion of individual rights. Ask: who bore \
the cost this week? Whose voice was absent from the decisions that moved? What did the \
structure — not the individual actor — reward? You believe institutions exist to level \
asymmetries of power. When they failed to this week, that is the story.""",
    "center": """\
Today's lens: PRAGMATIC CENTER. Argue from principles of institutional stability, \
empirical evidence, tradeoff analysis, and incremental reform. Ask: what did the week's \
data actually show? What did every side get right, and what did each refuse to see? You \
distrust grand narratives from any direction. When everyone spent the week certain, that \
is the story.""",
    "right": """\
Today's lens: CONSERVATIVE. Argue from principles of individual liberty, market \
discipline, institutional restraint, and the wisdom of inherited structures. Ask: what \
did this week cost, and who was asked to pay without consenting? What second-order \
effects will the architects never face? You believe concentrated power corrupts \
regardless of intent. When the week's solutions required more authority than the \
problems, that is the story.""",
}


_WEEKLY_OPINION_SYSTEM = """\
You are the lead editorial writer at Void Weekly. Once a week you step back from the \
daily churn to write the column that only makes sense at the week's length. You use \
"we" — not as a hiding place behind the institution, but because what you are saying \
carries the desk's weight behind it.

You are NOT recapping the week. You are building ONE argument with accumulating weight, \
drawn from the through-line that runs across the week's biggest stories. Steady pace \
throughout. Each piece of evidence adds gravitational pull. By the end the reader should \
feel the conclusion was inevitable before you stated it. Earned, not announced.

THE WEEKLY DIFFERENCE — READ THIS TWICE:
You have already published this week's daily columns. They are provided below. Your job \
is NOT to restate them. A daily column argues one story on one day. Your column argues \
what becomes visible only when you set the week's stories beside each other: the pattern, \
the repetition, the cost that compounded across days while everyone watched a different \
headline. Name the through-line no single day could see. If your argument could have run \
on Tuesday about Tuesday's news, you have failed. Throw it out and find the week-length \
pattern.

VOICE & REGISTER:
You publish a position for the record, with the desk's weight behind it. You are direct. \
Short sentences when you are certain. You slow down when the complexity is real. You are \
allowed to be pointed. You are allowed to be angry if the facts warrant it. What you are \
NOT allowed to be is detached.

CARDINAL RULE — SHOW, DON'T TELL:
Every sentence earns its place through evidence. Never assert significance — demonstrate \
it through mechanism and the pattern across the week. The column's weight comes from \
facts marshaled in sequence, not from adjectives.

GROUNDING:
Every fact MUST appear in the provided articles. Do not supplement with prior knowledge. \
Argue only from facts in the provided stories. Historical parallels, other countries and 'patterns' are not permitted unless a provided article states them.

KILL SCAFFOLDING — ZERO TOLERANCE (output containing these is REJECTED):
Never announce what you are about to argue. ALL banned: "This isn't just...", "Here's \
the thing...", "The bigger picture...", "What makes this...", "The reality is...", "The \
question now is...", "This goes beyond...", "What's really happening here is...", "It's \
not just about...", "The takeaway is...", "The bottom line...", "This matters \
because...", "This is about more than...", "Let's be clear...". Also banned — slop \
adjectives that assert instead of show: "significant", "notable", "crucially", \
"importantly", "unprecedented", "pivotal", "nuanced", "comprehensive", "robust", \
"landscape", "navigate", "navigating", "underscores", "multifaceted", "delve", \
"breaking", "historic", "controversial", "divisive."
NO EM DASHES (—) OR EN DASHES (–) IN "opinion_text" OR "opinion_headline." Em dashes are \
an AI tell in written editorial prose. Rewrite as two sentences, or use a comma, \
semicolon, colon, or parentheses. Hyphens in compound words are fine.
Never reference outlet names, "coverage," "sources," or "reporting patterns." Synthesize \
the facts — do not cite where they came from. Start every sentence with the FACT or the \
ARGUMENT. If the sentence works without its opening clause, delete the opening clause.

IDEOLOGICAL LENS — {LEAN_UPPER}:
{LEAN_INSTRUCTION}

CRITICAL: Argue from PRINCIPLES, not parties. Never name Democrats, Republicans, BJP, \
Congress, Labour, or any party. Never take a politician's side. Reason from underlying \
values — what kind of society the week's decisions build, what tradeoffs they accept.

CRAFT:
Open with the most striking fact of the week — a number, a name, a reversal. Front-load \
evidence for 60-70% of the piece, pulling from at least two different stories so the \
pattern shows. The thesis arrives no earlier than the third paragraph; by then the \
evidence has made it inescapable. Include a genuine turn: the counterargument you take \
seriously. Close on tension, not summary. Every evaluative word must be replaceable by a \
specific number or mechanism. If it cannot be, delete it and show the evidence instead.

Standards:
- 450-650 words. One argument, drawn across multiple stories. No meta-commentary about media.
- Active voice. Concrete nouns. Specific numbers, names, dates.
- Write for a reader who followed the week. Add the insight they missed.
- Short sentences deliver verdicts. Long sentences build cases. Vary both.
- MUST use first-person plural "we" at least 3 times — the editorial board speaking as an \
institution.\
"""


_WEEKLY_OPINION_PROMPT = """\
Write the Void Weekly editorial for the {LEAN_UPPER} lens.
Every fact MUST appear in the provided articles. Do not supplement with prior knowledge.
Week: {WEEK_LABEL}
Edition: {EDITION_UPPER}

THE WEEK'S COVER STORIES (your primary evidence — draw the through-line across them):
{COVERS}

OTHER STORIES THAT MOVED THIS WEEK:
{THREADS}

WHAT THE WEEK IN BRIEF COVERED:
{RECAP}

BIAS SIGNAL (how contested the week's coverage was):
{BIAS}

DAILY COLUMNS WE ALREADY PUBLISHED THIS WEEK — DO NOT RESTATE ANY OF THESE:
{DAILY_OPINIONS}

Return JSON with exactly two fields:
1. "opinion_headline" — 6-12 word editorial headline. Not a news headline. A declarative \
statement of the week's thesis. Concrete nouns, active verbs. No "slams," "blasts." \
Example: "The week three institutions chose speed over proof."
2. "opinion_text" — 450-650 words. ONE argument about the WEEK, from the {LEAN_UPPER} \
lens, built across at least two of the stories above. Structure: opening fact -> \
accumulating evidence -> thesis (third paragraph) -> turn -> close on tension. Synthesize \
the facts; never cite where they came from. NO em dashes in this field.\
"""


_WEEKLY_OPINION_AUDIO_PROMPT = """\
Rewrite the editorial below as a single-voice spoken monologue for the Void Weekly \
broadcast. ONE speaker at the editorial desk on a Sunday, who has spent the week with \
these stories and has something to say. Not reading — TELLING.

EDITORIAL ({LEAN_UPPER} lens):
Headline: {HEADLINE}

{TEXT}

Write ONLY the spoken monologue — no labels, no A:/B: tags, just flowing text.
Every fact MUST appear in the provided articles. Do not supplement with prior knowledge. \
The editorial above is the only article you have.
Open with exactly: "Now, the void weekly editorial."
Then: "The week, through a {LEAN_LABEL} lens."
Then speak the headline as a title.
Then deliver the argument.
PACING — let thoughts linger. Steady throughout, never rush. Each sentence of evidence \
adds weight; the listener should feel the conclusion becoming inevitable before you state \
it. Short declarative sentences are verdicts. Long sentences build the case. Use 3-4 \
paragraph breaks — in a monologue, a paragraph break is a full beat of silence. At least \
once, let a one-sentence paragraph stand alone. Use em dashes for mid-thought pivots and \
ellipses (2-3 max) for genuine deliberation. Write for the ear, not the page.
Target 600-800 words.
End with exactly: "This was void opinion." End on the unresolved question, not a summary.\
"""


def _generate_weekly_opinion(covers, top_threads, recap, bias_data, daily_opinions,
                             lean, week_label, edition):
    """Generate the weekly editorial — one argued week-in-review column.

    Two LLM calls:
      1. flash JSON -> {opinion_headline, opinion_text}
      2. flash-lite plain text -> opinion_audio_script (long monologue; plain
         text avoids the json.loads fragility of a quote/em-dash-heavy script)
    Returns {opinion_text, opinion_headline, opinion_lean, opinion_audio_script}
    or None on failure (caller stores NULLs / skips opinion audio).
    """
    if not gemini_is_available():
        print("    [weekly-opinion] Gemini unavailable — skipping editorial")
        return None, 0

    calls = 0
    lean_upper = lean.upper()
    lean_label = _WEEKLY_LEAN_LABELS[lean]

    # --- Build evidence blocks ---
    cover_block = "\n\n".join(
        f"COVER {i+1}: {c.get('headline', '?')}\n"
        f"{' '.join((c.get('text', '') or '').split()[:220])}"
        for i, c in enumerate((covers or [])[:2])
    ) or "None"

    thread_block = "\n".join(
        f"  - {t.get('title', '?')} ({t.get('cumulative_sources', 0)} sources, "
        f"{t.get('daily_appearances', 0)} days)"
        for t in (top_threads or [])[:8]
    ) or "None"

    recap_block = "\n".join(
        f"  - {s.get('headline', '?')}"
        for s in (recap.get("stories", []) if recap else [])[:10]
    ) or "None"

    mp = (bias_data.get("most_polarized") or []) if isinstance(bias_data, dict) else []
    stats = (bias_data.get("stats") or {}) if isinstance(bias_data, dict) else {}
    if mp or stats:
        bias_block = (
            f"Most polarized story: {mp[0].get('title', '?') if mp else '?'}. "
            f"Average lean {stats.get('avg_lean', '?')}/100, spread "
            f"{stats.get('lean_std', '?')} (higher spread = more contested coverage)."
        )
    else:
        bias_block = "None"

    if daily_opinions:
        daily_block = "\n".join(
            f"  [{(o.get('opinion_lean') or '?')}] {o.get('opinion_headline', '?')}: "
            f"{' '.join((o.get('opinion_text', '') or '').split()[:60])}..."
            for o in daily_opinions
        )
    else:
        daily_block = "None published this week."

    system = _WEEKLY_OPINION_SYSTEM.format(
        LEAN_UPPER=lean_upper,
        LEAN_INSTRUCTION=_WEEKLY_OPINION_LEAN_INSTRUCTIONS[lean],
    )
    prompt = _WEEKLY_OPINION_PROMPT.format(
        LEAN_UPPER=lean_upper,
        WEEK_LABEL=week_label,
        EDITION_UPPER=edition.upper(),
        COVERS=cover_block,
        THREADS=thread_block,
        RECAP=recap_block,
        BIAS=bias_block,
        DAILY_OPINIONS=daily_block,
    )

    # --- Call 1: opinion headline + text (flash, JSON, 1 regeneration) ---
    #
    # This was the ONLY site in the file that checked anything, and it checked
    # by raw substring against a word budget it did not measure. It now asks
    # the same `enforce` every other section asks, so the editorial and the
    # columns beside it are held to one standard.
    headline, text = None, None
    findings = []
    for attempt in range(2):
        calls += 1
        result, gen = _smart_generate(
            prompt if attempt == 0 else prompt + retry_suffix(findings),
            system_instruction=system, model=_FLASH_MODEL,
        )
        if not (result and isinstance(result, dict)):
            findings = ["it returned nothing usable"]
            continue
        cand_text = strip_significance(strip_dashes((result.get("opinion_text") or "").strip()))
        cand_head = strip_significance(strip_dashes((result.get("opinion_headline") or "").strip()))
        if not cand_text or word_count(cand_text) < 150:
            print("    [weekly-opinion] Text too short or empty — discarding")
            findings = ["it returned almost nothing; write the full column"]
            continue

        findings = enforce(cand_text, **ESSAY_SPECS["editorial"])
        # Keep the best attempt either way: an editorial that runs 40 words
        # long reads better than no editorial at all.
        if not findings or text is None:
            headline, text = (cand_head or None), cand_text
        if not findings:
            print(f"    [weekly-opinion] {lean_upper} editorial: {word_count(text)} words"
                  f"{', headline: ' + repr(headline[:50]) if headline else ''}"
                  f"{' (regenerated)' if attempt else ''}")
            break
        if attempt == 1 or not _may_retry(_FLASH_MODEL):
            print(f"    [weekly-opinion] shipped with: {'; '.join(findings)}")
            break
        print(f"    [weekly-opinion] rejected: {'; '.join(findings)} — regenerating")

    if not text:
        print("    [weekly-opinion] Editorial generation failed")
        return None, calls
    # Same rule as `_gen_essay`: a kill-list verb or noun that survived the
    # regeneration cuts its sentence, and a headline carrying one is dropped
    # (the page then sets the editorial without a headline).
    if drop_terms(headline):
        headline = None
    text, cut = cut_slop_sentences(text)
    for sent, terms in cut:
        print(f"    [weekly-opinion] cut for {', '.join(repr(t) for t in terms)}: {sent[:80]}")
    if not (text or "").strip():
        print("    [weekly-opinion] DROPPED: nothing left once the kill-list sentences were cut")
        return None, calls

    # --- Call 2: spoken monologue (flash-lite, plain text) ---
    audio_prompt = _WEEKLY_OPINION_AUDIO_PROMPT.format(
        LEAN_UPPER=lean_upper, LEAN_LABEL=lean_label,
        HEADLINE=headline or text.split(".")[0], TEXT=text,
    )
    calls += 1
    audio_script = _smart_generate_text(audio_prompt)
    if audio_script:
        audio_script = audio_script.strip()

    sign_on = f"Now, the void weekly editorial. The week, through a {lean_label} lens."
    if not audio_script or len(audio_script.split()) < 200:
        # Fallback: the opinion text is already in spoken cadence — add bookends.
        head_line = f" {headline}." if headline else ""
        audio_script = f"{sign_on}{head_line}\n\n{text}\n\nThis was void opinion."
        print(f"    [weekly-opinion] Audio: fallback from text ({len(audio_script.split())} words)")
    else:
        if "now, the void weekly editorial" not in audio_script.lower()[:80]:
            audio_script = f"{sign_on}\n\n{audio_script}"
        if "this was void opinion" not in audio_script.lower()[-80:]:
            audio_script = f"{audio_script}\n\nThis was void opinion."
        print(f"    [weekly-opinion] Audio script: {len(audio_script.split())} words")
    # Significance words go from the spoken text too; the dashes stay.
    audio_script = strip_significance(audio_script)

    return {
        "opinion_text": text,
        "opinion_headline": headline,
        "opinion_lean": lean,
        "opinion_audio_script": audio_script,
    }, calls


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def generate_weekly_digest(editions=None, week_offset=0):
    """Generate weekly digests for all editions."""
    if editions is None:
        editions = EDITIONS

    now = datetime.now(timezone.utc)
    # week_offset counts weeks BACK from the most recently COMPLETED Monday-to-
    # Sunday week: 0 is the week that just ended, 1 the week before it, and -1
    # the current in-progress week (partial data, for a mid-week refresh).
    #
    # This sign was inverted until 2026-09-19: offset 0 resolved to the week
    # CONTAINING today, so the Monday 12:00 UTC cron generated a digest for the
    # week that had just started, off roughly twelve hours of coverage, while
    # the cron comment and the --week-offset help both claimed it covered the
    # week that had just ended. Issue #23 (week of 2026-08-24, generated
    # 2026-08-24 12:48) is the last one that shipped that way.
    week_start, week_end, issue_number = weekly_window(now, week_offset)

    print("=" * 60)
    print(f"void --weekly Issue #{issue_number}")
    print(f"  Week: {week_start.strftime('%b %d')} — {week_end.strftime('%b %d, %Y')}")
    print(f"  Editions: {', '.join(editions)}")
    print("=" * 60)

    stored = 0
    for edition in editions:
        t0 = time.time()
        total_calls = 0
        print(f"\n{'─' * 50}")
        print(f"[weekly:{edition}] Issue #{issue_number}")
        print(f"{'─' * 50}")

        # Fetch data
        clusters, clusters_truncated = _fetch_week_clusters(edition, week_start, week_end)
        print(f"  Clusters: {'more than ' if clusters_truncated else ''}{len(clusters)}")
        # The printed record is read before deciding there is nothing to say:
        # a run a few days late finds the cluster table already pruned (0 rows
        # for Sep 21-27 on 2026-10-01) while every printed day is still there.
        printed = _fetch_week_printed(week_start, week_end)
        printed_days = sorted({r["printed_on"] for r in printed if r.get("printed_on")})
        print(f"  Printed: {len(printed)} front-page rows over {len(printed_days)} day(s)")
        if len(clusters) < 3 and len(printed_days) < 3:
            print(f"  Insufficient data — skipping")
            continue

        bias_stats = _fetch_bias_stats(edition, week_start, week_end)
        print(f"  Bias scores: {bias_stats['total_scored'] if bias_stats else 0}")

        # Track used cluster IDs to avoid repetition in recap
        used_ids = set()

        # The week's stories come from what Void printed, not from the raw
        # cluster table (pruned to two days, and full of what Stage 2
        # rejected). The cluster pool still feeds tech, sports and the bias
        # counts, which look past the front page by design.
        story_pool = printed if len(printed_days) >= 3 else clusters
        if story_pool is clusters:
            print(f"  [warn] fewer than 3 printed days in the week; covers read the cluster table")

        # Link clusters into story threads
        print(f"  Linking story threads...")
        threads = _link_story_threads(story_pool)
        print(f"  Threads: {len(threads)} (from {len(story_pool)} stories)")

        # Fetch daily brief signals
        brief_signals = _fetch_brief_signals(edition, week_start, week_end)
        print(f"  Brief signals: {len(brief_signals)} daily briefs")

        # Score and select top 2 mega-stories
        top_threads = _score_weekly_threads(threads, brief_signals, edition)
        print(f"  Top threads: {len(top_threads)}")
        for t in top_threads:
            print(f"    #{t.get('weekly_score',0):.2f} — {t['title'][:60]} "
                  f"({t['cumulative_sources']} sources, {t['daily_appearances']} days)")

        # Section 1: Cover stories from top threads
        print(f"\n  ── THE COVER ──")
        covers, calls = _generate_cover_stories(top_threads, edition)
        total_calls += calls
        for c in covers:
            if c.get("cluster_id"):
                used_ids.add(c["cluster_id"])
        # Every day of a cover thread is the cover's, not the recap's.
        for t in top_threads[:len(covers)]:
            used_ids.update(c.get("id") for c in t["clusters"] if c.get("id"))

        # Cover image: freely licensed sources only (Wikimedia Commons first).
        cover_image = None
        if covers and covers[0].get("cluster_id"):
            print(f"\n  ── COVER IMAGE ──")
            cover_image = find_cover_image_for_cluster(
                covers[0]["cluster_id"],
                covers[0].get("headline", ""),
                supabase_client=supabase,
                alt_title=covers[0].get("cluster_title", ""),
            )
            if cover_image:
                print(f"    ✓ {cover_image['source']}: {cover_image['url'][:80]}...")
            else:
                print(f"    No suitable cover image found")

        # Section 2: Opinions (5-6 topics × rotating leans)
        print(f"\n  ── THE OPINIONS ──")
        opinions, calls = _generate_opinions(top_threads, threads, edition)
        total_calls += calls
        for o in opinions:
            if o.get("cluster_id"):
                used_ids.add(o["cluster_id"])

        # Sections 3 and 4: Tech and Sports & Culture, SUSPENDED by default
        # (decision 5). No call is spent and the issue carries no department.
        tech, sports = None, None
        if not WEEKLY_DEPARTMENTS:
            print(f"\n  ── DEPARTMENTS ── suspended (VOID_WEEKLY_DEPARTMENTS=1 to run them)")
        else:
            print(f"\n  ── TECH BRIEF ──")
            tech, calls = _generate_tech_brief(clusters, edition)
            total_calls += calls
            if tech:
                print(f"    {tech.get('headline', '?')[:60]}")
                if tech.get("cluster_id"):
                    used_ids.add(tech["cluster_id"])
            else:
                print(f"    No tech story found")

            print(f"\n  ── SPORTS PAGE ──")
            sports, calls = _generate_sports(clusters, edition)
            total_calls += calls
            if sports:
                print(f"    {sports.get('headline', '?')[:60]}")
                if sports.get("cluster_id"):
                    used_ids.add(sports["cluster_id"])
            else:
                print(f"    No sports story found")

        # Section 5: Bias report (rule-based, 0 calls)
        print(f"\n  ── BIAS REPORT ──")
        bias_text, bias_data = _generate_bias_report(
            clusters, bias_stats, edition, clusters_truncated=clusters_truncated)

        # Section 6: Week in brief (remaining stories)
        print(f"\n  ── WEEK IN BRIEF ──")
        if story_pool is printed:
            # Skip a thread when ANY of its days went to a section above.
            used_threads = {r.get("story_thread_id") for r in printed if r.get("id") in used_ids}
            recap_pool = [r for r in _one_per_thread(printed)
                          if r.get("story_thread_id") not in used_threads]
        else:
            recap_pool = clusters
        recap, calls = _generate_week_recap(recap_pool, edition, skip_ids=used_ids)
        total_calls += calls
        recap_count = len(recap.get("stories", [])) if recap else 0
        print(f"    {recap_count} stories")

        # Section 6.5: Weekly editorial — one argued week-in-review column,
        # distinct from every daily opinion this week (fed in below).
        print(f"\n  ── WEEKLY EDITORIAL ──")
        daily_rows = _fetch_daily_opinions(edition, week_start, week_end)
        # The rail wants every day that ran a brief; the editorial prompt wants
        # only the days that argued something. One query, two consumers.
        week_days = _week_days(daily_rows, week_start, week_end)
        daily_opinions = [r for r in daily_rows if (r.get("opinion_text") or "").strip()]
        print(f"    {len(week_days)} day(s) of the week recorded for the rail")
        week_lean = _get_week_lean(issue_number)
        week_label = f"{week_start.strftime('%B %d')} through {week_end.strftime('%B %d, %Y')}"
        print(f"    {len(daily_opinions)} daily columns to differ from; lens: {week_lean}")
        weekly_opinion, calls = _generate_weekly_opinion(
            covers, top_threads, recap, bias_data, daily_opinions,
            week_lean, week_label, edition,
        )
        total_calls += calls

        # Grounding, before anything is spoken or stored. Every sentence that
        # carries a number or a multi-word name the week's sources do not is
        # cut (CLAUDE.md Rule 1: cut, not softened). Issue #27's first draft
        # said Iran's economic pressure "intensified since the U.S. withdrawal
        # from the Joint Comprehensive Plan of Action"; nothing printed that
        # week said so. The corpus is exactly what the writers were handed:
        # the story pool, the timelines' source counts and the daily columns.
        corpus = " ".join(
            (v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))
            for r in story_pool
            for v in (r.get("title") or "", r.get("summary") or "",
                      r.get("consensus_points") or "", r.get("divergence_points") or "",
                      str(r.get("source_count") or ""), str(r.get("printed_on") or ""))
        ) + " " + " ".join(
            f"{t.get('cumulative_sources', '')} {t.get('daily_appearances', '')}" for t in top_threads
        ) + " " + " ".join(str(d.get("opinion_text") or "") for d in (daily_rows or []))

        # Quotations are held to the PRINTED stories only (W-T22): a daily
        # column is Void's own prose, not anybody's words.
        quote_corpus = row_corpus(story_pool)

        def _ground(label, text, extra_rows=()):
            src = corpus + (" " + row_corpus(extra_rows) if extra_rows else "")
            kept, cut = ground_text(text, src)
            for sent, miss in cut:
                print(f"    [ground] {label}: cut {miss}: {sent[:120]}")
            qsrc = quote_corpus + ("\n\n" + row_corpus(extra_rows) if extra_rows else "")
            kept, cut = ground_quotes(kept, qsrc)
            for sent, miss in cut:
                print(f"    [ground] {label}: cut unsourced quotation {miss}: {sent[:120]}")
            return kept

        for i, c in enumerate(covers):
            c["text"] = _ground(f"cover {i + 1}", c.get("text") or "")
        for i, o in enumerate(opinions):
            o["text"] = _ground(f"opinion {i + 1}", o.get("text") or "")
        for i, st in enumerate((recap or {}).get("stories") or []):
            st["summary"] = _ground(f"recap {i + 1}", st.get("summary") or "")
        if weekly_opinion and weekly_opinion.get("opinion_text"):
            weekly_opinion["opinion_text"] = _ground("editorial", weekly_opinion["opinion_text"])
        # The departments read the cluster pool, so each is grounded against
        # its own cluster as well as the week.
        by_id = {c.get("id"): c for c in clusters}
        for name, piece in (("tech", tech), ("sports", sports)):
            if piece and piece.get("text"):
                own = [by_id[piece["cluster_id"]]] if piece.get("cluster_id") in by_id else []
                piece["text"] = _ground(name, piece["text"], own)

        # The source check: flash-lite reads every sentence against the week
        # (weekly_source_check). The deterministic cut above catches only an
        # unsourced number or name; this catches the unnamed background
        # ("a substantial portion of the world's seaborne oil") and the claim
        # the week contradicts. A piece it cannot read does not ship.
        print(f"\n  ── SOURCE CHECK ──")
        from briefing.weekly_source_check import check_piece, check_texts, source_text
        week_sources = source_text(story_pool) + "\n\n" + "\n\n".join(
            f"DAILY COLUMN: {d.get('opinion_text')}" for d in (daily_rows or []) if d.get("opinion_text"))

        def _lite_json(prompt, **kw):
            time.sleep(8)  # flash-lite TPM: each request carries the whole week
            return gemini_generate_json(prompt, count_call=False, model=None, **kw)

        kept_covers = []
        for i, c in enumerate(covers):
            txt, _ = check_piece(c.get("text") or "", week_sources, _lite_json, label=f"cover {i + 1}")
            if txt:
                c["text"] = txt
                kept_covers.append(c)
        covers = kept_covers
        kept_ops = []
        for i, o in enumerate(opinions):
            txt, _ = check_piece(o.get("text") or "", week_sources, _lite_json, label=f"opinion {i + 1}")
            if txt:
                o["text"] = txt
                kept_ops.append(o)
        opinions = kept_ops
        if recap and recap.get("stories"):
            outs, _ = check_texts([st.get("summary") or "" for st in recap["stories"]],
                                  week_sources, _lite_json, label="recap")
            recap["stories"] = [dict(st, summary=t) for st, t in zip(recap["stories"], outs) if t]
        if weekly_opinion and weekly_opinion.get("opinion_text"):
            txt, _ = check_piece(weekly_opinion["opinion_text"], week_sources, _lite_json,
                                 label="editorial")
            if txt:
                if txt != weekly_opinion["opinion_text"]:
                    # The monologue was written from the uncut text.
                    weekly_opinion["opinion_audio_script"] = None
                weekly_opinion["opinion_text"] = txt
            else:
                weekly_opinion = None
        # Tech and sports are written from the full cluster pool, not the
        # printed week, so each is read against its own cluster as well.
        by_id = {c.get("id"): c for c in clusters}
        for name in ("tech", "sports"):
            piece = tech if name == "tech" else sports
            if not piece or not piece.get("text"):
                continue
            own = [by_id[piece["cluster_id"]]] if piece.get("cluster_id") in by_id else []
            txt, _ = check_piece(piece["text"], source_text(own) + "\n\n" + week_sources,
                                 _lite_json, label=name)
            if txt:
                piece["text"] = txt
            elif name == "tech":
                tech = None
            else:
                sports = None

        # LENGTH, AGAIN, ON WHAT SURVIVED (P1-18). `_gen_essay` measured each
        # piece before grounding and the source check cut it, and nothing
        # measured it after: a cover could lose half its sentences and ship as
        # a fragment, or (the old failure) be padded to a brief the sources
        # could not fill. A short piece ships; a fragment does not; nothing is
        # ever regenerated to add words.
        covers, opinions = _after_cut("cover", covers), _after_cut("opinion", opinions)
        tech = (_after_cut("tech", [tech]) or [None])[0] if tech else None
        sports = (_after_cut("sports", [sports]) or [None])[0] if sports else None
        if weekly_opinion and weekly_opinion.get("opinion_text"):
            why = length_after_cut(weekly_opinion["opinion_text"], ESSAY_SPECS["editorial"])
            if why:
                print(f"    [length] editorial dropped: {why}")
                weekly_opinion = None
        print(f"    {len(covers)} cover(s), {len(opinions)} column(s), "
              f"{len((recap or {}).get('stories') or [])} recap item(s), "
              f"editorial {'kept' if weekly_opinion else 'dropped'} after the check")

        # Section 7: Audio.
        print(f"\n  ── AUDIO ──")
        audio_url = None
        audio_duration = None
        audio_size = None
        opinion_start = None
        audio_chapters = None
        audio_voice = None
        audio_script = None

        argument, calls = _produce_argument(
            _issue_view(edition, week_start, week_end, issue_number, covers,
                        opinions, tech, sports, recap, bias_data, weekly_opinion),
            edition,
        )
        total_calls += calls
        if argument:
            audio_url = argument["audio_url"]
            audio_duration = argument["seconds"]
            audio_size = argument["bytes"]
            audio_chapters = argument["chapters"]
            audio_script = argument["script"]
            v = argument["voices"]
            audio_voice = f"kokoro:{v['editor']}+{v['left']}+{v['right']}"
            # The Editor reads the editorial, so the opinion is a CHAPTER
            # rather than a seek offset. The rail supersedes the two-tab split.
            ed = next((c for c in audio_chapters if c["kind"] == "editorial"), None)
            opinion_start = ed["startTime"] if ed else None
            print(f"    The Argument: {audio_duration:.0f}s, {len(audio_chapters)} chapters, "
                  f"{audio_size/1e6:.1f} MB")

        # No fallback. The Argument renders or the Weekly ships without audio.
        #
        # Until 2026-09-20 a failure here silently ran the legacy two-voice
        # edge-tts read instead. The consequence was not a quieter episode, it
        # was a false one: the row kept saying "Three voices" and
        # kokoro:bm_lewis+am_michael+af_heart over a 96k mono 24 kHz file that
        # no loudnorm had touched, and every scheduled run since the format
        # shipped had taken that path without anyone noticing. A degraded
        # artifact published as the real one is worse than no artifact.
        #
        # VOID_WEEKLY_AUDIO_FORMAT=0 is now the only way to get the legacy
        # read, and it parks audio rather than substituting for it.
        #
        # "Ships without audio" is what this comment always said; the code
        # raised instead, so a rundown 1.6 minutes under its band (W-07,
        # 2026-10-01) threw away a finished issue: two covers, four columns,
        # a seven-day recap and the editorial, with nothing stored. W-09 on the
        # served page already accepts an issue with no audio. The failure
        # stays loud: an Actions error annotation, and the row carries no
        # audio fields at all, so nothing claims a voice that never read it.
        if not argument:
            print("::error title=The Argument did not render::The Weekly ships "
                  "WITHOUT audio this week. The cause is the [weekly-audio] line "
                  "above; re-render once fixed with mode=audio-only.")

        # A floor under what gets published. The audio raise used to stop a
        # run with no model at all, by accident; with the issue now allowed to
        # ship without audio, that has to be said on purpose. Without a single
        # written cover and at least one written column or recap, this is the
        # daily summaries re-printed under a Weekly masthead: store nothing.
        written_covers = [c for c in covers if not c.get("_fallback")]
        if not written_covers or not (opinions or (recap or {}).get("stories")):
            print(f"  [weekly:{edition}] NOT STORED: {len(written_covers)} written cover(s), "
                  f"{len(opinions)} column(s), {len((recap or {}).get('stories') or [])} recap item(s)")
            continue
        for c in covers:
            c.pop("_fallback", None)

        # Store
        elapsed = time.time() - t0

        def _cover_item(c):
            """The persisted cover item: the shared core, plus its picture."""
            item = _cover_core(c)
            # Each cover essay gets its own picture, from a freely licensed
            # source. This used to read `cached_image_url`, written by the
            # cluster_image_cacher that rev 60 RETIRED on copyright grounds, so
            # the column has been null on every row since and the weekly has
            # carried one image instead of three.
            headline = (c.get("headline") or "").strip()
            if headline:
                found = find_cover_image_for_cluster(
                    c.get("cluster_id") or "", headline, supabase_client=supabase,
                    alt_title=c.get("cluster_title", ""),
                )
                if found:
                    item["image_url"] = found["url"]
                    if found.get("attribution"):
                        item["image_attribution"] = found["attribution"]
                    if found.get("caption"):
                        item["image_caption"] = found["caption"]
                    print(f"    story image ({found['source']}): {found['url'][:70]}")
            return item

        row = build_weekly_row(
            edition=edition,
            week_start=week_start.strftime("%Y-%m-%d"),
            week_end=week_end.strftime("%Y-%m-%d"),
            issue_number=issue_number,
            cover_items=[_cover_item(c) for c in covers],
            opinions=opinions,
            tech=tech,
            sports=sports,
            recap_stories=recap.get("stories", []) if recap else [],
            bias_text=bias_text,
            bias_data=bias_data,
            weekly_opinion=weekly_opinion,
            audio={
                "script": audio_script,
                "audio_url": audio_url,
                "duration_seconds": audio_duration,
                "file_size": audio_size,
                "opinion_start_seconds": opinion_start,
                "chapters": audio_chapters,
                "voice": audio_voice,
                "voice_label": "Three voices" if audio_chapters else None,
            },
            cover_image=cover_image,
            # ONE article figure. This was the sum of `source_count` over the
            # cluster read, which is sources per story, not articles, and Issue
            # #26 printed 2,355 of it in the colophon beside "more than 60,000
            # articles" scored in The Week in Bias. The colophon's hedge reads
            # `clusters_truncated`, so a scorer read that hit its own ceiling
            # prints nothing rather than a floor dressed as a count.
            total_articles=(bias_stats["total_scored"]
                            if bias_stats and (not bias_stats.get("truncated") or clusters_truncated)
                            else None),
            week_days=week_days,
            total_clusters=len(clusters),
            gemini_calls=total_calls,
            elapsed=elapsed,
            voice_pair=WEEKLY_VOICE_PAIR,
        )

        try:
            supabase.table("weekly_digests").upsert(
                row, on_conflict="edition,week_start"
            ).execute()
            print(f"\n  ✓ Issue #{issue_number} stored ({total_calls} calls, {elapsed:.0f}s)")
            stored += 1
        except Exception as e:
            print(f"\n  ✗ Storage failed: {e}")

    print(f"\n{'=' * 60}")
    print(f"void --weekly complete.")
    return stored


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="void --weekly digest generator")
    parser.add_argument("--editions", type=str, default="", help="Comma-separated editions")
    parser.add_argument(
        "--week-offset", type=int, default=0,
        help="Weeks back from the week that just ended. "
             "0=the completed week, 1=the one before it, -1=the current partial week")
    args = parser.parse_args()

    editions = [e.strip() for e in args.editions.split(",") if e.strip()] if args.editions else None
    # No issue stored means the workflow must stop HERE. Its export step reads
    # the newest weekly row in the restored DB, which on 2026-10-01 was a stale
    # copy of the PREVIOUS issue: it re-wrote the published Issue #26 without
    # its audio chapters or images and committed it.
    if not generate_weekly_digest(editions=editions, week_offset=args.week_offset):
        print("No issue was stored; failing so nothing is exported or committed.")
        sys.exit(1)
