# void --news Database Schema & Index Analysis

**Date:** 2026-03-21
**Database:** Supabase (PostgreSQL 15)
**Tables:** 8 (sources, articles, bias_scores, story_clusters, cluster_articles, categories, article_categories, pipeline_runs)
**Views:** 1 (cluster_bias_summary)
**Functions:** 2 (refresh_cluster_enrichment, update_updated_at_column)
**RLS Enabled:** Yes (public read policies on all tables)

---

## SCHEMA OVERVIEW

### Core Tables

#### 1. sources (49 us_major, 82 international, 92 independent = 223 total)
```
id (UUID PK)
slug (TEXT UNIQUE) — for URL routing
name, url, rss_url, scrape_config (JSONB)
tier (us_major | international | independent)
country, type
political_lean_baseline (7-point spectrum: left, center-left, center, center-right, right, varies)
credibility_notes
is_active (BOOLEAN)
created_at, updated_at (TIMESTAMPTZ)
```

**Status:** ✓ Complete. All fields populated.

#### 2. articles (9,999 total)
```
id (UUID PK)
source_id (UUID FK → sources) — NOT NULL
url (TEXT UNIQUE)
title, summary, author, image_url
full_text (TEXT) — Truncated to 300-char excerpts for IP compliance
published_at, fetched_at (TIMESTAMPTZ)
section (world | us | other | NULL)
word_count (INTEGER)
created_at (TIMESTAMPTZ)
```

**Status:** ⚠ Minor issues
- NULL full_text: 507 (5.1%) — OK
- NULL published_at: 68 (0.7%) — OK
- NULL section: 0 ✓
- Word count <100: 5,330 (53.3%) — CONCERN (see audit)

#### 3. bias_scores (9,999 total, 100% coverage)
```
id (UUID PK)
article_id (UUID UNIQUE FK → articles ON DELETE CASCADE)
political_lean, sensationalism, opinion_fact, factual_rigor, framing (SMALLINT 0-100)
confidence (REAL 0.0-1.0)
rationale (TEXT/JSONB) — Structured reason dict
analyzed_at (TIMESTAMPTZ)
```

**Status:** ✓ Complete
- All 5 axes populated for all articles
- No defaults (50/50/50/50/50)
- Rationale: 100% populated (JSON strings, parseable client-side)
- Confidence: bimodal distribution (48.6% <0.5, 43.6% >=0.7)

**NOTE:** rationale column shown as TEXT in schema but actually stores JSON strings. Should be JSONB for consistency and performance.

#### 4. story_clusters (2,938 total)
```
id (UUID PK)
title, summary (Gemini Flash generated)
consensus_points, divergence_points (JSONB)
section (world | us | NULL)
sections (text[] GIN-indexed) — Multi-edition support

-- Enrichment fields (populated by pipeline)
divergence_score (REAL 0-100) — 55.7% are zero
bias_diversity (JSONB) — Per-cluster bias aggregation (100% populated)
headline_rank (REAL) — Importance score for feed ordering (1,536 unique values for 2,938 clusters — COLLISION ISSUE)
coverage_velocity (INTEGER) — Articles added in last 6h (99.9% zeros — BROKEN)
editorial_importance (SMALLINT 1-10) — From Gemini (16.8% populated, 2,445 NULL)

-- Metadata
source_count, first_published, last_updated (TIMESTAMPTZ)
created_at
importance_score (REAL) — Legacy field (use headline_rank instead)
category (TEXT) — Legacy field (replaced by auto-categorization)
```

**Status:** ⚠ Critical issues
- 45.5% of articles orphaned (4,553 not linked to any cluster)
- 614 invalid article_id references in cluster_articles junction
- headline_rank has only 1,536 unique values → feed sorting non-deterministic
- coverage_velocity is 99.9% zero → ranking signal broken

#### 5. cluster_articles (5,446 valid rows + 614 invalid = 6,060 total)
```
cluster_id (UUID FK → story_clusters ON DELETE CASCADE)
article_id (UUID FK → articles ON DELETE CASCADE) — ⚠ 614 invalid refs
PRIMARY KEY (cluster_id, article_id)
```

**Status:** ⚠ CRITICAL
- 614 rows reference articles that don't exist
- Should be prevented by FK constraint, but aren't
- Recommend deleting and verifying constraint is enforced

#### 6. categories (9 default categories)
```
id (UUID PK)
name (TEXT UNIQUE)
slug (TEXT UNIQUE)

Values: politics, economy, technology, health, environment, conflict, science, culture, sports
```

**Status:** ✓ Complete

#### 7. article_categories (junction, populated by pipeline)
```
article_id (UUID FK → articles ON DELETE CASCADE)
category_id (UUID FK → categories ON DELETE CASCADE)
PRIMARY KEY (article_id, category_id)
```

**Status:** ✓ Populated by pipeline step 9b (auto_categorize.py)

