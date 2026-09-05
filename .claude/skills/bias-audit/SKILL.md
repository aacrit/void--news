---
name: bias-audit
description: "Full Bias Audit Cycle: analytics-expert benchmarks + bias-auditor validates ground truth + nlp-engineer fixes + pipeline-tester confirms. The gold standard for bias engine changes."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /bias-audit — Full Bias Audit Cycle

You are the workflow orchestrator for the **Bias Audit Cycle** — the most rigorous quality process in void --news. This cycle ensures the 6-axis bias engine produces scores that align with expert consensus and real-world outlet profiles (AllSides, NewsGuard, Ad Fontes Media).

## Objective

Validate bias scoring accuracy against ground truth, identify systematic errors, fix them, and confirm no regressions. Target: maintain or exceed 100% validation accuracy.

## Workflow Stages

```
┌──────────────────────────────────────────────────────────┐
│  STAGE 1 — BENCHMARK + VALIDATE (parallel)               │
│  analytics-expert: score distributions, axis calibration  │
│  bias-auditor: ground-truth comparison, outlet profiles   │
├──────────────────────────────────────────────────────────┤
│  GATE: If both pass clean → DONE (skip 2-3)              │
├──────────────────────────────────────────────────────────┤
│  STAGE 2 — ENGINEER FIXES (sequential)                   │
│  nlp-engineer: implement bias engine corrections          │
├──────────────────────────────────────────────────────────┤
│  STAGE 3 — FINAL VALIDATION (parallel)                   │
│  pipeline-tester: full pipeline validation                │
│  bias-calibrator: regression suite + snapshot comparison  │
└──────────────────────────────────────────────────────────┘
```

## Execution Instructions

### Stage 1 — Benchmark + Validate (Parallel)

Launch these two agents **in parallel**:

1. **analytics-expert** — Quantitative benchmarking:
   - Score distribution analysis per axis (mean, median, std, skew)
   - Per-tier distribution comparison (us_major vs international vs independent)
   - Axis correlation matrix (are axes independent?)
   - Competitive gap audit: compare lean scores vs AllSides ratings
   - Flag any axis with >15% of scores at defaults (50)
   - Flag bimodal distributions (sign of binary scoring)

2. **bias-auditor** — Qualitative ground-truth validation:
   - Run `python pipeline/validation/runner.py --verbose`
   - Cross-reference 38 ground-truth fixtures against expected ranges
   - AllSides alignment check (source_profiles.py)
   - Per-category accuracy (wire, opinion, investigative, partisan_left/right, state_media, breaking, analysis)
   - Signal decomposition on any failures (`signal_tracker.py`)
   - Check: does Fox score right-of-center? Does AP score near-center? Does RT flag as state media?

Collect both reports into a unified audit document.

### Stage 1 Gate

- **BOTH PASS** → Report to CEO. Workflow complete.
- **ANY FINDING** → Categorize issues:
  - `axis_miscalibration` — systematic over/under-scoring on an axis
  - `outlet_misalignment` — specific outlet scores don't match known profile
  - `signal_dead` — a scoring signal contributes zero variance
  - `distribution_unhealthy` — axis scores bunched or bimodal

### Stage 2 — Engineer Fixes (Sequential)

Launch **nlp-engineer** with the categorized findings:
- For `axis_miscalibration`: adjust weights, thresholds, or normalization in the specific analyzer
- For `outlet_misalignment`: check source baseline, keyword lexicons, entity lists
- For `signal_dead`: investigate if signal logic is reached; fix or document as intentional
- For `distribution_unhealthy`: adjust scoring curves, caps, or floors
- After each fix: `python pipeline/validation/runner.py --quick` to verify
- Update `pipeline/validation/snapshot.json` only if accuracy improves

### Stage 3 — Final Validation (Parallel)

Launch **pipeline-tester** and **bias-calibrator** in parallel:
- pipeline-tester: full pipeline output validation
- bias-calibrator: `python pipeline/validation/runner.py --verbose --json`
- Confirm: accuracy >= 100%, no new regressions, all original findings resolved

### Final Report

```
## Bias Audit Report
- **Result**: PASS / FAIL
- **Accuracy**: [X]% (baseline: 100%)
- **Axes audited**: 6
- **Ground-truth fixtures**: 26 ([passed]/26 passed)
- **AllSides alignment**: [X]% concordance
- **Issues found**: [count] ([categories])
- **Fixes applied**: [list with file:line]
- **Regression check**: CLEAN / [count] new issues
```

## Key Files

| File | Role |
|------|------|
| `pipeline/analyzers/political_lean.py` | Axis 1: Political Lean |
| `pipeline/analyzers/sensationalism.py` | Axis 2: Sensationalism |
| `pipeline/analyzers/opinion_detector.py` | Axis 3: Opinion vs Reporting |
| `pipeline/analyzers/factual_rigor.py` | Axis 4: Factual Rigor |
| `pipeline/analyzers/framing.py` | Axis 5: Framing Analysis |
| `pipeline/analyzers/topic_outlet_tracker.py` | Axis 6: Per-Topic Tracking |
| `pipeline/validation/runner.py` | Validation runner |
| `pipeline/validation/fixtures.py` | 38 ground-truth articles |
| `pipeline/validation/signal_tracker.py` | Per-signal decomposition |
| `pipeline/validation/source_profiles.py` | AllSides cross-reference |

## Benchmarks (Real-World)

- **AllSides**: 1400+ outlets rated, 5-point scale → our 7-point lean should correlate
- **Ad Fontes Media**: reliability + bias chart → our factual_rigor + lean should align
- **NewsGuard**: 0-100 trust score → our factual_rigor should correlate for shared outlets
- **Ground News**: ownership + factuality → cross-reference for outlet profiles
