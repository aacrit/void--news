# void --news

Last updated: 2026-03-28 (rev 13)

> **Read this file first. Only read other docs when task-relevant. Only open source files when modifying code.**

A modern news aggregation platform with per-article, 6-axis rule-based NLP bias analysis. Every source is curated for credibility. Covers World, US, and India editions.

## Architecture

```
GitHub Actions (4x daily cron) → Python Pipeline → Supabase (PostgreSQL) ← Next.js Static Site (GitHub Pages)
```

- **No backend server.** Fully serverless.
- **Python pipeline** runs on GitHub Actions, handles ingestion, NLP analysis, writes to Supabase.
- **Next.js frontend** is statically exported, hosted on GitHub Pages, reads Supabase client-side.
- **Supabase** is the single data layer: articles, bias scores, source metadata, story clusters.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Ingestion | Python, feedparser, BeautifulSoup/Scrapy |
| NLP/Bias Engine | Python, spaCy, NLTK, TextBlob |
| Summarization | Gemini 2.5 Flash (free tier, google-genai SDK) |
| Audio | Gemini 2.5 Flash TTS (native multi-speaker, free tier, $0), pydub |
| Database | Supabase (PostgreSQL) |
| Frontend | Next.js 16 (App Router), React 19, TypeScript |
| Animation | Motion One v11 (spring physics, ~6.5KB CDN) |
| Styling | CSS custom properties, mobile-first, clamp() |
| Fonts | Playfair Display (editorial), Inter (structural), Barlow Condensed (meta), IBM Plex Mono (data) |
| Hosting | GitHub Pages (frontend), GitHub Actions (pipeline) |

## Core Principles

### Show, Don't Tell — The Cardinal Rule

Every piece of generated text in void --news — summaries, TL;DR, opinion, audio scripts — MUST embody show-don't-tell writing. This is non-negotiable and applies to all prompts, all output, all future development.

**What this means:**
- Never assert significance. Show the evidence that makes significance self-evident.
- Never say "this is important" — place facts side by side so the reader realizes it themselves.
- Never use "notable," "significant," "it should be noted," "interestingly," "crucially" — these are crutch words that TELL instead of SHOW.
- Juxtapose concrete facts to reveal patterns. "Three central banks moved in the same direction. Two did so despite domestic pressure. The third didn't have a choice." — the reader sees the pattern without being told.
- Use specific numbers, names, dates, actions. Abstraction is the enemy of show-don't-tell.
- The opinion section shows hidden patterns by placing facts next to each other — never by declaring a conclusion.

**BAD:** "It is worth noting that tensions are rising significantly between the two nations."
**GOOD:** "Both countries recalled their ambassadors within 48 hours. Neither has done that since 1979."

This principle applies to: `cluster_summarizer.py` prompts, `daily_brief_generator.py` prompts, `claude_brief_generator.py` prompts, and any future content generation. When reviewing or modifying prompts, enforce this standard.

### Product Family Branding

CLI-style naming convention — every feature is a command the user runs. Transparent, no mystery.

| Brand | English Subtitle | Purpose |
|-------|-----------------|---------|
| `void --news` | — | The platform |
| `void --tl;dr` | The Daily Brief | Top stories, editorially weighed |
| `void --onair` | Audio Broadcast | Two-voice BBC-style news conversation |
| `void --opinion` | The Board | Observational editorial judgment |
| `void --sources` | Source Spectrum | 370 outlets on one axis |
| `void --deep-dive` | Story Analysis | Per-story bias breakdown |
| `void --paper` | Broadsheet Edition | E-paper reading experience |

English subtitles appear on first encounter (sessionStorage) then fade. The CLI aesthetic signals transparency and anti-marketing — users are querying, not passively consuming. Extended branding should follow this pattern for any new feature.

### Zero Operational Cost
- No paid APIs. All bias analysis is rule-based NLP running locally.
- Gemini 2.5 Flash free tier: ~116 RPD used (7.7% of 1500 RPD limit). 4x daily runs × ~26 cluster calls + 5 brief calls per run.
- Gemini 2.5 Flash TTS: free tier ($0), same GEMINI_API_KEY as summarization. LLM-native multi-speaker dialogue synthesis in a single API call. No per-turn stitching needed.
- GitHub Actions, Supabase, GitHub Pages — all free tier.
- Motion One via CDN importmap (no npm install needed).

### Bias Analysis — The Differentiator
Per-article analysis across 6 axes. Axes 1-5 return score (0-100) + structured rationale dict (JSONB) for frontend hover display. Axis 6 tracks longitudinal trends per source per topic.

