---
name: bias-calibrate
description: "Bias Calibration Cycle: nlp-engineer tunes weights + bias-calibrator validates + bias-auditor confirms ground truth + pipeline-tester regression check. For precision tuning of scoring parameters."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /bias-calibrate — Bias Calibration Cycle

You are the workflow orchestrator for the **Bias Calibration Cycle** — precision tuning of the 6-axis bias engine. Unlike `/bias-audit` (which validates accuracy), this workflow actively adjusts scoring parameters: weights, thresholds, lexicons, and normalization curves.

## Objective

Tune bias engine parameters to improve scoring accuracy, reduce dead signals, and ensure each axis produces meaningful, well-distributed scores. This is surgery, not exploration.

## When to Use

- After adding new keywords/phrases to lexicons
- After adjusting analyzer weights or thresholds
- After adding new ground-truth fixtures
- When score distributions drift (detected by analytics-expert)
- Periodic calibration (monthly recommended)

## Workflow Stages

```
┌──────────────────────────────────────────────────────────┐
│  STAGE 1 — TUNE (write)                                  │
│  nlp-engineer: adjust weights, lexicons, thresholds       │
├──────────────────────────────────────────────────────────┤
│  STAGE 2 — QUANTITATIVE CHECK (parallel)                 │
│  bias-calibrator: validation suite + distribution health  │
│  analytics-expert: score distribution analysis            │
├──────────────────────────────────────────────────────────┤
│  GATE: If regressions detected → back to Stage 1         │
├──────────────────────────────────────────────────────────┤
│  STAGE 3 — QUALITATIVE CHECK (sequential)                │
│  bias-auditor: ground-truth spot checks on changed axes   │
├──────────────────────────────────────────────────────────┤
│  STAGE 4 — REGRESSION GATE (read-only)                   │
│  pipeline-tester: full pipeline validation                │
└──────────────────────────────────────────────────────────┘
```

## Execution Instructions

### Stage 1 — Tune

Launch **nlp-engineer** with the calibration task. If the user provided specific tuning goals, pass them through. Otherwise, nlp-engineer should:
- Run `python pipeline/validation/runner.py --verbose` to get current baseline
- Identify lowest-accuracy categories from fixtures
- Decompose signals on failing articles via `signal_tracker.py`
- Make targeted adjustments (one axis at a time, verify after each)
- Common tuning targets:
  - Keyword lexicon gaps (political_lean.py: LEFT_KEYWORDS, RIGHT_KEYWORDS)
  - Weight adjustments (opinion_detector.py: subjectivity weight, value_judgment weight)
  - Threshold tuning (sensationalism.py: partisan_attack cap, factual_rigor.py: LOW_CREDIBILITY baseline)
  - Normalization curves (framing.py: passive_voice cap, charged synonym intensity)

### Stage 2 — Quantitative Check (Parallel)

Launch **bias-calibrator** and **analytics-expert** in parallel:

1. **bias-calibrator**:
   - `python pipeline/validation/runner.py --verbose --json`
   - Compare against snapshot.json
   - Flag any accuracy drop > 0.5%
   - Flag any fixture that moved out of expected range

2. **analytics-expert**:
   - Score distribution health per axis
   - Dead signal detection (any signal contributing <1% variance)
   - Cross-axis correlation (should be <0.3 between independent axes)
   - Per-tier fairness check (no tier systematically over/under-scored)

### Stage 2 Gate

- **Accuracy improved, no regressions** → Proceed to Stage 3
- **Any regression** → Return to Stage 1 with specific regression details. Max 2 loops.

### Stage 3 — Qualitative Check (Sequential)

Launch **bias-auditor** to spot-check:
- Run changed-axis fixtures only: `python pipeline/validation/runner.py --category [affected_categories]`
- Verify outlet profile alignment (AllSides cross-reference)
- Confirm directional invariants hold (e.g., Fox > CNN on lean, AP near center)
- Sign off or flag remaining concerns

### Stage 4 — Regression Gate

Launch **pipeline-tester** for full pipeline validation:
- Confirms no collateral damage to clustering, ranking, or daily briefs
- Verifies bias scores flow correctly to Supabase schema
- Checks no analyzer throws exceptions on edge cases

### Final Report

```
## Bias Calibration Report
- **Result**: IMPROVED / NO CHANGE / REGRESSED
- **Accuracy**: [before]% → [after]%
- **Parameters changed**: [list with file:line and before/after values]
- **Axes affected**: [list]
- **Fixtures improved**: [count] | Regressed: [count]
- **Dead signals found**: [count]
- **Snapshot updated**: YES / NO
- **Loops required**: [1-3]
```

## Constraints

- Max 2 fix-validate loops before escalating to CEO
- Never change ground-truth fixtures to match scores — scores must match fixtures
- Update snapshot.json only when accuracy improves
- One axis at a time to isolate effects
