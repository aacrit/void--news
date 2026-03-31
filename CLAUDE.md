# void --news

Last updated: 2026-03-30 (rev 18)

> **Read this file first. Only read other docs when task-relevant. Only open source files when modifying code.**

News aggregation platform with per-article, 6-axis rule-based NLP bias analysis. 409 curated sources. World, US, India editions.

## Architecture

```
GitHub Actions (4x daily cron) → Python Pipeline → Supabase (PostgreSQL) ← Next.js Static Site (GitHub Pages)
```

No backend server. Python pipeline on Actions, Next.js static export on Pages, Supabase as single data layer.

**Tech**: Python/spaCy/NLTK/TextBlob (NLP), Gemini 2.5 Flash free tier (summaries + TTS), Supabase (PostgreSQL), Next.js 16/React 19/TypeScript, Motion One v11 (CDN), CSS custom properties. Fonts: Playfair Display / Inter / Barlow Condensed / IBM Plex Mono.

## Core Principles

### Show, Don't Tell — The Cardinal Rule
All generated text MUST embody show-don't-tell. Never assert significance — juxtapose concrete facts so the reader sees the pattern. Never use "notable," "significant," "it should be noted," "interestingly," "crucially." Use specific numbers, names, dates, actions.

**BAD:** "It is worth noting that tensions are rising significantly between the two nations."
**GOOD:** "Both countries recalled their ambassadors within 48 hours. Neither has done that since 1979."

Applies to: `cluster_summarizer.py`, `daily_brief_generator.py`, `claude_brief_generator.py` prompts, and all future content generation.

### Product Family Branding
CLI-style naming: `void --news` (platform), `void --tl;dr` (daily brief), `void --onair` (audio), `void --opinion` (editorial), `void --sources` (spectrum), `void --deep-dive` (analysis), `void --paper` (e-paper). Subtitles show on first encounter (sessionStorage) then fade.

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
26 ground-truth articles, 8 categories, 96.9% accuracy. CI gate via `.github/workflows/validate-bias.yml`.
```bash
python pipeline/validation/runner.py              # Full validation
python pipeline/validation/runner.py --quick      # Skip distribution checks
python pipeline/validation/runner.py --verbose    # Per-signal decomposition
python pipeline/validation/runner.py --update-snapshot  # Refresh regression baseline
```

### Importance Ranking — v5.4
**BIAS-BLIND.** 11-signal formula in `pipeline/ranker/importance_ranker.py` (weights sum to 1.0): source breadth 20%, maturity 16%, tier diversity 13%, consequentiality 10%, institutional authority 8%, factual density 8%, divergence 7%, perspective diversity 6%, geographic impact 6%, velocity 3%, lean diversity 3%. Plus Gemini editorial importance additive adjustment, gates (confidence, consequentiality, soft-news, tabloid, factual rigor, lead eligibility), topic diversity re-rank, cross-edition demotion, same-event cap, steepened time-decay. `pipeline/rerank.py` for standalone re-ranking.

### Cluster Summarization
3+-source clusters, 25-call Gemini cap/run, 250-350 words. Falls back to rule-based. Op-eds (opinion_fact > 50): single-article, no Gemini.

### Daily Brief — "void --onair"
World-focused, top 20 clusters. **TL;DR**: 8-12 sentences editorial paragraph (150-220 words), joint board voice. **Opinion**: 3-5 sentences first-person-plural editorial judgment (lean rotates daily: left/center/right). **Audio**: BBC two-host format, `A:`/`B:` speaker tags (no segment markers), Gemini 2.5 Flash TTS (native multi-speaker, single API call), pydub post-processing (Glass & Gravity sonic identity, no background music bed — intentional), MP3 192k mono → Supabase Storage. 5 rotating host pairs shared across all editions (not edition-specific); opinion voice fixed per edition. Stored in `daily_briefs` table: `audio_duration_seconds`, `audio_file_size`, `audio_voice` columns. 5 calls/run (separate from 25-call cap). Claude CLI premium scripts optional (`claude_brief_generator.py`, generates TL;DR + opinion + audio in one call).

### Source Curation
409 sources, 3 tiers: us_major (49), international (178), independent (182). 7-point lean spectrum. Editions: world (default), us, india. Source country determines edition.

## Pipeline Flow (4x Daily)

