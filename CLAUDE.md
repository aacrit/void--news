# Void News

News aggregation with 6-axis rule-based NLP bias analysis. 1,016 sources,
158 countries. **Live: https://news.voidvision.org** (Cloudflare Pages).

**This file is the current state and the rules in force.** The record of how it
got here is `docs/CHANGELOG.md` (28 rev entries, verbatim) — grep it when you
need the reasoning behind a decision or the root cause of a past defect. What
is unfinished is `docs/OPEN-ITEMS.md`. Keep this file short: it is re-read at
the start of every session, so anything that does not change what you do today
belongs in one of those two.

---

## Architecture

```
GitHub Actions (daily 11:00 UTC)
  → pipeline → pipeline_state.db (SQLite, VOID_SQLITE_PATH)
  → static JSON + MP3 committed to the repo
  → Next.js static export → Cloudflare Pages
  → verify-production.yml asserts ~22 checks on the LIVE served HTML

Live user writes (ship board, feedback) → Cloudflare Worker → D1 (void-live)
```

**There is no Supabase.** Decommissioned 2026-09-01 after an egress lockout
returned 402 on every REST call. Every read is static JSON on the CDN; the only
live database is D1, behind the Worker. `supabase/migrations/001-079` is
historical and applied by nothing.

**The switch:** `pipeline/utils/supabase_client.py` binds `supabase` to a
PostgREST-compatible SQLite shim (`pipeline/utils/pgrest_sqlite.py`) when `VOID_SQLITE_PATH`
is set, so ~40 call sites keep their imports unchanged. Without that env var it
raises `EnvironmentError` — which is why importing a pipeline module in CI can
fail for reasons that have nothing to do with your change.

**State** lives in `pipeline_state.db` (gitignored), restored from the Actions
cache (`void-state-v1-`), falling back to the gzipped `void-state-snapshot`
artifact (90-day retention). **There is no R2 sync** — several in-repo comments
claim one; it was never implemented. That artifact window plus the cache is the
entire durability floor for the `printed_stories` archive.

**The Worker is deployed BY HAND** (`npm run deploy` in `worker/`). No CI
deploys it.

**Stack:** Python 3.11+/spaCy/NLTK (rule-based NLP, no LLM in bias scoring),
Gemini 2.5 via google-genai, Kokoro-82M TTS (Apache-2.0, CPU, own venv
`.venv-tts`), Next.js 16/React 19/TypeScript, native CSS + Web Animations API.

---

## Rules in force

### Show, don't tell
Never assert significance. Juxtapose concrete facts so the reader sees the
pattern. Banned: "notable", "significant", "it should be noted",
"interestingly", "crucially".

> **BAD:** "It is worth noting that tensions are rising significantly."
> **GOOD:** "Both countries recalled their ambassadors within 48 hours. Neither
> has done that since 1979."

### Arrive late, leave early
Enter at the last possible moment, exit before the conclusion is spelled out.

> **BAD:** "The Partition of India was a complex historical process that began
> with British colonial rule and eventually led to the creation of two nations."
> **GOOD:** "A lawyer who'd never been to India drew the border in five weeks.
> 15 million crossed it."

### No em dashes
`—` and `–` are banned in all written editorial output: summaries, headlines,
TL;DR, opinion, weekly, history copy, CTAs, frontend microcopy. Rewrite as two
sentences, or use a comma, semicolon, colon or parentheses. Hyphens in compound
words are fine.

**Exception:** audio scripts (`audio_script`, `opinion_audio_script`) keep them
as TTS breath marks.

### Grounding
Every LLM prompt carries: "Every fact MUST appear in the provided articles. Do
not supplement with prior knowledge."

### No personalization (LOCKED)
Newspaper principle. Same stories, same order, for everyone. No accounts, no
recommendation algorithms.

### Bias scoring weighs BOTH outlet and text
Not one or the other. Political lean blends outlet baseline against the
article's own words, length-adaptively (~50/50 on a short wire item, ~90/10
text-weighted on a full article). Public copy on `/about` and
`/sources#methodology` must lead with "both", never "words not the outlet".

---

## Locked decisions (CEO)

Cinematic Press design · 6-axis bias model · Cloudflare stack · static export ·
1,016 sources (3 tiers, 7-point lean) · no personalization · $0/mo LLM cost ·
1×/day pipeline · **top-20 homepage feed** (moved from 50 on 2026-09-07 — the
one locked decision that has ever changed) · Claude Max CLI for agent work.

---

## Git & dev

- **Always push to `claude/*` branches.** Auto-merge to main.
- **Always commit AND push after every task.** Never wait to be asked.
- **Sync before push:** `git fetch origin main && git merge origin/main --no-edit`
- Pipeline runtime is **~1.5-2h** (dominated by RSS fetch/scrape), not the
  "25-35 min" some older docs claim. Actions `timeout-minutes: 240`; the scrape
  phase is capped by `SCRAPE_BUDGET_SECONDS` (40 min).
