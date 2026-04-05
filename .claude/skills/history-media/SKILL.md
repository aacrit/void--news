---
name: history-media
description: "Visual Asset Curation Workflow: media-archaeologist sources assets, historiographic-auditor checks visual bias, visual-historian integrates into page design."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /history-media -- Visual Asset Curation Workflow

You orchestrate visual asset sourcing and integration for void --history events.

## Workflow

```
media-archaeologist → historiographic-auditor (visual bias check) → visual-historian (integration)
```

### Stage 1 -- Source
Launch **media-archaeologist** to:
- Source 5-10 public domain images, maps, documents per event
- Complete Context Protocol for each (what/when/where/who/source/rights/perspective/not-shown)
- Verify licensing (public domain, CC0, CC-BY, CC-BY-SA)

### Stage 2 -- Visual Bias Audit
Launch **historiographic-auditor** to check:
- Does image collection represent all perspectives?
- Are non-Western visual sources included?
- Is the dominant perspective over-represented visually?

### Stage 3 -- Integration
Launch **visual-historian** to integrate assets into the event page design:
- Hero image selection and Ken Burns parameters
- Gallery ordering and archival grade filter settings
- Document viewer annotations

## Final Report

```
## History Media Report -- [Event Name]
- **Assets sourced**: [N] (photos [N], maps [N], documents [N])
- **Rights**: public domain [N], CC [N], fair use [N]
- **Perspective coverage**: [list perspectives with asset counts]
- **Visual bias**: [PASS/FAIL]
- **Integration**: [COMPLETE/PENDING]
```
