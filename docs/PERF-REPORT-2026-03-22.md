# void --news Pipeline Performance Report
**Run ID**: 23395580079
**Date**: 2026-03-22
**Type**: Fresh database (Vol I — no existing articles)
**Status**: Completed successfully

---

## Executive Summary

The pipeline ran for **107.9 minutes** against a 6-minute budget — **18x over**.

Two bottlenecks account for nearly all runtime:

1. **RSS fetch (Step 3)**: 38 minutes. Root cause: 370 sources (148 more than documented in CLAUDE.md), 90 dead sources (24%), feedparser CPU parsing not truly parallelized by GIL.
2. **Scrape + Analysis block**: ~70 minutes. Contains web scraping (30 workers), bias analysis (4 workers, 3 redundant spaCy parses per article), Gemini reasoning (589s), and Gemini summarization (~600s estimated).

**Critical context**: This was a fresh database run — all 4,874 articles needed scraping. Normal incremental runs will be 5-10x faster on the scrape step, since typically only 200-500 new articles appear per run.

---

## Run Statistics

| Metric | Value |
|--------|-------|
| Total duration | 6,475.8s (107.9 min) |
| Sources loaded | 370 |
| RSS articles fetched | 4,874 |
| Articles scraped (fresh DB) | 4,874 (100%) |
| Articles stored | 4,839 |
| Dedup removed | 219 duplicates |
| Articles analyzed | 4,620 |
| Clusters formed | 959 (+ 102 opinion = 1,061 total) |
| Clusters stored | 1,061 |
| Gemini reasoning calls | 25 (at cap) |
| Gemini summarization calls | 25 (at cap) |
| Errors | 1 |

---

## Step-by-Step Timing

Log timestamps in GitHub Actions are buffered and batch-flushed, making individual step timing difficult to read directly. The analysis below uses the two confirmed real-time gaps in log output (where GitHub Actions flushed at phase boundaries) plus self-reported timings from pipeline print statements.

### Confirmed Timing Gaps from Log Timestamps

| Period | Duration | What Happened |
|--------|----------|---------------|
| 04:24:23 → 05:02:27 | **38.1 min (2,284s)** | RSS fetch (Step 3) |
| 05:02:27 → 06:10:33 | **68.1 min (4,086s)** | Steps 4–7d (scrape, analysis, Gemini, rank, store) |
| 06:10:33 → 06:12:11 | **1.6 min (98s)** | Step 9 enrichment |
| Setup overhead | ~8 min | Install deps, Playwright, spaCy |

### Self-Reported Times (from pipeline output)

| Step | Self-Reported Time |
|------|--------------------|
| Step 6c: Gemini reasoning | 589.0s (9.8 min) |
| Step 7d: Daily brief | 47.6s |
| Total pipeline | 6,475.8s |

### Reconstructed Per-Step Estimates

These are estimates, not measured values, reconstructed from the above.

| Step | Estimated Time | % of Total | Budget |
|------|---------------|-----------|--------|
| Step 1: Load + sync sources | <5s | <0.1% | — |
| Step 2: Pipeline run record | <2s | <0.1% | — |
| Step 3: RSS fetch (370 sources, 20 workers) | **2,284s (38.1m)** | **35%** | <30s |
| Step 3b: URL filter (fresh DB = 0 existing) | <5s | <0.1% | — |
| Step 4: Scrape 4,874 articles (30 workers) | ~650s (10.8m) | ~10% | <120s |
| Step 4b: Content deduplication | ~30s | <1% | — |
| Step 5: Bias analysis 4,620 articles (4 workers) | ~1,826s (30.4m) | ~28% | <154s |
| Step 6: Clustering | ~30s | <1% | <30s |
| Step 6b: Framing re-run | ~50s | <1% | — |
| Step 6c: Gemini reasoning | 589s (9.8m) | 9% | — |
| Step 7b: Gemini summarization | ~600s (10m) | ~9% | — |
| Step 7: Categorize + rank | ~30s | <1% | — |
| Step 7c: Editorial triage | ~15s | <1% | — |
| Step 7d: Daily brief | 48s | <1% | — |
| Step 8: Store clusters | ~30s | <1% | — |
| Step 8b: Deduplicate clusters | ~20s | <1% | — |
| Step 9: Enrich clusters (8 workers) | 98s (1.6m) | 2% | — |
| Steps 9b, 9c, 10, cleanup | ~20s | <1% | — |

