# Database Quality Audit Framework

Last updated: 2026-04-28 (rev 1)

**Last Updated:** 2026-03-31
**Status:** Read-Only Audit Framework

> This document provides the comprehensive 8-domain audit framework for the void --news Supabase database. It is adapted from DondeAI's db-reviewer and serves as the specification for ongoing data quality validation.

## Context

The void --news platform runs 4x daily (every 6 hours) on GitHub Actions, ingesting ~1,200 articles from 951 curated sources and analyzing them through 6-axis NLP bias scoring. The pipeline writes to Supabase PostgreSQL, which serves as the single source of truth for the Next.js frontend (client-side reads only).

**Current as of 2026-03-31:**
- Sources: 951 total (42 us_major + 181 international + 196 independent)
- Pipeline runs: 4x daily (00:00, 06:00, 12:00, 18:00 UTC)
- Bias engine: 5 axes + confidence (Axis 6 = per-topic per-outlet EMA tracking, dormant)
- Clustering: 2-phase (TF-IDF + entity-overlap merge)
- Summarization: Gemini 2.5 Flash (25-call cap per run, 3+ source clusters)
- Daily Brief: TL;DR + 2-host BBC-style audio (Gemini TTS native multi-speaker)
- Story Memory: Dual top stories (rank 1-2) with live update polling between runs

## 8-Domain Audit Framework

### 1. Source Coverage — /10

**Requirement:** All 951 sources from `data/sources.json` are present, valid, and properly categorized.

#### Checks
| Check | Expected | Query |
|-------|----------|-------|
| Total active sources | 951 | `SELECT COUNT(*) FROM sources WHERE is_active = true` |
| us_major tier | 42 | `SELECT COUNT(*) FROM sources WHERE tier='us_major' AND is_active=true` |
| international tier | 181 | `SELECT COUNT(*) FROM sources WHERE tier='international' AND is_active=true` |
| independent tier | 196 | `SELECT COUNT(*) FROM sources WHERE tier='independent' AND is_active=true` |
| All have rss_url | 951 | `SELECT COUNT(*) FROM sources WHERE rss_url IS NOT NULL AND is_active=true` |
| All have political_lean_baseline | 951 | `SELECT COUNT(*) FROM sources WHERE political_lean_baseline IS NOT NULL AND is_active=true` |
| Baseline distribution: center | 204 | `SELECT COUNT(*) FROM sources WHERE political_lean_baseline='center' AND is_active=true` |
| Baseline distribution: center-left | 90 | `SELECT COUNT(*) FROM sources WHERE political_lean_baseline='center-left' AND is_active=true` |
| Baseline distribution: center-right | 27 | `SELECT COUNT(*) FROM sources WHERE political_lean_baseline='center-right' AND is_active=true` |
| Baseline distribution: left | 19 | `SELECT COUNT(*) FROM sources WHERE political_lean_baseline='left' AND is_active=true` |
| Baseline distribution: right | 25 | `SELECT COUNT(*) FROM sources WHERE political_lean_baseline='right' AND is_active=true` |
| Baseline distribution: far-left | 7 | `SELECT COUNT(*) FROM sources WHERE political_lean_baseline='far-left' AND is_active=true` |
| Baseline distribution: far-right | 8 | `SELECT COUNT(*) FROM sources WHERE political_lean_baseline='far-right' AND is_active=true` |

#### Severity
- **Critical:** < 951 active sources (> 2.5% missing)
- **Must Have:** Any us_major source missing
- **Nice to Have:** Distribution skewed > 5% in any direction

#### Scoring
- 10/10: All 951 active, all tiers present, all baselines set
- 9/10: < 5 sources missing
- 8/10: 5-10 sources missing OR 1 us_major missing
- 6/10: > 10 missing OR multiple tier coverage gaps
- 0/10: > 50 sources missing OR entire tier missing

---

### 2. Article Quality — /10

**Requirement:** Articles have complete metadata, sufficient text, and proper section/edition assignment.