- `pipeline/main.py` ends with `os._exit(0)` deliberately. Reaching that line means every
  stage finished; a lingering Playwright/Chromium child can otherwise block
  interpreter shutdown and skip the commit step (this hung the 09-17 run).
- **The repo carries the site's data.** Each run commits
  `frontend/public/data`, `frontend/build-data`, `frontend/public/audio`.
- **Correctness is judged against the served page.** Add a check to
  `scripts/verify_production.py` when a defect reaches production.

---

## LLM budget: $0/day, all free tier

| Model | Cap | Spends on |
|---|---|---|
| `gemini-2.5-flash` | **20 requests/DAY** | daily brief (~2-4) + candidate summaries (~10) ≈ 13/day |
| `gemini-2.5-flash-lite` | high RPD | Stage 2 critique pass, history/weekly support calls |

The flash day-cap is the binding constraint on anything new. Claude retired
2026-06-22 (`claude_client.is_available()` hard-returns `False`), Groq deleted
2026-06-24. Rule-based is the only fallback. Op-eds bypass all LLM.

---

## Gotchas that waste a session

**Jobs that still run against the dead Supabase** (all in `.github/workflows/`). Their output is meaningless.
Do NOT "fix" a failure here by reconnecting Supabase:

| Job | Cron | Reality |
|---|---|---|
| `feed-snapshot.yml` | 16:00 | Commits EMPTY snapshots (73 bytes, `count: 0`) |
| `db-cleanup.yml` | 09:00 | Prunes a database nothing reads |
| `audit-db.yml` | 12:30 | Audits the dead DB |
| `freshness-check.yml` | 15:00 | Repointed rev 66 — reads `feed.json.builtAt`, no Supabase |
| `curate-ship.yml` | manual | Targets `ship_requests`, which lives in D1 now |
| `refresh-brief`, `editorial`, `eval`, `ig-*`, history/revolt loaders | manual | Supabase env, no `VOID_SQLITE_PATH` |

**Comments and docs that lie.** `.env.example` still lists five `SUPABASE_*`
vars and no `VOID_SQLITE_PATH`. `frontend/app/lib/serverFeed.ts` and `archive.ts` headers
describe Supabase reads that are now `readFileSync`. `pipeline/main.py` prints a
"500 MB Free-Plan cap" warning computed from a local file size.
`frontend/app/components/HomeContent.tsx` carries a dead Supabase feed query that can never fire.
`docs/DEPLOYMENT.md` and `docs/PIPELINE-BRAIN.md` both predate the migration.

**`.github/workflows/weekly-digest.yml` restores the state cache and never saves it back.**
The weekly row therefore dies with the container, which is why the back-issue
archive lives in the deploy tree (`build-data/weekly-issues.json`) instead. On
the old Monday 12:00 slot restore-only was a hard requirement, because the
daily pipeline was usually still running and a save would have pushed a pre-run
copy of the state under a newer key. The cron is now **Sunday 18:00**, after the
daily has finished, so that race is gone; restore-only stays because the weekly
adds nothing to the state that anything reads back.

---

## Quick reference

| Working on | Read |
|---|---|
| Frontend, CSS, animation | `docs/DESIGN-SYSTEM.md` |
| Pipeline flow, ranker, bias axes | `docs/PIPELINE-BRAIN.md` ⚠ predates rev 64 restructure |
| Editorial rules (13 validators, one impl, two consumers) | `docs/EDITORIAL-STANDARD.md`, `pipeline/editorial/standard.py` |
| Voice and brand | `docs/VOICE-BRAND.md` |
| Stage 2 (bench → coherence → summarize → merge → critique → validate → order) | `pipeline/editorial/stage2.py` |
| Clustering (5 live phases; 2.5/2.55/2.6 parked, no prod caller; `MERGE_HARD_CEILING=120`) | `pipeline/clustering/story_cluster.py` |
| Bias engine (6 axes, all rule-based, deterministic rationales) | `pipeline/analyzers/`, fixtures in `pipeline/validation/` |
| Run the editorial half offline, no LLM key | `tests/test_editorial_stage.py` + `tests/build_test_db.py` |
| Feed size (one source of truth) | `frontend/config/feed.json` |
| The display window (one definition) | `pipeline/utils/display_window.py` |
| Lean labels, suppression gate, the one ladder | `frontend/app/lib/biasColors.ts` (`storyLeanLabel`) |
| Served-output gates | `scripts/verify_production.py` |
| **On Air** radio: rundown grammar, R-01..R-13, voices, mastering | `docs/ON-AIR-RADIO.md` |
| **Weekly audio** "The Argument": W-01..W-12, the moat, the dry argument | `docs/WEEKLY-AUDIO.md` |
| **History audio**: format, casting, H-01..H-11 | `docs/HISTORY-AUDIO.md`, `docs/HISTORY-SCRIPT-BRIEF.md` |
| Weekly magazine: running order, the measure, the grid | `frontend/app/weekly/`, `frontend/app/styles/weekly.css` |
| Weekly's pure core (testable with no key) | `pipeline/briefing/weekly_parse.py` |
| Weekly end matter (colophon, week-over-week, day-by-day, corrections, OG card, issue index) | `frontend/app/weekly/components/{Colophon,WeekDelta,WeekRail,Corrections}.tsx`, `app/weekly/ogCard.tsx` |
| What Postgres did that SQLite cannot | `migration/PORT_NOTES.md` (authoritative) |
| Agents, workflows, slash commands | `docs/AGENT-TEAM.md` |
| **Why a thing is the way it is** | `docs/CHANGELOG.md` |
| **What is unfinished** | `docs/OPEN-ITEMS.md` |

