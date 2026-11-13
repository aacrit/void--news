# Rigor: the workflow half (hand-merged PR)

**Rev 86 WS-G, 2026-10-03.** The code half of the factual-rigor floors
(`pipeline/validation/rigor.py`, `scripts/audit_grounding.py`,
`tests/test_rigor.py`) landed on a `claude/*` branch. A `claude/*` branch may
not change `.github/` (`tests/test_workflow_hygiene.py` W-02: the merge job
refuses it), so the two workflow edits below are applied by hand, in one PR,
together with the allowlist removal at the end.

Until this PR lands, `test_rigor.py` sits on the W-05 allowlist, nothing runs
the floors on the path that writes, and `rigor.json` is rewritten only by hand.
A gate that cannot run on the path that writes is not a gate.

## What it does

`pipeline.yml`, between the export and the data commit:

1. **Measure factual rigor** (new step): `python pipeline/validation/rigor.py --write`
   writes `frontend/build-data/rigor.json` (counts only) and this run's row in
   `docs/data/rigor-series.csv`.
2. **Gate the emitted data** (existing step, two lines added):
   `python scripts/audit_grounding.py --quiet` (F-1, F-2) and
   `python tests/test_rigor.py --floors` (F-1, F-2, F-3, F-5, and that
   `rigor.json` describes this run's feed). Either failing leaves the previous
   day's data in place, as the four existing gates do.
3. **Commit**: `docs/data/rigor-series.csv` is staged beside the data, and a
   rebase conflict on it resolves to this run's copy like every generated
   file. (Two runs in one day would keep the later run's file, so the earlier
   run's row could be lost on a conflict; the series is a trend, and a lost
   row is a gap in it, not an error in it.)

`auto-merge-claude.yml`: `python tests/test_rigor.py` beside
`test_brief_grounding.py`, so a branch that breaks a floor's ability to fail
cannot merge. In that mode a `rigor.json` that describes an older feed is a
warning, not a failure, because a branch carries whatever main's last pipeline
run wrote.

Verified before writing this file: `tests/test_workflow_hygiene.py` passes
against the patched workflows with the allowlist entry removed (W-05 sees
`tests/test_rigor.py` in a workflow; W-01..W-09 unchanged).

`verify-production.yml` needs no change: it checks out the repository, and
`scripts/verify_production.py` now reads the committed `build-data` itself.

## The diff

```diff
--- a/.github/workflows/pipeline.yml
+++ b/.github/workflows/pipeline.yml
@@ -221,6 +221,14 @@
           VOID_EXPORT_ONLY: feed,brief,archive,methodology,history,engine
         run: python pipeline/export_static.py
 
+      # Rev 86 WS-G (docs/proposals/FACTUAL-RIGOR-PLAN-2026-10-02.md, section
+      # 1). Counts only, internal only: per-product coverage, the audit's
+      # tallies and this run's counters into build-data/rigor.json, and one
+      # row per run into docs/data/rigor-series.csv. Before the gate step,
+      # because test_rigor --floors asserts the file describes THIS feed.
+      - name: Measure factual rigor
+        run: python pipeline/validation/rigor.py --write
+
       # The data commit goes STRAIGHT TO MAIN and skipped every gate until
       # 2026-09-23, because the controls live in auto-merge-claude.yml, which
       # only runs when a claude/* branch merges. So this job could commit
@@ -251,6 +259,15 @@
           # beside Sept 26's show and labelled two edge-tts voices with three
           # Gemini roster names.
           python tests/test_onair_sidecar.py
+          # Rule 1 floors (rev 86 WS-G). The grounding index was written every
+          # run and read by nothing. Every shipped card and point now goes
+          # through E-13, E-14 and E-16 against it: a confirmed finding (F-1)
+          # or a fresh card with no pre-truncation record (F-2) fails the run.
+          # A stub-only record reports "cannot confirm" and never fails. Then
+          # F-3 (a TL;DR, Opinion or On Air that shipped unverified must wear
+          # its label) and F-5 (every correction applied and gated).
+          python scripts/audit_grounding.py --quiet
+          python tests/test_rigor.py --floors
 
       - name: Commit refreshed static data to main
         id: commit
@@ -265,7 +282,7 @@
           gitauth() { git -c "http.https://github.com/.extraheader=AUTHORIZATION: basic $AUTH" "$@"; }
           git config user.name "github-actions[bot]"
           git config user.email "github-actions[bot]@users.noreply.github.com"
-          git add frontend/build-data frontend/public/data frontend/public/audio frontend/public/podcast-*.xml
+          git add frontend/build-data frontend/public/data frontend/public/audio frontend/public/podcast-*.xml docs/data/rigor-series.csv
           if git diff --cached --quiet; then
             echo "No static-data changes to commit."
             exit 0
@@ -296,7 +313,7 @@
             while IFS= read -r f; do
               [ -n "$f" ] || continue
               case "$f" in
-                frontend/build-data/*|frontend/public/data/*|frontend/public/audio/*) ;;
+                frontend/build-data/*|frontend/public/data/*|frontend/public/audio/*|docs/data/rigor-series.csv) ;;
                 *) echo "conflict outside generated data: $f"; return 1 ;;
               esac
             done <<< "$conflicted"
--- a/.github/workflows/auto-merge-claude.yml
+++ b/.github/workflows/auto-merge-claude.yml
@@ -242,6 +242,7 @@
           # Rev 85 (holistic fixes): the eight gates the workstreams added.
           python tests/test_games_content.py         # every Games bank: no dash, no kill-list term, no date, THE FRAME stays out
           python tests/test_brief_grounding.py       # TL;DR, Opinion and On Air cut what the sources do not carry
+          python tests/test_rigor.py                 # rigor.json recomputes; F-1, F-2, F-3, F-5 each fail on a planted defect
           python tests/test_stuck_runs.py            # a running pipeline run is never failed by its own cleanup
           python tests/test_rerank_pool.py           # 8c ranks only pool-eligible clusters; the feed does not move
           python tests/test_pipeline_runtime.py      # one metered Gemini call site, phase timings, Kokoro workers
```

And in the same PR, the W-05 allowlist entry goes:

```diff
--- a/tests/test_workflow_hygiene.py
+++ b/tests/test_workflow_hygiene.py
@@
-ALLOWLIST: dict[str, str] = {
-    # Rev 86 WS-G. A claude/* branch may not change .github/ (W-02), so the
-    # workflow half ships as a hand-merged PR whose exact diff is
-    # docs/proposals/RIGOR-WORKFLOW-DIFF.md. That PR adds this test to
-    # auto-merge-claude.yml and pipeline.yml and removes this entry.
-    "test_rigor.py": "pending the hand-merged workflow PR in docs/proposals/RIGOR-WORKFLOW-DIFF.md",
-}
+ALLOWLIST: dict[str, str] = {}
```
