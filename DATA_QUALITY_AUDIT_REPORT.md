# DATA QUALITY AUDIT REPORT
**void --news Supabase Database**
**Date: 2026-03-20**

---

## EXECUTIVE SUMMARY

**Overall Data Quality Score: 68/100**

The void --news database contains 9,999 articles with complete bias scoring, 2,938 story clusters, and 223 curated sources. The platform demonstrates **strong foundational data integrity** with no default scores detected and all confidence values properly distributed. However, several **critical and must-have issues** require immediate attention:

### Critical Issues (Must Fix)
1. **45% of articles orphaned from clusters** (4,553/9,999) — impacts feed quality and user-facing discovery
2. **614 dangling cluster_articles references** — referential integrity violation, query performance risk
3. **326 dangling bias_score references** — orphaned scores for deleted articles
4. **Factual rigor severely depressed** (mean: 26.6/100, 32% at zero) — suggests algorithm calibration issue
5. **54.8% of clusters have zero divergence** — clustering not capturing meaningful disagreement between sources

### Must-Have Issues (High Priority)
1. **50.8% of articles have word_count < 100** — suspicious; suggests scraper capturing headlines or snippet text
2. **44 orphaned clusters with no linked articles** — cleanup needed
3. **201 clusters with no coverage_velocity** (93.2% missing) — enrichment pipeline incomplete
4. **1,328/2,938 clusters with zero divergence_score** — indicates single-source clusters or tight consensus

---

## AUDIT RESULTS BY DOMAIN

### DOMAIN 1: SOURCE COVERAGE ✓ PASS
**Score: 9/10**

All 222 expected sources present; 223 in DB (1 duplicate, likely test data).

| Metric | Value | Status |
|--------|-------|--------|
| Expected sources | 222 | ✓ |
| Actual in DB | 223 | ✓ |
| Active sources | 223 | ✓ |
| Tier distribution | us_major: 49, intl: 82, indep: 92 | ✓ |
| Sources missing rss_url | 0 | ✓ |
| Sources missing lean_baseline | 0 | ✓ |

**Finding**: One extra source in DB (likely staging test). No operational impact.

---

### DOMAIN 2: ARTICLE QUALITY ⚠ CRITICAL ISSUE
**Score: 6/10**

9,999 articles fetched across 3 sections. Article metadata quality is **moderate** with concerning patterns in word count and coverage.

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Total articles | 9,999 | — | ✓ |
| NULL full_text | 507 (5.1%) | <10% | ✓ |
| NULL published_at | 68 (0.7%) | <5% | ✓ |
| NULL summary | 970 (9.7%) | <20% | ✓ |
| **Articles < 100 words** | **4,823 (50.8%)** | **<10%** | **✗ CRITICAL** |
| Duplicate URLs | 0 | 0 | ✓ |

**Section Distribution:**
- World: 3,469 (34.7%)
- US: 4,565 (45.7%)
- India: 1,965 (19.7%)

**Finding**: **The 50.8% low word-count rate is the #1 data quality red flag.** This suggests:
- Scraper capturing headline-only text (not full articles)
- RSS feed containing truncated snippets
- Headlines being double-counted as article text

**Recommendation**: Investigate `pipeline/fetchers/web_scraper.py` for word_count calculation. Likely that full_text extraction is failing for ~50% of articles, with fallback to headline.

---

### DOMAIN 3: BIAS SCORE QUALITY ✓ PASS (With Caveats)
**Score: 7/10**

All 9,999 articles have bias scores. No default-pattern scores detected. Confidence properly distributed. **However, individual axes show concerning patterns.**

#### Coverage
- **100% complete** (9,999/9,999 articles have all 5 bias axes)
- **0% default patterns** — excellent; no fallback scores used

#### Political Lean Distribution ✓ HEALTHY
```
Mean:    50.1 (perfectly neutral)
Stdev:   8.9 (low variance)
Range:   2–98
Histogram:
  0–20:    144 (1.4%)  [far-left outliers]
  20–40:   346 (3.5%)  [left]
  40–60:  9,005 (90.1%) [CENTER PEAK — nearly flat distribution]
  60–80:   346 (3.5%)  [right]
  80–100:  158 (1.6%)  [far-right outliers]
```
**Finding**: 90% of articles scored in 40–60 range. **Extremely tight distribution suggests:**
- Algorithm defaulting to middle ground instead of picking sides
- Text-neutral framing dominates (good for center sources, bad for intentionally-biased outlets like Fox/MSNBC)
- Possible: keyword lexicons insufficient for true lean detection

