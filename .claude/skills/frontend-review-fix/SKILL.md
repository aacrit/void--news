---
name: frontend-review-fix
description: "Frontend Review & Fix Cycle: uat-tester audits full UI state, CEO prioritizes focus areas, frontend-fixer implements chosen fixes, frontend-builder verifies build, uat-tester retests. CEO-in-the-loop quality cycle."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /frontend-review-fix — Frontend Review & Fix Cycle

You are the workflow orchestrator for the **Frontend Review & Fix Cycle** — a CEO-in-the-loop quality process for the void --news frontend. Unlike `/frontend-ship` (which builds + ships a specific feature), this workflow starts from the current frontend state, audits everything, lets the CEO decide what matters most, then fixes and verifies.

## Objective

Audit the full frontend, present findings to the CEO for prioritization, implement the prioritized fixes, build-verify, and confirm with a retest. The CEO decides what gets fixed — you execute.

## When to Use

- Periodic frontend health check (no specific feature in mind)
- CEO wants to assess overall UI quality before deciding next steps
- After a batch of changes, to catch accumulated regressions
- Pre-launch frontend hardening with CEO-directed focus

## Workflow Stages

```
+--------------------------------------------------------------+
|  STAGE 1 -- AUDIT (read-only)                                |
|  uat-tester: full 12-dimension UI/UX audit                   |
|  Deliverable: structured audit report with prioritized issues |
+--------------------------------------------------------------+
          |
          v
+--------------------------------------------------------------+
|  STAGE 2 -- CEO DECISION (human-in-the-loop)                |
|  Present findings. CEO selects focus areas and priorities.    |
|  Deliverable: scoped fix list with CEO approval              |
+--------------------------------------------------------------+
          |
          v
+--------------------------------------------------------------+
|  STAGE 3 -- FIX (write)                                      |
|  frontend-fixer: implement CEO-prioritized fixes              |
|  Deliverable: fix report with files changed                  |
+--------------------------------------------------------------+
          |
          v
+--------------------------------------------------------------+
|  STAGE 4 -- BUILD VERIFY (write)                             |
|  frontend-builder: build + verify changes compile clean      |
|  Deliverable: build confirmation                             |
+--------------------------------------------------------------+
          |
          v
+--------------------------------------------------------------+
|  STAGE 5 -- RETEST (read-only)                               |
|  uat-tester: targeted retest of fixed areas                  |
|  Deliverable: pass/fail confirmation                         |
+--------------------------------------------------------------+
          |
          v
+--------------------------------------------------------------+
|  GATE: All fixed items pass? -> DONE                         |
|  Remaining issues? -> Report to CEO for next iteration       |
+--------------------------------------------------------------+
```

## Execution Instructions

### Stage 1 -- Full UI/UX Audit

Launch **uat-tester** with the following prompt:

> Run a complete 12-dimension audit of the void --news frontend in its current state. Cover all 10 phases (first impression through edge cases). Evaluate information architecture, visual hierarchy, interaction design, accessibility, responsive behavior, design system compliance, and animation quality. Read every component in `frontend/app/components/`, the page entry points, all style files, and `tokens.css`. Produce the full structured audit report with severity classifications (S0-S4), persona impact, dimension scores, responsive matrix, and accessibility verdict. End with the Top 5 Priorities and The One Thing.

Collect the full audit report. This is a read-only agent; it will not modify any files.

### Stage 2 -- CEO Prioritization

**Do not skip this stage.** Present the audit findings to the CEO in a digestible summary:

1. **Executive summary** -- 2-3 sentences on overall frontend health
2. **Top issues by severity** -- List all S0 and S1 findings with one-line descriptions
3. **Dimension scores** -- The 12-dimension scorecard from the audit
4. **Suggested focus areas** -- Group findings into actionable themes, for example:
   - Accessibility gaps (keyboard nav, ARIA, contrast)
   - Responsive breakage (specific breakpoints, specific components)
   - Visual hierarchy issues (type voice misuse, spacing inconsistency)
   - Interaction problems (feedback, state communication, error handling)
   - Animation polish (spring timing, reduced-motion, GPU compliance)
   - Design system violations (Dot Matrix Rule, Press & Precision deviations)
   - Data display issues (null handling, fallback UI, edge cases)

Then ask the CEO:

> Which focus areas should I prioritize for this cycle? You can pick specific findings by ID, choose entire themes, or set a severity cutoff (e.g., "fix all S0 and S1"). I will scope the fix work accordingly.

**Wait for the CEO's response before proceeding.**

### Stage 3 -- Targeted Fix Implementation

Once the CEO specifies priorities, launch **frontend-fixer** with a scoped brief:

> Fix the following issues from the UI/UX audit. [Include the specific findings the CEO selected, with full detail: component name, viewport, evidence, fix direction from the audit report.]
>
> Priority order: [CEO's stated priority order, or default to severity S0 > S1 > S2]
>
> Constraints:
> - Max 4 CSS files, 2 TypeScript files per the blast radius limit
> - All colors from CSS custom properties (tokens.css)
> - Responsive: mobile-first, min-width breakpoints at 375/768/1024/1440
> - Animation: spring physics (Motion One), GPU-only (transform + opacity)
> - Typography: Playfair Display (editorial), Inter (structural), Barlow Condensed (meta), IBM Plex Mono (data)
> - Accessibility: WCAG 2.1 AA, keyboard nav, ARIA, focus management
> - Follow Press & Precision design system — no rounded-everything, no generic gradients, no SaaS dashboard patterns

Collect the fix report. Track which findings were addressed.

### Stage 4 -- Build Verification

Launch **frontend-builder** with a verification-only brief:

> Verify the frontend builds clean after the latest fixes. Run `cd frontend && npm run build` (static export). Check:
> - Build completes without errors or warnings
> - CSS load order is correct (reset, tokens, layout, typography, components, animations, responsive)
> - No new TypeScript errors
> - Component inventory is consistent (no broken imports)
>
> If the build fails, fix the build-breaking issue and report what was wrong.

If the build fails, the frontend-builder will fix the build issue. If it required code changes beyond the build fix, note this in the final report.

### Stage 5 -- Targeted Retest

Launch **uat-tester** with a focused retest brief:

> Retest the following specific fixes from the Frontend Review & Fix cycle. For each fix, confirm whether the issue is resolved. [Include the list of findings that were fixed in Stage 3, with their original evidence so the tester knows exactly what to verify.]
>
> For each fixed item, report: RESOLVED / PARTIALLY RESOLVED / NOT RESOLVED / REGRESSED.
>
> Also check: did any fix introduce a new issue in adjacent components or viewports? Report any regressions.

Collect the retest report.

### Final Gate

- **All fixed items RESOLVED, no regressions** -- Workflow complete. Deliver final report.
- **Some items NOT RESOLVED or REGRESSED** -- Report remaining issues to the CEO. Do not loop automatically. The CEO decides whether to run another iteration.

### Final Report

```
## Frontend Review & Fix Report
- **Date**: [today]
- **Result**: COMPLETE / PARTIAL (N items remaining)

### Audit Summary
- **UX Maturity**: [1-5] (from Stage 1 audit)
- **Composite Score**: [N]/120
- **Issues Found**: S0:[N] S1:[N] S2:[N] S3:[N] S4:[N] — Total: [N]

### CEO Focus
- **Selected themes**: [list]
- **Selected findings**: [IDs]
- **Severity cutoff**: [if applicable]

### Fix Results
- **Fixes attempted**: [N]
- **Files changed**: [list with file:line]
- **Build**: PASS / FAIL (fixed in Stage 4)

### Retest Results
- **RESOLVED**: [N] — [IDs]
- **PARTIALLY RESOLVED**: [N] — [IDs with notes]
- **NOT RESOLVED**: [N] — [IDs with reason]
- **REGRESSED**: [N] — [IDs with details]
- **New issues found**: [N] — [descriptions]

### Remaining Work
[List of unresolved items for the CEO to consider for the next cycle]
```

## Design Constraints (Press & Precision)

These are non-negotiable for all fix work:

- Sharp edges, thin rules — no rounded-everything
- Serif headlines (Playfair Display), structural body (Inter), meta (Barlow Condensed), data mono (IBM Plex Mono)
- Color earned through meaning (bias colors only for bias data, not decoration)
- Progressive disclosure: clean on arrival, data-dense on interaction
- GPU-only animations: transform + opacity only
- `prefers-reduced-motion`: all animations to 0ms
- WCAG 2.1 AA minimum
- Mobile-first responsive: 375/768/1024/1440px breakpoints
- Desktop: multi-column newspaper grid, top nav
- Mobile: single-column feed, bottom nav, bottom sheets
- Touch targets 44px+ on mobile
- CSS custom properties only (no hardcoded colors, spacing, or type sizes)
- No UI libraries (no Tailwind, no MUI, no Chakra)
- Body text: `text-align: justify; hyphens: auto`

## Differences from /frontend-ship

| Aspect | /frontend-ship | /frontend-review-fix |
|--------|----------------|----------------------|
| Trigger | Specific feature or change to build | No specific feature — audit current state |
| Starting point | A build task | The existing frontend |
| Stage 1 | Build the feature | Audit everything |
| CEO input | Before workflow (defines what to build) | Mid-workflow (prioritizes what to fix) |
| Scope | One feature through the quality gate | Broad audit, CEO-scoped fixes |
| Responsive check | Dedicated responsive-specialist stage | Covered within uat-tester audit |
| Performance check | Dedicated perf-optimizer stage | Build verification only (Stage 4) |
| Iterations | Fix + retest loop until clean | One cycle, CEO decides on next iteration |
