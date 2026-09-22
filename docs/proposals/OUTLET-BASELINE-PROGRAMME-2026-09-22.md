# Deriving our own outlet baselines: panel findings and staged plan

**2026-09-22. Commissioned by the CEO. Eight specialist angles, all returned.
Every number below was verified against the repo or the state snapshot by the
synthesising engineer, not taken from a specialist's report. The two exceptions
are marked UNVERIFIED.**

---

## 0. The finding that reorders the question

**62% of Void's article volume is being scored on a median of ELEVEN words.**

540 of 1,016 sources (53%) are fed by Google News search queries. Measured
across 78,328 archived articles:

| feed type | articles | median word count | share >= 150 words | share <= 25 words |
|---|---|---|---|---|
| direct outlet feed | 29,594 | **407** | **66.0%** | 7.6% |
| Google News query | 48,734 | **11** | **0.0%** | **99.8%** |

Not one of the 48,734 Google-News-fed articles reaches the 150-word threshold
for full text authority. `confidence = min(1, word_count/150)` is therefore
about **0.073** for that half of the roster: the text term is scaled to 7% of
its budget before the lexicon is even consulted.

**The mechanism.** Google News RSS returns opaque `news.google.com/rss/articles/CBMi...`
redirect tokens. `web_scraper.py:589-596` captures `canonical_url` from
`response.url` after redirects and `main.py:1165-1173` relies on that to
recover a publisher URL. Measured live today, with both a browser UA and the
pipeline's own `VoidNews/1.0`: **the redirect no longer leaves news.google.com.**
One hop, 582 KB of JavaScript, no publisher URL in the body. So scraping falls
through to the RSS summary fallback (`main.py:1178-1182`), and the archive shows
the result is a headline, not a summary.

This is a silent scraping regression, not a modelling problem, and it has been
degrading the product's core measurement for over half the roster. **It is the
first thing to fix and it is not what the CEO asked about.**

---

## 0b. And the lexicon is separately, genuinely flat

The two defects are additive, and this is the cleanest test in the engagement.
Every outlet whose text signal reads near zero is a **direct** feed holding real
articles:

| outlet | feed | median word count | share >= 150w | mean text deviation |
|---|---|---|---|---|
| N1 Info | direct | 350 | 89.3% | **-0.10** |
| Euro Weekly News | direct | 498 | 96.1% | **-0.09** |
| The National | direct | 588 | 96.7% | **-0.08** |
| ARY News (English) | direct | 369 | 98.6% | +0.11 |
| The Citizen (South Africa) | direct | 716 | 94.9% | +0.31 |
| **Townhall** | direct | 675 | 99.5% | **+7.07** |

Full articles in every row. The lexicon reads Townhall and is blind to the rest.
So the off-US flatness is real and is **not** explained by text starvation: it is
lexicon coverage. Fixing the Google News path will not fix it, and fixing the
lexicon will not fix the Google News path. Both are required.

---

## 1. The answer in one page

**Do not harvest twelve months, and do not harvest at all yet.** Two defects
sit upstream of the question: half the roster is scored on 11 words, and the
lexicon is blind outside US politics. A corpus gathered now would multiply both
at high confidence, which is worse than no corpus, because volume makes a null
look like a finding. Seven of eight specialists said do not harvest first, on
independent grounds.

**Harvest forward, not backward.** The pipeline already fetches all 1,016 feeds
daily. Had a derived-features table existed a year ago we would hold ~195,000
scored rows at zero incremental cost. Building that table costs one schema and
about zero added minutes to the run, and at current volume the median outlet
reaches n=25 in roughly 7 weeks and n=60 in 16. Forward-fill has no
survivorship bias, no ranking-cap bias, no redirect-resolution problem and no
ToS exposure. A targeted backfill then covers only the outlets that cannot
reach n=25 forward, which is tens of thousands of articles rather than 634,000.

**The premise needs correcting.** RSS is a sliding window of the most recent
items. It does not hold twelve months. 540 of 1,016 feeds (53%) are Google News
search queries pinned to `when:24h`, which can be date-windowed; the other 476
are direct outlet feeds holding hours to days. Historical text lives in Common
Crawl, GDELT, Wayback and publisher sitemaps, not in our feeds.

