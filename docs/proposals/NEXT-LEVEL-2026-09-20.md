# Void News: taking the product to the next level

Prepared 2026-09-20 against the live site (news.voidvision.org), the 09-20 feed
export, `docs/OPEN-ITEMS.md`, `docs/CHANGELOG.md`, the pipeline source, and a
benchmark of Ground News, AllSides v11 and Ad Fontes 2026. Nothing here adds an
LLM call, an account, a recommendation, or a paid tier. Every proposal is
deterministic, static-exportable, and stays inside the locked decisions.

---

## Context

Void's pitch is per-article, six-axis, inspectable bias measurement on a front
page that is the same for everyone. That is a real gap in the market: Ground
News and AllSides rate the *outlet*, not the article, and Ground News paywalls
factuality and ownership behind Vantage.

The problem is that the pitch is no longer visible on the page, and the data
under it is partly corrupt. Four findings drive this plan:

1. **A pipeline bug overwrites real bias scores with defaults.** Step 6b in
   `pipeline/main.py` (lines 2742-2807) re-scores framing for every article in
   a multi-article cluster and upserts a full row built from
   `article_bias_map.get(art_id, {})`. The 36-hour lookback articles (lines
   2495-2543) are never loaded into that map, so for each of them the upsert
   writes `political_lean=50, sensationalism=10, opinion_fact=25,
   factual_rigor=50, confidence=0.7` and a framing-only rationale, replacing
   yesterday's measured scores. Verified against the 09-20 export: of 737
   articles on the page, 106 carry a full rationale and **540 carry exactly the
   default tuple**. Every cluster mean, every "Flat" label, and every archived
   `members[].lean` is computed on top of this.
2. **The differentiator has gone silent.** On 09-09, 12 of 20 cards read
   "Flat". A cluster full of 50s has no margin, so finding 1 is a direct cause.
   Independently, "Flat" (we could not measure) and "Center" (we measured, it
   is balanced) look identical to a reader. The export already carries
   `lean_measured_count` / `lean_total_count` with a comment asking the UI to
   be honest; nothing renders it.
3. **The richest transparency UI is dead code.** `BiasInspector.tsx` (per-axis
   rationale + confidence badge), `SixLenses.tsx`, `ShareCard.tsx` and
   `lib/rankRationale.ts` have zero call sites since 2026-08-11. The ranker
   computes 16 named signals per story (`component_scores`) and `main.py:3017`
   keeps one. Matched keywords, clickbait signals, named-source counts, and
   the outlet-baseline vs. article-words split are all computed and thrown
   away or never shown.
4. **A reader has nowhere to go after card 20.** 1,577 stories across 40
   editions are prerendered at `/story/[id]`, but there is no edition index, no
   date browsing, no news RSS, and Cmd-K searches only the 20 stories in
   memory. Every shared story link carries the same generic image.

The thesis: **Void does not need new mechanisms. It needs receipts.** Fix the
data, surface what the engine already produces, make every label honest about
its own confidence, and let the reader verify "same front page for everyone"
by opening yesterday's.

---

## Benchmark

