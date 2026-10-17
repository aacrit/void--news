# Holistic fix and optimisation plan, 2026-10-02

Written from the six audits of 2026-10-01/02 (`1-editorial`, `2-ux`, `3-pipeline`,
`4-history-weekly-audio`, `5-security`, `6-bias`), `docs/OPEN-ITEMS.md`, and
rev 83 and 84 of `docs/CHANGELOG.md`. Every claim this plan rests on was opened
at the file and line it cites; the ones that did not hold are under "Audit
corrections". Work shipped on 2026-10-01 (the shim fix and lock, the On Air
retry, R-05 and R-14, the 429 backoff, summary-less brief inputs, the Weekly's
`printed_stories` read, floor, `ground_text` and source check, the Issue #26
text corrections and audio withdrawal, the script gate, the empty weekly feed)
is not re-planned.

Each item: problem with evidence, fix, files, the check that makes recurrence
structurally impossible (mandatory for Rule 1 items), effort (S under half a
day, M one to two days, L more), dependency, owner per `docs/AGENT-TEAM.md`.
`void-ciso` is read-only by charter, so it specifies and `bug-fixer` implements.

---

## Summary for the CEO

The product ships daily: 1,061 sources, 20 stories, 78 History episodes, 7
published theses, three podcast feeds, Weekly Vol. I at Issue #27 tonight. Run
#385 took 124 minutes, read full bodies on 69% of direct feeds, and left 63% of
rated articles on their outlet baseline. The repo is 760 MB, 688 MB of it MP3.
Security scores 74 of 100. UX maturity 3.5 of 5.

Three risks, in order:

1. **Rule 1 is enforced on the card and nowhere downstream.** TL;DR, Opinion and
   On Air are rewritten after the card checks and never grounded; five of this
   week's fifteen editorial findings sit there, including a 20 percent cut that
   listeners hear as 30. E-13 cannot see a decimal or what a number is attached to.
2. **Data goes live hours late by design.** No scheduled run has ever been
   followed by its own deploy; the 11:00 cron starts four to seven hours late;
   yesterday's run finished 19:22 and went live by hand at 19:49.
3. **Withdrawn audio is still served.** Issue #26's MP3 answers by URL, and two
   published theses serve audio that contradicts their corrected scripts.

Order: P0 in two branches today and tomorrow (deploy and audio, then Weekly
#26 and the merge-gate hole), P1 in five branches this week, then P2.

---

## P0, today and tomorrow

**P0-1. The deploy never follows a scheduled run.** `deploy-cloudflare.yml`
waits on `workflow_run` from "News Pipeline"; the 10-01 run finished 19:22 and
nothing deployed until a manual dispatch at 19:49; the file's own comments
record drops on 08-10, 08-14 and 08-21 (audit 3 item 1). Fix: `pipeline.yml`
ends with `gh workflow run deploy-cloudflare.yml` (needs `actions: write`),
after the data commit and the engine floor; keep `workflow_run`, retire the
15:00 and 17:00 backstops after two scheduled runs deploy this way. Files:
`.github/workflows/pipeline.yml`, `deploy-cloudflare.yml`. Check:
`freshness-check.yml` asserts the LIVE `feed.json.builtAt` is within 20 minutes
of the pipeline's commit. Effort S. Owner: bug-fixer.

**P0-2. Crons on :00 and :30 start hours late.** Runs #380 to #385 began 14:55
to 18:32 against an 11:00 cron (audit 3 item 2, confirmed from run history).
Fix: move every schedule off the shared minutes (pipeline `7 10 * * *`, weekly
`7 18 * * 0`, verify `37 15`/`37 17`, freshness `19 15`). Files: the six
workflows with a `cron:`. Check: `tests/test_docs_facts.py` asserts no cron on
minute 0 or 30. Effort S. Owner: bug-fixer. Ships with P0-1.

**P0-3. Issue #26's withdrawn audio is served by URL.** `latest.mp3`,
`2026-09-21-am.mp3` and `latest.chapters.json` ("Greenland's Arctic Calculus")
under `frontend/public/audio/weekly-world/` answer 206 and speak the passages
rev 84 cut (audit 4 item 2). Fix: delete them and the unreferenced 09-19/09-20
pilots. Check: `tests/test_weekly_audio_served.py` gains the inverse rule, no
file under `weekly-world/` that no issue row names; `verify_production.py`
asserts the old URL is 404 live. Effort S. Owner: audio-engineer.

**P0-4. Two theses serve audio contradicting their scripts.** `haitian-revolution`
(rendered 09-19, script corrected 09-25 17:03) still says "thirty thousand men"
and voices Toussaint's "tree of liberty" as his own words; `scramble-for-africa`
(rendered 09-20, script 09-25 16:50) voices a paraphrase of von Trotha as
quotation (audit 4 item 1). `tests/test_history_audio.py:254` skips its
newer-script check on a shallow clone, which is every CI run. Fix: re-render
both; the manifest stores the script's SHA-256 at render time and the test
compares content (all 78 scripts share a 09-25 12:51 commit, so dates would
flag everything). Files: `pipeline/history/*_producer.py`, `history-audio.json`,
`tests/test_history_audio.py`. Check: the hash comparison, on any clone.
Effort M. Owner: audio-engineer.

**P0-5. Weekly #26 misattributes Frederiksen's line to Nielsen and alters two
quotes.** Rasmussen's paraphrased "binding agreement" is set as a direct quote,
Trump's quote runs past the printed one, "EVER have a base" is in no printed
story, and Nielsen is credited with Frederiksen's sentence (audit 4 item 3,
checked against `build-data/archive.json`; still in `weekly-issues.json`).
Fix: edit the stored issue and `weekly.json`: restore the attribution, demote
two quotations to paraphrase, cut the invented clause; add a third correction.
Check: W-T22 in `tests/test_weekly.py`, every quotation in a committed issue is
verbatim in the archive's printed stories. Effort S. Owner: bug-fixer; CEO
signs the three edits.

