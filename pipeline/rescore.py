"""
Re-score existing articles using all 5 bias analyzers.

Reads articles from Supabase, runs the full bias analysis pipeline on each,
and writes updated scores back — without running fetch, scrape, or cluster steps.

Usage:
    python pipeline/rescore.py                    # Rescore ALL articles
    python pipeline/rescore.py --limit 500        # First 500 articles
    python pipeline/rescore.py --offset 200       # Skip first 200
    python pipeline/rescore.py --source ap-news   # Only AP articles
    python pipeline/rescore.py --dry-run          # Preview, no writes
    python pipeline/rescore.py --gemini           # Also run Gemini reasoning on clusters

Performance: ~200 articles/minute with spaCy (NER is the bottleneck).
"""

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

# Add pipeline root to sys.path so relative imports work
sys.path.insert(0, str(Path(__file__).parent))

from utils.supabase_client import supabase

# ---------------------------------------------------------------------------
# Analyzer imports (mirrors main.py step 5)
# ---------------------------------------------------------------------------
try:
    from analyzers.political_lean import analyze_political_lean
    from analyzers.sensationalism import analyze_sensationalism
    from analyzers.opinion_detector import analyze_opinion
    from analyzers.factual_rigor import analyze_factual_rigor
    from analyzers.framing import analyze_framing
    ANALYSIS_AVAILABLE = True
except ImportError as _err:
    print(f"[fatal] Could not import analyzers: {_err}")
    print("        Is spaCy / TextBlob / NLTK installed?  pip install -r pipeline/requirements.txt")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Confidence formula (verbatim copy from main.py so rescore stays consistent)
# ---------------------------------------------------------------------------

def compute_confidence(article: dict, scores: dict) -> float:
    """
    Compute per-article analysis confidence based on text quality and signal
    strength.  Identical formula to main.py compute_confidence().

    Factors:
        - Word count:       short articles have less signal      (30%)
        - Text availability: no full text = very low confidence  (30%)
        - Signal variance:  scores near defaults = low confidence (40%)
    """
    word_count = article.get("word_count", 0) or 0
    full_text = article.get("full_text", "") or ""

    length_conf = min(1.0, word_count / 500.0) if word_count > 0 else 0.1
    text_conf = min(1.0, max(0.1, len(full_text) / 1000.0)) if full_text else 0.1

    defaults = {
        "political_lean": 50, "sensationalism": 10,
        "opinion_fact": 25, "factual_rigor": 50, "framing": 15,
    }
    deviations = 0
    for key, default_val in defaults.items():
        actual = scores.get(key, default_val)
        if abs(actual - default_val) > 5:
            deviations += 1
    signal_conf = 0.3 + (deviations / 5.0) * 0.7

    confidence = (length_conf * 0.30) + (text_conf * 0.30) + (signal_conf * 0.40)
    return round(max(0.1, min(1.0, confidence)), 2)


# ---------------------------------------------------------------------------
# Core scoring function (mirrors main.py run_bias_analysis())
# ---------------------------------------------------------------------------

