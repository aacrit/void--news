# Void: third-party product and brand audit

Prepared 2026-09-21 against the live site (news.voidvision.org), the repository at commit `6c40f57`, and a local render of the same commit at 1440px and 390px. Read-only: nothing in the product was changed by this audit. Every finding carries a root cause, a source with line numbers, and a fix. Appendices A to F hold the evidence in full; this document is the argument.

The brief was: does the brand have the voice it claims, is every word driven by facts, does everything everywhere look and behave the same, does a reader arriving from Instagram get where they were sent and onward from there, can Paper come back, and where is the bloat. The answer to each is below, followed by one strategy that resolves them together.

---

## 0. Outcome, same day

The CEO answered the six questions in section 10 (sections with named programmes; fix step 6b; hide `/pipeline`; the banner from the second visit, below the masthead; Paper as the printable twenty; three lean states everywhere) and asked for everything but the Instagram automation to be built. It was, the same day, by eight agents in isolated worktrees merged behind the gates: items 1 to 8, 10 to 17, 19 to 23 of the backlog in section 9 are shipped; item 9 (the Instagram pipeline) is excluded by decision; item 11 (the token collapse) and item 18 (the dead-CSS purge and the DESIGN-SYSTEM rewrite) remain open. The record is `docs/CHANGELOG.md` rev 75; what is still open is in `docs/OPEN-ITEMS.md`. Two corrections to this report were found while building: `motion` is live (Appendix B, B-04 is corrected in place), and gate IDs R-12, R-13 and W-09 were already taken, so the new gates are R-14, R-15, W-10 and PR-01.

---

## 1. The verdict in five sentences

Void has one product idea worth protecting and eight surfaces that each present it differently. The editorial voice is real where the rules reach it (the feed, On Air, History, the promos, About) and absent where they do not (Weekly prose and the daily Opinion, which carry 34 kill-list words between them, no grounding line, and today assert facts from model memory), so the product currently speaks as two newsrooms. Underneath both, 73% of the per-article bias rows behind today's Deep Dives are the engine's default tuple, so the product's central claim rests on numbers that were never measured. History, Weekly, On Air and Paper were each built as a separate product under the old `void --x` model and the 2026-08-03 rebrand renamed the words without touching the architecture, which is why there are three mastheads, four token systems, twenty easing curves, six identity marks and no path from History to any sibling. The Instagram funnel cannot currently produce a post, and if it could, no post would link to the thing it advertised. None of this needs new mechanisms; it needs one system, applied everywhere, and gates that make the drift structurally impossible.

---

## 2. What is working, so it is not broken while fixing the rest

- **The voice on the page, where the rules reach.** Feed, Brief, On Air, History copy and scripts, the promos and About read as one newsroom: concrete, attributed, short, arriving late. The dash ban holds on every served route but `/sources` (one instance). The Hearing dek "A subcontinent torn along lines drawn by a man who had never been there" is exactly the house register. The "both outlet and text" ordering passes on `/about`, `/sources#methodology` and `/press`.
- **The controls that exist.** `standard.py` validators, `verify_production.py` on the front page, H-01 to H-11 on History scripts, the house-promo tests, and the nine gates the other session wired into CI on 2026-09-21. The instinct to make every production error structurally impossible is the right one.
- **The floating player.** One component, skinned per section by swapping one accent variable (`.fp--weekly`, `.fp--history`). This is the pattern the rest of the product should copy.
- **The About hero and the press callout** lead with "both the outlet's track record and the article's own words", as the rule requires.
- **The IG carousel system** shares one canvas, one Sigil and one slide grammar across all three families.

---

## 3. Facts and only facts: where the claim is not yet true

Rule 1 says nothing Void publishes may contain a factual error. These are the places the served product currently fails it, ranked by how much rests on them.

| # | Finding | Root cause | Proof | Fix |
|---|---|---|---|---|
| F-1 | **540 of 737 per-article bias rows behind today's Deep Dives are the default tuple (50, 10, 25, 50, 0.7).** Every cluster mean, every "Flat" caption and every archived lean is computed on top of this. | Step 6b in `pipeline/main.py` upserts a full row from `article_bias_map.get(id, {})`; the 36-hour lookback articles are never loaded into that map, so their measured scores are overwritten with defaults. Documented in `docs/proposals/NEXT-LEVEL-2026-09-20.md` finding 1 and parked in `docs/OPEN-ITEMS.md` as blocked on a CEO decision. | Appendix F, counted on `frontend/public/data/deepdive/*.json` today. | Take the decision. Preload `bias_scores` for the lookback window into the map and never write a defaults row. Then add a served-output check: fail the run when more than N% of exported rows equal the default tuple. |
| F-2 | **The one podcast cover for all three shows reads `void --onair`, `WORLD BRIEF`, `409 sources`.** Three stale facts on the artwork that would front Apple and Spotify. | `podcast_feed_generator.py:192-198` falls back to `podcast-cover-world.jpg` for every feed; the raster was rendered before the rebrand and never re-rendered; `podcast-cover-weekly.jpg` and `-history.jpg` return 404 live. | Appendix E, E-16; the JPG was viewed. | Render the three covers from one composer in CI; add a check that no shipped raster or XML carries `--`, an edition name, or a source count other than the live one. Do not submit the feeds until this passes. |
| F-3 | **The press kit's "approved language, copy it as written" says fifty stories.** The feed has been twenty since 2026-09-07. | `press/page.tsx:20` (`BOILER_LONG`), `:80-81` (`50 / Stories in one daily edition`), `:128-129` were hand-typed; only `BOILER_SHORT` reads `FEED_DISPLAYED`. The gate meant to catch this, `frontend/test/copy-facts.test.mjs`, matches `50 stories` and `top 50` and so misses `50</div>` and "fifty most important stories"; commit `cc49187` reported "all ten now derive from the config" without reading the page back. | Appendix C, F-01 and Appendix E, E-13; verified by grep at HEAD. | Interpolate `FEED_DISPLAYED` with a number-word helper; widen the regex; fetch `/press/` in `verify_sections.py`. |
| F-4 | **The On Air masthead labels the current clock "as of".** On `/onair` at 02:10 UTC the masthead read "Sep 21, 2026 · as of 2:00 AM UTC" above a card dated September 20. The home masthead for the same edition read "Sep 20 · as of 8:00 PM UTC". | `NavBar.tsx:60` falls back to `getEditionDatelineUTC(null)` = now; `OnAirPage.tsx:96` passes a client-fetched `editionBuiltAt` that starts null, while `HomeContent.tsx:798-799` passes the prerendered build time. | Appendix F, local render. | Pass `editionDateline` and `editionBuiltAt` from the server on every route that mounts `NavBar`; render nothing rather than "now" when the build time is unknown. |
| F-5 | **The IG caption prompt tells Gemini "the same 50 stories, in the same order".** | `ig_caption.py:100` predates rev 64. | Appendix E, E-03. | Interpolate `feed.json`, as `tests/test_house_promos.py` already ties "twenty" to a constant. |
| F-6 | **Paper's copy, if un-hidden as is:** category-to-city datelines (a Ukraine story datelined BEIRUT), "200 curated news organisations", "twice daily", a weather joke, an issue number counted from an arbitrary epoch. | Paper's data layer and copy were last touched at rev 47 (2026-06-11) and never re-audited. | Appendix D. | The Rule 1 copy pass in Appendix D step 3, before any redirect flip. |
| F-7 | **"Flat" and "Center" look identical to a reader**, and the Sigil paints a direction on cards whose caption says Flat; on phones the caption is absent entirely. | Documented in `docs/OPEN-ITEMS.md` ("The Sigil disagrees with its own caption"); the suppression gate and the mark were built separately. Compounded by F-1: a cluster full of 50s has no margin. | Appendix F (home render: six sigils, six "Flat"). | Decide the three-state label (measured-and-balanced / measured-and-tilted / not measured) and render it once, from `storyLeanLabel`, on every surface including the phone card. |
| F-8 | **Four History episodes serve audio that contradicts their corrected scripts**, and two more present secondhand remarks as verbatim speech. | Scripts corrected 2026-09-20, renders not re-run; `tests/test_history_audio.py` is red by design until they are. | `docs/OPEN-ITEMS.md`, other session's entry. | A render, not a rewrite. Already queued by the other session. |
| F-9 | **Today's Opinion asserts facts that are in no source.** "It tells autocrats in Beijing, Moscow, and Riyadh…" and "We have seen this pattern before. Governments that seek to consolidate power invariably begin by controlling the flow of information." Neither the three capitals nor the generalisation is in the 112-article cluster. | The Opinion prompt (`daily_brief_generator.py:1283, 1388`) carries no grounding line; nine production prompts do not (only 2 carry the exact CLAUDE.md sentence, 3 an equivalent). The line was added to the prompts that write news and never to the ones that write argument. | Appendix C, F-04, count table 1d. | Add the grounding sentence to all nine, plus for opinion: "Historical parallels, other countries and 'patterns' are not permitted unless a provided article states them." A five-line `tests/test_prompt_grounding.py` asserts it. Run E-13 and a proper-noun check on Opinion and Weekly editorial after generation. |
| F-10 | **On Air restates an ambassador's legal argument as Void's own statement of law.** The summary says Waltz argues the court protected the right to publish, not access; the rundown says "Ambassador Waltz argues the Supreme Court has protected such actions", then, unattributed, "The Supreme Court has previously protected the government's right to limit access to facilities." | R-01..R-11 are shape rules; nothing compares a rundown claim to the summary it was cut from. R-02 (no quotation marks read aloud) is advisory and fired without effect. | Appendix C, F-02, quoted from `brief.json`. | R-12 grounded attribution (object clause must overlap the cluster summary), R-13 no unattributed legal or causal assertion, R-02 promoted to hard fail. Planted-defect test using this exact pair. |
| F-11 | **The History YAML carries 81 time-relative claims**, including the rule's own example: "Sixty-five years on" (`cuban-revolution.yaml`), "remains largely uninhabited in 2026" (`chernobyl-disaster.yaml`), "leads French elections in the 2020s" (`algerian-war.yaml`). Twenty-one are in `summary`, which is rendered and feeds the podcast descriptions. | `test_history_copy.py` gates dashes and speaker shape; `test_history_data.py` gates identity and lifespans; neither has a time-relative check. | Appendix C, F-05. | One regex gate in `test_history_copy.py`, then 81 rewrites to dated forms. |
| F-12 | **The privacy page describes a retention job that runs against a database nothing reads.** "Removed by the daily cleanup job" refers to `db-cleanup.yml`, which prunes the decommissioned Supabase; live text lives in `pipeline_state.db` and a 90-day artifact. | Page dated 2026-08-08, three weeks before the decommission; no test reads it. | Appendix C, F-07. | Rewrite the sentence; tie the retention number to `pipeline/main.py` and `pipeline.yml` in `tests/test_docs_facts.py`. |

Where the zero-factual-error rule is **unenforced by any gate** today: the Weekly prose, the daily Opinion, all audio scripts (claim versus summary), the About, Press and Privacy pages, `/pipeline`, the podcast XML and cover art, the History landing (`verify_production.py` has no History checks), frontend string literals and aria-labels, and Paper. Appendix C section 6 tabulates what exists against what does not. Section 8 puts a gate on each.

---

## 3b. Voice: does the brand sound the way it says it does

The voice bible is `docs/VOICE-BRAND.md`. It is titled `void --onair`, dated 2026-04-28, describes six Gemini-TTS hosts on a four-runs-a-day, three-edition schedule that has not existed since June, claims six quality gates of which two exist, and uses the em dash 59 times while banning it. A live prompt still obeys it: the Opinion prompt (`daily_brief_generator.py:1336-1337`) tells Gemini to write as "the Investigator, the Editor, the Realist". Twenty-five production prompt strings still address the model as `void --news`, `void --weekly`, `void --history`. The real rules now live in three other documents the bible does not point to.

Measured against the kill list, surface by surface (Appendix C, table 1a):

| Surface | Kill-list hits | Hedges | Verdict |
|---|---|---|---|
| Feed top-20 (137 fields) | 1 | 6 | Clean, wire-flat: no arrive-late craft, which the summary prompt does not ask for |
| Brief, written | 0 (one near-miss: "sends a clear signal") | 0 | Same voice as the feed |
| Daily Opinion | 0 today, by luck | | Second house: abstract, adjectival, ungrounded (F-9) |
| On Air rundown | 1 ("significant escalation") | 0 | Distinctive and disciplined, closest to the wire voice |
| Weekly, two issues (104 fields) | **34** (`underscore` ×15, `significant` ×7, `robust` ×6, `navigate` ×4, `nuanced`, `a testament to`) | **38** | Second house: 41-word sentences, nominalisations, self-reference to "57 sources" |
| History events (6,150 fields) | 8 | 138 | The brand as written in CLAUDE.md; hedges are mostly legitimate ranges |
| History scripts, promos, About | 0-2 | | On brand |

The register comparison in Appendix C section 4 shows the split is not taste. The seven surfaces that sound like one newsroom are the ones whose prompts carry the grounding line and whose output passes through `sanitize_editorial_text`. The two that do not are the two that skip both. Root cause for Weekly specifically: `weekly_parse.py:171-181` knows 22 prohibited terms and none of the AI-slop set (27 of the 34 hits are words it cannot see), and `weekly_digest_generator.py:214-252` regenerates once on findings and then ships whichever attempt is better, which is right for length and wrong for a banned word. Fix: one shared kill regex in `prohibited_terms.py` serving feed, weekly, podcast XML and promos; a section that still fails on a verb or noun term after one regeneration is dropped rather than shipped; W-09 on the served page.

Three smaller voice leaks on the page itself: em dashes render in six History era ranges and four aria-labels (`HistoryLanding.tsx:34-64`, `EventCard.tsx:24`); three live components say "significantly" or "notably" (`Sigil.tsx:624`, `DivergenceAlerts.tsx:78`, `BiasInspector.tsx:562`); and there is no branded 404. Each gets a source-level scan in `copy-facts.test.mjs`.

---

## 4. Consistency: one product or eight

The user's question was whether History, Weekly and the rest belong to one system. They do not yet. The evidence is structural, not aesthetic.

### 4.1 Three mastheads, four token systems, twenty easings

| Layer | Feed | History | Weekly | Paper (hidden) |
|---|---|---|---|---|
| Masthead | `NavBar` 53px, opaque, z 20 | `HistoryTopbar` 56px, blurred, z 50, no destinations | `.wk-topbar` 48px, blurred, z 50, no destinations | none |
| Footer | `Footer` (9 links) | `HistoryFooter` (1 link) | `Footer` | colophon link |
| Tokens | `tokens.css` | 102 own (`--hist-*`), incl. a second full dark palette | 30 own (`--wk-*`) | 21 own (`--np-*`), two undefined font vars |
| Grain / vignette | one recipe | two recipes of its own | one of its own | textures removed |
| Reveal | 260ms | 300ms | 700ms | |
| Scroll physics | CSS scroll-driven | JS wheel hijack with friction loop and snap | IntersectionObservers | |
| Fonts loaded | 4 | 4 (+5 rules naming fonts that are not loaded) | 4 | 2 ghost families |

Root cause, in one line from the code: `history.css:5` "All classes scoped to .hist-page namespace." Each section was authored by a separate workflow that scoped itself to avoid collisions rather than extend the base; rev 60 kept them as separable, hideable products; rev 69 restored them verbatim. `NavBar` is not in the root layout (`layout.tsx:240-243`), so every page composes its own masthead. `docs/DESIGN-SYSTEM.md` stopped at rev 22 (2026-05-03), still says `void --news`, still documents edition tabs removed at rev 46, so every section built after it had no current reference to conform to.

### 4.2 The radius system says newsprint; the sections say app

`tokens.css` defines exactly three radii (0, 1px, 2px). Thirty-six distinct radius values are in use: the On Air console is 8-16px, the Ship pills are 999px, the feed chips are 1px. Shadows: 110 distinct values, 29 through a token, and History's key light comes from the opposite side to the feed's. Border weights run 1px to 3px by section. Sub-9px text in 22 rules. Details in Appendix B, PF-01.

### 4.3 Naming: five title grammars and two brand models

Titles use `X | Void News`, `X | History`, `X · Void Weekly`, the tagline, and `X | tagline`. Seven routes ship the root fallback title, including `/history/threads`. The masthead eyebrow says "Also from Void" over lockups that read VOID HISTORY and VOID WEEKLY (products of the parent), while the footer, drawer and titles call them History and Weekly (sections of Void News), and the podcasts split the difference: "Void News: On Air", "Void Weekly: The Argument", "Void News: History". CLAUDE.md's brand section says sections. The code says products wherever a mark is drawn. Appendix A section 3 and Appendix E, E-07/E-08.

### 4.4 Chrome collisions you can see

- The experimental banner offsets only `.nav-header` (`experimental.css:103`). History's own bar has no offset, so on desktop the era title renders under the topbar and on phones the banner disappears on `/history` while showing on `/weekly`.
- History's phone era chips print the last word of each label (`HistoryLanding.tsx:997`): WORLD · AGE · WORLD · PERIOD · ERA · WORLD.
- The Weekly floating pill overlaps the Weekly section bar at 1440px.
- On `/onair` the same episode is "13 min" on the card and "12:16" on the scrubber, under a "WORLD EDITION" label fifteen weeks after editions were collapsed.

