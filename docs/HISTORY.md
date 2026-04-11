# void --history — The Archive

Last updated: 2026-04-10 (rev 4)

> Full spec for the multi-perspective historical events platform.
> Only read when working on history-related files.

**Thesis:** History is not what happened. History is who told the story.

## Architecture

- **Organic ink timeline** (horizontal desktop, vertical mobile) at `/history`
- **8-stage museum journey** — no page navigation from landing; EventDetail renders below compressed timeline strip
- **58 events**, sqrt temporal spacing, above/below severity placement (catastrophic above, critical/major below)
- **290 perspectives** across all events, 6 viewpoint types
- **448 media items** (images, maps, documents, artwork, video)
- **197 cross-event connections**
- **4 Supabase tables** + Supabase Storage for mirrored media
- **Mock data fallback** when Supabase unavailable

Routes: `/history` (organic ink timeline), `/history/[slug]` (event detail), `/history/era/[era]`, `/history/region/[region]`.

## Design System — "Archival Cinema"

### Palette

| Token | Light | Dark | Purpose |
|-------|-------|------|---------|
| `--hist-accent` | `#5C4033` | `#A8806C` | Burnt umber — primary accent |
| `--hist-brass` | `#9B7A2F` | `#B08D3A` | Aged brass — secondary accent |
| `--hist-paper` | `#F2EDE0` | `#1E1A16` | Foxed vellum / archival charcoal |
| `--hist-ink` | `#2C2418` | `#E8E0CF` | Iron gall ink |
| `--hist-persp-{a-e}` | 5 perspective colors | inverted | Per-perspective identity |

### Typography

Same 4 voices as main site: Playfair Display (editorial), Inter (structural), Barlow Condensed (meta), IBM Plex Mono (data).

### Cinematographic Framing Principles (7 mandatory)

1. **Arrive Late, Leave Early** — enter every scene at the last possible moment, cut when the point lands
2. **Show, Don't Tell** — juxtapose concrete facts, never assert significance. No didactic section labels in EventDetail.
3. **Progressive Disclosure** — crack hooks, then record, then context, then perspectives unfold (museum vitrine: one argument visible, rest behind expand)
4. **Witness Focus** — when a new perspective scrolls into view, dim previous witnesses
5. **Parallax Depth** — era gradient bands scroll at different speed than cards
6. **Organic Line** — SVG ink track wobbles organically, never straight
7. **Severity Placement** — catastrophic events above the timeline, others below

### Animation Performance (current timings)

| Animation | Duration | Notes |
|-----------|----------|-------|
| Hero cold open | 150ms fade | Content visible immediately, no stagger delays |
| Scroll reveal | 300ms | `translateY(12px) -> 0`, `--ease-cinematic` |
| Card entrance | 300ms | Filter + transform transitions, no scale |
| Witness dimming | via IntersectionObserver | 30% threshold, `hist-witness--background` class |

### Topbar

**No NavBar** — uses its own sticky topbar (`.hist-topbar`) with back link + ThemeToggle (mirrors Weekly pattern). No MobileBottomNav.

### Stylesheet

`history.css` (~8,600 lines, `.hist-page` namespace). Full Archival Cinema implementation: palette tokens, timeline layout, card system, stage transitions, witness blocks, perspective colors, evidence gallery, Ken Burns parallax, era bands, fun facts, record block (chisel-grain texture), omissions toggle, dossier cards, thread stages, responsive breakpoints.

## Storytelling Rules

### Show Not Tell (Fiction Writing)
All generated text must embody show-don't-tell. Present evidence, let the reader conclude.

**BAD:** "The Partition of India was a complex historical process..."
**GOOD:** "A lawyer who'd never been to India drew the border in five weeks. 15 million crossed it."

### Arrive Late, Leave Early (Screenplay)
Enter every scene at the last possible moment. Exit before the conclusion is spelled out. The user's brain completes the story. These two rules together create the cognitive gap where understanding happens.

## 5-Lens Historiographic Framework

Every perspective is analyzed across 5 lenses:

| Lens | What It Measures |
|------|-----------------|
| **Geographic/National** | Where the narrator stands — which capital, which border |
| **Social Position** | Class, caste, ethnicity, gender of the narrator |
| **Temporal Frame** | When written — contemporary account vs. 50-year retrospective |
| **Causal Emphasis** | What each side says caused the event |
| **Evidentiary Base** | What sources each side cites — archives, oral history, state records |

### Viewpoint Types

`victor`, `vanquished`, `bystander`, `academic`, `revisionist`, `indigenous`

