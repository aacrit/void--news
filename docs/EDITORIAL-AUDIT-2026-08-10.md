# Void News Editorial Quality Audit, 2026-08-10

Phase 1 diagnosis. No engine code was changed to produce this document. All
figures are derived from the live 2026-08-10 pipeline run (started 11:52 UTC,
completed 13:35 UTC) via direct Supabase queries and faithful replays of the
production ranker and clusterer on the run's own data. Fixes (Phase 2) await
CEO approval of these findings.

Scope: ranking (1a), clustering contamination (1b), geographic distribution
(1c), plus cross-cutting findings and prioritized recommendations. Phase 0
(frontend) and Phase 3 (summarization prompts) shipped separately.

---

## Executive summary

Three defects are visible to any reader, and two of them are structural, not
cosmetic.

1. RANKING. The single largest ranking defect is the `incremental_update`
   0.75x gate in `feed_ranker.py`, applied on Gemini's `story_type` tag with no
   guardrail. It mislabels decisive one-time events as "updates" and buries
   them 10 to 13 positions: the El-Sayed Michigan Senate primary result (33
   sources) at rank 21 instead of about 9, the Sydney airliner near-miss (21
   sources) at 25, plus the Kinahan extradition and the Scharf appointment.
   Separately, breadth-linked signals dominate (about 49% of the score all key
   off source count), so same-day breaking news cannot catch mature 30-plus
   hour stories that have banked sources.

2. CLUSTERING. Every top-30 cluster we traced is contaminated with unrelated
   events, precision from 0.05 to 0.89, systemic across roughly a third to a
   half of the feed. The contaminating merges are introduced by Phase 2
   (`merge_related_clusters`, entity overlap) and compounded by Phase 3
   (title Jaccard). This is the highest-priority defect: a contaminated cluster
   makes the bias score measure a mix of topics rather than spin on one event,
   which breaks the core product claim, not just the copy.

3. GEOGRAPHY. India is 6.3% of sources but 10.0% of ingested articles and about
   20% of the top-30 (5 of 30 by subject). It is both source-list composition
   (Indian sources are prolific) and a ranking amplification (10% ingested
   becomes 20% surfaced), and it rides on the same "breadth is not actually
   dominant" mechanism as 1a: the India top-30 stories carry low source counts
   (5, 5, 6, 10, 16) yet outrank the 33-source El-Sayed primary.

Two documentation-vs-code discrepancies were found and are logged below (the
published ranker weight table is wrong, and `editorial_importance` is applied
twice). One premise in the audit brief was corrected: clustering Phase 2.6
(anchor-entity) is disabled in production, so it is not a culprit; Phase 2 is.

---

## 1a. Ranking audit

### Method and what is reconstructable

`rank_world` is produced in two stages:

1. `headline_rank` (`importance_ranker.py`): the 10 weighted signals plus about
   11 internal gates, computed from article-level data. The per-signal
   component scores are NOT persisted (only the final `headline_rank`, plus
   `coverage_score` inside `bias_diversity`, `divergence_score`,
   `coverage_velocity`, `avg_factual_rigor`). The other six signals (maturity,
   tier-diversity, consequentiality, authority, geographic, spectrum) are
   estimated from code plus title inspection and labeled as estimates.
2. `rank_world` (`feed_ranker.py`): takes the finished `headline_rank` and
   applies story-type and opinion gates, the editorial-importance nudge, and a
   stack of caps and partitions. This stage is fully replayable from persisted
   fields; the real `apply_feed_ordering()` was run on the pulled pool and
   reproduces stored `rank_world` exactly through rank 31.

### Top-30 decomposition table

Legend: sc = source_count. age = hours since first-published. hr =
headline_rank. cov = coverage_score (the 20% breadth signal, persisted). rig =
avg factual rigor. base = hr after feed_ranker steps 1 to 2 (story-type gate x
opinion gate x ei nudge). final = stored rank_world.

