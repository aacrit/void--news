# Void News Design System: "Cinematic Press"

**Version:** 3.1
**Last updated:** 2026-09-21

**What changed in v3.1 (same day):** the browser-chrome layer
(`styles/brand.css`, section 5), print for the two long reads (section 12),
the reading rule and the on-air beam (section 10), and the headless sweep as
the gate on all of it (section 14).

**What changed in v3.0:** rewritten against the code after the frame was
unified: one masthead and footer for every route, sections as skins rather
than forks, one share-card composer, the three lean states, and the token,
easing and radius rules stated as the standard.
**Deleted:** the edition switch and its row of chips, the three-lens bias mark
and the axis inspector panel that went with it, the dot matrix and the stamp
before them, the per-edition colour grades, the Film chapter inventory, and
the old product name. All are gone from the code; they are gone from here.

---

## 1. Philosophy, and the one brand rule

**Cinematic Press.** The editorial authority of a broadsheet, shot through a
cinema lens. Warm paper, film grain, a vignette and a shallow depth of field
on arrival; the precision of a data terminal on interaction.

The newspaper earns trust through restraint. The data layer earns trust
through transparency. The cinematic layer carries the feeling.

**The brand rule (CLAUDE.md, "Brand"), which governs every surface a mark is
drawn on:**

> `VOID NEWS` is the only word that gets a lockup. A section gets a nameplate
> in its accent. A programme gets a title.

So: no VOID HISTORY and no VOID WEEKLY, on the site, the share cards or the
podcast covers. The masthead reads `VOID NEWS` with a nameplate beside it
(`History`, `Weekly`, `Paper`). Programmes (On Air, The Argument, History
audio) are set as typographic titles, never as marks. Page titles are
`Page | Void News` for a landing and `Page | Section | Void News` for a leaf,
from `sectionTitle()` in `frontend/app/lib/siteMeta.ts`.

---

## 2. Typography: four voices

Loaded once, in `frontend/app/layout.tsx`, through `next/font/google`. Nothing
else may name a family.

| Voice | Family | Weights | Variable | Use |
|---|---|---|---|---|
| Editorial | Playfair Display | 400, 700 | `--font-editorial` | Headlines, story titles, section headers, pull quotes, nameplates |
| Structural | Inter | 400, 500, 600 | `--font-structural` | Body text, navigation, labels, buttons, UI chrome |
| Meta | Barlow Condensed | 400, 500, 600 | `--font-meta` | Category tags, source counts, timestamps; a condensed grotesque in the Franklin Gothic tradition |
| Data | IBM Plex Mono | 400 | `--font-data` | Bias scores, numeric data, tabular figures |

Playfair and Inter preload; Barlow and IBM Plex do not, so the two families on
the critical path stay uncontended at first paint.

**Never write a `font-family` literal.** `next/font` registers hashed family
names, so a rule that spells `'IBM Plex Mono'` silently renders in the
fallback. Reference the four variables.

### Scale (`frontend/app/styles/tokens.css`)

```css
--text-xxs:   clamp(0.625rem, 0.55rem + 0.25vw, 0.75rem);
--text-xs:    clamp(0.5625rem, 0.5rem + 0.25vw, 0.625rem);
--text-sm:    clamp(0.75rem, 0.7rem + 0.2vw, 0.875rem);
--text-base:  clamp(0.875rem, 0.8rem + 0.3vw, 1rem);
--text-lg:    clamp(1.0625rem, 0.95rem + 0.4vw, 1.3rem);
--text-xl:    clamp(1.25rem, 1.1rem + 0.6vw, 1.75rem);
--text-hero:  clamp(1.5rem, 1.3rem + 1.2vw, 3rem);
--type-lead-headline: clamp(1.8rem, 1.36rem + 1.92vw, 3.6rem);
```

`--type-lead-headline` is the rank-0 hero. `--type-digest-headline` and
`--type-wire-headline` both alias `--type-card-headline`: the three-tier
display scale collapsed to two when the feed went to twenty.

Utility classes in `styles/typography.css`: `.text-hero` (tracking -0.03em),
`.text-xl` (-0.015em), `.text-lg` (-0.005em), `.text-label` (0.08em, caps),
`.text-caption`, `.text-data` (tabular-nums, line-height 1.3), `.text-score`,
`.text-timestamp`, `.category-tag` (0.04em, caps).

### Rules

- Headlines: Playfair 700, sentence case.
- Body: Inter 400, line-height 1.6, measure capped (65ch in the feed, 72ch on
  prose pages through `--measure-prose`).
- Never mix voices inside one element.
- At most three headline levels visible at once.
- No em dash or en dash in any page-facing string. Gated by
  `frontend/test/copy-facts.test.mjs`.

---

## 3. Colour

### Light, "Morning Edition" (`:root, :root[data-mode="light"]`)