## Timeline Landing — HistoryLanding.tsx (~1,482 lines)

### Layout

- **Organic SVG ink track** at vertical center, proportionate sqrt temporal spacing
- **Cards above** (catastrophic severity) / **below** (critical/major) the track
- **Collision resolution**: minimum gap enforcement, side-flipping for overlaps
- **PosterImage**: robust fallback chain (heroImage -> media[0] -> ... -> gradient)

### Era System

- 6 eras: Ancient, Classical, Medieval, Early Modern, Modern, Contemporary
- **Fixed era header**: label, years, description, color — updates as scroll position changes
- **Fast-travel buttons**: jump to era boundaries
- **Era flash**: color flash on era boundary crossing
- **Fun facts**: ephemeral context between events (9 curated facts positioned at midpoints)

### Inline Story Loading (State B)

When user clicks a card:
1. Timeline compresses to a floating "Back to Timeline" strip at top
2. EventDetail renders inline below the strip
3. No page navigation, no overlay, no router push
4. Back button restores full timeline, scrolls to previous card

### Desktop vs Mobile

- **Desktop** (>=768px): horizontal scroll, edge-scroll zones, parallax background, keyboard arrows
- **Mobile** (<768px): vertical timeline, ink track on left, tap to open
- Starts at 1945 (contemporary era) on load

## Story Page — EventDetail.tsx (8 Stages, ~826 lines)

No didactic section labels anywhere. Show Don't Tell applied throughout -- the content speaks for itself.

### Stage 1 — HERO (Arrive Late)
Full-viewport hero image, 150ms fade cold open (content visible immediately, no stagger delays). Date, title, subtitle overlay. Hero attribution.

### HistoryAudioCue (between Hero and Crack)
void --onair companion audio. Renders only when `audioUrl` is present on the event. Shows perspective count, duration. `HistoryAudioCue.tsx` component.

### Stage 2 — CRACK (Show Not Tell)
One fact that breaks the textbook. Single blockquote. Uses shared HOOKS from `hooks.ts` (58 event-specific hooks).

### Stage 3 — RECORD (Merged Facts + Figures)
Aged-artifact block with chisel-grain SVG texture (`feTurbulence fractalNoise`, horizontal baseFrequency `0.01 0.65`). Key Facts and Key Figures merged into a single `dl` ledger -- all facts as equal-weight ruled rows (no pull stats tier). Figures separated by a mid-rule divider. Figure names link to Wikipedia when available. Born/died dates formatted (BCE for year <= 0).

### Stage 4 — CONTEXT (The Full Story)
Full narrative, paragraph-split on `\n`, first 2 paragraphs visible. `significance` rendered as pull-quote blockquote. `legacyPoints` rendered as `ul` in expanded section. Context image intercut after first paragraph (map priority). Expand/collapse toggle.

### Stage 5 — PERSPECTIVES (Museum Vitrine)
WitnessBlock components using museum vitrine model: identity (color dot + name + viewpoint type), ONE lead argument visible as blockquote. Remaining arguments + primary sources + narrative + disputed claims behind expand button showing `count` with directional arrow glyph. Alternating left/right on desktop, stacked on mobile. Witness background dimming on scroll focus. Archival image intercuts between every 2nd witness.

### Stage 6 — OMISSIONS (Toggle)
Mobile toggle between "stressed" and "ignored" views (button group with `aria-pressed`). Desktop: both panels visible. Per-perspective, color-coded. Omitted items use struck styling. Optional omission image intercut between panels.

### Stage 7 — EVIDENCE (Archival Gallery)
Alternating left/right image layout with captions and attributions. Supports video embeds (Internet Archive iframe with poster play button via `ArchivalVideo` sub-component). No didactic label.

### Stage 8 — EXIT (Leave Early)
No summary. When arc connections exist: dossier cards (top 3 connection-ranked events with hero image background, connection type glyph, hook text, CTA) + chronological link + thread stage list. Connection type glyphs: `caused` = down-arrow, `consequence`/`response-to` = up-arrow, `influenced`/`parallel` = centered-dot. Dossier card opacity transitions on scroll reveal. Fallback without connections: cliffhanger (next event hero thumb + hook + CTA). Final fallback: "Return to The Archive." Sidebar "Elsewhere, Meanwhile" margin notes when >= 2 parallel/consequence connections (desktop sticky, mobile accordion).

## Content — 58 Events