#### Checks
| Check | Good | Warning | Critical |
|-------|------|---------|----------|
| Total articles | > 100 | 50-100 | < 50 |
| Articles with full_text | > 90% | 70-90% | < 70% |
| Articles with published_at | > 95% | 85-95% | < 85% |
| Avg word_count | 400-600 | 200-800 | < 150 \| > 2000 |
| Articles < 100 words | 0-5% | 5-15% | > 15% |
| Articles > 2000 words | 0-5% | 5-10% | > 10% |
| Section distribution (world:us:other) | 60:30:10 | varies | > 70% one section |
| Duplicates (URL collision) | 0 | 0 | > 5 |

#### SQL
```sql
-- Full text coverage
SELECT
  COUNT(*) as total,
  COUNT(CASE WHEN full_text IS NOT NULL THEN 1 END) as with_full_text,
  COUNT(CASE WHEN published_at IS NOT NULL THEN 1 END) as with_published,
  COUNT(CASE WHEN word_count < 100 THEN 1 END) as suspiciously_short,
  AVG(word_count) as avg_word_count,
  STDDEV(word_count) as stddev_word_count
FROM articles;

-- Section distribution
SELECT section, COUNT(*) as count FROM articles GROUP BY section;

-- Duplicate URLs
SELECT url, COUNT(*) as count FROM articles GROUP BY url HAVING COUNT(*) > 1;
```

#### Severity
- **Critical:** > 20% NULL full_text OR > 10% NULL published_at (impacts feed quality)
- **Must Have:** > 30% articles < 100 words (likely scrape failures)
- **Nice to Have:** Skewed section distribution

#### Scoring
- 10/10: > 95% full_text, > 98% published_at, avg 400-600 words, < 5% short
- 8/10: 85-95% full_text, < 5% short articles
- 6/10: 70-85% full_text OR > 10% short articles
- 3/10: < 70% full_text OR > 20% short
- 0/10: Massive content quality loss

---

### 3. Bias Score Quality — /10

**Requirement:** Bias scores are comprehensive, distributed, and not defaulting to fallback values.

#### Checks
| Check | Good | Warning | Critical |
|-------|------|---------|----------|
| Coverage (articles with scores) | > 95% | 85-95% | < 85% |
| Axes coverage | 100% | 99% | < 98% |
| Default detection (50/10/25/50/15) | 0% | < 1% | > 5% |
| Confidence distribution (not all 0.7) | varied | < 3% at 0.7 | > 10% at exactly 0.7 |
| Lean distribution | 20-80 | 15-85 | skewed to edge |
| Sensationalism distribution | 10-60 | 5-70 | skewed to 0 or 100 |
| Opinion_fact outliers (0 or 100) | < 2% | 2-5% | > 5% |
| Factual_rigor by tier (us_major > intl > indep) | proper ordering | mostly | inverted |
| Framing distribution | 10-90 spread | 15-85 | skewed |

#### SQL
```sql
-- Coverage and defaults
SELECT
  COUNT(DISTINCT article_id) as scored_articles,
  (SELECT COUNT(*) FROM articles) as total_articles,
  COUNT(*) FILTER (WHERE political_lean=50 AND sensationalism=10 AND opinion_fact=25 AND factual_rigor=50) as defaults,
  COUNT(*) FILTER (WHERE confidence=0.7) as at_default_confidence
FROM bias_scores;

-- Distribution per axis
SELECT
  AVG(political_lean) as avg_lean,
  STDDEV(political_lean) as sd_lean,
  MIN(political_lean) as min_lean,
  MAX(political_lean) as max_lean,
  PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY political_lean) as median_lean,
  COUNT(*) FILTER (WHERE political_lean IN (0, 100)) as outliers
FROM bias_scores;

-- Similar for sensationalism, opinion_fact, factual_rigor, framing

-- Tier comparison (factual_rigor)
SELECT
  s.tier,
  AVG(b.factual_rigor) as avg_rigor,
  COUNT(*) as count
FROM bias_scores b
JOIN cluster_articles ca ON b.article_id = ca.article_id
JOIN story_clusters sc ON ca.cluster_id = sc.id
JOIN articles a ON b.article_id = a.id
JOIN sources s ON a.source_id = s.id
GROUP BY s.tier
ORDER BY avg_rigor DESC;
```