**The statistics do not need a large corpus.** Per-outlet mean error falls as
sd/sqrt(n). At a realistic within-outlet sd of 15 points, n=25 gives SE 3.0 and
n=60 gives SE 1.9, against ladder rungs 10 to 15 points apart. **SE 1.9 already
places an outlet.** There is no statistical case for thousands of articles per
outlet, and the binding scarcity is co-occurrence, not volume.

**The decisive experiment costs a week, not a month.** Pick five outlet pairs
outside US vocabulary that are editorially opposed (an Indian pro- and
anti-government English daily, a Turkish pair, a UK tabloid pair). Because Void
clusters by event, pull articles where both members covered the SAME event. Two
human raters label blind. Measure whether the scorer plus a hand-built
market lexicon separates known-opposed outlets on identical events.

- **AUC >= 0.75:** proceed to one market end to end.
- **AUC < 0.65:** stop the derive-our-own programme, keep the roster label as a
  label, restrict the per-article lean claim to markets where it demonstrably
  works, and redirect to the coverage products in section 6.

If the instrument cannot separate two outlets that loathe each other writing
about the same event, no corpus size fixes that.

**And one thing is due inside 48 hours regardless**, because Rule 1 outranks
everything else in `CLAUDE.md`. See section 5.

---

## 2. The measured causal chain

Each link verified directly.

| # | Finding | Evidence |
|---|---|---|
| 1 | `political_lean_baseline` is a STRING LABEL mapped to 7 integers. No source carries a number. | `data/sources.json`, `political_lean.py:472` |
| 2 | **636 of 1,016 outlets (63%) resolve to exactly 50.000** (350 `center` + 286 `unrated`); 163 are exactly 35.000. AP, AFP, Reuters, Bloomberg, DW, Nikkei and BBC are numerically identical. | roster count |
| 3 | Once unmeasured rows are excluded, the published lean sits **0.74 points** from the roster label for rated non-centre outlets (n=19,302). | state snapshot |
| 4 | The apparent 5.45-point centre-ward compression is **6,256 unmeasured default-tuple rows**, not the model. Excluding them collapses drift from 5.45 to 0.74. | state snapshot |
| 5 | The clamp is **not binding**. `_CENTER_TEXT_DELTA_MAX = 24` governs 62.6% of the roster at `_TEXT_AUTHORITY = 1.0`. Mean absolute shift 1.93 = **8% of available travel**. | `political_lean.py:517,523` |
| 6 | `_keyword_score` returns exactly 50 iff **zero** lexicon types fire. The sigmoid gives 55.5 for one type, 59.9 for two, 66.6 for three. A 1.93 mean shift implies the lexicon fires about **0.3 of a term per article**. | `political_lean.py:626-742` |
| 7 | **Every** entry in `LEFT/RIGHT_CODED_ENTITIES` is a US actor; the right-hand keyword list is roughly 95% US statute and campaign vocabulary. | lexicon dump |

**Conclusion: the bottleneck is lexicon coverage, not model weights, not data
volume, and not the roster's labels.** N1 Info at -0.10 is not a finding of
Serbian centrism. It is the instrument's null.

### The ceiling, so ambition is calibrated

- **BABE** (Spinde et al. 2021): 3,700 sentences, five *trained media experts*,
  Krippendorff **alpha = 0.40**. That is the human ceiling on sentence-level
  bias, conventionally exploratory-only.
- **BASIL** (Fan et al. 2019): best fine-tuned BERT with full context reaches
  **F1 31.49** on lexical bias, and the paper's finding is that *informational*
  bias (who gets quoted, what is omitted) is the more frequent kind.
- **Gentzkow and Shapiro's** 1,000 phrases were **derived** by chi-squared from
  a same-language same-polity corpus of known-ideology speakers, then validated
  against an anchor never used in fitting. The method generalises; the input is
  what we lack.

