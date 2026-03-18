# void --news Agent Team Structure

Last updated: 2026-03-18

## Philosophy

Adapted from DondeAI's proven agent ecosystem. Every principle below is inherited and tailored for a news bias analysis platform.

### Core Principles

1. **No Hierarchical Delegation** — Agents cannot spawn other agents. Task routing happens at the human level (CEO).
2. **Read-First Protocol** — Every agent reads CLAUDE.md + relevant docs before any work.
3. **Execution Protocol** — Assess → Plan → Build → Verify → Report. No exceptions.
4. **Max Blast Radius** — Each agent has bounded file modification limits (max 4 CSS, 2 JS/TS, 3 Python per run).
5. **$0 Cost — Claude Max CLI Only** — All AI/LLM work uses Claude Code CLI (claude-opus via Max subscription). No API-based LLM calls anywhere. No OpenAI, no Anthropic API keys, no paid inference. This is a hard constraint.
6. **Parallel-Safe vs Sequential** — Read-only agents can run simultaneously. Write agents require sequencing.
7. **Model: Opus** — All agents use Claude Opus via CLI. No model downgrades.

### Cost Policy

```
COST BUDGET: $0.00 — ABSOLUTE CEILING

All AI work runs through Claude Code CLI (Max subscription).
No API keys. No per-token billing. No exceptions.

Pipeline NLP: Rule-based only (spaCy, NLTK, TextBlob) — $0
Database: Supabase free tier — $0
Hosting: GitHub Pages — $0
CI/CD: GitHub Actions free tier — $0
Agent work: Claude Code CLI (Max subscription) — $0
```

**Before running ANY command that could incur API costs:** Stop. There are no API keys. If a task seems to require paid inference, redesign the approach to use rule-based NLP or Claude CLI.

---

## Organizational Structure

```
CEO (Aacrit)
  ├── Quality ————————— analytics-expert, bias-auditor, pipeline-tester, bug-fixer
  ├── Infrastructure ——— perf-optimizer, db-reviewer, update-docs
  ├── Frontend ————————— frontend-builder, frontend-fixer, responsive-specialist, uat-tester
  ├── Pipeline ————————— nlp-engineer, source-curator
  ├── Security ————————— void-ciso
  ├── Product —————————— ceo-advisor
  └── Branding ————————— logo-designer
```

**Total: 16 agents across 7 divisions**

---

## Division Roster

### Quality Division (4 agents)

| Agent | Purpose | Model | Write Access | Trigger |
|-------|---------|-------|-------------|---------|
| `analytics-expert` | Bias engine benchmarking, ranking calibration, competitive gap analysis | opus | Yes | After algorithm changes, periodic audits |
| `bias-auditor` | Ground-truth bias validation against known outlet profiles | opus | Yes | After scoring changes, periodic |
| `pipeline-tester` | Pipeline quality gate — article parsing, clustering, scoring validation | opus | No (read-only) | After every pipeline change |
| `bug-fixer` | Post-test bug remediation, root-cause grouping, surgical fixes | opus | Yes | After test failures |

**Sequential Quality Cycle:**
```
pipeline-tester → (review results) → bug-fixer → pipeline-tester (retest)
```

**Bias Audit Cycle:**
```
analytics-expert → bias-auditor → nlp-engineer → pipeline-tester
```

### Infrastructure Division (3 agents)

| Agent | Purpose | Model | Write Access | Trigger |
|-------|---------|-------|-------------|---------|
| `perf-optimizer` | Pipeline runtime + frontend load time optimization | opus | Yes | Performance issues, periodic |
| `db-reviewer` | Supabase data quality — articles, bias scores, clusters, sources | opus | No (read-only) | After pipeline runs, schema changes |
| `update-docs` | Sync CLAUDE.md and docs/*.md with current codebase | opus | Yes | After significant changes |

### Frontend Division (4 agents)

| Agent | Purpose | Model | Write Access | Trigger |
|-------|---------|-------|-------------|---------|
| `frontend-builder` | Component engineering — Press & Precision design system | opus | Yes | Feature requests, build tasks |
| `frontend-fixer` | UI bug remediation — bias display, layout, animation, a11y | opus | Yes | Bug reports, visual issues |
| `responsive-specialist` | Desktop/mobile layout optimization, light/dark modes | opus | Yes | New components, responsive bugs |
| `uat-tester` | Browser testing — clicks, resizes, screenshots, severity-ranked findings | opus | No (read-only) | After frontend changes |

**Sequential Frontend Cycle:**
```
frontend-builder → responsive-specialist → uat-tester → frontend-fixer
```

### Pipeline Division (2 agents)

| Agent | Purpose | Model | Write Access | Trigger |
|-------|---------|-------|-------------|---------|
| `nlp-engineer` | spaCy/NLTK specialist — bias scoring algorithms, NER, sentiment | opus | Yes | Bias engine development |
| `source-curator` | Source credibility vetting, RSS/scrape config, 90-source list | opus | Yes | Source list changes |

### Security Division (1 agent)

| Agent | Purpose | Model | Write Access | Trigger |
|-------|---------|-------|-------------|---------|
| `void-ciso` | Security audit — secrets, RLS, CORS, injection, OWASP, dependencies | opus | No (read-only) | Periodic, before launch |

### Product Division (1 agent)

| Agent | Purpose | Model | Write Access | Trigger |
|-------|---------|-------|-------------|---------|
| `ceo-advisor` | Strategic product counsel — roadmap, competitive positioning, priorities | opus | No (read-only) | Strategic decisions |

### Branding Division (1 agent)

| Agent | Purpose | Model | Write Access | Trigger |
|-------|---------|-------|-------------|---------|
| `logo-designer` | Brand identity — logo, favicon, SVG assets, editorial design | opus | Yes | Branding tasks |

---

## Agent Routing Rules

| Task Pattern | Agent | Division |
|---|---|---|
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
- 90-source curated list structure (3 tiers × 30)
- $0 operational cost constraint
- Claude Max CLI for all AI work (no API LLMs)

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
