# CEO Agent Playbook — void --news

Last updated: 2026-04-28 (rev 1)

**17 agents. 7 divisions. All via Claude Code CLI.**

---

## Quick Reference Card

```
                          void --news Agent Map
 -----------------------------------------------------------------------
  QUALITY (4)          INFRASTRUCTURE (3)     FRONTEND (4)
  analytics-expert     perf-optimizer         frontend-builder
  bias-auditor         db-reviewer            frontend-fixer
  pipeline-tester      update-docs            responsive-specialist
  bug-fixer                                   uat-tester
 -----------------------------------------------------------------------
  PIPELINE (3)         SECURITY (1)           PRODUCT (1)    BRAND (1)
  feed-intelligence    void-ciso              ceo-advisor    logo-designer
  nlp-engineer
  source-curator
 -----------------------------------------------------------------------
  Model tier:  [sonnet] execution (11)  [haiku] read-only (5)  [opus] creative (1)
```

---

## How to Invoke an Agent

Every agent lives in `.claude/agents/`. Claude Code auto-discovers them. Just describe what you need — the routing table handles the rest.

**Direct invocation** (when you know which agent):
```
Run the pipeline-tester agent to validate the latest pipeline output.
```

**Task-based** (let routing decide):
```
Check if our bias scores match known outlet profiles for AP, Fox News, and NPR.
```

**Multi-agent sequential** (chain agents yourself):
```
First run feed-intelligence to audit RSS health, then run pipeline-tester to validate output.
```

---

## Decision Tree: "I want to..."

### Pipeline & Data

| I want to... | Agent | Prompt to copy-paste |
|---|---|---|
| Check if RSS feeds are working | `feed-intelligence` | `Audit RSS feed health across all 90 sources. Report which feeds are broken, empty, or timing out.` |
| Improve cluster titles/summaries | `feed-intelligence` | `Review cluster summarization quality. Find clusters with "Untitled Story" titles or missing summaries. Improve the generation logic in story_cluster.py.` |
| Fix broken article scraping | `feed-intelligence` | `Audit article parsing quality. Check word_count distribution — flag sources where extraction consistently fails. Improve web_scraper.py selectors.` |
| Tune bias scoring algorithms | `nlp-engineer` | `Audit the political_lean analyzer. The keyword lexicons may be missing recent political terminology. Review and expand LEFT_KEYWORDS and RIGHT_KEYWORDS.` |
| Validate bias scores are accurate | `bias-auditor` | `Run a 25-article bias audit. Test 5 wire reports (AP, Reuters), 5 opinion pieces, 5 investigative (ProPublica), 5 partisan left (Jacobin), 5 partisan right (National Review). Grade each.` |
| Benchmark against competitors | `analytics-expert` | `Run a competitive gap analysis against AllSides, Ad Fontes, and NewsGuard. Where do they detect biases that our engine misses?` |
| Fix a pipeline bug | `bug-fixer` | `The pipeline-tester flagged [PASTE ISSUE]. Diagnose root cause, group related failures, and implement surgical fixes.` |
| Validate after pipeline changes | `pipeline-tester` | `Run full pipeline validation. Check article parsing, bias score distributions, clustering quality, and ranking output. Report verdict.` |
| Add/remove a news source | `source-curator` | `Evaluate [SOURCE NAME] for inclusion in the [TIER] tier. Check credibility criteria, RSS availability, and political lean baseline.` |
| Check database health | `db-reviewer` | `Run a full data quality audit on Supabase. Check article completeness, bias score distributions, cluster integrity, and orphaned records.` |

### Frontend

| I want to... | Agent | Prompt to copy-paste |
|---|---|---|
| Build a new component | `frontend-builder` | `Build the [COMPONENT] component following Press & Precision. It should [BEHAVIOR]. Desktop: [LAYOUT]. Mobile: [LAYOUT]. Use Playfair for headlines, Inter for body, JetBrains Mono for data.` |
| Fix a UI bug | `frontend-fixer` | `Fix: [DESCRIBE BUG]. It happens at [VIEWPORT]px in [LIGHT/DARK] mode. Steps to reproduce: [STEPS].` |
| Fix responsive layout | `responsive-specialist` | `The [COMPONENT] breaks at [VIEWPORT]px. Desktop shows [X], mobile should show [Y]. Verify across all 4 breakpoints x 2 color modes.` |
| Run browser testing | `uat-tester` | `Run full UAT on the homepage. Test all 7 phases: page load, core journey, bias display, responsive (375/768/1024/1440), accessibility, and edge cases.` |

