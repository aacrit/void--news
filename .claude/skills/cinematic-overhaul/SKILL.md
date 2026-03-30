---
name: cinematic-overhaul
description: "Cinematic Motion & VFX Overhaul: logo-designer establishes cinematic palette/texture + cinematographer designs camera movements + motion-director choreographs scroll/gesture timelines + vfx-artist applies post-processing + frontend-builder implements + responsive-specialist validates + perf-optimizer benchmarks + uat-tester audits. Full cinematic design evolution."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /cinematic-overhaul -- Cinematic Motion & Visual Design Evolution

You are the workflow orchestrator for the **Cinematic Overhaul** of void --news -- evolving the visual experience from "newspaper web app" to "cinematic news experience" while preserving the Press & Precision design philosophy. This is not replacing the identity; it is adding a new layer: the language of cinema applied to web interaction.

## Design Philosophy Evolution

```
Press & Precision v1 (current):
  "A modern newspaper that respects the printing press tradition
   while embracing the data density of modern interfaces."

Press & Precision v2 (cinematic):
  "A modern newspaper shot by Roger Deakins, graded by Bradford Young.
   The same editorial authority, the same data density, but now with
   depth, light, focus, atmosphere, and a unified color story.
   The user does not read a page -- they move through a scene."
```

### What Is Locked vs. What Evolves

**Locked** (CEO approval required to change): 6-axis bias model, Supabase data layer, static export, 380-source list, $0 cost, bias color semantics (7-point lean spectrum, sensationalism scale, opinion/reporting, factual rigor).

**Evolves with cinematic identity**: Accent colors, texture system (paper grain, film grain, surface materials), overall brand warmth/coolness, the void logo mark (how it adapts to cinematic context), sigil/icon styling, typography weight/tracking refinements for cinematic feel, dark mode color grading. The brand identity is NOT locked -- it is a living system that evolves alongside the cinematic motion redesign.

The key insight: cinematic feel is not just motion. Color grading is what makes a Fincher film look different from a Wes Anderson film. The texture, grain, and color story are foundational to the cinematic identity -- they must be designed BEFORE camera movements and VFX layers can be properly calibrated.

## The Cinematic Principles

Every change in this overhaul must trace back to a real cinematography principle:

| Principle | Film Meaning | Web Application |
|-----------|-------------|-----------------|
| **Depth of Field** | Control what the audience focuses on by blurring the rest | Active element sharp, surrounding elements softened; Deep Dive = shallow DoF, feed = deep focus |
| **Rack Focus** | Shift focus between two subjects within a shot | Card hover: focused card sharpens, neighbors soften; edition switch: old edition softens, new sharpens |
| **Parallax** | Objects at different distances move at different speeds as camera moves | Scroll: background texture at 0.3x, content at 1x, sticky nav slightly faster |
| **Motivated Lighting** | Every light source in a scene has a visible or implied origin | OnAir amber glow = practical light source; card hover glow = environmental response |
| **Key Light Direction** | Consistent primary light source angle across all shots | All shadows cast from top-left (consistent --shadow-cinematic-* direction) |
| **Film Grain** | Photochemical texture that adds warmth and organic feel | SVG noise overlay with mix-blend-mode, subtle enough to be felt not seen |
| **Chiaroscuro** | Strong contrast between light and shadow for dramatic effect | Deep Dive panel (bright) against blurred feed (dim) = cinematic contrast |
| **Match Cut** | Visual continuity between two shots through shared element | Story card headline morphs into Deep Dive header via FLIP animation |
| **L-Cut** | Audio from next scene begins before visual transition | Content appears before its container finishes animating; overlap creates continuity |
| **Camera Movement** | Dolly, truck, crane, steadicam -- each has a purpose | Scale changes = dolly; translateX = truck; translateY = crane; smooth scroll = steadicam |
| **Rule of Thirds** | Key subjects placed at grid intersection points | Lead story anchored at left third, Deep Dive content at right third |
| **Vignette** | Darkened edges focus attention on center of frame | Subtle CSS radial gradient darkening at viewport edges |
| **Color Grading** | Unified color science across all shots in a film | CSS filter on root: slight warmth (light) or desaturation (dark) across all content |
| **Scene Transitions** | Cut, dissolve, wipe, match cut -- each tells a different story | Feed->DeepDive = match cut; edition switch = whip pan; theme toggle = dissolve |