| # | Title | sc | age | hr | cov | rig | story_type gate | ei nudge | base | cap / partition | final |
|--|--|--|--|--|--|--|--|--|--|--|--|
| 1 | Netanyahu rejects Trump Gaza plan | 33 | 37.5h | 73.22 | 89.0 | 56 | policy_action (none) | x1.03 | 75.42 | - | 75.42 |
| 2 | Ukrainian drone strike, Tatarstan | 35 | 35.8h | 69.40 | 89.3 | 57 | ongoing_crisis (none) | x1.06 | 73.56 | - | 73.56 |
| 3 | Trump semi-negotiating with Iran | 41 | 35.8h | 69.27 | 88.5 | 54 | ongoing_crisis (none) | x1.03 | 71.35 | - | 71.35 |
| 4 | Pentagon pushes weapons production | 20 | 35.4h | 60.05 | 81.3 | 52 | policy_action (none) | x1.03 | 61.85 | - | 61.85 |
| 5 | Typhoon Dolphin flooding | 30 | 36.1h | 57.79 | 86.8 | 47 | breaking_crisis (none) | x1.06 | 61.26 | - | 61.26 |
| 6 | BC wildfires, 20k evacuations | 12 | 36.4h | 59.31 | 88.8 | 55 | breaking_crisis (none) | x1.03 | 61.09 | - | 61.09 |
| 7 | Houthis missile/drone on Saudi | 13 | 35.6h | 51.85 | 87.5 | 50 | ongoing_crisis (none) | x1.06 | 54.96 | CoverageGuard kept (3rd conflict) | 54.96 |
| 8 | SCOTUS allows Banerjee travel | 10 | 30.9h | 49.91 | 80.8 | 50 | policy_action (none) | x1.06 | 52.90 | - | 52.90 |
| 9 | Former Thai MP shoots official | 10 | 7.4h | 50.78 | 83.1 | 59 | breaking_crisis (none) | x1.03 | 52.30 | - | 52.30 |
| 10 | Tupac trial opens | 11 | 12.2h | 56.82 | 89.3 | 57 | incremental_update x0.75 | x1.0 | 42.62 | - | 42.62 |
| 11 | Zelenskyy: NK 50k troops | 8 | 33.8h | 54.53 | 82.0 | 56 | ongoing_crisis (none) | x1.0 | 54.53 | top-10 conflict cap -12.01 | 42.52 |
| 12 | Jharkhand tear gas on protesters | 16 | 33.7h | 53.04 | 87.8 | 51 | ongoing_crisis (none) | x0.94 | 49.86 | top-10 conflict cap -7.44 | 42.42 |
| 13 | Syria reclaims Russian base | 7 | 23.7h | 42.96 | 71.1 | 53 | policy_action (none) | x1.03 | 44.25 | encode -1.93 | 42.32 |
| 14 | 11 killed Cape Town shootings | 11 | 33.0h | 42.00 | 73.4 | 47 | ongoing_crisis (none) | x1.0 | 42.00 | - | 42.00 |
| 15 | Trump names Scharf WH counsel | 7 | 19.8h | 55.54 | 74.1 | 65 | incremental_update x0.75 | x1.0 | 41.66 | - | 41.66 |
| 16 | Iran appoints Rezaei | 7 | 37.4h | 41.48 | 72.3 | 58 | policy_action (none) | x1.0 | 41.48 | - | 41.48 |
| 17 | Kinahan extradited to Dublin | 9 | 31.0h | 51.33 | 83.8 | 49 | incremental_update x0.75 | x1.06 | 40.81 | - | 40.81 |
| 18 | Indonesian school safety fears | 7 | 36.0h | 42.29 | 77.8 | 53 | ongoing_crisis (none) | x0.94 | 39.75 | - | 39.75 |
| 19 | Trump: witness saw Olympian vandalize | 6 | 14.7h | 56.12 | 75.3 | 57 | incremental_update x0.75 | x0.94 | 39.56 | - | 39.56 |
| 20 | Bus/truck off Andhra bridge | 6 | 29.4h | 41.03 | 66.3 | 48 | ongoing_crisis (none) | x0.94 | 38.57 | - | 38.57 |
| 21 | El-Sayed wins Michigan Senate primary | 33 | 31.8h | 51.37 | 89.5 | 58 | incremental_update x0.75 | x1.0 | 38.53 | - | 38.53 |
| 22 | 18 injured Assam-Arunachal firing | 5 | 33.6h | 37.31 | 62.6 | 47 | ongoing_crisis (none) | x1.0 | 37.31 | - | 37.31 |
| 23 | Nagasaki 81st A-bomb anniversary | 14 | 36.4h | 51.22 | 80.6 | 49 | ceremonial x0.82 | x0.88 | 36.96 | - | 36.96 |
| 24 | Bengaluru hotel food raids | 5 | 10.2h | 37.55 | 59.8 | 36 | policy_action (none) | x0.97 | 36.42 | - | 36.42 |
| 25 | Jetstar/Qatar near-miss, Sydney | 21 | 35.6h | 49.25 | 86.8 | 47 | incremental_update x0.75 | x0.97 | 35.83 | - | 35.83 |
| 26 | Australian PM melons denial | 2 | 3.7h | 35.04 | 40.3 | 48 | none | - | 35.04 | - | 35.04 |
| 27 | Kumamoto evacuees hotel moves | 8 | 34.8h | 38.38 | 79.5 | 46 | ongoing_crisis (none) | x0.91 | 34.93 | - | 34.93 |
| 28 | Messi at father's funeral | 13 | 35.4h | 34.44 | 87.3 | 49 | human_interest (none) | x0.97 | 33.41 | - | 33.41 |
| 29 | HK democrats granted appeal | 8 | 35.9h | 43.90 | - | - | incremental_update x0.75 | x1.0 | 32.92 | - | 32.92 |
| 30 | US DoD invests Australian rare earths | 3 | 5.6h | 32.62 | - | - | policy_action (none) | x1.0 | 32.62 | - | 32.62 |