Realistic ceiling: rank correlation 0.5 to 0.7 against outlet-level human
labels, **in aggregate over 50+ articles per outlet**, for partisan English.
Per single wire article, near zero. We currently publish a continuous 0-100
that implies better resolution than the best published detector of the thing we
claim to detect.

---

## 3. Where the panel disagreed, and the adjudication

**(1) Is the centre pull caused by a feedback loop?** The engine specialist
found a genuine closed loop: `political_lean.py:955` blends
`source_topic_lean`'s EMA into the prior at `0.7/0.3`, and
`topic_outlet_tracker.py:88` builds that EMA from `political_lean`, the
engine's own published output, defaulting a missing key to `50`. Output becomes
input. They argued it explains the compression.

**Adjudication: the loop is real but is NOT the current cause.** Measured, drift
is 5.45 across all rows and **0.74** once default-tuple rows are excluded. The
simulation that matched Bearing Arms to one point matched the EMA value, not the
published score. The loop is a latent trap that must be cut before any learned
offset is wired in, and it is not today's symptom.

**(2) Continuous per-outlet numbers, or keep the roster ordinal?** The curator
argued a float is indefensible to a reader and to a publisher's lawyer, and
would launder ~690 zeros into apparent precision. The calibrator argued for a
posterior with an interval.

**Adjudication: both, at different layers.** Keep the published roster
**ordinal** on the seven rungs. Carry a continuous per-outlet offset with a
standard error **internally**, and assign a rung only when the whole interval
sits inside one rung; otherwise show two rungs or Unscored. Publish the band,
never the point. This must be wired into `leanToBucket` and asserted, or the
interval is silently discarded at render time.

**(3) Does the 4090 change the answer?** Three specialists say no for the
lexicon gap, and they are right: flatness off-US is **coverage**, and the fix is
Monroe/Colaresi/Quinn log-odds with an informative Dirichlet prior against a
cluster-matched corpus. That is a z-score over 78k articles, minutes on a CPU,
and its output is a word list a human can read.

**Adjudication: the GPU is valuable offline and must never enter the scoring
path.** It earns its place on (a) the Bayesian fit, (b) coreference and
target-of-sentiment, which `en_core_web_sm` cannot do, so `_entity_sentiment_score`
currently attributes sentiment to the nearest entity, and (c) a multilingual
encoder as a *miner* proposing lexicon candidates and as a held-out *validator*.
Never as a teacher distilling published numbers: an offset distilled from a
model is an LLM score wearing a rule's clothes.

**(4) Does the locked no-LLM decision block this?** Strategic counsel offered
the sharpest reframing of the engagement, and I endorse it: the locked decision
governs the **runtime scoring path**, not how the lexicon was **authored**. The
sentence for the CEO to accept or reject:

> A local model may propose lexicon terms and outlet placements offline, which a
> human ratifies into a versioned file in the repo; the published score stays a
> deterministic rule over that file, and no model runs in the scoring path.

Accept and per-market lexicon work goes from ~40 hours of hand-curation per
market to a reviewable candidate list. Reject and the lexicons are hand-built,
slower but not blocked. The line not to cross either way is a model in the
runtime path: that ends the inspectable-rationale moat.

**(5) Place the 74 unplaced European and Latin American outlets?** The curator's
claim checks out exactly: 51 Western Europe/EU + 23 Latin America = **74**
unplaced, and `docs/OPEN-ITEMS.md`'s "234 of 287 are in countries where
left/right does not apply" overstates the case.

**Adjudication: the finding is right, the conclusion overreaches.** The unplaced
Western European rows include Bellingcat, OCCRP, Forbidden Stories, Investigate
Europe, AFP Fact Check and Politico Europe. Those are investigative consortia
and transnational desks; placing them on a left/right axis is the same category
error `unrated` exists to prevent. Corriere della Sera and Helsingin Sanomat are
straightforward. **The split between "genuinely placeable" and "wrong axis" is
itself the deliverable**, and OPEN-ITEMS needs its figure corrected either way.

