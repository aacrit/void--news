# void --news

Last updated: 2026-03-20 (rev 4)

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
| Summarization  | Gemini 2.5 Flash (free tier, google-genai SDK)|
| Database       | Supabase (PostgreSQL)                         |
| Frontend       | Next.js 16 (App Router), React 19, TypeScript  |
| Animation      | Motion One v11 (spring physics, ~6.5KB CDN)   |
| Styling        | CSS custom properties, mobile-first, clamp()  |
| Fonts          | Playfair Display (editorial), Inter (structural), JetBrains Mono (data) |
| Hosting        | GitHub Pages (frontend), GitHub Actions (pipeline) |

## Core Principles

### Zero Operational Cost
- No paid APIs. All bias analysis is rule-based NLP running locally in the pipeline.
- Gemini 2.5 Flash free tier for cluster summarization (1500 RPD limit, pipeline uses ~50 RPD = 25 calls/run × 2 runs).
- GitHub Actions free tier (2000 min/month private, unlimited public).
- Supabase free tier for database.
- GitHub Pages free tier for hosting.
- Motion One via CDN importmap (no npm install needed).

### Bias Analysis — The Differentiator
The bias engine analyzes **each article individually** across multiple axes. All 6 axes are implemented. Axes 1-5 return both a numeric score (0-100) and a structured rationale dict with sub-scores and evidence, stored as JSONB for hover-popup display in the frontend's "Three Lenses" visualization. Axis 6 tracks longitudinal trends per source per topic.

1. **Political Lean** — left/center/right spectrum based on keyword lexicons, entity sentiment (spaCy NER + TextBlob), framing phrases, source baseline blending (0.85 text + 0.15 baseline). Rationale includes top left/right keywords, framing phrases found, entity sentiments.
2. **Sensationalism Score** — headline clickbait pattern matching, superlative/urgency/hyperbole density, TextBlob sentiment extremity, short-sentence ratio, measured-phrase inverse signal. Rationale includes headline_score, body_score, clickbait_signals, per-100-word densities.
3. **Opinion vs. Reporting** — first-person pronouns, TextBlob subjectivity, modal/prescriptive language, hedging, attribution density (inverse), metadata markers (URL/section), rhetorical questions, unattributed value judgments. Rationale includes all 8 sub-scores, classification label, dominant signals.
4. **Factual Rigor** — named source counting (spaCy NER near attribution verbs), organization citations, data/statistics patterns, direct quote density, reference/link counting, attribution specificity vs. vague sourcing penalties. Rationale includes named_sources_count, data_points_count, direct_quotes_count, vague_sources_count, specificity_ratio.
5. **Framing Analysis** — connotation analysis (entity-sentence sentiment), charged synonym detection (50+ pairs), omission detection (one-sided sourcing + cross-article entity comparison when cluster context available), headline-body sentiment divergence, passive voice (evasive patterns + spaCy dep parsing). Rationale includes all 5 sub-scores and has_cluster_context flag.
6. **Per-Topic Per-Outlet Tracking** — EMA-based tracking (alpha=0.3) of how each source's lean, sensationalism, and opinion scores vary by topic category. Stored in `source_topic_lean` table. Updated as pipeline step 9c after each run.

All bias analysis is algorithmic/rule-based using NLP heuristics. No LLM API calls for scoring. Confidence is computed per-article based on text length, text availability, and signal strength (deviation from defaults).

### Importance Ranking — v3.2

**Design principle: ranking is BIAS-BLIND.** Bias analysis belongs in the display layer (BiasLens, Sigil, Deep Dive), not in story selection. Stories are never boosted or penalized for political lean distribution.

9-signal formula in `pipeline/ranker/importance_ranker.py` (weights sum to 1.0):

| Signal | Weight | Notes |
|--------|--------|-------|
| Source coverage breadth | 25% | Diminishing returns curve (1 - e^(-n/5)) |
| Recency (adaptive decay) | 15% | Half-life 12h standard, 15-18h for breaking news |
| Perspective diversity | 12% | Editorial viewpoint spread; bias-blind; consensus floor |
| Coverage velocity | 10% | Sources added in last 6h; age-gated (fades after 48h) |
| Consequentiality | 10% | Outcome/action verb detection via pre-compiled word-boundary regex |
| Divergence | 8% | Framing-weighted (50% framing, 30% sensationalism, 20% lean range) |
| Geographic impact | 8% | Two-phase NER: titles first, full text only if needed |
| Tier diversity | 8% | Coverage across us_major / international / independent |
| Factual density | 4% | Average factual rigor across cluster articles |

