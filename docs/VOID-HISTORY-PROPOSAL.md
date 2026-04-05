# void --history — Unified Strategic Proposal

**Date:** 2026-04-04
**Status:** CEO REVIEW — awaiting greenlight
**Process:** 4 advisory agents (CEO Advisor, Agent Architect, Tech Planner, Frontend Builder) + 4 targeted debate rounds (Data Layer, Palette, Framework, MVP Scope)

---

## The Thesis

> Wikipedia tells you what happened. void --history shows you who told it — and what they left out.

void --news makes media bias visible in today's headlines. void --history makes narrative bias visible across the centuries. Same DNA, different timescale. The same event — the Partition of India, Hiroshima, the Scramble for Africa — reads differently depending on who wrote the account, when they wrote it, and who they were writing for.

**History is not what happened. History is who told the story.**

---

## 1. Product Identity

| Attribute | Value |
|-----------|-------|
| **CLI name** | `void --history` |
| **Subtitle** | "The Archive" |
| **First-encounter text** | "Every event, every side" |
| **Route** | `/history`, `/history/[slug]`, `/history/era/[era]`, `/history/region/[region]` |
| **Logo** | Same void logo, different chrome |
| **Topbar** | Own sticky topbar (no NavBar) — same pattern as void --weekly |

**Product family position:**
```
void --news      The Feed
void --tl;dr     The Brief
void --onair     The Studio
void --weekly    The Magazine
void --paper     The Broadsheet
void --sources   The Spectrum
void --history   The Archive      <-- NEW
void --ship      The Forge
```

---

## 2. Competitive Moat

**The gap nobody fills:** No platform systematically presents the SAME historical event from multiple documented perspectives with transparent analysis of where and why narratives diverge.

| Competitor | What They Do Well | What They Miss |
|-----------|-------------------|----------------|
| Wikipedia | Breadth, citations, NPOV | Single merged narrative, no explicit perspective mapping |
| History.com | Production value, video | American-centric, entertainment-first |
| Khan Academy | Pedagogy, accessibility | Single-narrator, Western-textbook framing |
| Crash Course | Engaging, young audience | Single narrator, US/Euro lens |
| Google Arts & Culture | Museum-quality digitization | No bias/perspective analysis |

**void --history's moat:**
1. Per-event perspective mapping (not per-outlet bias — per-TRADITION historiographic framing)
2. Divergence as the product (where perspectives agree, where they disagree, and why)
3. Inspectable methodology (every attribution traces to named historians and primary sources)
4. $0 content acquisition (history is public domain)

---

## 3. Audience

| Segment | Why They Come | Overlap with void --news |
|---------|--------------|------------------------|
| **News-engaged adults (25-45)** | Context for current events | ~60% bridge audience |
| **Educators & students (16-30)** | AP/IB History multi-perspective analysis | Growth audience |
| **History enthusiasts** | Depth between pop-history and academia | ~30% overlap |
| **Journalists & analysts** | Historical context for coverage | Direct complement |

**The flywheel:** void --news story on Kashmir → void --history "Partition of India" context → deeper understanding → return to void --news with perspective. No competitor can do this.

---

## 4. The 5-Lens Historiographic Framework

**DEBATE VERDICT:** CEO Advisor's 5 categorical lenses won. Tech Planner's 6 viewpoint types serve as vocabulary within Lens 2. Agent Architect's 8 lenses rejected (too many overlaps).

These are NOT scores on a 0-100 scale. They are categorical labels with explanatory text. History is not a scoring game.

| Lens | What It Captures | Example (Partition of India, 1947) |
|------|-----------------|-----------------------------------|
| **1. Geographic/National** | Whose state/people is centered | British: "Transfer of power." Indian: "Independence." Pakistani: "Creation of homeland." |
| **2. Social Position** | Class, caste, gender, power of narrating group | Congress elites vs. rural peasants who experienced displacement |
| **3. Temporal Frame** | When the narrative was constructed | 1950s triumphalist vs. 2000s trauma/displacement scholarship |
| **4. Causal Emphasis** | What factor is foregrounded as cause | Political personalities vs. economic systems vs. religious identity |
| **5. Evidentiary Base** | What sources the narrative draws from | British administrative records vs. oral histories vs. literary memoir |

