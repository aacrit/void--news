# void --news Pipeline Brain

Last updated: 2026-04-09 (rev 2, summarization cap updated)

Complete reference for every intelligent system in the pipeline: bias analysis, clustering, ranking, summarization, editorial triage, memory, and audio generation.

---

## Process Flow

```
                            INGESTION
  ================================================================================

  [1] LOAD SOURCES                    1,013 sources, 3 tiers, 158 countries
       |                              data/sources.json
       v
  [2] PIPELINE RUN                    Create run record in Supabase
       |
       v
  [3] FETCH RSS                       30 articles/feed cap, parallel
       |
       v
  [3b] URL DEDUP                      Skip URLs already in DB
       |
       v
  [4] SCRAPE                          Full-text extraction, parallel workers
       |
       v
  [4b] CONTENT DEDUP                  Fuzzy title + body overlap detection
       |                              deduplicator.py
       v

                            ANALYSIS
  ================================================================================

  [5] 5-AXIS BIAS ANALYSIS            Rule-based NLP, $0, per-article
       |
       |  +---> Axis 1: POLITICAL LEAN        keyword lexicons + entity sentiment
       |  |     political_lean.py              (NER + TextBlob) + framing phrases
       |  |                                    + source baseline blending
       |  |
       |  +---> Axis 2: SENSATIONALISM        clickbait patterns + superlative
       |  |     sensationalism.py              density + TextBlob extremity +
       |  |                                    partisan attack density (cap 30pts)
       |  |
       |  +---> Axis 3: OPINION vs FACT       pronouns + subjectivity +
       |  |     opinion_detector.py            attribution density (24 patterns)
       |  |                                    + value judgments + rhetorical Qs
       |  |
       |  +---> Axis 4: FACTUAL RIGOR         named sources (NER + verbs) +
       |  |     factual_rigor.py               org citations + data patterns +
       |  |                                    quotes + vague-source penalty
       |  |
       |  +---> Axis 5: FRAMING               charged synonyms (50+ pairs) +
       |        framing.py                     cluster-aware omission detection +
       |                                       headline-body divergence +
       |                                       passive voice (cap 30)
       v

                            CLUSTERING
  ================================================================================

  [6] CLUSTER ARTICLES                 TF-IDF cosine similarity (titles +
       |                               first 500 words) + agglomerative
       |                               clustering + entity-overlap merge pass
       |                               story_cluster.py
       v
  [6 post] ORPHAN WRAPPING            Single articles wrapped as 1-source clusters
       |
       v
  [6b] RE-FRAME                        Re-run framing analysis WITH cluster
       |                               context (omission detection needs to
       |                               know what other articles in the cluster
       |                               covered)
       v
  [6c] GEMINI REASONING                Contextual bias score adjustments
       |                               gemini_reasoning.py
       |                               25-call cap per run
       v

                            RANKING (v6.0)
  ================================================================================

  [7b] SUMMARIZE                       Gemini Flash, 3+ source clusters
       |                               250-350 words, 50-call cap
       |                               cluster_summarizer.py
       v
  [7] CATEGORIZE + RANK               Per-cluster importance scoring
       |                               importance_ranker.py
       |
       |   10 WEIGHTED SIGNALS (sum = 1.00)
       |   +-----------------------------------------+---------+
       |   | Signal                                   | Weight  |
       |   +-----------------------------------------+---------+
       |   | Source coverage breadth                  |   20%   |
       |   |   tier-weighted diminishing returns      |         |
       |   +-----------------------------------------+---------+
       |   | Story maturity                           |   16%   |
       |   |   recency x log2(1 + source_count)      |         |
       |   +-----------------------------------------+---------+
       |   | Tier diversity                           |   13%   |
       |   |   composition-aware, us_major rewarded   |         |
       |   +-----------------------------------------+---------+
       |   | Consequentiality                         |   10%   |
       |   |   lexicon + high-authority floor (70)    |         |
       |   |   + authority floor (30 when auth >= 80) |         |
       |   +-----------------------------------------+---------+
       |   | Perspective diversity                    |    9%   |
       |   |   stddev + range of lean values          |         |
       |   |   (absorbs former lean_diversity signal) |         |
       |   +-----------------------------------------+---------+
       |   | Institutional authority                  |    8%   |
       |   |   tier-1 (heads of state, courts, banks) |         |
       |   |   tier-2 (cabinet, federal courts, orgs) |         |
       |   +-----------------------------------------+---------+
       |   | Factual density                          |    8%   |
       |   |   average factual_rigor across cluster   |         |
       |   +-----------------------------------------+---------+
       |   | Divergence                               |    7%   |
       |   |   framing 62.5% + sensationalism 37.5%  |         |
       |   |   (lean component removed in v6.0)       |         |
       |   +-----------------------------------------+---------+
       |   | Geographic impact                        |    6%   |
       |   |   NER GPEs x geopolitical weight         |         |
       |   |   G20/P5 = 3x, mid-tier = 2x            |         |
       |   +-----------------------------------------+---------+
       |   | Velocity                                 |    3%   |
       |   |   sources added in last 24h              |         |
       |   +-----------------------------------------+---------+
       |
       |   ADDITIVE ADJUSTMENTS
       |   + Cross-spectrum bonus: 0-4 pts (left < 38 AND right > 62)
       |   + Gemini editorial adjustment: +/-6.7 pts (when available)
       |
       |   SEQUENTIAL MULTIPLIER GATES
       |   x Confidence multiplier: 0.65 + 0.35*conf (floor 0.85 if 15+ src, rigor > 40)
       |   x Longevity penalty: 1.0 -> 0.50 over 48h (stepped decay)
       |   x Gate 1: no-consequentiality -> 0.82x
       |   x Gate 2: soft-news category -> 0.78x
       |   x Gate 2b: tabloid keywords -> 0.75x
       |   x Gate 2c: high sensationalism -> 0.80x/0.90x
       |   x Gate 3: low factual rigor (< 30) -> 0.88x
       |   x Gate 4: single-source -> 0.65x (0.75x if high rigor)
       |
       |   OUTPUT: headline_rank (0-100)
       v

  [7c] EDITORIAL TRIAGE               Gemini reorders top 10 per section
       |                               (optional, when API budget allows)
       v

                            EDITION RANKING (v6.0)
  ================================================================================

       |   edition_ranker.py — single source of truth
       |   Processing order: us -> europe -> south-asia -> world
       |
       |   PER EDITION:
       |   1. Initialize rank_{edition} from headline_rank
       |   2. Story-type gates (incremental 0.75x, ceremonial 0.82x)
       |   3. Regional affinity boost (up to 1.5x, quality-capped)
       |      + Low-affinity demotion (0.65x for stray articles)
       |   4. Local-priority boost (1.40x for edition-exclusive, 5+ src)
       |   5. Regional content keyword boost (1.15x)
       |   6. World multi-edition boost (1.12x for 3+ edition stories)
       |   7. Cross-edition demotion (0.70x, milder 0.88x for global-sig)
       |   8. Same-event cap (max 2 per event, 0.80x decay for deferred)
       |   9. Topic diversity (max 2/category, max 1 soft-news in top 10)
       |  10. Edition lead gate (3+ sources for top 10 positions)
       |  11. Thin-edition backfill (import world stories when < 10 quality)
       |
       |   OUTPUT: rank_world, rank_us, rank_europe, rank_south_asia
       v

  [7d] DAILY BRIEF                     void --onair
       |
       |  +---> TL;DR: 8-12 sentence editorial (150-220 words)
       |  +---> Opinion: 3-5 sentences, lean rotates daily (L/C/R)
       |  +---> Audio: BBC two-host format, Gemini TTS, pydub post-processing
       |        5 rotating host pairs, MP3 96k mono -> Supabase Storage
       v

                            STORAGE
  ================================================================================

  [8] STORE CLUSTERS                   Upsert to story_clusters + cluster_articles
       |
       v
  [8b] DEDUPLICATE                     Article-overlap (>30%) + title-overlap (>40%)
       |                               removes old clusters superseded by new ones
       v
  [8c] HOLISTIC RE-RANK               Re-score ALL clusters in DB with v6.0
       |                               rerank_all_clusters() from rerank.py
       |                               Ensures old + new clusters compete equally
       |                               Runs rank_importance() + apply_edition_ranking()
       |                               on every cluster, writes back to Supabase
       v

                            ENRICHMENT
  ================================================================================

  [9] ENRICH                           refresh_cluster_enrichment() RPC
       |                               aggregated bias stats per cluster
       v
  [9a] MEMORY ENGINE                   Tracks top story, detects shifts
       |                               memory_orchestrator.py
       v
  [9b] ARTICLE CATEGORIES              Junction table population
       |
       v
  [9c] TOPIC-OUTLET TRACKING           Axis 6: per-source per-topic EMA
       |                               topic_outlet_tracker.py
       |                               adaptive alpha (0.3 new / 0.15 established)
       |                               Stored in source_topic_lean table
       v

                            CLEANUP
  ================================================================================

  [10] TRUNCATE FULL TEXT              IP compliance, 300-char excerpts
       |                               (preserves opinion articles)
       v
  [cleanup] RETENTION                  Clusters: archive + delete > 2 days
                                       Articles: delete > 8 days
                                       Briefs: delete > 8 days
                                       Empty clusters: RPC cleanup
                                       Stuck pipeline runs: RPC cleanup
```