Additional modifiers:
- **Confidence multiplier**: p25 confidence across cluster articles, floor 0.4 (prevents one bad article tanking a cluster)
- **Soft-floor normalization**: `5 + raw * 0.95` replaces linear rank collapse; preserves score meaning at the top
- **Lead eligibility gate**: top 2 feed positions require 5+ sources; under-sourced stories are demoted
- **Topic diversity re-rank**: max 3 stories of the same category in top 10 per content_type pool

`pipeline/rerank.py` — standalone script to re-apply the formula to existing clusters without a full pipeline run.

Source map keyed by both slug and db_id (UUID) to prevent source resolution mismatches.

### Cluster Summarization (Gemini Flash)
Cluster headlines, summaries, and consensus/divergence points are generated by **Gemini 2.5 Flash** (free tier). Only high-value clusters qualify (3+ sources), processed in descending source-count order. Hard-capped at **25 API calls per pipeline run** (50 RPD = 3.3% of free limit). Summaries are 150-250 word comprehensive briefings; `max_output_tokens=8192` (Gemini 2.5 Flash uses thinking tokens internally). Falls back to rule-based selection (best article title/summary) when Gemini is unavailable or cap is reached.

**Gemini Voice architecture** (`cluster_summarizer.py`): Uses a persistent `_SYSTEM_INSTRUCTION` (editorial role, journalistic voice constraints) passed via `generate_json(system_instruction=...)` alongside a `_USER_PROMPT_TEMPLATE` for per-cluster context. A `_PROHIBITED_TERMS` frozenset (26 terms) and `_check_quality()` post-generation validator enforce output quality — source slugs are rendered as tier labels (e.g., "major US outlet") in prompts to prevent brand bias. `generate_json()` in `gemini_client.py` accepts an optional `system_instruction` parameter (backward-compatible, defaults to None).

### Source Curation
200 vetted sources organized in three tiers:

- **Major US Outlets (49)** — AP, Reuters, NYT, WSJ, Washington Post, Fox News, CNN, NPR, PBS, Bloomberg, Breitbart, Newsmax, Daily Wire, Washington Examiner, NY Post, etc.
- **International Outlets (67)** — BBC, Al Jazeera, DW, France24, Reuters International, The Guardian, NHK, Mexico News Daily, The Brazilian Report, Yonhap, TRT World, RT, CGTN, etc.
- **Independent/Nonprofit (84)** — ProPublica, The Intercept, Bellingcat, The Markup, Center for Public Integrity, Premium Times Nigeria, RealClearPolitics, The Free Press, Epoch Times, etc.

Political lean baseline uses a **7-point spectrum**: far-left, left, center-left, center, center-right, right, far-right. Left:Right ratio is 1.15:1 (61 left-leaning : 53 right-leaning; 86 center). All sources must meet credibility criteria before inclusion.

## Pipeline Flow (2x Daily)