---

## Bottleneck Analysis

### Bottleneck 1: RSS Fetch — 38 minutes (35% of total)

**Root causes ranked by impact:**

1. **370 sources vs. 222 documented** — The source list has grown 67% beyond what CLAUDE.md describes. More sources = proportionally more fetch + parse time.

2. **90 dead sources (24%) clogging the worker pool** — 38 sources return HTTP 403, 49 return 404, 1 returns 429, 2 return 500. Each dead source still occupies a worker slot for 1–5 seconds while establishing a connection and receiving the error response.

3. **feedparser CPU parsing is GIL-bound** — The code uses `ThreadPoolExecutor` with 20 workers for RSS fetching. However, `feedparser.parse(resp.content)` is CPU-bound (XML parsing, date normalization, HTML content stripping) and holds Python's GIL. This means 20 workers do not truly parallelize the parsing phase — they effectively serialize. With 370 feeds averaging ~4s of combined I/O + parse time, the effective throughput is roughly 1 feed per 4s/20 workers = near-sequential behavior.

4. **Per-article BeautifulSoup call in `_parse_entry`** — For every RSS article summary containing HTML, `BeautifulSoup(summary, "html.parser").get_text()` is called. With 4,874 articles across all feeds, this adds significant CPU overhead that compounds the GIL problem.

5. **Large feeds** — 27 sources return 50+ articles each (The Indian Express: 200, The New Arab: 127, The Hill: 100, AP: 100, The Daily Beast: 100). Large RSS XML documents take longer to download and parse, and block workers for extended periods.

**Expected vs. actual:**
- Expected (370 sources, 20 workers, 2s avg): ~37 seconds
- Actual: 2,284 seconds — **62x over expected**

### Bottleneck 2: Bias Analysis — ~30 minutes (28% of total)

**Root causes ranked by impact:**

1. **3 redundant spaCy parses per article** — `political_lean.py`, `factual_rigor.py`, and `framing.py` each call `get_nlp()` independently and parse `text[:15000]` separately. Each parse of a ~15,000 character document takes ~200–400ms. Three parses = 600ms–1.2s of spaCy overhead per article before any scoring logic runs.

2. **Only 4 workers for CPU-bound work** — Bias analysis is CPU-intensive. While spaCy does release the GIL during its C-extension parsing (allowing true parallelism), the Python scoring logic, regex matching, and TextBlob sentiment analysis hold the GIL. The effective parallelism is somewhere between 1x and 4x, not the full 4x.

3. **TextBlob on 50,000 characters in sensationalism** — `sensationalism.py` calls `TextBlob(text[:50000])` — a 50KB text limit vs. the 15,000-char limit used by all other analyzers. TextBlob sentiment analysis on large text is slow (potentially 500ms–1s per article).

4. **4,620 articles on a fresh database** — Normal incremental runs analyze only new articles (typically 200–500/run). This fresh-DB run analyzed 4,620 articles — 9–23x more than normal.

**Effective rate**: ~1.6s per article with 4 workers. Budget is 2s per article, so per-article speed is acceptable — the problem is volume (4,620 vs. typical 200–500).

### Bottleneck 3: Gemini Steps — ~19 minutes (18% of total)

- **Step 6c Gemini reasoning**: 589s for 25 clusters (23.6s per call). This is I/O-bound (API latency) and cannot be easily sped up without changing the call budget.
- **Step 7b Gemini summarization**: ~600s estimated for 25 clusters at similar latency. Same constraint.

