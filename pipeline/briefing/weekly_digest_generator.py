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


def _generate_opinions(clusters, edition):
    """Generate 5-6 opinion pieces, one lean per topic, cycling voices."""
    opinions = []
    calls = 0

    # Select diverse clusters for opinions (skip the 2 cover stories)
    opinion_clusters = clusters[COVER_STORIES:COVER_STORIES + OPINION_COUNT]
    if len(opinion_clusters) < OPINION_COUNT:
        opinion_clusters = clusters[:OPINION_COUNT]

    for i, cluster in enumerate(opinion_clusters):
        lean = OPINION_LEANS[i % len(OPINION_LEANS)]
        voice = OPINION_VOICE_CONFIGS[lean]
        system = OPINION_SYSTEM.format(**voice)

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
            result["cluster_id"] = lead.get("id")
            result["timeline"] = timeline
            result["thread_cluster_ids"] = [c.get("id") for c in thread["clusters"]]
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

AUDIO_SYSTEM = """You are writing void --onair WEEKLY, a 15-minute magazine-pace
Sunday broadcast. Two hosts: A (anchor) and B (analyst). Reflective, analytical tone.

Format: A: and B: tags only. NO [MUSIC], NO stage directions, NO segment markers.

Structure:
1. A opens the week (30 sec)
2. Cover stories: A and B discuss the 2 top stories in depth (7 min)
3. Opinions spotlight: A shares one striking opinion excerpt, B reacts (2 min)
4. Tech + Sports: Quick hits (2 min)
5. Week recap: A runs through 4-5 key stories (3 min)
6. B closes with a forward look, A signs off (30 sec)

Output JSON: {"script": "A: ...\\n\\nB: ..."}
Target: 2500-3000 words (~15 min at broadcast pace)."""


def _generate_audio(covers, opinions, tech, sports, recap, edition):
    """Generate the weekly audio broadcast script."""
    cover_context = "\n".join(
        f"Cover {i+1}: {c.get('headline', '?')}\n{c.get('text', '')[:600]}"
        for i, c in enumerate(covers)
    )
    opinion_context = "\n".join(
        f"Opinion ({o.get('lean', '?')} on {o.get('topic', '?')}): {o.get('text', '')[:200]}..."
        for o in (opinions or [])[:3]
    )
    tech_context = f"Tech: {tech.get('headline', '?')}\n{tech.get('text', '')[:200]}" if tech else ""
    sports_context = f"Sports: {sports.get('headline', '?')}\n{sports.get('text', '')[:200]}" if sports else ""

    prompt = (
        f"Write void --onair WEEKLY for the {edition} edition.\n\n"
        f"COVER STORIES:\n{cover_context}\n\n"
        f"OPINIONS:\n{opinion_context}\n\n"
        f"{tech_context}\n{sports_context}\n\n"
        f"Generate a 2500-3000 word script."
    )

    result, gen = _smart_generate(prompt, system_instruction=AUDIO_SYSTEM, max_output_tokens=8192)
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

        # Section 7: Audio
        print(f"\n  ── AUDIO ──")
        audio_result, calls = _generate_audio(covers, opinions, None, None, recap, edition)
        total_calls += calls
        audio_script = audio_result.get("script", "") if audio_result else None

        # Produce audio TTS
        audio_url = None
        audio_duration = None
        if audio_script and len(audio_script) > 100:
            print(f"    Producing audio ({len(audio_script.split())} words)...")
            try:
                voices = get_voices_for_today(edition)
                result = produce_audio(audio_script, voices, edition)
                if result and isinstance(result, dict):
                    audio_url = result.get("audio_url")
                    audio_duration = result.get("audio_duration_seconds")
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
            # Audio
            "audio_script": audio_script,
            "audio_url": audio_url,
            "audio_duration_seconds": audio_duration,
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
