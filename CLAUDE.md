# void --news

Last updated: 2026-03-18

> **Read this file first. Only read other docs when task-relevant. Only open source files when modifying code.**

A modern news aggregation platform with a sophisticated, multi-dimensional bias analysis engine. Built from first principles to make bias analysis free, central, and per-article — not per-outlet. Every source is curated for credibility. Covers World News and US News with a 6-axis rule-based NLP approach that goes far beyond simple left/center/right labels.

## Architecture

```
GitHub Actions (2x daily cron) → Python Pipeline → Supabase (PostgreSQL) ← Next.js Static Site (GitHub Pages)
```

- **No backend server.** The entire system runs serverless.
- **Python pipeline** runs on GitHub Actions (morning + evening), handles ingestion, NLP analysis, and writes results to Supabase.
- **Next.js frontend** is statically exported and hosted on GitHub Pages. Reads directly from Supabase client-side.
- **Supabase** is the single data layer: articles, bias scores, source metadata, story clusters.

## Tech Stack

| Layer          | Technology                                    |
|----------------|-----------------------------------------------|
| Ingestion      | Python, feedparser, BeautifulSoup/Scrapy      |
| NLP/Bias Engine| Python, spaCy, NLTK, TextBlob                |
| Database       | Supabase (PostgreSQL)                         |
| Frontend       | Next.js 14+ (static export), React, TypeScript|
| Animation      | Motion One v11 (spring physics, ~6.5KB CDN)   |
| Styling        | CSS custom properties, mobile-first, clamp()  |
| Fonts          | Playfair Display (editorial), Inter (structural), JetBrains Mono (data) |
| Hosting        | GitHub Pages (frontend), GitHub Actions (pipeline) |

## Core Principles

### Zero Operational Cost
- No paid APIs. All analysis is rule-based NLP running locally in the pipeline.
- GitHub Actions free tier (2000 min/month private, unlimited public).
- Supabase free tier for database.
- GitHub Pages free tier for hosting.
- Motion One via CDN importmap (no npm install needed).

### Bias Analysis — The Differentiator
The bias engine analyzes **each article individually** across multiple axes:

1. **Political Lean** — left/center/right spectrum based on language, framing, source patterns
2. **Sensationalism Score** — measured vs. inflammatory tone, headline clickbait detection
3. **Opinion vs. Reporting** — distinguishes editorial content from factual reporting
4. **Factual Rigor** — presence of sourcing, citations, data-backed claims
5. **Framing Analysis** — what facts are emphasized, what is omitted, language connotation
6. **Per-Topic Per-Outlet Tracking** — an outlet's bias may differ by topic (economics vs. social issues)

All analysis is algorithmic/rule-based using NLP heuristics. No LLM API calls.

### Source Curation
90 vetted sources at launch, organized in three tiers (30 each):

- **Major US Outlets** — AP, Reuters, NYT, WSJ, Washington Post, Fox News, CNN, NPR, PBS, Bloomberg, etc.
- **International Outlets** — BBC, Al Jazeera, DW, France24, Reuters International, The Guardian, NHK, etc.
- **Independent/Nonprofit** — ProPublica, The Intercept, Bellingcat, The Markup, Center for Public Integrity, etc.

All sources must meet credibility criteria before inclusion. Quality over quantity.

## Pipeline Flow (2x Daily)

```
1. FETCH      — Pull articles via RSS feeds + web scraping from 90 sources
2. PARSE      — Extract full article text, metadata, publish date
3. DEDUPLICATE — Identify duplicate/syndicated content
4. CLUSTER    — Group articles covering the same story across sources
5. ANALYZE    — Run multi-axis bias scoring on each article
6. RANK       — Score story importance/impact for feed ordering
7. CATEGORIZE — Auto-tag topics (Politics, Economy, Tech, Health, Environment, Conflict, etc.)
8. WRITE      — Push processed data to Supabase
```

## Frontend Design

### Design Philosophy — "Press & Precision"
Modern newspaper aesthetic — pays tribute to the printing press era in design philosophy. Serif headlines, editorial layout sensibility. **Clean and minimal on arrival, data-dense on interaction.** Progressive disclosure is the core interaction pattern.

