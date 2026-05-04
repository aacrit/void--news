# DB Reviewer Guide — Data Quality Auditor

Last updated: 2026-04-28 (rev 1)

## Overview

The **DB Reviewer** (`pipeline/db_reviewer.py`) is a comprehensive data quality auditing tool for the void --news database. It examines Supabase across 8 domains and produces a detailed report with actionable findings.

**Cost:** $0 — read-only queries only. No modifications.

## Quick Start

```bash
# Full verbose audit
python pipeline/db_reviewer.py --verbose

# JSON output for CI/CD integration
python pipeline/db_reviewer.py --json

# Compact report
python pipeline/db_reviewer.py
```

**Requirements:** `SUPABASE_URL` and `SUPABASE_KEY` environment variables (available in GitHub Actions).

## Audit Framework — 8 Domains

### 1. Source Coverage (10 pts)
Ensures all 951 curated sources exist in the database with valid configuration.

**Checks:**
- All 951 sources from `data/sources.json` exist in DB (`is_active=true`)
- Every source has valid `rss_url` (not null)
- Every source has `political_lean_baseline` set
- Tier distribution: 42 us_major, 181 international, 196 independent ±10% tolerance
- No inactive sources blocking coverage

**Scoring:**
- -5 pts: 20+ missing sources (critical)
- -3 pts: Per missing baseline lean
- -2 pts: Tier imbalance >10 off target
- -1 pt: Missing RSS URLs

**Typical Issues:**
- New sources added to sources.json but not synced to DB
- Source tier misconfiguration
- RSS URL changes not propagated

### 2. Article Quality (10 pts)
Validates content completeness and distribution.

**Checks:**
- NULL `full_text` count (goal: <10%)
- NULL `published_at` count (goal: <5%)
- Word count distribution (suspicious if <100 words)
- Section distribution (world vs us)
- No duplicate URLs in database

**Scoring:**
- -3 pts: NULL full_text >10%
- -3 pts: NULL published_at >5%
- -2 pts: Duplicate URLs (data integrity issue)
- -1 pt: >15% of articles <100 words
- -1 pt: Section imbalance

**Typical Issues:**
- Web scraper incomplete (missing full_text)
- RSS entries missing published_at
- Duplicate detection failed in deduplicator
- Very short opinion pieces or breaking alerts (not necessarily bad)

### 3. Bias Score Quality (10 pts)
Validates the bias analysis engine output.

**Checks:**
- Coverage: % of articles with bias scores (goal: 95%+)
- Default detection: exact default score matching (goal: <5%)
- Per-axis distribution: mean, stdev, min, max
- Confidence distribution: should not be heavily concentrated
- Outlier detection: scores at 0 or 100 (goal: <5%)

**Scoring:**
- -5 pts: Coverage <95%
- -3 pts: >5% default scores
- -2 pts: Confidence overconcentration
- -1 pt: >5% outliers

**Typical Issues:**
- Analyzer skipped articles (coverage gap)
- Sparsity-weighted blending activating too often (defaults)
- Confidence formula not calibrated
- Sensationalism extremes on breaking news

### 4. Cluster Quality (10 pts)
Examines story cluster formation and enrichment.

**Checks:**
- Single-article cluster ratio (goal: <30%)
- Missing cluster summaries (goal: <5%)
- Untitled clusters ("Untitled Story")
- Source count accuracy: stated vs actual article count
- Gemini consensus/divergence quality (3+ source clusters should have rich, specific content, not generic templates like "Coverage maintains a measured tone")

**Scoring:**
- -2 pts: >30% single-article clusters
- -2 pts: Source count mismatches >5%
- -2 pts: High generic consensus (3+-source clusters with clichéd phrases)
- -1 pt: Untitled clusters present
- -1 pt: >5% missing summaries

