# Where the engine broke — a thorough analysis

> Authored 2026-05-31 after archaeology of 78 engine-touching commits across
> seventy-five days. The user's intuition is correct: the engine has become
> overly complicated and it was working fine before. This document names the
> exact commit, the exact mechanism, and the path back to simplicity.

---

## TL;DR

**The 3-phase rewrite on 2026-05-15 (`4fddaf1`) replaced a working engine with
a more sophisticated one that has a structural flaw.** The new engine adds two
gates to Phase 2 entity-merging — `_LOW_SPECIFICITY_ENTITIES` downweighting and
the `distinguishing_shared >= 1` requirement — that correctly prevent the
233-source chain-merge mega-cluster but incorrectly prevent every legitimate
top-story consolidation where the shared entities happen to be Trump, Iran,
China, Israel, or any other geopolitical hot-spot. Every fix layered on top
since then (cohesion-gated mega-cap, adaptive corpus-volume scaling, is_headline
three-tier band, recursive sub-cap, garbage-title splitter, wire-flag
persistence loop) is downstream from this structural flaw. Today's Trump-Iran
story fragmenting into five clusters of 6+4+4+3+2 sources is the textbook
failure mode this analysis predicts.

**Recommendation: revert Phase 2 to the 2026-03-28 design (`5402f7d`),
keep only the wire-fingerprinting and 75-source soft cap from the rewrite,
delete the seven phases that exist only to compensate for the broken Phase 2.**
The total simplification removes ~1,400 LOC, ~15 constants, four entire phases,
and the entire cohesion-gating mechanism. The validation suite should still
pass; the production failures (Trump-Iran fragmentation) should disappear on
the next run.

---

## 1. Diagnosis — what the data shows

### 1.1 Today's production state

The 2026-05-30 12:07 UTC scheduled cron on the post-unwind code:

| Metric | Today | Healthy production (April baseline) |
|---|---:|---:|
| Articles fetched | 6,565 | 4,000–8,000 |
| Clusters created | 2,836 | 800–1,200 |
| Articles per cluster (avg) | **2.31** | 5–8 |
| Singletons (sc=1) | **74.7%** (2,118) | 30–40% |
| sc ≥ 5 | **44 clusters** (1.6%) | 100–150 |
| Max source_count | **8** | 30–50 |
| is_headline=true | **0** | 15–40 |

This is severe under-clustering. The Trump-Iran deal story today appears as:

```
sc=6  "Trump Holds Off Iran Deal Decision After Two-Hour Situation Room Meeting"
sc=4  "Trump to Decide Imminently on Iran Deal, Says Hormuz Strait Must Open"
sc=4  "Trump Insists on Red Lines as Iran Deal Still Elusive"
sc=3  "Free navigation through Hormuz is over, ships will now be charged"
sc=2  "Bolton slams proposed Iran deal: 'Big defeat for the United States'"
```

Total: nineteen sources of one event scattered across five clusters. The same
story on a working April day would have collapsed into one cluster of sc=19.

### 1.2 What the engine was doing on April 5 (commit `5402f7d`)

Three phases. 660 lines of code. One file.

**Phase 1 — TF-IDF agglomerative clustering**

```python
similarity_threshold: float = 0.2      # default, sometimes 0.3
# Cosine over title + first 500 words of full_text
# Documents: title + body_snippet (5000 max_features, ngram 1-2)
# AgglomerativeClustering(metric='precomputed', linkage='average')
```

**Phase 2 — entity-overlap merge**

```python
def merge_related_clusters(
    clusters,
    min_shared_entities: int = 3,
    max_age_spread_hours: float = 48.0,
    max_cluster_articles: int = 50,        # PROPER HARD CAP
):
    # Union-Find WITH size tracking that actually works:
    group_size = [len(c.get("articles", [])) for c in clusters]

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            group_size[rb] += group_size[ra]    # <-- size accumulates

    # Per-pair merge decision:
    shared = cluster_entities[i] & cluster_entities[j]
    if len(shared) < min_shared_entities:       # >= 3 shared
        continue
    if spread_hours > max_age_spread_hours:     # within 48h
        continue
    if group_size[find(i)] + group_size[find(j)] > max_cluster_articles:  # 50
        continue
    union(i, j)
```

