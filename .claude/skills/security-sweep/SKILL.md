---
name: security-sweep
description: "Security + Performance Sweep: void-ciso audits security + perf-optimizer benchmarks speed in parallel. Fast hardening pass."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /security-sweep — Security + Performance Sweep

You are the workflow orchestrator for the **Security + Performance Sweep** — a focused hardening pass that runs security audit and performance benchmarking in parallel. Faster than `/full-audit`, targeted at the two dimensions most likely to block a deploy.

## Objective

Identify and fix security vulnerabilities and performance bottlenecks. These are the two dimensions that can cause real-world damage if missed.

## Workflow Stages

```
┌──────────────────────────────────────────────────────────┐
│  STAGE 1 — DUAL AUDIT (parallel)                         │
│  void-ciso: security audit (OWASP, secrets, RLS)         │
│  perf-optimizer: performance audit (runtime, Lighthouse)  │
├──────────────────────────────────────────────────────────┤
│  STAGE 2 — FIX CRITICAL (parallel, write)                │
│  bug-fixer: security P0/P1 fixes                          │
│  perf-optimizer: implement performance fixes              │
├──────────────────────────────────────────────────────────┤
│  STAGE 3 — VERIFY (parallel, read-only)                  │
│  void-ciso: re-scan for fixed vulnerabilities             │
│  pipeline-tester: confirm no regressions from fixes       │
└──────────────────────────────────────────────────────────┘
```

## Execution Instructions

### Stage 1 — Dual Audit (Parallel)

Launch BOTH agents **simultaneously**:

1. **void-ciso** — Security audit:

   **Secrets scanning**:
   - Grep repo for API keys, tokens, passwords, connection strings
   - Check `.env` is in `.gitignore`
   - Check no Supabase service_role key in client code
   - Check GitHub secrets are used in workflows (not hardcoded)

   **Supabase RLS**:
   - All tables have RLS enabled
   - Public read-only on: articles, bias_scores, story_clusters, cluster_articles, categories, sources, daily_briefs
   - No public write access from client
   - `pipeline_runs` not exposed to public

   **OWASP Top 10**:
   - Injection (SQL via Supabase client — should use parameterized queries)
   - XSS (Next.js auto-escapes, but check dangerouslySetInnerHTML usage)
   - CORS (Supabase CORS config)
   - CSRF (static site, but check any mutations)
   - Dependency vulnerabilities

   **Score**: 0-100

2. **perf-optimizer** — Performance audit:

   **Pipeline**:
   - Total runtime (target: 25-35 min incremental)
   - Step-by-step timing breakdown
   - Bottleneck identification (typically: web scraping, Gemini calls, bias analysis)
   - Worker count optimization (currently 8 for bias, 15 for scraping)

   **Frontend**:
   - `npm run build` time and success
   - Bundle size breakdown
   - Static export page count and size
   - CSS load order validation

   **Supabase**:
   - Query performance (any queries >1s?)
   - Index usage (GIN on sections[], btree on standard columns)
   - Connection pooling health

   **Score**: 0-100

### Stage 2 — Fix Critical (Parallel, conditional)

If either audit found P0/P1 issues:

- **bug-fixer**: security fixes (secrets removal, RLS fixes, dependency updates)
- **perf-optimizer**: performance fixes (query optimization, worker tuning, caching)

If no P0/P1 → skip to report.

### Stage 3 — Verify (Parallel)

Re-run verification:
- **void-ciso**: confirm security fixes resolved vulnerabilities
- **pipeline-tester**: confirm fixes didn't break pipeline output

### Final Report

```
## Security + Performance Sweep
- **Date**: [today]

### Security
- **Score**: [X]/100 (previous: [X]/100)
- **Secrets**: CLEAN / [count] found
- **RLS**: PASS / [count] issues
- **OWASP**: [count]/10 clean
- **Dependencies**: [count] vulnerabilities ([critical]/[high]/[medium])

### Performance
- **Score**: [X]/100
- **Pipeline runtime**: [X] min (target: 25-35)
- **Frontend build**: [X]s
- **Bundle size**: [X]KB
- **Slowest query**: [X]ms

### Fixes Applied
[list or "No critical fixes needed"]

### Recommendations
[top 3 hardening actions]
```

## Reference: Previous Audit

Last void-ciso audit (2026-03-19): Score 72/100
- 3 critical findings: hardcoded Supabase ref, anon key fallback, migrate input validation
- Fix path to 88/100 documented
