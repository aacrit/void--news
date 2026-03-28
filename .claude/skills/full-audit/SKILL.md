---
name: full-audit
description: "Full System Audit: security + database + performance + docs + bias in parallel, then unified report. The comprehensive health check."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /full-audit — Full System Audit

You are the workflow orchestrator for the **Full System Audit** — the most comprehensive health check in void --news. Runs 5 specialist agents in parallel across every system dimension, then synthesizes a unified health report for the CEO.

## Objective

Produce a single, actionable system health report covering security, data quality, performance, documentation freshness, and bias engine accuracy. This is the "annual physical" for the platform.

## Workflow Stages

```
┌──────────────────────────────────────────────────────────────┐
│  STAGE 1 — FIVE-WAY PARALLEL AUDIT (all read-only)           │
│                                                               │
│  void-ciso ──────── security (OWASP, secrets, RLS, CORS)     │
│  db-reviewer ─────── data quality (completeness, integrity)   │
│  perf-optimizer ──── performance (pipeline runtime, frontend) │
│  update-docs ─────── documentation freshness                  │
│  bias-calibrator ─── bias engine regression                   │
├──────────────────────────────────────────────────────────────┤
│  STAGE 2 — SYNTHESIS + TRIAGE (orchestrator)                 │
│  Combine 5 reports → unified health score + prioritized fixes │
├──────────────────────────────────────────────────────────────┤
│  STAGE 3 — CRITICAL FIXES (conditional, parallel)            │
│  bug-fixer: any P0/P1 issues from audit                       │
│  frontend-fixer: any P0/P1 UI issues                          │
└──────────────────────────────────────────────────────────────┘
```

## Execution Instructions

### Stage 1 — Five-Way Parallel Audit

Launch ALL FIVE agents **simultaneously** using the Agent tool:

1. **void-ciso** — Security audit:
   - Secrets scanning (no hardcoded keys, tokens, passwords in repo)
   - Supabase RLS policy review (public read only, no write from client)
   - CORS configuration
   - Dependency vulnerabilities (`npm audit`, `pip audit`)
   - OWASP Top 10 checklist against codebase
   - Injection prevention (SQL, XSS, command injection)
   - Score: 0-100 security rating

2. **db-reviewer** — Data quality audit:
   - Article completeness (% with full_text, bias_scores, categories)
   - Bias score distributions (no axis stuck at defaults)
   - Cluster integrity (no orphaned junction records)
   - Source coverage (all 370 sources active? any returning 0 articles?)
   - NULL audit on critical fields
   - `daily_briefs` freshness
   - Score: 0-100 data quality rating

3. **perf-optimizer** — Performance audit:
   - Pipeline runtime analysis (target: 25-35 min incremental)
   - Frontend build time + bundle size
   - Supabase query performance (any slow queries?)
   - Static export validation
   - Score: 0-100 performance rating

4. **update-docs** — Documentation audit:
   - CLAUDE.md accuracy vs current codebase
   - docs/*.md freshness
   - Agent definitions match actual capabilities
   - Source counts match data/sources.json
   - Score: 0-100 docs freshness rating

5. **bias-calibrator** — Bias engine audit:
   - `python pipeline/validation/runner.py --verbose --json`
   - Regression check against snapshot
   - Per-category accuracy
   - Dead signal detection
   - Score: accuracy % (target: 96.9%+)

### Stage 2 — Synthesis + Triage

After all 5 agents report, synthesize:

1. **System Health Score**: weighted average
   - Security: 25% weight
   - Data Quality: 25% weight
   - Performance: 20% weight
   - Bias Accuracy: 20% weight
   - Documentation: 10% weight

2. **Issue Triage**: categorize all findings by priority
   - **P0 (Critical)**: Security vulnerabilities, data corruption, pipeline crashes
   - **P1 (High)**: Bias regressions, performance degradation >50%, stale data
   - **P2 (Medium)**: Documentation drift, minor performance issues, coverage gaps
   - **P3 (Low)**: Cosmetic issues, nice-to-have improvements

### Stage 3 — Critical Fixes (Conditional)

If P0 or P1 issues found, launch fixers **in parallel**:
- **bug-fixer**: pipeline/backend P0/P1 issues
- **frontend-fixer**: UI P0/P1 issues

If no P0/P1 → skip Stage 3.

### Final Report

```
## Full System Audit Report
- **Overall Health**: [X]/100
- **Date**: [today]

### Scores
| Domain | Score | Status |
|--------|-------|--------|
| Security | [X]/100 | [emoji] |
| Data Quality | [X]/100 | [emoji] |
| Performance | [X]/100 | [emoji] |
| Bias Accuracy | [X]% | [emoji] |
| Documentation | [X]/100 | [emoji] |

### Issues by Priority
- **P0 (Critical)**: [count] — [list]
- **P1 (High)**: [count] — [list]
- **P2 (Medium)**: [count] — [list]
- **P3 (Low)**: [count] — [list]

### Fixes Applied (Stage 3)
[list or "No critical fixes needed"]

### Recommendations
[top 3 actions to improve health score]
```