```
 1. LOAD SOURCES → 2. PIPELINE RUN → 3. FETCH RSS → 4. SCRAPE → 4b. DEDUP
 5. ANALYZE (5-axis) → 6. CLUSTER (TF-IDF + entity merge) → 6b. RE-FRAME
 6c. GEMINI REASON → 7b. SUMMARIZE → 7. CATEGORIZE & RANK → 7c. EDITORIAL TRIAGE
 7d. DAILY BRIEF (TL;DR + audio) → 8. STORE → 8b. DEDUP CLUSTERS
 9. ENRICH → 9a. MEMORY ENGINE → 9b. ARTICLE CATS → 9c. TOPIC TRACK → 10. TRUNCATE + CLEANUP
```

Non-audio runs (00:00, 12:00 UTC) carry forward audio fields from previous brief.

## Frontend Design

### "Cinematic Press" (Press & Precision v2)
Editorial authority + cinematic depth, light, focus, atmosphere. **Clean on arrival, data-dense on interaction.** Progressive disclosure. Cinematic tokens in `tokens.css`: `--cin-amber` palette (amber/ash/paper tones, light+dark), `--ease-cinematic`/`--ease-whip`/`--ease-rack` easings, `--z-cinematic`, film grain (`--cin-grain-opacity`, numOctaves=3), vignette (`--cin-vignette-color`, z-index above grain), color grade (`--cin-grade`, applied to `.page-main` + `.nav-header` not `.page-container`), rack focus, atmospheric haze (`--cin-haze-far`), backdrop (`--cin-backdrop-bg/blur`), practical warmth (`--cin-practical-warmth`). Cold open stagger (nav 80ms, skybox 200ms, lead 320ms, feed 480ms), direction-aware whip pan (edition switch), golden hour pulse (theme toggle, 700ms). Spring physics (Motion One) for user actions, ease-out for reveals.

**Four type voices**: Editorial (Playfair Display), Structural (Inter), Meta (Barlow Condensed, `--font-meta`), Data (IBM Plex Mono).

**Responsive**: desktop = multi-column newspaper grid, top nav. Mobile = single-column feed, bottom nav, bottom sheets. Touch targets 44px+. Breakpoints: 375/768/1024/1440px.

### Homepage
Importance-ranked feed with category filtering (lean chips in HomeContent). Edition sections: World/US/India. Daily Brief between nav and Lead Section (blockquote left-border, justified, opinion behind dotted firewall rule). "void --onair" persistent bottom audio player + progress bar.

### Deep Dive
Centered popup (desktop 75vw, 80vh; mobile full-screen bottom sheet). Summary as lede (ResizeObserver overflow). Analysis row: Sigil + DeepDiveSpectrum (7-zone gradient, logos at exact lean %) + Press Analysis trigger. BiasInspectorInline (4-axis scorecard). ScoringMethodology ("How we score" collapsible dl/dt/dd, 6 axes). Source Perspectives (agree/diverge grid). Asymmetric animation: open bouncy 500ms, close snappy 380ms, cinematic dramatic shadow, data-settled studio reflection.

### Animation
Spring presets in `tokens.css`: snappy (600/35/1), smooth (280/22/1), gentle (150/12/1.2), bouncy. Cinematic easings: `--ease-cinematic`, `--ease-whip`, `--ease-rack`. Keyframes: coldOpenSettle, coldOpenDollyIn (staggered page entrance), whipPanOutRight/whipPanInLeft (direction-aware edition switch), cinGoldenHourPulse (theme toggle warmth). ScaleIcon idle: 5s period, 2-degree amplitude, `--ease-cinematic`. GPU-only (transform + opacity). `prefers-reduced-motion` → 0ms duration + delay. Asymmetric panels.

### CSS
Load order (in `frontend/app/globals.css`): `tokens → layout → typography → components → animations → spectrum → mobile-feed → desktop-feed → skybox-banner → audio-player → responsive → command-center` (all in `frontend/app/styles/`). Reset is inline in `globals.css` after imports. Custom properties only. Mobile-first. `clamp()` for fluid scaling. Justified body text.

## Data Model (Supabase)

**Tables**: `sources`, `articles` (300-char excerpt), `bias_scores` (rationale JSONB), `story_clusters` (sections text[] GIN-indexed), `cluster_articles`, `categories` + `article_categories`, `source_topic_lean`, `pipeline_runs`, `daily_briefs` (TL;DR + audio).

**Views/Functions**: `cluster_bias_summary`, `refresh_cluster_enrichment()`, `cleanup_stale_clusters()`, `cleanup_stuck_pipeline_runs()`. Migrations: `supabase/migrations/` (001-029).

Frontend edition filter: `.contains("sections", [edition])`.

## Agent Team & Workflows

