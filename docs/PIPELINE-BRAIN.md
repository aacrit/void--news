# void --news Pipeline Brain

Last updated: 2026-04-29 (rev 5, all-Sonnet stack + post-rerank single-pass top-50 cache)

Reference for every intelligent system in the pipeline: bias, clustering, ranking, summarization, editorial triage, memory, audio.

---

## Process Flow

```
                            INGESTION
  ============================================================

  [1] LOAD SOURCES                    1,013 sources, 3 tiers, 158 countries
                                      data/sources.json
  [2] PIPELINE RUN                    Create run record in Supabase
  [3] FETCH RSS                       30 articles/feed cap, parallel
  [3b] URL DEDUP                      Skip URLs already in DB
  [4] SCRAPE                          Full-text extraction, parallel workers
  [4b] CONTENT DEDUP                  Fuzzy title + body overlap (deduplicator.py)


                            ANALYSIS
  ============================================================

  [5] 5-AXIS BIAS ANALYSIS            Rule-based NLP, $0, per-article
       Axis 1 POLITICAL LEAN          political_lean.py: keyword lexicons + entity sentiment
                                      (NER + TextBlob) + framing phrases + source baseline blending
       Axis 2 SENSATIONALISM          sensationalism.py: clickbait + superlative density +
                                      TextBlob extremity + partisan attack density (cap 30pts)
       Axis 3 OPINION vs FACT         opinion_detector.py: pronouns + subjectivity +
                                      attribution density (24 patterns) + value judgments + rhetorical Qs
       Axis 4 FACTUAL RIGOR           factual_rigor.py: named sources (NER + verbs) + org citations +
                                      data patterns + quotes + vague-source penalty
       Axis 5 FRAMING                 framing.py: charged synonyms (50+ pairs) + cluster-aware
                                      omission detection + headline-body divergence + passive (cap 30)


                            CLUSTERING
  ============================================================

  [6] CLUSTER ARTICLES                TF-IDF cosine (titles + first 500 words) + agglomerative +
                                      entity-overlap merge (story_cluster.py)
  [6 post] ORPHAN WRAPPING            Single articles wrapped as 1-source clusters
  [6b] RE-FRAME                       Re-run framing WITH cluster context (omission detection
                                      needs to know what other cluster articles covered)
  [6c] GEMINI REASONING               Contextual bias score adjustments (gemini_reasoning.py,
                                      25-call cap, gated by DISABLE_GEMINI_REASONING)


                            RANKING (v6.0)
  ============================================================

  [7b] SMART-ROUTED SUMMARIZE         Claude Sonnet 4.6 primary, Gemini fallback. 3+ source clusters,
                                      250-350 words. cluster_summarizer._smart_generate_json().
                                      Persists summary_article_hash + summary_tier on cluster dict
                                      so step 8 cluster insert carries them to DB.
  [7] CATEGORIZE + RANK               importance_ranker.py — per-cluster importance scoring

       10 WEIGHTED SIGNALS (sum = 1.00)
       +-----------------------------------------+--------+
       | Source coverage breadth                  |  20%   |   tier-weighted diminishing returns
       | Story maturity                           |  16%   |   recency × log2(1 + source_count)
       | Tier diversity                           |  13%   |   composition-aware, us_major rewarded
       | Consequentiality                         |  10%   |   lexicon + high-authority floor (70/30)
       | Perspective diversity                    |   9%   |   stddev + range of lean (absorbs old lean_diversity)
       | Institutional authority                  |   8%   |   tier-1 (heads of state, courts, banks) + tier-2
       | Factual density                          |   8%   |   avg factual_rigor across cluster
       | Divergence                               |   7%   |   framing 62.5% + sensationalism 37.5%
       | Geographic impact                        |   6%   |   NER GPEs × geopolitical weight (G20/P5=3x)
       | Velocity                                 |   3%   |   sources added in last 24h
       +-----------------------------------------+--------+

       ADDITIVE: cross-spectrum bonus 0-4 pts (left<38 AND right>62); Gemini editorial ±6.7
       MULTIPLICATIVE GATES (sequential):
         confidence: 0.65 + 0.35×conf (floor 0.85 if 15+ src AND rigor>40)
         longevity: 1.0 → 0.50 over 48h (stepped)
         no-consequentiality 0.82x | soft-news 0.78x | tabloid 0.75x
         high-sensationalism 0.80x/0.90x | low-rigor (<30) 0.88x
         single-source 0.65x (0.75x if high rigor)

       OUTPUT: headline_rank (0-100)

  [7c] EDITORIAL TRIAGE               Gemini reorders top 10 per section (optional)


                            EDITION RANKING (v6.0)
  ============================================================

       edition_ranker.py — single source of truth.
       Order: us → europe → south-asia → world. Per edition:
         1. Initialize rank_{edition} from headline_rank
         2. Story-type gates (incremental 0.75x, ceremonial 0.82x)
         3. Regional affinity boost (up to 1.5x, quality-capped); low-affinity demotion 0.65x
         4. Local-priority boost (1.40x for edition-exclusive, 5+ src)
         5. Regional content keyword boost (1.15x)
         6. World multi-edition boost (1.12x for 3+ edition stories)
         7. Cross-edition demotion (0.70x; milder 0.88x for global-significance)
         8. Same-event cap (max 2 per event, 0.80x decay)
         9. Topic diversity (max 2/category, max 1 soft-news in top 10)
        10. Edition lead gate (3+ sources for top 10)
        11. Thin-edition backfill (import world stories when <10 quality)

       OUTPUT: rank_world, rank_us, rank_europe, rank_south_asia

  [7d] DAILY BRIEF                    void --onair
       TL;DR: 8-12 sentence editorial (150-220 words), Sonnet primary
       Opinion: 3-5 sentences, lean rotates daily (L/C/R), Sonnet primary
       Audio: BBC two-host, edge-tts ($0), pydub sonic identity, 6-host newsroom (3 pairs),
              MP3 96k mono → Supabase Storage


                            STORAGE
  ============================================================

  [8]  STORE CLUSTERS                 Upsert to story_clusters + cluster_articles.
                                      Writes summary_article_hash + summary_tier (from step 7b).
  [8b] DEDUPLICATE                    Article-overlap (>30%) + title-overlap (>40%);
                                      removes old clusters superseded by new ones.
  [8c] HOLISTIC RE-RANK               rerank_all_clusters() — re-score ALL clusters in DB
                                      with v6.0 (rank_importance + apply_edition_ranking),
                                      writes back to Supabase.
  [8d] POST-RERANK TOP-50 SUMMARIZE   summarize_top50_after_rerank() — single-pass, cached.
                                      Reads top-50 by rank_world from DB. Per cluster:
                                        - hash article membership (sha256 of sorted ids + count)
                                        - if hash matches summary_article_hash AND tier='sonnet'
                                          → reuse, skip API call
                                        - else → call Claude (Gemini fallback), write summary +
                                          hash + tier
                                      Op-eds and clusters with <3 articles skipped.
                                      Syncs in-memory clusters with fresh summaries so brief regen
                                      reads post-rerank text.
  [8e] CACHE CLUSTER IMAGES           Supabase Storage (bypasses CDN hotlink protection); top 10.


                            ENRICHMENT
  ============================================================

  [9]  ENRICH                         refresh_cluster_enrichment() RPC; aggregated bias per cluster.
  [9a] MEMORY ENGINE                  memory_orchestrator.py — tracks top story, detects shifts.
  [9b] ARTICLE CATEGORIES             Junction table population.
  [9c] TOPIC-OUTLET TRACKING          Axis 6: per-source per-topic EMA (topic_outlet_tracker.py).
                                      Adaptive alpha (0.3 new / 0.15 established).


                            CLEANUP
  ============================================================

  [10] TRUNCATE FULL TEXT             IP compliance, 300-char excerpts (preserves opinions).
  [cleanup] RETENTION                 Clusters: archive + delete >2d. Articles: delete >8d.
                                      Briefs: delete >8d. Empty clusters + stuck runs: RPC cleanup.
```

