# void --history — Design Specification

**Version:** 1.0 (Creative Brief)
**Date:** 2026-04-04
**Status:** DESIGN RESEARCH — no code yet
**Author:** Frontend Builder (Component Engineer)

---

## 0. The Premise

void --news makes media bias visible in today's headlines. void --history makes narrative bias visible across the centuries.

The same event — the Partition of India, the Fall of Constantinople, the Cuban Missile Crisis — reads differently depending on who wrote the account, when they wrote it, and who they were writing for. void --history takes 50 critical events and presents them through the lens of every side that lived them, died in them, or profited from them.

**The thesis:** History is not what happened. History is who told the story.

---

## 1. Visual Identity — "The Archive"

### 1a. Design Philosophy

void --news is a newspaper shot through a cinema lens. void --history is a **war correspondent's field archive shot through a documentary lens**.

Think: a leather-bound field journal opened on an archivist's lightbox. Typewritten dispatches pinned to corkboard. Declassified documents with redaction bars. Faded photographs with handwritten annotations in the margins. A cartographer's desk with overlapping maps from different empires, each claiming the same territory under different names.

The aesthetic is not "old-timey" or decorative nostalgia. It is the **physical weight of primary sources** — the texture of paper that was carried across a border, folded into an envelope, stamped by a censor, stored in an attic, and digitized 80 years later. Every visual choice should make the reader feel they are handling something that existed before them.

**On arrival:** The stillness of a reading room. Warm lamplight on foxed paper. One document centered under glass.
**On interaction:** The drawer slides open. More documents. Contradicting accounts. Maps that don't agree. The archive reveals its depth.

### 1b. Color Palette — "Lamplight & Foxing"

void --news lives in warm amber (a newspaper under morning light). void --history lives in **cooled sepia and archival neutrals** — the color of things preserved rather than printed fresh.

#### Light Mode — "Reading Room"

Not white. Not warm paper. **Foxed vellum** — the slightly yellowed, slightly mottled surface of aged document paper under controlled lighting.

```css
:root[data-mode="light"] .hist-page {
  /* Surfaces */
  --hist-bg-primary:    #F2EDE0;   /* Foxed vellum — warmer than white, cooler than void --news #F0EBDD */
  --hist-bg-secondary:  #E9E3D4;   /* Aged document backing */
  --hist-bg-card:       #F7F2E7;   /* Clean archival card stock */
  --hist-bg-elevated:   #FFFCF5;   /* Lamplight highlight on document surface */
  --hist-bg-inset:      #EAE4D2;   /* Recessed panel — shadow box interior */

  /* Text — iron gall ink character */
  --hist-fg-primary:    #1E1B16;   /* Near-black iron gall — very slightly warm brown */
  --hist-fg-secondary:  #4A4437;   /* Aged ink, slightly faded */
  --hist-fg-tertiary:   #716A5C;   /* Marginal annotations, faded */
  --hist-fg-muted:      #8C8475;   /* Ghost text, watermarks */

  /* Accent — Archival Red */
  --hist-accent:        #8B2E2E;   /* Archival stamp red / wax seal — muted, authoritative, not bright */
  --hist-accent-hover:  #A33636;
  --hist-accent-ghost:  rgba(139, 46, 46, 0.06);
  --hist-accent-glow:   rgba(139, 46, 46, 0.12);

  /* Borders — document edges */
  --hist-border-subtle: #E2DCCC;   /* Deckle edge suggestion */
  --hist-border-strong: #C4BBA8;   /* Document border / mat board edge */
  --hist-divider:       #D4CCBA;   /* Section rules — thicker, more deliberate than news */
}
```

#### Dark Mode — "Conservation Lab"

Not black. **Archival charcoal** — the inside of a museum display case. Controlled darkness that makes documents glow by contrast.

```css
:root[data-mode="dark"] .hist-page {
  --hist-bg-primary:    #191714;   /* Museum case interior — slightly cooler than void --news dark */
  --hist-bg-secondary:  #232018;   /* Shadow behind mounted document */
  --hist-bg-card:       #2C2820;   /* Document under glass — warm but contained */
  --hist-bg-elevated:   #36312A;   /* Lifted / lit document surface */
  --hist-bg-inset:      #1E1C18;   /* Deep shadow well */

  --hist-fg-primary:    #E8E2D4;   /* Warm cream — document paper illuminated */
  --hist-fg-secondary:  #B8AE9C;
  --hist-fg-tertiary:   #9A9080;
  --hist-fg-muted:      #706858;

  --hist-accent:        #C25A5A;   /* Brighter seal red for dark backgrounds */
  --hist-accent-hover:  #D46A6A;
  --hist-accent-ghost:  rgba(194, 90, 90, 0.08);
  --hist-accent-glow:   rgba(194, 90, 90, 0.15);

  --hist-border-subtle: #332F28;
  --hist-border-strong: #4A443A;
  --hist-divider:       #3E3830;
}
```

#### Perspective Colors (The Narrative Spectrum)

Where void --news uses a blue-gray-red political lean spectrum, void --history uses a **geographic/national perspective spectrum**. These are NOT political colors — they are neutral identifiers that distinguish viewpoints without implying which is "correct."

```css
/* Perspective identifiers — muted, archival-feeling tones */
--hist-perspective-a:  #3D6B8E;   /* Steel blue — Western/colonial perspective */
--hist-perspective-b:  #8E5A3D;   /* Burnt sienna — local/indigenous perspective */
--hist-perspective-c:  #5A7A4A;   /* Olive green — third-party/neutral observer */
--hist-perspective-d:  #7A5A7A;   /* Dusty mauve — revisionist/modern reinterpretation */
--hist-perspective-e:  #8E7A3D;   /* Ochre — contemporary primary source */

/* These are assigned per-event, not hardcoded to any nation or ideology.
   The same steel blue might be "British" on one event and "Japanese" on another.
   The assignment follows the event's specific narrative structure. */
```

### 1c. Typography — Four Voices, One New Addition

void --history inherits the four-voice system but modifies one voice and adds weight to another.

| Voice | Font | Weight | Role | Change from void --news |
|-------|------|--------|------|------------------------|
| **Editorial** | Playfair Display | 400, 700 | Event titles, section headers, pull quotes | Same — the editorial authority voice bridges the two products |
| **Structural** | Inter | 400, 500, 600 | Body narrative, navigation, labels | Same — the workhorse |
| **Archival** | IBM Plex Mono | 300, 400 | Primary source quotations, dates, document citations, metadata | Renamed from "Data" — used at lighter weight (300) for a typewritten dispatch feel |
| **Meta** | Barlow Condensed | 400, 500, 600 | Region tags, era labels, source type indicators | Same |

