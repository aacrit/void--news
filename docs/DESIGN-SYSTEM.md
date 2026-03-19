# void --news — Design System: "Press & Precision"

**Version:** 1.2
**Last updated:** 2026-03-19

---

## 1. Design Philosophy

**"Press & Precision"** — A modern newspaper that respects the printing press tradition while embracing the data density of modern interfaces.

**On arrival:** The quiet authority of a broadsheet. Clean, editorial, unhurried.
**On interaction:** The precision of a data terminal. Rich, layered, immediate.

This duality is the soul of void --news. The newspaper earns trust through restraint. The data layer earns trust through transparency.

---

## 2. Typography — Three Voices

| Voice | Font | Weight | Use |
|-------|------|--------|-----|
| **Editorial** | Playfair Display | 400, 700 | Headlines, story titles, section headers, pull quotes |
| **Structural** | Inter | 400, 500, 600 | Body text, navigation, labels, buttons, UI chrome |
| **Data** | JetBrains Mono | 400, 500 | Bias scores, source counts, timestamps, metrics, dot matrix |

### Type Scale (Fluid)

```css
--text-xs:    clamp(0.5625rem, 0.5rem + 0.25vw, 0.625rem);     /* 9-10px: metadata */
--text-sm:    clamp(0.75rem, 0.7rem + 0.2vw, 0.875rem);         /* 12-14px: captions */
--text-base:  clamp(0.875rem, 0.8rem + 0.3vw, 1rem);            /* 14-16px: body */
--text-lg:    clamp(1.125rem, 1rem + 0.5vw, 1.5rem);            /* 18-24px: subheads */
--text-xl:    clamp(1.5rem, 1.2rem + 1vw, 2.5rem);              /* 24-40px: headlines */
--text-hero:  clamp(2rem, 1.5rem + 2vw, 4rem);                  /* 32-64px: lead story */
```

### Editorial Rules

- Headlines: Playfair Display 700, sentence case
- Body: Inter 400, 1.6 line height, max 65ch measure
- Data labels: JetBrains Mono 400, all-caps for axis labels, tabular-nums
- Never mix voices within a single element
- Headline hierarchy: hero > xl > lg (max 3 levels visible at once)

---

## 3. Color System

### Light Mode — "Morning Edition"

Warm paper tones. Think aged broadsheet under morning light, not sterile white.

```css
:root[data-mode="light"] {
  /* Surfaces */
  --bg-primary:    #FAF8F5;   /* Warm paper */
  --bg-secondary:  #F2EDE8;   /* Aged newsprint */
  --bg-card:       #FFFFFF;   /* Clean card surface */
  --bg-elevated:   #FFFFFF;   /* Elevated surfaces */

  /* Text */
  --fg-primary:    #1A1A1A;   /* Near-black ink */
  --fg-secondary:  #4A4A4A;   /* Secondary text */
  --fg-tertiary:   #7A7A7A;   /* Captions, metadata */
  --fg-muted:      #A0A0A0;   /* Disabled, placeholder */

  /* Borders & Dividers */
  --border-subtle: #E8E2DB;   /* Light warm rule */
  --border-strong: #C8C0B5;   /* Column dividers */
  --divider:       #D4CCC2;   /* Section dividers (newspaper rules) */
}
```

### Dark Mode — "Evening Edition"

Dark walnut warmth. Retains newspaper character — not terminal black, not pure dark.

```css
:root[data-mode="dark"] {
  /* Surfaces */
  --bg-primary:    #1C1A17;   /* Dark walnut */
  --bg-secondary:  #252320;   /* Warm dark */
  --bg-card:       #2A2725;   /* Card surface */
  --bg-elevated:   #333028;   /* Elevated surfaces */

  /* Text */
  --fg-primary:    #EDE8E0;   /* Warm cream text */
  --fg-secondary:  #B8B0A5;   /* Secondary */
  --fg-tertiary:   #8A8278;   /* Tertiary */
  --fg-muted:      #5A5550;   /* Disabled */

  /* Borders & Dividers */
  --border-subtle: #3A3530;   /* Subtle warm rule */
  --border-strong: #4A4540;   /* Column dividers */
  --divider:       #403B35;   /* Section dividers */
}
```

