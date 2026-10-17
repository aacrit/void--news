---
name: workflows
description: "Lists all available workflows, agent team, and slash commands for void --news."
user-invocable: true
disable-model-invocation: false
allowed-tools: []
---

# /agents — void --news Agent Fleet & Workflows

Print the following reference card to the user. Do not run any tools — just display this information.

---

## Workflows (Slash Commands)

| Command | Agents | Pattern | When to Use |
|---------|--------|---------|-------------|
| `/pipeline-qa` | pipeline-tester, bug-fixer | Validate -> Fix -> Re-validate | After any `pipeline/` code change |
| `/bias-audit` | analytics-expert, bias-auditor, nlp-engineer, pipeline-tester | Benchmark -> Fix -> Confirm | Gold standard for bias engine changes |
| `/bias-calibrate` | nlp-engineer, bias-calibrator, analytics-expert, bias-auditor, pipeline-tester | Tune -> Check -> Verify | Precision tuning of scoring params |
| `/frontend-ship` | frontend-builder, responsive-specialist, perf-optimizer, uat-tester, frontend-fixer | Build -> Test -> Fix | Any UI change or feature |
| `/audio-qa` | audio-engineer, pipeline-tester, db-reviewer, bug-fixer | Review -> Validate -> Fix | Daily brief audio changes |
| `/full-audit` | void-ciso, db-reviewer, perf-optimizer, update-docs, bias-calibrator, bug-fixer, frontend-fixer | 5-way audit -> Triage -> Fix | Comprehensive system health check |
| `/launch-check` | 8 agents parallel, ceo-advisor | 8-way validate -> Go/No-go | Pre-launch final gate |
| `/daily-ops` | feed-intelligence, db-reviewer, pipeline-tester | 3-way health check | Morning check / post-pipeline |
| `/source-review` | source-curator, feed-intelligence, analytics-expert, pipeline-tester | Vet -> Health check -> Validate | Adding/removing/auditing sources |
| `/security-sweep` | void-ciso, perf-optimizer, bug-fixer, pipeline-tester | Audit -> Fix -> Re-verify | Fast security + perf hardening |
| `/rank-optimize` | analytics-expert, db-reviewer, nlp-engineer, pipeline-tester | Benchmark -> Tune -> Validate | Ranking engine weight tuning |

## Other Skills

| Command | Purpose |
|---------|---------|
| `/pressdesign` | Press & Precision design enforcement for UI tasks |
| `/agents` | This reference card |

## Agent Team (20 Agents, 9 Divisions)

```
CEO (Aacrit)
  +-- Agent Engineering -- agent-architect
  +-- Quality ----------- analytics-expert, bias-auditor, bias-calibrator, pipeline-tester, bug-fixer
  +-- Infrastructure ---- perf-optimizer, db-reviewer, update-docs
  +-- Frontend ---------- frontend-builder, frontend-fixer, responsive-specialist, uat-tester
  +-- Pipeline ---------- feed-intelligence, nlp-engineer, source-curator
  +-- Audio ------------- audio-engineer
  +-- Security ---------- void-ciso
  +-- Product ----------- ceo-advisor
  +-- Branding ---------- logo-designer
```

## Agent Routing Quick Reference

| Task | Agent |
|------|-------|
| RSS health, article collection, dedup, content quality | `feed-intelligence` |
| Bias score accuracy, calibration, benchmarking | `analytics-expert` |
| Ground-truth validation, known-outlet comparison | `bias-auditor` |
| Bias score regression, validation suite, weight tuning | `bias-calibrator` |
| Pipeline output validation, clustering quality | `pipeline-tester` |
| Post-test bug fixing | `bug-fixer` |
| Pipeline runtime, frontend load, Lighthouse | `perf-optimizer` |
| Article/cluster data quality, NULL audits | `db-reviewer` |
| Sync docs with codebase | `update-docs` |
| Build UI components, new features | `frontend-builder` |
| Fix UI bugs, layout breaks, a11y gaps | `frontend-fixer` |
| Desktop/mobile layout, responsive issues | `responsive-specialist` |
| Browser testing, click-through QA | `uat-tester` |
| spaCy models, bias scoring, NER | `nlp-engineer` |
| Broadcast audio, sonic branding, TTS voice | `audio-engineer` |
| Source vetting, RSS config, credibility | `source-curator` |
| Security audit, secrets scan, RLS, OWASP | `void-ciso` |
| Strategic advice, roadmap, priorities | `ceo-advisor` |
| Logo, favicon, brand identity | `logo-designer` |
| Agent audit, optimization, new agent design | `agent-architect` |

## Workflow Conventions

- `||` = parallel stage, `->` = sequential stage
- Gate between stages: if a stage passes clean, later fix stages may be skipped
- All workflows produce structured CEO reports
- $0 cost: Claude Max CLI only, no API keys needed
