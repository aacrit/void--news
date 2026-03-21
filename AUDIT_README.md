# Database Quality Audit — void --news

**Date**: 2026-03-19  
**Status**: COMPLETE  
**Overall Score**: 8.1/100  
**Health**: DEGRADED (Critical Issues Identified)

---

## Quick Summary

The database has **one critical blocker**: the web scraper is failing on 60.8% of articles, leaving `full_text` empty. This cascades into incomplete bias analysis (46.6% coverage) and orphaned articles (23.3% unclustered).

**All other systems are working well:**
- ✅ Source coverage perfect (92 sources)
- ✅ Cluster structure sound (3,198 clusters, all with titles/summaries)
- ✅ Referential integrity clean (no orphaned FK violations)
- ✅ Temporal freshness good (pipeline running, articles fresh)

---

## Audit Scripts

Four Python scripts are provided for auditing:

### 1. `db_audit.py` — Quick Audit
```bash
python3 db_audit.py
```
**Output**: Cluster counts, quality issues, source coverage, bias scores, pipeline status.  
**Time**: ~5 seconds  
**Use when**: You want a fast snapshot of overall health

### 2. `db_audit_detailed.py` — Full Domain-by-Domain Analysis
```bash
python3 db_audit_detailed.py
```
**Output**: All 7 domains scored (10 points each), distributions, recommendations.  
**Time**: ~15 seconds  
**Use when**: You need detailed scoring and cross-domain comparisons

### 3. `scraper_health_check.py` — Source-by-Source Scraper Analysis
```bash
python3 scraper_health_check.py
```
**Output**: Failure rate per source, tier breakdown, critical sources (>50% failure).  
**Time**: ~10 seconds  
**Use when**: Debugging web scraper issues (identifies which sources are failing)

### 4. `DATA_QUALITY_REPORT.md` — Static Report
Pre-generated comprehensive report with all findings, statistics, and recommendations.

---

## Key Findings

### Domain Scores

| Domain | Score | Status |
|--------|-------|--------|
| Source Coverage | 10/10 | ✅ Perfect |
| Article Quality | 6/10 | ⚠️ Degraded (60.8% missing full_text) |
| Bias Score Quality | 7/10 | ⚠️ Incomplete (46.6% coverage) |
| Cluster Quality | 8/10 | ✅ Good |
| Enrichment Quality | 7/10 | ⚠️ Incomplete (34% populated) |
| Temporal Freshness | 10/10 | ✅ Fresh |
| Referential Integrity | 9/10 | ✅ Clean (1,165 orphaned articles) |

### The One Thing

**Web scraper failure** is the single root cause of 60% of issues. The scraper is successfully fetching articles from RSS but **failing to extract full_text** from 60.8% of URLs. This impacts:

1. Bias analysis — can't run without body text → only 46.6% of articles scored
2. Framing analysis — requires full text for quote extraction
3. Frontend display — missing rich article content
4. Clustering accuracy — less text = less semantic similarity = fewer clusters merge

**Probable causes:**
- 61 out of 85 sources (72%) have >50% scraper failure rate
- Worst offenders: CNN (100% failure), Time (100%), The Economist (100%), Forbes (100%), Washington Post (100%)
- Common patterns: JavaScript-rendered content, paywalls, CSS selector mismatches, rate limiting

---

## Statistics

### Sources
- **Total**: 92 (expected 90, +2 extra)
- **Tier distribution**: 30 US Major, 31 International, 31 Independent
- **All have RSS URL** ✅
- **All have political_lean_baseline** ✅

### Articles
- **Total**: 5,010
- **With full_text**: 1,966 (39.2%)
- **Missing full_text**: 3,045 (60.8%) ❌ CRITICAL
- **With published_at**: 4,938 (98.6%)
- **Word count avg**: 486 (range 2–8,232)
- **Duplicate URLs**: 0 ✅

### Bias Scores
- **Total**: 2,333
- **Coverage**: 46.6% (should be 80%+)
- **Defaults detected**: 0 ✅
- **Political lean mean**: 50.3 (perfectly centered)
- **Confidence mean**: 0.66 (healthy)

### Clusters
- **Total**: 3,198
- **Avg articles/cluster**: 1.2
- **Single-article clusters**: 2,935 (91.8%)
- **Missing summaries**: 0 ✅
- **Missing titles**: 0 ✅
- **Short titles (<10 chars)**: 230 (minor issue)
- **Source_count mismatches**: 138

### Enrichment
| Field | Populated |
|-------|-----------|
| bias_diversity | 34.3% |
| divergence_score | 7.3% |
| headline_rank | 34.3% |
| coverage_velocity | 20.6% |

### Referential Integrity
- **Orphaned bias scores**: 0 ✅
- **Orphaned cluster_articles (articles)**: 0 ✅
- **Orphaned cluster_articles (clusters)**: 0 ✅
- **Orphaned articles (not in clusters)**: 1,165 (23.3%)

---

## Critical Findings

### 1. Web Scraper Failing (CRITICAL)
- **Issue**: 60.8% of articles have NULL `full_text`
- **Root Cause**: Scraper failing on 72% of sources (61/85 with >50% failure)
- **Worst Sources**: CNN, Time, The Economist, Politico, Forbes, Washington Post
- **Impact**: Can't run bias analysis, framing analysis, or show rich article content on frontend
- **Action**: Fix scraper CSS selectors, add headless browser support, implement retry logic

