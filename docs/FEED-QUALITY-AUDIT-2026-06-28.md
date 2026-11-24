# void --news — Feed Quality Audit (Clustering · Summary · Ranking)

**Date:** 2026-06-28 · **Data:** live production feed (clusters created 2026-06-28T13:31 UTC), pulled read-only from Supabase via the public anon key embedded in the deployed bundle. **Scope:** the displayed top 50 (top 50 by `rank_world` where `sections ∋ 'world'`, exactly the homepage query). All referenced events were web-verified as **real** late-June-2026 news (Iran–US strikes on Bahrain/Kuwait, Venezuela earthquake, Vučić resignation, Starmer succession), so the major-outlet benchmark is valid.

> **Headline finding.** The pipeline ran and produced a polished-looking feed, but **clustering over-merge is silently corrupting the entire stack**. Median cluster topical-coherence is **42%**; 38% of the feed is built on near-random article bags. The Gemini summarizer and the daily brief are genuinely good, which *masks* the rot from a casual reader — but the polluting articles inflate `source_count` (the dominant rank signal + the "X sources" trust badge), dilute the opinion signal (op-eds rank as news), and poison the categorizer (the "science" catch-all). One upstream defect, three downstream symptoms.

---

## 1. Scoring rubric

Each dimension is graded per item on a 4-tier scale (mirrors the existing validation suite), then rolled up.

**Clustering** — per cluster:
- *Coherence* = fraction of member-article titles sharing a content keyword with the cluster's own headline. CORRECT ≥70% · ACCEPTABLE 50–69% · WRONG 25–49% · CATASTROPHIC <25%.
- *Granularity* = one real-world event per cluster (not fragmented across many, not conflated with others).
- *Representativeness* = headline + summary reflect the membership majority, and `source_count` counts genuinely-on-topic voices.

**Summary** — per displayed cluster:
- *Coverage* = an LLM summary exists (not a raw article excerpt).
- *Topical accuracy* = summary describes the cluster's actual dominant story **and** matches the headline.
- *Style compliance* = no em/en-dash, no banned tells ("significant/notable/it should be noted/interestingly/crucially"), show-don't-tell, English, no outlet suffix in the headline.
- *Grounding* = every claim traceable to member articles.

**Ranking** — feed-level:
- *Top-story relevance* vs major-outlet benchmark.
- *Editorial purity* = hard news vs opinion/sports/PR leakage.
- *Same-event consolidation* = the megastory occupies one strong slot, not many weak duplicates.
- *Signal integrity* = rank not corrupted by inflated `source_count` or miscategorization.

---

## 2. Scorecard (today)

| Dimension | Grade | Evidence |
|---|---|---|
| **Clustering** | **D — Failing** | Median coherence 42% (mean 44%). CATASTROPHIC (<25%) **19/50 = 38%**; ≤WRONG **23/50 = 46%**; CORRECT (≥70%) only **12/50 = 24%**. 19/50 clusters pinned at *exactly* 50 articles (the cap acting as an attractor). |
| **Summary** | **D — Failing** | **16/50 (32%)** displayed cards show a raw excerpt (no LLM summary), frequently about a *different story than the headline*. "significant" leaks in 8 generated summaries; em-dashes + outlet suffixes ("- WSJ", "- TheCable") + one untranslated Spanish card reach the feed. |
| **Ranking** | **C− — Poor** | World's #1 story (Iran–US war) fragmented across 5 slots, main 117-article cluster at **#35**; Venezuela mega-disaster at **#17**; **Harry Styles (#9) and a football result (#10) in the top 10**; 20% of the feed is sports/opinion/PR; 23/50 slots are repeats of 7 mega-topics. |