Story-type gate reality check: only three story_types are gated
(`incremental_update` 0.75, `ceremonial` 0.82, `entertainment` 0.78). The
Gemini tags actually in use are mostly `policy_action` / `ongoing_crisis` /
`breaking_crisis`, all ungated. So the feed-ranker gate surface reduces, in
practice, to a single question: did Gemini call it an incremental update? Eight
of the top-30 got the 0.75x gate.

### Answer 1: Netanyahu (33 src) rank 1 vs El-Sayed (33 src) rank 21

The popular hypothesis (a US-wire coverage penalty) is wrong: El-Sayed's
`coverage_score` is 89.5, higher than Netanyahu's 89.0, and its rigor (58)
beats Netanyahu's (56). The 33 US-heavy sources were not discounted.

Stage A, headline_rank deficit (73.22 vs 51.37, a 21.85-point gap) before
feed_ranker. With coverage equal, the gap comes from importance signals a state
primary genuinely lacks (estimated from code):
- Institutional authority (8%): Netanyahu = prime minister, a Tier-1 head of
  state; El-Sayed = primary winner. About -7 points.
- Geographic impact (6%): Netanyahu carries Israel + Gaza + Trump + Iran;
  El-Sayed = Michigan/US only. About -3.5 points.
- Consequentiality (10%): "rejects [peace] plan" likely trips the peace-agreement
  floor; "wins primary" scores mid. About -3 points.
- Divergence and spectrum (7% + 9%): Netanyahu framing spread 10.0 vs El-Sayed
  6.8. About -1 to -2 points.
- Remainder (about 5 points): confidence multiplier, cross-spectrum bonus, the
  double-applied ei term.

This 22-point headline_rank gap is defensible: a head of state torpedoing a
US-brokered Gaza peace plan is more globally consequential than a Senate
primary. El-Sayed could not legitimately be rank 1.

Stage B, the feed-ranker gate (the questionable part). El-Sayed is tagged
`incremental_update`, so x0.75 costs it 12.84 points (51.37 to 38.53). Netanyahu
is tagged `policy_action` (ungated) and gets a +3% ei nudge instead. The single
factor that costs El-Sayed the most is this gate. Counterfactual: with only
El-Sayed de-gated, its base 51.37 slots at about rank 9; the gate alone drops
it about 12 positions. When all mis-gated incremental_update stories are
corrected together, El-Sayed nets +6 positions (21 to 15). It belongs in the
top 10, not at 21.

### Answer 2: is story maturity penalizing same-day breaking news?

Structurally yes, though the whole breadth stack is the driver, not a single
"maturity" signal. Evidence from the live top-30:
- All 8 top stories are 30 to 37.5h old. Every genuinely fresh sub-15h story
  ranks outside the top 8: Thai MP (7.4h) at 9, Tupac (12.2h) at 10,
  Trump-Olympian (14.7h) at 19, Bengaluru (10.2h) at 24, Australian PM (3.7h)
  at 26, US DoD rare-earths (5.6h) at 30.
- r(rank, source_count) = -0.559; r(rank, age) = -0.278. More sources means
  better rank (strong); older means better rank (moderate).