```css
--bg-primary:    #F0EBDD;  /* warm paper */
--bg-secondary:  #E8E2D4;  /* aged newsprint */
--bg-card:       #F5F0E4;
--bg-elevated:   #F5F0E4;
--fg-primary:    #1A1A1A;
--fg-secondary:  #4A4540;
--fg-tertiary:   #686260;
--fg-muted:      #52504A;  /* 4.5:1 on paper */
--border-subtle: #E8E2DB;
--border-strong: #C8C0B5;
--divider:       #D4CCC2;
```

### Dark, "Evening Edition" (`:root[data-mode="dark"]`)

```css
--bg-primary:    #1C1A17;  /* dark walnut, not terminal black */
--bg-secondary:  #252320;
--bg-card:       #2A2725;
--bg-elevated:   #333028;
--fg-primary:    #EDE8E0;
--fg-secondary:  #B8B0A5;
--fg-tertiary:   #A09890;
--fg-muted:      #9A938B;
--border-subtle: #3A3530;
--border-strong: #4A4540;
--divider:       #403B35;
```

### The lean spectrum: blue, green, red

Green is reserved for the centre, so a story at the centre does not read as
"grey, therefore unmeasured". Depth encodes distance from the centre.

| Token | Light | Dark |
|---|---|---|
| `--bias-far-left` | `#0E2E70` | `#5088D0` |
| `--bias-left` | `#1B5298` | `#6498D8` |
| `--bias-center-left` | `#2E78B4` | `#78AEDE` |
| `--bias-center` | `#2B784A` | `#48B870` |
| `--bias-center-right` | `#C4503E` | `#D05C48` |
| `--bias-right` | `#9C2C22` | `#CC3E34` |
| `--bias-far-right` | `#6E1610` | `#B02E26` |

Every value clears 4.5:1 on its own paper. Any tilt left is the blue family,
any tilt right the red family, and nothing else in the product may use those
two families for a non-bias purpose.

Three further ramps, the same in both modes: `--sense-low|medium|high`
(`#22C55E` / `#EAB308` / `#EF4444`), `--rigor-high|medium|low` (the same
three), and `--type-reporting|analysis|opinion` (`#3B82F6` / `#8B5CF6` /
`#F97316`).

### Section accents

`--palette-news` `#B26F52` (terracotta), `--palette-weekly` `#B91C1C`
(magazine red), `--palette-history` `#5C4033` (burnt umber), each with a
dark-mode counterpart. A section gets this accent and nothing else.

### The cinematic layer

Consumed tokens, all of which adapt between modes:

| Group | Tokens | What they do |
|---|---|---|
| Amber | `--cin-amber` (`#946B15`) and its bright, dim, ghost, glow variants | Warm accent, rim light, hover |
| Ash and paper | `--cin-ash*`, `--cin-paper-highlight`, `--cin-paper-shadow` | Neutral tones, paper texture shifts |
| Grain | `--cin-grain-opacity` (0.035 light, lower in dark) | SVG `feTurbulence` overlay on `.page-container::after`; overlay blend in light, soft-light in dark |
| Vignette | `--cin-vignette-color` | Edge darkening on `.page-container::before`, one stop above the grain |
| Grade | `--cin-grade`, `--cin-grade-editorial` | Page-level filter chain (contrast, saturate, sepia) |
| Image grade | `--img-grade-feed \| deepdive \| weekly \| epaper \| history` | Per-surface variants applied to `img` |
| Shadows | `--shadow-cinematic-contact \| ambient \| dramatic \| lifted` | Three-tier depth through `color-mix` |
| Elevation | `--shadow-e0..e3`, `--blur-e1..e3` (8/16/24px) | Surface, floating chrome, popout, modal |
| Z | `--z-base` 1, `--z-card` 2, `--z-sticky` 10, `--z-nav` 20, `--z-dropdown` 30, `--z-tooltip` 40, `--z-cinematic` 45, `--z-overlay` 50, `--z-player` 60, `--z-modal` 100, `--z-popup` 150 | One scale |

Applying `filter` to a page container creates a containing block that breaks
`position: fixed` descendants, which is why the page grade is scoped and why
the image grades exist as separate variants.

---

## 4. One token system, with section overrides

**The standard.** There is one token file, `frontend/app/styles/tokens.css`.
A section may override exactly five things: an accent ramp, its paper
(`--bg-primary`), its card surface (`--bg-card`), its grain
(`--cin-grain-opacity`) and its grade (`--cin-grade`). Nothing else. A section
that needs a value the globals do not have asks for the global; it does not
open a private namespace.

The rest of the standard, stated so a reviewer can fail a diff against it:

- **Fifteen easings, all named.** The five of v3.0 (`--ease-cinematic`,
  `--ease-whip`, `--ease-rack`, `--ease-out`, `--ease-unfold`) plus the nine
  the code was already using as literals and now names: `--ease-spring`
  `(0.34, 1.56, 0.64, 1)` (the overshoot; `--spring` is a `linear()` curve
  and stays), `--ease-sine`, `--ease-out-quad`, `--ease-classic`,
  `--ease-shake`, `--ease-stamp`, `--ease-hard-cut`, and `--ease-archive-snap`
  and `--ease-lectern-turn` promoted from History. No raw `cubic-bezier(`
  outside `tokens.css`; `--ease-steadicam`, `--ease-dramatic`,
  `--ease-whip-out`, `--ease-in`, `--ease-in-out` are gone, unreferenced.
- **Six durations.** `--dur-fast` 150ms, `--dur-step` 260ms, `--dur-normal`
  300ms, `--dur-reveal` 350ms, `--dur-morph` 400ms, `--dur-slow` 600ms.
  `--dur-instant` and `--dur-micro` are gone. A literal that matches a token
  is the token; 200ms has no token and stays a literal.
- **No `font-family` literal.** The four variables only (`onair.css` named
  the raw `--font-playfair` family for 29 rules; it names the semantic
  tokens now).
- **Five radii.** `--radius-none` 0, `--radius-sm` 1px, `--radius-md` 2px,
  `--radius-pill` 999px, `--radius-sheet` 16px 16px 0 0. The 62 literal
  radii that predate the scale each carry a `stylelint-disable-next-line`
  with the reason; the list only shrinks. The product is newsprint, not an
  app.
- **One reduced-motion block**, in `animations.css`, global: durations to
  0ms (not .01ms: at .01ms a transition still starts, and `HistoryLanding`
  read a start value and drew the timeline 330px off), `scroll-behavior:
  auto` on `*` with `!important` (the old `html` rule lost to the `smooth`
  that `globals.css` set after its imports, so under reduced motion the
  page had always scrolled smoothly). 52 per-file blocks that set a state
  (opacity, transform, display, stroke) stay; 15 that only repeated the
  global one are gone.
- **Every keyframe defined once.** `pullSpin`, `skbFadeIn` lost their
  byte-identical twins; `onboardDialogInSheet`, `fpBroadcastInCentered` and
  `wire-input-shake` are the variants that used to shadow their namesakes.
- **188 global tokens** (267 declarations across the light and dark blocks),
  down from 326 names: 138 unreferenced names deleted, the derivation in
  `frontend/test/css-tokens-purge.txt`.
- **One image grade with variants**, applied to `img`, never to a page
  container.
- **One shadow ladder, one z-index scale, one spacing scale**
  (`--space-1` through `--space-8`).

**Gates.** `frontend/test/css-lint.mjs` (stylelint, three rules, in
`npm test`): no `cubic-bezier(` outside `tokens.css`, no `font-family` value
off the four semantic tokens, no literal `border-radius` without a disable
and its reason. `frontend/test/css-parity.test.mjs`: every class selector is
referenced by markup (1,168 of 3,109 were not on 2026-09-21; the pre-purge
report is `css-parity-baseline.txt`). `games.css` and `revolt.css` are exempt
from both: hidden routes, kept for their return.

---

## 5. The frame: one masthead, one footer

`NavBar` and `Footer` are mounted once, in `frontend/app/layout.tsx`, above
and below `{children}`. **No section renders its own topbar.**

`frontend/app/components/NavBar.tsx`:

- **Section from the pathname.** `sectionForPath()` runs the same on the
  server and the client, so the served HTML already carries the right
  nameplate and the right `aria-current`, with no flash.
- **Nameplate** beside the wordmark for `history`, `weekly`, `paper` and
  `audio` (On Air's page wears the Audio nameplate: it is a programme inside
  the section, and the nameplate links to the section). Every other route
  gets the experimental badge and the tagline instead.
- **Section links**: Audio, History, Weekly. **Page links**: Sources,
  Feedback, About. The current page carries `aria-current="page"` and a 2px
  accent rule under the label, no arrow; Audio is current on `/onair/` too.
  At rest the links are neutral; on hover and focus each draws its own
  accent in from the left (History umber, Weekly red, Audio teal), the same
  device the nameplate uses. On Air and Listen were two links for one
  section until 2026-09-21; Listen was a page of feed addresses and 301s to
  `/audio`, which holds every programme, its play buttons and the feeds.
- **Dateline only on daily surfaces.** `DATED_SECTIONS` is news, On Air,
  Sources and a story page. The date is the build-time UTC string passed down
  from the layout; without it the masthead shows no date rather than the
  viewer's clock.
- **Search on the front page only.** The button raises a DOM event
  (`SEARCH_EVENT`) that `HomeContent` listens for, so the masthead holds no
  feed state.
- **Theme toggle hidden below 768px**, where the drawer carries it, so it is
  not rendered twice.
- **Scroll-compact**: `data-scroll-compact` goes on past 80px and off at 40px,
  through a single rAF-throttled listener. It scales the logo and fades the
  tagline and never changes the bar's height: the 6px it used to lose was
  compensated by scroll anchoring at the top of every client-side navigation,
  which landed the page at scrollY 6 with its first pixels under the bar
  (2026-09-21). `html { scroll-padding-top }` keeps navigations and in-page
  anchors below the bar.

