# void --news — Implementation Plan

**Version:** 1.1
**Last updated:** 2026-03-19 (rev 2)

---

## Overview

12-week implementation plan across 5 phases. Each phase has clear deliverables and dependencies. All work is $0 operational cost.

---

## Phase 1 — Foundation (Week 1-2) -- COMPLETE

**Goal:** Working pipeline that fetches articles from 200 sources and stores them in Supabase.

### Week 1: Scaffolding + Source List

| Task | Details | Agent |
|------|---------|-------|
| 1.1 | Initialize Git repo (`void--news`), project structure per CLAUDE.md | — |
| 1.2 | Curate 30 Major US Outlets with RSS URLs, scrape configs, credibility metadata | source-curator |
| 1.3 | Curate 30 International Outlets (same) | source-curator |
| 1.4 | Curate 30 Independent/Nonprofit Outlets (same) | source-curator |
| 1.5 | Write `data/sources.json` schema: name, url, rss_url, scrape_config, tier, country, credibility_score | source-curator |
| 1.6 | Set up Supabase project, create initial schema migration | db-reviewer |
| 1.7 | Set up Python virtual environment, `requirements.txt` (feedparser, beautifulsoup4, spacy, nltk, textblob, supabase-py) | — |

### Week 2: Fetcher + Storage + GitHub Actions

| Task | Details | Agent |
|------|---------|-------|
| 2.1 | Build RSS fetcher (`pipeline/fetchers/rss_fetcher.py`) — feedparser, parallel fetching, error handling | nlp-engineer |
| 2.2 | Build web scraper (`pipeline/fetchers/web_scraper.py`) — BeautifulSoup, article text extraction, fallback for non-RSS sources | nlp-engineer |
| 2.3 | Build article parser — extract title, body, author, publish_date, url from raw fetched content | nlp-engineer |
| 2.4 | Build Supabase client utility (`pipeline/utils/supabase_client.py`) — insert articles, upsert sources | — |
| 2.5 | Build pipeline orchestrator (`pipeline/main.py`) — fetch → parse → store, with logging and error handling | nlp-engineer |
| 2.6 | Set up GitHub Actions workflow (`.github/workflows/pipeline.yml`) — cron 2x daily (6 AM, 6 PM UTC) | — |
| 2.7 | Test pipeline end-to-end: 200 sources → Supabase with real articles | pipeline-tester |

**Phase 1 Deliverable:** Pipeline runs 2x daily via GitHub Actions, fetching articles from 200 sources into Supabase. Raw articles stored with metadata.

**Dependencies:** Supabase account (existing), GitHub repo created.

---

## Phase 2 — Analysis Engine (Week 3-5) -- COMPLETE

**Goal:** Full 6-axis bias scoring (axes 1-5 with rationale, axis 6 longitudinal tracking), content deduplication, story clustering, categorization, importance ranking, consensus/divergence generation, and IP compliance truncation.