Adapted from DondeAI's "Ink & Momentum" philosophy: every interaction has weight and intention. Spring physics for user-initiated actions, ease-out for system reveals.

### Three Voices of Type (from DondeAI)

| Voice | Font | Use For |
|-------|------|---------|
| Editorial | Playfair Display | Headlines, story titles, section headers |
| Structural | Inter | Body text, labels, navigation, buttons |
| Data | JetBrains Mono | Bias scores, source counts, timestamps, metrics |

### Responsive Strategy — One Project, Two Layouts

Single Next.js project with **device-optimized layouts** sharing the same data layer and component logic. Not two separate apps — one codebase with layout switching.

#### What Changes Between Desktop and Mobile

| Aspect | Desktop | Mobile |
|--------|---------|--------|
| **Layout** | Multi-column newspaper grid, sidebar for filters/deep dive | Single-column feed, bottom sheet for filters |
| **Story cards** | Horizontal layout with inline bias indicators | Vertical stack, bias indicators below headline |
| **Deep Dive** | Side panel or split-screen comparison | Full-screen modal with swipe navigation |
| **Navigation** | Top nav bar with section tabs | Bottom nav bar (thumb-reachable) |
| **Bias viz** | Inline charts, hover to expand | Tap to expand, full-width charts |
| **Data density** | High — show more metrics at a glance | Progressive — show headline + key score, tap for more |
| **Interactions** | Hover reveals, click expands | Tap reveals, swipe navigates |
| **Typography** | Larger editorial headings, wider measure | Tighter line lengths, slightly smaller scale |

#### What Stays the Same

- Component logic and data fetching
- Supabase queries and data shapes
- Animation system (spring physics, motion tokens)
- Color system and design tokens
- Accessibility (WCAG 2.1 AA)
- Bias scoring display and color coding

#### Implementation

```tsx
// Layout detection via CSS media queries + React context
// Breakpoints (mobile-first):
//   375px  — mobile (primary target)
//   768px  — tablet
//   1024px — desktop
//   1440px — wide desktop

// Component pattern:
// <StoryCard /> — shared logic
//   ├── <StoryCardDesktop /> — multi-column with inline charts
//   └── <StoryCardMobile />  — vertical stack with tap-to-reveal
```

- Use CSS `clamp()` for fluid scaling between breakpoints
- Mobile touch targets ≥ 44×44px (WCAG compliance)
- Horizontal scroll strips with scroll-snap on mobile
- Bottom sheet pattern for filters/detail on mobile
- One-handed reachability: critical actions in bottom 40% of screen

### Two Core Views

#### 1. Homepage — News Feed
- Organic, importance-ranked flow of stories (no rigid category sections)
- Auto-generated category tags for filtering
- Each story card shows: headline, source count, key bias indicators at a glance
- "Last updated" timestamp showing pipeline freshness
- Refresh button (re-fetches from Supabase, with confirmation dialog to avoid accidental clicks)
- Sections: World News and US News
- **Desktop**: newspaper-style multi-column grid with sidebar
- **Mobile**: single-column feed with bottom navigation

#### 2. Deep Dive Dashboard
- Story clustering view — same event from multiple sources side-by-side
- Full multi-axis bias breakdown with visualizations
- Framing comparison: what each source emphasizes/omits
- Coverage distribution charts (which outlet types are covering this?)
- Source credibility context
- **Desktop**: split-screen comparison, inline charts
- **Mobile**: full-screen with swipe between sources, vertically stacked charts

### Interaction Model
- **On arrival**: clean, minimal, newspaper-like. Headlines and importance.
- **On interaction**: rich data layers reveal — hover/click to expose bias scores, source comparisons, framing analysis.
- Progressive disclosure throughout.

## Animation System (Adapted from DondeAI)

### Motion Library
**Motion One v11** via CDN importmap (~6.5KB). Provides real spring physics with CSS transition fallback.

### Spring Presets

