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

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from utils.supabase_client import supabase
from summarizer.gemini_client import (
    generate_json as gemini_generate_json,
    is_available as gemini_is_available,
)

try:
    from summarizer.claude_client import (
        generate_json as claude_generate_json,
        is_available as claude_is_available,
    )
except ImportError:
    def claude_generate_json(*a, **kw): return None
    def claude_is_available(): return False

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

# ---------------------------------------------------------------------------
EDITIONS = ["world", "us", "europe", "south-asia"]
WEEK_RECAP_COUNT = 10
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

PROHIBITED_TERMS = frozenset({
    "notable", "notably", "significant", "significantly", "it should be noted",
    "interestingly", "crucially", "it is worth noting", "it's worth noting",
    "it bears mentioning", "noteworthy", "what you need to know",
    "here's what", "here is what", "let's break down", "let's dive",
    "in conclusion", "to summarize", "all things considered",
})

# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------
def _smart_generate(prompt, system_instruction=None, max_output_tokens=8192):
    """Try Claude first, fall back to Gemini. Returns (result_dict, gen_label)."""
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
            count_call=False, max_output_tokens=max_output_tokens,
        )
        if result:
            return result, "gemini-flash"

    return None, "none"


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def _fetch_week_clusters(edition, week_start, week_end):
    """Fetch clusters for the edition within date range, sorted by importance."""
    try:
        result = supabase.table("story_clusters").select(
            "id,title,summary,consensus_points,divergence_points,"
            "category,source_count,headline_rank,divergence_score,bias_diversity,"
            "sections,created_at,first_published,last_updated"
        ).contains("sections", [edition]).gte(
            "created_at", week_start.isoformat()
        ).lte(
            "created_at", week_end.isoformat()
        ).order("headline_rank", desc=True).limit(500).execute()
        return result.data or []
    except Exception as e:
        print(f"  [weekly:{edition}] cluster query failed: {e}")
        return []


def _fetch_bias_stats(edition, week_start, week_end):
    """Aggregate bias stats for the week."""
    try:
        result = supabase.table("bias_scores").select(
            "political_lean,sensationalism,opinion_fact,factual_rigor,framing,confidence"
        ).gte("analyzed_at", week_start.isoformat()).lte(
            "analyzed_at", week_end.isoformat()
        ).limit(3000).execute()

        if not result.data:
            return None

        scores = result.data
        leans = [s["political_lean"] for s in scores if s.get("political_lean") is not None]
        sensations = [s["sensationalism"] for s in scores if s.get("sensationalism") is not None]
        rigors = [s["factual_rigor"] for s in scores if s.get("factual_rigor") is not None]

        return {
            "total_scored": len(scores),
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

COVER_SYSTEM = """You are the lead writer for void --weekly, a magazine-style news digest.
Write in the register of The Economist or The Atlantic: measured, analytical,
mechanism-focused. Juxtapose concrete facts — never assert significance.

For the TIMELINE, extract 5-8 discrete EVENTS that drove this story forward
during the week. Each event should be a concrete action or development — a strike,
a vote, a resignation, a market move, a diplomatic break — not a vague summary.
Include the date and a punchy one-line description.

BANNED: "notable", "significant", "it should be noted", "interestingly",
"crucially", "here's what you need to know", "in conclusion".

You will receive a DATA TIMELINE showing real cluster creation dates and titles.
Use these as the skeleton for your essay. Do NOT invent events not shown.

Output JSON:
{
  "headline": "...",
  "text": "... (800-1200 words, analytical essay structured around the timeline)",
  "numbers": [{"stat": "...", "context": "..."}, ...]
}"""


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
            fp = c.get("first_published") or c.get("created_at")
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
            "tldr_headline,created_at"
        ).eq("edition", edition).gte(
            "created_at", week_start.isoformat()
        ).lte(
            "created_at", week_end.isoformat()
        ).order("created_at", desc=True).execute()
        return result.data or []
    except Exception as e:
        print(f"  [weekly:{edition}] brief signal query failed: {e}")
        return []


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
        related_ctx = "\n".join(
            f"  [{c.get('first_published', '')[:10]}] {c.get('title', '')} "
            f"({c.get('source_count', 0)} sources)"
            for c in thread["clusters"]
        )

        prompt = (
            f"Write a deep-dive cover story for void --weekly ({edition} edition).\n\n"
            f"MAIN STORY: {lead.get('title', 'Untitled')}\n"
            f"Total sources across the week: {thread['cumulative_sources']}\n"
            f"Days active: {thread['daily_appearances']}\n"
            f"Summary: {lead.get('summary', '')}\n"
            f"Key agreements: {json.dumps(lead.get('consensus_points', []))}\n"
            f"Key disagreements: {json.dumps(lead.get('divergence_points', []))}\n\n"
            f"DATA TIMELINE (real dates, real clusters):\n{timeline_ctx}\n\n"
            f"ALL RELATED DEVELOPMENTS:\n{related_ctx}\n\n"
            f"Write an 800-1200 word essay structured around this timeline.\n"
            f"Use these real dates. Do NOT invent events not shown above."
        )

        result, gen = _smart_generate(prompt, system_instruction=COVER_SYSTEM)
        calls += 1
        if result and isinstance(result, dict):
            result["cluster_id"] = lead.get("id")
            result["timeline"] = timeline
            result["thread_cluster_ids"] = [c.get("id") for c in thread["clusters"]]
            covers.append(result)
            print(f"    Cover {i+1}: {result.get('headline', '?')[:60]}... ({len(result.get('text','').split())} words)")
        else:
            # Fallback
            covers.append({
                "headline": cluster.get("title", ""),
                "text": cluster.get("summary", ""),
                "timeline": [],
                "numbers": [],
                "cluster_id": cluster.get("id"),
            })
        time.sleep(3)

    return covers, calls