**Typical Issues:**
- TF-IDF clustering threshold too high (over-clustering)
- Entity-overlap merge pass not catching related stories
- Gemini API cap reached (only first 25 clusters summarized)
- Generic prompt output in early pipeline runs

### 5. Enrichment Quality (10 pts)
Validates cluster-level computed fields.

**Checks:**
- `bias_diversity` JSONB populated (goal: 80%+)
- `divergence_score` populated and non-zero (goal: 80%+)
- `headline_rank` variance (stdev goal: >10)
- `coverage_velocity` populated (goal: 80%+)

**Scoring:**
- -3 pts: <80% bias_diversity coverage
- -2 pts: <80% divergence_score coverage
- -1 pt: Headline rank stdev <5
- -1 pt: <80% coverage_velocity coverage

**Typical Issues:**
- `refresh_cluster_enrichment()` RPC failed or incomplete
- Ranking step 7 didn't complete
- No Gemini data (editorial_importance field)

### 6. Temporal Freshness (10 pts)
Ensures pipeline recency and article age.

**Checks:**
- Most recent article date (should be <6 hours old)
- Most recent pipeline run date (goal: <12 hours)
- Article age distribution (goal: <50% older than 7 days)
- Pipeline run frequency (expect 4x daily, ~6-hour intervals)

**Scoring:**
- -3 pts: Last pipeline run >24 hours ago
- -2 pts: >50% articles >7 days old
- -1 pt: Avg run interval drifts >6 hours from 6h target
- -1 pt: High stale ratio

**Typical Issues:**
- GitHub Actions workflow disabled or failing
- RSS feeds returning no new content (all stale)
- Pipeline timeout on large dataset
- Clustering step slow (merges for 72-hour window)

### 7. Referential Integrity (10 pts)
Validates FK relationships and data consistency.

**Checks:**
- `cluster_articles` junction refs valid (both cluster_id and article_id exist)
- No orphaned articles (articles not in any cluster)
- No orphaned bias scores (scores for deleted articles)
- Foreign key constraints enforced

**Scoring:**
- -3 pts: Invalid cluster_articles refs
- -1 pt: Orphaned bias scores
- -2 pts: >10 orphaned articles (data corruption)

**Typical Issues:**
- Cluster deletion cascade didn't clean up articles (shouldn't happen with ON DELETE CASCADE)
- Article deleted but bias score not removed
- Deduplication/cleanup RPC failed

### 8. Cross-Field Consistency (10 pts)
Validates alignment between source metadata and actual article data.

**Checks:**
- Sources with `political_lean_baseline: "center"` have articles averaging 40-60 lean
- High-rigor sources have higher `factual_rigor` scores (future expansion)
- Opinion sections have higher `opinion_fact` scores (future expansion)

**Scoring:**
- -2 pts: >10% of center-baseline sources drift outside 40-60 range
- Future: validation against tier quality baselines

**Typical Issues:**
- Source lean baseline miscalibrated
- Bias engine drift (consistent over/under scoring a source)
- Contaminated article sample for a source

## Report Structure

```
DATA QUALITY REPORT
Date: 2026-03-27T15:42:33+00:00

DOMAIN SCORES
  Source Coverage:...........................9.5/10
  Article Quality:...........................8.2/10
  Bias Score Quality:.........................8.0/10
  Cluster Quality:............................7.8/10
  Enrichment Quality:.........................8.5/10
  Temporal Freshness:.........................9.0/10
  Referential Integrity:.....................10.0/10
  Cross-Field Consistency:....................9.0/10

  OVERALL SCORE: 8.5/10

CRITICAL FINDINGS
  1. Invalid cluster_articles refs: 5 junction records reference deleted clusters/articles

MUST HAVE FINDINGS
  1. High NULL full_text: 12.3% (goal <10%)
  2. Stale pipeline: 18.5 hours since last run (should be <12h)

NICE TO HAVE FINDINGS
  1. High single-article clusters: 28% (goal <30%)
  2. Low headline_rank variance: stdev=4.2 (goal >10)

KEY STATISTICS
  sources_total: 951
  sources_active: 368
  articles_total: 45280
  articles_null_full_text: 5620
  clusters_total: 8420
  clusters_single_article: 2357
  bias_scores_coverage_pct: 95.8
  most_recent_article: 2026-03-27T13:22:45+00:00
  most_recent_pipeline_run: 2026-03-27T11:15:22+00:00
  pipeline_runs_total: 127

THE ONE THING
  Stale pipeline: 18.5 hours since last run (should be <12h)
```