| Era | Events |
|-----|--------|
| Ancient (3) | Cyrus Cylinder (539 BCE), Peloponnesian War (431 BCE), Ashoka & Maurya Empire (268 BCE) |
| Classical (4) | Conquests of Alexander (334 BCE), Assassination of Caesar (44 BCE), Silk Road (2nd c. BCE-15th c. CE), Fall of Rome (476 CE) |
| Medieval (10) | Rise of Islam (610), The Crusades (1095), Khmer Empire (802), Mongol Empire (1206), Mali Empire / Mansa Musa (1235), Mongol Conquest of Baghdad (1258), Black Death (1346), Gutenberg (1440), Fall of Constantinople (1453), Ottoman Empire (1299) |
| Early Modern (7) | Kingdom of Kongo (1390), Columbian Exchange (1492), Transatlantic Slave Trade (1500), Fall of Tenochtitlan (1519), Inca Conquest (1438), Mughal Empire (1526), Haitian Revolution (1791) |
| Modern (15) | Industrial Revolution (1760), French Revolution (1789), Bolivarian Revolutions (1810), Trail of Tears (1830), Opium Wars (1839), Treaty of Waitangi (1840), Taiping Rebellion (1850), Meiji Restoration (1868), Scramble for Africa (1884), Congo Free State (1885), Armenian Genocide (1915), Russian Revolution (1917), Women's Suffrage (1848), Indian Independence Movement (1857), Holodomor (1932) |
| Contemporary (19) | Holocaust (1941), Hiroshima (1945), Partition of India (1947), Apartheid (1948), Israel/Nakba (1948), Korean War (1950), Bandung Conference (1955), Civil Rights Movement (1954), Cuban Missile Crisis (1962), Cultural Revolution (1966), Vietnam War (1955), Cambodian Genocide (1975), Iranian Revolution (1978), Berlin Wall (1989), Tiananmen Square (1989), Rwanda (1994), Congo Wars (1996), 9/11 & War on Terror (2001), Arab Spring (2010) |

All 58 have story-specific HOOKS (arrive-late one-liners) and CTAS in `hooks.ts`. Shared across HistoryLanding (timeline cards) and EventDetail (Stage 2 crack + Stage 8 exit).

## Data Model (Supabase)

### Tables

| Table | Purpose | Migration |
|-------|---------|-----------|
| `history_events` | Core event data (slug, title, era, region, severity, summary, key_figures JSONB) | 039 |
| `history_perspectives` | Per-event perspectives (viewpoint, narrative, emphasized[], omitted[], notable_quotes JSONB) | 039 |
| `history_media` | Images, maps, documents, artwork, video (source_url, attribution, license) | 039, 043 |
| `history_connections` | Cross-event links (event_a_id, event_b_id, connection_type, description) | 039 |

**Migration 039**: 4 history tables with constraints and indexes.
**Migration 043**: Expanded media constraints for Unsplash/Pexels licenses + artwork media type.
**Migration 045**: `audioUrl` and `audioDuration` columns on `history_events` for void --onair companion audio.

### Data Layer — `data.ts`

Supabase queries with mock data fallback. Functions:
- `fetchHistoryEvents()` — all published events with batch-fetched perspectives, media, connections (forward + reverse)
- `fetchHistoryEvent(slug)` — single event with full relations
- `fetchHistoryEventsByEra(era)` — listing (summary only, no full relations)
- `fetchHistoryEventsByRegion(region)` — listing
- `fetchRedactedEvents()` — always from mock data (currently empty)

### Types — `types.ts`

Core types: `HistoricalEvent`, `Perspective`, `MediaItem` (incl. `videoEmbedUrl`), `EventConnection`, `RedactedEvent`.
`HistoricalEvent` fields include: `significance?`, `legacyPoints?`, `audioUrl?`, `audioDuration?`.
`MediaItem` types: `image`, `map`, `document`, `artwork`, `video`.
Enums: `HistoryEra` (6), `HistoryRegion` (10), `HistoryCategory` (10), `Severity` (3), `ViewpointType` (6), `ConnectionType` (5), `PerspectiveColor` (5).
Arc types (future, CEO decision pending): `LongArcTopic`, `ArcPerspective`, `ArcChapter`, `ArcChapterPerspective`, `ArcKeyMoment`, `StatisticalSeries`.

## Pipeline

| File | Purpose |
|------|---------|
| `pipeline/history/content_loader.py` | YAML to Supabase batch loader — reads `data/history/events/*.yaml`, upserts to 4 tables |
| `pipeline/history/image_enricher.py` | Unsplash + Pexels search, downloads to Supabase Storage |
| `pipeline/history/mirror_images.py` | Wikimedia Commons mirroring to Supabase Storage |
| `pipeline/history/source_enricher.py` | 15 free API source discovery CLI (output to `data/history/enrichment/`) |
| `pipeline/history/verify_content.py` | Content verification |
| `pipeline/history/upgrade_sources.py` | Source upgrade utility |
| `pipeline/media/image_search.py` | Shared unified image search API (Unsplash, Pexels, Wikimedia) |