Mechanism: three of the ten signals, coverage (20%) + maturity depth (16%) +
tier-diversity (13%), about 49% of the score, all key off source_count, which
accumulates over a story's lifetime. The `_longevity_penalty` that should
punish age is computed on the most-recent article timestamp, so an ongoing
story that keeps getting fresh updates pays penalty 1.0 no matter how old its
first article is. A 1.5-day-old story that is still updating has banked 30-plus
sources and pays no age penalty; a 2-hour-old 3-source break cannot catch it.
Magnitude: a fresh 3-source story starts about 17 points behind a mature
33-source story on breadth-linked signals alone, before any gate. Defensible
for a "most important" feed; backwards for anything meant to feel like a
breaking-news front page.

### Answer 3: did the soft-news category gate (0.78x) misclassify El-Sayed?

No. El-Sayed's `category = politics` (not in the soft-news set) and
`content_type = reporting`, so neither the 0.78x soft-news gate nor the 0.78x
entertainment gate fired. What fired is the `incremental_update` story-type gate
at 0.75x. The two multipliers are close enough to conflate, but the mechanism
differs: El-Sayed was judged an incremental update to an ongoing story, not soft
news. That is the real misclassification: a decisive election result is not an
update. The same gate mislabels other hard news in this run: Jetstar/Qatar
near-miss at Sydney (rank 25, 21 sources), Kinahan extradition (17), Scharf
appointment (15). The incremental_update tag is the single most damaging and
most error-prone gate in the feed-ranker layer.

### Answer 4: topic-diversity partition and mid-feed cap firing unexplainably?

Yes, the top-10 category cap produces visibly inverted ordering.
- Zelenskyy / North Korea 50k troops (rank 11, base 54.53): the 7th-highest
  base score in the feed, sitting at 11, below Tupac (rank 10, base 42.62).
  Cause: category `conflict` already filled its 2 top-10 slots (drone at 2,
  Pentagon at 4) plus a 3rd (Houthis at 7) that the coverage guard force-kept,
  so the diversity partition deferred Zelenskyy out of the top 10 and the
  strictly-decreasing encoding stamped it at 42.52. Net cost -12.01; removing
  the cap moves it to 8. A reader sees a 54.5-base story ranked below 42.x-base
  stories with no visible explanation.
- Jharkhand tear gas (rank 12, base 49.86, 16 sources): same conflict-cap
  deferral, -7.44.
- The cap interacts confusingly with the coverage guard: the top-10 shows 3
  conflict stories (drone at 2, Pentagon at 4, Houthis at 7), exceeding the
  nominal cap of 2, because the coverage guard reclaimed the Houthis slot. So
  the cap let a 3rd-in-category story in at 7 while demoting the 1st and 2nd
  best in category (Zelenskyy, Jharkhand) below the fold. That combination is
  genuinely unexplainable to a reader.
- Mid-feed category cap (FEED_CATEGORY_CAP = 12, positions 10 to 50): not
  binding in this run (no category reaches 12 in the window). No-op here.

---

## 1b. Clustering contamination audit (highest priority)

A contaminated cluster (unrelated events merged together) corrupts the lean
distribution, so the bias score measures a mix of topics rather than spin on one
event. That breaks the core product claim.

### Method (how phase attribution was determined)

Three escalating replays using the pipeline modules plus the run's own data:
- A. Within-cluster signal probe: for each final cluster, computed each
  off-topic member's TF-IDF cosine (Phase-1 signal), stemmed-title Jaccard
  (Phase-3 signal), and shared-entity overlap (Phase-2 signal) against the
  on-topic core. Off-topic members share about 0 title stems and about 0
  discriminative entities with the core, implying transitive chaining.
- B. Full-corpus Phase-1-only replay: fetched all 6,496 clustered articles (the
  run's actual `cluster_articles` membership), ran only Phase 1 (production
  settings). Phase 1 keeps sub-topics cleanly separated: each contaminated final
  cluster decomposes into 3 to 13 distinct, mostly-pure Phase-1 labels. Phase 1
  is largely innocent.
- C. Instrumented Phase 2, 3, 4 replay in production order, measuring after each
  phase how many foreign (non-target) articles sit in each target cluster.

Honest caveat: the replay corpus is the 6,496 articles that survived into
`cluster_articles`, not the full pre-clustering set, so the replay under-merges
relative to production (replay hosts are smaller than live). Direction and phase
attribution are robust; live contamination is at least as bad as shown.