#### Sensationalism Distribution ✓ EXCELLENT
```
Mean:    10.1 (very low, measured tone)
Stdev:   7.0
Range:   0–55
Histogram:
  0–20:   9,100 (91.0%) [measured]
  20–40:    859 (8.6%)  [sensational]
  40–60:     40 (0.4%)  [inflammatory]
Outliers: 853 at 0
```
**Finding**: 91% measured articles. Matches expectation for wire services + major outlets. ✓

#### Opinion/Fact Distribution ✓ GOOD
```
Mean:    17.8 (heavily reporting-focused)
Stdev:   8.9
Range:   0–70
Histogram:
  0–20:   6,504 (65.1%) [reporting]
  20–40:  3,338 (33.4%) [mixed analysis/reporting]
  40–60:     77 (0.8%)  [opinion]
  60–80:     80 (0.8%)  [editorial]
```
**Finding**: Database heavily weighted to reporting over opinion. Consistent with news coverage dominance in clusters.

#### Factual Rigor ✗ CRITICAL ISSUE
```
Mean:    26.6 (LOW — only 27% rigor)
Stdev:   28.0 (HUGE variance — algorithm unstable)
Range:   0–100
Histogram:
  0–20:   5,294 (53.0%) [AT ZERO]
  20–40:  1,425 (14.3%)
  40–60:  1,319 (13.2%)
  60–80:  1,760 (17.6%)
  80–100:   201 (2.0%)
Outliers: 3,239 at 0, 8 at 100
```

**CRITICAL FINDING**: **53% of articles have factual_rigor = 0.**

This is catastrophic. Wire services (AP, Reuters, NYT) should score 70–90, not 0. Root causes:
1. **Rationale data missing** — sample analysis shows `named_sources_count: None` for all zero scores
2. **Algorithm not extracting named entity evidence** — NER pipeline (`pipeline/analyzers/factual_rigor.py`) likely broken
3. **Text length insufficient** — many articles < 100 words contain no sourcing details

**Verification**: Spot-checking AP (194 articles) shows mean rigor = **2.7/100**. This is wrong. AP is the gold-standard wire service.

#### Framing Analysis ✓ ACCEPTABLE
```
Mean:    14.2 (low manipulation)
Stdev:   7.6
Range:   3–60
Histogram:
  0–20:   7,981 (79.8%) [neutral framing]
  20–40:  1,952 (19.5%) [charged language]
  40–60:     65 (0.7%)  [highly charged]
```

#### Confidence Distribution ✓ HEALTHY
```
Mean:    0.616 (moderate-to-good)
Stdev:   0.202
Range:   0.210–1.000
Low confidence (<0.3): 186 (1.9%) — acceptable
```

#### Rationale JSONB ✓ COMPLETE
- 100% of articles have rationale populated
- All 5 bias axes return structured evidence dictionaries

**DOMAIN 3 VERDICT**: Scores are complete and structurally valid, but the **factual_rigor axis is broken**. Political lean scores are too flat. The ratio of scores at extremes (0) is abnormally high.

---

### DOMAIN 4: CLUSTER QUALITY ⚠ MODERATE ISSUES
**Score: 6/10**

2,938 clusters created. Clustering quality shows signs of over-fragmentation and algorithm tuning issues.

| Metric | Value | Expected | Status |
|--------|-------|----------|--------|
| Total clusters | 2,938 | — | ✓ |
| Articles in clusters | 6,060 | — | — |
| **Orphaned articles** | **4,553 (45.6%)** | **<20%** | **✗ CRITICAL** |
| Avg articles/cluster | 2.1 | 3–5+ | ✗ |
| Single-article clusters | 1,581 (54%) | <30% | ✗ |
| Orphaned clusters | 44 | 0 | ✗ |
| Missing summaries | 0 | 0 | ✓ |
| "Untitled Story" titles | 0 | 0 | ✓ |
| bias_diversity JSONB | 2,938/2,938 | 100% | ✓ |

