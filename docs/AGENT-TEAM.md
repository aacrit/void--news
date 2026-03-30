# void --news Agent Team Structure

Last updated: 2026-03-29 (rev 12)

## Philosophy

Adapted from DondeAI. Every principle is inherited and tailored for a news bias analysis platform.

### Core Principles

1. **No Hierarchical Delegation** — Agents cannot spawn other agents. Task routing at the human level.
2. **Read-First Protocol** — Every agent reads CLAUDE.md + relevant docs before any work.
3. **Execution Protocol** — Assess → Plan → Build → Verify → Report. No exceptions.
4. **Max Blast Radius** — Max 4 CSS, 2 JS/TS, 3 Python files per run.
5. **$0 Cost — Claude Max CLI Only** — All agent/dev work via Claude Code CLI. The only permitted external API call is Gemini Flash on its free tier. No paid inference anywhere.
6. **Parallel-Safe vs Sequential** — Read-only agents can run simultaneously. Write agents require sequencing.

### Cost Policy

```
COST BUDGET: $0.00 — ABSOLUTE CEILING

Pipeline NLP:      Rule-based only (spaCy, NLTK, TextBlob) — $0
Summarization:     Gemini Flash free tier (~116 RPD used, 7.7% of 1500 limit) — $0
Audio TTS:         Gemini 2.5 Flash TTS free tier (same GEMINI_API_KEY) — $0
Database:          Supabase free tier — $0
Hosting:           GitHub Pages — $0
CI/CD:             GitHub Actions free tier — $0
Agent work:        Claude Code CLI (Max subscription) — $0
```

---

## Organizational Structure

```
CEO (Aacrit)
  ├── Agent Engineering — agent-architect
  ├── Quality ————————— analytics-expert, bias-auditor, bias-calibrator, pipeline-tester, bug-fixer
  ├── Infrastructure ——— perf-optimizer, db-reviewer, update-docs
  ├── Frontend ————————— frontend-builder, frontend-fixer, responsive-specialist, uat-tester
  ├── Cinematic ————————— cinematographer, vfx-artist, motion-director
  ├── Pipeline ————————— feed-intelligence, nlp-engineer, source-curator
  ├── Audio ———————————— audio-engineer
  ├── Security ————————— void-ciso
  ├── Product —————————— ceo-advisor
  └── Branding ————————— logo-designer
```

**Total: 23 agents across 10 divisions**

---

## Division Roster

### Quality Division

| Agent | Purpose | Write Access | Trigger |
|-------|---------|-------------|---------|
| `analytics-expert` | Bias engine benchmarking, ranking calibration | Yes | After algorithm changes |
| `bias-auditor` | Ground-truth validation against known outlet profiles | Yes | After scoring changes |
| `bias-calibrator` | Validation suite execution, score regression detection, axis weight tuning, ground-truth corpus maintenance. Quantitative counterpart to bias-auditor (qualitative). CI gate: `validate-bias.yml` runs on every push to `claude/*` touching `pipeline/analyzers/`; blocks merge on CATASTROPHIC failures. | Yes | After analyzer changes, on regression alert |
| `pipeline-tester` | Pipeline quality gate — parsing, clustering, scoring validation | No | After every pipeline change |
| `bug-fixer` | Post-test bug remediation, surgical fixes | Yes | After test failures |

### Infrastructure Division