#### Severity
- **Critical:** < 85% coverage OR > 5% defaults (indicates pipeline failure)
- **Must Have:** Confidence all equal to 0.7 (suggests confidence calc bypassed)
- **Nice to Have:** Distribution shows unexpected skew

#### Scoring
- 10/10: > 98% coverage, < 0.5% defaults, varied confidence
- 8/10: 95-98% coverage, < 1% defaults
- 6/10: 85-95% coverage, 1-5% defaults
- 3/10: 75-85% coverage OR > 5% defaults
- 0/10: < 75% coverage OR > 10% defaults

---

### 4. Cluster Quality — /10

**Requirement:** Story clusters are well-formed, properly enriched, and have proper source attribution.

#### Checks
| Check | Good | Warning | Critical |
|-------|------|---------|----------|
| Total clusters | 5-50 per run | 1-5 | 0 |
| Avg articles/cluster | 3-8 | 2-10 | < 2 |
| Single-article clusters | < 10% | 10-30% | > 30% |
| Clusters without summaries | 0% | < 5% | > 5% |
| Clusters with "Untitled Story" | 0% | 0% | > 0% (find & fix) |
| Source count accuracy | matches JOIN | off by ≤ 1 | off by > 1 |
| NULL consensus_points | 0% | < 5% | > 5% |
| NULL divergence_points | 0% | < 5% | > 5% |
| Gemini vs rule-based summary quality | check manually | — | generic templates |

#### SQL
```sql
-- Cluster overview
SELECT
  COUNT(*) as total_clusters,
  AVG(source_count) as avg_sources,
  MIN(source_count) as min_sources,
  MAX(source_count) as max_sources,
  COUNT(*) FILTER (WHERE source_count = 1) as single_article_clusters,
  COUNT(*) FILTER (WHERE summary IS NULL) as without_summaries,
  COUNT(*) FILTER (WHERE title LIKE '%Untitled%') as untitled
FROM story_clusters;

-- Source count accuracy
SELECT
  sc.id,
  sc.title,
  sc.source_count as recorded,
  COUNT(DISTINCT ca.article_id) as actual_articles,
  COUNT(DISTINCT s.id) as unique_sources
FROM story_clusters sc
LEFT JOIN cluster_articles ca ON sc.id = ca.cluster_id
LEFT JOIN articles a ON ca.article_id = a.id
LEFT JOIN sources s ON a.source_id = s.id
GROUP BY sc.id
HAVING sc.source_count != COUNT(DISTINCT s.id);

-- Summary quality (manual check): look for generic templates
SELECT
  title,
  summary,
  source_count
FROM story_clusters
WHERE source_count >= 3
ORDER BY updated_at DESC
LIMIT 10;
```

#### Gemini vs Rule-Based Detection

Review 5-10 recent clusters (3+ sources) and manually check if `consensus_points` and `divergence_points` contain:
- **Gemini clusters:** Specific facts, quoted positions, contrasts ("X claims Y, Z counters with...")
- **Rule-based fallback:** Generic templates ("Coverage varies," "Sources maintain measured tone")

Count both types. If > 30% of 3+ source clusters are generic/rule-based, investigate Gemini availability.

#### Severity
- **Critical:** No clusters (pipeline failed) OR > 50% single-article clusters
- **Must Have:** > 80% of 3+ source clusters have Gemini summaries (not generic templates)
- **Nice to Have:** Source count mismatches > 1

#### Scoring
- 10/10: 5-50 clusters, 3-8 avg sources, < 10% single-article, all with Gemini summaries
- 8/10: 5-50 clusters, 2-8 avg sources, < 15% single-article
- 6/10: < 5 clusters OR > 20% single-article OR 30-50% without summaries
- 3/10: > 50% single-article OR > 50% without summaries
- 0/10: No clusters

---

### 5. Enrichment Quality — /10

**Requirement:** Cluster-level bias aggregation, consensus/divergence consensus, and editorial metadata are populated.