## Team Composition

| Agent | Role | Phase | Parallel With |
|-------|------|-------|---------------|
| `logo-designer` | Cinematic palette, texture system, brand mark evolution | 1 (1a) | cinematographer |
| `cinematographer` | Camera language, depth planes, lighting design | 1 (1a) | logo-designer |
| `motion-director` | Scene choreography, scroll timelines, gesture physics | 1 (1b) | -- |
| `vfx-artist` | Post-processing, grain, color grading, lens effects | 1 (1c) | -- |
| `frontend-builder` | Token + CSS + component implementation | 2 | -- |
| `responsive-specialist` | Breakpoint validation | 3 | perf-optimizer |
| `perf-optimizer` | Lighthouse + GPU audit | 3 | responsive-specialist |
| `uat-tester` | Cinematic experience audit | 4 | -- |
| `frontend-fixer` | Patch issues (conditional) | 5 | -- |

## Workflow Stages

```
 PHASE 1 ── DESIGN (read + design tokens)
 ┌───────────────────────────────────────────────────────────────────┐
 │  STAGE 1a — PARALLEL:                                             │
 │                                                                   │
 │    Logo Designer: Cinematic Brand Identity                        │
 │      Establish the cinematic color story, texture system, accent  │
 │      palette, brand mark evolution, and sigil/icon refinements.   │
 │      This is the color grading LUT and film stock selection —     │
 │      it defines HOW the film looks before the camera moves.       │
 │      Output: cinematic palette tokens + texture specs + brand     │
 │      mark adaptations + typography refinements.                   │
 │                                                                   │
 │    Cinematographer: Camera Language Design                         │
 │      Design all camera movements, depth planes, focus behavior,   │
 │      and scene compositions. Uses logo-designer's palette for     │
 │      lighting design (key light warmth, rim light color, shadow   │
 │      tint). Output: cinematic design tokens + per-component       │
 │      motion specifications.                                       │
 │                                                                   │
 │  ──── SYNC POINT: merge palette + camera language ────            │
 │                                                                   │
 │  STAGE 1b — Motion Director: Scene Choreography                   │
 │    Sequence all animations into scene timelines. Define scroll-   │
 │    driven behaviors, gesture physics, L-cut overlaps, and the     │
 │    overall temporal rhythm. Output: scene-by-scene timeline +     │
 │    scroll API strategy.                                           │
 │                                                                   │
 │  STAGE 1c — VFX Artist: Post-Processing Design                    │
 │    Design film grain, color grading, vignette, atmospheric haze,  │
 │    lens effects, and light interaction. Uses logo-designer's      │
 │    texture system for grain character and color grading values.    │
 │    Output: VFX layer specs + CSS filter values + SVG filter       │
 │    definitions.                                                   │
 └───────────────────────────────────────────────────────────────────┘

 PHASE 2 ── IMPLEMENT (write)
 ┌───────────────────────────────────────────────────────────────────┐
 │  STAGE 2a — Frontend Builder: Token + CSS Implementation          │
 │    Implement cinematic design tokens in tokens.css.               │
 │    Add new keyframes to animations.css.                           │
 │    Apply camera movement CSS to components.css.                   │
 │    Add scroll-driven animation rules.                             │
 │    Add VFX post-processing layers.                                │
 │                                                                   │
 │  STAGE 2b — Frontend Builder: Component Updates                   │
 │    Update DeepDive.tsx (match cut, L-cut timing, dolly effects).  │
 │    Update HomeContent.tsx (parallax, rack focus, scroll timeline). │
 │    Update StoryCard.tsx (rack focus hover, cinematic shadow).      │
 │    Update SkyboxBanner.tsx (practical lighting propagation).       │
 │    Add VFX wrapper component (film grain + vignette overlay).     │
 └───────────────────────────────────────────────────────────────────┘

 PHASE 3 ── VALIDATE (parallel read-only + write)
 ┌───────────────────────────────────────────────────────────────────┐
 │  STAGE 3a — Responsive Specialist: Breakpoint Validation          │
 │    (parallel)                                                     │
 │    Verify cinematic effects degrade gracefully on mobile.         │
 │    Verify parallax reduces to 2 layers on mobile.                 │
 │    Verify blur levels halved on mobile.                           │
 │    Verify film grain disabled on hover:none.                      │
 │    All 8 combinations: 4 breakpoints x 2 color modes.            │
 │                                                                   │
 │  STAGE 3b — Perf Optimizer: Lighthouse + GPU Audit                │
 │    (parallel)                                                     │
 │    Run `npm run build` (must pass).                               │
 │    Verify Lighthouse Performance score >= 90.                     │
 │    Count simultaneous backdrop-filter elements (<= 2).            │
 │    Count will-change active elements (<= 5).                      │
 │    Verify no layout-triggering property animations.               │
 │    Verify CSS filter is applied to max 1 root element.            │
 │    Measure FCP, LCP, TBT, CLS against budgets.                   │
 └───────────────────────────────────────────────────────────────────┘

 PHASE 4 ── QA (read-only)
 ┌───────────────────────────────────────────────────────────────────┐
 │  STAGE 4 — UAT Tester: Cinematic Experience Audit                 │
 │    Evaluate through the cinematic lens:                            │
 │    - Does scrolling feel like a steadicam shot? (smooth, layered) │
 │    - Does card hover feel like a focus pull? (depth shift)         │
 │    - Does Deep Dive open feel like a match cut? (visual continuity)│
 │    - Does edition switch feel like a whip pan? (directional, fast) │
 │    - Is film grain felt but not seen? (subliminal)                │
 │    - Is the vignette adding framing without claustrophobia?       │
 │    - Does the overall experience feel cinematic or gimmicky?      │
 │    - Does prefers-reduced-motion disable everything correctly?    │
 │    - Is the Press & Precision editorial authority preserved?      │
 │    Standard UAT checklist + cinematic quality assessment.          │
 └───────────────────────────────────────────────────────────────────┘

 PHASE 5 ── FIX (write, conditional)
 ┌───────────────────────────────────────────────────────────────────┐
 │  GATE: If Phase 3+4 pass clean → DONE                            │
 │                                                                   │
 │  STAGE 5a — Frontend Fixer: Patch Issues                          │
 │    Fix any performance regressions (filter budget exceeded, etc.) │
 │    Fix responsive breakage (mobile parallax, blur levels).        │
 │    Fix animation timing issues (jank, missed L-cuts).             │
 │    Fix reduced-motion gaps.                                       │
 │                                                                   │
 │  STAGE 5b — UAT Tester: Re-verify (re-run Stage 4)               │
 └───────────────────────────────────────────────────────────────────┘
```

