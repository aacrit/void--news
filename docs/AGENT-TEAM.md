# void --news Agent Team Structure

Last updated: 2026-03-20 (rev 4)

## Philosophy

Adapted from DondeAI's proven agent ecosystem. Every principle below is inherited and tailored for a news bias analysis platform.

### Core Principles

1. **No Hierarchical Delegation** — Agents cannot spawn other agents. Task routing happens at the human level (CEO).
2. **Read-First Protocol** — Every agent reads CLAUDE.md + relevant docs before any work.
3. **Execution Protocol** — Assess → Plan → Build → Verify → Report. No exceptions.
4. **Max Blast Radius** — Each agent has bounded file modification limits (max 4 CSS, 2 JS/TS, 3 Python per run).
5. **$0 Cost — Claude Max CLI Only** — All agent/development AI work uses Claude Code CLI (claude-opus via Max subscription). No paid inference anywhere. The only permitted external API call is Gemini Flash for pipeline cluster summarization, capped at 25 calls/run on its free tier. No OpenAI, no paid Anthropic API, no other paid inference. This is a hard constraint.
6. **Parallel-Safe vs Sequential** — Read-only agents can run simultaneously. Write agents require sequencing.
7. **Model Tiering** — Opus for creative agents, Sonnet for execution agents, Haiku for read-only agents.

### Cost Policy

```
COST BUDGET: $0.00 — ABSOLUTE CEILING

All AI agent work runs through Claude Code CLI (Max subscription).
No paid inference. No exceptions.

Pipeline NLP (bias analysis): Rule-based only (spaCy, NLTK, TextBlob) — $0
Pipeline summarization: Gemini Flash free tier (25 calls/run cap, 50 RPD = 3.3% of 1500 RPD limit) — $0
Database: Supabase free tier — $0
Hosting: GitHub Pages — $0
CI/CD: GitHub Actions free tier — $0
Agent work: Claude Code CLI (Max subscription) — $0
```

**Before running ANY command that could incur API costs:** Stop. The only permitted external API is Gemini Flash via its free tier, hard-capped at 25 calls/run. If a task seems to require paid inference, redesign the approach to use rule-based NLP or Claude CLI.

---

## Organizational Structure

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

**Total: 17 agents across 7 divisions**

---

## Division Roster

### Quality Division (4 agents)

| Agent | Purpose | Model | Write Access | Trigger |
|-------|---------|-------|-------------|---------|
| `analytics-expert` | Bias engine benchmarking, ranking calibration, competitive gap analysis | sonnet | Yes | After algorithm changes, periodic audits |
| `bias-auditor` | Ground-truth bias validation against known outlet profiles | sonnet | Yes | After scoring changes, periodic |
| `pipeline-tester` | Pipeline quality gate — article parsing, clustering, scoring validation | haiku | No (read-only) | After every pipeline change |
| `bug-fixer` | Post-test bug remediation, root-cause grouping, surgical fixes | sonnet | Yes | After test failures |

### Infrastructure Division (3 agents)