## Integration with CI/CD

Add to GitHub Actions workflow (`.github/workflows/`):

```yaml
- name: Audit database quality
  env:
    SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
    SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
  run: |
    python pipeline/db_reviewer.py --json > db-audit-report.json
    python pipeline/db_reviewer.py --verbose
```

Exit code:
- `0` if overall_score >= 7.0 (healthy)
- `1` if overall_score < 7.0 (needs attention)

## Running Standalone

```bash
# Local development (requires .env with credentials)
python pipeline/db_reviewer.py --verbose

# GitHub Actions (secrets injected)
python pipeline/db_reviewer.py --json

# Dry-run query (no auth required)
python3 -c "from pipeline.db_reviewer import DataQualityAuditor; print('Auditor loaded')"
```

## Troubleshooting

### "SUPABASE_URL and SUPABASE_KEY must be set"
- Credentials are only available in GitHub Actions
- Set them in repo secrets: Settings → Secrets and variables → Actions
- Or create `.env` locally (never commit)

### Queries timeout or fail
- Supabase has 30-second query timeout
- DB Reviewer batches queries efficiently
- If still timing out, split audit manually:
  ```bash
  # Single domain audit
  python3 << 'EOF'
  from pipeline.db_reviewer import DataQualityAuditor
  auditor = DataQualityAuditor(verbose=True)
  auditor.audit_source_coverage()
  auditor.audit_article_quality()
  EOF
  ```

### "No articles in database"
- First pipeline run hasn't completed
- Check `.github/workflows/pipeline.yml` triggers
- Manually trigger: GitHub → Actions → News Pipeline → Run workflow

### Confidence scores all 0.7
- Early pipeline runs had hardcoded default
- Run fresh pipeline to regenerate: `python pipeline/main.py`

### Source count mismatches
- cluster_articles junction incomplete
- Check if clustering step 6 completed
- Run: `python pipeline/rerank.py` to recompute

## Maintenance Schedule

Run the auditor:
- **Daily:** After each pipeline run (automated in workflow)
- **Weekly:** Comprehensive review with `--verbose` flag
- **Before release:** Ensure overall_score >= 8.5

## Roadmap

### v2 (Planned)
- Time-series tracking (audit history graph)
- Anomaly detection (score drift alerts)
- Per-source bias distribution comparison vs AllSides baselines
- Bias engine signal decomposition (which signals firing per article)
- Topic-category alignment validation
- Edition-specific freshness checks

### v3 (Future)
- Automatic remediation (orphan cleanup, cluster repair)
- Predictive health scoring
- Frontend dashboard integration
- Real-time webhook alerts

## Related Tools

- `pipeline/validation/runner.py` — Bias engine regression testing (38 ground-truth articles)
- `pipeline/rerank.py` — Standalone cluster re-scoring
- `supabase/migrations/` — Schema documentation
- `CLAUDE.md` — Pipeline architecture

## Files Referenced

- `/home/user/void--news/pipeline/db_reviewer.py` — This auditor
- `/home/user/void--news/data/sources.json` — Expected source list
- `/home/user/void--news/CLAUDE.md` — Architecture documentation
- `/home/user/void--news/supabase/migrations/` — Schema files

---

**Author:** db-reviewer agent | **Last Updated:** 2026-03-31 | **Status:** Production