**P0-6. Cloudflare rate-limits first-party assets.** One calm load of `/` got
429 on `/_next/static` chunks and twice fell to Next's bare error page;
`/sources` fired 406 logo requests and 284 got 429 (audit 2 F1, F2). The rule
is in the dashboard, not the repo. Fix: exempt `/_next/static/*`, `/logos/*`,
`/brand/*`, `/audio/*`; record the rule in `docs/DEPLOYMENT.md`. Check:
`verify_production.py` loads `/` and `/sources` and asserts zero 429 on
first-party assets. Effort S. Owner: void-ciso specifies, CEO applies.

**P0-7. A `claude/*` push can rewrite its own merge gate.** `auto-merge-claude.yml`
runs from the pushed commit with `contents: write`, so a branch can delete the
tests and still merge; `${{ github.ref_name }}` is interpolated into shell at
lines 365-366; no `.github/CODEOWNERS` (audit 5 H3, confirmed). Fix: a first
job diffs against `origin/main` and refuses when `.github/**` changed; pass
the ref through `env:` and quote it; add CODEOWNERS; required status checks on
`main`. Check: `test_docs_facts.py` asserts the refusal step precedes the
merge. Effort S. Owner: void-ciso, bug-fixer; this one change to `.github/`
is hand-merged.

**P0-8. Four thesis exhibit images are broken.** Hand-typed Commons hash paths
at `scramble-for-africa/ledger.yaml:1181,1193,1205` and
`cambodian-genocide/ledger.yaml:1317` (audit 4 item 5; MD5 recomputed: 5/5c,
d/de, 5/52, 9/9c). Fix: the ledger stores the Commons file page; `export_thesis.py`
derives the upload URL from the filename's MD5. Check: T-21 in
`test_history_thesis.py` recomputes every image path. Effort S. Owner:
media-archaeologist.

---

## P1, this week

### Rule 1: the derived products

**P1-1. TL;DR, Opinion and On Air are never grounded.** Audit 1 items 1, 2, 4, 5:
a stacked 20 percent, a £1,000 figure no source carries, "two days later"
against "a day earlier", "purged" for "no longer work here".
`daily_brief_generator.py` runs no E-13/E-14 on its output; `radio_script_generator.py`
has R-14 for attributed claims only. Fix: one deterministic per-paragraph pass
mapped to the paragraph's cluster (the shape OPEN-ITEMS specifies): every
number, quotation, proper name and date must appear in THAT cluster's text.
Repair by cutting the sentence, never regenerating (flash is capped at 20 a
day). Files: new `pipeline/editorial/derived_grounding.py`, the two generators.
Check: `tests/test_brief_grounding.py` with a planted cross-story number, an
altered quote and a reworded kicker, each cut. Effort L. Dependency: P1-4.
Owner: nlp-engineer.

