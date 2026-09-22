# Can we rank the outlets from our own data? (2026-09-22)

The question, from the CEO: the baselines govern almost everything about a
published lean, so have we rated the outlets correctly, and can we re-derive
them from the months of data the pipeline has already collected instead of
inventing numbers?

Answer: **the data exists and is recoverable. It is not enough, and the reason
it is not enough is not its volume.**

Everything below is measured, not estimated. The state snapshot was downloaded
and queried directly; the queries are reproducible from the artifact named in
"Where the data actually is".

---

## 1. The baselines have no resolution, which is the premise confirmed

`data/sources.json` stores `political_lean_baseline` as a **string label**,
one of seven, mapped to seven integers in
`pipeline/analyzers/political_lean.py` `BASELINE_MAP` (10/20/35/50/65/80/90).
**Not one of the 1,016 sources carries a number.**

| label | outlets | every one of them scores |
|---|---|---|
| center | **350** | exactly 50.000 |
| unrated | 286 | exactly 50.000 |
| center-left | **163** | exactly 35.000 |
| center-right | 88 | exactly 65.000 |
| right | 70 | exactly 80.000 |
| left | 31 | exactly 20.000 |
| far-right | 15 | exactly 90.000 |
| far-left | 13 | exactly 10.000 |

**636 of 1,016 outlets (63%) resolve to the same number.** AP, AFP, Reuters,
Bloomberg, DW, Nikkei, BBC and 343 others are numerically identical.

The analyser already accepts a numeric baseline (`_is_unrated` returns False
for `isinstance(baseline, (int, float))`), so the plumbing for per-outlet
numbers exists and is unused.

And the article layer does not rescue it. On the 339 rows of the 2026-09-21
export that carry a full lean rationale, `text_shift` runs -10.0 to +11.8 with
a **mean absolute shift of 1.93 points**. The published score is the label,
plus or minus two.

## 2. Where the data actually is

**Not Supabase.** The `backup-db.yml` pg_dumps were Actions artifacts with
`retention-days: 14`. The last run was 2026-08-30 (the cron was disabled at
the Cloudflare migration). Artifact `db-backup-33309697576`, 36.5 MB, reports
`expired: true`, `expires_at: 2026-09-13T11:46:03Z`. **The pre-migration
Supabase history is not recoverable.**

**The state snapshot is, and it is the real archive.** `void-state-snapshot`
from pipeline run #375, artifact id `10656444320`, 99 MB gzipped / 414 MB
open, `expires_at: 2026-12-20`. 90-day retention, uploaded every run. It
contains `pipeline_state.db`:

| table | rows |
|---|---|
| `articles` | 78,328 |
| `bias_scores` | 78,328 |
| `source_topic_lean` | 6,356 |
| `sources` | 1,062 |
| `cluster_articles` | 18,402 |
| `printed_stories` | 1,597 |

`articles.created_at` reaches back to **2026-03-22**. Six months, as expected.

## 3. The depth is an illusion

Articles by ingestion month:

| month | articles |
|---|---|
| 2026-03 | 284 |
| 2026-04 | 720 |
| 2026-05 | 690 |
| 2026-06 | 638 |
| 2026-07 | 699 |
| 2026-08 | 587 |
| **2026-09** | **74,710** |

**95% of the corpus is the last three weeks.** Retention pruned the earlier
months down to a few hundred rows each. Six months of calendar reach, three
weeks of usable density.

## 4. The number that decides it

98.8% of bias rows (77,390) carry a non-empty `rationale`. But the
uncontaminated signal, `rationale.lean.text_score`, is the article's reading
*before* its outlet's baseline is added, and it is present on only:

**13,386 of 77,390 rows (17.3%), across 293 outlets. Median 32 readings per
outlet. 155 outlets have >=30, 47 have >=100, none has >=300.**

The rest are short items and rows written before the rationale was stored.

## 5. And the text signal is flat for almost everyone

Mean text deviation from neutral, the six highest-volume outlets in the
corpus:

| outlet | readings | mean text deviation | stdev |
|---|---|---|---|
| N1 Info | 190 | **-0.10** | 0.64 |
| Euro Weekly News | 184 | **-0.09** | 1.38 |
| **Townhall** | 157 | **+7.07** | 7.49 |
| The National | 153 | **-0.08** | 1.49 |
| The Citizen (South Africa) | 150 | +0.31 | 2.24 |
| ARY News (English) | 150 | +0.11 | 1.47 |

This is the finding. **The text scorer discriminates only for outlets with a
strong lexical signature.** Townhall's copy reads +7 right of neutral and
holds it across 157 articles. Everything else reads 0.0 within noise, and 37%
of full-length articles score `text_score` exactly 50.0.

So re-deriving 730 baselines from this corpus would produce roughly 40
meaningful numbers and 690 zeros. **The bottleneck is not the archive. It is
that the lexicon fires on partisan American vocabulary and is silent on
ordinary reporting in every other register.**

## 6. The learning table already exists, and trusting it today would make
things worse

`source_topic_lean` (schema line 244, written by
`analyzers/topic_outlet_tracker.py`, wired at `main.py:4139`, blended in
`categorizer/auto_categorize.py:356`) is already a per-source per-category EMA
of lean with an `article_count`. 6,356 rows over 853 outlets, 4,484 of them
backed by >=20 articles.

Its **median |deviation| from the outlet's own label is 0.04**. And every
large deviation points the same way, toward 50:

| outlet | category | n | label | EMA | drift |
|---|---|---|---|---|---|
| Bearing Arms | environment | 44 | 80 | 57.62 | **-22.38** |
| City Journal | science | 69 | 80 | 63.28 | -16.72 |
| Financial Express (India) | economy | 189 | 65 | **50.00** | -15.00 |
| Jacobin | environment | 27 | 10 | 22.23 | +12.23 |
| OpIndia | environment | 37 | 90 | 77.78 | -12.22 |

Financial Express sitting at exactly 50.00 across 189 economy articles is the
signature of every one of those rows being an unscored or default row averaged
in as though measured. **The EMA is not measuring outlet lean; it is measuring
how often an outlet's articles failed to be scored.** Feeding it back as a
learned offset would drag every outlet toward the centre, which is the defect
it would be meant to cure.

## 7. What follows

The proposed sequence (derive from our own corpus, keep improving it as
articles arrive, cross-check a sample of ~50 majors against published ratings)
is the right shape. The order has to change, because step 1 as stated is
blocked on the text scorer rather than on data:

1. **Fix what feeds the corpus before mining it.** `text_score` has to be
   stored on every row, not 17%, and the unscored rows have to be excluded
   from any EMA rather than averaged in at 50. Until both hold, every
   aggregate over this data is biased toward the centre by construction.
2. **Raise the text scorer's sensitivity outside American partisan
   vocabulary.** This is the item already blocked in `OPEN-ITEMS.md` on ground
   truth: all 43 lean fixtures are US/Western. It is now the critical path,
   not a nice-to-have.
3. **Then derive offsets**, shrunk toward the label by article count, bounded
   so an outlet cannot be published off its own rung.
4. **Then the cross-check**, on ~50 majors against published ratings. Full
   agreement would mean we are reselling someone else's judgement; the useful
   outcome is small, explainable disagreements.

Until step 2 lands, the honest statement about the roster is that its
**labels** are defensible and its **resolution** does not exist.

---

Reproduce: download the `void-state-snapshot` artifact from the newest
successful `pipeline.yml` run, `gunzip pipeline_state.db.gz`, and query
`bias_scores.rationale` (JSON, occasionally double-encoded) joined to
`articles` and `sources`.