---

## The Brain: All Intelligent Systems

### 1. Bias Analysis Engine (5 axes, rule-based, $0)

Every article gets scored 0-100 on 5 axes. All NLP, no LLM calls.

| Axis | File | Key Techniques |
|------|------|---------------|
| Political Lean | `political_lean.py` | Keyword lexicons (left/right coded), entity sentiment via NER + TextBlob, framing phrases, length-adaptive + sparsity-weighted source baseline blending |
| Sensationalism | `sensationalism.py` | Clickbait patterns, superlative density (word-boundary regex), TextBlob polarity extremity, partisan attack density (capped 30pts) |
| Opinion vs Fact | `opinion_detector.py` | First-person pronouns, TextBlob subjectivity, attribution density (24 investigative patterns), value judgments, rhetorical questions |
| Factual Rigor | `factual_rigor.py` | Named sources (NER + attribution verbs), org citations, data patterns (numbers, dates, stats), quote density, vague-source penalty. LOW_CREDIBILITY baseline 35 |
| Framing | `framing.py` | Charged synonym pairs (50+), cluster-aware omission detection, headline-body sentiment divergence, passive voice (capped 30) |

**Axis 6** (tracking, not scoring): Per-source per-topic EMA in `topic_outlet_tracker.py`. Tracks how each outlet leans on each topic over time. Adaptive alpha: 0.3 for new outlets (< 10 articles), 0.15 for established.