**Viewpoint types** (vocabulary for Lens 2): `victor`, `vanquished`, `bystander`, `academic`, `revisionist`, `indigenous`

Each event presents 3-6 named perspectives, each tagged with its lenses, each with specific citations. The user sees WHERE perspectives agree, where they DIVERGE, and WHY.

---

## 5. Visual Identity — "Archival Cinema"

**DEBATE VERDICT:** Burnt umber primary + aged brass secondary. Foxed vellum paper. Orthogonal to amber (news) and red (weekly).

**At a glance:** void --news = warm amber. void --weekly = editorial red. void --history = archival brown. Three distinct temperature zones.

### Color Palette

```css
/* Light Mode — "Reading Room" */
.hist-page {
  --hist-accent:          #5C4033;   /* Burnt umber — archival authority */
  --hist-accent-secondary: #9B7A2F;  /* Aged brass — dates, metadata */
  --hist-accent-ghost:    rgba(92, 64, 51, 0.06);
  --hist-accent-glow:     rgba(92, 64, 51, 0.12);

  --hist-bg-primary:      #F2EDE0;   /* Foxed vellum */
  --hist-bg-secondary:    #E9E3D4;   /* Aged document backing */
  --hist-bg-card:         #F7F2E7;   /* Clean archival card stock */
  --hist-bg-elevated:     #FFFCF5;   /* Lamplight highlight */

  --hist-fg-primary:      #2C2418;   /* Iron gall ink */
  --hist-fg-secondary:    #4A4437;   /* Aged ink */
  --hist-fg-tertiary:     #716A5C;   /* Marginal annotations */

  --hist-border:          #C4B896;   /* Aged paper edge */
  --hist-divider:         #D4CCBA;   /* Section rules */
}

/* Dark Mode — "Conservation Lab" */
.hist-page[data-mode="dark"] {
  --hist-accent:          #8B7355;   /* Lighter umber for contrast */
  --hist-accent-secondary: #B8972F;  /* Brighter brass */

  --hist-bg-primary:      #1A1612;   /* Museum case interior */
  --hist-bg-secondary:    #232018;   /* Shadow behind document */
  --hist-bg-card:         #2C2820;   /* Document under glass */

  --hist-fg-primary:      #D9CFC0;   /* Parchment cream */
  --hist-fg-secondary:    #B8AE9C;
}

/* Perspective Spectrum (assigned per-event, not per-nation) */
--hist-perspective-a:     #3D6B8E;   /* Steel blue */
--hist-perspective-b:     #8E5A3D;   /* Burnt sienna */
--hist-perspective-c:     #5A7A4A;   /* Olive green */
--hist-perspective-d:     #7A5A7A;   /* Dusty mauve */
--hist-perspective-e:     #8E7A3D;   /* Ochre */
```

### Typography (Same 4 voices, adapted roles)

| Voice | Font | Role in void --history |
|-------|------|----------------------|
| **Editorial** | Playfair Display | Event titles, section headers, pull quotes |
| **Structural** | Inter | Body narrative (1.7 lh for contemplative reading) |
| **Archival** | IBM Plex Mono 300 | Primary source quotations — typewriter dispatch feel |
| **Meta** | Barlow Condensed | Region tags, era labels, perspective type badges |

### Texture System (Paper, not Film)

| Texture | Implementation | Replaces |
|---------|---------------|----------|
| **Foxing** | SVG feTurbulence (fractalNoise, 0.015/0.02, 2 octaves) | Film grain |
| **Laid paper lines** | Repeating SVG pattern (2px period, 0.04 opacity) | — |
| **Document edge** | Stepped box-shadow (irregular opacity) | Rounded corners |
| **Photo grain** | High-frequency turbulence (0.8, 1 octave) on images | — |