---

## The Brain

### 1. Bias Analysis Engine (5 axes, rule-based, $0)

Every article scored 0-100 on 5 axes. All NLP, no LLM.

| Axis | File | Key Techniques |
|---|---|---|
| Political Lean | `political_lean.py` | Keyword lexicons (left/right coded), entity sentiment via NER + TextBlob, framing phrases, length-adaptive + sparsity-weighted source baseline blending. `rationale.unscored` flag emitted when text has zero partisan signal vs 45-55 baseline — UI renders "unscored" instead of implying center verdict (op-ed/wire safeguard). |
| Sensationalism | `sensationalism.py` | Clickbait patterns, superlative density (word-boundary regex), TextBlob extremity, partisan attack density (cap 30pts). Tier baselines halved 2026-04 (us_major 8, international 10, independent 12); curve inflection tightened 25→15 to widen spread on legitimate tabloid copy. |
| Opinion vs Fact | `opinion_detector.py` | First-person pronouns, TextBlob subjectivity, attribution density (24 investigative patterns), value judgments, rhetorical questions |
| Factual Rigor | `factual_rigor.py` | Named sources (NER + attribution verbs), org citations, data patterns, quote density, vague-source penalty. LOW_CREDIBILITY baseline 35 |
| Framing | `framing.py` | Charged synonym pairs (50+), cluster-aware omission detection, headline-body sentiment divergence, passive voice (cap 30) |

