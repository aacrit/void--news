<!-- Research and plan by a planning agent, 2026-09-26, for findings 4 to 10 of docs/audits/UX-PASS-FRONTPAGE-DEEPDIVE-2026-09-26.md. Line numbers are against 6e2921d. -->

# Deep Dive redesign plan: audit findings 4 to 10

> **Status, 2026-09-26: built** on `claude/dreamy-einstein-22owl7`. PR 1
> (address, lead kept, row split, focus, Esc, keys), PR 2 (sticky bar, the
> ending on all three shells, the static page walking its own edition), PR 3
> (paragraphs, measure, drop cap, the Brief), PR 4 (CoverageList, ComparativeView
> and its CSS deleted, `leanUnscored` and headlines carried to `/story/`), PR 5
> (legend from `LEAN_SHAPE_LEGEND`, on phones and in the Deep Dive) and PR 6
> (no number in the dial, "N measured") shipped together, each with the headless
> scenarios in section E. **Not done:** C5's internal extraction
> (`DeepDiveBody`, `lib/deepDiveSources.ts`); the three shells still carry
> their own fetch-and-map and body markup, now sharing `DeepDiveSummary`,
> `CoverageList` and `DeepDiveNext`. R2 (pipeline paragraphs) and rung filter
> tabs stay deferred as planned. Finding A.3 (publisher summaries in
> `public/data/deepdive/`) is open and needs an owner.

Scope: `docs/audits/UX-PASS-FRONTPAGE-DEEPDIVE-2026-09-26.md` findings 4 to 10 only. Not covered here, because another engineer is on them: `Sigil.tsx`, `MobileSidePanel.tsx`, `app/lib/utils.ts`, `StoryCard.tsx`/`animations.css` (the no-JS fix), and polish items 11 to 20. Where this plan has to touch or overlap their files, section H says so.

Paths are relative to `/home/user/void--news/frontend` unless shown as absolute. Line numbers are from HEAD `6e2921d`.

---

## Summary

**Recommendation:** keep the inline Deep Dive on desktop, but give it a real address. Open it in place below the row it came from. Push the story's existing static permalink (`/story/<id>/`) as a shallow history entry, so the URL, the title, Back, reload and copying the address bar all behave the way a reader expects. Pull the body of the three Deep Dive shells into one shared component so they stop drifting apart.

**Shipping:** six PRs, landed one after another because of the one-branch rule. The first three fix navigation and reading comfort. The next two put the original coverage up front and make the legend match the cards. The last (the dial number) waits for the other engineer's Sigil work.

**Check these before building, because they change what the audit said:**

1. **The "role=dialog aria-modal=false" in finding 5 is probably not the Deep Dive.**
   - `InlineDeepDive` renders `<article aria-label>` (`InlineDeepDive.tsx:545`). It has no dialog role at all.
   - The only element that fits is the menu drawer, which is always mounted with `role="dialog" aria-modal={open}`, so it reads false while closed (`MobileSidePanel.tsx:388-392`).
   - That file belongs to the other engineer. Pass it on; do not "fix" the Deep Dive for it.
2. **A likely factual error that this plan fixes by construction (Rule 1).**
   - `ComparativeView` sorts every source by `politicalLean` into three buckets at 40/60 (`ComparativeView.tsx:30-34, 67-76`).
   - A source whose lean was never measured is stored as 50, so it gets printed under **Center**. The `leanUnscored` flag is carried on the live path but ignored by this component.
   - The archive mapper drops the flag entirely (`lib/archive.ts:231-261`), so `/story/<id>/` pages have the same problem.
   - I found this by reading the code, not on the live page. Verify it there before calling it a defect.
3. **Out of scope, but it needs an owner: publisher prose in the committed tree.**
   - In `public/data/deepdive/*.json`, 832 of 1,034 article rows carry a publisher `summary` longer than 12 words.
   - The frontend never renders `articleSummary`, but the text ships in the public tree. That conflicts with the IP control that `tests/test_grounding.py` enforces for `build-data/grounding`.
   - Proposed fix: `pipeline/export_static.py:319-393` stops writing `article.summary`, with a gate in the same commit.
4. **The mobile pager does not actually scroll away.**
   - `.dd-page__bar` is `position: sticky; top: 0; z-index: 4` (`styles/deep-dive-page.css:24-34`).
   - The masthead is also `sticky; top: 0` with a higher `z-index: var(--z-nav)` (`styles/components.css:987-989`).
   - So the bar does stick, but underneath the masthead, which reads as "gone". It is a one-line fix plus a better sticky check.
5. **The desktop shortcuts overlay tells the reader something false.**
   - It lists "← → Prev/next story" (`KeyboardShortcuts.tsx:16`).
   - Only the mobile Deep Dive handles arrow keys (`DeepDive.tsx:434-447`). The desktop inline one handles only Esc (`InlineDeepDive.tsx:497-507`).
   - The current `shortcuts` headless scenario only checks that O and / are listed, so nothing catches it.

---

## A. How it works today

### Three Deep Dive shells, each with its own copy of the body

| Shell | When it is used | File | How it opens | Address |
|---|---|---|---|---|
| Inline accordion | 768px and wider | `components/InlineDeepDive.tsx` (742 lines) | `HomeContent` puts it into the feed; it grows from zero height (`:383-449`) | None. The URL stays `/` and the title is the tagline |
| Full-page "next screen" | Under 768px | `components/DeepDive.tsx` (645 lines) | `HomeContent` returns it instead of the feed (`HomeContent.tsx:796-809`) | `pushState({voidDeepDive:true}, "")` with **no URL** (`DeepDive.tsx:420-426`) |
| Static permalink | `/story/<printed id>/` | `story/[id]/page.tsx` feeding `components/StandaloneDeepDive.tsx` (239 lines) | A real page, prerendered for every archive row (1,671 today) | Canonical. Title is `${title} \| Void News` (`page.tsx:121`) |

