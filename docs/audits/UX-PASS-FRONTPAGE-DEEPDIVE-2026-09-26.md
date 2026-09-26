# UX pass: front page and Deep Dive (live site), 2026-09-26

Scope: `https://news.voidvision.org/` front page and the Deep Dive, Void News only.
Method: headless Chromium (Playwright) against the LIVE served site, at 1440x900
(desktop) and 390x844 (mobile, touch), light and dark scheme. Every finding below
was observed on the live page, and where it is a code defect the file is named.
Edition under test: Sep 25, 2026, as of 6:00 PM UTC (20 stories).

Severity: **P0** wrong information shown to the reader, or content lost.
**P1** a core task is harder than it should be. **P2** polish and consistency.
**Opp** an opportunity, not a defect.

---

## Summary

| # | Sev | Area | Finding |
|---|---|---|---|
| 1 | P0 | Card lean | The card says one thing, its tooltip and screen-reader label say another |
| 2 | P0 | Menu | "Edition as of" in the Menu shows the current hour, not the edition time |
| 3 | P0 | Front page | 18 of 20 stories are invisible if JavaScript fails or is slow |
| 4 | P1 | Deep Dive (desktop) | Opening story 2 removes the top story from the page |
| 5 | P1 | Deep Dive (desktop) | No URL, no title, Back leaves the site, Esc drops focus to `<body>` |
| 6 | P1 | Deep Dive | Desktop has no previous/next; mobile's pager vanishes on scroll; both dead-end |
| 7 | P1 | Deep Dive | "The Story" is a single ~25-line paragraph at ~150 characters per line |
| 8 | P1 | Deep Dive | The original coverage is hidden behind a 10px "Show source breakdown" link |
| 9 | P1 | Legend | The "What the coverage labels mean" legend uses words the cards never print |
| 10 | P1 | Card | The number inside the Sigil is a source count drawn inside a lean gauge |
| 11 | P2 | Deep Dive | Three different groupings of the same sources on one screen |
| 12 | P2 | Deep Dive | Lead-story Spread shows an orphan Sigil with no word; story 2 shows the word twice |
| 13 | P2 | Deep Dive | Meta line repeats "24 sources"; "CONTESTED · ▬ · RIGOR 51" is unexplained |
| 14 | P2 | Front page | Headlines truncated with an ellipsis in the 4-column grid |
| 15 | P2 | Front page | Summaries end in "....": a period plus the clamp ellipsis |
| 16 | P2 | Front page | 18 cards in 4 columns leaves a 2-card orphan row and uneven rules |
| 17 | P2 | Global | The On Air pill permanently covers the bottom-left of the content |
| 18 | P2 | Global | Type below legibility: 6px Sigil numbers, 8px labels, 10px nav |
| 19 | P2 | Deep Dive | Source Perspectives separator renders as a floating dash |
| 20 | P2 | Deep Dive | Bullets touch their text ("–The US Senate") |
| 21 | Opp | The Brief | Brief paragraphs don't link to the stories they summarise |
| 22 | Opp | Front page | Masthead drops the tagline and "as of" inconsistently between states |

---

## P0: wrong information shown to the reader

### 1. The card's lean word disagrees with its own tooltip and aria-label

On every card, three labels describe the same story and they come from two
different rules:

- the printed word under the Sigil comes from `leanShapeLabel(biasSpread)`, the roster rule;
- the `aria-label` and the hover tooltip come from `storyLeanLabel(politicalLean, …)`, the older gated-mean ladder
  (`frontend/app/components/Sigil.tsx:686-708`).

Live, on this edition:

| Story | Printed on card | Screen reader hears | Tooltip heading |
|---|---|---|---|
| Iran Proposes Seven-Day Plan | **Leans left** | "Not measured" | "Not measured" · "Balanced coverage from multiple perspectives" · "Lean measured from 8 of 12 analyzed articles" |
| OpenAI Agent Hacks Australian… | **Leans left** | "Center (46)" | |
| UN Security Council Condemns… | **Leans left** | "Center (45)" | |
| Ukrainian Charged with Murder… | **Leans right** | "Not measured" | |
| Congo Faces Health Worker… | **9 articles** | "18 sources" | |
| Senate Rejects Resolution… | **Split** | "Contested" | |

The Iran tooltip contradicts itself three times in one box: "Not measured",
"Balanced", and "measured from 8 of 12". The card beneath it says "Leans left".
Under Rule 1 this is a factual error: a reader who hovers gets a different
answer than a reader who looks.

**Fix:** have the aria-label and tooltip heading read the same `leanShapeLabel`
and `leanShapeColor` as the printed word, and delete the second ladder from the
card. **Control:** a headless assertion that on every card the printed label,
the `aria-label` word and the tooltip heading are identical. It belongs in
`verify-headless.mjs` next to `lean-label-contrast`.

### 2. The Menu's "Edition as of" is the reader's clock, not the edition