**P1-2. E-13 cannot see a decimal and checks existence, not attachment.**
`_NUM_RE = r"\b\d[\d,]*\b"` (`standard.py:643`) splits "8.3%" into two ignored
digits; the Iraq card's 4,419 passed because the number exists in a source
about a different war (audit 3 item 3, audit 1 item 3). Fix: match decimals
with their unit; require the number and its clause's head noun (spaCy) to
co-occur in one source sentence; the index stores numbers with context, not
bare. Files: `standard.py`, `grounding.py`. Check: fixtures for "8.3%", "47.6%
to 44.7%", and 4,419 on the wrong noun. Effort M. Owner: nlp-engineer.

**P1-3. E-14 passes a punctuation-altered quotation.** The Hegseth card dropped
an ellipsis; shingles strip punctuation (audit 1 item 6). Fix: words for
recall, then a punctuation-preserving 4-gram filter for the exact string, with
ellipsis as the one allowed cut mark. Check: fixture with a dropped ellipsis
fails E-14. Effort S. Owner: nlp-engineer.

**P1-4. The grounding index is built after step 10 truncates bodies.**
`main.py:4234` truncates to 300 characters; `export_static.py:398` writes the
record afterwards, so the median indexed article is 496 characters and a
post-run check false-flags 48 numbers and 6 quotes (audit 1 systemic a). Fix:
write the record in step 8f from full bodies. Check: `test_grounding.py`
asserts shingle count against the cluster's full-body length. Effort S. Owner:
bug-fixer.

**P1-5. Clusters carry unrelated stories into the card.** The Putin card holds
a Kanye West concert; the pensions card ends with RAF Fairford and rejoin-EU;
the summarizer writes "Separately," (audit 1 item 8). Fix: Stage 2 coherence
cuts a member whose entities share nothing with the modal bag instead of
abstaining; the prompt forbids topic-shift adverbs; E-16 fails a paragraph that
opens with one. Files: `stage2.py`, `cluster_summarizer.py`, `standard.py`.
Check: E-16 fixture; `test_same_event_merge.py` gains the Putin-plus-concert
case. Effort M. Owner: nlp-engineer, feed-intelligence.

**P1-6. Kill-list words in the rule-based fallback.** `main.py:732` and `:745`
carry two banned adverbs and an em dash, served on archived Deep Dives
(audit 1 item 13). Fix: rewrite the strings. Check: `test_prompt_grounding.py`
runs `find_prohibited` over every string literal in `main.py` and `briefing/`.
Effort S. Owner: bug-fixer.

### Security

**P1-7. Ship-board votes and replies are keyed on a client fingerprint.**
`worker/src/index.ts:167-176` inserts a vote on a client string with no per-IP
cap and before the parent exists; replies at `:217-223` limit on the same
string, so one client can exhaust the global caps (audit 5 H1, H2). Fix: key on
server `ipHash`, `UNIQUE(request_id, ip_hash)`, 30 votes per IP per hour, parent
checked first, per-IP reply cap, Cloudflare rate rule on `/api/*`. Files:
`index.ts`, `schema.sql`, a D1 migration. Check: `worker/test/` (vitest): a 31st
vote and a cross-fingerprint flood both refused. Effort M. Dependency: hand
deploy. Owner: void-ciso, bug-fixer.

**P1-8. The privacy page misdescribes what is stored.** It says "a coarse
one-way hash" (`privacy/page.tsx:47`); `FeedbackForm.tsx:104` sends the full
user agent; `IP_SALT` is the dev string at `wrangler.toml:18`; the 500 handler
returns `String(e)` (audit 5 M3). Fix: `wrangler secret put IP_SALT` and drop
the literal; send a device class, not the UA; drop `detail`; name the IP hash
and retention on the page. Check: `copy-facts.test.mjs` asserts the privacy
page names every field `schema.sql` writes. Effort S. Owner: void-ciso,
bug-fixer, frontend-fixer.

