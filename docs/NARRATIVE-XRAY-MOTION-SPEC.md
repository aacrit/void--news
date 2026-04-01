# Narrative X-Ray -- Motion Specification

**Cinematographer:** void --news Director of Photography
**Date:** 2026-04-01
**Status:** Design specification -- pending frontend-builder implementation

---

## Scene Overview

The Narrative X-Ray is a per-sentence framing analysis layer within Deep Dive source perspectives. It reveals three signal types (charged synonyms, entity sentiment, omissions) as inline text annotations. The motion language must feel like a documentary DP pulling focus to reveal what was always there in the text -- not adding decoration, but shifting the viewer's attention to see what they were already reading differently.

**Cinematic reference:** The long-take documentary work of Frederick Wiseman -- the camera is already pointed at reality; we just adjust the lens to sharpen on what matters. Also: the "enhanced vision" sequences in Michael Mann's *Heat* and *Collateral* where the existing scene gains an analytical overlay without breaking spatial continuity.

---

## 1. The Reveal -- Toggle Activation

### Motivation

When the user activates "14 framing signals," the text they were reading transforms from plain prose into annotated evidence. This is a **rack focus**: the surrounding text slightly recedes in visual priority while the framing signals resolve into sharp focus. Not a flashy reveal -- a perceptual shift.

### Cinematic Technique: Rack Focus + Staggered Resolve

The existing text body does NOT blur or dim. Instead, the highlights fade in with a top-to-bottom stagger that reads like a developing photograph -- signals "resolve" into visibility as if emerging from the paper. The stagger is fast enough to feel like a single wash, slow enough that the eye registers directionality.

### CSS Keyframes

```css
/* ── Narrative X-Ray: Highlight Resolve ──
   Highlights emerge from transparent into their signal color.
   Transform: subtle 1px upward drift (text settling into place).
   The highlight background-color fades in; the text never moves.
   Cinematic ref: rack focus resolve -- sharp detail emerging from soft. */

@keyframes nxHighlightResolve {
  from {
    background-color: transparent;
    box-decoration-break: clone;
    outline-color: transparent;
  }
  to {
    background-color: var(--nx-highlight-color);
    box-decoration-break: clone;
    outline-color: var(--nx-outline-color, transparent);
  }
}

/* ── Entity Sentiment Underline Resolve ──
   Underlines draw in left-to-right via background-size.
   Mimics the ink-draw technique already used by sigil underlines. */

@keyframes nxUnderlineDraw {
  from {
    background-size: 0% 2px;
  }
  to {
    background-size: 100% 2px;
  }
}
```

### Timing

| Property | Value | Rationale |
|----------|-------|-----------|
| **Stagger gap** | `30ms` per highlight | Fast wash, not individual pops. 14 signals complete in ~420ms total. Reads as a developing wave, not a list. |
| **Individual duration** | `var(--dur-normal)` (300ms) | Each highlight needs enough time to register but not linger. Matches existing card entrance timing. |
| **Easing** | `var(--ease-cinematic)` (0.22, 1, 0.36, 1) | Deakins-style smooth deceleration. Highlights "arrive" quickly then settle. No overshoot -- this is analytical, not playful. |
| **Stagger direction** | DOM order (top-to-bottom within the source text) | Natural reading direction. The eye follows the cascade downward like scanning a column. |
| **Total envelope** | ~720ms for 14 signals | Under one second. Feels immediate but structured. |

### Implementation Pattern

```css
/* Applied to each highlight <mark> or <span> wrapper */
.nx-highlight {
  --nx-highlight-color: var(--cin-amber-ghost);  /* Default: charged synonym amber */
  background-color: transparent;
  border-radius: 1px;
  transition: background-color var(--dur-normal) var(--ease-cinematic);
}

/* Active state: X-Ray toggled ON */
.nx-active .nx-highlight {
  animation: nxHighlightResolve var(--dur-normal) var(--ease-cinematic) both;
  animation-delay: calc(var(--nx-index, 0) * 30ms);
}

/* Entity sentiment: warm/cool underline via background-image */
.nx-entity {
  background-image: linear-gradient(
    var(--nx-entity-color),
    var(--nx-entity-color)
  );
  background-position: 0 100%;
  background-size: 0% 2px;
  background-repeat: no-repeat;
  transition: background-size var(--dur-normal) var(--ease-cinematic);
}

.nx-active .nx-entity {
  animation: nxUnderlineDraw var(--dur-morph) var(--ease-cinematic) both;
  animation-delay: calc(var(--nx-index, 0) * 30ms);
}
```