| Capability | Void today | Ground News | AllSides | Ad Fontes | Void after this plan |
|---|---|---|---|---|---|
| Unit of bias rating | Article (5 axes) + outlet baseline | Outlet, averaged from 3 raters | Outlet, survey + editorial panel | Article sample per outlet, 3-analyst pods | Article, with the baseline/text split shown per source |
| Per-story coverage split (L/C/R) | Computed, hidden behind hover | Bias Bar on every story, free | Balanced headline roundups | No | Three-segment bar on every card, honest about measured/total |
| Coverage gaps ("blindspot") | Data exists in archive `members[]`, no UI | Blindspot feed, 6/day free, unlimited paid | No | No | "Who covered it" on every Deep Dive, free, deterministic |
| Why a story ranks where it does | 16 signals computed, discarded | Not exposed | Not exposed | Not exposed | "Why it is here" line on every Deep Dive. Nobody else has this |
| Per-axis evidence (matched terms, counts) | Computed, dead UI, 14% export coverage | No (metadata only) | No | Analyst notes, paid | Evidence layer under The Spread, 100% coverage |
| Confidence shown to reader | Never | No | No | Reliability axis | Three-state badge + "measured from N of M articles" |
| Ownership / state affiliation | `state_affiliated` scored, never shown; ownership only in prose | Paid (Vantage), 8 categories | No | No | State-affiliation mark; structured ownership field |
| Published accuracy of the method | 42 fixtures, 215 checks, in a doc nobody sees | No | No | Analyst agreement stats | Public track-record page, regenerated every run |
| Archive / edition browsing | None | Yes | Yes | No | `/archive` + `/archive/[date]` + story threads |
| RSS | Podcast only | Yes | Yes | No | News RSS 2.0 + JSON Feed |
| Personalization | None (locked) | Core to product | Some | No | None |
| Price | Free | Freemium, $5/mo+ | Ads | B2B | Free |

Sources fetched 2026-09-20: Ground News rating-system and blindspot pages,
AllSides v11 chart, Ad Fontes 2026 edition, s2n.news 2026 comparison. The
critique both incumbents face, "an outlet's label is fixed; its framing
changes story to story", is exactly the gap Void's per-article engine fills,
and exactly what the page currently fails to show.

---

## Prioritization

Scored with the repo's own formula (`.claude/agents/ceo-advisor.md`): trust
30%, habit 25%, differentiation 25%, feasibility 20%. Tier order is the build
order. Each tier ships on its own `claude/*` branch, green on
`verify_production.py`, with a pipeline run between Tier 0 and Tier 1 so the
data fix is proven on production before anything is built on it.

### Tier 0. Truth fixes (3-4 days). The page must not contradict itself.

| # | Item | Evidence |
|---|---|---|
| 0.1 | **Fix the step-6b overwrite.** Preload `bias_scores` for lookback ids; never write a defaults row | Finding 1. Everything in Tier 1 is worthless on 50/10/25/50 data |
| 0.2 | `/about` says "50 stories" in three places; locked decision is 20 | `AboutFaq.tsx:18`, `AboutPipeline.tsx:9,41`. `config/feed.json` is the source of truth |
| 0.3 | Lean gate honesty: three distinct states (Not measured / Balanced / directional) + "lean measured from N of M articles" | OPEN-ITEMS "differentiator going silent". CEO decision points isolated in one constants block |
| 0.4 | The Sigil obeys its caption (rule F-03) | Open defect: paints direction on cards captioned "Flat" |
| 0.5 | Mobile first paint shows the desktop card variant | Known one-frame flash; render both, choose in CSS |
| 0.6 | Sources page: legend for tier stamps, "last reviewed" date, state-affiliation mark | Live fetch 09-20 found none of the three |

### Tier 1. Receipts (2-3 weeks). The differentiator, made visible.

| # | Item | Why it matters |
|---|---|---|
| 1.1 | **Coverage bar on every card.** L/C/R from `lean_buckets`, hatched segment for unmeasured. Quiet, 3 px, on every card (the predecessor was removed because it appeared only on some) | Ground News' most-used surface, free here, and honest about what it could not measure. Needs CEO sign-off since the CEO removed `LeanCoverageBar` |
| 1.2 | **Evidence layer.** Trimmed panel under The Spread: per-axis one-line rationale, matched terms, confidence badge | Turns "rule-based NLP" from a claim into something a Skeptic checks in ten seconds |
| 1.3 | **Both, shown.** Per source: "Fox News: outlet 80, these words 62" from `rationale.lean.source_baseline / text_score / text_shift` | The locked rule ("weighs BOTH outlet and text") gets its public proof |
| 1.4 | **Who covered it.** Deep Dive block listing outlets by lean; "No outlet from the right in our 1,016 ran it" when a bucket is zero | Void's coverage-gap feature, named differently from Blindspot on purpose (`docs/IP-COMPLIANCE.md`) |
| 1.5 | **Why it is here.** Persist `component_scores` + feed-ranker reorder moves; one numbers-only line per Deep Dive | The non-algorithmic claim becomes inspectable. No competitor shows this |