### Bias Color System

Colors are consistent across light/dark modes for instant recognition. Designed for accessibility (min 4.5:1 contrast on both backgrounds).

#### Political Lean Spectrum

```css
--bias-left:        #3B82F6;   /* Blue — left lean */
--bias-center-left: #60A5FA;   /* Light blue — center-left */
--bias-center:      #9CA3AF;   /* Neutral gray — center */
--bias-center-right:#F97316;   /* Orange — center-right */
--bias-right:       #EF4444;   /* Red — right lean */
```

#### Sensationalism Scale

```css
--sense-low:     #22C55E;   /* Green — measured, factual tone */
--sense-medium:  #EAB308;   /* Yellow — moderate sensationalism */
--sense-high:    #EF4444;   /* Red — inflammatory, clickbait */
```

#### Opinion vs. Reporting

```css
--type-reporting: #3B82F6;   /* Blue — factual reporting */
--type-analysis:  #8B5CF6;   /* Purple — analysis/explainer */
--type-opinion:   #F97316;   /* Orange — opinion/editorial */
```

#### Factual Rigor

```css
--rigor-high:    #22C55E;   /* Green — well-sourced, data-backed */
--rigor-medium:  #EAB308;   /* Yellow — partially sourced */
--rigor-low:     #EF4444;   /* Red — unsourced claims */
```

---

## 4. BiasLens — "Three Lenses" (The Core Visual Language)

BiasLens is void --news's signature visual element. Three distinctive micro-visualizations, each encoding a different dimension of bias analysis. Replaces the earlier Dot Matrix (removed) and BiasStamp (removed) approaches.

**Component:** `BiasLens.tsx` (active) -- `BiasStamp.tsx` and `DotMatrix` are deleted.

### The Three Lenses

```
[Story Headline]
[Source Name] · [Time]   /  (3)  ■
                         N   R   P
```

| Lens | Name | Visual | Encoding |
|------|------|--------|----------|
| 1 (N) | **The Needle** | Tilting line with pivot dot | Political lean: rotates -30 to +30 degrees from center. Color from lean spectrum (blue left, gray center, red right). |
| 2 (R) | **The Signal Ring** | SVG ring (Harvey ball) with source count | Coverage/confidence composite: ring fill 0-100%. Source count displayed in center. Color: green (strong) / yellow (moderate) / red (weak). |
| 3 (P) | **The Prism** | Morphing shape (square to circle) | Opinion vs. reporting: square = factual reporting, circle = opinion. Color: blue (reporting) / purple (analysis) / orange (opinion). |

### Sizes

- **sm** (story cards): Needle 18px, Ring 18px, Prism 14px. Gap 6px.
- **lg** (lead story, deep dive header): Needle 28px, Ring 28px, Prism 22px. Gap 10px.

### Interaction

- **Desktop hover**: Each lens has its own independent popup with title, score, spectrum bar, and rationale sub-scores (when available from pipeline analysis).
- **Mobile tap**: Same popup positioned near the lens element.
- **Deep Dive source list**: Per-source BiasLens (sm) inline next to each source name.
- **Pending state**: When bias scores are fallback placeholders (not yet analyzed), the entire lens group renders at 35% opacity with grayscale filter and a "Pending" label.

### Accessibility

- Each lens has `role="img"` with descriptive `aria-label` (e.g., "Political lean: Center-Left, score 42").
- Popups use `role="tooltip"` with `aria-describedby` linking.
- Keyboard accessible: Tab to focus, Enter/Space to toggle popup, Escape to close.
- Color is never the sole differentiator -- shape (needle angle, ring fill, square-to-circle morph) encodes the data independently.
- Min 4.5:1 contrast on both light and dark backgrounds.

