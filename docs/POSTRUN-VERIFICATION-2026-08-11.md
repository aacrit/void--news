# Void News Post-Run Verification: Phase 2 fixes on live data

Verifies the FIRST pipeline run to execute with the Phase 2 engine fixes
(clustering B, ranking C, source-hygiene E) live. Because those branches merged
to main after the 08-10 scheduled run, and the 08-11 scheduled run was 15-plus
hours out, this was verified on a manually triggered full run completed
2026-08-10 21:09 UTC (a fresh news cycle: a 7.4 Colombia earthquake leads).
Read-only verification. Findings only.

Overall verdict: the fixes are working in production. Clustering precision rose
0.71 to 0.81 with no harmful fragmentation, the ranking guardrails fired on all
gated stories, the Nature errata are gone, and the lean band rule applies. Three
issues surfaced, none a Phase 2 regression on their own axis: a summary-length
regression from the Phase 3 branch (short below the top 10, uncapped above it),
residual clustering over-merge on low-title-agreement clusters (a smaller,
different vector than what B fixed), and the already-known aggregate_confidence
saturation (Branch G).

---

## F1. Fragmentation check: PASS

Zero harmful same-event splits in the top-30. Branch B traded recall for
precision, and the failure mode to catch was a single major story splitting into
multiple cards. It did not happen this cycle.

The candidate case, two El-Sayed clusters, is genuinely distinct, not a split:
- #4 "Abdul El-Sayed Faces Scrutiny Following Michigan Senate Primary" (36
  sources, 62 members): the sprawling primary aftermath, the Obama call and party
  unity, Trump's marriage jibe, GOP defining him, socialism and Medicare columns.
- #26 "El-Sayed Pressed on Ties to Hasan Piker's 9/11 Remarks" (12 sources, 14
  members): one self-contained controversy, all 14 members are the Meet the Press
  Piker/9/11 disavowal arc.
These are two different events about the same person. Merging the tight 14-member
Piker story into the already-broad 62-member aftermath would blend distinct
events. The two headlines share only the stem "el-sayed" (about 1 content stem),
far below the Phase-3 title floor. Under the OLD Phase 2, `PHASE2_STRONG_DISTINGUISHING
= 2` would have let the shared entities (El-Sayed, Trump) bypass the title check
and fuse them. Retiring that bypass is exactly what keeps them apart. Correct.

Other candidates checked and confirmed distinct: Trump appears as subject in six
different stories (childhood-vaccine EO, Scharf, BBC suit, ballroom, reflecting
pool, mail-in ballots), none a fragmentation; two Iran stories (Hormuz vs new
commanders); two White House construction stories (ballroom ruling vs reflecting
pool). All distinct events.

Open watch item: the Trump-Xi / Trump-Iran summit family and the Streeting story
(the loose multi-desk merges the Phase 2 report flagged as most at risk of
fragmenting) are ABSENT from this cycle and could not be tested. They must be
checked on a run where they appear before that watch item is closed.

## F2. Source-count distribution

Fresh top-30: source_count mean 22.6, median 19 (min 7, max 63). The 2026-08-10
pre-fix top-30 was mean about 14, median about 10. Source counts went UP, not
down. The fragmentation signature is a DROP with no news-cycle explanation; the
opposite is observed. The rise is partly a bigger news cycle (the earthquake
carries 63 sources), so this is not a clean like-for-like comparison, but there
is no fragmentation-driven collapse.

## F3. Clustering precision: confirmed improvement

Hand-verified precision (member titles and sources read against the headline
event; topic_coherence deliberately not used, it is structurally blind to this
defect).

| Metric | 2026-08-10 pre-fix live | offline replay predicted | this live post-fix run |
|---|---|---|---|
| Mean top-30 precision | 0.71 | 0.83 | 0.81 |
| Clusters below 0.75 | 15 | 8 | 8 |

The live run lands at 0.81 mean and 8 sub-0.75, on the offline replay's forecast
and a clear lift over the 0.71 pre-fix baseline. The predicted 15 to 8 reduction
reproduced exactly on live data. The precision gain is confirmed in production.

Per-cluster precision (rank, sources, members, hand precision):

