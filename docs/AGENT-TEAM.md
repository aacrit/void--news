# void --news Agent Team Structure

Last updated: 2026-04-09 (rev 22)

## Philosophy

Adapted from DondeAI. Every principle is inherited and tailored for a news bias analysis platform.

### Core Principles

1. **No Hierarchical Delegation** — Agents cannot spawn other agents. Task routing at the human level.
2. **Read-First Protocol** — Every agent reads CLAUDE.md + relevant docs before any work.
3. **Execution Protocol** — Assess → Plan → Build → Verify → Report. No exceptions.
4. **Max Blast Radius** — Max 4 CSS, 2 JS/TS, 3 Python files per run.
5. **$0 Cost — Claude Max CLI Only** — All agent/dev work via Claude Code CLI. The only permitted external API call is Gemini Flash on its free tier. No paid inference anywhere.
6. **Parallel-Safe vs Sequential** — Read-only agents can run simultaneously. Write agents require sequencing.

### Cost Policy

```
COST BUDGET: $0.00 — ABSOLUTE CEILING

Pipeline NLP:      Rule-based only (spaCy, NLTK, TextBlob) — $0
Summarization:     Gemini Flash free tier (250 RPD budget, ~177 RPD used) — $0
Audio TTS:         Gemini 2.5 Flash TTS free tier (same GEMINI_API_KEY) — $0
Database:          Supabase free tier — $0
Hosting:           GitHub Pages — $0
CI/CD:             GitHub Actions free tier — $0
Agent work:        Claude Code CLI (Max subscription) — $0
```

---

## Organizational Structure

```
CEO (Aacrit)
  ├── Agent Engineering — agent-architect
  ├── Quality ————————— analytics-expert, bias-auditor, bias-calibrator, pipeline-tester, bug-fixer
  ├── Infrastructure ——— perf-optimizer, db-reviewer, update-docs
  ├── Frontend ————————— frontend-builder, frontend-fixer, responsive-specialist, uat-tester
  ├── Cinematic ————————— cinematographer, vfx-artist, motion-director, color-grader
  ├── Pipeline ————————— feed-intelligence, nlp-engineer, source-curator, linguist
  ├── History —————————— history-curator, perspective-analyst, historiographic-auditor, media-archaeologist, timeline-architect, narrative-engineer
  ├── History Visual ——— visual-historian, archive-cartographer
  ├── Audio ———————————— audio-engineer
  ├── Security ————————— void-ciso
  ├── Product —————————— ceo-advisor
  └── Branding ————————— logo-designer
```

**Total: 34 agents across 13 divisions**

Note: Cinematic Division agents (cinematographer, motion-director, vfx-artist) are also core History team members, integrated into `/history-publish` and `/cinematic-overhaul` workflows. Full history spec: `docs/HISTORY.md`.

---

## Division Roster

### Quality Division

| Agent | Purpose | Write Access | Trigger |
|-------|---------|-------------|---------|
| `analytics-expert` | Bias engine benchmarking, ranking calibration | Yes | After algorithm changes |
| `bias-auditor` | Ground-truth validation against known outlet profiles | Yes | After scoring changes |
| `bias-calibrator` | Validation suite execution, score regression detection, axis weight tuning, ground-truth corpus maintenance. Quantitative counterpart to bias-auditor (qualitative). CI gate: `validate-bias.yml` runs on every push to `claude/*` touching `pipeline/analyzers/`; blocks merge on CATASTROPHIC failures. | Yes | After analyzer changes, on regression alert |
| `pipeline-tester` | Pipeline quality gate — parsing, clustering, scoring validation | No | After every pipeline change |
| `bug-fixer` | Post-test bug remediation, surgical fixes | Yes | After test failures |

### Infrastructure Division

