# void --news

Last updated: 2026-05-13 (rev 43 — lead is text-only (image removed); headline scale unified for ranks 1+ via `--type-card-headline`; void --onair parked end-to-end behind `DISABLE_AUDIO` + `NEXT_PUBLIC_DISABLE_AUDIO`; mobile reorder — TL;DR + Opinion collapsible pill on top with single chevron, hero text-only below, all three above the fold at every mobile width; hover microinteractions toned to subconscious (no card lift, no caret translate, no fill+underline on lens index, half source-circle fan radius); React #418 root-cause fix (HomeContent isMobile lazy-init read pre-hydration DOM); WCAG 2.5.5 tap-target sweep)

News aggregation, 6-axis rule-based NLP bias analysis. 1,013 sources / 158 countries. World edition (regional editions parked). Pipeline runs 1x/day; homepage shows top 50 stories (digest 1-9, wire 10+). All editorial LLM work routes through Claude Sonnet 4.6. **Live at https://void-news.pages.dev** (Cloudflare Pages, root basePath). GH Pages deprecated.

## Quick Reference

| Working on... | Read |
|---|---|
| Frontend, components, CSS, animation | `docs/DESIGN-SYSTEM.md` |
| Pipeline flow, ranker v6.0, bias axes, summarization | `docs/PIPELINE-BRAIN.md` |
| Agents, workflows, slash commands | `docs/AGENT-TEAM.md` |
| void --history | `docs/HISTORY.md` |
| Source curation, tiers, L:R | `docs/SOURCE-CURATION-REPORT-2026-04-02.md` |
| Daily brief, audio, edge-tts, voice rotation | `docs/GEMINI-VOICE-PLAN.md` |
| DB schema, audits | `docs/DB-REVIEWER-GUIDE.md`, `docs/DB-AUDIT-FRAMEWORK.md` |
| Performance | `docs/PERF-REPORT-2026-04-29.md` (Lighthouse polish), `docs/PERF-REPORT-2026-03-22.md` (Vol I baseline) |
| Deploy, basePath, CF migration | `docs/DEPLOYMENT.md` |
| PWA, iOS/Android app build | `docs/APP-BUILD-GUIDE.md` |
| Security | `docs/IP-COMPLIANCE.md` |
| Memory engine | `docs/MEMORY-ENGINE-ARCHITECTURE.md` |
| Scope, roadmap | `docs/PROJECT-CHARTER.md`, `docs/IMPLEMENTATION-PLAN.md` |

## Architecture

```
GitHub Actions (1x daily cron, 11:00 UTC) → Python Pipeline → Supabase (PostgreSQL) ← Next.js Static Site (Cloudflare Pages — void-news.pages.dev)
```

No backend server. **Tech**: Python/spaCy/NLTK/TextBlob (NLP), Pillow ~=11 (WebP conversion at upload, q82, ~25-35% LCP image shrink), Claude Sonnet 4.6 via Anthropic SDK with prompt caching (summaries + briefs + opinion + weekly), Gemini 2.5 Flash (fallback only + history script gen), edge-tts 4-voice Multilingual Neural roster (audio, $0), Supabase, Next.js 16/React 19/TypeScript, native CSS + Web Animations API. Fonts: Playfair Display / Inter / Barlow Condensed / IBM Plex Mono. Deploy: Cloudflare Pages — live at https://void-news.pages.dev (GH Pages deprecated). See `docs/DEPLOYMENT.md`.

## Core Principles

### Show, Don't Tell — Cardinal Rule (Fiction)
All generated text MUST embody show-don't-tell. Never assert significance — juxtapose concrete facts so the reader sees the pattern. Never use "notable," "significant," "it should be noted," "interestingly," "crucially." Use specific numbers, names, dates, actions. Present evidence. Let the reader conclude.

**BAD:** "It is worth noting that tensions are rising significantly between the two nations."
**GOOD:** "Both countries recalled their ambassadors within 48 hours. Neither has done that since 1979."

Applies to: `cluster_summarizer.py`, `daily_brief_generator.py`, `claude_brief_generator.py`, void --history, CTAs, all generated content.

### Arrive Late, Leave Early — Screenplay Rule
Enter scenes at the last possible moment. Exit before the conclusion is spelled out. Drop the reader INTO the action. Cut when the point lands. The user's brain completes the story.

**BAD:** "The Partition of India was a complex historical process that began with British colonial rule and eventually led to the creation of two nations in 1947, resulting in massive displacement."
**GOOD:** "A lawyer who'd never been to India drew the border in five weeks. 15 million crossed it."

Applies to: void --history events, daily briefs, CTAs, audio scripts. Together these create the cognitive gap where understanding happens.

### No Em Dashes — AI Slop Rule
Em dashes (`—`) and en dashes (`–`) are banned in all written editorial output: cluster summaries, headlines, TL;DR, opinion text, weekly digest, history copy, CTAs, frontend microcopy. They are an AI tell. Rewrite as two short sentences, or use a comma, semicolon, colon, or parentheses. Hyphens in compound words ("fact-check," "twenty-four-hour") are fine. **Exception**: audio scripts (`audio_script`, `opinion_audio_script`) keep em dashes because they function as TTS prosody / breath marks for the spoken broadcast — void --onair is parked, but the rule is preserved for re-enable.

**BAD:** "The central bank cut rates Tuesday — the third move this quarter."
**GOOD:** "The central bank cut rates Tuesday. Third move this quarter."

Applies to: `cluster_summarizer.py` (summary, headline), `daily_brief_generator.py` (tldr_text, tldr_headline, opinion_text, opinion_headline), `claude_brief_generator.py`, `weekly_digest_generator.py`, void --history YAML copy, all frontend strings.

- **Product Family**: `void --news`, `void --tl;dr`, `void --onair`, `void --history`, `void --weekly`, `void --paper`, `void --sources`, `void --deep-dive`, `void --opinion`, `void --ship`, `void --games`.
- **No Personalization (LOCKED)**: Newspaper principle. Same stories, same order for everyone. No accounts, no recommendation algorithms.
- **Minimal Cost, High Editorial Value**: ~$30/month total LLM spend. Sonnet 4.6 ($3 in / $15 out per MTok) at ~57 calls/run × 1 run/day ≈ $1/day. Anthropic budget cap recommended at $50/mo (60% buffer). Rule-based NLP, edge-tts audio, Supabase, GitHub Actions/Pages remain $0. **Gemini TTS NOT used — was $3/day, not free tier.**
- **Bias Analysis**: 6 axes (political lean, sensationalism, opinion vs reporting, factual rigor, framing, per-topic EMA). All rule-based NLP, no LLM. See `docs/PIPELINE-BRAIN.md`.
- **LLM Grounding**: All Claude/Gemini prompts: "Every fact MUST appear in the provided articles. Do not supplement with prior knowledge."

## Status

**Complete**: Pipeline (all steps + cleanup + memory engine + holistic re-rank + post-rerank top-50 Sonnet single-pass with content-hash cache + WebP image cache, top_n=15; Sonnet 3-strike consecutive-failure counter replaces single-failure latch; daily-brief stub-on-failure writer so homepage never serves stale audio; article retention RPC `cleanup_stale_articles(days INT)` + source-health `consecutive_fetch_failures` quarantine — migrations 050 + 051 applied), 6-axis bias engine recalibrated 2026-05-13 (political_lean `unscored` gate widened `total_distinct≤2` + ±2.0 shifts + 40-60 baseline → fires ~26% on fixtures, target 30-50% in prod; sensationalism inflection 15→22, tier baselines un-halved; opinion_detector adds `OPINION_SOURCE_TYPE_BASELINES` for magazine/tabloid/independent/investigative/nonprofit; confidence formula recomputed → mean 0.545/std 0.119; show-don't-tell regex post-check in cluster_summarizer; validation 210/210 with 203 CORRECT / 7 ACCEPTABLE / 0 WRONG), ranking v6.0 + edition-unique, daily brief + weekly digest (all on Sonnet primary, Gemini fallback), frontend MVP (feed top 50 with digest/wire variants + Deep Dive 2-col + sources + paper + weekly + about + command center + ship + games — wire/run/cipher/frame/undertow), $100B layout overhaul + 2026-05-13 lead simplification (top story is text-only — no hero image; `--type-card-headline` token unifies ranks 1+ at 18→22px Playfair; lead summary single full-width column; "Top Story" badge `align-self: flex-start` so SVG oval hugs text), Lighthouse polish, **mobile layout redesign + 2026-05-13 reorder** (TL;DR + Opinion collapsible pill on top with single chevron; hero second; compact cards below — all three above the fold on 360-430 widths; React #418 hydration root cause fixed in HomeContent.tsx; WCAG 2.5.5 tap-target sweep across .mob-nav__lean, .nav-logo, .nav-lens__*, .sigil--sm via `@media (pointer:coarse)`, floating-player controls 32→44; mobile summary clamp 2→3 lines, TL;DR preview 2→3 sentences), **subconscious hover microinteractions** (no translateY card lift, no caret translate, lens-index hover = color only no fill no underline, source-circle fan radius halved 22→12px + r-jump 80%→20%), **PWA distribution** + **Capacitor iOS/Android shells**, **Cloudflare Pages live at void-news.pages.dev** (GH Pages deprecated; CSP `frame-ancestors 'none'` + `wss://*.supabase.co` moved to `_headers`), void --history (58 events, 22 components, 25 events rewritten Show-Don't-Tell + Arrive Late), `--canvas-max: min(92vw, 1600px)`, scroll-compact masthead, route-scoped CSS splits.
**In progress**: Deep Dive framing comparison; source credibility panels; iOS/Android signing + first store submission.
**Pending**: WCAG audit, Lighthouse 90+ verified post-deploy, cross-browser testing, launch. CF Pages live; PWA installable. Verify the new pipeline P0s on tomorrow's run (Sonnet recovery + brief stub-on-failure + cluster-image-cache writer logging + new bias distributions on full prod sample).

### Parking Lot (Disabled Pre-Launch)

| Feature | Gate | Re-enable |
|---|---|---|
| Regional editions | `ACTIVE_EDITIONS = ["world"]` in `main.py` | Add editions back |
| Gemini bias reasoning | `DISABLE_GEMINI_REASONING=1` in `pipeline.yml` | Remove env var |
| Editorial triage | `DISABLE_EDITORIAL_TRIAGE=1` in `pipeline.yml` | Remove env var |
| Weekly digest cron | Cron commented in `weekly-digest.yml` | Uncomment |
| **Audio (void --onair)** | `DISABLE_AUDIO=1` in `pipeline.yml` (pipeline TTS + podcast feed) **AND** `NEXT_PUBLIC_DISABLE_AUDIO=1` (frontend — gated via `app/lib/audioGate.ts`; hides FloatingPlayer, MobileMiniPlayer, MobileTabBar onair entry, MobileBriefPill Listen button, WeeklyDigest AudioBar, Footer `void --onair` pill, PipelineFlow step-7d label) | Remove both env vars together. `produce_audio()` early-returns on the pipeline flag; the frontend imports `AUDIO_ENABLED` from `audioGate.ts` to short-circuit each surface |

**LLM budget**: Anthropic Sonnet 4.6 primary, ~$1/day at 1 run × ~57 calls. Sonnet cap: 80 calls/run. Gemini Flash fallback when Anthropic unavailable; legacy free-tier limit ~250 RPD. Op-eds bypass all LLM — original article text preserved (`content_type=opinion`).

## Git & Dev

- **Always push to `claude/*` branches.** Auto-merge to main. Confirm deploy passes.
- **Always commit AND push after every task.** Never wait to be asked.
- **Sync before push:** `git fetch origin main && git merge origin/main --no-edit`.
- Python 3.11+, Node 18+, TypeScript. All bias analysis rule-based.
- Pipeline: 25-35 min incremental, 108 min fresh DB. Static export (`next export`).

## Locked Decisions (CEO Approval)

Cinematic Press design, 6-axis bias model, Supabase, static export, 1,013-source list (3 tiers, 7-point lean), no personalization, ~$30/mo LLM cost target on Sonnet 4.6 (was $0; broken intentionally for editorial quality), 1x/day pipeline cadence, top-50 homepage feed, Claude Max CLI for all agent work.

## Project Structure

```
void-news/
├── pipeline/
│   ├── fetchers/          # RSS + scraping
│   ├── analyzers/         # 5 bias axes + gemini_reasoning + topic_outlet_tracker
│   ├── clustering/        # deduplicator, story_cluster
│   ├── summarizer/        # claude_client (primary), gemini_client (fallback), cluster_summarizer
│   ├── briefing/          # daily brief (Sonnet primary), audio (edge-tts), weekly digest, voice rotation, podcast feed
│   ├── categorizer/       # auto_categorize
│   ├── ranker/            # importance_ranker, edition_ranker
│   ├── validation/        # 42 ground-truth fixtures, runner, CI gate
│   ├── memory/            # memory_orchestrator, live_poller
│   ├── history/           # content_loader, image/source enrichers, verify
│   ├── utils/             # supabase client, nlp_shared
│   ├── main.py            # Orchestrator (1x daily, smart-routed Claude→Gemini)
│   └── rerank.py          # Holistic re-ranker
├── frontend/
│   ├── app/
│   │   ├── components/    # 55 components (HomeContent: EDITION_FEED_SIZE=50, CATEGORY_CAP=12, fetch=80; StoryCard variant=digest|wire; BiasSnapshot inline+rail; MobilePerspectivePeek long-press modal)
│   │   ├── history/       # 22 history components + data/types/hooks
│   │   ├── film/          # 7 cinematic scenes
│   │   ├── lib/           # supabase, types, utils (BASE_PATH ← NEXT_PUBLIC_BASE_PATH), haptics, biasColors
│   │   ├── styles/        # 23 CSS files (added layout-zones.css — Grid scaffold + lead-split + BiasSnapshot + Deep Dive 2-col)
│   │   ├── games/         # 5 games (wire, run, cipher, frame, undertow)
│   │   └── [routes]/      # sources, paper, weekly, about, ship, command-center, [edition]
│   ├── public/            # _headers (Cloudflare Pages cache + security policy + CSP — frame-ancestors via HTTP, not meta), sw.js (PWA service worker), manifest.json, offline.html
│   ├── ios/               # Capacitor iOS shell (appId void.news; opens in Xcode)
│   ├── android/           # Capacitor Android shell (appId void.news; opens in Android Studio)
│   ├── capacitor.config.ts # appId void.news, webDir out
│   └── next.config.ts     # basePath = NEXT_PUBLIC_BASE_PATH ?? "/void--news"
├── data/sources.json      # 1,013 sources
├── data/history/events/   # 58 YAML event files
├── supabase/migrations/   # 001-049 (049 = summary_article_hash + summary_tier + llm_metrics)
├── pipeline/media/        # cluster_image_cacher (WebP at upload, top_n=15)
├── .github/workflows/     # pipeline (1x/day), deploy-cloudflare (CF Pages — primary), migrate, validate-bias, auto-merge, audit-db, refresh-brief, weekly-digest, generate-history-audio (deploy.yml — GH Pages — deprecated)
├── .claude/agents/        # 35 agents across 14 divisions
├── .claude/skills/        # 24 skills
└── docs/                  # 26 documentation files
```
