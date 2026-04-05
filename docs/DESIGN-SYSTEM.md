# void --news — Design System: "Cinematic Press" (Press & Precision v2)

**Version:** 2.1
**Last updated:** 2026-04-04 (rev 16)

---

## 1. Design Philosophy

**"Cinematic Press"** — Same editorial authority as Press & Precision, now with cinematic depth, light, focus, and atmosphere. A modern newspaper shot through a cinema lens.

**On arrival:** The quiet authority of a broadsheet — warm amber light, subtle film grain, shallow depth of field.
**On interaction:** The precision of a data terminal with rack focus, atmospheric haze, and cinematic shadows.

The newspaper earns trust through restraint. The data layer earns trust through transparency. The cinematic layer earns emotion through light and texture.

---

## 2. Typography — Four Voices

| Voice | Font | Weight | Use |
|-------|------|--------|-----|
| **Editorial** | Playfair Display | 400, 700 | Headlines, story titles, section headers, pull quotes, nav edition tabs (Row 2), weekly link (Row 1) |
| **Structural** | Inter | 400, 500, 600 | Body text, nav page links (Row 1), labels, buttons, UI chrome |
| **Meta** | Barlow Condensed | 400, 500, 600 | Category tags, source counts, timestamps, edition metadata; condensed grotesque in Franklin Gothic / News Gothic newspaper tradition; `--font-meta` CSS variable |
| **Data** | IBM Plex Mono | 400, 500 | Bias scores, numeric data, BiasLens data labels, nav filter lens (Row 2 bracket notation); humanist monospace with institutional warmth (not a coding font) |

### Type Scale (Fluid)

```css
--text-xs:    clamp(0.5625rem, 0.5rem + 0.25vw, 0.625rem);      /* 9-10px: metadata */
--text-sm:    clamp(0.75rem, 0.7rem + 0.2vw, 0.875rem);          /* 12-14px: captions */
--text-base:  clamp(0.875rem, 0.8rem + 0.3vw, 1rem);             /* 14-16px: body */
--text-lg:    clamp(1.0625rem, 0.95rem + 0.4vw, 1.3rem);         /* 17-21px: subheads */
--text-xl:    clamp(1.25rem, 1.1rem + 0.6vw, 1.75rem);           /* 20-28px: headlines */
--text-hero:  clamp(1.5rem, 1.3rem + 1.2vw, 3rem);               /* 24-48px: lead story */
```

### Tracking (letter-spacing)

| Class | Tracking | Purpose |
|-------|----------|---------|
| `.text-hero` | -0.03em | Tighten display headlines |
| `.text-xl` | -0.015em | Tighten section headlines |
| `.text-lg` | -0.005em | Subtle tightening for subheads |
| `.text-label` | 0.08em | Open spacing for uppercase labels |
| `.category-tag` | 0.04em | Open spacing for meta wayfinding |
| `.text-data` | — | line-height 1.3, tabular-nums |

### Editorial Rules

- Headlines: Playfair Display 700, sentence case
- Body: Inter 400, 1.6 line height, max 65ch measure
- Meta labels: Barlow Condensed 500 (`.category-tag`: 400), all-caps for category tags, condensed letter-spacing
- Data labels: IBM Plex Mono 400, all-caps for axis labels, tabular-nums, line-height 1.3
- Never mix voices within a single element
- Headline hierarchy: hero > xl > lg (max 3 levels visible at once)

---

## 3. Color System

### Light Mode — "Morning Edition"

Warm paper tones. Think aged broadsheet under morning light, not sterile white.

```css
:root[data-mode="light"] {
  /* Surfaces */
  --bg-primary:    #F0EBDD;   /* Warm paper */
  --bg-secondary:  #E8E2D4;   /* Aged newsprint */
  --bg-card:       #F5F0E4;   /* Clean card surface */
  --bg-elevated:   #F5F0E4;   /* Elevated surfaces */

  /* Text */
  --fg-primary:    #1A1A1A;   /* Near-black ink */
  --fg-secondary:  #4A4540;   /* Secondary text */
  --fg-tertiary:   #686260;   /* Captions, metadata */
  --fg-muted:      #5A5550;   /* Disabled, placeholder (WCAG AA 5.0:1) */

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
  --fg-tertiary:   #A09890;   /* Tertiary (WCAG AA on #1C1A17) */
  --fg-muted:      #8A847B;   /* Disabled */

  /* Borders & Dividers */
  --border-subtle: #3A3530;   /* Subtle warm rule */
  --border-strong: #4A4540;   /* Column dividers */
  --divider:       #403B35;   /* Section dividers */
}
```