Masthead: **Sep 25, 2026 · as of 6:00 PM UTC**. Menu drawer, same page, same
moment: **Edition as of 2:00 AM UTC**, which was the current hour when tested.
`MobileSidePanel.tsx:451` calls `getEditionTimestampLocal(editionBuiltAt)`, and
that helper falls back to `new Date()` when the argument is empty
(`app/lib/utils.ts:50-51`). The drawer is evidently rendered without
`editionBuiltAt`. The NavBar comment at `NavBar.tsx:139` records the same bug
being fixed once already in the masthead.

**Fix:** pass `editionBuiltAt` into the drawer, and make the helper return `""`
rather than "now" with no input, so a missing value shows nothing instead of a
wrong value. **Control:** a headless check that the drawer's time equals the
masthead's.

### 3. With no JavaScript, 18 of 20 stories are invisible

Every grid card is server-rendered as `story-card anim-stagger` at
`opacity: 0` with a paused `staggerUnfold` animation. Only
`useInView` → `.anim-stagger--visible` reveals it
(`app/components/StoryCard.tsx:52`, `app/lib/sharedObserver.ts`). Observed live
when the JS chunks failed to load through a flaky network: the two lead stories
rendered and the other 18 were blank rectangles framed by column rules, while
the "20 stories" footer still printed. The same happens for a reader with a
script blocker, a failed chunk, an old browser, or a hydration error.

**Fix:** make the hidden state opt-in rather than the default. Gate it behind a
class the client sets on `<html>` before first paint (`html.js .anim-stagger
{opacity:0}`), or give the rule a `@media (scripting: none)` override. The
static-export promise is "every read is static"; the page should survive
without its entrance animation. **Control:** a headless run with JavaScript
disabled asserting that all 20 `article`s have non-zero opacity.

---

## P1: a core task is harder than it should be

### 4. Opening story 2 on desktop removes the top story from the page

