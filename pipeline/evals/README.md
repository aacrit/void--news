# Void News — Evaluation System (v1)

A deterministic, **$0, no-LLM** rule layer that interrogates the most recent
daily run's **displayed top-50** feed and emits ranked red-flag findings + a
scored report.

This module's job is to produce **high-signal CANDIDATE findings deterministically**
and emit exactly the data a judge needs to confirm them. The LLM **judge /
resolution layer is intentionally OUT of scope** here — it runs separately as
**Claude agents** over the `judge_candidates` array in `eval_report.json`.

Read-only. It never writes to the database and never calls an LLM.

## Checks

| Code | Dimension | What it flags | Grade |
|---|---|---|---|
| **RF-4** | coverage | A displayed card with an empty `summary` or null `summary_tier` (CATASTROPHIC), or a summary that looks like a raw scraped excerpt (WRONG). Ports `summaryHygiene.ts` `isRawExcerpt`. | CATASTROPHIC / WRONG |
| **RF-1** | contamination | *(PRIMARY mission)* The summary's tokens are **disjoint** from the cluster's dominant topic (voted from member article titles). Likely cross-contamination — the summary describes a different event. **Judge candidate** (emits summary + member titles). | WRONG (candidate) |
| **RF-3** | agreement | The headline has distinctive (high-IDF) stems and the summary shares **none** of them. **Judge candidate** (emits both texts). | WRONG (candidate) |
| **RF-6** | duplication | Two top-50 clusters are the **same story** (re-runs `feed_ranker`'s near-dup shared-stem rules). Keeps the higher-sourced telling. | WRONG |
| **RF-7** | junk | An evergreen / junk item in the feed (runs `newsworthiness()` over the titles). | WRONG |
| **RF-5** | cohesion | An incoherent / **mis-titled bag**: `entity_convergence < 0.40` AND `avg_title_jaccard < 0.12` (the `MEGA_OVERMERGE_*` over-merge condition), **corroborated** by an off-topic summary. **Judge candidate.** See the RF-5 recalibration note below. | WRONG or ACCEPTABLE (candidate) |
| **RF-11** | hygiene | Em/en dashes or show-don't-tell / source-meta patterns in `summary`/`title`/`consensus_points`/`divergence_points`. | ACCEPTABLE |

Priorities: **P0** when a finding touches the front page (top-10), otherwise
**P1** (or **P2** for hygiene). Findings are sorted P0 > P1 > P2.

### RF-5 recalibration (2026-08-07) — trustworthy cohesion WRONGs

RF-5 recomputes cohesion from member **titles** only (the eval does not have the
pipeline's in-memory NER entity sets), so a coherent BIG story with varied
headlines (e.g. a 50-member Ebola outbreak, whose members share a topic but
phrase their headlines many ways) fails both floors and used to be reported as a
hard **WRONG** — a false positive that made RF-5's WRONGs untrustworthy.

RF-5 now demands a **corroborating signal** before a hard WRONG: after both
floors fail, it checks whether the cluster's **summary still tracks the members'
dominant topic** (`_dominant_topic`, the same token vote RF-1 uses).

- **WRONG** (P0/P1, trustworthy) only when: both floors fail **AND** the real
  (NER-backed `_cluster_cohesion`) numbers were available **AND** the summary is
  **off-topic** from the members. All three signals agree the bag is incoherent.
- **ACCEPTABLE** (P2, low-confidence "verify" candidate) when the numbers are the
  **title-only approximation** (`approximated=True`, no NER) **OR** the summary
  still tracks the members' topic. The finding is clearly labeled
  `title-only heuristic, verify` / `summary still on members' topic, verify` and
  stays a judge candidate, so a coherent big story is surfaced for review but
  never hard-failed on headline variance alone.

Evidence now carries `summary_on_topic` and `low_confidence` flags; the judge
payload carries the cluster `summary` (first ~400 chars) + `summary_tier` /
`content_type` / `n_articles` so the resolution layer can act without re-querying.

### Offending-card data on every finding

Every **RF-4** finding and every **judge candidate** (RF-1 / RF-3 / RF-5) now
emits the offending card's `summary` (first ~400 chars — RF-4; candidates carry
the full/whole summary they already emitted), `summary_tier`, `content_type`, and
`n_articles`, so the resolution/judge layer has the exact text it needs. RF-4
previously named the card but never carried its summary text.

## Grade vocabulary

- **CORRECT** — no problem.
- **ACCEPTABLE** — a minor tell, not a correctness failure (e.g. an em dash).
- **WRONG** — a real defect a reader would notice.
- **CATASTROPHIC** — a launch-blocker (e.g. a blanked card). Caps the Feed Score at 40.

The **Feed Score** (0–100) is the mean of the seven per-dimension scores; each
dimension starts at 100 and loses points per finding by grade.

## Reused helpers vs. reimplemented

Every check **prefers the real repo helper** and only falls back to a local
equivalent when a heavy dependency (spaCy / nltk / sklearn / google-genai) is
unavailable (e.g. in the offline smoke test). Production CI installs the deps, so
the real helpers run there.

- **Reused:** `cluster_summarizer._SHOW_DONT_TELL_PATTERN` /
  `_META_BRACKET_RE` / `_META_SENT_RE` / `_ontopic_title_tokens`;
  `feed_ranker._specific_title_stems` / `_contest_anchor_conflict` /
  `_GENERIC_EVENT_WORDS` / `_COMMON_ACTION_WORDS` + the `NEAR_DUP_*` constants;
  `story_cluster._title_word_stems` / `_cluster_cohesion` +
  `MEGA_OVERMERGE_ENTITY_CONV_FLOOR` / `MEGA_OVERMERGE_TITLE_JACCARD_FLOOR`;
  `newsworthiness.newsworthiness`.
- **Reimplemented:** `is_raw_excerpt` (ported 1:1 from the TypeScript
  `summaryHygiene.ts`, which has no Python source). Local fallbacks: a light
  Porter-ish stemmer and a title-jaccard / entity-convergence approximation,
  used only when the clustering deps can't import.

> Note: the cohesion helper is named `story_cluster._cluster_cohesion` (the task
> referred to it as `_compute_cohesion`).

## How to run

**Locally / manually** (needs `SUPABASE_URL` + `SUPABASE_KEY` in the env):

```bash
python -m pipeline.evals.run_eval
```

Writes `eval_report.json` and `eval_report.md` (set `EVAL_OUT_DIR` to change the
output directory) and prints the Markdown to stdout.

**CI:** `.github/workflows/eval.yml` runs on `workflow_dispatch` and after the
**News Pipeline** workflow completes (`workflow_run`). It writes the Markdown to
the GitHub Step Summary and uploads both files as the `feed-eval-report`
artifact. Non-gating — it reports, it never fails a build.

**Offline smoke test** (no DB, no LLM, no network):

```bash
python pipeline/evals/smoke_test.py
```

## Output shape (`eval_report.json`)

```jsonc
{
  "feed_score": 40,
  "dimension_scores": { "coverage": 55, "contamination": 84, ... },
  "counts_by_grade": { "CATASTROPHIC": 1, "WRONG": 3, ... },
  "findings": [ { "code": "RF-1", "grade": "WRONG", "priority": "P0",
                  "cluster_id": "...", "is_candidate": true,
                  "judge_payload": { ... }, ... } ],
  "judge_candidates": [ /* the exact payload the Claude judge agents consume */ ]
}
```