### Bias Color System

Colors are consistent across light/dark modes for instant recognition. Designed for accessibility (min 4.5:1 contrast on both backgrounds).

#### Political Lean Spectrum (7-point)

```css
--bias-far-left:     #1D4ED8;  /* Deep blue — far left */
--bias-left:         #3B82F6;  /* Blue — left lean */
--bias-center-left:  #93C5FD;  /* Light blue — center-left */
--bias-center:       #9CA3AF;  /* Neutral gray — center */
--bias-center-right: #FCA5A5;  /* Light red / salmon — center-right */
--bias-right:        #EF4444;  /* Red — right lean */
--bias-far-right:    #B91C1C;  /* Deep red — far right */
```

Dark mode overrides (in `tokens.css` under `[data-mode="dark"]`): blues boosted for saturation on dark walnut; `--bias-right` brightened to `#F87171`.

Source `political_lean_baseline` values: `far-left`, `left`, `center-left`, `center`, `center-right`, `right`, `far-right`, `varies`. Enforced by DB check constraint (migration 007).

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

### Cinematic Palette & Post-Processing (v2)

Cinematic tokens live in `tokens.css` under `:root` (light) and `[data-mode="dark"]` blocks.

| Token Group | Tokens | Purpose |
|-------------|--------|---------|
| Amber palette | `--cin-amber`, `--cin-amber-bright`, `--cin-amber-dim`, `--cin-amber-ghost`, `--cin-amber-glow` | Warm cinematic accent — highlights, rim light, hover states |
| Ash palette | `--cin-ash`, `--cin-ash-warm`, `--cin-ash-cool` | Neutral cinematic tones — shadows, secondary UI |
| Paper tones | `--cin-paper-highlight`, `--cin-paper-shadow` | Subtle paper texture shifts |
| Semantics | `--cinematic-accent`, `--cinematic-shadow-tint`, `--cinematic-rim-light` | Mapped aliases for component use |
| Easings | `--ease-cinematic` (0.22,1,0.36,1), `--ease-whip` (0.25,0,0,1), `--ease-rack` (0.4,0,0.2,1) | Camera-language timing curves |
| Rack focus | `--rack-focus-dur` (600ms), `--rack-focus-ease` | Selective focus transitions |
| Shadows | `--shadow-cinematic-contact`, `--shadow-cinematic-ambient`, `--shadow-cinematic-dramatic` | Three-tier depth via `color-mix` |
| Backdrop | `--cin-backdrop-bg`, `--cin-backdrop-blur` | DeepDive overlay backdrop (blur + desaturate + dim) |
| Practical warmth | `--cin-practical-warmth` | `color-mix(in srgb, amber 4%, bg-primary)` — OnAir warmth spread via `:has()` |
| Cold open timing | `--cold-open-nav` (80ms), `--cold-open-skybox` (200ms), `--cold-open-lead` (320ms), `--cold-open-feed` (480ms), `--cold-open-dur` (500ms) | Staggered page entrance sequence |
| Whip pan | `--whip-pan-dur` (350ms) | Direction-aware edition switch transition |
| Film grain | `--cin-grain-opacity` (0.035 light / 0.025 dark) | SVG noise overlay (numOctaves=4, baseFrequency=0.75, fractalNoise). Light: overlay blend. Dark: soft-light blend. Warm feColorMatrix (R-biased). |
| Vignette | `--cin-vignette-color` | Edge darkening — subtle light, stronger dark. Z-index: `calc(--z-cinematic + 1)` — above film grain |
| Color grade | `--cin-grade` | CSS filter chain: contrast + saturation + sepia. Applied to `.page-main` + `.nav-header` (not `.page-container` — filter creates containing block that breaks position:fixed children). Per-edition overrides (US: warmer sepia, South Asia: boosted saturation, Europe: cooler grade). |
| Atmospheric haze | `--cin-haze-far` | Depth-of-field fade on distant elements |
| Z-index | `--z-cinematic` (45) | Film grain layer; vignette at `+1` (above grain) |