#### Checks
| Check | Expected | Query |
|-------|----------|-------|
| bias_diversity JSONB populated | > 95% of clusters | `SELECT COUNT(*) FILTER (WHERE bias_diversity IS NOT NULL AND bias_diversity != '{}') FROM story_clusters` |
| divergence_score > 0 | > 80% of clusters | `SELECT COUNT(*) FILTER (WHERE divergence_score > 0) FROM story_clusters` |
| headline_rank has variance | stddev > 5 | `SELECT STDDEV(headline_rank) FROM story_clusters` |
| coverage_velocity populated | > 90% | `SELECT COUNT(*) FILTER (WHERE coverage_velocity IS NOT NULL) FROM story_clusters` |
| editorial_importance set (1-10) | > 80% of clusters | `SELECT COUNT(*) FILTER (WHERE editorial_importance BETWEEN 1 AND 10) FROM story_clusters` |

#### SQL
```sql
-- Enrichment coverage
SELECT
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE bias_diversity IS NOT NULL AND bias_diversity != '{}') as with_bias_diversity,
  COUNT(*) FILTER (WHERE divergence_score > 0) as with_divergence_score,
  COUNT(*) FILTER (WHERE coverage_velocity IS NOT NULL) as with_coverage_velocity,
  COUNT(*) FILTER (WHERE editorial_importance BETWEEN 1 AND 10) as with_editorial_importance
FROM story_clusters;

-- Headline rank distribution (should vary)
SELECT
  COUNT(*) as total,
  MIN(headline_rank) as min_rank,
  MAX(headline_rank) as max_rank,
  AVG(headline_rank) as avg_rank,
  STDDEV(headline_rank) as stddev_rank
FROM story_clusters;

-- Check bias_diversity structure (sample)
SELECT
  id,
  title,
  bias_diversity,
  divergence_score
FROM story_clusters
WHERE bias_diversity IS NOT NULL
ORDER BY updated_at DESC
LIMIT 3;
```

#### Severity
- **Critical:** < 50% with bias_diversity OR < 50% with divergence_score > 0
- **Must Have:** headline_rank stddev < 2 (suggests ranking broken)
- **Nice to Have:** < 80% with editorial_importance

#### Scoring
- 10/10: > 95% bias_diversity, > 90% divergence_score > 0, stddev headline_rank > 10
- 8/10: 85-95% bias_diversity, 80-90% divergence_score > 0
- 6/10: 70-85% bias_diversity OR 60-80% divergence_score > 0
- 3/10: 50-70% OR headline_rank stddev < 2
- 0/10: < 50% populated

---

### 6. Temporal Freshness — /10

**Requirement:** Data is current and pipeline runs are reliable.

#### Checks
| Check | Good | Warning | Critical |
|-------|------|---------|----------|
| Most recent article | < 12h | 12-24h | > 24h |
| Most recent cluster | < 6h | 6-24h | > 24h |
| Most recent pipeline run | completed | in progress | failed |
| Last run duration | 25-40 min | 40-60 min | > 60 min or < 10 min |
| Pipeline run frequency | exactly 6h apart | within 7h | > 8h gap |
| Articles > 7 days old | < 30% | 30-50% | > 50% |
| Daily briefs: latest per edition | present | partial | missing |
| Audio briefs generated | yes | sometimes | no |

#### SQL
```sql
-- Temporal overview
SELECT
  MAX(published_at) as latest_article,
  NOW() - MAX(published_at) as article_age,
  MAX(updated_at) as latest_cluster,
  NOW() - MAX(updated_at) as cluster_age
FROM articles, story_clusters;

-- Pipeline health (last 10 runs)
SELECT
  created_at,
  status,
  articles_fetched,
  articles_analyzed,
  clusters_created,
  duration_seconds,
  LEAD(created_at) OVER (ORDER BY created_at DESC) - created_at as time_since_previous
FROM pipeline_runs
ORDER BY created_at DESC
LIMIT 10;

-- Article age distribution
SELECT
  COUNT(*) FILTER (WHERE published_at > NOW() - INTERVAL '1 day') as last_24h,
  COUNT(*) FILTER (WHERE published_at > NOW() - INTERVAL '7 days') as last_7d,
  COUNT(*) FILTER (WHERE published_at <= NOW() - INTERVAL '7 days') as older_than_7d
FROM articles;

-- Daily briefs check
SELECT
  edition,
  tldr_text,
  audio_url,
  created_at
FROM daily_briefs
ORDER BY edition, created_at DESC;
```

