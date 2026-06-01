# Simplification — full scope, beyond engine code

> Companion to [ENGINE-BREAKAGE-ANALYSIS.md](./ENGINE-BREAKAGE-ANALYSIS.md).
> The engine simplification reaches into the database, the workflows, the
> frontend, the diagnostic infrastructure, and the docs. This document is
> the complete inventory of what accumulated outside the engine itself
> during Eras 5-7 (2026-05-15 → 2026-05-28), with a keep / modify / delete
> verdict on each.

---

## Why this matters

The 3-phase rewrite didn't only add Python. It added six Supabase migrations,
three new tables, four DDL changes to existing tables, two RLS policies,
three new Python services (`engine_snapshot.py`, `sandbox_replay.py`,
`sandbox_server.py`), one new GitHub Actions workflow (`sandbox.yml`), four
new workflow inputs on `pipeline.yml`, a 2,397-line diagnostic-lab HTML
page, a frontend query schema update, five new validation fixtures, and
the entire 192-line `DIAGNOSTIC-LAB.md` doc.

Roll back the engine code without rolling back its parallel state and you
get inconsistencies: DB columns that are never written, a sandbox page that
points at endpoints that no longer exist, validation fixtures that test for
deleted gates, a CLAUDE.md that documents a rev 44 architecture that's no
longer there. Worse — some of the parallel state is mid-flight (the
in-progress recluster sandbox, the engine_snapshot writer that's been
silently failing for the last several runs).

This document lists every artifact and what to do with it.

---

## 1 · Database (Supabase migrations + tables + columns + indexes + RLS)

### 1.1 What was added

| Migration | Date | Adds | Where it touches |
|---|---|---|---|
| **054** | 2026-05-17 | `story_clusters.mega_cluster_capped BOOLEAN DEFAULT FALSE` + partial index `idx_story_clusters_mega_capped` | clustering writes, ranker reads |
| **055** | 2026-05-17 | `articles.is_wire_copy BOOLEAN DEFAULT FALSE` + `articles.wire_origin_publisher_id TEXT` + partial index `idx_articles_wire_origin` | deduplicator writes, ranker reads for voice-collapse |
| **056** | 2026-05-18 | `story_clusters.mega_cluster_original_count INT` (sparse) + one-shot backfill UPDATE for historical clusters above the 75-source cap | one-time data migration |
| **057** | 2026-05-22 | Three new tables: `engine_runs`, `engine_snapshots` (JSONB payloads), `sandbox_runs` | sandbox-only |
| **058** | 2026-05-22 | RLS policies on the three sandbox tables — anon read on all, anon write on recent `sandbox_runs` rows | sandbox-only |
| **059** | 2026-05-24 | `story_clusters.is_headline BOOLEAN DEFAULT false` + `story_clusters.headline_confidence INT` + partial index `story_clusters_is_headline_idx` + one-shot backfill | Era 7 cohesion-gated headline signal |

### 1.2 Verdict

| Migration | Verdict | Reasoning |
|---|---|---|
| 054 (mega_cluster_capped) | **KEEP** | The simplified Phase 5 still soft-caps at 75 sources and stamps this flag. Ranker still reads it to apply demotion. Column is structurally correct. |
| 055 (wire fields) | **KEEP** | Wire fingerprinting is one of the two genuinely useful things from the rewrite (the other being the 75-source soft cap). Source-count math depends on these columns. |
| 056 (one-shot backfill) | **KEEP** | History. The migration ran once on 2026-05-18; the `mega_cluster_original_count` column is sparse and harmless. Don't roll back. |
| 057 (engine_runs/snapshots/sandbox_runs) | **KEEP, but stop writing** | The tables themselves are inert and harmless. The `engine_snapshot` writer call from `pipeline/main.py` is what's expensive (~5-7 MB JSONB per run, plus encode time). Disable the writer; leave the tables for optional sandbox use. |
| 058 (sandbox RLS) | **KEEP** | Anon-read RLS on inert tables is zero risk. The `sandbox_runs` insert/update policy is gated to "last hour" — safe. |
| 059 (is_headline + headline_confidence) | **KEEP columns, write naively** | Don't drop. The simplified ranker writes `is_headline` from the 3-signal formula (source_count ≥ 8 AND headline_rank ≥ 40 AND not mega_capped). `headline_confidence` becomes a derived UI signal (linear blend of source_count + rank), persisted for the frontend. |