**Duplicated code:**
- `InlineDeepDive.tsx:167-356` and `DeepDive.tsx:224-406` are the same roughly 180-line fetch-and-map routine for `/data/deepdive/<clusterId>.json`.
- The disputed-claim highlighter also exists twice: `DeepDive.tsx:105-158` and `SummaryWithContradictions.tsx`.

**The same fact, counted differently per shell:**
- The source count in the meta line is `sources.length` after de-duplication on the live shells (`InlineDeepDive.tsx:517`, `DeepDive.tsx:477`).
- On the permalink page it is `story.source.count` (`StandaloneDeepDive.tsx:68`).
- The Source Perspectives gate also differs: live shells hide it behind a button, the permalink page always shows it (`StandaloneDeepDive.tsx:223-234`).

**Data shape, confirmed on disk:**
- `build-data/feed.json` has `{clusters, builtAt}` with 35 clusters.
- `summary` is **one string with no line breaks**, 162 to 342 words on today's twenty. The Senate story is 326 words.
- The pipeline prompt asks for 200 to 300 words, with a 350 ceiling (`pipeline/summarizer/cluster_summarizer.py:339-381`).
- Several post-processing steps rejoin sentences with a single space (`:590-601`, `:644-652`). So any paragraph break the model wrote would be thrown away today.
- The daily Brief, by contrast, is paragraphed with blank lines and split by `lib/briefText.ts:splitBriefParagraphs`.

**Which ids exist:**
- Each story's id is the cluster id.
- `story.permalink` is `/story/<printed id>/`, attached at build from `build-data/archiveMap.json` (`lib/serverFeed.ts:106-122`). The build fails if a displayed story has no permalink.
- Live per-source rows (`public/data/deepdive/<clusterId>.json`) carry article titles. The archive rows (`members`) carry only `source_name, url, lean, rigor, confidence, tier, published_at, lean_unscored`, with **no titles**.

### Finding by finding

- **Finding 4 (the top story disappears).**
  - `HomeContent.tsx:932-949`: `inlineInLead ? <InlineDeepDive/> : <div className="lead-twin">…`. Opening either lead swaps out the whole two-lead block, including the `<h1>` (`LeadStory.tsx:50`).
  - For grid cards (`:960-984`), the grid is split at the card's position in the list, not at the end of its visual row. The opened card itself is removed, and the cards after it in the same row drop below the Deep Dive.
- **Finding 5 (no address, broken Back, lost focus).**
  - Open: `handleStoryClick` (`:243-247`) only sets state.
  - Close: `handleInlineCollapse` (`:260-271`) sets state and scrolls. It never puts focus back on the card.
  - The Deep Dive puts focus on its headline button when it opens (`InlineDeepDive.tsx:509-515`). When it unmounts, focus falls to `<body>`.
  - The Esc listener is on `document` and checks nothing (`:497-507`). So Esc pressed to close a Sigil popup, the legend or the On Air panel also collapses the Deep Dive.
  - The card link's `preventDefault` (`LeadStory.tsx:95-100`, `StoryCard.tsx:62-70`) is what keeps the URL at `/`.
- **Finding 6 (no next story).**
  - Desktop toolbar: Share and Close only (`InlineDeepDive.tsx:547-568`).
  - Mobile has prev/next and a counter (`DeepDive.tsx:494-516`), fed by `handleDeepDiveNav` (`HomeContent.tsx:275-284`), but only in the top bar that the masthead hides.
  - The permalink page has "Go to today's feed" only (`StandaloneDeepDive.tsx:125-144`).
  - J/K are switched off while a Deep Dive is open (`KeyboardShortcuts.tsx:147`). Lead cards have no `data-story-index` (`LeadStory.tsx:81-85`), so J/K cannot scroll to stories 0 and 1.
- **Finding 7 (wall of text).**
  - One `<p>` in all three shells (`InlineDeepDive.tsx:616-624`, `DeepDive.tsx:553-558`, `StandaloneDeepDive.tsx:168-175`).
  - The width cap is switched off on purpose: `inline-dd.css:179-187` sets `max-width: none` inside a 68rem (1,088px) column (`:159-163`). That is about 150 characters per line.
  - Drop cap: `components.css:2077-2086` sets `3.2em` with `line-height: .8`, which spans about 2 lines although its comment says 3.
  - Brief: `skybox-banner.css:482-506` justifies both the Brief and Opinion bodies at full width.
- **Finding 8 (coverage hidden).**
  - The trigger is `.dd-read-more` at `--text-xs` (`components.css:1685-1731`), shown only when sources span two of the three buckets (`InlineDeepDive.tsx:155-165, 681-688`).
  - The list shows `VISIBLE_LIMIT = 3` per column (`ComparativeView.tsx:61`).
- **Finding 9 (legend vocabulary).**
  - `LeanLabelLegend.tsx:54-89` hard-codes the retired `storyLeanLabel` words (`biasColors.ts:256-258`: Balanced / Not measured / Contested).
  - Cards print `leanShapeLabel` (`biasColors.ts:467-479`): Leans left, Leans right, Split, Balanced, Consensus, and "N articles".
  - `docs/DESIGN-SYSTEM.md` section 7 still documents the retired ladder.
  - Mobile has no legend at all (`MobileFeed.tsx`: its feed-start line is aria-hidden text).
- **Finding 10 (the number in the dial).**
  - `Sigil.tsx:343-355` draws `data.sourceCount` at font-size 6 inside the dial.
  - That number counts distinct outlets (`source_count`, e.g. 33).
  - The "thin" label counts **measured articles** (left + center + right from `bias_diversity`, e.g. 30+8+5 = 43 against 33 outlets). So they really are two different units.

### Headless checks that already touch the Deep Dive (`scripts/verify-headless.mjs`)