### Implementation Notes for Frontend-Builder

- Each highlight element gets a CSS custom property `--nx-index` set via inline style: `style={{ '--nx-index': i } as React.CSSProperties}`. The index is computed in DOM order (first highlight in the source text = 0, second = 1, etc.).
- The parent container (source perspective card body) receives the class `.nx-active` when the toggle is ON. Removing this class triggers the reverse: highlights fade out with a single `transition: background-color 200ms var(--ease-out)` (no stagger on exit -- a clean cut, not a slow dissolve).
- Do NOT blur or dim the surrounding text. The highlights are additive; the text remains fully readable. This is not shallow depth of field -- it is a focus pull within a deep-focus shot.
- `box-decoration-break: clone` ensures multi-line highlights wrap correctly without visual seams.

### Reduced Motion Fallback

```css
@media (prefers-reduced-motion: reduce) {
  .nx-active .nx-highlight,
  .nx-active .nx-entity {
    animation: none !important;
    background-color: var(--nx-highlight-color);
    background-size: 100% 2px;
  }
}
```

Instant appearance. No stagger. Highlights are simply present.

---

## 2. Tooltip Entrance -- Lens Detail Pull

### Motivation

When the user hovers or taps a charged synonym highlight, a tooltip appears showing the neutral alternative (e.g., "regime" -> "Neutral: government"). This should feel like a lens pulling focus to a detail -- quick, precise, informative. Not a balloon. Not a popup. A loupe.

### Cinematic Technique: Dolly In (Micro)

The tooltip enters with a subtle `scale(0.97) -> scale(1)` combined with `opacity: 0 -> 1` and a very slight `translateY(4px) -> translateY(0)`. This is the micro-dolly: the camera moves fractionally closer to examine a detail.

### CSS Keyframes

```css
/* ── Narrative X-Ray: Tooltip Entrance ──
   Micro-dolly: camera pulls in to examine a word.
   Scale from 97% (slightly receded) to 100% (sharp focus plane).
   Subtle translateY for directional arrival (from below, toward the word). */

@keyframes nxTooltipIn {
  from {
    opacity: 0;
    transform: translateY(4px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes nxTooltipOut {
  from {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
  to {
    opacity: 0;
    transform: translateY(2px) scale(0.98);
  }
}
```

### Timing

| Property | Value | Rationale |
|----------|-------|-----------|
| **Entrance duration** | `180ms` | Between `--dur-fast` (150ms) and `--dur-normal` (300ms). Fast enough to feel responsive, slow enough to register the directional arrival. |
| **Exit duration** | `120ms` | Faster than entrance. Asymmetric: arrive with weight, depart quickly. The user is already moving on. |
| **Entrance easing** | `var(--spring-snappy)` | Tight overshoot settles in ~300ms. The tooltip "lands" with physical authority -- like a loupe being placed on a page. |
| **Exit easing** | `var(--ease-out)` | Clean departure, no spring. Just leaves. |
| **Delay before show** | `120ms` | Prevents tooltip flicker on mouse-through. Intentional hover only. |
| **Delay before hide** | `80ms` | Brief grace period for cursor jitter. |

### Implementation Pattern

```css
.nx-tooltip {
  position: absolute;
  z-index: var(--z-tooltip);
  pointer-events: none;

  /* Visual: editorial data card feel */
  background: var(--bg-elevated);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-cinematic-contact);
  padding: var(--space-2) var(--space-3);
  max-width: 240px;

  /* Typography: Data voice for analytical precision */
  font-family: var(--font-data);
  font-size: var(--text-xs);
  line-height: 1.4;
  color: var(--fg-secondary);

  /* Animation */
  animation: nxTooltipIn 180ms var(--spring-snappy) both;
}

.nx-tooltip--exiting {
  animation: nxTooltipOut 120ms var(--ease-out) both;
}

/* Tooltip arrow — 5px CSS triangle, inherits parent bg */
.nx-tooltip::before {
  content: "";
  position: absolute;
  top: -5px;
  left: var(--nx-tooltip-arrow-x, 50%);
  transform: translateX(-50%);
  border: 5px solid transparent;
  border-bottom-color: var(--bg-elevated);
  border-top: 0;
}
```

