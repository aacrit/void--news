"""
Re-rank existing clusters using the v4.0 ranking engine.

Reads clusters + articles + bias scores from Supabase, runs rank_importance()
on each, and writes back updated headline_rank + divergence_score +
coverage_velocity. Skips fetch/scrape/analyze — just re-scores.

Usage:
    python pipeline/rerank.py           # re-rank all clusters
    python pipeline/rerank.py --dry-run # show scores without writing
"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Add pipeline root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.supabase_client import supabase
from ranker.importance_ranker import rank_importance
from categorizer.auto_categorize import categorize_article, map_to_desk

SOURCES_PATH = Path(__file__).parent.parent / "data" / "sources.json"
DRY_RUN = "--dry-run" in sys.argv


def _get_section(cluster_id: str, clusters: list[dict]) -> str:
    """Look up the primary section (world/us) for a cluster by ID."""
    for c in clusters:
        if c["id"] == cluster_id:
            return c.get("section", "world")
    return "world"


def _cluster_in_section(cluster_id: str, clusters: list[dict], section: str) -> bool:
    """Check if a cluster belongs to a section via sections[] array.
    This matches the frontend query logic (.contains("sections", [section]))
    so that ranking pools see the same stories the user sees."""
    for c in clusters:
        if c["id"] == cluster_id:
            sections = c.get("sections") or [c.get("section", "world")]
            return section in sections
    return section == "world"


def _get_cluster_tier_info(articles: list[dict], sources: list[dict]) -> dict:
    """Get tier breakdown and independent factual rigor for lead gate exemptions."""
    source_map = {}
    for s in sources:
        if s.get("db_id"):
            source_map[s["db_id"]] = s
        if s.get("id"):
            source_map[s["id"]] = s

    tiers = set()
    for a in articles:
        sid = a.get("source_id", "")
        src = source_map.get(sid, {})
        tier = src.get("tier", "")
        if tier:
            tiers.add(tier)

    return {"tiers": tiers}


def load_sources() -> list[dict]:
    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def sync_source_ids(sources: list[dict]) -> list[dict]:
    """Fetch DB UUIDs for all sources so the ranker can resolve source_id lookups."""
    result = supabase.table("sources").select("id,slug,tier,political_lean_baseline").execute()
    db_map = {r["slug"]: r for r in (result.data or [])}
    for s in sources:
        slug = s.get("id", "")
        db_row = db_map.get(slug)
        if db_row:
            s["db_id"] = db_row["id"]
    return sources


def main():
    start = time.time()
    print("=" * 60)
    print(f"void --news re-ranker v5.7 {'(DRY RUN)' if DRY_RUN else ''}")
    print("=" * 60)

    # 1. Load sources with DB IDs
    print("\n[1/4] Loading sources...")
    sources = load_sources()
    sources = sync_source_ids(sources)
    matched = sum(1 for s in sources if s.get("db_id"))
    print(f"  {len(sources)} sources loaded, {matched} matched to DB")

    # 2. Fetch all clusters
    print("\n[2/4] Fetching clusters from Supabase...")
    # Try fetching with v5.0 editorial columns; fall back without them
    try:
        clusters_res = supabase.table("story_clusters").select(
            "id,title,category,section,sections,content_type,headline_rank,source_count,"
            "editorial_importance,story_type"
        ).execute()
    except Exception:
        # editorial columns may not exist yet (migration 013 not applied)
        clusters_res = supabase.table("story_clusters").select(
            "id,title,category,section,sections,content_type,headline_rank,source_count"
        ).execute()
    clusters = clusters_res.data or []
    print(f"  {len(clusters)} clusters found")

    if not clusters:
        print("No clusters to re-rank.")
        return

    # 3. Bulk-fetch all cluster_articles, articles, and bias_scores upfront.
    # Previously: 3 queries per cluster = 25,941 HTTP calls for 8,647 clusters.
    # Now: 3 paginated bulk fetches + in-memory dicts = ~30 HTTP calls total.
    print("\n[3/4] Bulk-fetching cluster data...")

    def _paginated_fetch(table: str, select: str, page_size: int = 500) -> list[dict]:
        """Fetch all rows with pagination and retry on connection drops."""
        all_rows: list[dict] = []
        offset = 0
        retries = 0
        while True:
            try:
                res = supabase.table(table).select(select).range(
                    offset, offset + page_size - 1
                ).execute()
                retries = 0
            except Exception as e:
                retries += 1
                if retries <= 3:
                    print(f"  [retry {retries}/3] {table} offset {offset}: {type(e).__name__}")
                    time.sleep(2)
                    continue
                print(f"  [err] {table} failed after 3 retries at offset {offset}")
                break
            if not res.data:
                break
            all_rows.extend(res.data)
            if len(res.data) < page_size:
                break
            offset += page_size
        return all_rows

    # 3a. Fetch all cluster_articles rows
    ca_rows = _paginated_fetch("cluster_articles", "cluster_id,article_id")
    cluster_article_map: dict[str, list[str]] = {}
    for row in ca_rows:
        cluster_article_map.setdefault(row["cluster_id"], []).append(row["article_id"])
    print(f"  cluster_articles: {len(ca_rows)} rows covering {len(cluster_article_map)} clusters")

    # 3b. Fetch all articles
    art_rows = _paginated_fetch("articles",
        "id,source_id,title,summary,full_text,published_at,word_count")
    articles_by_id: dict[str, dict] = {r["id"]: r for r in art_rows}
    print(f"  articles: {len(articles_by_id)} rows fetched")

    # 3c. Fetch all bias_scores
    bs_rows = _paginated_fetch("bias_scores",
        "article_id,political_lean,sensationalism,opinion_fact,factual_rigor,framing,confidence")
    bias_by_article_id: dict[str, dict] = {r["article_id"]: r for r in bs_rows}
    print(f"  bias_scores: {len(bias_by_article_id)} rows fetched")

    # 3d. Re-rank each cluster using in-memory data (no per-cluster DB queries)
    print("\n  Re-ranking clusters in memory...")
    updates = []
    errors = 0

    for i, cluster in enumerate(clusters):
        cid = cluster["id"]

        article_ids = cluster_article_map.get(cid, [])
        if not article_ids:
            continue

        articles = [articles_by_id[aid] for aid in article_ids if aid in articles_by_id]
        if not articles:
            continue

        bias_scores = [bias_by_article_id[aid] for aid in article_ids if aid in bias_by_article_id]

        # Map articles for ranker (add published_at key it expects)
        for art in articles:
            art["published_at"] = art.get("published_at", "")

        # Compute cluster confidence (p25)
        conf_values = sorted(
            bs.get("confidence", 0.5) for bs in bias_scores
        )
        if conf_values:
            p25_idx = max(0, len(conf_values) // 4)
            cluster_confidence = conf_values[p25_idx]
        else:
            cluster_confidence = 0.5

        # Classify content type
        if bias_scores:
            avg_opinion = sum(
                (bs.get("opinion_fact") or 25) for bs in bias_scores
            ) / len(bias_scores)
        else:
            avg_opinion = 25.0
        content_type = "opinion" if avg_opinion > 50 else "reporting"

        # Re-categorize using up to 3 articles
        try:
            cat_votes: dict[str, int] = {}
            for art in articles[:3]:
                for cat in categorize_article(art):
                    cat_votes[cat] = cat_votes.get(cat, 0) + 1
            best_cat = max(cat_votes, key=cat_votes.get) if cat_votes else "politics"
            category = map_to_desk(best_cat)
        except Exception:
            category = cluster.get("category", "politics")

        # Read editorial intelligence from DB (Gemini-generated, may be NULL)
        editorial_importance = cluster.get("editorial_importance")
        story_type = cluster.get("story_type")

        # Run v5.1 ranker — pass sections for US-only divergence damper
        cluster_sections = cluster.get("sections") or [cluster.get("section", "world")]
        try:
            result = rank_importance(
                articles, sources, bias_scores,
                cluster_confidence=cluster_confidence,
                category=category,
                editorial_importance=editorial_importance,
                sections=cluster_sections,
            )
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  [err] Cluster {cid[:8]}: {e}")
            continue

        # Story-type gates (v5.0): demote incremental updates and ceremonial
        if story_type == "incremental_update":
            result["headline_rank"] *= 0.75
            result["importance_score"] = result["headline_rank"]
        elif story_type == "ceremonial":
            result["headline_rank"] *= 0.82
            result["importance_score"] = result["headline_rank"]

        old_rank = cluster.get("headline_rank") or 0
        new_rank = result["headline_rank"]

        source_count = len({a["source_id"] for a in articles if a.get("source_id")})
        updates.append({
            "id": cid,
            "headline_rank": new_rank,
            "importance_score": result["importance_score"],
            "divergence_score": result["divergence_score"],
            "coverage_velocity": result["coverage_velocity"],
            "content_type": content_type,
            "category": category,
            "source_count": source_count,
            "_articles": articles,
            "_bias_scores": bias_scores,
        })

        # Progress
        if (i + 1) % 25 == 0 or i == len(clusters) - 1:
            print(f"  [{i+1}/{len(clusters)}] "
                  f"last: \"{cluster['title'][:50]}\" "
                  f"{old_rank:.1f} -> {new_rank:.1f}")

    print(f"\n  Scored {len(updates)} clusters, {errors} errors")

    # Per-section lead gate + topic diversity (v4.0)
    # Both gates run PER SECTION so each section's top 10 is independently curated.
    LEAD_MIN_SOURCES = 3
    LEAD_SLOTS = 10
    _SOFT_CATS = {"sports", "entertainment", "culture", "lifestyle",
                  "celebrity", "music", "film", "television", "gaming"}
    MAX_SAME_CAT_DEFAULT = 2
    MAX_SAME_CAT_SOFT = 1
    TOP_N = 10

    updates.sort(key=lambda u: u["headline_rank"], reverse=True)

    for section_val in ("world", "us", "europe", "south-asia"):
        pool = [u for u in updates if _cluster_in_section(u["id"], clusters, section_val)]
        if not pool:
            continue

        # --- Lead gate: top LEAD_SLOTS positions require 3+ sources ---
        # Exception: independent-tier stories with factual_rigor > 70
        # Strategy: separate eligible vs ineligible, rebuild the pool
        # with eligible stories first (up to LEAD_SLOTS), then backfill.
        def _is_lead_exempt(u: dict) -> bool:
            """Check if a low-source story qualifies for lead gate exemption."""
            tier_info = _get_cluster_tier_info(u.get("_articles", []), sources)
            avg_rigor = 0.0
            bs_list = u.get("_bias_scores", [])
            if bs_list:
                rigor_vals = [bs.get("factual_rigor", 0) for bs in bs_list if bs.get("factual_rigor") is not None]
                avg_rigor = sum(rigor_vals) / len(rigor_vals) if rigor_vals else 0.0
            return "independent" in tier_info["tiers"] and avg_rigor > 70

        lead_eligible = []
        lead_deferred = []
        for u in pool:
            if u["source_count"] >= LEAD_MIN_SOURCES or _is_lead_exempt(u):
                lead_eligible.append(u)
            else:
                lead_deferred.append(u)

        # Rebuild: eligible stories fill the top, ineligible go after
        if lead_eligible and lead_deferred:
            new_pool = lead_eligible[:LEAD_SLOTS]
            # Backfill remaining slots with deferred if not enough eligible
            remaining_eligible = lead_eligible[LEAD_SLOTS:]
            # Merge remaining eligible + deferred by score
            overflow = remaining_eligible + lead_deferred
            overflow.sort(key=lambda u: u["headline_rank"], reverse=True)
            new_pool.extend(overflow)
            demoted = len(pool) - len(new_pool)  # should be 0
            if len(new_pool) == len(pool):
                pool[:] = new_pool
                print(f"  Lead gate ({section_val}): enforced 3+ sources in top-{LEAD_SLOTS} ({len(lead_deferred)} stories deferred)")

        # --- Same-event cap (v5.1, strengthened v5.6) ---
        # Detects event clusters by keyword overlap in titles.
        # "Iran war" stories all share keywords like iran/tehran/hormuz.
        # v5.6: Reduced from 3 to 2 in top pool. Deferred stories get
        # 0.92x rank decay so they don't cluster at positions 11-20
        # (benchmark found 11/20 world stories were Iran variants).
        MAX_SAME_EVENT = 2
        EVENT_DECAY = 0.92  # rank multiplier for deferred same-event stories
        _EVENT_KEYWORDS = {
            "iran": {"iran", "iranian", "tehran", "hormuz", "persian gulf", "irgc", "hegseth", "isfahan"},
            "ukraine": {"ukraine", "ukrainian", "kyiv", "zelenskyy", "zelensky", "donbas", "crimea"},
            "israel_palestine": {"gaza", "hamas", "west bank", "netanyahu", "idf", "hezbollah"},
            "china_taiwan": {"taiwan", "taipei", "strait", "xi jinping", "pla"},
            "us_scotus": {"supreme court", "scotus", "constitutional"},
        }

        def _detect_event(title: str) -> str | None:
            """Return event key if title matches a known event, else None."""
            t = title.lower()
            for event_key, keywords in _EVENT_KEYWORDS.items():
                if any(kw in t for kw in keywords):
                    return event_key
            return None

        if len(pool) > TOP_N:
            event_counts: dict[str, int] = {}
            event_promoted: list[dict] = []
            event_deferred: list[dict] = []

            for u in pool:
                title = next((c["title"] for c in clusters if c["id"] == u["id"]), "")
                event = _detect_event(title)
                if event and event_counts.get(event, 0) >= MAX_SAME_EVENT:
                    event_deferred.append(u)
                else:
                    event_promoted.append(u)
                    if event:
                        event_counts[event] = event_counts.get(event, 0) + 1

            # v5.6: Apply rank decay to deferred same-event stories.
            # Without decay, deferred stories keep their original rank and
            # cluster at positions 11-20 (e.g., 8 Iran stories in a row).
            # Each deferred story gets 0.92x, making them spread out and
            # allowing non-event stories to interleave naturally.
            for u in event_deferred:
                u["headline_rank"] = round(u["headline_rank"] * EVENT_DECAY, 2)

            # Merge: promoted first, deferred after
            pool[:] = event_promoted + event_deferred

            event_demoted = len(event_deferred)
            if event_demoted:
                print(f"  Event diversity ({section_val}): demoted {event_demoted} stories exceeding same-event cap (max {MAX_SAME_EVENT})")

        # --- Topic diversity: soft-news max 1 slot, others max 2 ---
        if len(pool) > TOP_N:
            promoted: list[dict] = []
            deferred: list[dict] = []
            cat_counts: dict[str, int] = {}

            for u in pool:
                if len(promoted) >= TOP_N:
                    deferred.append(u)
                    continue
                cat = u.get("category", "general")
                cat_limit = MAX_SAME_CAT_SOFT if cat in _SOFT_CATS else MAX_SAME_CAT_DEFAULT
                if cat_counts.get(cat, 0) < cat_limit:
                    promoted.append(u)
                    cat_counts[cat] = cat_counts.get(cat, 0) + 1
                else:
                    deferred.append(u)

            while len(promoted) < TOP_N and deferred:
                promoted.append(deferred.pop(0))

            final_order = promoted + deferred
            if final_order and len(promoted) >= 2:
                # Use 0.1pt spacing: enough to avoid false ties (0.01 made
                # 22src Paris bomb = 6src strike) without distorting ranks
                # (0.5 pushed a 57pt airstrike down to 48.5).
                for j in range(1, len(promoted)):
                    if promoted[j]["headline_rank"] >= promoted[j-1]["headline_rank"]:
                        promoted[j]["headline_rank"] = round(promoted[j-1]["headline_rank"] - 0.1, 2)

            demoted_count = sum(1 for d in deferred if d not in pool[TOP_N:])
            if demoted_count:
                print(f"  Topic diversity ({section_val}): demoted {demoted_count} stories exceeding category cap")

    updates.sort(key=lambda u: u["headline_rank"], reverse=True)

    # --- Per-edition rank computation (v5.7 — edition-unique) ---
    # Mirrors main.py's v5.7 logic. Regional affinity computed from source
    # country since DB-fetched articles don't carry the section field.
    #
    # Three mechanisms:
    # 1. Regional affinity boost (up to 1.50x per source-country match)
    # 2. Local-priority boost (1.40x exclusive, 1.15x cross-listed)
    # 3. Cross-edition demotion (0.70x, milder 0.88x for global events)
    # Processing order: regional first, world last.

    _COUNTRY_EDITION = {
        "US": "us",
        "IN": "south-asia", "PK": "south-asia", "BD": "south-asia",
        "LK": "south-asia", "NP": "south-asia", "AF": "south-asia",
        "MV": "south-asia", "BT": "south-asia",
        "GB": "europe", "UK": "europe",
        "FR": "europe", "DE": "europe", "ES": "europe", "IT": "europe",
        "NL": "europe", "BE": "europe", "PT": "europe", "AT": "europe",
        "CH": "europe", "IE": "europe", "SE": "europe", "DK": "europe",
        "NO": "europe", "FI": "europe", "IS": "europe",
        "PL": "europe", "CZ": "europe", "RO": "europe", "BG": "europe",
        "HR": "europe", "RS": "europe", "GR": "europe", "HU": "europe",
        "EE": "europe", "LV": "europe", "LT": "europe",
        "UA": "europe", "GE": "europe",
    }

    # Build source_id → edition lookup from sources list
    _src_edition: dict[str, str] = {}
    for s in sources:
        country = (s.get("country", "") or "").upper()
        ed_val = _COUNTRY_EDITION.get(country, "world")
        db_id = s.get("db_id", "")
        slug = s.get("id", "")
        if db_id:
            _src_edition[db_id] = ed_val
        if slug:
            _src_edition[slug] = ed_val

    # Build cluster_id → sections lookup for efficiency
    _cluster_sections: dict[str, list[str]] = {}
    for c in clusters:
        _cluster_sections[c["id"]] = c.get("sections") or [c.get("section", "world")]

    CROSS_EDITION_TOP = 8
    CROSS_DEMOTION = 0.70
    GLOBAL_SIG_DEMOTION = 0.88
    GLOBAL_SIG_SOURCES = 20
    GLOBAL_SIG_EDITIONS = 3
    LOCAL_EXCLUSIVE_BOOST = 1.40
    LOCAL_CROSSLIST_BOOST = 1.0   # no boost for cross-listed; affinity handles it
    AFFINITY_MAX_BOOST = 1.5     # max boost at 100% regional sources (v5.8: capped from 2.0)
    WORLD_MULTI_ED_BOOST = 1.12
    EDITIONS = ["us", "europe", "south-asia", "world"]  # regional first!

    # Store base importance for each update
    for u in updates:
        if "base_rank" not in u:
            u["base_rank"] = u["importance_score"]

    # Initialize edition ranks from base
    for u in updates:
        for ed in EDITIONS:
            u[f"rank_{ed}"] = u["base_rank"]

    # Apply regional affinity + local-priority boost
    for u in updates:
        c_sections = _cluster_sections.get(u["id"], ["world"])
        articles = u.get("_articles", [])

        for ed in ("us", "europe", "south-asia"):
            if ed not in c_sections:
                continue

            # Regional affinity: % of articles from this edition's sources
            if articles:
                regional_count = sum(
                    1 for a in articles
                    if _src_edition.get(a.get("source_id", ""), "world") == ed
                )
                total = len(articles)
                if total > 0:
                    affinity = regional_count / total

                    # LOW-AFFINITY DEMOTION: if <10% of articles are from this
                    # region, the story is a stray (e.g., White Sox in South Asia
                    # because one Pakistani wire picked it up). Demote 0.65x.
                    if affinity < 0.10 and regional_count <= 1:
                        u[f"rank_{ed}"] = round(u[f"rank_{ed}"] * 0.65, 2)
                    else:
                        affinity_mult = 1.0 + (AFFINITY_MAX_BOOST - 1.0) * affinity
                        # Quality cap: proportional to source count.
                        # Full boost only at 10+ sources.
                        _sc = u.get("source_count", 0)
                        if _sc < 10:
                            _cap = 1.0 + (_sc / 10.0) * (AFFINITY_MAX_BOOST - 1.0)
                            affinity_mult = min(affinity_mult, _cap)
                        u[f"rank_{ed}"] = round(u[f"rank_{ed}"] * affinity_mult, 2)

            # Local-priority boost — only for clusters with 8+ sources.
            # Prevents thin regional stories from outranking major global stories.
            _sc = u.get("source_count", 0)
            if "world" not in c_sections and _sc >= 8:
                u[f"rank_{ed}"] = round(u[f"rank_{ed}"] * LOCAL_EXCLUSIVE_BOOST, 2)
            elif "world" not in c_sections:
                pass  # no boost for thin edition-exclusive clusters
            else:
                u[f"rank_{ed}"] = round(u[f"rank_{ed}"] * LOCAL_CROSSLIST_BOOST, 2)

    # World edition: boost truly global stories (3+ editions)
    for u in updates:
        c_sections = _cluster_sections.get(u["id"], ["world"])
        if "world" in c_sections:
            edition_count = sum(1 for ed in EDITIONS if ed in c_sections)
            if edition_count >= 3:
                u["rank_world"] = round(u["rank_world"] * WORLD_MULTI_ED_BOOST, 2)

    # Cross-edition demotion: regional first, world last
    claimed_ids: set[str] = set()
    for ed in EDITIONS:
        pool = [u for u in updates if _cluster_in_section(u["id"], clusters, ed)]

        for u in pool:
            if u["id"] in claimed_ids:
                c_sections = _cluster_sections.get(u["id"], ["world"])
                edition_count = sum(1 for e in EDITIONS if e in c_sections)
                src_count = u.get("source_count", 0)

                if src_count >= GLOBAL_SIG_SOURCES and edition_count >= GLOBAL_SIG_EDITIONS:
                    u[f"rank_{ed}"] = round(u[f"rank_{ed}"] * GLOBAL_SIG_DEMOTION, 2)
                else:
                    u[f"rank_{ed}"] = round(u[f"rank_{ed}"] * CROSS_DEMOTION, 2)

        pool.sort(key=lambda u: u.get(f"rank_{ed}", 0), reverse=True)

        # Edition-level lead gate: ALWAYS push thin clusters (< 5 sources)
        # below all quality clusters. No exceptions — a 3-source story should
        # never outrank a 20-source story regardless of affinity boosts.
        _ED_LEAD_MIN = 5
        eligible = [u for u in pool if u.get("source_count", 0) >= _ED_LEAD_MIN]
        ineligible = [u for u in pool if u.get("source_count", 0) < _ED_LEAD_MIN]
        if eligible and ineligible:
            # Floor = lowest eligible rank minus 0.1
            floor_rank = eligible[-1].get(f"rank_{ed}", 0) - 0.1
            for u in ineligible:
                if u.get(f"rank_{ed}", 0) > floor_rank:
                    u[f"rank_{ed}"] = round(floor_rank, 2)
                    floor_rank -= 0.1
        # Reconstruct pool: all eligible first, then ineligible
        pool[:] = eligible + sorted(ineligible, key=lambda u: u.get(f"rank_{ed}", 0), reverse=True)

        # Thin-edition backfill (v5.8): when a regional edition has
        # fewer than 10 stories with headline_rank >= 40, backfill from
        # world pool. BBC principle: thin desk imports from global.
        _QUALITY_FLOOR = 40.0
        _BACKFILL_TARGET = 10
        if ed != "world":
            quality_count = sum(
                1 for u in pool[:_BACKFILL_TARGET]
                if u.get("headline_rank", 0) >= _QUALITY_FLOOR
            )
            if quality_count < _BACKFILL_TARGET:
                pool_ids = {u["id"] for u in pool}
                world_pool = [
                    u for u in updates
                    if _cluster_in_section(u["id"], clusters, "world")
                    and u["id"] not in pool_ids
                    and u.get("headline_rank", 0) >= _QUALITY_FLOOR
                    and u.get("source_count", 0) >= 5
                ]
                world_pool.sort(key=lambda u: u.get("headline_rank", 0), reverse=True)
                backfill_needed = _BACKFILL_TARGET - quality_count
                for wu in world_pool[:backfill_needed]:
                    wu[f"rank_{ed}"] = wu.get("headline_rank", 0)
                    pool.append(wu)
                pool.sort(key=lambda u: u.get(f"rank_{ed}", 0), reverse=True)
                if world_pool[:backfill_needed]:
                    print(f"  Thin-edition backfill ({ed}): imported {min(backfill_needed, len(world_pool))} world stories")

        for u in pool[:CROSS_EDITION_TOP]:
            claimed_ids.add(u["id"])

    # Report overlap
    _section_top: dict[str, list[str]] = {}
    for ed in EDITIONS:
        pool = [u for u in updates if _cluster_in_section(u["id"], clusters, ed)]
        pool.sort(key=lambda u: u.get(f"rank_{ed}", 0), reverse=True)
        _section_top[ed] = [u["id"] for u in pool[:10]]

    def _overlap(a: str, b: str, n: int) -> int:
        return len(set(_section_top.get(a, [])[:n]) & set(_section_top.get(b, [])[:n]))

    print(f"\n  Edition-unique ranks (v5.7).")
    print(f"  Top-5 overlap: world/us={_overlap('world','us',5)}, "
          f"world/eu={_overlap('world','europe',5)}, "
          f"world/sa={_overlap('world','south-asia',5)}, "
          f"us/eu={_overlap('us','europe',5)}, "
          f"us/sa={_overlap('us','south-asia',5)}, "
          f"eu/sa={_overlap('europe','south-asia',5)}")

    updates.sort(key=lambda u: u["headline_rank"], reverse=True)

    # Print top 15 per edition
    for ed in EDITIONS:
        pool = [u for u in updates if _cluster_in_section(u["id"], clusters, ed)]
        pool.sort(key=lambda u: u.get(f"rank_{ed}", 0), reverse=True)
        print(f"\n  --- Top 15 {ed.upper()} by rank_{ed} ---")
        for j, u in enumerate(pool[:15]):
            title = next(
                (c["title"] for c in clusters if c["id"] == u["id"]), "?"
            )[:60]
            print(f"  {j+1:2}. [{u.get(f'rank_{ed}', 0):5.1f}] {u['source_count']:2}src {u['category']:12} {title}")

    if DRY_RUN:
        print(f"\n  DRY RUN — no writes. Re-run without --dry-run to apply.")
        return

    # 4. Write back to Supabase in batches (16 concurrent workers).
    print(f"\n[4/4] Writing {len(updates)} updates to Supabase (batched, 16 workers)...")
    write_rows = [
        {
            "id": u["id"],
            "headline_rank": u["headline_rank"],
            "importance_score": u["importance_score"],
            "divergence_score": u["divergence_score"],
            "coverage_velocity": u["coverage_velocity"],
            "content_type": u["content_type"],
            "category": u["category"],
            "source_count": u["source_count"],
            "rank_world": u.get("rank_world", u["headline_rank"]),
            "rank_us": u.get("rank_us", u["headline_rank"]),
            "rank_europe": u.get("rank_europe", u["headline_rank"]),
            # Edition name "south-asia" (hyphen) → DB column "rank_south_asia" (underscore)
            "rank_south_asia": u.get("rank_south-asia", u["headline_rank"]),
        }
        for u in updates
    ]

    WRITE_CHUNK = 100
    write_chunks = [
        write_rows[i:i + WRITE_CHUNK]
        for i in range(0, len(write_rows), WRITE_CHUNK)
    ]

    written = 0
    write_errors = 0

    def _write_chunk(chunk: list[dict]) -> int:
        ok = 0
        for row in chunk:
            rid = row.pop("id")
            try:
                supabase.table("story_clusters").update(row).eq("id", rid).execute()
                ok += 1
            except Exception as e:
                if ok == 0:  # only log first error per chunk to avoid spam
                    print(f"  [err] Write failed for {rid[:8]}: {e}")
            finally:
                row["id"] = rid  # restore for any retry logic
        return ok

    with ThreadPoolExecutor(max_workers=16) as write_exec:
        write_futures = [write_exec.submit(_write_chunk, chunk) for chunk in write_chunks]
        for future in as_completed(write_futures):
            try:
                written += future.result()
            except Exception:
                write_errors += WRITE_CHUNK

    elapsed = time.time() - start
    print(f"\n  Done. {written} clusters re-ranked in {elapsed:.1f}s"
          + (f" ({write_errors} write errors)" if write_errors else ""))
    print("  Refresh the frontend to see new rankings.")


if __name__ == "__main__":
    main()