### Tier 2. Findability and habit (2 weeks)

| # | Item | Why |
|---|---|---|
| 2.1 | `/archive` edition index + `/archive/[date]`; "Previous edition, Sep 19" link under card 20 | 40 editions prerendered as stories, zero navigation. Also how a reader verifies "same page for everyone" |
| 2.2 | Story threads: "Day 3 of this story" with prev/next on Deep Dive, from `story_thread_id` | Continuity is what a daily edition sells that a feed cannot |
| 2.3 | Archive search index; Cmd-K searches 1,577 stories, not 20 | `title_keywords` and `search_terms` already exported |
| 2.4 | News RSS 2.0 + JSON Feed | The non-algorithmic audience is the RSS audience |
| 2.5 | Per-story OG image with coverage bar and source count, last 7 editions | Every share today carries a generic image. The growth loop for a product with no ads |
| 2.6 | Edition framing: "Edition No. N, printed 11:00 UTC" in the dateline | Makes the 1×/day cadence a feature, not a limitation |

### Tier 3. Public accountability (1-2 weeks)

| # | Item | Why |
|---|---|---|
| 3.1 | Track-record page: validation results (42 fixtures, 215 checks, pass rate), editorial validator pass rates per run, sources by lean, regenerated into `public/data/track-record.json` | Neither incumbent can publish a reproducible accuracy figure. Void can, every day |
| 3.2 | Corrections log: `corrections.json` writer + `/corrections` page | Newspaper principle. Weekly has one; the daily does not |
| 3.3 | Structured `ownership` field in `data/sources.json` (Ground News' 8 categories as the starting taxonomy), shown on `/sources` and Deep Dive rows | Currently prose in `credibility_notes`. Ground News charges for this |
| 3.4 | `claim_consensus`: null on all 35 clusters despite 606 lines of extractor. Ship "Agreed by 40 of 72 sources" per claim, or delete the code | Do not keep a column that promises and never delivers |

### Tier 4. Surface restoration (opportunistic)

- **Games** (Frame, Wire): dramatize the bias thesis, no known defect. Restore
  behind a nav item after an a11y pass.
- **Paper**: cheapest restore, pure presentation over the feed; collapse the
  stale `[edition]` route first.
- **Revolt**: blocked on static JSON and entangled with the unexecuted
  `/archive` merge decision. Defer until Tier 2.1 defines what `/archive` is.

### Polish (fold into whichever tier touches the file)

- Wordmark DOM text reads "V ID NEWS" (the Sigil is the O); `role=img` +
  `aria-label` covers screen readers, but crawlers index "VIDNEWS". Add a
  hidden text node.
- "Progressive" tag on the Brief's opinion has no explanation on hover.
- Feedback form error messaging; weekly heading level.
- Lighthouse last point to 90; CSP `unsafe-inline`; `IP_SALT` real secret.

---

## Measuring it without tracking anyone

1. **On-page truth metrics**, computed by the pipeline and asserted by
   `verify_production.py`: share of exported articles with a full rationale
   (today 14%, target 100%); share of cards with a directional or Balanced
   label (today ~40%, target above 60%); share of Deep Dives with a receipt
   line (target 100%).
2. **Cloudflare Web Analytics** (cookieless, no PII). The CSP in
   `frontend/public/_headers` already allows `static.cloudflareinsights.com`,
   so this is a Pages dashboard toggle, not code. Watch: returning-visitor
   share, `/story/*` share of entries, `/archive` depth, RSS fetches,
   feedback submissions per week.

---

## Design (file-level)

### 0.1 Fix the step-6b overwrite
- `pipeline/main.py`: factor the chunked `bias_scores` load at 2008-2024 into
  `_load_bias_rows(ids) -> dict`; call it for `recent_articles` ids after line
  2543 and merge into `article_bias_map`; in 6b (line 2770) `continue` when
  `art_id not in article_bias_map` so a defaults row can never be written.
- Test: `tests/build_test_db.py` gains a second-run fixture;
  `tests/test_editorial_stage.py` asserts every exported article with
  `word_count >= 150` carries all five rationale keys.
- Gate: `verify_sections.py` E-01 fetches `/data/deepdive/<lead id>.json` and
  asserts at least 80% of articles carry `rationale.lean`.
- Note in `docs/CHANGELOG.md` that labels will shift on the first run after
  the fix, because cluster means stop averaging fake 50s.

### Was the overwrite an intentional damper?

The question was raised, and it is the right question to ask before touching
scoring. The answer from the code and the data is no.

- **The comment states a different purpose.** Lines 2767-2769 say the row
  includes all axes so a partial upsert does not null out columns ("Fix F7").
  The 50/10/25/50/0.7 values are the `.get()` fallbacks, copied from the
  analyzer's own initial defaults at lines 348-353. Nothing names damping.
- **The pipeline already has a deliberate fallback, and it looks nothing like
  this.** The word-count gate (lines 359-378) writes the outlet baseline lean
  (10 for Jacobin, 80 for Fox), confidence `max(0.15, words/500)`, and sets
  `lean_unscored` so the row is excluded from the cluster lean. Its comment
  warns that a compressed baseline "quietly reintroduced the same pull to the
  middle the deviation model removed" and that a false center "must not be
  averaged into the cluster lean as measured centrism". The 6b row writes 50
  regardless of outlet, confidence 0.7, and leaves `lean_unscored` untouched,
  so it is averaged in as measured centrism.
- **The defaults get more weight, not less.** Across the 106 real rows on the
  09-20 page the median confidence is 0.67 and 56% sit below 0.7. In the
  confidence-weighted mean a defaulted row therefore outweighs most measured
  rows. A damper designed to reduce outlier influence would carry low
  confidence.
- **The recorded history of the engine is a fight against compression, not
  outliers.** Rev 49 added perceptual expansion because top stories "bunch at
  center". The sensationalism curve was re-inflected because production
  medians were "compressed away from the target mean". The linguist brief
  asks for lexicon changes that "improve distribution SPREAD". Real rows on
  09-20 show lean mean 46.6, standard deviation 19.6, with 15 of 106 beyond
  20 or 80: a spread, not an outlier problem.

If outlier damping is wanted as policy, the honest mechanism already exists
and should be tuned instead: the rigor- and confidence-weighted cluster mean,
the lean-spread damping in `compute_aggregate_confidence`, the word-count gate,
and optionally a documented shrinkage of low-confidence articles toward their
outlet baseline. All of those keep the per-article record intact, which the
Deep Dive and the charter promise. A silent overwrite of stored scores does
not.

### 0.3 / 0.4 Lean gate honesty and F-03
- `frontend/app/lib/biasColors.ts`: one exported `LEAN_GATE` constants block
  (`MIN_MEASURED`, `MIN_MEASURED_SHARE` new, `MIN_CONFIDENCE`,
  `MEANINGFUL_MARGIN`, `SHARE_TILT_DENOMINATOR: "wings" | "all"`) so the CEO
  reviews a single block. `LeanLabelState` becomes `not-measured | balanced |
  contested | confident`. Delete `NO_CLEAR_LEAN_LABEL = "Flat"`.
- `BiasSnapshot.tsx` and the Sigil popup render "lean measured from
  {leanMeasuredCount} of {leanTotalCount} articles" (article counts, so the
  copy says articles). `LeanLabelLegend.tsx`: replace the Flat row with Not
  measured and Balanced.