| # | src | mem | Title | precision |
|--|--|--|--|--|
| 1 | 63 | 85 | Colombia 7.4 earthquake | 0.94 |
| 2 | 51 | 76 | Netanyahu rejects Gaza plan | 0.95 |
| 3 | 19 | 23 | Trump childhood-vaccine EO | 0.87 |
| 4 | 36 | 62 | El-Sayed Michigan primary | 0.89 |
| 5 | 28 | 33 | Houthis attack Saudi refinery | 0.97 |
| 6 | 35 | 50 | Scharf named WH counsel | 0.56 (flag) |
| 7 | 32 | 42 | Iran/US Hormuz standoff | 0.98 |
| 8 | 31 | 38 | Typhoon Dolphin hits China | 1.00 |
| 9 | 21 | 26 | Taylor Farms jalapeno recall | 0.81 |
| 10 | 41 | 48 | Zuckerberg yacht / Meta AI | 1.00 |
| 11 | 17 | 21 | NY Harbor boat capsize | 0.95 |
| 12 | 23 | 31 | Kinahan extradition | 1.00 |
| 13 | 25 | 28 | Tupac murder trial | 1.00 |
| 14 | 9 | 12 | Trump BBC defamation suit | 0.25 (flag) |
| 15 | 22 | 36 | Mecca defense pact | 0.69 (flag) |
| 16 | 16 | 17 | Western US/Canada wildfires | 1.00 |
| 17 | 33 | 41 | AOC egg freezing | 0.93 |
| 18 | 17 | 21 | Florida AG / WNBA foul | 1.00 |
| 19 | 20 | 28 | Pentagon weapons production | 0.46 (flag) |
| 20 | 12 | 13 | Congo Ebola outbreak | 1.00 |
| 21 | 15 | 15 | Ceuta migrant protests | 1.00 |
| 22 | 8 | 9 | Trump Ballroom unlawful | 0.33 (flag) |
| 23 | 7 | 9 | Amazon Texas data center | 0.22 (flag) |
| 24 | 9 | 12 | Mamata Banerjee convoy attack | 0.83 |
| 25 | 17 | 22 | Ex-Thai MP shooting | 0.50 (flag) |
| 26 | 12 | 14 | El-Sayed / Hasan Piker | 0.86 |
| 27 | 14 | 15 | Trump reflecting pool | 1.00 |
| 28 | 12 | 12 | SCOTUS mail-in ballot plea | 0.33 (flag) |
| 29 | 15 | 20 | Iran names military commanders | 0.90 |
| 30 | 19 | 50 | Jharkhand student protests | 1.00 |

The 8 flagged residuals are OVER-merge (not the F1 fragmentation), on two
vectors:
- Topic/GPE bags surviving on low-title-agreement clusters (the entity-bridge
  class B targeted, still leaking on the weakest cases). The textbook case is #28
  SCOTUS, bridged only by "Supreme Court": it pulls in Assam NRC, a Kejriwal
  collegium item, Kenya and Nepal court stories. Similar: #23 "AI data center"
  bag, #19 Pentagon (Israel-election polls + Ukraine), #25 Thai shooting merged
  with a Philippines weather story, #15 Mecca pact merged with a Saudi factory
  fire, #14 and #22 generic Trump bags. These cluster among the lowest-source
  cards (7 to 9 sources), consistent with the audit's granularity-at-low-source
  note.
- One single-publisher over-merge outside Phase-2/3 scope: #6 Scharf pulled in 11
  distinct Daily Wire articles (real, distinct URLs, 336 to 1156 words: F-16s,
  AOC eggs, a Jane Austen piece, unrelated crime) plus a CBS/NIH bag. This is
  most plausibly Phase-1 TF-IDF latching onto shared Daily Wire page boilerplate,
  a scraper / Phase-1 issue, not the Phase-2/3 entity bridge.

## F4. Ranking guardrails

Six top-30 stories were tagged `incremental_update`, and all six were SUPPRESSED
by the new guardrails (none received the 0.75x gate):

