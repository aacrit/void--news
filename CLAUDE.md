# void --news

Last updated: 2026-04-09 (rev 34)

News aggregation platform with per-article, 6-axis rule-based NLP bias analysis. 1,013 curated sources across 158 countries. World edition (regional editions parked pre-launch).

## Quick Reference — Read the Right Doc

| Working on... | Read |
|---------------|------|
| Frontend design, components, CSS, animation | `docs/DESIGN-SYSTEM.md` |
| Pipeline flow, ranker v6.0, bias axes, clustering, summarization | `docs/PIPELINE-BRAIN.md` |
| Agents, workflows, slash commands | `docs/AGENT-TEAM.md` |
| void --history (The Archive) | `docs/HISTORY.md` |
| Source curation, tiers, L:R balance | `docs/SOURCE-CURATION-REPORT-2026-04-02.md` |
| Daily brief, audio, TTS, voice rotation | `docs/GEMINI-VOICE-PLAN.md` |
| Database schema, audits | `docs/DB-REVIEWER-GUIDE.md`, `docs/DB-AUDIT-FRAMEWORK.md` |
| Performance benchmarks | `docs/PERF-REPORT-2026-03-22.md` |
| Security posture | `docs/IP-COMPLIANCE.md` |
| Memory engine | `docs/MEMORY-ENGINE-ARCHITECTURE.md` |
| Project scope, roadmap | `docs/PROJECT-CHARTER.md`, `docs/IMPLEMENTATION-PLAN.md` |

## Architecture

```
GitHub Actions (3x daily cron) → Python Pipeline → Supabase (PostgreSQL) ← Next.js Static Site (GitHub Pages)
```

No backend server. **Tech**: Python/spaCy/NLTK/TextBlob (NLP), Gemini 2.5 Flash free tier (summaries + TTS), Supabase (PostgreSQL), Next.js 16/React 19/TypeScript, Motion One v11 (CDN), CSS custom properties. Fonts: Playfair Display / Inter / Barlow Condensed / IBM Plex Mono.

## Core Principles

### Show, Don't Tell — The Cardinal Rule (Fiction Writing)
All generated text MUST embody show-don't-tell. Never assert significance -- juxtapose concrete facts so the reader sees the pattern. Never use "notable," "significant," "it should be noted," "interestingly," "crucially." Use specific numbers, names, dates, actions. Present evidence. Let the reader conclude.

**BAD:** "It is worth noting that tensions are rising significantly between the two nations."
**GOOD:** "Both countries recalled their ambassadors within 48 hours. Neither has done that since 1979."

Applies to: all generated text -- `cluster_summarizer.py`, `daily_brief_generator.py`, `claude_brief_generator.py`, void --history perspectives, CTAs, and all future content.

### Arrive Late, Leave Early — The Screenplay Rule
Enter every scene at the last possible moment. Exit before the conclusion is spelled out. Drop the reader INTO the action. Cut when the point lands. The user's brain completes the story.

**BAD:** "The Partition of India was a complex historical process that began with British colonial rule and eventually led to the creation of two nations in 1947, resulting in massive displacement."
**GOOD:** "A lawyer who'd never been to India drew the border in five weeks. 15 million crossed it."

Applies to: void --history event pages, daily briefs, CTAs, audio scripts. These two rules together create the cognitive gap where understanding happens. The user doesn't receive a conclusion. They arrive at one.

- **Product Family Branding**: CLI-style naming: `void --news`, `void --tl;dr`, `void --onair`, `void --history`, `void --weekly`, `void --paper`, `void --sources`, `void --deep-dive`, `void --opinion`, `void --ship`.
- **No Personalization (LOCKED)**: Newspaper principle. Same stories, same order for everyone. No user accounts, no recommendation algorithms, no "for you" logic. Locked architectural decision.
- **Zero Operational Cost**: $0. Rule-based NLP + Gemini Flash free tier (250 RPD) + GitHub Actions + Supabase + Pages all free tier.
- **Bias Analysis**: 6 axes (political lean, sensationalism, opinion vs. reporting, factual rigor, framing, per-topic EMA). All rule-based NLP, no LLM. See `docs/PIPELINE-BRAIN.md`.
- **LLM Grounding**: All Gemini prompts: "Every fact MUST appear in the provided articles. Do not supplement with prior knowledge."