| Agent | Purpose | Write Access | Trigger |
|-------|---------|-------------|---------|
| `perf-optimizer` | Pipeline runtime + frontend load time optimization | Yes | Performance issues |
| `db-reviewer` | Supabase data quality — articles, bias scores, clusters | No | After pipeline runs |
| `update-docs` | Sync CLAUDE.md and docs/*.md with current codebase | Yes | After significant changes |

### Frontend Division

| Agent | Purpose | Write Access | Trigger |
|-------|---------|-------------|---------|
| `frontend-builder` | Component engineering — Press & Precision design system | Yes | Feature requests |
| `frontend-fixer` | UI bug remediation — bias display, layout, animation, a11y | Yes | Bug reports |
| `responsive-specialist` | Desktop/mobile layout, light/dark modes | Yes | New components, responsive bugs |
| `uat-tester` | Browser testing — clicks, resizes, screenshots | No | After frontend changes |

### Pipeline Division

| Agent | Purpose | Write Access | Trigger |
|-------|---------|-------------|---------|
| `feed-intelligence` | RSS health, collection strategy, deduplication, cluster summarization | Yes | Pipeline development |
| `nlp-engineer` | spaCy/NLTK specialist — bias scoring algorithms, NER, sentiment | Yes | Bias engine development |
| `source-curator` | Source credibility vetting, RSS/scrape config, 380-source list | Yes | Source list changes |

### Cinematic Division

| Agent | Purpose | Write Access | Trigger |
|-------|---------|-------------|---------|
| `cinematographer` | Camera language design — depth of field, rack focus, parallax, camera movements, scene compositions, cinematic design tokens | Yes | Cinematic overhaul, motion design tasks |
| `vfx-artist` | Post-processing — film grain, color grading, vignettes, lens effects, atmospheric lighting, texture via CSS filters and SVG | Yes | After cinematographer, cinematic polish |
| `motion-director` | Scroll-driven choreography — scene timelines, gesture physics, transition sequencing, L-cut/match-cut timing, scroll-timeline API | Yes | After cinematographer, interaction choreography |

### Agent Engineering Division

| Agent | Purpose | Write Access | Trigger |
|-------|---------|-------------|---------|
| `agent-architect` | Audits, optimizes, and designs all agents. Reviews definitions for best-in-class tooling, cost efficiency, prompt engineering. Builds new agents on CEO demand. | Yes (agent definitions only) | CEO request, post-major-change review, periodic fleet audit |

### Security Division

| Agent | Purpose | Write Access |
|-------|---------|-------------|
| `void-ciso` | Secrets, RLS, CORS, injection, OWASP, dependencies | No |

### Product Division

| Agent | Purpose | Write Access |
|-------|---------|-------------|
| `ceo-advisor` | Strategic counsel — roadmap, competitive positioning | No |

### Branding Division

| Agent | Purpose | Write Access |
|-------|---------|-------------|
| `logo-designer` | Brand identity — logo, favicon, SVG assets, cinematic palette, texture system | Yes |

---

## Sequential Cycles

**Quality Cycle:**
```
pipeline-tester → bug-fixer → pipeline-tester (retest)
```

**Bias Audit Cycle:**
```
analytics-expert → bias-auditor → nlp-engineer → pipeline-tester
```

**Bias Calibration Cycle:**
```
nlp-engineer → bias-calibrator → bias-auditor → pipeline-tester
```

**Frontend Cycle:**
```
frontend-builder → responsive-specialist → uat-tester → frontend-fixer
```

**Audio Quality Cycle:**
```
audio-engineer → pipeline-tester → bug-fixer
```

**Cinematic Overhaul Cycle:**
```
[logo-designer + cinematographer] (parallel) → motion-director → vfx-artist → frontend-builder → [responsive-specialist + perf-optimizer] (parallel) → uat-tester → frontend-fixer
```

**Full Pipeline Dev Cycle:**
```
feed-intelligence → nlp-engineer → pipeline-tester → bug-fixer → pipeline-tester
```

---

## Agent Routing Rules

| Task Pattern | Agent | Division |
|---|---|---|
| RSS feed health, article collection, deduplication, cluster summaries, content quality | `feed-intelligence` | Pipeline |
| Bias score accuracy, calibration, benchmarking | `analytics-expert` | Quality |
| Ground-truth validation, known-outlet comparison | `bias-auditor` | Quality |
| Bias score regression, validation suite, weight tuning | `bias-calibrator` | Quality |
| Pipeline output validation, clustering quality | `pipeline-tester` | Quality |
| Post-test bug fixing | `bug-fixer` | Quality |
| Pipeline runtime, frontend load, Lighthouse | `perf-optimizer` | Infrastructure |
| Article/cluster data quality, NULL audits | `db-reviewer` | Infrastructure |
| Sync docs with codebase | `update-docs` | Infrastructure |
| Build UI components, new features | `frontend-builder` | Frontend |
| Fix UI bugs, layout breaks, a11y gaps | `frontend-fixer` | Frontend |
| Desktop/mobile layout, responsive issues | `responsive-specialist` | Frontend |
| Browser testing, click-through QA | `uat-tester` | Frontend |
| spaCy models, bias scoring algorithms, NER | `nlp-engineer` | Pipeline |
| Source vetting, RSS config, credibility | `source-curator` | Pipeline |
| Broadcast audio, sonic branding, TTS voice, audio post-processing | `audio-engineer` | Audio |
| Security audit, secrets scan, RLS, OWASP | `void-ciso` | Security |
| Strategic advice, roadmap, priorities | `ceo-advisor` | Product |
| Logo, favicon, brand identity, cinematic palette, texture system | `logo-designer` | Branding |
| Camera movement, depth of field, parallax, cinematic scene composition | `cinematographer` | Cinematic |
| Film grain, color grading, vignette, lens effects, atmospheric post-processing | `vfx-artist` | Cinematic |
| Scroll-driven choreography, scene timelines, gesture physics, transition sequencing | `motion-director` | Cinematic |
| Agent audit, optimization, new agent design, prompt engineering | `agent-architect` | Agent Engineering |

---

## Parallel Safety

**Can run simultaneously (read-only):** `pipeline-tester`, `db-reviewer`, `void-ciso`, `ceo-advisor`, `uat-tester`

**Never run simultaneously:** Two write agents on overlapping files; `bug-fixer` + `pipeline-tester`; `frontend-builder` + `frontend-fixer`.

---

## Locked Decisions (Require CEO Approval)

- Press & Precision design system (3-voice type, BiasLens Three Lenses, newspaper grid)
- 6-axis bias scoring model (political lean, sensationalism, opinion/fact, factual rigor, framing + confidence)
- Supabase as single data layer
- Static export (Next.js → GitHub Pages)
- 380-source curated list (3 tiers: 49 us_major, 158 international, 173 independent); 7-point political lean spectrum
- $0 operational cost constraint
- Claude Max CLI for all agent work; Gemini Flash free tier only for pipeline summarization

---

## Future Expansion

R&I advisory agents (read-only, propose but don't implement):

| Agent | Purpose |
|-------|---------|
| `data-storytelling-designer` | Bias visualization, chart design |
| `micro-interaction-designer` | Progressive disclosure, delight |
| `accessibility-inclusivity-lead` | WCAG 2.1 AA compliance |

Note: `motion-physics-designer` was promoted to three active agents: `cinematographer`, `motion-director`, `vfx-artist` (Cinematic Division, rev 12).

---

## Session Log (Major Changes)

| Date | Key Changes |
|------|-------------|
| 2026-03-19 | Full agent chain run: bias engine fixes (nlp-engineer), Gemini Voice architecture (feed-intelligence), ThreadPoolExecutor parallelization (perf-optimizer), full favicon set + OG meta (logo-designer), responsive fixes (responsive-specialist) |
| 2026-03-20 | Ranking v3.2→v3.3: 9 signals, confidence multiplier, lead gate, soft-floor normalization, topic diversity re-rank; dedup threshold 0.80; 3-article majority vote categorization; rerank.py; "Why This Story" tooltip; bias-blind ranking principle |
| 2026-03-20 | Clustering v2 (threshold 0.2, entity-overlap merge pass); multi-section cross-listing (sections[], migration 011); source count corrected to 222 |
| 2026-03-21 | Ranking v5.1 (Gemini editorial importance 12%, US-only divergence damper, cross-spectrum bonus, step 6c Gemini reasoning, step 7c editorial triage); new gemini_reasoning.py analyzer; migrations 012-013; Deep Dive redesign (seamless lede, dd-analysis-row, BiasInspectorInline, Source Perspectives, slot-machine cascade, iOS bottom-sheet, NavBar dateline with edition badge pills + regional timestamps) |
| 2026-03-21 | Daily Brief (step 7d): pipeline/briefing/ module (daily_brief_generator.py, audio_producer.py, voice_rotation.py, generate_assets.py); Gemini BBC-style two-host TL;DR + audio script; edge-tts synthesis + pydub stitching; migration 017 (daily_briefs table + audio-briefs Storage); DailyBrief.tsx frontend component ("void --onair" pill + ScaleIcon + progress bar); pipeline cron corrected to 4x daily |
| 2026-03-21 | Bias engine calibration (all 5 analyzers): sparsity-weighted baseline blending; LOW_CREDIBILITY_US_MAJOR (22 outlets) baseline 35; SPECIFIC_ATTRIBUTION verb-proximity gate; value_judgment denominator fix (weight 0.06); partisan_attack cap 30pts; superlative word-boundary regex; "invasion"/"killed" intensity reduced; passive voice ratio capped at 30; adaptive EMA alpha (0.3/0.15); cluster entity cache excludes current article. New: pipeline/validation/ (28-fixture ground-truth suite, signal_tracker, AllSides cross-ref, runner with --verbose/--quick/--json/--update-snapshot, snapshot.json). |
| 2026-03-22 | Step 8b cluster dedup (delete stale clusters superseded by current run via article overlap); RSS global timeout fix (as_completed TimeoutError caught gracefully — hung feeds skipped without pipeline crash); refresh_audio.py (standalone audio regeneration ~60-90s); HomeContent progressive batch reveal (BATCH_SIZE=8, infinite scroll mobile); layout fixes (overflow-x hidden, min-width 0 on grid children); Daily Brief typography: Inter regular + blockquote left-border (replaced Playfair italic); justified body text with hyphens:auto; lean chips right-aligned via flex spacer; filter-row opaque bg-primary (was glass-bg). |
| 2026-03-22 | Audio TTS migration: replaced Google Cloud TTS Neural2 + edge-tts with Gemini 2.5 Flash TTS (`gemini-2.5-flash-preview-tts`). Both speakers synthesized in a single API call with LLM-native prosody — no per-turn stitching. PCM 24kHz → pydub (pips + outro) → MP3 128k mono. voice_rotation.py rewritten to use Gemini prebuilt voices (5 rotating host pairs shared across all editions: Charon/Aoede, Orus/Zephyr, Sadaltager/Kore, Achird/Gacrux, Algenib/Achernar; opinion voice fixed per edition; 30 voices available). claude_brief_generator.py added (Claude CLI premium manual generator). Removed dependencies: edge-tts, google-cloud-texttospeech. Code: 592 lines → 231 lines. Benchmark: 211 words → 75.8s audio, 42s latency, $0. |
| 2026-03-22 | Vol I clean DB reset: first-ever full pipeline run on empty database, 370 sources, 4,839 articles stored, 1,061 clusters (959 news + 102 opinion). Perf analysis (perf-optimizer): run took 108 min vs. 6 min budget; realistic incremental target 25-35 min after optimizations. Applied: TextBlob 50K→5K chars (sensationalism.py), RSS cap 30/feed (rss_fetcher.py), bias workers 4→8 (main.py). Source count reconciled: sources.json has 370 sources (49 us_major / 154 international / 167 independent), not 222 as previously documented. Validation framework (pipeline/validation/): 26-fixture ground-truth suite + signal_tracker + AllSides cross-ref + runner; 96.9% accuracy on first run. |