def run_bias_analysis(article: dict, source: dict,
                      cluster_articles: list[dict] | None = None) -> dict:
    """
    Run all 5 bias analyzers on a single article and compute confidence.

    Args:
        article: Dict with keys the analyzers expect (full_text, title,
                 summary, url, section, source_id, word_count).
        source:  Dict with political_lean_baseline, tier, name,
                 state_affiliated (optional bool).
        cluster_articles: Optional list of sibling articles for framing
                          omission detection (passed through to analyze_framing).

    Returns:
        Dict with score keys + rationale, ready for bias_scores upsert.
        Keys: political_lean, sensationalism, opinion_fact, factual_rigor,
              framing, confidence, rationale (JSON string).
    """
    scores: dict = {
        "political_lean": 50,
        "sensationalism": 10,
        "opinion_fact": 25,
        "factual_rigor": 50,
        "framing": 15,
        "confidence": 0.7,
    }
    rationale: dict = {}

    try:
        result = analyze_political_lean(article, source)
        if isinstance(result, dict):
            scores["political_lean"] = result["score"]
            rationale["lean"] = result["rationale"]
        else:
            scores["political_lean"] = result
    except Exception as exc:
        print(f"    [warn] political_lean failed: {exc}")

    try:
        result = analyze_sensationalism(article)
        if isinstance(result, dict):
            scores["sensationalism"] = result["score"]
            rationale["sensationalism"] = result["rationale"]
        else:
            scores["sensationalism"] = result
    except Exception as exc:
        print(f"    [warn] sensationalism failed: {exc}")

    try:
        result = analyze_opinion(article)
        if isinstance(result, dict):
            scores["opinion_fact"] = result["score"]
            rationale["opinion"] = result["rationale"]
        else:
            scores["opinion_fact"] = result
    except Exception as exc:
        print(f"    [warn] opinion_detector failed: {exc}")

    try:
        result = analyze_factual_rigor(article)
        if isinstance(result, dict):
            scores["factual_rigor"] = result["score"]
            rationale["coverage"] = result["rationale"]
        else:
            scores["factual_rigor"] = result
    except Exception as exc:
        print(f"    [warn] factual_rigor failed: {exc}")

    try:
        result = analyze_framing(article, cluster_articles=cluster_articles)
        if isinstance(result, dict):
            scores["framing"] = result["score"]
            rationale["framing"] = result["rationale"]
        else:
            scores["framing"] = result
    except Exception as exc:
        print(f"    [warn] framing failed: {exc}")

    scores["confidence"] = compute_confidence(article, scores)

    if rationale:
        scores["rationale"] = json.dumps(rationale)

    return scores


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def _batch_upsert(table: str, rows: list[dict], chunk_size: int = 150,
                  on_conflict: str | None = None) -> int:
    """Upsert rows in chunks; returns total rows written."""
    total = 0
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        try:
            if on_conflict:
                supabase.table(table).upsert(chunk, on_conflict=on_conflict).execute()
            else:
                supabase.table(table).upsert(chunk).execute()
            total += len(chunk)
        except Exception as exc:
            print(f"  [warn] Batch upsert failed (chunk {i}): {exc}")
            # Fall back to individual row upserts for this chunk
            for row in chunk:
                try:
                    if on_conflict:
                        supabase.table(table).upsert(row, on_conflict=on_conflict).execute()
                    else:
                        supabase.table(table).upsert(row).execute()
                    total += 1
                except Exception as row_exc:
                    print(f"    [err] Single-row upsert failed: {row_exc}")
    return total


def fetch_sources_from_db() -> dict[str, dict]:
    """
    Fetch all sources from Supabase and return a dict keyed by DB UUID.

    The source dict is shaped to match what the analyzers expect:
        political_lean_baseline, tier, name, state_affiliated, slug
    """
    result = supabase.table("sources").select(
        "id,slug,name,tier,political_lean_baseline,state_affiliated"
    ).execute()
    sources_by_id: dict[str, dict] = {}
    for row in (result.data or []):
        src = {
            "id": row.get("slug", ""),          # slug used as "id" key in sources.json
            "db_id": row["id"],
            "name": row.get("name", ""),
            "tier": row.get("tier", ""),
            "political_lean_baseline": row.get("political_lean_baseline", "center"),
            "state_affiliated": bool(row.get("state_affiliated", False)),
        }
        sources_by_id[row["id"]] = src          # keyed by UUID for article.source_id lookup
    return sources_by_id


def fetch_articles(
    limit: int | None,
    offset: int,
    source_slug: str | None,
    sources_by_id: dict[str, dict],
) -> list[dict]:
    """
    Fetch articles from Supabase.

    Returns list of article dicts enriched with a "source" key holding
    the resolved source dict (so we can pass it to analyzers).

    Columns fetched match the keys analyzers use:
        id, title, summary, full_text, source_id, url, section, word_count
    """
    query = supabase.table("articles").select(
        "id,title,summary,full_text,source_id,url,section,word_count"
    )

    # Filter by source slug if requested
    if source_slug:
        # Resolve slug -> DB UUID
        slug_match = [src for src in sources_by_id.values() if src["id"] == source_slug]
        if not slug_match:
            print(f"[fatal] Source slug '{source_slug}' not found in DB.")
            sys.exit(1)
        source_uuid = slug_match[0]["db_id"]
        query = query.eq("source_id", source_uuid)

    # Pagination
    query = query.order("id").range(offset, offset + (limit or 99_999) - 1)

    result = query.execute()
    articles = result.data or []

    # Attach resolved source dict to each article for easy lookup during scoring
    for art in articles:
        sid = art.get("source_id", "")
        art["_source"] = sources_by_id.get(sid, {
            "id": "",
            "name": "",
            "tier": "",
            "political_lean_baseline": "center",
            "state_affiliated": False,
        })

    return articles