#### Severity
- **Critical:** Most recent article > 48h old OR last pipeline run failed
- **Must Have:** Pipeline runs consistently > 2h apart (indicates stuck pipeline or scheduling issue)
- **Nice to Have:** Audio briefs not generated

#### Scoring
- 10/10: Latest article < 6h, all pipeline runs completed < 7h apart, < 20% articles > 7d old
- 8/10: Latest article < 12h, all runs < 8h apart
- 6/10: Latest article < 24h, some runs > 8h apart
- 3/10: Latest article > 24h OR runs > 12h apart OR > 50% articles > 7d old
- 0/10: Latest article > 48h OR no recent pipeline runs

---

### 7. Referential Integrity — /10

**Requirement:** Foreign key relationships are valid and no orphaned data exists.

#### Checks
| Check | Expected | Query |
|-------|----------|-------|
| No orphaned articles (not in any cluster) | 0 | `SELECT COUNT(*) FROM articles a WHERE NOT EXISTS (SELECT 1 FROM cluster_articles ca WHERE ca.article_id = a.id)` |
| No orphaned bias scores | 0 | `SELECT COUNT(*) FROM bias_scores b WHERE NOT EXISTS (SELECT 1 FROM articles a WHERE a.id = b.article_id)` |
| No orphaned cluster_articles (cluster or article deleted) | 0 | Check foreign key constraints |
| All cluster_articles reference valid clusters | 100% | `SELECT COUNT(*) FROM cluster_articles ca WHERE NOT EXISTS (SELECT 1 FROM story_clusters sc WHERE sc.id = ca.cluster_id)` |
| All cluster_articles reference valid articles | 100% | `SELECT COUNT(*) FROM cluster_articles ca WHERE NOT EXISTS (SELECT 1 FROM articles a WHERE a.id = ca.article_id)` |
| No story_memory records with deleted clusters | 0 | `SELECT COUNT(*) FROM story_memory sm WHERE NOT EXISTS (SELECT 1 FROM story_clusters sc WHERE sc.id = sm.cluster_id)` |
| No live_updates records with deleted story_memory | 0 | `SELECT COUNT(*) FROM live_updates lu WHERE NOT EXISTS (SELECT 1 FROM story_memory sm WHERE sm.id = lu.story_memory_id)` |

#### SQL
```sql
-- Comprehensive integrity check
SELECT
  'orphaned_articles' as issue,
  COUNT(*) as count
FROM articles a
WHERE NOT EXISTS (SELECT 1 FROM cluster_articles ca WHERE ca.article_id = a.id)

UNION ALL

SELECT
  'orphaned_bias_scores',
  COUNT(*)
FROM bias_scores b
WHERE NOT EXISTS (SELECT 1 FROM articles a WHERE a.id = b.article_id)

UNION ALL

SELECT
  'orphaned_cluster_articles_bad_cluster',
  COUNT(*)
FROM cluster_articles ca
WHERE NOT EXISTS (SELECT 1 FROM story_clusters sc WHERE sc.id = ca.cluster_id)

UNION ALL

SELECT
  'orphaned_cluster_articles_bad_article',
  COUNT(*)
FROM cluster_articles ca
WHERE NOT EXISTS (SELECT 1 FROM articles a WHERE a.id = ca.article_id)

UNION ALL

SELECT
  'orphaned_story_memory',
  COUNT(*)
FROM story_memory sm
WHERE NOT EXISTS (SELECT 1 FROM story_clusters sc WHERE sc.id = sm.cluster_id);
```

#### Severity
- **Critical:** Any orphaned records > 0 (data corruption)
- **Must Have:** All foreign key constraints pass
- **Nice to Have:** N/A

#### Scoring
- 10/10: Zero orphaned records
- 0/10: Any orphaned records

---

### 8. Cross-Field Consistency — /10

**Requirement:** Bias scores align with source metadata and article properties.

