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

**The lean gate: the CARD no longer depends on it (2026-09-21), but the gate
still runs and the threshold below is still unreviewed.** The feed card and
the Sigil now read the roster's SHAPE (`leanShape`), not the gated mean, so
`LABEL_MIN_CONFIDENCE` no longer decides whether a story says anything: the
card speaks on 30 of 35 stories against 15. `storyLeanLabel` and
`leanLabelState` are still live for the Deep Dive's own label and the share
card, which is where the decision below still bites. Read what follows as
scoped to those two surfaces, not to the feed.

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

### Partition audio: the Nehru chapter title and three quiet-mood chapters (2026-09-25)

The re-render with the signed Nehru clip (run 36181105314) admitted it at
-19.3 LUFS. Left: H-10 warns that "Radio" is spoken but appears only in the
ledger, not the event data; the chapter title is the ledger row's full title;
"How many", "The force that was supposed to hold", "Women's history" and
"Legacy" master 2 to 3 LU above their mood targets.

### The cambodian-genocide event YAML carries errors the thesis ledger refuted (2026-09-25)

Found while settling the record for the thesis; the YAML and the script were
not edited (parallel-work rule). Each item names what the fetched record says.

- `primary_source_excerpts` and the survivor perspective attribute a quotation
  to Dith Pran as "Testimony to the ECCC, 2009". The YAML's own `key_figures`
  row has him dead in 2008. Impossible; no ECCC transcript carries him.
- `hero_image_attribution` and the media rows name Commons files that do not
  exist: `File:Tuol_Sleng_Genocide_Museum.jpg` and `File:Vann_Nath_Painting.jpg`
  both answer 404. `File:Choeungek2.JPG` exists but is Adam Carr, February 2005,
  released to the public domain, not "Bong Vat, CC BY-SA 3.0, 2007".
- Subtitle and legacy points: "14,000 faces, 7 survivors" and "14,000-17,000
  prisoners; between 7 and 12 survived". The Case 001 Judgement's floor is
  12,273 detained and 12,272 executed, and it says only "a very small number"
  survived; no held record counts the survivors.
- "Nuon Chea and Khieu Samphan, both convicted of genocide": Khieu Samphan was
  convicted for the Vietnamese only and found not responsible for the Cham
  (Case 002/02 summary paragraph 62).
- The Ba Chuc massacre is dated "April 1978" in one perspective and "April 30,
  1977" in another; neither date is in any held record.
- "Mark Harmon resigned in 2019": the ECCC's own notice has Harmon resigning
  in 2015 and Bohlander in 2019 (search only; not held as an extract).
- Bibliography identifiers: `10.2307/20045600` and `10.2307/20034330` are
  Foreign Affairs reviews, `10.5860/choice.*` are Choice reviews and
  `10.1355/cs36-2h` is a Contemporary Southeast Asia review, none of them the
  books they are attached to; Chanda's `OL2552862M` resolves to "The business
  of shipping"; Mertha's archive item is a libgen upload, not a lawful copy.
- The Duch quotation "I am not a violent man. I was simply doing my duty..."
  is not in the ECCC's compilation of his statements of apology.
- "$337 million over 16 years" is press reporting; the ECCC's own 2014 sheet
  gives $204.6 million for 2006 to 2013 and no total.

### Four more event YAMLs carry errors their thesis ledgers refuted (2026-09-25)

Found during the Stage 5 audits of the 2026-09-25 theses. The theses are
correct; the Hearing data and the audio scripts are not yet. Fix each during
that event's audio pilot, and run `tests/test_history_quote_ledger.py` after.

- **scramble-for-africa**: Leopold's "cake" letter is 1877, not 1876; the
  Rhodes, Casement, Yaa Asantewaa, Mahdi and Omar Mukhtar quotations are not
  in any held source; Morel's "smoked hands"; "104 days"; Adwa "6,000"; a dash
  in the Kipling line; several attributions.
- **spanish-flu-1918**: Samoa "8,500 / 22%" against the held 7,542 / 19.8%;
  "revised upward by every study" is false; "21 million"; the Sanitary
  Commissioner, Vaughan and other quotations are unsourced; Gandhi's 1918
  illness was dysentery; the Pacific studies name the wrong authors; the
  Funston cook detail is unsourced.
- **armenian-genocide**: the Biden and Hitler quotations are misworded; the
  Mardiganian, Scheubner-Richter and Morgenthau quotations are not in their
  texts; "235 arrests"; the death_toll floor omits the 450,000 figure.
- **haitian-revolution**: "I have avenged America" is from Dessalines's April
  1804 proclamation; the Boukman prayer is not in Dalmas; "until 1947"
  conflates the indemnity with the loans; review DOIs attached as books; the
  7 April 1803 death date is unsupported by the held record.