`Footer.tsx` carries ten destinations: On Air, History, Weekly, Paper, Audio,
About, Sources, Feedback, Press, Privacy.

### Section skins

A section declares its palette on `:root` while it is mounted, so the masthead
and footer, which sit outside the section container, can wear the same paper:

```css
:root:has(.hist-page) { --hist-bg: …; --hist-ink: …; --hist-accent: …; }
:root:has(.wk-page)   { --wk-accent: …; --wk-paper: …; }
:root:has(.np-root)   { … }
```

Declared at the top of `styles/history.css`, `styles/weekly.css` and
`paper/paper.css`; consumed by the "Section skins" block in
`styles/components.css`, which swaps `--nav-accent`, the background and the
border on `.nav-header` and `.site-footer`, and paints `body` in the section's
paper so the page does not end in a seam of a different colour. Paper
additionally neutralises the chrome for print. The floating player is the same
pattern, one variable deep.

### The experimental banner

`components/ExperimentalBanner.tsx` sits **below** the masthead and renders
only from the second visit on. A first-time reader, usually arriving from a
shared link, meets a headline before a bug-report request; the masthead's
badge carries the posture until then. A visit is counted once per browser
session, a dismissal lasts fourteen days, and nothing renders when storage is
unavailable.

### The browser wears the section (`styles/brand.css`)

Six touches, each a token and a rule, none of them script, all of them
asserted by `scripts/verify-headless.mjs` so that a touch which quietly rots
fails a gate instead of fading out:

| Touch | Rule | Section-aware by |
|---|---|---|
| Status bar | `theme-color` from the `viewport` export of the root, History and Weekly layouts: the section's **paper**, never its accent. `ThemeToggle` rewrites both metas from `--nav-paper`, the custom property the masthead is painted with (a property does not transition, so it is already the new value the moment the mode flips) | the layout that exports it |
| Scrollbar | `html { scrollbar-width: thin; scrollbar-color: var(--scrollbar-thumb) transparent }` plus the WebKit pseudo-elements, no radius | `:root:has(.hist-page)` and `:has(.wk-page)` retint `--scrollbar-thumb` with the section accent mixed into its paper |
| Selection | 24% of the accent under the ink, `color-mix`; the old inversion survives only under `@supports not (color-mix)` | the same two selectors swap the accent |
| Nameplate | `.nav-nameplate::after` draws a 1px rule in from the left on hover, focus and `aria-current`, on `--dur-step` and `--ease-unfold` | `--nav-accent` |
| Reading rule | on a long read only (`.story-page`, `.hist-hearing-page`, `.wk-issue`), a 2px brass `.nav-header::after` scales with `animation-timeline: scroll(root block)`; nothing under reduced motion or where the timeline is unsupported | brass, deliberately not the accent |
| On air | `NavBar` sets `data-playing` from `useAudio().isPlaying`; the wordmark's beam rocks three degrees each way over six seconds in brass (`brand-on-air`), never the lean sweep, off under reduced motion | brass |

What is NOT in the layer, with the reason: the loading skeleton's ink doodle
(a rare client refetch state with inline radii, not worth a rule) and
cross-document view transitions (they would cross-fade the sticky masthead
against itself, and the React API is behind an experimental flag).

---

## 6. Layout

### Canvas

`--canvas-max: min(92vw, 1600px)`. The home page's `.page-main`, `.nav-inner`
and `.site-footer` spell the expression out instead of reading the token, for
a documented Chromium bfcache defect (`styles/layout.css`, top). That
exception belongs to the frame alone; any new route consumes the token.

### Zones (`styles/layout-zones.css`)

One grid definition for the feed, the lead split and the Deep Dive body.

| Zone | Selector | Behaviour |
|---|---|---|
| Lead split | `.lead-split` | 50/50 image and text when rank 0 has a cached image; one column on a phone |
| Lead twin | `.lead-twin` | **`1.3fr 1fr` at 1024px and up, with rank 1's headline one notch down.** The ranker had already decided an order; two identical halves discarded it |
| Feed grid | `.feed-grid` | `align-items: start`, `grid-auto-rows: max-content`, so cards with different headline sizes do not ragged-baseline |
| Wire grid | `desktop-feed.css` | 5 columns at 1440px and up, 4 at 1024 to 1439 |
| Bias snapshot | `.bias-snapshot--inline`, `--rail` | Horizontal strip in the Deep Dive header; vertical column in the right rail at 1280px and up |
| Deep Dive body | `.dd-body--2col` | `1.7fr 1fr` at 1280px, `1.6fr 1fr` at 1440px and up, one column below |

### Spacing