### Decisive evidence: foreign-article counts by phase

```
cluster      PHASE1 host (foreign)   PHASE2 host (foreign)   PHASE3 host (foreign)
Pentagon        17  (4 foreign)         28  (15 foreign)        28  (15)
Scharf          13  (6 foreign)         50  (42 foreign)        50  (42)
Netanyahu       34  (4 foreign)         50  (14 foreign)       103  (65 foreign)
Kumamoto         7  (0 foreign)          9  ( 1 foreign)         9  ( 1)
Kazakhstan       3  (0 foreign)          4  ( 0 foreign)         4  ( 0)
HongKong        17  (7 foreign)         17  ( 7 foreign)        17  ( 7)
```

Foreign counts explode at Phase 2 (Pentagon 4 to 15, Scharf 6 to 42, Netanyahu
4 to 14) and again at Phase 3 for the biggest cluster (Netanyahu 14 to 65).
Phase 4 changed nothing (merged garbage titles do not match the force-split
signatures).

Articles Phase 2 injected (real titles from the replay diff):
- into Pentagon: "India condemns embassy defacement in Slovenia", "Marine
  heatwaves strike as climate change plays out", "the ship crews stuck in Gulf
  since February", "Esper calls Iran's demands ridiculous".
- into Trump Names Will Scharf: 33 foreign articles, the entire Trump Reflecting
  Pool / Olympian vandalism saga, late-night segments, "Epstein email
  revealed", a MAGA Senate-nominee thread, unrelated op-eds. All bridged by
  `trump` plus one rare co-occurring entity.
- into Kumamoto Evacuees: "Hiroshima A-bomb girl inspiring Filipino children",
  "Ainu musician brings tradition to New York" (Japan-desk features).

### Root cause: why Phase 2 over-merges

`merge_related_clusters` merges any two clusters that share at least 3 entities
total with at least 1 discriminative entity. Discriminative means document
frequency at or below `max(5, int(n*0.05))`. At production scale (n about 2,196
post-Phase-1 clusters) that threshold is `max(5, 109) = 109`: an entity counts
as discriminative unless it appears in more than 109 clusters. Essentially every
GPE and proper noun (Assam df about 6, Kazakhstan, Kumamoto, Cape Town,
Banerjee) clears this trivially. The `PHASE2_TITLE_SANITY_FLOOR` (0.08) only
applies to single-discriminative-entity bridges; any pair sharing 2 or more
sub-109-df entities skips the title check entirely (`PHASE2_STRONG_DISTINGUISHING
= 2`), and regional or political co-coverage always shares 2 or more. Union-find
then chains them transitively. The only Phase-2 brake is `max_cluster_articles =
50` (Scharf and Netanyahu both stop at exactly 50 in Phase 2); Phase 3 then
resumes up to the 120 ceiling (Netanyahu to 103). Phase 3 has the same scale
problem (`PHASE3_STEM_DF_PCT = 0.08`, a stem is discriminative unless in more
than about 175 titles).

### Per-cluster precision table (all top-30)

`coh` is the code's own `topic_coherence` (a title-keyword proxy that
over-estimates, counting a shared GPE as on-topic). `prec` is hand-verified
on-topic fraction where traced. Note the gap between coh and prec on rows 22,
27, 30: wherever contamination rides on a shared GPE that is also a headline
keyword, the code's coherence metric is blind to it. n_art much greater than sc
is itself a contamination tell.

