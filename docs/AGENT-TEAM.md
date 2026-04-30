# void --news Agent Team Structure

Last updated: 2026-04-29 (rev 27 — Sonnet 4.6 editorial LLM stack + layout-zones.css scaffold under Frontend Division)

## Philosophy

Adapted from DondeAI. Every principle inherited and tailored for a news bias analysis platform.

### Core Principles

1. **No Hierarchical Delegation** — Agents cannot spawn other agents. Task routing at the human level.
2. **Read-First Protocol** — Every agent reads CLAUDE.md + relevant docs before any work.
3. **Execution Protocol** — Assess → Plan → Build → Verify → Report. No exceptions.
4. **Max Blast Radius** — Max 4 CSS, 2 JS/TS, 3 Python files per run.
5. **Claude Max CLI for agent work; Sonnet 4.6 API for editorial LLM** — All agent/dev work via Claude Code CLI ($0). Pipeline editorial LLM (summaries, briefs, opinion, weekly) routes through Claude Sonnet 4.6 with smart-routed Gemini fallback (~$30/mo target). Rule-based NLP and edge-tts audio remain $0.
6. **Parallel-Safe vs Sequential** — Read-only agents can run simultaneously. Write agents require sequencing.

### Cost Policy

```
COST BUDGET: ~$30/month editorial LLM (Sonnet 4.6); rest is $0

Pipeline NLP:      Rule-based (spaCy, NLTK, TextBlob)              — $0
Editorial LLM:     Claude Sonnet 4.6 primary (~57 calls/run × 1 run/day)
                   $3 in / $15 out per MTok, ephemeral prompt cache — ~$30/mo
LLM Fallback:      Gemini Flash free tier (~250 RPD legacy limit)  — $0
Audio TTS:         edge-tts (Microsoft Neural)                     — $0
Database:          Supabase free tier                              — $0
Hosting:           GitHub Pages                                    — $0
CI/CD:             GitHub Actions free tier                        — $0
Agent work:        Claude Code CLI (Max subscription)              — $0
```

Anthropic console budget cap recommended at $50/month (60% buffer over $30 target).

---

## Organizational Structure

```
CEO (Aacrit)
  ├── Agent Engineering — agent-architect
  ├── Quality ————————— analytics-expert, bias-auditor, bias-calibrator, pipeline-tester, bug-fixer
  ├── Infrastructure ——— perf-optimizer, db-reviewer, update-docs
  ├── Frontend ————————— frontend-builder, frontend-fixer, responsive-specialist, uat-tester
  ├── Cinematic ————————— cinematographer, vfx-artist, motion-director, color-grader
  ├── Pipeline ————————— feed-intelligence, nlp-engineer, source-curator, linguist
  ├── History —————————— history-curator, perspective-analyst, historiographic-auditor, media-archaeologist, timeline-architect, narrative-engineer
  ├── History Visual ——— visual-historian, archive-cartographer
  ├── Audio ———————————— audio-engineer
  ├── Games ———————————— game-content-writer
  ├── Security ————————— void-ciso
  ├── Product —————————— ceo-advisor
  └── Branding ————————— logo-designer
```

**Total: 35 agents across 14 divisions**

Cinematic Division agents (cinematographer, motion-director, vfx-artist) are also core History team members, integrated into `/history-publish` and `/cinematic-overhaul`. Full history spec: `docs/HISTORY.md`.

### Cycle Status (2026-04-29)

| Tier | Status | Notes |
|---|---|---|
| Tier 0 (foundation) | **Shipped** | `--canvas-max`, scroll-compact masthead, lead photo clamp, Deep Dive double-defocus fix, mobile reclaim |
| Tier 1 (polish) | **Shipped** | `anim-stagger` IO-replay safe, dead CSS sweep, 3/5-col `/ship` Kanban, hardcoded widths → `var(--canvas-max)` |
| Tier 2 (motion) | **Shipped** | Press states, card lift on hover, gesture inertia, 496 bare easings → tokens across 18 CSS files |
| $100B Layout Overhaul (2026-04-29) | **Shipped** | LeadStorySplit 50/50, StoryCard `variant=digest\|wire`, BiasSnapshot inline+rail, Deep Dive 2-col body, `layout-zones.css` Grid scaffold, type scale tokens (lead/digest/wire) |
| Lighthouse Polish (2026-04-29) | **Shipped** | WebP at upload (Pillow ~=11, q82, 25-35% LCP shrink), spectrum.css + verify.css route-scoped (~130KB gzipped off homepage), tablet/wire-grid/Deep-Dive-rail breakpoint surgical fixes |
| Cloudflare Pages parallel deploy (2026-04-29) | **Scaffolded** | `_headers`, `deploy-cloudflare.yml`, `NEXT_PUBLIC_BASE_PATH` env contract. Awaits `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` secrets |
| Tier 3 (cinematic depth) | Pending | |
| Tier 4 (hero overhaul) | Pending | |