```css
--space-1: clamp(0.125rem, 0.1rem + 0.1vw, 0.25rem);   /* 2-4px   */
--space-2: clamp(0.25rem,  0.2rem + 0.2vw, 0.5rem);    /* 4-8px   */
--space-3: clamp(0.5rem,   0.4rem + 0.4vw, 0.75rem);   /* 8-12px  */
--space-4: clamp(0.75rem,  0.6rem + 0.6vw, 1rem);      /* 12-16px */
--space-5: clamp(1rem,     0.8rem + 0.8vw, 1.5rem);    /* 16-24px */
--space-6: clamp(1.5rem,   1rem + 1.5vw, 2.5rem);      /* 24-40px */
--space-7: clamp(2rem,     1.5rem + 2vw, 4rem);        /* 32-64px */
--space-8: clamp(3rem,     2rem + 3vw, 6rem);          /* 48-96px */
```

---

## 7. The feed: cards, the lean label, the skybox

### The one lean ladder

`frontend/app/lib/biasColors.ts` owns the question "what does this story's
lean say", and every surface that names it calls `storyLeanLabel()`. Before
it, three functions answered the same question three ways from one number, and
a card could read as a confident direction while the Deep Dive called the same
story flat.

`leanLabelState()` returns one of four states, and a card says three of them
out loud:

| State | The card reads | When |
|---|---|---|
| `confident` | a direction, plus the score | The mean is clearly off centre, or the coverage roster is lopsided and the mean agrees in sign |
| `balanced` | **Balanced** | Measured, supported, not split, mean at the centre. The score is withheld |
| `contested` | **Contested** | The support gate failed but both wings are present and polarization is high |
| `unmeasured` | **Not measured** | Too few measured articles, outlets or confidence for the engine to have a read |

The word "Flat" is gone, and `frontend/test/labels.test.mjs` asserts it stays
gone.

**The Sigil tilts only on a confident read.** `components/Sigil.tsx` runs the
same gate as the caption: a suppressed label gets a level beam in muted ink,
because a beam that tilted under a withheld label hinted at a direction the
caption had just declined to state. The beam angle is
`((displayLean - 50) / 50) * 24` degrees through the perceptual expansion
curve, and it rides `--spring-beam` over `--beam-tilt-dur`.

**The caption shows on phones too** (`styles/mobile-feed.css`). The ring
colour alone cannot say "Balanced" or "Not measured", and a label that exists
on desktop and not on a phone is one card saying two things. Floored at 9px,
nowrap, allowed to run wider than the mark.

### The skybox is one object

`styles/skybox-banner.css`, end of file. The compact skybox used to be two
peer-weighted columns, The Brief and Opinion, each claiming the day in one
read above the first headline. The Brief keeps its column; **Opinion folds to
a single line beneath it** (label, lean badge, headline), still a tap target
that expands in place. The Brief's preview clamps to two lines, and the first
headline moves up a row.

---

## 8. Deep Dive

Two implementations, split by device.

**Desktop: `components/InlineDeepDive.tsx`.** An in-flow, full-width block
inside the feed that pushes later cards down. No fixed positioning, no
backdrop, no body scroll lock, no focus trap. Adds `inline-dd.css` for the
in-flow chrome.

**Phones: `components/DeepDive.tsx`.** Not a modal and not a bottom sheet: it
fills the viewport as its own page and replaces the feed, mounts the shared
masthead at the top exactly as `/onair` does, pushes a history entry so the
hardware back button returns to the feed, and offers prev and next walkers.
One scrollable page; the old Story and Spread segmented switch is gone.

Shared between them: `Sigil`, `DeepDiveSpectrum`, `BiasSnapshot`,
`ComparativeView`, `SpreadDisagreement`, `ClaimConsensusSection`,
`SummaryWithContradictions`, and `LazyOnView` (an IntersectionObserver wrapper
that defers the heavy sections). `verify.css` and `deep-dive-page.css` ship
with the lazy chunk rather than globally.

`DeepDiveSpectrum` positions each source logo at its exact lean, with three
toggleable views (Ink Ridge, Witness Line, Terrain Map) remembered in
`localStorage`. It is the sole source display; the separate source roster was
removed. The archival cross-link into History renders again.

---

## 9. Mobile

`MobileTabBar.tsx` is the single primary navigation surface below 768px:
three zones, a raised centre brand anchor between two side tabs.

```
[ On Air ]        (( Home ))        [ Menu ]
```

Home is the Sigil mark in the news terracotta, larger than the side tabs,
punching through the bar. On Air always navigates to `/onair`, with a small
teal dot for the playing state. Menu opens `MobileSidePanel`, which carries
the theme control and the destinations the masthead drops.

Layout rules below 767px (`styles/responsive.css`, `styles/mobile-feed.css`):

| Element | Rule | Why |
|---|---|---|
| `.page-main`, `.nav-inner`, `.site-footer` | padding `--space-5` | Recovers about 32px of content width |
| Lead headline and summary | `max-width` removed | The container constrains width; a `ch` cap is wasted |
| All headlines | `overflow-wrap: break-word` | A long word must not force a horizontal scroll |
| `.section-header` | `flex-wrap: wrap` | The timestamp wraps instead of overflowing |
| Touch targets | 44x44px minimum | WCAG |