All cinematic tokens adapt between light/dark modes. Dark mode: boosted amber brightness, stronger vignette, lower grain, cooler grade.

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
| 1 (B) | **The Beam** | Horizontal tilting beam with center post | Political lean: tilts ±15° from center (formula: `(lean - 50) * 0.30`). Color from lean spectrum (blue left, gray center, red right). Matches the Sigil DataMark beam. |
| 2 (R) | **The Signal Ring** | SVG ring (Harvey ball) with source count | Coverage/confidence composite: ring fill 0-100%. Source count displayed in center. Color: green (strong) / yellow (moderate) / red (weak). |
| 3 (P) | **The Prism** | Morphing shape (square to circle) | Opinion vs. reporting: square = factual reporting, circle = opinion. Color: blue (reporting) / purple (analysis) / orange (opinion). |

### Sizes

- **sm** (story cards): Beam 18px, Ring 18px, Prism 14px. Gap 6px.
- **lg** (lead story, deep dive header): Beam 28px, Ring 28px, Prism 22px. Gap 10px.

### Interaction

- **Desktop hover**: Each lens has its own independent popup with title, score, spectrum bar, and rationale sub-scores (when available from pipeline analysis).
- **Mobile tap**: Same popup positioned near the lens element.
- **Deep Dive source list**: Per-source BiasLens (sm) inline next to each source name.
- **Pending state**: When bias scores are fallback placeholders (not yet analyzed), the entire lens group renders at 35% opacity with grayscale filter and a "Pending" label.

### Accessibility

- Each lens has `role="img"` with descriptive `aria-label` (e.g., "Political lean: Center-Left, score 42").
- Popups use `role="tooltip"` with `aria-describedby` linking.
- Keyboard accessible: Tab to focus, Enter/Space to toggle popup, Escape to close.
- Color is never the sole differentiator -- shape (beam tilt angle, ring fill, square-to-circle morph) encodes the data independently.
- Min 4.5:1 contrast on both light and dark backgrounds.

---

## 5. Layout System

### Desktop — "Broadsheet Grid"

```
┌──────────────────────────────────────────────────────┐
│  void --news  [dateline] Sources Ship About [Weekly] ☀ │ ← Row 1 (Chrome)
│  World  US  Europe  South-Asia  [topics] [·L·C·R] [🔍] │ ← Row 2 (Lens)
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
┌──────────────────────────────────────────────────────┐  ← 75vw centered, max-width 920px (1080px at 1280px+), 80vh
│  ← Back          Story headline [BiasLens]            │
├──────────────────────────────────────────────────────┤
│                                                      │
│  [Summary as lede text — no "What happened" heading] │
│  [viewport-responsive height; "Read more" at 600+ chars]│
│                                                      │
│  ┌── dd-analysis-row (single flex row) ────────────┐ │
│  │  [Sigil]  [── gradient track w/ favicons ──]    │ │
│  │                             [Press Analysis ▶]  │ │
│  └─────────────────────────────────────────────────┘ │
│  ┌── (Press Analysis expanded) ───────────────────┐  │
│  │  [4-axis scorecard — BiasInspectorInline]      │  │
│  │  [tap axis to expand sub-scores + AI reasoning]│  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  SOURCE PERSPECTIVES (2-column grid)                 │
│  ┌── Agreement ──────┐  ┌── Divergence ────────┐    │
│  │ ✓ [agree point]   │  │ ⚠ [diverge point]    │    │
│  │   (green border)  │  │   (red border)       │    │
│  └───────────────────┘  └──────────────────────┘    │
│                                                      │
│  COVERAGE BREAKDOWN                                  │
│  ┌─────────────────────────────────────────┐        │
│  │  Source A (NYT)        ● ● ○ ● ●  [→]  │        │
│  │  Source B (Fox)        ● ○ ● ○ ●  [→]  │        │
│  │  Source C (BBC)        ○ ● ● ● ○  [→]  │        │
│  └─────────────────────────────────────────┘        │
│                                                      │
└──────────────────────────────────────────────────────┘
```

Desktop: 75vw centered modal (max-width 920px, 1080px at 1280px+, 80vh); main feed blurred (6px backdrop blur) when open. FLIP morph animation: card expands into panel via double-rAF (open 500ms bouncy, close 420ms smooth), `data-story-id` attributes on StoryCard/LeadStory/MobileStoryCard enable DOM-based rect lookup for reverse morph on close. Analysis row (`dd-analysis-row`) places Sigil + Spectrum + Press Analysis ▶ trigger in a single flex row. Press Analysis expands inline via `grid-template-rows 0fr→1fr`. Source Perspectives shows Agreement | Divergence in a 2-column grid. Progressive disclosure: press analysis collapsed behind ▶ trigger by default.