**(6) Where does non-circular ground truth come from?** Unanimous on the trap:
fit anything to `political_lean_baseline` and you recover an **outlet
classifier** that learns boilerplate, datelines and byline conventions, scores
well, measures nothing, and then gets fed back into the baselines.

**Adjudication, and the best single idea the panel produced:** the
**Manifesto Project (MARPOR/CMP) RILE scores**, hand-coded left-right for ~1,000
parties across 50+ countries, plus party press feeds, give a per-country
reference corpus of known-ideology text *in the target language*. Run
Gentzkow-Shapiro chi-squared per market against it. That is the only legitimate
route to per-market lexicons and it is what properly retires the OPEN-ITEMS
block. Outlet labels may derive candidate features; they may **never** evaluate.

---

## 4. If a harvest follows: sample, do not sweep

Consensus across the legal and statistical angles.

- A per-outlet mean's error falls as 1/sqrt(n), so **300 to 500 articles per
  outlet stratified across 12 months** reaches a publishable interval for most
  outlets. That is roughly 400k articles worst case against 0.5M to 5M for a
  sweep, and it collapses every risk dimension at once.
- **The sampling frame is itself the credibility asset** that NewsGuard and
  AllSides actually sell.
- Route risk, best first: **GDELT** (metadata only, cannot feed the engine),
  **Common Crawl** (a third party already made the copy under a defined ToU; no
  publisher clickwrap, no CFAA surface), **Wayback/CDX** (weakened posture after
  *Hachette v. Internet Archive*, throttled), **Google News date-windowing**
  (opaque redirect tokens, ToS breach to resolve at scale), **publisher
  sitemaps plus direct fetch** (all risk lands on us; highest).
- **The binding scarcity is co-occurrence, not articles.** 11,377 of 12,823
  archive clusters are singletons, while live displayed clusters carry 20 to 61
  outlets. Much of that singleton mass is a clustering-recall artefact, and
  fixing recall buys more identified outlets per engineer-hour than crawling
  does.
- *AP v. Meltwater* supports us less than `IP-COMPLIANCE.md` assumes, in both
  directions: its holding was about a clipping service distributing verbatim
  excerpts as a substitute for reading AP copy. It neither condemns nor blesses
  ingestion for computation. The cases that do are *iParadigms*, *HathiTrust*
  and *Google Books*, and in all three **security of the retained corpus was a
  holding-level fact.** Separately, EU sui generis database right Art. 7(5)
  prohibits repeated systematic extraction of insubstantial parts, and fair use
  is no defence to it. UK s.29A is non-commercial research only.
- Exclude the 40 `type == "wire"` outlets **pre-fetch, at the roster**. Agency
  copy is the flattest text in the corpus and the most aggressively enforced.

---

## 5. Due inside 48 hours, independent of everything above

### 5.1 The served methodology claim (Rule 1)

`frontend/app/sources/SourcesClient.tsx:565-585` serves, verbatim:

> "Most bias tools assign one fixed score to an entire outlet, as if every
> article from it leaned the same way. Void News looks at two things instead..."

The copy describes the **architecture** accurately, and is admirably honest
elsewhere (it already says a short wire item "sits close to the record", and the
`not placed on this axis` paragraph is exemplary). The gap is disclosure, not
falsehood: measured, the second thing contributes **0.74 points** for rated
outlets, so for most of the roster the published number is operationally the
fixed per-outlet score the copy says other tools use. A reader finishes that
paragraph believing both inputs contribute materially. They do not.

**The fix is to publish the number, not soften the sentence.** "On the articles
where we could measure it, the words moved the score a mean of 1.93 points,
range -10 to +11.8." No competitor publishes its own instrument's resolution.
That converts the weakest fact in the product into the most trust-building
sentence on the site. Then extend `frontend/test/copy-facts.test.mjs` to assert
the stated magnitude against a number the export emits, on the pattern of the
existing stale-count check, or it drifts back within a month.

### 5.2 Verified defects found on the way, none of them part of the programme