**Axis 6** (tracking, not scoring): Per-source per-topic EMA in `topic_outlet_tracker.py`. Adaptive alpha: 0.3 for new outlets (<10 articles), 0.15 for established.

**Confidence**: Per-article alongside bias. P25 across cluster = cluster confidence. Floor 0.85 for 15+ source clusters with factual_rigor > 40.

### 2. Clustering Engine

| Component | File | Technique |
|---|---|---|
| TF-IDF Clustering | `story_cluster.py` | Titles + first 500 words vectorized, cosine similarity, agglomerative |
| Entity Merge | `story_cluster.py` | Post-clustering: merges clusters sharing named entities |
| Title Dedup | `story_cluster.py` | Word-overlap detection for cross-run dedup |
| Content Dedup | `deduplicator.py` | Fuzzy matching to prevent duplicate articles entering system |

### 3. Importance Ranking Engine (v6.0, bias-blind)

Ranking is **BIAS-BLIND**. Bias analysis belongs in display layer (BiasLens, Sigil, Deep Dive), not story selection. Never boost/penalize for political lean.

- 10 weighted signals summing to 1.00
- Additive: cross-spectrum bonus, Gemini editorial
- 7 multiplicative gates: confidence, longevity, consequentiality, soft-news, tabloid, sensationalism, factual rigor, single-source
- Direction-blind but diversity-sensitive (~12% of ranking influenced by political lean *spread*, not direction)

### 4. Edition Ranking Engine (v6.0)

`pipeline/ranker/edition_ranker.py` — single source of truth. Per-edition ranks (rank_world, rank_us, rank_europe, rank_south_asia) so each edition surfaces regional stories first while maintaining global significance.

- Regional affinity proportional to % of articles from regional outlets
- Cross-edition demotion prevents same story dominating all editions
- Same-event cap: max 2 per event keyword group per edition
- Holistic re-rank: every pipeline run re-scores ALL clusters in DB

### 5. Summarization Engine (Sonnet 4.6 primary)

| Component | File | Technique |
|---|---|---|
| Smart-routed Summarizer | `cluster_summarizer.py` | `_smart_generate_json()` — Claude Sonnet 4.6 first, Gemini Flash fallback. 250-350 words. Sonnet cap: 80/run. |
| Content-Hash Cache | `cluster_summarizer.py` | `_content_hash()` = sha256 of sorted article_ids + "|" + count. Skips clusters whose membership hasn't changed since last Sonnet summary. |
| Post-Rerank Single-Pass | `cluster_summarizer.summarize_top50_after_rerank()` | Step 8d: reads top-50 by rank_world from DB, hash-checks cache, calls Claude only on misses, writes summary + hash + tier. Replaces old "Gemini top-up". |
| Rule-based Fallback | `cluster_summarizer.py` | Lead extraction when both LLMs unavailable |
| Gemini Reasoning | `gemini_reasoning.py` | Contextual bias adjustments, 25-call cap |