- `Sigil.tsx`: pass `info.state` into `DataMark` (line 99) instead of letting
  it derive its own beam angle; not-measured → level, grey, no fan.
- Test: extend `frontend/test/labels.test.mjs` with a sweep of lean 0..100 ×
  measured share, exactly one state each. Gate: `verify_production.py`
  `check_lean_vocabulary` (every Sigil aria-label in the allowed set, "Flat"
  never appears).

### 1.1 / 1.4 Coverage bar and Who covered it
- New `CoverageBar.tsx` (do not resurrect `LeanCoverageBar`, which gates on
  both wings; delete it). Input: collapsed `lean_buckets` + unmeasured
  remainder; `aria-label="12 left, 78 center, 5 right of 112 articles; 17 not
  measured"`, `data-lean-measured="95/112"`. Mount under the summary in
  `StoryCard`, `LeadStory`, `MobileStoryCard`.
- New `WhoCoveredIt.tsx` under The Spread: three columns from `members[]`
  (standalone) or the deepdive roster (inline); a fourth "Not measured" list
  from `lean_unscored`, which `export_static.py` (~344) and
  `print_archive._build_members_by_cluster` (~134) must add to their selects.
  `SOURCE_TOTAL = 1016` moves to `siteMeta.ts` (hard-coded in four files).