# ── SECTION 2: THE OPINIONS (5-6 topics × 1 voice each) ──

OPINION_SYSTEM = """You are a {perspective} columnist for void --weekly.
Write a 400-600 word opinion essay. {instruction}

Your essay should:
- Take a clear position informed by {tradition} values
- Use specific facts, names, and numbers from the story
- Acknowledge the strongest counterargument in one sentence
- End with a concrete prediction or recommendation

BANNED: "notable", "significant", "it should be noted", "in conclusion".

Output JSON: {{"headline": "...", "text": "..."}}"""


def _generate_opinions(top_threads, all_threads, edition):
    """Generate 5 opinions: 2 opposing on cover story, 3 on other important topics.

    The reader sees a genuine dialectic on the #1 story (progressive vs conservative)
    plus diverse perspectives on other key stories.
    """
    opinions = []
    calls = 0

    # Build opinion plan: 2 opposing on #1, then 3 on other stories
    plan = []  # list of (cluster_dict, lean_str)

    # First 2: opposing voices on cover story #1
    if top_threads:
        lead = top_threads[0]["lead_cluster"]
        plan.append((lead, "left"))
        plan.append((lead, "right"))

    # Third: center voice on cover story #2
    if len(top_threads) > 1:
        second = top_threads[1]["lead_cluster"]
        plan.append((second, "center"))

    # Remaining: other important threads not in cover
    cover_ids = set()
    for t in top_threads:
        for c in t["clusters"]:
            cover_ids.add(c.get("id"))
    other = [t for t in all_threads if t.get("lead_cluster", {}).get("id") not in cover_ids]
    lean_cycle = ["center-left", "center-right"]
    for i, thread in enumerate(other[:2]):
        plan.append((thread["lead_cluster"], lean_cycle[i % 2]))

    for i, (cluster, lean) in enumerate(plan):
        voice = OPINION_VOICE_CONFIGS.get(lean, OPINION_VOICE_CONFIGS["center"])
        is_paired = i < 2 and len(plan) >= 2
        system = OPINION_SYSTEM.format(**voice)
        if is_paired:
            opposing = "conservative" if lean == "left" else "progressive"
            system += f"\n\nThis is a PAIRED opinion. A {opposing} columnist writes about the same story. Your reader sees both side by side."

        prompt = (
            f"Write a {voice['perspective']} opinion essay for void --weekly ({edition}).\n\n"
            f"Topic: {cluster.get('title', 'Untitled')}\n"
            f"Summary: {cluster.get('summary', '')}\n"
            f"Key points: {json.dumps(cluster.get('consensus_points', []))}\n"
            f"Disagreements: {json.dumps(cluster.get('divergence_points', []))}\n"
        )

        result, gen = _smart_generate(prompt, system_instruction=system, max_output_tokens=4096)
        calls += 1

        if result and isinstance(result, dict):
            result["lean"] = lean
            result["topic"] = cluster.get("title", "")
            result["cluster_id"] = cluster.get("id")
            result["paired"] = is_paired
            opinions.append(result)
            print(f"    Opinion {i+1} ({lean}): {result.get('headline', '?')[:50]}...")
        time.sleep(2)

    return opinions, calls