| Agent | Purpose | Model | Write Access | Trigger |
|-------|---------|-------|-------------|---------|
| `perf-optimizer` | Pipeline runtime + frontend load time optimization | sonnet | Yes | Performance issues, periodic |
| `db-reviewer` | Supabase data quality — articles, bias scores, clusters, sources | haiku | No (read-only) | After pipeline runs, schema changes |
| `update-docs` | Sync CLAUDE.md and docs/*.md with current codebase | sonnet | Yes | After significant changes |

### Frontend Division (4 agents)

| Agent | Purpose | Model | Write Access | Trigger |
|-------|---------|-------|-------------|---------|
| `frontend-builder` | Component engineering — Press & Precision design system | sonnet | Yes | Feature requests, build tasks |
| `frontend-fixer` | UI bug remediation — bias display, layout, animation, a11y | sonnet | Yes | Bug reports, visual issues |
| `responsive-specialist` | Desktop/mobile layout optimization, light/dark modes | sonnet | Yes | New components, responsive bugs |
| `uat-tester` | Browser testing — clicks, resizes, screenshots, severity-ranked findings | haiku | No (read-only) | After frontend changes |

### Pipeline Division (3 agents)

| Agent | Purpose | Model | Write Access | Trigger |
|-------|---------|-------|-------------|---------|
| `feed-intelligence` | RSS health, collection strategy, deduplication, cluster summarization, frontend content | sonnet | Yes | Pipeline development, content quality issues |
| `nlp-engineer` | spaCy/NLTK specialist — bias scoring algorithms, NER, sentiment | sonnet | Yes | Bias engine development |
| `source-curator` | Source credibility vetting, RSS/scrape config, 200-source list | sonnet | Yes | Source list changes |

### Security Division (1 agent)

| Agent | Purpose | Model | Write Access | Trigger |
|-------|---------|-------|-------------|---------|
| `void-ciso` | Security audit — secrets, RLS, CORS, injection, OWASP, dependencies | haiku | No (read-only) | Periodic, before launch |

### Product Division (1 agent)

| Agent | Purpose | Model | Write Access | Trigger |
|-------|---------|-------|-------------|---------|
| `ceo-advisor` | Strategic product counsel — roadmap, competitive positioning, priorities | haiku | No (read-only) | Strategic decisions |

### Branding Division (1 agent)

| Agent | Purpose | Model | Write Access | Trigger |
|-------|---------|-------|-------------|---------|
| `logo-designer` | Brand identity — logo, favicon, SVG assets, editorial design | opus | Yes | Branding tasks |

---

## Sequential Cycles

**Quality Cycle:**
```
pipeline-tester → (review results) → bug-fixer → pipeline-tester (retest)
```

**Bias Audit Cycle:**
```
analytics-expert → bias-auditor → nlp-engineer → pipeline-tester
```

**Frontend Cycle:**
```
frontend-builder → responsive-specialist → uat-tester → frontend-fixer
```

**Content Quality Cycle:**
```
feed-intelligence → pipeline-tester → (if issues) → bug-fixer → pipeline-tester
```

**Full Pipeline Development Cycle:**
```
feed-intelligence (ingestion) → nlp-engineer (bias) → pipeline-tester (validate) → bug-fixer (fix) → pipeline-tester (retest)
```

---

## Agent Routing Rules

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

---

## Parallel Safety

**Can run simultaneously (read-only):**
- `pipeline-tester`
- `db-reviewer`
- `void-ciso`
- `ceo-advisor`
- `uat-tester`

**Never run simultaneously:**
- Two write-capable agents modifying the same files
- `bug-fixer` + `pipeline-tester` (sequential required)
- `frontend-builder` + `frontend-fixer` (sequential required)

---

## Locked Decisions (Require CEO Approval to Change)

- Press & Precision design system (3-voice type, dot matrix rule, newspaper grid)
- 6-axis bias scoring model (political lean, sensationalism, opinion/fact, factual rigor, framing + confidence)
- Supabase as single data layer
- Static export (Next.js → GitHub Pages)
- 200-source curated list structure (3 tiers: 49 us_major + 67 international + 84 independent); 7-point political lean spectrum
- $0 operational cost constraint
- Claude Max CLI for all agent/dev work; Gemini Flash free tier only for pipeline cluster summarization (no paid inference)

---

## Future Expansion (Phase 2)

When the product matures, add R&I division advisory agents:

| Agent | Purpose | From DondeAI |
|-------|---------|-------------|
| `motion-physics-designer` | Spring physics, gesture interactions | Direct port |
| `data-storytelling-designer` | Bias visualization, chart design | Direct port |
| `micro-interaction-designer` | Progressive disclosure, delight moments | Direct port |
| `accessibility-inclusivity-lead` | WCAG 2.1 AA compliance | Direct port |

These are read-only advisory agents — they propose, they don't implement.

---

## Session Log

### 2026-03-19 — Full Agent Chain Run (6 chains + Gemini Voice)

**Agents run:** `nlp-engineer`, `bug-fixer`, `feed-intelligence`, `perf-optimizer`, `responsive-specialist`, `logo-designer`, `update-docs`

| Agent | Division | Outcome |
|-------|----------|---------|
| `nlp-engineer` | Pipeline | Bias engine fixes: COMMON_ACRONYMS frozenset in sensationalism.py, attribution floor 80→50 in opinion_detector.py, 12 new political_lean keywords + 4 framing phrases, SPECIFIC_ATTRIBUTION counted as named sources in factual_rigor.py |
| `bug-fixer` | Quality | Confidence `text_conf` binary threshold replaced with smooth linear ramp (0.1 at no text → 1.0 at 1000+ chars) in main.py |
| `feed-intelligence` | Pipeline | Gemini Voice architecture: `_SYSTEM_INSTRUCTION`, `_USER_PROMPT_TEMPLATE`, `_PROHIBITED_TERMS` (26 terms), `_check_quality()` validator; source slugs rendered as tier labels in prompts; `generate_json()` extended with optional `system_instruction` param |
| `perf-optimizer` | Infrastructure | ThreadPoolExecutor parallelization for cluster enrichment + full-text truncation (8 workers each); pip + spaCy model caching in pipeline.yml; next.config.ts compress + no source maps; migration 009_perf_indexes.sql (3 composite indexes) |
| `responsive-specialist` | Frontend | Safe area inset for iPhone notch; DeepDive symmetric translateX/translateY animation; BiasLens SignalRing position fix; article role="button" moved to inner div in LeadStory + StoryCard |
| `logo-designer` | Branding | Full favicon set (SVG, ICO, PNG 16/32/180/192/512), OpenGraph 1200x630, Twitter card 1024x512; manifest.json updated; layout.tsx favicon metadata + Supabase preconnect + OG/Twitter meta; --bias-far-left/--bias-far-right tokens added; loading indicator copy updated |
| `update-docs` | Infrastructure | CLAUDE.md: migration count 001-007→001-009, Gemini Voice architecture note, GEMINI-VOICE-PLAN.md added to project structure; AGENT-TEAM.md: session log added |

**Files modified this session:** ~25 files across pipeline, frontend, supabase/migrations, .github/workflows, and docs.

### 2026-03-20 — Ranking Engine v3.2 + Pipeline Improvements

**Agents run:** `update-docs`

| Agent | Division | Outcome |
|-------|----------|---------|
| `update-docs` | Infrastructure | CLAUDE.md + AGENT-TEAM.md updated to reflect: ranking engine v3.2 (9 signals, confidence multiplier, lead eligibility gate, soft-floor normalization, topic diversity re-rank); dedup threshold 0.80; 3-article majority vote categorization; new `pipeline/rerank.py` standalone script; "Why This Story" tooltip on StoryCard + LeadStory; bias-blind ranking design principle; source map dual-key fix |

**Files modified this session:** `CLAUDE.md`, `docs/AGENT-TEAM.md`