- Gate: `check_coverage_totals` (every card has `data-lean-measured`, n ≤ m).

### 1.2 / 1.3 Evidence layer
- `print_archive._build_members_by_cluster` copies a trimmed `evidence` object
  per member: `{baseline, text, shift, left[:3], right[:3], rigor_named,
  sense[:2]}` from the keys in `pipeline/analyzers/political_lean.py`
  1073-1083 (~200 B × 60 members; `archive.json` is build-only).
- New `EvidencePanel.tsx` (~150 lines) lifting `AxisRow` (BiasInspector
  285-400) and `ConfidenceBadge` (699-745); then delete `BiasInspector.tsx`,
  `SixLenses.tsx`, `ShareCard.tsx`, `rankRationale.ts`. Two blocks: per-axis
  one-liners from the cluster-average rationale `InlineDeepDive` already maps
  (200-260), and "Outlet vs. words" sorted by `|text_shift|`.

### 1.5 Rank receipts
- `main.py:3016`: keep the whole `component_scores` dict as
  `cluster["rank_components"]`. `feed_ranker.apply_feed_ordering`: a
  `_note(c, pass, from, to)` helper at each mutation site (opinion gate,
  same-event decay, near-dup, event cap, lead clamp, diversity deferrals, cap
  correction, breadth promote, mass-casualty floor). Persist from
  `stage2.order_feed` (295-366), which is the pass the reader sees, not the
  earlier call at `main.py:3181`.
- Column `rank_receipt TEXT` on `story_clusters` and `printed_stories`, in
  BOTH `migration/schema_pipeline.sql` and `_ADDITIVE_COLUMNS` in
  `pipeline/utils/supabase_client.py` (39-75). `_prepare_row_for_write` in
  `pgrest_sqlite.py:671` raises on an unknown column and `_batch_upsert`
  swallows it, so missing one edit silently drops every cluster chunk. Test in
  `pipeline/utils/test_pgrest_sqlite.py`.
- `export_static.py` `FEED_COLS` + archive pjson; `types.ts` `RankReceipt`;
  `feedMapping.ts`, `archive.ts` pass-through. New `RankReceipt.tsx`, numbers
  only: "72 sources across 3 tiers. 5 new articles in the last 6 hours. Held
  to slot 3 by the two-per-event cap." Mounted after `deep-dive-meta` in both
  Deep Dives. Gate: R-01 in `verify_sections.py`.

### 2.1-2.3 Archive, threads, search
- `export_static.py` emits `build-data/editions.json` and
  `public/data/search-index.json` (`{id, t, d, c, s}`, 90 editions, ~70 KB
  gzip). `app/archive/page.tsx` + `app/archive/[date]/page.tsx`, both
  `force-static`, `dynamicParams=false`, copying `weekly/archive` and
  `weekly/[week]`. ~41 extra pages, under 30 s build. Sitemap entries.
- "Previous edition, Sep 19" at the `edition-line` in `HomeContent.tsx`
  (~977), date from `editions.json` at build (no `Date.now` in render; do not
  say "Yesterday" because editions have gaps). Older editions carry 50 rows;
  show each row's own count.