### 1.3 No new migration required

The simplified engine writes a strict SUBSET of what the current schema
supports. All six existing columns remain useful. No DDL is needed; **no
migration 060 to drop columns**. The simplification is purely in writer
behaviour.

### 1.4 One-time cleanup query (recommended after deploy)

Once the simplified engine runs a full cycle, normalize stale state:

```sql
-- Recompute is_headline on all clusters in the last 7 days using the
-- new formula, so the frontend doesn't display stale Era 7 values.
UPDATE story_clusters
SET is_headline = (
      source_count >= 8
      AND COALESCE(headline_rank, 0) >= 40
      AND COALESCE(mega_cluster_capped, false) = false
    ),
    headline_confidence = LEAST(100, GREATEST(0,
      ROUND(0.5 * LEAST(50, source_count * 5)
          + 0.5 * COALESCE(headline_rank, 0))::int
    ))
WHERE created_at > NOW() - INTERVAL '7 days';
```

Apply via Management API PAT after the first post-simplification pipeline
run completes successfully.

---

## 2 · Pipeline supporting code (outside `clustering/` and `ranker/`)

### 2.1 What was added

| File | LOC | Purpose | Verdict |
|---|---:|---|---|
| `pipeline/engine_snapshot.py` | 187 | Serialises articles + clusters + bias + rank into JSONB and writes to `engine_snapshots` table at end of every run | **STOP CALLING** from main.py; keep file in repo for the sandbox path. The writer's been silently failing on recent runs (the May 30 cron has no snapshot row); not load-bearing for production. |
| `pipeline/sandbox_replay.py` | 264 | Re-runs clustering + ranking + bias on a saved snapshot with param overrides. Powers the diag.html "replay" button. | **KEEP** as opt-in debugging tool. Don't wire into production. |
| `pipeline/sandbox_server.py` | 106 | FastAPI sidecar for low-latency local replays. | **KEEP** as opt-in. Only runs when developer starts it manually. |

### 2.2 Removals from `pipeline/main.py`

Era 7 wove ~250 lines of recluster + engine-only + snapshot + world-tag
reconciliation logic into `main.py`. The simplification removes:

| Block | Lines | What it does | Verdict |
|---|---|---|---|
| `_ReclusterSkip` exception path | 931, 1184, 1225 | Skips fetch/scrape/bias in recluster mode | **KEEP** (recluster-only is a useful diagnostic flag, just fix the bug — done in c2ac66c) |
| `engine_only` flag handling | 982, 988-997 | Disables all LLMs for $0 fresh run | **KEEP** (useful for testing) |
| `DISABLE_GEMINI` auto-set | 992 | When engine_only, set env var so summarizer skips | **KEEP** (cost emergency lever) |
| Engine snapshot writer call | ~step 8c.6 | Calls `engine_snapshot.write_snapshot(...)` after rerank | **DELETE** the call (file stays). Removes ~5-7 MB JSONB write per run + serialization cost. |
| Step 8c.5 world-tag reconciliation | 3016-3066 | Post-rerank reconciliation of which clusters belong to the world section | **AUDIT** — added 2026-05-22, may have been necessary because of the broken Phase 2. Check whether removing it leaves stories ungrouped. If clusters lose their `sections=['world']` tag, frontend `/world` page empties. Likely keep but trim. |
| Wire-flag UPDATE loop (`004d272`) | 1404-1429 | Persists `is_wire_copy` to DB per article | **MODIFY** to single batched `upsert` (the analysis doc's §4.5 perf item). |
| Garbage-title filter | 1607-1635 | Drops login pages / stub articles before clustering | **KEEP** — genuinely useful, doesn't over-fire by much. |
| Cluster insert failure tracking | ~step 8a | Logs first failed cluster insert for diagnostics | **KEEP** — harmless, useful when debugging |
| Pipeline_runs finalization fix (`4894735`) | end of `engine_only` path | Updates pipeline_runs row before exit so dashboards aren't stale | **KEEP** — small, correct |

---

## 3 · CI / GitHub Actions

### 3.1 What was added

| Workflow | Purpose | Verdict |
|---|---|---|
| `.github/workflows/sandbox.yml` (56 LOC) | workflow_dispatch path for the diag.html lab to trigger a sandbox replay on GHA when no local sidecar | **KEEP** — opt-in, only runs when manually dispatched. Zero cost when unused. |
| `.github/workflows/validate-clustering.yml` | CI gate on the 35-fixture validation suite, blocks merge on regression | **KEEP, update** — add the three new fixtures from §4.6 of the analysis doc (Trump-Iran consolidation, Observer publisher-bridge, transitive chain at 50). |

### 3.2 Changes to `pipeline.yml` (the cron workflow)

| Input | When added | Verdict |
|---|---|---|
| `brief_only` | pre-Era 7 | **KEEP** — pre-existing, useful for daily brief regeneration |
| `recluster_only` | Era 7 (`a4838b0`) | **KEEP** — useful diagnostic, bug fixed in c2ac66c |
| `recluster_window_hours` | Era 7 (`a4838b0`) | **KEEP** — parameter for `recluster_only` |
| `engine_only` | Era 7 (`f24b1ed`) | **KEEP** — $0 fresh runs for testing |
| `DISABLE_ANTHROPIC=1` | 2026-05-22 cost emergency | **KEEP** (cost lever; remove only when budget restored) |
| `DISABLE_GEMINI_REASONING=1` | Era 4 | **KEEP** (pre-Era 7, separate concern) |
| `DISABLE_EDITORIAL_TRIAGE=1` | Era 4 | **KEEP** (pre-Era 7) |
| `DISABLE_AUDIO=1` | onair-parked | **KEEP** (audio is parked) |

All env-var kill switches are orthogonal to the engine simplification.
Leave them alone.

---

## 4 · Frontend

### 4.1 `frontend/public/diag.html` (2,397 LOC)

The diagnostic lab page. Reads `engine_runs`, `engine_snapshots`,
`sandbox_runs`. Documents the 7-phase pipeline. Has knob drawer for
`MEGA_COHESION_FLOOR`, `HEADLINE_CONFIDENCE_THRESHOLD`, adaptive thresholds.

**Verdict: KEEP, mark out-of-date in a banner.** The page is standalone
HTML deployed by Cloudflare Pages. It doesn't break anything by existing.
Its knob drawer references constants the simplified engine no longer
honors; rather than rewrite all 2,397 lines, add a yellow banner at top:

```html
<div class="banner-warning">
  Diagnostic lab is documenting the pre-simplification engine (Era 7).
  Many displayed knobs (MEGA_COHESION_FLOOR, adaptive thresholds, etc.)
  no longer exist. See ENGINE-BREAKAGE-ANALYSIS.md for current state.
</div>
```

If you ever want the lab to reflect reality again, refactor it then. Until
then, the banner prevents misleading diagnosis.

### 4.2 `frontend/app/components/HomeContent.tsx`

One line changed (line 464 — `enrichedFields` adds `is_headline,
headline_confidence`). The simplified engine still writes these columns,
so this query stays correct. **No change needed.**

The `is_headline` field is read but never visually rendered as a badge
right now (I grepped — no HEADLINE component exists). When you want
the badge, it's a small component add. Until then, the field is queried
and ignored, which is fine.

### 4.3 No HEADLINE badge to remove

Grep confirms: no `<HeadlineBadge>` component exists. The is_headline
infrastructure was wired to the DB but never made it to the UI. Saves us
one cleanup step.

---

## 5 · Validation fixtures

### 5.1 Current state

`pipeline/validation/clustering/fixtures/` has **35 fixtures**, growing
from 21 at the start of the rewrite. The post-rewrite additions:

| Fixture | Added | Purpose | Verdict |
|---|---|---|---|
| 030-cross-country-rare-name-anchor.yaml | Era 5 | Verify Phase 2.6 anchor entity merge works | **KEEP** if anchor phase stays; **DELETE** if we drop Phase 2.6 |
| 031-no-regression-republic-of-congo-vs-drc.yaml | Era 5 | Verify Phase 2.55 synonym pair (Congo ↔ DRC) | **KEEP** — move logic into `_build_document` synonym normalization, keep test |
| 032-anchor-overreach-rejection.yaml | Era 5 (post-1330640) | Verify anchor merge does NOT over-fire | **KEEP** |
| 033-size-cap-property.yaml | Era 5 | Verify `MERGE_HARD_CEILING=120` prevents transitive mega-merges | **REWRITE** — the simplified engine restores the 50-article cap (not 120-source), so this fixture needs updating |
| 034-cross-summit-anchor-triangle.yaml | Era 5 | Anchor across 3+ clusters | **KEEP** if anchor phase stays |

### 5.2 Additions required (per §4.6 of analysis doc)

| New fixture | Asserts |
|---|---|
| `036-trump-iran-fragmentation-merge.yaml` | 5 articles with shared `{trump, iran, deal}` and Jaccard ~0.20 titles must merge to one cluster |
| `037-publisher-bridge-rejection.yaml` | 8 articles all from "* Observer" outlets, sharing only the publisher-name entity, must NOT merge |
| `038-transitive-chain-50-cap.yaml` | 3 clusters of 25 sources each sharing only `{trump}`, must cap at 50-article ceiling and refuse the 75-article transitive union |

The first one is the regression test for the failure that motivated this
whole analysis. Once it goes green, the work is done.

---

## 6 · Documentation

### 6.1 Current state

| Doc | Lines | Status | Verdict |
|---|---:|---|---|
| `CLAUDE.md` | 200+ | Currently at "rev 44" (May 18) per the most recent local edit | **UPDATE to rev 45** describing the simplification |
| `docs/DIAGNOSTIC-LAB.md` | 192 | Documents Era 5-7 lab + sandbox + knob system | **MARK DEPRECATED** — keep for history, add header pointer to ENGINE-BREAKAGE-ANALYSIS.md |
| `docs/PIPELINE-BRAIN.md` | varies | Documents v6.0 ranker | **UPDATE** — drop is_headline three-tier band, document the 3-signal formula |
| `docs/ENGINE-EVOLUTION.html` | 788 | Self-contained timeline doc | **APPEND** an Era 9 section after simplification ships |
| `docs/ENGINE-BREAKAGE-ANALYSIS.md` | 521 | This analysis | **KEEP** as-is — historical record |
| `docs/ENGINE-SIMPLIFICATION-FULL-SCOPE.md` | this file | Cleanup roadmap | **KEEP** as-is |

### 6.2 CLAUDE.md changes

The current rev 44 paragraph documents the post-rewrite engine state.
Replace it with rev 45 mentioning:
- Phase 2 reverted to simple set-intersection + 50-article cap (proper union-find)
- Phases 2.5/2.55/2.6 removed (or 2.55 absorbed into `_build_document`, 2.6 behind flag default-off)
- Phase 5 simplified to soft-cap-only
- is_headline rebuilt around 3 signals
- migrations unchanged (054-059 columns retained)
- engine_snapshot writer disabled in production runs

---

## 7 · Cleanup execution order

Recommended sequence to minimize blast radius:

1. **Add the 3 new validation fixtures** (036, 037, 038). Run suite — they will FAIL on current code. This gives a regression baseline.

2. **Branch `claude/engine-simplification`** off main.

3. **Engine code changes** per analysis doc §4.1, §4.3, §4.4 (revert Phase 2, simplify Phase 5, rebuild is_headline). Re-run validation suite — expect all 38 fixtures (35 existing + 3 new) to pass. If a known-good fixture regresses, iterate.

4. **Delete the engine_snapshot writer call** from `pipeline/main.py` (file stays, just stop calling it). Saves 5-7 MB JSONB write per run.

5. **Batch the wire-flag UPDATE** into single `upsert` (§4.5).

6. **Audit step 8c.5 world-tag reconciliation** — does removing it leave clusters un-tagged for `/world`? If yes, keep; if no, delete.

7. **Update validation fixture 033** (size-cap property) to assert the new 50-article cap instead of the broken 120-source ceiling.

8. **Optionally rewrite or delete fixtures 030 + 032 + 034** if dropping Phase 2.6 entirely. Keep if Phase 2.6 stays behind flag.

9. **Push branch, let CI run**, confirm `validate-clustering.yml` gate is green.

10. **Dispatch `pipeline.yml` with `recluster_only: true`** on 48h window. Watch DB for the expected jumps (max sc 8 → 25-40, sc≥5 from 44 → 120-180, is_headline from 0 → 15-30).

11. **One-shot SQL** to recompute is_headline on the trailing 7 days (§1.4) so the frontend doesn't display stale Era 7 values.

12. **Add the diag.html deprecation banner** (§4.1).

13. **Update CLAUDE.md to rev 45** documenting the simplification.

14. **Append an Era 9 section to ENGINE-EVOLUTION.html** (§6.1).

15. **Merge to main.** Watch next cron at 11:00 UTC.

---

## 8 · What this does NOT touch (intentional non-scope)

To prevent scope creep:

- **Bias engine** (`pipeline/analyzers/`). Six axes, rule-based, validation suite green at 210/210. Untouched.
- **Source curation** (`data/sources.json`, 1,013 sources). Untouched.
- **Memory engine** (`pipeline/memory/`). Cross-day story continuity logic, separate concern. `is_top_story` (set by memory orchestrator) is a DIFFERENT concept from `is_headline` — the two coexist correctly.
- **void --history**, **void --weekly**, **void --paper**, **void --games**, **void --ship**, **void --opinion**. Untouched.
- **PWA / Capacitor shells**. Untouched.
- **Cloudflare Pages deploy pipeline**. Untouched.
- **Anthropic / Gemini / edge-tts integrations**. Untouched.
- **Daily brief generation**. Already routes through the kill switch; untouched.

---

## 9 · Decision points for you

Two questions for you before I start the cleanup work:

**Q1 — Keep diag.html or delete it?**
The lab is 2,397 lines and reflects the Era 5-7 architecture. Options:
- **A.** Keep with deprecation banner (recommended; zero risk, minor visual mess)
- **B.** Delete the file + `engine_snapshot.py` + `sandbox_replay.py` + `sandbox_server.py` + `sandbox.yml` + migrations 057+058. Cleaner repo, removes ~3,500 LOC. Lose the $0 sandbox replay capability.

**Q2 — Drop Phase 2.6 anchor merge or keep behind flag?**
Phase 2.6 (anchor-entity merge) was added to catch fragmented international
stories (Burkinabé minister, Latvian PM Siliņa). With the simplified Phase 2
restored, Phase 2.6 becomes mostly redundant — but it might still rescue a
handful of edge cases. Options:
- **A.** Delete entirely. Simpler, less surface. Tested on the new fixtures.
- **B.** Keep behind a `--enable-anchor-merge` flag, default off, available
  for diagnostic use when fragmentation creeps back.

My recommendation: **A1 (keep diag banner)** and **B2 (keep anchor merge
behind flag, off by default)**. Conservative, reversible.

Say "ship A1+B2" or "ship A2+B1" etc. and I'll start with the validation
fixtures and work the cleanup sequence in order.
