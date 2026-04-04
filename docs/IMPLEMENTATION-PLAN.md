# void --news — Implementation Plan

**Version:** 1.3
**Last updated:** 2026-04-03 (rev 8)

12-week implementation plan across 5 phases. All work is $0 operational cost.

---

## Phase 1 — Foundation -- COMPLETE

**Deliverable:** Pipeline runs 4x daily via GitHub Actions, fetching articles from 1,013 sources into Supabase. Raw articles stored with metadata.

**What was built:** Git scaffolding, 1,013-source list (`data/sources.json`, 7-point lean spectrum, 3 tiers, 158 countries), Supabase schema (migrations 001-036), RSS fetcher (feedparser), web scraper (BeautifulSoup), Supabase client utility, pipeline orchestrator (`main.py`), GitHub Actions cron.

---

## Phase 2 — Analysis Engine -- COMPLETE

**Deliverable:** Pipeline produces fully analyzed articles with 6-axis bias scores (all with rationale JSONB), clustering, ranking v5.6/v5.7/v5.8, and Gemini integration.

**What was built:**
- Content dedup: TF-IDF + cosine similarity (threshold 0.80), Union-Find grouping
- Story clustering: two-phase (TF-IDF agglomerative threshold 0.2 + entity-overlap merge pass)
- 5-axis bias scoring (all return score + rationale): political_lean, sensationalism, opinion_detector, factual_rigor, framing (cluster-aware)
- Auto-categorization: 3-article majority vote; article_categories junction table
- Ranking v5.6: 11 signals + soft confidence curve + Gemini editorial importance (optional 12% weight) + US-only divergence damper + cross-spectrum bonus + tabloid gate + steepened time-decay
- Ranking v5.7/v5.8 (edition-unique): regional affinity boost (up to 1.5x), local-priority boost (1.40x), cross-edition demotion (0.70x/0.88x), world multi-edition boost (1.12x), thin-edition backfill, edition-level lead gate (in `main.py` + `rerank.py`)
- Multi-section cross-listing: sections[] on story_clusters (migration 011, GIN-indexed)
- Gemini Voice architecture: `_SYSTEM_INSTRUCTION` + `_USER_PROMPT_TEMPLATE` + `_PROHIBITED_TERMS` + `_check_quality()` validator; 250-350 word summaries; real outlet names in attribution
- Step 6c Gemini reasoning: contextual score adjustments on low-confidence/high-divergence clusters (`gemini_reasoning.py`; 25-call budget)
- Step 7c editorial triage: Gemini reorders top 10 per section using editorial_importance
- Op-ed handling: opinion_fact > 50 → single-article cluster, no Gemini, original text
- Axis 6 EMA tracking: source_topic_lean table, alpha=0.3
- Confidence scoring (smooth ramp: 0.1 at no text → 1.0 at 1000+ chars)
- Orphan wrapping, IP truncation (300 chars), cleanup RPCs

---

## Phase 3 — Frontend MVP -- COMPLETE (deploy pending)

**Deliverable:** Live web app on GitHub Pages with importance-ranked news feed, BiasLens Three Lenses, desktop + mobile layouts, light/dark mode, category filtering.

**What was built:**
- Next.js 16 App Router + React 19 + TypeScript
- CSS split architecture: `globals.css` → `./styles/` (tokens, layout, typography, components, animations, spectrum, mobile-feed, desktop-feed, skybox-banner, floating-player, responsive, command-center, weekly, about)
- BiasLens Three Lenses (Beam, Ring, Prism) — replaces Dot Matrix and BiasStamp (removed)
- Desktop broadsheet grid + mobile tabloid stack
- LeadStory (hero) + StoryCard (standard) + "Why This Story" tooltip
- NavBar ("Depth of Field" CTA hierarchy — edition tabs, filter lens, page links, weekly, utility), ThemeToggle, MobileBottomNav
- `/sources` page: SpectrumChart + source list with favicons
- `/paper` and `/paper/[edition]`: e-paper layout; `/command-center`: KPI dashboard
- HomeContent, PageToggle, Sigil, LogoFull/Icon/Wordmark, ScaleIcon (8 animation states)
- DesktopFeed, MobileFeed, MobileStoryCard, MobileBriefPill, DigestRow, WireCard, DailyBrief
- ErrorBoundary, LoadingSkeleton, KeyboardShortcuts, InstallPrompt, Footer, EditionIcon
- ComparativeView, DivergenceAlerts, OpEdPage, OpinionCard, SkyboxBanner, CommandCenter, StoryMeta
- FloatingPlayer, SearchOverlay, ShareCard, WeeklyDigest (weekly digest page component)
- OnboardingCarousel, OnboardingSpotlight, UnifiedOnboarding (replaced BiasLensOnboarding)
- Full favicon set (SVG, ICO, PNG), OpenGraph/Twitter meta
- Pending: Motion One spring utilities wiring, GitHub Pages deployment