### Content Structure

```
[ regime ]  ->  Tooltip: "Neutral: government"
                         ^^^^^^^^  ^^^^^^^^^^
                         Label     Alternative
                         (Meta)    (Structural)
```

The label ("Neutral:") uses `--font-meta` (Barlow Condensed), uppercase, `--text-xxs`. The alternative word uses `--font-structural` (Inter), normal weight, `--text-xs`. This two-voice split mirrors the existing bias label/value pattern throughout Deep Dive.

### Reduced Motion Fallback

```css
@media (prefers-reduced-motion: reduce) {
  .nx-tooltip {
    animation: none !important;
    opacity: 1;
    transform: none;
  }
  .nx-tooltip--exiting {
    animation: none !important;
    opacity: 0;
  }
}
```

---

## 3. Source Comparison Transition -- Density Contrast

### Motivation

When the user switches between source perspectives (e.g., reading RT's text, then switching to AP's text), the highlight density tells a story. RT might have 14 framing signals; AP might have 3. The visual "silence" of AP's clean text should feel intentional and meaningful -- not like the feature broke, but like the absence of noise IS the data.

### Cinematic Technique: Dissolve + Density Shift

This is a cross-dissolve between two shots: one busy, one quiet. The eye should register the contrast immediately. No fancy transition -- the content swap does the work. But the highlights in the new source re-stagger from the top, giving the eye a fresh "scan" opportunity to register the new density.

### Timing

| Phase | Duration | Easing | What Happens |
|-------|----------|--------|--------------|
| **Old source exit** | `200ms` | `var(--ease-out)` | Old source text fades to `opacity: 0`. Old highlights do NOT individually exit -- the entire block dissolves. This is a "cut away," not a "clear the board." |
| **Content swap** | `0ms` | Instant | React swaps the source content. No intermediate empty state. |
| **New source entrance** | `300ms` | `var(--ease-cinematic)` | New source text fades in from `opacity: 0`. Text arrives at full opacity. |
| **Highlight re-stagger** | `30ms` gap, `300ms` each | `var(--ease-cinematic)` | If X-Ray is active, highlights in the new source resolve with the same top-to-bottom stagger as the initial reveal. Fresh scan for fresh content. |

### Implementation Pattern

```css
/* Source perspective card body -- dissolve wrapper */
.nx-source-body {
  transition: opacity 200ms var(--ease-out);
}

.nx-source-body--exiting {
  opacity: 0;
  transition: opacity 200ms var(--ease-out);
}

.nx-source-body--entering {
  animation: fadeIn 300ms var(--ease-cinematic) both;
}
```

### The "Visual Silence" Effect

When a source has very few or zero framing signals, the clean text needs to feel authoritative, not empty. This is achieved through NO additional animation -- the absence of highlight stagger is itself the signal. The text simply arrives, unadorned.

If the X-Ray toggle shows "3 framing signals" for AP vs. "14 framing signals" for RT, the badge count updates with a number transition:

```css
/* Count badge number transition -- tabular-nums for stable width */
.nx-badge__count {
  font-family: var(--font-data);
  font-variant-numeric: tabular-nums;
  display: inline-block;
  transition: transform 200ms var(--spring-snappy),
              opacity 200ms var(--ease-out);
}

/* When count changes, brief scale pulse */
.nx-badge__count--updating {
  transform: scale(1.08);
  opacity: 0.7;
}
```

### Reduced Motion Fallback

Content swaps instantly. No fade. Highlights appear immediately without stagger.

---

## 4. Omission Banner Entrance

### Motivation

The "Missing entities" banner sits at the top of each source perspective, showing what that source did NOT cover (e.g., "Covers 4 of 11 entities. Missing: WHO, UNICEF, displacement figures..."). This is editorially the most important Narrative X-Ray signal -- omission IS framing. The banner should enter with quiet weight, not fanfare.

### Cinematic Technique: Tilt Down (Vertical Reveal)

