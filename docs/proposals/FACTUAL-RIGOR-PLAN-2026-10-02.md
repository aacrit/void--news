# Factual rigor: optimization and enhancement plan

**2026-10-02. Builds on the factual-rigor audit of the same date (HEAD `bdd6b651`).** Every claim the plan rests on was re-read in the code before it was used. Hard constraints: $0/month (flash at 20 requests a day, about 13 spent; flash-lite high RPD; no paid API), rule-based first, no publisher prose committed (indexes only), one pipeline run a day of about two hours, no personalization, and every new control is a check that can fail, with a planted-defect fixture, run in `auto-merge-claude.yml` and, where it guards data, in `pipeline.yml` before the data commit. Rule 1 outranks style.

## 0. Where the audit stands

The audit is right on every point that matters. Re-read in the code: `review_bench` keeps a failing card when the cluster has fewer than three articles or the LLM is down (`stage2.py:332-346`); the critique treats an unread card as clean and never drops; `grounding.load_verifier` has no caller outside tests; `verify_production.py` runs no grounded rule; the four `pipeline.yml` gates check no factual content; consensus and divergence points feed `derived_grounding.cluster_text` and are validated by nothing; `claim_consensus` is null on all 1,777 archive rows; `cambodian-genocide.yaml` has Dith Pran dying in 2008 and testifying in 2009, and `history.json` serves it; the three 2026-10-01 brief errors are still in `brief.json`; Weekly `validate_script` grounds only W-01 and W-09; `corrections.apply_all` touches card rows only.

Two refinements. The stub-index false flags (format 2, median 499 characters) are already addressed in structure: 8f writes a `pre-truncation` record for every bench card and export keeps it (`grounding.keep_existing`). No run has exercised it, so what is missing is the gate, not the fix. And `docs/IP-COMPLIANCE.md` is marked historical; the operative prose control is `tests/test_grounding.py`.

## 1. The outcome metric

Rule 1 is a claim about published sentences, so it is measured in sentences. Two numbers, one deterministic and one sampled, plus the record of confirmed errors.

**Coverage** (deterministic, every run). For each product (card headline, card summary, consensus/divergence points, TL;DR, Opinion, On Air, Weekly, History narration), the share of published sentences carrying at least one anchor that an enforced deterministic rule checked against source evidence: a number in E-13 scope, a quotation of four or more words, a multi-word name, a date or interval. Computed by `pipeline/validation/rigor.py` after export, over the committed outputs, with the same sentence splitter the checks use. Also recorded: sentences cut by reason and product, cards shipped fresh against pre-truncation evidence, cards shipped against their stored index, cards shipped with no evidence, critique cards read and unread, regenerations, drops.

**Error rate** (sampled, weekly). Errors per 1,000 published sentences with a 95% Clopper-Pearson interval, from a fixed sample drawn by `scripts/rigor_sample.py --week <iso>`: 200 sentences a week, seeded by the ISO week so the sample is fixed before anyone reads it, stratified by product in proportion to volume. Each sentence is judged against its sources by a Claude Max CLI session (the agent budget, not an API) reading the live article URLs; the verdict goes into `docs/data/rigor-audit.csv` as `week, product, story_id, sentence_index, sentence_sha1, verdict, error_class, correction_id`. No sentence text, no source text. At 200 sentences and zero errors the upper bound is 15 per 1,000; a rolling four weeks (800) brings it to 3.7. That bound is the honest number; a point estimate from zero errors is not.

**Confirmed errors.** Every entry in `corrections.json` and `weekly-corrections.json` is an error that reached production. Counted per surface per month with time to correction, and each entry must name the gate that now catches its class.

**Storage.** `frontend/build-data/rigor.json` per run (counts only) and one row per run in `docs/data/rigor-series.csv`, committed by `pipeline.yml` beside `engine.json`. `tests/test_rigor.py` asserts no string over twelve words, that the per-product counts recompute from the committed outputs, and that the run's series row exists.

**Display.** Internal: `rigor.json` and the series. Public: a `/corrections` page across every surface, and one line on `/sources#methodology` from the audit CSV: "Of N sentences sampled since <date>, M were corrected." No published errors-per-1,000 headline, because a reader takes a zero-error sample as proof of zero errors, and the interval is the truth. **CEO decision 1**: publish the log and the sentence count (recommended), or keep both internal.