---

## Phase 4 — Deep Dive Dashboard -- IN PROGRESS

**Deliverable:** Deep Dive Dashboard with unified summaries, source comparison, bias visualizations.

**Completed:**
- Slide-in panel: desktop 55% width (min 560px) from right; mobile full-screen from bottom (iOS bottom-sheet)
- Seamless lede (no "What happened" heading); viewport-responsive height; "Read more" at 600+ chars
- `dd-analysis-row`: Sigil + lean spectrum (favicons above/below gradient track) + "Press Analysis ▶" trigger in one flex row
- Press Analysis: expands inline via `grid-template-rows 0fr→1fr`; `BiasInspectorInline` (4-axis scorecard with Gemini reasoning, collapsible rows)
- Source Perspectives: Agreement | Divergence 2-column grid (desktop) / single column (mobile)
- Per-source BiasLens (sm) in source list + tier breakdown bars
- Slot-machine cascade, panel flash prevention, backdrop blur (6px desktop / 2px mobile)
- `BiasInspector.tsx`: `BiasInspectorInline` (primary), `BiasInspectorTrigger` + `BiasInspectorPanel` (legacy, backward-compat)

**Remaining:**
- Detailed framing comparison view
- Source credibility context panels

### Week 10: Remaining Bias Visualizations

| Task | Details | Agent |
|------|---------|-------|
| 10.1 | Build `FramingComparison` — keyword emphasis map: what each source emphasizes/omits | frontend-builder |
| 10.2 | Source credibility context panels — outlet tier, lean baseline, credibility note | frontend-builder |
| 10.3 | Chart entrance animations — countUp for numbers, stagger for data points | frontend-builder |
| 10.4 | Responsive chart layouts | responsive-specialist |

---

## Phase 5 — Polish & Launch

**Goal:** Production-ready quality, performance, accessibility, animation polish.

| Task | Details | Agent |
|------|---------|-------|
| 12.1 | Accessibility audit — full WCAG 2.1 AA | uat-tester + frontend-fixer |
| 12.2 | Performance audit — Lighthouse 90+, bundle size, lazy loading | perf-optimizer |
| 12.3 | Animation polish — Motion One spring wiring, stagger timing | frontend-builder |
| 12.4 | Micro-interaction polish — filter chips, BiasLens hover, theme toggle | frontend-builder |
| 12.5 | Cross-browser testing — Chrome, Firefox, Safari, Edge | frontend-fixer |
| 12.6 | Mobile touch gesture refinement — swipe thresholds, touch targets | responsive-specialist |
| 12.7 | Pipeline stability audit — error handling, retry logic, source health | pipeline-tester |
| 12.8 | Data quality audit — bias score distribution, clustering accuracy | bias-auditor |
| 12.9 | Final deploy to GitHub Pages | — |
| 12.10 | Security: address CRITICAL items from void-ciso audit (Supabase ref, anon key) before public deploy | void-ciso |

**Phase 5 Deliverable:** Production-ready void --news, live on GitHub Pages.

---

## Risk Mitigation Checkpoints

| Checkpoint | Gate |
|-----------|------|
| Pipeline reliability | 95%+ fetch success rate (currently at target) |
| Bias scoring accuracy | 80%+ accuracy on benchmark (Phase 2 complete) |
| Frontend visual quality | Lighthouse 90+, CEO visual approval |
| Deep Dive usability | Unified summaries are useful and accurate |
| Security pre-launch | 3 CRITICAL void-ciso findings resolved |
| Launch readiness | All Phase 5 checks pass |
