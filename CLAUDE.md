# void --news

Last updated: 2026-04-06 (rev 33)

> **Read this file first. Only read other docs when task-relevant. Only open source files when modifying code.**

News aggregation platform with per-article, 6-axis rule-based NLP bias analysis. 1,013 curated sources across 158 countries. World edition (regional editions parked pre-launch).

## Architecture

```
GitHub Actions (3x daily cron) → Python Pipeline → Supabase (PostgreSQL) ← Next.js Static Site (GitHub Pages)
```

No backend server. Python pipeline on Actions, Next.js static export on Pages, Supabase as single data layer.

**Tech**: Python/spaCy/NLTK/TextBlob (NLP), Gemini 2.5 Flash free tier (summaries + TTS), Supabase (PostgreSQL), Next.js 16/React 19/TypeScript, Motion One v11 (CDN), CSS custom properties. Fonts: Playfair Display / Inter / Barlow Condensed / IBM Plex Mono.

## Core Principles

### Show, Don't Tell — The Cardinal Rule (Fiction Writing)
All generated text MUST embody show-don't-tell. Never assert significance — juxtapose concrete facts so the reader sees the pattern. Never use "notable," "significant," "it should be noted," "interestingly," "crucially." Use specific numbers, names, dates, actions. Present evidence. Let the reader conclude.

**BAD:** "It is worth noting that tensions are rising significantly between the two nations."
**GOOD:** "Both countries recalled their ambassadors within 48 hours. Neither has done that since 1979."

Applies to: all generated text — `cluster_summarizer.py`, `daily_brief_generator.py`, `claude_brief_generator.py`, void --history perspectives, CTAs, and all future content.

### Arrive Late, Leave Early — The Screenplay Rule
Enter every scene at the last possible moment. Exit before the conclusion is spelled out. Don't set up context before the action — drop the reader INTO the action. Don't summarize at the end — cut when the point lands. The user's brain completes the story.

**BAD:** "The Partition of India was a complex historical process that began with British colonial rule and eventually led to the creation of two nations in 1947, resulting in massive displacement."
**GOOD:** "A lawyer who'd never been to India drew the border in five weeks. 15 million crossed it."