| Scenario | Lines | What changes under this plan |
|---|---|---|
| `deep-dive-inline` | 486-492 | Still passes: clicks the first link, expects `.inline-dd` and no `.dd-page` |
| `bench @1440/@390` | 499-660 | Opens the first story; the Bench stays. Still passes |
| `deep-dive-page` (390) | 669-678 | Clicks `.dd-page__back` and expects the feed back. Still passes if Back still calls `history.back()` |
| `search-select` | 843-857 | Accepts inline or page. Still passes |
| `deep-dive-share` (390) | 859-867 | Clipboard must match `/story/<uuid>`. Still passes |
| Per-route `one-h1`, `title-grammar`, `data-section`, `aria-current-*` | 255-285 | Run at page load, so a shallow URL does not trip them. Treat them as rules the shallow state must also obey (new checks below) |
| `reading-progress`, `print` on `/story/<id>/` | 1439-1528 | Unchanged, but the new permalink-page layout must keep `.story-page`, `.print-mast` and `.dd-page__bar` (the bar is hidden in print, `brand.css:204`) |
| `shortcuts` | 757-768 | Must also check the arrow and J/K lines (new) |
| `verify-responsive.mjs` sticky | 74-100 | Only covers History, and would pass an element pinned at top 0 *behind* the masthead. Needs strengthening (below) |

`test/css-parity.test.mjs` fails on any CSS class that nothing references. Deleting `ComparativeView` or `.dd-analysis-trigger` therefore means deleting their CSS in the same PR: 49 `comp-view` rules in `components.css`, plus some in `responsive.css`.

---

## B. Root cause per finding

| # | Root cause |
|---|---|
| 4 | The desktop split treats "open" as **replace**, not **insert**: the lead-block branch swaps both leads, and the grid split drops the opened card and breaks its row. The split is by position in a list, but the layout is by visual row. |
| 5 | The inline Deep Dive was built as "just a block in the flow" (its header comment, `InlineDeepDive.tsx:36-52`), so it owns no state in the address bar, no title, and no way back to its opener. Esc is a global listener with no guard. |
| 6 | Walking between stories was built only for the mobile shell. The desktop and permalink shells have no idea where they sit in the edition. The mobile bar is hidden behind the masthead because two stickies share `top: 0`. No shell has an ending. |
| 7 | The pipeline emits one string and flattens any breaks (joins at `cluster_summarizer.py:590-601`, `:644-652`), and the renderer drops it into one `<p>`. The width cap was removed on 2026-08-10 for looks (`inline-dd.css:179-187`). The drop cap is sized for 2 lines. The Brief is justified at full width. |
| 8 | The coverage list is framed as a secondary "breakdown", hidden behind a text link, and gated on crossing the 40/60 lines. It is a 3-bucket view on a different ladder from the 7-rung Bench and the card's register (which is also finding 11). |
| 9 | The legend is hand-written copy, not generated from `leanShape`. When the card moved to `leanShape` on 2026-09-21, nothing tied the legend to it. |
| 10 | The Sigil geometry reserves the lower half of the dial for a count (`Sigil.tsx:343-345`), the one place a reader of a left/right gauge expects a score. The thin label counts a second unit, and neither number says what it counts. |

---

## C. Design options and recommendation

### C1. Navigation model (findings 4, 5, 6)

How the best-in-class sites do it:
- NYT, The Economist, Apple News, Ground News and AllSides all give each story its own page. Opening is a navigation, Back is native, and the page has a canonical URL.
- Ground News desktop adds an in-page "full coverage" list with bias filter tabs.
- Apple News and NYT's app end each article with "Next" or "More in <section>".
- Feeds that open in place (Google News "full coverage" on mobile web, X or Instagram photo modals) keep the feed underneath but always **write the item's canonical URL** to history, so reload and share land on the real page.

**Option A (recommended): inline and addressable.**
- Keep the in-feed accordion on desktop. Insert it after the opened card's visual row; the card stays visible, marked "Open", and dimmed like its siblings.
- On open, push `${BASE_PATH}${story.permalink}` with `history.pushState({voidStory: story.id}, "", url)` and set `document.title = "<title> | Void News"` (exactly what `generateMetadata` serves at that URL).
  - Next 16's app router patches `pushState` to copy its internal tree into the entry and update `usePathname` (`node_modules/next/dist/client/components/app-router.js:234-305`). So Back and Forward move between entries without refetching.
  - Our own `popstate` listener opens or closes based on `history.state.voidStory`.