| Defect | Evidence | Severity |
|---|---|---|
| **519,041 characters of publisher prose committed to git.** `grounding.py:31` sets `PER_ARTICLE_CHARS = 24_000`; `frontend/build-data/grounding/` holds 35 files, 975 records, longest 10,003 chars, committed 2026-09-21 and in history permanently. The daily pipeline truncates `full_text` to 300 chars at `main.py:4180` for exactly this reason, so the throwaway state DB is protected and the public repo leaks. | verified | **highest** |
| **robots.txt fails open.** `web_scraper.py:230-252` returns `True` on unreachable *and* on non-200, and checks `rp.can_fetch("*", url)`, so a site disallowing only named bots reads as open. A documented tradeoff at daily volume; a finding at harvest volume. | verified | high if harvesting |
| **Wire attribution matches 5 of 40 wire outlets.** `CANONICAL_WIRE_SLUGS` misses `dpa-international`, `kyodo-news`, `pti-india`, `anadolu-agency`, `tass-english` and 30 others through near-miss slugs. The `tier in ("wire","wire-service")` branch matches **zero** rows (`tier` only ever holds `independent`/`international`/`us_major`) and is dead code. Cheap fix: key on `type == "wire"` from the roster. | verified | medium |
| **186 default-tuple rows in the committed export, none marked `lean_unscored`, and the gate passes.** `tests/test_bias_defaults_gate.py` exempts itself when *no* row carries the key, which is indistinguishable from the marking having broken. | verified | medium |
| **The closed loop** in section 3(1). Latent, not yet biting. | verified | cut before any learned offset |
| **Google News text starvation.** Section 0. 540 outlets, 48,734 articles, median 11 words, 0.0% over 150. | verified | **highest, tied** |
| **`framing.py::_omission_score` is inert.** 39% of 975 values are exactly 40.0, every cluster under 10 outlets is 100% saturated at 40.0, and it correlates with cluster size at r = -0.375. The cross-article term is `(1 - entity_overlap) * 30` and one article never overlaps a 60-outlet entity set. It is 15% of the framing axis. | UNVERIFIED (specialist measurement) | medium |
| **The validation suite cannot distinguish the engine from a lookup table.** A baseline-only null model reportedly scores 42/43 against the suite's 43/43; the one fixture the text signal earns is `wsj-opinion-tax-2026`. Fixture count and tier mix confirmed (43; 25 us_major / 8 independent / 10 international) and **zero fixtures mention `unrated`**, so 28% of the roster has no regression guard. | claim UNVERIFIED (needs spaCy), fixture mix verified | **high** |
| **`is_wire_copy` flags 213 of 34,233 archive observations (0.6%)**, median per-story wire share 0.0%. Probably a dead detector, and it is what any "covered independently" claim would rest on. | UNVERIFIED (specialist measurement) | medium |

---

## 6. Other value from the same effort, ranked

The CEO asked what else the exercise pays for. Ranked by reader-visible value
over effort, and noting which survive an AUC kill in section 1.

1. **Measured coverage absence, and the data is already committed.**
   `frontend/build-data/archive.json` (21 MB, in the deploy tree) holds 1,597
   printed stories across 41 days, 644 distinct outlets, **34,233 outlet-story
   observations**, each carrying `source_name`, `tier`, `lean`, `rigor`,
   `confidence`, `url`, `published_at`. 88% of stories carry >= 5 lean-placed
   outlets. Counted: **38 right-blindspots and 29 left-blindspots in 41 days**
   (>= 3 outlets on one wing, zero on the other), about 1.6 per day. Enough for
   a daily rail, with no harvest and no new code.
   The credibility risk is fetch confounding: only ~248 of 1,016 outlets appear
   on a median day, so a full-roster blindspot would report RSS failures as
   editorial silence. The measured fix: **77 outlets appear on >= 90% of the 41
   days** (26 left, 18 centre, 21 right, 12 unplaced). Ship against a declared,
   named 77-outlet panel and it is defensible. Two specialists independently
   ranked this the highest value-per-effort item on the board, and it
   **survives the kill gate** because it needs no lexicon.
   Note the conflict to settle first: Ground News already does event-level
   coverage, so the event view is not the moat. The moat is that we measure the
   article's own text while they attach one borrowed outlet label. State it
   precisely or a reviewer will dismantle it.
   Prerequisite for anything longitudinal: `printed_stories` is 1,597 rows
   behind a 90-day artifact window with **no R2 sync**. Build a durable archive
   regardless.