### Post-Processing

```css
--hist-grade:       contrast(1.02) saturate(0.85) sepia(0.06);   /* Light */
--hist-grade-dark:  contrast(1.04) saturate(0.80) sepia(0.03);   /* Dark */
--hist-photo-grade: contrast(1.08) saturate(0.70) sepia(0.12);   /* Images */
```

**Vignette:** Tighter circle (desk lamp pool), not cinematic ellipse.

### Motion — "Documentary Camera"

| Technique | Implementation | Where |
|-----------|---------------|-------|
| **Ken Burns** | Slow zoom+pan on photos (8-12s CSS scale+translate) | Hero images |
| **Cross-dissolve** | Opacity crossfade (300ms) | Perspective switching fallback |
| **Lectern Turn** | Y-axis rotation (4deg, 450ms total) with 60ms beat | Perspective switching |
| **Iris Wipe** | clip-path: circle() expanding from click point | Timeline → event page |
| **Typewriter Stagger** | 80ms per tab appearance | Perspective tabs reveal |

Spring presets: `archive-snap` (600/35), `document-settle` (280/22), `lectern-turn` (200/18/1.1), `unfold` (150/14/1.2).

All motion disabled under `prefers-reduced-motion`.

---

## 6. Data Layer

**DEBATE VERDICT:** Supabase from day 1. Same patterns as the other 37 migrations. Cross-linking with void --news is the editorial value proposition, not a future maybe.

### Schema (Migration 039)

**4 tables:**

| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `history_events` | Event registry | slug, title, date_sort, era, region, category, severity, summary, significance, key_figures (JSONB), coordinates (JSONB), hero_media_id, is_published |
| `history_perspectives` | Per-event viewpoints (3-6 each) | event_id FK, viewpoint, viewpoint_type (victor/vanquished/etc.), narrative, key_arguments (JSONB), sources (JSONB), notable_quotes (JSONB) |
| `history_media` | Images, maps, documents, video | event_id FK, media_type, title, source_url, storage_path, attribution, license, creator, creation_date |
| `history_connections` | Cross-event graph | event_a_id FK, event_b_id FK, connection_type (caused/influenced/response-to/parallel/consequence) |

**RLS:** Public read, service_role write. Same pattern as all existing tables.

### Content Pipeline (NOT Automated)

No cron. No RSS. Content is batch-curated:

1. **Draft**: Gemini 2.5 Flash generates first drafts from structured prompts (~150 calls total, within free tier)
2. **Review**: Human editorial review for accuracy, balance, show-don't-tell
3. **Source**: YAML files in `data/history/events/` (version-controlled for review)
4. **Load**: Python script `pipeline/history/content_loader.py` upserts YAML → Supabase
5. **Media**: Public domain images pre-processed to WebP, stored in Supabase Storage bucket `history-media/`

### Media Strategy ($0)

| Source | Content | License |
|--------|---------|---------|
| Wikimedia Commons | Photos, maps, paintings | Public domain / CC |
| Library of Congress | American history, maps | Public domain |
| National Archives (US/UK) | War photos, documents | Public domain |
| Metropolitan Museum | Art, artifacts | CC0 |
| Europeana | European cultural heritage | Various CC |
| Internet Archive | Video, documents | Public domain |
| David Rumsey Map Collection | Historical maps | Various |

**Storage budget:** ~50MB images + ~75MB video = ~125MB (12.5% of 1GB free tier).
**Bandwidth strategy:** Thumbnails in Supabase Storage, full-size linked from source archives.

---

## 7. Frontend Architecture

### Routing (Sub-path, not subdomain)

```
frontend/app/history/
  page.tsx                    -- /history (landing)
  [slug]/
    page.tsx                  -- /history/partition-of-india (event detail)
  era/
    [era]/
      page.tsx                -- /history/era/modern
  region/
    [region]/
      page.tsx                -- /history/region/africa
  components/                 -- History-specific components
```

