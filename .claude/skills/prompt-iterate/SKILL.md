---
name: prompt-iterate
description: "Gemini Prompt Iteration Cycle: baseline dry-run, diagnose quality failures, fix prompt, re-run, compare metrics. For iteratively improving brief/opinion/audio prompts."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /prompt-iterate — Gemini Prompt Iteration Cycle

You are the workflow orchestrator for iteratively improving Gemini prompts in the daily brief pipeline. You diagnose quality gate failures, implement targeted prompt fixes, and validate improvements against deterministic test data.

## Objective

When daily brief output fails quality gates (prohibited terms, flat pacing, monologue detection, missing sign-offs), systematically identify the root cause in the prompt, fix it, and verify the fix produces better output.

## Prerequisites

Before running this workflow, ensure test fixtures exist:

```bash
python pipeline/refresh_brief.py --snapshot-fixtures --editions world,us,india
```

This saves current DB clusters to `pipeline/briefing/test_clusters.json` for deterministic A/B comparison.

## Workflow Stages

```
┌─────────────────────────────────────────────────────────┐
│  STAGE 1 — BASELINE (read-only)                         │
│  Run dry-run with fixtures, capture quality report       │
├─────────────────────────────────────────────────────────┤
│  STAGE 2 — DIAGNOSE (read-only)                         │
│  audio-engineer: parse quality report, map failures      │
│  to prompt sections, propose fixes                       │
├─────────────────────────────────────────────────────────┤
│  STAGE 3 — FIX (write)                                  │
│  audio-engineer: implement highest-priority prompt fix   │
├─────────────────────────────────────────────────────────┤
│  STAGE 4 — RE-RUN (read-only)                           │
│  Run dry-run again, capture new quality report           │
├─────────────────────────────────────────────────────────┤
│  STAGE 5 — COMPARE                                      │
│  Diff baseline vs. new metrics. Improved → commit.       │
│  Regressed → revert. Max 3 iterations.                   │
└─────────────────────────────────────────────────────────┘
```

## Stage Details

### STAGE 1 — BASELINE

Run the brief generator in dry-run + fixtures mode:

```bash
python pipeline/refresh_brief.py --editions world --fixtures --dry-run --no-audio --output /tmp/prompt-baseline.json
```

Read `/tmp/prompt-baseline.json` and extract the `quality_report` for each edition. Summarize:
- **Failures** (hard gates): prohibited terms found
- **Warnings** (soft gates): pacing, monologue, word counts, sign-off, filler
- **Metrics**: pacing_short_pct, pacing_long_pct, rhythm_markers, monologue_max, script_words

### STAGE 2 — DIAGNOSE

Spawn `audio-engineer` with this prompt:

> Read the quality report below and map each failure/warning to the specific prompt section in `pipeline/briefing/daily_brief_generator.py` that governs it. For each, propose a concrete, minimal prompt modification. One change per issue. Do NOT implement yet — just propose.
>
> Quality failures to address (in priority order):
> 1. Prohibited terms → KILL SCAFFOLDING or ANTI-SLOP section
> 2. Pacing issues → PACING or RHYTHM sections
> 3. Monologue detection → STRUCTURE section
> 4. Word count issues → word count targets in prompt
> 5. Missing sign-off → CLOSE instruction
> 6. Banned filler → BANNED section
>
> [Paste quality_report JSON here]

Review the audio-engineer's proposals. Select the top 1-2 fixes to implement.

### STAGE 3 — FIX

Spawn `audio-engineer` to implement the selected fix(es). Rules:
- One prompt section modified per iteration
- Document the exact before/after change
- No changes outside `pipeline/briefing/daily_brief_generator.py` (or `claude_brief_generator.py` if the fix applies to both)

### STAGE 4 — RE-RUN

Run the same dry-run command as Stage 1, but output to a different file:

```bash
python pipeline/refresh_brief.py --editions world --fixtures --dry-run --no-audio --output /tmp/prompt-after.json
```

### STAGE 5 — COMPARE

Read both JSON files and compare metrics:

| Metric | Baseline | After | Delta | Pass? |
|--------|----------|-------|-------|-------|
| prohibited_terms_found | [...] | [...] | | fewer = pass |
| pacing_short_pct | N% | N% | | higher = pass (want >=15%) |
| pacing_long_pct | N% | N% | | higher = pass (want >=10%) |
| rhythm_markers | N | N | | higher = pass (want >=5) |
| monologue_max | N | N | | lower = pass (want <=5) |
| script_words | N | N | | 600-1200 = pass |
| sign_off_present | T/F | T/F | | true = pass |
| filler_found | [...] | [...] | | fewer = pass |

**Decision:**
- All metrics improved or stable → **commit** the prompt change, move to next issue
- Any metric regressed significantly → **revert** the change, try a different approach
- Mixed results → CEO decides

### GATE: Max 3 iterations per session

Each iteration costs 2 Gemini Flash calls (TL;DR + opinion). At 3 iterations that's 6 calls. Combined with the 2-call baseline, total is 8 calls per prompt-iterate session. Well within the 1500 RPD free tier.

## Production Validation

After all iterations pass against fixtures, run one final live validation:

```bash
python pipeline/refresh_brief.py --editions world --dry-run --output /tmp/prompt-live.json
```

This uses real DB clusters (not fixtures) to confirm the prompt improvements hold against real-world data. If it passes, the changes are ready for the next pipeline run.

## Prompt Section Map

Quick reference for where each quality gate maps to in `daily_brief_generator.py`:

| Quality Gate | Prompt Section | Variable |
|-------------|---------------|----------|
| Prohibited terms | KILL SCAFFOLDING + ANTI-SLOP | `_SYSTEM_INSTRUCTION`, `_USER_PROMPT_TEMPLATE` |
| Pacing (sentence rhythm) | PACING — Write for the ear | `_USER_PROMPT_TEMPLATE` |
| Rhythm markers | PACING (ellipses, dashes, pauses) | `_USER_PROMPT_TEMPLATE` |
| Monologue detection | STRUCTURE — Headlines > 3 Stories > Close | `_USER_PROMPT_TEMPLATE` |
| Script word count | Audio script word targets | `_USER_PROMPT_TEMPLATE` |
| Sign-off | CLOSE instruction | `_USER_PROMPT_TEMPLATE` |
| Banned filler | BANNED — zero tolerance | `_USER_PROMPT_TEMPLATE` |
| Opinion prohibited terms | KILL SCAFFOLDING | `_OPINION_SYSTEM_INSTRUCTION` |
| Opinion word count | Standards (300-500 words) | `_OPINION_SYSTEM_INSTRUCTION` |

## Cost Budget

| Item | Calls | Notes |
|------|-------|-------|
| Baseline (1 edition) | 2 | TL;DR + opinion |
| Per iteration (1 edition) | 2 | TL;DR + opinion |
| Max iterations | 3 | Configurable |
| Live validation | 2 | Optional final check |
| **Total max** | **10** | 0.7% of 1500 RPD |

## Report Format

After all iterations, summarize:

```
PROMPT ITERATION REPORT — void --news
Date: [today]
Editions tested: [editions]
Iterations: [N]

BASELINE METRICS:
  [metric table from Stage 1]

CHANGES MADE:
  1. [prompt section]: [before] → [after] — [rationale]

FINAL METRICS:
  [metric table from last Stage 4]

DELTA:
  [which metrics improved, which held, which regressed]

PRODUCTION VALIDATED: [yes/no]
COMMITTED: [commit hash or "pending CEO approval"]
```