- Walking to the previous or next story uses `replaceState`, so one Back always returns to the feed. That matches the mobile shell's current "one entry per open" rule.
- Close puts focus back on the opener's link and restores the title and scroll.
- The container is an `<article>` region. It gets no focus trap, and it must not be given `role="dialog"`.
- Pros: keeps the feed in view (the product's "same twenty, in order" model); reload, share and copying the address bar all land on the prerendered static page; no change for search engines (cards already carry crawlable `<a href>`).
- Cons: the masthead's `usePathname` becomes `/story/<id>/` while open, so `data-section` reads `story`. That section is dated and has no nameplate, so the masthead looks the same, but the News link and the mobile Home tab drop `aria-current`. This is correct (you are not on the front page), but it has to be asserted. There is also some shallow-routing risk inside Next (see F).

**Option B: go to the page.**
- Desktop cards navigate (client-side `Link`) to `/story/<id>/`. Delete `InlineDeepDive`, and give the static page previous/next plus the live data.
- Pros: one shell. URL, title, Back, focus, scroll restoration, print and the reading-progress rule all come native. The same model as NYT and Ground News.
- Cons: loses the feed-in-view feel of the Cinematic Press design (the accordion is a 2026-08-09 design decision, not a locked CEO one). The permalink page is fed by archive rows, which lack article titles, so it would need enriching at build. Bigger visual change, and a CEO call.

**Option C: a side panel on desktop** (a right-anchored pane like `OnAirPanel` from 1024px).
- Pros: the feed stays visible, and the focus model is simple.
- Cons: the Bench needs width. A second right-anchored pane would collide with the On Air pane (`--onair-pane-w`). And the reading width would be cramped to about half the viewport. Rejected.

**Recommendation: Option A, built so that B stays a small later change.** Pull the body into one `DeepDiveBody` used by all three shells (C5). If the CEO later prefers B, desktop just stops using the inline shell.

### C2. Previous/next and the ending (finding 6)

- **One component, `DeepDiveNext`, rendered at the end of all three shells.**
  - Shows: "Next story", the next headline as a large link, and "3 of 20". A smaller "Previous" link sits beside it.
  - After story 20 it shows "That is the edition: 20 of 20" with three ways out: "Back to the top story", "Print the Paper" (`/paper/`) and "Listen: On Air" (`/onair/`). The copy has no dashes.
- **Desktop:** the inline header toolbar becomes a slim sticky bar (`position: sticky; top: var(--nav-height)`) holding "‹ 3/20 ›", Share and Close. Keep it at the top, because the On Air pill (finding 17) and the mobile tab bar own the bottom edge.
- **Mobile:** fix `.dd-page__bar` to `top: var(--nav-height)` (check the compact-masthead height on phones in `responsive.css:234-240`; if it differs, add a `--nav-height-compact` token).
- **Permalink page:** previous/next within **its own edition**, computed at build:
  - For the latest edition, reuse `fetchInitialFeed()` plus `archiveMap`, so the order is by construction the front page's order.
  - For older editions, use `printed_on` + `edition_position`.
  - Label it "Next in the Sep 25 edition". This keeps the rule that a shared old story must never inline into today's feed.
- **Keyboard:** while a Deep Dive is open, J and → go to the next story, K and ← to the previous one, Esc closes. None of them fire when focus is in an input or a modal is open (`[aria-modal="true"]`), or when the event is already `defaultPrevented`. Update the overlay text to say so.

### C3. Reading measure and paragraphs (finding 7)

| Option | Mechanism | Trade-off |
|---|---|---|
| **R1 (recommended now): split in the renderer** | New pure `lib/summaryParagraphs.ts`. Respect `\n\n` first if the pipeline ever sends it. Otherwise split into sentences with a guard for abbreviations and initials (U.S., Dr., Sen., Gov., St., Jr., No., single capital initials like "Ihor M.", decimals, "5(c)"), never break inside an open quotation, and group into paragraphs of about 55 to 90 words. The first paragraph is the lede (one or two sentences). Never leave a last paragraph under about 25 words; merge it back. | No pipeline or LLM change. Works for all 1,671 archived summaries. Risk: a missed abbreviation puts a break inside a sentence. That misleads nobody, but it looks wrong, and a unit fixture corpus from `feed.json` plus `archive.json` catches it. The invariant **joined paragraphs equal the original with whitespace normalised** guarantees no text changes (Rule 1). |
| R2: pipeline paragraphs | The prompt asks for 3 to 4 paragraphs separated by blank lines; every post-processor keeps the breaks. | Touches the most heavily gated module (E-13, E-14, hygiene parity with `summaryHygiene.ts`, `labels.test` hygiene fixtures). A prompt-version bump regenerates the cache against a 20-request daily cap. Old archive rows stay unbroken, so R1 is needed anyway. Do it later, and only if R1's breaks read wrong. |

**Layout:**
- Cap the story text at `max-width: 68ch` (use a shared `--measure-read: 68ch` token next to `--measure-prose`), and align it with the header's left edge. Do not centre it: a centred column under a left-aligned headline reads as a mistake.
- The Spread (Bench), agree/split, and the coverage list stay at full 68rem width.
- At 1280px and up, optionally use the existing unused `bias-snapshot--rail` zone (`layout-zones.css:270-300`) as a right rail. Defer this, because it is not needed for the fix.
- **Drop cap:** only on the lede paragraph, and only when that paragraph is three or more lines. Use `initial-letter: 3` under `@supports`, with the float fallback re-sized to three line boxes at `line-height 1.75`.
- **The Brief:** `text-align: left` (drop `justify` and `text-align-last`) on `.skb__section-body--tldr` and `--opinion`, plus `max-width: 68ch`.
- **Disputed-claim marks:** compute the matches on the full string, then cut them by paragraph offsets. Never place a break inside a match. Matches come from sentence pieces, so they stay inside one sentence anyway.

### C4. Original coverage up front (finding 8)

Ground News lists every article with outlet, bias rung, factuality and time, filterable by Left, Center and Right. AllSides shows three columns. NYT shows no outside sources. Void's promise, "See through the void", fits Ground News's model best.

- **Recommended: a new `CoverageList` section, open by default, placed after "Where they split" and before the claim check.**
  - A real `<h2>`: "The coverage".
  - One row per source, sorted Far Left to Far Right on **the same seven rungs as the Bench** (`leanToBucket`). Each row shows the rung as a text label plus a small mark (colour is never the only cue), the outlet name, and the article headline where the data has one.
  - Remove a trailing " - Outlet" or " | Outlet" from the headline (overlaps item 19).
  - Each row is an external link with `rel="noopener noreferrer"`.
  - Sources with an unmeasured lean go in a final group, "Not placed on the lean scale", **never in Center**.
  - The first 10 rows show. A real 44px button, "Show all 33 sources", expands the list in place and sets `aria-expanded`.
  - The count in the heading comes from the same source array as the meta line.
- **Alternative: keep the 3 columns, open by default, with a bigger button.** Smaller change, but it keeps the second ladder (finding 11) and the Center bug.
- **Alternative: rung filter tabs like Ground News.** Nice to have. Defer.
- **The permalink page needs headlines too.** At build, `story/[id]/page.tsx` reads `public/data/deepdive/<row.source_cluster_id>.json` when it exists (the 35 displayed clusters) and joins article titles by source name. Older rows show outlet names only. That is honest, not a gap to fill.
- **Delete `ComparativeView`**, its CSS and the `.dd-analysis-trigger` path in the same PR. Its `hideInsights` disclosure is already dead in all three shells.

### C5. One shared body

Extract:
- `lib/deepDiveSources.ts`: the fetch-and-map logic, currently copied in two places.
- `components/DeepDiveBody.tsx`: in order, the Story, the Spread, agree/split, the coverage list, the claim check, history context, then `DeepDiveNext`.

The three shells keep only their chrome (bar, headline tag, open animation). This fixes the meta-count drift between shells (`sources.length` against `source_count`). Pick one rule: the count of de-duplicated sources the list actually shows, falling back to `source_count` only when no rows loaded. Assert it (E).

### C6. Legend from one table (finding 9)

- In `lib/biasColors.ts`, export `LEAN_SHAPE_LEGEND`: an entry for each `LeanShape` with its label (or label pattern), its colour (via `leanShapeColor`) and a definition **built from the constants**, so the numbers can never drift:
  - **Leans left / Leans right:** at least `SHAPE_MIN_WINGS` (5) articles on the wings, and one wing outnumbers the other by about two to one (`LABEL_MIN_SHARE_TILT` 0.33). Do not write "at least twice": 0.33 admits 1.985 to 1.
  - **Split:** both wings have at least 2 articles, the wings are roughly even, and fewer than half of the articles are in the centre.
  - **Balanced:** the same even wings, with at least half in the centre.
  - **Consensus:** at least 75% of 8 or more measured articles in the centre.
  - **"N measured" (the thin state):** too few measured articles to read a shape, so the card states the count.
- Also explain the register (seven strokes, one per rung) and the ink underline (divergent or consensus flag).
- `LeanLabelLegend.tsx` renders from the table. Mount it on the desktop feed-start (as now), on the mobile feed-start (move `aria-hidden` onto the text only), and next to "The Spread" heading in the Deep Dive.
- Update `docs/DESIGN-SYSTEM.md` section 7 to the `leanShape` table.

### C7. The dial number (finding 10)

- **Recommended:**
  - Take the count out of the dial (delete `Sigil.tsx:343-355`).
  - Print "33 sources" on a second caption line under the lean word, inside the Sigil component, so every card surface picks it up.
  - Change the thin label from "9 articles" to "9 measured", with the legend and tooltip saying "9 articles had a measurable lean".
  - Why keep two numbers: they are two true quantities (outlets covering, articles measured), so the fix is to name the unit, not to merge them (Rule 1).
- **Alternative:** put the unit inside the dial ("33 src"). At 6px it is illegible (finding 18), and it still sits where a score would. Rejected.
- **CEO wording choice:** "9 measured" against "9 read". The first is more exact.

---

## D. Implementation steps

### PR 1: navigation model (findings 4 and 5; the key parts of 6). Size M, about 500 to 700 lines changed.

0. **Spike first (half a day, throwaway).**
   - In a dev build, `pushState({voidStory:id}, "", "/story/<pid>/")` from `/`, then Back, then Forward, then reload.
   - Confirm: no RSC fetch in the network log, no hydration warning, `usePathname` is `/story/…` while open, Back gets `/` with no remount of `HomeContent` (scroll and state survive), and reload serves the static page.
   - Repeat with `NEXT_PUBLIC_BASE_PATH="/void--news"`.
   - If the patched router misbehaves, fall back to `?story=<clusterId>` for the pushed URL. The deep-link handler at `HomeContent.tsx:668-686` already reopens from that on reload. It costs the canonical URL, but keeps Back and the title.
1. **New `app/lib/deepDiveHistory.ts`** (pure plus a thin DOM wrapper):
   - `urlFor(story)` returns `${BASE_PATH}${story.permalink}`, or `?story=<id>` when there is no permalink.
   - `openEntry(story)` pushes and sets the title. `swapEntry(story)` replaces. `closeEntry()` calls `history.back()` when the entry is ours, otherwise it replaces with `/` and restores the title.
   - `subscribe(onOpen, onClose)` wraps `popstate` and reads `history.state?.voidStory`.
   - Keep the original title in a module variable.
2. **`components/HomeContent.tsx`:**
   - Always render the lead block (delete the `inlineInLead ?` branch, `:932-949`). When `inlineIndex` is 0 or 1, render `<InlineDeepDive>` right after `.lead-twin`.
   - Grid: replace the list-position split (`:960-984`) with a **split at the end of the visual row**. When a card opens, read the `offsetTop` of every `.feed-grid__item`; the last item sharing the opened card's `offsetTop` is the split point. Store `rowEndIndex` in state and recompute with a `ResizeObserver` on the grid while open. The opened card stays in the DOM with `data-open="true"`.
     - This works for any column count, so it survives item 16 changing 4 columns to 3.
     - Do not use `grid-auto-flow: dense`: it would make visual order differ from DOM and focus order (WCAG 2.4.3).
   - `handleStoryClick`: record the opener (`document.activeElement` if it is inside a card, otherwise the card's `.story-card__stretch-link`) and call `openEntry`.
   - `handleInlineCollapse` / `handleDeepDiveClose`: call `closeEntry()`. On the resulting `popstate`, clear the story, restore scroll, then `opener.focus({preventScroll:true})` after two animation frames.
   - Subscribe to `popstate` once: Forward to an entry with a `voidStory` id reopens that story if it is in `visibleStories`.
   - `handleDeepDiveNav`: call `swapEntry(next)` and pass `animate={false}` so the swap does not collapse and re-expand.
   - Enable keys while open: pass `deepDiveOpen` into a new `useDeepDiveKeys(onNav, onClose)` hook instead of switching nav off.
3. **`components/InlineDeepDive.tsx`:**
   - Esc: guard on `e.defaultPrevented`, an open `[aria-modal="true"]`, focus inside `.search-overlay` / `.kbd-overlay` / `.oap`, or an open Sigil popup.
   - Add an `animate` prop that skips the open tween.
   - Add `aria-labelledby` pointing at the headline id. Keep `<article>`, with no `role="dialog"`.
   - Add a visible sticky mini-bar (see PR 2); the Close control stays.
4. **`components/DeepDive.tsx`** (mobile): replace the bare `pushState` (`:420-426`) with `openEntry` (the permalink URL) and use the shared popstate subscription. `handleBack` keeps calling `history.back()`, so `deep-dive-page-back` still passes.
5. **`components/LeadStory.tsx`:** add `data-story-index={rank}` so J/K can reach stories 0 and 1. Add `aria-current="true"` or `data-open` on the opened lead.
6. **`styles/inline-dd.css`:** `.lead-twin--recede` stays. Add a `[data-open="true"]` treatment for the opened card (a hairline and the word "Open" for screen readers) so the reader sees where the Deep Dive came from.
7. **`components/KeyboardShortcuts.tsx`:** make the rows true: "J or →: next story (in a Deep Dive, the next Deep Dive)", "K or ←: previous", "Esc: close the Deep Dive".

### PR 2: previous/next and the ending on every shell (finding 6). Size M, about 400 lines.

1. **New `components/DeepDiveNext.tsx`:** props `{prev?: {title, href}, next?: {title, href}, position, total, editionLabel?, onNavigate?}`. With `onNavigate` it renders buttons (feed shells); otherwise `<Link>` (permalink page). It includes the end-of-edition state. All copy passes `copy-facts.test.mjs` (no dash, no kill-list word).
2. **Inline:** a sticky `.inline-dd__bar` (`top: var(--nav-height)`) with ‹ n/20 ›, Share and Close, plus `DeepDiveNext` at the end of the body.
3. **Mobile:** `deep-dive-page.css:24-34`, change to `top: var(--nav-height)` (using the compact value if the masthead compacts on phones), and put `DeepDiveNext` at the end.
4. **Permalink page:**
   - `story/[id]/page.tsx` computes neighbours at build.
   - If `row.printed_on` is the latest edition: `fetchInitialFeed()` gives the displayed order, mapped to permalinks through `archiveMap`.
   - Otherwise: rows with the same `printed_on`, sorted by `edition_position`.
   - Pass them to `StandaloneDeepDive` and render `DeepDiveNext` with "Next in the <date> edition".
   - Read the archive once through the existing module cache, so it adds nothing per page.

### PR 3: reading comfort (finding 7). Size M, about 350 lines plus fixtures.

1. **New `app/lib/summaryParagraphs.ts`** as described in C3. It returns `{paragraphs: string[], offsets: number[]}`.
2. **`components/SummaryWithContradictions.tsx`:** return `<p>` elements, one per paragraph, with `ClaimMark` spans cut by offsets. Delete the copy in `DeepDive.tsx:105-158` and use this component.
3. **All three shells:** replace `<p className="dd-summary-text">` with `<div className="dd-summary">` holding the paragraphs. The lede paragraph gets `dd-summary__lede`, with slightly larger type (for example `--text-lg`) and `--fg-primary`.
4. **CSS:**
   - `inline-dd.css:179-187`: `max-width: var(--measure-read)`.
   - Add the token in `tokens.css` (the `css-lint` rule does not cover `ch`, but keep it a token).
   - `components.css:2068-2086`: move the drop cap to `.dd-summary__lede::first-letter`, with the `@supports (initial-letter: 3)` path and the fallback re-sized.
   - `story-page.css` and `deep-dive-page.css`: the same measure.
   - `skybox-banner.css:482-506`: left-aligned, `max-width: var(--measure-read)`.
5. Leave the pipeline alone (R2 is deferred). Record the decision and the R1 invariant in `docs/DESIGN-SYSTEM.md` section 8.

### PR 4: the coverage list (finding 8, and by construction the Center bug; overlaps items 11 and 19). Size M to L, about 600 lines added and 400 deleted.

1. **Extract `app/lib/deepDiveSources.ts`** from the two copies (`InlineDeepDive.tsx:167-356`, `DeepDive.tsx:224-406`). Both shells import it.
2. **New `components/CoverageList.tsx`** plus a `coverage-list.css` section in `verify.css` (already loaded by all three shells). It groups rows by `leanToBucket` and `leanLabel` (seven rungs), puts `leanUnscored` rows in the last group, and removes a trailing outlet name from the headline.
3. **`lib/archive.ts:231-261`:** carry `leanUnscored: m.lean_unscored === true` into `StorySource`. Add an optional `titlesByName` map parameter for the build-time enrichment.
4. **`story/[id]/page.tsx`:** read `public/data/deepdive/<source_cluster_id>.json` if present (with `readFileSync` in the server component, which works under static export) and pass the titles in.
5. **Extract `components/DeepDiveBody.tsx`** (C5) and make the three shells use it. The meta count uses one rule.
6. **Delete** `ComparativeView.tsx`, every `.comp-view*` rule in `components.css` and `responsive.css`, the `.dd-analysis-trigger` rules, and `hasCrossLeanSources` in all three shells.

### PR 5: the legend (finding 9). Size S, about 200 lines.

1. **`lib/biasColors.ts`:** add `LEAN_SHAPE_LEGEND` and a `legendTermFor(label)` helper that maps a printed label back to its entry (including the thin pattern `^\d+ measured$`).
2. **`components/LeanLabelLegend.tsx`:** render from the table. Replace the intro line with one that describes the register and the word.
3. Mount it in `MobileFeed.tsx` (the feed-start line) and in `DeepDiveBody` beside "The Spread" heading.
4. **`docs/DESIGN-SYSTEM.md` section 7:** replace the four-state table with the `leanShape` table, generated as a copy of the legend and checked by a test (E).

### PR 6: the dial number (finding 10). Size S, about 120 lines. Land after the other engineer's Sigil PR merges.

1. **`Sigil.tsx:343-355`:** delete the `<text>`. Add a `.sigil__count` caption line ("33 sources") under `.sigil__lean-label`, 12px minimum (finding 18's floor).
2. **`biasColors.ts:469-473`:** change the thin label to `${n} measured`, and update `labels.test.mjs`.
3. The popup and aria-label use the same count and word, which the other engineer's finding 1 fix already moves to `leanShapeLabel`.

---

## E. Tests and headless checks

Every new check goes in the same PR as the change it guards.

**New pure tests** (node plus `tsc` compile, the pattern already used by `test/labels.test.mjs`):
- `test/summary-paragraphs.test.mjs` (PR 3), run over every summary in `build-data/feed.json` and a sample of `archive.json`:
  - joining the paragraphs gives back the whitespace-normalised input, exactly;
  - no break directly after a known abbreviation or single initial, and none inside an open quotation;
  - summaries over 120 words produce two or more paragraphs;
  - no paragraph is under 25 words except a lone lede sentence.
  - Add it to `npm test`.
- `test/labels.test.mjs` additions (PR 5):
  - the `LEAN_SHAPE_LEGEND` keys equal the `LeanShape` set;
  - `leanShapeLabel` over a grid of wing counts always maps through `legendTermFor`;
  - no legend text contains "Contested", "Not measured" or "Aligned";
  - the numbers in each definition equal the exported constants.
- `test/copy-facts.test.mjs`: new strings are covered automatically. Check that the "20 of 20" copy is built from `FEED_DISPLAYED`, never a literal, since the test flags stale story counts.

**New `verify-headless.mjs` scenarios:**

| Scenario | Width | Asserts | PR |
|---|---|---|---|
| `deep-dive-keeps-lead` | 1440 | Open lead story 1 (the second lead). Both `.lead-story` stay in the DOM, there is still exactly one `h1`, the 20 `article` cards are still present, and `.inline-dd` comes after `.lead-twin` in document order | 1 |
| `deep-dive-row` | 1440, 1024 | Open grid card 5. The opened card is still present, and every card in its visual row (same `offsetTop`) comes before `.inline-dd` | 1 |
| `deep-dive-address` | 1440, 390 | After opening, `location.pathname` equals the card's `href` pathname and `document.title` equals `"<headline> \| Void News"`. After Back, the path is `/`, the title is the tagline, and the Deep Dive is closed. After Forward, it is open again. Also covers `data-section` equalling `sectionForPath(location.pathname)` in both states | 1 |
| `deep-dive-reload` | 1440 | Open, then `page.reload()`. `.story-page` renders with the same headline | 1 |
| `deep-dive-escape-focus` | 1440 | Open with the keyboard (Tab to a card, press Enter), then press Esc. `document.activeElement` is that card's stretch link. Open a Sigil popup inside the Deep Dive and press Esc: the Deep Dive stays open | 1 |
| `deep-dive-keys` | 1440 | While open, J moves to story n+1 and the URL follows; K returns; → and ← do the same. History length does not grow (replace, not push) | 1 |
| `shortcuts` (extend) | 1440 | The overlay lists J, K, ←, →, Esc, and each one does what it says (depends on `deep-dive-keys`) | 1 |
| `deep-dive-walk` | 1440, 390 | Starting at story 1, follow "Next" 19 times. The sequence of headlines equals the feed's card order, and story 20 shows the end-of-edition block with three working links. This ties to "same stories, same order" | 2 |
| `story-page-next` | fs-level, like `paper-parity` | For every latest-edition `/story/<id>/index.html` in `out/`, the Next link is the next permalink in the front page's order. For one older edition, the order follows `edition_position` | 2 |
| `deep-dive-bar-visible` | 390, 1440 | Scroll to the end of the Deep Dive. The bar's top is at or below the masthead's bottom minus 1px, and `elementFromPoint` at the bar's centre is inside the bar (not covered). Also extend `verify-responsive.mjs` sticky to these two bars with the same "not covered" rule, so it stops accepting an element hidden under the masthead | 2 |
| `deep-dive-measure` | 1440, 1024, 390 | For each `.dd-summary p`, characters per line (text length divided by the number of line boxes from `Range.getClientRects()`) is at most 80. Summaries over 120 words have two or more `p`. The Brief body's `text-align` is not `justify` | 3 |
| `coverage-list` | 1440, 390, and one `/story/` route | Visible without a click. The row count (after "Show all") equals the meta count. Every row link is external. No unmeasured-lean source sits under a centre rung (compare against Bench `.bench__unscored` and marks). Each row's rung equals the Bench column for the same outlet (this settles item 11 as a fact) | 4 |
| `deep-dive-count-parity` | 1440 | For the first 3 stories, the inline meta count equals the count on the `/story/<id>/` page. The summary text is identical | 4 |
| `legend-matches-cards` | 1440, 390 | Every printed `.sigil__lean-label` word resolves to a legend `dt` (open the legend, read the `dt`s). Every legend term can be emitted (checked in the pure test) | 5 |
| `sigil-no-score` | 1440 | No `<text>` inside `.sigil svg` whose content is a number. The `.sigil__count` text equals the Deep Dive meta count for that story | 6 |

Existing scenarios needing no change: `deep-dive-inline`, `bench @*`, `deep-dive-page`, `search-select`, `deep-dive-share`. Re-run the full grid by hand (`node scripts/verify-headless.mjs`) for PRs 1 and 4, not just `--quick`.

---

## F. Risks

- **Static export and shallow routing (PR 1, the main risk).**
  - Next's patched `pushState` restores the *home* tree at a `/story/` URL. Anything reading `usePathname` flips (`NavBar`, `MobileNav`, `FloatingPlayer`).
  - `FloatingPlayer` only suppresses on `/onair`, and `MobileNav` only on `/history`, so audio chrome is unaffected. The `audio-survives-navigation` scenario must still pass.
  - Prefetching: the masthead's `<Link>`s keep working from a `/story/` URL, since relative resolution is not used.
  - The spike in PR 1 step 0 is a hard gate before the rest of that PR.
- **basePath.** Every pushed URL must go through `BASE_PATH` (default `/void--news`; production `""`). `trailingSlash: true` means permalinks end in `/`. `storyHref` already does this. Test under both base paths.
- **Title.** React 19 hoists `<title>` from Next metadata. A manual `document.title` holds as long as the head does not re-render with different metadata, and restore-on-close handles the rest. Guarded by `deep-dive-address`.
- **SEO.** No change to what crawlers see. Cards keep `<a href="/story/<id>/">`, canonical and JSON-LD live on the static page, and sitemap entries are unchanged. Making the permalink the address-bar URL gives the canonical URL more human shares, which is a mild plus.
- **History semantics.** Previous/next uses replace, so Back always means "back to the feed". The `?story=` handler (`HomeContent.tsx:668-686`) must keep working for Revolt cross-links and cold-bootstrap stories without a permalink.
- **Keyboard.** J/K inside the Deep Dive change meaning from "move focus" to "change story". The overlay must say so. Arrow keys must not fire inside the Bench if the Bench ever handles arrows (it does not today; its marks are reached with Tab), or in any input. Esc now has several owners (search, shortcuts overlay, On Air panel, legend, Sigil popup), so the guard order matters.
- **Audio player.** The fixed On Air pill covers the bottom-left corner (item 17). That is why the new pager is at the top. The end-of-story `DeepDiveNext` must sit above the `data-fp-pill` body padding (`FloatingPlayer.tsx:75-83`).
- **Paragraph splitting (Rule 1).** It must never change text, and the test invariant enforces that. A bad break is a readability problem, not a factual one, but it would reach every story, so the fixture corpus is the control.
- **Coverage list and IP.** Render outlet name, headline and link only, never `articleSummary`. Headlines are short and link to the publisher.
- **css-parity.** Deleting `ComparativeView` requires deleting its CSS in the same commit; forgetting it fails CI.
- **Performance.** The row-end calculation uses `offsetTop` reads at open and on resize only. Keep the Deep Dive chunks lazy (`HomeContent.tsx:24-25`); `DeepDiveBody` must not pull the Bench into the home bundle.
- **One-branch rule.** The PRs are sequential by rule, not in parallel. Each needs green checks and auto-merge before the next branch opens.

---

## G. Sequencing

| PR | Findings | Size | Depends on | Files that matter most |
|---|---|---|---|---|
| 1 Navigation model | 4, 5, keys part of 6 | M | spike (step 0) | `HomeContent.tsx`, `InlineDeepDive.tsx`, `DeepDive.tsx`, new `lib/deepDiveHistory.ts`, `LeadStory.tsx`, `KeyboardShortcuts.tsx`, `verify-headless.mjs` |
| 2 Previous/next and the ending | 6 | M | 1 | new `DeepDiveNext.tsx`, `inline-dd.css`, `deep-dive-page.css`, `story/[id]/page.tsx`, `StandaloneDeepDive.tsx`, `verify-responsive.mjs` |
| 3 Reading comfort | 7 | M | 1 (same shells) | new `lib/summaryParagraphs.ts`, `SummaryWithContradictions.tsx`, `components.css`, `inline-dd.css`, `skybox-banner.css`, `tokens.css` |
| 4 Coverage list and shared body | 8 (supersedes 11, 19) | M to L | 3 | new `CoverageList.tsx`, `DeepDiveBody.tsx`, `lib/deepDiveSources.ts`, `lib/archive.ts`, delete `ComparativeView.tsx` and its CSS |
| 5 Legend | 9 | S | none (can go before 4 if wanted) | `lib/biasColors.ts`, `LeanLabelLegend.tsx`, `MobileFeed.tsx`, `labels.test.mjs`, `DESIGN-SYSTEM.md` |
| 6 Dial number | 10 | S | the other engineer's Sigil PR (finding 1) | `Sigil.tsx`, `biasColors.ts`, `labels.test.mjs` |

Suggested order: 1, 2, 3, 5, 4, 6. Moving PR 5 earlier ships a small, visible, factual fix while PR 4 is under review. PR 6 is last because it edits `Sigil.tsx`.

---

## H. Coordination with the other engineer

- **`Sigil.tsx`:** PR 6 edits it (the count leaves the dial, a caption is added). Land it after their finding 1 change, rebased on it, or hand them the 20-line diff to include.
- **`MobileSidePanel.tsx`:** the "dialog, aria-modal false" the audit saw is very likely their closed drawer. Suggest `inert` or `hidden` while closed.
- **Items 11 and 19 are superseded by PR 4** (seven rungs, headline suffix removal, `ComparativeView` deleted). Agree on this before they spend time on `ComparativeView`.
- **Item 20** (bullets in `SpreadDisagreement`) and **items 12 and 13** (Spread header, meta line) touch the shared body that PR 4 extracts. Land theirs first, or fold them into PR 4.
- **Item 16** (grid columns) is safe with PR 1, because the row-end split reads the live layout.
- **Item 18** (legibility floor) sets the size of the new count caption in PR 6: 12px.
- **`app/lib/utils.ts`** is theirs. Nothing here touches it; `BASE_PATH` is only imported.

---

### Critical Files for Implementation
- /home/user/void--news/frontend/app/components/HomeContent.tsx
- /home/user/void--news/frontend/app/components/InlineDeepDive.tsx
- /home/user/void--news/frontend/app/components/DeepDive.tsx
- /home/user/void--news/frontend/app/components/StandaloneDeepDive.tsx (with /home/user/void--news/frontend/app/story/[id]/page.tsx)
- /home/user/void--news/frontend/scripts/verify-headless.mjs