Follows the `/weekly`, `/sources`, `/ship`, `/about` precedent. Same static export, same build process.

### Page Architecture

**Landing — "The Archive Index"**
- Hero pull quote: "History is not what happened. It is who told the story."
- Era drawers (clickable, slide open to reveal events)
- Region pills (filter by geography)
- Featured events (3 editorial picks, full-bleed archival photos)
- Compact horizontal timeline (all events plotted chronologically)

**Event Detail — "The Dossier"**
- Full-bleed hero image with Ken Burns + archival grade filter
- Context panel (neutral facts — date, actors, death toll, affected population)
- Perspective Navigator (tabbed cards with colored borders, temporal/geographic anchors)
- Active Perspective (narrative + primary sources + emphasized/omitted panel)
- Comparison Mode toggle (split-screen, draggable divider, vocabulary highlighting)
- Media Gallery (horizontal scroll with lightbox)
- Connected Events (visual link graph)
- Timeline Context (prev/next navigation)

**The Perspective UI — "The Rotating Lectern"**
- Each tab is a card with perspective color border, name, temporal anchor, geographic anchor
- Switching uses Y-axis rotation (the "lectern turn") with 60ms silence beat
- Split-screen comparison: draggable divider, vocabulary differences underlined in perspective colors
- "Emphasized vs. Omitted" panel: filled circles (emphasized), hollow + strikethrough (omitted), half-filled (disputed)

### New Components (18)

`HistoryLanding`, `EraDrawer`, `EventCard`, `EventDetail`, `PerspectiveSelector`, `PerspectiveView`, `PerspectiveComparison`, `NarrativeOverlap`, `PrimarySourceBlock`, `DocumentViewer`, `ArchivalGallery`, `Lightbox`, `HistoryTimeline`, `CompactTimeline`, `MapView`, `KeyFacts`, `OmissionsPanel`, `HistoryTopbar`

### CSS

New file: `frontend/app/styles/history.css` — `.hist-*` namespace, scoped to `.hist-page`.
Added to `globals.css` import chain after `ship.css`.

---

## 8. Agent Team — 8 New Agents, 2 Divisions

### History Division (6 agents)

| Agent | Role | Access | Trigger |
|-------|------|--------|---------|
| `history-curator` | Event selection, source research, regional diversity | Read+Write | New event onboarding |
| `perspective-analyst` | Multi-perspective structuring, 5-lens framework application | Read+Write | After curator drafts event |
| `historiographic-auditor` | Balance validation, Western-centric bias detection, 10-dimension audit | Read-only | Before publishing |
| `media-archaeologist` | Public domain image/video/map sourcing, provenance verification | Read+Write | After event identified |
| `timeline-architect` | Temporal narratives, cause-effect chains, cross-event connections | Read+Write | After events curated |
| `narrative-engineer` | Show-don't-tell enforcement, citation standards, content polish | Read+Write | After auditor approves |

### History Visual Division (2 agents)

| Agent | Role | Access | Trigger |
|-------|------|--------|---------|
| `visual-historian` | History UI/UX, immersive layouts, image-heavy pages | Read+Write | Page design tasks |
| `archive-cartographer` | Interactive maps, geographic visualization, territorial change | Read+Write | Events with geographic dimension |

**New total: 32 agents across 13 divisions.**

### New Workflows (6)

| Workflow | Pattern | When |
|----------|---------|------|
| `/history-research` | curator → [perspective-analyst + media-archaeologist] → auditor → narrative-engineer | New event |
| `/history-audit` | auditor → perspective-analyst (fixes) → auditor (re-validate) | Before publishing |
| `/history-publish` | narrative-engineer → auditor (final) → visual-historian → frontend-builder → uat-tester | Ship event |
| `/history-media` | media-archaeologist → auditor (visual bias) → visual-historian | Asset curation |
| `/history-timeline` | curator → timeline-architect → visual-historian → archive-cartographer | Timeline/map design |
| `/history-qa` | [auditor + narrative-engineer] parallel → fixes → auditor → uat-tester | Quality sweep |

