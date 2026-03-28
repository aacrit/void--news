---
name: daily-ops
description: "Daily Operations Check: feed-intelligence + db-reviewer + pipeline-tester in parallel. Quick health pulse — run every morning or after pipeline runs."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /daily-ops — Daily Operations Check

You are the workflow orchestrator for the **Daily Operations Check** — a fast, lightweight health pulse for void --news. Run this every morning, after pipeline runs, or whenever you want a quick status snapshot. Designed to complete in under 5 minutes.

## Objective

Quickly verify: feeds are delivering, data is fresh, pipeline ran successfully, and content is flowing to all editions. Surface problems early before they compound.

## Workflow Stages

```
┌──────────────────────────────────────────────────────────┐
│  STAGE 1 — THREE-WAY PARALLEL HEALTH CHECK               │
│                                                           │
│  feed-intelligence ── RSS health + article freshness      │
│  db-reviewer ──────── data completeness + freshness       │
│  pipeline-tester ──── latest pipeline run status          │
├──────────────────────────────────────────────────────────┤
│  STAGE 2 — TRIAGE (orchestrator)                         │
│  Synthesize → traffic-light dashboard                     │
│  GREEN = all clear | YELLOW = degraded | RED = broken    │
├──────────────────────────────────────────────────────────┤
│  STAGE 3 — AUTO-FIX (conditional, for known patterns)    │
│  bug-fixer: only for previously-seen failure patterns     │
└──────────────────────────────────────────────────────────┘
```

## Execution Instructions

### Stage 1 — Three-Way Health Check (Parallel)

Launch ALL THREE agents **simultaneously**:

1. **feed-intelligence** — Content pipeline health:
   - How many sources returned articles in the last pipeline run?
   - Any feeds timing out or returning 0 articles?
   - Deduplication stats (how many dupes caught?)
   - Article freshness: what % of articles are <24h old?
   - Edition coverage: World, US, India all have content?
   - Cluster summary coverage: 3+ source clusters have Gemini summaries?

2. **db-reviewer** — Data layer health:
   - Latest `pipeline_runs` record: status, started_at, finished_at
   - Article count trend (today vs yesterday vs 7-day avg)
   - NULL audit: articles missing bias_scores, categories, or cluster assignment
   - `daily_briefs` freshness: latest brief age per edition
   - Orphaned records check (cluster_articles pointing to deleted clusters)
   - Source coverage: any tier with <80% of sources returning articles?

3. **pipeline-tester** — Pipeline output validation (quick mode):
   - Latest run completed without errors
   - Top 10 per section have 3+ sources (lead gate)
   - Bias score distributions not stuck at defaults
   - Rankings are non-zero and correctly ordered
   - No duplicate clusters (step 8b dedup working)

### Stage 2 — Triage Dashboard

Synthesize the three reports into a traffic-light dashboard:

```
## Daily Ops Dashboard — [date]

| System | Status | Detail |
|--------|--------|--------|
| RSS Feeds | [GREEN/YELLOW/RED] | [X]/370 sources active |
| Data Freshness | [GREEN/YELLOW/RED] | Latest articles: [age] |
| Pipeline Run | [GREEN/YELLOW/RED] | Last run: [time], duration: [min] |
| Bias Scores | [GREEN/YELLOW/RED] | [X]% articles scored |
| Clustering | [GREEN/YELLOW/RED] | [X] clusters, [X] orphans |
| Daily Brief | [GREEN/YELLOW/RED] | Latest: [age] per edition |
| Edition Coverage | [GREEN/YELLOW/RED] | W:[X] US:[X] IN:[X] clusters |

### Action Items
[only if YELLOW or RED — specific, actionable items]
```

**Status thresholds**:
- **GREEN**: >90% sources active, articles <6h old, pipeline ran <6h ago, >95% scored
- **YELLOW**: 70-90% sources, articles 6-24h old, pipeline 6-12h ago, 80-95% scored
- **RED**: <70% sources, articles >24h old, pipeline >12h ago or failed, <80% scored

### Stage 3 — Auto-Fix (Conditional)

Only if RED status on known patterns:
- **Pipeline stuck**: call `cleanup_stuck_pipeline_runs()` RPC
- **Stale clusters**: call `cleanup_stale_clusters()` RPC
- **Feed failures**: log the failing sources for source-curator review

Do NOT auto-fix unknown issues — flag them for CEO attention.

## Quick Mode

If the user passes `--quick` or wants fastest possible check, skip db-reviewer and only run feed-intelligence + pipeline-tester in parallel. Report in 2 minutes.