## Status

**Complete**: Pipeline (all steps + cleanup + memory engine + holistic re-rank), 6-axis bias engine, ranking v6.0 + edition-unique, daily brief + audio + weekly digest, frontend MVP (feed + deep dive + sources + paper + weekly + about + command center + ship), void --history (40 events, 20 components).
**In progress**: Deep Dive framing comparison, source credibility panels.
**Pending**: GitHub Pages deploy, WCAG audit, Lighthouse 90+, cross-browser testing, launch.

### Parking Lot (Disabled Pre-Launch)
Features disabled for Gemini Flash free tier (250 RPD). All gated by env vars/config -- no code deleted.

| Feature | Gate | Re-enable |
|---------|------|-----------|
| Regional editions | `ACTIVE_EDITIONS = ["world"]` in `main.py` | Add editions back |
| Gemini bias reasoning | `DISABLE_GEMINI_REASONING=1` in `pipeline.yml` | Remove env var |
| Editorial triage | `DISABLE_EDITORIAL_TRIAGE=1` in `pipeline.yml` | Remove env var |
| Audio/TTS | `DISABLE_AUDIO=1` in `pipeline.yml` | Remove env var |
| Weekly digest cron | Cron commented in `weekly-digest.yml` | Uncomment |
| Claude API briefs | `CLAUDE_AVAILABLE = False` in `claude_client.py` | Uncomment import |

**Current budget**: ~177 RPD/day (71% of 250 limit). Summarization cap: 50/run.

## Git & Dev

- **Always push to `claude/*` branches.** Auto-merge to main. Confirm deploy passes.
- **Always commit AND push after every task.** Never wait to be asked.
- **Before every push, sync with main:** `git fetch origin main && git merge origin/main --no-edit`.
- Python 3.11+, Node 18+, TypeScript frontend. All bias analysis rule-based.
- Pipeline: 25-35 min incremental, 108 min fresh DB. Static export (`next export`).

## Locked Decisions (CEO Approval Required)

Cinematic Press design, 6-axis bias model, Supabase data layer, static export, 1,013-source list (3 tiers, 7-point lean), $0 cost, no user personalization, Claude Max CLI only.

## Project Structure

```
void-news/
├── pipeline/
│   ├── fetchers/          # RSS + scraping
│   ├── analyzers/         # 5 bias axes + gemini_reasoning + topic_outlet_tracker
│   ├── clustering/        # deduplicator, story_cluster
│   ├── summarizer/        # gemini_client, cluster_summarizer
│   ├── briefing/          # daily brief, audio, weekly digest, voice rotation, podcast feed
│   ├── categorizer/       # auto_categorize
│   ├── ranker/            # importance_ranker, edition_ranker
│   ├── validation/        # 42 ground-truth fixtures, runner, CI gate
│   ├── memory/            # memory_orchestrator, live_poller
│   ├── history/           # content_loader, image/source enrichers, verify
│   ├── utils/             # supabase client, nlp_shared
│   ├── main.py            # Orchestrator (3x daily)
│   └── rerank.py          # Holistic re-ranker
├── frontend/
│   ├── app/
│   │   ├── components/    # 53 components
│   │   ├── history/       # 20 history components + data/types/hooks
│   │   ├── film/          # 6 cinematic scenes (prologue + manifesto)
│   │   ├── lib/           # supabase, types, utils, haptics, biasColors
│   │   ├── styles/        # 19 CSS files (tokens → verify)
│   │   └── [routes]/      # sources, paper, weekly, about, ship, command-center, [edition]
│   └── next.config.ts
├── data/sources.json      # 1,013 sources
├── data/history/events/   # 40 YAML event files
├── supabase/migrations/   # 001-043
├── .github/workflows/     # pipeline, deploy, migrate, validate-bias, auto-merge, audit-db, refresh-brief, weekly-digest
├── .claude/agents/        # 34 agents across 13 divisions
├── .claude/skills/        # 24 skills (workflows + tools)
└── docs/                  # 23 documentation files
```