### 62% of article volume is scored on eleven words (2026-09-22)

**The largest measured defect in the product.** Full write-up in
`docs/proposals/OUTLET-BASELINE-PROGRAMME-2026-09-22.md` section 0.

**Update 2026-09-26 (rev 82).** Now measured every run in
`frontend/build-data/engine.json` and printed on `/sources`, dated. Run #379:
251 Google News sources delivered 4,809 of 11,613 articles at a median of 11
words; 58.5% of the run was under 150 words and never reached the text
analyzer. The check this entry asked for exists (`tests/test_engine_health.py
--floors`, after the data commit), keyed on the DIRECT share because that is
the class that can regress. The roster still carries 340 Google News rows.
Re-ran `discover_feeds.py` over all 340 (2026-09-26): 52 returned a candidate
feed, the rest 404 / 403 / 402 / not a feed (some 403s may be the sandbox's
datacenter IP, so a re-run from a runner is worth one try). `verify_feeds.py` +
`apply_feeds.py` applied **8** (`data/roster/feed-changes-2026-09-26-gfed2.json`)
and held 44 with reasons (`feed-review-2026-09-26-gfed2.json`). The bar gained
two holds on the way, because it passed 24.kg English's Russian elections
section (last updated for the 2021 vote), Ecuador Times (newest item 820 days
old) and CMC (23 days): a feed's newest item must be under 14 days old, and an
outlet listed by an edition path (`/english/`) must get that edition. 332
Google News rows remain, and most of them cannot be migrated: they are
declared on `/sources` instead.

540 of the 1,016 sources on the roster as measured on 2026-09-22 (53%) are fed
by Google News search queries. Across 78,328
archived articles:

| feed type | articles | median word count | share >= 150 words |
|---|---|---|---|
| direct outlet feed | 29,594 | 407 | 66.0% |
| Google News query | 48,734 | **11** | **0.0%** |

`confidence = min(1, word_count/150)` is therefore ~0.073 for half the roster:
the text term is scaled to 7% of its budget before the lexicon is consulted.

Mechanism: Google News returns opaque `news.google.com/rss/articles/CBMi...`
tokens. `web_scraper.py:589-596` takes `canonical_url` from `response.url`
after redirects and `main.py:1165-1173` relies on it to recover a publisher
URL. Measured 2026-09-22 with both a browser UA and `VoidNews/1.0`: the
redirect no longer leaves news.google.com (one hop, 582 KB of JavaScript, no
publisher URL). Scraping falls through to the RSS summary at
`main.py:1178-1182`, and the archive shows the result is a headline.

