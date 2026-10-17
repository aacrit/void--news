---
name: history-publish
description: "Content Publishing Workflow: narrative-engineer polishes, auditor signs off, cinematic trio designs motion, visual-historian implements, frontend-builder builds, uat-tester verifies."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /history-publish -- Content Publishing Workflow

You orchestrate the publication of a void --history event from content-complete to live.

## Workflow

```
narrative-engineer → historiographic-auditor (final sign-off)
  → [cinematographer + motion-director + vfx-artist] (parallel cinematic pass)
  → visual-historian (implement design)
  → frontend-builder (build components)
  → [responsive-specialist + perf-optimizer] (parallel validation)
  → uat-tester (final verification)
```

### Stage 1 -- Final Content Polish
Launch **narrative-engineer** for final show-don't-tell pass and citation verification.

### Stage 2 -- Final Audit
Launch **historiographic-auditor** for sign-off. Must be BALANCED or ACCEPTABLE.

### Stage 3 -- Cinematic Design (Parallel)
Launch in parallel:
1. **cinematographer** -- Camera language for the event page
2. **motion-director** -- Scroll choreography, perspective transitions
3. **vfx-artist** -- Archival grade, textures, Ken Burns parameters

### Stage 4 -- Implementation
Launch **visual-historian** to implement the cinematic design in components.

### Stage 5 -- Build
Launch **frontend-builder** to handle any complex component engineering.

### Stage 6 -- Validation (Parallel)
Launch in parallel:
1. **responsive-specialist** -- Validate across breakpoints (375/768/1024/1440)
2. **perf-optimizer** -- Lighthouse 85+ despite image-heavy pages

### Stage 7 -- Final Verification
Launch **uat-tester** to click through everything: perspectives, gallery, timeline, comparison mode, mobile.

## Final Report

```
## History Publish Report -- [Event Name]
- **Content**: narrative-engineer APPROVED
- **Audit**: historiographic-auditor [grade]
- **Cinematic**: camera + motion + VFX designed
- **Implementation**: visual-historian COMPLETE
- **Responsive**: [breakpoints tested]
- **Performance**: Lighthouse [score]
- **UAT**: [pass/fail with details]
```