## Components (22)

All in `frontend/app/history/components/`:

| Component | Lines | Purpose |
|-----------|-------|---------|
| `HistoryLanding` | ~1,482 | Organic ink timeline, above/below cards, inline story loading, thread overlay mode |
| `EventDetail` | ~826 | 8-stage museum journey (hero, crack, record, context, perspectives, omissions, evidence, exit) |
| `HistoryAudioCue` | — | void --onair companion audio player (between hero and crack, renders when `audioUrl` present) |
| `ThreadsLanding` | — | Thematic thread strips: horizontal EventCard carousels per thread, scroll snap + nav buttons |
| `EventCard` | — | Timeline card (poster + hook + CTA) |
| `HistoryOverlay` | — | **DEPRECATED** — replaced by inline loading in HistoryLanding State B. Kept for `[slug]/page.tsx` direct access |
| `HistoryTopbar` | — | Sticky topbar with back link + ThemeToggle |
| `HistoryTimeline` | — | Alternative timeline component |
| `CompactTimeline` | — | Compact timeline variant |
| `HistoryFooter` | — | Footer |
| `PerspectiveSelector` | — | Perspective tab selector |
| `PerspectiveView` | — | Single perspective full view |
| `PerspectiveComparison` | — | Side-by-side perspective comparison |
| `PrimarySourceBlock` | — | Primary source quote with citation |
| `OmissionsPanel` | — | Emphasized vs. omitted panel |
| `MediaGallery` | — | Image/document gallery |
| `Lightbox` | — | Full-screen image lightbox |
| `KeyFacts` | — | Compact reference panel (date, location, figures, toll). Superseded by Record block in EventDetail but kept as standalone component |
| `EraDrawer` | — | Era filter/navigation drawer |
| `MapView` | — | Geographic map visualization |
| `CartographerStrip` | — | Geographic cartography strip |
| `RedactedDossier` | — | Redacted/coming-soon event stubs (currently empty) |

### Page Files

| File | Route | Purpose |
|------|-------|---------|
| `history/page.tsx` | `/history` | Landing page (fetches events, renders HistoryLanding) |
| `history/[slug]/page.tsx` | `/history/[slug]` | Direct event access (generateStaticParams for 58 slugs) |
| `history/[slug]/EventPageClient.tsx` | — | Client wrapper for event detail |
| `history/era/[era]/page.tsx` | `/history/era/[era]` | Era listing |
| `history/era/[era]/EraPageClient.tsx` | — | Client wrapper for era page |
| `history/region/[region]/page.tsx` | `/history/region/[region]` | Region listing |
| `history/region/[region]/RegionPageClient.tsx` | — | Client wrapper for region page |
| `history/layout.tsx` | — | Shared layout (metadata, topbar) |

### Supporting Files

| File | Purpose |
|------|---------|
| `history/hooks.ts` | Shared HOOKS (58 arrive-late one-liners) and CTAS (58 story-specific calls to action) |
| `history/data.ts` | Supabase fetch layer with mock fallback |
| `history/types.ts` | TypeScript types (events + arcs) |
| `history/mockData.ts` | Mock fallback data (3 events, REDACTED_EVENTS cleared) |
| `history/arc-features.ts` | Feature flags for arc connections (THREAD_STAGE, DOSSIER, LEDGER, SIDEBAR, LONG_VIEW) |
| `history/threads.ts` | Thematic thread definitions for ThreadsLanding |

## Content Data

Event YAML files in `data/history/events/` (58 files). Each contains:
- Metadata: slug, title, subtitle, date_display, date_sort, era, region, country, category, severity
- Narrative: summary (full contextual narrative), significance, legacy_points
- Key figures: name, role, born/died years, optional wikidata/wikipedia links
- Perspectives: viewpoint, viewpoint_type, region_origin, narrative, emphasized[], omitted[], notable_quotes[]
- Media: title, media_type, source_url, attribution, license, creation_date, description
- Stats: death_toll, affected_population, duration

Arc pilot content (CEO decision pending): `data/history/arcs/capitalism-and-communism.yaml`.

## Agent Team (10 agents, 3 divisions)

### History Division (6 agents)