---

## 10. Motion

### Principles

1. Every animation communicates a state change.
2. Only `transform` and `opacity` animate.
3. Nothing locks: an animation is always interruptible.
4. A double rAF snap before a transition, for 90Hz and 120Hz displays.
5. Everything collapses to 0ms under `prefers-reduced-motion: reduce`.

### Tokens

Springs, as `linear()` curves in `tokens.css`: `--spring` (the default),
`--spring-bouncy`, `--spring-snappy`, `--spring-gentle`, `--spring-elastic`,
`--spring-beam` (tighter, so a second oscillation reads as mass).

Durations: `--dur-fast` 150ms, `--dur-step` 260ms, `--dur-normal` 300ms,
`--dur-reveal` 350ms, `--dur-morph` 400ms, `--dur-slow` 600ms.

Easings, the fifteen the system names (section 4): `--ease-cinematic`
`cubic-bezier(0.22, 1, 0.36, 1)` for the primary deceleration, `--ease-whip`
`(0.25, 0, 0, 1)`, `--ease-rack` `(0.4, 0, 0.2, 1)` for a focus pull,
`--ease-out` `(0.16, 1, 0.3, 1)`, `--ease-unfold` `(0.14, 0.8, 0.26, 1)`,
`--ease-spring` `(0.34, 1.56, 0.64, 1)` for an overshoot, and the nine
one-offs named after what they do.

### What moves

| Element | Trigger | Motion |
|---|---|---|
| Story card | Reveal in view | `anim-stagger` keyframes, 260ms, 40ms apart |
| Cold open | Page load | Nav settles at 80ms, skybox dollies in at 200ms, lead at 320ms, feed at 480ms |
| Sigil beam | Data arrives | Tilt to the lean angle on `--spring-beam`, only on a confident read |
| Card lift | Hover, fine pointer only | `translateY(-2px)` plus an elevation bump, 180ms |
| Press state | Pointer down | `scale(0.98)`, 80ms |
| Inline Deep Dive | Open | Section cascade, `translateY(12px)` to 0 |
| Theme toggle | Tap | Cross-fade plus a 700ms warmth swell on `.page-main`, zero layout shift |
| History timeline | Scroll | Native snap, plus a CSS scroll-driven parallax (section 13) |
| Reading rule | Scroll, long reads only | `.nav-header::after` scales 0 to 1 on a scroll timeline, no listener |
| Wordmark beam | Audio playing | `brand-on-air`, 3 degrees each way over 6s, brass |
| Nameplate rule | Hover, focus, current | `scaleX(0)` to 1 from the left, `--dur-step` on `--ease-unfold` |

### Reduced motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0ms !important;
    animation-delay: 0ms !important;
    transition-duration: 0ms !important;
    transition-delay: 0ms !important;
  }
}
```

One block is the standard. Motion that cannot simply be zeroed, such as the
History parallax, is wrapped in
`@media (prefers-reduced-motion: no-preference)` instead of being switched off
afterwards.

---

## 11. Share cards: one composer

`frontend/app/lib/ogCard.tsx` draws every card the product emits. The grammar,
in the order the eye reads it:

```
[brass Sigil]  VOID NEWS          the lockup, identical on every card
──────────────────────────
▌ History                         the section nameplate, in its accent
The Cyrus Cylinder                the card's own content
539 BCE  ·  Middle East
▓▓▓▓▓▓▓                           the lean spectrum, where there is one
tagline                    news.voidvision.org
```

Before it there were three looks for one brand, and one of them named products
that do not exist. The Sigil is the coverage ring with the level balance beam,
the same footed geometry as `ScaleIcon.tsx`, `SigilWordmark.tsx` and
`public/favicon.svg`, drawn in brass.

- `og-image.png` is rendered by `node brand/ci/render_og.mjs`. It is never
  hand-edited.
- **Per-story cards are emitted for the latest edition only**
  (`story/[id]/ogCard.tsx`, `EDITIONS_WITH_CARDS = 1`). The archive is over
  1,500 rows and every card is a build-time render; older permalinks keep the
  site-wide brand card.
- **A card states a lean only when the read is confident.** It runs the same
  `leanLabelState` gate as the feed card. A share card is the most public and
  least correctable surface in the product, and it has no room to explain what
  "Contested" means, so the line is left out and the source count stands alone.
- Editing the JSX: satori needs an explicit `display` on every element with
  more than one child. Keep the `display: "flex"` even where it looks
  redundant.

---

## 12. Prose pages, and Paper

### Prose pages

`styles/prose-page.css` is the shared reading surface for Audio, Press and
Privacy. It replaced `about.css`, which shipped 1,102 lines to four routes and
matched nothing in any component. One measure (`--measure-prose: 72ch`, set as
a property so a page that needs more room widens the token rather than
overriding the rule), one type ramp off `--text-*`, spacing from `--space-*`,
radii from the three tokens. Page files layer on top and win, being imported
after.

### Print for the long reads (`styles/brand.css`)

A Deep Dive page and a History event print the way Paper does: the masthead,
footer, bars, banner, player, vignette and rail are gone, the paper is white
and the ink black, every reveal is revealed, and the sheet opens with
`components/PrintMast.tsx` (the wordmark and the page's own address, hidden on
screen). Paper keeps its own sheet.

### Paper (`frontend/app/paper/paper.css`)

The printable front page, scoped to `.np-root`: the same twenty stories as the
home page, in the same order, read from `build-data/feed.json`, every headline
a link to its Deep Dive.

- **Two voices, the site's own.** Playfair sets the nameplate, headlines and
  decks; Inter sets labels, bylines and body. Two further families were
  referenced through variables nothing defined, so the broadsheet had been
  rendering in Georgia since it was written; both went rather than being wired
  up to add a fourth and fifth face.
- **Six tokens**: `--np-paper` `#F4F1EC`, `--np-ink` `#111111`,
  `--np-ink-mid`, `--np-ink-light`, `--np-rule`, `--np-rule-dark`, with a
  dark-mode override block. Nothing here is a bias colour.