**Cost**: Sonnet 4.6 $3 in / $15 out per MTok. ~3500 in × 800 out per call ≈ $0.0225/call. ~57 calls/run × 1 run/day ≈ $1/day ≈ $30/mo.

### 6. Editorial Intelligence (Gemini-assisted)

| Component | Where | What |
|---|---|---|
| Editorial importance | Step 6c | 1-10 score, additive ranking adjustment |
| Story type | Step 6c | incremental_update (0.75x) / ceremonial (0.82x) |
| Editorial triage | Step 7c | Reorders top 10 per section |
| Consequentiality | Step 6c | has_binding_consequences flag |

### 7. Daily Brief Engine (void --onair)

| Component | File | Output |
|---|---|---|
| TL;DR Generator | `daily_brief_generator.py` | 8-12 sentences, 150-220 words. Claude Sonnet primary, Gemini fallback. |
| Opinion Generator | `daily_brief_generator.py` | 3-5 sentences, lean rotates daily (L/C/R). Sonnet primary. |
| Audio Producer | `audio_producer.py` | BBC two-host TTS, edge-tts per-turn (4 Multilingual voices), pydub sonic identity |
| Voice Rotation | `voice_rotation.py` | 5 host pairs, daily rotation |
| Podcast Feed | `podcast_feed_generator.py` | RSS XML for podcast apps |
| Weekly Digest | `weekly_digest_generator.py` | 7-section magazine, Sunday 6AM CST. Sonnet primary. |
| Claude Premium (legacy) | `claude_brief_generator.py` | Standalone Claude CLI for manual brief regen |
| History Audio | `history/audio_script_generator.py` + `generate_audio.py` | Two-host (Chronicler + Witness) edge-tts. Canonical Gemini scripts cached at `data/history/scripts/{slug}.txt`; `--voices-only` reuses cache for zero-Gemini voice sweeps. |

### 8. Memory Engine

| Component | File | Purpose |
|---|---|---|
| Memory Orchestrator | `memory_orchestrator.py` | Tracks top story per run, detects narrative shifts |
| Live Poller | `live_poller.py` | Real-time tracking between pipeline runs |

### 9. Categorization Engine

| Component | File | Technique |
|---|---|---|
| Auto-categorize | `auto_categorize.py` | Keyword + NER classification → desks (politics, conflict, economy, science, culture, environment, general) |
| Desk mapping | `auto_categorize.py` | Fine-grained categories → editorial desks |

---

## Validation

| System | Method | Location |
|---|---|---|
| Bias Engine | 42 ground-truth articles, 100% accuracy, CI gate | `pipeline/validation/` |
| Ranking | Analytics benchmarks, edge case detection | `/rank-optimize` workflow |
| Cross-axis | Correlation gate (r < 0.70) | `pipeline/validation/runner.py` |
| Source profiles | AllSides alignment check (92.9%) | `pipeline/validation/source_profiles.py` |

---

## Key Design Decisions

1. **~$30/mo LLM cost** (broken from $0 intentionally for editorial quality): Bias rule-based, edge-tts $0; summaries/briefs/opinion/weekly route through Claude Sonnet 4.6 with content-hash cache + 5-min ephemeral prompt caching.
2. **Bias-blind ranking**: Never factor political lean into story selection.
3. **Newspaper principle**: No personalization. Same stories, same order for everyone.
4. **Holistic ranking**: Every pipeline run re-scores ALL clusters, not just new ones.
5. **Edition-unique feeds**: Regional stories surface first; globally significant stories appear everywhere.
6. **Show, don't tell**: All generated text juxtaposes facts, never asserts significance.
7. **Single-pass post-rerank summarization**: Top-50 by rank_world summarized AFTER holistic re-rank so the published feed always reflects the freshest Sonnet text. Content-hash cache prevents redundant re-summarization on stable membership.
