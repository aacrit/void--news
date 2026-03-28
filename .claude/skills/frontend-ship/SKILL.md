---
name: frontend-ship
description: "Frontend Ship Cycle: frontend-builder builds + responsive-specialist validates layouts + uat-tester clicks everything + frontend-fixer patches. Full UI quality gate."
user-invocable: true
disable-model-invocation: false
allowed-tools: Agent, Read, Grep, Glob, Bash, Edit, Write, TaskCreate, TaskUpdate, TaskList, SendMessage
---

# /frontend-ship — Frontend Ship Cycle

You are the workflow orchestrator for the **Frontend Ship Cycle** — the end-to-end quality gate for any UI change in void --news. This ensures every component meets Press & Precision standards, works across desktop and mobile, passes UAT, and ships clean.

## Objective

Take a frontend change from implementation through responsive validation, browser UAT, and bug fixing. Nothing ships without passing all four stages.

## Workflow Stages

```
┌──────────────────────────────────────────────────────────┐
│  STAGE 1 — BUILD (write)                                 │
│  frontend-builder: implement the UI change/feature        │
│  (invoke /pressdesign skill internally for design review) │
├──────────────────────────────────────────────────────────┤
│  STAGE 2 — RESPONSIVE + BUILD CHECK (parallel)           │
│  responsive-specialist: dual-layout validation            │
│  perf-optimizer: Lighthouse audit (target 90+)            │
├──────────────────────────────────────────────────────────┤
│  STAGE 3 — UAT (read-only)                               │
│  uat-tester: click every button, resize viewports         │
├──────────────────────────────────────────────────────────┤
│  GATE: If Stage 2+3 pass clean → DONE                    │
├──────────────────────────────────────────────────────────┤
│  STAGE 4 — FIX (write)                                   │
│  frontend-fixer: patch all reported issues                │
│  → Re-run Stage 3 (uat-tester) for confirmation           │
└──────────────────────────────────────────────────────────┘
```

## Execution Instructions

### Stage 1 — Build

Launch **frontend-builder** with the user's feature/change request:
- Implement using Next.js 16 App Router, React 19, TypeScript
- Follow Press & Precision design system (3-voice typography, newspaper grid, progressive disclosure)
- Use CSS custom properties from `frontend/app/styles/tokens.css`
- Animation: Motion One v11 spring presets (snappy/smooth/gentle)
- Mobile-first responsive: `min-width` breakpoints at 375/768/1024/1440
- Build must pass: `cd frontend && npm run build`

### Stage 2 — Responsive + Performance (Parallel)

Launch these two agents **in parallel**:

1. **responsive-specialist** — Dual-layout validation:
   - Desktop (1024px+): multi-column newspaper grid, side panel Deep Dive (55% width)
   - Mobile (375px): single-column feed, bottom sheet, 44x44px touch targets
   - Tablet (768px): graceful transition
   - Check: `overflow-wrap: break-word` on headlines, `flex-wrap: wrap` on section headers
   - Check: edge padding `--space-5` on mobile
   - Check: `clamp()` fluid scaling, no fixed pixel widths
   - Light/dark mode both layouts

2. **perf-optimizer** — Frontend performance:
   - `cd frontend && npm run build` (static export must succeed)
   - Bundle size check (Motion One ~6.5KB only external dependency)
   - No unnecessary re-renders (React 19 best practices)
   - Image optimization if applicable
   - CSS load order correct (reset → tokens → layout → typography → components → animations → responsive)

### Stage 3 — UAT (Read-Only)

Launch **uat-tester** with the build output:
- Click every interactive element (buttons, toggles, filters, Deep Dive triggers)
- Test edition switching (World/US/India)
- Test category filtering
- Test Deep Dive open/close on desktop and mobile
- Test BiasLens hover/click interactions
- Test DailyBrief audio player controls
- Test light/dark theme toggle
- Resize viewport continuously from 375px to 1440px
- Screenshot any visual anomalies
- Report: list of issues with component name, viewport size, and reproduction steps

### Stage 3 Gate

- **ALL PASS** → Report to CEO. Workflow complete.
- **ANY ISSUE** → Proceed to Stage 4.

### Stage 4 — Fix + Re-test

Launch **frontend-fixer** with the UAT report:
- Fix each reported issue
- Categorize: layout break / animation jank / a11y gap / responsive breakage / interaction bug
- After fixes: re-run **uat-tester** to confirm all issues resolved

### Final Report

```
## Frontend Ship Report
- **Result**: SHIPPED / BLOCKED
- **Feature/Change**: [description]
- **Build**: PASS (static export succeeded)
- **Responsive**: Desktop PASS/FAIL | Mobile PASS/FAIL | Tablet PASS/FAIL
- **Lighthouse**: Performance [X] | Accessibility [X] | Best Practices [X]
- **UAT Issues**: [count] found → [count] fixed → [count] remaining
- **Components touched**: [list]
- **Files changed**: [list with file:line]
```

## Design Constraints (Press & Precision)

- Sharp edges, thin rules — no rounded-everything
- Serif headlines (Playfair Display), structural body (Inter), data mono (JetBrains Mono)
- Color earned through meaning (bias colors, not decoration)
- Progressive disclosure: clean on arrival, data-dense on interaction
- GPU-only animations: transform + opacity only
- `prefers-reduced-motion`: all animations → 0ms
- WCAG 2.1 AA minimum
