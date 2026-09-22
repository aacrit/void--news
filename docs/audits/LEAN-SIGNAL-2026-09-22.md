# Can the outlet baselines be derived from our own data?

Measured 2026-09-22 against the `void-state-snapshot` artifact from pipeline run
#375 (78,328 articles, each with a bias score). Reproduce with:

    python3 scripts/roster/measure_lean_signal.py <pipeline_state.db>

**Answer: the signal is real, and it is not the sample size that is stopping
us. It is that the lexicon says nothing about three articles in four.**

---

## The one trap this had to avoid

The published `political_lean` is `baseline + shift`. Deriving a baseline from
it would read the engine's own output back into its own prior, which is the
loop cut earlier the same day and now gated by
`tests/test_lean_prior_is_not_self_fed.py`. It would be a particular kind of
absurd to reopen that loop with the work meant to fix the baselines.

The only non-circular signal stored per article is
`rationale.lean.keyword_score`: the lexicon's reading of the text alone, which
never sees the outlet. Everything below uses that and nothing else.

## What the data actually contains

| population | rows | share |
|---|---|---|
| articles with a bias score | 78,328 | 100% |
| **usable**: outlet placed on the axis, 150+ words, not `lean_unscored` | 13,268 | 16.9% |
| of those, carrying a stored `keyword_score` | 9,411 | |
| of those, **the lexicon fired at all** | **2,482** | **26.4% of scored** |
| usable articles contributing NOTHING about their outlet | 6,929 | 73.6% |

`keyword_score` is exactly 50.0 when zero lexicon terms match. For 73.6% of the
articles the scorer could fully read, that is what it is.

## Sample size, and the distinction that matters

| | outlets |
|---|---|
| with any signal at all | 199 |
| **median signal-bearing articles per outlet** | **8** |
| n >= 5 | 129 |
| n >= 10 | 84 |
| n >= 25 | 20 |
| n >= 30 | 17 |
| n >= 50 | 8 |
| n >= 100 | 1 |

**This corrects an earlier estimate in this project's own notes.** A previous
pass reported "229 outlets, median 31, 116 at n >= 30, the core already has the
sample size", and concluded no harvest was needed. That counted USABLE
articles. The number that governs a per-outlet estimate is the SIGNAL-BEARING
count, and it is 26.4% of usable: median 8, and only 20 outlets at n >= 25.
The earlier conclusion ("no harvest needed") happens to survive, but not for
the reason given, and the timeline built on it was too optimistic.

## Is the signal real? Yes.

Spearman rank correlation between an outlet's mean text-only score and its
label's numeric baseline. Rank, not linear, because the magnitudes are known
to differ.

| floor | outlets | rho | US | non-US | text spread | ladder spread |
|---|---|---|---|---|---|---|
| n >= 5 | 129 | **+0.479** | +0.515 (81) | +0.428 (48) | 36.3-68.3 (32 pts) | 10-90 (80 pts) |
| n >= 10 | 84 | **+0.487** | +0.515 (53) | +0.414 (31) | 36.3-65.7 (29 pts) | 80 pts |
| n >= 25 | 20 | **+0.630** | +0.474 (17) | n too small | 41.4-65.7 (24 pts) | 80 pts |

Two things follow, and they point in opposite directions.

**The signal is at the published ceiling already.** This project's own
literature review put the realistic ceiling at "rank correlation 0.5 to 0.7
against outlet-level human labels, in aggregate over 50+ articles per outlet,
for partisan English" (BABE's five trained experts agree with each other at
Krippendorff alpha 0.40; the best fine-tuned BERT reaches F1 31.49 on lexical
bias). We are at 0.48 to 0.63 on 8 to 25 articles. That is not a broken
detector.

**And it holds outside the US**, at +0.41 against +0.51. Weaker, not absent.
That qualifies an earlier finding in `docs/OPEN-ITEMS.md` that the lexicon is
"flat outside US politics": it fires less often there, and when it fires it is
still directionally right.

**But the magnitude is compressed by roughly 3x.** 29 points of text spread
against 80 points of ladder. The engine is being asked to move a score along a
ladder three times wider than anything its own evidence can span, which is the
real reason the published lean sits so close to the label.

The ordering is visibly correct at the extremes:

| outlet | label | text reads | n |
|---|---|---|---|
| Truthout | far-left (10) | 41.4 | 30 |
| Common Dreams | far-left (10) | 45.4 | 41 |
| The Atlantic | center-left (35) | 48.7 | 34 |
| PJ Media | right (80) | 56.8 | 95 |
| Townhall | right (80) | 57.6 | 139 |
| The Daily Signal | right (80) | 65.7 | 70 |

## What this means for the plan

**More articles is the wrong lever.** Waiting doubles n and moves rho by
roughly nothing, because rho is already at its ceiling and the constraint is
coverage, not precision. Lexicon coverage is the right lever: firing on 50% of
articles instead of 26% would take the median outlet from 8 signal-bearing
articles to ~16 and put ~80 outlets over n=25 instead of 20, at once, without
waiting a day.

**What can be published now, honestly:**

1. A validation figure. rho = +0.48 across 129 outlets is a real, defensible
   number and it belongs on `/sources#methodology` beside the claim that the
   engine weighs both. It is validated against our own curated labels rather
   than an independent panel, and that has to be said in the same sentence.
2. A band, not a point, wherever the evidence is thin. A continuous 0-100
   implies a resolution that 8 signal-bearing articles and a 29-point spread do
   not support.

**What has to happen before a derived baseline can replace a curated label:**

1. Lexicon coverage, per market. This is the long pole and it is linguistic
   work, not compute.
2. An independent anchor. Our labels are partly informed by the same public
   ratings we would validate against, so rho against them is
   semi-independent. MARPOR/CMP manifesto scores are the non-circular option
   this project has already identified.
3. `_TEXT_DELTA_MAX` can only rise once 1 and 2 hold. Raising it on a signal
   that spans 29 points would let noise move a published score.

## What is NOT claimed here

- That a single article can be scored to this accuracy. Per article the same
  literature puts it near zero, and nothing here contradicts that.
- That the curated labels are correct. rho measures agreement, and both sides
  could be wrong together.
- That 73.6% silence is a bug. It is a coverage limit of a rule-based lexicon,
  which is the documented, deliberate design (no LLM in bias scoring, $0/day).