Clicking the second lead ("Senate Rejects…") replaces the whole lead row with
the inline Deep Dive. The first lead ("Sarandon, Einbinder…", the day's top story
and the page's `<h1>`) is no longer in the DOM (19 `article`s while open). The
Brief also collapses. A reader who opens #2 has to close it to see #1 again.

**Fix:** expand the Deep Dive below the row it came from, or keep the sibling
lead visible above it.

### 5. The desktop Deep Dive has no address and breaks Back

- The URL stays `/` and `document.title` stays "Void News. See through the
  void." while a story is open. The card itself is an `<a href="/story/<id>">`,
  but a left-click prevents the navigation.
- **Browser Back leaves the site.** On a fresh tab, opening a Deep Dive and
  pressing Back went to `about:blank`. Back is the most common "close" gesture.
- **Esc closes the Deep Dive but drops focus to `<body>`.** A keyboard user is
  thrown back to the top of the document, not returned to the card they opened.
- The container is `role="dialog"` with `aria-modal="false"`, yet Tab walks
  straight out of it into the feed.

**Fix:** push `?story=<id>` (or the `/story/<id>` path) with `history.pushState`
on open, close on `popstate`, set the title to `Headline | Void News`, and
return focus to the originating card on close. Either make it a real modal
(trap focus) or drop `role="dialog"`, since inline content is a region.

### 6. No next-story path; the Deep Dive is a dead end

- **Mobile** has a "Back to feed · ‹ 2/20 ›" bar, but it's only at the top and
  scrolls away. It's gone by the time a reader finishes the story.
- **Desktop** has no previous/next at all (its buttons are Share, Close,
  Collapse, Show source breakdown).
- Both end on the tiny "Show source breakdown" link and then the footer (mobile)
  or the grid (desktop).

**Fix:** a "Next: <headline> ›" row at the end of every Deep Dive, the same on
both layouts, and make the mobile bar sticky. Going through the twenty in order
is the product's reading model ("same stories, same order").

### 7. "The Story" is a wall of text

The Senate summary is one paragraph of about 450 words. On desktop it runs the
full 1,090px content width, about 150 characters per line (a comfortable measure
is 60 to 75). On mobile it's about 25 unbroken lines. The drop cap spans two
lines of a 14-line block, so it reads as an accident. The expanded Brief is
the same: full-width **justified** text, which opens rivers at that width.

**Fix:** cap the Deep Dive body at about `68ch` and centre it (the Spread and
the lists can stay wide). Split the summary into paragraphs at the pipeline or
render layer. Don't justify the Brief.

### 8. The original coverage is the least visible thing in the Deep Dive

The list of actual articles (the thing "See through the void" promises) sits
behind "Show source breakdown", a 10px grey text button under the last bullet.
Once opened, it shows three per column with "+6 more", "+3 more".

**Fix:** show it by default as its own section after "Where they split", with a
real heading and a proper button for the full list.

### 9. The legend's vocabulary isn't the cards' vocabulary

The "What the coverage labels mean" popover defines **Left / Right, Balanced,
Not measured, Contested, Split / Divergent, Aligned**. The cards actually print
**Leans left, Leans right, Split, Balanced**, and **"9 articles"** (the thin
state), and the code also emits **Consensus**. So "Leans", "Consensus" and the
"N articles" state are never explained, and "Contested", "Aligned" and "Not
measured" are explained but never printed. The legend describes the retired
ladder, the same one that feeds the aria-label in finding 1.

**Fix:** generate the legend from the same `leanShape` states the card uses, so
one list feeds both.

### 10. The number in the Sigil reads as a score

Each card's gauge carries a number (33, 24, 26, 102…) in the centre of a
left/right dial, which is exactly where a reader expects a lean score. It is
the **source count**. The Congo card then prints "9 articles" under a Sigil
reading 18. That's two units for one story, side by side.

**Fix:** move the count out of the dial ("33 sources" in the meta line, where
the Deep Dive already puts it), or label it in place. Pick sources or articles
and use it everywhere.

---

## P2: polish and consistency

11. **Three groupings of the same sources.** For the Senate story the header
    says 24 sources, the Bench says "22 placed · 11 from headlines only · 2 not
    measured" across seven columns, and Source Perspectives says Left 9 · Center
    6 · Right 9 (24) in three columns. "Outlook India" is a centre-left column
    in the Bench and sits under LEFT in the list. Label the three-way list as a
    collapse of the seven rungs, or show it in seven.
12. **Spread header.** Lead story: a large Sigil ring floats alone in the left
    whitespace with no word, which looks broken. Story 2 on mobile: Sigil +
    "Split" and then a second "Split" heading with a second, tiny Sigil. One
    mark, one word.
13. **Deep Dive meta.** "Politics • 24 sources • 1d ago", then "● CONTESTED ·
    ▬ · RIGOR 51 · 24 SOURCES" right under it. The count is repeated, the bar
    glyph is unlabelled, and "Rigor 51" has no explanation or link to
    methodology. "Contested" is a third lean word (the card says Split).
14. **Truncated headlines.** In the 4-column grid, headlines are clamped with an
    ellipsis ("…Fighting in Ethiopia'…", "Health System,…", "Calls for UN…").
    A newspaper doesn't cut its headlines. Let them wrap and clamp the
    summary instead.
15. **"...."** Card summaries end in a period plus the clamp's ellipsis
    ("Thursday….", "according to one report…."). Trim the trailing period
    before truncating.
16. **Orphan row.** 2 leads plus 18 cards in 4 columns leaves 2 cards alone in
    the last row. The vertical rules end at different heights, and there's a
    blank quarter of the page. 3 columns, or a 3-4-4-4-3 rhythm, fills it.
17. **On Air pill overlap.** The fixed pill (bottom-left, about 220x55) covers
    column-one card text in every desktop screenshot, the "THE SPREAD" label in
    the Deep Dive, and the Source Perspectives link. Reserve a bottom gutter or
    let the pill collapse to the play button after scroll.
18. **Legibility floor.** Measured computed sizes: Sigil centre numbers **6px**,
    Sigil words ("Leans left", "Split") **8px** on grid cards, top nav and
    footer links **10px** (9px on mobile), "20 stories" footer 10px, search
    result meta about 8px. Desktop nav links are 16px tall hit areas. A 12px floor
    for data labels and a 24px minimum target (WCAG 2.2 2.5.8) would clear most
    of it.
19. **Source list separator.** In Source Perspectives each row is "Outlet ⎯
    Headline", with the rule drawn as a floating dash that misaligns when the
    headline wraps. Headlines also keep their own " - Outlook India" suffix,
    which repeats the outlet name.
20. **List bullets** in "What they agree on" and "Where they split" touch the
    text on mobile ("–The US Senate…"). Add a gap.

---

## Opportunities

21. **Link the Brief to the feed.** Each Brief paragraph is one story (the rule
    is one story per paragraph). Making each one open its Deep Dive turns the
    Brief into a table of contents. Today it's a dead block that pushes the
    feed down about 1,400px when expanded.
22. **One masthead state machine.** The desktop masthead shows the tagline "See
    through the void." and "Sep 25, 2026 · as of 6:00 PM UTC" at rest. It drops
    the tagline when a Deep Dive is open or after a scroll, and drops "as of"
    on compact. Mobile shows "as of" with no date. The date and edition time
    should be the constant; the tagline is the thing to shed.

---

## What works well (keep)

- Search (Ctrl+K) is fast, keyboard-driven, and shows section, age and source
  count.
- Focus rings are present on every control tabbed (2px solid).
- The Bench (seven columns of source marks) reads instantly and every mark is
  keyboard-reachable with a name ("Truthout, Far Left").
- "What they agree on / Where they split" is the clearest expression of the
  product's point of view on the page.
- Mobile's "Back to feed · 2/20" pager is the right model; it only needs to be
  sticky and mirrored on desktop.
- Dark mode holds contrast on cards, Brief and Deep Dive.
- No horizontal overflow at 390 or 1440, and no console errors from the app.

## Suggested order

1. Finding 1 (lean labels agree) and 2 (edition time): both are factual, both
   small, and both need their headless control in the same commit.
2. Finding 3 (content visible without JS).
3. Findings 4, 5 and 6 (Deep Dive navigation model): one piece of work.
4. Findings 7, 8 and 9 (reading comfort, sources up front, legend from one source).
5. The P2 list as one polish pass.