**Floors that fail a run**, in `pipeline.yml` before the data commit, as `python tests/test_rigor.py --floors`:

| Floor | Fails when |
|---|---|
| F-1 | Any shipped card, or any shipped consensus or divergence point, carries an enforced E-13, E-14 or E-16 finding against its pre-truncation index |
| F-2 | A fresh card has no `pre-truncation` grounding record |
| F-3 | The brief, Opinion or radio grounding pass did not complete (raised, or was skipped) and the product shipped |
| F-4 | The critique read zero cards while `is_available()` was true (a bug, not a quota) |
| F-5 | A correction in `corrections.json` is unapplied in the export, or names no gate |

Quota exhaustion is not a floor: a checker that cannot run must not drop stories, but it must be counted, and `rigor.json` prints unread cards every run.

## 2. The gaps, prioritized

Effort: S under a day, M two to four days, L more. LLM cost is flash calls per day unless marked lite. "False cuts" is the risk of removing a true sentence.

| # | Gap | Fix | Check that proves it | Effort | LLM | False cuts | Protects |
|---|---|---|---|---|---|---|---|
| 1 | Consensus and divergence points unchecked, then reused as evidence downstream | E-13/E-14/E-16 on each point at 8d.3 against the same `src`; a failing point is dropped, not the card. `cluster_text` reads only points that passed | `test_editorial_standard`: a point with an unsourced number is dropped. `test_brief_grounding`: a brief sentence anchored only in a dropped point is cut | S | 0 | Low: a point goes, the card survives | Card, TL;DR, On Air, Weekly |
| 2 | 71.7% of card sentences have no anchor and rest on a fail-open critique that never drops | Rebuild the critique as a verification pass (section 3) with falsifiable spans; shadow mode for a week, then an unsupported unanchored sentence is cut under a per-card cap, and a card over the cap is dropped | Stubbed model answer: an unsupported sentence is cut, an unreadable verdict cuts nothing, a "supported" whose span is not in the article counts as unread | M | 0 flash; 8 to 12 lite | Medium; shadow mode measures it first | Card, Deep Dive, Paper |
| 3 | Cached cards skip grounded rules; a factual failure is kept when the cluster is thin or the LLM is down | A cached card is checked against its stored `pre-truncation` record via `load_verifier` as `source_index`; a card still carrying an enforced grounded finding after repair never ships. Style-only failures may be kept | Fixture: a cached card whose number is not in its stored index is cut; a headline E-13 failure on a two-article cluster is dropped, not kept | S | 0 | Low | Card, Deep Dive, Paper |
| 4 | No correction path for brief, Opinion, On Air or Deep Dive; no reader notice on daily cards | `corrections.json` entries carry `product` and `gate`. Export applies brief edits to `brief.json`, deepdive edits to members with `source_count` and histogram recomputed. A corrected audio script withdraws the episode until re-rendered. `CorrectionNotice` on `/story/[id]` and `/brief`, and `/corrections` | `test_corrections`: an unapplied entry fails; a corrected sentence still in `brief.json` fails; `source_count` equals the member count. `verify_production` C-01: the served page carries the notice | M | 0 | None | Every surface |
| 5 | Who said what: no speaker check on cards or in the Weekly | E-19: a fourth Bloom holds `(proper name, shingle)` for every source sentence and its predecessor. A named speaker paired with a quote of four or more words must find the pair; a paraphrase ("X said that") is advisory first | Planted Nielsen/Frederiksen fixture: right speaker passes, wrong one fails, unnamed speaker out of scope | M | 0 | Medium on paraphrase, so advisory there; low on quotes | Card, Weekly, On Air |
| 6 | History: narration numbers unchecked, H-10 warn-only, H-01 circular for 71 events, Dith Pran served | Now: cut the Dith Pran quote and add to `test_history_data` a check that no quote is dated after its speaker's death or before birth. H-18: every numeral spoken in a script appears in the event YAML, blocking. Later: ledger extracts for the 71 Hearings | A quote dated 2009 for a figure who died 2008 fails; a script number absent from the YAML fails H-18 | S now, L later | 0 | Low: scripts are written from the YAML | History, History audio |
| 7 | Weekly audio Editor lines ungrounded | W-13: every number and multi-word name in COVER, DATELINE, TOPIC, TURN, EDITORIAL and CLOSE is in the issue; fail means no render | An Editor line carrying a figure the issue lacks fails W-13 | S | 0 | Low | The Argument |
| 8 | The index is stored and never read; the served gate lacks E-13/E-14/E-16 | `scripts/audit_grounding.py` after export in `pipeline.yml`: every `feed.json` card and brief source card through `load_verifier`; enforced findings fail the run (F-1). `verify-production.yml` checks out the repo, so it runs the same rules on the served cards against the committed index | A planted index missing a shipped number fails; a stub-only record reports "cannot confirm" and never fails | S | 0 | None: stubs excluded | Card, Paper |
| 9 | `claim_consensus` null; disagreement is a prompt only | E-20: where two sources attach different numbers to the same context word, write `claim_consensus` with values and outlets; a card stating one value with no range word is advisory for a week, then cut. Deep Dive renders the table | "12 killed" against "15 killed" populates the structure and fails without a range word; "12 killed" against "15 injured" does not | M | 0 | Medium at first; the advisory week sets enforcement | Card, Deep Dive |
| 10 | 146 archive cards still carry a contamination opener on permanent pages | Deterministic archive repair at export: the E-16 sentence is removed, the row marked `auto_corrected` with the date, the notice reads "A sentence from another story was removed" | `verify_production` A-01: no served `/story` carries an E-16 opener | S | 0 | None: a true sentence about the wrong story is not this story's fact | Deep Dive, archive |