Narrative-engineer pass: 25 YAML event files rewritten Show-Don't-Tell + Arrive Late Leave Early. Voice remap (Cycle 4): 12 first-gen Neural voices retired, 4 Multilingual (Andrew/Brian/Ava/Emma).

---

## Division Roster

### Quality Division

| Agent | Purpose | Write | Trigger |
|---|---|---|---|
| `analytics-expert` | Bias engine benchmarking, ranking calibration | Yes | Algorithm changes |
| `bias-auditor` | Ground-truth validation against known outlet profiles | Yes | After scoring changes |
| `bias-calibrator` | Validation suite, regression detection, axis weight tuning, ground-truth corpus. Quantitative counterpart to bias-auditor. CI gate: `validate-bias.yml` runs on every push to `claude/*` touching `pipeline/analyzers/`; blocks merge on CATASTROPHIC failures. | Yes | Analyzer changes, regression alerts |
| `pipeline-tester` | Pipeline quality gate — parsing, clustering, scoring | No | Every pipeline change |
| `bug-fixer` | Post-test surgical fixes | Yes | After test failures |

### Infrastructure Division

| Agent | Purpose | Write | Trigger |
|---|---|---|---|
| `perf-optimizer` | Pipeline runtime + frontend load time | Yes | Performance issues |
| `db-reviewer` | Supabase data quality | No | After pipeline runs |
| `update-docs` | Sync CLAUDE.md and docs/*.md with codebase | Yes | After significant changes |

### Frontend Division

| Agent | Purpose | Write | Trigger |
|---|---|---|---|
| `frontend-builder` | Press & Precision component engineering. Owns `layout-zones.css` Grid scaffold (LeadStorySplit, BiasSnapshot inline+rail, Deep Dive 2-col body, feed-grid baseline rules). | Yes | Feature requests |
| `frontend-fixer` | UI bug remediation — bias display, layout, animation, a11y | Yes | Bug reports |
| `responsive-specialist` | Desktop/mobile, light/dark. Co-owns `layout-zones.css` breakpoint surgical fixes (tablet 768-1023px lead image cap, wire grid 4↔5 cols, Deep Dive 2-col `1.7fr/1.6fr` ratios). | Yes | New components, responsive bugs |
| `uat-tester` | Browser testing, screenshots | No | After frontend changes |

### Pipeline Division

| Agent | Purpose | Write | Trigger |
|---|---|---|---|
| `feed-intelligence` | RSS health, collection, deduplication, cluster summarization | Yes | Pipeline development |
| `nlp-engineer` | spaCy/NLTK — bias scoring algorithms, NER, sentiment | Yes | Bias engine development |
| `source-curator` | Source vetting, RSS/scrape config, 1,013-source list | Yes | Source list changes |
| `linguist` | Media bias vocabulary research, lexicon expansion across 5 analyzers | Yes | After bias calibration, lexicon gaps |
| `media-curator` | Free-API image sourcing for weekly cover + history (Wikimedia, Unsplash, Pexels, Pixabay) | Yes | Weekly digest, history media |

### Cinematic Division

| Agent | Purpose | Write | Trigger |
|---|---|---|---|
| `cinematographer` | Camera language — DOF, rack focus, parallax, scene composition, cinematic tokens | Yes | Cinematic overhaul, motion design |
| `vfx-artist` | Post-processing — grain, color grading, vignettes, lens, atmosphere via CSS filters + SVG | Yes | After cinematographer |
| `motion-director` | Scroll-driven choreography — scene timelines, gesture physics, L-cut/match-cut, scroll-timeline API | Yes | After cinematographer |
| `color-grader` | Per-image CSS grading — external source normalization, page-specific filters (weekly warmth, history sepia, feed amber), grain/vignette compositing | Yes | After media-curator + vfx-artist |

### History Division

| Agent | Purpose | Write | Trigger |
|---|---|---|---|
| `history-curator` | Event selection, YAML content, era/region taxonomy | Yes | New event onboarding |
| `perspective-analyst` | 5-lens framework (Geographic/National, Social Position, Temporal Frame, Causal Emphasis, Evidentiary Base), viewpoint gaps | Yes | After event draft |
| `historiographic-auditor` | Accuracy validation, source verification, narrative bias, visual bias | No | Before publishing |
| `media-archaeologist` | Primary source discovery, historical media, rights/provenance | Yes | Visual asset curation |
| `timeline-architect` | Event connections, chronological accuracy, cross-event relationships | Yes | Timeline construction |
| `narrative-engineer` | Prose polish, show-don't-tell, multi-perspective coherence | Yes | Final content polish |

### History Visual Division

| Agent | Purpose | Write | Trigger |
|---|---|---|---|
| `visual-historian` | Archival Cinema implementation, Ken Burns, page layouts | Yes | After cinematographer |
| `archive-cartographer` | Geographic visualization, map layers, region/era spatial data | Yes | Map features |

### Agent Engineering Division

| Agent | Purpose | Write | Trigger |
|---|---|---|---|
| `agent-architect` | Audits, optimizes, designs all agents. Reviews definitions for tooling, cost efficiency, prompt engineering. Builds new agents on CEO demand. | Yes (agent definitions only) | CEO request, post-major-change review |

### Games Division

| Agent | Purpose | Write | Trigger |
|---|---|---|---|
| `game-content-writer` | Word lists, puzzles, clue banks for void --games (THE WIRE, CIPHER, FRAME, VOID RUN, UNDERTOW) | Yes | New game content |

### Security Division

| Agent | Purpose | Write |
|---|---|---|
| `void-ciso` | Secrets, RLS, CORS, injection, OWASP, dependencies | No |

### Product Division

| Agent | Purpose | Write |
|---|---|---|
| `ceo-advisor` | Strategic counsel — roadmap, competitive positioning | No |

### Branding Division

| Agent | Purpose | Write |
|---|---|---|
| `logo-designer` | Brand identity, favicon, SVG, cinematic palette, texture system | Yes |

---

## Sequential Cycles

**Quality:** `pipeline-tester → bug-fixer → pipeline-tester`
**Bias Audit:** `analytics-expert → bias-auditor → nlp-engineer → pipeline-tester`
**Bias Calibration:** `nlp-engineer → bias-calibrator → bias-auditor → pipeline-tester`
**Frontend:** `frontend-builder → responsive-specialist → uat-tester → frontend-fixer`
**Audio Quality:** `audio-engineer → pipeline-tester → bug-fixer`
**Cinematic Overhaul:** `[logo-designer + cinematographer] → motion-director → vfx-artist → color-grader → frontend-builder → [responsive-specialist + perf-optimizer] → uat-tester → frontend-fixer`
**Pipeline Dev:** `feed-intelligence → nlp-engineer → pipeline-tester → bug-fixer → pipeline-tester`
**Weekly Media:** `weekly_digest_generator → media-curator → frontend-builder`
**History Media:** `media-archaeologist → media-curator → historiographic-auditor → visual-historian`
**History Research:** `history-curator → [perspective-analyst + media-archaeologist] → historiographic-auditor → narrative-engineer`
**History Publishing:** `narrative-engineer → historiographic-auditor → [cinematographer + motion-director + vfx-artist] → visual-historian → frontend-builder → uat-tester`
**History QA:** `[historiographic-auditor + perspective-analyst] → perspective-analyst → historiographic-auditor → uat-tester`

---

## Agent Routing Rules

| Task | Agent | Division |
|---|---|---|
| RSS health, article collection, deduplication, cluster summaries | `feed-intelligence` | Pipeline |
| Bias score accuracy, calibration, benchmarking | `analytics-expert` | Quality |
| Ground-truth validation | `bias-auditor` | Quality |
| Bias regression, validation suite, weight tuning | `bias-calibrator` | Quality |
| Pipeline output validation, clustering quality | `pipeline-tester` | Quality |
| Post-test bug fixing | `bug-fixer` | Quality |
| Pipeline runtime, frontend load, Lighthouse | `perf-optimizer` | Infrastructure |
| Article/cluster data quality, NULL audits | `db-reviewer` | Infrastructure |
| Sync docs with codebase | `update-docs` | Infrastructure |
| Build UI components, new features | `frontend-builder` | Frontend |
| Fix UI bugs, layout breaks, a11y | `frontend-fixer` | Frontend |
| Desktop/mobile responsive | `responsive-specialist` | Frontend |
| Browser testing, click QA | `uat-tester` | Frontend |
| spaCy, bias algorithms, NER | `nlp-engineer` | Pipeline |
| Source vetting, credibility | `source-curator` | Pipeline |
| Bias lexicon research | `linguist` | Pipeline |
| Broadcast audio, sonic branding, TTS, post-processing | `audio-engineer` | Audio |
| Security audit, secrets scan, RLS, OWASP | `void-ciso` | Security |
| Strategic advice, roadmap | `ceo-advisor` | Product |
| Logo, favicon, brand identity, palette | `logo-designer` | Branding |
| Camera, DOF, parallax, scene composition | `cinematographer` | Cinematic |
| Grain, color grading, vignette, lens, atmosphere | `vfx-artist` | Cinematic |
| Scroll choreography, scene timelines, gesture physics | `motion-director` | Cinematic |
| Per-image CSS color grading, page filter pipelines | `color-grader` | Cinematic |
| Agent audit, optimization, new agent design | `agent-architect` | Agent Engineering |
| Historical event research, YAML content | `history-curator` | History |
| Multi-perspective balance, viewpoint gaps | `perspective-analyst` | History |
| Historical accuracy validation | `historiographic-auditor` | History |
| Primary source discovery, rights/provenance | `media-archaeologist` | History |
| Free-API image sourcing for weekly/history | `media-curator` | Pipeline |
| Event connections, timeline data | `timeline-architect` | History |
| Narrative polish, show-don't-tell | `narrative-engineer` | History |
| Archival Cinema UI, Ken Burns, history layouts | `visual-historian` | History Visual |
| Geographic visualization, map layers | `archive-cartographer` | History Visual |
| Game content — words, puzzles, clue banks | `game-content-writer` | Games |

---

## Parallel Safety

**Can run simultaneously (read-only):** `pipeline-tester`, `db-reviewer`, `void-ciso`, `ceo-advisor`, `uat-tester`, `historiographic-auditor`

**Never simultaneous:** Two write agents on overlapping files; `bug-fixer` + `pipeline-tester`; `frontend-builder` + `frontend-fixer`.

---

## Locked Decisions (CEO Approval)

- Cinematic Press design system (4-voice type, BiasLens Three Lenses, newspaper grid + cinematic tokens)
- 6-axis bias scoring model
- Supabase as single data layer
- Static export (Next.js → GitHub Pages)
- 1,013-source curated list (3 tiers: 43 us_major, 373 international, 597 independent); 7-point lean spectrum; 158 countries
- ~$30/mo LLM cost target (Sonnet 4.6 primary, Gemini fallback); broken intentionally from prior $0 ceiling for editorial quality
- 1x/day pipeline cadence; top-50 homepage feed
- Claude Max CLI for all agent work

---

## Future Expansion

R&I advisory agents (read-only, propose but don't implement):

| Agent | Purpose |
|---|---|
| `data-storytelling-designer` | Bias visualization, chart design |
| `micro-interaction-designer` | Progressive disclosure, delight |
| `accessibility-inclusivity-lead` | WCAG 2.1 AA compliance |

`motion-physics-designer` was promoted to `cinematographer` + `motion-director` + `vfx-artist` (Cinematic Division, rev 12).

---

## Session Log

| Date | Key Changes |
|---|---|
| 2026-03-19 | First agent chain: bias fixes, Gemini Voice arch, parallelization, favicon/OG, responsive |
| 2026-03-20 | Ranking v3.3 (9 signals, bias-blind); Clustering v2 (entity-merge); multi-section editions |
| 2026-03-21 | Ranking v5.1 (Gemini editorial); Deep Dive redesign; Daily Brief + audio; bias calibration; validation framework (26 fixtures, 96.9%) |
| 2026-03-22 | Audio migration (Gemini TTS trialed, reverted Apr); Vol I reset (370 sources, 4,839 articles, 108 min); perf optimizations |
| 2026-03-29 | Cinematic Division added (cinematographer, motion-director, vfx-artist); 20→23 agents, 9→10 divisions; Cinematic Press v2; sources 370→409 |
| 2026-03-31 | Source review: 11 RSS fixed, 13 right-spectrum added, L:R 1.82:1→1.54:1; 409→419 |
| 2026-04-02 | Major source expansion 419→951 (+532), 77→155 countries, L:R 1.16:1; India→South Asia rename; Europe edition added |
| 2026-04-03 | Sources 951→1,013 (EU +49, SA +27); ranking v5.7/v5.8 edition-unique; migrations 030-036; linguist agent; weekly digest; 24 agents, 11 divisions |
| 2026-04-04 | void --history launch: 19 components, 5-lens framework, 25 events, migrations 039+043, 8 history agents; 32 agents, 13 divisions |
| 2026-04-05 | color-grader + media-curator added; per-image CSS grading; ranking v6.0 (10 signals, holistic re-rank step 8c); 34 agents, 13 divisions |
| 2026-04-10 | History museum redesign: 8-stage journey, 25→58 events, 20→22 components; DeepDiveSpectrum 3 toggleable views; migration 045; generate-history-audio workflow |
| 2026-04-11 | edge-tts replaces Gemini TTS permanently; void --games added (5 games); game-content-writer; 35 agents, 14 divisions |
| 2026-04-29 | **Editorial LLM stack moves to Claude Sonnet 4.6** (~$30/mo, was $0); pipeline cadence 2x/day → 1x/day; homepage feed 30 → 50; smart-routed Claude→Gemini; content-hash cache on top-50 post-rerank (migration 049); ephemeral prompt caching |