2. **Clustering recall audit.** 88.7% singletons against live clusters of 20 to
   61 outlets is a measurable defect with a number attached. Fixing it improves
   the lean estimator, the Bench histogram and coverage absence at once. Fund
   before any crawl.
3. **Narrative drift over the life of one story.** Axis 6 is longitudinal and
   nothing reader-facing uses it. Showing how framing on one event moved over
   ten days across the same outlets is the only candidate that makes a returning
   visit strictly better than a first visit.
4. **Omission with a denominator.** `framing.py` already does cluster-aware
   omission detection with no base rate. Multi-outlet clusters give, per outlet,
   which consensus entities it systematically drops. A publishable "what this
   outlet leaves out" number.
5. **Propagation and lead time.** Cluster plus timestamp gives first-mover
   order and a breaks-versus-follows ratio. No lexicon, so it covers the
   unrated tail and singletons do not apply.
6. **Per-market derived phrase tables** (MARPOR + party feeds + chi-squared).
   Auditable, each term carrying its own frequency differential.
7. **Euphemism and attribution drift dating.** When an outlet switches
   militant to terrorist, protest to riot, said to claimed. Pure counting, and a
   natural standing Weekly department.
8. **Free rider:** the identical paired estimator runs on sensationalism and
   factual rigor with no extra data.
9. **Roster hygiene.** Per-outlet article counts and last-seen dates are the
   only real liveness signal we have (a Google News query returns valid XML
   forever, so the current health check cannot see a dead outlet). Plus
   duplicate-entity detection: six The Conversation rows, two AP, two Guardian,
   two DW.

---

## 7. Decisions the CEO owns

1. **Accept or reject the runtime-versus-authoring sentence** in section 3(4).
2. **Approve the 48-hour copy correction** and whether to publish the 1.93
   figure (recommended) or soften the claim (weaker).
3. **Fix the grounding leak** in 5.2 now, and decide whether git history needs
   rewriting or whether stopping the bleed is sufficient.
4. **Authorise the one-week pair test** with its AUC kill gate, before any
   crawl.
5. **Full-text retention:** re-deriving scores after a lexicon change requires
   retaining text, which is the exact risk `IP-COMPLIANCE.md` exists to
   eliminate. The alternative is that every lexicon improvement applies only
   going forward and history is never re-scored. This is a legal-exposure call,
   not an engineering one.

---

## 8. Panel roster

Eight angles: lexicon and measurement science; scoring-engine architecture;
harvest feasibility and cost; legal, IP and security; roster curation;
statistical estimation and validation; competitive and analytics; strategic
sequencing. Disagreements between them are adjudicated in section 3 rather than
averaged, per Rule 1's instruction to publish the disagreement.

Two specialist measurements could not be reproduced in this container and are
marked UNVERIFIED in 5.2. Re-running the validation suite's null model is the
highest-value verification outstanding, because if it holds, the suite's 100%
on lean has never tested the text signal at all.

## 9. Measured constants, for the docs pass

`_TEXT_AUTHORITY = 1.0`; `_TEXT_DELTA_MAX = 10` (rated), `_CENTER_TEXT_DELTA_MAX = 24`
(unrated), `_STATE_TEXT_DELTA_MAX = 8` (state-affiliated);
`_LENGTH_FULL_CONFIDENCE = 150`; ladder 10/20/35/50/65/80/90.

`CLAUDE.md`'s lean paragraph describes "~50/50 on a short wire item, ~90/10
text-weighted on a full article". With `_TEXT_DELTA_MAX = 10`, text can never
exceed 10% of the axis for a rated outlet, so that phrasing is wrong by
construction and not merely empirically. It should be replaced with the
anchor-and-modulate form the code implements and the served `/sources`
methodology copy already uses correctly. That is a one-paragraph Rule 1 fix in
our own instructions file, and it is the cheapest item on this list.