### Quality Gates (12)

Every event must pass ALL before publishing:

| Gate | Agent | Criteria |
|------|-------|---------|
| Perspective minimum | curator | 3+ genuinely distinct perspectives |
| Juxtaposition test | perspective-analyst | Perspectives are genuinely different, not emphasis variations |
| Balance audit | auditor | BALANCED or ACCEPTABLE on all 10 dimensions |
| Swap test | auditor | Swapping "mainstream"/"alternative" labels wouldn't change presentation |
| Source diversity | auditor | Non-Western sources >= 30% for non-Western events |
| Show-don't-tell | narrative-engineer | Zero banned vocabulary in published content |
| Citation density | narrative-engineer | 1+ citation per factual claim, 1+ primary source per perspective |
| Visual provenance | media-archaeologist | 100% images have full Context Protocol metadata |
| Visual bias | auditor | No perspective has zero visual representation |
| Connection minimum | timeline-architect | Every event connected to 2+ others |
| Accessibility | uat-tester | Alt text, keyboard nav, reduced-motion fallbacks |
| Performance | perf-optimizer | Lighthouse 85+ despite image-heavy pages |

---

## 9. MVP Scope

**DEBATE VERDICT:** 10 events. Build the frontend for 50, populate 10.

### Why 10

- A timeline with 3 points looks like a demo. 10 makes it feel inhabited.
- A region grid with 10 pins across 5+ regions signals global scope.
- 10 events at maximum quality > 50 events at mediocre quality.
- Each event requires ~2-3 days of focused curation (perspectives, sources, images).
- 10 events = 3-5 weeks of content work. Achievable.
- Remaining 40 shown as "Coming" cards — signals ambition without empty restaurant.

### The MVP 10 (Selected for Maximum Visual Spread)

| # | Event | Year | Region | Why Selected |
|---|-------|------|--------|-------------|
| 1 | **Partition of India** | 1947 | South Asia | 5+ perspectives, rich archives, connects to active news |
| 2 | **Creation of Israel / Nakba** | 1948 | Middle East | Highest perspective divergence of any modern event |
| 3 | **Hiroshima & Nagasaki** | 1945 | East Asia | US/Japanese/international perspectives, extraordinary media |
| 4 | **Rwandan Genocide** | 1994 | Africa | Genocide studies, Hutu/Tutsi/international perspectives |
| 5 | **Scramble for Africa / Berlin Conference** | 1884 | Africa/Europe | African vs European historiographic divergence |
| 6 | **French Revolution** | 1789 | Europe | 4+ perspectives including Haitian impact |
| 7 | **Trail of Tears** | 1830s | Americas | Indigenous/settler perspectives, living consequences |
| 8 | **Fall of the Berlin Wall** | 1989 | Europe | East/West/Soviet/dissident perspectives |
| 9 | **Opium Wars** | 1839 | East Asia | British/Chinese historiographic divergence |
| 10 | **Transatlantic Slave Trade** | 1500s-1800s | Global | African/European/American/diasporic perspectives |

**Regional coverage:** South Asia 1, Middle East 1, East Asia 2, Africa 2, Europe 2, Americas 1, Global 1.
**Temporal spread:** 1500s, 1789, 1830s, 1839, 1884, 1945, 1947, 1948, 1989, 1994.

---

## 10. Risk Mitigation

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| **Historical inaccuracy** | HIGH | Every claim cites a specific source. No uncited assertions. |
| **Cultural insensitivity** | HIGH | Never "speak for" an oppressed group. Center scholars and primary sources FROM that group. |
| **False equivalence** | HIGH | Not all perspectives deserve equal weight. Editorial notes when a perspective is widely rejected by historians. |
| **Controversy backlash** | HIGH | Attribute every claim to named historians, not to void --history. The platform curates — it does not adjudicate. |
| **Content quality** | MEDIUM | Human review of every AI-generated draft. Quality gate: does this read like someone who read the primary sources? |
| **Scope creep** | MEDIUM | 10 events for MVP. Prove the format, then scale. |
| **Image rights** | LOW | Strict public domain / CC only. Full attribution metadata for every image. |