Applies to: void --history event pages (start with the crack, not the background), daily briefs (lead with the action), CTAs (pose the contradiction, don't promise the answer), audio scripts (open mid-scene). These two rules together — Show Not Tell + Arrive Late Leave Early — create the cognitive gap where understanding happens. The user doesn't receive a conclusion. They arrive at one.

### Product Family Branding
CLI-style naming: `void --news` (platform), `void --tl;dr` (daily brief), `void --onair` (audio), `void --opinion` (editorial), `void --sources` (spectrum), `void --deep-dive` (analysis), `void --paper` (e-paper), `void --weekly` (magazine digest), `void --history` (the archive). Subtitles show on first encounter (sessionStorage) then fade.

### No Personalization — The Newspaper Principle
void --news is a newspaper, not a feed. Every reader sees the same stories in the same order. The engine decides what is shown based on editorial importance, not user behavior. No reading history tracking, no recommendation algorithms, no "for you" logic, no user accounts. This is a locked architectural decision. Features that adapt content to individual consumption patterns violate the platform's core philosophy.

### Zero Operational Cost
$0. All bias analysis is rule-based NLP. Gemini Flash free tier (~116/1500 RPD). GitHub Actions + Supabase + Pages all free tier. Motion One via CDN importmap.

### Bias Analysis — 6 Axes
Per-article, score 0-100 + structured rationale JSONB. No LLM calls for scoring.

1. **Political Lean** — keyword lexicons, entity sentiment (NER + TextBlob), framing phrases, length-adaptive + sparsity-weighted source baseline blending. See `political_lean.py`.
2. **Sensationalism** — clickbait patterns, superlative density (word-boundary regex), TextBlob extremity, partisan attack density (capped 30pts). See `sensationalism.py`.
3. **Opinion vs. Reporting** — pronouns, subjectivity, attribution density (24 investigative patterns), value judgments, rhetorical questions. See `opinion_detector.py`.
4. **Factual Rigor** — named sources (NER + attribution verbs), org citations, data patterns, quotes, vague-source penalty. LOW_CREDIBILITY_US_MAJOR (5 slugs) baseline 35. See `factual_rigor.py`.
5. **Framing** — charged synonyms (50+ pairs), cluster-aware omission detection, headline-body divergence, passive voice (capped 30). See `framing.py`.
6. **Per-Topic Per-Outlet EMA** — adaptive alpha (0.3 new / 0.15 established). Stored in `source_topic_lean`. See `topic_outlet_tracker.py`.

### Validation Framework (`pipeline/validation/`)
42 ground-truth articles, 8 categories, 100% accuracy. Cross-axis correlation gate (r<0.70). CI gate via `.github/workflows/validate-bias.yml`.
```bash
python pipeline/validation/runner.py              # Full validation
python pipeline/validation/runner.py --quick      # Skip distribution checks
python pipeline/validation/runner.py --verbose    # Per-signal decomposition
python pipeline/validation/runner.py --update-snapshot  # Refresh regression baseline
```

### Importance Ranking — v6.0 + Edition-Unique
**BIAS-BLIND.** 10-signal formula in `pipeline/ranker/importance_ranker.py` (weights sum to 1.0): source breadth 20%, maturity 16%, tier diversity 13%, consequentiality 10%, institutional authority 8%, factual density 8%, divergence 7%, perspective diversity 9%, geographic impact 6%, velocity 3%. Plus Gemini editorial importance additive adjustment, gates (confidence, consequentiality, soft-news, tabloid, factual rigor, lead eligibility), topic diversity re-rank, same-event cap, steepened time-decay. v6.0 changes: lean_diversity (3%) merged into perspective_diversity (6%->9%), divergence purified to framing (62.5%) + sensationalism (37.5%) only (lean-range removed), high-authority consequentiality floor (authority >= 80 + consequentiality < 5 -> floor 30), thin cluster gate removed from base ranker.

**Edition-unique ranking** (in `pipeline/ranker/edition_ranker.py`, imported by both `main.py` and `rerank.py`): regional affinity boost (up to 1.5x, quality-capped for <5 sources), local-priority boost (1.40x edition-exclusive), cross-edition demotion (0.70x, milder 0.88x for globally significant 20+ source/3+ edition stories), world multi-edition boost (1.12x for 3+ edition stories), edition-level lead gate (3+ sources for top 10), thin-edition backfill (imports from world when <10 quality stories), same-event cap, story-type gates, regional keyword boost. Processing order: regional first (us -> europe -> south-asia), then world.

### Cluster Summarization
3+-source clusters, 25-call Gemini cap/run, 250-350 words. Falls back to rule-based. Op-eds (opinion_fact > 50): single-article, no Gemini.

### Daily Brief — "void --onair"
World-focused, top 20 clusters. **TL;DR**: 8-12 sentences editorial paragraph (150-220 words), joint board voice. **Opinion**: 3-5 sentences first-person-plural editorial judgment (lean rotates daily: left/center/right). **Audio**: BBC two-host format, `A:`/`B:` speaker tags (no segment markers), Gemini 2.5 Flash TTS (native multi-speaker, single API call), pydub post-processing (Glass & Gravity sonic identity, subharmonic presence layer at -34 to -42 dB), MP3 96k mono → Supabase Storage. 5 rotating host pairs shared across all editions (not edition-specific); opinion voice fixed per edition. Stored in `daily_briefs` table: `audio_duration_seconds`, `audio_file_size`, `audio_voice` columns. 5 calls/run (separate from 25-call cap). Claude CLI premium scripts optional (`claude_brief_generator.py`, generates TL;DR + opinion + audio in one call).

### Source Curation
1,013 sources, 3 tiers: us_major (43), international (373), independent (597). 7-point lean spectrum. L:R ratio 1.20:1. 38 wire services, 10 fact-checkers. Editions: world (default), us, europe, south-asia. 158 countries. Source country determines edition via `_COUNTRY_EDITION_MAP` in `main.py`.

## Pipeline Flow (3x Daily — 7 AM / 2 PM / 8 PM Chicago)

```
 1. LOAD SOURCES → 2. PIPELINE RUN → 3. FETCH RSS → 4. SCRAPE → 4b. DEDUP
 5. ANALYZE (5-axis) → 6. CLUSTER (TF-IDF + entity merge) → 6b. RE-FRAME
 6c. GEMINI REASON → 7b. SUMMARIZE → 7. CATEGORIZE & RANK → 7c. EDITORIAL TRIAGE
 7d. DAILY BRIEF (TL;DR + audio) → 8. STORE → 8b. DEDUP CLUSTERS
 8c. HOLISTIC RE-RANK (all clusters, v6.0 engine)
 9. ENRICH → 9a. MEMORY ENGINE → 9b. ARTICLE CATS → 9c. TOPIC TRACK → 10. TRUNCATE + CLEANUP
```

All 3 runs generate audio. TTS budget: 3 runs × ~16 calls = ~48/day (within 100 RPD).

## Frontend Design

### "Cinematic Press" (Press & Precision v2)
Editorial authority + cinematic depth, light, focus, atmosphere. **Clean on arrival, data-dense on interaction.** Progressive disclosure. Cinematic tokens in `tokens.css`: `--cin-amber` palette (amber/ash/paper tones, light+dark), `--ease-cinematic`/`--ease-whip`/`--ease-rack` easings, `--z-cinematic`, film grain (`--cin-grain-opacity`, numOctaves=3), vignette (`--cin-vignette-color`, z-index above grain), color grade (`--cin-grade`, applied to `.page-main` + `.nav-header` not `.page-container`), rack focus, atmospheric haze (`--cin-haze-far`), backdrop (`--cin-backdrop-bg/blur`), practical warmth (`--cin-practical-warmth`). Cold open stagger (nav 80ms, skybox 200ms, lead 320ms, feed 480ms), direction-aware whip pan (edition switch), golden hour pulse (theme toggle, 700ms). Spring physics (Motion One) for user actions, ease-out for reveals.

**Four type voices**: Editorial (Playfair Display), Structural (Inter), Meta (Barlow Condensed, `--font-meta`), Data (IBM Plex Mono).

**Navigation — "Depth of Field" CTA Hierarchy (v2)**: Two-row structure with 5 visual layers. **Row 1 (Chrome)**: Logo, dateline + timestamp, page links (`.nav-pages`, `.nav-page`) — Inter uppercase, departure arrow `→` on hover (Sources, Ship, About), **Weekly** (`.nav-weekly`) — Playfair italic, deep red accent (`#B91C1C` light / `#EF5350` dark), vertical rule spine glow + unfold physics on hover, ThemeToggle. **Row 2 (Lens)**: Edition tabs (`.nav-lens__editions`, `.nav-ed`) — Playfair Display, warm `--cin-amber` underline, `hapticConfirm`; hidden on mobile. Filter Lens (`.nav-lens`, `.nav-lens__*`) — IBM Plex Mono, bracket notation `[ topics ]` `[ ·left ·center ·right ]`, dotted underline active state, `--ease-rack`, `hapticMicro`; hidden on mobile. Search bar (`.nav-lens__search`) — expandable (160px compact, 280px on focus), `Cmd+K` kbd hint, opens SearchOverlay. Row 2 has inset shadow texture (recessed behind Row 1). Nav onair button removed (floating player is single audio entry point).

```
Row 1 (Chrome): [Logo] [dateline] [Sources Ship About] [Weekly] [Theme]
Row 2 (Lens):   [World US Europe South-Asia] [ topics ▾ ] [ ·L ·C ·R ] [Search...]
```

**Responsive**: desktop = multi-column newspaper grid, top nav. Mobile = single-column feed, bottom nav, bottom sheets. Touch targets 44px+. Breakpoints: 375/768/1024/1440px.

### Homepage
Importance-ranked feed with category and lean filtering (bracket notation in NavBar Row 2 filter lens). Edition sections: World/US/Europe/South Asia (NavBar Row 2 typographic tabs). Expandable search bar in Row 2 (160px compact, 280px on focus, Cmd+K hint). Daily Brief between nav and Lead Section (blockquote left-border, justified, opinion behind dotted firewall rule). "void --onair" persistent bottom audio player + progress bar.

### Deep Dive
Centered popup (desktop 75vw, 80vh; mobile full-screen bottom sheet). Summary as lede (ResizeObserver overflow). Analysis row: Sigil + DeepDiveSpectrum (7-zone gradient, logos at exact lean %) + Press Analysis trigger. BiasInspectorInline (4-axis scorecard). ScoringMethodology ("How we score" collapsible dl/dt/dd, 6 axes). Source Perspectives (agree/diverge grid). FLIP morph animation: double-rAF for open (card rect via `data-story-id` attribute on StoryCard/LeadStory/MobileStoryCard), reverse morph on close (finds source card via DOM query), slide-in fallback when no source rect. Cinematic dramatic shadow, data-settled studio reflection.

### Weekly Page — "void --weekly"
Magazine-style weekly digest at `/weekly`. **No NavBar** — uses its own sticky topbar (`.wk-topbar`) with `<- [LogoFull]` back link + ThemeToggle (glass blur background). Deep red magazine palette: `--wk-accent: #B91C1C` light / `#EF5350` dark (Economist/TIME inspired). Warmer matte paper background: `#EDE4D0` light (vs main feed `#F0EBDD`), `#1E1A16` dark (vs `#151310`). Film grain at 3x base opacity, tighter vignette (30% start). Sections: red masthead banner (full void logo in cream), cover hero (headline in red accent on page background, organic ink rule, up to 2 stories with drop cap + justified text), timeline (horizontal desktop / vertical mobile with media detection), opinions (3-column grid by lean: left/center/right, lean-colored left borders, no card backgrounds), week in brief (2-column compact story list), inline audio player, archive (issue list with current highlighted), footer. No MobileBottomNav. No collapsible sections. Component: `WeeklyDigest.tsx` (~700 lines TSX), styles: `weekly.css` (~650 lines).

### Film System — Shared Cinematic Scenes (`frontend/app/film/`)
Unified component library powering both the onboarding prologue and the about manifesto. 6 chapters (~90s prologue, scroll-driven manifesto). Content constants in `data.ts` (CHAPTERS, DIVERGENT_HEADLINES, SIX_AXES, FIRST_PRINCIPLES, PRODUCT_FAMILY, RANKING_SIGNALS, NUMBERS, LANDSCAPE, COMPARISON_SCORES, SIGIL_PARTS, SWEEP_POSITIONS). SVG paths, spring easings, and timing tokens in `constants.ts`. Shared `useReducedMotion.ts` hook. 6 scene components in `film/scenes/`: `SigilBreakdown` (centerpiece: 6-stage animated exploded Sigil view — draw, separate, label, reassemble, activate, hold), `DivergentHeadlines`, `SourceEngine`, `ArticleDifference`, `ProductWorlds`, `TheVerdict`. Each scene accepts `mode: "prologue" | "manifesto"` + `active: boolean`. Styles: `film.css` (`.film-*` namespace, mode-specific overrides via `--prologue`/`--manifesto` suffixes). `OnboardingCarousel.tsx` is a thin wrapper (modal overlay, auto-advance, keyboard nav) importing scenes with `mode="prologue"`. `/about` page is a thin wrapper (scroll-driven IO reveals) importing scenes with `mode="manifesto"` — no forced dark mode. `OnboardingSpotlight.tsx` deleted (dead code).

### History — "void --history" (`frontend/app/history/`)
Multi-perspective historical events platform ("The Archive"). See `docs/HISTORY.md` for full spec.
Routes: `/history` (organic ink timeline), `/history/[slug]` (6-stage story), `/history/era/[era]`, `/history/region/[region]`.
40 events, 175 perspectives, 278 media, 120 connections. 19 components. Supabase tables: `history_events`, `history_perspectives`, `history_media`, `history_connections` (migrations 039, 043).

### Animation
Spring presets in `tokens.css`: snappy (600/35/1), smooth (280/22/1), gentle (150/12/1.2), bouncy. Cinematic easings: `--ease-cinematic`, `--ease-whip`, `--ease-rack`. Keyframes: coldOpenSettle, coldOpenDollyIn (staggered page entrance), whipPanOutRight/whipPanInLeft (direction-aware edition switch), cinGoldenHourPulse (theme toggle warmth). Layer-specific: edition tabs (Row 2) use `hapticConfirm` on switch, filter lens uses `--ease-rack` timing + `hapticMicro`, page links (Row 1) use CSS departure arrow slide (4px shift), weekly (Row 1) uses spine rule glow + unfold physics on hover, search bar expands 160px to 280px on focus. ScaleIcon idle: 5s period, 2-degree amplitude, `--ease-cinematic`. GPU-only (transform + opacity). `prefers-reduced-motion` → 0ms duration + delay. Asymmetric panels.

### CSS
Load order (in `frontend/app/globals.css`): `tokens → layout → typography → components → animations → spectrum → mobile-feed → desktop-feed → skybox-banner → floating-player → mobile-nav → responsive → command-center → weekly → film → about → ship → history → verify` (all in `frontend/app/styles/`). Reset is inline in `globals.css` after imports. Custom properties only. Mobile-first. `clamp()` for fluid scaling. Justified body text. Nav classes: `.nav-pages`/`.nav-page` (Row 1 pages), `.nav-weekly` (Row 1 magazine link, deep red accent), `.nav-lens__editions`/`.nav-ed` (Row 2 edition tabs), `.nav-lens`/`.nav-lens__*` (Row 2 filters), `.nav-lens__search` (Row 2 expandable search bar) — all in `components.css`.

## Data Model (Supabase)

**Tables**: `sources`, `articles` (300-char excerpt), `bias_scores` (rationale JSONB), `story_clusters` (sections text[] GIN-indexed), `cluster_articles`, `categories` + `article_categories`, `source_topic_lean`, `pipeline_runs`, `daily_briefs` (TL;DR + audio). History tables: see `docs/HISTORY.md`.

**Views/Functions**: `cluster_bias_summary`, `refresh_cluster_enrichment()`, `cleanup_stale_clusters()`, `cleanup_stuck_pipeline_runs()`. Migrations: `supabase/migrations/` (001-043).

Frontend edition filter: `.contains("sections", [edition])`.

## Agent Team & Workflows

34 agents, 13 divisions. Full details: `docs/AGENT-TEAM.md`. Agent definitions: `.claude/agents/`.

| Command | Pattern | When |
|---------|---------|------|
| `/pipeline-qa` | pipeline-tester → bug-fixer → re-validate | After pipeline code change |
| `/bias-audit` | benchmark → fix → confirm | Gold standard for bias changes |
| `/bias-calibrate` | tune → check → verify | Scoring param tuning |
| `/frontend-ship` | build → test → fix | Any UI change |
| `/audio-qa` | review → validate → fix | Audio changes |
| `/full-audit` | 5-way parallel audit → triage → fix | System health check |
| `/launch-check` | 8-way validate → go/no-go | Pre-launch gate |
| `/daily-ops` | 3-way health check | Morning / post-pipeline |
| `/source-review` | vet → health check → validate | Source changes |
| `/security-sweep` | audit → fix → re-verify | Security + perf |
| `/rank-optimize` | benchmark → tune → validate → audit | Ranking engine tuning |
| `/frontend-review-fix` | audit → CEO prioritize → fix → build → retest | CEO-in-the-loop UI quality |
| `/cinematic-overhaul` | cinematographer → motion-director → vfx-artist → color-grader → build → validate → QA | Cinematic motion/VFX design evolution |
| `/history-research` | history-curator → perspective-analyst + media-archaeologist → auditor → narrative-engineer | New event onboarding |
| `/history-audit` | historiographic-auditor → perspective-analyst → re-validate | Perspective balance check |
| `/history-publish` | narrative-engineer → auditor → cinematic trio → visual-historian → build → test | Content publishing |
| `/history-media` | media-archaeologist → auditor → visual-historian | Visual asset curation |
| `/history-timeline` | history-curator → timeline-architect → visual-historian → archive-cartographer | Timeline & connections |
| `/history-qa` | parallel audit + content check → perspective-analyst → auditor → uat-tester | History quality gate |

### Locked Decisions (CEO Approval Required)
Cinematic Press design, 6-axis bias model, Supabase data layer, static export, 1,013-source list (3 tiers, 7-point lean), $0 cost, no user personalization (newspaper principle), Claude Max CLI only.

## Project Structure

```
void-news/
├── pipeline/
│   ├── fetchers/          # rss_fetcher.py, web_scraper.py
│   ├── analyzers/         # political_lean, sensationalism, opinion_detector, factual_rigor, framing, gemini_reasoning, topic_outlet_tracker
│   ├── clustering/        # deduplicator.py, story_cluster.py
│   ├── summarizer/        # gemini_client.py, cluster_summarizer.py
│   ├── briefing/          # daily_brief_generator, audio_producer, claude_brief_generator, voice_rotation, generate_assets, podcast_feed_generator, weekly_digest_generator, compare_generators
│   ├── categorizer/       # auto_categorize.py
│   ├── ranker/            # importance_ranker.py, edition_ranker.py
│   ├── validation/        # fixtures, signal_tracker, source_profiles, runner, snapshot
│   ├── memory/            # memory_orchestrator.py, live_poller.py (story memory engine)
│   ├── history/           # content_loader, image_enricher, mirror_images, source_enricher, verify_content (see docs/HISTORY.md)
│   ├── utils/             # supabase client, nlp_shared, prohibited_terms
│   ├── main.py            # Orchestrator
│   └── rerank.py          # Re-ranker CLI + rerank_all_clusters() shared function
├── frontend/
│   ├── app/
│   │   ├── components/    # 53 components: AudioProvider, BiasInspector, BiasLens, ClaimConsensusSection, ClaimMark, CommandCenter, ComparativeView, ConsensusBadge, CredibilityArc, DailyBrief, DeepDive, DeepDiveSpectrum, DesktopFeed, DigestRow, DivergenceAlerts, EditionIcon, ErrorBoundary, FloatingPlayer, Footer, HomeContent, InstallPrompt, KeyboardShortcuts, LeadStory, LoadingSkeleton, Logo{Full,Icon,Wordmark}, MobileBottomNav, MobileBriefPill, MobileFeed, MobileMiniPlayer, MobileNav, MobileSidePanel, MobileStoryCard, MobileTabBar, NavBar, OnboardingCarousel, OpEdPage, OpinionCard, PageToggle, ScaleIcon, SearchOverlay, ShareCard, ShipBoard, Sigil, SkyboxBanner, SpectrumChart, StoryCard, StoryMeta, ThemeToggle, UnifiedOnboarding, WeeklyDigest, WireCard
│   │   ├── history/       # /history routes + 19 components + hooks.ts, data.ts, mockData.ts, types.ts (see docs/HISTORY.md)
│   │   ├── lib/           # supabase.ts, types.ts, utils.ts, mockData.ts, biasColors.ts, haptics.ts, sharedObserver.ts, shareCardRenderer.ts
│   │   ├── film/           # Shared cinematic scenes: data.ts, constants.ts, useReducedMotion.ts, scenes/{SigilBreakdown,DivergentHeadlines,SourceEngine,ArticleDifference,ProductWorlds,TheVerdict}.tsx
│   │   ├── styles/        # tokens, layout, typography, components, animations, spectrum, mobile-feed, desktop-feed, skybox-banner, floating-player, mobile-nav, responsive, command-center, weekly, film, about, ship, history, verify
│   │   ├── sources/       # /sources page
│   │   ├── paper/         # /paper and /paper/[edition] e-paper pages
│   │   ├── command-center/ # /command-center KPI dashboard
│   │   ├── weekly/        # /weekly digest page
│   │   ├── about/         # /about page
│   │   ├── ship/          # /ship feature request board
│   │   └── [edition]/     # /[edition] dynamic edition routes
│   └── next.config.ts
├── data/sources.json      # 1,013 curated sources
├── data/history/events/   # 40 YAML event files (see docs/HISTORY.md for full list)
├── supabase/migrations/   # 001-043
├── .github/workflows/     # pipeline.yml, deploy.yml, migrate.yml, validate-bias.yml, auto-merge-claude.yml, audit-db.yml, refresh-brief.yml, weekly-digest.yml
├── .claude/agents/        # 34 agent definitions
├── .claude/skills/        # pressdesign + prompt-iterate + workflows + ship-queue + 20 workflow skills (24 total)
└── docs/                  # PROJECT-CHARTER, DESIGN-SYSTEM, IMPLEMENTATION-PLAN, GEMINI-VOICE-PLAN, PERF-REPORT, IP-COMPLIANCE, CEO-AGENT-GUIDE, DB-AUDIT-FRAMEWORK, DB-REVIEWER-GUIDE, MEMORY-ENGINE-*, MUSICAL-ELEMENTS-SPEC, NEWS-MEMORY-ENGINE, VOICE-BRAND, SOURCE-CURATION-REPORT-2026-04-02, HISTORY, HISTORY-FRONTEND-SPEC, HISTORY-AUDIO-SPEC, VOID-HISTORY-DESIGN-SPEC, VOID-HISTORY-PROPOSAL, PIPELINE-BRAIN, VOID-VERIFY
```

## Status

**Complete**: Pipeline (all 12 steps + cleanup + memory engine + holistic re-rank), 6-axis bias engine, ranking v6.0 + edition-unique, daily brief + audio + weekly digest, frontend MVP (feed + deep dive + sources + paper + weekly + about + command center), void --history (40 events, 19 components, 5-lens historiographic framework).
**In progress**: Deep Dive framing comparison, source credibility panels.
**Pending**: GitHub Pages deploy, WCAG audit, Lighthouse 90+, cross-browser testing, launch.
**Shelved**: Op-Ed page (pipeline still computes axis 3).

### Parking Lot (Disabled Pre-Launch — Fully Reversible)
Features disabled to stay within Gemini Flash free tier (250 RPD). All gated by env vars or config — no code deleted.

| Feature | Gate | RPD Saved | Re-enable |
|---------|------|-----------|-----------|
| Claude API for briefs | `CLAUDE_AVAILABLE = False` in `claude_client.py` | ~$140/month | Uncomment import |
| Regional editions (us/europe/south-asia) | `ACTIVE_EDITIONS = ["world"]` in `main.py`, `EDITIONS` in `types.ts` | 18-24/day | Add editions back to arrays |
| Gemini bias reasoning (step 6c) | `DISABLE_GEMINI_REASONING=1` in `pipeline.yml` | 45-60/day | Remove env var |
| Editorial triage (step 7c) | `DISABLE_EDITORIAL_TRIAGE=1` in `pipeline.yml` | 12/day | Remove env var |
| Audio/TTS | `DISABLE_AUDIO=1` in `pipeline.yml` | ~16/day | Remove env var |
| Weekly digest cron | Cron commented in `weekly-digest.yml` | 100-120/Sunday | Uncomment cron |
| Podcast RSS feeds | Gated behind `DISABLE_AUDIO` | trivial | Follows audio |

**Current budget**: ~51-87 RPD/day (35% of 250 RPD limit). Comfortable headroom.

### LLM Grounding Rule
All Gemini prompts (cluster summaries, daily briefs) include: "Every fact MUST appear in the provided articles. Do not supplement with prior knowledge." Enforced in `cluster_summarizer.py` and `daily_brief_generator.py` system instructions.

## Git & Dev

- **Always push to `claude/*` branches.** Auto-merge to main. Confirm deploy passes.
- **Always commit AND push after every task.** Never wait to be asked. Commit, push, then confirm both to the user.
- **Before every push, sync with main:** `git fetch origin main && git merge origin/main --no-edit`. Multiple sessions may advance main concurrently. Never push without syncing first.
- Python 3.11+, Node 18+, TypeScript frontend. All bias analysis rule-based.
- Pipeline: 25-35 min incremental, 108 min fresh DB. Static export (`next export`).