## Execution Instructions

### Phase 1: Design

**Stage 1a: Launch `logo-designer` and `cinematographer` in PARALLEL**

These two agents run simultaneously. The logo-designer establishes the color story and texture language; the cinematographer designs the camera movements. Both inform each other at the sync point.

**Launch `logo-designer`** with this brief:

> You are establishing the cinematic brand identity for void --news. This is not a logo redesign -- it is a cinematic evolution of the entire sensory palette. Think of yourself as the colorist and film stock selector: you define HOW the film looks before anyone points the camera.
>
> Design the following systems:
>
> **1. Cinematic Color Palette**
> - Primary accent color(s) for cinematic identity (what is void's "teal" the way Fincher has teal-and-orange, or Wes Anderson has pastels?)
> - Secondary accents for interactive states, hover glows, active indicators
> - Dark mode color grading direction: cooler/warmer, desaturation level, shadow warmth
> - Light mode color grading direction: warmth level, paper tone refinement
> - Accent colors must harmonize with the existing bias spectrum (blue-gray-red) without competing
>
> **2. Texture System**
> - Paper grain: refine the existing paper texture (is it laid paper? linen? cotton rag? newsprint halftone?)
> - Film grain: character of the cinematic grain overlay (fine/coarse, warm/cool, density)
> - Surface materials: card surfaces (matte? satin? slightly glossy?), elevated surface feel
> - Noise patterns: SVG noise parameters (frequency, octaves, type) for different layers
>
> **3. Brand Mark Evolution**
> - How does the void logo (ScaleIcon circle + beam) adapt to the cinematic identity?
> - Does the stroke weight, animation timing, or glow behavior change?
> - Sigil/icon system: how do BiasLens icons, category markers, and UI glyphs evolve?
> - Favicon: any refinement needed for cinematic consistency?
>
> **4. Typography Refinements** (adjustments only -- fonts are locked)
> - Weight or tracking adjustments for cinematic headlines (e.g., slightly tighter tracking on Playfair for density)
> - Any letter-spacing refinements on Barlow Condensed meta text for cinematic feel
> - Contrast ratio adjustments between headline and body weights
>
> Output as CSS custom property specifications and design rationale. Reference specific films, colorists, or visual references for each choice. Read the existing tokens.css, DESIGN-SYSTEM.md, and all logo components before designing.

**Launch `cinematographer`** with this brief:

> Design the cinematic camera language for void --news. You are converting every interaction and transition from "functional web animation" to "motivated camera movement." Cover these scenes:
>
> 1. Page load (cold open)
> 2. Feed scrolling (steadicam + parallax)
> 3. Story card hover (rack focus)
> 4. Feed -> Deep Dive (match cut)
> 5. Deep Dive -> Feed (reverse shot)
> 6. Edition switching (whip pan)
> 7. Audio playback (practical lighting)
> 8. Theme toggle (dissolve)
>
> For each scene: specify the camera technique, the CSS/JS implementation, the timing, and the depth-of-field behavior. Create the cinematic design tokens. Reference real cinematographers.
>
> NOTE: The logo-designer is running in parallel to establish the cinematic color palette and texture system. Your lighting design (key light warmth, rim light color, shadow tint, practical light color) should use CSS custom properties that the logo-designer's palette will populate. Design your shadow and light tokens as references to palette variables (e.g., `var(--cinematic-accent)`, `var(--cinematic-shadow-tint)`) so they can be connected after the sync point.

**SYNC POINT: After both agents complete, review their outputs together. Ensure:**
- Cinematographer's shadow tint and lighting warmth align with logo-designer's color grading
- Logo-designer's texture specs are compatible with cinematographer's depth plane system
- No conflicting token names or overlapping custom properties
- Resolve any conflicts before proceeding to Stage 1b

**Stage 1b: Launch `motion-director`**

Provide the merged logo-designer + cinematographer output, then brief:

> Take the cinematographer's camera language and choreograph it into scene timelines. Define the frame-by-frame sequence for each scene. Specify where L-cuts overlap (content before container), where match cuts maintain visual continuity, and where whip pans create directional energy. Define the scroll-driven animation strategy (CSS scroll-timeline with IntersectionObserver fallback). Define gesture physics for mobile.
>
> The logo-designer has established the cinematic palette and texture system. Your choreography should respect the texture layering order (paper grain beneath content, film grain above, vignette topmost) and use the palette accent colors for any timed glow or flash effects.

**Stage 1c: Launch `vfx-artist`**

Provide logo-designer + cinematographer + motion-director outputs, then brief:

> Apply the final post-processing layer. The logo-designer has established the foundational texture system and color grading direction -- your job is to implement and refine those specifications into production-ready VFX layers.
>
> Specifically:
> - **Film grain**: Use the logo-designer's grain character specs (frequency, octaves, warmth) as your SVG noise parameters. Refine for screen rendering.
> - **Color grading**: Use the logo-designer's Morning/Evening Edition color grading direction to set your CSS filter values. The grade should feel like the LUT was baked from the logo-designer's palette.
> - **Vignette**: Viewport edge darkening using the logo-designer's shadow warmth values.
> - **Atmospheric haze**: Depth-based desaturation calibrated to the logo-designer's saturation targets.
> - **Lens effects**: Chromatic aberration on hero headline, lens breathing on scroll.
> - **Light interaction**: OnAir glow propagation using the logo-designer's accent color, card hover rim light using the palette.
>
> Every effect must be subliminal -- felt, not seen. The logo-designer's palette is your LUT. The cinematographer's depth planes are your compositing layers. Layer them.

### Phase 2: Implement (Sequential)

**Stage 2a: Launch `frontend-builder`**

Provide all Phase 1 outputs. Brief:

> Implement the cinematic design system. In order:
> 1. Add cinematic tokens to `tokens.css` (depth planes, focus levels, cinematic easings, parallax rates, grain, shadows, vignette)
> 2. Add cinematic keyframes to `animations.css` (parallax, rack focus, whip pan, lens breathing, grain cycle)
> 3. Update `components.css` with cinematic shadows, rack focus hover on cards, depth-layered z-planes
> 4. Add VFX overlay layer (film grain + vignette) as a CSS pseudo-element system
> 5. Add scroll-driven animation rules with `@supports` progressive enhancement
>
> Follow the cinematographer's token specifications exactly. Do not deviate from the VFX artist's opacity levels. Respect all performance guardrails.

**Stage 2b: Launch `frontend-builder`** (second run)

> Now update the components that need JavaScript changes:
> 1. Update `DeepDive.tsx` -- enhance FLIP morph timing, add feed dolly-out effect, add L-cut content overlap
> 2. Update `HomeContent.tsx` -- add scroll-driven parallax CSS classes, rack focus neighbor dimming on card hover
> 3. Update `StoryCard.tsx` -- add rack focus data attributes, cinematic shadow on hover
> 4. Add a `CinematicLayer.tsx` component (client-only) that renders the film grain SVG filter `<defs>` and the vignette pseudo-element, mounted once at root
>
> All changes must preserve existing functionality. New cinematic behaviors layer on top, they do not replace.

### Phase 3: Validate (Parallel)

Launch **responsive-specialist** and **perf-optimizer** simultaneously.

Responsive brief:
> Verify cinematic effects across all breakpoints. Specific checks:
> - Mobile (375px): parallax reduced to 2 layers, blur halved, no film grain animation, no rack focus
> - Tablet (768px): reduced parallax, reduced blur
> - Desktop (1024px, 1440px): full cinematic experience
> - prefers-reduced-motion: ALL cinematic effects disabled (grain static, no parallax, no rack focus, no vignette scroll tracking, instant transitions)
> - Light/dark mode: color grading appropriate per mode

Performance brief:
> Audit cinematic impact on Lighthouse and GPU:
> - `npm run build` must pass
> - Lighthouse Performance >= 90
> - FCP < 1.5s, LCP < 2.5s, TBT < 200ms, CLS < 0.1
> - Simultaneous backdrop-filter <= 2
> - will-change elements <= 5
> - Global CSS filter on max 1 element
> - Film grain compositing layer count
> - No layout-triggering property animations (width, height, top, left, margin, padding)

### Phase 4: QA

Launch **uat-tester** with this extended brief:

> Perform a standard UAT audit with an additional cinematic quality section. Beyond the normal 10-phase audit, evaluate:
>
> **Cinematic Quality Assessment (10 questions)**:
> 1. Does page load feel like a cold open? (elements arrive with purpose, not popping in)
> 2. Does scrolling feel smooth and layered? (parallax creates spatial depth)
> 3. Does card hover feel like a camera focus pull? (focused card pops, neighbors recede)
> 4. Does Deep Dive opening feel like a match cut? (visual continuity from card to panel)
> 5. Does Deep Dive closing feel snappy and decisive? (reverse shot, quick cut)
> 6. Does edition switching have directional momentum? (whip pan energy)
> 7. Is the film grain subliminal? (felt as "warmth" not as "noise")
> 8. Does the vignette frame the content without feeling like an Instagram filter?
> 9. Is the color grading consistent? (Morning Edition warm, Evening Edition moody)
> 10. Overall: Does this feel like a cinematic experience or a VFX demo reel?
>
> Score: "Cinematic" (success) / "Gimmicky" (VFX too visible) / "Flat" (VFX not perceptible)
> Target: "Cinematic" -- the user FEELS it but cannot EXPLAIN it.

### Phase 5: Fix (Conditional)

If any issues from Phase 3 or 4:
- Launch **frontend-fixer** with the combined report
- Re-run **uat-tester** to confirm

### Final Report

```
## Cinematic Overhaul Report
- **Result**: SHIPPED / NEEDS WORK / BLOCKED
- **Philosophy**: Press & Precision v2 -- "newspaper shot by Roger Deakins, graded by Bradford Young"

### Brand Identity Evolution
| Element | Before | After | Rationale |
|---------|--------|-------|-----------|
| Accent color | [old] | [new] | [film/colorist reference] |
| Texture | [old] | [new] | [paper/film stock reference] |
| Logo adaptation | [old] | [new] | [how mark evolved] |
| Dark mode grade | [old] | [new] | [cinematic direction] |
| Typography tuning | [old] | [new] | [tracking/weight change] |

### Cinematic Techniques Applied
| Technique | Component | Implementation |
|-----------|-----------|----------------|
| Rack focus | StoryCard hover | Neighbor opacity dim + blur |
| Match cut | Feed -> DeepDive | FLIP morph with L-cut |
| Whip pan | Edition switch | Directional translateX + motion blur |
| Parallax | Feed scroll | CSS scroll-timeline + IO fallback |
| Film grain | Global | SVG noise, mix-blend-mode overlay |
| Vignette | Global | Fixed pseudo-element, scroll-tracked center |
| Color grade | Global | CSS filter on :root, per-mode values |
| Chiaroscuro | DeepDive | Panel bright vs blurred dim feed |
| Practical lighting | OnAir pill | Accent glow propagation |
| Key light | All shadows | Consistent top-left direction |

### Performance
- Lighthouse: [score]/100
- FCP: [N]s | LCP: [N]s | TBT: [N]ms | CLS: [N]
- GPU budget: backdrop-filter [N]/2 | will-change [N]/5 | global filter [N]/1

### Responsive
- Desktop: Full cinematic | Mobile: Graceful reduction | Reduced motion: All disabled

### Cinematic Quality
- UAT verdict: [Cinematic / Gimmicky / Flat]
- "Does it feel like a film?" [Yes/No]
- "Can you explain why?" [Should be No -- subliminal effects succeed when invisible]

### Files Changed
[list with file:line]

### Design Token Additions
[list of new CSS custom properties -- palette, texture, and cinematic tokens]
```

## Guardrails (Non-Negotiable)

1. **Lighthouse >= 90** -- If any cinematic effect drops performance below 90, it gets cut
2. **prefers-reduced-motion**: ALL cinematic effects instantly disabled. No exceptions.
3. **Mobile**: Film grain animated = off. Parallax = 2 layers max. Blur = halved. Rack focus = off.
4. **$0 cost**: CSS + Motion One CDN only. No WebGL. No paid libraries. No canvas.
5. **Press & Precision preserved**: Typography voices, bias colors, data semantics, layout structure unchanged
6. **Subtlety test**: If a user can consciously identify a VFX effect, it is too strong. Dial it back.
7. **No barrel distortion, no extreme chromatic aberration, no motion blur > 2px, no shake cam**
8. **Existing functionality preserved**: All current animations continue to work. Cinematic layers ADD, they do not REPLACE.