def fetch_cluster_articles_map() -> dict[str, list[dict]]:
    """
    Build a mapping: article_id -> [sibling article dicts in the same cluster].

    Used to pass cluster_articles to analyze_framing for omission detection.
    Only fetches what we need: article id, title, full_text, summary.

    Strategy:
        1. Fetch cluster_articles (cluster_id, article_id) — full join table.
        2. Fetch article content for all referenced article IDs in batches.
        3. Build: article_id -> list of sibling article content dicts.
    """
    print("  Fetching cluster membership for framing omission context...")

    # Fetch entire cluster_articles junction table
    ca_result = supabase.table("cluster_articles").select("cluster_id,article_id").execute()
    ca_rows = ca_result.data or []

    if not ca_rows:
        return {}

    # Build cluster_id -> [article_ids]
    cluster_to_arts: dict[str, list[str]] = defaultdict(list)
    for row in ca_rows:
        cluster_to_arts[row["cluster_id"]].append(row["article_id"])

    # Collect all unique article IDs that appear in multi-article clusters
    multi_cluster_art_ids: set[str] = set()
    for art_ids in cluster_to_arts.values():
        if len(art_ids) > 1:
            multi_cluster_art_ids.update(art_ids)

    if not multi_cluster_art_ids:
        return {}

    # Fetch article content in batches of 200
    all_ids = list(multi_cluster_art_ids)
    content_map: dict[str, dict] = {}
    BATCH = 200
    for i in range(0, len(all_ids), BATCH):
        batch = all_ids[i:i + BATCH]
        res = supabase.table("articles").select(
            "id,title,summary,full_text"
        ).in_("id", batch).execute()
        for art in (res.data or []):
            content_map[art["id"]] = art

    # Build article_id -> siblings mapping
    # For each article, siblings = all other articles in the same cluster
    art_to_siblings: dict[str, list[dict]] = {}
    for art_ids in cluster_to_arts.values():
        if len(art_ids) < 2:
            continue
        art_contents = [content_map[aid] for aid in art_ids if aid in content_map]
        for aid in art_ids:
            if aid in content_map:
                siblings = [a for a in art_contents if a["id"] != aid]
                art_to_siblings[aid] = siblings

    print(f"  Cluster context ready: {len(art_to_siblings)} articles have sibling context")
    return art_to_siblings


# ---------------------------------------------------------------------------
# Gemini reasoning (optional --gemini flag)
# ---------------------------------------------------------------------------

def run_gemini_on_clusters() -> None:
    """
    Re-run Gemini cluster summarization on qualifying clusters (3+ sources).
    Requires GEMINI_API_KEY in environment.  Respects the 25-call cap.
    """
    try:
        from summarizer.cluster_summarizer import summarize_cluster
    except ImportError:
        print("  [skip] cluster_summarizer not importable — skipping Gemini step.")
        return

    print("\n[Gemini] Fetching clusters for re-summarization...")
    clusters_res = supabase.table("story_clusters").select(
        "id,title,source_count"
    ).gte("source_count", 3).order("source_count", desc=True).limit(25).execute()
    clusters = clusters_res.data or []
    print(f"  {len(clusters)} clusters qualify (3+ sources, cap 25)")

    updated = 0
    for cluster in clusters:
        cid = cluster["id"]
        # Fetch articles for this cluster
        ca_res = supabase.table("cluster_articles").select("article_id").eq(
            "cluster_id", cid
        ).execute()
        art_ids = [r["article_id"] for r in (ca_res.data or [])]
        if not art_ids:
            continue
        art_res = supabase.table("articles").select(
            "id,title,summary,full_text,source_id,url,section"
        ).in_("id", art_ids).execute()
        articles = art_res.data or []
        if not articles:
            continue
        try:
            summary_result = summarize_cluster(cluster, articles)
            if summary_result:
                supabase.table("story_clusters").update(summary_result).eq(
                    "id", cid
                ).execute()
                updated += 1
        except Exception as exc:
            print(f"  [warn] Gemini failed for cluster {cid[:8]}: {exc}")

    print(f"  Gemini: updated {updated}/{len(clusters)} clusters")