**Confidence score**: Computed per-article alongside bias. Measures how much text the analyzers had to work with. P25 across cluster = cluster confidence. Floor 0.85 for 15+ source clusters with factual rigor > 40.

### 2. Clustering Engine

| Component | File | Technique |
|-----------|------|-----------|
| TF-IDF Clustering | `story_cluster.py` | Titles + first 500 words vectorized, cosine similarity, agglomerative clustering |
| Entity Merge | `story_cluster.py` | Post-clustering pass: merges clusters sharing named entities (handles different framings of same event) |
| Title Dedup | `story_cluster.py` | Word-overlap detection for cross-run dedup |
| Content Dedup | `deduplicator.py` | Fuzzy matching to prevent duplicate articles entering the system |

### 3. Importance Ranking Engine (v6.0, bias-blind)

**Design principle**: ranking is BIAS-BLIND. Bias analysis belongs in the display layer (BiasLens, Sigil, Deep Dive), not in story selection. We never boost or penalize a story for its political lean.

- **10 weighted signals** summing to 1.00 (see flow diagram above)
- **Additive adjustments**: cross-spectrum bonus, Gemini editorial
- **7 multiplicative gates**: confidence, longevity, consequentiality, soft-news, tabloid, sensationalism, factual rigor, single-source
- **Direction-blind but diversity-sensitive**: ~12% of ranking influenced by political lean *spread* (not direction)