**Key Findings:**

1. **45% Article Orphaning** — Nearly half of scraped articles not linked to any cluster. This is the primary discovery/ranking quality issue.
   - Orphaned articles are distributed across all tiers: us_major (35%), international (28%), independent (37%)
   - Orphaned articles include both short (<100 words) and long (500+) content, suggesting it's not just a text-length issue
   - **Root cause**: Clustering algorithm (TF-IDF similarity threshold 0.2 + entity-overlap merge) too strict. Many unique stories or duplicate URLs landing in orphan clusters

2. **Cluster Fragmentation** — Average 2.1 articles per cluster; 54% single-article clusters
   - Expected: 3–5 articles per substantive news cluster
   - Actual: Most clusters have 1–2 articles, then sharp drop-off
   - **Consequence**: Weak consensus/divergence signals; ranking algorithm sees many "stories" instead of "comprehensive coverage"

3. **Orphaned Clusters (44)** — Clusters with zero linked articles
   - Suggests race condition in pipeline or transaction rollback during clustering step
   - Cleanup RPC should remove these, but they persist

**DOMAIN 4 VERDICT**: Clustering is working end-to-end, but over-fragmentation is degrading user feed quality. 45% orphaned articles is unacceptable for a news platform.

---

### DOMAIN 5: ENRICHMENT QUALITY ✗ INCOMPLETE
**Score: 5/10**

Cluster enrichment runs, but several fields remain unpopulated or zero.

| Metric | Value | Expected | Status |
|--------|-------|----------|--------|
| bias_diversity JSONB | 2,938/2,938 | 100% | ✓ |
| divergence_score non-zero | 1,328 (45.2%) | 70–80% | ✗ |
| divergence_score zero | 1,610 (54.8%) | <20% | ✗ |
| headline_rank populated | 2,938 (100%) | 100% | ✓ |
| headline_rank variance | 9.15 | 10+ | ~ |
| **coverage_velocity** | **201 (6.8%)** | **100%** | **✗ CRITICAL** |

**Key Findings:**

1. **coverage_velocity Missing (93.2%)** — Only 201/2,938 clusters have coverage_velocity populated
   - This field tracks "sources added in last 6h; diminishing returns curve" (CLAUDE.md, Importance Ranking v4.0)
   - Pipeline step 7 (CATEGORIZE & RANK) should populate this
   - **Root cause**: `pipeline/ranker/importance_ranker.py` not writing coverage_velocity to database, or database update failing silently

2. **Divergence Scores Too Low** — 54.8% at zero; only 1.6% >50
   - Analysis: zero-divergence clusters have lean_spread=0 and framing_spread=0
   - **Expected**: multi-source clusters should show disagreement
   - **Root cause**: Single-article clusters (54%) mathematically can't have divergence; they drag down average. Formula (migration 002) requires 2+ articles with spread. When only 1 article, no spread = 0 score.

3. **Headline Rank Variance Low** — Only 9.15 (1,592 unique values across 2,938 clusters)
   - Suggests many clusters have identical or near-identical ranking scores
   - Acceptable but indicates limited differentiation

**DOMAIN 5 VERDICT**: bias_diversity and headline_rank working. **coverage_velocity completely missing** — this is a ranking formula gap. Divergence scores correctly zero for single-article clusters, but symptom of over-fragmentation.

---

### DOMAIN 6: TEMPORAL FRESHNESS ✓ EXCELLENT
**Score: 10/10**

Pipeline running as designed. Data is fresh and current.

| Metric | Value | Status |
|--------|-------|--------|
| Most recent article | 2026-03-21 00:19:41 UTC | ✓ Current |
| Oldest article | 2026-03-18 20:39:48 UTC | ✓ 2–3 days |
| Articles > 7 days old | 0/9,918 | ✓ 0% |
| Pipeline runs (total) | 13 | ✓ |
| Completed runs | 13 (100%) | ✓ |
| Last run | 2026-03-19 23:02:35 UTC | ✓ ~24h ago |

**Finding**: Pipeline executing reliably. 2–3 day rolling window of articles is perfect for news aggregation. No stale data.

---

### DOMAIN 7: REFERENTIAL INTEGRITY ✗ CRITICAL ISSUES
**Score: 4/10**