# ---------------------------------------------------------------------------
# Per-source summary for sanity check
# ---------------------------------------------------------------------------

def print_source_averages(source_stats: dict[str, dict]) -> None:
    """Print per-source average scores for quick sanity check."""
    print("\n  --- Per-source averages (sanity check) ---")
    header = f"  {'Source':<30} {'N':>5}  {'Lean':>5}  {'Sens':>5}  {'Opin':>5}  {'Fact':>5}  {'Fram':>5}  {'Conf':>5}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for slug in sorted(source_stats):
        s = source_stats[slug]
        n = s["count"]
        if n == 0:
            continue
        lean = s["political_lean"] / n
        sens = s["sensationalism"] / n
        opin = s["opinion_fact"] / n
        fact = s["factual_rigor"] / n
        fram = s["framing"] / n
        conf = s["confidence"] / n
        print(
            f"  {slug:<30} {n:>5}  "
            f"{lean:>5.1f}  {sens:>5.1f}  {opin:>5.1f}  "
            f"{fact:>5.1f}  {fram:>5.1f}  {conf:>5.3f}"
        )


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Re-score existing articles with all 5 bias analyzers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Maximum number of articles to rescore (default: all)",
    )
    parser.add_argument(
        "--offset", type=int, default=0,
        help="Number of articles to skip (for pagination, default: 0)",
    )
    parser.add_argument(
        "--source", type=str, default=None, metavar="SLUG",
        help="Rescore only articles from this source slug (e.g. ap-news)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run analysis but do not write results to Supabase",
    )
    parser.add_argument(
        "--gemini", action="store_true",
        help="After rescoring, also re-run Gemini summarization on top clusters",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    args = parse_args()
    dry_run: bool = args.dry_run
    run_gemini: bool = args.gemini

    start_time = time.time()

    print("=" * 60)
    print(f"void --news re-scorer  {'(DRY RUN)' if dry_run else ''}")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Step 1: Load source metadata from DB
    # ------------------------------------------------------------------
    print("\n[1/4] Loading source metadata from Supabase...")
    sources_by_id = fetch_sources_from_db()
    print(f"  {len(sources_by_id)} sources loaded")

    # ------------------------------------------------------------------
    # Step 2: Fetch articles
    # ------------------------------------------------------------------
    print(f"\n[2/4] Fetching articles from Supabase"
          f"{f' (source: {args.source})' if args.source else ''}"
          f"{f' limit={args.limit}' if args.limit else ''}"
          f"{f' offset={args.offset}' if args.offset else ''}...")

    articles = fetch_articles(
        limit=args.limit,
        offset=args.offset,
        source_slug=args.source,
        sources_by_id=sources_by_id,
    )
    total = len(articles)
    print(f"  {total} articles fetched")

    if total == 0:
        print("  Nothing to rescore.")
        return

    # ETA estimate based on ~200 articles/minute
    eta_minutes = total / 200.0
    if eta_minutes < 1:
        eta_str = f"~{int(eta_minutes * 60)}s"
    else:
        eta_str = f"~{eta_minutes:.1f} min"
    print(f"  Estimated time: {eta_str} (~200 articles/min with spaCy)")

    # ------------------------------------------------------------------
    # Step 3: Optionally fetch cluster sibling context for framing
    # ------------------------------------------------------------------
    # Only do the cluster fetch if we are rescoring enough articles to
    # make it worth the extra round-trips.  Skip for single-source runs
    # under 100 articles to keep it fast.
    fetch_cluster_ctx = (not args.source) or (total >= 100)
    art_to_siblings: dict[str, list[dict]] = {}
    if fetch_cluster_ctx:
        print()
        art_to_siblings = fetch_cluster_articles_map()

    # ------------------------------------------------------------------
    # Step 4: Score each article
    # ------------------------------------------------------------------
    print(f"\n[3/4] Scoring {total} articles...")

    bias_rows: list[dict] = []
    errors = 0
    # Per-source aggregates for the final sanity-check table
    source_stats: dict[str, dict] = defaultdict(lambda: {
        "count": 0, "political_lean": 0.0, "sensationalism": 0.0,
        "opinion_fact": 0.0, "factual_rigor": 0.0, "framing": 0.0, "confidence": 0.0,
    })

    for i, article in enumerate(articles):
        source = article.pop("_source", {})  # remove helper key before passing to analyzers
        art_id = article.get("id", "")
        siblings = art_to_siblings.get(art_id)

        try:
            scores = run_bias_analysis(article, source, cluster_articles=siblings)
        except Exception as exc:
            errors += 1
            if errors <= 10:
                title_snippet = (article.get("title") or "")[:50]
                print(f"  [err] {art_id[:8]}  '{title_snippet}': {exc}")
            continue

        scores["article_id"] = art_id
        bias_rows.append(scores)

        # Accumulate per-source stats
        slug = source.get("id", "unknown")
        ss = source_stats[slug]
        ss["count"] += 1
        ss["political_lean"] += scores.get("political_lean", 50)
        ss["sensationalism"] += scores.get("sensationalism", 10)
        ss["opinion_fact"] += scores.get("opinion_fact", 25)
        ss["factual_rigor"] += scores.get("factual_rigor", 50)
        ss["framing"] += scores.get("framing", 15)
        ss["confidence"] += scores.get("confidence", 0.7)

        # Progress every 100 articles
        if (i + 1) % 100 == 0 or (i + 1) == total:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed * 60 if elapsed > 0 else 0
            remaining = total - (i + 1)
            eta_rem = remaining / (rate / 60) if rate > 0 else 0
            print(
                f"  [{i+1:>{len(str(total))}}/{total}]  "
                f"{rate:.0f} art/min  "
                f"ETA {eta_rem:.0f}s  "
                f"errors={errors}"
            )

    print(f"\n  Scored {len(bias_rows)}/{total} articles  ({errors} errors)")

    # ------------------------------------------------------------------
    # Step 5: Write results to Supabase
    # ------------------------------------------------------------------
    if dry_run:
        print(f"\n[4/4] DRY RUN — {len(bias_rows)} rows ready but NOT written.")
        # Show a sample of what would be written
        sample = bias_rows[:3]
        print("  Sample rows (first 3):")
        for row in sample:
            aid = row.get("article_id", "")[:8]
            print(
                f"    {aid}  lean={row.get('political_lean'):5.1f}  "
                f"sens={row.get('sensationalism'):5.1f}  "
                f"opin={row.get('opinion_fact'):5.1f}  "
                f"fact={row.get('factual_rigor'):5.1f}  "
                f"fram={row.get('framing'):5.1f}  "
                f"conf={row.get('confidence'):.3f}"
            )
    else:
        print(f"\n[4/4] Writing {len(bias_rows)} rows to Supabase (chunks of 150)...")
        written = _batch_upsert(
            "bias_scores", bias_rows,
            chunk_size=150,
            on_conflict="article_id",
        )
        print(f"  {written}/{len(bias_rows)} rows written")

    # ------------------------------------------------------------------
    # Optional: Gemini reasoning on clusters
    # ------------------------------------------------------------------
    if run_gemini and not dry_run:
        run_gemini_on_clusters()
    elif run_gemini and dry_run:
        print("\n[Gemini] Skipped in dry-run mode.")

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    elapsed = time.time() - start_time
    rate_final = len(bias_rows) / elapsed * 60 if elapsed > 0 else 0
    print(f"\n  Total time: {elapsed:.1f}s  ({rate_final:.0f} articles/min)")

    print_source_averages(source_stats)

    print("\n  Scoring complete.")
    print("  Run 'python pipeline/rerank.py' to re-apply ranking.")


if __name__ == "__main__":
    main()
