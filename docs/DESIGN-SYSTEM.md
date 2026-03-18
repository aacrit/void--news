# void --news — Design System: "Press & Precision"

**Version:** 1.0
**Date:** 2026-03-18

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

## 4. Bias Dot Matrix — The Core Visual Language

The dot matrix is void --news's signature visual element. Minimal, scannable, information-dense.

### Anatomy

```
[Story Headline]
[Source Name] · [Time]   ● ● ○ ● ●
                         L S O R F
```

Five dots, one per bias axis:

| Position | Axis | Encoding |
|----------|------|----------|
| 1 (L) | Political Lean | Color from lean spectrum (blue → gray → red) |
| 2 (S) | Sensationalism | Green (low) → Yellow → Red (high) |
| 3 (O) | Opinion/Fact | Blue (reporting) → Purple (analysis) → Orange (opinion) |
| 4 (R) | Factual Rigor | Green (high) → Yellow → Red (low) |
| 5 (F) | Framing | Filled (neutral framing) → Half-filled → Hollow (heavy framing) |

### Dot Sizes

- **Filled circle (●)**: Strong signal, high confidence
- **Half-filled (◐)**: Moderate signal
- **Hollow circle (○)**: Weak signal or neutral
- **Size**: 8px desktop, 10px mobile (touch-friendly)
- **Spacing**: 6px between dots

### Interaction

- **Desktop hover**: Tooltip showing axis name + value + brief explanation
- **Mobile tap**: Bottom sheet with full bias breakdown
- **Cluster view**: Dot matrices stacked vertically for source comparison — patterns visible at a glance

### Accessibility

- Dots always accompanied by screen reader text: "Political lean: center-left. Sensationalism: low. Type: reporting. Rigor: high. Framing: moderate."
- Color + shape encoding (filled/half/hollow) — never color alone
- Min 4.5:1 contrast on both light and dark backgrounds

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
│  12 sources  ● ● ○ ● ●                    │  ← Data voice + dot matrix
│              L S O R F                     │
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
│  12 sources  ● ● ○ ● ●          │
└──────────────────────────────────┘
```

### Lead Story Card (Desktop)

- Full-width or 2/3 width
- Hero typography (--text-hero for headline)
- 3-4 line summary
- Source count badge prominent
- Dot matrix larger (12px dots)

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

| Component | Desktop | Mobile | Shared Logic |
|-----------|---------|--------|-------------|
| `StoryCard` | Multi-column, hover reveals | Full-width, tap reveals | Data fetching, bias display |
| `LeadStory` | Hero card, 2/3 width | Full-width, larger type | Same |
| `DotMatrix` | 8px dots, hover tooltips | 10px dots, tap bottom sheet | Score calculation, colors |
| `BiasTooltip` | Hover popup | Bottom sheet | Content |
| `DeepDive` | Right panel / split-screen | Full-screen modal | Summary, source list |
| `SourceList` | Expandable inline list | Scrollable list | Source data, links |
| `FilterBar` | Horizontal chips in header | Bottom sheet with chips | Filter state |
| `NavBar` | Top horizontal nav | Bottom tab bar | Navigation state |
| `RefreshButton` | Header, with confirmation dialog | Pull-area or bottom bar | Supabase refresh |
| `ThemeToggle` | Header icon | Settings or header | Mode switching |
| `UnifiedSummary` | Inline in deep dive | Full-width card | Summary generation |
| `CoverageChart` | Inline, medium size | Full-width, scrollable | Chart data |

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