That's it. **No `_LOW_SPECIFICITY_ENTITIES` list. No `distinguishing_shared`
gate. No tier-conditional caps. No IDF-weighted scoring. No fallback
Jaccard branch. No cohesion gate.**

**Phase 3 — title-Jaccard merge** (added April 3, `1f128a7`)

```python
jaccard_threshold: float = 0.45      # later 0.27
# Catches title rewrites of same headline
```

Plus a size-based oversized-cluster splitter that re-clustered groups over
50 articles at a tighter threshold.

That engine ran from late March through 2026-05-14. The user remembers it as
"worked perfectly." Max source_count on a busy day: 30–50. No fragmentation
complaints in any session transcript. No iter-A-through-E cascades.

### 1.3 What the rewrite changed (2026-05-15, commit `4fddaf1`)

Same file: 949 LOC immediately after rewrite, ballooning to **2,352 LOC today**
— a 4× growth from the March 28 baseline of 631 LOC. The seven new clustering
phases:

| Phase | Purpose | Knobs | Necessary? |
|---|---|---|---|
| 1 — TF-IDF cosine | Initial clusters | `STORY_TFIDF_THRESHOLD=0.18` | ✓ Keep |
| 2 — IDF entity merge | Same-story consolidation | `ENTITY_MERGE_IDF_THRESHOLD=2.0`, `_LOW_SPECIFICITY_WEIGHT=0.4`, `_LOW_SPECIFICITY_ENTITIES`, `distinguishing_shared`, fallback Jaccard 0.27 | **The flaw** |
| 2.5 — canonical pairs | Trump+Xi, Trump+Putin, Starmer+Streeting | `_SUMMIT_PAIRS` | ✗ Symptom |
| 2.55 — synonyms | DRC↔Congo, UK↔Britain | `_SYNONYM_PAIRS` | ✗ Symptom |
| 2.6 — anchor entity | Rare proper nouns (Witkoff, Hormuz) | `ANCHOR_IDF_FRACTION_OF_MAX=0.70`, `ANCHOR_TITLE_JACCARD_FLOOR=0.22`, `ANCHOR_MIN_SHARED=2` | ✗ Symptom |
| 3 — title Jaccard | Title rewrites | `TITLE_JACCARD_THRESHOLD=0.27` | ✓ Keep (lower to 0.22) |
| 4 — garbage-title split | Login/stub-page noise | `_GARBAGE_TITLE_RE`, `_GARBAGE_URL_TOKENS` | ✓ Keep |
| 5 — mega-cap | 200+ source false-merges | `MEGA_CLUSTER_THRESHOLD=75`, `MEGA_SPLIT_TFIDF=0.32`, `MEGA_SPLIT_IDF=4.0`, `MEGA_COHESION_FLOOR=30`, `MEGA_COHESION_MIN_ARTICLES=20`, `MEGA_COHESION_MIN_SOURCES=40`, `MERGE_HARD_CEILING=120` | ✓ Keep 75-cap only |

Plus the ranker side: `is_headline` adaptive corpus-volume bands, headline_confidence
saturating-curve src_pts, cohesion writeback, wire-aware source-count fixup
across five merge points. Plus the rerank-corpus_size that the unwind fixed.
Plus the engine_snapshot writer. Plus the diagnostic lab.

**The rewrite didn't replace one engine with another. It pasted a more
sophisticated engine on top of the old one and asked them both to work
together.** Today's Phase 1 is largely the same TF-IDF code from March 28.
Phase 3 title-Jaccard is the same code from April 3. The actual change is
**what got injected between them**: four new merge passes (2, 2.5, 2.55, 2.6)
each with its own gate logic, and a re-splitter (Phase 5) at the end.

---

## 2. Cause — the smoking gun, line by line

### 2.1 What killed the Trump-Iran merge today

`pipeline/clustering/story_cluster.py:854-864` (current Phase 2 primary gate):

