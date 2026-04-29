#!/usr/bin/env python3
"""
DB Reviewer — Data Quality Auditor for void --news

Audits the Supabase database across 8 domains:
1. Source Coverage
2. Article Quality
3. Bias Score Quality
4. Cluster Quality
5. Enrichment Quality
6. Temporal Freshness
7. Referential Integrity
8. Cross-Field Consistency

Usage:
    python pipeline/db_reviewer.py [--json] [--verbose]

Requires: SUPABASE_URL, SUPABASE_KEY environment variables.
"""

import json
import sys
import argparse
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter
from pathlib import Path

# Add pipeline root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.supabase_client import supabase

# Load sources baseline
SOURCES_PATH = Path(__file__).parent.parent / "data" / "sources.json"


class DataQualityAuditor:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.findings = {
            "critical": [],
            "must_have": [],
            "nice_to_have": [],
        }
        self.stats = {}
        self.scores = {}

    # =========================================================================
    # 1. SOURCE COVERAGE
    # =========================================================================

    def audit_source_coverage(self) -> dict:
        """Check that all 90 sources from sources.json exist in DB with valid config."""
        print("\n[1/8] Auditing Source Coverage...")

        with open(SOURCES_PATH) as f:
            expected_sources = json.load(f)

        expected_count = len(expected_sources)
        expected_by_slug = {s["id"]: s for s in expected_sources}

        # Fetch all DB sources
        result = supabase.table("sources").select("*").execute()
        db_sources = result.data or []
        db_by_slug = {s["slug"]: s for s in db_sources}

        db_active = [s for s in db_sources if s.get("is_active", True)]

        # Check coverage
        missing = []
        for slug, src in expected_by_slug.items():
            if slug not in db_by_slug:
                missing.append(slug)

        score = 10
        if missing:
            score -= min(5, len(missing) // 10)  # 0.5 pt per 10 missing
            self.findings["critical"].append(
                f"Missing sources: {len(missing)} expected sources not in DB: {missing[:5]}{'...' if len(missing) > 5 else ''}"
            )

        # Check rss_url validity
        no_rss = [s for s in db_active if not s.get("rss_url")]
        if no_rss:
            score -= min(3, len(no_rss) / 10)
            self.findings["must_have"].append(
                f"Missing RSS URLs: {len(no_rss)} active sources have null rss_url"
            )

        # Check baseline lean set
        no_baseline = [s for s in db_active if not s.get("political_lean_baseline")]
        if no_baseline:
            score -= min(3, len(no_baseline) / 10)
            self.findings["must_have"].append(
                f"Missing baseline lean: {len(no_baseline)} sources lack political_lean_baseline"
            )

        # Check tier distribution
        tier_counts = Counter(s.get("tier") for s in db_active if s.get("tier"))
        expected_tiers = {"us_major": 30, "international": 30, "independent": 30}
        tier_imbalance = False
        for tier, expected in expected_tiers.items():
            actual = tier_counts.get(tier, 0)
            if abs(actual - expected) > 10:
                tier_imbalance = True
                break

        if tier_imbalance:
            score -= 2
            self.findings["nice_to_have"].append(
                f"Tier distribution imbalance: {dict(tier_counts)} (expected ~30 each)"
            )

        self.stats["sources_total"] = len(db_sources)
        self.stats["sources_active"] = len(db_active)
        self.stats["sources_expected"] = expected_count
        self.stats["sources_missing"] = len(missing)
        self.stats["sources_no_rss"] = len(no_rss)
        self.stats["tier_distribution"] = dict(tier_counts)

        self.scores["source_coverage"] = max(0, score)
        if self.verbose:
            print(f"  Sources: {len(db_active)}/{expected_count} active")
            print(f"  Tiers: {dict(tier_counts)}")
        return {"coverage": len(db_active) / expected_count if expected_count else 0}

    # =========================================================================
    # 2. ARTICLE QUALITY
    # =========================================================================

    def audit_article_quality(self) -> dict:
        """Check NULL rates, word count distribution, duplicates."""
        print("[2/8] Auditing Article Quality...")

        result = supabase.table("articles").select("id,full_text,published_at,word_count,url,section").execute()
        articles = result.data or []

        if not articles:
            self.findings["critical"].append("No articles in database")
            self.scores["article_quality"] = 0
            return {}

        # NULL checks
        no_full_text = sum(1 for a in articles if not a.get("full_text"))
        no_published = sum(1 for a in articles if not a.get("published_at"))
        null_word_count = sum(1 for a in articles if a.get("word_count") is None)

        null_full_text_pct = (no_full_text / len(articles)) * 100
        null_published_pct = (no_published / len(articles)) * 100

        score = 10
        if null_full_text_pct > 10:
            score -= min(3, (null_full_text_pct - 10) / 10)
            self.findings["must_have"].append(
                f"High NULL full_text: {null_full_text_pct:.1f}% (goal <10%)"
            )

        if null_published_pct > 5:
            score -= min(3, (null_published_pct - 5) / 5)
            self.findings["must_have"].append(
                f"High NULL published_at: {null_published_pct:.1f}% (goal <5%)"
            )

        # Word count distribution
        word_counts = [a.get("word_count", 0) for a in articles if a.get("word_count")]
        suspicious_short = sum(1 for wc in word_counts if wc < 100)
        if word_counts:
            avg_wc = sum(word_counts) / len(word_counts)
            min_wc = min(word_counts)
            max_wc = max(word_counts)
        else:
            avg_wc = min_wc = max_wc = 0

        if suspicious_short / max(len(word_counts), 1) > 0.15:
            score -= 1
            self.findings["nice_to_have"].append(
                f"High proportion of short articles (<100 words): {suspicious_short}/{len(word_counts)}"
            )

        # Section distribution
        sections = Counter(a.get("section", "unknown") for a in articles)

        # Check for duplicate URLs
        urls = [a.get("url") for a in articles]
        duplicates = [url for url, count in Counter(urls).items() if count > 1]
        if duplicates:
            score -= 2
            self.findings["critical"].append(
                f"Duplicate URLs found: {len(duplicates)} unique URLs appear multiple times"
            )

        self.stats["articles_total"] = len(articles)
        self.stats["articles_null_full_text"] = no_full_text
        self.stats["articles_null_published"] = no_published
        self.stats["articles_word_count_avg"] = round(avg_wc, 1) if word_counts else 0
        self.stats["articles_word_count_min"] = min_wc
        self.stats["articles_word_count_max"] = max_wc
        self.stats["articles_section_distribution"] = dict(sections)
        self.stats["articles_suspicious_short"] = suspicious_short

        self.scores["article_quality"] = max(0, score)
        if self.verbose:
            print(f"  Articles: {len(articles)} total")
            print(f"  NULL full_text: {null_full_text_pct:.1f}%")
            print(f"  NULL published_at: {null_published_pct:.1f}%")
            print(f"  Word count: avg {avg_wc:.0f}, min {min_wc}, max {max_wc}")
            print(f"  Sections: {dict(sections)}")

        return {"articles": len(articles), "null_rates": (null_full_text_pct, null_published_pct)}

    # =========================================================================
    # 3. BIAS SCORE QUALITY
    # =========================================================================

    def audit_bias_score_quality(self) -> dict:
        """Check coverage, default detection, distribution, confidence."""
        print("[3/8] Auditing Bias Score Quality...")

        # Fetch bias scores
        result = supabase.table("bias_scores").select(
            "article_id,political_lean,sensationalism,opinion_fact,factual_rigor,framing,confidence"
        ).execute()
        bias_scores = result.data or []

        # Fetch article count
        result_articles = supabase.table("articles").select("id").execute()
        articles = result_articles.data or []
        article_count = len(articles)

        score = 10
        coverage_pct = (len(bias_scores) / article_count * 100) if article_count else 0

        if coverage_pct < 95:
            score -= min(5, (100 - coverage_pct) / 10)
            self.findings["must_have"].append(
                f"Low bias score coverage: {coverage_pct:.1f}% (goal 95%+)"
            )

        # Default detection: all scores = 50/10/25/50/15 (or close)
        defaults = 0
        for bs in bias_scores:
            # Common defaults for the 5-axis model
            if (bs.get("political_lean") == 50 and
                bs.get("sensationalism") == 10 and
                bs.get("opinion_fact") == 25 and
                bs.get("factual_rigor") == 50 and
                bs.get("framing") == 15):
                defaults += 1

        default_pct = (defaults / len(bias_scores) * 100) if bias_scores else 0
        if default_pct > 5:
            score -= min(3, (default_pct - 5) / 10)
            self.findings["must_have"].append(
                f"High default bias scores: {default_pct:.1f}% of scores are exact defaults"
            )

        # Distribution per axis
        axes = {
            "political_lean": [],
            "sensationalism": [],
            "opinion_fact": [],
            "factual_rigor": [],
            "framing": [],
        }
        for bs in bias_scores:
            for axis in axes:
                val = bs.get(axis)
                if val is not None:
                    axes[axis].append(val)

        # Compute stats per axis
        axis_stats = {}
        for axis, values in axes.items():
            if values:
                axis_stats[axis] = {
                    "mean": round(sum(values) / len(values), 1),
                    "min": min(values),
                    "max": max(values),
                    "stdev": round((sum((v - sum(values) / len(values)) ** 2 for v in values) / len(values)) ** 0.5, 1) if len(values) > 1 else 0,
                }

        # Confidence distribution — should NOT all be 0.7
        confidences = [bs.get("confidence", 0) for bs in bias_scores]
        conf_counter = Counter([round(c, 1) for c in confidences])
        mode_conf = conf_counter.most_common(1)[0] if conf_counter else (0, 0)
        if mode_conf[0] > 0 and mode_conf[1] / len(confidences) > 0.5:
            score -= 2
            self.findings["nice_to_have"].append(
                f"Confidence heavily concentrated: {mode_conf[1]}/{len(confidences)} scores = {mode_conf[0]}"
            )

        # Outlier detection (scores at 0 or 100)
        outliers = 0
        for axis, values in axes.items():
            outliers += sum(1 for v in values if v == 0 or v == 100)

        if outliers > len(bias_scores) * 0.05:
            score -= 1
            self.findings["nice_to_have"].append(
                f"High outliers (0 or 100): {outliers} scores at extremes"
            )

        self.stats["bias_scores_total"] = len(bias_scores)
        self.stats["bias_scores_coverage_pct"] = round(coverage_pct, 1)
        self.stats["bias_scores_defaults_pct"] = round(default_pct, 1)
        self.stats["bias_scores_axes"] = axis_stats
        self.stats["bias_scores_confidence_distribution"] = dict(conf_counter)
        self.stats["bias_scores_outliers"] = outliers

        self.scores["bias_score_quality"] = max(0, score)
        if self.verbose:
            print(f"  Coverage: {coverage_pct:.1f}%")
            print(f"  Defaults: {default_pct:.1f}%")
            print(f"  Confidence mode: {mode_conf}")
            for axis, stats in axis_stats.items():
                print(f"  {axis}: mean={stats['mean']}, stdev={stats['stdev']}, range=[{stats['min']},{stats['max']}]")

        return {"coverage": coverage_pct, "defaults": default_pct, "axis_stats": axis_stats}

    # =========================================================================
    # 4. CLUSTER QUALITY
    # =========================================================================

    def audit_cluster_quality(self) -> dict:
        """Check cluster content, single-article clusters, summaries, source accuracy."""
        print("[4/8] Auditing Cluster Quality...")

        # Fetch clusters with sections array support
        result = supabase.table("story_clusters").select("id,title,summary,consensus_points,divergence_points,source_count,sections").execute()
        clusters = result.data or []

        score = 10

        if not clusters:
            self.findings["critical"].append("No story clusters in database")
            self.scores["cluster_quality"] = 0
            return {}

        # Fetch cluster_articles junction
        result_ca = supabase.table("cluster_articles").select("cluster_id,article_id").execute()
        cluster_articles = result_ca.data or []
        articles_per_cluster = defaultdict(list)
        for ca in cluster_articles:
            articles_per_cluster[ca["cluster_id"]].append(ca["article_id"])

        # Metrics
        single_article = sum(1 for cid in articles_per_cluster if len(articles_per_cluster[cid]) == 1)
        total_articles_in_clusters = sum(len(aids) for aids in articles_per_cluster.values())
        avg_articles = total_articles_in_clusters / len(clusters) if clusters else 0

        if single_article / len(clusters) > 0.30:
            score -= 2
            self.findings["nice_to_have"].append(
                f"High single-article clusters: {single_article}/{len(clusters)} ({single_article/len(clusters)*100:.1f}%)"
            )

        # Check for untitled/missing summaries
        no_summary = sum(1 for c in clusters if not c.get("summary"))
        untitled = sum(1 for c in clusters if "Untitled" in c.get("title", ""))

        if no_summary > len(clusters) * 0.05:
            score -= min(2, no_summary / 100)
            self.findings["nice_to_have"].append(
                f"Missing cluster summaries: {no_summary}/{len(clusters)}"
            )

        if untitled > 0:
            score -= 1
            self.findings["nice_to_have"].append(f"Untitled clusters: {untitled}")

        # Check source_count accuracy
        count_mismatches = 0
        for c in clusters:
            cid = c["id"]
            actual_count = len(articles_per_cluster.get(cid, []))
            stated_count = c.get("source_count", 0)
            if actual_count != stated_count:
                count_mismatches += 1

        if count_mismatches > len(clusters) * 0.05:
            score -= 2
            self.findings["critical"].append(
                f"Source count mismatches: {count_mismatches} clusters have incorrect source_count"
            )

        # Check consensus/divergence quality (Gemini vs rule-based)
        # 3+ source clusters should have richer content (not generic templates)
        rich_clusters = sum(1 for c in clusters if len(articles_per_cluster.get(c["id"], [])) >= 3)
        generic_consensus = 0
        generic_phrases = [
            "Coverage maintains a measured tone",
            "Reports remain consistent",
            "Sources generally agree",
            "maintains consistent coverage",
        ]

        for c in clusters:
            if len(articles_per_cluster.get(c["id"], [])) >= 3:
                consensus = c.get("consensus_points", [])
                if any(isinstance(p, str) and any(g in p for g in generic_phrases) for p in consensus):
                    generic_consensus += 1

        if rich_clusters > 0 and generic_consensus / rich_clusters > 0.30:
            self.findings["nice_to_have"].append(
                f"Generic consensus content: {generic_consensus}/{rich_clusters} 3+-source clusters use generic phrases"
            )

        self.stats["clusters_total"] = len(clusters)
        self.stats["clusters_single_article"] = single_article
        self.stats["clusters_single_article_pct"] = round(single_article / len(clusters) * 100, 1) if clusters else 0
        self.stats["clusters_avg_articles"] = round(avg_articles, 1)
        self.stats["clusters_no_summary"] = no_summary
        self.stats["clusters_untitled"] = untitled
        self.stats["clusters_source_count_mismatches"] = count_mismatches
        self.stats["clusters_3plus_sources"] = rich_clusters
        self.stats["clusters_generic_consensus"] = generic_consensus

        self.scores["cluster_quality"] = max(0, score)
        if self.verbose:
            print(f"  Clusters: {len(clusters)} total")
            print(f"  Single-article: {single_article} ({single_article/len(clusters)*100:.1f}%)")
            print(f"  Avg articles/cluster: {avg_articles:.1f}")
            print(f"  No summary: {no_summary}")
            print(f"  Source count mismatches: {count_mismatches}")

        return {"clusters": len(clusters), "single_article_pct": single_article/len(clusters)*100}

    # =========================================================================
    # 5. ENRICHMENT QUALITY
    # =========================================================================

    def audit_enrichment_quality(self) -> dict:
        """Check bias_diversity, divergence_score, headline_rank, coverage_velocity."""
        print("[5/8] Auditing Enrichment Quality...")

        result = supabase.table("story_clusters").select(
            "id,bias_diversity,divergence_score,headline_rank,coverage_velocity"
        ).execute()
        clusters = result.data or []

        score = 10

        # Check bias_diversity (JSONB) populated
        no_bias_diversity = sum(1 for c in clusters if not c.get("bias_diversity"))
        bias_div_pct = (no_bias_diversity / len(clusters) * 100) if clusters else 0

        if bias_div_pct > 20:
            score -= min(3, (bias_div_pct - 20) / 20)
            self.findings["nice_to_have"].append(
                f"Low bias_diversity coverage: {bias_div_pct:.1f}% null (goal 80%+)"
            )

        # divergence_score populated and non-zero
        no_divergence = sum(1 for c in clusters if c.get("divergence_score") is None or c.get("divergence_score") == 0)
        div_pct = (no_divergence / len(clusters) * 100) if clusters else 0

        if div_pct > 30:
            score -= 2
            self.findings["nice_to_have"].append(
                f"Low divergence_score coverage: {div_pct:.1f}% null/zero"
            )

        # headline_rank variance
        headline_ranks = [c.get("headline_rank") for c in clusters if c.get("headline_rank") is not None]
        if headline_ranks:
            hr_avg = sum(headline_ranks) / len(headline_ranks)
            hr_variance = sum((h - hr_avg) ** 2 for h in headline_ranks) / len(headline_ranks) if len(headline_ranks) > 1 else 0
            hr_stdev = hr_variance ** 0.5
        else:
            hr_avg = hr_stdev = 0

        if hr_stdev < 5:
            score -= 1
            self.findings["nice_to_have"].append(
                f"Low headline_rank variance: stdev={hr_stdev:.1f} (goal >10)"
            )

        # coverage_velocity populated
        no_velocity = sum(1 for c in clusters if c.get("coverage_velocity") is None or c.get("coverage_velocity") == 0)
        vel_pct = (no_velocity / len(clusters) * 100) if clusters else 0

        if vel_pct > 30:
            score -= 1
            self.findings["nice_to_have"].append(
                f"Low coverage_velocity coverage: {vel_pct:.1f}% null/zero"
            )

        self.stats["clusters_no_bias_diversity"] = no_bias_diversity
        self.stats["clusters_bias_diversity_pct"] = round((1 - bias_div_pct / 100) * 100, 1)
        self.stats["clusters_no_divergence_score"] = no_divergence
        self.stats["clusters_headline_rank_stdev"] = round(hr_stdev, 1)
        self.stats["clusters_no_coverage_velocity"] = no_velocity

        self.scores["enrichment_quality"] = max(0, score)
        if self.verbose:
            print(f"  bias_diversity: {round((1-bias_div_pct/100)*100, 1)}% populated")
            print(f"  divergence_score: {round((1-div_pct/100)*100, 1)}% non-zero")
            print(f"  headline_rank stdev: {hr_stdev:.1f}")
            print(f"  coverage_velocity: {round((1-vel_pct/100)*100, 1)}% populated")

        return {"bias_diversity_pct": round((1-bias_div_pct/100)*100, 1)}

    # =========================================================================
    # 6. TEMPORAL FRESHNESS
    # =========================================================================

    def audit_temporal_freshness(self) -> dict:
        """Check recent article dates, pipeline run frequency."""
        print("[6/8] Auditing Temporal Freshness...")

        # Most recent article
        result = supabase.table("articles").select("published_at").order(
            "published_at", desc=True
        ).limit(1).execute()
        most_recent_article = result.data[0]["published_at"] if result.data else None

        # Most recent pipeline run
        result = supabase.table("pipeline_runs").select("completed_at").order(
            "completed_at", desc=True
        ).limit(1).execute()
        most_recent_run = result.data[0]["completed_at"] if result.data else None

        # Age distribution
        result = supabase.table("articles").select("published_at").execute()
        articles = result.data or []

        now = datetime.now(timezone.utc)
        one_week_ago = now - timedelta(days=7)

        old_articles = sum(1 for a in articles if a.get("published_at") and
                          datetime.fromisoformat(a["published_at"].replace("Z", "+00:00")) < one_week_ago)
        old_pct = (old_articles / len(articles) * 100) if articles else 0

        # Pipeline run frequency (expect 2x daily)
        result = supabase.table("pipeline_runs").select("completed_at").order(
            "completed_at", desc=True
        ).limit(100).execute()
        runs = result.data or []

        run_times = []
        for r in runs:
            if r.get("completed_at"):
                run_times.append(datetime.fromisoformat(r["completed_at"].replace("Z", "+00:00")))

        run_intervals = []
        for i in range(len(run_times) - 1):
            delta = (run_times[i] - run_times[i+1]).total_seconds() / 3600  # hours
            run_intervals.append(delta)

        expected_interval = 12  # 2x daily = ~12 hour intervals
        avg_interval = sum(run_intervals) / len(run_intervals) if run_intervals else 0

        score = 10

        if old_pct > 50:
            score -= 2
            self.findings["nice_to_have"].append(
                f"High stale article ratio: {old_pct:.1f}% >7 days old"
            )

        if most_recent_run:
            run_age = (now - datetime.fromisoformat(most_recent_run.replace("Z", "+00:00"))).total_seconds() / 3600
            if run_age > 24:
                score -= min(3, run_age / 24)
                self.findings["must_have"].append(
                    f"Stale pipeline: {run_age:.1f} hours since last run (should be <12h)"
                )

        if abs(avg_interval - expected_interval) > 6:
            score -= 1
            self.findings["nice_to_have"].append(
                f"Pipeline frequency drift: avg {avg_interval:.1f}h (expected ~{expected_interval}h)"
            )

        self.stats["most_recent_article"] = most_recent_article
        self.stats["most_recent_pipeline_run"] = most_recent_run
        self.stats["articles_older_than_7_days_pct"] = round(old_pct, 1)
        self.stats["pipeline_runs_last_100_avg_interval_hours"] = round(avg_interval, 1)
        self.stats["pipeline_runs_total"] = len(runs)

        self.scores["temporal_freshness"] = max(0, score)
        if self.verbose:
            print(f"  Most recent article: {most_recent_article}")
            print(f"  Most recent run: {most_recent_run}")
            print(f"  Articles >7d old: {old_pct:.1f}%")
            print(f"  Avg run interval: {avg_interval:.1f}h")
            print(f"  Total runs: {len(runs)}")

        return {"old_articles_pct": old_pct, "avg_run_interval": avg_interval}

    # =========================================================================
    # 7. REFERENTIAL INTEGRITY
    # =========================================================================

    def audit_referential_integrity(self) -> dict:
        """Check valid cluster/article refs, orphaned articles/bias scores."""
        print("[7/8] Auditing Referential Integrity...")

        # Supabase caps single .select() at 1000 rows; paginate so all rows
        # land in the comparison sets (otherwise truncation produces
        # phantom orphans + phantom invalid refs at scale).
        def _fetch_all(table: str, columns: str, page: int = 1000) -> list:
            rows: list = []
            start = 0
            while True:
                batch = (
                    supabase.table(table)
                    .select(columns)
                    .range(start, start + page - 1)
                    .execute()
                    .data
                    or []
                )
                rows.extend(batch)
                if len(batch) < page:
                    break
                start += page
            return rows

        articles = {a["id"] for a in _fetch_all("articles", "id")}
        clusters = {c["id"] for c in _fetch_all("story_clusters", "id")}
        cluster_articles = _fetch_all("cluster_articles", "cluster_id,article_id")
        bias_scores = _fetch_all("bias_scores", "article_id")

        score = 10

        # Check invalid refs in cluster_articles
        bad_refs = 0
        for ca in cluster_articles:
            if ca["cluster_id"] not in clusters or ca["article_id"] not in articles:
                bad_refs += 1

        if bad_refs > 0:
            score -= 3
            self.findings["critical"].append(
                f"Invalid cluster_articles refs: {bad_refs} junction records reference deleted clusters/articles"
            )

        # Check orphaned articles (not in any cluster)
        clustered = {ca["article_id"] for ca in cluster_articles}
        orphaned = articles - clustered
        orphaned_pct = (len(orphaned) / len(articles) * 100) if articles else 0

        if len(orphaned) > 10:
            score -= min(2, len(orphaned) / 100)
            self.findings["must_have"].append(
                f"Orphaned articles: {len(orphaned)} ({orphaned_pct:.1f}%) not in any cluster"
            )

        # Check orphaned bias scores (for deleted articles)
        bias_article_ids = {bs["article_id"] for bs in bias_scores}
        orphaned_bias = bias_article_ids - articles

        if orphaned_bias:
            score -= 1
            self.findings["critical"].append(
                f"Orphaned bias scores: {len(orphaned_bias)} scores reference deleted articles"
            )

        self.stats["articles_orphaned"] = len(orphaned)
        self.stats["articles_orphaned_pct"] = round(orphaned_pct, 1)
        self.stats["bias_scores_orphaned"] = len(orphaned_bias)
        self.stats["cluster_articles_invalid_refs"] = bad_refs

        self.scores["referential_integrity"] = max(0, score)
        if self.verbose:
            print(f"  Orphaned articles: {len(orphaned)} ({orphaned_pct:.1f}%)")
            print(f"  Orphaned bias scores: {len(orphaned_bias)}")
            print(f"  Invalid cluster_articles refs: {bad_refs}")

        return {"orphaned_articles": len(orphaned), "orphaned_bias_scores": len(orphaned_bias)}

    # =========================================================================
    # 8. CROSS-FIELD CONSISTENCY
    # =========================================================================

    def audit_cross_field_consistency(self) -> dict:
        """Check sources with center lean have articles averaging 40-60 lean, etc."""
        print("[8/8] Auditing Cross-Field Consistency...")

        # Fetch sources with lean baseline
        result = supabase.table("sources").select("id,slug,political_lean_baseline,tier").execute()
        sources = {s["id"]: s for s in (result.data or [])}

        # Fetch articles with source_id
        result = supabase.table("articles").select("id,source_id").execute()
        articles_by_source = defaultdict(list)
        for a in (result.data or []):
            articles_by_source[a["source_id"]].append(a["id"])

        # Fetch all bias scores
        result = supabase.table("bias_scores").select("article_id,political_lean").execute()
        bias_by_article = {bs["article_id"]: bs.get("political_lean") for bs in (result.data or [])}

        score = 10
        consistency_issues = 0

        # Check center sources
        for src_id, src in sources.items():
            if src.get("political_lean_baseline") == "center":
                article_ids = articles_by_source.get(src_id, [])
                leans = [bias_by_article.get(aid) for aid in article_ids if aid in bias_by_article]

                if leans:
                    avg_lean = sum(leans) / len(leans)
                    if not (40 <= avg_lean <= 60):
                        consistency_issues += 1

        if consistency_issues > 0:
            score -= min(2, consistency_issues / 10)
            self.findings["nice_to_have"].append(
                f"Center-baseline lean divergence: {consistency_issues} sources have avg lean outside 40-60 range"
            )

        # Note: High-rigor and opinion-section checks would require more nuanced data
        # Placeholder for future expansion

        self.stats["cross_field_consistency_issues"] = consistency_issues
        self.scores["cross_field_consistency"] = max(0, score)

        if self.verbose:
            print(f"  Cross-field consistency issues: {consistency_issues}")

        return {"consistency_issues": consistency_issues}

    # =========================================================================
    # GENERATE REPORT
    # =========================================================================

    def generate_report(self) -> dict:
        """Run all audits and generate final report."""
        print("=" * 70)
        print("void --news DATA QUALITY REPORT")
        print("=" * 70)
        print(f"Generated: {datetime.now(timezone.utc).isoformat()}")

        self.audit_source_coverage()
        self.audit_article_quality()
        self.audit_bias_score_quality()
        self.audit_cluster_quality()
        self.audit_enrichment_quality()
        self.audit_temporal_freshness()
        self.audit_referential_integrity()
        self.audit_cross_field_consistency()

        # Compute overall score
        domain_scores = list(self.scores.values())
        overall_score = (sum(domain_scores) / len(domain_scores)) if domain_scores else 0

        print("\n" + "=" * 70)
        print("DOMAIN SCORES")
        print("=" * 70)
        for domain, score in self.scores.items():
            print(f"  {domain.replace('_', ' ').title():.<45} {score:.1f}/10")

        print(f"\n  OVERALL SCORE: {overall_score:.1f}/10")

        print("\n" + "=" * 70)
        print("CRITICAL FINDINGS")
        print("=" * 70)
        if self.findings["critical"]:
            for i, finding in enumerate(self.findings["critical"], 1):
                print(f"  {i}. {finding}")
        else:
            print("  None — data integrity is healthy")

        print("\n" + "=" * 70)
        print("MUST HAVE FINDINGS")
        print("=" * 70)
        if self.findings["must_have"]:
            for i, finding in enumerate(self.findings["must_have"], 1):
                print(f"  {i}. {finding}")
        else:
            print("  None")

        print("\n" + "=" * 70)
        print("NICE TO HAVE FINDINGS")
        print("=" * 70)
        if self.findings["nice_to_have"]:
            for i, finding in enumerate(self.findings["nice_to_have"], 1):
                print(f"  {i}. {finding}")
        else:
            print("  None")

        print("\n" + "=" * 70)
        print("KEY STATISTICS")
        print("=" * 70)
        for key, value in self.stats.items():
            print(f"  {key}: {value}")

        # Determine THE ONE THING
        if self.findings["critical"]:
            the_one_thing = self.findings["critical"][0]
        elif self.findings["must_have"]:
            the_one_thing = self.findings["must_have"][0]
        else:
            the_one_thing = "Database is in good health"

        print("\n" + "=" * 70)
        print("THE ONE THING")
        print("=" * 70)
        print(f"  {the_one_thing}")

        return {
            "overall_score": round(overall_score, 1),
            "domain_scores": {k: round(v, 1) for k, v in self.scores.items()},
            "findings": self.findings,
            "statistics": self.stats,
            "the_one_thing": the_one_thing,
        }


def main():
    parser = argparse.ArgumentParser(description="void --news Database Quality Auditor")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    auditor = DataQualityAuditor(verbose=args.verbose)
    report = auditor.generate_report()

    if args.json:
        print("\n" + "=" * 70)
        print("JSON REPORT")
        print("=" * 70)
        print(json.dumps(report, indent=2))

    return 0 if report["overall_score"] >= 7 else 1


if __name__ == "__main__":
    sys.exit(main())