| rank | sc | n_art | coh | hand prec | title |
|---|---|---|---|---|---|
| 1 | 33 | 50 | 0.82 | 0.80 | Netanyahu Rejects Trump 15-Point Gaza Peace Plan |
| 2 | 35 | 49 | 0.53 | suspect | Ukrainian Drone Strike, Tatarstan |
| 3 | 41 | 60 | 0.93 | - | Trump semi-negotiating with Iran |
| 4 | 20 | 28 | 0.50 | 0.50 | Pentagon Pushes Defense Companies |
| 5 | 30 | 41 | 0.98 | - | Typhoon Dolphin Flooding |
| 6 | 12 | 14 | 0.79 | - | British Columbia Wildfires |
| 7 | 13 | 14 | 1.00 | - | Houthis Missile/Drone on Saudi Forces |
| 8 | 10 | 25 | 0.36 | 0.28 | SCOTUS Allows Banerjee Foreign Travel |
| 9 | 10 | 11 | 1.00 | - | Former Thai MP Shoots Official |
| 10 | 11 | 11 | 0.73 | - | Tupac Trial Opens |
| 11 | 8 | 11 | 0.64 | - | Zelenskyy: NK to Deploy 50,000 Troops |
| 12 | 16 | 50 | 0.80 | suspect (50/16) | Jharkhand Tear Gas on Protesters |
| 13 | 7 | 8 | 1.00 | - | Syria Reclaims Russian Bases |
| 14 | 11 | 12 | 0.17 | 0.17 | Eleven Killed in Cape Town Shootings |
| 15 | 7 | 9 | 1.00 | 0.89 | Trump Names Will Scharf WH Counsel |
| 16 | 7 | 8 | 0.88 | - | Iran Appoints Rezaei |
| 17 | 9 | 10 | 1.00 | - | Kinahan Extradited to Dublin |
| 18 | 7 | 13 | 0.54 | suspect | Indonesian School Safety Fears |
| 19 | 6 | 8 | 1.00 | - | Trump: Witness Saw Olympian Vandalize |
| 20 | 6 | 7 | 0.43 | 0.29 | Bus and Truck Off Andhra Bridge |
| 21 | 33 | 50 | 0.62 | suspect (50/33) | El-Sayed Wins Michigan Senate Primary |
| 22 | 5 | 8 | 1.00 | 0.25 | Eighteen Injured in Assam-Arunachal Firing |
| 23 | 14 | 25 | 0.80 | - | Nagasaki 81st A-bomb Anniversary |
| 24 | 5 | 6 | 0.83 | - | Bengaluru Hotels Raided Over Rotten Food |
| 25 | 21 | 28 | 0.57 | suspect | Jetstar/Qatar Near-Miss at Sydney |
| 26 | 8 | 15 | 0.53 | 0.40 | Kumamoto Evacuees Hotel Moves |
| 27 | 4 | 9 | 0.67 | 0.22 | Kazakhstan Comic Con, Releases Tiger |
| 28 | 3 | 3 | 1.00 | - | Boat Capsizes Near Statue of Liberty |
| 29 | 13 | 13 | 0.92 | - | Messi at Father's Funeral |
| 30 | 8 | 22 | 0.45 | 0.05 | HK Democrats Granted Permission to Appeal |

Selected traces:
- Netanyahu (proof cluster, precision 0.80): confirmed at source level. Contains
  the exact cited off-topic articles: Common Dreams (Jewish-American activist
  visas), Anadolu (West Bank eviction), JPost/LA-Times "Yellow Line" pieces,
  plus other West Bank / settler coverage. The off-topic occupation coverage is
  what corrupts the lean read on the rejection.
- Hong Kong appeal (precision 0.05, worst): the headline event is about 1 of 22
  members. The rest are a Hong Kong heat-record / typhoon story, a local
  grab-bag, and three Nature journal "Author Correction" science papers, bridged
  by the GPE Hong Kong plus publisher boilerplate.
- Assam-Arunachal firing (precision 0.25): 2 of 8 are the firing; the rest are a
  separate Assam flood story plus celebrity flood-relief donations, bridged by
  the GPE Assam. The code's coherence proxy reports 1.00 for this cluster.
- Two contaminated clusters found beyond the named list: Cape Town shootings
  (precision 0.17, a South Africa / Africa bag) and Banerjee travel (0.28, an
  India / Supreme Court / TMC-Bengal bag).

### Answers restated

- Q1: traces and precisions above. Named clusters: Pentagon 0.50, Andhra 0.29,
  Kumamoto 0.40, Assam 0.25, Kazakhstan 0.22, Hong Kong 0.05, Scharf 0.89,
  Netanyahu 0.80. Plus Cape Town 0.17 and Banerjee 0.28.
- Q2: Phase 2 (`merge_related_clusters`) introduces the contaminating articles;
  Phase 3 (`merge_duplicate_title_clusters`) compounds it on the largest,
  entity-dense clusters. Phase 1 keeps sub-topics separate; Phase 4 corrects
  none of it.
- Q3: neither 2.6 nor Phase 3 is the primary culprit; Phase 2 is. Phase 2.6
  (anchor-entity) is DISABLED in production (`enable_anchor_merge = False`, no
  caller passes the flag), so it cannot contribute. This corrects the audit
  brief's premise. Phase 3 is a real but secondary aggravator.
