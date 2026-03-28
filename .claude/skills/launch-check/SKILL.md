---
name: launch-check
description: "Pre-Launch Readiness Check: all quality agents validate in parallel, then ceo-advisor assesses go/no-go. The final gate before shipping."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /launch-check — Pre-Launch Readiness Check

You are the workflow orchestrator for the **Pre-Launch Readiness Check** — the final gate before any major release of void --news. This runs every quality agent in parallel, then feeds results to the CEO Advisor for a go/no-go recommendation.

## Objective

Determine if void --news is ready to ship. Every system must pass its quality bar. One P0 = no-go.

## Workflow Stages

```
┌──────────────────────────────────────────────────────────────┐
│  STAGE 1 — EIGHT-WAY PARALLEL VALIDATION                     │
│                                                               │
│  pipeline-tester ─── pipeline output quality                  │
│  bias-calibrator ─── bias engine accuracy (96.9%+ required)   │
│  uat-tester ──────── browser UAT (homepage + Deep Dive)       │
│  responsive-spec ─── dual-layout validation                   │
│  perf-optimizer ──── Lighthouse 90+ target                    │
│  void-ciso ──────── security sweep                            │
│  db-reviewer ─────── data completeness                        │
│  feed-intelligence ─ content freshness + feed health          │
├──────────────────────────────────────────────────────────────┤
│  STAGE 2 — STRATEGIC ASSESSMENT (sequential)                 │
│  ceo-advisor: go/no-go recommendation with rationale          │
├──────────────────────────────────────────────────────────────┤
│  GATE: GO → deploy | NO-GO → prioritized fix list            │
├──────────────────────────────────────────────────────────────┤
│  STAGE 3 — DEPLOY (conditional)                              │
│  Push to claude/* branch → auto-merge → gh run watch          │
└──────────────────────────────────────────────────────────────┘
```

## Execution Instructions

### Stage 1 — Eight-Way Parallel Validation

Launch ALL EIGHT agents **simultaneously**:

1. **pipeline-tester** — Pipeline health:
   - All 12 steps completing without errors
   - Articles have bias scores, clusters, categories
   - Rankings are deterministic and correctly ordered
   - Daily brief exists and is current

2. **bias-calibrator** — Bias accuracy:
   - `python pipeline/validation/runner.py --json`
   - Accuracy >= 96.9% (hard requirement)
   - No category below 90% accuracy
   - No regression from snapshot

3. **uat-tester** — Browser UAT:
   - Homepage loads with real data
   - Edition switching works (World/US/India)
   - Category filtering works
   - Deep Dive opens/closes correctly
   - BiasLens renders correctly
   - DailyBrief plays audio
   - All interactive elements respond

4. **responsive-specialist** — Layout validation:
   - Desktop 1024px+: newspaper grid, side panel
   - Mobile 375px: single column, bottom sheet
   - Tablet 768px: graceful transition
   - Light + dark mode both correct
   - No overflow, no text truncation

5. **perf-optimizer** — Performance:
   - `cd frontend && npm run build` succeeds
   - Bundle size reasonable
   - Lighthouse: Performance 90+, Accessibility 90+, Best Practices 90+

6. **void-ciso** — Security:
   - No secrets in repo
   - RLS policies correct
   - No known vulnerabilities in dependencies
   - OWASP Top 10 clean

7. **db-reviewer** — Data quality:
   - >90% articles have full_text
   - All bias axes populated
   - Clusters have summaries
   - Source coverage across all tiers

8. **feed-intelligence** — Content health:
   - RSS feeds returning current content
   - Deduplication working (no duplicate clusters)
   - Article freshness (<24h for latest)
   - All editions have content

### Stage 2 — Strategic Assessment

Launch **ceo-advisor** with ALL eight reports:
- Evaluate each domain: PASS / CONDITIONAL PASS / FAIL
- Assess competitive positioning vs AllSides/Ground News
- Consider: is the product differentiated enough to launch?
- Provide go/no-go recommendation with clear rationale
- If no-go: prioritized list of what must be fixed first

### Stage 2 Gate

- **GO** → Proceed to Stage 3
- **NO-GO** → Report blockers to CEO with priority order. Workflow ends here.

### Stage 3 — Deploy (Conditional, requires CEO confirmation)

Only with explicit CEO approval:
- Commit all changes
- Push to `claude/*` branch (auto-merge enabled)
- `gh run watch` to confirm deploy succeeds
- Verify GitHub Pages is serving the new build

### Final Report — Launch Readiness Scorecard

```
## Launch Readiness Report
- **Recommendation**: GO / NO-GO
- **Date**: [today]

### Domain Scores
| Domain | Status | Notes |
|--------|--------|-------|
| Pipeline | PASS/FAIL | [detail] |
| Bias Accuracy | [X]% | [vs 96.9% target] |
| Browser UAT | PASS/FAIL | [issues count] |
| Responsive | PASS/FAIL | [breakpoints tested] |
| Performance | Lighthouse [X] | [vs 90 target] |
| Security | [X]/100 | [P0 count] |
| Data Quality | PASS/FAIL | [completeness %] |
| Content Health | PASS/FAIL | [freshness] |

### Go/No-Go Rationale
[ceo-advisor assessment]

### If No-Go — Fix Priority
1. [most critical blocker]
2. [second blocker]
3. [third blocker]
```