**CEO decision 2**: fail closed on the daily brief, Opinion and On Air when their grounding pass cannot run (F-3), so a day can ship with no TL;DR. The Weekly already works this way. Recommended: yes. Rule 1 outranks completeness, and the audio page already handles an absent episode.

**CEO decision 3**: the archive repair of item 10 rewrites 146 permanent pages with a notice. Recommended: yes.

## 3. Optimizations

**Stop treating stub evidence as evidence.** The format-2 false flags came from indexing after step 10. The 8f record fixes the source; the plan adds floor F-2 and the stub exclusion in the audit and otherwise stops re-solving it. A stub carried in by the 36-hour lookback is "cannot confirm", never a failure.

**One grounding module.** Numbers, names, quotes and dates are checked four ways: E-13/E-14 on cards, `derived_grounding` on brief and radio, `weekly_parse.ground_text` and `ground_quotes` on the Weekly, R-14 and W-01 by word overlap. Each has its own normaliser, so "twenty percent" passes in the brief and would fail E-13 on a card. Consolidate extraction and normalisation (spoken numbers, `1.2m`, `two-thirds`, percent and currency units) in `grounding` and keep the products as thin adapters, with a parity test in the style of `test_summary_hygiene_parity`. This is the largest precision gain available; the 48 false-flagged numbers of 2026-10-01 become its regression fixture as synthetic sentences carrying the same forms.

**Spend flash-lite on verification, not style.** The critique spends tokens on L-01, L-03, L-04 and L-07, which deterministic rules cover, and sees 700 characters per article. Since 8d now runs before truncation, send whole bodies within the TPM budget, drop the style rules, and ask one question per numbered sentence: `supported | unsupported | out_of_scope`, with `article_k` and the first five words of the supporting sentence. Code checks that prefix as a shingle in article k, so a "supported" the model cannot point to counts as unread, and an "unsupported" acts only on a sentence with no deterministic anchor. Four or five cards a batch covers 35 candidates and their points in 8 to 12 lite calls and zero flash calls.

**Stop swallowing.** The brief handler that keeps text on exception, the radio fallback that grounds against the union of every card, and the critique's silent "unread" all exist to protect the edition. Under F-3 and F-4 they protect it by counting and failing instead.

**Duplicates to remove.** E-17 is subsumed by the format-3 contexts check inside E-13 once a run confirms it; `check_lifted_quote` and E-14 should share code.

## 4. Enhancements

**Regression corpus of every production error.** `tests/fixtures/rigor_regressions/` holds one synthetic planted fixture per confirmed error (five daily, nine Weekly, three brief, Dith Pran), named by its correction id and gate. `test_rigor_regressions` fails when a correction names no gate, the fixture is missing, or the gate does not fire. "The fix is not complete until a check exists" becomes a test.

**Reader-visible corrections.** `/corrections` across every surface, a notice on the corrected page, the Weekly `Corrections` component generalised rather than duplicated.