- `archive.ts`: memoized `Map<story_thread_id, rows[]>`; `getThread(id)` feeds
  "Day 3 of this story" in `StandaloneDeepDive`.
- `SearchOverlay.tsx` lazy-loads the index on open via `fetchSearchIndex()` in
  `lib/supabase.ts`; `search_terms` are stems, match by prefix both ways.

### 2.4 / 2.5 Distribution
- New `pipeline/briefing/news_feed_generator.py` reusing `_rfc2822`,
  `SITE_URL` and the ElementTree style of `podcast_feed_generator.py`. Items =
  latest edition's `printed_stories`; description = summary plus numbers only,
  never a lean label (the ladder lives in TypeScript). Writes
  `frontend/public/feed.xml` and `frontend/public/feed.json`; add both to the
  `git add` line (`pipeline.yml:184`) and `resolve_generated` (215).
  `alternates.types` in `app/layout.tsx`.
- `app/story/[id]/opengraph-image.tsx` copying `weekly/[week]/opengraph-image.tsx`
  exactly; `OG_EDITIONS = 7` (~140 renders); `generateMetadata` drops the
  static `OG_IMAGE` only for rows in that window. Extend `sectionCard` in
  `lib/ogCard.tsx` with a `bar` and a `meta` line; cache the `displayFont`
  fetch at module level.

### 3.1 Track record
- `pipeline/validation/runner.py` already emits `accuracy_pct` and per-axis
  breakdown; a new export step writes it with `pipeline_runs.llm_metrics.editorial`
  and the sources-by-lean counts into `public/data/track-record.json`.
  Page at `/sources#track-record` reading it client-side like the
  methodology samples.

---

## Verification

1. **Tier 0 data fix:** run `tests/build_test_db.py` twice, then
   `tests/test_editorial_stage.py`; assert zero exported rows with the default
   tuple. After the next production run, `python3 -c` over
   `public/data/deepdive/*.json` must report full-rationale share above 80%.
2. **Frontend:** `npm test` (labels, coverage), `npm run build` static export
   succeeds, `frontend/uat-mobile.mjs` for layout and a11y heuristics.
3. **Served page:** `scripts/verify_production.py` and `verify_sections.py`
   with the new checks (E-01/02, `check_lean_vocabulary`,
   `check_coverage_totals`, R-01, C-01, A-01..03, D-01..04) green against the
   live site after deploy.
4. **Editorial rules:** grep every new copy string for em dashes and the banned
   words before commit.
5. **Docs:** `docs/CHANGELOG.md` rev entry per tier; discharge the matching
   `docs/OPEN-ITEMS.md` entries; `CLAUDE.md` section-state table updated.

## Effort

Roughly 16 engineer-days for Tiers 0-2 (data fix 1, lean gate 2, coverage 2,
evidence 3, receipts 3, archive 3, distribution 2), one pipeline run between
Tier 0 and Tier 1, and CEO sign-off on the `LEAN_GATE` constants and the card
coverage bar before Tier 1 starts. Tier 3 is another 5-7 days.

## Sources

- Ground News rating system: https://ground.news/rating-system
- Ground News blindspot: https://ground.news/blindspot
- AllSides media bias chart (v11): https://www.allsides.com/media-bias/media-bias-chart
- AllSides vs Ad Fontes 2026 comparison: https://s2n.news/blog/allsides-vs-ad-fontes-2026-media-bias-chart-comparison
- Ground News review, September 2026: https://www.stationx.net/ground-news-review/
- Live site read on 2026-09-20: https://news.voidvision.org, /sources, /about
- Repo evidence: `pipeline/main.py` 2495-2543 and 2742-2807, `frontend/public/data/deepdive/*.json` (09-20 export), `docs/OPEN-ITEMS.md`, `docs/CHANGELOG.md`, `.claude/agents/ceo-advisor.md`, `docs/IP-COMPLIANCE.md`
