---
name: pipeline-qa
description: "Pipeline Quality Cycle: pipeline-tester validates, bug-fixer remediates, pipeline-tester re-validates. Use after any pipeline code change."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /pipeline-qa — Pipeline Quality Cycle

You are the workflow orchestrator for the **Pipeline Quality Cycle**. This is the most frequently run workflow in void --news — it validates pipeline output, fixes failures, and confirms the fix.

## Objective

Ensure the 12-step pipeline (CLAUDE.md § Pipeline Flow) produces correct, complete, and consistent output after any code change to `pipeline/`.

## Workflow Stages

```
┌─────────────────────────────────────────────────────┐
│  STAGE 1 — VALIDATE (read-only)                     │
│  pipeline-tester: full pipeline output validation    │
│  + bias-calibrator: validation suite (parallel)      │
├─────────────────────────────────────────────────────┤
│  GATE: If Stage 1 passes clean → DONE (skip 2-3)    │
├─────────────────────────────────────────────────────┤
│  STAGE 2 — FIX (write)                              │
│  bug-fixer: root-cause group + surgical fixes        │
├─────────────────────────────────────────────────────┤
│  STAGE 3 — RE-VALIDATE (read-only)                  │
│  pipeline-tester: confirm fixes resolved failures    │
└─────────────────────────────────────────────────────┘
```

## Execution Instructions

### Stage 1 — Validate (Parallel)

Launch these two agents **in parallel** using the Agent tool:

1. **pipeline-tester** — Run full validation:
   - Article parsing quality (>90% have full_text)
   - Clustering quality (no orphans with 3+ source matches)
   - Bias score distributions (no axis stuck at defaults)
   - Ranking output (top 10 per section have 3+ sources)
   - Daily brief existence and quality
   - Gemini summarization (3+ source clusters have summaries)

2. **bias-calibrator** — Run validation suite:
   - `python pipeline/validation/runner.py --verbose`
   - Check for regressions against snapshot
   - Report any accuracy drops

Collect both reports. Create a task list tracking each finding.

### Stage 1 Gate

Analyze the combined results:
- **ALL PASS** → Report success to CEO. Workflow complete. Skip Stages 2-3.
- **ANY FAILURE** → Proceed to Stage 2. Compile a unified failure report with: failure code, affected files, expected vs actual values.

### Stage 2 — Fix (Sequential)

Launch **bug-fixer** with the compiled failure report:
- Group failures by root cause
- Implement minimal, surgical fixes
- No refactoring, no feature additions
- Each fix must be reversible
- Run `python pipeline/validation/runner.py --quick` after each fix to verify

### Stage 3 — Re-Validate (Parallel, same as Stage 1)

Re-run both **pipeline-tester** and **bias-calibrator** in parallel to confirm:
- All original failures are resolved
- No new regressions introduced
- Validation suite accuracy >= baseline (96.9%)

### Final Report

Deliver a structured report to the CEO:

```
## Pipeline QA Report
- **Result**: PASS / FAIL
- **Stage 1 findings**: [count] issues in [domains]
- **Fixes applied**: [list of changes with file:line]
- **Stage 3 confirmation**: All [count] issues resolved, no regressions
- **Validation accuracy**: [X]% (baseline: 96.9%)
- **Duration**: [time]
```

## Key Files

| File | Role |
|------|------|
| `pipeline/main.py` | Orchestrator (12 steps) |
| `pipeline/analyzers/*.py` | 5 bias analyzers + gemini_reasoning + topic_tracker |
| `pipeline/clustering/story_cluster.py` | Two-phase clustering |
| `pipeline/ranker/importance_ranker.py` | v5.1 ranking |
| `pipeline/validation/runner.py` | Validation suite |
| `pipeline/validation/snapshot.json` | Regression baseline |

## Constraints

- $0 cost — no external API calls during testing
- Read-only agents (pipeline-tester, bias-calibrator) must NEVER modify files
- bug-fixer modifies only the files causing failures
- Never touch `data/sources.json` or `supabase/migrations/`