**New behavior for the Archival voice:** In void --news, IBM Plex Mono is used for numeric data (scores, timestamps). In void --history, it takes on the role of **typewritten primary source text** — dispatches, cables, diary entries, official correspondence. Used at weight 300 with slightly increased letter-spacing (`0.02em`) and reduced line height (`1.5`) to evoke a typewriter ribbon's output.

**Type Hierarchy:**

```
Event title:         Playfair Display 700, var(--hist-text-hero)   — "The Partition of India, 1947"
Section title:       Playfair Display 700, var(--hist-text-xl)     — "The British Perspective"
Narrative subhead:   Playfair Display 400, var(--hist-text-lg)     — "Mountbatten's Deadline"
Body narrative:      Inter 400, var(--hist-text-base), 1.7 lh     — Slightly more generous than news (1.6)
Primary source:      IBM Plex Mono 300, var(--hist-text-sm)        — Typewriter voice
Document citation:   IBM Plex Mono 400, var(--hist-text-xs)        — Source reference
Era/Region label:    Barlow Condensed 500, uppercase, 0.08em tracking
```

### 1d. Texture System — "Paper Aging, Not Film Grain"

void --news uses film grain (fractalNoise SVG) to evoke cinema. void --history replaces film grain with **document aging textures** — foxing, laid paper lines, and ink absorption variation.

| Texture | Implementation | Where Used |
|---------|---------------|------------|
| **Foxing** | SVG feTurbulence (type="fractalNoise", baseFrequency="0.015 0.02", numOctaves=2) with warm brown colorMatrix | Page background — the irregular brown spots on aged paper |
| **Laid Paper Lines** | Repeating SVG pattern (horizontal lines, 2px period, opacity 0.04) | Document cards, primary source blocks — the texture of handmade paper |
| **Ink Absorption** | CSS backdrop-filter: contrast(1.02) saturate(0.90) | Text containers — simulates how ink looks slightly different on absorbent paper |
| **Document Edge** | Box-shadow with irregular opacity (stepped gradient) | Card edges — deckle/torn edge suggestion, not rounded corners |
| **Photograph Grain** | High-frequency turbulence (baseFrequency="0.8", numOctaves=1) | Image overlays — silver halide grain on photographs |
| **Map Crease** | Linear gradient with opacity variation | Map overlays — fold lines |
| **Redaction Bar** | Solid black rectangle with 2% opacity noise overlay | Censored/unknown content indicator |

### 1e. Post-Processing — "Archival Grade"

void --news applies a cinematic color grade. void --history applies an **archival preservation grade**.

```css
/* Light mode — aged but preserved. Not sepia-drenched — controlled. */
--hist-grade: contrast(1.02) saturate(0.85) sepia(0.06) brightness(1.01);

/* Dark mode — museum-lit. Slight warmth from display lighting. */
--hist-grade-dark: contrast(1.04) saturate(0.80) sepia(0.03) brightness(0.98);

/* Photograph overlay — heavier treatment for images specifically */
--hist-photo-grade: contrast(1.08) saturate(0.70) sepia(0.12);

/* Document scan overlay — the look of a flatbed scan of old paper */
--hist-scan-grade: contrast(1.06) saturate(0.75) sepia(0.08) brightness(1.02);
```

**Vignette:** Tighter and more circular than void --news (which uses an ellipse). This evokes a desk lamp's pool of light centered on the document.

```css
--hist-vignette: radial-gradient(
  circle 45% at 50% 40%,
  transparent 30%,
  rgba(30, 27, 22, 0.08) 70%,
  rgba(30, 27, 22, 0.18) 100%
);
```

---

## 2. Page Architecture

### 2a. Landing/Home — "The Archive Index"

The landing page is not a timeline (too cliche), not a map (too interactive-for-its-own-sake), and not a grid of cards (too void --news).

It is a **catalog cabinet** — the card-catalog drawers of a research library, where each drawer is an era or region, and pulling one open reveals the events within.

**Layout:**