- **Six reading columns on a desktop, three in tablet landscape, one on a
  phone** (`@media (max-width: 767px)`). A broadsheet grid that keeps six
  columns on a 390px screen is a photograph of a newspaper, not a newspaper.
- No classifieds, no datelines, no weather, no edition route.
- Gated by P-01 to P-04 in `scripts/verify_sections.py` and
  `tests/test_paper.py`.

---

## 13. History: "Archival Cinema"

`.hist-page` namespace, `styles/history.css`. Foxed vellum, iron gall ink,
aged brass. The palette is `--hist-*`, declared on `:root` while a History
page is mounted: `--hist-accent` burnt umber, `--hist-brass` aged brass,
`--hist-paper` `#F2EDE0`, `--hist-ink` `#2C2418`, plus six perspective
identity colours `--hist-persp-a` through `-f`.

### The landing

`/history` is a **Server Component** (`frontend/app/history/page.tsx`). It
reads the catalogue at build and hands it down as a prop. It used to be a
client component that fetched in an effect, so a crawler saw an empty `<main>`
and a reader saw one italic line until the round trip landed. There is an
`<h1>`, every card, and era, region and thread browse links in the served
HTML.

**The timeline scrolls natively.** What used to be here: a `wheel` listener
with `preventDefault()` turning vertical delta into horizontal velocity, a rAF
friction loop with its own snap at rest, a second rAF loop that scrolled
whenever the pointer came within 60px of a screen edge, and a third listener
writing `transform` on the background every frame. Three drivers, one
scrollbar, and physics no other section uses.

Now:

- `scroll-snap-type: x mandatory` on the container, desktop only (below 768px
  the timeline is a vertical scroll and there is nothing for `x` to act on).
- **`scroll-snap-align: center`, not `start`.** Every affordance on the page
  already centres: the focused-index reader measures from
  `scrollLeft + clientWidth / 2`, and the year ribbon, the era pills and the
  prev and next pair all call `scrollIntoView({ inline: "center" })`. With
  `start` the browser would re-snap a card flush left after each of those had
  just centred it.
- **A prev and next caret pair**, for a mouse with no horizontal wheel, each
  naming its destination. It replaced the edge-scroll zones, which moved the
  scrollbar under the pointer without being asked.
- **Parallax is a CSS scroll-driven animation**: the background bands travel
  30% of the cards' distance over the container's inline scroll range, inside
  `@media (prefers-reduced-motion: no-preference)` and
  `@supports (animation-timeline: scroll(nearest inline))`. No support means
  no parallax, which is also what a reduced-motion reader gets.

### The museum grammar

The event page walks the reader through exhibits without didactic headers:
hero, the inscribed one-line crack, the Record block, context, perspectives,
omissions, evidence, exit. The Record block merges key facts and key figures
into one ruled `dl` under a chisel-grain texture (`feTurbulence fractalNoise`,
horizontal bias, multiply at 7%, screen in dark mode). Each perspective shows
one lead argument, the rest behind a count and a directional glyph, the way a
vitrine makes you lean in. Connection types are drawn as glyphs, not labels:
`caused` is a down arrow, `consequence` and `response-to` an up arrow,
`influenced` and `parallel` a centred dot.

---

## 14. Accessibility

- **Contrast** 4.5:1 for body text, 3:1 for large, in both modes. Every lean
  colour is checked against its own paper.
- **Focus** visible on every interactive element, through `:focus-visible`.
- **Keyboard** throughout: Tab, Enter, Escape, arrows. The Hearing adds `j`
  and `k` anywhere the reader is not typing.