---

## 5. Layout System

### Desktop — "Broadsheet Grid"

```
┌──────────────────────────────────────────────────────┐
│  void --news              [World] [US]    [◐ Dark]   │ ← Top nav
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────────────────────┐ ┌──────────────────┐   │
│  │                         │ │                  │   │
│  │     LEAD STORY          │ │   STORY 2        │   │
│  │     (large card)        │ │   (medium card)  │   │
│  │                         │ │                  │   │
│  ├─────────────────────────┤ ├──────────────────┤   │
│  │  STORY 3  │  STORY 4   │ │   STORY 5        │   │
│  │  (small)  │  (small)   │ │   (medium)       │   │
│  └───────────┴────────────┘ └──────────────────┘   │
│                                                      │
│  ┌───────┬───────┬───────┬───────┬───────┐          │
│  │ ST 6  │ ST 7  │ ST 8  │ ST 9  │ ST 10 │          │ ← Dense grid
│  └───────┴───────┴───────┴───────┴───────┘          │
│                                                      │
│  Last updated: 6:00 AM CT    [↻ Refresh]             │
└──────────────────────────────────────────────────────┘
```

- Lead story gets hero treatment (large card, hero typography)
- Stories 2-5: medium cards in a 2-column asymmetric grid
- Stories 6+: compact cards in a dense 3-5 column grid
- Column dividers use thin rules (newspaper tradition)
- Generous whitespace between sections

### Mobile — "Tabloid Stack"

```
┌──────────────────┐
│ void --news   ☰  │ ← Minimal header
├──────────────────┤
│ [World] [US]     │ ← Section tabs
├──────────────────┤
│                  │
│  LEAD STORY      │
│  (full-width)    │
│  ● ● ○ ● ●      │
│                  │
├──────────────────┤
│  STORY 2         │
│  ● ● ● ○ ●      │
├──────────────────┤
│  STORY 3         │
│  ○ ● ● ● ●      │
├──────────────────┤
│  ...             │
│                  │
├──────────────────┤
│  [World] [US]    │ ← Bottom nav
│  Last: 6:00 AM   │
└──────────────────┘
```

- Single column, full-width cards
- Dot matrix inline below each headline
- Bottom navigation (thumb-reachable)
- Pull-down area shows "Last updated" + refresh
- Critical actions in bottom 40% of screen

### Deep Dive — Desktop

```
┌──────────────────────────────────────────────────────┐
│  ← Back to feed        Story: [Headline]              │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌─────────── UNIFIED SUMMARY ───────────────┐      │
│  │                                           │      │
│  │  What happened:  [synthesized narrative]   │      │
│  │                                           │      │
│  │  Where sources agree:  [consensus points] │      │
│  │                                           │      │
│  │  Where sources diverge: [divergence map]  │      │
│  │                                           │      │
│  └───────────────────────────────────────────┘      │
│                                                      │
│  COVERAGE BREAKDOWN                                  │
│  ┌─────────────────────────────────────────┐        │
│  │  Source A (NYT)        ● ● ○ ● ●  [→]  │        │
│  │  Source B (Fox)        ● ○ ● ○ ●  [→]  │        │
│  │  Source C (BBC)        ○ ● ● ● ○  [→]  │        │
│  │  Source D (Al Jazeera) ● ● ● ● ●  [→]  │        │
│  │  ...                                     │        │
│  └─────────────────────────────────────────┘        │
│                                                      │
│  BIAS DISTRIBUTION          FRAMING ANALYSIS         │
│  ┌────────────────┐        ┌────────────────┐       │
│  │  [dot density]  │        │ [emphasis map]  │       │
│  │  [chart]        │        │                 │       │
│  └────────────────┘        └────────────────┘       │
│                                                      │
└──────────────────────────────────────────────────────┘
```

### Deep Dive — Mobile