```
┌─────────────────────────────────────────────────────────────────┐
│  void --history                               [Search] [Theme]  │  ← Topbar (no NavBar — like Weekly)
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  "History is not what happened.                                 │
│   It is who told the story."                                    │  ← Hero pull quote (Playfair 400 italic)
│                                                                 │
│  ─────────── Explore 50 events across 6 centuries ───────────   │
│                                                                 │
│  ┌─── By Era ──────────────────────────────────────────────┐    │
│  │                                                         │    │
│  │  ■ Antiquity & Medieval (before 1500)         4 events  │    │
│  │  ■ Early Modern (1500–1800)                   8 events  │    │
│  │  ■ The Long 19th Century (1789–1914)         10 events  │    │
│  │  ■ World Wars (1914–1945)                    12 events  │    │
│  │  ■ Cold War & Decolonization (1945–1991)     10 events  │    │
│  │  ■ Contemporary (1991–present)                6 events  │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─── By Region ───────────────────────────────────────────┐    │
│  │                                                         │    │
│  │  Asia · Africa · Europe · Americas · Middle East        │    │  ← Horizontal region pills
│  │  Global (multi-region events)                           │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─── Featured ────────────────────────────────────────────┐    │
│  │                                                         │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │    │
│  │  │ [image]      │  │ [image]      │  │ [image]      │  │    │  ← 3 featured events
│  │  │              │  │              │  │              │  │    │     full-bleed images
│  │  │ The Partition│  │ Fall of the  │  │ Cuban Missile│  │    │     with title overlay
│  │  │ of India     │  │ Berlin Wall  │  │ Crisis       │  │    │
│  │  │ 1947         │  │ 1989         │  │ 1962         │  │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─── Timeline ────────────────────────────────────────────┐    │
│  │                                                         │    │
│  │  1453 ──●── 1776 ──●── 1857 ──●── 1914 ──●── 1947 ... │    │  ← Compact horizontal timeline
│  │         │          │          │          │              │    │     scrub to browse all 50
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**Era Drawers:** Each era row is a clickable/tappable drawer. On click, it slides open to reveal the events within as a horizontal scroll of small document cards — each showing the event name, year, a thumbnail image, and the number of perspectives available.

**Featured Rotation:** The 3 featured events rotate weekly (or editorially curated). Full-bleed archival photographs with the `--hist-photo-grade` filter applied. Event title in Playfair Display 700 over a dark gradient at the bottom of the image.

**Compact Timeline:** A thin horizontal timeline at the bottom of the landing page. Each event is a node (small dot) positioned proportionally along the timeline. Hovering a node reveals the event title. Clicking navigates to the event detail page. The timeline doubles as a persistent navigation element that can be surfaced on event detail pages.

### 2b. Event Detail Page — "The Dossier"

This is the core experience. Each event gets a dedicated page that functions like an open dossier on an archivist's desk.

**Layout — Desktop (1024px+):**

```
┌───────────────────────────────────────────────────────────────────────────┐
│  ← Archive    The Partition of India, 1947     [share] [theme]           │  ← Topbar
├───────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌─── Hero ──────────────────────────────────────────────────────────┐   │
│  │                                                                    │   │
│  │  [Full-bleed archival photograph with archival grade filter]       │   │
│  │                                                                    │   │
│  │  ┌─────────────────────────────────────────────────────────────┐  │   │
│  │  │  THE PARTITION OF INDIA                                     │  │   │  ← Title card overlay
│  │  │  August 14-15, 1947                                         │  │   │     (Playfair 700, hero size)
│  │  │  South Asia · Decolonization · 4 perspectives               │  │   │
│  │  └─────────────────────────────────────────────────────────────┘  │   │
│  │                                                                    │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                                                           │
│  ┌─── Context Panel ("What Happened") ────────────────────────────────┐  │
│  │                                                                     │  │
│  │  [Neutral, factual summary of the event — 200-300 words.           │  │  ← Inter 400 body text
│  │   No perspective. Just verifiable facts, dates, participants.      │  │     Playfair subhead
│  │   Like a museum placard.]                                          │  │
│  │                                                                     │  │
│  │  Key Facts:                                                         │  │  ← IBM Plex Mono, compact
│  │  Date: August 14-15, 1947                                          │  │
│  │  Location: British India → India + Pakistan                        │  │
│  │  Principal Actors: Mountbatten, Nehru, Jinnah, Radcliffe          │  │
│  │  Estimated Deaths: 200,000 - 2,000,000                            │  │
│  │  Displaced: ~15 million                                            │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌─── Perspective Navigator ──────────────────────────────────────────┐  │
│  │                                                                     │  │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐     │  │
│  │  │ ■ British  │ │ ■ Indian   │ │ ■ Pakistani│ │ ■ Modern   │     │  │  ← Tab-style perspective
│  │  │   Colonial │ │   National │ │   National │ │   Academic │     │  │     selector
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘     │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌─── Active Perspective ──── "The British Perspective" ──────────────┐  │
│  │                                                                     │  │
│  │  ┌── Narrative ─────────────────────────────────────────────────┐  │  │
│  │  │                                                               │  │  │
│  │  │  [Long-form narrative from this perspective. 500-800 words.  │  │  │  ← Inter 400, justified
│  │  │   How did this side experience, justify, or narrate this     │  │  │     1.7 line-height
│  │  │   event? What was the dominant framing? What was omitted?]   │  │  │
│  │  │                                                               │  │  │
│  │  └───────────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  ┌── Primary Sources ───────────────────────────────────────────┐  │  │
│  │  │                                                               │  │  │
│  │  │  ┌ dispatch ──────────────────────────────────────────────┐  │  │  │
│  │  │  │ "The transfer of power was accomplished with dignity   │  │  │  │  ← IBM Plex Mono 300
│  │  │  │  and in accordance with the wishes of the people..."   │  │  │  │     typewriter voice
│  │  │  │                                                        │  │  │  │
│  │  │  │  — Mountbatten's address, Aug 15 1947                  │  │  │  │  ← Citation in Meta voice
│  │  │  └────────────────────────────────────────────────────────┘  │  │  │
│  │  │                                                               │  │  │
│  │  │  ┌ document ──────────────────────────────────────────────┐  │  │  │
│  │  │  │ [Annotated image of the Indian Independence Act 1947]  │  │  │  │  ← Document image with
│  │  │  │                                                        │  │  │  │     annotation pins
│  │  │  └────────────────────────────────────────────────────────┘  │  │  │
│  │  │                                                               │  │  │
│  │  └───────────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  │  ┌── Key Narratives & Omissions ────────────────────────────────┐  │  │
│  │  │                                                               │  │  │
│  │  │  EMPHASIZED:                                                  │  │  │
│  │  │  • Orderly transfer of power                                  │  │  │
│  │  │  • Democratic self-determination                              │  │  │
│  │  │                                                               │  │  │
│  │  │  OMITTED OR MINIMIZED:                                        │  │  │
│  │  │  • Arbitrary border drawing (Radcliffe Line)                  │  │  │
│  │  │  • Violence during mass migration                             │  │  │
│  │  │  • Bengal Famine of 1943                                      │  │  │
│  │  │                                                               │  │  │
│  │  └───────────────────────────────────────────────────────────────┘  │  │
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌─── Comparison Mode (toggle) ───────────────────────────────────────┐  │
│  │                                                                     │  │
│  │  British Perspective        │  Indian Perspective                   │  │  ← Split-screen comparison
│  │                             │                                       │  │
│  │  "Transfer of power"       │  "Freedom at midnight"                │  │  ← Same event, different
│  │                             │                                       │  │     vocabulary highlighted
│  │  "Partition was necessary   │  "Partition was the final wound      │  │
│  │   to prevent civil war"    │   of colonial rule"                   │  │
│  │                             │                                       │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌─── Media Gallery ──────────────────────────────────────────────────┐  │
│  │                                                                     │  │
│  │  [photo] [photo] [map] [document scan] [video clip]                │  │  ← Horizontal scroll gallery
│  │                                                                     │  │     each with archival grade
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌─── Timeline Context ───────────────────────────────────────────────┐  │
│  │                                                                     │  │
│  │  ◄ Suez Crisis (1956)    ──[YOU ARE HERE]──    Kashmir War (1947) ►│  │  ← Next/prev on timeline
│  │                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

### 2c. Timeline View — "The Corridor"

A dedicated page with the timeline as primary navigation. Think of it as walking down a long museum corridor with events mounted on the wall.

**Desktop:** Horizontal scrolling timeline. The center of the viewport is the "present" — scrolling left goes backward in time, right goes forward. Each event is a node that expands on hover to show a thumbnail and title. Clicking enters the event detail page.

**Above the timeline:** A context bar showing the current era, region filter, and total events visible.

**Below the timeline:** A narrative ribbon — a single-line teaser for the currently centered event. As the user scrolls, the ribbon updates.

**Visual treatment:** The timeline track itself is rendered as an SVG with irregular weight (thicker during periods of dense events, thinner during gaps) — like a seismograph or ECG trace that accelerates during moments of historical intensity.

### 2d. Map View — "The Cartographer's Desk"