---

## 11. Implementation Phases

### Phase 0 — Foundation (2 weeks)
- [ ] Create 8 agent definitions in `.claude/agents/`
- [ ] Create 6 workflow skills in `.claude/skills/`
- [ ] Write migration `039_history_tables.sql`
- [ ] Create `frontend/app/styles/history.css` with Archival Cinema tokens
- [ ] Create `frontend/app/history/` route structure
- [ ] Build `HistoryTopbar`, `HistoryLanding`, `EventCard` components
- [ ] Add history.css to globals.css import chain
- [ ] Update PRODUCT_FAMILY in `film/data.ts`
- [ ] Create `data/history/events/` YAML template
- [ ] Create `pipeline/history/content_loader.py`

### Phase 1 — Pilot (3-5 weeks)
- [ ] Curate 10 events (Gemini drafts + human review)
- [ ] Source 50-100 public domain media assets
- [ ] Build: EventDetail, PerspectiveSelector, PerspectiveView, PerspectiveComparison
- [ ] Build: PrimarySourceBlock, ArchivalGallery, Lightbox, OmissionsPanel
- [ ] Build: HistoryTimeline, CompactTimeline, MapView
- [ ] Run `/history-research` workflow for all 10 events
- [ ] Run `/history-audit` for all 10 events
- [ ] Deploy to GitHub Pages alongside main site

### Phase 2 — Expansion (6+ weeks)
- [ ] Scale to full 50 events
- [ ] Cross-link: void --news Deep Dive → void --history context
- [ ] Cross-link: void --history "In the News Now" → void --news clusters
- [ ] Era browser and region explorer pages
- [ ] "Coming" cards for unpopulated events
- [ ] Community-suggested events via void --ship

### Phase 3 — Maturity (ongoing)
- [ ] 1-2 new events per month
- [ ] Audio companion: narrator-driven perspective walkthroughs (Gemini TTS)
- [ ] Education partnerships (AP History teachers, IB programs)
- [ ] void --history --weekly magazine digest

---

## 12. Cost Analysis

| Item | Cost | Notes |
|------|------|-------|
| Supabase (storage + DB) | $0 | Within free tier (125MB of 1GB storage, minimal rows) |
| Gemini Flash (content drafts) | $0 | ~150 calls total, within 1500 RPD free tier |
| GitHub Pages hosting | $0 | Same static export |
| GitHub Actions (content deploy) | $0 | One-shot workflow, not cron |
| Media assets | $0 | All public domain / CC |
| Agent team (Claude CLI) | $0 | Max subscription (existing) |
| **Total incremental cost** | **$0** | |

---

## 13. Decisions Requiring CEO Approval

1. **GREENLIGHT** — Approve void --history as a product initiative
2. **MVP 10** — Confirm the 10 selected events (or swap any)
3. **5-Lens Framework** — Confirm the historiographic perspective model
4. **Burnt Umber Palette** — Confirm "Archival Cinema" visual direction
5. **8 New Agents** — Confirm the agent team expansion (32 total)
6. **Supabase from Day 1** — Confirm data layer approach
7. **Audio** — Defer to Phase 3, or include in Phase 1?
8. **Cross-linking** — Phase 2 priority for news ↔ history integration?

---

## The Positioning Line

**void --news** shows you how today's news is being told differently.
**void --history** shows you how yesterday's events have been told differently.

Together, they make the argument that all information is perspectival — and the best response is not to pick a side, but to see all of them.

---

*Proposal assembled from: CEO Advisor strategic memo, Agent Architect team blueprint, Tech Planner architecture plan, Frontend Builder design specification (VOID-HISTORY-DESIGN-SPEC.md), plus 4 debate verdicts on contested points.*