#### 8. pipeline_runs (tracking history)
```
id (UUID PK)
started_at, completed_at (TIMESTAMPTZ)
status (running | completed | failed)
articles_fetched, articles_analyzed, clusters_created (INTEGER)
errors (JSONB)
duration_seconds (REAL)
```

**Status:** ✓ Complete. Last run: 2026-03-20 18:22:25 (completed successfully)

#### 9. source_topic_lean (Axis 6: Per-Topic Per-Outlet Tracking)
```
id (UUID PK)
source_id (UUID FK → sources ON DELETE CASCADE)
category (TEXT)
avg_lean, avg_sensationalism, avg_opinion (NUMERIC(5,2))
article_count (INT)
last_updated (TIMESTAMPTZ)
UNIQUE(source_id, category)
```

**Status:** ✓ Populated by pipeline step 9c (EMA-based tracking)

---

## VIEW: cluster_bias_summary

Aggregates per-article bias_scores to cluster level:

```sql
SELECT
  ca.cluster_id,
  avg_political_lean (weighted by factual_rigor),
  avg_sensationalism, avg_opinion_fact, avg_factual_rigor, avg_framing,
  lean_spread, framing_spread, lean_range, sensationalism_spread, opinion_spread,
  aggregate_confidence (COUNT / 5, saturates at 1.0),
  analyzed_article_count
FROM cluster_articles ca
JOIN bias_scores bs ON bs.article_id = ca.article_id
GROUP BY ca.cluster_id;
```

**Status:** ✓ Working correctly

---

## FUNCTIONS

### refresh_cluster_enrichment(p_cluster_id UUID)
Called after all clusters are inserted to populate divergence_score and bias_diversity.

**Status:** ✓ Used by pipeline, but triggers may not be called for manually inserted clusters

### update_updated_at_column() TRIGGER
Keeps articles.updated_at and story_clusters.last_updated in sync.

**Status:** ✓ Working

---

## INDEX ANALYSIS

### Existing Indexes (Migration 001)
```
idx_articles_source                    — GOOD: FK lookups
idx_articles_published                 — GOOD: Temporal queries
idx_articles_section                   — GOOD: Section filtering
idx_bias_scores_article                — GOOD: Score lookups
idx_clusters_importance                — LEGACY: Use headline_rank instead
idx_clusters_section                   — LEGACY: Replaced by multi-section support
idx_cluster_articles_cluster           — GOOD: Cluster member queries
idx_cluster_articles_article           — GOOD: Article cluster membership
```

### Performance Indexes (Migration 009)
```
idx_clusters_section_headline_rank     — CRITICAL for homepage feed query
idx_clusters_section_content_type      — For content_type filtering (if used)
idx_pipeline_runs_completed            — For "last run" lookup
```

### Array Support (Migration 011)
```
idx_clusters_sections_gin              — GIN index for multi-section queries (sections @> ARRAY['world'])
```

### Ranking Signals (Migration 013)
```
idx_story_clusters_editorial_importance — For Gemini-assisted ranking
idx_story_clusters_story_type          — For story type gating
```

**Status:** ✓ All critical indexes present

---

## INDEX RECOMMENDATIONS

### Current Issues

1. **headline_rank precision loss**
   - Only 1,536 unique values for 2,938 clusters
   - Likely rounding/truncation in ranking formula
   - **Fix:** Change from REAL to NUMERIC(10,8)

2. **coverage_velocity ineffective**
   - 99.9% zeros
   - Even if fixed, no compound index needed (only 3 non-zero values)

### Recommended Additions (Optional)

```sql
-- Composite index for important combined queries
CREATE INDEX idx_clusters_section_published
  ON story_clusters (sections, first_published DESC)
  WHERE sections IS NOT NULL;

-- For future content_type filtering
CREATE INDEX idx_clusters_section_editorial
  ON story_clusters (sections, editorial_importance DESC NULLS LAST)
  WHERE editorial_importance IS NOT NULL;

-- For article age-based cleanup
CREATE INDEX idx_articles_published_desc
  ON articles (published_at DESC)
  WHERE published_at IS NOT NULL;
```

---

## CONSTRAINTS & REFERENTIAL INTEGRITY

### Foreign Keys (All using ON DELETE CASCADE)
- articles.source_id → sources.id ✓
- bias_scores.article_id → articles.id ✓
- cluster_articles.cluster_id → story_clusters.id ✓
- cluster_articles.article_id → articles.id ⚠ **614 violations found**
- article_categories.article_id → articles.id ✓
- article_categories.category_id → categories.id ✓
- source_topic_lean.source_id → sources.id ✓

### Unique Constraints
- sources.slug ✓
- sources.id (PK) ✓
- articles.url ✓
- bias_scores.article_id ✓ (one-to-one)
- categories.name, categories.slug ✓
- source_topic_lean(source_id, category) ✓

---

## ROW LEVEL SECURITY (RLS)