| Preset | Stiffness | Damping | Mass | Use Case |
|--------|-----------|---------|------|----------|
| snappy | 600 | 35 | 1 | Buttons, toggles, filter chips |
| smooth | 280 | 22 | 1 | Cards, panels, story expansion |
| gentle | 150 | 12 | 1.2 | Page transitions, view switches |
| bouncy | 450 | 12 | 1.1 | Celebrations, data reveals |

### Duration Tokens

```css
:root {
  --dur-instant:  0ms;
  --dur-fast:     150ms;
  --dur-normal:   300ms;
  --dur-morph:    400ms;
  --dur-step:     450ms;
  --dur-slow:     600ms;
}
```

### Easing Curves

```css
:root {
  --spring: linear(/* damped oscillation with real overshoot */);
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);  /* Apple-sharp deceleration */
  --ease-in: cubic-bezier(0.4, 0, 1, 1);       /* Use sparingly */
}
```

### Animation Patterns

| Trigger | Curve | Duration | Example |
|---------|-------|----------|---------|
| User tap/click | var(--spring) | 300-450ms | Filter chip select, story expand |
| System reveal | var(--ease-out) | 300-600ms | Data fade-in, chart animate |
| View transition | var(--ease-out) | 400ms | Feed ↔ Deep Dive |
| Reduced motion | instant | 0ms | All animations |

### Motion Utilities (Ported from DondeAI)

- `springAnimate(el, keyframes, opts)` — Motion One with CSS fallback
- `springPress(el, opts)` — Button press interaction (0.97x scale, 300ms return)
- `springStagger(elements, opts)` — Stagger reveals across story cards
- `countUp(el, target, opts)` — Numeric count animation for bias scores
- `timeline()` — Sequential animation orchestrator
- `trackedRaf(name, tickFn)` — Named RAF loops with auto-cleanup
- `isReducedMotion()` — Accessibility check

### Animation Rules
- **Symmetric**: open/close, in/out use identical duration and easing in both directions
- **GPU-only**: only animate transform and opacity (composite properties)
- **Accessible**: all animations → 0ms under `prefers-reduced-motion: reduce`
- **Interruptible**: no animation locks, user can interact during transitions
- **Performance budget**: max 3 simultaneous spring animations, 60fps target

### Glass Morphism Elevation (from DondeAI)

| Level | Blur | Use Case |
|-------|------|----------|
| E0 Surface | 0px | Base content |
| E1 Floating | 16px | Headers, nav bars |
| E2 Popout | 24px | Tooltips, bias popups |
| E3 Modal | 32px | Deep dive overlay (mobile) |

## CSS Architecture (Adapted from DondeAI)

### Load Order (Cascade)
```
reset.css → tokens.css → layout.css → typography.css → components.css → animations.css → responsive.css
```

### Design Tokens
- CSS custom properties only — no preprocessor (no Sass/LESS)
- BEM-like naming convention (`.component__element--modifier`)
- Mobile-first with `min-width` media queries
- `clamp()` for all fluid scaling (typography, spacing)
- No `!important` — ever

### Color System — Bias Scoring

| Axis | Color Coding |
|------|-------------|
| Political Lean | Blue (left) ← Neutral (gray) → Red (right) |
| Sensationalism | Green (measured) → Yellow → Red (inflammatory) |
| Opinion vs. Fact | Blue (reporting) ↔ Orange (opinion) |
| Factual Rigor | Green (high) → Yellow → Red (low) |

### Breakpoints (Mobile-First with clamp())

```
375px  — mobile (primary target)
768px  — tablet
1024px — desktop
1440px — wide desktop
```

### Fluid Scaling
```css
/* Typography */
--text-xs:   clamp(0.5625rem, 0.5rem + 0.25vw, 0.625rem);
--text-sm:   clamp(0.75rem, 0.7rem + 0.2vw, 0.875rem);
--text-base: clamp(0.875rem, 0.8rem + 0.3vw, 1rem);
--text-lg:   clamp(1.125rem, 1rem + 0.5vw, 1.5rem);
--text-xl:   clamp(1.5rem, 1.2rem + 1vw, 2.5rem);
--text-hero: clamp(2rem, 1.5rem + 2vw, 4rem);

/* Spacing */
--space-xs:  clamp(0.25rem, 0.2rem + 0.2vw, 0.5rem);
--space-sm:  clamp(0.5rem, 0.4rem + 0.4vw, 1rem);
--space-md:  clamp(1rem, 0.8rem + 0.8vw, 1.5rem);
--space-lg:  clamp(1.5rem, 1rem + 1.5vw, 3rem);
--space-xl:  clamp(2rem, 1.5rem + 2vw, 4rem);
```