#### Checks
| Check | Expected | Query |
|-------|----------|-------|
| Center baseline sources avg lean 40-60 | > 80% | `SELECT COUNT(*) FROM (...) WHERE lean BETWEEN 40 AND 60` / total |
| Center-left baseline avg lean 30-50 | > 80% | — |
| Center-right baseline avg lean 50-70 | > 80% | — |
| High-rigor sources (us_major) avg factual_rigor > low-rigor (independent) | yes | tier comparison |
| Opinion sections avg opinion_fact > 50 | > 80% | `WHERE section='opinion' AND opinion_fact > 50` |
| Source credibility_notes matches tier | mostly | manual spot-check |

#### SQL
```sql
-- Lean distribution by baseline
SELECT
  s.political_lean_baseline as baseline,
  AVG(b.political_lean) as avg_lean,
  COUNT(*) as count
FROM bias_scores b
JOIN articles a ON b.article_id = a.id
JOIN sources s ON a.source_id = s.id
WHERE s.is_active = true
GROUP BY s.political_lean_baseline
ORDER BY avg_lean;

-- Expected ranges for baseline
-- center: 40-60
-- center-left: 30-50
-- center-right: 50-70
-- left: 20-40
-- right: 60-80
-- far-left: 10-30
-- far-right: 70-90

-- Factual rigor by tier
SELECT
  s.tier,
  AVG(b.factual_rigor) as avg_rigor,
  STDDEV(b.factual_rigor) as sd_rigor,
  COUNT(*) as count
FROM bias_scores b
JOIN articles a ON b.article_id = a.id
JOIN sources s ON a.source_id = s.id
WHERE s.is_active = true
GROUP BY s.tier
ORDER BY avg_rigor DESC;

-- Opinion articles
SELECT
  COUNT(*) FILTER (WHERE opinion_fact > 50) as opinion_heavy,
  COUNT(*) as total
FROM bias_scores
WHERE article_id IN (
  SELECT id FROM articles WHERE section = 'opinion'
);
```

#### Severity
- **Critical:** < 60% of center baseline articles fall in 40-60 lean range
- **Must Have:** Tier ordering inverted (independent avg rigor > us_major)
- **Nice to Have:** Edge case misalignments

#### Scoring
- 10/10: > 90% of baselines match expected range, tier ordering correct
- 8/10: 80-90% match, tier ordering correct
- 6/10: 70-80% match OR minor tier inversion
- 3/10: 60-70% match OR clear baseline-lean mismatch
- 0/10: < 60% match

---

## OVERALL SCORE CALCULATION

```
Overall = (
  Domain1_score × 0.15 +  // Source Coverage (critical path)
  Domain2_score × 0.15 +  // Article Quality (critical path)
  Domain3_score × 0.20 +  // Bias Score Quality (core deliverable)
  Domain4_score × 0.15 +  // Cluster Quality (core deliverable)
  Domain5_score × 0.10 +  // Enrichment Quality
  Domain6_score × 0.10 +  // Temporal Freshness
  Domain7_score × 0.10 +  // Referential Integrity
  Domain8_score × 0.05    // Cross-Field Consistency
) / 10 * 100

Range: 0-100
Grading:
  90-100: Excellent (production-ready)
  80-89:  Good (minor gaps acceptable)
  70-79:  Fair (some manual review needed)
  60-69:  Poor (immediate remediation needed)
  < 60:   Critical (halt operations)
```

---

## Report Template

```
DATA QUALITY REPORT
Date: [YYYY-MM-DD HH:MM UTC]
Reporter: db-reviewer agent

OVERALL SCORE: [N]/100 — [Grade]

DOMAIN SCORES:
  Source Coverage:        [N]/10
  Article Quality:        [N]/10
  Bias Score Quality:     [N]/10
  Cluster Quality:        [N]/10
  Enrichment Quality:     [N]/10
  Temporal Freshness:     [N]/10
  Referential Integrity:  [N]/10
  Cross-Field Consistency: [N]/10

CRITICAL FINDINGS:
  [if any]
  1. [Finding] — [Impact] — [Remediation]

STATISTICS:
  Sources: [N] active / 951 expected
  Articles: [N] total, [N] with full_text, [N] with published_at
  Bias Scores: [N] total, [N] defaults, confidence distribution
  Clusters: [N] total, [N] single-article, avg [N.N] articles/cluster
  Pipeline Runs: [N] total, last [duration]m on [timestamp]
  Last Article: [age] ago
  Last Cluster: [age] ago

THE ONE THING:
[Single highest-impact improvement that would most improve overall quality]

NEXT STEPS:
1. [Priority 1 remediation]
2. [Priority 2 remediation]
3. [Priority 3 improvement]
```