### Operations & Strategy

| I want to... | Agent | Prompt to copy-paste |
|---|---|---|
| Speed up the pipeline | `perf-optimizer` | `Profile the pipeline runtime. The 6-minute budget is [OVER/CLOSE]. Find the top 3 bottlenecks and implement safe optimizations.` |
| Run a security audit | `void-ciso` | `Run a full 10-domain security audit. Priority: secrets exposure, RLS policies, injection vectors, and dependency vulnerabilities.` |
| Get strategic advice | `ceo-advisor` | `Review current product state. Give me your top 10 recommendations ranked by impact x feasibility. End with "The One Thing" for launch.` |
| Sync documentation | `update-docs` | `Scan the codebase for doc drift. Compare CLAUDE.md, AGENT-TEAM.md, and docs/*.md against actual code. Fix any stale content.` |
| Design the logo | `logo-designer` | `Explore 5 logo directions for void --news. The logo must work at 16px (favicon) and 400px+ (masthead). Deliver SVG concepts for review.` |

---

## Sequential Cycle Recipes

These are pre-defined agent chains. Run them in order — each agent's output feeds the next.

### After every pipeline code change

```
Step 1:  Run pipeline-tester — validate output
Step 2:  If RED → run bug-fixer with the test report
Step 3:  Re-run pipeline-tester to confirm fix
```

**Copy-paste prompt chain:**
```
1. "Run pipeline-tester. Validate articles, bias scores, clusters, and ranking."
2. "Run bug-fixer. Here's the pipeline-tester report: [PASTE REPORT]. Fix the failures."
3. "Re-run pipeline-tester. Confirm the fixes didn't regress."
```

### Full bias engine tune-up

```
Step 1:  analytics-expert  — benchmark scores, find gaps
Step 2:  bias-auditor      — validate against ground truth
Step 3:  nlp-engineer      — implement scoring improvements
Step 4:  pipeline-tester   — validate no regression
```

**Copy-paste:**
```
1. "Run analytics-expert. Benchmark bias scores for AP, Fox, NPR, Jacobin, ProPublica. Identify gaps."
2. "Run bias-auditor. 25-article validation round. Grade results and find worst failures."
3. "Run nlp-engineer. Fix the failures identified by bias-auditor: [PASTE FAILURES]."
4. "Run pipeline-tester. Full regression check after nlp-engineer changes."
```

### Frontend feature build

```
Step 1:  frontend-builder      — build the component
Step 2:  responsive-specialist  — verify all breakpoints
Step 3:  uat-tester             — browser testing
Step 4:  frontend-fixer         — fix any issues found
```

**Copy-paste:**
```
1. "Run frontend-builder. Build [COMPONENT] with Press & Precision design system."
2. "Run responsive-specialist. Verify [COMPONENT] across 375/768/1024/1440px, light+dark."
3. "Run uat-tester. Full UAT on homepage including the new [COMPONENT]."
4. "Run frontend-fixer. Fix these issues from UAT: [PASTE FINDINGS]."
```

### Content quality improvement

```
Step 1:  feed-intelligence  — audit ingestion quality
Step 2:  pipeline-tester    — validate improvements
Step 3:  bug-fixer          — fix any issues
Step 4:  pipeline-tester    — confirm
```

**Copy-paste:**
```
1. "Run feed-intelligence. Audit cluster titles, summaries, and section assignments. Fix the worst offenders."
2. "Run pipeline-tester. Validate clustering quality and content generation after changes."
3. "If issues: Run bug-fixer with the test report."
4. "Re-run pipeline-tester. Confirm green."
```

### Full pipeline development cycle

```
Step 1:  feed-intelligence  — improve ingestion/summarization
Step 2:  nlp-engineer       — improve bias scoring
Step 3:  pipeline-tester    — validate everything
Step 4:  bug-fixer          — fix failures
Step 5:  pipeline-tester    — final confirmation
```

---

## Parallel Agents (Run Simultaneously)

These read-only agents never conflict — run them all at once for a full system health check:

```
Run these 5 agents in parallel:
1. pipeline-tester — validate pipeline output
2. db-reviewer — audit Supabase data quality
3. void-ciso — security audit
4. ceo-advisor — strategic recommendations
5. uat-tester — browser testing
```

**Copy-paste for full system audit:**
```
Run these agents in parallel:
- pipeline-tester: Full pipeline validation
- db-reviewer: Supabase data quality audit
- void-ciso: Security audit (10 domains)
- uat-tester: Full browser UAT on homepage
- ceo-advisor: Top 10 strategic recommendations for launch
```

---

## Agent Quick-Reference by Model Tier

### Sonnet (11 agents) — Execution, Read+Write

These do the actual building and fixing. Run sequentially when touching the same files.

```
analytics-expert    bias-auditor       bug-fixer
feed-intelligence   frontend-builder   frontend-fixer
nlp-engineer        perf-optimizer     responsive-specialist
source-curator      update-docs
```

### Haiku (5 agents) — Read-Only, Fast

These audit, test, and advise. Safe to run in parallel. Never modify files.

```
pipeline-tester   db-reviewer   void-ciso   ceo-advisor   uat-tester
```

### Opus (1 agent) — Creative

```
logo-designer
```

---

## Rules of Engagement

### DO

- **Always pipeline-tester after pipeline changes** — it's your safety net
- **Chain agents sequentially** for write operations on same files
- **Run read-only agents in parallel** for fast system audits
- **Paste previous agent output** into the next agent's prompt for context
- **Be specific** — "Fix the political_lean scorer for Reuters articles" beats "fix bias"

### DON'T

- **Don't run two write agents on the same files** simultaneously
- **Don't skip pipeline-tester** after nlp-engineer or bug-fixer changes
- **Don't ask agents to spawn other agents** — you route, they execute
- **Don't ask for paid API calls** — everything is rule-based NLP, $0
- **Don't change locked decisions** without updating CLAUDE.md

### Blast Radius Limits (Per Agent Run)

```
Pipeline agents:  max 4 Python files
Frontend agents:  max 4 CSS + 2 TypeScript files
Source curator:   max 1 file (sources.json)
Update docs:      max 4 documentation files
```

---

## Common Scenarios

### "The pipeline output looks wrong"
```
Run pipeline-tester. Full validation — articles, scores, clusters, ranking.
```
Then based on the verdict:
- **RED (scoring)** → `bias-auditor` then `bug-fixer`
- **RED (clustering)** → `feed-intelligence` then `bug-fixer`
- **RED (data integrity)** → `db-reviewer` then `bug-fixer`
- **AMBER** → monitor, no immediate action

### "A news source stopped working"
```
Run feed-intelligence. Audit RSS health for [SOURCE]. Report status, error type, and suggest fix.
```
Then:
```
Run source-curator. The feed for [SOURCE] is broken. Find a working RSS URL or recommend a replacement source for the [TIER] tier.
```

### "Bias scores seem off for [OUTLET]"
```
Run bias-auditor. Test 5 recent articles from [OUTLET]. Expected lean: [X]. Compare actual scores to expected ranges. Grade each result.
```
If failures:
```
Run nlp-engineer. The bias-auditor found [OUTLET] articles scoring [ACTUAL] instead of expected [EXPECTED]. Root cause: [FROM AUDITOR REPORT]. Fix the relevant analyzer.
```

### "The frontend looks broken on mobile"
```
Run uat-tester. Focus on 375px viewport. Test homepage story cards, bias stamps, navigation, and Deep Dive modal.
```
Then:
```
Run frontend-fixer. Here are the UAT findings: [PASTE]. Fix the mobile layout issues.
```
Then:
```
Run responsive-specialist. Verify the fixes across all 4 breakpoints x 2 color modes.
```

### "Pre-launch checklist"
Run all 5 read-only agents in parallel:
```
Run in parallel:
- pipeline-tester: Full pipeline validation
- db-reviewer: Data quality audit
- void-ciso: Security audit
- uat-tester: Full browser UAT
- ceo-advisor: Launch readiness assessment
```
Then address any findings with the appropriate write agents.

---

## File Locations

```
Agents:          .claude/agents/*.md          (17 files)
Team structure:  docs/AGENT-TEAM.md
Design system:   docs/DESIGN-SYSTEM.md
Master doc:      CLAUDE.md
Source list:     data/sources.json
Pipeline:        pipeline/main.py
Frontend:        frontend/
```