## Data Model (Supabase)

### Key Tables
- `sources` — outlet metadata, credibility info, RSS/scrape config, tier (us_major/international/independent)
- `articles` — full text, metadata, source_id, publish_date, url
- `bias_scores` — per-article multi-axis scores (linked to article_id)
- `story_clusters` — groups of articles about the same event
- `cluster_articles` — junction table linking articles to clusters
- `categories` — auto-generated topic tags
- `article_categories` — junction table linking articles to categories
- `pipeline_runs` — tracking pipeline execution history

## Skills (`.claude/skills/`)

| Skill | Purpose | Trigger |
|-------|---------|---------|
| `/pressdesign` | "Press & Precision" design system enforcement — anti-slop, typography, motion grammar, dot matrix rule, newspaper layout, responsive strategy | Auto on UI tasks, manual for design review |

**Also recommended:** Install the official Anthropic `frontend-design` plugin for additional anti-slop design foundations:
```bash
/plugin install frontend-design@claude-plugins-official
```

## Agent Team (Adapted from DondeAI — 16 Agents, 7 Divisions)

> Full team structure, R&R, and sequential cycles: `docs/AGENT-TEAM.md`

### Agent Hierarchy

```
CEO (Aacrit)
  ├── Quality ————————— analytics-expert, bias-auditor, pipeline-tester, bug-fixer
  ├── Infrastructure ——— perf-optimizer, db-reviewer, update-docs
  ├── Frontend ————————— frontend-builder, frontend-fixer, responsive-specialist, uat-tester
  ├── Pipeline ————————— nlp-engineer, source-curator
  ├── Security ————————— void-ciso
  ├── Product —————————— ceo-advisor
  └── Branding ————————— logo-designer
```

### Cost Policy — $0 Absolute Ceiling

```
ALL AI/LLM WORK USES CLAUDE CODE CLI (Max subscription).
No Anthropic API keys. No OpenAI. No paid inference. Anywhere. Ever.

Pipeline NLP: Rule-based only (spaCy, NLTK, TextBlob) — $0
Agent work:   Claude Code CLI (opus via Max subscription) — $0
Database:     Supabase free tier — $0
Hosting:      GitHub Pages — $0
CI/CD:        GitHub Actions free tier — $0
```

### Agent Design Principles (from DondeAI)

1. **No Hierarchical Delegation** — Agents cannot spawn other agents. Task routing at CEO level.
2. **Read-First Protocol** — Every agent reads CLAUDE.md + relevant docs before any work.
3. **Execution Protocol** — Assess → Plan → Build → Verify → Report. No exceptions.
4. **Max Blast Radius** — Each agent bounded: max 4 CSS, 2 JS/TS, 3 Python files per run.
5. **$0 Cost — Claude CLI Only** — All AI work via `claude` CLI command. No API keys, no per-token billing.
6. **Model: Opus** — All agents use Claude Opus via CLI. No model downgrades.
7. **Parallel-Safe vs Sequential** — Read-only agents run concurrently; write agents require sequencing.

### Sequential Cycles

```
Pipeline Quality:  pipeline-tester → bug-fixer → pipeline-tester (retest)
Bias Audit:        analytics-expert → bias-auditor → nlp-engineer → pipeline-tester
Frontend Build:    frontend-builder → responsive-specialist → uat-tester → frontend-fixer
```

### Agent Routing