Both Gemini steps are hard-capped at 25 calls each and are I/O-bound on free-tier Gemini API latency. These are unlikely to be reducible without changing the API tier or call cap.

### Bottleneck 4: Web Scraping — ~10 minutes (10% of total, this run)

- 4,874 articles with 30 workers at ~4s average = ~650s
- **This is a fresh-DB artifact.** Normal runs scrape 200–500 new articles: ~27–67 seconds.
- The URL pre-filter (Step 3b) correctly skips known URLs, but on a fresh DB there are none.

---

## What a Normal Incremental Run Looks Like

On a normal run (database already populated from previous runs):

| Step | Fresh DB (this run) | Normal Run (estimate) |
|------|--------------------|-----------------------|
| RSS fetch | 38 min (370 sources) | 38 min (same issue — not DB-dependent) |
| URL filter | 0s (DB empty) | ~5s (DB has existing URLs) |
| Web scrape | ~11 min (4,874 articles) | ~1–2 min (200–500 new articles) |
| Bias analysis | ~30 min (4,620 articles) | ~3–7 min (200–500 articles) |
| Everything else | ~29 min | ~29 min (Gemini steps dominate) |
| **Total** | **~108 min** | **~70 min** |

**A normal run is estimated at ~70 minutes** — still 11x over the 6-minute budget. The RSS fetch and Gemini steps alone exceed the budget.

---

## Error Report

| Error | Severity | Impact |
|-------|----------|--------|
| 38 sources returning HTTP 403 | Medium | Lost coverage from 38 sources |
| 49 sources returning HTTP 404 | Medium | Lost coverage from 49 sources |
| 3 sources timed out | Low | Minimal — 15s timeout caught them |
| ~50% of `enrich_cluster` calls failed with "Server disconnected" | High | Cluster bias/diversity data incomplete |
| 1 global pipeline error logged | Low | Pipeline completed successfully |

**Server disconnected errors in Step 9** — The enrichment step made ~1,061 parallel Supabase RPC calls with 8 workers. Many failed with "Server disconnected". This is likely a Supabase connection pool exhaustion issue — too many concurrent connections overwhelming the free-tier connection limit. The fallback code handled this gracefully (pipeline continued), but cluster bias diversity data is incomplete for affected clusters.

---

## Top 10 Optimization Recommendations

Ranked by estimated impact on runtime reduction.

### 1. Fix dead sources in sources.json (Impact: -8 to -12 min, -20% runtime)

Remove or mark as inactive the 90 sources returning HTTP 403/404. These sources waste worker slots and have wasted work for every pipeline run since they were added.

- Generate a report: which 90 sources are dead?
- Remove or comment them from `data/sources.json`
- Add a CI check that fails if any source returns 4xx consistently

**File**: `/home/aacrit/projects/void-news/data/sources.json`
**Implementation**: Run a pre-flight health check before main pipeline. Remove dead sources.

### 2. Share spaCy doc across analyzers (Impact: -15 to -20 min, -15% runtime)

`run_bias_analysis()` in `main.py` calls `political_lean`, `factual_rigor`, and `framing` each independently. Each re-parses the same text through spaCy. Parse once, pass the doc to all three.

Currently: 3 spaCy parses per article × 4,620 articles = 13,860 parses
After fix: 1 parse per article × 4,620 articles = 4,620 parses
**Saves ~2/3 of spaCy time** — estimated 10–15 minutes on a full run.

Note: `run_bias_analysis()` already has a comment about this optimization being done ("parses spaCy doc once"), but looking at the code, each analyzer still calls `get_nlp()` independently.

**File**: `/home/aacrit/projects/void-news/pipeline/main.py`
**File**: `/home/aacrit/projects/void-news/pipeline/analyzers/factual_rigor.py`
**File**: `/home/aacrit/projects/void-news/pipeline/analyzers/political_lean.py`
**File**: `/home/aacrit/projects/void-news/pipeline/analyzers/framing.py`