An optional geographic entry point. A simplified world map (SVG, not a mapping library — consistent with void's no-library rule) with event pins. The map uses an intentionally archival cartographic style — muted land masses, thin border lines, no satellite imagery.

**Interaction:**
- Click a region to filter events to that geography
- Event pins are small circles in `--hist-accent` color
- Hover a pin for event title + year tooltip
- Click navigates to event detail page

**Visual treatment:** The map is drawn with thin strokes (1px) and filled with `--hist-bg-secondary`. Borders use dashed lines where contested. The overall effect is a map from a historical atlas, not Google Maps.

This view is supplementary, not primary. The era-based catalog and timeline are the main navigation paths.

### 2e. Gallery/Media View — "The Lightbox"

A full-screen media viewer for images, documents, and video clips. Invoked from within an event detail page when a user clicks any media item.

**Behavior:**
- Full-viewport overlay with dark backdrop (`--hist-bg-primary` dark at 92% opacity)
- Image/document centered with generous padding (museum-hanging proportion)
- Caption below in Meta voice (Barlow Condensed)
- Source citation in Archival voice (IBM Plex Mono)
- Left/right arrows for gallery navigation
- Close button top-right
- Pinch-to-zoom on mobile, scroll-to-zoom on desktop (for document detail)

**Image treatment:** All photographs receive `--hist-photo-grade` filter. An optional toggle switches between "as archived" (filtered) and "restored" (original color) where color images exist. This toggle is educational — it shows the reader how archival treatment shapes perception.

---

## 3. The Perspective UI — "The Rotating Lectern"

This is the most important design challenge and the place where void --history must innovate.

### 3a. Core Metaphor

Imagine a rotating lectern in a debate hall. One speaker presents their account. The lectern turns. Another speaker presents theirs. The audience (the reader) sees the same event from a different physical position in the room.

The UI must make switching perspectives feel like **turning to face a different speaker**, not like clicking a tab on a website.

### 3b. Perspective Selector

**Desktop (tab bar with physical presence):**

```
┌──────────────────────────────────────────────────────────────┐
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ ■ BRITISH   │  │ ■ INDIAN    │  │ ■ PAKISTANI │  ...    │
│  │   COLONIAL  │  │   NATIONAL  │  │   NATIONAL  │         │
│  │             │  │             │  │             │         │
│  │  1858-1947  │  │  1947-      │  │  1947-      │         │  ← Each tab shows the
│  │  London     │  │  Delhi      │  │  Karachi    │         │     perspective's temporal
│  └─────────────┘  └─────────────┘  └─────────────┘         │     and geographic anchor
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

Each perspective tab is a small card (not a flat text tab) with:
- A colored left border (perspective color from the spectrum)
- The perspective name in Meta voice (Barlow Condensed, uppercase)
- A temporal anchor (when this perspective was dominant)
- A geographic anchor (where this perspective originates)
- Active state: elevated with `--shadow-cinematic-ambient`, archival accent border glow

**Mobile (horizontal scroll pills with swipe):**

Horizontal scrollable row of perspective pills. Active pill is filled with perspective color at 12% opacity. Swipe between perspectives with a gesture that feels like turning a page — the outgoing perspective slides left and fades, the incoming slides in from right.

### 3c. Perspective Switching Animation

When switching perspectives, the content does not simply swap. It **turns**.

**The Lectern Turn:** The outgoing perspective content rotates slightly (2-3 degrees around Y axis) while fading to 0 opacity, as if the lectern is turning away. A 60ms pause (the "beat" — the silence between speakers). Then the incoming perspective content rotates in from the opposite direction. Total duration: 450ms.

```css
/* Outgoing */
@keyframes perspectiveOut {
  0%   { transform: perspective(800px) rotateY(0deg); opacity: 1; }
  100% { transform: perspective(800px) rotateY(-4deg); opacity: 0; filter: blur(1px); }
}

/* Incoming */
@keyframes perspectiveIn {
  0%   { transform: perspective(800px) rotateY(4deg); opacity: 0; filter: blur(1px); }
  100% { transform: perspective(800px) rotateY(0deg); opacity: 1; filter: blur(0); }
}
```

Under `prefers-reduced-motion`: simple crossfade, 0ms.

### 3d. Split-Screen Comparison Mode

A toggle at the top of the perspective section activates **comparison mode** — two perspectives displayed side by side.

**Desktop:** True 50/50 split with a vertical divider. Each side independently scrollable. A thin divider line in `--hist-divider` separates them. The divider is draggable to adjust the split ratio (40/60, 50/50, 60/40).

**Mobile:** Vertical stack with clear visual separation (a horizontal rule with the perspective name on each side). Or: a swipe-comparison mode like "before/after" image sliders — the divider is a vertical line that the user drags left/right to reveal more of one perspective vs. the other.

**Highlighting differences:** When in comparison mode, key vocabulary differences are highlighted:
- Words unique to Perspective A get a subtle blue underline
- Words unique to Perspective B get a subtle sienna underline
- The same event described with different vocabulary becomes visually scannable

### 3e. "Emphasized vs. Omitted" — Making Narrative Bias Visible

Each perspective includes a structured section: **"Key Narratives & Omissions."**

**Visual treatment:**

| Category | Visual | Color |
|----------|--------|-------|
| **Emphasized** | Bullet with filled circle | `--hist-perspective-[x]` at 80% opacity |
| **Omitted or Minimized** | Bullet with hollow circle + strikethrough rule behind text | `--hist-fg-muted` with 40% opacity |
| **Disputed** | Bullet with half-filled circle | Split between two perspective colors |

This is the void --history equivalent of void --news's BiasLens — a structured, visual way to see what each narrative includes and excludes. The pattern:

```
EMPHASIZED:                           OMITTED OR MINIMIZED:
● Orderly transfer of power           ○ ̶A̶r̶b̶i̶t̶r̶a̶r̶y̶ ̶b̶o̶r̶d̶e̶r̶ ̶d̶r̶a̶w̶i̶n̶g̶
● Democratic self-determination        ○ ̶V̶i̶o̶l̶e̶n̶c̶e̶ ̶d̶u̶r̶i̶n̶g̶ ̶m̶i̶g̶r̶a̶t̶i̶o̶n̶
● Gradual devolution of power          ○ ̶B̶e̶n̶g̶a̶l̶ ̶F̶a̶m̶i̶n̶e̶ ̶o̶f̶ ̶1̶9̶4̶3̶
```

The strikethrough on omitted items is a deliberate design choice — it makes absence visible. It says: this happened, but this perspective chose not to tell it.

### 3f. Narrative Overlap Indicator

At the top of the perspective section, a small visual shows where perspectives **agree** and where they **diverge**.

```
Agreement Spectrum:
████████░░░░░░░░░░░░  35% overlap
        ▲
   British + Indian agree on timeline, disagree on causation
```

This is analogous to void --news's consensus/divergence pattern but applied to historical narratives instead of media coverage.

---

## 4. Motion & Interaction — "The Documentary Camera"

### 4a. Cinematic Language

void --news uses cinema (Deakins, Lubezki, Kubrick). void --history uses **documentary filmmaking** (Ken Burns, Frederick Wiseman, Adam Curtis) — a related but distinct visual grammar.

| Documentary Technique | UI Implementation | Where Used |
|----------------------|-------------------|------------|
| **Ken Burns Effect** | Slow zoom + pan on archival photographs (CSS `scale` + `translate` over 8-12s) | Hero images, gallery view, event header |
| **Cross-Dissolve** | Opacity crossfade between perspectives (300ms) | Perspective switching fallback |
| **Interstitial Card** | Brief text card between content sections (centered, smaller type) | Transitions between perspectives, section breaks |
| **Talking Head Frame** | Centered primary source quote with generous margin | Pull quotes from historical figures |
| **B-Roll Pan** | Slow horizontal translate on background images while text scrolls | Parallax on event detail page background image |
| **Iris Wipe** | Circular reveal from center (clip-path animation) | Timeline node click → event detail page transition |

### 4b. Scroll-Driven Storytelling

The event detail page is a scrollytelling experience. As the user scrolls:

1. **Hero image** Ken Burns zooms slowly
2. **Context panel** fades up with a document-unfolding feel (translateY + opacity, 300ms stagger)
3. **Perspective tabs** appear with a typewriter-stagger (each tab appears 80ms after the previous)
4. **Active perspective content** is revealed section by section (narrative, then primary sources, then omissions)
5. **Media gallery** slides in from below
6. **Timeline context** (next/prev events) appears last

Each section's reveal is triggered by IntersectionObserver at 20% visibility threshold — identical to void --news's about page pattern. No forced auto-scroll.

### 4c. Map Interactions

If the map view is included:
- **Region hover:** Land mass subtly brightens (`filter: brightness(1.08)`), event pins in that region pulse
- **Pin click:** Iris wipe transition to event detail page (CSS `clip-path: circle()` expanding from pin position)
- **Zoom:** Scroll-driven zoom with momentum (not pinch — this is CSS transform, not a map library)

### 4d. Timeline Scrubbing

The compact timeline supports:
- **Drag to scrub:** Grab the timeline and drag horizontally. The current era label updates in real time. This is CSS scroll-snap with `scroll-behavior: smooth`.
- **Node hover:** Event title appears in a tooltip above the node
- **Node click:** Navigate to event detail page
- **Era indicators:** Background color bands (very subtle, 3-4% opacity) mark era boundaries on the timeline

### 4e. Spring Presets

Same spring system as void --news, but with different semantic naming:

| Preset | Physics | Use |
|--------|---------|-----|
| **archive-snap** | stiffness 600, damping 35 | Tab selection, drawer open/close |
| **document-settle** | stiffness 280, damping 22 | Page transitions, image settling after Ken Burns |
| **lectern-turn** | stiffness 200, damping 18, mass 1.1 | Perspective switching |
| **unfold** | stiffness 150, damping 14, mass 1.2 | Drawer expansion, timeline expansion |

### 4f. Reduced Motion

All Ken Burns, parallax, perspective rotation, iris wipe, and stagger animations disabled. Content appears immediately. Perspective switching becomes instant opacity swap. Timeline scrub still works (it's functional, not decorative).

---

## 5. Component Inventory

### 5a. New Components (void --history specific)

| Component | Purpose | Key Details |
|-----------|---------|-------------|
| `HistoryLanding.tsx` | Archive index page | Era drawers, featured events, region filter, compact timeline |
| `EraDrawer.tsx` | Collapsible era section | Drawer metaphor, event cards inside, unfold animation |
| `EventCard.tsx` | Event preview card | Thumbnail, title, year, region, perspective count |
| `EventDetail.tsx` | Full event dossier | Hero, context, perspectives, gallery, timeline nav |
| `PerspectiveSelector.tsx` | Tab-style perspective nav | Colored tabs with temporal/geographic anchors |
| `PerspectiveView.tsx` | Single perspective content | Narrative, primary sources, omissions |
| `PerspectiveComparison.tsx` | Split-screen comparison | Draggable divider, vocabulary highlighting |
| `NarrativeOverlap.tsx` | Agreement/divergence indicator | Spectrum bar showing perspective overlap |
| `PrimarySourceBlock.tsx` | Typewritten source quote | IBM Plex Mono 300, laid paper texture, citation |
| `DocumentViewer.tsx` | Annotated document/image | Zoom, annotation pins, archival grade filter |
| `ArchivalGallery.tsx` | Horizontal media scroll | Images, documents, maps, video with grade filters |
| `Lightbox.tsx` | Full-screen media viewer | Zoom, caption, citation, gallery navigation |
| `HistoryTimeline.tsx` | Full-page horizontal timeline | Scroll-snap, era bands, node tooltips |
| `CompactTimeline.tsx` | In-page timeline navigation | Event nodes, current position indicator, next/prev |
| `MapView.tsx` | SVG world map with event pins | Region highlighting, pin tooltips, iris wipe transition |
| `KeyFacts.tsx` | Structured fact block | Date, location, actors, statistics in Archival voice |
| `OmissionsPanel.tsx` | Emphasized vs. Omitted | Filled/hollow/strikethrough visual language |
| `HistoryTopbar.tsx` | Page header (no NavBar) | Back link, event title, share, theme toggle |
| `EraLabel.tsx` | Era/period indicator | Barlow Condensed, small pill with era name and date range |
| `HistoryFooter.tsx` | Site footer | "void --history" branding, link back to void --news |

### 5b. Adapted from void --news

| void --news Component | void --history Adaptation |
|----------------------|--------------------------|
| `ThemeToggle.tsx` | Reused directly — same light/dark toggle |
| `LogoFull.tsx` / `LogoIcon.tsx` | Reused — same void logo, different page chrome |
| `LoadingSkeleton.tsx` | Adapted — skeleton shapes match document cards, not story cards |
| `ErrorBoundary.tsx` | Reused directly |
| Film grain/vignette pattern | Adapted — foxing texture instead of film grain, tighter vignette |
| `DeepDiveSpectrum.tsx` pattern | Adapted for `NarrativeOverlap.tsx` — same gradient bar concept |
| About page IO pattern | Reused — same IntersectionObserver scroll-driven reveal system |
| Weekly page topbar pattern | Reused — `.wk-topbar` approach for `.hist-topbar` (no NavBar) |

### 5c. Image Presentation Components (detailed)

**FullBleedHero:** Event header image. 100vw width, 50vh height (desktop) / 40vh (mobile). Ken Burns animation (8s). Dark gradient overlay at bottom for title legibility. `--hist-photo-grade` filter. Object-fit: cover.

**AnnotatedDocument:** An image of a historical document with interactive annotation pins. Each pin is a small circle (12px) in `--hist-accent`. Hovering/tapping a pin reveals a callout with explanatory text. Pins are positioned with percentage-based coordinates so they scale with the image.

**ComparisonSlider:** Before/after style slider for comparing two images (e.g., a city before and after a bombing, or the same map drawn by two different empires). Vertical divider that the user drags. Each side labeled with source/date.

**MapOverlay:** An archival map (static SVG or image) with a semi-transparent modern map overlaid for context. Opacity slider to blend between historical and modern views.

---

## 6. Responsive Strategy

### 6a. Desktop (1024px+) — "The Exhibition"

- Multi-column layouts for comparison mode (true 50/50 split)
- Full-bleed hero images at 50vh
- Horizontal timeline with scroll-snap
- Era drawers expand in-place
- Gallery uses horizontal scroll
- Map view at full width
- Perspective tabs as cards (not pills)

### 6b. Tablet (768px-1023px) — "The Catalog"

- Comparison mode stacks to 100%/100% with clear divider
- Hero images at 40vh
- Timeline maintains horizontal scroll but with larger touch targets (48px nodes)
- Era drawers use same expand behavior
- Gallery maintains horizontal scroll
- Map view at full width but simplified (fewer labels)
- Perspective tabs as compact pills in horizontal scroll

### 6c. Mobile (375px-767px) — "The Field Journal"

- Everything single-column
- Hero images at 35vh
- **Swipe between perspectives** (horizontal gesture, CSS scroll-snap)
- Comparison mode becomes a "swipe slider" (before/after style) or vertical stack with perspective headers
- Timeline becomes vertical (chronological top-to-bottom)
- Era drawers are the primary navigation (fullscreen feel)
- Gallery uses full-width horizontal scroll with peek
- Map view simplified to region list (SVG map too dense for small screens)
- Bottom navigation for key actions: Archive, Timeline, Share
- Touch targets 48px minimum (larger than void --news's 44px — history content is less dense, more contemplative)

### 6d. Content Density

| Element | Desktop | Tablet | Mobile |
|---------|---------|--------|--------|
| Perspectives visible | All tabs visible | Scrollable tabs | Swipeable, one at a time |
| Primary sources | Expanded inline | Expanded inline | Collapsed behind "View source" |
| Key facts | Sidebar on right | Below hero | Below hero, collapsible |
| Media gallery | Horizontal scroll, 4 visible | 3 visible | 2 visible with peek |
| Omissions panel | Expanded | Expanded | Collapsed behind toggle |
| Timeline | Horizontal, always visible | Horizontal, sticky bottom | Vertical, separate page |

---

## 7. Inspiration & References

### 7a. Web References

| Reference | What to Take | What to Avoid |
|-----------|-------------|---------------|
| **The Pudding** (pudding.cool) | Scrollytelling execution, data-driven narratives, visual density | Playful tone — void --history is more serious |
| **NYT "1619 Project"** | Long-form historical narrative, pull quotes, archival imagery integration | The political framing — void --history is multi-perspective |
| **BBC History Extra** | Accessible historical writing, clean typography | Generic web design — no distinctive visual identity |
| **The Guardian "NSA Files"** | Interactive document presentation, progressive disclosure, annotation | Complex interaction patterns that don't work on mobile |
| **Reuters "Wider Image"** | Full-bleed photography, minimal chrome, story through images | Single-narrative approach |
| **Apple TV+ "For All Mankind" site** | Alternate history visual language, cinematic web presentation | Fiction — void --history is documented fact |
| **Google Arts & Culture** | Museum exhibition design adapted for web, zoomable documents | Generic Google Material design language |
| **Bloomberg "CityLab"** | Map-driven journalism, geographic data storytelling | Dashboard density — too much for contemplative history |

### 7b. Museum Exhibition Design Principles

1. **The 3-Second Rule:** A visitor decides in 3 seconds whether to engage with an exhibit. The hero image + title must be that compelling.
2. **Layered Information:** Headline (2 seconds), placard (20 seconds), full text (2 minutes), interactive (5+ minutes). Same progressive disclosure as void --news, but the layers are: event title, context summary, perspective narrative, primary sources.
3. **Spatial Organization:** Related items near each other. Contradicting items facing each other (like our split-screen comparison). Context on the walls, detail in the drawers.
4. **Controlled Lighting:** Museum galleries use directed light to create focus. Our `--hist-vignette` (desk lamp circle) does this digitally.
5. **White Space as Respect:** History content needs breathing room. Dense grids trivialize serious events. Generous margins say "this matters, take your time."

### 7c. Documentary Filmmaking Visual Language

| Technique | Film Example | void --history Equivalent |
|-----------|-------------|--------------------------|
| Ken Burns pan/zoom | *The Civil War* (1990) | Hero image slow zoom + pan |
| Archival footage grade | *They Shall Not Grow Old* (2018) | `--hist-photo-grade` filter + optional "restored" toggle |
| Interstitial cards | *The Act of Killing* (2012) | Text cards between perspective sections |
| Talking head composition | *Shoah* (1985) | Centered primary source quotes |
| Split screen | *Conversations with a Killer* (2019) | Perspective comparison mode |
| Timeline scroll | *Adam Curtis — HyperNormalisation* | Horizontal timeline scrub |

---

## 8. Data Architecture (Preliminary)

### 8a. Content Model

Each event needs:

```typescript
interface HistoricalEvent {
  id: string;
  slug: string;                          // URL-friendly: "partition-of-india-1947"
  title: string;                         // "The Partition of India"
  year: number;                          // 1947
  date_range: string;                    // "August 14-15, 1947"
  era: Era;                              // "cold-war-decolonization"
  regions: Region[];                     // ["south-asia"]
  context_summary: string;               // Neutral 200-300 word summary
  key_facts: KeyFact[];                  // Structured facts
  perspectives: Perspective[];           // 3-6 perspectives
  media: MediaItem[];                    // Images, documents, maps, video
  timeline_neighbors: {                  // For next/prev navigation
    before: string | null;               // Slug of previous event
    after: string | null;                // Slug of next event
  };
  featured: boolean;                     // Show on landing page
}

interface Perspective {
  id: string;
  name: string;                          // "British Colonial"
  color_key: 'a' | 'b' | 'c' | 'd' | 'e';  // Maps to --hist-perspective-[x]
  geographic_anchor: string;             // "London"
  temporal_anchor: string;               // "1858-1947"
  narrative: string;                     // 500-800 word long-form narrative
  primary_sources: PrimarySource[];
  emphasized: string[];                  // Key narratives this perspective stresses
  omitted: string[];                     // What this perspective minimizes
  disputed: DisputedClaim[];             // Claims where perspectives disagree
}

interface PrimarySource {
  type: 'dispatch' | 'document' | 'speech' | 'diary' | 'official' | 'newspaper';
  text: string;                          // The quoted text
  author: string;                        // "Lord Mountbatten"
  date: string;                          // "August 15, 1947"
  source_name: string;                   // "Address to the Constituent Assembly"
  image_url?: string;                    // Optional document scan
}

interface MediaItem {
  type: 'photo' | 'document' | 'map' | 'video';
  url: string;
  caption: string;
  source: string;                        // Attribution
  date: string;
  perspective_id?: string;               // If media belongs to a specific perspective
  annotations?: Annotation[];            // For document viewer pins
}

type Era =
  | 'antiquity-medieval'
  | 'early-modern'
  | 'long-nineteenth-century'
  | 'world-wars'
  | 'cold-war-decolonization'
  | 'contemporary';

type Region =
  | 'asia'
  | 'africa'
  | 'europe'
  | 'americas'
  | 'middle-east'
  | 'global';
```

### 8b. Storage

**Option A — Static JSON (preferred for launch):** All 50 events as JSON files in `frontend/app/history/data/`. No database. Aligns with void --news's static export architecture. Content is editorial-curated, not pipeline-generated.

**Option B — Supabase (future):** If events grow beyond 50 or if community contributions are added, migrate to Supabase with `historical_events`, `perspectives`, `primary_sources`, and `media` tables.

### 8c. Routing

```
/history                    → Landing page (Archive Index)
/history/timeline           → Full timeline view
/history/map                → Map view
/history/[slug]             → Event detail page
/history/[slug]?p=[id]      → Event detail with specific perspective pre-selected
/history/[slug]?compare=a,b → Event detail in comparison mode
```

---

## 9. Accessibility

### 9a. Screen Reader Strategy

- **Perspectives:** Each perspective tab has `role="tab"`, the perspective content has `role="tabpanel"`. `aria-selected` on active tab. `aria-controls` linking tab to panel.
- **Timeline:** `role="slider"` with `aria-valuemin` (earliest year), `aria-valuemax` (latest year), `aria-valuenow` (current position), `aria-valuetext` ("1947, The Partition of India").
- **Gallery:** `role="region"` with `aria-label="Media gallery"`. Each item focusable with descriptive `aria-label`.
- **Comparison mode:** `aria-live="polite"` region that announces which perspectives are being compared.
- **Ken Burns animation:** Purely decorative — does not convey information. `aria-hidden="true"` on animation layer; static image remains accessible.
- **Omissions panel:** Strikethrough text is visual only. Screen readers get: "Omitted: Arbitrary border drawing. Omitted: Violence during mass migration." No CSS text-decoration reliance for meaning.

### 9b. Keyboard Navigation

- **Perspective tabs:** Arrow keys to navigate between tabs. Enter/Space to select. Home/End for first/last.
- **Timeline:** Arrow keys to move between events. Enter to select. Home/End for first/last era.
- **Gallery:** Arrow keys to navigate items. Enter to open lightbox. Escape to close.
- **Comparison mode:** Tab to move between panels. `Ctrl+[` and `Ctrl+]` to adjust divider position.
- **Era drawers:** Enter/Space to toggle. Arrow down enters drawer contents.
- **Lightbox:** Arrow keys for previous/next. Escape to close. Focus trapped inside.

### 9c. Contrast

All color combinations verified at 4.5:1 minimum (WCAG AA). The perspective colors (`--hist-perspective-*`) are used as border/indicator colors only, never as text colors on backgrounds. Text remains in the `--hist-fg-*` system.

---

## 10. What "Screams History" — The Signature Moments

These are the five moments where a user should viscerally feel "this is different from void --news."

1. **The First Photograph:** When the event detail page loads, the hero image fills the viewport with a Ken Burns zoom. The `--hist-photo-grade` filter gives it archival weight. The title appears in Playfair Display over a dark gradient. The foxing texture on the page background is visible at the edges. This is not a news article. This is a document being opened.

2. **The Typewriter Quote:** When a primary source block appears, the text is in IBM Plex Mono at weight 300 with slightly increased spacing. The container has a laid-paper texture. A thin left border in the perspective's color. A citation beneath in Barlow Condensed. It feels like reading a transcribed dispatch.

3. **The Lectern Turn:** When switching perspectives, the content rotates on the Y axis. The reader physically senses "turning to face another speaker." The 60ms beat of silence between perspectives is palpable.

4. **The Strikethrough:** When reading the omissions panel, the items that a perspective chose to minimize appear with a visual strikethrough. The omission is present on the page, but struck through — making absence tangible. This is the void --history equivalent of the BiasLens.

5. **The Split Screen:** When comparison mode activates, two perspectives sit side by side with vocabulary differences highlighted. The same event, told with different words, visible in the same viewport. The draggable divider makes the reader an active participant in deciding how much weight to give each side.

---

## 11. Anti-Slop Checklist (void --history Specific)

Every void --history component must pass:

- [ ] Would NOT be mistaken for a Wikipedia article or generic history site
- [ ] Would NOT be mistaken for a void --news news article (different textures, different palette, different motion)
- [ ] Uses correct type voice: Playfair (editorial titles), Inter (narrative body), IBM Plex Mono 300 (primary sources), Barlow Condensed (era/region labels)
- [ ] All colors from `--hist-*` custom properties, never hardcoded
- [ ] Perspective colors used ONLY on perspective indicators (borders, dots), never decoration
- [ ] Archival textures (foxing, laid paper) used on appropriate surfaces, not everywhere
- [ ] Works in "Reading Room" (light) and "Conservation Lab" (dark) modes
- [ ] Responsive 375px-1440px with correct layout at each breakpoint
- [ ] Touch targets >= 48px on mobile (larger than void --news — more contemplative pacing)
- [ ] Spring physics for user actions, documentary ease-out for reveals
- [ ] Ken Burns animation on `prefers-reduced-motion: reduce` → static image
- [ ] All animations disabled under `prefers-reduced-motion`
- [ ] Semantic HTML with ARIA for perspective tabs, timeline, gallery
- [ ] Focus management for lightbox, comparison mode, perspective switching
- [ ] Primary source text: `font-family: var(--font-data); font-weight: 300; letter-spacing: 0.02em`
- [ ] Body narrative: `text-align: justify; hyphens: auto; line-height: 1.7`
- [ ] No `!important`, no hardcoded px for typography/spacing

---

## 12. Relationship to void --news

### 12a. What They Share

- The void logo (same `LogoFull`, `LogoIcon` components)
- The CLI naming convention (`void --history`)
- The ThemeToggle component
- The four-font type system (same families, different usage weights)
- The spring physics animation engine (Motion One)
- The IntersectionObserver scroll-driven reveal pattern
- The topbar-without-NavBar pattern (from void --weekly)
- The film grain/texture overlay pattern (different texture, same technique)
- The vignette pattern (different shape, same technique)
- The `prefers-reduced-motion` discipline
- Error boundaries and loading skeletons (adapted shapes)

### 12b. What Is Completely Different

| Dimension | void --news | void --history |
|-----------|-------------|---------------|
| Color temperature | Warm amber / ochre | Cooled sepia / archival neutral |
| Accent color | Ochre gold `#946B15` | Archival stamp red `#8B2E2E` |
| Texture | Film grain (cinema) | Foxing + laid paper (archive) |
| Vignette | Elliptical (wide screen) | Circular (desk lamp) |
| Color grade | Cinematic (contrast + saturation) | Archival (desaturation + sepia) |
| Motion language | Cinema (whip pan, rack focus, dolly) | Documentary (Ken Burns, cross-dissolve, iris wipe) |
| Content model | Pipeline-generated (3x daily) | Editorially curated (static) |
| Data density | High (scores, sources, axes) | Lower (narrative, images, quotes) |
| Interaction pace | Fast (news is urgent) | Slow (history is contemplative) |
| Layout | Newspaper grid | Museum exhibition / scrollytelling |
| Navigation | Top nav + bottom nav | Topbar + era drawers + timeline |
| Primary visual | BiasLens (beam, ring, prism) | Perspective tabs + omissions |

### 12c. Cross-Navigation

The void --news NavBar "Pages" row includes a link to void --history (if hosted as a sub-path) or an external link (if hosted separately). void --history's topbar includes a "void --news" link back. The two products are siblings, not parent-child.

---

## 13. Technical Constraints

- **$0 budget.** No mapping libraries (Mapbox, Leaflet). SVG map hand-drawn or adapted from public domain.
- **Static export.** All content compiled at build time. No server-side rendering of historical data.
- **No image hosting costs.** All archival images either public domain (Library of Congress, National Archives, Wikimedia Commons) or credited under fair use for educational commentary.
- **Same tech stack.** Next.js 16, React 19, TypeScript, CSS custom properties, Motion One via CDN.
- **CSS load order.** void --history styles added as `history.css` at the end of the global import chain. All styles scoped to `.hist-page` or `.hist-*` namespace to prevent bleed into void --news.
- **Max bundle impact.** History is a separate route tree (`/history/*`). Components are code-split. The main void --news bundle is not affected.

---

## 14. The 50 Events (Initial Curation Scope)

Curated for geographic diversity, temporal range, and narrative complexity (events where multiple perspectives exist and meaningfully diverge).

### Antiquity & Medieval (pre-1500)
1. Fall of Constantinople (1453)
2. Mongol Siege of Baghdad (1258)
3. The Crusades — Fall of Jerusalem (1099)
4. Viking Settlement of Vinland (~1000 CE)

### Early Modern (1500-1800)
5. Spanish Conquest of the Aztec Empire (1519-1521)
6. Atlantic Slave Trade — Middle Passage (1500s-1800s)
7. American Revolution (1775-1783)
8. French Revolution (1789-1799)
9. Haitian Revolution (1791-1804)
10. Captain Cook's Arrival in Australia (1770)
11. Mughal-Maratha Wars (1680-1707)
12. The Boston Tea Party and Taxation Debates (1773)

### The Long 19th Century (1789-1914)
13. Napoleonic Wars — Battle of Waterloo (1815)
14. Indian Rebellion of 1857
15. American Civil War (1861-1865)
16. Scramble for Africa — Berlin Conference (1884-1885)
17. Opium Wars (1839-1842, 1856-1860)
18. Meiji Restoration (1868)
19. Armenian Genocide (1915-1923)
20. Boxer Rebellion (1899-1901)
21. Russo-Japanese War (1904-1905)
22. Irish Great Famine (1845-1852)

### World Wars (1914-1945)
23. Assassination of Archduke Franz Ferdinand (1914)
24. Battle of Gallipoli (1915-1916)
25. Russian Revolution (1917)
26. Treaty of Versailles (1919)
27. Rise of Fascism — March on Rome (1922)
28. Nanjing Massacre (1937)
29. The Holocaust (1941-1945)
30. Atomic Bombings of Hiroshima and Nagasaki (1945)
31. D-Day — Normandy Landings (1944)
32. Bengal Famine (1943)
33. Battle of Stalingrad (1942-1943)
34. Japanese Internment in the US (1942-1945)

### Cold War & Decolonization (1945-1991)
35. Partition of India (1947)
36. Creation of Israel / Nakba (1948)
37. Korean War (1950-1953)
38. Cuban Missile Crisis (1962)
39. Vietnam War — Tet Offensive (1968)
40. Rwandan Genocide (1994)
41. Fall of the Berlin Wall (1989)
42. Tiananmen Square (1989)
43. Iranian Revolution (1979)
44. Apartheid — Soweto Uprising (1976)

### Contemporary (1991-present)
45. Dissolution of the Soviet Union (1991)
46. September 11 Attacks (2001)
47. Iraq War — "Weapons of Mass Destruction" (2003)
48. Arab Spring — Egyptian Revolution (2011)
49. Annexation of Crimea (2014)
50. COVID-19 Pandemic — Origin Narratives (2019-2020)

---

## 15. Open Questions

1. **Audio component?** Should void --history have narrated versions of perspectives? A "void --onair" for history? (Possible: re-use TTS infrastructure from void --news daily briefs. Each perspective narrated as a separate track.)

2. **User-generated perspectives?** Should there be a mechanism for readers to submit perspectives or primary sources? (Probably not for v1 — editorial curation maintains quality. But the data model should not preclude it.)

3. **Cross-linking with void --news?** When a current news event relates to a historical event (e.g., Israel-Palestine coverage linking to 1948 Nakba), should there be a "Historical Context" card in void --news that links to void --history? (Strong yes for v2.)

4. **Search?** Full-text search across all 50 events, perspectives, and primary sources? (Yes for v1 — simple client-side search over static JSON. The data set is small enough.)

5. **Print stylesheet?** Given the archival nature, a well-designed print stylesheet could be valuable — users printing event dossiers for educational use. (Nice-to-have for v1.)

---

*This specification is a creative brief. No code has been written. It requires CEO approval before implementation begins.*

*Next step: CEO review and approval of visual identity, page architecture, and perspective UI. Then: component engineering begins.*