| Agent | Purpose |
|-------|---------|
| `history-curator` | Event selection, research, YAML content authoring, era/region taxonomy |
| `perspective-analyst` | Multi-perspective balance, 5-lens framework, viewpoint gap analysis |
| `historiographic-auditor` | Accuracy validation, source verification, narrative bias detection |
| `media-archaeologist` | Primary source discovery, historical media curation, rights/provenance |
| `timeline-architect` | Event connections, chronological accuracy, timeline data structure |
| `narrative-engineer` | Prose polish, show-don't-tell enforcement, narrative flow |

### History Visual Division (2 agents)

| Agent | Purpose |
|-------|---------|
| `visual-historian` | Archival Cinema design, Ken Burns effects, page layouts, component styling |
| `archive-cartographer` | Geographic visualization, map layers, region/era spatial data |

### Shared Cinematic Division (2 agents also used by history)

`cinematographer` and `motion-director` participate in `/history-publish` and `/cinematic-overhaul` workflows.

## Workflows (6)

| Command | Pattern | When |
|---------|---------|------|
| `/history-research` | history-curator -> perspective-analyst + media-archaeologist -> auditor -> narrative-engineer | New event onboarding |
| `/history-audit` | historiographic-auditor -> perspective-analyst -> re-validate | Perspective balance check |
| `/history-publish` | narrative-engineer -> auditor -> cinematic trio -> visual-historian -> build -> test | Content publishing |
| `/history-media` | media-archaeologist -> auditor -> visual-historian | Visual asset curation |
| `/history-timeline` | history-curator -> timeline-architect -> visual-historian -> archive-cartographer | Timeline & connections |
| `/history-qa` | parallel audit + content check -> perspective-analyst -> auditor -> uat-tester | History quality gate |

## Known Issues (from 2026-04-05 audit)

### P1 Critical
- Stage 8 exit: `onNavigateToEvent` wired in EventDetail but depends on parent passing handler. Dossier cards use `<Link>` (works without handler), but cliffhanger fallback still needs it
- Region filter uses single `region` column — events spanning multiple regions only appear under primary

### P2 Significant
- No `<title>` or metadata on individual history pages
- Overlay focus not moved on mount (WCAG)
- Era/region listing pages show "0 perspectives" (empty arrays)

### P3 Polish
- contextNarrative rendered as single blob in some components (EventDetail splits correctly)
- No preloading of adjacent lightbox images

## Future — Long Arcs (CEO Decision Required)

Arc types already defined in `types.ts`. Pilot content exists (`capitalism-and-communism.yaml`). Migration 042 written. Two options under consideration:

- **Option A (Lightweight)**: Arc pages from existing EventConnection graph, 2-3 days
- **Option B (Full)**: New content type with chapters x perspectives matrix, 10 new components, thread/chapter reading modes

See `docs/HISTORY-FRONTEND-SPEC.md` for full arc design spec.

## Files Reference

```
frontend/app/history/
  components/       # 22 components (see table above)
  [slug]/           # Event detail route + client wrapper
  era/[era]/        # Era listing route + client wrapper
  region/[region]/  # Region listing route + client wrapper
  hooks.ts          # Shared HOOKS (58) and CTAS (58)
  data.ts           # Supabase fetch layer
  types.ts          # TypeScript types (events + arcs)
  mockData.ts       # Mock fallback
  arc-features.ts   # Feature flags (THREAD_STAGE, DOSSIER, LEDGER, SIDEBAR, LONG_VIEW)
  threads.ts        # Thematic thread definitions
  layout.tsx        # Shared layout
  page.tsx          # Landing page

frontend/app/styles/history.css   # ~8,600 lines, .hist-page namespace

pipeline/history/
  content_loader.py     # YAML -> Supabase
  image_enricher.py     # Unsplash + Pexels -> Storage
  mirror_images.py      # Wikimedia -> Storage
  source_enricher.py    # 15 API source discovery
  verify_content.py     # Content verification
  upgrade_sources.py    # Source upgrade utility

pipeline/media/image_search.py    # Shared image search API

data/history/events/*.yaml        # 58 event content files
data/history/arcs/                # Arc pilot content (pending)

supabase/migrations/039_history_tables.sql
supabase/migrations/042_history_arcs.sql
supabase/migrations/043_history_media_constraints.sql
supabase/migrations/045_history_audio.sql

docs/HISTORY-FRONTEND-SPEC.md     # Frontend spec + audit findings
docs/VOID-HISTORY-DESIGN-SPEC.md  # Original design spec
docs/VOID-HISTORY-PROPOSAL.md     # Original proposal
docs/HISTORY-AUDIO-SPEC.md        # Audio spec
```
