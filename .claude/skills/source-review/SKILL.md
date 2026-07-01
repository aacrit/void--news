---
name: source-review
description: "Source Curation Review: source-curator vets sources + feed-intelligence checks RSS health + pipeline-tester validates downstream impact. For adding/removing/auditing sources."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /source-review — Source Curation Review

You are the workflow orchestrator for the **Source Curation Review** — the quality gate for any changes to the 951-source curated list. Sources are the foundation of void --news; bad sources corrupt everything downstream.

## Objective

Vet source additions/removals, validate RSS feed health, check tier balance, verify lean spectrum coverage, and confirm no downstream pipeline breakage.

## When to Use

- Adding new sources to `data/sources.json`
- Removing or replacing sources
- Auditing existing source health (dead feeds, paywalls, redirect loops)
- Rebalancing tier or lean distribution
- Expanding to a new edition (adding country-specific sources)

## Workflow Stages

```
┌──────────────────────────────────────────────────────────┐
│  STAGE 1 — SOURCE AUDIT (sequential)                     │
│  source-curator: vet credibility, RSS, lean assignment    │
├──────────────────────────────────────────────────────────┤
│  STAGE 2 — HEALTH + BALANCE CHECK (parallel)             │
│  feed-intelligence: RSS feed health for changed sources   │
│  analytics-expert: lean spectrum balance analysis         │
├──────────────────────────────────────────────────────────┤
│  STAGE 3 — DOWNSTREAM VALIDATION (sequential)            │
│  pipeline-tester: confirm pipeline handles new sources    │
└──────────────────────────────────────────────────────────┘
```

## Execution Instructions

### Stage 1 — Source Audit

Launch **source-curator** with the review task:

**For new sources**:
- Verify editorial standards (original reporting, corrections policy, editorial board)
- Check RSS feed URL returns valid entries
- Assign tier: us_major (top-line US outlets), international (non-US), independent (nonprofit/niche)
- Assign 7-point lean: far-left, left, center-left, center, center-right, right, far-right
- Cross-reference with AllSides, Ad Fontes Media, NewsGuard ratings
- Assign country code for edition routing (US→us, IN→india, else→world)
- Verify slug uniqueness in `data/sources.json`
- Check for duplicate coverage (is this outlet already covered by a wire service?)

**For removals**:
- Document reason (dead feed, paywall, credibility concern, redundancy)
- Check if removal creates a lean gap (e.g., removing the only far-right independent)
- Check if removal affects edition balance

**For health audits**:
- Test all RSS URLs for 200 status
- Identify feeds returning 0 articles in last 30 days
- Identify feeds with broken encoding or malformed XML
- Identify paywalled sources where scraper gets 0 full_text

### Stage 2 — Health + Balance (Parallel)

Launch these two agents **in parallel**:

1. **feed-intelligence** — RSS health for affected sources:
   - Test each changed/new RSS URL
   - Check article parse quality (title, date, content present)
   - Verify deduplication handles new source correctly
   - Check article volume (too few = low value, too many = noise)

2. **analytics-expert** — Spectrum balance:
   - Current lean distribution: Left:Right ratio (target: near 1:1, currently 1.16:1)
   - Per-tier lean coverage (each tier should span the spectrum)
   - Per-edition source count (US=420, Europe=146, World=443, South Asia=72 targets)
   - Flag any lean zone with <5 sources
   - Flag any tier with >60% concentration in one lean zone

### Stage 3 — Downstream Validation

Launch **pipeline-tester** to confirm:
- Pipeline doesn't crash with new/modified sources
- New sources produce articles with valid bias scores
- Clustering still works correctly
- Rankings not disrupted
- Edition routing correct (new sources appear in right edition)

### Final Report

```
## Source Review Report
- **Result**: APPROVED / NEEDS REVISION / REJECTED
- **Sources reviewed**: [count] (added: [X], removed: [X], audited: [X])
- **Tier balance**: us_major=[X], international=[X], independent=[X] (total: [X])
- **Lean distribution**: L:R ratio [X]:1
  - far-left=[X], left=[X], center-left=[X], center=[X], center-right=[X], right=[X], far-right=[X]
- **Edition coverage**: US=[X], World=[X], India=[X]
- **Feed health**: [X]/[X] feeds returning valid articles
- **Pipeline impact**: CLEAN / [issues]
- **Recommendations**: [if any]
```

## Locked Constraints

- 951-source curated list (expandable, not reducible without CEO approval)
- 3-tier system (us_major, international, independent)
- 7-point lean spectrum
- Source country determines edition routing
- AllSides/Ad Fontes/NewsGuard as cross-reference standards