- Full-screen modal with swipe-to-dismiss
- Vertically stacked sections (summary → sources → charts)
- Each source row is tappable → opens article in browser
- Charts render full-width, scroll horizontally if needed
- Source rows use `flex-wrap: wrap` so metadata wraps instead of overflowing on narrow viewports

### Mobile Layout Rules (max-width: 767px)

| Element | Rule | Rationale |
|---------|------|-----------|
| `.page-main`, `.nav-inner`, `.site-footer` | padding: `--space-5` (~16px) | Recovers 32px content width vs desktop `--space-7` |
| `.lead-story__headline`, `.lead-story__summary` | `max-width` constraints removed | Container constrains width; `ch` limits are redundant and wasteful on mobile |
| `.story-card__headline`, `.lead-story__headline` | `overflow-wrap: break-word` (global) | Prevents long words from causing horizontal overflow |
| `.section-header` | `flex-wrap: wrap` | RefreshButton timestamp wraps instead of overflowing |
| Deep Dive source rows | `flex-wrap: wrap` | Source metadata wraps on narrow viewports |

---

## 6. Story Card Anatomy

### Desktop Card (Medium)

```
┌────────────────────────────────────────────┐
│  POLITICS                     2h ago       │  ← Category tag + time
│                                            │
│  Headline in Playfair Display              │  ← Editorial voice
│  700 weight, --text-xl                     │
│                                            │
│  Brief summary in Inter 400, 2 lines max.  │  ← Structural voice
│  Truncated with ellipsis if longer.        │
│                                            │
│  12 sources  /  (12)  ■                    │  ← Data voice + BiasLens (sm)
│              N   R    P                    │
└────────────────────────────────────────────┘
```

### Mobile Card

```
┌──────────────────────────────────┐
│  POLITICS · 2h ago               │
│                                  │
│  Headline in Playfair            │
│  Display 700                     │
│                                  │
│  Brief summary in Inter...       │
│                                  │
│  12 sources  /  (12)  ■          │
└──────────────────────────────────┘
```

### Lead Story Card (Desktop)

- Full-width or 2/3 width
- Hero typography (--text-hero for headline)
- 3-4 line summary
- Source count badge prominent
- BiasLens (lg) — larger Needle (28px), Ring (28px), Prism (22px)

---

## 7. Animation System

Adapted from DondeAI's "Ink & Momentum" motion system.

### Principles

1. **Purposeful** — every animation communicates state change, never decorative
2. **Symmetric** — open/close, in/out use identical timing
3. **Accessible** — all → 0ms under `prefers-reduced-motion: reduce`
4. **Performant** — only animate transform and opacity (GPU composite)
5. **Interruptible** — no animation locks

### Spring Presets

| Preset | Stiffness | Damping | Mass | Use |
|--------|-----------|---------|------|-----|
| snappy | 600 | 35 | 1 | Buttons, filter chips, toggles |
| smooth | 280 | 22 | 1 | Card expansion, panel slides |
| gentle | 150 | 12 | 1.2 | View transitions (feed ↔ deep dive) |

### Duration Tokens

| Token | Value | Use |
|-------|-------|-----|
| --dur-instant | 0ms | Reduced motion, immediate feedback |
| --dur-fast | 150ms | Hover states, small reveals |
| --dur-normal | 300ms | Card interactions, dot tooltips |
| --dur-morph | 400ms | View transitions |
| --dur-slow | 600ms | Page-level animations |

### Key Animations

| Element | Trigger | Animation | Duration |
|---------|---------|-----------|----------|
| Story card | Page load | fadeInUp (opacity + translateY 12px→0) | 300ms, 40ms stagger |
| Dot matrix | Card appear | Dots fade in left-to-right | 150ms, 30ms stagger |
| Bias tooltip | Hover/tap | Scale from 0.95→1, opacity 0→1 | 150ms ease-out |
| Deep Dive panel | Click story | Slide in from right (desktop) / bottom (mobile) | 400ms spring |
| Filter chips | Select | Scale 1→0.97→1, fill color wipe | 200ms spring |
| Refresh confirm | Tap refresh | Modal scale from 0.95, backdrop fade | 300ms ease-out |
| Dark mode toggle | Tap | Cross-fade colors, 0 layout shift | 400ms ease-out |
| Source list expand | Tap "12 sources" | Height auto with spring, items stagger | 300ms, 30ms stagger |