### Deep Dive — Mobile

- Full-screen modal sliding up from bottom; iOS bottom-sheet style: `border-radius: 16px 16px 0 0`, drag indicator pill, `-webkit-overflow-scrolling: touch` momentum scrolling
- `padding-bottom: env(safe-area-inset-bottom)` for home indicator; `padding-top: env(safe-area-inset-top)` for notch
- Backdrop blur reduced to 2px (6px is too expensive on low-end devices)
- Slot-machine cascade: `opacity 150ms ease-out, transform 250ms ease-out` (no spring — avoids GPU jitter); `translateY(8px) → 0` (shallower than 12px desktop)
- Content reveal delay: 30ms (prevents blank header flash)
- Analysis row stacks vertically on mobile (dd-analysis-row: `flex-direction: column`)
- Source Perspectives collapses to single column on mobile (dd-perspectives-grid: `grid-template-columns: 1fr`)
- Press Analysis expand: 300ms ease-out on mobile
- Each source row is tappable → opens article in browser
- Source rows use `flex-wrap: wrap` so metadata wraps instead of overflowing on narrow viewports

### Mobile Layout Rules (max-width: 767px)

| Element | Rule | Rationale |
|---------|------|-----------|
| `.page-main`, `.nav-inner`, `.site-footer` | padding: `--space-5` (~16px) | Recovers 32px content width vs desktop `--space-7` |
| `.lead-story__headline`, `.lead-story__summary` | `max-width` constraints removed | Container constrains width; `ch` limits are redundant and wasteful on mobile |
| `.story-card__headline`, `.lead-story__headline` | `overflow-wrap: break-word` (global) | Prevents long words from causing horizontal overflow |
| `.section-header` | `flex-wrap: wrap` | Timestamp wraps instead of overflowing |
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
- BiasLens (lg) — larger Beam (28px), Ring (28px), Prism (22px)

---

## 7. Animation System

Adapted from DondeAI's "Ink & Momentum" motion system.

### Principles

1. **Purposeful** — every animation communicates state change, never decorative
2. **Asymmetric for panels** — Deep Dive open uses FLIP morph with `--spring-bouncy` (500ms, genuine overshoot from card origin); close uses reverse morph (420ms smooth deceleration back to card). Micro-interactions (chips, toggles) remain symmetric.
3. **Accessible** — all → 0ms under `prefers-reduced-motion: reduce`
4. **Performant** — only animate transform and opacity (GPU composite)
5. **Interruptible** — no animation locks
6. **High-refresh ready** — double-rAF snap (first rAF commits snap to DOM, browser paints, second rAF starts transition) for 90/120Hz reliability

### Spring Presets

| Preset | Stiffness | Damping | Mass | Use |
|--------|-----------|---------|------|-----|
| snappy | 600 | 35 | 1 | Buttons, filter chips, toggles |
| smooth | 280 | 22 | 1 | Card expansion, panel slides |
| gentle | 150 | 12 | 1.2 | View transitions (feed ↔ deep dive) |
| bouncy | — | — | — | Deep Dive FLIP morph open (500ms, genuine overshoot from card origin); `--spring-bouncy` CSS token. Close uses 420ms smooth reverse morph. |

### Cinematic Easings

| Token | Curve | Use |
|-------|-------|-----|
| `--ease-cinematic` | cubic-bezier(0.22, 1, 0.36, 1) | Primary cinematic ease — smooth deceleration with authority |
| `--ease-whip` | cubic-bezier(0.25, 0, 0, 1) | Fast whip-pan transitions — aggressive deceleration |
| `--ease-rack` | cubic-bezier(0.4, 0, 0.2, 1) | Rack focus transitions — measured pull between focal planes |

### Duration Tokens

| Token | Value | Use |
|-------|-------|-----|
| --dur-instant | 0ms | Reduced motion, immediate feedback |
| --dur-fast | 150ms | Hover states, small reveals |
| --dur-normal | 300ms | Card interactions, tooltips |
| --dur-morph | 400ms | View transitions |
| --dur-step | 450ms | Step-by-step reveals, stagger sequences |
| --dur-slow | 600ms | Page-level animations |
| --rack-focus-dur | 600ms | Rack focus selective blur transitions |

### Key Animations