- Q4: MERGE_HARD_CEILING (120) is not masking so much as inapplicable. The
  contaminated clusters are 3 to 50 sources, well under the 120 ceiling and
  under Phase 5's 75-source mega-cap. Every size-based guard sits above the band
  where contamination occurs, so none engage. Only Netanyahu approached the
  ceiling (103) and still passed through.
- Q5: full table above.

---

## 1c. Geographic distribution

Source-list composition (data/sources.json, 1,016 sources): US 422 (42%), GB 73
(7%), IN 64 (6.3%), CA 19, AU 18, DE 13, FR 12, ZA 12.

Articles ingested in the 2026-08-10 window (8,258 total, by source country):

| Country | Ingested | Share |
|---|---|---|
| US | 3,179 | 38.5% |
| GB | 900 | 10.9% |
| IN | 822 | 10.0% |
| AU | 333 | 4.0% |
| JP | 250 | 3.0% |
| SG | 220 | 2.7% |

Top-30 by dominant source country: US 13 (43%), IN 6 (20%), GB 2, JP 2, then IL,
NL, ZA, SG, AU, KZ, HK at 1 each. By subject, 5 of 30 are India stories
(SCOTUS/Banerjee, Jharkhand, Andhra bridge, Assam firing, Bengaluru raids).

India comparison: 6.3% of sources, 10.0% of ingested articles, 20% of top-30 by
dominant source country, about 17% by subject.

Conclusion: it is both, not one or the other.
- Source-list composition and source prolificacy: 64 Indian sources produced 822
  articles (about 13 each) versus US 422 sources producing 3,179 (about 7.5
  each). Indian regional sources publish at nearly double the per-source rate,
  so India's ingested share (10%) already exceeds its source share (6.3%).
- Ranking amplification: 10% ingested becomes 20% surfaced, a further doubling.
  The India top-30 stories carry low source counts (5, 5, 6, 10, 16), yet they
  outrank the 33-source El-Sayed primary. That is the same mechanism as 1a:
  breadth is not the dominant signal the docs claim, so low-breadth regional
  clusters are not penalized relative to genuinely high-coverage stories.

---

## Cross-cutting findings

- Contamination is upstream of the product claim. Because a contaminated cluster
  mixes multiple events, its lean distribution is a topic mixture, not spin on
  one story. Fixing 1b is a precondition for the bias score to mean what the
  product says it means. This is why 1b is the highest priority.
- The three defects share one root theme: breadth (source_count) is
  over-weighted and under-guarded. In ranking it triple-counts (1a) and rewards
  age; in geography it lets prolific regional desks surface (1c); in clustering
  a loose entity gate inflates member counts and therefore breadth (1b), which
  then feeds back into the ranker.

Documentation-vs-code discrepancies (for update-docs, not fixes):
- The published ranker weight table lists perspective-diversity 6% and velocity
  6%. The code (importance_ranker.py:1316-1327) uses spectrum 0.09 and velocity
  0.03. Weights still sum to 1.00.
- `editorial_importance` is applied twice: additively in importance_ranker.py
  (1382-1388, plus or minus 6.7 points into headline_rank) and multiplicatively
  in feed_ranker.py (350-354, x0.88 to x1.12). Small per-story effect, but
  double-counted.
- CLAUDE.md and docs/PIPELINE-BRAIN.md describe clustering Phase 2.6
  (anchor-entity) as a live production phase. It is parked
  (`enable_anchor_merge = False`, no production caller). The "7-phase clustering
  engine" wording should flag 2.6 as opt-in/diagnostic-only to avoid future
  misdiagnosis.

---

## Recommendations for Phase 2 (diagnosis only, prioritized)

These are proposals. Nothing here has been implemented. They await approval and
must go through the clustering and bias validation gates.

1. Clustering Phase 2 gate (highest priority). The discriminative-df threshold
   collapses at production scale (`max(5, int(n*0.05))` to 109), so common GPEs
   count as rare anchors. The specific hole is `PHASE2_STRONG_DISTINGUISHING =
   2`, which lets any 2-GPE bridge skip the title-agreement check. Investigate a
   scale-stable df bound (a fixed small df, or IDF rather than raw df) and remove
   or tighten the 2-entity title bypass so entity bridges still require title
   agreement. Impact high, effort medium. Owner: story_cluster.py, with
   pipeline-tester sequential validation.