```
 1.  LOAD SOURCES — Load 200 sources from data/sources.json, sync to Supabase
 2.  PIPELINE RUN — Create pipeline_runs record for tracking
 3.  FETCH        — Pull articles via RSS feeds from 200 sources (parallel)
 4.  SCRAPE       — Extract full article text via web scraper (15 parallel workers), RSS summary fallback
 4b. DEDUPLICATE  — Content-based dedup (TF-IDF + cosine similarity, threshold 0.80, Union-Find grouping)
 5.  ANALYZE      — Run 5-axis bias scoring on each article (all return score + rationale)
 6.  CLUSTER      — Group articles into story clusters (TF-IDF + entity overlap)
 6b. RE-FRAME     — Re-run framing analysis with cluster context (omission detection across articles)
     ORPHANS      — Wrap unclustered articles in single-article clusters so they appear in feed
 7b. SUMMARIZE    — Gemini Flash: 150-250 word briefings + consensus/divergence for 3+-source clusters (25-call cap)
 7.  CATEGORIZE & RANK — Auto-tag topics (3-article majority vote) + v3.2 importance ranking (9 signals + today bonus); topic diversity re-rank (max 3 per category in top 10)
 8.  STORE        — Write clusters with enrichment data, populate article_categories junction table
 9.  ENRICH       — Compute cluster-level aggregated bias data, consensus/divergence points
 9b. ARTICLE CATS — Populate article_categories junction table
 9c. TOPIC TRACK  — Update per-source per-topic tracking (Axis 6, EMA-based)
10.  TRUNCATE     — Truncate full_text to 300-char excerpts for IP compliance
     CLEANUP      — Call cleanup_stale_clusters and cleanup_stuck_pipeline_runs RPCs
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
- Mobile edge padding: `--space-5` (~16px) on `.page-main`, `.nav-inner`, `.site-footer` (not `--space-7`)
- `overflow-wrap: break-word` on all headline elements to prevent horizontal overflow
- Section header and Deep Dive source rows use `flex-wrap: wrap` on mobile

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
- `sources` — outlet metadata, credibility info, RSS/scrape config, tier (us_major/international/independent), slug
- `articles` — excerpt text (truncated post-analysis for IP compliance), metadata, source_id, publish_date, url, section, updated_at (auto-trigger)
- `bias_scores` — per-article multi-axis scores + rationale JSONB (linked to article_id)
- `story_clusters` — groups of articles about the same event; includes bias_diversity JSONB, consensus_points JSONB, divergence_points JSONB, divergence_score, headline_rank, coverage_velocity, updated_at (auto-trigger)
- `cluster_articles` — junction table linking articles to clusters
- `categories` — auto-generated topic tags
- `article_categories` — junction table linking articles to categories (populated by pipeline)
- `source_topic_lean` — per-source per-topic EMA-averaged lean/sensationalism/opinion scores, article_count (Axis 6)
- `pipeline_runs` — tracking pipeline execution history

### Key Views & Functions
- `cluster_bias_summary` — view aggregating bias scores per cluster (weighted averages, spreads)
- `refresh_cluster_enrichment(p_cluster_id)` — function computing divergence_score, bias_diversity, coverage_score, tier_breakdown
- `update_updated_at_column()` — trigger function for auto-updating updated_at on articles and story_clusters
- `cleanup_stale_clusters()` — removes clusters with no linked articles
- `cleanup_stuck_pipeline_runs()` — marks stale running pipeline entries as failed

## Skills (`.claude/skills/`)

| Skill | Purpose | Trigger |
|-------|---------|---------|
| `/pressdesign` | "Press & Precision" design system enforcement — anti-slop, typography, motion grammar, dot matrix rule, newspaper layout, responsive strategy | Auto on UI tasks, manual for design review |

**Also recommended:** Install the official Anthropic `frontend-design` plugin for additional anti-slop design foundations:
```bash
/plugin install frontend-design@claude-plugins-official
```

## Agent Team (Adapted from DondeAI — 17 Agents, 7 Divisions)

> Full team structure, R&R, and sequential cycles: `docs/AGENT-TEAM.md`

### Agent Hierarchy

```
CEO (Aacrit)
  ├── Quality ————————— analytics-expert, bias-auditor, pipeline-tester, bug-fixer
  ├── Infrastructure ——— perf-optimizer, db-reviewer, update-docs
  ├── Frontend ————————— frontend-builder, frontend-fixer, responsive-specialist, uat-tester
  ├── Pipeline ————————— feed-intelligence, nlp-engineer, source-curator
  ├── Security ————————— void-ciso
  ├── Product —————————— ceo-advisor
  └── Branding ————————— logo-designer
```

### Cost Policy — $0 Absolute Ceiling

```
ALL AI/LLM WORK USES CLAUDE CODE CLI (Max subscription).
No Anthropic API keys. No OpenAI. No paid inference. Anywhere. Ever.

Pipeline NLP:    Rule-based only (spaCy, NLTK, TextBlob) — $0
Summarization:   Gemini 2.5 Flash free tier (25 calls/run, 50 RPD) — $0
Agent work:      Claude Code CLI (opus via Max subscription) — $0
Database:        Supabase free tier — $0
Hosting:         GitHub Pages — $0
CI/CD:           GitHub Actions free tier — $0
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

### Agent Routing Rules