| Element | Trigger | Animation | Duration |
|---------|---------|-----------|----------|
| Story card | Page load | fadeInUp (opacity + translateY 12px→0) | 300ms, 40ms stagger |
| Dot matrix | Card appear | Dots fade in left-to-right | 150ms, 30ms stagger |
| Bias tooltip | Hover/tap | Scale from 0.95→1, opacity 0→1 | 150ms ease-out |
| Deep Dive panel | Click story | Slide in from right (desktop) / bottom (mobile); JS-driven translateX/translateY | Open: `--spring-bouncy` 500ms (genuine overshoot); Close: `--spring-snappy` 380ms; fallback: 200ms opacity ramp |
| Deep Dive content sections | Panel open | Cascade: translateY 12px→0; desktop: content reveal 180ms; mobile: opacity 150ms + transform 250ms ease-out (no spring) | Desktop reveal delay 120ms, mobile 30ms |
| Press Analysis expand | Click ▶ trigger | grid-template-rows 0fr→1fr | var(--dur-morph) ease-out desktop; 300ms ease-out mobile |
| Filter chips | Select | Scale 1→0.97→1, fill color wipe | 200ms spring |
| Dark mode toggle | Tap | Cross-fade colors + cinGoldenHourPulse on `.page-main` (warmth swell: contrast/saturation/sepia peak at 40% then return), 0 layout shift | 400ms ease-out + 700ms pulse |
| Source list expand | Tap "12 sources" | Height auto with spring, items stagger | 300ms, 30ms stagger |
| Cold open (nav) | Page load | coldOpenSettle (translateY -6px→0, opacity 0→1) | 500ms, delay 80ms |
| Cold open (skybox) | Page load | coldOpenDollyIn (scale 0.985→1, opacity 0→1) | 500ms, delay 200ms |
| Edition switch | Click edition tab | Direction-aware whip pan: whipPanOutRight + whipPanInLeft (translateX 8%, blur 2px) | 350ms `--ease-whip` |
| ScaleIcon idle | Continuous | Gentle beam tipping (rotate 0→2deg→-2deg→0) | 5s, `--ease-cinematic`, infinite |

### Reduced Motion

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

---

## 7b. Film System — Shared Cinematic Scenes

**Directory:** `frontend/app/film/`

Unified component library powering both the onboarding prologue (`OnboardingCarousel`) and the about manifesto (`/about`). Single source of truth for all demo/educational content. Change once, both surfaces update.

### Architecture

| File | Purpose |
|------|---------|
| `data.ts` | Canonical content constants: `CHAPTERS` (6 chapters), `DIVERGENT_HEADLINES`, `SIX_AXES`, `FIRST_PRINCIPLES`, `PRODUCT_FAMILY`, `RANKING_SIGNALS`, `NUMBERS`, `LANDSCAPE`, `COMPARISON_SCORES`, `SIGIL_PARTS`, `SWEEP_POSITIONS` |
| `constants.ts` | SVG paths (organic hand-drawn brand mark coordinates matching ScaleIcon/Sigil), stroke-dasharray lengths, spring easings (`SPRING`, `SPRING_BOUNCY`, `SPRING_GENTLE`), draw stagger timing (`DRAW_TIMING`), breakdown stage durations (`BREAKDOWN_TIMING`), exploded view transforms (`EXPLODE_TRANSFORMS`) |
| `useReducedMotion.ts` | Shared hook — checks `prefers-reduced-motion` once on mount |
| `scenes/*.tsx` | 6 scene components (see below) |

### Scene Components

Each scene accepts `mode: "prologue" | "manifesto"` and `active: boolean`.

| Scene | Chapter | Description |
|-------|---------|-------------|
| `DivergentHeadlines` | I: The Void | 5 outlets, same event, different headlines. Cards stagger in with spring physics. |
| `SigilBreakdown` | II: The Instrument | **Centerpiece.** 6-stage animated exploded Sigil view: (0) draw — stroke-dashoffset reveals parts, (1) separate — components translate apart, (2) label — labels fade in beside each part, (3) reassemble — spring back to center, (4) activate — beam sweeps spectrum + ring fills, (5) hold — settled state. Prologue: auto-advance via setTimeout. Manifesto: IO-triggered + six-axis accordion. |
| `SourceEngine` | III: The Engine | 1,013 sources, 158 countries, 11 ranking signals visualization. |
| `ArticleDifference` | IV: The Difference | Per-article vs. per-outlet scoring comparison morph. |
| `ProductWorlds` | V: The Worlds | Product family showcase (6 products with CLI names + descriptions). |
| `TheVerdict` | VI: Read with clarity | Key numbers counter + closing statement. |