| # | sources | age | velocity | suppressed by |
|--|--|--|--|--|
| 4 | 36 | 39h | 30 | sources >= 20, velocity >= 7 |
| 13 | 25 | 37h | 25 | sources >= 20, velocity >= 7 |
| 14 | 9 | 39h | 8 | velocity >= 7 |
| 18 | 17 | 34h | 13 | velocity >= 7 |
| 26 | 12 | 36h | 9 | velocity >= 7 |
| 27 | 14 | 24h | 14 | velocity >= 7 |

The cascade is strictly decreasing across the top-30, and no story sits below one
it out-bases by more than 8 points. The gate no longer buries decisive events.

Calibration note: every one of the six was suppressed, five of them by the
velocity >= 7 rule. The velocity floor may be permissive enough that the
incremental_update gate now almost never fires. That is safe for the audit's goal
(it stops burying decisive events), but if the gate is meant to still de-rank
genuine slow updates, the velocity threshold is worth revisiting. No fix
proposed here.

## F5. Cheap confirmations

- Nature errata: ZERO "Author Correction", "Publisher Correction", or "Editorial
  Expression of Concern" items in the feed. Branch E is working.
- Lean band: 17 of 30 stories are in [48, 52] and would render "No clear lean"
  (Branch D). Note it renders "No clear lean" for all 17, never Contested,
  because the RPC still does not emit the wing counts (Branch G, ticket 3).
- aggregate_confidence: still pinned at 1.0 for all 30. Confirms the saturation
  bug (Branch G, ticket 2) is unresolved, as expected.
- Summary lengths: a regression from the Phase 3 branch, in BOTH directions, on
  freshly generated summaries (not stale cache):
  - flash-lite (ranks 11 to 50, 38 stories): mean 59 words, minimum 32. These are
    the "extremely short" summaries. The Phase 3 prompt ("at most 90 words, tight
    and specific" plus a terse house-standard example) pushed the smaller model to
    over-compress.
  - flash (top 10): the 90-word trim is NOT firing. British Columbia Wildfires 175
    words, Pentagon 243 words, both generated in this run.
  - Cause is NOT a Gemini limit (0 rate/quota errors, 0 summary failures in the
    run metrics). It is a Phase 3 calibration/wiring defect. Proposed fix: ensure
    the 90-word trim post-check reaches the flash top-10 path, and change the
    prompt from "at most 90" to a target band (about 55 to 90) with a soft floor
    so flash-lite stops over-trimming. Small cluster_summarizer.py change; awaiting
    approval.
- Summary quality spot-check (5 summaries): the terminal-restatement and
  ungrounded-age post-checks appear to be holding on the flash-lite path (no
  restated leads or invented ages observed in the sampled short summaries); the
  primary issue is length, not content.

---

## Summary of verdicts

| Check | Result |
|---|---|
| F1 fragmentation | PASS (zero harmful splits; El-Sayed distinct; summit family untestable this cycle) |
| F2 source distribution | No fragmentation signature (counts up, not down) |
| F3 precision | Confirmed lift 0.71 to 0.81; 15 to 8 sub-0.75, matching the replay |
| F4 ranking guardrails | All 6 gated stories suppressed; cascade clean; velocity threshold worth a look |
| F5 errata | Zero (Branch E working) |
| F5 lean band | 17 of 30 suppressed; Contested still dormant (ticket 3) |
| F5 aggregate_confidence | Still 1.0 (ticket 2, Branch G) |
| F5 summaries | Regression: flash-lite too short, flash uncapped; not a Gemini limit; fix proposed |

## Recommended follow-ups (no code changed here)

1. Summary-length fix (proposed above). Highest-visibility reader-facing issue.
2. Close the fragmentation watch item on a run where Trump-Xi / Trump-Iran /
   Streeting appear.
3. Residual over-merge on low-title-agreement clusters (#28 SCOTUS "Supreme
   Court" GPE bag is the textbook case). A future targeted look at high-frequency
   topic-token bridges, distinct from what B fixed.
4. The Scharf Daily Wire single-publisher over-merge points at a Phase-1 /
   source-hygiene ticket, distinct from Branch B.
5. Revisit the incremental_update velocity >= 7 suppression threshold if the gate
   is meant to still de-rank genuine slow updates.
6. Branch G (aggregate_confidence + histogram emission) remains queued and
   unblocks the display-gain damping and the Contested marker.