**Attribution checker** (E-19) and **disagreement publishing** (E-20) as above. **CEO decision 4**: render `claim_consensus` as a disagreement table on the Deep Dive. Recommended: yes, the one place "publish the disagreement" becomes visible.

**Atomic claims with spans.** Deterministic first: a sentence splits at conjunctions and semicolons into clauses, each carrying its anchors and binding context words, and the index stores hashes of `(anchor, context)` pairs as format 3 already does for numbers. The verification pass reports per clause once the splitter exists. No prose is stored.

**The weekly sampled audit** of section 1, as a Routine that opens a Claude Max CLI session with the sample, writes the CSV and opens a correction for every error. `test_rigor_audit` asserts the CSV holds ids, hashes and verdicts only, every sampled sentence has a verdict within seven days, and every error verdict has a correction id.

## 5. Roadmap

"Parallel" means separable files inside the one live `claude/*` branch, as independent commits, so the one-branch rule holds.

**Phase 0, this week.** WS-H (`data/history`, `tests/test_history_data.py`): cut the Dith Pran quote; death-date check with fixture. WS-A (`standard.py`, `stage2.py`, `tests/test_editorial_standard.py`): points through E-13/E-14/E-16; cached cards through `source_index`; factual failures never kept. WS-G (`pipeline/validation/rigor.py`, `scripts/audit_grounding.py`, `tests/test_rigor.py`, `pipeline.yml`): `rigor.json`, the series row, the post-export audit, floors F-1, F-2, F-5. WS-R (`tests/fixtures/rigor_regressions/`, `corrections.json` schema): the regression corpus with a `gate` field. Acceptance: every fixture fails its gate when planted and passes when not; `pipeline.yml` runs the audit before `git add`; `test_workflow_hygiene` sees the new test in both workflows.

**Phase 1, weeks 2 and 3.** WS-C (`derived_grounding.py`, `daily_brief_generator.py`, `radio_script_generator.py`): F-3 fail closed (decision 2). WS-D (`corrections.py`, `export_static.py`, `frontend/app/corrections/`, `CorrectionNotice.tsx`): corrections for every product, membership recompute, the page and the notice (decision 1), archive E-16 repair (decision 3). WS-W (`weekly_script.py`, `tests/test_weekly_script.py`): W-13. WS-H: H-18 narration numbers. WS-L (`cluster_summarizer.py` critique): the verification pass in shadow mode, counts into `rigor.json`. WS-G: `verify_production` runs E-13/E-14/E-16 and C-01, A-01. Acceptance: the 2026-10-01 brief errors are corrected and the notice is served; a dry run of the verification pass reports its would-cut rate.

**Phase 2, weeks 4 to 6.** WS-A: E-19 (quotes enforced, paraphrase advisory) and E-20 advisory with `claim_consensus` populated. WS-L: verification cuts enabled under the cap, F-4 live. WS-G: grounding consolidation and the parity test; the weekly sampled audit Routine, first interval recorded. WS-D: the Deep Dive disagreement table (decision 4). Acceptance: `rigor-audit.csv` holds four weeks; E-20 enforced only after its advisory week shows a false-cut rate under 5% on reviewed findings.

**Phase 3, the quarter.** WS-H: ledger extracts for the 71 Hearings so H-01 stops being YAML against YAML; **CEO decision 5**: until then, label unverified History quotations "attributed" on the page (recommended) or withdraw them. WS-A: the clause splitter and per-clause verification. WS-G: the methodology line reading from the audit CSV (decision 1).

## 6. What this still will not catch

A paraphrase that inverts a position with no number, name, quote or date in it, when the verification pass is unread or wrong; the pass is probabilistic and fails open by policy. Sources that are wrong together: grounding proves presence in a source, not truth. A quotation that is a Bloom false positive, at 0.1% per four-word quote. Facts true at write time that time falsifies, beyond E-18's regex. Opinion's argumentative sentences, which have no anchors by nature. Numbers under two digits and spelled-out numbers until the consolidated normaliser lands. Disagreement in wording rather than in numbers. Translated sources where the quotation exists only in another language. Errors in the auditor's own judgment, and errors rarer than the sample can see: at 800 sentences, an error rate of one per 1,000 is as likely to show zero as one. Images, captions and Games make no checked factual claims and stay outside the metric.
