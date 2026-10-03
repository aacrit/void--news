---
name: history-audit
description: "Perspective Validation Workflow: historiographic-auditor checks balance, perspective-analyst fixes, auditor re-validates. Before publishing or on CEO spot-check."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /history-audit -- Perspective Validation Workflow

You orchestrate the balance validation cycle for void --history events.

## Workflow

```
historiographic-auditor �� perspective-analyst (fixes) → historiographic-auditor (re-validate)
```

### Stage 1 -- Audit
Launch **historiographic-auditor** on the target event(s). Collect the 10-dimension scores and swap test result.

### Stage 2 -- Fix (if needed)
If grade is SKEWED or FAILED, launch **perspective-analyst** with the specific fixes from the audit report.

### Stage 3 -- Re-validate
Launch **historiographic-auditor** again to confirm fixes resolved all issues. Repeat until BALANCED or ACCEPTABLE.

## Final Report

```
## History Audit Report
- **Event**: [name]
- **Initial grade**: [grade]
- **Fix rounds**: [N]
- **Final grade**: [BALANCED/ACCEPTABLE]
- **Source diversity ratio**: Western [N] : Non-Western [N]
- **Swap test**: PASS
```