### Modes

| Mode | Surface | Behavior |
|------|---------|----------|
| `prologue` | `OnboardingCarousel.tsx` | Auto-advance (~90s total), modal overlay, keyboard nav, progress dots, skip/complete callbacks |
| `manifesto` | `/about` page | Scroll-driven, IntersectionObserver one-shot reveals, extended content (manifestoLead, SIX_AXES details, FIRST_PRINCIPLES, LANDSCAPE comparisons), no forced dark mode |

### Styles

`film.css` in `frontend/app/styles/`. `.film-*` namespace. Mode-specific overrides via `.film-*--prologue` and `.film-*--manifesto` suffixes. Keyframes: `filmDraw` (stroke reveal), `filmFadeInUp`, `filmSpectrumGrow`.

### 6 Chapters

| # | ID | Headline | Prologue Duration |
|---|-----|----------|-------------------|
| I | `the-void` | The Void | 15s |
| II | `the-instrument` | The Instrument | 20s |
| III | `the-engine` | The Engine | 15s |
| IV | `the-difference` | The Difference | 15s |
| V | `the-worlds` | The Worlds | 15s |
| VI | `the-verdict` | Read with clarity. | 10s |

---

## 8. Component Inventory

Active components in `frontend/app/components/`:

| Component | Purpose | Bias Visualization |
|-----------|---------|-------------------|
| `BiasInspector` | "Press Analysis" 4-axis scorecard (Lean, Sensationalism, Factual Rigor, Framing). Three exports: `BiasInspectorInline` (rendered inline in Deep Dive, expanded via ▶ trigger — no dialog wrapper), `BiasInspectorTrigger` + `BiasInspectorPanel` (legacy pop-out, kept for backward compat). Each axis row is collapsible — expand for sub-scores + Gemini reasoning text. | Cluster-averaged across all sources |
| `BiasLens` | Three Lenses bias visualization (Beam, Ring, Prism) | Primary -- used on all story cards and deep dive source list |
| `StoryCard` | Standard story card with headline, summary, metadata, BiasLens | Inline BiasLens (sm) |
| `LeadStory` | Hero story card, larger typography | Inline BiasLens (lg) |
| `DeepDive` | Slide-in panel: FLIP morph open/close. "Read more" overflow detected via ResizeObserver; gradient overlay hidden when content fits (`dd-collapsible--fits`). `dd-analysis-row`: Sigil + `DeepDiveSpectrum` + "How was this scored?" trigger in one row on desktop, stacked on mobile. Press Analysis expands via `grid-template-rows 0fr→1fr`; expand panel max-height 60vh with overflow-y scroll. `ScoringMethodology` collapsible section ("How we score" — dl/dt/dd, 6 axes). Loading skeleton guard (sources.length === 0). Source Perspectives: 2-column Agreement\|Divergence grid (desktop), single column (mobile). Action buttons WCAG 44×44px. Open: `--spring-bouncy` 500ms (overshoot); Close: `--spring-snappy` 380ms (L-cut close 80ms). Content reveal 180ms desktop, 30ms mobile. Cinematic dramatic shadow, data-settled studio reflection. Backdrop blur 6px desktop, 2px mobile. iOS bottom-sheet. Panel `opacity:0` CSS safety + JS fallback 200ms opacity ramp. | Per-source BiasLens (sm) |
| `DeepDiveSpectrum` | Continuous lean spectrum for Deep Dive panel. 7-zone gradient bar (Far Left → Far Right) with full zone labels (smaller font on mobile). Logos positioned at exact `politicalLean` % (0–100) on a relative track — not bucketed into columns. No max-height cap. 3-row algorithm for dense source clustering. "+N more" expand button when >6 sources (COMPACT_LIMIT). Each logo is a link to the source article (opens in new tab). Tooltip on hover/focus: source name, lean label + colored dot, lean score, tier, "Click to read article". Spring-bouncy hover scale. Responsive: 26px logos desktop, 22px mobile. CSS: `dd-spectrum-*` classes in `spectrum.css`. | -- |
| `HomeContent` | News feed container: edition switching (direction-aware whip pan via prevEditionRef tracking, URL sync via pushState), lean filter (LeanChip/LEAN_RANGES from types.ts), opinion mode, story grid | -- |
| `OpEdPage` | Opinion/editorial feed view | -- |
| `OpinionCard` | Op-ed story card | -- |
| `NavBar` | "Depth of Field" CTA hierarchy (v2), two-row structure. Cold open animation class (`anim-cold-open-nav`). **Row 1 (Chrome)**: Logo, dateline + timestamp (`getEditionTimestamp()`), page links (`.nav-pages`, `.nav-page`) — Inter uppercase, departure arrow `→` on hover (Sources, Ship, About), **Weekly** (`.nav-weekly`) — Playfair italic, deep red accent (`#B91C1C`/`#EF5350`), spine rule glow + unfold physics on hover, ThemeToggle. **Row 2 (Lens)**: Edition tabs (`.nav-lens__editions`, `.nav-ed`) — Playfair Display, warm `--cin-amber` underline, `hapticConfirm`, hidden on mobile. Filter Lens (`.nav-lens__*`) — IBM Plex Mono bracket notation `[ topics ]` `[ ·left ·center ·right ]`, dotted underline, `--ease-rack`, `hapticMicro`, hidden on mobile. Search bar (`.nav-lens__search`) — expandable 160px to 280px on focus, `Cmd+K` kbd hint. Row 2 has inset shadow texture. Nav onair button removed (floating player is single audio entry point). Mobile: bottom nav handles editions/filters. | -- |
| `ThemeToggle` | Light/dark mode toggle. Golden hour pulse on toggle (700ms cinGoldenHourPulse targeting `.page-main`, reduced-motion guarded). | -- |
| `LoadingSkeleton` | Animated skeleton loading state | -- |
| `ErrorBoundary` | Error boundary wrapper | -- |
| `Footer` | Page footer with last-updated info | -- |
| `LogoFull` | Combination mark: void circle + scale beam icon + "void --news" wordmark as single SVG. Use in NavBar (desktop), Footer, error pages. Direction 5 "Negative Space O" — hollow O in "void", monospace "--news". | -- |
| `LogoIcon` | Icon-only wrapper around `ScaleIcon`. Use in mobile nav, loading indicators, compact contexts. `animation="none"` shows void circle only (favicon mark). | -- |
| `LogoWordmark` | Text-only "void --news" SVG — no icon mark. Hollow-O treatment. Use for edition lines, attribution, compact footers, print contexts. | -- |
| `ScaleIcon` | "Void Circle + Scale Beam" hybrid brand icon. Hollow ring as primary mark with scale beam passing through as fulcrum, weight ticks at beam ends, post + base below. 8 animation states: `idle` (gentle tipping — 5s period, 2-degree amplitude, `--ease-cinematic`), `loading` (dramatic tipping — 8-degree), `hover` (snappy tip), `analyzing` (deliberate read), `balanced` (spring settle), `pulse` (scale pulse), `draw` (stroke reveal on mount), `none` (void circle only — favicon mark). All animations respect `prefers-reduced-motion`. | -- |
| `PageToggle` | Row 1 text link toggling Feed/Sources. No pills, no icons — plain `.nav-page` link with departure arrow on hover. | -- |
| `SpectrumChart` | `/sources` political lean spectrum. Gradient bar on top; all sources below in 7 lean zone columns (mixed tiers, no tier split). Logos overlap at −3px margin, fan out to 2px on zone hover. Zone counts shown below each column. Collapsed to ~4 rows by default; single "Show all N" expand button reveals all. Each zone scrollable at 60vh cap when expanded. Tooltip shows name, lean, tier, country, credibility notes. | -- |
| `Sigil` | Compact bias sigil using `SigilData` type. Inline bias indicator variant. Simplified at sm size (no InkUnderline, compact popup); full detail at lg/xl. | -- |
| `DailyBrief` | "void --onair" daily brief: TL;DR + opinion + audio player | -- |
| `SkyboxBanner` | Top-of-page daily brief skybox with TL;DR, opinion, and OnAir sections. Cold open animation class (`anim-cold-open-skybox`). OnAir practical light warmth spread via `:has()` selector. | -- |
| `MobileBriefPill` | Mobile daily brief pill trigger | -- |
| `DesktopFeed` | Desktop multi-column newspaper grid layout | -- |
| `MobileFeed` | Mobile single-column feed layout | -- |
| `MobileStoryCard` | Mobile-optimized story card | -- |
| `MobileBottomNav` | Bottom navigation bar for mobile | -- |
| `DigestRow` | Compact digest-style story row | -- |
| `WireCard` | Wire-service-style compact card | -- |
| `StoryMeta` | Shared story metadata display (sources, time, category) | -- |
| `CommandCenter` | KPI monitoring dashboard with sparklines and health score | -- |
| `ComparativeView` | Side-by-side source comparison view | -- |
| `DivergenceAlerts` | Highlights divergent coverage across sources | -- |
| `EditionIcon` | Edition-specific icon (US flag, South Asia Ashoka Chakra, Europe stars, etc.) | -- |
| `OnboardingCarousel` | Thin wrapper for "The Film: Prologue" — imports `film/scenes` with `mode="prologue"`. 6 chapters, ~90s auto-advance. Handles modal overlay, keyboard nav, body scroll lock, focus trap, progress dots. | -- |
| `UnifiedOnboarding` | Unified onboarding wrapper | -- |
| `KeyboardShortcuts` | Keyboard shortcut handler and help overlay | -- |
| `InstallPrompt` | PWA install prompt | -- |
| `ShipBoard` | Feature request board for `/ship` page | -- |
| `WeeklyDigest` | `/weekly` magazine page. No NavBar — own sticky topbar (`.wk-topbar`: back link + ThemeToggle, glass blur). Deep red palette (`--wk-accent: #B91C1C` light / `#EF5350` dark). Warmer paper (`#EDE4D0` light / `#1E1A16` dark). Film grain 3x, tighter vignette. Sections: red masthead, cover hero (drop cap, justified), timeline (horizontal desktop / vertical mobile), opinions (3-col lean grid, no card backgrounds), week in brief (2-col compact), inline audio, archive, footer. No MobileBottomNav. No collapsibles. | -- |