The banner slides down from `height: 0` using a `clip-path` reveal, NOT a height animation (which would cause layout thrash). The text is already in the DOM at full height; a `clip-path: inset(100% 0 0 0)` crops it from view, then animates to `clip-path: inset(0)`.

### CSS Keyframes

```css
/* ── Narrative X-Ray: Omission Banner Reveal ──
   Vertical wipe: clip-path reveals from top to bottom.
   Cinematic ref: tilt-down reveal, like panning down to read
   a chyron at the bottom of a documentary frame. */

@keyframes nxOmissionReveal {
  from {
    clip-path: inset(100% 0 0 0);
    opacity: 0.5;
  }
  to {
    clip-path: inset(0);
    opacity: 1;
  }
}
```

### Timing

| Property | Value | Rationale |
|----------|-------|-----------|
| **Duration** | `var(--dur-morph)` (400ms) | Longer than individual highlights. The banner carries editorial weight -- it deserves a measured entrance. |
| **Easing** | `var(--ease-cinematic)` | Smooth deceleration. The banner "settles" into position. |
| **Delay** | `calc(var(--nx-total-highlights, 14) * 30ms + 100ms)` | Enters AFTER the highlight stagger completes. L-cut timing: the highlights are the setup, the omission banner is the payoff. The 100ms gap between last highlight and banner prevents visual collision. |
| **Exit** | `200ms`, `var(--ease-out)`, reverse clip-path | When X-Ray toggles off, banner wipes up and out. Faster than entrance -- departures are quicker than arrivals. |

### Implementation Pattern

```css
.nx-omission-banner {
  /* Visual: subtle warm-tinted bar, not alarming */
  background: color-mix(in srgb, var(--cin-amber) 6%, var(--bg-secondary));
  border-left: 2px solid var(--cin-amber-muted);
  padding: var(--space-2) var(--space-3);
  margin-bottom: var(--space-3);

  /* Typography: Meta voice for structural annotation */
  font-family: var(--font-meta);
  font-size: var(--text-sm);
  letter-spacing: 0.01em;
  color: var(--fg-secondary);

  /* Initial state: hidden via clip-path */
  clip-path: inset(100% 0 0 0);
  opacity: 0;
  will-change: clip-path, opacity;
}

.nx-active .nx-omission-banner {
  animation: nxOmissionReveal var(--dur-morph) var(--ease-cinematic) both;
  animation-delay: calc(var(--nx-total-highlights, 14) * 30ms + 100ms);
}

/* Exit: reverse wipe */
.nx-omission-banner--exiting {
  animation: nxOmissionReveal 200ms var(--ease-out) reverse both;
}

/* Missing entity names: data voice for precision */
.nx-omission-banner__entities {
  font-family: var(--font-data);
  font-size: var(--text-xs);
  color: var(--fg-tertiary);
  margin-top: var(--space-1);
}
```

### Reduced Motion Fallback

```css
@media (prefers-reduced-motion: reduce) {
  .nx-active .nx-omission-banner {
    animation: none !important;
    clip-path: none;
    opacity: 1;
  }
}
```

---

## 5. Count Badge Idle State

### Motivation

The "14 framing signals" badge sits near the source perspective header. Before activation, it must invite interaction without demanding it. This is not a notification -- it is an analytical tool waiting to be used. Think of a documentary camera's focus ring: always visible on the barrel, never flashing at you.

### Cinematic Technique: Practical Light (Warm Ambient Presence)

The badge has a very subtle warm ambient glow -- not pulsing, not blinking, but a static warmth that distinguishes it from surrounding metadata. The `--cin-amber-ghost` token at 8% opacity provides just enough visual distinction to register as interactive.

### NO Animation at Idle

The badge does NOT pulse, breathe, glow, or animate at rest. A pulsing badge would violate the editorial restraint principle. The badge communicates through:

1. **Typography contrast**: The count number uses `--font-data` (IBM Plex Mono), making it visually distinct from the surrounding `--font-structural` (Inter) body text.
2. **Warm tint**: Background uses `var(--cin-amber-ghost)` -- a barely-there amber wash that reads as "interactive" in the warm-paper context.
3. **Border**: `1px solid var(--cin-amber-dim)` at 25% opacity -- enough to define the badge boundary, not enough to shout.

### Hover State: Micro-Dolly

