---
name: history-qa
description: "History Quality Assurance Workflow: parallel audit + content check, perspective-analyst fixes, auditor re-validates, uat-tester checks frontend."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /history-qa -- History Quality Assurance Workflow

You orchestrate comprehensive quality sweeps across void --history content and UI.

## Workflow

```
[historiographic-auditor + narrative-engineer] (parallel audit)
  → perspective-analyst (fixes)
  → historiographic-auditor (re-validate)
  → uat-tester (frontend check)
```

### Stage 1 -- Parallel Audit
Launch in parallel:
1. **historiographic-auditor** -- Full 10-dimension balance audit across all published events
2. **narrative-engineer** -- Show-don't-tell sweep, citation density check, vocabulary audit

### Stage 2 -- Fix
Compile findings from both auditors. Launch **perspective-analyst** to fix:
- Balance issues flagged by auditor
- Content quality issues flagged by narrative-engineer

### Stage 3 -- Re-validate
Launch **historiographic-auditor** to confirm all fixes resolved.

### Stage 4 -- Frontend Check
Launch **uat-tester** to verify:
- All event pages render correctly
- Perspective switching works (lectern turn animation)
- Media gallery loads (lazy loading, archival grade)
- Timeline navigation functions
- Comparison mode works
- Mobile responsive behavior
- Reduced-motion fallbacks
- Keyboard accessibility

## Final Report

```
## History QA Report
- **Events audited**: [N]
- **Balance issues found**: [N] → [N] fixed
- **Show-don't-tell violations**: [N] → [N] fixed
- **Citation gaps**: [N] → [N] fixed
- **Frontend issues**: [N] → [N] fixed
- **Overall**: PASS / FAIL
```