1. **Political Lean** — keyword lexicons (90+ terms per side), entity sentiment (spaCy NER + TextBlob), framing phrases, length-adaptive + sparsity-weighted source baseline blending. Blending: `<50w → 0.50/0.50`, `50-150w → 0.70/0.30`, `150-500w → 0.85/0.15`, `500+w → 0.90/0.10`. Sparsity override: when ≤3 distinct keywords found, baseline weight increases further (up to 0.8× of available slack) — a Fox article with zero keyword hits scores ~75 not 53. Short-article divergence guard: when `<150w` and text diverges `>30pts` from baseline, baseline weight floors at 0.60. State-affiliated outlets (RT, CGTN, Sputnik, CGTN): baseline weight floors at 0.30 regardless of length. Optional `topic_lean_data` from Axis 6 EMA blends into prior: `source_baseline = baseline×0.7 + topic_avg×0.3`. Figures added to entity lists: Trump/Soros/Musk (RIGHT), Biden/Sanders/AOC/Harris (LEFT). "critics say"/"some argue"/"many believe" framing weights: 0.05 each (reduced from 0.3/0.1/0.1). "crisis at the border" moved from LEFT to RIGHT framing. Rationale: top left/right keywords, framing phrases, entity sentiments.
2. **Sensationalism** — headline clickbait patterns, superlative/urgency density (word-boundary regex, no substring hits), TextBlob extremity, short-sentence ratio, partisan attack phrase density (capped at 30pts, was 50pts), measured-phrase inverse. Rationale: headline_score, body_score, clickbait_signals, partisan_attack_density.
3. **Opinion vs. Reporting** — first-person pronouns (excludes all-caps "US" country code), TextBlob subjectivity (weight 0.18, reduced from 0.22), modal language, hedging, attribution density (includes 14 investigative sourcing patterns: "a review of", "obtained by", "documents show", etc.), absolutist assertion density (state-media correction), value judgment score (weight 0.06, restored from 0.02; denominator is total_judgments not sentence count), metadata markers, rhetorical questions. Rationale: 8 sub-scores, classification label, dominant signals.
4. **Factual Rigor** — named source counting (spaCy NER near attribution verbs, ±120 char window), organization citations (requires ORG_CITATION_PATTERNS or verb within 80 chars; normalizes "the " prefix), data patterns, direct quotes, attribution specificity (SPECIFIC_ATTRIBUTION regex requires verb within ±150 chars — prevents biographical mentions), 8 vague-source phrases added, direct vague-source penalty up to -15pts. Tier baselines: `us_major=65`, `international=55`, `independent=50`. LOW_CREDIBILITY_US_MAJOR frozenset (22 slugs: Breitbart, Newsmax, Daily Wire, Daily Caller, Gateway Pundit, Infowars, OANN, NY Post, Daily Mail, Occupy Democrats, Palmer Report, Daily Kos, Raw Story, etc.) receives baseline 35 instead of 65. Rationale: named_sources_count, data_points_count, direct_quotes_count, vague_sources_count, specificity_ratio.
5. **Framing Analysis** — connotation analysis, charged synonym detection (50+ pairs; word-boundary regex for single-word terms), omission detection (one-sided sourcing + cross-article entity comparison; cluster entity cache excludes current article's own entities), headline-body divergence, passive voice ratio (capped at 30, was ~80). "killed" intensity 3→1, "invasion" intensity 3→1 (AP wire false positive fixes). Rationale: 5 sub-scores + has_cluster_context flag.
6. **Per-Topic Per-Outlet Tracking** — Adaptive EMA: alpha=0.3 for new series (<10 articles), alpha=0.15 for established series (≥10 articles). Category normalized to lowercase before grouping. Wired to `analyze_political_lean` via `topic_lean_data` parameter but dormant until categorization moves before step 5. Stored in `source_topic_lean`. Updated at step 9c.

No LLM API calls for scoring. Confidence computed per-article: text length + availability + signal strength.

### Bias Engine Validation Framework (`pipeline/validation/`)

Ground-truth test suite for regression-safe bias engine development.

| File | Purpose |
|------|---------|
| `fixtures.py` | 26 ground-truth articles across 8 categories (wire, opinion, investigative, partisan_left, partisan_right, state_media, breaking, analysis) with expected score ranges + rationale |
| `signal_tracker.py` | Per-signal decomposition — `decompose_lean`, `decompose_sensationalism`, `decompose_opinion`, `decompose_rigor`, `decompose_framing`, `detect_dead_signals` |
| `source_profiles.py` | AllSides cross-reference alignment — maps AllSides ratings to expected lean ranges per article |
| `runner.py` | Validation runner; distribution health checks, directional invariants, regression snapshots; 96.9% accuracy on first run |
| `snapshot.json` | Regression baseline snapshot |

**Run it:**
```bash
cd /home/aacrit/projects/void-news
python pipeline/validation/runner.py              # Full validation
python pipeline/validation/runner.py --quick      # Skip distribution checks
python pipeline/validation/runner.py --verbose    # Per-signal decomposition
python pipeline/validation/runner.py --json       # JSON output for CI
python pipeline/validation/runner.py --update-snapshot  # Refresh regression baseline
python pipeline/validation/runner.py --category wire    # Single category
```

Requires `spaCy en_core_web_sm`. Designed for CI integration (exits non-zero on regression); CI gate via `.github/workflows/validate-bias.yml`. Run after any bias engine change.

### Importance Ranking — v5.3

**Ranking is BIAS-BLIND.** Bias analysis belongs in the display layer, not story selection.

11-signal formula in `pipeline/ranker/importance_ranker.py`. Deterministic weights sum to 1.0:

| Signal | Weight | Notes |
|--------|--------|-------|
| Source coverage breadth | 20% | Tier-weighted: independent 1.5x, international 1.2x, us_major 1.0x |
| Story maturity | 16% | recency × log2(1 + source_count); rewards "recent AND thoroughly reported" |
| Tier diversity | 13% | Composition-aware; us_major presence explicitly rewarded |
| Consequentiality | 10% | Outcome/action verbs + high-authority phrase floor (70+) |
| Institutional authority | 8% | Heads of state, supreme courts, central banks, UN Security Council |
| Factual density | 8% | Avg factual rigor; gate: <30 → 0.88x |
| Divergence | 7% | Framing-weighted (50% framing, 30% sensationalism, 20% lean); US-only → 0.85x damper |
| Perspective diversity | 6% | Editorial viewpoint spread; bias-blind |
| Geographic impact | 6% | G20/P5 nations score 3x |
| Coverage velocity | 3% | Sources added in last 6h; diminishing returns |
| Lean diversity | 3% | Whether left+right BOTH cover the story |

**Gemini editorial importance** (v5.0): When available, 1-10 editorial score applies additive adjustment (+/-6.7 pts max). ei=10 -> up to +10 pts; ei=1 -> up to -5 pts; ei~5 -> neutral. Deterministic base is never scaled down.

**v5.1 additions**: US-only divergence damper (0.85x); cross-spectrum interest bonus (+2.5 pts max when genuine left-right split across 3+ articles, non-US clusters only).

**v5.3 additions**: Lean diversity signal (3%, from velocity 6%->3%); longevity penalty for old stories.

Tier diversity scoring:

| Tier combination | Score |
|-----------------|-------|
| all 3 tiers | 100 |
| us_major + international | 80 |
| us_major + independent | 70 |
| us_major alone | 50 |
| international + independent | 50 |
| international alone | 30 |
| independent alone | 15 |

Gates and modifiers:
- **Confidence multiplier**: `0.65 + 0.35 * conf` (soft curve)
- **Consequentiality gate**: consequentiality < 5 → 0.82x
- **Soft-news gate**: sports/entertainment/culture/lifestyle → 0.78x
- **Low factual rigor gate**: avg factual_rigor < 30 → 0.88x
- **Lead eligibility gate**: top 10 per-section require 3+ sources; exception: independent investigative exclusives (factual_rigor > 70)
- **Topic diversity re-rank**: max 2 per hard-news category, max 1 per soft-news in top 10 per section pool
- **Cross-edition demotion**: top-5 in primary section demoted below pos 5 in secondary sections
- **Same-event cap**: max 3 per event (Iran/Ukraine/Gaza/Taiwan)
- **Deliberation dampener**: 0.7x for "considers"/"weighs"/"discusses"
- **Tier concentration penalty**: 0.85x when >70% same tier

`pipeline/rerank.py` — standalone re-ranker without full pipeline run. Source map keyed by slug + db_id (UUID).

### Cluster Summarization (Gemini Flash)
3+-source clusters only, processed descending source-count. Hard cap: **25 API calls per run** (4 runs/day = 100 RPD for cluster summaries + reasoning budget). Summaries: 250-350 words. `max_output_tokens=8192`. Falls back to rule-based when unavailable or cap reached.

**Gemini Voice** (`cluster_summarizer.py`): `_SYSTEM_INSTRUCTION` (editorial role) + `_USER_PROMPT_TEMPLATE` per cluster. `_PROHIBITED_TERMS` frozenset (26 terms) + `_check_quality()` validator enforce output. Source names used directly (not tier labels — per feedback). `generate_json()` in `gemini_client.py` accepts optional `system_instruction` (backward-compatible).

**Op-eds** (opinion_fact > 50): No clustering, no Gemini. Single-article clusters using original text/headline. Author/pub shown only if available.

### Daily Brief — "void --onair"
One world-focused brief generated per run, drawing from the top 20 clusters globally (all editions). Stored in `daily_briefs` table; old briefs pruned to keep latest per edition.

**TL;DR** (`tldr_text`): 8-12 sentences as a flowing editorial paragraph (150-220 words). Written as a joint editorial board voice — expert writers from left, center, and right. Opinionated about significance, neutral on partisanship. Writes about the world, never about coverage patterns or media behavior. Displayed between FilterBar and Lead Section on homepage. Fetched as "world" brief regardless of active edition.

**Opinion** (`opinion_text`): 3-5 sentences (80-120 words) from "The Board." Genuinely opinionated editorial judgment in first person plural ("we"). Where the TL;DR says what happened, the opinion says what the board thinks about it. Italic Playfair Display, fg-primary color, text-md size. Separated from TL;DR by 2px dotted editorial firewall rule. Desktop: always visible. Mobile: hidden behind "Read more · The Board" toggle (3-line clamp). Same Gemini API call as TL;DR — $0 extra cost.

**Audio broadcast** (`audio_script` + `audio_url`): BBC World Service 1970s two-host radio format. Host A (anchor) delivers facts; Host B (analyst) adds context/divergence. Script uses `[MARKER]` structural delimiters + `A:`/`B:` speaker tags. **Gemini 2.5 Flash TTS** (`gemini-2.5-flash-preview-tts`) generates both speakers in a single API call with LLM-native prosody, natural turn-taking, and conversational rhythm — no per-turn synthesis or stitching needed. Script converted to `One:`/`Two:` dialogue format, artifacts stripped. PCM 24kHz output → pydub post-processing (Glass & Gravity sonic identity: D major 9th bloom intro, glass-bell story transitions, resolving outro; no background bed) → MP3 192k mono → Supabase Storage `audio-briefs` bucket (`{edition}/latest.mp3`).

**Voice pairs** (`pipeline/briefing/voice_rotation.py`): Gemini prebuilt voices. world=Charon/Aoede, us=Enceladus/Kore, india=Puck/Leda. Roles swap on alternate days (UTC day-of-year parity). 30 voices available.

**Gemini budget**: 5 calls/run (one per edition, supports all 5 editions). Uses `count_call=False` — does not consume 25-call cluster summarization cap. Falls back to rule-based TL;DR (top 5 cluster titles) when Gemini unavailable. No audio without Gemini script.

**Claude CLI premium scripts** (`pipeline/briefing/claude_brief_generator.py`): Optional manual 1x/day generation via `python -m pipeline.briefing.claude_brief_generator --edition world --model sonnet`. Uses Claude Max (Sonnet/Opus) for higher-quality conversational dialogue. Enhanced disfluency prompt addendum for natural speech patterns. Stores to Supabase, overwrites current brief for edition.

**Audio cadence**: currently always-on (testing mode). Production target: 2x/day (morning + evening UTC).

### Source Curation
380 vetted sources in three tiers:
- **Major US (49)** — AP, Reuters, NYT, WSJ, WaPo, Fox, CNN, NPR, PBS, Bloomberg, Breitbart, Newsmax, Daily Wire, etc.
- **International (158)** — BBC, Al Jazeera, DW, France24, The Guardian, NHK, Yonhap, TRT World, RT, CGTN, etc.
- **Independent/Nonprofit (173)** — ProPublica, The Intercept, Bellingcat, The Markup, RealClearPolitics, The Free Press, Epoch Times, etc.

7-point lean spectrum: far-left, left, center-left, center, center-right, right, far-right. Left:Right ratio 1.93:1 (116 left : 60 right : 204 center).

**Editions**: world (default), us, india. Source country determines edition (IN→india, US→us, else→world). Source counts: US=150, World=210, India=20.

## Pipeline Flow (4x Daily)

```
 1.  LOAD SOURCES  — 380 sources from data/sources.json, sync to Supabase
 2.  PIPELINE RUN  — Create pipeline_runs record
 3.  FETCH         — RSS feeds from 380 sources (parallel)
 4.  SCRAPE        — Full text via web scraper (30 workers), RSS summary fallback
 4b. DEDUPLICATE   — TF-IDF + cosine similarity (threshold 0.80), Union-Find grouping
 5.  ANALYZE       — 5-axis bias scoring (all return score + rationale)
 6.  CLUSTER       — Phase 1: TF-IDF agglomerative (threshold 0.2, doc length 500 words)
                     Phase 2: entity-overlap merge pass (3+ shared entities, 48h window)
 6b. RE-FRAME      — Framing re-run with cluster context (omission detection)
     ORPHANS       — Unclustered articles wrapped as single-article clusters
 6c. GEMINI REASON — Contextual score adjustments on low-confidence/high-divergence clusters (25-call budget); mutates article_bias_map
 7b. SUMMARIZE     — Gemini: 250-350 word briefings + consensus/divergence + editorial_importance (1-10); 3+-source clusters, 25-call cap
 7.  CATEGORIZE & RANK — Topic tagging (3-article majority vote) + v5.3 ranking (11 signals + optional Gemini importance); topic diversity re-rank
 7c. EDITORIAL TRIAGE  — Gemini reorders top 30 per section using editorial_importance when available
 7d. DAILY BRIEF   — Gemini generates 1 world-focused TL;DR (5-7 sentences) + two-host BBC-style audio script (5-call budget, separate from 25-call cap); Gemini 2.5 Flash TTS synthesizes native multi-speaker dialogue in single API call; pydub post-processing (Glass & Gravity: bloom intro, glass-bell transitions, resolving outro) → MP3 192k mono; uploaded to Supabase Storage `audio-briefs`; stored in `daily_briefs` table. Non-audio runs (00:00, 12:00 UTC) carry forward audio fields (audio_url, audio_script, audio_duration) from the previous brief so audio is never buried by text-only updates.
 8.  STORE         — Write clusters; sections[] array from all editions covered
 8b. DEDUP CLUSTERS — Delete old clusters whose articles overlap any new cluster (any shared article → old cluster is stale); prevents duplicate story clusters across pipeline runs
 9.  ENRICH        — Cluster-level bias aggregation, consensus/divergence points
 9b. ARTICLE CATS  — Populate article_categories junction table
 9c. TOPIC TRACK   — Axis 6 EMA update (source_topic_lean)
10.  TRUNCATE      — full_text → 300-char excerpts (IP compliance)
     CLEANUP       — cleanup_stale_clusters + cleanup_stuck_pipeline_runs RPCs; old daily_briefs (keep latest per edition)
```

## Frontend Design

### Design Philosophy — "Press & Precision"
Modern newspaper aesthetic. Serif headlines, editorial layout sensibility. **Clean on arrival, data-dense on interaction.** Progressive disclosure is the core interaction pattern. 1920s low-tech aesthetic: space-efficient, enriched only on user interaction.

Adapted from DondeAI's "Ink & Momentum": spring physics for user-initiated actions, ease-out for system reveals.

### Four Voices of Type

| Voice | Font | Use For |
|-------|------|---------|
| Editorial | Playfair Display | Headlines, story titles, section headers |
| Structural | Inter | Body text, labels, navigation, buttons |
| Meta | Barlow Condensed | Category tags, source counts, timestamps, edition metadata (Franklin Gothic / News Gothic newspaper tradition) |
| Data | IBM Plex Mono | Bias scores, numeric data (humanist monospace; institutional warmth, not a coding font) |

CSS variable: `--font-meta` (Barlow Condensed). IBM Plex Mono replaces JetBrains Mono for data display.

### Responsive Strategy — One Project, Two Layouts

| Aspect | Desktop | Mobile |
|--------|---------|--------|
| Layout | Multi-column newspaper grid | Single-column feed, bottom sheet |
| Story cards | Horizontal, inline bias indicators | Vertical stack, indicators below headline |
| Deep Dive | Centered popup (75vw, max 920px–1080px, 80vh), cinematic shadow, backdrop blur 6px | Full-screen bottom sheet, blur 2px |
| Navigation | Top nav bar | Bottom nav bar (thumb-reachable) |
| Data density | High — more metrics at a glance | Progressive — tap to reveal |

Shared: component logic, Supabase queries, animation system, color system, accessibility (WCAG 2.1 AA).

Mobile rules:
- Edge padding: `--space-5` (~16px) on `.page-main`, `.nav-inner`, `.site-footer`
- `overflow-wrap: break-word` on all headline elements
- `.section-header` and Deep Dive source rows: `flex-wrap: wrap`
- Touch targets ≥ 44×44px

### Two Core Views

#### 1. Homepage — News Feed
- Importance-ranked story flow. Auto-generated category tags for filtering.
- Each card: headline, source count, key bias indicators (BiasLens).
- "Last updated" timestamp + Refresh button (confirmation dialog).
- Sections: World / US / India.
- **Daily Brief** (`DailyBriefText`): displayed between FilterBar and Lead Section. Full-width, on-canvas. TL;DR in Inter regular with blockquote left-border (newspaper editorial aside tradition), justified text, top/bottom rules. Opinion ("The Board") always visible on desktop; separated by 2px dotted editorial firewall rule; italic Playfair Display. "void --onair" pill (right-aligned) with ScaleIcon (analyzing animation when playing); progress bar fills as audio plays. Mobile: body collapses to 3 lines with "Read more · The Board" toggle (opinion hidden). Always fetches world brief regardless of active edition.

#### 2. Deep Dive Dashboard
- Centered popup overlay (desktop: 75vw, max-width 920px–1080px, 80vh, cinematic shadow; mobile full-screen from bottom).
- **Summary as lede**: no "What happened" heading; flows as article lede. Viewport-responsive height (`clamp(12em, 25vh, 22em)`); "Read more" overflow detected via ResizeObserver (not character count). Gradient overlay hidden when content fits (`dd-collapsible--fits` class).
- **`dd-analysis-row`**: Sigil + `DeepDiveSpectrum` (7-zone gradient bar, logos positioned continuously at their exact lean %, nearby sources use 3-row algorithm for dense clusters, no max-height cap, "+N more" expand button when >6 sources) + "Press Analysis ▶" trigger in one flex row (desktop); stacked vertically (mobile). Zone labels smaller font on mobile.
- **Press Analysis**: collapsed behind ▶ trigger; expands via `grid-template-rows 0fr→1fr`; opens `BiasInspectorInline` (4-axis scorecard: Lean, Sensationalism, Factual Rigor, Framing; each axis collapsible with Gemini reasoning text). Expand panel: max-height 60vh with overflow-y scroll.
- **Source Perspectives**: Agreement | Divergence in 2-column grid (desktop); single column (mobile). Green left borders = agree, red = diverge.
- Action buttons: WCAG 44×44px touch targets.
- **Popup open animation**: `var(--spring-bouncy)` 500ms with genuine overshoot. **Close**: `var(--spring-snappy)` 380ms. Asymmetric: slow open, fast close.
- Slot-machine cascade: `translateY(12px) → 0`. Desktop: content reveal 180ms delay (was 400ms). Mobile: `opacity 150ms ease-out, transform 250ms ease-out` (no spring), reveal delay 30ms. rAF snap uses `setTimeout(0)` for 90/120Hz reliability.
- Panel flash prevention: CSS `opacity:0` on `.deep-dive-panel` + JS asymmetric opacity transition; fallback 200ms opacity ramp.
- iOS bottom-sheet: `border-radius: 16px 16px 0 0`, drag indicator, momentum scroll, safe-area insets.

### Interaction Model
- **On arrival**: clean, minimal, newspaper-like.
- **On interaction**: rich data layers reveal via hover/click/tap.
- Progressive disclosure throughout. Unified interaction: Press Analysis and lean spectrum details use the same system.

## Animation System

**Motion One v11** via CDN importmap (~6.5KB).

### Spring Presets

| Preset | Stiffness | Damping | Mass | Use Case |
|--------|-----------|---------|------|----------|
| snappy | 600 | 35 | 1 | Buttons, toggles, filter chips; Deep Dive close (380ms) |
| smooth | 280 | 22 | 1 | Cards, panels, story expansion |
| gentle | 150 | 12 | 1.2 | Page transitions, view switches |
| bouncy | — | — | — | Deep Dive open (500ms, genuine overshoot); `--spring-bouncy` token |

### Duration Tokens

```css
--dur-instant: 0ms; --dur-fast: 150ms; --dur-normal: 300ms;
--dur-morph: 400ms; --dur-step: 450ms; --dur-slow: 600ms;
```

### Easing Curves

```css
--ease-out: cubic-bezier(0.16, 1, 0.3, 1);  /* Apple-sharp deceleration */
--ease-in:  cubic-bezier(0.4, 0, 1, 1);     /* Use sparingly */
/* --spring: linear(/* damped oscillation */) — defined in tokens.css */
```

### Rules
- GPU-only: animate transform + opacity only.
- Accessible: all → 0ms under `prefers-reduced-motion`.
- Asymmetric for panels: open uses `--spring-bouncy` (500ms, overshoot), close uses `--spring-snappy` (380ms, tight). Symmetric for micro-interactions (chips, toggles).
- Interruptible: no animation locks.
- Max 3 simultaneous springs, 60fps target. rAF snap via `setTimeout(0)` for 90/120Hz reliability.

## CSS Architecture

Load order: `reset.css → tokens.css → layout.css → typography.css → components.css → animations.css → responsive.css` (split into `frontend/app/styles/`; `globals.css` is the entry point via `@import`).

- CSS custom properties only (no Sass/LESS). BEM-like naming. Mobile-first `min-width` queries.
- `clamp()` for all fluid scaling. No `!important`.
- Body text (story summaries, lead story, Daily Brief): `text-align: justify; hyphens: auto` — newspaper norm.
- Sticky `.filter-row` uses `background-color: var(--bg-primary)` (opaque) to prevent text bleed-through on scroll.
- `overflow-x: hidden` on `.page-container`; `min-width: 0` on all CSS Grid children to prevent blowout from long headlines.

Breakpoints: 375px (mobile), 768px (tablet), 1024px (desktop), 1440px (wide).

## Data Model (Supabase)

### Key Tables
- `sources` — outlet metadata, RSS/scrape config, tier, slug, 7-point lean baseline
- `articles` — 300-char excerpt (truncated post-analysis), metadata, source_id, publish_date, url, section, updated_at
- `bias_scores` — per-article multi-axis scores + rationale JSONB
- `story_clusters` — event groups; bias_diversity JSONB, consensus_points JSONB, divergence_points JSONB, divergence_score, headline_rank, coverage_velocity, updated_at, `sections text[]` (GIN-indexed)
- `cluster_articles` — junction: articles ↔ clusters
- `categories` + `article_categories` — topic tags + junction (populated by pipeline)
- `source_topic_lean` — EMA lean/sensationalism/opinion per source per topic (Axis 6)
- `pipeline_runs` — execution history
- `daily_briefs` — per-edition TL;DR text + audio script + audio metadata (url, duration_seconds, file_size, voice); unique on (edition, pipeline_run_id); public read RLS

Frontend filters by edition: `.contains("sections", [edition])` (PostgREST array containment). Cross-listed clusters appear in all matching edition feeds.

### Key Views & Functions
- `cluster_bias_summary` — weighted bias averages/spreads per cluster
- `refresh_cluster_enrichment(p_cluster_id)` — computes divergence_score, bias_diversity, coverage_score, tier_breakdown
- `update_updated_at_column()` — auto-trigger on articles + story_clusters
- `cleanup_stale_clusters()` + `cleanup_stuck_pipeline_runs()` — maintenance RPCs

Migrations: `supabase/migrations/` (001-019).

## Skills & Workflows (`.claude/skills/`)

### Design Skill

| Skill | Purpose | Trigger |
|-------|---------|---------|
| `/pressdesign` | Press & Precision design enforcement — anti-slop, typography, motion grammar, newspaper layout, responsive strategy | Auto on UI tasks |

### Agent Team Workflows (10 Orchestrated Pipelines)

Multi-agent workflows invoked via `/command`. Each orchestrates agents in parallel (||) and sequential (→) stages with automatic gating.

| Command | Agents | Pattern | When to Use |
|---------|--------|---------|-------------|
| `/pipeline-qa` | pipeline-tester \|\| bias-calibrator → bug-fixer → pipeline-tester \|\| bias-calibrator | Validate → Fix → Re-validate | After any `pipeline/` code change |
| `/bias-audit` | analytics-expert \|\| bias-auditor → nlp-engineer → pipeline-tester \|\| bias-calibrator | Benchmark → Fix → Confirm | Gold standard for bias engine changes |
| `/bias-calibrate` | nlp-engineer → bias-calibrator \|\| analytics-expert → bias-auditor → pipeline-tester | Tune → Check → Verify | Precision tuning of scoring params |
| `/frontend-ship` | frontend-builder → responsive-specialist \|\| perf-optimizer → uat-tester → frontend-fixer | Build → Test → Fix | Any UI change or feature |
| `/audio-qa` | audio-engineer → pipeline-tester \|\| db-reviewer → bug-fixer | Review → Validate → Fix | Daily brief audio changes |
| `/full-audit` | void-ciso \|\| db-reviewer \|\| perf-optimizer \|\| update-docs \|\| bias-calibrator → bug-fixer \|\| frontend-fixer | 5-way audit → Triage → Fix | Comprehensive system health check |
| `/launch-check` | 8 agents parallel → ceo-advisor → deploy | 8-way validate → Go/No-go | Pre-launch final gate |
| `/daily-ops` | feed-intelligence \|\| db-reviewer \|\| pipeline-tester → triage | 3-way health check | Morning check / post-pipeline |
| `/source-review` | source-curator → feed-intelligence \|\| analytics-expert → pipeline-tester | Vet → Health check → Validate | Adding/removing/auditing sources |
| `/security-sweep` | void-ciso \|\| perf-optimizer → bug-fixer → void-ciso \|\| pipeline-tester | Audit → Fix → Re-verify | Fast security + perf hardening |

**Workflow conventions**: `||` = parallel, `→` = sequential, gate between stages (pass = skip remaining). All workflows produce structured CEO reports.

## Agent Team (20 Agents, 9 Divisions)

> Full structure, R&R, cycles: `docs/AGENT-TEAM.md`

```
CEO (Aacrit)
  ├── Agent Engineering — agent-architect
  ├── Quality ————————— analytics-expert, bias-auditor, bias-calibrator, pipeline-tester, bug-fixer
  ├── Infrastructure ——— perf-optimizer, db-reviewer, update-docs
  ├── Frontend ————————— frontend-builder, frontend-fixer, responsive-specialist, uat-tester
  ├── Pipeline ————————— feed-intelligence, nlp-engineer, source-curator
  ├── Audio ———————————— audio-engineer
  ├── Security ————————— void-ciso
  ├── Product —————————— ceo-advisor
  └── Branding ————————— logo-designer
```

**$0 Cost — Claude Max CLI Only.** No Anthropic API keys. No OpenAI. No paid inference. Gemini Flash free tier only (capped per run).

### Agent Routing Rules

| Task Pattern | Agent |
|---|---|
| RSS health, article collection, deduplication, cluster summaries, content quality | `feed-intelligence` |
| Bias score accuracy, calibration, benchmarking | `analytics-expert` |
| Ground-truth validation, known-outlet comparison | `bias-auditor` |
| Bias score regression, validation suite, weight tuning | `bias-calibrator` |
| Pipeline output validation, clustering quality | `pipeline-tester` |
| Post-test bug fixing | `bug-fixer` |
| Pipeline runtime, frontend load, Lighthouse | `perf-optimizer` |
| Article/cluster data quality, NULL audits | `db-reviewer` |
| Sync docs with codebase | `update-docs` |
| Build UI components, new features | `frontend-builder` |
| Fix UI bugs, layout breaks, a11y gaps | `frontend-fixer` |
| Desktop/mobile layout, responsive issues | `responsive-specialist` |
| UI/UX audit, user-lens testing, journey validation | `uat-tester` |
| spaCy models, bias scoring, NER | `nlp-engineer` |
| Broadcast audio, sonic branding, TTS voice, audio post-processing | `audio-engineer` |
| Source vetting, RSS config, credibility | `source-curator` |
| Security audit, secrets scan, RLS, OWASP | `void-ciso` |
| Strategic advice, roadmap, priorities | `ceo-advisor` |
| Logo, favicon, brand identity | `logo-designer` |
| Agent audit, optimization, new agent design, prompt engineering, technology radar | `agent-architect` |

### Sequential Cycles (now invocable as `/commands`)
```
Pipeline Quality:  /pipeline-qa   — pipeline-tester → bug-fixer → pipeline-tester
Bias Audit:        /bias-audit    — analytics-expert → bias-auditor → nlp-engineer → pipeline-tester
Bias Calibration:  /bias-calibrate — nlp-engineer → bias-calibrator → bias-auditor → pipeline-tester
Frontend Build:    /frontend-ship — frontend-builder → responsive-specialist → uat-tester → frontend-fixer
Audio Quality:     /audio-qa      — audio-engineer → pipeline-tester → bug-fixer
Full Audit:        /full-audit    — 5-way parallel audit → triage → critical fixes
Launch Gate:       /launch-check  — 8-way parallel validation → ceo-advisor go/no-go
Daily Ops:         /daily-ops     — 3-way parallel health check → traffic-light dashboard
Source Review:     /source-review — source-curator → feed-intelligence → pipeline-tester
Security Sweep:    /security-sweep — void-ciso || perf-optimizer → fix → re-verify
```

### Locked Decisions (Require CEO Approval)
- Press & Precision design system (3-voice type, BiasLens Three Lenses, newspaper grid)
- 6-axis bias scoring model + confidence
- Supabase as single data layer
- Static export (Next.js → GitHub Pages)
- 380-source curated list (3 tiers); 7-point political lean spectrum
- $0 operational cost constraint
- Claude Max CLI for all AI work

## Project Structure

```
void-news/
├── CLAUDE.md
├── docs/
│   ├── PROJECT-CHARTER.md         # Project charter and scope
│   ├── DESIGN-SYSTEM.md           # Press & Precision design system (component inventory, layout diagrams)
│   ├── IMPLEMENTATION-PLAN.md     # Phased implementation roadmap
│   ├── GEMINI-VOICE-PLAN.md       # Gemini voice architecture, prompt templates, anti-bias guardrails
│   └── PERF-REPORT-2026-03-22.md  # Vol I: pipeline + frontend performance analysis
├── pipeline/
│   ├── fetchers/
│   │   ├── rss_fetcher.py         # Parallel RSS fetch; global as_completed TimeoutError caught gracefully — hung feeds logged and skipped without crashing pipeline
│   │   └── web_scraper.py
│   ├── analyzers/
│   │   ├── political_lean.py      # Length-adaptive + sparsity-weighted blending; entity lists include key political figures
│   │   ├── sensationalism.py      # Word-boundary regex for superlatives; partisan_attack cap 30pts
│   │   ├── opinion_detector.py    # Adaptive EMA alpha; 14 investigative attribution patterns; value_judgment weight 0.06
│   │   ├── factual_rigor.py       # SPECIFIC_ATTRIBUTION verb-proximity gate; LOW_CREDIBILITY_US_MAJOR baseline 35
│   │   ├── framing.py             # Cluster-aware omission detection; passive voice ratio capped at 30
│   │   ├── gemini_reasoning.py    # Step 6c: contextual score adjustments; mutates article_bias_map; reasoning strings capped at 300 chars
│   │   └── topic_outlet_tracker.py # Axis 6: adaptive EMA (0.3 new / 0.15 established); category normalized to lowercase
│   ├── clustering/
│   │   ├── deduplicator.py        # TF-IDF + cosine dedup
│   │   └── story_cluster.py       # Two-phase: TF-IDF agglomerative + entity-overlap merge
│   ├── summarizer/
│   │   ├── gemini_client.py       # Rate limiting, call caps, optional system_instruction
│   │   └── cluster_summarizer.py  # Headline/summary/consensus/divergence + editorial_importance
│   ├── briefing/
│   │   ├── daily_brief_generator.py # Gemini: TL;DR (5-7 sentences) + two-host audio script; 5-call budget; rule-based fallback
│   │   ├── audio_producer.py      # Gemini 2.5 Flash TTS: native multi-speaker dialogue synthesis, PCM→MP3 via pydub, Supabase Storage upload
│   │   ├── claude_brief_generator.py # Claude CLI premium script generator (manual 1x/day, Claude Max)
│   │   ├── voice_rotation.py      # Neural voice pairs per edition; roles swap daily
│   │   ├── generate_assets.py     # Glass & Gravity sonic identity: bloom intro, glass-bell transition, resolving outro
│   │   └── assets/                # ident.wav, transition.wav, outro.wav (generated)
│   ├── categorizer/
│   ├── ranker/                    # v5.3: 11 signals + confidence curve + Gemini editorial importance
│   ├── validation/                # Bias engine test suite: 26 ground-truth articles, signal_tracker, AllSides cross-ref, runner (96.9% accuracy), snapshot
│   ├── utils/                     # Supabase client, nlp_shared
│   ├── main.py                    # Orchestrator (12 steps + cleanup)
│   ├── rerank.py                  # Standalone re-ranker
│   └── refresh_audio.py           # Standalone audio brief refresh — regenerates TTS from current DB without full pipeline run (~60-90s)
├── frontend/
│   ├── app/
│   │   ├── components/
│   │   │   ├── BiasInspector.tsx  # "Press Analysis" 4-axis scorecard; BiasInspectorInline (Deep Dive inline), BiasInspectorTrigger + BiasInspectorPanel (legacy); each axis collapsible with Gemini reasoning
│   │   │   ├── BiasLens.tsx       # Three Lenses: Needle, Ring, Prism
│   │   │   ├── DeepDive.tsx       # Centered popup overlay: FLIP morph open/close, lede, DeepDiveSpectrum, Press Analysis ▶, Source Perspectives
│   │   │   ├── DeepDiveSpectrum.tsx # Continuous lean spectrum: 7-zone gradient bar + logos at exact politicalLean %, nearby sources alternate rows, each logo links to source article, tooltip on hover
│   │   │   ├── HomeContent.tsx    # Feed container: edition switching, lean filter, story grid; progressive batch reveal (BATCH_SIZE=8, visibleCount); desktop "Continue reading" link; mobile infinite scroll via IntersectionObserver sentinel; Supabase limit 500
│   │   │   ├── LeadStory.tsx      # Hero story card
│   │   │   ├── OpEdPage.tsx       # SHELVED — commented out, pending redesign
│   │   │   ├── OpinionCard.tsx    # SHELVED — commented out, pending redesign
│   │   │   ├── StoryCard.tsx      # Standard story card
│   │   │   ├── NavBar.tsx         # World/US/India nav; dateline row with edition badge pills, time-of-day badge, regional timestamps (US: "9 AM ET", World: HH:MM UTC, India: HH:MM IST); India: Ashoka Chakra SVG icon
│   │   │   ├── FilterBar.tsx
│   │   │   ├── RefreshButton.tsx
│   │   │   ├── ThemeToggle.tsx
│   │   │   ├── LoadingSkeleton.tsx
│   │   │   ├── ErrorBoundary.tsx
│   │   │   ├── Footer.tsx
│   │   │   ├── LogoFull.tsx       # Combo mark: void circle + scale beam + wordmark (SVG, Direction 5)
│   │   │   ├── LogoIcon.tsx       # Icon-only wrapper around ScaleIcon
│   │   │   ├── LogoWordmark.tsx   # Text-only "void --news" SVG, hollow-O
│   │   │   ├── ScaleIcon.tsx      # Void Circle + Scale Beam; 8 animation states (idle/loading/hover/analyzing/balanced/pulse/draw/none)
│   │   │   ├── PageToggle.tsx     # Feed / Sources view switcher
│   │   │   ├── SpectrumChart.tsx  # /sources political spectrum: gradient bar + all sources below in 7 lean zone columns (mixed tiers), logos overlap with -3px margin / fan out on hover, zone counts below, single "Show all" expand button, each zone scrollable at 60vh when expanded
│   │   │   ├── Sigil.tsx          # Compact bias sigil (SigilData type)
│   │   │   └── DailyBrief.tsx     # useDailyBrief() hook + DailyBriefText; "void --onair" pill + ScaleIcon; progress bar; TL;DR in Inter regular with blockquote left-border; text-align justify; mobile 4-line collapse
│   │   ├── lib/
│   │   │   ├── supabase.ts        # Supabase client, fetchDeepDiveData, fetchLastPipelineRun
│   │   │   ├── types.ts           # BiasScores, ThreeLensData, Story, etc.
│   │   │   ├── mockData.ts        # Fallback mock data
│   │   │   └── utils.ts           # timeAgo, etc.
│   │   ├── page.tsx               # Homepage: live Supabase queries
│   │   ├── sources/page.tsx       # /sources: SpectrumChart + source list with favicons
│   │   ├── layout.tsx             # Root layout: fonts, metadata
│   │   ├── globals.css            # Style entry point: @imports from ./styles/
│   │   └── styles/                # tokens.css, layout.css, typography.css, components.css, animations.css, responsive.css, spectrum.css
│   ├── public/
│   ├── package.json               # Next.js 16.1.7, React 19.2.3
│   └── next.config.ts
├── .claude/
│   ├── agents/                    # 20 agent definitions
│   └── skills/                    # 11 skills: pressdesign + 10 agent team workflows (/pipeline-qa, /bias-audit, /bias-calibrate, /frontend-ship, /audio-qa, /full-audit, /launch-check, /daily-ops, /source-review, /security-sweep)
├── .github/workflows/
│   ├── pipeline.yml               # 4x daily cron
│   ├── deploy.yml                 # Build + deploy to GitHub Pages
│   ├── migrate.yml                # Supabase migration runner
│   └── validate-bias.yml          # CI gate: bias engine regression on every push
├── data/sources.json              # 380 curated sources (7-point lean spectrum)
└── supabase/migrations/           # 001-019
```

## MVP Scope

### Phase 1 — Foundation -- COMPLETE
- [x] Project scaffolding, 380 sources (expanded from 222), Supabase schema (migrations 001-019), RSS fetcher, web scraper, GitHub Actions cron, pipeline orchestrator.

### Phase 2 — Analysis Engine -- COMPLETE
- [x] Content dedup (TF-IDF, threshold 0.80, Union-Find), story clustering (two-phase), 5-axis bias scoring (all with rationale), auto-categorization (3-article majority vote), ranking v5.3 (11 signals + Gemini), multi-section cross-listing (sections[]), confidence scoring, consensus/divergence, IP truncation, Axis 6 EMA tracking, Gemini reasoning (step 6c), editorial triage (step 7c), Daily Brief (step 7d: TL;DR + two-host BBC-style audio via Gemini 2.5 Flash TTS), cluster dedup (step 8b), RSS fetch global timeout handling.

### Phase 3 — Frontend MVP -- COMPLETE
- [x] Next.js 16 App Router, design token system, desktop + mobile layouts, StoryCard + LeadStory, news feed (headline_rank), "Why This Story" tooltip, category filtering, BiasLens Three Lenses, RefreshButton, light/dark mode, DailyBrief ("void --onair" TL;DR + audio player).
- [ ] Animation system (Motion One spring presets, utilities) — pending.
- [ ] GitHub Pages deployment — pending.

### Phase 4 — Deep Dive Dashboard -- IN PROGRESS
- [x] Centered popup overlay (desktop 75vw / mobile full-screen), per-source BiasLens, tier breakdown bars, Source Perspectives (Agreement/Divergence), Press Analysis inline (BiasInspectorInline), lean spectrum above/below track.
- [ ] Detailed framing comparison view.
- [ ] Source credibility context panels.

### SHELVED — Op-Ed / Opinion Page
Removed from frontend. Pipeline still computes opinion_fact (Axis 3). `OpEdPage.tsx` and `OpinionCard.tsx` commented out for reference. Future redesign needs: dedicated curation, distinct visual treatment, author-first display, no Gemini, no clustering.

### Phase 5 — Polish & Launch
- [ ] WCAG 2.1 AA accessibility audit
- [ ] Lighthouse 90+ performance
- [ ] Animation polish
- [ ] Cross-browser testing
- [ ] Mobile touch gesture refinement
- [ ] Launch

## Git Workflow

- **Always push to `claude/*` branches.** Never push directly to `main`.
- GitHub auto-merge is enabled — pushing to `claude/*` auto-creates a PR and merges.
- **After every completed change:** commit, push to `claude/*`, and confirm deployment succeeds (`gh run watch`). Do not consider work done until the deploy workflow passes.

## Development Notes

- Python 3.11+, Node 18+, TypeScript for all frontend.
- All bias analysis must be rule-based (no external API dependencies).
- Pipeline runtime: realistic target is **25-35 min** for normal incremental runs (after perf optimizations). Fresh DB run (Vol I, 2026-03-22) took 108 min. The 6-min GitHub Actions soft limit does not apply — pipeline runs to completion.
- Frontend is fully static (next export). Supabase client-side reads only.
- Animation adapted from DondeAI (`/home/aacrit/projects/dondeAI/js/spring.js`, `motion.js`).
- CSS adapted from DondeAI (`/home/aacrit/projects/dondeAI/css/tokens.css`).

### perf-optimizer: Applied Optimizations
- TextBlob text limit: 50K → 5K chars (`sensationalism.py`; sentiment signal saturates within ~1000 words)
- RSS entry cap: 30 per feed (`rss_fetcher.py`; reduces fetch + parse time)
- Bias analysis workers: 4 → 8 (`main.py`; parallel analyzer threads)