- **Screen readers**: semantic HTML, `aria-current="page"` on the masthead,
  live regions for the era header.
- **Colour is never the sole carrier.** The Sigil encodes lean as a beam angle
  and coverage as a ring fill; the lean state is also written out in words.
- **Reduced motion** collapses everything, and motion that cannot collapse is
  gated behind `no-preference` instead.
- **Touch targets** 44x44px minimum.
- **Zoom** to 200% with no horizontal scroll, asserted by
  `frontend/scripts/verify-responsive.mjs`.
- **The sweep.** `frontend/scripts/verify-headless.mjs` loads every route
  family at 390, 768, 1024 and 1440 in both modes and asserts: no console or
  hydration error, no same-origin 4xx, no dangling link, one `h1`, one
  masthead and footer with the right `data-section` and `aria-current`, a
  name on every control, no dash in chrome, the skip link first in the Tab
  order with a visible ring, and axe-core at WCAG 2.1 AA (critical and
  serious fail). Then the scenarios: Deep Dive inline and full page, search by
  three routes, the theme toggle and both `theme-color` metas, the drawer's
  focus trap, the Sigil's popup, the shortcuts overlay telling the truth,
  the banner's second-visit rule, the player's presence per route, Paper
  parity, and the brand layer above. `--quick` runs in CI; the full grid by
  hand before a release. Its first run found six contrast failures (the
  dateline's stacked opacities, the player clock and chapter title, the
  History nameplate in dark, the long-view toggle), a control nested in a
  control (the player pill), a focusable row under `aria-hidden` (the year
  ribbon), a doubled masthead on the phone Deep Dive, and a lead Sigil whose
  popup closed a frame after it opened because the hover shift on its
  headline had trapped it under the stretched link.
---

## 15. Containment: `overflow-x: clip`, never `hidden`

**This is a system-wide rule, and it cost a rail and a topbar that had never
once pinned.**

`overflow-x: hidden` establishes a scroll container. A scroll container between
the viewport and a `position: sticky` descendant kills the stickiness silently:
the CSS is correct, the element simply never pins, and nothing in devtools says
why. On the History section four ancestors carried it, so the Hearing's rail
measured **y = -3130** at scrollY 4000, and the topbar had never pinned on any
History page either.

Use `overflow-x: clip` for horizontal containment. It clips without creating a
scroll container, so sticky survives. `layout.css` already carried this note for
`.page-container`; it had simply never been applied to `history.css`.

The exception is a rule that pairs with a real `overflow-y: auto` on a genuine
scroller (`.hist-tl-full`, `.hist-overlay`, `.hist-reel--vertical`). Those want
to be scroll containers.

`frontend/scripts/verify-responsive.mjs` asserts this by scrolling to 4000 and
checking the rail and topbar are still in the viewport.

## 16. The Hearing's rail

`/history/[slug]` is a server component; the rail is one of three client
islands.

- **Labels are legible at rest.** Hierarchy is weight and ink, not visibility:
  the current station is 700 / `--hist-ink`, the rest are 500 /
  `--hist-ink-muted`, plus the brass wash already on the current glyph.
  Showing only the current label left the reader with bare `01 02 03`.
- **Height-capped with an internal scroll.** Fifteen labelled stations can
  outgrow a short viewport, so the slot and the rail carry
  `max-height: var(--hist-rail-cap)`, the `<ol>` scrolls, and a JS effect keeps
  the current station in view. The track anchors to the rail, not the list, so
  it does not scroll away.
- **A prev/next caret pair** rides the ends of the track and names its
  destination. `j`/`k` move between stations anywhere the reader is not typing.
  Plain `ArrowUp`/`ArrowDown` are bound **only** when focus is inside the rail:
  taking line-by-line scroll away from a reader mid-account, on a page whose
  argument is that it is a long read, costs more than the shortcut is worth.
- **Tokens:** `--hist-rail-bar-h` (44px), `--hist-rail-caret` (16px),
  `--hist-rail-cap`, and `--hist-rail-col` widening from 17ch to 21ch at
  1280px.

### There is no scroll-snap on the spine, and there should not be

Measured on `partition-of-india`: the OPEN is 66 words, scenes run 89 to 209,
and the five account sections run **603 to 883 words**, which is three to five
viewport heights each. Mandatory snap would grab the reader at an account's top
and fight every gesture for 800 words. Navigation here is an affordance, not a
constraint. Recorded so it is not re-proposed.

### The full-bleed trap

A `grid-column: full` child cancels the container's `padding-inline` with a
negative margin. That arithmetic only works while the flanking tracks exist.
The text track is `min(--hist-measure, 100%)`, so below the measure it claims
the entire content box and the column gaps have nowhere to go: the grid
overflows by exactly `4 x gap`. At 390px that put a rest at 438px against a
390px viewport, cropping rather than scrolling because an ancestor clipped it.
The gap is therefore scoped to the widths where the flanks exist.