### 3. Reduce TextBlob text limit in sensationalism (Impact: -3 to -6 min)

`sensationalism.py` uses `text[:50000]` for TextBlob — 3.3x the 15,000-char limit used everywhere else. Reduce to 5,000 characters for TextBlob (sentiment signal saturates quickly; the first 1,000 words capture the tone).

TextBlob sentiment on 50KB text vs. 5KB: ~10x faster per article.

**File**: `/home/aacrit/projects/void-news/pipeline/analyzers/sensationalism.py`
**Change**: Line 395: `TextBlob(text[:50000])` → `TextBlob(text[:5000])`

### 4. Use multiprocessing for bias analysis instead of threading (Impact: -10 to -15 min)

ThreadPoolExecutor with 4 workers is limited by the GIL for CPU-bound work. `ProcessPoolExecutor` with 4 workers would give true parallelism for all Python code in the analyzers.

Constraint: spaCy's shared model must be re-loaded per process (adds ~10s startup per worker). With 4 processes: 40s startup, but then true 4x parallelism for all Python/TextBlob code.

Estimated gain: 2x–3x speedup on bias analysis time.

**File**: `/home/aacrit/projects/void-news/pipeline/main.py`
**Change**: `ThreadPoolExecutor(max_workers=4)` → `ProcessPoolExecutor(max_workers=4)` with process initializer to load spaCy model.

### 5. Increase bias analysis workers (Impact: -5 to -8 min)

Even with the GIL, spaCy releases it during C-extension work, so 4 threads do get real parallelism for the spaCy-heavy portion. Increasing from 4 to 8 workers would improve utilization of the GitHub Actions runner (which has 2 cores available).

**File**: `/home/aacrit/projects/void-news/pipeline/main.py`
**Change**: `ThreadPoolExecutor(max_workers=4)` → `ThreadPoolExecutor(max_workers=8)` for bias analysis.

### 6. Switch RSS fetching to asyncio (Impact: -5 to -10 min for RSS)

The RSS fetch uses `ThreadPoolExecutor` for I/O-bound work, which is appropriate, but feedparser's CPU-bound parsing limits true parallelism. Two options:

**Option A (recommended)**: Keep `requests` + threads but increase workers from 20 to 50. The I/O portion (network fetch) truly parallelizes and the CPU portion (parsing) will still see GIL contention, but more workers means faster I/O overlap.

**Option B**: Use `asyncio` + `aiohttp` for the HTTP fetch, then run `feedparser.parse(content)` in a thread pool. This separates I/O from CPU and allows maximum concurrency on the I/O phase.

**File**: `/home/aacrit/projects/void-news/pipeline/fetchers/rss_fetcher.py`

### 7. Add RSS article count limit per source (Impact: -3 to -5 min)

Several sources return 100–200 articles per RSS fetch. Most of these are stale (older than a few hours) and will be filtered by the `MAX_ARTICLE_AGE_DAYS=2` check anyway. The time is wasted on downloading + parsing entries that get discarded.

Add an article limit per feed in `_fetch_single_feed`: stop after the first 30 entries (most recent). RSS feeds are ordered newest-first.

**File**: `/home/aacrit/projects/void-news/pipeline/fetchers/rss_fetcher.py`
**Change**: `for entry in feed.entries:` → `for entry in feed.entries[:30]:`

### 8. Skip BeautifulSoup in RSS parser for summaries without HTML (Impact: -2 to -3 min)

`_parse_entry()` calls `BeautifulSoup(summary, "html.parser")` for every summary. Most RSS summaries don't contain HTML tags. Add a fast pre-check:

```python
if "<" in summary:
    # Only parse if HTML present
    summary = BeautifulSoup(summary, "html.parser").get_text(strip=True)
```

This is already in the code. However, it checks `if "<" in summary` but then unconditionally constructs `TextBlob` for the photo credit pattern. The guard should be verified.