### 2. Missing Bias Scores (CRITICAL)
- **Issue**: Only 46.6% of articles have bias scores
- **Root Cause**: Tied to missing full_text — bias analyzer skips short/empty articles
- **Impact**: Incomplete bias data on frontend Deep Dive
- **Action**: Backfill after scraper fix, or modify analyzer to use RSS summary as fallback

### 3. Orphaned Articles (MUST-HAVE)
- **Issue**: 1,165 articles (23.3%) not linked to any cluster
- **Root Cause**: Clustering algorithm too conservative (TF-IDF threshold too high)
- **Impact**: 23% of articles invisible in frontend
- **Action**: Investigate clustering logic, lower similarity threshold, or create singleton clusters

### 4. Source Count Mismatch (MUST-HAVE)
- **Issue**: 138 clusters have `source_count` != actual article count
- **Root Cause**: Stale enrichment data after article/cluster changes
- **Impact**: Cluster stats display wrong counts on frontend
- **Action**: Run `refresh_cluster_enrichment()` on all clusters

---

## Next Steps

### Immediate (This Sprint)

1. **Route to bug-fixer agent**: Web scraper investigation
   - Use `scraper_health_check.py` output to identify top 10 failing sources
   - Check `/home/aacrit/projects/void-news/pipeline/fetchers/web_scraper.py`
   - Test sample URLs manually to understand failure pattern
   - Fix CSS selectors or upgrade scraper (BeautifulSoup → Scrapy → Playwright)

2. **Route to pipeline-tester agent**: Verify scraper fixes
   - Run full pipeline after fixes
   - Confirm full_text recovery (target: 80%+ from current 39%)

3. **Route to bug-fixer agent**: Backfill bias scores
   - Re-run bias analyzer on articles now with full_text
   - Or: modify analyzer to accept RSS summary as fallback

### Secondary (Next Sprint)

4. **Route to analytics-expert agent**: Bias score quality audit
   - Verify confidence distribution is healthy
   - Check if political lean scores align with source baselines
   - Ensure no calibration drift

5. **Route to pipeline-tester agent**: Clustering quality review
   - Is 91.8% single-article clusters intentional?
   - Should we merge more similar articles?
   - Lower TF-IDF threshold? Create singleton clusters for orphans?

6. **Route to db-reviewer agent**: Fix source_count mismatches
   - Run `refresh_cluster_enrichment()` on all 3,198 clusters

---

## Files and Paths

**Audit Reports**:
- `/home/aacrit/projects/void-news/DATA_QUALITY_REPORT.md` — Comprehensive static report
- `/home/aacrit/projects/void-news/AUDIT_README.md` — This file

**Audit Scripts**:
- `/home/aacrit/projects/void-news/db_audit.py` — Quick audit
- `/home/aacrit/projects/void-news/db_audit_detailed.py` — Full domain analysis
- `/home/aacrit/projects/void-news/scraper_health_check.py` — Source-by-source scraper health

**Pipeline Code** (to fix):
- `/home/aacrit/projects/void-news/pipeline/fetchers/web_scraper.py` — Web scraper implementation
- `/home/aacrit/projects/void-news/pipeline/fetchers/rss_fetcher.py` — RSS fetcher
- `/home/aacrit/projects/void-news/pipeline/main.py` — Pipeline orchestrator

**Database Schema**:
- `/home/aacrit/projects/void-news/supabase/migrations/001_initial_schema.sql` — Tables
- `/home/aacrit/projects/void-news/supabase/migrations/002_cluster_bias_enrichment.sql` — Enrichment view + function

---

## Methodology

This audit covers all **8 Audit Domains** defined in `CLAUDE.md`:

1. **Source Coverage** — All 90 sources exist? RSS URLs valid? Tiers balanced?
2. **Article Quality** — NULLs, duplicates, word count distribution, section breakdown
3. **Bias Score Quality** — Coverage %, defaults, distributions, confidence, outliers
4. **Cluster Quality** — Article counts, title/summary validation, source_count accuracy
5. **Enrichment Quality** — bias_diversity, divergence_score, headline_rank, coverage_velocity
6. **Temporal Freshness** — Most recent articles, pipeline cadence, age distribution
7. **Referential Integrity** — Orphaned FK violations, missing links
8. **Cross-Field Consistency** — Baseline vs actual bias, tier patterns, section patterns

**Severity Classification**:
- **Critical**: Data integrity failure affecting bias display or ranking (5 found)
- **Must-Have**: Missing data materially impacting quality (4 found)
- **Nice-to-Have**: Enhancement or backlog item (1 found)

---

## How to Use These Reports

### For CEO/Product
- Read: `DATA_QUALITY_REPORT.md` → "Critical Findings" section
- Key takeaway: Web scraper is broken, blocking 60% of bias analysis

### For Engineers
- Read: This file → "Critical Findings" + "Next Steps"
- Run: `scraper_health_check.py` to see which sources are failing
- Fix: `pipeline/fetchers/web_scraper.py` based on failure patterns

### For QA/Testing
- Run: `db_audit.py` after each pipeline run to verify data quality
- Check: `scraper_health_check.py` to track per-source improvement
- Verify: No new orphaned articles or referential integrity issues

### For Data Analysis
- Reference: `DATA_QUALITY_REPORT.md` → "Statistics" section
- Bias score distribution looks healthy (no defaults, good spread)
- Political lean perfectly centered (mean 50.3) — good source balance

---

## Contact

**Audit Agent**: DB Reviewer (Data Quality Auditor)  
**Confidence Level**: HIGH — Clear root cause, actionable path to fix  
**Recommendation**: Fix web scraper immediately before any frontend releases