# ── SECTION 3: TECH BRIEF ──

TECH_SYSTEM = """You are the technology correspondent for void --weekly. Write a
500-700 word analysis of this week's most important technology story.
Focus on mechanism and implication, not hype. Think Ars Technica meets The Economist.

BANNED: "game-changing", "revolutionary", "notable", "significant", "disrupting".

Output JSON: {"headline": "...", "text": "..."}"""


def _generate_tech_brief(clusters, edition):
    """Find the top tech story and write a brief."""
    tech_categories = {"Technology", "Science", "AI", "Cybersecurity", "Space"}
    tech_clusters = [c for c in clusters if c.get("category") in tech_categories]

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
    prompt = (
        f"Write a tech brief for void --weekly ({edition}).\n\n"
        f"Story: {top_tech.get('title', '')}\n"
        f"Summary: {top_tech.get('summary', '')}\n"
        f"Sources: {top_tech.get('source_count', 0)}\n"
    )

    result, gen = _smart_generate(prompt, system_instruction=TECH_SYSTEM, max_output_tokens=4096)
    if result:
        result["cluster_id"] = top_tech.get("id")
    return result, 1


# ── SECTION 4: SPORTS PAGE ──

SPORTS_SYSTEM = """You are the sports-and-culture correspondent for void --weekly.
Write a 400-600 word piece about this week's top sports story — but through the
lens of culture, politics, or economics. Sports as a mirror of society.
Think of how The New Yorker covers sports: the game is the entry point, the
story is about something larger.

Output JSON: {"headline": "...", "text": "..."}"""


def _generate_sports(clusters, edition):
    """Find the top sports story and write a culture piece."""
    sports_clusters = [c for c in clusters if c.get("category") in {"Sports", "Culture"}]

    if not sports_clusters:
        sports_clusters = [
            c for c in clusters
            if any(kw in (c.get("title", "") or "").lower()
                   for kw in ["nba", "nfl", "fifa", "olympic", "world cup", "tennis",
                              "cricket", "formula", "premier league", "champions league",
                              "baseball", "athlete", "stadium", "tournament"])
        ]

    if not sports_clusters:
        return None, 0

    top = sports_clusters[0]
    prompt = (
        f"Write a sports-as-culture piece for void --weekly ({edition}).\n\n"
        f"Story: {top.get('title', '')}\n"
        f"Summary: {top.get('summary', '')}\n"
    )

    result, gen = _smart_generate(prompt, system_instruction=SPORTS_SYSTEM, max_output_tokens=4096)
    if result:
        result["cluster_id"] = top.get("id")
    return result, 1


# ── SECTION 5: BIAS REPORT (rule-based, $0) ──