### 9. Reduce Supabase enrichment concurrency in Step 9 (Impact: -1 min, fix "Server disconnected")

Step 9 runs `enrich_cluster` with 8 workers making concurrent Supabase RPC calls. This caused widespread "Server disconnected" failures — likely Supabase free-tier connection pool exhaustion. Reduce from 8 workers to 4 workers, or add retry logic with backoff.

**File**: `/home/aacrit/projects/void-news/pipeline/main.py`
**Change**: Step 9 `ThreadPoolExecutor(max_workers=8)` → `ThreadPoolExecutor(max_workers=4)` with retry.

### 10. Cache feedparser results with ETag/Last-Modified (Impact: -5 to -8 min for RSS on normal runs)

HTTP conditional requests: most RSS servers support `ETag` and `Last-Modified` headers. If a feed hasn't changed since last fetch, the server returns HTTP 304 Not Modified with an empty body, saving download + parse time.

This requires storing the ETag/Last-Modified per source in Supabase and sending `If-None-Match`/`If-Modified-Since` headers on subsequent requests.

---

## Realistic Performance Targets

Given the $0 cost constraint and no infrastructure changes:

| Optimization | Est. Time Saved | Cumulative Runtime | Notes |
|---|---|---|---|
| Baseline (this run) | — | 108 min | Fresh DB, Vol I |
| Fix 90 dead sources | -10 min | 98 min | Remove from sources.json |
| Share spaCy doc | -15 min | 83 min | Code change, 3 files |
| Reduce TextBlob limit | -5 min | 78 min | 1-line change |
| Increase bias workers to 8 | -5 min | 73 min | 1-line change |
| RSS article limit (30/feed) | -5 min | 68 min | 1-line change |
| **Normal run baseline** | -38 min | **30 min** | After above + not fresh DB |

**The 6-minute budget is not achievable** with 370 sources, 25 Gemini reasoning calls (589s), and 25 Gemini summarization calls (~600s). Gemini API latency alone consumes ~20 minutes, which exceeds the 6-minute budget before any other work.

**Realistic target for a normal incremental run**: **25–35 minutes** after implementing recommendations 1–5.

**To hit 6 minutes**: Would require eliminating Gemini steps (losing summarization quality) and reducing sources from 370 to ~100. Neither is acceptable within the project constraints.

---

## Comparison vs. Previous Run

| Metric | Previous Run | This Run (Fresh DB) | Change |
|--------|-------------|---------------------|--------|
| Total runtime | ~22 min | 107.9 min | +390% |
| Article volume | Unknown | 4,874 (fresh DB) | Much higher |
| Context | Normal run | Fresh DB (Vol I) | Key difference |

The previous ~22-minute run was a normal incremental run. This run's 108 minutes is expected for a fresh database — all 4,874 articles needed scraping and analysis. Normal runs will be significantly faster.

---

## Immediate Actions (Max Blast Radius: 3 Files)

For the next run, the highest-ROI changes with minimal risk:

**Action 1** — Reduce TextBlob limit in sensationalism (1 line, 1 file, safe):
`/home/aacrit/projects/void-news/pipeline/analyzers/sensationalism.py`, line 395:
`TextBlob(text[:50000])` → `TextBlob(text[:5000])`

**Action 2** — Add RSS article limit per feed (1 line, 1 file, safe):
`/home/aacrit/projects/void-news/pipeline/fetchers/rss_fetcher.py`:
`for entry in feed.entries:` → `for entry in feed.entries[:30]:`

**Action 3** — Increase bias analysis workers (1 line, 1 file, safe):
`/home/aacrit/projects/void-news/pipeline/main.py`, line 1161:
`ThreadPoolExecutor(max_workers=4)` → `ThreadPoolExecutor(max_workers=8)`

These three changes require modifying 3 files, touch no analysis logic, and are fully reversible. Estimated combined time saving: **8–15 minutes** on a full run.