| Task Pattern | Agent | Division |
|---|---|---|
| RSS feed health, article collection, deduplication, cluster summaries, frontend content quality | `feed-intelligence` | Pipeline |
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
- 200-source curated list structure (3 tiers: 49 us_major + 67 international + 84 independent); 7-point political spectrum
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
│   └── GEMINI-VOICE-PLAN.md       # Gemini summary/headline voice architecture
├── pipeline/                      # Python ingestion + analysis
│   ├── fetchers/                  # RSS and scraping modules
│   │   ├── rss_fetcher.py
│   │   └── web_scraper.py
│   ├── analyzers/                 # NLP bias analysis engine (all return score + rationale)
│   │   ├── political_lean.py
│   │   ├── sensationalism.py
│   │   ├── opinion_detector.py
│   │   ├── factual_rigor.py
│   │   ├── framing.py             # Cluster-aware: accepts cluster_articles for omission detection
│   │   └── topic_outlet_tracker.py # Axis 6: EMA-based per-source per-topic tracking
│   ├── clustering/                # Story deduplication and grouping
│   │   └── deduplicator.py        # TF-IDF + cosine similarity content dedup
│   ├── summarizer/                # Gemini Flash cluster summarization
│   │   ├── gemini_client.py       # API client with rate limiting + call caps
│   │   └── cluster_summarizer.py  # Headline/summary/consensus/divergence generation
│   ├── categorizer/               # Auto-topic classification
│   ├── ranker/                    # Importance/impact scoring (v3.2: 9 signals + confidence multiplier + lead gate)
│   ├── utils/                     # Shared utilities, Supabase client, nlp_shared
│   ├── main.py                    # Pipeline orchestrator (12 steps + cleanup)
│   ├── rerank.py                  # Standalone re-ranker: apply formula changes without full pipeline run
│   └── requirements.txt
├── frontend/                      # Next.js 16 App Router
│   ├── app/
│   │   ├── components/            # React components
│   │   │   ├── BiasLens.tsx       # Three Lenses: Needle, Ring, Prism (active bias viz)
│   │   │   ├── DeepDive.tsx       # Slide-in panel: consensus/divergence, source coverage
│   │   │   ├── LeadStory.tsx      # Hero story card
│   │   │   ├── StoryCard.tsx      # Standard story card
│   │   │   ├── NavBar.tsx         # Section navigation (World/US)
│   │   │   ├── FilterBar.tsx      # Category filter chips
│   │   │   ├── RefreshButton.tsx  # Refresh with last-updated timestamp
│   │   │   ├── ThemeToggle.tsx    # Light/dark mode
│   │   │   ├── LoadingSkeleton.tsx
│   │   │   ├── ErrorBoundary.tsx
│   │   │   ├── Footer.tsx
│   │   │   ├── LogoFull.tsx       # Combination mark: void circle + scale beam icon + wordmark (single SVG, Direction 5)
│   │   │   ├── LogoIcon.tsx       # Icon-only wrapper around ScaleIcon (compact contexts, mobile nav)
│   │   │   ├── LogoWordmark.tsx   # Text-only "void --news" with hollow-O treatment (no icon mark)
│   │   │   ├── ScaleIcon.tsx      # Void Circle + Scale Beam hybrid icon; 8 animation states (idle/loading/hover/analyzing/balanced/pulse/draw/none)
│   │   │   ├── PageToggle.tsx     # Feed / Sources page switcher
│   │   │   ├── SpectrumChart.tsx  # Horizontal political spectrum bar chart (used on /sources page)
│   │   │   └── Sigil.tsx          # Compact bias sigil using SigilData type
│   │   ├── lib/
│   │   │   ├── supabase.ts        # Supabase client, fetchDeepDiveData, fetchLastPipelineRun
│   │   │   ├── types.ts           # TypeScript types (BiasScores, ThreeLensData, Story, etc.)
│   │   │   ├── mockData.ts        # Fallback mock data
│   │   │   └── utils.ts           # Helpers (timeAgo, etc.)
│   │   ├── page.tsx               # Homepage: news feed with live Supabase queries
│   │   ├── sources/
│   │   │   └── page.tsx           # /sources: spectrum visualization + source list with favicons
│   │   ├── layout.tsx             # Root layout with fonts and metadata
│   │   └── globals.css            # All styles (tokens, layout, components, animations)
│   ├── public/
│   ├── package.json               # Next.js 16.1.7, React 19.2.3
│   └── next.config.ts
├── .claude/
│   ├── agents/                    # 17 Claude agent definitions
│   └── skills/                    # pressdesign skill
├── .github/
│   └── workflows/
│       ├── pipeline.yml           # 2x daily news pipeline cron
│       ├── deploy.yml             # Frontend build + deploy to GitHub Pages
│       └── migrate.yml            # Supabase migration runner
├── data/
│   └── sources.json               # 200 curated sources with RSS URLs and metadata (7-point lean spectrum)
└── supabase/
    ├── config.toml
    └── migrations/                # Database schema migrations (001-009)