On hover, the badge gains a slightly stronger warm tint and a 1px warm shadow. This is the only animation -- a micro-dolly that says "yes, I am interactive."

```css
.nx-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);

  /* Warm ember -- interactive but patient */
  background: var(--cin-amber-ghost);
  border: 1px solid color-mix(in srgb, var(--cin-amber-dim) 25%, transparent);
  border-radius: var(--radius-sm);

  /* Data voice for the count, meta voice for the label */
  font-family: var(--font-data);
  font-size: var(--text-xs);
  color: var(--cin-amber);
  letter-spacing: 0.02em;
  cursor: pointer;

  /* Micro-dolly on hover */
  transition:
    background-color var(--dur-fast) var(--ease-out),
    box-shadow var(--dur-fast) var(--ease-out),
    transform 300ms var(--spring-snappy);
}

.nx-badge:hover {
  background: var(--cin-amber-glow);
  box-shadow: var(--shadow-cinematic-contact);
  transform: scale(1.02);
}

.nx-badge:active {
  transform: scale(0.97);
  transition: transform 60ms var(--ease-out);
}

/* Active state: badge is "on" -- filled amber */
.nx-badge--active {
  background: color-mix(in srgb, var(--cin-amber) 15%, var(--bg-card));
  border-color: color-mix(in srgb, var(--cin-amber) 40%, transparent);
  color: var(--cin-amber-bright);
  box-shadow: var(--shadow-cinematic-contact);
}
```

### Badge Label Typography

```
 14 framing signals
 ^^                 -- font-data, tabular-nums, --cin-amber
    ^^^^^^^^^^^^^^^^ -- font-meta, normal weight, --cin-amber-dim
```

The number is data voice. The label is meta voice. Two voices in one badge, consistent with existing Sigil and BiasInspector patterns.

### Reduced Motion Fallback

No animation to disable. Hover states remain (color change only -- the `transform: scale(1.02)` is suppressed by the global `transition-duration: 0ms` rule). The badge is fully functional without motion.

---

## Design Tokens to Add

These tokens extend `tokens.css` in the existing cinematic token section.

```css
:root,
:root[data-mode="light"] {
  /* ── Narrative X-Ray ── */
  --nx-charged-bg: rgba(148, 107, 21, 0.10);           /* Amber highlight for charged synonyms */
  --nx-charged-border: rgba(148, 107, 21, 0.20);       /* Subtle border on charged words */
  --nx-entity-warm: rgba(180, 100, 50, 0.50);          /* Warm underline: positive entity sentiment */
  --nx-entity-cool: rgba(80, 120, 170, 0.50);          /* Cool underline: negative entity sentiment */
  --nx-entity-neutral: rgba(140, 130, 120, 0.35);      /* Neutral entity underline */
  --nx-omission-bg: color-mix(in srgb, var(--cin-amber) 6%, var(--bg-secondary));
  --nx-stagger-gap: 30ms;                              /* Per-highlight stagger interval */
  --nx-badge-bg: var(--cin-amber-ghost);
  --nx-badge-border: color-mix(in srgb, var(--cin-amber-dim) 25%, transparent);
  --nx-badge-color: var(--cin-amber);
}

:root[data-mode="dark"] {
  --nx-charged-bg: rgba(212, 165, 116, 0.10);
  --nx-charged-border: rgba(212, 165, 116, 0.18);
  --nx-entity-warm: rgba(200, 140, 80, 0.45);
  --nx-entity-cool: rgba(100, 150, 200, 0.45);
  --nx-entity-neutral: rgba(160, 150, 140, 0.30);
  --nx-omission-bg: color-mix(in srgb, var(--cin-amber) 8%, var(--bg-secondary));
  --nx-badge-bg: var(--cin-amber-ghost);
  --nx-badge-border: color-mix(in srgb, var(--cin-amber-dim) 20%, transparent);
  --nx-badge-color: var(--cin-amber);
}
```

---

## Choreography Timeline

Complete sequence when user toggles the X-Ray ON for a source with 14 highlights and an omission banner:

```
Time (ms)   Event
─────────   ──────────────────────────────────────
  0         Badge click. Badge transitions to --active state.
            Spring press feedback (scale 0.97 -> 1.02 -> 1).
 16         First highlight begins resolving (opacity + bg-color).
 46         Second highlight begins resolving.
 76         Third highlight begins resolving.
  .             (30ms stagger continues)
  .
406         13th highlight begins resolving.
436         14th (last) highlight begins resolving.
636         Omission banner begins clip-path reveal.
            (100ms after last highlight starts, 636 = 436 + 100 + 100 for overlap)
1036        Omission banner fully revealed.
            Total sequence: ~1036ms from click.
            Perceived duration: ~700ms (last 300ms is just the banner settling).
```

Toggle OFF is faster:

```
Time (ms)   Event
─────────   ──────────────────────────────────────
  0         Badge click. Badge transitions to default state.
  0         All highlights begin fading (200ms, no stagger).
  0         Omission banner begins reverse clip-path wipe (200ms).
200         Everything cleared. Clean text restored.
```

The asymmetry is intentional: ON is a deliberate analytical reveal (staggered, ~1s). OFF is a clean cut (simultaneous, 200ms). Cinematic parallel: a slow zoom-in to examine evidence, then a quick cut back to the wide shot.

---

## Performance Checklist

| Criterion | Status | Notes |
|-----------|--------|-------|
| **GPU-only properties** | Yes | `opacity`, `transform`, `clip-path`, `background-color`, `background-size`, `box-shadow`. No width/height/top/left animation. |
| **will-change discipline** | Yes | Only `.nx-omission-banner` gets `will-change: clip-path, opacity` (applied at rest because it is always inside a conditionally rendered panel). Highlights use no `will-change` -- background-color animation is cheap. |
| **backdrop-filter count** | 0 | No backdrop-filter used in X-Ray. Budget remains available for Deep Dive backdrop + nav. |
| **Reduced motion** | Yes | Global `prefers-reduced-motion: reduce` rule zeros all animation-duration/delay. Per-component overrides ensure correct final visual state (highlights visible, banner visible, no stagger). |
| **Maximum simultaneous animations** | ~14 highlights + 1 banner | Each highlight is a single CSS animation on a `<mark>` element. Lightweight: bg-color only. No layout thrash. ~15 concurrent animations is well within browser compositing budgets. |
| **Blur operations** | 0 | No blur used in Narrative X-Ray. Surrounding text stays sharp. This preserves the blur budget for Deep Dive backdrop. |
| **Layout stability** | Yes | Highlights are inline `<mark>` elements with `display: inline`. They do not alter text flow. Omission banner uses `clip-path` (no height change). No CLS impact. |

---

## Color System Integration

The Narrative X-Ray color tokens derive from the existing cinematic amber palette, not from the bias color system. This is intentional:

- **Amber highlights** for charged synonyms use `--cin-amber-ghost` / `--cin-amber-glow` -- the same warmth as the Deep Dive accent system. Framing signals are editorial annotations, not bias scores. They belong to the "practical light" family, not the blue-red lean spectrum.
- **Entity sentiment** uses warm (amber-orange) and cool (steel-blue) underlines. These are not political -- they indicate TextBlob polarity. The warm/cool distinction maps to `positive/negative` sentiment, borrowing the natural cinematic association of warm=safe, cool=threatening without importing the political lean palette.
- **Omission banner** uses the muted amber left-border already established by the daily brief banner pattern (`border-left: 2px solid var(--cin-amber-muted)`). Visual consistency: amber left-borders mean "editorial annotation" throughout the app.

---

## Accessibility Notes

1. Highlights must not rely solely on color. Each highlight type gets a distinct visual treatment:
   - Charged synonyms: background-color fill (rectangle)
   - Entity sentiment: underline (line beneath text)
   - These two shapes are distinguishable even in grayscale.

2. Tooltips must be keyboard-accessible. On focus (Tab to a highlight), the tooltip appears with the same entrance animation. On blur, it exits.

3. The omission banner is a `role="status"` live region so screen readers announce it when it appears.

4. The count badge is a `<button>` with `aria-pressed` toggling between `true`/`false`.

5. All animated content must be readable at any point during animation -- no frames where text is invisible or illegible.

---

## Files to Create/Modify