---

## How to Use This Framework

### For Automated CI Audits (validate-bias.yml)
Run subset of checks post-pipeline on every merged PR or scheduled:
```bash
# Pseudo-code (implement in audit.py)
python pipeline/audit_database.py \
  --check sources \
  --check articles \
  --check bias_scores \
  --check clusters \
  --output json
```

### For Manual Audits (db-reviewer agent)
Full 8-domain audit, once per week:
```bash
# Read-only queries against Supabase
# Generate report following template
# Flag any CRITICAL findings for immediate action
```

### For On-Demand Diagnostics
When a specific domain shows degradation:
```bash
# Run relevant SQL queries
# Identify root cause
# Recommend fixes (don't apply without approval)
```

---

## Known Data Patterns & Thresholds

### Article Ingestion
- **4x daily runs:** Expect 200-400 new articles per run (80-120 per source average across 951 sources)
- **Duplication rate:** TF-IDF cosine 0.80 threshold removes ~15-20% of raw fetch
- **Scrape success rate:** 85-95% (some RSS summaries retained as fallback)
- **Section distribution:** World (60%), US (30%), India (10%)

### Bias Scoring
- **Axis distributions (expected)**
  - Political Lean: mean 45-55, stddev 15-20 (center-biased corpus)
  - Sensationalism: mean 25-35, stddev 12-18
  - Opinion vs Fact: mean 20-30, stddev 10-15
  - Factual Rigor: mean 50-60, stddev 15-20 (tier-dependent: us_major > intl > indep)
  - Framing: mean 30-40, stddev 12-18

- **Confidence (typical)**
  - Mean: 0.65-0.75
  - Should NOT cluster at 0.7 (suggests default)
  - Long articles (500+ words): confidence > 0.75
  - Short articles (< 100 words): confidence < 0.60

### Clustering
- **Expected cluster count per run:** 10-50 total
- **Average articles per cluster:** 3-8 (rule-based 2-phase clustering)
- **Single-article clusters:** 10-20% (articles that don't match others)
- **Gemini summarization:** 3+ source clusters prioritized; 25-call budget typical
- **Summary quality:** Gemini clusters have specific facts + divergence; rule-based have generic templates

### Daily Briefs
- **Update frequency:** 4x daily (one per pipeline run)
- **Editions:** world, us, india (world always run; us/india conditional)
- **TL;DR:** 3-5 sentences, 150-220 words
- **Audio:** Generated from 2-host script only when Gemini available (not on 00:00, 12:00 UTC text-only runs)

---

## Common Issues & Remediation

| Issue | Root Cause | Check | Fix |
|-------|-----------|-------|-----|
| NULL full_text > 20% | Web scraper failures | RSS logs | Increase scraper timeout, add fallback URLs |
| All confidence = 0.7 | Confidence calc disabled | Check bias_score generation | Re-run analysis with confidence logic |
| < 80% bias_diversity populated | Gemini unavailable | GEMINI_API_KEY in env | Check API quota, re-run cluster enrichment RPC |
| > 50% single-article clusters | Clustering threshold too high | Adjust TF-IDF threshold | Re-run clustering on latest articles |
| Orphaned articles | Manual data deletion or failed cleanup | Run cleanup RPC | `SELECT cleanup_stale_clusters();` |
| Pipeline runs > 60 min | Performance degradation | Check worker count, article count | Optimize analyzer workers, re-profile |

---

## Related Documents
- `CLAUDE.md` — Full architecture, pipeline flow, tech stack
- `pipeline/validation/runner.py` — Bias engine regression testing (100% accuracy)
- `pipeline/main.py` — Pipeline orchestrator (steps 1-10)
- `supabase/migrations/` — Schema definition and evolution

---

**Last Verified:** 2026-03-31
**Next Review:** TBD (scheduled for db-reviewer agent)