| Task Pattern | Agent | Division |
|---|---|---|
| Bias score accuracy, calibration, benchmarking | `analytics-expert` | Quality |
| Ground-truth validation, known-outlet comparison | `bias-auditor` | Quality |
| Pipeline output validation, clustering quality | `pipeline-tester` | Quality |
| Post-test bug fixing, scoring fixes | `bug-fixer` | Quality |
| Pipeline runtime, frontend load, Lighthouse | `perf-optimizer` | Infrastructure |
| Article/cluster data quality, NULL audits | `db-reviewer` | Infrastructure |
| Sync docs with codebase | `update-docs` | Infrastructure |
| Build UI components, new features | `frontend-builder` | Frontend |
| Fix UI bugs, layout breaks, a11y gaps | `frontend-fixer` | Frontend |
| Desktop/mobile layout, responsive issues | `responsive-specialist` | Frontend |
| Browser testing, click-through QA | `uat-tester` | Frontend |
| spaCy models, bias scoring algorithms, NER | `nlp-engineer` | Pipeline |
| Source vetting, RSS config, credibility | `source-curator` | Pipeline |
| Security audit, secrets scan, RLS, OWASP | `void-ciso` | Security |
| Strategic advice, roadmap, priorities | `ceo-advisor` | Product |
| Logo, favicon, brand identity | `logo-designer` | Branding |

### Locked Decisions (Require CEO Approval)

- Press & Precision design system (3-voice type, dot matrix rule, newspaper grid)
- 6-axis bias scoring model + confidence
- Supabase as single data layer
- Static export (Next.js → GitHub Pages)
- 90-source curated list structure (3 tiers × 30)
- $0 operational cost constraint
- Claude Max CLI for all AI work (no API LLMs)

## Project Structure

```
void-news/
├── CLAUDE.md
├── docs/
│   ├── PROJECT-CHARTER.md         # Project charter and scope
│   ├── DESIGN-SYSTEM.md           # Press & Precision design system
│   ├── IMPLEMENTATION-PLAN.md     # Phased implementation roadmap
│   └── ARCHITECTURE.md            # Technical architecture details
├── pipeline/                      # Python ingestion + analysis
│   ├── fetchers/                  # RSS and scraping modules
│   │   ├── rss_fetcher.py
│   │   └── web_scraper.py
│   ├── analyzers/                 # NLP bias analysis engine
│   │   ├── political_lean.py
│   │   ├── sensationalism.py
│   │   ├── opinion_detector.py
│   │   ├── factual_rigor.py
│   │   └── framing.py
│   ├── clustering/                # Story deduplication and grouping
│   ├── categorizer/               # Auto-topic classification
│   ├── ranker/                    # Importance/impact scoring
│   ├── utils/                     # Shared utilities, Supabase client
│   ├── main.py                    # Pipeline orchestrator
│   └── requirements.txt
├── frontend/                      # Next.js static site
│   ├── src/
│   │   ├── components/
│   │   │   ├── shared/            # Shared logic components
│   │   │   ├── desktop/           # Desktop-specific layouts
│   │   │   └── mobile/            # Mobile-specific layouts
│   │   ├── layouts/
│   │   │   ├── DesktopLayout.tsx
│   │   │   └── MobileLayout.tsx
│   │   ├── pages/                 # Next.js pages
│   │   ├── hooks/                 # Custom React hooks (data fetching, device detection)
│   │   ├── lib/                   # Supabase client, utilities
│   │   ├── animations/            # Motion One spring presets, utilities
│   │   │   ├── spring.ts          # Spring presets (adapted from DondeAI)
│   │   │   └── motion.ts          # Timeline, RAF, interactions (adapted from DondeAI)
│   │   └── styles/
│   │       ├── reset.css
│   │       ├── tokens.css         # Design tokens (colors, spacing, typography, animation)
│   │       ├── layout.css
│   │       ├── typography.css
│   │       ├── components.css
│   │       ├── animations.css     # Keyframes, transitions
│   │       └── responsive.css     # Breakpoint-specific overrides
│   ├── public/
│   └── next.config.js
├── .claude/
│   └── agents/                    # Claude agents for development
├── .github/
│   └── workflows/
│       ├── pipeline.yml           # 2x daily news pipeline cron
│       └── deploy.yml             # Frontend build + deploy to GitHub Pages
├── data/
│   └── sources.json               # Curated source list with RSS URLs and metadata
└── supabase/
    └── migrations/                # Database schema migrations
```