**49 components total** (49 `.tsx` files). Added since last audit: `AudioProvider`, `MobileMiniPlayer`, `MobileNav`, `MobileSidePanel`, `MobileTabBar`. Removed: `OnboardingSpotlight` (dead code, replaced by Film system), `AudioPlayer.tsx`, `BiasStamp.tsx`, `DotMatrix`, `BiasTooltip`, `UnifiedSummary`, `FilterBar.tsx` (lean chips moved to `types.ts`, dead CSS removed).

### Logo Animation Deployment

| Context | Component | Animation State |
|---------|-----------|----------------|
| NavBar (mobile, on mount) | `LogoIcon` | `draw` → transitions to `idle` after 800ms |
| NavBar (desktop) | `LogoFull` | static SVG (idle beam embedded) |
| LoadingSkeleton | `LogoIcon` | `loading` |
| ErrorBoundary | `LogoIcon` | `balanced` |
| DeepDive panel header | `LogoIcon` | `analyzing` |
| Empty state | `LogoIcon` | `analyzing` |
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
- **Bias**: BiasLens Three Lenses (Beam, Ring, Prism) — no traditional icons needed
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
- **Color independence**: BiasLens uses shape + angle + fill + morph (never color alone) — Beam tilt angle, Ring fill percentage, and Prism square-to-circle morph all encode data independently of color.

### BiasLens Screen Reader Pattern

```html
<!-- Each lens has role="img" with descriptive aria-label -->
<div class="bias-lens" role="group" aria-label="Bias analysis for this article">
  <div class="bias-lens__beam" role="img" aria-label="Political lean: Center-Left, score 42"></div>
  <div class="bias-lens__ring" role="img" aria-label="Coverage confidence: 67%, 8 sources"></div>
  <div class="bias-lens__prism" role="img" aria-label="Article type: Reporting (factual)"></div>
</div>
<!-- Popups use role="tooltip" with aria-describedby linking -->
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
| Cinematic | `--cin-`, `--cinematic-`, `--ease-cinematic/whip/rack` | `--cin-amber`, `--cin-grade`, `--cin-grain-opacity` |
| Cinematic shadows | `--shadow-cinematic-` | `--shadow-cinematic-contact`, `--shadow-cinematic-dramatic` |
| Borders | `--border-` | `--border-subtle`, `--divider` |
| Elevation | `--blur-`, `--shadow-` | `--blur-e2`, `--shadow-e1` |
| Z-index | `--z-` | `--z-base(1)`, `--z-cinematic(45)`, `--z-modal(100)` |