**Additions beyond original plan:**
- All 5 per-article analyzers now return structured rationale dicts (sub-scores + evidence) stored as JSONB
- Framing analyzer is cluster-aware: step 6b re-runs framing with cluster context for cross-article omission detection
- Content-based deduplication (step 4b) using TF-IDF + cosine similarity (threshold 0.85) with Union-Find transitive grouping; keeps higher-tier source articles
- Gemini Flash summarization (step 7b): `pipeline/summarizer/` module (`gemini_client.py` + `cluster_summarizer.py`) generates headlines, 150-250 word summaries, consensus/divergence for clusters with 3+ sources using `gemini-2.5-flash` via `google-genai` SDK; hard-capped at 25 calls/run (50 RPD = 3.3% of 1500 RPD free tier); `max_output_tokens=8192`; clusters processed by source_count descending; falls back to rule-based when unavailable or cap reached
- Per-topic per-outlet tracking (Axis 6, step 9c): EMA-based (alpha=0.3) tracking in `source_topic_lean` table
- Pipeline generates consensus/divergence points per cluster from bias score distributions
- article_categories junction table populated by pipeline
- Cleanup RPCs (stale clusters, stuck pipeline runs) called at end of each run
- Full-text truncated to 300-char excerpts post-analysis for IP compliance
- Confidence scoring per article (text length + availability + signal strength)
- Source list expanded to 200 sources (us_major=49, international=67, independent=84); 7-point political lean spectrum (far-left → far-right); left:right ratio fixed to 1.15:1
- Orphan article detection: unclustered articles wrapped in single-article clusters so they appear in feed
- Junk title filters expanded: 9 additional patterns in rss_fetcher.py (Economist section pages, Yonhap digests, crosswords, obituaries)
- Truncation step switched from upsert to UPDATE to avoid NOT NULL violations
- `first_published` sends None instead of empty string to avoid invalid timestamp errors
- `_gemini_enriched` flag on cluster dicts survives sort-order changes
- DB cleanup: updated_at auto-triggers on articles/story_clusters, redundant indexes dropped (migrations 005-007)
- `google-genai>=1.0.0` added to `requirements.txt`; `GEMINI_API_KEY` env var added to pipeline.yml and `.env`

### Week 3: Deduplication + Clustering

| Task | Details | Agent |
|------|---------|-------|
| 3.1 | Build deduplication module — TF-IDF cosine similarity on headlines + first paragraph, threshold-based duplicate detection | nlp-engineer |
| 3.2 | Build story clustering algorithm — group articles about the same event using TF-IDF + named entity overlap | nlp-engineer |
| 3.3 | Build cluster metadata — generate cluster headline (most common entities), source count, time range | nlp-engineer |
| 3.4 | Add `story_clusters` and `cluster_articles` tables to Supabase | — |
| 3.5 | Integration test: feed 50+ articles, verify correct clustering | pipeline-tester |

### Week 4: Bias Scoring Engine (Axes 1-4)

| Task | Details | Agent |
|------|---------|-------|
| 4.1 | **Political Lean** (`analyzers/political_lean.py`) — keyword lexicons (partisan vocabulary), source baseline weighting, sentiment toward political entities, framing patterns | nlp-engineer |
| 4.2 | **Sensationalism** (`analyzers/sensationalism.py`) — headline clickbait patterns, emotional word density, exclamation/question marks, superlatives, urgency language | nlp-engineer |
| 4.3 | **Opinion vs. Reporting** (`analyzers/opinion_detector.py`) — first-person pronouns, subjective adjectives, attribution presence, hedging language, "should/must" imperatives | nlp-engineer |
| 4.4 | **Factual Rigor** (`analyzers/factual_rigor.py`) — citation/source counting, data/statistics presence, named source attribution, quote density, "according to" patterns | nlp-engineer |
| 4.5 | Add `bias_scores` table to Supabase, link to articles | — |
| 4.6 | Unit tests for each analyzer with known articles | pipeline-tester |

### Week 5: Framing Analysis + Categorization + Ranking

