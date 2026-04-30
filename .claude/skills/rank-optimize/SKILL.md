---
name: rank-optimize
description: "Ranking Engine Optimization Cycle: analytics-expert benchmarks current ranking quality, nlp-engineer tunes weights/signals, pipeline-tester validates output, db-reviewer audits homepage ordering. For tuning the importance ranker."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /rank-optimize — Ranking Engine Optimization Cycle

You are the workflow orchestrator for the **Ranking Engine Optimization Cycle**. This workflow benchmarks, tunes, and validates the importance ranker (`pipeline/ranker/importance_ranker.py`) to ensure the homepage feed ordering matches editorial quality expectations.

## Objective

Ensure the v5.1 importance ranker (10 signals, bias-blind) produces homepage ordering that surfaces the most consequential, well-reported stories first — across both World News and US News sections.

## Workflow Stages

```
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 1 — BENCHMARK (read-only, parallel)                      │
│  analytics-expert: score distribution analysis + edge cases      │
│  db-reviewer: homepage ordering audit (top 20 per section)       │
├─────────────────────────────────────────────────────────────────┤
│  GATE: If Stage 1 shows no issues → DONE (skip 2-3)             │
├─────────────────────────────────────────────────────────────────┤
│  STAGE 2 — TUNE (write, sequential)                             │
│  nlp-engineer: adjust weights, signals, gates, thresholds        │
├─────────────────────────────────────────────────────────────────┤
│  STAGE 3 — VALIDATE (read-only, parallel)                       │
│  pipeline-tester: full pipeline output validation                │
│  analytics-expert: re-benchmark to confirm improvement           │
└─────────────────────────────────────────────────────────────────┘
```

## Execution Instructions

### Stage 1 — Benchmark (Parallel)

Launch these two agents **in parallel** using the Agent tool:

1. **analytics-expert** — Ranking quality analysis:
   - Query Supabase for top 30 clusters per section (world/us) ordered by `headline_rank DESC`
   - Analyze score distributions: mean, median, p10, p90, max, min
   - Identify edge cases: high-source clusters ranked low, low-source clusters ranked high
   - Check signal contribution balance: is any single signal dominating?
   - Compare coverage breadth vs. maturity vs. authority signal contributions
   - Flag any "obviously wrong" orderings (e.g., celebrity gossip above geopolitical crisis)
   - Check soft-news gate effectiveness (sports/entertainment properly deprioritized)

2. **db-reviewer** — Homepage ordering audit:
   - Query the top 20 stories per section as they would appear on the homepage
   - For each: report headline, source_count, headline_rank score, category, age
   - Flag stories where source_count >= 5 but rank is below position 10
   - Flag stories where source_count <= 2 but rank is in top 5
   - Check for stale stories (>24h old) in top 10
   - Verify lead story (position 1) is defensible as the most important

Collect both reports. Create a task list tracking each finding.

### Stage 1 Gate

Analyze the combined results:
- **ALL PASS** (ordering looks editorially sound, no edge cases) → Report success. Workflow complete.
- **ANY ISSUES** → Proceed to Stage 2. Compile findings into a tuning brief.

### Stage 2 — Tune (Sequential)

Launch **nlp-engineer** with the compiled findings:
- Adjust signal weights in `importance_ranker.py` based on findings
- Tune thresholds (soft-news multiplier, low-rigor gate, authority floor)
- Add/modify consequentiality keywords or institutional authority patterns if needed
- Add/modify geopolitical weights if edge cases involve geographic ranking issues
- Preserve bias-blind design principle: NEVER factor political lean into ranking
- Run `python -c "from pipeline.ranker.importance_ranker import rank_importance; print('OK')"` to verify no import errors
- Each change must include a comment explaining the rationale

### Stage 3 — Validate (Parallel)

Re-run both agents from Stage 1 **in parallel**:

1. **pipeline-tester** — Full pipeline output validation:
   - Ranking output (top 10 per section have 3+ sources)
   - No regressions in other pipeline steps
   - Validation suite still passes

2. **analytics-expert** — Re-benchmark:
   - Compare new distributions vs. Stage 1 baseline
   - Confirm edge cases from Stage 1 are resolved
   - Verify no new edge cases introduced

### Final Report

Deliver a structured report to the CEO:

```
## Ranking Optimization Report
- **Result**: PASS / FAIL / IMPROVED
- **Stage 1 findings**: [count] issues in [categories]
- **Signal weight changes**: [before → after for each changed weight]
- **Threshold changes**: [list of threshold modifications]
- **Stage 3 confirmation**: [count] issues resolved, [count] remaining
- **Top 5 per section (before vs after)**: side-by-side comparison
- **Duration**: [time]
```

## Key Files

| File | Role |
|------|------|
| `pipeline/ranker/importance_ranker.py` | v5.1 ranker (10 signals, bias-blind) |
| `pipeline/main.py` | Pipeline orchestrator (step 7 = categorize + rank) |
| `pipeline/validation/runner.py` | Validation suite |
| `data/sources.json` | Source metadata (tiers, lean baselines) |

## Signal Reference (v5.1)

| Signal | Weight | Description |
|--------|--------|-------------|
| Coverage breadth | 20% | Tier-weighted diminishing returns |
| Story maturity | 16% | recency * log2(1 + source_count) |
| Tier diversity | 13% | Composition-aware, us_major presence rewarded |
| Consequentiality | 10% | Outcome/action verbs + high-authority floor |
| Institutional authority | 8% | Heads of state, courts, central banks, UN |
| Factual density | 8% | Average factual rigor; <30 gets 0.88x gate |
| Divergence score | 7% | Framing-weighted source disagreement |
| Perspective diversity | 6% | Editorial viewpoint spread (bias-blind) |
| Geographic impact | 6% | Geopolitically weighted NER GPEs |
| Confidence multiplier | - | 0.65 + 0.35 * conf (applied to final score) |
| Soft-news gate | - | sports/entertainment/culture get 0.78x |

## Constraints

- $0 cost — no external API calls
- BIAS-BLIND ranking — never factor political lean into story selection
- Read-only agents (analytics-expert, db-reviewer, pipeline-tester) must NEVER modify files
- nlp-engineer modifies ONLY `pipeline/ranker/importance_ranker.py`
- Never touch `data/sources.json` or `supabase/migrations/`
- Weight changes must sum to 100% (or explicitly document if not)