---

## 5. The journey from Instagram

Model: a reader taps a History post, lands on `/history`, and should end the visit knowing that Void News exists, that it has a daily broadcast, a Sunday magazine and podcasts, and how to get to each.

What happens today, with evidence in Appendix A and E:

1. **The post cannot be made.** All three social skills call `ig-pipeline.yml`, whose every step reads Supabase, dead since 2026-09-01 (E-01).
2. **If it could, it would link to `/history`, not the event** (E-02). The reader lands on the section index, not the story they tapped.
3. **`/history` is empty to a crawler and blank-then-animate to a person.** The served `<main>` is empty; `HistoryClient` fetches in an effect; there is no `<h1>` (E-11, F-N2).
4. **The first line of copy asks them to file bugs.** The experimental banner is the topmost element on every route (F-06).
5. **From History there is no way to any sibling.** The History topbar carries a back arrow and a self-link; `HistoryFooter` carries one link; the global `Footer` is not rendered (F-08d). On desktop the reader can go to `/history` or `/` and nowhere else.
6. **The only in-content link from News into History is switched off.** `DeepDive.tsx:53` and `InlineDeepDive.tsx:58` still carry `HISTORY_HIDDEN = true` with the comment "the /history routes 301 away", a premise reversed on 2026-09-19 (F-08a).
7. **`/about` and `/press` do not mention History or Weekly** (F-08b, F-08c). The two pages that turn a curious visitor into an informed one advertise two of four live sections.
8. **`/listen`, `/press` and `/privacy` have no navigation on desktop** (F-04). Their only back link is hidden above 767px.
9. **`/pipeline`, `/command-center` and `/admin/ig` are served publicly**, with `robots.txt: Allow: /` and a 6-hex-digit password hash in the bundle (F-05). The command-center meta description reads "CEO operational dashboard".

The home page itself, for the reader who lands there: four competing "read this first" claims in the first viewport (banner CTA, The Brief, Opinion, two equal-weight leads), a masthead carrying three wordmarks, and the first headline 380px down. Appendix A section 7.

---

## 6. Paper

The layout and print stylesheet are finished (1,013 lines). Everything under them is Supabase: un-hidden today, the page renders a masthead, a colophon and a PDF button with zero stories. Plus the Rule 1 defects in F-6 and six em dashes. It is a Medium job (roughly one focused engineer-day), not a redirect flip. Full plan and both sides of the redundancy argument in Appendix D.

Recommendation: bring it back, but as the **printable edition of the same twenty stories in the same order**, read from `build-data/feed.json` through the same server path as the home page, with every article linked to its Deep Dive, wearing the global masthead, and gated by four checks in `verify_sections.py`. Do not bring back the joke classifieds, the datelines, the weather, or the edition route. Paper's value is that it literalises the locked principles (one front page for everyone, dated, once a day); a period pastiche with its own voice undercuts them.

---

## 7. Bloat

| What | Size | Certainty |
|---|---|---|
| `about.css`: 48 classes, none referenced by any TSX, imported by four routes | 1,102 lines | certain |
| CSS targeting classes that no longer exist (lean filter, topic bar, edition tabs, `.skb-v2`, thirty History families) | ~13,700 of 51,891 lines (26%) | heuristic, spot-checked |
| Ten components never imported (`ShipBoard`, `BiasInspector`, `ShareCard`, `MobileMoreSheet`, `MobileMiniPlayer`, `OpEdPage`, `DivergenceAlerts`, `SixLenses`, `StoryMeta`, `ConsensusBadge`) | 4,087 lines | certain |
| `lib/mockData.ts` (0 importers), Revolt mocks, History mock fallback | 4,966 lines | certain / conditional |
| Global tokens never consumed | 109 of 315 | certain |
| Dependencies dead via the above (`qrcode`), or decommissioned but still bundled (`@supabase/supabase-js`, imported by 14 files). Correction 2026-09-21: `motion` is NOT dead; `components/about/useMotion.ts` loads it with a dynamic import for the About page, so the first grep missed it | | certain |
| Served weight: 330 KB CSS and 959 KB JS on the home page, 507 KB CSS on History | | measured |