```

## MVP Scope

### Phase 1 — Foundation (Week 1-2) -- COMPLETE
- [x] Project scaffolding (Next.js, Python pipeline, Supabase)
- [x] Source list curation (200 sources with RSS/scrape configs; 7-point lean spectrum)
- [x] Supabase schema setup (all tables + migrations 001-009)
- [x] Basic RSS fetcher (feedparser)
- [x] Basic web scraper (BeautifulSoup)
- [x] Article storage pipeline
- [x] GitHub Actions cron (2x daily)
- [x] Pipeline orchestrator (main.py)

### Phase 2 — Analysis Engine (Week 3-5) -- COMPLETE
- [x] Content-based deduplication (TF-IDF + cosine similarity, threshold 0.80, Union-Find grouping)
- [x] Story clustering algorithm
- [x] Political lean scoring (with rationale)
- [x] Sensationalism detection (with rationale)
- [x] Opinion vs. reporting classifier (with rationale)
- [x] Factual rigor scoring (with rationale)
- [x] Framing analysis (cluster-aware omission detection, with rationale)
- [x] Auto-categorization (topic tagging, 3-article majority vote) + article_categories junction table populated
- [x] Importance/impact ranking (v3.2: 9 signals + confidence multiplier + lead eligibility gate)
- [x] Confidence scoring per article
- [x] Consensus/divergence generation per cluster
- [x] IP compliance: full_text truncation post-analysis
- [x] Per-topic per-outlet tracking (Axis 6, EMA-based, source_topic_lean table)

### Phase 3 — Frontend MVP (Week 6-8) -- COMPLETE
- [x] Next.js project setup with TypeScript (App Router, Next.js 16)
- [x] Design token system (CSS custom properties in globals.css)
- [ ] Animation system (Motion One spring presets, utilities)
- [x] Desktop layout — newspaper-style multi-column grid
- [x] Mobile layout — single-column feed
- [x] Story card component (LeadStory + StoryCard)
- [x] Homepage news feed (importance-ranked via headline_rank)
- [x] "Why This Story" tooltip on StoryCard + LeadStory (derives top ranking signals from story data)
- [x] Category tag filtering (FilterBar)
- [x] Bias indicator display on story cards (BiasLens: Three Lenses)
- [x] Refresh button with last-updated timestamp (RefreshButton)
- [x] "Last updated" timestamp
- [x] Light/dark mode (ThemeToggle)
- [ ] GitHub Pages deployment

### Phase 4 — Deep Dive Dashboard (Week 9-11) -- IN PROGRESS
- [x] Deep Dive Dashboard view (slide-in panel, mobile full-screen)
- [x] Multi-source story comparison (per-source BiasLens in Deep Dive)
- [x] Coverage distribution view (tier breakdown bars)
- [x] Consensus/divergence display (pipeline-generated, read from JSONB)
- [ ] Framing analysis display (detailed framing comparison)
- [ ] Source credibility context panels

### Phase 5 — Polish & Launch (Week 12)
- [ ] Accessibility audit (WCAG 2.1 AA)
- [ ] Performance optimization (Lighthouse 90+)
- [ ] Animation polish (spring physics, micro-interactions)
- [ ] Cross-browser testing
- [ ] Mobile touch gesture refinement
- [ ] Launch

## Git Workflow

- **Always push to `claude/*` branches** (e.g., `claude/feature-name`). Never push directly to `main`.
- GitHub auto-merge is enabled — pushing to `claude/*` auto-creates a PR and merges to `main`.
- No need to manually create PRs, merge, or push to `main`. Just push to `claude/*` and it handles the rest.

## Development Notes

- Python 3.11+ for pipeline
- Node 18+ / Next.js 16 (App Router) for frontend
- TypeScript for all frontend code
- All bias analysis must be rule-based — no external API dependencies
- Pipeline must complete within GitHub Actions time limits (~6 min for 200 sources)
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