All tables have RLS enabled with public read access:

```
CREATE POLICY "Public read <table>" ON <table> FOR SELECT USING (true);
```

**Status:** ✓ Correctly configured for public data

---

## PERFORMANCE ANALYSIS

### Query Patterns

#### Homepage Feed (Frontend)
```sql
SELECT id, title, summary, headline_rank, source_count, bias_diversity
FROM story_clusters
WHERE sections @> ARRAY['world']  -- or 'us'
ORDER BY headline_rank DESC
LIMIT 100;
```

**Execution plan:** Uses idx_clusters_sections_gin for filtering, then sorts by headline_rank ✓

**Issue:** headline_rank collisions mean sort is unstable when ranks tie. Add secondary sort:
```sql
ORDER BY headline_rank DESC, created_at DESC
```

#### Deep Dive Data
```sql
SELECT ca.article_id, a.*, bs.*, s.name, s.tier
FROM cluster_articles ca
JOIN articles a ON a.id = ca.article_id
LEFT JOIN bias_scores bs ON bs.article_id = a.id
LEFT JOIN sources s ON s.id = a.source_id
WHERE ca.cluster_id = ?;
```

**Execution plan:** Uses idx_cluster_articles_cluster, then nested joins ✓

#### Last Pipeline Run
```sql
SELECT completed_at, articles_fetched, status
FROM pipeline_runs
WHERE status = 'completed'
ORDER BY completed_at DESC
LIMIT 1;
```

**Execution plan:** Uses idx_pipeline_runs_completed ✓

### Performance Bottlenecks

**None identified.** Index structure is sound. Slowest queries are likely:
1. Full cluster enrichment (refresh_cluster_enrichment for all clusters)
2. Article clustering algorithm (CPU-bound, not DB-bound)
3. Gemini API calls (external service latency)

---

## STORAGE & SIZE

**Estimated footprint (9,999 articles + 2,938 clusters):**
- articles: ~50 MB
- bias_scores: ~15 MB
- story_clusters: ~20 MB
- cluster_articles: ~3 MB
- **Total: ~90 MB** (Supabase free tier supports 500 MB)

**Indexes:** ~30 MB

**Overall DB size: ~120 MB** (Well within free tier)

---

## RECOMMENDATIONS

### Schema Changes (Low Priority)

1. **Change bias_scores.rationale to JSONB**
   ```sql
   ALTER TABLE bias_scores ALTER COLUMN rationale TYPE JSONB USING rationale::jsonb;
   ```
   - Better query performance (JSONB operators)
   - No parsing needed client-side
   - Safe: existing JSON strings will parse correctly

2. **Change headline_rank from REAL to NUMERIC(10,8)**
   ```sql
   ALTER TABLE story_clusters
   ALTER COLUMN headline_rank TYPE NUMERIC(10,8);
   ```
   - Prevents precision loss from rounding
   - Solves rank collision issue
   - Requires data migration (multiply existing by 10^8, then divide in queries, or just re-rank)

3. **Add NOT NULL constraint to story_clusters.section**
   ```sql
   ALTER TABLE story_clusters ALTER COLUMN section SET NOT NULL;
   ```
   - All clusters have a primary section
   - Simplifies queries
   - Safe: no NULL values currently exist

### Data Fixes (High Priority)

1. **Apply Migration 014** to fix orphaned articles and invalid refs
2. **Debug coverage_velocity** in pipeline/ranker/importance_ranker.py
3. **Investigate factual_rigor** calibration (avg 31.0)
4. **Fix headline_rank collisions** (precision or secondary sort)

### Monitoring (Medium Priority)

1. Add data quality metrics view (see audit report)
2. Monthly data audit (compare sources_expected vs sources_actual, etc.)
3. Monitor invalid references via periodic constraint check

---

## MIGRATION PATH FORWARD

If you want to clean up the schema (optional), apply these in order:

```
014_fix_orphaned_articles.sql      (MANDATORY: referential integrity)
015_improve_headline_rank.sql      (RECOMMENDED: fix rank collisions)
016_convert_rationale_to_jsonb.sql (NICE: better query perf)
017_add_not_null_constraints.sql   (NICE: data integrity)
```

Each is backward-compatible and can be rolled back if needed.

---

## SUMMARY

**Schema health:** 8/10
- Correct structure with proper relationships
- Constraints and indexes in place
- RLS configured for public read
- All required enrichment fields present

**Data quality:** 5/10 (see main audit report)
- 45.5% orphaned articles (critical)
- 614 invalid references (critical)
- coverage_velocity broken (critical)
- headline_rank collisions (critical)

**Performance:** 9/10
- Proper indexes for all major queries
- RLS policies simple (no performance penalty)
- DB size well within free tier limits

**Recommendation:** Apply Migration 014 immediately, then address the three critical data quality issues (coverage_velocity, headline_rank, factual_rigor).