23 agents, 10 divisions. Full details: `docs/AGENT-TEAM.md`. Agent definitions: `.claude/agents/`.

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
| `/cinematic-overhaul` | cinematographer → motion-director → vfx-artist → build → validate → QA | Cinematic motion/VFX design evolution |

### Locked Decisions (CEO Approval Required)
Cinematic Press design, 6-axis bias model, Supabase data layer, static export, 409-source list (3 tiers, 7-point lean), $0 cost, Claude Max CLI only.

## Project Structure

```
void-news/
├── pipeline/
│   ├── fetchers/          # rss_fetcher.py, web_scraper.py
│   ├── analyzers/         # political_lean, sensationalism, opinion_detector, factual_rigor, framing, gemini_reasoning, topic_outlet_tracker
│   ├── clustering/        # deduplicator.py, story_cluster.py
│   ├── summarizer/        # gemini_client.py, cluster_summarizer.py
│   ├── briefing/          # daily_brief_generator, audio_producer, claude_brief_generator, voice_rotation, generate_assets
│   ├── categorizer/       # auto_categorize.py
│   ├── ranker/            # importance_ranker.py
│   ├── validation/        # fixtures, signal_tracker, source_profiles, runner, snapshot
│   ├── memory/            # memory_orchestrator.py, live_poller.py (story memory engine)
│   ├── utils/             # supabase client, nlp_shared, prohibited_terms
│   ├── main.py            # Orchestrator
│   └── rerank.py          # Standalone re-ranker
├── frontend/
│   ├── app/
│   │   ├── components/    # 39 components: AudioPlayer, BiasInspector, BiasLens, BiasLensOnboarding, CommandCenter, ComparativeView, DailyBrief, DeepDive, DeepDiveSpectrum, DesktopFeed, DigestRow, DivergenceAlerts, EditionIcon, ErrorBoundary, Footer, HomeContent, InstallPrompt, KeyboardShortcuts, LeadStory, LoadingSkeleton, Logo{Full,Icon,Wordmark}, MobileBottomNav, MobileBriefPill, MobileFeed, MobileStoryCard, NavBar, OpEdPage, OpinionCard, PageToggle, ScaleIcon, Sigil, SkyboxBanner, SpectrumChart, StoryCard, StoryMeta, ThemeToggle, WireCard
│   │   ├── lib/           # supabase.ts, types.ts, utils.ts, mockData.ts, biasColors.ts, haptics.ts, sharedObserver.ts
│   │   ├── styles/        # tokens, layout, typography, components, animations, spectrum, mobile-feed, desktop-feed, skybox-banner, audio-player, responsive, command-center
│   │   ├── sources/       # /sources page
│   │   ├── paper/         # /paper and /paper/[edition] e-paper pages
│   │   ├── command-center/ # /command-center KPI dashboard
│   │   └── [edition]/     # /[edition] dynamic edition routes
│   └── next.config.ts
├── data/sources.json      # 409 curated sources
├── supabase/migrations/   # 001-029
├── .github/workflows/     # pipeline.yml, deploy.yml, migrate.yml, validate-bias.yml, auto-merge-claude.yml, audit-db.yml, refresh-opinion.yml, refresh-tldr.yml, refresh-onair.yml
├── .claude/agents/        # 23 agent definitions
├── .claude/skills/        # pressdesign + 14 workflow skills
└── docs/                  # PROJECT-CHARTER, DESIGN-SYSTEM, IMPLEMENTATION-PLAN, GEMINI-VOICE-PLAN, PERF-REPORT, IP-COMPLIANCE, CEO-AGENT-GUIDE, DB-AUDIT-FRAMEWORK, DB-REVIEWER-GUIDE, MEMORY-ENGINE-*, MUSICAL-ELEMENTS-SPEC, NEWS-MEMORY-ENGINE
```

## Status

**Complete**: Pipeline (all 12 steps + cleanup + memory engine), 6-axis bias engine, ranking v5.4, daily brief + audio, frontend MVP (feed + deep dive + sources + paper + command center).
**In progress**: Deep Dive framing comparison, source credibility panels.
**Pending**: GitHub Pages deploy, WCAG audit, Lighthouse 90+, cross-browser testing, launch.
**Shelved**: Op-Ed page (pipeline still computes axis 3).

## Git & Dev

- **Always push to `claude/*` branches.** Auto-merge to main. Confirm deploy passes.
- **Always commit after every task.** Never wait to be asked. Confirm the commit to the user.
- Python 3.11+, Node 18+, TypeScript frontend. All bias analysis rule-based.
- Pipeline: 25-35 min incremental, 108 min fresh DB. Static export (`next export`).