def _generate_bias_report(clusters, bias_stats, edition):
    """Rule-based bias report from aggregate data."""
    if not clusters or not bias_stats:
        return "Insufficient data for this week's bias report.", {}

    polarized = sorted(clusters, key=lambda c: c.get("divergence_score", 0), reverse=True)[:5]

    lines = [
        f"This week's {edition} edition processed {bias_stats['total_scored']} articles across {len(clusters)} story clusters.",
        "",
        f"Coverage lean: {bias_stats['avg_lean']}/100 "
        f"({'left-of-center' if bias_stats['avg_lean'] < 45 else 'center' if bias_stats['avg_lean'] < 55 else 'right-of-center'}).",
        f"Lean spread: {bias_stats['lean_std']} — "
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
    }


# ── SECTION 6: WEEK IN BRIEF (8-10 additional stories) ──

RECAP_SYSTEM = """You are an editor for void --weekly. Write concise 150-200 word recaps.
Focus on what happened and what it means. Use specific facts.

BANNED: "notable", "significant", "it should be noted", "interestingly".

Output JSON: {"stories": [{"headline": "...", "summary": "..."}]}"""


def _generate_week_recap(clusters, edition, skip_ids=None):
    """Generate recap for remaining stories not covered elsewhere."""
    skip = set(skip_ids or [])
    remaining = [c for c in clusters if c.get("id") not in skip][:WEEK_RECAP_COUNT]

    if not remaining:
        return None, 0

    stories_text = "\n".join(
        f"--- Story {i+1} ---\n"
        f"Title: {c.get('title', '')}\n"
        f"Summary: {(c.get('summary') or '')[:300]}\n"
        f"Category: {c.get('category', 'General')}"
        for i, c in enumerate(remaining)
    )

    prompt = f"Write 150-200 word recaps for these {len(remaining)} stories ({edition} edition):\n\n{stories_text}"
    result, gen = _smart_generate(prompt, system_instruction=RECAP_SYSTEM)
    return result, 1


# ── SECTION 7: AUDIO ──