| File | Action | What Changes |
|------|--------|--------------|
| `frontend/app/styles/tokens.css` | Modify | Add `--nx-*` tokens in both light and dark mode sections |
| `frontend/app/styles/animations.css` | Modify | Add `nxHighlightResolve`, `nxUnderlineDraw`, `nxTooltipIn`, `nxTooltipOut`, `nxOmissionReveal` keyframes + reduced motion overrides |
| `frontend/app/styles/components.css` | Modify | Add `.nx-highlight`, `.nx-entity`, `.nx-tooltip`, `.nx-omission-banner`, `.nx-badge` component styles |
| `frontend/app/components/NarrativeXRay.tsx` | Create | New component: toggle badge, highlight wrapper, tooltip controller |

---

## CINEMATOGRAPHER REPORT -- void --news

```
Date: 2026-04-01

SCENE: Narrative X-Ray (Deep Dive source perspective framing overlay)
MOTIVATION: Users need to see per-sentence bias signals without leaving
  their reading flow. The motion must shift attention without breaking
  spatial continuity -- documentary rack focus, not VFX.

SHOTS COMPOSED:
  1. RACK FOCUS RESOLVE on source text highlights
     Cinematic ref: Frederick Wiseman long-take documentary -- adjusting
       the lens to sharpen on what was always there
     Implementation: CSS background-color animation with DOM-order stagger
     Timing: 300ms per highlight, 30ms stagger gap, ease-cinematic
     Depth: No blur. Highlights are additive. Text stays sharp (deep focus).

  2. MICRO-DOLLY on tooltip entrance
     Cinematic ref: Michael Mann detail examination -- camera pulls in
       fractionally to inspect a word
     Implementation: CSS keyframe scale(0.97->1) + translateY(4px->0)
     Timing: 180ms entrance (spring-snappy), 120ms exit (ease-out)
     Depth: Tooltip at z-tooltip plane. No surrounding blur.

  3. CROSS-DISSOLVE on source comparison switch
     Cinematic ref: Standard editorial dissolve -- one shot replaces another
     Implementation: CSS opacity crossfade (200ms out, 300ms in)
     Timing: 500ms total envelope. Highlights re-stagger in new source.
     Depth: No depth change. Flat dissolve. Density contrast IS the shot.

  4. VERTICAL WIPE on omission banner entrance
     Cinematic ref: Documentary chyron reveal -- information appearing
       as text, not as spectacle
     Implementation: CSS clip-path: inset() animation, top-to-bottom
     Timing: 400ms, ease-cinematic, delayed after highlight stagger completes
     Depth: Banner at content plane. No elevation change.

  5. PRACTICAL LIGHT (STATIC) on count badge idle
     Cinematic ref: Terrence Malick available-light -- warmth that exists
       in the scene, not added by the DP
     Implementation: Static warm amber tint (cin-amber-ghost), no animation
     Timing: N/A (static). Hover: 150ms micro-dolly.
     Depth: Badge at content plane. No elevation.

TOKENS ADDED:
  - --nx-charged-bg: rgba(148,107,21,0.10) -- charged synonym amber fill
  - --nx-charged-border: rgba(148,107,21,0.20) -- charged synonym boundary
  - --nx-entity-warm: rgba(180,100,50,0.50) -- positive entity underline
  - --nx-entity-cool: rgba(80,120,170,0.50) -- negative entity underline
  - --nx-entity-neutral: rgba(140,130,120,0.35) -- neutral entity underline
  - --nx-omission-bg: color-mix amber+bg-secondary -- omission bar fill
  - --nx-stagger-gap: 30ms -- per-highlight cascade interval
  - --nx-badge-bg/border/color: amber family -- badge surface tokens

FILES TO MODIFY:
  - tokens.css: +18 lines (nx tokens, light + dark)
  - animations.css: +45 lines (5 keyframes + reduced motion)
  - components.css: +120 lines (nx component styles)
  - NarrativeXRay.tsx: new file (component implementation)

PERFORMANCE:
  GPU-only: Yes
  will-change discipline: Yes (only on omission banner)
  Backdrop-filter count: 0 simultaneous (no blur used)
  Reduced-motion fallback: Yes (instant appearance, no stagger)

NEXT: frontend-builder for component implementation, then vfx-artist
  for post-processing (potential film grain density shift when X-Ray
  is active -- grain receding to emphasize analytical clarity).
```
