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

### Rule 1: zero factual error

**Nothing Void publishes may contain a factual error. This outranks every
other rule in this file.** If show-don't-tell, the dash ban, a word budget or a
deadline conflicts with getting a fact right, the fact wins and the other rule
yields.

This is a standard, not a hope, so it is stated as behaviour:

- **Every factual claim traces to a source in the data.** Not to model
  knowledge, however certain. If the source does not carry it, it does not
  ship. This is already enforced for History scripts by H-01 and H-10, and for
  every LLM prompt by the grounding line.
- **Silence beats a plausible reconstruction.** A claim that cannot be sourced
  is cut, not softened, not hedged into place. Where a quote is attributed,
  paraphrased or secondhand, say so out loud or do not use it.
- **Where two sources genuinely disagree, publish the disagreement.** Do not
  pick one and present it as settled, and do not average them. An unreconciled
  range is honest; a false precision is not.
- **A number that goes stale is a future error.** Do not publish a count that
  changes with time ("ten presidents", "sixty-five years on") when a durable
  formulation exists.
- **Check the convention before calling something a defect.** Two reported
  errors in the 2026-09-20 audit were refutations: a population figure another
  field licensed, and a sort year that seventeen events share. Acting on an
  unverified finding introduces an error while claiming to remove one.
- **Verify, then report.** Never state that something is fixed, committed or
  passing without reading back the thing itself. A chained command that echoes
  success is not evidence.

**Controls, because a rule nobody can fail is not enforced.** Every class of
factual error found in production gets a check that makes it structurally
impossible, not a note asking people to be careful:

| Check | Catches |
|---|---|
| `tests/test_history_data.py` | figure identity against its own link, impossible lifespans, malformed attribution |
| `tests/test_history_script.py` (H-01..H-11) | a quote not in the sources, a hedge not said aloud, a speaker not named |
| `tests/test_history_audio.py` | audio that no longer matches its corrected script |
| `pipeline/editorial/standard.py` | the daily feed's editorial rules, run at write time and against served HTML. **E-13** a number not in the sources, **E-14** a quotation not in the sources |
| `pipeline/editorial/grounding.py` | keeps the text a card was written from, so E-13 and E-14 can still be run after the run that wrote it |
| `tests/test_history_copy.py` | an em dash in page-facing prose, a speaker that is a description with nothing behind it |
| `tests/test_history_export_parity.py` | a correction that never reached the served JSON |
| `tests/test_truncation_lint.py` | a query cap published as an exact count |
| `tests/test_weekly_audio_served.py` | an MP3 that is not what its own row says it is |
| `tests/test_docs_facts.py` | this file's own numbers, against disk |
| `frontend/scripts/verify-responsive.mjs` | content past the viewport, and sticky that does not stick |
| `scripts/verify_production.py` | what the live page actually serves, and that `/command-center`, `/admin`, `/pipeline` are not served at all |
| `scripts/verify_sections.py` | served History (H-01..H-06), Weekly (W-01..W-10, W-10 is the kill list on the page), Paper (P-01..P-04: the front page's twenty, in order, no dash, no retired claim) and Press (PR-01: the feed size it quotes) |
| `tests/test_prompt_grounding.py` | a production prompt without the grounding sentence, or one that still calls the product `void --x` |
| `tests/test_bias_defaults_gate.py` + `pipeline/validation/bias_defaults.py` | an export whose per-article bias rows are mostly the default tuple (the step 6b overwrite, 73% of rows on 2026-09-20) |
| `tests/test_podcast_feed.py` | a podcast cover that is missing or carries retired text, a channel title outside "Void News: <programme>", an item title that disagrees with the page |
| `tests/test_paper.py` | Paper drifting from the front page, a dash or a retired claim in its source |
| `frontend/test/copy-facts.test.mjs` | a stale story count in page copy, and any dash or kill-list word in a frontend string literal or JSX text, **including one spelled as an escape** (`\u2013`, `&mdash;`, `&#8212;`): three rendered dashes shipped past the literal-character check |
| `frontend/test/episode.test.mjs` | the pure core of the audio system: an episode wearing another programme's edition, a play button that loads and does not play, a page that seizes a playing element |
| `frontend/test/labels.test.mjs` | the one lean ladder; asserts the word "Flat" is gone (a card says Balanced, Not measured, Contested, or a direction) |
| `frontend/test/css-parity.test.mjs` | a class selector nothing in `app/` references (1,168 of 3,109 were dead on 2026-09-21); prints the reverse direction too |
| `frontend/test/css-lint.mjs` + `.stylelintrc.json` | a raw `cubic-bezier(` outside `tokens.css`, a `font-family` off the four semantic tokens, a literal radius without a disable and its reason |
| `frontend/scripts/verify-headless.mjs` | the product in a browser: console and hydration errors, a link to a page the export does not carry, a second `h1` or masthead, a title outside the grammar, a masthead that disagrees with the URL, a control with no name, a dash in chrome, a focus ring that is not there, axe WCAG 2.1 AA; and the journeys (search to a result and into the story, Deep Dive share to the clipboard, theme, drawer, Sigil, shortcuts, banner, the player per route, the Audio hub's play buttons, History's long-view toggle and Listen island, Weekly's Argument loading, the Sources picker and axis dots, the About demo's sliders, an empty feedback submit refused in the page, navigation landing at the top, Paper parity, the podcast feeds and manifest, the brand layer); and the On Air system, one scenario per measured desync (`one-play-button` on all three programmes, `audio-survives-navigation`, `weekly-does-not-seize`, `tab-resume-keeps-its-programme`, `onair-tells-the-truth`, `play-state-cannot-lie`, `no-double-transport`, `onair-panel` at both widths). `--quick` in CI, the full grid by hand |

Every one of these runs in `auto-merge-claude.yml`. Nine of them did not until
2026-09-21, which is the whole reason the line above this table is worth
repeating: a rule nobody can fail is not enforced.

When a factual error reaches production, the fix is not complete until a check
exists that would have caught it. Add the check in the same commit.

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
| Editorial rules (18 validators incl. E-15 hedge-is-not-attribution, one impl, two consumers) | `docs/EDITORIAL-STANDARD.md`, `pipeline/editorial/standard.py` |
| Voice and brand | `docs/VOICE-BRAND.md` |
| Stage 2 (bench → coherence → summarize → merge → critique → validate → order) | `pipeline/editorial/stage2.py` |
| Clustering (5 live phases; 2.5/2.55/2.6 parked, no prod caller; `MERGE_HARD_CEILING=120`) | `pipeline/clustering/story_cluster.py` |
| Bias engine (6 axes, all rule-based, deterministic rationales) | `pipeline/analyzers/`, fixtures in `pipeline/validation/` |
| Run the editorial half offline, no LLM key | `tests/test_editorial_stage.py` + `tests/build_test_db.py` |
| Feed size (one source of truth) | `frontend/config/feed.json` |
| The display window (one definition) | `pipeline/utils/display_window.py` |
| Lean labels, suppression gate, the one ladder. Three measurement states said aloud: **Balanced** (measured, at the centre), **Not measured** (gate failed), **Contested** (measured, split), else a direction. The Sigil tilts only on a confident read | `frontend/app/lib/biasColors.ts` (`storyLeanLabel`, `leanLabelState`) |
| **The one masthead and footer**: mounted once in `app/layout.tsx`, section read from the pathname, skinned per section via `:root:has(.hist-page)` / `:has(.wk-page)` / `:has(.np-root)` (section palettes live on `:root` while mounted). No section renders its own topbar | `frontend/app/components/NavBar.tsx`, `Footer.tsx`, `styles/components.css` "Section skins" |
| **The audio state machine**: two slots, never one. `dailyBrief` is today's edition and only the daily fetch writes it; `nowPlaying: Episode \| null` is what is in the element and the `<audio>` src comes from it. `play(ep)` toggles what it owns and loads then plays what it does not; `load(ep)` offers and refuses to interrupt. `isPlaying` is written only by element events | `frontend/app/lib/episode.ts`, `app/components/AudioProvider.tsx`, `frontend/test/episode.test.mjs` |
| **One transport, two mounts**: `/onair` is a page whose subject is TODAY'S broadcast whoever owns the element; `OnAirPanel` is chrome whose subject is what is playing. The panel is right-anchored from 1024px (`--onair-pane-w`), a modal sheet below. The pill stands down on `/onair` and while the panel is open | `frontend/app/components/OnAirPanel.tsx`, `OnAirPage.tsx`, `FloatingPlayer.tsx` |
| **Share cards**: one composer draws every card (Sigil, VOID NEWS, section nameplate, content); `og-image.png` is rendered by `node brand/ci/render_og.mjs`, never hand-edited; per-story cards for the latest edition only | `frontend/app/lib/ogCard.tsx`, `app/story/[id]/ogCard.tsx` |
| **Paper** (the printable twenty) | `frontend/app/paper/`, `scripts/verify_sections.py` P-01..P-04, `tests/test_paper.py` |
| Shared kill list (significance + AI slop), one regex for feed, Weekly, Opinion, promos, served pages | `pipeline/utils/prohibited_terms.py` (`find_prohibited`, `strip_significance`) |
| Served-output gates | `scripts/verify_production.py` |
| **On Air** radio: rundown grammar, R-01..R-15 (R-14 grounded attribution, R-15 no unattributed statement of law), voices, mastering | `docs/ON-AIR-RADIO.md` |
| **Weekly audio** "The Argument": W-01..W-12, the moat, the dry argument | `docs/WEEKLY-AUDIO.md` |
| **History audio**: format, casting, H-01..H-11 | `docs/HISTORY-AUDIO.md`, `docs/HISTORY-SCRIPT-BRIEF.md` |
| **The Hearing**: `/history/[slug]`, a SERVER component. Three client islands (rail, Listen, lightbox). `omitted` appears in the turn and nowhere else | `frontend/app/history/components/Hearing.tsx`, `hearing.ts`, `docs/proposals/HISTORY-PAGE-REVAMP.md` |
| **House promos** (post-roll under every outro; pool, rules, retrofit) | `data/promos/house.yaml`, `pipeline/briefing/house_promos.py`, `docs/VOICE-BRAND.md` "House Promos" |
| **Podcast feeds** (On Air, The Argument, History) and directory submission | `pipeline/briefing/podcast_feed_generator.py`, `docs/PODCAST-DISTRIBUTION.md`, `/audio` |
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
| **Weekly audio** ("The Argument") | Live. Three Kokoro anchors, 11 chapters, mastered to -16 LUFS, verified against the served file. Rendered by **manual `audio-only` dispatch**; no scheduled run has produced one yet. There is no fallback: a failed render ships no audio rather than a quiet legacy substitute. |
| **History** | Live, 78 events, static JSON since rev 69. Landing prerendered with an `<h1>` and every card (2026-09-21); era, region and thread browse routes linked and in the sitemap; native scroll, no wheel hijack. 149 time-bound claims dated or dropped 2026-09-21 (`docs/audits/HISTORY-DATA-2026-09-21.md`). |
| **History audio** | **78/78 scripts written, 78/78 rendered**, each carrying a house promo under its outro. Register: `docs/data/history-episodes.csv`, regenerate with `python3 pipeline/history/episode_report.py`. |
| **Revolt** | 301-hidden, serves MOCK data. Cannot be un-hidden until it reads static JSON. |
| **Ship / Feedback** | Live on the Worker + D1. |
| **Podcast feeds** | Generated: `podcast-world.xml`, `podcast-weekly.xml`, `podcast-history.xml` (78). Linked from `/audio` (the section that holds every programme and its play buttons) and `layout.tsx`. **Not yet submitted** to Apple or Spotify. Three covers rendered 2026-09-21 from the house lockup (`podcast-cover-{world,weekly,history}.jpg`); `tests/test_podcast_feed.py` gates them. |
| **House promos** | Live. 24 promos, `af_kore` at speed 0.86 over `radio_promo_bed.wav`. **All 78 History episodes stitched 2026-09-21**; On Air and Weekly pick one up on their next render. |
| **Paper** | **Live 2026-09-21** as the printable twenty: the same 20 stories as the front page, in the same order, read from `build-data/feed.json`, every headline a link to its Deep Dive, print stylesheet, no classifieds, no datelines, no edition route. Gated by P-01..P-04. |
| **Games** | 301-hidden. |

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
title case with plain names: The Brief (tag "TL;DR"), Audio, History, Weekly,
Paper, Sources, Deep Dive, Opinion, Ship, Games, Revolt. **Audio** (2026-09-21)
is the section that holds the three programmes; On Air is the daily
programme's page inside it, The Argument plays from Weekly and from Audio,
History audio from the event page and from Audio. `/listen` 301s to `/audio`.

**The one-line rule for every surface (CEO, 2026-09-21): `VOID NEWS` is the
only word that gets a lockup; a section gets a nameplate in its accent; a
programme (On Air, The Argument, History audio) gets a title.** There is no
VOID HISTORY or VOID WEEKLY lockup on the site, the cards or the podcast
covers; the masthead reads VOID NEWS · History. Podcast channels are all
"Void News: <programme>". Page titles are `Page | Void News` for a landing
and `Page | Section | Void News` for a leaf (`sectionTitle()` in
`lib/siteMeta.ts`). Themes stay: History keeps its archival paper and umber,
Weekly its magazine red; a section overrides at most an accent ramp, its
paper, its card surface and its grain. The browser wears the section too,
quietly: the status bar is the section's paper (never its accent), the
scrollbar and the selection take its accent, the nameplate draws its rule in,
a long read carries a brass reading rule under the masthead, the wordmark's
beam rocks while audio plays, and a Deep Dive or a History event prints as a
sheet with its own address. All of it is `app/styles/brand.css` plus one
attribute, and every touch is asserted by the headless sweep.

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
data/           sources.json (1,016) · history/events (78) · history/scripts (78)
tests/          editorial stage, weekly, radio, history script + audio, gates
docs/           CHANGELOG.md · OPEN-ITEMS.md · 45 reference docs
```