Fix before any bias-engine or baseline work: resolving the token needs the
private `batchexecute` RPC (signature-sensitive, breaks on Google's schedule)
or Playwright at 2 to 3s per item, so the honest options are to migrate those
540 sources to direct feeds where they exist, or to accept and DECLARE that
those outlets are scored on headlines. Either way the 6 axes are currently
measuring something different for 53% of sources than the methodology copy
describes.

**Add a check in the same commit:** assert median `word_count` by feed type in
the state DB after a run, and fail when a source class collapses below a floor.
Nothing today would have noticed this.

### The lexicon is flat outside US politics, and it is a separate defect

Confirmed independently of the above, which is what makes it clean: every
outlet whose text signal reads near zero is a DIRECT feed holding real
articles. N1 Info (median 350 words, 89.3% over 150) reads -0.10; Euro Weekly
News (498, 96.1%) reads -0.09; The National (588, 96.7%) reads -0.08; ARY News
(369, 98.6%) reads +0.11. Townhall, also direct at 675 words, reads **+7.07**.

`_keyword_score` returns exactly 50 iff zero lexicon types fire, and the
sigmoid gives 55.5 for one type, 59.9 for two, 66.6 for three. A mean absolute
shift of 1.93 implies the lexicon fires about 0.3 of a term per article. Every
entry in `LEFT/RIGHT_CODED_ENTITIES` is a US actor.

The clamp is NOT the constraint: `_CENTER_TEXT_DELTA_MAX = 24` governs 62.6% of
the roster at `_TEXT_AUTHORITY = 1.0`, and we use 8% of available travel.
Widening any weight turns a valve that is already open.

Non-circular route to per-market lexicons, which is what unblocks the item
already recorded below: **Manifesto Project (MARPOR/CMP) RILE scores**,
hand-coded left-right for ~1,000 parties across 50+ countries, plus party press
feeds, give a per-country reference corpus of known-ideology text in the target
language. Run Gentzkow-Shapiro chi-squared per market against it. Outlet labels
may derive candidate features; they may never evaluate, or the result is an
outlet classifier that scores well and measures nothing.

### `source_topic_lean` was a closed loop (CUT 2026-09-22)

FIXED. `political_lean.py` blended the EMA into the prior at 0.7/0.3;
`topic_outlet_tracker.py:88` builds that EMA from `political_lean`, the
engine's published OUTPUT, defaulting a missing key to 50. Output became input,
and no outside evidence entered anywhere in the cycle, so it could not correct
an error, only compound one.

Measured before cutting, it was **not** the cause of the centre pull: mean
|published - label| for rated non-centre outlets is 5.45 across all rows and
**0.74** once default-tuple rows are excluded. The apparent compression is
6,256 unmeasured rows. It was cut anyway because the outlet-baseline programme
wires a LEARNED per-outlet offset into the same prior, and a self-fed term
beside a learned one corrupts the thing being learned.

`topic_lean_data` is still accepted and discarded, so the four call sites need
no edit and Axis 6 keeps writing the table for its own reporting.
`tests/test_lean_prior_is_not_self_fed.py` asserts the parameter is inert at
four text lengths across four outlet ratings, that the reported
`source_baseline` is the outlet's own, and (the part that stops it coming back)
that the scorer names no field of its own output table and the tracker does not
import the scorer. Restoring the blend fails 18 of its 19 checks.

**Not measured:** how many rows `source_topic_lean` actually held. The table is
in `migration/schema_pipeline.sql` and written every run, so the loop was wired
at both ends in production; the row count needs the state database, which is
gitignored and not present here.

### The pipeline commits to main with no gate (FIXED 2026-09-23)

`pipeline.yml` pushed `frontend/build-data`, `frontend/public/data` and the audio
straight to main and ran **zero tests** first. Every control lives in
`auto-merge-claude.yml`, which only runs when a `claude/*` branch merges, so the
daily production path could commit anything to a public repository and nothing
could catch it.

It did, on 2026-09-22. Run `d2520a39` checked out main before the grounding fix
had merged and wrote 35 format-1 records carrying **439,244 characters of
publisher prose**, against `docs/IP-COMPLIANCE.md`'s top control. The check that
forbids exactly that had been written the day before and could not fire.
Converted in place by `scripts/migrate_grounding_index.py`; the tree is clean
again at 70 records, all format 2.

`test_grounding.py` and `test_bias_defaults_gate.py` now run in `pipeline.yml`
immediately before its `git add`. Kept to those two on purpose: this is the daily
production path, and the right checks there are the ones that read what the run
just wrote.

**The general lesson, worth more than the fix:** a gate that cannot run on the
path that writes is not a gate. Worth auditing the other workflows that commit.

### Publisher prose in git history (the working tree is clean)

FIXED IN THE TREE 2026-09-22, still in history.

`frontend/build-data/grounding/` held 35 files, 975 records, **519,041
characters of source article text**, longest record 10,003 chars, because
`grounding.py` stored the prose E-13 and E-14 read and the repo commits
`build-data/`. The daily pipeline truncates `full_text` to 300 chars at
`main.py` step 10 for exactly this reason, so the throwaway state DB was
protected and the permanent public repo leaked.
`docs/IP-COMPLIANCE.md` names this as its single highest-priority control.

A record is now a verification index rather than prose: the set of numbers, and
a Bloom filter of 4-word shingles that answers membership and cannot be
inverted. All 35 committed records were converted in place by
`scripts/migrate_grounding_index.py` with no loss of audit power (501/501
numbers, 5,826/5,826 within-article 8-word spans still verify; 700/700 shuffled
spans still rejected). `tests/test_grounding.py` now fails on any committed
record that is format 1 or carries a string over 12 words.

**What is left is a decision, not a task.** The prose committed on 2026-09-21
is in git history permanently unless the history is rewritten. A rewrite of a
pushed public branch changes every downstream clone's hashes and is the CEO's
call, not a maintenance action. Until it is taken, the tree is compliant and
the history is not.

### 22 major outlets still absent, and why each class of them is

Added 48 on 2026-09-22 (roster 1,061; 216 of 238 targets covered, was 147). Full
record in `docs/CHANGELOG.md` rev 80 and
`data/roster/majors-added-2026-09-22.json`. The 22 that remain are not a
backlog of the same work; they fall into classes that need different answers:

- **A bot wall.** Reuters returns 401 and AP a Cloudflare 403 to any
  non-browser client, and several majors now serve RSS only behind one. These
  cannot be migrated by a fetcher and need a decision: accept that they are
  scored on headlines and say so on the page, or drop them.
- **RSS discontinued.** Some majors no longer publish a public feed at all
  (10 of the 70 returned 404 on every candidate path, 7 returned 403).
- **Paywalled at the feed.** A feed whose items carry a teaser and whose
  article the scraper cannot read is a Google-News-grade 11-word item wearing
  a direct feed's URL.

Still absent: Ahram Online, Asahi Shimbun, Diario de Noticias, Die Zeit, Duvar English, El Mostrador, El Tiempo, Expresso, GhanaWeb, Il Foglio, L'Express, Le Figaro, Le Soir, Les Echos, Mediapart, Publico, Publico (Portugal), Sueddeutsche Zeitung, Svenska Dagbladet, Tages-Anzeiger, The Daily Star (Lebanon), taz.

**The added rows carry a provisional baseline, not a measurement.** The
intended side is mapped inward (L to `center-left`, C to `center`, R to
`center-right`) and every row's notes say so. The outlet-baseline programme
measures them; until it does, the roster understates rather than overstates,
and `unrated` was rejected because it would have dropped all 48 out of the lean
aggregate and off the spectrum.

**Their market verdicts read `pending`, not covered.** The healthy-sides column
in `scripts/roster/audit_majors.py` reads a tiers snapshot built from the
41-day archive, which a row verified today cannot be in. Such a row is tier
`N`, and a side whose only evidence is an N row says "added today, no archive
yet". Rebuild `data/roster/tiers-<date>.json` after these outlets have
published for a few weeks to resolve them.

**Two feeds are held on a 429 from this runner's IP**, not on their merits: St.
Louis Post-Dispatch and Rapid City Journal, both Lee Enterprises. St. Louis
measured 50 items / 50 on-domain / 50 article-shaped once in the same session,
which is one observation and not two, so it is recorded rather than applied
(`data/roster/rejection-corrections-2026-09-22.json`). Re-run from an
unthrottled IP.

### robots.txt: statuses FIXED, the UA token is a product decision

The fail-open half is fixed (2026-09-22). `_check_robots_txt` returned `True`
for every non-200 and every network error, so a 403 on robots.txt, a 503 and a
429 all read as consent, on the one file whose job is to say no. The error ran
one way: it never refused a site that had allowed us, it only scraped sites
whose answer we had failed to obtain. Now split per RFC 9309 section 2.3.1:
404/410 and other 2xx allow (no restrictions exist), 401/403 deny
("unauthorized", access completely disallowed), 429/5xx and network errors deny
for the run. `robots_verdict_for_status` is a pure function so
`tests/test_robots_compliance.py` can assert it with no network, which is the
point: the old behaviour was untestable except against real sites, so it was
never tested.

**The cost was measured, not assumed.** Sampled 70 random roster domains on
2026-09-22: 60 served robots.txt (200), 5 returned 403, 1 returned 429, and 4
failed at the transport (2 read timeouts, 1 proxy error, 1 TLS error, at least
two of them this container's network rather than the site's). So the split
denies 14.3% of domains, of which 7% are an outright refusal we should always
have honoured. Because most of the rest is noise rather than a decision, a
transient failure now gets ONE retry before it denies; a 401, 403 or 404 is a
real answer and is not retried.

**Still open, and it is a product decision, not a defect.** We send a browser
User-Agent, so we present no product token and the applicable group is `*`.
That is the correct robots reading for an unnamed agent, and it is also why a
site disallowing only named crawlers reads as open to us. Declaring our own
token would fix the reading and would also change what a great many sites serve
us, which is a CEO call. Wire attribution, the other half of this entry, was
fixed the same day: see `tests/test_wire_attribution.py`.

`CANONICAL_WIRE_SLUGS` matches **5 of the 40** outlets carrying
`"type": "wire"` (ap-news, reuters, upi, afp, ians), missing
`dpa-international`, `kyodo-news`, `pti-india`, `anadolu-agency`,
`tass-english` and 30 others through near-miss slugs. The
`tier in ("wire","wire-service")` branch matches **zero** rows, because `tier`
only ever holds `independent`/`international`/`us_major`, so it is dead code.
Cheap fix: key on `type == "wire"` from the roster.



### The lexicon cannot be derived from the surviving corpus (2026-09-22)

**Update 2026-09-26 (rev 82): `phrase_counts` now runs daily** as step 9e, to its
own file, capped at 3 bodies per rated outlet per day. The corpus a derivation
can use starts accumulating from the first run after merge; the median outlet
reaches n=25 in about nine days. Run the derivation with
`lexicon_derive.py --counts phrase_counts.db --roster pipeline_state.db`.

Tried and measured, full write-up in `docs/audits/LEAN-SIGNAL-2026-09-22.md`.

`lexicon_derive.py` reached **rho +0.226 on 119 held-out outlets, scoring 100% of
them**, against the hand-written lexicon's +0.201 on 54%. It also rediscovered **zero
of the 318** hand-written political phrases, and its top entries were `getty images`,
`continue`, `follow`, `photo`, `this article` and `sep`.

It was fingerprinting CMS templates. Outlets on a side often share a publishing
platform, and `full_text` is truncated to 300 chars after analysis, so the surviving
corpus is titles, RSS summaries and leads: largely boilerplate. **Nothing was
promoted.**

**The unblock is `pipeline/analyzers/phrase_counts.py`**, which accumulates per-outlet
phrase counts from full article bodies before the truncation. Counts, never text, on
the grounding index's argument. **It is written and gated but NOT yet wired into
`pipeline/main.py`**: the call belongs in the analysis step, before step 10 truncates
`full_text`, and that is the next action here. Until it runs for a few weeks there is
no corpus a real lexicon can come from.

### Deriving the baselines: measured 2026-09-22, and the lever is not more data

Full write-up in `docs/audits/LEAN-SIGNAL-2026-09-22.md`, reproducible with
`scripts/roster/measure_lean_signal.py` against a state snapshot.

**The signal is real.** Spearman rho between an outlet's mean TEXT-ONLY score
(`rationale.lean.keyword_score`, which never sees the outlet, so this is not
the cut loop reopened) and its label's baseline is **+0.479 across 129
outlets**, +0.515 US, **+0.428 non-US**. This project's own literature review
put the realistic ceiling at 0.5 to 0.7 over 50+ articles per outlet. We are
there on 8.

It also qualifies the entry above about the lexicon being flat outside US
politics: it fires LESS often there and is still directionally right.

**Two numbers say why it cannot be published as a baseline yet.** The lexicon
fires on **26.4%** of the articles the scorer could fully read, so 73.6% of
usable articles say nothing about their outlet; and the text scores span **29
points against the ladder's 80**, a 3x compression.

**A correction to this file's own earlier claim.** It reported "229 outlets,
median 31, 116 at n >= 30, the core already has the sample size". That counted
USABLE articles. The count that governs a per-outlet estimate is
SIGNAL-BEARING, which is median **8**, with only **20** outlets at n >= 25 and
8 at n >= 50. The "no harvest needed" conclusion survives; the reasoning under
it did not.

**So waiting is the wrong lever.** Doubling n moves rho by roughly nothing,
because rho is already at its ceiling and the constraint is coverage. Firing on
50% of articles instead of 26% would take the median outlet from 8 to ~16 and
put ~80 outlets over n=25 instead of 20, at once, with no waiting. Per-market
lexicon coverage is the long pole, and it is linguistic work.

**Publishable now:** rho = +0.48 over 129 outlets belongs on
`/sources#methodology`, said in the same sentence as the fact that it is
measured against our own curated labels rather than an independent panel.
**Blocked on that independence:** raising `_TEXT_DELTA_MAX`. On a signal
spanning 29 points it would let noise move a published score.

### The outlet baselines have no resolution, and the learning table would make it worse

Measured 2026-09-22, full write-up in
`docs/audits/OUTLET-BASELINE-DATA-2026-09-22.md`.

`political_lean_baseline` is a string label mapped to seven integers, so
**636 of the 1,016 outlets on the roster that day (63%) resolve to exactly
50.000** and AP, Reuters,
Bloomberg, DW and 346 others are numerically identical. The article layer does
not rescue it: mean absolute `text_shift` is **1.93 points**. The published
lean is the label, plus or minus two. That is the whole of the "everything
reads centre" complaint, and no display change touches it.

Three things block re-deriving per-outlet numbers from our own corpus, which
is otherwise the only non-fabricated source:

1. **Only 17.3% of bias rows store `rationale.lean.text_score`** (13,386 of
   77,390), the one signal not already contaminated by the baseline. 293
   outlets, median 32 readings, none above 300.
2. **The text scorer reads flat outside American partisan vocabulary.** Mean
   text deviation: N1 Info -0.10, Euro Weekly -0.09, The National -0.08, ARY
   +0.11, against Townhall at **+7.07**. 37% of full-length articles score
   `text_score` exactly 50.0. Deriving 730 baselines from this would yield
   ~40 real numbers and ~690 zeros. This makes the per-market lexicon item
   below the **critical path**, not an enhancement.
3. **`source_topic_lean` already implements the learning, and it is
   inverted.** 6,356 rows, 4,484 backed by >=20 articles, median |deviation|
   from the label **0.04**, and every large deviation points toward 50
   (Financial Express: 189 economy articles, label 65, EMA exactly 50.00). It
   averages unscored rows in as measured centrism, so it measures scoring
   failure rather than outlet lean. **Do not wire it into the baseline until
   it excludes `lean_unscored` rows.**

Also recorded there: the Supabase pg_dumps are **gone** (14-day retention,
last run 2026-08-30, expired 2026-09-13). The durable archive is the
`void-state-snapshot` artifact, 90-day retention, which carries
`pipeline_state.db` with 78,328 articles back to 2026-03-22 by `created_at`,
though 95% of it is the last three weeks.

### The default-tuple gate exempts itself on the exact failure it exists to catch

`tests/test_bias_defaults_gate.py` skips the mark assertion when **no** row in
the committed export carries a `lean_unscored` key, on the reasoning that such
an export predates the field. That condition is indistinguishable from the
marking having broken. Measured 2026-09-22: the committed export carries
**186 default-tuple rows and not one is marked**, and the gate passes. The
export code stamps them correctly (`export_static.py:377`), so this export
genuinely predates it, but the exemption needs to lapse on something that
changes, such as the export's `builtAt` being newer than the stamping code,
rather than on nothing being marked.



### `--sense-high` is a 3.16:1 colour and is still used as text

`#EF4444` is defined once for both modes. On the dark paper it measures
4.61:1; on the light paper (#F0EBDD) it measures **3.16:1**, under AA. It was
the "Contested" label's colour until 2026-09-21, and both that label and the
Bench's `split` word now use `--fg-primary` instead.

The token itself was not changed, because it is primarily a NON-text colour:
the sensationalism scale's top stop, drawn as dots and bars, where 3:1 is the
bar it has to clear. Retuning it would move every sensationalism reading on
both papers. What is left to do is a sweep of its remaining uses to check that
none of them is text on the light paper, and the same question for
`--sense-medium` (#EAB308, which is a yellow and will be worse).

`lean-label-contrast` in `verify-headless.mjs` measures the lean labels in
both schemes and would catch a regression there; nothing yet measures the
sensationalism or rigor labels.



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

## The roster's `state_affiliated` flag: SETTLED 2026-09-23 (CEO)

Found 2026-09-21 while answering "why can't we score the unscored", and left
unacted for two days because acting either way changes how ~25 major outlets are
scored, which is an editorial decision about what Void asserts rather than a
defect to fix by inference.

**The answer: `state_affiliated` means state-ALIGNED editorial control, not
state-funded.** The CEO's reading, and the one the roster's own majority already
followed: the BBC is publicly funded like PBS, and that is a different thing from
RT. So the seven democratic public broadcasters that carried the flag lost it
(SVT, NRK, Tagesschau, RTP, Lusa, SABC, Agencia Brasil) and 41 outlets whose
government alignment IS the dominant editorial signal keep it. Zero flagged
outlets now sit in a democracy.

**Magnitude, stated precisely because an earlier note of mine got it wrong:** all
seven are labelled `center`, which `_is_unrated_source` treats as a FINDING and
not the absence of one, so they were never on the 24-point unrated budget.
Unflagging moves them from **8 points to 10**. It widens what their own words may
say about them by two points; it changes no baseline, tier or placement.

**The gate is deliberately not "no democracy may be flagged",** because a public
broadcaster captured by its government is a real case and a blanket rule would
force a wrong answer the day one appears. `check_public_broadcasters_are_one_class`
names its twelve peers and fails if they are not flagged alike, so a future
divergence has to be argued rather than drift in.

The record of what was wrong, kept because it is the reason this took two days:

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

**Phrase counts, step 9e (rev 82): the steady state is NOT measured past sixteen
days.** The replay ran out of corpus at 2.7M rows (123 MB, part of it filters
since shrunk), still growing close to linearly, with the 7-day prune firing and
the 28-day one not yet reached. Read the `[9e]` line each day: rows before and
after, pruned, capped, file size. `DAILY_MAX_ROWS` (8M) halts recording loudly
and never prunes to fit. If rows are still climbing ~200k a day after day 30,
the late rule needs tightening before the ceiling is reached, and the cache
cost (`void-phrases-v1-`, one entry per run) wants checking against the
repository's 10 GB cache budget, where it sits beside the state cache.

**Direct-feed scrape success doubled on 2026-09-24 with no code change.** The
direct full-body share was 45.0-47.8% on 09-19..23 and 69.4-70.8% on 09-24/25
(state snapshot of run #379). On the bad days ~2,500 direct articles a day carry
a `word_count` equal to the word count of their stored text, the RSS-summary
fallback. No commit in `pipeline/` lands between; run #377's scrape finished
11,451 URLs in twelve minutes, so the 40-minute budget did not bind. Cause
unknown. The engine-health floor (55%) would have failed all five bad days; it
now fails the run on the next one, and the log above that is where to start.

**Pair test (rev 82): score it after about a week of collection.** `pair-test.yml`
collects twice a day. Then `python3 scripts/roster/pair_test.py score --out
pair-test-result.json` (needs spaCy and network). Before trusting the default
bar of 18, eyeball the stored headlines: the first collection matched 3 of 4 at
that bar. India Today's feed returned 403 from the sandbox; check the Actions
log for whether it does from GitHub's runners. The verdict is against the
roster's own labels (CEO chose no human raters), so a high AUC means "agrees
with our labels", while a low one is a real negative.

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

## History: PARKED by the CEO 2026-09-26, holistic Partition approved but not promoted

The holistic Partition thesis (`data/history/theses/drafts/partition-of-india.md`,
overlay `data/history/evidence/partition-of-india/draft/`) passed its Stage 5
audit in two passes (2026-09-26) and the CEO approved it; all History work was
then parked before the promotion commit landed. The live page is still the
single-question thesis. To resume, promote per `docs/proposals/HISTORY-THESIS-PAGE.md`
§15e: fold the overlay into the base ledger, move the drafts file over the
published one with `status: published`, `audited_by: historiographic-auditor
(independent Stage 5, two passes)`, `audited_at: 2026-09-26`, re-export, run
every gate plus TH-01..TH-05 on a production build.

Rights decision already taken (CEO, 2026-09-26): every Kirpal Singh collection
entry goes under the 150-word cap with `rights: null`, including
`src-jenkins-punjab-problem-1947` (162 words, on the LIVE page today, marked
public), `src-mountbatten-press-19470604`, `src-league-memo-1947`,
`src-mahajan-1947`, `src-tejasingh-1947`, `src-dinmohammad-1947` (184 to 228
words) and `src-sikh-note-1942`; re-slice verbatim keeping every cited figure.

Also parked: the other six theses in the holistic model; audio pilots for
Cambodia, Scramble, 1918 flu, Armenia, Haiti (their event-YAML errors are
listed under Known defects); the sentence splitter ends a sentence at a single
initial such as "E." (`_is_abbrev` in `pipeline/history/thesis_format.py`).

## History theses (2026-09-25): Srebrenica and Partition published, Mongol Baghdad not started

Phase 1 of `docs/proposals/HISTORY-THESIS-PAGE.md`. The Srebrenica ledger
(`data/history/evidence/srebrenica-genocide/`) and thesis
(`data/history/theses/srebrenica-genocide.md`) passed an independent Stage 5
audit in two passes on 2026-09-24, and the Partition of India ledger
(`data/history/evidence/partition-of-india/`, 54 entries, 91 extracts, 7
positions, 4 analyses, 25 gaps) and thesis
(`data/history/theses/partition-of-india.md`) on 2026-09-25; both are
`published`: the route renders the Thesis and the served JSON is committed
under `frontend/build-data/history-theses/`. A correction is re-exported with
`python3 -m pipeline.history.export_thesis`; T-14 fails on drift.

**Partition: errors in the event YAML and the episode script, found while
building the ledger.** The YAML and the script were corrected on 2026-09-25
(every item below; the script is re-cut against the ledger, every spoken
quotation is a ledger extract, and it carries inert `# CLIP:` / `# MOOD:`
slots per `docs/proposals/HISTORY-AUDIO-ARCHIVAL.md`). **The served MP3
still carries the old script**: it must be re-rendered (one
`render-history-audio.yml` dispatch), after which the thesis's episode marks
are re-aligned to the new chapters. Until then chapter 5 keeps the manifest's
title "The force that was supposed to hold" so T-10 resolves. The list, as
found:

- `data/history/events/partition-of-india.yaml` says the maps Radcliffe worked
  from were "not resurveyed since 1931"; no document supports it. The 3 June
  statement made the 1941 census authoritative, Abell told the commission's
  secretaries any map read with the 1941 statistics would suffice (ToP XII
  No. 196 n. 2), and both Punjab judges argue from the 1941 census. The
  episode's "census data from nineteen forty one" is right; the YAML is wrong.
- The Punjab Boundary Force as "25,000-strong" over "38,000 sq mi": the
  Governor's own telegram of 8 August gives 7,500 effective rifles (9,000
  with static troops) for 12 districts of at least 12 million people, and his
  letter of 13 August says he had asked for about 20,000. Neither figure in
  the YAML has a document behind it.
- The bibliography entry "The struggle for Pakistan ... by Ayesha Jalal" is
  authored by Ishtiaq Ahmed: it is an Asian Studies Review review of Jalal
  (DOI 10.1080/10357823.2018.1524259). DOIs 10.2307/40194131, 10.2307/1569475
  and 10.2307/20050025 also resolve to reviews (International Journal, Die
  Welt des Islams, Foreign Affairs), not to the works named.
- "Only road link to Kashmir" for Gurdaspur is a position, not a fact: the one
  pre-award document tying Gurdaspur to Kashmir is Mountbatten's interview of
  4 August 1947 (ToP XII No. 335), the award's own grounds are the Upper Bari
  Doab Canal and the Mandi scheme, and the Pakistani charge (No. 428) and
  Ismay's denial are both in the ledger.
- The death toll "200,000 to 2 million" attributes the upper figure to Pandey
  and Butalia, neither of which could be read; the free record holds Khosla's
  200,000 to 250,000 non-Muslims plus "an equal number" of Muslims, and the
  SGPC's and the economists' "about a million". "75,000 women abducted"
  (Menon and Bhasin) could not be read either.
- Quotations not found in any reachable source: Jinnah "Pakistan is a dream
  that has come true" (not in the 11 August address); Gandhi "Muslim friends"
  (not in the two Calcutta speeches reached); Radcliffe "blunder", Attlee "I
  gave them their freedom", Mountbatten "greatest gamble" (none in ToP XI or
  XII). `tests/test_history_quote_ledger.py` reports the three that touch a
  ledger source as unpinned.
- "Constituent Assembly chaired by B.R. Ambedkar": the record of 14 August
  1947 shows the President (Rajendra Prasad) presiding.
- `hero_image_url` points at the decommissioned Supabase storage.

What is unfinished on Srebrenica:

- **The ICJ judgment of 26 February 2007** could not be fetched (the ICJ site
  answers every PDF request with a Cloudflare challenge; the mirror answered
  403). The thesis reaches the finding only through A/RES/78/282's recital of
  it and says so in its gaps. A session with a browser that can pass the
  challenge should fetch it, pin it and re-cut the three sentences that lean
  on the recital.
- **The NIOD report, the Republika Srpska reports of 2002 and 2004, and the
  IRMCT appeal judgments** are gaps for the same reason (host unreachable,
  no open archive found, guessed paths 404). Each is listed in the ledger's
  `gaps` with what was tried.
- **The Srebrenica episode speaks two lines the page no longer prints.**
  Corrected 2026-09-24 in the YAML, the script and the served JSON: the
  Erdemović quotation is now the sentencing judgment's own words (para. 10,
  in the court's English), the narration no longer says the words were about
  "the ones who tried to refuse" (they were about his own refusal), and
  Resolution 819 gets back its silently cut "and others concerned".
  `tests/test_history_quote_ledger.py` fails either divergence.
  **Fixed text-side 2026-09-25: the whole script re-cut against the ledger.**
  Every spoken claim now traces to an extract or the thesis. Cut as
  unsourced: the Mladic "revenge" quotation (the film is a ledger gap), the
  ICJ quotation (a gap), Dodik, Munira Subasic, the Bassiouni definition,
  Nuhanovic, the Sarajevo siege figures, the forest march, the Scorpions
  video, the RS report revoked in 2018, Omarska/Visegrad/Foca, "boys judged by
  height", "eight men doing the shooting". Corrected: "did not fire a shot"
  (they fired warning shots, never directly: A/54/549 paras 304, 472), "a
  handful of bombs" (two, para 305), "roughly eight thousand" (now the
  tribunal's 7,000 to 8,000 and the General Assembly's recital of 8,372,
  kept apart), the battalion (no more than 600 per the tribunal, 150 fighting
  men per the Secretariat; only the besieging force is agreed), Kozluk
  undated, Kravica 1,000 to 1,500 at about 18.00. Added: Witness K at
  Kravica (Krstic TJ para 206) as the survivors' own witness, the denial
  position in its strongest form (Atlagic and Martinovic, p16 and their
  English summary), the Dutch Supreme Court's para 5.1. The event YAML's
  ledger-contradicted fields were corrected with it (death toll, summary,
  significance, the 2019 Karadzic appeal as the Mechanism's, the Riad context,
  the Katzenberger photograph dated 2010, the photographer Michael Büker), and
  every spoken quotation is now in `primary_source_excerpts` and pinned
  verbatim to an extract. **The MP3 still carries the old script and awaits a
  re-render**; the thesis page's episode blocks already show the new lines.
- **Mongol Baghdad** is not started. Partition's gaps that a browser could
  close: Munir's report (in the Kirpal Singh collection, pp. 409-444, fetched
  but not sliced), the Punjab volume of the 1941 census, the two Security
  Council submissions S/628 and S/646 (ODS text layers unreadable), Hill et
  al. 2008 (paywalled), Moon's Divide and Quit, and any Urdu, Hindi or
  Bengali source readable as text.
- **Wikimedia's API answers HTTP 429 to this container**, so the two exhibit
  images' provenance was read from the file pages' HTML, not the API. The
  ledger records Commons' own dates (the Katzenberger photograph is dated
  11 July 2010 on its file page; the event YAML dated it 2007, fixed
  2026-09-25).

## Weekly: no scheduled run has produced The Argument

The format works and the episode is live, but it got there by manual
`audio-only` dispatch. Every scheduled run so far fell back to the legacy read,
and that fallback is now deleted, so the next Sunday 18:00 run either produces a
real episode or ships none. The generator fix (`word_budget`) is what should
make it produce one. **Watch the first scheduled run.**