## MVP Scope

### Phase 1 — Foundation (Week 1-2)
- [ ] Project scaffolding (Next.js, Python pipeline, Supabase)
- [ ] Source list curation (90 sources with RSS/scrape configs)
- [ ] Supabase schema setup (all tables + migrations)
- [ ] Basic RSS fetcher (feedparser)
- [ ] Basic web scraper (BeautifulSoup)
- [ ] Article storage pipeline
- [ ] GitHub Actions cron (2x daily)
- [ ] Pipeline orchestrator (main.py)

### Phase 2 — Analysis Engine (Week 3-5)
- [ ] Story deduplication (TF-IDF similarity)
- [ ] Story clustering algorithm
- [ ] Political lean scoring
- [ ] Sensationalism detection
- [ ] Opinion vs. reporting classifier
- [ ] Factual rigor scoring
- [ ] Framing analysis (keyword emphasis, omission detection)
- [ ] Auto-categorization (topic tagging)
- [ ] Importance/impact ranking

### Phase 3 — Frontend MVP (Week 6-8)
- [ ] Next.js project setup with static export + TypeScript
- [ ] Design token system (CSS custom properties)
- [ ] Animation system (Motion One spring presets, utilities)
- [ ] Desktop layout — newspaper-style multi-column grid
- [ ] Mobile layout — single-column feed with bottom nav
- [ ] Story card component (shared logic, separate layouts)
- [ ] Homepage news feed (importance-ranked)
- [ ] Category tag filtering
- [ ] Bias indicator display on story cards
- [ ] Refresh button with confirmation
- [ ] "Last updated" timestamp
- [ ] GitHub Pages deployment

### Phase 4 — Deep Dive Dashboard (Week 9-11)
- [ ] Deep Dive Dashboard view (desktop: split-screen, mobile: full-screen modal)
- [ ] Multi-source story comparison
- [ ] Bias visualization charts (per-axis breakdowns)
- [ ] Framing analysis display
- [ ] Coverage distribution view
- [ ] Source credibility context panels

### Phase 5 — Polish & Launch (Week 12)
- [ ] Accessibility audit (WCAG 2.1 AA)
- [ ] Performance optimization (Lighthouse 90+)
- [ ] Animation polish (spring physics, micro-interactions)
- [ ] Cross-browser testing
- [ ] Mobile touch gesture refinement
- [ ] Launch

## Development Notes

- Python 3.11+ for pipeline
- Node 18+ / Next.js 14+ for frontend
- TypeScript for all frontend code
- All bias analysis must be rule-based — no external API dependencies
- Pipeline must complete within GitHub Actions time limits (~6 min for 90 sources)
- Frontend must work as a fully static site (next export)
- Supabase client-side reads only (no server-side operations from frontend)
- Animation system adapted from DondeAI (`/home/aacrit/projects/dondeAI/js/spring.js`, `motion.js`)
- CSS architecture adapted from DondeAI (`/home/aacrit/projects/dondeAI/css/tokens.css`)
- Agent definitions adapted from DondeAI/DondeBackend agent ecosystem

## Reference: DondeAI Source Files

Animation and design patterns to port/adapt:

| Source | Path | What to Adapt |
|--------|------|---------------|
| Spring presets | `/home/aacrit/projects/dondeAI/js/spring.js` | Spring configs, animate function, fallback |
| Motion utilities | `/home/aacrit/projects/dondeAI/js/motion.js` | Timeline, trackedRaf, springPress, springStagger, countUp |
| CSS tokens | `/home/aacrit/projects/dondeAI/css/tokens.css` | Duration tokens, easing curves, spacing scale |
| Animations | `/home/aacrit/projects/dondeAI/css/animations.css` | Keyframes, reduced-motion handling |
| Responsive | `/home/aacrit/projects/dondeAI/css/responsive.css` | Breakpoints, clamp() patterns, touch targets |
| Swipe cards | `/home/aacrit/projects/dondeAI/js/swipe-cards.js` | Touch gesture detection for mobile Deep Dive |