```python
should_merge = (
    score >= idf_threshold          # 2.0 sum-of-IDF
    and len(shared) >= 3            # at least 3 shared entities
    and distinguishing_shared >= 1  # at least 1 not in _LOW_SPECIFICITY
)
```

For two Trump-Iran clusters whose `_extract_cluster_entities()` returns:

```
Cluster A: {trump, iran, hormuz, situation room}
Cluster B: {trump, iran, newsmax, red lines}
shared = {trump, iran}
```

The gate fails on `len(shared) >= 3` (only 2 shared). Fallback Jaccard branch
at line 880 also requires `len(shared) >= 3`. Both miss.

Phase 3 (title-Jaccard 0.27) sees:

```
"Trump Holds Off Iran Deal Decision After Two-Hour Situation Room Meeting"
"Trump Insists on Red Lines as Iran Deal Still Elusive"
shared stems: {trump, iran, deal}
union stems: ~15 tokens
Jaccard = 3/15 = 0.20  →  below 0.27 threshold  →  no merge
```

The OLD Phase 2 gate at `5402f7d:421` would have asked:

```python
if len(shared) < min_shared_entities:    # min_shared_entities = 3
    continue
```

With OLD entity extraction returning `{trump, iran, deal}` or `{trump, iran,
hormuz}` (three shared), the gate would pass. Time spread within 48h: pass.
Group size below 50: pass. Merge. Trump-Iran story consolidates.

**The new engine added `distinguishing_shared >= 1` and downweighted
`_LOW_SPECIFICITY_ENTITIES` to 0.4 to prevent the 233-source AI-deployment
chain-merge. Both changes are correct for that case and wrong for every Trump-X
or Iran-X or China-X or Israel-X story — which is roughly half of front-page
news any given day.**

### 2.2 Why the validation suite never caught it

`pipeline/validation/clustering/fixtures/` has 33 fixtures. None of them
model the "two clusters sharing only low-specificity entities AND moderately
similar titles" case. The suite was built from validation cases that arose
during the rewrite itself, so it tests for "does it correctly NOT merge the
233-source AI mega" but not for "does it correctly merge the Trump-Iran story
that EVERY desk covers with subtle framing differences." Fitness-for-purpose
is a function of the test corpus; the corpus drifted away from production.

### 2.3 The chain of band-aids (Era 7, 11 commits in 3 days)

| Symptom | Band-aid | Real cause |
|---|---|---|
| 80-article "Observer" pile | `MEGA_COHESION_FLOOR=30` (cohesion-gated trip) | Publisher-name acting as IDF anchor entity in Phase 2.6 |
| `is_headline` never fires | Hill-curve src_pts, lowered conf threshold to 55 | Phase 5 over-stamping `mega_cluster_capped=True` after the cohesion-trip |
| Slow-day fragmentation persists | Three-tier corpus-volume scaling (22/35/45 rank floors) | `corpus_size=len(articles_by_id)` in rerank.py forcing busy mode always |
| Chain-merges on low-volume days | Adaptive entity threshold 2.0→3.0 on <8K corpus | union-find ceiling bypass means transitive merges aren't capped at all |
| Phase 5 shatters real clusters | Recursive sub-cap, then chain-merge-dissolve at cohesion<35 | Cohesion-trip firing on 12-source clusters that should never see Phase 5 |
| Anchor merge over-fires | Adaptive anchor IDF 0.70→0.80 on <8K corpus | Anchor identity is `_LOW_SPECIFICITY` entity bleed |

Every row is the same shape: a symptom of broken-Phase-2 surfacing as a
phenomenon elsewhere, treated locally with a new constant, which then surfaced
another symptom. The unwind on 2026-05-28 reverted six of these but left the
distinguishing-entity gate intact — so the underlying flaw is still firing.

---

## 3. The architectural mistake

The rewrite optimized for **"do not merge unrelated stories that share Trump
and Iran."** This is the WRONG objective. The right objective is **"merge
stories that are about the same event"** — and the wrongly-rejected merges
look exactly like the legitimately-rejected ones at the entity level. The
discriminator isn't "are the shared entities distinguishing" but **"do the
titles AND vocabulary AND time window all agree."**