**P1-9. Prompt injection has no boundary.** Scraped bodies enter prompts with
no delimiter or data-only clause in `cluster_summarizer.py`, `daily_brief_generator.py`,
`stage2.py` (audit 5 M4, confirmed). Fix: wrap each source and add one
sentence to the grounding line. Check: `test_prompt_grounding.py` asserts it on
every prompt. Effort S. Owner: nlp-engineer.

### Bias-display honesty

**P1-10. "Blend" survives in two strings and `/press` contradicts the engine.**
`film/data.ts:81`, `SourcesClient.tsx:59`, and `press/page.tsx:232-236` ("on a
full feature, the article's own words lead") against a 10-point cap and a
1.43-point mean (audit 1 items 10, 11; audit 6 item 3). Fix: quote `delta_max`;
`/press` reads `engine.json` as `/sources` does. Check: `copy-facts.test.mjs`
bans "blend"; `test_engine_health.py` covers `/press`. Effort S. Owner:
frontend-fixer.

**P1-11. The card and the Bench count different things.** The card votes per
article (`bias_aggregation.py:76`, `main.py:900`); the Deep Dive dedups by
source name (`DeepDive.tsx:319-323`); three of twenty stories print different
words while `Bench.tsx:299` says they cannot (audit 6 item 1). Fix, after
decision 3: one histogram computed once in the pipeline, read by both. Check:
`labels.test.mjs` and `test_bias_bins.py` assert card word equals Bench word on
every exported story. Effort M. Owner: nlp-engineer, frontend-fixer.

**P1-12. The About demos print "0 measured" beside a lean word.** `demoSigil.ts:11`
passes no wing counts (audit 6 item 4). Fix: real counts. Check:
`labels.test.mjs` asserts a nonzero count under every printed word. Effort S.
Owner: frontend-fixer.

**P1-13. "Every score shows its work" is untrue in the Deep Dive.**
`DeepDive.tsx:281` builds `lensData`; nothing renders it (audit 6 item 5). Fix:
the Bench mark card prints outlet baseline, text shift, and "placed from
outlet only". Check: headless `bench-mark-shows-work`. Effort M. Owner:
frontend-builder.

### UX

**P1-14. A first-time visitor is never told what Void is.** "Bias" first appears
8,581 characters in; the legend hides behind a 14 px icon; the tour waits 120 s
(`UnifiedOnboarding.tsx:29`) or three clicks (audit 2 F6). Fix: one sentence
under the dateline on first visit, a legend link, the tour offered once on
arrival. Check: headless `first-visit-explainer` at 375 and 1440. Effort S.
Owner: frontend-builder.

**P1-15. Audio cannot be paused on History pages.** `MobileNav.tsx:56,71` hides
`FloatingPlayer` on `/history*` unless History audio plays (audit 2 F5, WCAG
1.4.2). Fix: the player mounts wherever `nowPlaying` is set; the History skin
restyles it. Check: headless `audio-controllable-everywhere`. Effort S. Owner:
frontend-fixer.

**P1-16. `/audio` and `/weekly` hide the withdrawal.** `audio/page.tsx:143` says
"No issue has been recorded yet"; `/weekly` mentions it only in Corrections at
the foot (audit 2 F3, F4). Fix: a withdrawn state read from the corrections
file, one line in each place; hide the feed link while it holds no items.
Check: `test_podcast_feed.py` and `onair-tells-the-truth` extended. Effort S.
Owner: frontend-fixer.

**P1-17. Logos fail without a fallback in the roster columns.** 582 of 1,610
images broke on one load; the right-hand columns read as empty (audit 2 F2).
The picker has a letter fallback (`SourcesClient.tsx:652-667`); the columns do
not. Fix: the fallback on every mark, `loading="lazy"`, one sprite for the 922
PNGs. Check: headless `sources-no-empty-marks` under throttling. Effort M.
Dependency: P0-6. Owner: frontend-fixer.

### Weekly generator

**P1-18. Tech and sports filters match a taxonomy that does not exist; length
is enforced before the cut.** `weekly_digest_generator.py:1003` and `:1145` test
capitalised labels against lowercase categories (`auto_categorize.py:6`);
`ESSAY_SPECS` is enforced before `ground_text` and the source check, never
after; `drop_terms` discards a piece over one word; the band is fixed at 18-22
(`weekly_script.py:57`) while material shrinks (audit 4 root causes). Fix:
case-insensitive match plus a real tech classifier; the full sourced corpus to
every writer; length sized to sourced words and re-checked after the cut; cut
the offending sentence, not the piece; band from sourced words (decision 6).
Check: WG-12..WG-15 with planted inputs. Effort L. Owner: nlp-engineer.

---

## P2, this month

**P2-1. Pipeline runtime.** 8c re-ranks 15,566 clusters in 637 s, ~11,800 of
them orphans that cannot reach the pool; Kokoro runs 2 workers
(`tts_engines.py:152`) on 4 cores (audit 3). Fix: rank only pool-eligible
clusters; 4 workers. Check: `engine.json` carries phase timings;
`test_engine_health.py` fails a run over 110 minutes. Effort M. Owner:
perf-optimizer.

**P2-2. MP3s out of git.** 688 MB of the 743 MB pack is 67 MP3 blobs, growing
11-22 MB a day (audit 3). Fix: release assets or R2, the manifest carrying URL
and SHA-256, the deploy copying them in. Check: the sidecar and weekly tests
read the manifest hash against the served file. Effort L. Dependency: CEO call
on R2 ($0 under 10 GB). Owner: perf-optimizer.

**P2-3. State DB and phrase_counts growth.** +9 MB a day (477 MB); 2.0 M phrase
rows in six days, pruning first due around 10-03, halt at 8 M (audit 3). Fix:
watch the 10-03 prune; lower the spread threshold if the daily gain stays over
150 k; retention sweep on `articles` past the archive window. Check:
`test_phrase_counts_daily.py` caps rows per day from the last counter. Effort
S then M. Owner: db-reviewer, bug-fixer.

**P2-4. Page weight.** JS 1.19-1.43 MB decoded, CSS 417-452 KB, up to eight
unused CSS preloads, `/history` serving 5.1 MB of images at 375 against 3.7 MB
at 1440 (audit 2 F7). Fix: route-scope CSS, `sizes` on History images, drop
unused preloads. Check: `verify-headless.mjs` transfer budgets per route (home
under 600 KB, History images under 2.5 MB at 375). Effort M. Owner:
perf-optimizer.

**P2-5. Dependencies.** Two critical and six high npm findings, `requests~=2.32.3`,
`Pillow~=11.0.0`, `playwright~=1.49.0` rendering untrusted pages beside
`GEMINI_API_KEY`, no `worker/` lockfile, actions on tags, no `dependabot.yml`
(audit 5 M1, M2). Fix: bump, lockfile, weekly Dependabot, SHA pins, scrape in a
no-secrets job handing off by artifact. Check: `npm audit --omit=dev` and
`pip-audit` in `auto-merge-claude.yml`, failing on high. Effort M. Owner:
void-ciso, bug-fixer.

**P2-6. Quarantined sources.** 260 of 1,061 (24.5%), 250 on one day, with
repeated 429s from one publisher group and one SSL failure (audit 3 item 4).
Fix: a review that retries each held feed from a different hour and reports
per cause. Check: `test_apply_feeds.py` asserts every quarantine carries its
cause. Effort M. Owner: source-curator.

**P2-7. The SessionStart hook.** `per_page=8` (`session-start.sh:62`) misses the
pipeline; a newer skipped run masks an older failure; 121 KB of JSON as one
argv; the env step fails on PyYAML and spaCy (audit 3 item 6). Fix: one call
per workflow, JSON on stdin, pin PyYAML. Check: a fixture with a masked
failure must print "NOT GREEN". Effort S. Owner: agent-architect.

**P2-8. Gate inventory drift.** `test_insecure_origins.py` and
`test_lean_suite_discriminates.py` run in no workflow; `weekly-digest.yml` and
`refresh-brief.yml` push to main untested; `db-cleanup.yml` runs daily against
the dead Supabase (audit 3 item 5, all confirmed). Fix: an inventory test
failing on any test file no workflow runs; the pushing workflows run the four
pre-commit gates; unschedule `db-cleanup.yml`. Effort S. Owner: bug-fixer.

**P2-9. History over-ceiling and stale claims.** Four episodes run over 15:00
(Ottoman 15.26, Peloponnesian 15.21, Srebrenica 15.19, Sykes-Picot 15.18, from
the manifest); Congo "seventy percent ... today", Apollo "has not resumed",
Great Leap "to this day", Ottoman "thirty to forty five million Kurds" are
time-bound (audit 4 items 6, 7). Fix: re-cut and re-render four; date or cut
four claims; `episode_report.py` derives the list from the manifest. Check:
H-07 fails over 15:00 after the re-cuts; `test_history_copy.py` gains a
time-bound phrase list. Effort L. Owner: narrative-engineer, audio-engineer.

**P2-10. Publisher prose in the Deep Dive.** 784 per-article summaries, 111 over
60 words, longest 174 (audit 5 M5, recounted). Fix: 300-character cap in
`export_static.py`. Check: `test_grounding.py` fails on a longer one. Effort S.
Owner: bug-fixer.

**P2-11. History credits and hotlinks.** 40 credits carry scraped junk, one
source title an em dash, 152 images hotlink Commons and draw 429s (audit 4
item 8). Fix: a credit normaliser; self-host under `public/history/` with
licence rows. Check: `test_history_copy.py`, `test_image_license.py`. Effort M.
Owner: media-archaeologist.

**P2-12. An LLM meter.** Flash use against the 20-a-day cap is unmeasurable
(audit 3 item 9). Fix: `gemini_client.py` counts calls per model into
`engine.json`. Check: `test_engine_health.py` fails over 18 flash calls. Effort
S. Owner: perf-optimizer.

---

## CEO decisions required

1. **State media in the lean wings.** RT and Global Times are `far-right`, Tehran
   Times `far-left`, TASS and Xinhua `center` in `political_lean_baseline`; state
   outlets cast 12 wing votes on the top 20 (audit 6 item 6). (a) Leave as
   rated. (b) A `state` rung outside the ladder, its own mark, excluded from
   the shape word. (c) `unrated`, leaving the aggregate. Recommend (b): a
   government's line is not a position on a domestic axis, and (c) hides them.
2. **Card counts and format.** (a) The word alone. (b) The word with its count,
   "Leans right · 15 of 22 outlets right of centre". (c) An L/C/R share like
   Ground News. Recommend (b), and rename "N measured" to "N placed", since 36%
   of placements come from the outlet alone.
3. **Article versus outlet voting.** (a) Outlets everywhere. (b) Articles
   everywhere. Recommend (a): ten RT articles are one view, and the Bench
   already draws it so. About 15% of card words move.
4. **The share card's confidence gate.** `ogCard.tsx:70` still gates on
   `leanLabelState`, a third rule. (a) Align to `leanShape`. (b) Retire the gate.
   Recommend (a): the share card must never say what the page does not.
5. **Tech and sports in the Weekly.** The filters have never matched a cluster
   (P1-18). (a) Fix the classifier and keep both. (b) Drop them until each has
   a sourced corpus. Recommend (b) for Issue #28, (a) once gated.
6. **Audio band versus sourced length.** The 18-22 band refused a 17.6 minute
   corrected script. (a) Keep the band, pad from sources. (b) The band floats
   with sourced words, floor 14 minutes. Recommend (b): padding is where the
   unsourced sentences came from.
7. **Games un-hiding.** Hidden by decision only. (a) Un-hide with refreshed
   banks. (b) Keep hidden this month. Recommend (b) until P0 and P1 are green.
8. **The pronoun scrubber (Block 5a).** It rewrote "all of us" to "all of them"
   inside a Cruz quotation. (a) Exempt quoted spans. (b) Retire it and let
   E-03 cut the sentence. Recommend (b): a cut is silence; a rewritten quote is
   a factual error.

---

## Sequencing

One branch at a time, merged and deleted before the next opens. No branch adds
a flash call: every new grounding pass is deterministic or flash-lite.

| # | Branch | Items | Gates that go green |
|---|---|---|---|
| 1 | `claude/deploy-and-withdrawn-audio` (today) | P0-1, P0-2, P0-3, P0-4, P0-8 | live freshness, no orphan audio, script hash, T-21 |
| 2 | `claude/weekly-26-and-merge-gate` (tomorrow; P0-6 in the dashboard in parallel) | P0-5, P0-7 | W-T22, refusal step, zero 429 on assets |
| 3 | `claude/grounding-derived` | P1-4, P1-2, P1-3, P1-1, P1-6 | test_brief_grounding, E-13 decimals and attachment, E-14 punctuation, index ratio |
| 4 | `claude/worker-and-privacy` (Worker deployed by hand after) | P1-7, P1-8, P1-9 | worker vitest, privacy copy, prompt clause |
| 5 | `claude/display-honesty` (after decisions 1-4) | P1-10 to P1-13 | blend ban, card equals Bench, demo counts, mark shows work |
| 6 | `claude/first-visit-and-player` | P1-14 to P1-17 | four headless scenarios |
| 7 | `claude/weekly-generator` (before Sunday 10-11, after decisions 5-6) | P1-18, P1-5 | WG-12..15, E-16 |
| 8 | `claude/runtime-and-durability` | P2-1, P2-3, P2-7, P2-8, P2-10, P2-12 | runtime ceiling, inventory, summary cap, flash meter |
| 9 | `claude/weight-deps-media`, then P2-2, P2-6 and P2-9 as their own branches | P2-4, P2-5, P2-11 | transfer budgets, audit gates |

---

## Expected gains

| Measure | Now | Target |
|---|---|---|
| Data live after the pipeline commits | 30 min to 6 h, often by hand | under 10 min, every scheduled run |
| Pipeline start after cron | 4 to 7.5 h late | under 30 min |
| Pipeline runtime | 124 min (#385) | under 100 min |
| Repo growth | 11-22 MB a day | under 1 MB a day once audio leaves git |
| Home transfer at 375 | ~280 KB compressed, 1.2 MB JS decoded | under 600 KB; History images under 2.5 MB |
| Security score (audit 5 scale) | 74 | 88 after P0-7, P1-7, P1-8, P2-5 |
| Rule 1 error classes with no gate | 6 (derived products, decimals, attachment, punctuation, truncated index, contamination) | 0, each with a planted-defect fixture |
| Withdrawn or contradicting audio served | 3 files | 0, gated |
| Card word equals Bench word | 17 of 20 | 20 of 20, asserted |
| Flash calls per day | unmeasured | metered, under 18 |

---

## Audit corrections

- **Audit 4 item 9** (R-05 on quoted "welcome back", the 211-word retry) was
  fixed in rev 83; the 10-01 rundown passed first time with three voices. Dropped.
- **Audit 3 item 1, mechanism.** It attributes the missing deploy to GitHub
  suppressing `workflow_run` from GITHUB_TOKEN-originated runs; a scheduled run
  is started by the scheduler, so the mechanism is doubtful. The record stands:
  the 10-01 run finished 19:22 and nothing deployed until a manual dispatch at
  19:49. The fix works either way.
- **Audit 4 item 1, OPEN-ITEMS.** OPEN-ITEMS names `great-leap-forward` and
  `gutenberg-printing-press` as unrendered; both rendered 2026-09-20 18:52,
  after their corrections. The contradicting pair is `haitian-revolution` and
  `scramble-for-africa`. All 78 scripts share a 09-25 12:51 commit, so a date
  comparison would flag all 78; P0-4 compares a content hash.
- **Audit 4 item 6** is confirmed from `durationSeconds`: Ottoman 15.26,
  Peloponnesian 15.21, Srebrenica 15.19, Sykes-Picot 15.18. The OPEN-ITEMS list
  (Congo, Rise of Islam, Russian Revolution, Indian Independence) is stale.
- **Audit 5 M5** counts 846 summaries; the current tree holds 784. The 111 over
  60 words and the 174 maximum hold.
- **Audit 2 F2** says no fallback letter; one exists in the picker
  (`SourcesClient.tsx:652-667`). The roster columns lack it. Narrower fix.
- **Audit 1 items 10, 11 and audit 6 item 3** are the same three strings: P1-10.
- **Audit 4 item 3** was recorded in OPEN-ITEMS as uncheckable; the audit
  checked it against `archive.json`, so it is a confirmed error and is P0-5.
- **Issue #27** regenerates tonight at about 19:35 UTC through
  `weekly_source_check.py`; audit 4's findings against the held-off draft are
  not re-listed.
- Everything else cited was opened and holds: `_NUM_RE` at `standard.py:643`,
  the four Commons MD5 prefixes, `IP_SALT` at `wrangler.toml:18`, `ref_name` at
  `auto-merge-claude.yml:365-366`, no CODEOWNERS or dependabot file, the two
  unscheduled tests, the untested pushing workflows, Kokoro workers default 2,
  the article-vote histogram and the Bench's source-name dedup, and the
  state-media baselines.