### 4. Edition Ranking Engine (v6.0)

**Single source of truth**: `pipeline/ranker/edition_ranker.py`

Produces per-edition ranks (rank_world, rank_us, rank_europe, rank_south_asia) so each edition surfaces regional stories first while maintaining global significance.

- **Regional affinity**: proportional to % of articles from regional outlets
- **Cross-edition demotion**: prevents the same story dominating all editions
- **Same-event cap**: max 2 stories per event keyword group per edition
- **Holistic re-rank**: every pipeline run re-scores ALL clusters in DB

### 5. Summarization Engine

| Component | File | Technique |
|-----------|------|-----------|
| Gemini Summarizer | `cluster_summarizer.py` | Gemini 2.5 Flash, 250-350 words, 50-call cap/run |
| Rule-based Fallback | `cluster_summarizer.py` | Lead extraction when Gemini budget exhausted |
| Gemini Reasoning | `gemini_reasoning.py` | Contextual bias score adjustments, 25-call cap |

### 6. Editorial Intelligence (Gemini-assisted)

| Component | Where | What |
|-----------|-------|------|
| Editorial importance | Step 6c | 1-10 score, additive adjustment to ranking |
| Story type | Step 6c | incremental_update (0.75x) or ceremonial (0.82x) |
| Editorial triage | Step 7c | Reorders top 10 per section |
| Consequentiality detection | Step 6c | has_binding_consequences flag |

### 7. Daily Brief Engine (void --onair)

| Component | File | Output |
|-----------|------|--------|
| TL;DR Generator | `daily_brief_generator.py` | 8-12 sentence editorial, 150-220 words |
| Opinion Generator | `daily_brief_generator.py` | 3-5 sentences, lean rotates daily (L/C/R) |
| Audio Producer | `audio_producer.py` | BBC two-host TTS, Gemini native multi-speaker |
| Voice Rotation | `voice_rotation.py` | 5 host pairs, daily rotation |
| Podcast Feed | `podcast_feed_generator.py` | RSS XML for podcast apps |
| Weekly Digest | `weekly_digest_generator.py` | 7-section magazine, Sunday 6AM CST |
| Claude Premium | `claude_brief_generator.py` | Optional Claude CLI for TL;DR + opinion + audio |

### 8. Memory Engine

| Component | File | Purpose |
|-----------|------|---------|
| Memory Orchestrator | `memory_orchestrator.py` | Tracks top story per run, detects narrative shifts |
| Live Poller | `live_poller.py` | Real-time story tracking between pipeline runs |

### 9. Categorization Engine

| Component | File | Technique |
|-----------|------|-----------|
| Auto-categorize | `auto_categorize.py` | Keyword + NER-based article classification into desks (politics, conflict, economy, science, culture, environment, general) |
| Desk mapping | `auto_categorize.py` | Fine-grained categories mapped to editorial desks |

---

## Validation

| System | Method | Location |
|--------|--------|----------|
| Bias Engine | 42 ground-truth articles, 100% accuracy, CI gate | `pipeline/validation/` |
| Ranking | Analytics benchmarks, edge case detection | `/rank-optimize` workflow |
| Cross-axis | Correlation gate (r < 0.70) | `pipeline/validation/runner.py` |
| Source profiles | AllSides alignment check (92.9%) | `pipeline/validation/source_profiles.py` |

---

## Key Design Decisions

1. **$0 operational cost**: All bias analysis is rule-based NLP. Gemini Flash free tier for summaries/TTS.
2. **Bias-blind ranking**: Never factor political lean into story selection.
3. **Newspaper principle**: No personalization. Every reader sees the same stories in the same order.
4. **Holistic ranking**: Every pipeline run re-scores ALL clusters, not just new ones.
5. **Edition-unique feeds**: Regional stories surface first in their edition, but globally significant stories appear everywhere.
6. **Show, don't tell**: All generated text must juxtapose facts, never assert significance.