| Agent | Purpose | Write Access | Trigger |
|-------|---------|-------------|---------|
| `perf-optimizer` | Pipeline runtime + frontend load time optimization | Yes | Performance issues |
| `db-reviewer` | Supabase data quality — articles, bias scores, clusters | No | After pipeline runs |
| `update-docs` | Sync CLAUDE.md and docs/*.md with current codebase | Yes | After significant changes |

### Frontend Division

| Agent | Purpose | Write Access | Trigger |
|-------|---------|-------------|---------|
| `frontend-builder` | Component engineering — Press & Precision design system | Yes | Feature requests |
| `frontend-fixer` | UI bug remediation — bias display, layout, animation, a11y | Yes | Bug reports |
| `responsive-specialist` | Desktop/mobile layout, light/dark modes | Yes | New components, responsive bugs |
| `uat-tester` | Browser testing — clicks, resizes, screenshots | No | After frontend changes |

### Pipeline Division

| Agent | Purpose | Write Access | Trigger |
|-------|---------|-------------|---------|
| `feed-intelligence` | RSS health, collection strategy, deduplication, cluster summarization | Yes | Pipeline development |
| `nlp-engineer` | spaCy/NLTK specialist — bias scoring algorithms, NER, sentiment | Yes | Bias engine development |
| `source-curator` | Source credibility vetting, RSS/scrape config, 1,013-source list | Yes | Source list changes |
| `linguist` | Media bias vocabulary research, lexicon expansion, linguistic gap analysis across all 5 bias analyzers | Yes | After bias calibration, lexicon gaps identified |
| `media-curator` | Free-API image sourcing for weekly cover + history supplemental (Wikimedia, Unsplash, Pexels, Pixabay) | Yes | Weekly digest generation, history media enrichment |

### Cinematic Division

| Agent | Purpose | Write Access | Trigger |
|-------|---------|-------------|---------|
| `cinematographer` | Camera language design — depth of field, rack focus, parallax, camera movements, scene compositions, cinematic design tokens | Yes | Cinematic overhaul, motion design tasks |
| `vfx-artist` | Post-processing — film grain, color grading, vignettes, lens effects, atmospheric lighting, texture via CSS filters and SVG | Yes | After cinematographer, cinematic polish |
| `motion-director` | Scroll-driven choreography — scene timelines, gesture physics, transition sequencing, L-cut/match-cut timing, scroll-timeline API | Yes | After cinematographer, interaction choreography |
| `color-grader` | Per-image CSS color grading — external source normalization, page-specific filter pipelines (weekly magazine warmth, history archival sepia, feed cinematic amber), grain/vignette compositing on image containers | Yes | After media-curator + vfx-artist, image visual consistency |

### History Division

| Agent | Purpose | Write Access | Trigger |
|-------|---------|-------------|---------|
| `history-curator` | Event selection, research coordination, YAML content authoring, era/region taxonomy | Yes | New event onboarding, content expansion |
| `perspective-analyst` | Multi-perspective balance, 5-lens historiographic framework (Geographic/National, Social Position, Temporal Frame, Causal Emphasis, Evidentiary Base), viewpoint gap analysis | Yes | After event draft, perspective audit |
| `historiographic-auditor` | Accuracy validation, source verification, bias detection in historical narratives, visual bias checks | No | Before publishing, CEO spot-check |
| `media-archaeologist` | Primary source discovery, historical media curation, rights verification, provenance tracking | Yes | Visual asset curation, new event media |
| `timeline-architect` | Event connection mapping, chronological accuracy, timeline data structure, cross-event relationships | Yes | Timeline construction, connection discovery |
| `narrative-engineer` | Prose polish, show-don't-tell enforcement, narrative flow, multi-perspective coherence | Yes | Final content polish before publish |

### History Visual Division

| Agent | Purpose | Write Access | Trigger |
|-------|---------|-------------|---------|
| `visual-historian` | Archival Cinema design implementation, Ken Burns effects, page layouts, component styling | Yes | After cinematographer, UI implementation |
| `archive-cartographer` | Geographic visualization, map layers, region/era spatial data, MapView component | Yes | Map features, geographic context |

### Agent Engineering Division

| Agent | Purpose | Write Access | Trigger |
|-------|---------|-------------|---------|
| `agent-architect` | Audits, optimizes, and designs all agents. Reviews definitions for best-in-class tooling, cost efficiency, prompt engineering. Builds new agents on CEO demand. | Yes (agent definitions only) | CEO request, post-major-change review, periodic fleet audit |

### Security Division

| Agent | Purpose | Write Access |
|-------|---------|-------------|
| `void-ciso` | Secrets, RLS, CORS, injection, OWASP, dependencies | No |

### Product Division

| Agent | Purpose | Write Access |
|-------|---------|-------------|
| `ceo-advisor` | Strategic counsel — roadmap, competitive positioning | No |

### Branding Division

| Agent | Purpose | Write Access |
|-------|---------|-------------|
| `logo-designer` | Brand identity — logo, favicon, SVG assets, cinematic palette, texture system | Yes |

---

## Sequential Cycles

**Quality Cycle:**
```
pipeline-tester → bug-fixer → pipeline-tester (retest)
```

**Bias Audit Cycle:**
```
analytics-expert → bias-auditor → nlp-engineer → pipeline-tester
```

**Bias Calibration Cycle:**
```
nlp-engineer → bias-calibrator → bias-auditor → pipeline-tester
```

**Frontend Cycle:**
```
frontend-builder → responsive-specialist → uat-tester → frontend-fixer
```

**Audio Quality Cycle:**
```
audio-engineer → pipeline-tester → bug-fixer
```

**Cinematic Overhaul Cycle:**
```
[logo-designer + cinematographer] (parallel) → motion-director → vfx-artist → color-grader → frontend-builder → [responsive-specialist + perf-optimizer] (parallel) → uat-tester → frontend-fixer
```

**Full Pipeline Dev Cycle:**
```
feed-intelligence → nlp-engineer → pipeline-tester → bug-fixer → pipeline-tester
```

**Weekly Media Cycle:**
```
weekly_digest_generator (cover stories selected) → media-curator (source cover image) → frontend-builder (render in WeeklyDigest.tsx)
```

**History Media Cycle (updated):**
```
media-archaeologist (archival) → media-curator (modern supplemental) → historiographic-auditor (visual bias) → visual-historian (integration)
```

**History Research Cycle:**
```
history-curator → [perspective-analyst + media-archaeologist] (parallel) → historiographic-auditor → narrative-engineer
```

**History Publishing Cycle:**
```
narrative-engineer → historiographic-auditor → [cinematographer + motion-director + vfx-artist] (cinematic trio) → visual-historian → frontend-builder → uat-tester
```

**History QA Cycle:**
```
[historiographic-auditor + perspective-analyst] (parallel audit) → perspective-analyst (fixes) → historiographic-auditor (re-validate) → uat-tester
```

---

## Agent Routing Rules

| Task Pattern | Agent | Division |
|---|---|---|
| RSS feed health, article collection, deduplication, cluster summaries, content quality | `feed-intelligence` | Pipeline |
| Bias score accuracy, calibration, benchmarking | `analytics-expert` | Quality |
| Ground-truth validation, known-outlet comparison | `bias-auditor` | Quality |
| Bias score regression, validation suite, weight tuning | `bias-calibrator` | Quality |
| Pipeline output validation, clustering quality | `pipeline-tester` | Quality |
| Post-test bug fixing | `bug-fixer` | Quality |
| Pipeline runtime, frontend load, Lighthouse | `perf-optimizer` | Infrastructure |
| Article/cluster data quality, NULL audits | `db-reviewer` | Infrastructure |
| Sync docs with codebase | `update-docs` | Infrastructure |
| Build UI components, new features | `frontend-builder` | Frontend |
| Fix UI bugs, layout breaks, a11y gaps | `frontend-fixer` | Frontend |
| Desktop/mobile layout, responsive issues | `responsive-specialist` | Frontend |
| Browser testing, click-through QA | `uat-tester` | Frontend |
| spaCy models, bias scoring algorithms, NER | `nlp-engineer` | Pipeline |
| Source vetting, RSS config, credibility | `source-curator` | Pipeline |
| Bias lexicon research, vocabulary gap analysis | `linguist` | Pipeline |
| Broadcast audio, sonic branding, TTS voice, audio post-processing | `audio-engineer` | Audio |
| Security audit, secrets scan, RLS, OWASP | `void-ciso` | Security |
| Strategic advice, roadmap, priorities | `ceo-advisor` | Product |
| Logo, favicon, brand identity, cinematic palette, texture system | `logo-designer` | Branding |
| Camera movement, depth of field, parallax, cinematic scene composition | `cinematographer` | Cinematic |
| Film grain, color grading, vignette, lens effects, atmospheric post-processing | `vfx-artist` | Cinematic |
| Scroll-driven choreography, scene timelines, gesture physics, transition sequencing | `motion-director` | Cinematic |
| Per-image color grading, CSS filter pipelines for external images, page-specific media grades | `color-grader` | Cinematic |
| Agent audit, optimization, new agent design, prompt engineering | `agent-architect` | Agent Engineering |
| Historical event research, YAML content, era/region taxonomy | `history-curator` | History |
| Multi-perspective balance, historiographic framework, viewpoint gaps | `perspective-analyst` | History |
| Historical accuracy validation, source verification, narrative bias | `historiographic-auditor` | History |
| Primary source discovery, historical media, rights/provenance | `media-archaeologist` | History |
| Free-API image sourcing for weekly/history (Wikimedia, Unsplash, Pexels) | `media-curator` | Pipeline |
| Event connections, timeline data, chronological accuracy | `timeline-architect` | History |
| Narrative polish, show-don't-tell, multi-perspective coherence | `narrative-engineer` | History |
| Archival Cinema UI, Ken Burns effects, history page layouts | `visual-historian` | History Visual |
| Geographic visualization, map layers, region/era spatial data | `archive-cartographer` | History Visual |

---

## Parallel Safety

**Can run simultaneously (read-only):** `pipeline-tester`, `db-reviewer`, `void-ciso`, `ceo-advisor`, `uat-tester`, `historiographic-auditor`

**Never run simultaneously:** Two write agents on overlapping files; `bug-fixer` + `pipeline-tester`; `frontend-builder` + `frontend-fixer`.

---

## Locked Decisions (Require CEO Approval)

- Cinematic Press design system (4-voice type, BiasLens Three Lenses, newspaper grid + cinematic tokens)
- 6-axis bias scoring model (political lean, sensationalism, opinion/fact, factual rigor, framing + confidence)
- Supabase as single data layer
- Static export (Next.js → GitHub Pages)
- 1,013-source curated list (3 tiers: 43 us_major, 373 international, 597 independent); 7-point political lean spectrum; 158 countries
- $0 operational cost constraint
- Claude Max CLI for all agent work; Gemini Flash free tier only for pipeline summarization

---

## Future Expansion

R&I advisory agents (read-only, propose but don't implement):

| Agent | Purpose |
|-------|---------|
| `data-storytelling-designer` | Bias visualization, chart design |
| `micro-interaction-designer` | Progressive disclosure, delight |
| `accessibility-inclusivity-lead` | WCAG 2.1 AA compliance |

Note: `motion-physics-designer` was promoted to three active agents: `cinematographer`, `motion-director`, `vfx-artist` (Cinematic Division, rev 12).

---

## Session Log (Major Changes)

| Date | Key Changes |
|------|-------------|
| 2026-03-19 | First agent chain run: bias fixes, Gemini Voice arch, parallelization, favicon/OG, responsive |
| 2026-03-20 | Ranking v3.3 (9 signals, bias-blind); Clustering v2 (entity-merge); multi-section editions |
| 2026-03-21 | Ranking v5.1 (Gemini editorial); Deep Dive redesign; Daily Brief + audio pipeline; bias calibration (all 5 axes); validation framework (26 fixtures, 96.9%) |
| 2026-03-22 | Gemini TTS migration (replaced edge-tts + GCloud); Vol I reset (370 sources, 4,839 articles, 108 min); perf optimizations |
| 2026-03-29 | Cinematic Division added (cinematographer, motion-director, vfx-artist); 20→23 agents, 9→10 divisions; Cinematic Press v2 design tokens; source expansion 370→409 |
| 2026-03-31 | Source review: 11 broken RSS feeds fixed, 13 right-spectrum sources added, L:R 1.82:1→1.54:1; 409→419 sources |
| 2026-04-02 | Major source expansion: 419→951 sources (+532), 77→155 countries, L:R 1.54:1→1.16:1; India→South Asia rename; new Europe edition; 38 wire services, 10 fact-checkers; US regional metros + specialty/beat press added |
| 2026-04-03 | Source expansion 951→1,013 (EU +49, SA +27); ranking v5.7/v5.8 edition-unique (regional affinity 1.5x, local-priority, cross-edition demotion, thin-edition backfill); migrations 030-036; linguist agent added; weekly digest; Deep Dive FLIP morph animation; 24 agents, 11 divisions |
| 2026-04-04 | void --history ("The Archive"): multi-perspective historical events platform, Archival Cinema design, 19 components, 5-lens historiographic framework, 25 events (100 perspectives, 218 media), migrations 039+043 (4 history tables), pipeline/history (content_loader, image_enricher, mirror_images, source_enricher), 8 new agents (history-curator, perspective-analyst, historiographic-auditor, media-archaeologist, timeline-architect, narrative-engineer, visual-historian, archive-cartographer), 6 history workflows; 32 agents, 13 divisions |
| 2026-04-05 | color-grader + media-curator agents added to Cinematic Division; per-image CSS filter grading pipeline for external media (Weekly cover, History archival, Deep Dive); cinematic overhaul cycle updated; ranking v6.0 (10 signals, lean_diversity merged into perspective_diversity, divergence purified, edition_ranker.py extracted, holistic re-rank step 8c); 34 agents, 13 divisions |