### Reduced Motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0ms !important;
    transition-duration: 0ms !important;
  }
}
```

---

## 8. Component Inventory

Active components in `frontend/app/components/`:

| Component | Purpose | Bias Visualization |
|-----------|---------|-------------------|
| `BiasLens` | Three Lenses bias visualization (Needle, Ring, Prism) | Primary -- used on all story cards and deep dive source list |
| `StoryCard` | Standard story card with headline, summary, metadata, BiasLens | Inline BiasLens (sm) |
| `LeadStory` | Hero story card, larger typography | Inline BiasLens (lg) |
| `DeepDive` | Slide-in panel: consensus, divergence, source coverage, tier breakdown | Per-source BiasLens (sm) |
| `FilterBar` | Category filter chips | -- |
| `NavBar` | Section navigation (World/US) with logo and theme toggle | -- |
| `RefreshButton` | Refresh with "last updated" timestamp | -- |
| `ThemeToggle` | Light/dark mode toggle | -- |
| `LoadingSkeleton` | Animated skeleton loading state | -- |
| `ErrorBoundary` | Error boundary wrapper | -- |
| `Footer` | Page footer with last-updated info | -- |
| `LogoFull` | Combination mark: void circle + scale beam icon + "void --news" wordmark as single SVG. Use in NavBar (desktop), Footer, error pages. Direction 5 "Negative Space O" — hollow O in "void", monospace "--news". | -- |
| `LogoIcon` | Icon-only wrapper around `ScaleIcon`. Use in mobile nav, loading indicators, compact contexts. `animation="none"` shows void circle only (favicon mark). | -- |
| `LogoWordmark` | Text-only "void --news" SVG — no icon mark. Hollow-O treatment. Use for edition lines, attribution, compact footers, print contexts. | -- |
| `ScaleIcon` | "Void Circle + Scale Beam" hybrid brand icon. Hollow ring as primary mark with scale beam passing through as fulcrum, weight ticks at beam ends, post + base below. 8 animation states: `idle` (gentle tipping), `loading` (dramatic tipping), `hover` (snappy tip), `analyzing` (deliberate read), `balanced` (spring settle), `pulse` (scale pulse), `draw` (stroke reveal on mount), `none` (void circle only — favicon mark). All animations respect `prefers-reduced-motion`. | -- |

**Removed components:** `BiasStamp.tsx` (517 lines, superseded by BiasLens), `DotMatrix`, `BiasTooltip`, `UnifiedSummary` (consensus/divergence is now inline in DeepDive).

### Logo Animation Deployment

| Context | Component | Animation State |
|---------|-----------|----------------|
| NavBar (mobile, on mount) | `LogoIcon` | `draw` → transitions to `idle` after 800ms |
| NavBar (desktop) | `LogoFull` | static SVG (idle beam embedded) |
| LoadingSkeleton | `LogoIcon` | `loading` |
| ErrorBoundary | `LogoIcon` | `balanced` |
| DeepDive panel header | `LogoIcon` | `analyzing` |
| Empty state | `LogoIcon` | `analyzing` |
| RefreshButton (idle) | `LogoIcon` | `idle` |
| RefreshButton (refreshing) | `LogoIcon` | `loading` |
| Footer | `LogoIcon` | `idle` |
| Favicon (`/public/icon.svg`) | Static SVG | void circle only (`none` equivalent) |

Add `.si-hoverable` class to any ancestor to activate hover animation on `LogoIcon` / `ScaleIcon`.

---

## 9. Spacing Scale

```css
--space-1:  clamp(0.125rem, 0.1rem + 0.1vw, 0.25rem);    /* 2-4px: tight */
--space-2:  clamp(0.25rem, 0.2rem + 0.2vw, 0.5rem);       /* 4-8px: compact */
--space-3:  clamp(0.5rem, 0.4rem + 0.4vw, 0.75rem);       /* 8-12px: default */
--space-4:  clamp(0.75rem, 0.6rem + 0.6vw, 1rem);          /* 12-16px: comfortable */
--space-5:  clamp(1rem, 0.8rem + 0.8vw, 1.5rem);           /* 16-24px: section */
--space-6:  clamp(1.5rem, 1rem + 1.5vw, 2.5rem);           /* 24-40px: major section */
--space-7:  clamp(2rem, 1.5rem + 2vw, 4rem);               /* 32-64px: page margin */
```

---

## 10. Elevation & Depth

Glass morphism adapted from DondeAI, muted for newspaper aesthetic.

| Level | Blur | Shadow | Use |
|-------|------|--------|-----|
| E0 Surface | 0 | none | Base content, cards |
| E1 Floating | 8px | subtle | Header, nav bars |
| E2 Popout | 16px | medium | Tooltips, bias popups |
| E3 Modal | 24px | strong | Deep dive overlay (mobile), confirmation dialogs |

Shadow values are warmer in light mode, cooler in dark mode to maintain the newspaper feel.

---

## 11. Iconography

Minimal. Line-style icons only. No filled icons except for active/selected states.

- **Category icons**: Minimal line illustrations (politics gavel, economy chart, health cross, etc.)
- **Navigation**: Standard line icons (home, search, settings, back)
- **Bias**: Dot matrix (no traditional icons needed)
- **Actions**: Minimal line (refresh, external link, expand, collapse)

---

## 12. Accessibility Requirements

### WCAG 2.1 AA Compliance

- **Contrast**: 4.5:1 for normal text, 3:1 for large text — all modes
- **Focus**: Visible focus indicators on all interactive elements (`:focus-visible`)
- **Keyboard**: Full keyboard navigation (Tab, Enter, Escape, Arrow keys)
- **Screen reader**: Semantic HTML, ARIA labels, live regions for dynamic content
- **Reduced motion**: All animations instant under `prefers-reduced-motion`
- **Touch targets**: ≥ 44×44px on mobile
- **Zoom**: Content readable at 200% zoom, no horizontal scroll
- **Color independence**: Dot matrix uses shape + color (never color alone)

### Dot Matrix Screen Reader Pattern

```html
<div class="dot-matrix" role="group" aria-label="Bias analysis for this article">
  <span class="dot dot--lean-center-left" aria-label="Political lean: center-left"></span>
  <span class="dot dot--sense-low" aria-label="Sensationalism: low"></span>
  <span class="dot dot--type-reporting" aria-label="Type: factual reporting"></span>
  <span class="dot dot--rigor-high" aria-label="Factual rigor: high"></span>
  <span class="dot dot--framing-moderate" aria-label="Framing: moderate"></span>
</div>
```

---

## 13. Design Token Summary

All values via CSS custom properties. No hardcoded values in components.

| Category | Token Prefix | Example |
|----------|-------------|---------|
| Colors (surface) | `--bg-` | `--bg-primary`, `--bg-card` |
| Colors (text) | `--fg-` | `--fg-primary`, `--fg-muted` |
| Colors (bias) | `--bias-`, `--sense-`, `--type-`, `--rigor-` | `--bias-left`, `--sense-low` |
| Typography | `--text-` | `--text-hero`, `--text-base` |
| Spacing | `--space-` | `--space-3`, `--space-6` |
| Animation | `--dur-`, `--spring`, `--ease-` | `--dur-normal`, `--ease-out` |
| Borders | `--border-` | `--border-subtle`, `--divider` |
| Elevation | `--blur-`, `--shadow-` | `--blur-e2`, `--shadow-e1` |
| Z-index | `--z-` | `--z-base(1)`, `--z-modal(100)` |