2. Clustering Phase 3 title-Jaccard (`PHASE3_STEM_DF_PCT = 0.08`) has the same
   scale problem and compounds the biggest clusters. Fix alongside item 1.
3. Ranking `incremental_update` gate. It is applied on Gemini's tag with no
   guardrail and mislabels decisive events. Options: suppress the gate for
   clusters under about 12 hours old or gaining sources fast (a real update is a
   mature, slow story), exempt high-source clusters (sc at or above 20), and
   audit the Gemini story_type prompt for update-vs-result confusion. Impact
   high, effort small.
4. Ranking longevity penalty keys off the most-recent timestamp, so
   continuously-refreshed stories never pay for age. Add a story-birth-age
   component so mature ongoing stories do not monopolize the top while same-day
   breaks are locked out. Impact high, effort medium.
5. Ranking top-10 category cap plus coverage-guard interaction demotes
   higher-base stories below lower-base ones (Zelenskyy 54.5 at rank 11). Make
   the cap rank-aware: never let a capped story fall below a story it out-bases
   by more than about 8 points. Impact medium, effort medium.
6. Ranking breadth is roughly triple-counted (coverage 20% + maturity depth 16%
   + tier-diversity 13%, about 49%). This is the structural reason source_count
   dominates (r = -0.56). Worth a weight review. Impact medium, effort medium.
7. Documentation fixes (weights 9/3 not 6/6; ei double-applied; Phase 2.6
   parked). Impact low, effort small.

---

## Phase 4. Lean label suppression (proposal, not implemented)

The brief proposed suppressing the lean label when confidence is below a
threshold, when source count is low, or when the category is non-political,
showing "Unscored" instead. Tested against the 2026-08-10 top-30. The important
finding is that two of the three proposed signals, as currently stored, do not
work.

The defect, quantified. 21 of 30 top stories (70%) have an aggregated lean in
the 47 to 53 band; 16 of 30 (53%) are in a tighter 48 to 52 band. The frontend
renders these as confident-looking near-center labels. This is the false-center
problem rev 49 addressed, reappearing through low-variance aggregation. A second
mode is the confident tilt on an apolitical story: the Tupac murder trial rendered
Left (aggregated lean 44) and the Bengaluru food-safety raids rendered Right,
because on an apolitical topic with few sources the outlet baseline dominates.
These two modes are different: the apolitical tilts are NOT near-center, so a
near-center rule will not catch them.

The three proposed signals, evaluated on this feed:
- Confidence threshold: unusable as stored. `bias_diversity.aggregate_confidence`
  is saturated at 1.0 for all 30 stories, so any confidence threshold suppresses
  0. `lean_spread` is also uniformly low (all under 18, max 16.3), so it does not
  cleanly flag uncertain labels either. A real per-label confidence signal does
  not currently exist at the cluster level.
- Category non-political: unreliable as stored. The `category` field is 37%
  "general" (11 of 30), a catch-all that includes Netanyahu, Trump/Iran, and
  Syria. Suppressing on non-political category would wrongly hide the lean on
  major political stories. It would nominally suppress 16 of 30, but for the
  wrong reasons.
- Source count low: actionable but narrow. source_count < 5 suppresses 2 of 30;
  source_count < 8 suppresses 10 of 30.

Recommended suppression rules (for CEO decision, do not implement yet):
1. False-center band. Show "No clear lean" (or "Unscored") when
   avg_political_lean is in [48, 52]. Suppresses 16 of 30. A tighter [49, 51]
   band suppresses fewer. This directly targets the false center and is the
   single highest-value rule. Optionally gate it on lean_spread so a genuinely
   contested balanced story (real left and right coverage) keeps a "Contested"
   marker rather than being hidden.
2. Low-breadth secondary gate. Suppress the lean when source_count < 8 (10 of
   30), because a thin cluster's lean is dominated by the outlet baseline rather
   than the article words. Combine with rule 1 rather than applying alone.
3. Apolitical suppression needs a NEW signal, not the current category. The
   coarse category cannot separate apolitical (Tupac, Bengaluru) from political
   "general" (Netanyahu). Recommend deriving an apolitical flag from the absence
   of political entities/topics, or a dedicated lightweight classifier, before
   suppressing on it.

Net: only the lean-band rule (1) and the source-count rule (2) are actionable
with today's stored signals. The confidence and category rules require new
signals first. Awaiting the CEO's chosen band and source-count floor.