---

## Section state

| Section | State |
|---|---|
| **News** (daily feed) | Live. Top 20, two-stage pipeline, 35-cluster bench. |
| **On Air** (daily radio) | Live. Kokoro three voices, chapters, mastered to -16 LUFS. |
| **The Brief** (TL;DR + Opinion) | Live. One story per paragraph. |
| **Weekly** | Live. **Vol. I, No. 1 published 2026-09-20**, the first issue on the Sunday cadence and the first ever to carry departments. Aug 24-30 is kept as the pilot. |
| **Weekly audio** ("The Argument") | Built rev 72, **first episode never heard**. |
| **History** | Live, 78 events, static JSON since rev 69. |
| **History audio** | **62/78 scripts written, 49/78 rendered.** Register: `docs/data/history-episodes.csv`, regenerate with `python3 pipeline/history/episode_report.py`. |
| **Revolt** | 301-hidden, serves MOCK data. Cannot be un-hidden until it reads static JSON. |
| **Ship / Feedback** | Live on the Worker + D1. |
| **Paper, Games** | 301-hidden. |

---

## Kill switches

| Feature | Gate |
|---|---|
| Gemini bias reasoning | `DISABLE_GEMINI_REASONING=1` (`.github/workflows/pipeline.yml`) |
| Editorial triage | `DISABLE_EDITORIAL_TRIAGE=1` (same file) |
| All audio | `DISABLE_AUDIO` + `NEXT_PUBLIC_DISABLE_AUDIO` — flip together |
| On Air radio format | `VOID_RADIO_FORMAT=0` → legacy path |
| Weekly audio format | `VOID_WEEKLY_AUDIO_FORMAT=0` |
| TTS engine | `VOID_TTS_ENGINE=edge` → edge-tts fallback |
| Export scope | `VOID_EXPORT_ONLY=feed\|brief\|weekly\|archive\|methodology\|history` |
| Claude API | Retired at source; no env var can re-enable a paid call |

---

## Brand

**Void** is the parent brand. **Void News** (this app) is a product; **Void
Vision** is a coming sibling. Everything else is a SECTION of Void News, in
title case with plain names: The Brief (tag "TL;DR"), On Air, History, Weekly,
Paper, Sources, Deep Dive, Opinion, Ship, Games, Revolt.

Internal identifiers were deliberately NOT renamed in the 2026-08-03 rebrand:
routes (`/weekly`, `/history`), `.void--news` classes, `void-news-*` storage
keys, `com.void.news` appId, the `/void--news` BASE_PATH default. Leave them.

---

## Layout

```
pipeline/
  fetchers/ analyzers/ clustering/ categorizer/ ranker/ validation/ memory/
  summarizer/   gemini_client (sole LLM), cluster_summarizer
  editorial/    standard.py, stage2.py, same_event.py
  briefing/     daily brief, radio_*, weekly_*, audio, podcast feed
  history/      export_history, casting, script_format, *_producer, episode_report
  utils/        supabase_client (the switch), pgrest_sqlite (the shim)
  main.py  export_static.py  rerank.py
frontend/
  app/          components/ history/ weekly/ story/[id]/ lib/ styles/ games/
  build-data/   build-time JSON the server components read
  public/data/  emitted static JSON, committed each run
  public/audio/ MP3s on the CDN, committed each run
worker/         Cloudflare Worker + D1 — the ONLY live database
migration/      PORT_NOTES.md is authoritative
data/           sources.json (1,016) · history/events (78) · history/scripts (62)
tests/          editorial stage, weekly, radio, history script + audio, gates
docs/           CHANGELOG.md · OPEN-ITEMS.md · 45 reference docs
```