Everything in the "certain" rows can be deleted this week with no visible change. The 26% estimate needs a class-parity test first (the other session already recommends porting Weekly's two-directional parity test to `history.css` before deleting anything).

---

## 8. The strategy: one Void, applied everywhere

### 8.1 Decide the architecture, once

Two coherent options. Pick one and rewrite the other's residue.

- **Sub-brands:** Void History and Void Weekly each get a lockup, a cover, a handle. Costs: three identities to keep consistent (the last three months show they drift: E-07, E-16, E-17), a split audience, and a contradiction with the locked CLAUDE.md wording.
- **Sections with named programmes (recommended):** parent **Void** (bare brass Sigil) → product **Void News** (the only `V◎ID NEWS` lockup) → sections in plain title case (History, Weekly, The Brief, Sources, Deep Dive) → programmes as typographic titles (On Air, The Argument, History audio). "Advertise separately" is achieved by separate creative, section accent and deep links, not separate brands.

The naming table that follows from the recommendation, and what each current surface changes to, is in Appendix E section 6. The one-line rule for every future surface: **`Void News` is the only word that gets a lockup; a section gets a nameplate in its accent; a programme gets a title.**

### 8.2 One frame, skinned by section

Mount `NavBar` and `Footer` once in the root layout. Give `NavBar` a `section` prop that swaps the nameplate and one accent variable, exactly as the floating player already does. Delete `HistoryTopbar`, `HistoryFooter`, `.wk-topbar`, `.hist-topbar` (about 400 lines). Every route then has the same nine destinations, the same masthead height, the same banner offset, and the same theme toggle in the same place. This single change closes the History dead end, the desktop dead ends on Listen/Press/Privacy, the banner collision, and the duplicated theme toggle.

### 8.3 One token system, with section overrides limited to five values

A section may override: an accent ramp, `--bg-primary`, `--bg-card`, `--cin-grain-opacity`, `--cin-grade`. Nothing else. Collapse `--hist-*`, `--wk-*`, `--np-*` onto the globals by aliasing first (`--hist-ink: var(--fg-primary)`, the way `revolt.css:13-19` already does), then deleting the alias once callers are migrated. Delete the 109 unconsumed tokens. Reduce easings to five and durations to five; add a stylelint rule against raw `cubic-bezier(` and raw `ms` values. Four radii (0, 1px, 2px, and the documented bottom-sheet exception). One shadow ladder. One z-index scale. One image grade with two variants applied to `img`, never to the page container.

### 8.4 One motion physics

Remove the History wheel hijack (`HistoryLanding.tsx:700-765`): a horizontal strip that eats vertical scroll is the single most "different site" moment in the product. Use CSS `scroll-snap-type: x mandatory` and the same `view()` timelines the feed uses. Set the three reveal durations to one token. One global `prefers-reduced-motion` block instead of 88 per-file ones. Drop `motion` from `package.json`.

### 8.5 One first viewport

On every route the reader sees, in this order: masthead, one line that says what this page is, the first real content. On the home page that means: move the experimental banner out of the first viewport (or fire it on the second visit, as `InstallPrompt` already does), fold Opinion into a one-line footer of The Brief so the skybox is one object, and let the ranker's order show: rank 0 wider or larger than rank 1, not badged identically. The first headline should sit inside the first 250px on desktop.

### 8.6 Every section links to every section

A shared "Also from Void News" strip at the end of every section and story page; the floating player's product label links to its section; `/onair` links to `/listen`; `/about`'s "Where to next" lists every live destination as its own comment says it should; `/press` gains a Programmes block with the three shows and their feed URLs; the mobile drawer gains Listen. Flip the two `HISTORY_HIDDEN` flags.

### 8.7 The funnel

Re-source the IG generators from the deploy tree (`history.json`, `weekly-issues.json`, `archive.json`); deep-link every post (`/history/<slug>`, `/weekly/<week>`, `/story/<id>`); interpolate the feed size into the caption prompt; prerender `/history` with an `<h1>` and one sentence; one OG composer (with the Sigil) for the site card, the section cards, a new story card, and the three podcast covers; retitle `podcast-weekly.xml` to "Void News: The Argument"; one issue label used by the page, the post and the feed.

### 8.8 Gates, because a rule nobody can fail is not enforced

Add to `scripts/verify_production.py` or `verify_sections.py`:

- `/command-center/`, `/admin/ig/` do not return 200.
- Every served `<title>`, `og:site_name`, OG wordmark and podcast channel title agrees with one naming table.
- `/press/` numbers equal `feed.json` and `sources.json`.
- A Deep Dive whose slug matches a History event renders the cross-link.
- `/history/` served HTML contains an `<h1>` and at least one event card.
- No shipped raster or XML carries `--`, an edition name, or a stale source count.
- The exported bias rows are less than N% default tuples.
- Every route that mounts `NavBar` passes a server dateline (grep-level lint).
- Every production prompt contains the grounding sentence (`tests/test_prompt_grounding.py`).
- One shared kill regex, run on feed, Weekly, Opinion, podcast XML and promos at write time and on served `/weekly` (W-09) and `/history` (H-05).
- Rundown claims overlap their cluster summary (R-12); no unattributed legal or causal assertion (R-13).
- No time-relative claim in History `summary`, `significance` or `legacy_points`.
- No dash or kill-list word in any frontend string literal or aria-label.
- Token, easing, radius and z-index lints in CI; a class-parity test per stylesheet; a zero-consumer check on tokens.

---

## 9. Ranked backlog

P0 items are correctness or exposure; P1 items are the architecture; P2 is polish; P3 is hygiene. Effort: S under half a day, M a day or two, L a week.

| # | Sev | Item | Effort | Appendix |
|---|---|---|---|---|
| 1 | P0 | Fix step 6b default-tuple overwrite; add the exported-defaults gate (F-1) | M + a run | F |
| 2 | P0 | Redirect and `disallow` `/command-center`, `/admin`, `/ig`; decide `/pipeline`; add the gate (F-05) | S | A |
| 3 | P0 | Render the three podcast covers from one composer; cover-text gate; retitle the weekly feed (F-2, E-16, E-17) | S | E |
| 4 | P0 | Delete `about.css` and its four imports; delete the ten unimported components, `lib/mockData.ts`, `motion`, `qrcode` (B-01, B-03, B-04) | S | B |
| 5 | P1 | Press page: interpolate feed size, add Programmes block, gate `/press/` (F-3, E-13, E-14) | S | E |
| 6 | P1 | Flip `HISTORY_HIDDEN` ×2; render `Footer` on History, On Air, Listen, Press, Privacy; fix `PageToggle` and `aria-current` (F-08a, F-08d, F-04, F-03) | S | A |
| 7 | P1 | Mount `NavBar`/`Footer` once in the root layout with a `section` prop; delete the two section bars (TH-02, 8.2) | M | B |
| 8 | P1 | Server dateline on every `NavBar` mount (F-4) | S | F |
| 9 | P1 | Re-source the IG pipeline from static JSON; deep links; caption facts (E-01, E-02, E-03) | M | E |
| 10 | P1 | Prerender `/history` with `<h1>`; metadata on threads/era/region; sitemap (E-11, F-M2, F-M4) | S | A, E |
| 11 | P1 | Token collapse: alias then delete `--hist-*`/`--wk-*`/`--np-*`; delete 109 dead tokens; easing/duration/radius/z lints (T-01, T-03, M-01, M-02, PF-01) | L | B |
| 12 | P1 | Decide the three-state lean label and render it once on every surface (F-7) | M | F |
| 13 | P2 | Home first viewport: banner out, skybox as one object, rank 0 differentiated (F-06, F-07) | M | A |
| 14 | P2 | History: remove wheel hijack, CSS snap, era chip labels, banner offset (M-03, F chips) | M | B, F |
| 15 | P2 | One OG composer with Sigil; story card; `pageMetadata()` on press/privacy (E-09, F-M3) | M | E |
| 16 | P2 | Paper relaunch on static JSON with the copy pass and four gates (Appendix D steps 1-6) | M | D |
| 17 | P2 | One `prefers-reduced-motion` block; duplicate keyframes; fonts referenced but not loaded (M-04, M-05, T-05) | S | B |
| 18 | P3 | Dead CSS purge behind class-parity tests (B-02); rewrite `DESIGN-SYSTEM.md` and `VOICE-BRAND.md` to describe what ships | L | B, C |
| 19 | P1 | Grounding line in all nine prompts; `test_prompt_grounding.py`; E-13 and entity check on Opinion and Weekly editorial (F-9) | S | C |
| 20 | P1 | Shared kill regex; Weekly drops a section that still fails; W-09 on served `/weekly` (3b) | S | C |
| 21 | P1 | R-12 grounded attribution and R-13 for the rundown; R-02 hard (F-10) | M | C |
| 22 | P2 | Time-relative gate in `test_history_copy.py`, then 81 rewrites (F-11) | M | C |
| 23 | P2 | Privacy retention sentence; `/pipeline` Supabase strings; the 25 `void --x` prompt strings; era-range and aria-label dashes; three "significantly" strings; branded 404 | S | C |

Items 2, 3, 4, 5, 6, 8, 10, 19 and 20 are each under half a day and together remove every P0 exposure, every dead end, and the two-newsroom split. They are the first week.

---

## 10. Questions for the CEO

These change what gets built, so they are asked rather than assumed.

1. **Sections or sub-brands?** Section 8.1 recommends sections with named programmes. If you want Void History and Void Weekly as brands with their own Instagram accounts, say so and CLAUDE.md's brand paragraph is rewritten instead of the nav.
2. **Step 6b.** It is a small fix with a large consequence; it has been blocked on your decision since 2026-09-20. Yes or no.
3. **`/pipeline`:** keep as a public transparency page (then link it from About and Press) or hide it with the other operator surfaces?
4. **The experimental banner:** second-visit only, below the lead, or gone?
5. **Paper:** the printable twenty (recommended), or not now?
6. **The lean label:** are you willing to show "not measured" as a distinct state, which is honest but makes the engine's current coverage visible on every card until item 1 lands?

---

## Appendices

- A. Information architecture, navigation and cross-section flow
- B. Visual system, motion and bloat
- C. Voice and facts across every content surface
- D. Paper relaunch
- E. Instagram funnel and identity system
- F. First-hand measurements

---

# Appendix A. IA, navigation and cross-section flow (audit detail)

## Navigation surface matrix

| Surface | Code | Routes it renders on |
|---|---|---|
| Desktop masthead `.nav-header` | `components/NavBar.tsx` | `/` (HomeContent.tsx:795), `/sources` (SourcesClient.tsx:887), `/onair` (OnAirPage.tsx:170), `/story/[id]` (StandaloneDeepDive.tsx:117) |
| Global footer `.site-footer` | `components/Footer.tsx` | `/` (HomeContent.tsx:1000), `/sources` (SourcesClient.tsx:968), `/weekly` + `/weekly/[week]` (WeeklyIssue.tsx:38) |
| Mobile tab bar `.mtb` (<768px) | `components/MobileTabBar.tsx` | every route (root `layout.tsx:242` via `MobileNav.tsx:63`) |
| Mobile side panel `.msp` | `components/MobileSidePanel.tsx` | every route (`MobileNav.tsx:64`) |
| Mobile more-sheet | `components/MobileMoreSheet.tsx` | nowhere: dead file, referenced only in a comment (`MobileNav.tsx:14`) |
| History topbar/footer | `history/components/HistoryTopbar.tsx`, `HistoryFooter.tsx` | `/history/*` (`history/layout.tsx:25,27`) |
| Weekly topbar `.wk-topbar` | `weekly/WeeklyIssue.tsx:215-234` | `/weekly`, `/weekly/[week]`, `/weekly/archive` |
| `.pwa-back` link | inline per page | `/sources`, `/about`, `/press`, `/privacy`, `/listen`; `display:none` above 767px (`responsive.css:860-862`) |
| Floating player | `components/FloatingPlayer.tsx` | every route except `/ship`; carries zero navigation links |
| Experimental banner | `components/ExperimentalBanner.tsx` | every route (`layout.tsx:239`); links only to `/ship` |
| Onboarding | `components/UnifiedOnboarding.tsx` | mounted on `/` but hard-disabled: `active={false}` (HomeContent.tsx:1015) |
| About "Void suite" grid | `film/data.ts:174-184` | `/about` only |

### Destination by surface

`Y` present, `—` absent, `self` links to the page you are on.

| Destination | Desktop NavBar | Global Footer | Mobile tab bar | Mobile side panel | History topbar/footer | Weekly topbar | About suite grid | Listen page |
|---|---|---|---|---|---|---|---|---|
| `/` News feed | Y (logo only) |: | Y (center) | Y | Y (back arrow) | Y (back arrow) | Y | Y (mobile only) |
| `/onair` On Air |: | Y | Y (left tab) | Y |: |: | Y | Y |
| `/history` | Y (≥768px) | Y |: | Y | Y (brand, self) |: |: | Y |
| `/weekly` | Y (≥768px) | Y |: | Y |: | Y (brand, self) |: | Y |
| `/listen` |: | Y |: |: |: |: |: | self |
| `/sources` | self (bug) | Y |: | Y |: |: | Y |: |
| `/ship` Feedback | Y | Y |: | Y |: |: | Y |: |
| `/about` | Y | Y |: | Y (utility) |: |: |: |: |
| `/press` |: | Y |: | Y (utility) |: |: |: |: |
| `/privacy` |: | Y |: | Y (utility) |: |: |: |: |
| Theme toggle | Y |: |: | Y | Y | Y |: |: |
| Search (Ctrl+K) | Y (home only) |: |: |: |: |: |: |: |

## Getting back and getting across

| From | Back to `/` | Across to siblings | Verdict |
|---|---|---|---|
| `/history` | `HistoryTopbar.tsx:25` "← VOID NEWS"; `HistoryFooter.tsx:20` "← Back to Void News"; mobile tab Home | none. No Weekly, On Air, Listen, Sources or About. Served `/history/` HTML contains 0 × `site-footer` | Dead end on desktop. Two redundant back links, zero lateral links |
| `/weekly` | `WeeklyIssue.tsx:217` "← VOID NEWS"; global Footer | global Footer (nine destinations) | OK |
| `/onair` | NavBar logo | NavBar spinoffs (≥768px), Sources, Feedback, About. No Footer, no Listen | Partial: no route to `/listen`, the page that hands out the podcast feed |
| `/listen` | `.pwa-back`, mobile only | "Open X on the site" links (`listen/page.tsx:83`) | Desktop: no way home except browser Back |
| `/about` | `.pwa-back` mobile only; suite grid tile | On Air, Sources, Feedback (`film/data.ts:174-184`). No History, Weekly, Listen | Partial |
| `/sources` | `.pwa-back` (mobile), logo, Footer | NavBar + Footer | OK |
| `/ship` | `ship/page.tsx:22` "← Back to the feed" | none | Dead end, low cost (terminal form) |
| `/press` | `.pwa-back` mobile only; body link to `/privacy` | none | Desktop: no way home except browser Back |

History replaces the global masthead entirely and the replacement carries no destinations (`history/components/HistoryTopbar.tsx:23-51`: back arrow, self-link brand, theme toggle). Weekly's topbar is structurally identical (`WeeklyIssue.tsx:215-234`) but Weekly also renders the global `Footer` (`WeeklyIssue.tsx:38`). History does not. That single missing import is the largest IA hole in the product.

## Naming mismatches

| Thing | Desktop nav | Mobile drawer | Footer | `<title>` | Page heading | Other |
|---|---|---|---|---|---|---|
| Feedback | "Feedback" → `/ship` | "Feedback" → `/ship` | "Feedback" → `/ship` | "Feedback \| Void News" | "Tell us what to build or fix" | route is `/ship`; `film/data.ts:183` subtitle "The Suggestion Box" |
| On Air | absent | "On Air" / "The broadcast." | "On Air" | "On Air \| Void News" | `<h1>The Broadcast</h1>` (`OnAirPage.tsx:178`), kicker "On Air" | Listen page: "On Air", "Four stories, under fifteen minutes." |
| History | wordmark "VOID HISTORY", `aria-label="Void History"`, `title="History"` (`NavBar.tsx:157`) | "History" | "History" | "History \| Void News"; events "`<title>` \| History" | no `<h1>` at all on the landing | `HistoryFooter` label lowercase "history" |
| Weekly | wordmark "VOID WEEKLY", `aria-label="Void Weekly"` (`NavBar.tsx:160`) | "Weekly" | "Weekly" | "Vol. I, No. 1: … · Void Weekly"; archive "Every issue · Void Weekly" | cover headline | share title "Void Weekly · …" |
| Sources | "Sources" (self-link) | "Sources" | "Sources" | "1,016 Sources \| Void News" | "1,016 Sources" | |
| Listen | absent | absent | "Listen" | "Listen \| Void News" | "Listen" | |

## Title grammars in use

- Pattern A `X | Void News`: `/about`, `/onair`, `/listen`, `/ship`, `/press`, `/privacy`, `/sources`, `/history`, `/story/[id]`, `/pipeline`, `/command-center`.
- Pattern B `X | <Section>`: history events (`historyMeta.ts:57`), games, revolt.
- Pattern C `X · Void Weekly`: `issueMeta.ts:28-29`, `weekly/archive/page.tsx:22`.
- Pattern D tagline as title: `/` and the root fallback (`page.tsx:22`, `layout.tsx:65`).
- Pattern E `X | <tagline>`: `revolt/page.tsx:5`.

Routes shipping the root fallback title and site-wide OG card (no `metadata` export): `history/threads/page.tsx` ("use client"), `history/era/[era]/page.tsx`, `history/region/[region]/page.tsx`, `admin/ig/page.tsx`, `admin/ig/inbox/page.tsx`, `ig/render/[postId]/page.tsx`, `paper/[edition]/page.tsx`. Routes that bypass `pageMetadata()` and so emit no canonical and no OG image: `/press` (`press/page.tsx:10-15`), `/privacy` (`privacy/page.tsx:6-11`), `/feedback`, `/pipeline`, `/command-center` (`siteMeta.ts:49-51` warns about exactly this). `sitemap.ts:12-29` omits `/press/`, `/privacy/`, `/history/threads/`, `/history/era/*`, `/history/region/*`.

## Public exposure of internal tooling (live probe 2026-09-21)

| URL | Status | Served `<title>` | In sitemap | Linked anywhere |
|---|---|---|---|---|
| `/pipeline/` | 200 | Pipeline Flow \| Void News | no | no |
| `/command-center/` | 200 | Command Center \| Void News | no | no |
| `/admin/ig/` | 200 | root fallback | no | no |
| `/admin/ig/inbox/` | 200 | root fallback | no | no |
| `/feedback/` | 301 → /ship | | no | no |
| `/paper/`, `/games/`, `/revolt/` | 301 → / | | no | no |

`robots.ts:9` is `allow: "/"` with no disallow; no route sets `robots: { index: false }`. `/command-center` carries a client-side password gate whose 6-hex-digit hash is in the bundle (`components/CommandCenter.tsx:13-18`). Its meta description reads "CEO operational dashboard for Void News pipeline, bias engine, and source monitoring." `grep -c "command-center" docs/CHANGELOG.md` → 0: the route was never revisited in 73 revisions.

## Homepage first viewport, in DOM order

Mobile (<768px): (1) ExperimentalBanner "Void News is experimental. Things will change. Tell us what breaks." (`layout.tsx:239`); (2) NavBar: wordmark, dateline, search, theme; (3) `MobileBriefPill` collapsed teaser carrying both The Brief and Opinion (`MobileBriefPill.tsx:114-141`); (4) "Today's Top Stories" rule (`MobileFeed.tsx:89`); (5) `mf__twin-leads`: two co-equal hero cards both badged Top Story (`MobileFeed.tsx:93-108`); (6) fixed `MobileTabBar`: On Air · Home · Menu.

Desktop (≥768px): (1) ExperimentalBanner; (2) NavBar: wordmark, `experimental` badge (≥1320px), tagline, dateline, "Also from Void" + VOID HISTORY + VOID WEEKLY, Sources · Feedback · About, search, theme; (3) `SkyboxBanner` (`HomeContent.tsx:918`): two clickable columns, The Brief and Opinion; (4) "Today's Top Stories" + lean legend; (5) `lead-twin`: two `LeadStory` heroes side by side; (6) FloatingPlayer.

## Cross-promotion map

| Section | Masthead | Footer | Drawer | In-content | About page |
|---|---|---|---|---|---|
| On Air |: | Y | Y | Brief pill play + floating player (audio, not a link) | Y |
| History | Y ≥768px | Y | Y | `HistoryContextLink`: switched off |: |
| Weekly | Y ≥768px | Y | Y | none |: |
| The Argument |: |: |: | none |: |
| Podcasts / `/listen` |: | Y |: | `layout.tsx:73-81` alternates (machine-readable only) |: |

Key evidence:

- `components/DeepDive.tsx:50-53` and `components/InlineDeepDive.tsx:54-58`: `const HISTORY_HIDDEN: boolean = true;` with the comment "History is hidden pre-launch (the /history routes 301 away)". `_redirects:14-17` records the reversal on 2026-09-19. The render path below (`DeepDive.tsx:79-101`) produces "See how this event is told from N perspectives".
- `film/data.ts:174-177` `PRODUCT_FAMILY` lists only Void News and On Air.
- `press/page.tsx`: zero occurrences of "History", "Weekly", "On Air".
- `grep -rn 'href="/weekly' frontend/app/history/` → 0; `grep -rn 'href="/history' frontend/app/weekly/` → 0.
- `FloatingPlayer.tsx` contains one `href` (chapter deep link, line 679) and knows `productLabel` (line 76) but never links to a section. `OnAirPage.tsx` has no link to `/listen`.
- `MobileSidePanel.tsx:77-84` `MAIN_ITEMS` has no Listen row.
- `NavBar.tsx:169-171` passes `activePage="feed"` as a literal; `PageToggle.tsx:82-84` derives the href from it, so `/sources` self-links; no `aria-current` anywhere in NavBar.
- `history/arc-features.ts:11` `LEDGER = true`; `/history/threads/`, `/history/era/*`, `/history/region/*` are built, served, and linked from nothing but themselves (`EraPageClient.tsx:97`, `RegionPageClient.tsx:91`).
- Dead nav files: `MobileMoreSheet.tsx` (~200 lines), `MobileMiniPlayer.tsx`, `feedback/page.tsx` (behind a 301).
- `NavBar.tsx:195` comment says the theme toggle is hidden on mobile; no CSS rule hides it, so it renders twice below 768px (masthead and `MobileSidePanel.tsx:434`).

---

# Appendix B. Visual system, motion and bloat (audit detail)

Counts come from greps and scripts run on 2026-09-21. Dead-CSS figures are heuristic (class-name presence in TSX/TS source, template-literal prefix tolerated) and were spot-checked on 12 selectors, all confirmed dead.

## Tokens

**T-01 (P1) Four parallel token systems instead of one.**

| File | Custom props defined | What they redefine |
|---|---|---|
| `styles/history.css` | 102 | full light+dark palette (`--hist-bg/-card/-elevated/-border/-border-subtle/-divider/-ink/-ink-secondary/-ink-muted/-shadow-tint`), a 3-tier shadow set, 4 easings, 2 nav heights, plus `--rev-cta`/`--rev-blue` (Revolt tokens inside History, lines 374-419) |
| `styles/revolt.css` | 54 | 7 aliases of globals, then 47 new colours, 4 shadow edges, 2 easings |
| `styles/weekly.css` | 30 | accent ramp, two creams, paper, topbar height, measure, rail |
| `paper/paper.css` | 21 | paper, 3 inks, 2 rules, 5 font stacks (two undefined) |
| `styles/ship.css` | 14 | 6 status colours × 2 modes |
| `styles/spectrum.css` | 14 | 7 zone tints × 2 modes |
| `globals.css` | 18 | a second copy of the dark surface tokens under `prefers-color-scheme` (lines 235-252) |

Duplications of what `tokens.css` already provides: `history.css:86-89` defines `--ease-document-settle: cubic-bezier(0.16,1,0.3,1)`, identical to `--ease-out` (tokens.css:900), and re-declares `--ease-unfold` byte-for-byte equal to tokens.css:204. `history.css:72-84` defines a third shadow ladder next to `--shadow-e1..3` and `--shadow-cinematic-*`. Nav heights: `--nav-height: 53px` (tokens.css:975) vs `--hist-topbar-height: 56px` (history.css:92) vs `--wk-topbar-h: 3rem` (weekly.css:63). Root cause: history.css line 5 "All classes scoped to .hist-page namespace"; each section was authored by a separate workflow that scoped itself to avoid collisions rather than extend the base; rev 60 kept History and Weekly as separable, hideable products.

**T-02 (P2) Hex literals duplicating tokens.** tokens 155, games 111, history 100, ship 42, revolt 35, paper 26, weekly 23, command-center 23, pipeline 21, ig-render 21, components 4. Examples: `--hist-accent: #5C4033` (history.css:28) = `--palette-history`; `--wk-paper: #EDE4D0` (weekly.css:62) while `--palette-weekly-paper: #EDE4D0` exists in tokens.css and is never used; `.nav-history { --hist-nav-accent: #5C4033 }` (components.css:2382) and dark `#8B7355` (2436) match neither `--hist-accent` dark (`#8E6A56`, history.css:101) nor `--hist-brass`. Three different umbers in dark mode for one section.

**T-03 (P2) 109 of 315 global tokens are never consumed (35%).** All eight `--scene-*`, all four `--parallax-*`, all five `--z-depth-*`, four of six `--focus-*`, all `--cin-rack-*`, `--whip-pan-dur`, `--ease-steadicam`, `--ease-in-out`, `--ease-whip-out`, `--dur-instant`, `--dur-micro`, `--radius-none`, `--palette-weekly-paper`, `--palette-onair-surface`, `--shadow-cinematic-lifted`, `--shadow-card-lead-hover`, `--img-grade-feed`, `--glass-shadow`, `--scroll-parallax-range`, `--scroll-vignette-range`, `--type-digest-headline`, `--type-wire-headline`, the six `--cat-*`. tokens.css is 40% comment lines by volume.

**T-04 (P2) `--canvas-max` is not respected, and the frame itself refuses it.** Home `.page-main` uses the literal `min(92vw,1600px)` (layout.css:36) deliberately, because of a documented Chromium bfcache bug (layout.css:23-36); `.nav-inner` (components.css:2005) and `.site-footer` (layout.css:243) likewise. History mixes the token with `1200px` (history.css:629, 8832) and `900px` (3162, 3259, 6781). On Air `660px` (onair.css:21), Press `760px` (press.css:19), Feedback `640px`, Privacy `720px`, Story `900px`: five reading measures within 260px of each other.

**T-05 (P2) CSS references fonts that are not loaded.** `history.css:8695, 8741, 8838, 8904` use the literal `'IBM Plex Mono'` and `:8729` `'Barlow Condensed'`; next/font registers hashed family names, so these render Courier New / Arial Narrow. `paper.css:20-21` reference `--np-lora` and `--np-oldstandard`, defined nowhere. Undefined variables: `--font-text` (components.css:7964), `--font-display` (weekly.css:509, no fallback), `--font-body` (deep-dive-page.css:45,135; layout-zones.css:577).

## Theming

**TH-01 (P1) History and Weekly are forks of the page, not themes on it.**

| Layer | Feed (base) | History | Weekly |
|---|---|---|---|
| Container | `.page-container > .page-main` | `.hist-page` (own div; history/layout.tsx:19) | `.wk-page` |
| Paper | `--bg-primary #F0EBDD` | `--hist-bg #F2EDE0` (history.css:63) | `#EDE4D0` literal (weekly.css:65) |
| Ink | `--fg-primary` | `--hist-ink #2C2418` | `--fg-primary` |
| Accent | brass `#946B15` | umber `#5C4033` + brass `#9B7A2F` | red `--palette-weekly` |
| Grade | `.page-main{filter:var(--cin-grade)}` (components.css:7266) | `.hist-grade` (198-203), applied only on era/region pages, not landing or events | none |
| Grain | `.page-container::after` feTurbulence freq .75 seed 7 | history.css:1986 freq .5 seed 17; :2726 freq .65 | `.wk-page::before` at `calc(var(--cin-grain-opacity)*3)` (weekly.css:97) |
| Vignette | `.page-container::before` | `<div class="hist-vignette">` at half opacity | `.wk-page::after`, `z-index: 3` literal |
| Reveal | `.anim-stagger` 260ms | `.hist-reveal` 300ms | `.wk-reveal` 700ms |

Because `.hist-page` and `.wk-page` sit outside `.page-main`, none of the base cinematic layer applies; each section re-implements it with different parameters. Three feTurbulence recipes and three vignette ellipses ship for one brand.

**TH-02 (P1) Nav chrome is forked three ways.** `NavBar` is not in the root layout (layout.tsx:240-243); every page composes its own masthead.

| | Feed `.nav-header` (components.css:1873) | History `.hist-topbar` (history.css:209) | Weekly `.wk-topbar` (weekly.css:120) |
|---|---|---|---|
| Background | opaque `--bg-primary` (backdrop-filter removed for a measured bfcache bug) | `color-mix(--hist-bg 88%)` + `blur(10px) saturate(0.9)` | `color-mix(--wk-paper 85%)` + `blur(8px)` |
| z-index | `--z-nav` = 20 | `50` literal | `50` literal |
| Height | ~53px | 56px | 48px |
| Border | `--glass-border` | `--hist-border-subtle` | red |
| Footer | `Footer` | `HistoryFooter` | `Footer` |

The floating player is the counter-example done right: `.fp--weekly`/`.fp--history` (floating-player.css:1993-2004) skin one component by swapping `--fp-accent`.

**TH-03 (P2) Dark mode handled by four mechanisms.** tokens.css `:root[data-mode=…]`; globals.css:235-252 duplicates 18 dark tokens under `prefers-color-scheme`; history.css:96-146 a complete second dark palette; and sections with zero `[data-mode=` hooks despite hardcoded colour: `games.css` (111 hex), `pipeline.css`, `ig-render.css`, `command-center.css`, `listen.css`, `privacy.css`, `layout-zones.css`, `deep-dive-page.css`.

## Motion

**M-01 (P1) 20 easing curves, three names for one curve, raw literals where the doc forbids them.** DESIGN-SYSTEM.md:618: "Never write a raw easing literal in new CSS". `(0.16,1,0.3,1)` appears as a raw literal 50 times and under three token names; `(0.22,1,0.36,1)` 10 times; `(0.34,1.56,0.64,1)` 7; `(0.45,0.05,0.55,0.95)` 6 (no token); 14 further curves 1-2 each. Plus 7 `linear()` springs in tokens.css and a 15-stop `linear()` pasted twice (components.css:6629/6757).

**M-02 (P1) 78 distinct durations; 417 literal transitions vs 153 tokenised.** 200ms ×167, 300ms ×114, 150ms ×68, 400ms ×65, `0.15s` ×35, 250ms ×32, 60ms ×31. The same gesture differs per section: fade-in 260ms (feed, animations.css:131), 300ms (History, history.css:775), 700ms (Weekly, weekly.css:1642).

**M-03 (P2) Different physics per section.** Feed: CSS scroll-driven, behind `prefers-reduced-motion`. History: JS physics. `HistoryLanding.tsx:700-765` hijacks the wheel (`e.preventDefault()`), converts vertical delta to horizontal velocity (`velocity += e.deltaY * 1.2`), runs a rAF friction loop (`velocity *= 0.88`) with snap-to-card, and drives a parallax layer on every scroll event. History has 10 rAF loops, 4 scroll listeners and 7 IntersectionObservers versus 2 scroll listeners in the whole feed. `motion` `^12.41.0` is in `package.json` with zero imports.

**M-04 (P2) Reduced-motion coverage is uneven.** No `prefers-reduced-motion` block in `listen.css`, `privacy.css`, `pipeline.css`, `ig-render.css`, `layout-zones.css`, `typography.css`, both admin files. Keyframes-to-reduced-motion ratios: games 64:8, history 37:15, floating-player 19:1, ship 16:1.

**M-05 (P3) 273 `@keyframes`, 5 duplicate names** (`wire-shake`, `skbFadeIn`, `pullSpin`, `onboardDialogIn`, `fpBroadcastIn`).

## Bloat

**B-01 (P0) `about.css` (1,102 lines) is entirely dead and shipped to four routes.** Imported by `about/layout.tsx`, `listen/page.tsx`, `press/page.tsx`, `privacy/page.tsx`. Zero of its 48 top-level classes appear in any TSX. The live `/about` is `AboutExperience`, styled in `onboarding.css`. Root cause: rev 62 replaced the About page; the old stylesheet was left and later re-imported by Listen/Press/Privacy as a "prose page" base it does not provide.

**B-02 (P1) About a quarter of all CSS targets classes that no longer exist.** Estimate 13,723 of 51,891 lines (26.4%).

| File | Dead est. | Retired feature |
|---|---|---|
| components.css | 4,280 / 8,508 | `.lean-filter__*`, `.lean-bar__*`, `.filter-row`, `.topic-bar__*`, `.nav-ed`, `.dd-press-trigger`, `.dd-read-all-sides`, `.dd-action-btn`, `.dd-share-toast`, `.intro__stage`, `.bi-source-btn`, `.sigil__tap-hint` |
| history.css | 4,006 / 10,969 | `.hist-back-to-timeline`, `.hist-audio-cue`, `.hist-threads__card`, `.hist-context-toggle`, `.hist-topbar__revolt`, `.hist-standalone-back`, `.hist-dossier__card`, `.hist-compare-toggle`, `.hist-classified-tile__reveal`, `.hist-witness__expand`, `.hist-tl-strip__dot`, `.hist-thread-stage__lead` |
| about.css | 1,064 / 1,102 | all |
| spectrum.css | 856 / 3,534 | `.sources-edition-chip`, `.dd-spectrum__bar` |
| games.css | 851 / 4,657 | `.cipher-share` (route hidden anyway) |
| desktop-feed.css | 521 / 576 | `.skb-v2` |
| skybox-banner.css | 379 / 1,008 | `.skb__topbar-chip` |
| deep-dive-page.css | 320 / 452 | |
| responsive.css | 285 / 925 | |
| typography.css | 103 / 169 | `.edition-meta` |
| mobile-nav.css | 65 | `.mobile-edition-pill` |

Edition remnants: `:root[data-edition="us"]` / `"india"` grades (components.css:7273-7276) can never match because `HomeContent.tsx:387` hard-sets `data-edition="world"`. 104 selectors are defined in more than one file (40 of them components.css vs responsive.css); within-file redeclaration counts: history.css 211, games.css 123, components.css 113, spectrum.css 77.

**B-03 (P1) Ten components (4,087 lines) are never imported.** `ShipBoard.tsx` 1,431, `BiasInspector.tsx` 1,181, `ShareCard.tsx` 601 (only consumer chain for `lib/shareCardRenderer.ts` and the `qrcode` dependency), `MobileMoreSheet.tsx` 210, `MobileMiniPlayer.tsx` 129, `OpEdPage.tsx` 128, `DivergenceAlerts.tsx` 127, `SixLenses.tsx` 113, `StoryMeta.tsx` 85, `ConsensusBadge.tsx` 82.

**B-04 (P2) Mock data and dead dependencies.** `lib/mockData.ts` 1,074 lines, zero importers; `history/mockData.ts` 610 (last-resort fallback); `revolt/mock*.ts` 3,282 feeding a hidden route. `@supabase/supabase-js` still a dependency, `lib/supabase.ts` imported by 14 files. `qrcode` dead via B-03. (Correction: `motion` is loaded by a dynamic `import("motion")` in `components/about/useMotion.ts`, so it is live; the static grep missed it.)

## Premium feel

**PF-01 (P1) The radius system says "sharp newsprint"; the sections say "rounded app".** tokens.css:967-970 defines `--radius-none: 0; --radius-sm: 1px; --radius-md: 2px`. In use: 36 distinct radius values. `2px` literal ×132 vs `var(--radius-md)` ×37; `50%` ×112; pills `999px` ×11 + `100px` ×4; `8px` ×9, `12px` ×3, `16px` ×6, `20px`, `22px`, `2.5px`, `1.5px`, `0.75px`. Where the UI reads as assembled from parts:

1. `onair.css:77` `border-radius: 12px`, `:95` `16px`, `:305/:437/:515/:827` `8px`: the On Air console is an iOS widget beside a broadsheet feed.
2. `ship.css:282/1818` `8px` cards and `:623/:1432/:1884` `999px` pill buttons next to the feed's 1px chips.
3. `components.css:6832` `border-radius:100px` and `:6670` `.intro__stage{border-radius:16px}` (onboarding chrome) inside the feed's own stylesheet.
4. Three mastheads at 48/53/56px with different blur and border colour.
5. Shadow key light contradicts itself: tokens.css states negative-X offsets are the top-left key light; `history.css:72-84` casts positive X, so History's light comes from the top-right; Revolt uses hard `3px 3px 0 0` stamps.
6. Border weights: 1px ×455, 1.5px ×24, 2px ×84, 3px ×36.
7. `.hist-topbar` and `.wk-topbar` at `z-index: 50` sit at the overlay tier; history.css uses 63 literal z-indexes and 0 tokens.
8. Sub-9px text in 22 rules (`components.css:232` 7px, `mobile-feed.css:1090` 7px, `floating-player.css:1904` 7px, `paper.css:499/853/854` 8px, `skybox-banner.css:989` 7px).
9. Spacing scale abandoned on the quiet pages: On Air 96% literal, Paper 96%, Press 97%, Listen 90%, versus feed 21%, Weekly 8%.
10. 168 `box-shadow` declarations, 110 distinct, 29 through a token, while three shadow ladders exist in tokens.css. `--text-hero` consumed once; 85 bespoke `font-size: clamp(...)` expressions; On Air 33 literal px and 0 `--text-*`.

## Imagery

**IM-01 (P2) Nine unrelated grade chains.** Page-wide `var(--cin-grade)` on `.page-main, .nav-header` (components.css:7266); Weekly images ×4 with `var(--img-grade-weekly, contrast(1.05) saturate(0.92) sepia(0.04))` where the inline fallback duplicates the token with different numbers; History era/region only `contrast(1.02) saturate(0.88) sepia(0.06)` (history.css:198); History photos `sepia(0.18)` (2417); History states `saturate(0.3)` (2610, 4634 `!important`), `grayscale(0.8) opacity(0.5)` (4445); Revolt two variants (383, 472). Applying `filter` to the whole `.page-main` is also the structural cause of the fixed-descendant containing-block workaround (components.css:7260-7264) and the bfcache canvas freeze.

## Documentation debt driving the drift

`docs/DESIGN-SYSTEM.md` v2.5 dated 2026-05-03 (rev 22) still names the product `void --news` (6 occurrences; 33 more in CSS comments), documents "Edition switch: click edition tab" (line 611) six revs after editions were collapsed, documents BiasInspector (unimported), lists three easings where twenty exist, and asserts a canvas rule the frame opts out of. Every section built after rev 22 (History rev 60-69, Weekly rev 72, On Air, Listen, Press) had no current reference to conform to.

---

# Appendix C. Voice and facts across every content surface (audit detail)

Repo: `/home/user/void--news`. Method: every served-content surface was loaded into a scanner (`/tmp/.../scratchpad/scan.py`, `scan2.py`) and matched against the CLAUDE.md rules and the VOICE-BRAND.md section VII kill list; every `.tsx/.ts` under `frontend/app` was scanned with block comments stripped; every LLM prompt in `pipeline/` was located and checked for a grounding phrase; the two fact-control files and the tests were read. Audio surfaces (`audio_script`, `opinion_audio_script`, `data/history/scripts/*.txt`, house promos) were scored with em dashes exempt, as the rule allows.

### 0. Headline verdict

The product has the voice it claims on four surfaces (History copy, History audio, On Air, house promos, the About page) and does not have it on three (Weekly prose, the daily Opinion, and the Press page). The daily feed is clean but wire-flat. The controls that exist enforce shape (dashes, first person, quote balance, numbers-in-source) on the feed and on History; they do not reach Weekly prose, Opinion, Press, About, Privacy, /pipeline, podcast XML, or the audio scripts, and the voice bible that everything is supposed to follow describes a product that no longer exists.

Two Rule 1 breaches are live today. One is on the page labelled for journalists to copy verbatim.

---

### 1. Count tables

### 1a. Served content (written surfaces; audio surfaces marked)

| Surface | Fields scanned | Em/en dash | Kill list (VII strict) | "significant/notable" family | Unattributed ("experts say" class) | Hedge words | "!" | Time-relative claims | 2nd person |
|---|---|---|---|---|---|---|---|---|---|
| Feed top-20 (`frontend/build-data/feed.json`: titles, summaries, consensus points) | 137 | **0** | 1 (`underscore`) | 0 | 0 | 6 (`reportedly` x3, `likely`, `potentially` x2) | 2 (both inside a Trump quote) | 4 (`nearly a year ago`, `currently` x2, `this year` in a quote) | 1 (in a quote) |
| Deep Dive JSON (`public/data/deepdive/*.json`) | 3,404 | 55, all in `article.*` source text; **0 in Void-written fields** (there are none) | 0 | 0 | 0 | n/a | n/a | n/a | n/a |
| Brief, written (`brief.json`: `tldr_headline/text`, `opinion_headline/text`) | 4 | **0** | 0 (but "it sends a clear signal across borders", a one-word variant of the banned "sends a clear message") | 0 | 0 | 0 | 2 (inside quotes) | 0 | 0 |
| Brief, audio (exempt from dash rule) | 2 | 0 | 1 (`significant escalation`), 1 (`highlight`) | 1 | 0 | 0 | 3 | 0 | 0 |
| Weekly, both issues (`build-data/weekly-issues.json`: cover, recap, departments, bench opinions, editorial, numbers, chapters) | 104 | **0** (strip_dashes works) | **34** | 7 | 2 (`some argue`, `Critics argue`) | **38** | 0 | 1 | 0 |
| History events, 78 YAML (`data/history/events`, served as `public/data/history.json`) | 6,150 | 30, **all inside quotations or a published title** (exempt by `tests/test_history_copy.py`) | 8, all in `perspectives[].narrative` (`significant` x2, `notable`, `pivotal`, `navigate` x4) | 4 | 4 (`analysts argue` x2, `sources say`, `Some argue`) | 138 | 18 (inside quotes) | **81** (summary 21, significance 40, legacy 20) | 131 (quotes) |
| History scripts, 78 (audio, exempt) | 78 | 0 | 2 (one is a 1381 quote, "delved"; `pivotal` in soviet-union-collapse) | 0 | 2 (`Some say`, `sources say`, mongol-conquest-baghdad) | 56 | 15 (quotes) | 22 | 157 (quotes, plus 1 direct address: arab-spring OPEN "You think you know how this one starts") |
| House promos (`data/promos/house.yaml`, 24) | 176 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 (deliberate: "nothing knows who you are") |
| Podcast XML x3 (`public/podcast-*.xml`, titles/descriptions/summaries) | 231 | 0 | 0 | 0 | 0 | 6 | 6 (quotes) | 2 | 4 (quotes) |

### 1b. Weekly kill-list breakdown (the only written surface that fails)

| Term | Hits | Where |
|---|---|---|
| underscore(s/d/ing) | 15 | cover x3, recap x6, dept x0, opinions x6 |
| significant(ly) | 7 | cover, recap x2, opinions x4 |
| robust | 6 | dept tech, dept sports, recap, opinions x3 |
| navigate/navigating/navigated | 4 | cover x3, opinions x1 |
| nuanced | 1 | dept sports |
| a testament to | 1 | opinions[1] (Sep 14) |
| **Total** | **34** | 25 distinct fields of 104 |

Plus one scaffolding hit: `opinions[0].text` "This isn't just about military bases; it's about who holds the power." (Sep 14 issue), and a significance assertion outside the list: `recap[0]` "This marks a key moment for Turkey's diplomatic engagement on the international stage."

### 1c. Frontend microcopy (non-comment lines, `frontend/app/**`)

| Check | Lines | Notes |
|---|---|---|
| Em/en dash rendered | **11** | 10 in History components, 1 admin |
| Kill-list word rendered | **3** live + 1 UI verb | BiasInspector, DivergenceAlerts, Sigil; "Navigate" in SearchOverlay is a verb label, fine |
| Hardcoded "1,016" | 14 places | gated by `frontend/test/copy-facts.test.mjs` against the roster (passes today) |
| Hardcoded "158 countries" | 9 places | gated, passes |
| Hardcoded "78" events | 2 (`MobileSidePanel.tsx:80`, `historyMeta.ts:36` fallback `eventCount \|\| 78`) | **not gated** |
| "50 stories" / "fifty" | **2 on /press** | **gate regex misses both** (see F-01) |
| Supabase-era copy rendered | 4 strings on `/pipeline` | page is served, not linked |
| "both outlet and text" leads on /about and /sources | **PASS** | see section 2 |

### 1d. Prompts

| Metric | Count |
|---|---|
| Production prompts located | 16 (plus 5 parked/dead/manual) |
| Carry the exact CLAUDE.md grounding line | **2** (`cluster_summarizer.py:219`, `daily_brief_generator.py:260-261`) |
| Carry an equivalent ("from the stories provided / outside knowledge") | 3 (radio 627, history 128, weekly cover 389/696) |
| **No grounding phrase at all** | **9 production prompts** (F-04) |
| Prompt strings that name the product "void --news/--weekly/--history/--onair/--opinion" | **25** |
| Prompts referencing the retired VOICE-BRAND host roster | 1 (`daily_brief_generator.py:1336-1337`) + 1 retired Gemini-TTS host name in weekly audio (`weekly_digest_generator.py:1460`) |

---

### 2. Findings

#### F-01 · P0 · The Press page publishes the wrong feed size, twice, on copy labelled for journalists to quote

**Observation.** `/press` says the daily edition has 50 stories. The feed has been 20 since 2026-09-07 (`frontend/config/feed.json` `"displayed": 20`; CLAUDE.md locked decision).

**Evidence.**
- `frontend/app/press/page.tsx:80-81`: `<div className="press-stat__n">50</div>` / `Stories in one daily edition`
- `frontend/app/press/page.tsx:128-129` (long boilerplate, under the heading "Copy it as written"): "The fifty most important stories are ranked once a day, in the same order for everyone"
- Same page, line 17, `BOILER_SHORT` correctly interpolates `${FEED_DISPLAYED}`; the two hand-written restatements beside it were not converted.
- Commit `cc49187` (2026-09-20, "The site described itself wrongly in ten places, and now it cannot") states "All ten now derive from the config" and "It earned itself immediately by catching the press boilerplate". Both statements are false against HEAD: `git show HEAD:frontend/app/press/page.tsx | grep -nE "\b50\b|fifty"` returns lines 80 and 129.

**Root cause.** The control added in that commit, `frontend/test/copy-facts.test.mjs`, tests `/\b(?:50|fifty)\s+stories\b|\btop\s+50\b/i`. "50</div>" and "fifty most important stories" do not match. The commit message reports the control's success without reading the page back, which is the exact failure CLAUDE.md Rule 1 names ("Verify, then report. A chained command that echoes success is not evidence").

**Solution.**
1. Change lines 80 and 128-129 to derive from `FEED_DISPLAYED` (a number-word helper for the prose: `twenty`).
2. Widen the regex in `copy-facts.test.mjs` to `/\b(?:50|fifty)\b(?![^<]*(?:%|percent|years|km|kilomet))/` scoped to `.tsx` prose and JSX text, or better, assert that the literal `FEED_DISPLAYED` value's *old* values (50, "fifty") never appear in any JSX text node or string prop in `app/press`, `app/about`, `app/components/about`, `app/layout.tsx`, `app/page.tsx`.
3. Add a served-page check to `scripts/verify_sections.py`: fetch `/press/`, assert `_visible_text` contains the string `f"{displayed} stories"` or its number-word and does not contain `50 stories|fifty`. The gate currently fetches only `/`, `/history/`, `/weekly/` and their JSON; `/press` is the one page whose whole job is to be quoted.

#### F-02 · P1 · On Air restates an official's legal argument as Void's own statement of law, and changes what he argued

**Observation.** The served radio script (`frontend/public/data/brief.json` `audio_script`, STORY 1) alters an attributed claim in two steps.

**Evidence.**
- Source summary (`frontend/build-data/feed.json` cluster [0], `summary`): "U.N. Ambassador Mike Waltz ... Waltz argues the Supreme Court has protected the right to publish, but not access to any government facility."
- Radio, turn A: "Ambassador Waltz argues the Supreme Court has protected **such actions**." ("such actions" now refers to the ban, not to the right to publish.)
- Radio, next turn A, unattributed: "**The Supreme Court has previously protected the government's right to limit access to facilities. This protection applies to journalists.**" This is Void asserting a proposition of constitutional law in its own voice. No article in the deep dive is Void's source for that as fact; it is Waltz's argument.
- Same block: `He accused the outlets of in his words "FAKE NEWS!"` carries quotation marks; R-02 ("quotation marks are never read aloud") fires as *advisory only* (`radio_script_generator.py:476-480`), and the served script has 4 quote marks.

**Root cause.** R-01..R-11 in `pipeline/briefing/radio_script_generator.py` are shape rules (segments present, no numerals, attribution order, sentence length, word share). Nothing compares a rundown line's *claim* to the summary it was cut from. The compression prompt is grounded (line 627), but a grounded model still paraphrases, and no E-13/E-14-style check runs on the rundown. The daily `standard.py` grounded validators (E-13 numbers, E-14 quotes) never see audio text.

**Solution.**
1. Add `R-12 grounded attribution`: for every rundown sentence beginning with a proper noun + speech verb (`says|argues|states|describes|calls`), require that the object clause's content words (minus stop words) appear within the matching cluster's `summary` or `consensus_points` at >= 0.6 token overlap; fail on lower. Implement in `radio_script_generator.validate_rundown` next to R-07, with a planted-defect test in `tests/test_radio_script.py` using exactly this Waltz pair.
2. Add `R-13 no unattributed legal/causal assertion`: a sentence whose subject is a court, a law, or "the Constitution" and whose verb is present-perfect/present ("has protected", "protects", "prohibits") must be preceded in the same turn by an attribution. Same test pattern.
3. Promote R-02 from advisory to hard fail when `count('"') > 0` in news segments; regenerate once, then strip.

#### F-03 · P1 · Weekly prose ships with the kill list in it, and the enforcement is designed to ship it

**Observation.** 34 kill-list hits and 38 hedges across 104 Weekly fields in the two published issues; the current issue (Sep 14, "Vol. I, No. 1") alone has 17.

**Evidence** (all `frontend/build-data/weekly-issues.json[0]` unless marked):
- `cover_text[0].text`: "...appeared in reports from 16 sources on September 19th, **underscoring** the delicate balance..."; "...granting the US **significant** operational rights..."; "The divergence in public statements ... **highlights the complex interplay** of sovereignty, strategic interests, and self-determination"
- `cover_text[1].text`: "...found himself **navigating** a highly politicized environment"; "This financial commitment **underscored** the depth of his conviction"
- `recap[4].summary`: "This incident **underscores** the vulnerability of security forces."
- `dept[1:sports].text`: "...has established **robust** mechanisms..."; "...fear expressing **nuanced** opinions..."
- `opinions[1].text`: "...**significant** access to Greenland under a treaty from the 1950s, **a testament to** a long-standing security cooperation"
- `opinions[0].text`: "**This isn't just about** military bases; it's about who holds the power." (VII scaffolding)
- `[1](2026-08-24) recap[3]`: "**Critics argue** that this existing, **robust** security infrastructure..."
- Cover essay also narrates its own sourcing inside the prose: "News outlets, drawing on 57 sources, reported Denmark's affirmation", which the daily prompt forbids ("Never reference outlet names, 'coverage,' 'sources'", `daily_brief_generator.py:1324`) and the weekly prompt does not.

**Root cause** (three, stacked).
1. `pipeline/briefing/weekly_parse.py:171-181` `PROHIBITED_TERMS` contains the significance family and the Vox scaffolding but **none of the VII AI-slop set**: no `underscore`, `robust`, `navigate`, `nuanced`, `pivotal`, `delve`, `multifaceted`, `tapestry`, `paves the way`, `sheds light on`. 27 of the 34 hits are words the check does not know.
2. `weekly_digest_generator.py:214-252` regenerates **once** on findings and then ships the better attempt ("a missing department reads worse than a long one"). That rationale is right for length and wrong for a banned word, which is one `re.sub` away from gone. The 7 `significant` hits *are* on the list and shipped anyway, which proves the once-then-ship path is the leak.
3. The daily feed's deterministic sanitiser `pipeline/utils/prohibited_terms.py:sanitize_editorial_text` (which removes significance words) is never applied to weekly text; the weekly uses only `strip_dashes`. So the two surfaces have different definitions of "clean".

**Solution.**
1. Move the VII AI-slop set into `pipeline/utils/prohibited_terms.py` `_SIGNIFICANCE_RE` (or a sibling `_SLOP_RE`) so one regex serves feed, weekly, podcast XML and promos: `underscor(e|es|ed|ing)`, `robust(ly)?`, `navigat(e|es|ed|ing)`, `nuanced`, `pivotal`, `delv(e|es|ed|ing)`, `multifaceted`, `tapestry`, `paves? the way`, `sends? a clear (message|signal)`, `a testament to`, `sheds? light on`, `marks a (key|pivotal|significant) moment`, `highlights? the`, `complex interplay`. Removal is not safe for all of these (deleting "underscores" leaves a broken sentence), so: significance adjectives are deleted (existing behaviour); verbs and nouns are *findings that fail*, not substitutions.
2. In `weekly_parse.banned_terms`, import that shared list instead of the local tuple. `tests/test_weekly.py` gets one planted-defect case per new term.
3. In `weekly_digest_generator._generate_section`, after the single regeneration, run `sanitize_editorial_text` on the text (it already runs on every feed card) and if `banned_terms` still fires on a *verb/noun* term, fail the section rather than ship it. A missing department is visible and honest; "underscores the vulnerability" is neither.
4. Add to the weekly prompts the line the daily opinion prompt already has: "Never reference outlet names, 'coverage,' 'sources,' or 'reporting patterns.'" (`weekly_digest_generator.py` COVER_SYSTEM 369, RECAP_SYSTEM 1123).
5. Extend `scripts/verify_sections.py` W-08 (currently: no em/en dash on served `/weekly`) with **W-09**: served `/weekly` visible text contains none of the shared kill regex outside `<blockquote>`/`<q>`.

#### F-04 · P1 · Nine production prompts carry no grounding line; the daily Opinion is one of them and today's Opinion shows why

**Observation.** CLAUDE.md: "Every LLM prompt carries: 'Every fact MUST appear in the provided articles. Do not supplement with prior knowledge.'" The exact string exists in two prompts. Equivalents exist in three more. Nine production prompts have no grounding sentence of any kind.

**Evidence** (prompt start line; grep window 4,000 chars for `prior knowledge|outside knowledge|MUST appear|only from the provided|do not invent`):
- `pipeline/briefing/daily_brief_generator.py:1283` and `:1388` (daily Opinion system + user): none. The prompt says "Synthesize the facts: do not cite where they came from" (1325) and "MUST use first-person plural 'we' at least 3 times" (1360), never "only the facts provided".
- `pipeline/briefing/weekly_digest_generator.py:749` OPINION_SYSTEM (bench columns), `:886` TECH_SYSTEM, `:934` SPORTS_SYSTEM, `:1123` RECAP_SYSTEM, `:1505` weekly audio, `:1826/1899` weekly editorial, `:1930` monologue rewrite: none. Only COVER_SYSTEM (369, grounded at 389) carries one.
- `pipeline/briefing/weekly_rundown.py:35`: none (by design it may only cut the published columns; acceptable, but say so in the prompt).
- Parked/dead/manual, listed for completeness: `analyzers/gemini_reasoning.py:73` (parked), `memory/live_poller.py:278` (reads dead Supabase), `social/ig_caption.py:233` (manual bundle, never posted).
- Today's Opinion (`brief.json` `opinion_text`): "It tells autocrats in **Beijing, Moscow, and Riyadh** that their own crackdowns on the press are ... justifiable" and "**We have seen this pattern before.** Governments that seek to consolidate power invariably begin by controlling the flow of information." Neither the three capitals nor the historical generalisation is in the 112-article cluster; they are model knowledge presented as editorial fact. Rule 1: "Silence beats a plausible reconstruction."

**Root cause.** The grounding line was added to the summary and TL;DR prompts (which write *news*) and never to the prompts that write *argument*, on an implicit view that opinion is exempt. CLAUDE.md does not exempt it ("Every LLM prompt"), and VOICE-BRAND V says opinion must "argue from the evidence in the stories". Nothing tests prompt text.

**Solution.**
1. Add the exact grounding sentence to all nine prompts, plus for opinion: "Argue only from facts in the provided stories. Historical parallels, other countries, and 'patterns' are not permitted unless a provided article states them."
2. Add `tests/test_prompt_grounding.py`: import each prompt constant (or regex the module source for `You are ...` blocks) and assert the grounding sentence is present in every production prompt. This is a five-line test that makes CLAUDE.md's claim true by construction.
3. For Opinion and Weekly editorial specifically, run E-13 (numbers in sources) and a proper-noun variant (every capitalised entity in the essay appears in the cluster texts) after generation; fail on a miss. The machinery exists in `pipeline/editorial/standard.py:616-690`.

#### F-05 · P1 · History served data carries 81 time-relative claims that will silently become false

**Observation.** Rule 1: "A number that goes stale is a future error. Do not publish a count that changes with time ('ten presidents', 'sixty-five years on') when a durable formulation exists." The History YAML contains the very example.

**Evidence** (`data/history/events/`, served verbatim in `frontend/public/data/history.json`; `summary` paragraph 1 also feeds `podcast-history.xml` descriptions):
- `cuban-revolution.yaml` summary: "**Sixty-five years on**, the question of whether January 1, 1959 was a liberation..." and "a trade embargo that **remains in force in 2026**"
- `chernobyl-disaster.yaml` summary: "remains largely uninhabited **in 2026**"; legacy[3]: "the 2,600 sq km exclusion zone persists **in 2026**"
- `chinese-civil-war.yaml` summary: "One question left open in 1949 is **still open in 2026**"; "survives **to this day**"
- `algerian-war.yaml` significance: "his party **leads French elections in the 2020s**"; "the Fifth Republic that **still governs** France"
- `congo-wars.yaml` summary: "**As of 2026**, eastern Congo has over 120 active armed groups"
- `bandung-conference.yaml` significance: "shapes the BRICS grouping ... **in 2026**"
- `apartheid.yaml` legacy[3]: "**remains** the world's most unequal country by Gini coefficient (0.63)"
- Distribution: summary 21, significance 40, legacy_points 20. Note `significance` and `legacy_points` are deliberately **not rendered** on the page (`frontend/app/history/components/Hearing.tsx:29-31`), so the reader-facing exposure is the 21 in `summary` plus the JSON itself.

**Root cause.** `tests/test_history_copy.py` gates dashes and speaker shape; `tests/test_history_data.py` gates identity, lifespans, attribution. Neither has a time-relative check, and the 2026-09-20 audit that produced them looked for false facts, not facts with an expiry date.

**Solution.** Add a third gate to `tests/test_history_copy.py`: fail any `summary`, `subtitle`, `legacy_points[]`, `significance` field matching `\b(in|as of|since) 20(2[4-9]|3\d)\b|\bto this day\b|\bstill (open|governs|leads|stands|in force)\b|\b(remains?|persists?) (in force|today|the (most|largest|only))\b|\b\w+(-\w+)? years (on|ago|later)\b(?! in \d{4})`. Allowed rewrite pattern, stated in the test docstring: anchor to a dated fact ("In 2024 the embargo entered its sixty-fourth year") or drop the clause. 81 fields to rewrite; the durable forms exist for all of them.

#### F-06 · P1 · The voice bible describes a retired product, and a production prompt still obeys it

**Observation.** `docs/VOICE-BRAND.md` is what the Quick Reference sends writers to for "Voice and brand". Of its 367 lines, 161 (sections III-IV host roster, IX shift schedule) describe six Gemini-TTS hosts on a 4-runs-per-day, 3-edition schedule. The pipeline is 1x/day, one edition, Kokoro. The doc never says "Kokoro".

**Evidence.**
- Title line 1: `# void --onair: Voice Brand Specification`
- Line 52: "**Gemini voice:** Kore (firm)"; line 60: "Charon (informative)"
- Line 241: "6 hosts, 3 editions, 4 runs/day. Every host works every day across the three editions."; line 272: "Full Day Schedule (4 runs × 3 editions = 12 broadcasts)"
- Section X "Quality Gates" claims six gates. Two exist in some form (prohibited terms, monologue/consecutive-lines). "Scaffolding scan", "Attribution check", "Disfluency cap" and "Line length under 100 characters" match nothing in `pipeline/` (`grep -rliE "disfluenc|\[uhm\]"` returns nothing). Line 327 claims "~100 banned phrases"; `pipeline/utils/prohibited_terms.py` holds 43.
- The doc uses the em dash 59 times while banning it in the product.
- Downstream: `pipeline/briefing/daily_brief_generator.py:1336-1337` (the live Opinion prompt): "the Investigator builds evidence chains, the Editor weighs historical patterns, the Realist challenges with counter-data" instructs Gemini to write as a host roster that has not existed since the Kokoro switch. `weekly_digest_generator.py:1460` still names "The Correspondent".

**Root cause.** The doc is rev 1 (2026-04-28) and was never revised through the Gemini-TTS retirement, the edge-tts interlude, the Kokoro adoption, the 1x/day cut, or the "Void News" rebrand. The real voice rules now live in three places the doc does not point to: `docs/ON-AIR-RADIO.md` (R-rules), `docs/HISTORY-SCRIPT-BRIEF.md` (H-rules), `docs/EDITORIAL-STANDARD.md` (E/S/F rules).

**Solution.** Rewrite VOICE-BRAND.md as rev 2: keep I, II, VII, VIII, XI (they are correct and good); delete III, IV, VI, IX (retired); replace X with a table that lists the gates that actually exist by ID and file (S-01..S-07, E-03..E-14, R-01..R-11, H-01..H-11, P-01..P-07, W-01..W-08) and say plainly what is unenforced (this report's section 6). Retitle "Void News: Voice". Remove the roster reference from the Opinion prompt (F-04 fix touches the same lines). Add VOICE-BRAND.md to `tests/test_docs_facts.py` so "Kokoro", "1x", and the gate count are checked against code.

#### F-07 · P2 · The Privacy page states a data-retention mechanism that no longer runs against live data

**Evidence.** `frontend/app/privacy/page.tsx` "Data retention" section: "Article text is retained for about a week, then removed by the daily cleanup job." Per CLAUDE.md, `db-cleanup.yml` "prunes a database nothing reads" (the decommissioned Supabase). Live article text is in `pipeline_state.db`, restored from the Actions cache and a 90-day artifact. Retention is therefore "about a week in the working database, up to 90 days in a CI artifact", not "about a week".

**Root cause.** Page dated "Last updated 2026-08-08", three weeks before the Supabase decommission. No test reads the privacy page against the workflow files.

**Solution.** Change the sentence to "Article text lives in the pipeline's working database for about a week (`cleanup_stale_articles(days=7)`), and a compressed snapshot of that database is kept as a build artifact for up to 90 days." Add a `tests/test_docs_facts.py` case: the retention days on the privacy page equal the `days=` argument in `pipeline/main.py` and the `retention-days` in `pipeline.yml`.

#### F-08 · P2 · Kill-list words are rendered by three live components

**Evidence.**
- `frontend/app/components/BiasInspector.tsx:562`: `"Headline is notably more sensational than the article body."`
- `frontend/app/components/DivergenceAlerts.tsx:78`: `"Sources differ significantly on framing"`
- `frontend/app/components/Sigil.tsx:624`: `"Sources disagree significantly on this story"`

**Root cause.** No gate scans `.tsx` string literals; `standard.py` runs on card text only, and `verify_production.py` runs on the served homepage where these strings appear only after interaction.

**Solution.** Rewrite: "Headline reads more sensational than the article body."; "Sources split on framing"; "Sources split on this story". Add a fourth check to `frontend/test/copy-facts.test.mjs`: no string literal or JSX text node in `app/**` (excluding `mock*`, `games/`, `revolt/`, `admin/`) matches the shared kill regex or contains U+2014/U+2013.

#### F-09 · P2 · Em dashes render on the History landing and in four accessible names

**Evidence.**
- `frontend/app/history/components/HistoryLanding.tsx:34-64`: era ranges `"3000 BCE — 500 BCE"`, `"500 BCE — 500 CE"`, `"500 — 1500"`, `"1500 — 1800"`, `"1800 — 1945"`, `"1945 — Present"` (six rendered strings).
- `EventCard.tsx:24`, `HistoryLanding.tsx:1451`, `HistoryOverlay.tsx:201`, `PerspectiveReader.tsx:77`: `aria-label={\`${event.title}: ${event.datePrimary}\`}` and similar (screen-reader output is written editorial output).
- `admin/ig/ReviewCard.tsx:27` (admin only).

**Root cause.** W-08 checks `/weekly` for dashes; nothing checks `/history` or component strings.

**Solution.** Era ranges: "3000 to 500 BCE", "1945 to present". Aria-labels: comma. Extend `verify_sections.py` H-rules with **H-05**: served `/history/` visible text and `aria-label` attributes carry no U+2014/U+2013. Same tsx scan as F-08 covers the source.

#### F-10 · P2 · `/pipeline` is served with Supabase-era copy and a "live polling" claim

**Evidence.** `frontend/app/components/PipelineFlow.tsx` (rendered by `app/pipeline/page.tsx`, metadata present, not in nav or sitemap):
- `:67` "Supabase pipeline_runs record: enables health monitoring and duration tracking"
- `:253` "Persist to Supabase · rank_world · global re-rank"
- `:293` "Tracks top story per run · detects narrative shifts · live polling between pipeline runs"
- `:232` "Gemini reorders the top 10 of the daily feed by editorial priority · currently disabled via DISABLE_EDITORIAL_TRIAGE env var" (the word "currently" is a stale-by-design claim)

Commit `cc49187` fixed three other lines on this page and left these.

**Root cause.** Orphan page: reachable by URL, covered by no test, not in the nav, so no one sees it.

**Solution.** Either delete the route (it duplicates `/about`'s pipeline section) or rewrite the four strings (`"SQLite state (pipeline_state.db)"`, `"Persist to state DB · rank_world"`, drop "live polling", drop "currently"). If kept, add it to the `copy-facts` scan and to `verify_sections.py`.

#### F-11 · P2 · The model is told it writes for "void --news"; the masthead says "Void News"; the nav says "Void History" and the brand rule says "History"

**Evidence.**
- 25 prompt strings: `daily_brief_generator.py:251` "You are the editorial voice of void --news", `:348`, `:1283`, `:1388` ("Write a void --opinion editorial"); `cluster_summarizer.py:212,214,270,291,398`; `gemini_reasoning.py:73`; `history/audio_script_generator.py:116` ("void --history"); `weekly_digest_generator.py:369,685,749,817,886,916,934,1058,1123,1505,1745,1826,1899,1930` ("void --weekly", "void --onair WEEKLY").
- `social/ig_caption.py:120` contradicts them: `NEVER write "void --news" or "void --history"; the brands are "Void News" and "Void History".`
- CLAUDE.md Brand: sections are "title case with plain names: The Brief, On Air, History, Weekly". But `NavBar.tsx:157` `"Void History"`, `:160` `"Void Weekly"`; `layout.tsx:77` `"Void Weekly: The Argument"`; `weekly/archive/page.tsx:27` "Void Weekly, the Sunday magazine from Void News"; all History/Weekly OG images; and 8 of 24 house promos end "check out Void History" / "check out Void Weekly" (`data/promos/house.yaml` promos 8, 10-17).

**Root cause.** The 2026-08-03 rebrand deliberately left internal identifiers; prompt strings and nav labels were treated as internal. A model given "void --news" as its identity produces terminal-flavoured copy on occasion and, more to the point, the brand has three spellings for the same section in public.

**Solution.** Decide once, in CLAUDE.md Brand, whether "Void History"/"Void Weekly" are permitted as programme titles (they read well in promos and podcast directories) or whether sections are bare. Then: sed the 25 prompt strings to "Void News"/"Void Weekly"/"Void History" (or "History"), and align `NavBar.tsx`, `layout.tsx`, the OG images and the promos to the decision. Add a `copy-facts` case that the chosen spellings are the only ones present.

#### F-12 · P2 · Podcast History descriptions lose a sentence boundary

**Evidence.** `frontend/public/podcast-history.xml` (description and itunes:summary, Vietnam episode): "the third foreign army they expelled in thirty years On August 4, 1964, the destroyer USS Maddox..." Source: `data/history/events/vietnam-war.yaml:3` `subtitle:` ends without terminal punctuation; `podcast_feed_generator.py:531-537` `_history_description` joins subtitle and summary with whitespace.

**Root cause.** S-03 (terminal punctuation) exists for feed cards and is not run on podcast descriptions; the join assumes the subtitle ends a sentence.

**Solution.** In `_history_description`, append "." to the subtitle when it does not end in `.!?`; run `s03_terminal_punctuation` on the composed description and fail the feed build on a finding. Add `tests/test_podcast_feed.py` (none exists) with this planted defect.

#### F-13 · P2 · On Air news segment asserts significance; audio text is never sanitised for anything

**Evidence.** `brief.json` `audio_script`, STORY 2: "This attack marks a **significant** escalation in the conflict." The radio prompt bans it (`radio_script_generator.py:628` "Never 'significant', 'notable'...") and R-05 checks a banned-phrase list; the sanitiser is skipped for audio fields by design (dash exemption), and with it the significance-word removal.

**Root cause.** The dash exemption for audio was implemented as "skip `sanitize_editorial_text` entirely" (`daily_brief_generator.py:1651` comment "Audio keeps em dashes (TTS prosody): never sanitized"), which also skipped the significance regex that has nothing to do with prosody.

**Solution.** Split `sanitize_editorial_text` into `strip_dashes` and `strip_significance`; apply the second to `audio_script`, `opinion_audio_script`, weekly audio and History scripts (H-rules already cover scripts, but the significance regex is cheap). Add `significant|notable|...` to R-05's phrase list as a hard fail.

#### F-14 · P3 · Hedges standing in for attribution on feed cards

**Evidence.** `feed.json` [9].summary and consensus[3]: "Defense Department staffers **reportedly** likened Jennifer to Yoko Ono"; [19]: "Charles **reportedly** hosted the Sussexes"; "King Charles has **reportedly** taken a more compassionate approach". E-05 accepts "reportedly" as attribution; VOICE-BRAND II says "Attribute or Abstain". "Reportedly" attributes to no one.

**Solution.** Add "reportedly", "allegedly", "is said to" to E-05's *non*-attribution set: a sentence carrying a reputational claim must name who reports it or be cut. Advisory first, then enforced.

#### F-15 · P3 · "Analysts argue" / "some argue" in History perspectives and Weekly

**Evidence.** `chernobyl-disaster.yaml` perspectives[4]: "pro-nuclear **analysts argue**"; `iran-iraq-war.yaml` perspectives[4]: "**many analysts argue**"; `suez-crisis.yaml` perspectives[4]: "**Some argue** that Eisenhower's financial coercion"; `mongol-conquest-baghdad.yaml` summary and script: "**Some sources say** he was forced to watch his sons killed first"; Weekly `opinions[4]` "**While some argue** that military action is necessary"; `[1] recap[3]` "**Critics argue**".

**Solution.** Extend `tests/test_history_copy.py` speaker-shape gate to prose: `\b(analysts|experts|critics|observers|some|many) (say|argue|believe|note)\b` in `summary`/`significance`/`perspectives[].narrative` fails unless followed within the sentence by a named person or work. Same regex into the shared kill list for Weekly.

#### F-16 · P3 · Second-person direct address in one History script

**Evidence.** `data/history/scripts/arab-spring.txt` OPEN: "N: You think you know how this one starts." The other 77 scripts open on a particular. H-rules do not cover person.

**Solution.** H-12: narrator lines (`N:`) contain no second-person pronoun outside a DOCUMENT/M: turn.

#### F-17 · P3 · No branded 404

**Evidence.** No `frontend/app/not-found.tsx` exists; Next.js default 404 is served on static export. Every other page carries the wordmark and "See through the void."

**Solution.** Add `app/not-found.tsx` with the masthead, one line in house voice ("Nothing here. The front page is one tap away."), and the standard back link. Add a served check for `/does-not-exist/` returning the wordmark.

#### F-18 · P3 · The Press page makes a promise and a solicitation

**Evidence.** `press/page.tsx:471` "Response time: we answer within a day."; `:55` "Ask us anything."; `:296-297` "Void, the company behind our news and audio work" (the boilerplate says "Void" is the parent brand; "company" is a legal claim CLAUDE.md does not make).

**Solution.** Cut the response-time line (a time-bound claim, Rule 1) or make it "Press questions are answered by the person who builds the product." Replace "company" with "the parent brand".

---

### 3. Bias-copy ordering check (required by CLAUDE.md)

**PASS on all three pages.**
- `/about`: `AboutExperience.tsx:90` "Void measures the spin, on six axes, from **both** the outlet's track record and the article's own words"; `AboutMission.tsx:27-28` "It reads two things: what the outlet has published before, and what this article actually says."
- `/sources#methodology`: `SourcesClient.tsx:562-568` heading "Two Things, Six Lenses" ... "Void News looks at two things instead ... **Both**, across six axes".
- `/press`: `press/page.tsx:189-191` "We do not judge a story by its outlet alone, and we do not judge it by its words alone. We use both."

One wobble: `SourcesClient.tsx:566` "No LLM calls." is true today only because `DISABLE_GEMINI_REASONING=1`; `PipelineFlow.tsx:181-184` on `/pipeline` describes the same Gemini reasoning path as "parked, off in production". Both are accurate; the sentence on `/sources` should say "No LLM in scoring" so a flag flip does not falsify it.

---

### 4. Register comparison: one newsroom or several?

One paragraph each, as served today.

**(a) Feed summary** (`feed.json` [1]): "North Korea launched two short-range ballistic missiles toward the sea on Sunday, according to South Korea's military. The launches occurred about three hours apart from North Korea's eastern coastal Wonsan area. The first missile flew approximately 450 kilometers (280 miles), and the second traveled more than 600 kilometers (370 miles), both landing in the North's eastern waters." Third person, past tense, attribution-first, 22-35 word sentences, zero adjectives, digits. Wire register.

**(b) TL;DR** (`brief.json`): "North Korea launched two short-range ballistic missiles toward the sea on Sunday. The launches occurred from the Wonsan area, with the first missile flying 450 kilometers and the second traveling more than 600 kilometers. Both missiles landed in the North's eastern waters." Identical register to (a); it is (a) shortened. One voice.

**(c) Daily Opinion** (`brief.json`): "This action is not an isolated incident of presidential pique. It is a calculated assault on the mechanisms of accountability, designed to normalize the suppression of independent reporting and to embolden authoritarian regimes worldwide. We have seen this pattern before. Governments that seek to consolidate power invariably begin by controlling the flow of information." First-person plural (mandated), present tense, evaluative adjectives ("calculated", "invariably"), generalisation beyond sources, scaffolding ("We have seen this pattern before"). Cable-editorial register.

**(d) On Air** (`audio_script` STORY 1): "House Majority Leader Steve Scalise says he does not know why President Trump banned the three news outlets. Representative Maria Elvira Salazar defends President Trump's move. She says he has his own style." Present tense, under-20-word sentences (R-11), attribution before claim (R-07), initials hyphenated. Distinctive, disciplined, and closest to the wire voice of (a). Same newsroom as (a)/(b).

**(e) Weekly cover** (Sep 14): "Danish and Greenlandic leaders immediately sought to reassure their publics that the arrangement would respect Greenland's right to self-determination and the sovereignty of the Danish kingdom. News outlets, drawing on 57 sources, reported Denmark's affirmation of its sovereignty following the announcement, highlighting the immediate tension between Washington's strategic ambitions and Copenhagen's constitutional responsibilities." 40-50 word sentences, nominalisations ("affirmation", "responsibilities"), participial tails ("highlighting..."), meta-reference to its own source counts, abstraction over particular. Generic LLM-magazine register. **(e2) Weekly tech dept**: "While the specifics remain nebulous, the underlying intent appears to be a top-down, nationalistic push..." Hedged, abstract, no number in the paragraph.

**(f) History event summary** (`algerian-war.yaml`): "At three in the morning on November 1, 1954, All Saints' Day, roughly 30 coordinated attacks struck police posts, barracks, and farms across Algeria. Seven people died. From Cairo, a radio broadcast announced a new organization, the National Liberation Front, and demanded the restoration of a sovereign Algerian state. The French Interior Minister, Francois Mitterrand, answered within days: Algeria is France, and the only negotiation is war." Arrives late, particular first, contested numbers published as ranges, no adjectives of significance. This is the brand as written in CLAUDE.md.

**(g) History script** (`algerian-war.txt`): "N: Three in the morning, November first, nineteen fifty four. All Saints' Day. / N: Roughly thirty coordinated attacks hit police posts, barracks, and farms across Algeria at once. Seven people die." Same voice as (f), present tense, numbers as words. Same writer.

**(h) House promo**: "It ends on a particular, not a moral. Visit news.voidvision.org to check out Void History." Two sentences, no digits, particular-first. Same writer as (f)/(g).

**(i) About**: "Every outlet covers the same events. Each one chooses the words, the order, the things left unsaid. That choosing is bias, and it is almost always invisible. Read one paper and you never see the tilt. Read a hundred and the tilt is all you see." Second person, short declaratives, aphoristic. On brand; one register shift (direct address) that is appropriate for the one page that speaks to the reader.

**(j) Press boilerplate**: "Void News is an independent daily news reader. Each day it gathers reporting from more than a thousand outlets across 158 countries, groups the coverage of each event together, and scores every story on six axes..." Institutional third person, list-heavy, correct except for the "fifty" (F-01). Fine for its purpose.

**Verdict: two newsrooms.** (a)(b)(d)(f)(g)(h)(i) are one house: concrete, attributed, short, arriving late. (c) and (e)/(e2) are a second house: abstract, hedged, adjectival, self-referential about "sources", and they are the two surfaces whose prompts lack the grounding line and whose output no deterministic sanitiser touches (F-03, F-04). The difference is not the writer's taste; it is which prompts carry the rules and which outputs pass through `sanitize_editorial_text`. The daily feed sits between: clean, but "wire-flat" with no arrive-late craft, which the summary prompt does not ask for.

Concrete differences, (f) vs (e): mean sentence length 17 words vs 41; adjectives per 100 words 2 vs 9; hedges per paragraph 0 vs 2; numbers per paragraph 6 vs 1; references to "sources/reports/coverage" 0 vs 2.

---

### 5. Doc drift that can cause future voice errors

Docs in CLAUDE.md's Quick Reference or otherwise likely to be read as current. One stale claim each (line numbers from `grep`).

| Doc | Title still says | Stale claim (current tense) |
|---|---|---|
| `docs/VOICE-BRAND.md` | `void --onair` | L52/60 "Gemini voice: Kore / Charon"; L241 "6 hosts, 3 editions, 4 runs/day"; L272 "12 broadcasts"; §X six gates (two exist); "~100 banned phrases" (43) |
| `docs/DESIGN-SYSTEM.md` | `void --news` | L39 "top-50 layout overhaul" section header presented as the current hierarchy |
| `docs/PIPELINE-BRAIN.md` | `void --news` | L34 "Create run record in Supabase"; L100 "Claude Sonnet 4.6 primary, Gemini fallback"; L166 "MP3 → Supabase Storage" |
| `docs/AGENT-TEAM.md` | `void --news` | L15/24 "Sonnet 4.6 API for editorial LLM (~57 calls/run)"; L28 "Database: Supabase free tier" |
| `docs/CEO-AGENT-GUIDE.md` | `void --news` | L66 "Run a full data quality audit on Supabase" as a live command |
| `docs/DEPLOYMENT.md` | `void --news` | CLAUDE.md already flags as pre-migration; L22 auto-merge section still describes migrations |
| `docs/HISTORY.md` | `void --history` | L20-21 "4 Supabase tables + Supabase Storage", "Mock data fallback when Supabase unavailable"; L170 "Data Model (Supabase)" |
| `docs/HISTORY-AUDIO-SPEC.md` | `void --history` | Supabase (2), void -- (3) |
| `docs/HISTORY-FRONTEND-SPEC.md` | `void --history` | Supabase (6) |
| `docs/VOID-HISTORY-DESIGN-SPEC.md` / `-PROPOSAL.md` | `void --history` | 48 and 27 uses of the terminal name; proposal names Gemini TTS |
| `docs/MUSICAL-ELEMENTS-SPEC.md` | `void --onair` | L88 "finds zero gaps in Gemini TTS output"; L506 "Speech from Gemini TTS arrives at -6 to -12 dBFS" (mastering numbers for a retired engine) |
| `docs/WEEKLY-AUDIO.md` | "void --weekly's audio edition" | title only; body is current |
| `docs/VOID-VERIFY.md` | `void --verify` | L11 "Product name: void --verify" (the section is "Deep Dive" claim consensus now) |
| `docs/PROJECT-CHARTER.md` | `void --news` | L31 "4x daily automated pipeline"; L36 "Static site on GitHub Pages, data in Supabase"; L57 "Pipeline completion < 6 minutes" |
| `docs/OPEN-ITEMS.md` | ok | L102 Revolt "falls back to MOCK_EVENTS when the browser Supabase client has no credentials" (correct as a description of dead code; fine) |
| `docs/GEMINI-VOICE-PLAN.md` | `void --news` | whole doc plans Claude + Gemini TTS; not marked historical |
| `docs/MEMORY-ENGINE-RUNBOOK.md`, `NEWS-MEMORY-ENGINE.md`, `DB-AUDIT-FRAMEWORK.md`, `DB-REVIEWER-GUIDE.md`, `DIAGNOSTIC-LAB.md`, `LAUNCH-PLAN.md`, `IP-COMPLIANCE.md`, `IMPLEMENTATION-PLAN.md`, `APP-BUILD-GUIDE.md`, `MOBILE-RELEASE.md`, `UI-STACK-ANALYSIS`, both ranking audits, both perf reports, `INDEPENDENT-REVIEW` | `void --news` | Supabase and/or Claude as current in each; these are dated reports and mostly read as such, but none carries a "historical" banner |
| `.claude/skills` (per listing) | `void --news` | `pressdesign`, `workflows`, `ship-queue` ("fetch triaged requests from Supabase") describe the terminal name and the dead DB |

Docs that are clean: `EDITORIAL-STANDARD.md`, `ON-AIR-RADIO.md`, `HISTORY-AUDIO.md` (one flagged line), `HISTORY-SCRIPT-BRIEF.md`, `PODCAST-DISTRIBUTION.md`, `CHANGELOG.md` (verbatim record, correctly so).

**Solution.** A one-line banner at the top of every doc in the last group ("Historical, predates the 2026-09-01 Supabase decommission and the Kokoro switch; see CLAUDE.md") and a `tests/test_docs_facts.py` case that any doc in Quick Reference contains neither "Supabase" nor "Gemini TTS" nor "4 runs" outside a line containing "retired|decommissioned|historical|was".

---

### 6. Fact controls: what exists, and where Rule 1 is unenforced

### Exists

| Gate | File | Scope | Runs |
|---|---|---|---|
| S-01..S-07 (link shape, length, terminal punctuation, quote balance, doubled word, abbreviation spacing, a/an) | `pipeline/editorial/standard.py` | feed cards | write time + served HTML |
| E-03 first person, E-04 orphan clause, E-05 reputational attribution, E-07 contested terms (adv), E-08 passive evaluation (adv), E-09 absence-of-info (adv), E-11 second person (adv), E-12 isolated sentence (adv), **E-13 numbers in sources, E-14 quotes verbatim** | same | feed cards | same |
| Dash + significance strip | `pipeline/utils/prohibited_terms.py` | feed cards, podcast XML descriptions | write time |
| Weekly: length band, 22 prohibited terms, dash strip; one regeneration then ship | `pipeline/briefing/weekly_parse.py` | weekly cover/depts/opinions/recap/editorial | write time |
| W-01..W-08 (issue number, week range, prerender, archive, **no dash on served /weekly**) | `scripts/verify_sections.py` | served /weekly | CI `verify-production.yml` |
| H-01..H-04 (catalog, prerender) | same | served /history | CI |
| ~22 structural/corruption/consistency checks incl. count match | `scripts/verify_production.py` | served homepage only | CI |
| R-01..R-11 (segments, quotes adv, numerals adv, clock, banned phrases, budget, attribution order, chapter length, kicker, voice share, sentence length) | `radio_script_generator.py` | On Air rundown | write time |
| H-01..H-11 (quote in sources, hedge said aloud, speaker named, etc.) | `pipeline/history/script_format.py` + `tests/test_history_script.py` | History scripts | test + write |
| History data: identity, lifespans, attribution; **dash gate with quote/title exemptions; speaker shape** | `tests/test_history_data.py`, `tests/test_history_copy.py` | History YAML | test |
| P-01..P-07 (two sentences, no digits, no dash/quote/!, address, duration) | `pipeline/briefing/house_promos.py`, `tests/test_house_promos.py` | promos | test |
| Copy facts: no "50 stories"/"top 50" literal; source and country counts match roster; ranking weights match engine | `frontend/test/copy-facts.test.mjs` | `.tsx/.ts` source | `npm test` in `auto-merge-claude.yml` |
| CLAUDE.md self-counts | `tests/test_docs_facts.py` | CLAUDE.md | test |

### Does not exist (Rule 1 unenforced)

| Surface | What is ungated | Finding |
|---|---|---|
| **Weekly prose** | AI-slop words (27 of 34 hits are off-list); any number-in-source (E-13) or quote-verbatim (E-14) check; entity grounding; the once-then-ship path | F-03, F-04 |
| **Daily Opinion** | No grounding line, no E-13/E-14, no entity check, no kill-list scan (it passes today by luck: "sends a clear signal") | F-04 |
| **On Air / weekly audio / opinion audio** | No claim-vs-summary check; R-02 advisory; significance words unstripped | F-02, F-13 |
| **Press page** | Not fetched by any served gate; the source gate's regex misses its two literals | F-01, F-18 |
| **About, Privacy, Listen, Feedback, /pipeline** | No served check; only the `1,016`/`158` literals are source-gated | F-07, F-10 |
| **History `summary`/`significance`/`legacy_points`** | Time-relative claims; "analysts argue" attribution shape in prose | F-05, F-15 |
| **Podcast XML** | No S-03 on composed descriptions; no test file at all | F-12 |
| **Frontend string literals / aria-labels** | No dash or kill-word scan | F-08, F-09 |
| **Prompts** | Nothing asserts the grounding line is present | F-04 |
| **VOICE-BRAND.md** | Nothing checks the voice bible against the code it describes | F-06 |
| **Served `/history` HTML** | No dash check (W-08 is weekly-only) | F-09 |
| **404** | No page, no check | F-17 |

The order to fix, by damage per hour: F-01 (two lines and one regex), F-04 (nine prompt lines and a five-line test), F-03 (one shared regex and one `if`), F-02 (one validator with a planted test), F-05 (one regex gate, then 81 rewrites), F-06 (a doc rewrite that stops the next writer from reproducing all of the above).

### Files referenced (absolute)

- `/home/user/void--news/frontend/app/press/page.tsx`
- `/home/user/void--news/frontend/test/copy-facts.test.mjs`
- `/home/user/void--news/frontend/public/data/brief.json`
- `/home/user/void--news/frontend/build-data/feed.json`
- `/home/user/void--news/frontend/build-data/weekly-issues.json`
- `/home/user/void--news/frontend/public/data/history.json`
- `/home/user/void--news/frontend/public/podcast-history.xml`
- `/home/user/void--news/frontend/app/components/BiasInspector.tsx`, `DivergenceAlerts.tsx`, `Sigil.tsx`, `PipelineFlow.tsx`, `NavBar.tsx`
- `/home/user/void--news/frontend/app/history/components/HistoryLanding.tsx`, `EventCard.tsx`, `HistoryOverlay.tsx`, `PerspectiveReader.tsx`, `Hearing.tsx`
- `/home/user/void--news/frontend/app/privacy/page.tsx`
- `/home/user/void--news/pipeline/briefing/daily_brief_generator.py`
- `/home/user/void--news/pipeline/briefing/weekly_digest_generator.py`
- `/home/user/void--news/pipeline/briefing/weekly_parse.py`
- `/home/user/void--news/pipeline/briefing/radio_script_generator.py`
- `/home/user/void--news/pipeline/briefing/podcast_feed_generator.py`
- `/home/user/void--news/pipeline/summarizer/cluster_summarizer.py`
- `/home/user/void--news/pipeline/utils/prohibited_terms.py`
- `/home/user/void--news/pipeline/editorial/standard.py`
- `/home/user/void--news/scripts/verify_production.py`, `verify_sections.py`
- `/home/user/void--news/tests/test_history_copy.py`, `test_docs_facts.py`, `test_weekly.py`, `test_radio_script.py`
- `/home/user/void--news/docs/VOICE-BRAND.md`
- `/home/user/void--news/data/history/events/cuban-revolution.yaml`, `chernobyl-disaster.yaml`, `algerian-war.yaml`, `vietnam-war.yaml`
- `/home/user/void--news/data/promos/house.yaml`

No files were modified. Scanner scripts and raw output are in the session scratchpad (`scan.py`, `scan2.py`, `fe.py`, `fe2.py`, `fe3.py`, `scan_out.txt`, `fe_out.txt`).
---

# Appendix D. Paper (the e-paper) relaunch audit

**Bottom line.** "The work is already done" is true for the CSS and layout (1,013 lines of finished broadsheet styling, print stylesheet included) and false for everything underneath it. The page's entire data layer is Supabase and returns nothing in the production build; the served page would be a masthead, a colophon and a PDF button with zero stories. The copy carries Rule 1 problems (fabricated datelines, a wrong source count, an invented weather line, a fake issue number) and six em dashes. It is a Medium job, not a redirect flip.

## What exists

| File | Lines | Role |
|---|---|---|
| `frontend/app/paper/PaperContent.tsx` | 721 | client page: masthead, article, fillers, classifieds, colophon, PDF button, data load |
| `frontend/app/paper/paper.css` | 1,013 | tokens, masthead, 3-zone grid, multi-column flow, 4 breakpoints, print |
| `frontend/app/paper/paperUtils.ts` | 264 | tier assignment, deck generation, datelines, fillers, zone distribution, edition config |
| `frontend/app/paper/layout.tsx` | 33 | loads Lora + Old Standard TT via `next/font/google` |
| `frontend/app/paper/page.tsx` | 15 | `<PaperContent edition="world" />` + metadata |
| `frontend/app/paper/[edition]/page.tsx` | 27 | per-edition route |

Design: self-described "1970s New York Times Broadsheet" (`PaperContent.tsx:32-36`). Masthead with two ears, nameplate "Void News.", `No. N / DATE / Free of Charge` row, an "Edition" nav with one link (`:272-312`). Front page grid `5fr 4fr 5fr` (`paper.css:212`), zones A and C multicol, zone B the lead; `FRONT_PAGE_CAP = 20` (`paperUtils.ts:161`). Section flow takes stories 21-60 (`paperUtils.ts:182`) and wire bulletins from 61+. Three joke classifieds (`PaperContent.tsx:446-474`), colophon, floating PDF button that calls `window.print()` (`:505-518`). Print block at `paper.css:939-1013`. Articles carry no link anywhere: `Article` (`PaperContent.tsx:331-413`) renders no `<a>`.

Last data-path change: rev 47 (2026-06-11), the comment at `PaperContent.tsx:533-535`. The Cloudflare migration and Supabase decommission did not touch Paper. `docs/OPEN-ITEMS.md` has no Paper entry. No test references Paper.

## Data path

```ts
// PaperContent.tsx:15
import { supabase, fetchClusterLeadImage } from "../lib/supabase";
// PaperContent.tsx:531
if (!supabase) { setIsLoading(false); return; }
```

`supabase` is null unless two `NEXT_PUBLIC_SUPABASE_*` vars are set at build (`lib/supabase.ts:40-55`); `deploy-cloudflare.yml:136-142` sets neither on purpose. Un-hiding today ships a masthead, "Setting type..." then nothing, colophon, PDF button. Three queries target decommissioned tables (`:538-543`, `:578-584`, `:589-595`).

Static exports already carry every field in Paper's `enrichedFields` select (`export_static.py:140-174`); `pipeline_runs.completed_at` maps to `feed.json.builtAt`; `daily_briefs.tldr_text` to `public/data/brief.json`. Missing fields: none. Three real gaps that are not fields:

1. Location: `build-data/feed.json` is read at build by a server component (`serverFeed.ts:84-86`); Paper is a client component that fetches at runtime. It has to become a server-read page like `app/page.tsx`.
2. Window: Paper asks for 150 rows; the export is the 35-cluster bench. Paper would print 15 stories the homepage deliberately excludes, against its own promise "The same stories, the same order" (`paper/page.tsx:8`) and the locked top-20.
3. Stale mapper: `buildStory` (`PaperContent.tsx:89-197`) forks `mapClustersToStories` from before the hygiene work: no `cleanFeedSummary`, no CSAM guard, no 3-source floor, no permalinks, and its own lean ladder (`leanLabel` at 29/46/53/72, `:218-224`) instead of the canonical `storyLeanLabel`.

## The `[edition]` route

`EDITIONS` contains only `world` (`lib/types.ts:372-374`). `generateStaticParams` returns a placeholder so `/paper/world/` prerenders as a metadata-less duplicate of `/paper/`. Dead edition code: `US_DATELINES`, `INDIA_DATELINES` (`paperUtils.ts:40-74`), `getSectionConfig`, `editionSubtitle`, `editionDisplayName`, `generateSubheads` (never imported).

Datelines are a Rule 1 problem: `getDateline` maps category to a city (Conflict → BEIRUT, Tech → TOKYO, Environment → NAIROBI, default LONDON; `paperUtils.ts:52-62, 91`) and every article opens with it (`PaperContent.tsx:401`). A Ukraine story datelined BEIRUT is a published factual error.

## Brand fit

Own tokens (`--np-paper #F4F1EC`, `--np-ink`, `--np-rule`; `paper.css:9-39`), own fonts (Lora, Old Standard TT; `paper/layout.tsx:24-35`), Inter for labels instead of the house meta face. No NavBar, no Footer, no topbar, no theme toggle; the only way out is the colophon link at the bottom (`:495-497`). Textures explicitly removed (`paper.css:57-61`). It is a fourth look and a period pastiche; the ear copy "An ode to simpler times. A quiet pursuit of balance." (`:275`) and the joke classifieds are a different voice.

## Copy defects (Rule 1)

- "200 curated news organisations" (`paperUtils.ts:128`, `PaperContent.tsx:452-453`); the site says 1,016.
- "No editorial judgments were made" (`:454-455`); Stage 2 is an editorial pass.
- "twice daily" (`:443`) and "Next edition at dawn" (`:469`) against the 11:00 UTC cadence.
- A "Weather forecast" joke (`:469-471`), a boilerplate editor's note (`paperUtils.ts:135`).
- Issue number computed from an arbitrary epoch of 2026-03-01 (`PaperContent.tsx:253-256`); masthead date is the viewer's local date (`:242-250`).
- Six em dashes (`PaperContent.tsx:213, 281, 401, 450, 459, 467`; `paperUtils.ts:120`).

## Effort to relaunch on static JSON

| # | Step | Size |
|---|---|---|
| 1 | Server-read data path: `paper/page.tsx` becomes async, calls `fetchInitialFeed()` and `getInitialBrief()`, passes `stories.slice(0, FEED_DISPLAYED)`, `builtAt`, `tldr_text`. Delete the Supabase import, `buildStory`, the three queries, the loading state. | M |
| 2 | Collapse editions: delete `[edition]/page.tsx`, the `edition` prop and the dead dateline/section/subhead code. | S |
| 3 | Rule 1 copy pass: remove city datelines, fix the source count, cadence, issue number, weather joke, em dashes; swap `leanLabel` for `storyLeanLabel`; link each article to `story.permalink`. | M |
| 4 | Un-hide and navigate: remove `_redirects:39-40`, add `/paper/` to `sitemap.ts`, Footer, side panel, masthead; add a topbar in the Weekly pattern. | S |
| 5 | Served-output checks in `scripts/verify_sections.py`: P-01 200 at `/paper/`; P-02 exactly `FEED_DISPLAYED` articles whose headlines equal the homepage's in order; P-03 no dashes; P-04 no city dateline or "200 curated". | S |
| 6 | Mobile pass: single column below 768px (multicol at 767px is a column jump on a phone, `paper.css:793+`). | S-M |

Overall M: roughly one focused engineer-day for steps 1-5. Nothing in the pipeline changes.

## Redundancy, both sides

Against: a third daily presentation of the same twenty summaries next to the home feed and The Brief (the TL;DR would appear on three pages); no per-source rows, no sigils, no links; every editorial defect gains a second served surface, and `verify_production.py` runs only against `/`. A fourth visual register on a site whose design is locked.

For: the only artefact meant to be printed; it literalises the locked principles (one front page for everyone, dated, numbered, once a day) better than any other page; cheapest surface to restore because it is pure presentation over `feed.json`; with permalinks it becomes a second crawlable path into the archive.

---

# Appendix E. Instagram-to-site funnel and identity system (audit detail)

## Social generators

Format: every track is a 3-slide 1080×1350 carousel (`frontend/app/styles/ig-render.css:59-60`): hook (dark ink `#14120F`), substance (cream / archival / weekly paper), CTA (dark ink). Every slide carries a corner stamp Sigil + "VOID <WORD>" (`frontend/app/ig/render/templates/LogoMark.tsx:69-88`). Accents: terracotta `#B26F52` (News), umber `#A07A54` (History), red `#D24334` (Weekly) (`ig-render.css:85-96`). The three families share one visual system.

| ID | Sev | Finding |
|---|---|---|
| E-01 | P0 | The IG pipeline is wired to the decommissioned Supabase and cannot generate anything. Root cause: rev 63 ported pipeline call sites through `VOID_SQLITE_PATH` but not the social pipeline. Evidence: `.github/workflows/ig-pipeline.yml:120-123,143-147`; `pipeline/social/ig_generator.py:1128-1131` (`supabase.table("ig_posts")`), `:1329` (`weekly_digests`); `frontend/app/ig/render/[postId]/page.tsx:152-153` → `lib/supabase-server.ts:207-210`. Skills still say "Migrations 073 + 074 must be applied" (`.claude/skills/void-social/SKILL.md:52`, `history-social/SKILL.md:47`, `weekly-social/SKILL.md:47`). Fix: re-source the generators from the deploy tree (`public/data/history.json`, `build-data/weekly-issues.json`, `build-data/archive.json`); write drafts to a local file the render route reads; drop Supabase steps. |
| E-02 | P1 | No post deep-links to what it advertises. `ig_generator.py:75-78` fixes `URL_HOME`, `URL_HISTORY = ".../history"`, `URL_WEEKLY = ".../weekly"`; the History CTA (`:1240-1246`) carries `event_slug` yet links `URL_HISTORY`; Weekly CTA (`:1357-1361`) has no `week_start`; Example CTA (`:1103-1107`) uses `URL_HOME`. Captions are told to end with the section root (`ig_caption.py:139,204,211`). Fix: `/history/<slug>`, `/weekly/<week_start>`, `/story/<id>`; root URL only on Vision/Method posts. |
| E-03 | P1 | Caption prompt publishes a false fact and a contradictory brand model: `ig_caption.py:100` "the same 50 stories, in the same order" (feed is 20), "sister products: Void History … and Void Weekly"; `:120` "the brands are 'Void News' and 'Void History'". Fix: interpolate `feed.json`; use the section wording. |
| E-04 | P2 | Weekly posts and the podcast number the issue differently from the site: `weekly/format.ts:76,129` (Vol. I, No. N, `WEEKLY_LAUNCH_ISSUE = 26`), `ig/render/templates/Weekly.tsx:26-28` (`Issue #${n}`), `podcast_feed_generator.py:448` (`Issue #{no}`). Live: `/weekly/` says "Vol. I, No. 1: Greenland's Arctic Calculus"; `podcast-weekly.xml` item says "Issue #26: Trump Mocks Banned Reporters…". Same issue, two numbers, two cover headlines. |
| E-05 | P2 | No section handles or hashtags; footer has no social links (`Footer.tsx:44-58`); `cross_post.py:17` documents a Bluesky handle that is not the live one. |
| E-06 | P3 | Preferred history events hard-coded (`ig_generator.py:1118-1123`); the workflow exposes no `event` input. |

## Identity marks in production (separate implementations)

1. `SigilWordmark` "V[◎]ID NEWS" (`components/SigilWordmark.tsx`), wrapped by `LogoFull`/`LogoWordmark`.
2. `ScaleIcon` footed Sigil (`ScaleIcon.tsx`, favicon.svg, icon.svg, apple-touch-icon.svg), brass `#946B15`.
3. IG `LogoMark`/`HeroSigil`: a re-drawn Sigil + "VOID <WORD>" stamp (`ig/render/templates/LogoMark.tsx:33-64`), not the shared component.
4. Composed OG card: letter-spaced plain text "VOID WEEKLY"/"VOID HISTORY" on paper, no Sigil (`lib/ogCard.tsx:80-82,119-130`).
5. `og-image.png`: dark, footed Sigil, "VOID NEWS", "AN EXPERIMENTAL NEWSROOM", 5-dot spectrum.
6. Podcast cover JPG: `void --onair`, "WORLD BRIEF", "409 sources" (`public/podcast-cover-world.jpg`).
7. `ShareCard.tsx` and `shareCardRenderer.ts`: "Void" serif + " News" mono, amber `#C8A96E`. No importers; dead code carrying a seventh identity.
8. Press-kit SVGs `public/brand/logos/void-{news,history,weekly,vision}-*.svg` plus legacy `public/logo-full.svg` and `public/logo-concepts/01..05`.

Accent drift: History umber `#5C4033` (tokens light, OG), `#8B7355` (tokens dark), `#A07A54` (IG); Weekly red `#B91C1C` (tokens, OG), `#D24334` (IG), `#EF5350` (dark).

| ID | Sev | Finding |
|---|---|---|
| E-07 | P1 | History and Weekly are rendered as products wherever a mark is drawn; CLAUDE.md and rev 60 define them as sections. `SigilWordmark.tsx:8-10` ("swappable product slot"); `NavBar.tsx:148,156,158,161`; `HistoryTopbar.tsx:7-8,38-44`; `WeeklyIssue.tsx:196,222-229`; `IssueIndex.tsx:81-90`; `RevoltTopbar.tsx:14` `product="REVOLT"`; `GamesHub.tsx:214` `product="GAMES"`. Root cause: rev 51 built the spinoff nav under the `void --history` sub-brand model; rev 60 rebranded copy but left the row; rev 69 restored it verbatim. |
| E-08 | P1 | Naming inconsistent across surfaces (live-verified): titles say section (`historyMeta.ts:39`, `onair/page.tsx:7`, `listen/page.tsx:11`); Weekly's say product (`issueMeta.ts:28`, `weekly/archive/page.tsx:22` whose description says "the Sunday magazine from Void News"); nav eyebrow says parent ("Also from Void"); OG cards say VOID HISTORY / VOID WEEKLY; podcasts mix models: "Void News: On Air", "Void Weekly: The Argument", "Void News: History" (`layout.tsx:76-78`, `podcast_feed_generator.py:80,92,108`); Listen files The Argument under `section: "Weekly"`; the press kit ships `void-history-*`/`void-weekly-*` lockups but lists only News + Vision (`press/page.tsx:316-376`). |
| E-09 | P2 | Two OG systems, no per-story card: sections use the composed paper card without Sigil; everything else the dark `og-image.png`; `/story/<id>` uses the site card (`story/[id]/page.tsx:126-140`); `/weekly/archive/`, `/onair/`, `/listen/`, `/press/` fall back to it; `/press/` serves og:title "Void News. See through the void." |
| E-10 | P3 | Dead identity files: `ShareCard.tsx`, `shareCardRenderer.ts`, `public/logo-full.svg`, `public/logo-concepts/*`, `public/games-logo.svg`, `podcast-cover-us.{svg,jpg}`. |

## Landing quality per advertised destination (live)

| Route | First thing seen | One-line "what this is" in HTML? | Path onward | OG image |
|---|---|---|---|---|
| `/history` | VOID HISTORY topbar, then nothing: served `<main>` is empty, `HistoryClient` fetches in an effect (`history/page.tsx:18-19`, `HistoryClient.tsx:5,62`); no `<h1>` | No | Only "← Back to Void News" | Composed card |
| `/history/<slug>` | Title, standfirst, "Five accounts" | Yes | Next event; back | Composed card |
| `/weekly` | Cover, nameplate, "Vol. I, No. 1" | Issue line only | Only `href="/"` (`WeeklyIssue.tsx:217`); The Argument is embedded but no link to `/listen` | Composed card |
| `/weekly/archive` | Issue index | Yes | back only | Site card |
| `/onair` | `<h1>` "The Broadcast" | Meta only | No links to `/listen`, `/weekly`, `/history` | Site card |
| `/listen` | "Void News / Listen", three shows | Yes | Links to each section | Site card |
| `/story/<id>` | Headline, analysis | Yes | "Go to today's feed"; Share copies title+URL only | Site card |
| `/about` "Where to next" | "Everything on Void" map | | Lists Feed, Sources, On Air, Feedback; omits History, Weekly, Listen (`about/beats/BeatVerdict.tsx:26-34`, whose comment says "every live destination") | Site card |

## Press kit (`frontend/app/press/page.tsx`)

- E-13 (P1): the page contradicts itself on feed size. `BOILER_SHORT` reads `FEED_DISPLAYED` (`:17`) but `BOILER_LONG` (`:20`) says "The fifty most important stories"; the fast-facts ledger (`:80-81`) says `50 / Stories in one daily edition`; `:128-129` renders "fifty". This is labelled "Approved language … Copy it as written" (`:101`).
- E-14 (P2): the kit sells only the feed. No History, Weekly, On Air, The Argument, podcast feeds or Listen; no podcast cover or square asset; History/Weekly lockups exist in `public/brand/logos/` but are unlisted; a "Void Vision logo" is offered for a product CLAUDE.md calls "coming".

## Podcast distribution

- E-16 (P0): all three shows ship one cover and it is pre-rebrand and factually stale. All three XMLs carry `<itunes:image href=".../podcast-cover-world.jpg">`; `podcast_feed_generator.py:192-198` falls back to the world JPG; live HEAD: `podcast-cover-weekly.jpg` 404, `podcast-cover-history.jpg` 404. The JPG reads `void --onair`, `WORLD BRIEF`, `409 sources`. The SVG source says "1,016 sources", so the raster was never re-rendered.
- E-17 (P1): channel titles use two brand models ("Void News: On Air", "Void Weekly: The Argument", "Void News: History"); author/owner is "Void News" on all (`:67`), so the middle title contradicts its own author. Weekly/History SVG covers say lowercase "void weekly"/"void history", a fourth rendering.
- E-18 (P2): world and weekly feeds carry one item each (item counts 1/1/73); the weekly item's title does not match the served issue.
- E-19 (P3): no RSS-level `<image>`; `podcast-us.xml` is 404 live but `podcast-cover-us.*` remain.

---

# Appendix F. First-hand measurements (2026-09-21, live site and local render)

All fetched with curl against `https://news.voidvision.org` unless noted. Screenshots were taken from a local `next dev` render of the same commit (the sandbox cannot present the proxy certificate to Chromium); Wikimedia hotlinks return 400 in the sandbox, so image tiles rendered empty locally and were not judged.

## Served page weight (uncompressed, as served)

| Route | HTML | of which RSC payload | CSS linked | JS linked |
|---|---|---|---|---|
| `/` | 328 KB | 190 KB (61 chunks) | 330 KB in 5 files | 959 KB in 11 files |
| `/history` | 59 KB | 40 KB | 507 KB in 6 files (history.css alone 177 KB) | 1,066 KB in 13 files |
| `/weekly` | 231 KB | 132 KB | 363 KB in 6 files | 904 KB in 10 files |
| `/sources` | 1,013 KB | 252 KB | | |

Every route loads the same 137 KB, 105 KB, 47 KB and 38 KB stylesheets regardless of section; History adds its own 177 KB on top. Source: 50,805 lines of CSS in `frontend/app/styles/*.css` plus `globals.css`.

## Page titles and metadata (served)

| Route | Status | `<title>` |
|---|---|---|
| `/` | 200 | Void News. See through the void. |
| `/history` | 200 | History \| Void News |
| `/history/threads` | 200 | Void News. See through the void. (root fallback) |
| `/weekly` | 200 | Vol. I, No. 1: Greenland's Arctic Calculus · Void Weekly |
| `/weekly/archive` | 200 | Every issue · Void Weekly |
| `/onair` | 200 | On Air \| Void News |
| `/listen` | 200 | Listen \| Void News |
| `/sources` | 200 | 1,016 Sources \| Void News |
| `/ship`, `/feedback` | 200 (301) | Feedback \| Void News |
| `/press`, `/privacy` | 200 | Press \| Void News, Privacy \| Void News |
| `/pipeline` | 200 | Pipeline Flow \| Void News ("Every step of the daily Python pipeline") |
| `/command-center` | 200 | Command Center \| Void News ("CEO operational dashboard") |
| `/paper`, `/games`, `/revolt` | 301 → / | |
| `/ig`, `/film`, `/admin` | 404 | |

## Dashes on served pages

Zero em or en dashes in the served HTML of `/`, `/history`, `/weekly`, `/about`, `/onair`, `/listen`, `/press`, `/privacy`, `/ship`. One on `/sources`. The dash rule holds on the page; the podcast cover raster and the Paper source do not (see Appendix D and E).

## Bias scores that drive the product (today's deep-dive exports)

`frontend/public/data/deepdive/*.json`, 35 files, 737 per-article bias rows:

| Tuple (lean, sensationalism, opinion_fact, rigor, confidence) | Rows |
|---|---|
| (50, 10, 25, 50, 0.7) | 540 |
| (50, 10, 25, 50, 0.15) | 53 |
| (80, 10, 25, 50, 0.15) | 11 |
| (35, 10, 25, 50, 0.15) | 11 |

73% of the rows behind the served Deep Dives carry the exact default tuple. This confirms finding 1 of `docs/proposals/NEXT-LEVEL-2026-09-20.md` (step 6b in `pipeline/main.py` overwrites measured scores with defaults for the 36-hour lookback articles) and it is listed in `docs/OPEN-ITEMS.md` as blocked on a CEO decision. Every "Flat" caption, every cluster mean and every archived lean sits on top of this.

## Masthead dateline disagrees between pages

`NavBar.tsx:60`: `const dateline = editionDateline ?? (mounted ? getEditionDatelineUTC(editionBuiltAt) : "")`, and `getEditionDatelineUTC(null)` falls back to now. The home page passes the build-time dateline (`HomeContent.tsx:798-799`) and rendered "Sep 20, 2026 · as of 8:00 PM UTC". `OnAirPage.tsx:96,170` passes a client-fetched `editionBuiltAt` that starts null, so the same masthead on `/onair` rendered "Sep 21, 2026 · as of 2:00 AM UTC" at 02:10 UTC on 2026-09-21: the sandbox clock, labelled "as of", above a card dated "September 20, 2026". The masthead claims a freshness the edition does not have.

## History era chips on phones read "WORLD AGE WORLD PERIOD ERA WORLD"

`HistoryLanding.tsx:997`: `{(ERA_CONTEXT[era.id]?.label || era.label).split(" ").pop()}`. The six era labels end in World, Age, World, Period, Era, World, so three chips say WORLD. Observed in the 390px render.

## The experimental banner collides with the section topbars

`experimental.css:103` offsets only `.nav-header` for the banner. History and Weekly mount their own bars (`hist-topbar`, `wk-topbar`) with no offset rule. In the 1440px render of `/history` the era title "The Contemporary World" sat under the topbar; in the 390px render the banner was not visible at all on `/history` while it was on `/weekly` and `/`.

## Same programme, four play affordances

Home: floating pill "On Air · Headlines · 13m" (bottom left). `/onair`: a second, teal console for the same file, plus the floating pill. `/weekly`: red floating pill "Weekly · The week · 23m" overlapping the section bar. `/history/<slug>`: a rectangular "LISTEN · 5 accounts · 14:02" chip. On `/onair` the card says "13 min" and the scrubber says "12:16" for the same episode, and the card is labelled "WORLD EDITION" fifteen weeks after editions were collapsed (rev 46).

## First viewport, desktop home (1440×900)

In order: the experimental banner ("Tell us what breaks."), a masthead carrying three wordmarks (VOID NEWS, VOID HISTORY, VOID WEEKLY) plus a badge, a tagline, a dateline and three page links; a two-column skybox (The Brief in sans, Opinion in italic serif with a "PROGRESSIVE" badge); a "TODAY'S TOP STORIES" rule; two equal-weight lead stories; six sigils each showing a number, a colour and the caption "Flat". The first headline begins 380px down the page. On the 390px render the captions are absent, so the same sigil reads "Flat" on desktop and nothing on a phone.

## Other session in flight

Branch `claude/radio-news-production-rt8eu0` (auto-merged to main) has, since 2026-09-20: a History dash pass over 1,668 YAML fields, a server-rendered Hearing for `/history/[slug]`, an `overflow-x: clip` rule that fixed a rail and topbar that had never pinned, a weekly back-issue index fix, nine gates wired into CI, and a `docs/DESIGN-SYSTEM.md` addendum (sections 15-16). Five commits were not yet on main at the time of this audit. Nothing in them changes the findings above; the History landing is still client-rendered and `verify_production.py` still has no History checks (their own OPEN-ITEMS entry says so).

---

