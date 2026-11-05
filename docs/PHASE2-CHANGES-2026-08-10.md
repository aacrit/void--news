# Void News Phase 2: Editorial Audit Fixes, 2026-08-10

Implementation of the CEO-approved fixes from docs/EDITORIAL-AUDIT-2026-08-10.md.
Five independent branches, one concern each (no batching). All findings and
deltas are verified against the live 2026-08-10 run.

## Status at a glance

| Branch | Concern | State | Effect |
|---|---|---|---|
| A `docs-weight-correction` | Docs + public weight claims | merged | live |
| B `clustering-phase2-fix` | Clustering Phase 2/3 contamination (priority) | merged (clustering gate green) | next run |
| C `ranking-guardrails` | Ranking gates and caps | merged | next run |
| D `lean-suppression` | False-center lean label | merged | live on deploy |
| E `source-hygiene` | Journal-errata ingestion | merged | next run |

Frontend changes (A public weight surface, D lean label) go live on the next
deploy. Engine changes (B clustering, C ranking, E ingestion filter) take effect
on the next 11:00 UTC pipeline run, not the currently displayed feed. This is
the same deferral as the Phase 3 summarization prompts already shipped.

---

## Summary of changes

### B. Clustering Phase 2/3 contamination (the big one)

The audit's highest-priority defect: unrelated events merged into one cluster,
which corrupts the lean read and breaks the core product claim. Fixed at the
root, validated against a hand-labeled fixture (topic_coherence was proven blind
to this defect and was not used).

Root cause confirmed by a df probe on the real 1,945-cluster corpus:
contaminating GPEs sit at df 5 to 10 (Assam 5, Kazakhstan 6, Hong Kong 10) while
genuinely story-specific anchors sit at df 2 to 3 (Tatarstan 3, Rezaei 3). The
old `max(5, int(n*0.05))` gate collapsed to about 97 at scale, so every GPE
counted as a discriminative anchor.

Three constant changes in `story_cluster.py`:
1. Phase 2 entity df cap `max(5, int(n*0.05))` replaced with a fixed
   `PHASE2_ANCHOR_DF_ABS = 3` (scale-stable: a story-specific entity stays df 2
   to 4 at any corpus size; a multi-story region grows with volume). IDF was
   evaluated and rejected because the contaminating GPEs score high IDF, so
   corpus rarity is the wrong axis.
2. Phase 2 title bypass retired: `PHASE2_STRONG_DISTINGUISHING = 2` let any pair
   sharing 2 or more entities skip the title-agreement check entirely. Now every
   entity bridge must clear the stemmed-title floor. This was the specific hole.
3. Phase 3 stem df cap `max(5, int(n*0.08))` replaced with a fixed
   `PHASE3_STEM_DF_ABS = 5`.

Result: mean top-30 precision 0.707 to 0.830; clusters below 0.75 went 15 to 8.
Biggest wins: Rezaei 0.06 to 0.86, Trump-Olympian 0.07 to 0.88, Scharf 0.30 to
0.78, Pentagon to 1.00, Assam to 1.00, Banerjee to 1.00, Sydney to 0.88.

Clustering validation gate: 34 CORRECT / 4 ACCEPTABLE / 3 WRONG / 0 CATASTROPHIC.
No new WRONG or CATASTROPHIC versus the 38/0/3/0 baseline (the 3 WRONG remain the
documented obsolete section-classification fixtures). Gate passes.

### C. Ranking guardrails

Four changes across `feed_ranker.py` and `importance_ranker.py`, verified by
replaying `apply_feed_ordering()` on the live pool (reproduces stored rank_world
exactly through rank 31).

1. incremental_update gate guardrail. The 0.75x gate is now suppressed when the
   story is clearly major or still breaking, on any of: first-article age under
   12h, source_count at or above 20, or coverage_velocity at or above 7. The
   Gemini story_type prompt was also tightened so decisive outcomes (results,
   verdicts, extraditions, appointments, accidents) are not tagged incremental.
2. Longevity birth-age. `_longevity_penalty` now also factors first-published
   age (0.96 at 24h, 0.93 at 36h, 0.90 at 48h, floored to 0.95 for 30-plus
   source developing stories), so a continuously-refreshed story no longer pays
   zero age toll. Fresh sub-24h stories are untouched.
3. Rank-aware top-10 category cap: a cap-deferred story is pulled up so it never
   falls below a story it out-bases by more than 8 points (CAP_RANK_TOLERANCE=8).
4. editorial_importance applied once: the additive plus/minus 6.7 term was
   removed from importance_ranker; the single ei effect is now the feed_ranker
   multiplicative nudge.

Replay deltas (the audit's buried stories move toward their signal-justified
positions):

| Story | before rank | after rank | mechanism |
|---|---|---|---|
| El-Sayed (Michigan primary) | 21 | 14 | de-gated, 33 sources |
| Sydney near-miss | 25 | 16 | de-gated, 21 sources |
| Kinahan extradition | 17 | 12 | de-gated, velocity 8 |
| Scharf appointment | 15 | 8 | de-gated, velocity 7 |
| Zelenskyy (NK troops) | 11 | 11 | cap penalty removed (rw rises to true base) |

The Zelenskyy inversion is resolved at its root: change 1 also de-gates Tupac,
lifting its base above Zelenskyy's, so no more-than-8-point inversion remains.
The cascade stays strictly decreasing across all 80 rows.

### A. Docs and public weight claims