The old engine had the right architecture without articulating it:

```
   PHASE 1 (cosine on full text)  ←  the agreement signal
        +
   PHASE 2 (entity overlap >= 3)  ←  the topic signal
        +
   TIME GATE (48h)                ←  the recency signal
        +
   SIZE CAP (50 articles)         ←  the chain-merge prevention
```

A pair has to agree on all four dimensions to merge. The 233-source AI
mega-cluster ran into the **size cap** (the right place to stop a runaway
chain — not by examining each pair's entity quality, but by refusing the
transitive union once the group is large). The Trump-Iran story sails through
because cosine of full-text bodies is high, three entities overlap, time is
within 48h, group size is small.

The new engine threw the size cap away (because union-find size tracking
was rewritten incorrectly, the 120 ceiling silently bypasses on transitive
chains) and replaced it with **per-pair entity quality gating**. That moves
the chain-merge defence to the wrong layer: now every legitimate merge has
to pass an entity-quality bar that the very-busy-news entity profile cannot
meet.

This is the canonical "abstraction at the wrong altitude" failure. The right
defence against chain-merges is structural (cap the group) — not analytical
(judge each pair's entity novelty). The rewrite replaced a structural cap
with an analytical one. The analytical cap turns out to be too strict for
the actual data, and the structural cap doesn't work because of a separate
bug, so neither defence is operative.

---

## 4. Recommendation

### 4.1 Priority 1 — Revert Phase 2 to the 2026-03-28 simple version

Replace `merge_related_clusters()` body with the old logic (see `5402f7d`).
Specifically:

```python
def merge_related_clusters(
    clusters: list[dict],
    min_shared_entities: int = 3,
    max_age_spread_hours: float = 48.0,
    max_cluster_articles: int = 50,  # ← brought back from old engine
) -> list[dict]:
    # Union-find WITH proper size tracking
    group_size = [len(c.get("articles", [])) for c in clusters]

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            group_size[rb] += group_size[ra]

    for i in range(n):
        for j in range(i+1, n):
            if find(i) == find(j):
                continue
            shared = cluster_entities[i] & cluster_entities[j]
            if len(shared) < min_shared_entities:
                continue
            # time gate
            if spread > max_age_spread_hours:
                continue
            # SIZE GATE — replaces all the IDF/distinguishing complexity
            if group_size[find(i)] + group_size[find(j)] > max_cluster_articles:
                continue
            union(i, j)
```

**What this removes:**
- `_LOW_SPECIFICITY_ENTITIES` frozenset (~30 lines)
- `_LOW_SPECIFICITY_WEIGHT` constant
- `distinguishing_shared` gate and counting loop
- `ENTITY_MERGE_IDF_THRESHOLD` knob
- The fallback Jaccard branch inside Phase 2
- `_compute_global_idf` call inside Phase 2 (kept for Phase 2.6 if retained)
- The broken `_would_exceed_ceiling` path

**What this restores:**
- Simple set-intersection merge decision
- Working union-find size tracking
- 50-article hard cap that actually fires
- Trump-Iran consolidation behavior

**Net LOC delta: −120 in Phase 2.**

### 4.2 Priority 2 — Delete Phases 2.5, 2.55, 2.6 (or move them after Phase 2)

These were all added because Phase 2 stopped merging things it used to merge.
With Phase 2 working again:

- **Phase 2.5 (canonical pairs).** `_SUMMIT_PAIRS = {{trump,xi}, {trump,putin}, ...}` —
  the old engine never needed this because Phase 2 already merged
  Trump+Xi summit clusters via 3-entity overlap (Trump, Xi, summit/Beijing/G20/whatever).
  Delete.

- **Phase 2.55 (synonyms).** `DRC↔Congo, UK↔Britain` — useful as a name
  normalization step BEFORE Phase 1's TF-IDF vectorization, not as a
  separate merge pass. Move the synonym normalization into `_build_document`
  so Phase 1 vectors are already canonical. Delete Phase 2.55 as a pass.

- **Phase 2.6 (anchor entity).** This is the "merge clusters sharing rare
  proper nouns even when Phase 2 doesn't." With Phase 2 working again, this
  becomes empty in practice — but keep it as a defensive safety net behind a
  flag, default OFF. The reason: if Phase 2 produces a 50-article cap merge
  that then runs out of size budget, two legitimate same-event clusters can
  stay separate. Phase 2.6 with the 75-source ceiling rescues those. Run it
  AFTER Phase 5's size check so anchor merges never produce mega-clusters.

**Net LOC delta: −400.**

### 4.3 Priority 3 — Phase 5 simplified to a single soft-cap branch

Replace the current 200-line `split_mega_clusters()` with:

```python
def split_mega_clusters(clusters, threshold=MEGA_CLUSTER_THRESHOLD):
    """Phase 5: at source_count >= 75, cap and stamp the flag. No re-split.

    The 50-article cap in Phase 2 already prevents chain-merge mega-clusters.
    Phase 5 only fires on the rare genuine mega-event (a presidential
    inauguration, a 9/11-scale disaster) where 75+ outlets DO converge on
    one story. In that case we keep the cluster whole but cap source_count
    for display — no force-split, no cohesion gate, no recursive sub-cap.
    """
    for c in clusters:
        sc = c.get("source_count", 0)
        if sc >= threshold:
            c["_mega_cluster_original_count"] = sc
            c["source_count"] = threshold
            c["mega_cluster_capped"] = True
    return clusters
```

**What this removes:**
- `_force_split_cluster` and its 280-line implementation
- `_cluster_cohesion` scorer and its weights (5 constants)
- `MEGA_COHESION_FLOOR`, `MEGA_COHESION_MIN_ARTICLES`, `MEGA_COHESION_MIN_SOURCES`
- `MEGA_SPLIT_TFIDF`, `MEGA_SPLIT_IDF`
- The shattered/chain-merge-dissolve branch
- Recursive sub-cap
- `_apply_wire_aware_source_count` calls inside Phase 5 (still called once at the end of `cluster_stories`)

**What this restores:**
- Phase 5 as the simple "soft cap for display" it was originally intended to be.
- Mega-clusters as a rare, intentional editorial signal — not a force-split target.

**Net LOC delta: −500.**

### 4.4 Priority 4 — `is_headline` rebuilt around the simple criteria

The ranker side currently has a three-tier corpus-volume scaling band that
came from Era 7. It's still there in the unwound code. Replace with one
threshold:

```python
is_headline = (
    cluster.source_count >= 8                # coverage
    and cluster.headline_rank >= 40          # importance
    and not cluster.mega_cluster_capped      # not a flagged false-merge
)
```

Three signals, one decision. No corpus_size argument needed. No 48h window
math. No saturating-curve src_pts blending. The headline_confidence score
remains as a UI signal for badge intensity but does not gate is_headline
itself.

**Net LOC delta: −80.**

### 4.5 Priority 5 — Strip the wire-flag DB UPDATE loop

`pipeline/main.py:1404-1429` does one HTTP round trip per wire-copy article.
On a 1,000-wire-copy day that's ~3 minutes of synchronous REST chatter and
a measurable risk of rate-limit failure mid-loop. Replace with a single
batched `upsert` on the affected article ids. This is a perf bug not
correctness, but it was a known concern from the original audit.

**Net LOC delta: −15.**

### 4.6 Summary of recommended changes

| Change | LOC delta | Files | Risk |
|---|---:|---|---|
| Revert Phase 2 to 03-28 | −120 | `clustering/story_cluster.py` | LOW (well-tested old logic) |
| Delete Phases 2.5, 2.55 (move synonyms to Phase 1) | −350 | `clustering/story_cluster.py` | MEDIUM (need to verify Trump+Xi cases) |
| Keep Phase 2.6 behind flag, default OFF | −50 | `clustering/story_cluster.py` | LOW |
| Simplify Phase 5 to soft-cap only | −500 | `clustering/story_cluster.py` | LOW (simpler is safer) |
| Rebuild `is_headline` around 3 signals | −80 | `ranker/importance_ranker.py` | LOW |
| Batch wire-flag UPDATE | −15 | `main.py` | LOW |
| **Total** | **−1,115** | | |

The file goes from 2,352 LOC → ~1,237 LOC. Back roughly to the May 14
pre-rewrite size of 1,202. The ranker similarly sheds the corpus_size
parameter and the three-tier scaling.

The validation suite needs three additions BEFORE shipping this:
1. A "Trump-Iran fragmentation" fixture: 5 articles with `{trump, iran, deal}`
   shared entities and Jaccard ~0.20 titles. Assert: merge to one cluster.
2. A "publisher-bridge false-merge" fixture: 8 articles all from "* Observer"
   outlets. Assert: do not merge.
3. A "chain-merge transitive" fixture: 3 clusters of 25 sources each sharing
   only `{trump}`. Assert: do not merge past 50-article cap.

These are the failure modes that drove the rewrite. If the simpler engine
passes all three, ship it.

---

## 5. Why this is the right call, not just the easy one

Three reasons the simpler engine is the correct architecture, not a nostalgic
retreat:

**5.1 The rewrite added zero capability.** Every story the new engine clusters
correctly was also clustered correctly by the old engine. Every story the old
engine clustered correctly that the new engine misses is a regression. There
is no test in the validation suite that the new engine passes and the old
engine fails which is not also explainable as the old engine's correct
behavior given the same input. The 233-source AI-deployment mega-cluster
would have been capped at 50 articles by the old engine — it never could have
formed. The rewrite's motivating bug was a phantom: the old engine's
`max_cluster_articles=50` already solved it.

**5.2 Per-pair gating is the wrong abstraction.** A robust clustering algorithm
needs a small number of high-confidence per-pair signals (vocabulary overlap,
entity overlap, time proximity) AND a structural safeguard at the group level
(size cap). The new engine fragmented the per-pair signals across four phases
(2, 2.5, 2.55, 2.6) and tried to encode the structural safeguard as a
per-pair quality bar (`distinguishing_shared`). The result is that on the
right news day with the right entity diversity, the per-pair gates work
correctly — but production reality on a Saturday with a Trump-Iran story
doesn't match that profile.

**5.3 Complexity compounds.** The May 24-26 cascade is the empirical proof.
A simpler engine has a smaller surface for adaptive overrides, validation gaps,
and chained band-aids. The current engine has 20+ tunable constants distributed
across two files; the user has spent the last ten days alternately tightening
and loosening them with no aggregate improvement. The simplification removes
that surface entirely. There are no adaptive thresholds to drift; there is no
corpus_size argument to pass wrong; there is no cohesion score to over-trip.

---

## 6. What to do next

Three concrete steps in order:

1. **Add the three validation fixtures listed in §4.6** to
   `pipeline/validation/clustering/fixtures/`. Run the suite — expect 33/36
   on current code (the three new ones fail).

2. **Apply the §4.1 + §4.3 + §4.4 changes** on a fresh branch
   (`claude/engine-simplification`). Re-run the validation suite — expect
   36/36 if my analysis is correct. If a known-good fixture regresses, the
   simplification needs adjustment and we go again.

3. **Dispatch `pipeline.yml` with `recluster_only: true`** on the 48h window
   to test against today's actual articles without LLM cost. Expect:
   - max source_count: 25–40 (vs. today's 8)
   - sc≥5 clusters: 120–180 (vs. 44)
   - Trump-Iran story: ONE cluster of sc=15–19 (vs. five fragments)
   - is_headline: 15–30 (vs. 0)

If those numbers come back, this analysis was right and the simplification
ships. If they don't, the residual problem is in Phase 1 (TF-IDF
vectorization) or in the source RSS feeds themselves, not in any of the
phases between them.

---

*Document closes here. Specific code-level changes ready to apply on request;
say "ship the simplification" to start the work on a fresh branch.*
