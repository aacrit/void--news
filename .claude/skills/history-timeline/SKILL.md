---
name: history-timeline
description: "Timeline & Connection Workflow: history-curator provides events, timeline-architect maps connections, visual-historian designs UI, archive-cartographer adds map layer."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /history-timeline -- Timeline & Connection Workflow

You orchestrate temporal narrative design and geographic visualization for void --history.

## Workflow

```
history-curator (event list) → timeline-architect → visual-historian (timeline UI) → archive-cartographer (map layer)
```

### Stage 1 -- Event Registry
Launch **history-curator** to provide the current event registry with dates, regions, and coordinates.

### Stage 2 -- Connection Mapping
Launch **timeline-architect** to:
- Map all cross-event connections (minimum 2 per event)
- Classify by type (caused/influenced/response-to/parallel/consequence)
- Identify hub events (5+ connections)
- Design visual hierarchy

### Stage 3 -- Timeline UI
Launch **visual-historian** to design the timeline interface:
- Horizontal corridor with organic ink SVG track
- Era background bands
- Event nodes with archival photos on hover
- Connection lines between related events

### Stage 4 -- Map Layer
Launch **archive-cartographer** to:
- Design SVG world map with event pins
- Organic ink line quality for borders
- Ink-stipple terrain textures
- Region highlighting interactions

## Final Report

```
## Timeline Report
- **Events mapped**: [N]
- **Connections**: [N] (caused [N], influenced [N], parallel [N], ...)
- **Hub events**: [list with connection counts]
- **Orphan events**: [list with < 2 connections]
- **Map regions covered**: [list]
```