| Task | Details | Agent |
|------|---------|-------|
| 5.1 | **Framing Analysis** (`analyzers/framing.py`) — keyword emphasis detection (what words/entities appear most), omission detection (what other cluster sources mention that this one doesn't), connotation analysis (positive/negative word choice for same entities) | nlp-engineer |
| 5.2 | **Auto-Categorization** (`categorizer/`) — topic classification using keyword matching + named entity categories (Politics, Economy, Tech, Health, Environment, Conflict, Science, Culture, Sports) | nlp-engineer |
| 5.3 | **Importance Ranking** (`ranker/`) — composite score: source coverage breadth × editorial weight (top outlets per bias tier) × recency decay × geographic impact estimation | nlp-engineer |
| 5.4 | **Editorial Weight Model** — top outlets in each bias category get higher importance multiplier; cross-spectrum coverage (left + center + right all covering it) gets maximum boost | nlp-engineer |
| 5.5 | **Gemini Flash summarization** (`summarizer/gemini_client.py` + `cluster_summarizer.py`) — step 7b: generate headlines, 150-250 word summaries, consensus/divergence for 3+-source clusters using `gemini-2.5-flash`; 25-call/run cap, descending source_count priority, rule-based fallback | nlp-engineer |
| 5.6 | Integrate all analyzers into pipeline orchestrator: fetch → parse → deduplicate → cluster → analyze → re-frame → rank → summarize → categorize → store → enrich | nlp-engineer |
| 5.7 | End-to-end pipeline test with full analysis | pipeline-tester |
| 5.8 | Benchmark bias scoring against manually labeled test set (50 articles) | bias-auditor |

**Phase 2 Deliverable:** Pipeline produces fully analyzed articles with 6-axis bias scores (5 per-article + longitudinal per-source-per-topic tracking), content deduplication, story clusters, categories, and importance rankings. All stored in Supabase.

**Dependencies:** Phase 1 complete (articles in Supabase).

---

## Phase 3 — Frontend MVP (Week 6-8) -- COMPLETE

**Goal:** Responsive web app with news feed, bias indicators, desktop + mobile layouts.

**Implementation notes:**
- Built with Next.js 16 App Router (not pages router) + React 19
- BiasLens "Three Lenses" visualization (Needle, Ring, Prism) replaces earlier Dot Matrix concept
- BiasStamp.tsx (517 lines) removed as dead code, superseded by BiasLens
- Supabase functions fetchClusterBiasSummary and fetchArticlesForCluster removed (unused)
- pg server-side package removed (unnecessary dependency)
- Fallback bias display shows dimmed/pending state when using placeholder values
- RefreshButton rendered in section header area
- `/sources` page added: horizontal SpectrumChart visualization + source list with favicons and hover tooltips; mobile uses vertical layout
- PageToggle component: switches between Feed and Sources views
- Sigil component: compact bias sigil using SigilData type
- DeepDive: source icons moved to compact favicons under headline (verbose source list removed)
- BiasLens: optional chaining on rationale array properties (crash fix); Array.isArray guards on consensus/divergence
- Lead stories layout: two equal-width cards (1fr 1fr desktop, stacked mobile)
- Footer: Source link removed; "Built with transparency" line removed; copyright added
- Empty state: "The Presses Are Warming Up" with morning/evening edition messaging
- All "90/97 sources" UI references updated to "200 sources"

### Week 6: Project Setup + Design System

| Task | Details | Agent |
|------|---------|-------|
| 6.1 | Initialize Next.js 14+ project with TypeScript, static export config | frontend-builder |
| 6.2 | Implement CSS token system (`styles/tokens.css`) — all design tokens from DESIGN-SYSTEM.md | frontend-builder |
| 6.3 | Implement CSS reset, typography, layout foundations | frontend-builder |
| 6.4 | Port Motion One spring presets and animation utilities from DondeAI (adapted for React) | frontend-builder |
| 6.5 | Set up Supabase client (`lib/supabase.ts`) — read-only queries for articles, clusters, bias scores | frontend-builder |
| 6.6 | Build `useDeviceType()` hook — media query detection for layout switching | frontend-builder |
| 6.7 | Build `DesktopLayout` and `MobileLayout` wrapper components | frontend-builder |
| 6.8 | Implement light/dark mode with theme toggle (CSS custom properties swap via `data-mode` attribute) | frontend-builder |
| 6.9 | Logo design | logo-designer |

### Week 7: Story Cards + News Feed

| Task | Details | Agent |
|------|---------|-------|
| 7.1 | Build `DotMatrix` component — 5 dots with color/shape encoding, hover tooltips (desktop), tap bottom sheet (mobile) | frontend-builder |
| 7.2 | Build `StoryCard` shared logic — data fetching, bias score display, category tag | frontend-builder |
| 7.3 | Build `StoryCardDesktop` — multi-column layout, inline dot matrix, hover interactions | frontend-builder |
| 7.4 | Build `StoryCardMobile` — full-width, tap interactions, vertical stack | frontend-builder |
| 7.5 | Build `LeadStory` — hero card with large typography and prominent dot matrix | frontend-builder |
| 7.6 | Build Homepage news feed — importance-ranked organic flow, load from Supabase | frontend-builder |
| 7.7 | Build desktop broadsheet grid layout (lead + medium + compact cards) | responsive-specialist |
| 7.8 | Build mobile tabloid stack layout | responsive-specialist |
| 7.9 | Card entrance animations — fadeInUp with stagger (from DondeAI springStagger) | frontend-builder |

### Week 8: Filtering + Polish + Deploy

| Task | Details | Agent |
|------|---------|-------|
| 8.1 | Build `FilterBar` — category tag filter chips (desktop: horizontal in header, mobile: bottom sheet) | frontend-builder |
| 8.2 | Build World News / US News section tabs | frontend-builder |
| 8.3 | Build `RefreshButton` with confirmation dialog | frontend-builder |
| 8.4 | Build "Last updated" timestamp display | frontend-builder |
| 8.5 | Build `NavBar` — desktop top nav, mobile bottom nav | frontend-builder |
| 8.6 | Build `ThemeToggle` — light/dark mode switch with cross-fade animation | frontend-builder |
| 8.7 | Set up GitHub Pages deployment workflow (`.github/workflows/deploy.yml`) | — |
| 8.8 | Cross-device testing (375px, 768px, 1024px, 1440px) | responsive-specialist |
| 8.9 | Accessibility audit — keyboard nav, screen reader, reduced motion | accessibility-inclusivity-lead |

**Phase 3 Deliverable:** Live web app on GitHub Pages showing importance-ranked news feed with bias dot matrix, desktop + mobile layouts, light/dark mode, category filtering.

**Dependencies:** Phase 2 complete (analyzed articles in Supabase).

---

## Phase 4 — Deep Dive Dashboard (Week 9-11) -- IN PROGRESS

**Goal:** Story clustering view with unified summaries, source comparison, bias visualizations.

**Completed:**
- Deep Dive slide-in panel (desktop 50% width from right, mobile full-screen from bottom)
- Pipeline-generated consensus/divergence points displayed (from JSONB columns, not hardcoded)
- Per-source BiasLens with rationale popups in source list
- Coverage breakdown by tier (US Major / International / Independent)
- Live data fetching from Supabase (cluster_articles -> articles -> bias_scores with rationale)

**Remaining:**
- Detailed framing comparison view
- Source credibility context panels

### Week 9: Unified Summary + Source List

| Task | Details | Agent |
|------|---------|-------|
| 9.1 | Build `UnifiedSummary` component — synthesized narrative from cluster articles: what happened, where sources agree, where they diverge | frontend-builder |
| 9.2 | Build summary generation logic — extract consensus points (entities/facts appearing in 80%+ of sources) and divergence points (facts/framing unique to <30% of sources) | nlp-engineer |
| 9.3 | Add summary data to pipeline: generate unified summary per cluster, store in Supabase | nlp-engineer |
| 9.4 | Build `SourceList` component — all sources covering this story, each with dot matrix and link to original article | frontend-builder |
| 9.5 | Build `DeepDiveDesktop` — right panel or split-screen layout | frontend-builder |
| 9.6 | Build `DeepDiveMobile` — full-screen modal with swipe-to-dismiss | frontend-builder |

### Week 10: Bias Visualizations

| Task | Details | Agent |
|------|---------|-------|
| 10.1 | Build `CoverageDistribution` — visual showing which source tiers (US/International/Independent) and bias leans are covering this story | data-storytelling-designer + frontend-builder |
| 10.2 | Build `BiasSpread` — dot density visualization showing distribution of political lean across all sources in the cluster | data-storytelling-designer + frontend-builder |
| 10.3 | Build `FramingComparison` — side-by-side keyword emphasis map: what each source emphasizes/omits | data-storytelling-designer + frontend-builder |
| 10.4 | Chart entrance animations — countUp for numbers, stagger for data points | frontend-builder |
| 10.5 | Responsive chart layouts — inline on desktop, full-width stacked on mobile | responsive-specialist |

### Week 11: Integration + Navigation

| Task | Details | Agent |
|------|---------|-------|
| 11.1 | Wire story card → Deep Dive navigation (click story opens deep dive view) | frontend-builder |
| 11.2 | Deep Dive view transitions — slide from right (desktop), slide from bottom (mobile) | frontend-builder |
| 11.3 | Source link handling — tap source → opens original article in new tab | frontend-builder |
| 11.4 | Back navigation — return to feed with preserved scroll position | frontend-builder |
| 11.5 | Deep dive data fetching — load cluster details, all source articles, pre-computed summaries | frontend-builder |
| 11.6 | Mobile gesture support — swipe to dismiss deep dive, horizontal swipe between sources | frontend-builder |

**Phase 4 Deliverable:** Deep Dive Dashboard with unified summaries, source comparison with dot matrices, bias visualizations, and responsive layouts.

**Dependencies:** Phase 3 complete (frontend deployed), Phase 2 cluster/summary data.

---

## Phase 5 — Polish & Launch (Week 12)

**Goal:** Production-ready quality, performance, accessibility, animation polish.

### Week 12: Final Quality Pass

| Task | Details | Agent |
|------|---------|-------|
| 12.1 | Accessibility audit — full WCAG 2.1 AA compliance check | accessibility-inclusivity-lead |
| 12.2 | Performance audit — Lighthouse 90+, bundle size check, lazy loading for below-fold content | perf-optimizer |
| 12.3 | Animation polish — spring physics tuning, stagger timing, transition smoothness | motion-physics-designer + frontend-builder |
| 12.4 | Micro-interaction polish — filter chip interactions, dot hover/tap, theme toggle, refresh confirm | micro-interaction-designer + frontend-builder |
| 12.5 | Cross-browser testing — Chrome, Firefox, Safari, Edge (desktop + mobile) | frontend-fixer |
| 12.6 | Mobile touch gesture refinement — swipe thresholds, scroll behavior, touch targets | responsive-specialist |
| 12.7 | Pipeline stability audit — error handling, retry logic, source health monitoring | pipeline-tester |
| 12.8 | Data quality audit — bias score distribution, clustering accuracy, ranking sanity | bias-auditor |
| 12.9 | Final deploy to GitHub Pages | — |
| 12.10 | Update all documentation | — |

**Phase 5 Deliverable:** Production-ready void --news, live on GitHub Pages.

---

## Agent Deployment Schedule

| Phase | Active Agents |
|-------|--------------|
| 1 | source-curator, db-reviewer, nlp-engineer, pipeline-tester |
| 2 | nlp-engineer, pipeline-tester, bias-auditor |
| 3 | frontend-builder, responsive-specialist, logo-designer, accessibility-inclusivity-lead |
| 4 | frontend-builder, responsive-specialist, data-storytelling-designer, nlp-engineer |
| 5 | All agents for final quality pass |

---

## Risk Mitigation Checkpoints

| Checkpoint | When | Gate |
|-----------|------|------|
| Source list review | End of Week 1 | 200 sources with valid RSS/scrape configs |
| Pipeline reliability | End of Week 2 | 95%+ fetch success rate |
| Bias scoring accuracy | End of Week 5 | 80%+ accuracy on 50-article benchmark |
| Frontend visual quality | End of Week 8 | Lighthouse 90+, CEO visual approval |
| Deep Dive usability | End of Week 11 | Unified summaries are useful and accurate |
| Launch readiness | End of Week 12 | All Phase 5 checks pass |
