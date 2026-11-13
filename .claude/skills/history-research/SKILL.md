---
name: history-research
description: "Event Research Workflow: history-curator selects event, perspective-analyst + media-archaeologist work parallel, historiographic-auditor validates, narrative-engineer polishes. For new event onboarding."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /history-research -- Event Research Workflow

You are the workflow orchestrator for void --history event research. This workflow takes a new historical event from selection through to publication-ready content.

## Workflow Stages

```
┌────────────────────────────────────────────────────────┐
│  STAGE 1 -- SELECT (write)                             │
│  history-curator: identify event, verify criteria,     │
│  draft event YAML                                      │
├────────────────────────────────────────────────────────┤
│  STAGE 2 -- STRUCTURE (parallel, write)                │
│  perspective-analyst: 5-lens framework, 3-6 viewpoints │
│  media-archaeologist: public domain images, maps, docs │
├────────────────────────────────────────────────────────┤
│  STAGE 3 -- CINEMATIC PASS (parallel, write)           │
│  cinematographer: camera language for event page        │
│  motion-director: scroll choreography                  │
│  vfx-artist: archival grade, foxing, post-processing   │
├────────────────────────────────────────────────────────┤
│  STAGE 4 -- AUDIT (read-only)                          │
│  historiographic-auditor: 10-dimension balance check   │
├────────────────────────────────────────────────────────┤
│  GATE: BALANCED/ACCEPTABLE → Stage 5                   │
│        SKEWED/FAILED → return to Stage 2               │
├────────────────────────────────────────────────────────┤
│  STAGE 5 -- POLISH (write)                             │
│  narrative-engineer: show-don't-tell, citations, voice │
└────────────────────────────────────────────────────────┘
```

## Execution Instructions

### Stage 1 -- Select
Launch **history-curator** with the event name/topic. The curator will:
- Research the event using academic sources
- Verify all 5 selection criteria (multi-perspective, structural impact, source richness, regional balance, narrative tension)
- Draft the event YAML in `data/history/events/`

### Stage 2 -- Structure (Parallel)
Launch these two agents **in parallel**:
1. **perspective-analyst** -- Structure 3-6 perspectives using the 5-lens framework. Apply juxtaposition test.
2. **media-archaeologist** -- Source 5-10 public domain images, maps, documents. Complete Context Protocol for each.

### Stage 3 -- Cinematic Pass (Parallel)
Launch these three agents **in parallel**:
1. **cinematographer** -- Design camera language for this event's page (parallax depth, rack focus points)
2. **motion-director** -- Choreograph scroll-driven reveals and perspective transitions
3. **vfx-artist** -- Specify archival grade treatment, texture overlays, Ken Burns parameters

### Stage 4 -- Audit
Launch **historiographic-auditor** to validate:
- Balance across all 10 dimensions
- Source diversity (non-Western sources >= 30%)
- Swap test passage
- Visual bias check

**Gate:** If BALANCED or ACCEPTABLE → proceed. If SKEWED or FAILED → return to Stage 2 with specific fixes.

### Stage 5 -- Polish
Launch **narrative-engineer** to:
- Enforce show-don't-tell (zero banned vocabulary)
- Verify citation density (1+ per claim)
- Verify primary source quotes (1+ per perspective)
- Polish for precision and voice

## Final Report

```
## History Research Report -- [Event Name]
- **Result**: READY / NEEDS WORK
- **Perspectives**: [N] structured, all pass juxtaposition test
- **Media**: [N] assets sourced, all with Context Protocol
- **Audit grade**: [BALANCED/ACCEPTABLE]
- **Citations**: [N] per 500 words
- **Show-don't-tell violations**: 0
```