**What is working (so the fixes don't break it):** the Gemini summaries that *did* generate (flash/flash-lite) are clean, accurate and well-written (#1 IDF, #2 UAE/Egypt, #5 Ukraine). The **daily brief is excellent** — "Gulf Under Fire; Ukraine Targets Fuel; US Aids Venezuela" leads with the correct global priorities and is style-clean. Several clusters are perfectly coherent (Iran-US war live 98%/117 articles, Beijing crash 100%, Kentucky floods 100%, IDF Lebanon 95%). The pipeline completed; the bias join and source attribution are intact. **The data can support a great feed — the ranker and the over-merger are the divergent components.**

---

## 3. Findings & root causes

### 3.1 Clustering

**Symptom.** Most feed clusters are "garbage bags": a coherent seed story plus dozens of unrelated articles. "Indigenous Woman Wins Canadian Immigration Appeal" → 2/41 members on-topic (rest are a New York Sun grab-bag). "Iran Protests US Visa" (38 sources) → members are *all* Texas-Bible-in-schools. "Israel Attacks Hezbollah" → members are *all* World Cup football. Two signatures: (A) single-publisher piles (all Malay Mail / NY Sun / NBC-Spanish), (B) multi-source TF-IDF false-merges (36 distinct outlets, all unrelated).

**Root cause (code-confirmed).** Production runs with `enable_anchor_merge=False` (`main.py:1680`), so Phases 2.5/2.55/2.6 are OFF — the over-merge is Phase 1+2+3.
- **Primary:** Phase 1 agglomerative clustering uses `linkage="average"` at `STORY_TFIDF_THRESHOLD=0.18` (`story_cluster.py:63, 2102-2109`). A 0.18 cosine cut under average linkage lets a single bridge article chain unrelated sub-topics; the **50-article cap is the only brake** (`story_cluster.py:853,944`) → the spike of clusters at exactly 50.
- **Single-source piles:** Phase-1 `min_df=1` (`story_cluster.py:2096`) keeps single-document tokens, so one outlet's nav/footer boilerplate in `full_text` self-clusters its own articles; Phase-2 `MIN_DISTINGUISHING_SHARED=1` (`story_cluster.py:412`) then bridges them on one incidental shared entity.
- **Why no guard fires:** Phase 5 `split_mega_clusters` gates on `source_count≥75` (`story_cluster.py:662,1570`) and the cohesion trip needs `source_count≥40` (`story_cluster.py:1695`); the contaminated clusters carry 50 articles but only 8–46 voices, so they pass untouched (`mega_cluster_capped` set on 1/80). The `_cluster_cohesion` scorer (with `dominant_publisher_share`) is computed but never gates anything.
- **Why it hides:** title = single best-scoring member headline; summary = single longest member excerpt (`story_cluster.py:167-251, 1917-1918`) — both describe the seed, so the card looks fine while `source_count` is inflated.

### 3.2 Summary

**Symptom.** 16/50 displayed cards have `summary_tier=NULL` + `story_type=NULL` and show a raw excerpt — often a *third* story (headline "Germany/Denmark heat" → summary about Tirupati archaeology; headline "Trump…Christians in Nigeria" → summary about UK Labour). "significant" appears in 8 LLM summaries; em-dashes only in NULL-tier fallback text.

**Root cause (code-confirmed).** The homepage and step-8d order **identically** by `rank_world DESC` (`HomeContent.tsx:371`, `cluster_summarizer.py:1184-1186`) — so it is **not** a candidate-set mismatch and **not** the per-run call cap (`_MAX_CALLS_PER_RUN=90` has headroom; the NULL pattern is interleaved, not a contiguous tail). The 16 NULLs come from **in-loop skip/fail paths**: `<3 articles` skip, `content_type=="opinion"` skip, and silent generation-failure `continue` (`cluster_summarizer.py:1236-1267`) all leave the row untouched, so the raw step-8 title + longest-excerpt (`main.py:2562-2563`) survives. The show-don't-tell / em-dash "post-check" is **warning-only** (`cluster_summarizer.py:829-834`) — it logs, never mutates — and the rule-based fallback path never passes through any scanner. Titles keep outlet suffixes because `_clean_title` only strips a fixed wire allow-list (`story_cluster.py:88-111`) and never translates.

### 3.3 Ranking

**Benchmark.** Global priority on 2026-06-28 (AJ/CNN/NPR/PBS/ABC/Reuters/UN): **(1) Iran–US war / strikes on Bahrain & Kuwait, (2) Venezuela earthquake ~1,430 dead, (3) Ukraine fuel-infrastructure strikes, (4) SCOTUS presidential-power term-end, (5) Vučić resignation.** void's actual top 10: IDF-officer-Lebanon, UAE/Egypt-condemn, Trump-ICE, SCOTUS, Ukraine-drone, Albania-protests, **Israeli-American-fraud-extradition**, Türkiye-protest-ban, **Harry-Styles-collapses**, **Bafana-Bafana-football**. The world's #1 is fragmented (main cluster #35); the #2–3 disaster is #17; two soft items are in the top 10.

**Root cause (code-confirmed).**
- **R1 editorial leakage (10/50):** the ranking path never reads `content_type` (`importance_ranker.py:1127`, `feed_ranker.py:96-239`) — *no opinion demotion exists*. The soft-news gate keys on `category` not Gemini's `story_type` (`importance_ranker.py:1424`, ×0.78), and `feed_ranker.STORY_TYPE_GATES` has no `entertainment` entry (`feed_ranker.py:26-29`) — so sports tagged `science`/`economy` evade it. `content_type` itself is a *mean* of member `opinion_fact` (`main.py:2025`), which over-merge dilutes below 50 → op-eds stored as "reporting".
- **R2 fragmentation:** same-event handling is **decay-only, not consolidation** (`feed_ranker.py:132-143`): `MAX_SAME_EVENT=2`, `EVENT_DECAY=0.80`, applied in rank order — so the **richest** cluster (Iran-US war, 75 sources) is penalized hardest (×0.80 → #35) while a 24-source framing leads at #2. No sibling-suppression, no source-union.
- **R3 source_count inflation (master):** `source_count` moves ~36% of the score (coverage 0.20 + maturity 0.16) plus gates tier-diversity, velocity, the confidence floor (`:1348`), the longevity floors (`:1081-1085`) and `is_headline` (`:1541`). It is taken at face value — **no coherence signal feeds the ranker** — so a 38-source 16%-coherent bag buys a slot and a trust badge. The over-merge penalty (`:1371`) only fires at 75 sources → 1/80.
- **Categorizer:** the cluster category is voted on the first **3 sampled member articles** (`main.py:1982`), polluted on over-merged clusters; `DESK_MAP` collapses **technology→science** (`auto_categorize.py:281`) so incidental "AI"/"Apple" tokens win; the science lexicon has weak generic terms (study/launch/research/journal, `:176-190`). Headlines alone categorize *correctly* — it's the polluted sample that defaults to science.
- **Cross-cutting:** `feed_ranker.py:235-239` clamps ranks to `prev−0.1`, compressing ranks 11–26 into a staircase that discards real `headline_rank` separation (e.g. #11 Saudi Aramco crash hl_rank 70.22 → rank_world 51.95).

---

## 4. The master-cause cascade

```
                 Phase-1 over-merge (threshold 0.18, average linkage, min_df=1)
                                     │
              ┌──────────────────────┼───────────────────────────┐
              ▼                      ▼                            ▼
   source_count INFLATED     opinion_fact MEAN diluted     3-article sample POLLUTED
        (R3 master)            (op-eds → "reporting")         (category → "science")
              │                      │                            │
              ▼                      ▼                            ▼
   garbage bags rank top-50   opinion/sports leak (R1)    soft-news gate misses sports
   + inflated "X sources"                                  (keys on wrong category)
```

Fixing the ranker gates (R1/R2) and the summary coverage gap are **high-value, low-risk, independently shippable**. Fixing the over-merge (O1–O3) is the **highest-leverage** change but the **highest regression risk** (coupled to the 42-fixture validation suite + the documented 217/362-source mega-cluster history). Recommended order in §6.

---

## 5. Optimization plan

Each item: **why · what it optimizes · expected result · regression potential · test case.**

### Theme A — Clustering (master cause)

**O1 — Tighten Phase-1 agglomerative clustering.**
- *Why:* `average` linkage at `STORY_TFIDF_THRESHOLD=0.18` (`story_cluster.py:63,2102`) chains unrelated topics; the 50-article cap is the only brake (19/50 pinned at 50; median coherence 42%).
- *Optimizes:* cluster coherence — the master signal; cascades to source_count integrity, content_type accuracy, categorizer purity.
- *Change:* raise threshold 0.18 → ~0.28–0.32 and/or switch linkage `average`→`complete`; raise Phase-1 `min_df` 1→2 (`:2096`).
- *Expected:* median coherence 42%→≥70%; clusters-<25% 38%→<10%; the 50-article spike disappears; `source_count` reflects real coverage.
- *Regression:* **HIGH** — may over-split legitimately large breaking clusters (the 117-article Iran-US war; the 217/362-source mega-event history). Tune on the live snapshot first.
- *Test:* `python pipeline/validation/runner.py --verbose --json` ≥ baseline (33C/2A/3W) AND re-pull today's feed → median coherence ≥70% AND the 5 known-good big clusters stay single (not split).

**O2 — Same-publisher dominance guard on the entity-merge phases.**
- *Why:* `min_df=1` + `MIN_DISTINGUISHING_SHARED=1` (`story_cluster.py:412`) let one outlet's boilerplate self-cluster (NADI 80% Malay Mail; Indigenous-Woman NY Sun+National Post).
- *Optimizes:* kills the single-publisher contamination class specifically.
- *Change:* raise `MIN_DISTINGUISHING_SHARED` 1→2; refuse a Phase-2/3 merge when one `source_id` would exceed ~50% of the group (wire in the already-computed `dominant_publisher_share`).
- *Expected:* ~6–8 of the 19 worst clusters dissolve into their component stories.
- *Regression:* MEDIUM — a genuine single-source scoop could split; gate only when group size > ~10.
- *Test:* no top-50 cluster >50% articles from one `source_id` (today 5+ violate); validation suite unchanged.

**O3 — Make the Phase-5 mega-guard fire on article-count + cohesion, not just `source_count≥75`.**
- *Why:* the guard triggers only at 75 sources (`story_cluster.py:662,1570`); 50-article/low-voice bags pass (`mega_cluster_capped` 1/80), which also disables the ranker's over-merge penalty.
- *Optimizes:* a working brake on the exact over-merge class that fills the feed; restores the ranking penalty.
- *Change:* add an article-count trigger (≥60) to the Phase-5 gate; lower `MEGA_COHESION_MIN_SOURCES` 40→~8 (`:1695`); wire `_cluster_cohesion` into a real force-split (`:1547`).
- *Expected:* low-coherence bags split or flagged; `mega_cluster_capped` (+0.65× rank penalty) starts firing on real over-merges.
- *Regression:* MEDIUM — could split a coherent large cluster; gate the split on low cohesion only.
- *Test:* today's 19 worst clusters split/flagged; the 117-article Iran-US war cluster (98% coherent) is NOT split.

### Theme B — Summary

**O4 — Eliminate the 16 NULL slots: write a clean summary on every skip/fail branch.**
- *Why:* `<3 articles`/`opinion`/generation-failure all `continue` without writing (`cluster_summarizer.py:1236-1267`), leaving the raw, often off-topic step-8 excerpt.
- *Optimizes:* summary coverage (32%→0% raw) + topical accuracy of the displayed card.
- *Change:* on each skip/fail branch, synthesize a deterministic clean summary from the cluster's on-topic members (title-matching excerpt) and stamp a `rule-based` tier so it is never NULL/misleading. No new LLM calls.
- *Expected:* every displayed card shows an on-topic summary; zero title/summary cross-story mismatches.
- *Regression:* LOW — deterministic fallback; worst case a blander summary (still better than off-topic).
- *Test:* re-run step 8d on today's 50 → 0 displayed NULL tiers AND every summary shares ≥1 headline keyword (reuse `coherence.py` on summary-vs-title).

**O5 — Make the show-don't-tell / em-dash check enforcing (mutating) on BOTH paths.**
- *Why:* the check only `print()`s (`cluster_summarizer.py:829-834`); "significant" survives in 8 LLM summaries and em-dashes in all fallback text. CLAUDE.md's "regex post-check" claim is inaccurate.
- *Optimizes:* editorial-style compliance (the no-em-dash + show-don't-tell cardinal rules).
- *Change:* one shared mutating sanitizer (strip/replace em-dashes, rewrite/remove banned tells, strip outlet suffixes, guard non-Latin) applied to every title+summary write including the rule-based fallback (`story_cluster.py:232-251` → `main.py:2562-2563`).
- *Expected:* 0 banned tokens / em-dashes / outlet suffixes displayed.
- *Regression:* LOW — textual only; keep "significant" rewrites conservative.
- *Test:* regex sweep over today's 50 titles+summaries → 0 hits for `—|–|significant|notable|interestingly|crucially| - (WSJ|AP News|Reuters|TheCable|Just The News)$`.

**O6 — Clean fallback titles: strip outlet suffixes, flag/translate non-English.**
- *Why:* `_clean_title` strips only a fixed wire allow-list (`story_cluster.py:88-111`) → "- WSJ", "- TheCable", "- Just The News" and a Spanish headline reach the feed.
- *Optimizes:* headline professionalism.
- *Change:* generalize the suffix stripper to ` - <known source name>$` using the sources table; prefer an English member's title when the chosen title is majority non-ASCII.
- *Expected:* no outlet-suffixed/foreign headlines on the English feed.
- *Regression:* LOW — strip only when the suffix matches a known source name.
- *Test:* no top-50 title matches the outlet-suffix pattern or >30% non-ASCII.

### Theme C — Ranking

**O7 — Demote opinion and sports in the ranker.**
- *Why:* the ranking path never reads `content_type` (`importance_ranker.py:1127`); the soft-news gate keys on `category` not `story_type` (`:1424`); `STORY_TYPE_GATES` lacks `entertainment` (`feed_ranker.py:26-29`) → 10/50 slots (incl. top-10) are op-eds/sports.
- *Optimizes:* editorial purity; frees ~10 premium slots for hard news.
- *Change:* pass `content_type`/`story_type` into `rank_importance`; add an opinion gate (×0.70–0.75); fire the soft-news gate on `story_type=="entertainment"`; add `entertainment:0.78` to `STORY_TYPE_GATES`.
- *Expected:* op-eds + sports leave the top ~25; Harry Styles/Bafana/England leave the top 10.
- *Regression:* LOW-MEDIUM — over-demoting a World Cup final or landmark op-ed; tune multiplier; mid-feed still allowed.
- *Test:* re-rank today → 0 opinion/sports in top 10, ≤2 in top 25; the brief's hard-news `top_cluster_ids` all surface in top 12.

**O8 — Consolidate same-event fragments instead of gently decaying them.**
- *Why:* decay-only handling (`feed_ranker.py:132-143`) penalizes the richest cluster — Iran-US war (75 sources) gets ×0.80 → #35 while a 24-source framing leads at #2.
- *Optimizes:* top-story relevance + feed diversity (one strong slot for the megastory, not 5 weak ones).
- *Change:* within an event group, exempt the highest-source canonical cluster from decay, union sibling source coverage into it, and suppress / progressively decay (0.6, 0.4, …) the rest; consider `MAX_SAME_EVENT=1` in the lead region.
- *Expected:* Iran/Gulf consolidates to 1 top-3 slot reflecting ~100+ sources; the 4 redundant fragments leave the feed.
- *Regression:* MEDIUM — static `EVENT_KEYWORDS` (`feed_ranker.py:50-84`) could group distinct stories sharing a keyword; make the canonical-pick coherence-aware.
- *Test:* today → Iran/Gulf occupies 1 (≤2) top-10 slots not 5; the survivor is the 75-source cluster; distinct mega-topics in top 20 ≥ 12.

**O9 — Discount `source_count` by topical coherence in the importance score.**
- *Why:* `source_count` drives ~36% of the score + gates confidence/longevity/headline floors (`importance_ranker.py:520,1081,1348,1541`) with no coherence signal — a 16%-coherent 38-source bag buys a slot + badge.
- *Optimizes:* signal integrity; de-inflates the "X sources" badge; defense-in-depth even if O1–O3 don't fully split a bag.
- *Change:* compute a per-cluster coherence factor at clustering time, store it, multiply `weighted_count` by it before `_source_coverage_score` (`:520`); optionally promote the already-computed `wire_amp` to a standalone penalty.
- *Expected:* over-merged bags lose rank inflation; clean big stories keep their rank.
- *Regression:* LOW-MEDIUM — needs a reliable coherence metric; ship AFTER O1–O3 so the discount is rarely large.
- *Test:* today → the 19 worst clusters drop below rank 50; badge count ≤ on-topic article count.

### Theme D — Categorization

**O10 — Categorize on the headline + full membership, and split tech from science.**
- *Why:* category is voted on the first 3 sampled members (`main.py:1982`), polluted on over-merged clusters; `technology→science` collapse (`auto_categorize.py:281`) + weak science lexicon (`:176-190`) → 11/50 mislabeled science.
- *Optimizes:* category accuracy (section tags + the topic-diversity partition the ranker depends on).
- *Change:* categorize the cluster HEADLINE as a strong prior + vote across more/all members (`sample[:3]`→`[:8]`/all); split `technology` into its own desk (or map→science only when science keywords co-occur); demote weak science terms.
- *Expected:* top-50 science count 11→~2–3 real science; conflict/sports/disaster correctly tagged.
- *Regression:* LOW — self-contained classifier change.
- *Test:* re-categorize today → Ukraine-drone/Zaporizhzhia/Israel-Hezbollah=conflict, England/Colombia=sports, Beijing-crash=disaster; ≤3 science.

**Watch-item (not a standalone fix):** the `rank_world` staircase clamp (`feed_ranker.py:235-239`) compresses ranks 11–26; account for it in any reweighting work so real `headline_rank` separation isn't discarded.

---

## 6. Suggested iteration sequencing

1. **Wave 1 — low-risk quick wins (visible immediately, independently shippable):** O5 (sanitizer), O6 (title clean), O7 (opinion/sports demotion), O10 (categorizer). Surgical, low regression, big perceived-quality jump.
2. **Wave 2 — medium-risk:** O4 (summary coverage fallback), O8 (event consolidation), O9 (coherence discount). O9 also de-risks Wave 3 by capping the rank impact of any remaining over-merge.
3. **Wave 3 — highest leverage, highest risk, done last with the full safety net:** O1–O3 (clustering over-merge), tuned against the validation suite + a live-snapshot coherence check, with the validate-clustering CI gate enforced.

Every change re-runs `pipeline/validation/runner.py` (+ `validate-clustering` / `validate-bias` CI gates) and a fresh live-feed re-pull to confirm the metric moved without regressing the known-good clusters. After landing, run `update-docs` to correct the inaccurate CLAUDE.md rev-50 ("full-50 summary coverage") and rev-47 ("show-don't-tell regex post-check") claims.

---

*Audit method, raw measurements, and the per-cluster coherence table are reproducible from the scripts used to generate this report (live REST pull + `coherence.py` title-keyword overlap). No production data or code was modified during this audit.*