# ---------------------------------------------------------------------------
# Weekly-specific voice pair — fixed for gravitas and reflective authority.
# The Editor (Sadaltager, knowledgeable) + Correspondent (Charon, informative)
# are the two most authoritative, lowest-tempo voices in the roster. The Editor
# synthesizes and contextualizes (the "step back" voice); the Correspondent
# delivers facts with weight and patience. Together they create the Sunday
# magazine register: unhurried, substantive, the voice of two people who have
# spent the week reading everything so you don't have to.
#
# This pair does NOT rotate. The weekly is a branded product — same hosts
# every Sunday, same sonic signature. Listeners learn to associate these
# two voices with the long-form format.
# ---------------------------------------------------------------------------
WEEKLY_VOICE_PAIR = {
    "host_a": {
        "id": "Sadaltager",
        "name": "The Editor",
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
        "id": "Charon",
        "name": "The Correspondent",
        "key": "correspondent",
        "gender": "male",
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
You are writing void --onair WEEKLY — the Sunday magazine broadcast from void --news. \
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

WRONG (daily-brief pace): A reports 3 sentences. B reacts 2 sentences. Repeat.
RIGHT (magazine pace): A develops a thought across 4-5 sentences, building to \
a point. B responds with a new angle or counter-fact, also developed across \
3-4 sentences. They are two minds working through the material together.

---

STRUCTURE (target: 2500-3000 words total):

1. COLD OPEN (~100 words, ~30 sec)
   A hooks the listener with the week's defining tension in one dramatic sentence.
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

FIRST LINE: A: From void news, this is the weekly for {WEEK_LABEL}.
LAST LINE: A: From void news, this was the weekly. We'll be back next Sunday.

Output JSON: {{"script": "A: ...\\nB: ...\\n\\nA: ..."}}
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
    system = AUDIO_SYSTEM.replace("{WEEK_LABEL}", week_label)

    # --- Assemble the user prompt ---
    prompt = (
        f"Write void --onair WEEKLY for the {edition} edition.\n"
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

    result, gen = _smart_generate(prompt, system_instruction=system, max_output_tokens=8192)
    return result, 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def generate_weekly_digest(editions=None, week_offset=0):
    """Generate weekly digests for all editions."""
    if editions is None:
        editions = EDITIONS

    now = datetime.now(timezone.utc)
    days_since_monday = now.weekday()
    week_end = now - timedelta(days=days_since_monday - 6 + (week_offset * 7))
    week_start = week_end - timedelta(days=6)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_end.replace(hour=23, minute=59, second=59, microsecond=0)

    epoch = datetime(2026, 3, 22, tzinfo=timezone.utc)
    issue_number = max(1, int((week_start - epoch).days / 7) + 1)

    print("=" * 60)
    print(f"void --weekly Issue #{issue_number}")
    print(f"  Week: {week_start.strftime('%b %d')} — {week_end.strftime('%b %d, %Y')}")
    print(f"  Editions: {', '.join(editions)}")
    print("=" * 60)

    for edition in editions:
        t0 = time.time()
        total_calls = 0
        print(f"\n{'─' * 50}")
        print(f"[weekly:{edition}] Issue #{issue_number}")
        print(f"{'─' * 50}")

        # Fetch data
        clusters = _fetch_week_clusters(edition, week_start, week_end)
        print(f"  Clusters: {len(clusters)}")
        if len(clusters) < 3:
            print(f"  Insufficient data — skipping")
            continue

        bias_stats = _fetch_bias_stats(edition, week_start, week_end)
        print(f"  Bias scores: {bias_stats['total_scored'] if bias_stats else 0}")

        # Track used cluster IDs to avoid repetition in recap
        used_ids = set()

        # Link clusters into story threads
        print(f"  Linking story threads...")
        threads = _link_story_threads(clusters)
        print(f"  Threads: {len(threads)} (from {len(clusters)} clusters)")

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

        # Section 2: Opinions (5-6 topics × rotating leans)
        print(f"\n  ── THE OPINIONS ──")
        opinions, calls = _generate_opinions(top_threads, threads, edition)
        total_calls += calls
        for o in opinions:
            if o.get("cluster_id"):
                used_ids.add(o["cluster_id"])

        # Section 3: Tech brief
        print(f"\n  ── TECH BRIEF ──")
        tech, calls = _generate_tech_brief(clusters, edition)
        total_calls += calls
        if tech:
            print(f"    {tech.get('headline', '?')[:60]}")
            if tech.get("cluster_id"):
                used_ids.add(tech["cluster_id"])
        else:
            print(f"    No tech story found")

        # Section 4: Sports
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
        bias_text, bias_data = _generate_bias_report(clusters, bias_stats, edition)

        # Section 6: Week in brief (remaining stories)
        print(f"\n  ── WEEK IN BRIEF ──")
        recap, calls = _generate_week_recap(clusters, edition, skip_ids=used_ids)
        total_calls += calls
        recap_count = len(recap.get("stories", [])) if recap else 0
        print(f"    {recap_count} stories")

        # Section 7: Audio — weekly uses fixed voice pair + richer context
        print(f"\n  ── AUDIO ──")
        audio_result, calls = _generate_audio(
            covers, opinions, tech, sports, recap, bias_data,
            edition, week_start=week_start, week_end=week_end,
        )
        total_calls += calls
        audio_script = audio_result.get("script", "") if audio_result else None

        # Produce audio TTS — weekly uses fixed Editor+Correspondent pair
        audio_url = None
        audio_duration = None
        audio_size = None
        if audio_script and len(audio_script) > 100:
            print(f"    Producing audio ({len(audio_script.split())} words)...")
            try:
                # Weekly uses WEEKLY_VOICE_PAIR (fixed) instead of daily rotation
                # and overrides the TTS preamble for magazine pace
                weekly_voices = {
                    "host_a": WEEKLY_VOICE_PAIR["host_a"],
                    "host_b": WEEKLY_VOICE_PAIR["host_b"],
                    "opinion": {"id": WEEKLY_VOICE_PAIR["host_a"]["id"]},
                }
                # Use "weekly-{edition}" path to avoid overwriting daily audio
                result = produce_audio(
                    audio_script, weekly_voices, f"weekly-{edition}",
                    tts_preamble_override=_WEEKLY_TTS_PREAMBLE,
                )
                if result and isinstance(result, dict):
                    audio_url = result.get("audio_url")
                    audio_duration = result.get("duration_seconds")
                    audio_size = result.get("file_size")
                    print(f"    Audio: {audio_duration:.0f}s uploaded" if audio_duration else "    Audio: uploaded")
            except Exception as e:
                print(f"    [warn] Audio failed: {e}")
        else:
            print(f"    No audio script generated")

        # Store
        elapsed = time.time() - t0
        row = {
            "edition": edition,
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": week_end.strftime("%Y-%m-%d"),
            "issue_number": issue_number,
            # Cover
            "cover_headline": covers[0].get("headline", "") if covers else "",
            "cover_text": json.dumps([{
                "headline": c.get("headline", ""),
                "text": c.get("text", ""),
                "timeline": c.get("timeline", []),
                "numbers": c.get("numbers", []),
                "cluster_id": c.get("cluster_id"),
            } for c in covers]),
            "cover_numbers": json.dumps(covers[0].get("numbers", []) if covers else []),
            "cover_timelines": json.dumps([
                {"story_index": i, "entries": c.get("timeline", [])}
                for i, c in enumerate(covers)
            ]),
            # Recap
            "recap_stories": json.dumps(recap.get("stories", []) if recap else []),
            # Opinions (store as JSONB array instead of separate columns)
            "opinion_left": json.dumps([o for o in opinions if o.get("lean") == "left"]),
            "opinion_center": json.dumps([o for o in opinions if o.get("lean") in ("center", "center-left", "center-right")]),
            "opinion_right": json.dumps([o for o in opinions if o.get("lean") == "right"]),
            "opinion_headlines": json.dumps({o.get("topic", f"topic-{i}"): {"headline": o.get("headline", ""), "lean": o.get("lean", "")} for i, o in enumerate(opinions)}),
            "opinion_topic": ", ".join(o.get("topic", "") for o in opinions[:3]),
            # Bias report
            "bias_report_text": bias_text,
            "bias_report_data": json.dumps(bias_data),
            # Tech + Sports (store in cover_text JSON alongside covers)
            # Audio (fixed weekly pair: Editor + Correspondent)
            "audio_script": audio_script,
            "audio_url": audio_url,
            "audio_duration_seconds": audio_duration,
            "audio_file_size": audio_size,
            # Stats
            "total_articles": sum(c.get("source_count", 0) for c in clusters),
            "total_clusters": len(clusters),
            "generator": "gemini-flash",
            "gemini_calls_used": total_calls,
            "generation_duration_seconds": round(elapsed, 1),
        }

        recap_data = recap.get("stories", []) if recap else []
        row["recap_stories"] = json.dumps(recap_data)

        try:
            supabase.table("weekly_digests").upsert(
                row, on_conflict="edition,week_start"
            ).execute()
            print(f"\n  ✓ Issue #{issue_number} stored ({total_calls} calls, {elapsed:.0f}s)")
        except Exception as e:
            print(f"\n  ✗ Storage failed: {e}")

    print(f"\n{'=' * 60}")
    print(f"void --weekly complete.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="void --weekly digest generator")
    parser.add_argument("--editions", type=str, default="", help="Comma-separated editions")
    parser.add_argument("--week-offset", type=int, default=0, help="0=current, -1=last week")
    args = parser.parse_args()

    editions = [e.strip() for e in args.editions.split(",") if e.strip()] if args.editions else None
    generate_weekly_digest(editions=editions, week_offset=args.week_offset)
