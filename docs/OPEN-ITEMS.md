# Open Items

What is unfinished, what to watch on the next run, and what was deliberately
left alone. Moved out of `CLAUDE.md` on 2026-09-20 so it is read when it is
needed rather than at the start of every session.

`CLAUDE.md` keeps a one-line index of these; the reasoning lives here.
When an item is discharged, delete it from this file and note it in
`docs/CHANGELOG.md` — a stale open item costs more than a missing one,
because it sends the next session chasing a fixed bug.

---

## Blocked on a CEO decision

**Block 5a — the pronoun scrubber rewrites quoted speech.** It converts
we/our/us/my and has no rule for "I", so it leaves a sentence in two voices.
On the live 09-09 feed it turned Ted Cruz's "a traumatic experience for all of
us" into "for all of them" — a real person's words, altered, in production.
`E-07` and `E-08` ship ADVISORY pending this call. Proposal:
`docs/proposals/EDITORIAL-VOICE-2026-09.md`.

**The lean gate: the dilution is FIXED 2026-09-21, the thresholds still want a
read on a post-fix feed.** `leanShareTilt` now divides by the wing coverage
(left + right) rather than by every analyzed article, with a five-wing floor,
and `LABEL_MIN_SHARE_TILT` was re-derived from 0.20 to 0.33 for the new
denominator. Measured against the 2026-09-20 feed that moves 2 of 35 cards,
both Balanced to a direction, both real (12 left vs 5 right across 72 sources;
0 left vs 6 right across 24). The old denominator was failing in BOTH
directions at once: it diluted a real 14:5 split to 0.153, and it also cleared
0.20 on two left articles out of nine. **Label coverage re-read on the post-fix export (run #375), and the binding
gate is not the one this note assumed.** Of 35 clusters: 20 read "Not
measured", 7 Balanced, 5 a direction, 3 Contested. On the front page's twenty:
9 Not measured, 4 Balanced, 4 a direction, 3 Contested. So informative labels
went from 2 of 35 to 8 of 35 with the denominator fix, but "Not measured"
barely moved (18 to 20).

Which gate binds, across the 20 failures:

| binding gate | clusters |
|---|---|
| `aggregate_confidence < 0.5` | **14** |
| `lean_measured_count < 10` | 2 |
| both confidence and measured | 2 |
| sources and measured | 2 |

**`LABEL_MIN_CONFIDENCE` is the gate, and it is not a small-sample problem.**
The suppressed clusters include the best-covered stories in the feed: 54
sources / 53 measured articles at confidence 0.43; 46 / 52 at 0.42; 37 / 32 at
0.46; 34 / 42 at 0.47; 25 / 28 at 0.47. Thin evidence is not what silenced
them.

The reason is the shape of the metric: `aggregate_confidence` across all 35
clusters runs **min 0.40, median 0.51, max 0.71**. The threshold sits within a
hundredth of the median, so it suppresses about half the feed by construction,
and two clusters fail it at 0.499. Either the metric is compressed (0.40-0.71
is a narrow band for something documented as 0-1) or the threshold was chosen
against a different distribution.

**Nothing was changed.** Moving a threshold that sits on the median of its own
metric is exactly the decision this file already says needs a CEO call rather
than a tweak, and the honest fix may be to the metric rather than the cut
point. The numbers above are what that decision needs.

**The original report, for the record.** On 09-09 it emitted ZERO
directional labels: 12 of 20 cards read "Flat". Suppressors, in order of how
often they fired: `margin < 8` (8 cards), `confidence < 0.5` (6),
`measured < 10` (3). The mechanism worth understanding before anyone touches a
threshold: `leanShareTilt` divides by L+C+R, so a story carried 14 left to 5
right lands at 0.153 against a 0.20 threshold purely because 40 neutral wire
articles dilute it, while a nearly identical 16:6 story passes.

The page also shows "Flat" (we could not measure) and "Center" (we measured,
it is balanced) as if a reader could tell them apart. This is the product's
differentiator going silent, and loosening it unilaterally changes what Void
claims about its own confidence. It needs a decision, not a tweak.

---

## Known defects, not yet fixed

### Bias centring: DIAGNOSED AND ANSWERED 2026-09-21. Not a calibration problem.

Kept because the wrong hypothesis was written down here first and acting on it
would have made things worse.

**What this file used to say:** that `pipeline/main.py:2469`,
`source_map.get(source_slug, {"political_lean_baseline": "center"})`, was
silently anchoring articles to centre on a slug miss, and that the outlet
baselines or the article-level analyzer might need recalibrating.

**Refuted, measured on the 2026-09-20 export (737 rows, 35 clusters):**

- **Zero** source names in the export failed to match `data/sources.json`. A
  mass slug miss would have shown up here and did not.
- On the 142 rows that were genuinely measured, the baseline ladder comes
  through monotonically: far-left 30.0, left 35.0, centre-left 46.2, centre
  50.0, centre-right 52.5, right 57.9, far-right 61.0. The anchor is reaching
  the score.
- Those 142 rows have stdev **21.2** across the full 10..97 range, with only
  10.6% at exactly 50. That is a working measurement, not a collapse.
- The "80% of sources read as centre" figure was **540 rows that were never
  scored at all** (73.3% carrying the whole default tuple, 610 at lean exactly
  50), which is the step 6b overwrite, fixed in `1484db4`.

**So neither the outlet baselines nor the article-level analyzer were changed**
(CEO, 2026-09-21). The article-level score is the differentiator and it is
working on every row that reached it. What changed is the plumbing that let
unscored rows read as measured centrism:

- `lean_unscored` is now **exported**. It existed since the analyzer was
  written and already excluded a row from the cluster aggregate, but it stopped
  at the database, so the page kept plotting the article's pin at 50. Carried
  on the live path (`export_static.py`) and the archive path
  (`archive/print_archive.py`), withheld by `DeepDiveSpectrum`, `fetchSourceLeans`
  and `archiveMembersToSpectrumSources`.
- A default-tuple row is stamped unscored at export time, unconditionally.
- `DEFAULT_TUPLE_MAX_SHARE` 0.5 to 0.10, plus a per-axis cap, asserted in CI
  against the committed export rather than blocking the daily run.

**What is still open, and it is one number:** the per-axis caps
(`PER_AXIS_MAX_SHARE`) were set from the damaged export plus judgement, not
from a healthy run. Read the `bias per-axis defaults:` block in the first
post-fix run log and tighten them to fit. `sensationalism` at 86.4% on the old
export is the one to watch: its cap is 60% and a real corpus may well sit far
below that, in which case 60% is too loose to catch anything.

**Two live episodes serve audio that contradicts their own script.**
`great-leap-forward` presents a secondhand Mao remark, and
`gutenberg-printing-press` an attributed line from a Dominican friar, as
verbatim speech. Both scripts were corrected for H-11 and neither was
re-rendered. `tests/test_history_audio.py` now fails on exactly this and stays
red until both are re-rendered. No script work needed; the fix is a render.

**Live History episodes that run over the 15 minute format ceiling.** Congo
Free State 15.46, Rise of Islam 15.43, Russian Revolution 15.37, Indian
Independence 15.36. All sit under the audio gate's 15.5, so they shipped and
still serve. Peloponnesian War renders at about 15.2 and joins this list when
it publishes.

(An earlier version of this entry named Peloponnesian War instead of Russian
Revolution. Peloponnesian War's 15.2 came from a render log, not the manifest:
that run was rejected at publish over a different episode, so it never went
live. Read the manifest for what is serving, not a render log for what was
made.)

This is not a regression. The runtime estimator modelled non-speech time as a
flat 1.1 minutes, so it could not see them; it now spends silence per segment
(2026-09-20) and H-07 warns on each. The warning is the first honest report of
a condition that was already live.

Each is a re-cut of roughly 100-200 words followed by a re-render, in the
manner of `september-11-attacks`: drop whole lines that repeat a fact the
script tells better elsewhere, never trim clauses, and protect the cold open,
the closing turn, every perspective's strongest fact and witness, and the
close. Left alone for now because they are live and serving, and four re-cuts
is its own piece of work rather than a footnote to another one.

**The Sigil disagrees with its own caption.** It paints a direction, and
sometimes consensus-green, on cards whose caption reads "Flat".

**Mobile first paint shows the desktop card variant**, then swaps after
hydration. Not a content bug: the 20 cards, their text and their canonical
anchors are all in the served HTML, no rule hides them under 767px, and a
crawler or a JS-off reader gets the full feed. It is a one-frame layout flash.
`HomeContent` must seed `isMobile=false` to match SSR (reading `data-viewport`
synchronously caused React #418 on every iPhone-width route), so the fix is
rendering both variants and choosing in CSS — not moving the check earlier.

**`_coherence_factor` returns 1.0 for a single-token topic bag**, so the
ranker's only incoherence discount is a no-op on exactly the clusters it was
written for.

**`editorial_importance` is applied twice in ranking.** Added additively in
`importance_ranker.py:1382-1388` (±6.7 points around the ei pivot) and
multiplied again in `feed_ranker.py:350-354` (±3%/point, clamped
[0.88, 1.12]), so a high-ei story gets both. Documented, not yet collapsed.

**Revolt serves MOCK data and cannot be un-hidden.** `revolt/data.ts` falls
back to `MOCK_EVENTS` when the browser Supabase client has no credentials,
which is always true in the Cloudflare build. It needs the same static-JSON
treatment `history/data.ts` got in rev 69 before the 301 comes off.

---

## The roster's `state_affiliated` flag is not applied consistently (CEO call)

Found 2026-09-21 while answering "why can't we score the unscored". **Not
acted on**, because acting on it either way changes how ~25 major outlets are
scored and that is an editorial decision about what Void asserts.

`tests/test_source_roster.py` reports the split every run:

- **48 outlets carry `state_affiliated`.** Mostly state media whose alignment
  is the dominant editorial signal (RT, CGTN, Xinhua, TASS, Global Times, Gulf
  and Saudi state press), plus six democratic public broadcasters: SVT, NRK,
  RTP, Tagesschau, SABC, Agencia Brasil.
- **30 more are described in their own notes as publicly funded and carry no
  flag.** Among them the BBC ("charter requires impartiality"), CBC ("funded
  by parliamentary appropriation"), NPR, Yle, AFP, DPA, and **Voice of
  America**, whose note reads "US federal government international broadcaster
  operated by USAGM".

The two groups are the same class of outlet under two different conventions.
SVT is flagged; Yle is not. Tagesschau is flagged; the BBC is not.

**Why it matters, concretely:** `_delta_max_for` gives a flagged outlet a text
delta of 8 instead of the default, so its own words move its score far less
and the baseline anchors harder. And `political_lean.py`'s `unscored` rule
excludes a state-affiliated outlet outright. So the flag is not cosmetic; it
changes both the number and whether the article counts.

**The decision:** does `state_affiliated` mean *state-funded* (then the BBC,
CBC, NPR, Yle, AFP and VOA all need it, and their scores tighten) or
*state-aligned editorial control* (then SVT, NRK, RTP, Tagesschau, SABC and
Agencia Brasil should lose it)? Either answer is defensible; picking one by
inference is not, which is why nothing was changed.

Recorded because an assertion demanding the first reading was written, ran, and
flagged the BBC. It was downgraded to a report before it could be committed:
"fixing" 25 rows on an unchecked inference would have introduced error while
claiming to remove one.

---

## Watch on the next run

**Bias defaults after the step 6b fix: MEASURED 2026-09-21, and the fix works.**
Run #375 (built 2026-09-21T18:18, the first scheduled run carrying the fix)
against the export it committed:

| | before (2026-09-20) | after (run #375) |
|---|---|---|
| whole default tuple | 540/737 (73.3%) | 186/975 (**19.1%**) |
| `political_lean` at exactly 50 | 610/737 (82.8%) | 522/975 (53.5%) |
| `sensationalism` at 10 | 637/737 (86.4%) | 657/975 (67.4%) |

19.1% is not the low single digits this note used to predict, and the reason
is the one a share cannot express: **all 186 default rows are published
2026-09-20. Not one of the 534 articles published 2026-09-21 is a default.**
Today's scoring was clean. The residue is the previous day's damage, loaded
out of the state DB by step 6b's own 36h lookback and written back faithfully
by `existing.get("political_lean", 50)`.

**Confirmed from run #375's own counters**, not inferred from the export:

    Articles analyzed: 10029/10029
    Lookback articles needing stored scores: 2845; bias rows loaded: 2845
    Framing re-scored: 7193 articles (7193 DB rows updated in batches)
    bias defaults: 186/975 per-article rows are the default tuple (19.1%)

Every article the run fetched was scored. The lookback preload hit **2845 of
2845**, so it has no gap. And there is **no "Framing update skipped" line at
all**, meaning `framing_no_scores` was 0: not one row was written from
defaults. 6b did precisely its job, which is to preserve what is stored, and
what was stored for those 186 was already the previous day's default tuple.

So it is not a live defect and it clears itself: those articles leave the 36h
window within about a day and a half. **Prediction to check on the run of
2026-09-23: near zero.** If it is not, something is writing defaults again and
the mark assertion below will say so.

**`PER_AXIS_MAX_SHARE` was deliberately NOT retuned against this run.** Lean
at 50 came in at 53.5% against a 40% cap, but that population still contains
the carried-forward residue, so tightening or loosening to fit it would be
calibrating against contaminated data, which is the mistake this whole pass
exists to undo. The caps only drive the printed `OVER` marker now, not a
failure. Retune them against the 2026-09-23 run.

The rows are recognisable: four default axes, a real varying `framing` score
and a framing-only rationale, which is the old 6b signature. 135 of the 186
come from RATED outlets, including nine Newsmax rows at lean 50 against a
`far-right` baseline of 90, which the analyzer's own contract makes impossible
for a measured article.

`tests/test_bias_defaults_gate.py` asserts the invariant that actually
protects the reader, not the share: **no default-tuple row may be unmarked.**
A marked row is out of the cluster aggregate, off the Deep Dive spectrum and
labelled Unscored, so it misleads nobody; an unmarked one is read as a
measured 50 everywhere. The share is printed every run, and only a run that
measured almost nothing (>60%) fails on it.

The check exempts itself, self-detectingly, while the committed export carries
no `lean_unscored` key on any row, which is true of run #375 because it ran on
`adc05f4`, before the field was carried out of the database. The first export
from current code turns the assertion on with no edit.

**House promos: DISCHARGED 2026-09-21.** All 78 published History episodes
carry a promo under their outro, stitched without re-rendering a single line
of TTS (run 2 of `stitch-promos.yml`, 50 minutes, zero guard failures). Every
duration is unchanged and inside the 7.5-15.5 minute gate, 18 distinct promos
are in use, none advertises History to itself, and `renderedAt` is preserved
so the script-staleness check still bites.

Left to watch: the first daily run after this lands should put a `promo`
chapter on the served On Air MP3 with A-04 still passing, and the first Sunday
issue the same for The Argument. The CEO ear test on `af_kore` at speed 0.86
over `radio_promo_bed.wav` has not happened; `af_sarah` is the American
alternate (`VOID_PROMO_VOICE`), and a voice change means a re-render plus a
re-stitch, which is cheap because the un-stitched masters are parked under the
release tag `history-audio-clean`.

**Podcast channel.** `podcast-history.xml` (73 items) and `podcast-weekly.xml`
now generate and are linked from `/listen` and `layout.tsx`. Not submitted to
Apple Podcasts or Spotify (`docs/PODCAST-DISTRIBUTION.md` has the checklist;
the owner mailbox must be monitored for Apple's verification mail). Weekly
and History covers exist as SVG only; the JPGs need the brand render step.
`frontend/public/podcast-us.xml` was deleted (dead Supabase host, nothing
regenerated it); the US edition gets a feed again when it renders again. The world feed
was cut from 9 items to the episodes whose MP3s exist (7 of 9 enclosures
returned 404 because audio retention keeps two dated files).



**Weekly — DISCHARGED 2026-09-20.** Vol. I, No. 1 ran on the new Sunday cadence
and is live. Everything rev 71/72 left unverified now has evidence:
`departments` carries Technology and Sports & Culture (the first departments
the section has ever published), `opinions` carries five essays with the first
two paired, `week_days` recorded seven days, every brief item carries a
`cluster_id` and a section kicker, and `build-data/weekly-issues.json` took its
append. Enforcement fired on six pieces, named each finding, regenerated all
six, and shipped the cleaner attempt every time (opinion 4 went 310 to 354
words; opinion 2 lost "crucial"). `_spread_over_week` logged "10 stories across
3 day(s) of the week" against the old all-ten-from-one-date. All nine
`verify_sections` W-checks pass against the served page, W-08 included, which
was red on the live site before this branch.

What it exposed, all now fixed: a `NameError` on the last line before
persistence that discarded four minutes of paid generation (and the import-wall
premise that had exempted the whole generator file from testing), and a brief
length check that tested a ceiling with no floor, which passed a column with
nine of ten items below the spec.

**Still short of spec, and not yet solved:** the model undershoots every length
target and regeneration narrows the gap without closing it. Cover 2 shipped at
507 words against 800-1200, two opinions below the 400 floor, and the briefs at
40-49 against 55-75. The enforcement is working as designed (measure,
regenerate once naming the findings, ship the cleaner attempt); the prompts are
what need strengthening. Three uses of "significant" also survived two attempts
and are on the page. They are deliberately NOT stripped mechanically: deleting
the word from "widespread protests and significant disruption" changes what the
sentence says, so this needs a rewrite, not a regex.

**No cover image** was found for the issue. W-03 treats that as acceptable
(better than an unlicensed one) but a magazine cover with no photograph is a
standing gap.

**Daily pipeline, after rev 65** (the rev-64 list is DISCHARGED: 09-07/08/09
were clean, `14208/14208 re-ranked`, `Errors: 0`, verify-production green):

- `[8c.6]` coherence: the trimmed count should fall sharply from 17 clusters /
  55 members. Read the removals; every one should be a story you would not put
  in that cluster.
- `[8d.15]` merge now runs after the title clean. Expect roughly 1 merge where
  09-09 got 0, and a `survivor summary invalidated` line beside it.
- `[8d.2]` critique: `N cards read, M carried a finding` should rise well above
  09-09's 2 of 35, now that the editorial rules are judged from the card.
- `Bench lifted` should be single digits, not 48. A large lift means a sentinel
  leaked into the minimum again; the harness asserts this too.
- No card in the top 20 should be a listicle, a shopping page or a photo
  gallery, and no headline should carry quotation marks around words no source
  printed.

---

## Left by the audio restructure (rev 77, 2026-09-21)

Three things the two-slot rewrite deliberately did not touch. None of them
causes the desyncs that rev fixed; each would have widened it.

**The daily archive UI is permanently empty.** `lib/supabase.ts:201-231`
takes an `edition` argument and ignores it, so the "Previous broadcasts" list
on `/onair` and in the panel has nothing to show. The whole `edition` axis
(`world`, `us`, `europe`, `south-asia`) is dead below the label: the pipeline
writes one edition and the reader has no control that switches it.
`setEdition` still exists in the provider and now only sets state, having lost
the ownership claim it used to make. Decide whether the axis comes back or the
archive, `previousEpisodes`, `loadEpisode` and `setEdition` all go.

**Revolt has its own `<audio>` element.** It can play at the same time as the
shared player, which no other section can. Revolt is 301-hidden and serves
MOCK data, so nobody can reach it; the fix belongs with the work that makes it
read static JSON.

**`.msc__modal-backdrop` carries `z-index: 1000`**, off the token scale
(`--z-modal` is 100). It happens to sit above everything and so works; it is
the one place a layer is decided by a literal rather than by the scale.

---

## Scoring the unscored: two items authorised 2026-09-21, both blocked on ground truth

The CEO authorised all three answers to "why can't we score them". The first
(rate the chartered broadcasters) shipped in rev 79: eight outlets placed,
3.4% of article volume recovered. These two did not, and the reason is the
same for both.

### 1. Per-market English lexicons

India (24 outlets), Pakistan, Nigeria, Kenya, Bangladesh and Sri Lanka publish
in English, and their political discourse is highly placeable: Hindutva /
secular, communal, reservation, Dalit, anti-national for India; comparable
vocabularies elsewhere. Adding them would move real articles off 50 for real
reasons, which is the largest single reduction available in the 26% unscored
population.

**Blocked on:** all 43 fixtures in `pipeline/validation/fixtures.py` are US or
Western outlets (AP, Reuters, NYT, Fox, Jacobin, ProPublica, Bellingcat,
Intercept, Mother Jones, Breitbart, Daily Wire, Newsmax, RT, CGTN, Sputnik,
NPR). There is **no** Indian, Pakistani, Nigerian or Kenyan fixture. So
running the suite after a lexicon change proves only that US scoring still
works. It cannot show that the new terms score an Indian article correctly,
and it cannot show they do not misfire on Indian NEUTRAL reporting, which is
the failure mode `political_lean.py` already documents three times over:
`fossil fuel`, `renewable energy`, `carbon neutral`, `diversity`, `equity`,
`inclusivity` and `housing crisis` were all REMOVED for firing on neutral
copy, each costing 20-30 points of false lean.

**First step is a corpus, not code:** real articles from those outlets with
expected lean ranges, the way the 43 existing fixtures are built. That is
research (`linguist` and `bias-auditor` exist for it), and until it exists a
lexicon expansion ships unvalidated keyword changes straight into production
bias scores.

### 2. A second axis for politics that does not run left/right

The deeper answer, and the one no lexicon reaches. India's main cleavage is
secular / Hindutva. Kenya's is ethnic-regional. Scoring those on a left/right
axis is a category error however good the vocabulary, which is why 234 of the
287 still-unplaced outlets are in countries of exactly that kind.

**Blocked on two things.** It needs the same ground truth as item 1, and it
changes a **locked decision**: the 6-axis bias model is on the CEO's locked
list, and this is either a 7th axis or a per-region axis with its own labels,
ladder, colours and public methodology copy. Worth a written proposal before
any code, since it touches `/about`, `/sources#methodology`, the Sigil and
every card.

---

## Deliberately not done, with reasons

**Ranking signal weights are unchanged.** They must not be tuned against a
baseline where the re-rank was dead. Re-run `pipeline/evals/replay_ordering.py`
after a week of post-fix runs first.

**The coherence pass abstains** rather than trimming a cluster with no modal
vocabulary. That is a clustering defect, and trimming would pick an arbitrary
half.

**A deterministic L-03** (split the headline on a semicolon, flag when the
halves share no subject) was tried and REJECTED on measurement: it flags 84 of
the 96 semicolon headlines in the archive, because "development; consequence"
is ordinary headline grammar. Recorded so it is not retried.

**Audio is not on R2.** The deploy pulls ~470 MB and still finishes in under
three minutes; at 78 episodes it is ~950 MB and still a few minutes. Flagged as
a scaling worry, measured, and not one yet — but it is the reason binaries keep
accruing in git history.

---

## Housekeeping backlog

- Last Lighthouse point to clear 90 (home/weekly ~88/89 mobile, gzip-measured).
  The old "code-split `@supabase/supabase-js` off the critical path" item is
  obsolete now it is off the read path. Re-measure before acting.
- a11y follow-ups: feedback error messaging, weekly heading.
- Security MED-2: CSP `unsafe-inline`.
- `IP_SALT` must be set as a real secret in prod (`wrangler secret put
  IP_SALT`) — the checked-in value in `worker/wrangler.toml` is a dev
  placeholder. The D1 `database_id` there is genuinely provisioned.
- iOS/Android signing, first store submission, branch protection.
- 77 class names are written in markup with no rule behind them (the reverse
  direction of `frontend/test/css-parity.test.mjs`, printed on every run, not
  failing). Among them `.dd-page__section`, `.hist-hr-account__type`,
  `.fp__playlist`. Each is either a hook nothing styles yet or a name that
  outlived its CSS; the owner of each component decides which.

## History: 70 over-escaped apostrophes reach the reader

Found 2026-09-21 by a drafter working the dash pass, who flagged it rather than
silently editing text outside its remit.

70 string values across `apartheid`, `bandung-conference`, `mongol-empire`,
`silk-road` and `the-crusades` carry a literal doubled apostrophe, and it
reaches `frontend/public/data/history.json`. Readers see `Mandela''s`,
`Biko''s`, `Chang''an`, `the world''s tallest equestrian statue`, and
`Jami'' al-Tawarikh` for what should be `Jami' al-Tawarikh`.

The diagnosis is certain. In a single-quoted YAML scalar `''` is the escape for
one apostrophe and the parser collapses it, so anything still doubled AFTER
`yaml.safe_load` is an escape written into a scalar that does not honour it.

What is NOT certain is where each one sits, and that is why this is written
down rather than fixed. Every sampled instance is on a CONTINUATION line of a
multi-line scalar, with no `key:` prefix to say how the scalar opened. A
line-based replacement cannot tell a plain continuation from the continuation
of a single-quoted scalar, where `''` is correct and must stay. A first attempt
proved it: it broke all four files it touched, and only a "revert anything that
will not re-parse" guard kept the damage at zero.

The sound fix is a formatting-preserving round trip (`ruamel.yaml`, not
installed here) or a scalar-span tracker that knows which quoting style opened
the block. Not a regex.

Worth doing with the tree quiet, since the same five files were being rewritten
by the dash pass when this was found.

## History audio: two episodes nobody has ear-checked

The five episodes whose scripts changed on 2026-09-20 and 09-21 were
re-rendered and published on 2026-09-21 (run 35562858536, after the publish
job learned to `pip install pyyaml`; the first attempt rendered all five and
then failed 78 promo checks for want of it). `tests/test_history_audio.py`
names a stale episode automatically on a **full clone**; at `fetch-depth: 1`
it skips that check by design.

Still pending: `peloponnesian-war` estimates 15.06 minutes against a 15.0 warn
line (the hard gate is 15.5, so it ships), and `treaty-of-waitangi` reads a te
reo Maori passage verbatim and has never been ear-checked. No validator can sign
off a synthesiser on unfamiliar phonemes.

## The Hearing: deletion and production gates

Steps 3d and 3e of `docs/proposals/HISTORY-PAGE-REVAMP.md` are unbuilt.

**Nothing has been deleted yet.** `EventDetail`, `PerspectiveFrame`,
`PerspectiveReader`, `ReelScrubber`, `OmissionsPanel`, the reel CSS and the
six-stage CSS are all still present, and `EventDetail` is still mounted from
`HistoryOverlay` on the landing. Port the weekly's two-directional class-parity
test to `history.css` **before** deleting anything: the file is large and a
class removed from CSS while still referenced in TSX fails silently.

Served History checks live in `scripts/verify_sections.py`: H-01..H-04 plus
H-05 (no dash in the served text or any accessible name) and H-06 (one `<h1>`,
at least 60 event card links), added 2026-09-21 when the landing became a
prerendered page. `verify_production.py` itself still reads only `/`.

## Weekly: no scheduled run has produced The Argument

The format works and the episode is live, but it got there by manual
`audio-only` dispatch. Every scheduled run so far fell back to the legacy read,
and that fallback is now deleted, so the next Sunday 18:00 run either produces a
real episode or ships none. The generator fix (`word_budget`) is what should
make it produce one. **Watch the first scheduled run.**