Four documentation corrections. Notable nuance: the reader-facing weight table
(the /pipeline page and PIPELINE-BRAIN.md) was already correct at 9% spectrum /
3% velocity; the stale 6%/6% lived only in internal agent/skill docs, now fixed.
Added an honest one-line disclosure that coverage (20%) + maturity (16%) + tier
diversity (13%), about 49% combined, all share source_count as an input. Marked
clustering Phase 2.6 as parked/diagnostic-only. Documented the ei double-apply
(now actually resolved by Branch C).

### D. Lean label band suppression (frontend)

The false-center rule only, per the CEO decision (no source-count floor this
pass). Shows "No clear lean" when the aggregated lean is in [48, 52], except when
both wings are genuinely present (left and right counts both positive, total at
least 3), where the existing rev-49 Contested marker renders instead. Applied at
the Sigil and BiasSnapshot label surfaces; the Deep Dive KDE (the analytical
true-distribution view) is deliberately left alone.

Counts on the live 2026-08-10 top-30: 16 of 30 are in band. All 16 resolve to
"No clear lean" and 0 hit Contested (see the first callout below).

### E. Source hygiene

Root cause: Nature's `nature.rss` is the flagship journal feed, which interleaves
research-paper corrections with journalism. Seven junk items in this run (5
"Author Correction", 1 "Publisher Correction", 1 "Editorial Expression of
Concern") leaked into the Hong Kong cluster. Added a prefix-anchored
academic-artifact filter to the step-3c newsworthiness gate, with precision
guards so real journalism survives (Retraction Watch, "police issue correction"
wire phrasing). Verified against the live 11 DB rows: 7 drop, 4 keep, all
correct; 4/4 unit tests pass.

---

## Callouts and comments

1. B tradeoff, accepted deliberately. Four clustering fixtures shifted CORRECT to
   ACCEPTABLE (Trump-Xi, Trump-Iran, Streeting loose multi-desk merges): they now
   fragment into 2 or 3 still-coherent sub-clusters because they lack strong
   title agreement. The audit explicitly prioritizes precision here (two coherent
   cards beat one contaminated card), so this is by design. Worth watching on the
   next live run to confirm it does not fragment genuinely-single major stories.

2. B, the 8 remaining sub-0.75 clusters are not regressions. Four are measurement
   artifacts where the fix actually improved recall (gathered more genuine
   same-event articles than production had), so the fixture, keyed to the smaller
   stored cluster, undercounts them; true precision is high (Houthis about 0.83,
   Kinahan about 1.0, Cape Town about 1.0, Statue of Liberty about 0.85). The
   other four are genuinely sub-0.75 but out of Phase-2/3 scope: Bengaluru 0.57 is
   Phase-1 driven (Phase 1 is off-limits per the audit), and Andhra/Kazakhstan are
   3-article clusters where one different article is pure granularity at 4 to 6
   sources.

3. D, the rev-49 Contested exception is currently dormant on live data. All 16
   in-band stories got "No clear lean" and 0 got Contested, because the live
   `bias_diversity` written by the SQL RPC does NOT contain the rev-49 wing and
   polarization fields at all (only the Python fallback emits them, and it does
   not run when the RPC succeeds). So the rev-49 Contested marker and the
   LeanCoverageBar are effectively off on today's feed. The implementation is
   defensively correct and lights up automatically once the RPC emits the
   histogram. This is a new ticket (see What's next).

4. D, aggregate_confidence root cause found. It is `LEAST(1.0, COUNT/5.0)` in both
   `migrations/002` and `main.py:799`, a saturating article-count proxy that pins
   to 1.0 at 5-plus articles and ignores the per-article `bias_scores.confidence`
   that already exists. That is why it never varies across top stories. Not
   patched (separate ticket, per instruction).

5. Premise corrections from the branches. The public weight table was already
   correct (A). Clustering Phase 2.6 is parked, not the culprit (confirmed in B).
   IDF is the wrong axis for the clustering df gate (B).

---

## What is next

Deploy and effect timing:
- Live on next deploy: Branch A public weight surface, Branch D lean label, plus
  the earlier Phase 0 frontend fixes. A deploy fires on each merge to main.
- Effect on next 11:00 UTC pipeline run: Branch B clustering, Branch C ranking,
  Branch E ingestion filter, plus the Phase 3 summarization prompts.

Verification to run on tomorrow's run:
- Clustering precision on the fresh top-30 (expect the contaminated bags gone).
- The de-gated stories (primaries, accidents, appointments, extraditions) ranking
  in the top 10 to 15 rather than buried.
- Zero Nature "Author Correction" items in the feed.
- The lean label showing "No clear lean" on near-center apolitical stories.

Open follow-up tickets (deferred, need owner or CEO decision):
1. Signal-weight rebalance. Explicitly deferred: the clustering fix changes source
   counts, so the 10-signal weights (breadth is roughly triple-counted at about
   49%) should be reviewed after we see the new source-count distribution, not
   before.
2. aggregate_confidence recompute. Derive it from the mean rigor-weighted
   per-article bias_scores.confidence (and optionally lean_spread) in both the RPC
   and the Python fallback. Until then the frontend confidence gate and the
   display-position confidence damping are effectively dead.
3. rev-49 wing/polarization fields are not emitted by the primary RPC, so the
   Contested marker and LeanCoverageBar are dormant on live data. Emit the
   histogram from the RPC (or route through the Python fallback) to light them up.
4. Source curation: narrow Nature's RSS from the journal feed to a news-only feed
   so research-paper content stops at the source (source-curator's call).
5. Watch the four loose multi-desk merges (Trump-Xi, Trump-Iran, Streeting) on
   live data to confirm the precision-first fragmentation does not hurt a genuine
   major story.