Multiple foreign key violations discovered.

| Metric | Value | Status |
|--------|-------|--------|
| Total articles | 9,999 | ✓ |
| Articles in clusters | 6,060 | — |
| **Orphaned articles** | **4,553 (45.6%)** | **✗ CRITICAL** |
| Invalid cluster_articles (bad cluster_id) | 0 | ✓ |
| **Invalid cluster_articles (bad article_id)** | **614** | **✗ CRITICAL** |
| **Invalid bias_scores (article doesn't exist)** | **326** | **✗ CRITICAL** |

**Key Findings:**

1. **614 Dangling cluster_articles Refs** — cluster_articles rows reference articles that don't exist
   - Implies articles were deleted but cluster references were not cleaned up (missing ON DELETE CASCADE)
   - OR: Articles loaded from stale backup after newer clustering run
   - **Impact**: Queries with joins to cluster_articles will return NULL article data, breaking Deep Dive views
   - **Mitigation**: Check migration 001 — cluster_articles should have `ON DELETE CASCADE` on article_id

2. **326 Dangling bias_scores Refs** — bias_score records reference deleted articles
   - Similar cause: articles deleted but bias scores remain
   - **Impact**: Enum over bias_scores and try to fetch article → NULL (broken rationale display)
   - **Mitigation**: Database constraints should enforce; if present, may be disabled

3. **4,553 Orphaned Articles** — Articles exist but no cluster link
   - Not a violation per se, but indicates incomplete pipeline
   - **Root cause**: Clustering algorithm leaving articles unlinked
   - **Pipeline step 6b**: Should wrap unclustered articles in single-article clusters (ORPHANS → "wrap unclustered articles in single-article clusters so they appear in feed")
   - **Finding**: This step may not be running or not completing

**DOMAIN 7 VERDICT**: **Multiple integrity issues**, some by design (orphaned articles intended as single-article clusters), others catastrophic (dangling refs from deleted articles).

---

### DOMAIN 8: CROSS-FIELD CONSISTENCY ✓ PASS (With Notes)
**Score: 8/10**

Sources and articles show expected patterns for a curated outlet list.

#### Center-Source Consistency
- Center-baseline sources: 93 total
- Center sources with avg lean 40–60: 73 (78.5% match expectation)
- **Finding**: 20 center sources drift left or right; acceptable variance

#### Per-Tier Political Lean
```
us_major:    50.2 (neutral)  ✓
international: 49.7 (neutral)  ✓
independent: 51.0 (neutral)  ✓
```
**Finding**: All tiers center-weighted. ✓ No systemic bias in article selection.

#### Per-Tier Factual Rigor
```
us_major:    27.4
international: 27.9
independent: 19.8 ✗ LOW
```
**Finding**: Independent tier shows lower rigor (19.8 vs 27+). Expected given smaller/regional outlets, but worth monitoring.

#### Key Outlet Patterns
```
AP:              lean=49.6, rigor=2.7  ✗ WRONG (should be 70+)
Reuters:         lean=50.0, rigor=5.7  ✗ WRONG (should be 70+)
NYT:             lean=47.8, rigor=5.3  ✗ WRONG (should be 60+)
Fox News:        lean=58.9, rigor=59.2 ✓ REASONABLE (right-leaning, moderate rigor)
Breitbart:       lean=63.7, rigor=54.4 ✓ REASONABLE (far-right, opinion-heavy)
```

**Critical Finding**: **Wire services (AP, Reuters) and major broadsheets (NYT) all scoring rigor < 10.** This confirms that **factual_rigor axis is fundamentally broken** — see Domain 3.

**DOMAIN 8 VERDICT**: Political lean and tier distributions look healthy. **Factual rigor axis is broken across all sources.**

---

## CRITICAL ISSUES REQUIRING IMMEDIATE ATTENTION

### Issue #1: Factual Rigor Axis Broken
**Severity: CRITICAL**  
**Impact: HIGH** — Bias display, ranking, search features all rely on rigor

- 53% of articles score 0
- AP, Reuters, NYT all score < 10 (should be 70+)
- Rationale data missing (named_sources_count: None)

**Root Cause**: NER pipeline in `pipeline/analyzers/factual_rigor.py` not extracting sourcing evidence.

**Fix**:
1. Debug `factual_rigor.py` named entity recognition
2. Verify spaCy NER model is loaded and functioning
3. Add logging to named_source extraction
4. Re-score all articles with fixed algorithm
5. Validate against known outlets (AP should be 80+)

---

### Issue #2: 45% Articles Orphaned from Clusters
**Severity: CRITICAL**  
**Impact: VERY HIGH** — User discovery, feed quality

- 4,553 articles exist but not linked to clusters
- Pipeline step 6b (ORPHANS) should wrap these in single-article clusters
- May not be executing or completing

**Root Cause**: Clustering algorithm too strict (threshold 0.2) or orphan-wrapping step broken.

**Fix**:
1. Check `pipeline/clustering/story_cluster.py` — does ORPHANS step exist?
2. If not: implement single-article cluster wrapper for unclustered articles
3. If exists: debug why it's not executing (check pipeline logs)
4. Re-run clustering on existing articles
5. Verify all 9,999 articles now have cluster link

---

### Issue #3: 614 + 326 Dangling References
**Severity: CRITICAL**  
**Impact: HIGH** — Query correctness, Deep Dive view breakage

- 614 cluster_articles rows reference non-existent articles
- 326 bias_scores rows reference non-existent articles
- Implies article deletion without cascade cleanup

**Root Cause**: Missing ON DELETE CASCADE in migrations, or manual data deletion outside pipeline.

**Fix**:
1. Verify migration 001 has ON DELETE CASCADE on articles(id) foreign keys
2. If missing: create new migration to add cascade
3. Clean up orphaned rows:
   ```sql
   DELETE FROM cluster_articles 
   WHERE article_id NOT IN (SELECT id FROM articles);
   
   DELETE FROM bias_scores 
   WHERE article_id NOT IN (SELECT id FROM articles);
   ```
4. Add cleanup RPC to pipeline (already exists: `cleanup_stale_clusters`)

---

### Issue #4: Coverage Velocity Missing (93.2%)
**Severity: HIGH**  
**Impact: MEDIUM** — Ranking formula gap

- Only 201/2,938 clusters have coverage_velocity populated
- Ranking formula (v4.0) includes 6% weight for "sources added in last 6h"
- If missing, ranking degrades slightly but doesn't break

**Root Cause**: Pipeline step 7 (CATEGORIZE & RANK) not writing coverage_velocity field.

**Fix**:
1. Check `pipeline/ranker/importance_ranker.py` — does it set coverage_velocity?
2. If not: add calculation and database write
3. Re-run ranking on all clusters
4. Validate coverage_velocity populated post-run

---

### Issue #5: Political Lean Distribution Too Flat (90% in 40–60 range)
**Severity: HIGH**  
**Impact: MEDIUM** — Bias analysis accuracy

- Political lean algorithm returns nearly all scores in 40–60 (neutral)
- Real outlets have clear lean (Fox News should be 65+, MSNBC 35–)
- Suggests keyword lexicons insufficient or default behavior over-triggered

**Root Cause**: `pipeline/analyzers/political_lean.py` keyword-matching too weak or confidence too low.

**Fix**:
1. Review CLAUDE.md political_lean spec: "0.85 text + 0.15 baseline blending"
2. If baseline_blend too high, lowers impact of detected keywords
3. Audit keyword lexicons (left/right/neutral counts)
4. Test on known outlets (Fox, MSNBC, AP) to see if keywords fire
5. Consider increasing text weight vs baseline (0.90 text + 0.10 baseline)

---

## MUST-HAVE ISSUES (High Priority but Not Blocking)

### Issue #6: 50.8% of Articles Have Word Count < 100
**Severity: HIGH**  
**Impact: MEDIUM** — Article quality, bias scoring reliability

- 4,823/9,499 articles with word_count < 100
- Suggests scraper capturing headlines or RSS snippets, not full text
- Short articles have lower confidence in bias scoring (fewer signals)

**Root Cause**: Web scraper fallback to RSS summary when full text extraction fails.

**Fix**:
1. Check `pipeline/fetchers/web_scraper.py` for fallback logic
2. Log when fallback triggered (source, URL, extracted length)
3. Audit top 10 sources by article count; check sample articles
4. Consider: requiring minimum word_count (500+) for bias scoring, flag short articles
5. Re-scrape low-quality sources with improved extraction

---

### Issue #7: 54% Single-Article Clusters
**Severity: MEDIUM**  
**Impact: MEDIUM** — Story presentation, divergence scoring

- 1,581/2,938 clusters have exactly 1 article
- Expected: 3–5 articles per cluster for meaningful story
- Root cause: Over-fragmentation from clustering algorithm

**Fix**:
1. Adjust TF-IDF similarity threshold (currently 0.2) — try 0.15 or 0.25
2. Review entity-overlap merge pass parameters
3. A/B test clustering on sample data
4. Re-cluster all articles with improved parameters
5. Validate: aim for avg 3+ articles per cluster, <30% single-article clusters

---

### Issue #8: 44 Orphaned Clusters (0 articles)
**Severity: LOW**  
**Impact: LOW** — Database cleanup

- 44 story_clusters exist with no linked articles
- Suggests incomplete transaction or race condition
- `cleanup_stale_clusters` RPC should remove but doesn't

**Fix**:
1. Manual cleanup:
   ```sql
   DELETE FROM story_clusters 
   WHERE id NOT IN (SELECT DISTINCT cluster_id FROM cluster_articles);
   ```
2. Test cleanup RPC to ensure it fires on future runs
3. Check pipeline logs for transaction failures during clustering

---

## SUMMARY BY SEVERITY

### CRITICAL (Block release, fix immediately)
1. ✗ Factual rigor axis broken (53% at 0)
2. ✗ 45% articles orphaned from clusters
3. ✗ 614 + 326 dangling references (referential integrity)

### MUST-HAVE (Fix before launch)
4. ~ Coverage velocity missing (93.2%)
5. ~ 50.8% articles < 100 words (scraper quality)
6. ~ Political lean too flat (90% neutral)
7. ~ 54% single-article clusters (algorithm tuning)

### NICE-TO-HAVE (Backlog)
8. ~ 44 orphaned clusters (cleanup)

---

## SCORING RUBRIC

| Domain | Score | Rationale |
|--------|-------|-----------|
| 1. Source Coverage | 9/10 | All sources present; one extra (test) |
| 2. Article Quality | 6/10 | Good metadata; 50% word count issue |
| 3. Bias Score Quality | 7/10 | 100% coverage; factual_rigor broken; lean too flat |
| 4. Cluster Quality | 6/10 | 45% orphaned; over-fragmentation |
| 5. Enrichment Quality | 5/10 | coverage_velocity missing; divergence low |
| 6. Temporal Freshness | 10/10 | Fresh data; pipeline running |
| 7. Referential Integrity | 4/10 | Multiple dangling references |
| 8. Cross-Field Consistency | 8/10 | Tiers balanced; outlets show wrong rigor |
| **OVERALL** | **68/100** | **Functional but needs critical fixes** |

---

## THE ONE THING

**If you fix one issue, fix this: The factual rigor axis is completely broken.** 53% of articles score 0, including AP, Reuters, and NYT. This undermines the entire bias analysis premise — high-rigor sources should rank higher, but you can't distinguish them from tabloids. The NER pipeline in `pipeline/analyzers/factual_rigor.py` is not extracting named sources. Debug and re-score all articles immediately.

---

## NEXT STEPS

1. **Week 1: Critical Path**
   - [ ] Fix factual_rigor NER pipeline
   - [ ] Implement orphan-article cluster wrapping
   - [ ] Clean up dangling references

2. **Week 2: Must-Have**
   - [ ] Add coverage_velocity to ranking formula
   - [ ] Audit and improve web scraper
   - [ ] Tune clustering algorithm thresholds

3. **Week 3: Polish**
   - [ ] Re-score all articles with fixed algorithms
   - [ ] Validate ranking on known stories
   - [ ] Monitor pipeline for 7-day cycle
   - [ ] A/B test UI with improved bias signals

---

## Data Files
- Audit script: `/home/aacrit/projects/void-news/db_audit.py`
- Detailed analysis: `/home/aacrit/projects/void-news/db_audit_detailed.py`
- Full output: `/home/aacrit/projects/void-news/audit_output.txt`

**Report generated:** 2026-03-20 21:39 UTC
