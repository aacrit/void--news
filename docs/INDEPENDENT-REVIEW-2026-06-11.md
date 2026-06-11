# Independent App Review — void --news

**Date:** 2026-06-11
**Scope:** Full-stack independent correctness + security review (Python pipeline, Next.js frontend, GitHub Actions, Supabase schema), focused on the rev-46 "collapse-editions" refactor surface plus pre-existing bugs.
**Method:** Four parallel deep audits (pipeline correctness, frontend correctness, workflows/security, DB schema-vs-code) cross-checked against the live source. Every finding below was re-verified against exact lines.

---

## Executive summary

| Severity | Count | Headline |
|---|---|---|
| **P0** | 3 | Daily pipeline crashes on slow-news days; weekly digest crashes when LLMs degrade; `/paper` renders blank |
| **P0/P1 security** | 4 | Anon-writable tables (data poisoning + free-tier DB-fill DoS); no-op auto-merge gate ships unvalidated code + migrations to prod |
| **P1** | 9 | `_db_id` not written back kills 3 subsystems; PWA broken on live origin; unpaginated reads truncate at 1k rows; topic-diversity/category caps are no-ops; dead nav links; 3 dead-feature DB selects |
| **P2** | ~16 | Cache mislabels, wire-flag loss, non-transitive merge ceiling, fresh-DB bootstrap break, RSS timeout, latent crashes |
| **P3** | ~10 | Doc drift |

The single common thread in the P0/P1 set is the rev-46 edition collapse: per-edition loops were flattened to single passes, and several loop-body variables (`section_val`), write-backs (`_db_id`), and downstream consumers (topic diversity, `/paper`, weekly editions) were left half-converted.

---

## P0 — Crash / blank (fix immediately)

### P0-1 · Daily pipeline crashes uncaught when any top-10 story has no article in 24h
`pipeline/main.py:2287`
```python
print(f"  [{section_val}] Recency gate: demoted {len(demoted)} stale stories from top 10")
```
`section_val` was the per-edition loop variable deleted in rev 46; it now appears nowhere else in the file. The recency-gate block (`main.py:2263-2287`) sits at 8-space indent inside `main()` **with no enclosing `try`** (verified: nearest 4-space `try` closes at 1359, nearest 8-space `try` is at 2197 and closes at 2227; next `except` is 2885). So the first time `demoted` is non-empty — i.e. any top-10 cluster whose newest article is older than the 24h cutoff, a routine slow-news condition given the 36h clustering lookback — the run dies with `NameError` **after** step-7b Sonnet spend but **before** feed ordering, daily-brief generation, and cluster storage. The `pipeline_runs` row stays `running`; the homepage serves stale data. The `print` is also wrongly inside the `for c in demoted` loop (logs N times).
**Fix:** replace `{section_val}` with a literal (`"feed"`), and move the `print` out of the inner loop.

### P0-2 · Weekly digest crashes precisely when the LLM kill-switch should degrade it
`pipeline/briefing/weekly_digest_generator.py:466-470`
```python
else:  # fallback when _smart_generate returns falsy
    covers.append({
        "headline": cluster.get("title", ""),   # NameError: 'cluster' is undefined
        ...
        "cluster_id": cluster.get("id"),
    })
```
`_generate_cover_stories(threads, edition)`'s locals are `thread`, `lead`, `timeline`, `c` — there is no `cluster`. The fallback branch runs exactly when `_smart_generate` returns None (DISABLE_ANTHROPIC set **and** Gemini down/over-budget), so the documented kill-switch degradation chain crashes the whole weekly run instead of producing a fallback cover. Called uncaught from `generate_weekly_digest` (`:1110`).
**Fix:** `cluster` → `lead` (the lead cluster of the thread).

### P0-3 · `/paper` route renders blank for direct visitors (dropped-column query)
`frontend/app/paper/PaperContent.tsx:531`
```ts
const enrichedFields = `...,rank_world,rank_us,rank_europe,rank_south_asia`;
```
Migration 061 dropped `rank_us / rank_europe / rank_south_asia`. PostgREST returns error 42703; the code destructures only `{ data: clusters }` (no `error` check, no fallback — unlike `HomeContent`'s 3-tier fallback), so `clusters` is null → `stories` is `[]` → `/paper` (and `/paper/world/`) render masthead + colophon with zero stories. Dead fallbacks at `:181,183` also name the dropped columns.
**Fix:** trim the select to `rank_world` only; remove the `rank_us/...` fallbacks at 181/183; surface `error`. (`HomeContent.tsx:384`'s `rank_${activeEdition}` cast is **safe** — `activeEdition` is the constant `"world"`, so it orders by `rank_world` and selects only `rank_world`.)

---

## Security — P0/P1

### SEC-1 · Tables shipped without RLS → anon read/write (data poisoning + free-tier DB-fill DoS)
- `supabase/migrations/041_void_verify_claims.sql` creates `article_claims` (`:7`) and `source_claim_accuracy` (`:53`) with **zero** `ENABLE ROW LEVEL SECURITY` / `CREATE POLICY` (verified: 0 matches). On Supabase a public-schema table without RLS is fully read/write via the shipped anon key → anyone can insert/update/delete void --verify claim data.
- `supabase/migrations/034_weekly_digests.sql:65` — `CREATE POLICY "...service role write..." ON weekly_digests FOR ALL USING (true) WITH CHECK (true)` — the name says service-role but `USING (true)` with no role check grants INSERT/UPDATE/DELETE to anon. Anon can overwrite/delete published weekly issues.
- `supabase/migrations/058_sandbox_rls.sql` grants anon INSERT + UPDATE on `sandbox_runs` with **unbounded JSONB** payloads, but the only consumer (the sandbox worker workflow) was deleted — it is now pure attack surface. On the Free-tier 0.5 GB project (the 2026-06-01 near-outage was a table filling toward the cap), an anon actor can fill the DB in minutes.
- `ship_requests`/`ship_replies` (`037`/`038`) are anon-INSERT with no size/rate limit and are in `supabase_realtime` (insert amplified to all clients).
**Fix:** ship migration 062 — enable RLS + `FOR SELECT USING (true)` on `article_claims`, `source_claim_accuracy`; recreate the `weekly_digests` write policy with `auth.role() = 'service_role'`; `REVOKE`/drop the dead `sandbox_runs` anon policies; add a payload-size `CHECK` on `ship_*`. Also enable RLS on the `_migrations` tracker (`migrate.yml:56`) so anon can't pre-insert future filenames and block their application.

### SEC-2 · Auto-merge gate is a no-op; unvalidated code + migrations reach prod
- `.github/workflows/auto-merge-claude.yml:24` — `npx next build || npx next build || npx next build || echo "Build flaky but proceeding"`. The trailing `echo` exits 0, so a **failing build still passes** the gate, and `auto-merge` (`needs: build-check`) always merges `claude/**` → `main`. The bias (`validate-bias.yml`) and clustering (`validate-clustering.yml`) gates run in parallel but are **not required** by the merge job.
- `.github/workflows/migrate.yml` auto-applies migrations from `claude/**` to the **production DB** with the full postgres role, no human review.
**Impact:** any actor who can push a `claude/**` branch ships to `main`/prod and can mutate prod schema, with a meaningless test gate.
**Fix:** drop the `|| echo`; make the merge job depend on the bias + clustering checks (branch protection with required status checks); scope `migrate.yml` to run **after** merge to `main` only.

---

## P1 — Broken features / wrong behavior

### P1-1 · DB cluster UUIDs never written back to in-memory clusters → 3 subsystems silently dead
`pipeline/main.py:2627-2645` collects `cluster_id = result.get("id")` into `cluster_ids_to_enrich` but **never assigns `cluster["_db_id"]` / `cluster["id"]`**; line 2291-2293 leaves `c["id"] = str(id(c))` (a Python object address). Consequences, each verified:
- **WebP image cache is a guaranteed no-op every run.** `cache_cluster_images(clusters, ...)` (`main.py:2991`) → `cluster_image_cacher.py:233-245` filters on a UUID regex and skips every cluster ("Skipped N cluster(s) without a DB UUID"). This is the documented `cached_image_url` 0%-populated symptom; the frontend silently falls back to raw article images (no WebP/LCP optimization).
- **Daily briefs persist empty linkage.** `daily_brief_generator.py` builds `top_cluster_ids` from `c.get("_db_id","")` → always `[]`, `opinion_cluster_id` always NULL. The `[NEW]/[CONTINUING]` tagging, repeat-deprioritization, and the weekly digest's brief-ID signal are all inert. (Note: step-7d brief generation runs **before** step-8 inserts, so a step-8 write-back alone won't fix briefs — generation must move after step 8, or match by title.)
- **Step-8d in-memory summary sync is dead code** (`main.py:2968-2979` keys by `str(id(c))` vs DB UUIDs).
**Fix:** assign `cluster["_db_id"] = cluster_id` in the step-8 loop; reorder brief generation after step 8 (or title-match) to make `top_cluster_ids` real.

### P1-2 · PWA / service worker / icons fully broken on the live Cloudflare origin
The CF build sets `NEXT_PUBLIC_BASE_PATH=""` (root), but these are hardcoded to `/void--news/...`, which 404s on `void-news.pages.dev` (and `_redirects` has no catch-all):
- `frontend/app/layout.tsx:184` — `navigator.serviceWorker.register('/void--news/sw.js')` → SW never registers (offline + installability dead; the `.catch` swallows it).
- `frontend/public/manifest.json:5-7,34-55` — `id`/`start_url`/`scope`/icons all `/void--news/...`.
- `layout.tsx:91-98,157-163` — favicon, apple-touch-icon, 7 iOS splash images.
- `frontend/public/sw.js:8-13` — `PRECACHE_ASSETS` hardcoded; even if registration were fixed, `cache.addAll` rejects (all 404) and SW install fails.
Normal browsing is fine (Next auto-prefixes `<Link>`/`<Image>` with the empty basePath); only PWA/SW/raw-asset paths break. **CLAUDE.md's "PWA installable" status is currently false on the live origin.**
**Fix:** template manifest/SW/asset URLs from `NEXT_PUBLIC_BASE_PATH` (use `BASE_PATH` from `app/lib/utils.ts` for raw anchors); add `/void--news/*  /:splat  301` to `_redirects` as a stopgap (note: a redirected SW *script* URL still fails registration, so the `layout.tsx` line must be fixed in code).

### P1-3 · Dangling `/world` nav link + double-prefixed `next/link` hrefs (404s)
- `frontend/app/components/MobileSidePanel.tsx:143` — `<Link href="/world">` "void --world / International overflow" → route deleted in rev 46. Hard 404 in the Capacitor shells; edge-301 to `/` on CF.
- `frontend/app/components/PipelineFlow.tsx:624` — `<Link href="/void--news/command-center">` and `frontend/app/paper/PaperContent.tsx:493,266,305` (`/void--news/...`) — `next/link` auto-prepends basePath, so these double-prefix (`/void--news/void--news/...` on GH Pages) or 404 on CF.
**Fix:** remove the `/world` link; change the hardcoded hrefs to root-relative (`/command-center`, `/`).

### P1-4 · Unpaginated Supabase selects silently truncate at 1,000 rows
- `pipeline/rerank.py:74-88` — top-level `select(...).execute()` with no `.range()`. The project's own comment at `main.py:1074-1077` documents this PostgREST trap. The 2-day retention window routinely holds >1,000 clusters (orphan-wrapping makes a singleton per unclustered article), so everything past row 1,000 keeps stale `headline_rank`/`rank_world` — the same stale-pin class as the 2026-05-22 regression.
- `pipeline/main.py:1474-1476` — `source_topic_lean` whole-table select; at 1,016 sources × N categories this exceeds 1k → Axis-6 EMA silently partial.
**Fix:** paginate (mirror `_paginated_fetch`), or filter to the retention window.

### P1-5 · Topic-diversity and mid-feed category caps never affect `rank_world`
`pipeline/ranker/feed_ranker.py:142-189` (and the mirror at `main.py:2234-2261`) partition the pool into `promoted`/`deferred`, but the only rank mutation is 0.1-pt tie-spacing **within `promoted`**; deferred clusters keep their original higher `rank_world`, and the reordered `pool` list is local and unused. All consumers sort by `rank_world`, so an over-cap category re-emerges in the top 10 untouched and the positions-10-50 category cap is a complete no-op. CLAUDE.md claims `rank_world = headline_rank × … × topic-diversity × …`; in code only story-type gates, same-event decay, and the feed-lead clamp actually change `rank_world`.
**Fix:** write ranks that encode the final pool order (demote deferred below `promoted[-1]`), as the old `edition_ranker` did.

### P1-6 · Three dead-feature DB selects (nonexistent columns → silently empty)
- `frontend/app/lib/supabase.ts:204` selects `articles.excerpt` (never existed) → `fetchMethodologyArticles` 42703 swallowed at `:209` → the sources-page "live autopsy" section renders nothing. Fix: select `summary`.
- `pipeline/social/ig_generator.py:135` selects `sources.lean_label, lean_score` (never existed; column is `political_lean_baseline`) → every receipt-pillar query raises, caught at `:142`, so the IG "receipt" pillar **never generates a draft**. Fix: use `political_lean_baseline` / rely on the embedded `bias_scores.political_lean`.
- `pipeline/scripts/pipeline_health.py:53-54,69` selects/orders `daily_briefs.generated_at` (never existed) → `brief_health()` 400s every run. Fix: `created_at`.

### P1-7 · Ship-request vote counter never increments
`frontend/app/lib/supabase.ts:435-438` does an anon `UPDATE ship_requests.votes`, but `037:40` grants anon only INSERT+SELECT (UPDATE is service-role). RLS drops the row silently; the function still returns `true`. Votes land in `ship_votes` but the displayed/sorted counter stays frozen.
**Fix:** SECURITY DEFINER RPC `increment_ship_vote(request_id)`, or derive counts from `ship_votes` at read time.

### P1-8 · Weekly digest still iterates the deleted regional editions
`pipeline/briefing/weekly_digest_generator.py:64,1054` default `EDITIONS = ["world","us","europe","south-asia"]`; the three regional editions now always fetch 0 clusters and skip. Should be `["world"]`. (Also `weekly/page.tsx` "Most Contested" never renders — `fetchWeeklyDigest` doesn't select `contested_stories`, so it's always undefined; `supabase.ts:304`.)

---

## P2 — Latent / edge-case / hardening

**Pipeline:**
- `cluster_summarizer.py:1090` hardcodes `summary_tier: "sonnet"` even for Gemini-fallback summaries → the step-8d cache check (`tier == "sonnet"`) permanently skips re-summarizing those clusters with real Sonnet.
- `cluster_summarizer.py:537-541` slices `articles[:max_articles]` **before** sorting, while `_content_hash` hashes the newest 10 of the whole membership → prompt inputs and cache key diverge.
- `main.py:1540-1543` (36h lookback) omits `is_wire_copy,wire_origin_publisher_id` → persisted wire copies re-enter clustering as distinct voices → `source_count` inflation, partially defeating the wire-persistence fix.
- `story_cluster.py:671-688` `MERGE_HARD_CEILING` reads root-cluster `source_count`/`len(articles)` that `union()` never updates → not transitive; two 60-source groups can chain past 120 (contra CLAUDE.md).
- `pipeline_runs.errors` is overwritten by the finalize writer (`main.py:3424-3433`) and the step-8 marker (`:2661-2670`), clobbering `claude_client`'s appended failures.
- `main.py:2683-2700` + `memory_orchestrator.py:62-64` zip `clusters` against `cluster_ids_to_enrich` by index; an early insert failure (`continue` at `:2633`) misaligns them → claims/memory attach to the wrong cluster.
- `memory_orchestrator.py:111` reads `art.get("source_tier")` — pipeline articles carry `tier` → source selection degrades to alphabetical.
- `main.py:2853` `for c in all_clusters` — `all_clusters` is undefined; the NameError is swallowed by the wrapping try every run, so cross-run zero-overlap title dedup never runs (doubly broken by P1-1).
- `daily_brief_generator.py:1094` `_rule_based_opinion` falls back to `cluster.get("id")` = `str(id(c))` at step 7d → invalid-UUID FK on `opinion_cluster_id` could lose the brief row (stub-on-failure covers only generator exceptions, not upsert failures).
- `audio_producer.py:350-728` dead Gemini-TTS code references undefined `GEMINI_TTS_AVAILABLE/genai/types/_TTS_MODEL` — instant NameError if re-enabled.
- `rss_fetcher.py:342` — the global `as_completed(..., timeout=FEED_TIMEOUT*2)` caps the **entire** ~1,000-source fetch at 30s. The per-feed `safe_get` already bounds each feed at 15s; this global cap risks firing on a slow-tail run, marking hundreds of healthy-but-pending feeds `timeout` and quarantining them over 5 runs. Raise/remove it.

**DB / migrations:**
- `003_schema_fixes.sql:46` — `ALTER TABLE ... ADD CONSTRAINT IF NOT EXISTS` is invalid PostgreSQL → a fresh-DB "all" replay halts at 003 and 004-061 never apply (disaster-recovery/bootstrap defect; `chk_confidence_range` likely never existed in prod). Rewrite as a `DO $$ ... IF NOT EXISTS (SELECT 1 FROM pg_constraint ...) $$` block.
- Idempotency gaps: `CREATE TRIGGER` without DROP-first (017/022/037/039/042), `ADD CONSTRAINT` without guards (029), `RENAME COLUMN` (032), `CREATE TABLE/INDEX` without `IF NOT EXISTS` (037/038/039/041/042), `026` backfill `UPDATE rank_us/rank_india` now errors post-061. `migrate.yml` marks a multi-statement file "applied" on the first "already exists", silently skipping later statements.
- `main.py:2727` `_batch_upsert("article_claims", rows, on_conflict="id")` but rows carry no `id` → conflict target never fires; with no unique (article_id, claim_text), repeated runs accumulate duplicate claims.

**Frontend / security:**
- `AudioProvider.tsx` is **not** gated by the audio kill switch (never imports `audioGate`); `fetchDailyBrief` + the hidden `<audio preload="metadata">` (`:454-461`) still fetch mp3 metadata while audio is "disabled". The 7 documented UI surfaces ARE gated; the `<audio>` element is not. Gate it on `AUDIO_ENABLED`.
- `layout.tsx:52` `metadataBase: new URL("https://aacrit.github.io")` + `/void--news/og-image.svg` → all OG/canonical/share URLs point at the deprecated GH Pages origin.
- `sw.js` — cache names (`void-news-v1`) never bumped across rev 46 (GH-Pages installs still serve cached `/world/` HTML offline); `offline.html` exists but is never referenced as the navigation fallback.
- `Sigil.tsx:540-543` `INK_UNDERLINES[data.politicalLean % 3]` throws if `politicalLean` is ever non-integer (`47.5 % 3 = 2.5` → undefined `.d`); currently safe only because `main.py:666` rounds it. Use `Math.round(...)`.
- `sources/page.tsx:581` `Methodology` component is defined but never rendered, yet `DeepDive.tsx:147` and `sources/page.tsx:972` link to `#methodology` → the entire scoring explainer is unreachable.
- `DeepDive.tsx:825,895` `handleShare` reads `liveData` but `useCallback` deps are `[story]` → stale closure ships the empty initial sources array on the Evidence Card.
- `.github/workflows/generate-history-audio.yml:69` interpolates `${{ inputs.slugs }}` unquoted into a `run:` line (shell-injection; gated to write-access today). `_headers:24` CSP allows `unsafe-eval`. A git-tracked `.playwright-mcp/*.log` contains a decoded anon JWT (public-by-design, but logs shouldn't be in git).
- Missing `concurrency:`/`timeout-minutes:` on `pipeline.yml`/`migrate.yml`/`auto-merge` (concurrent `claude/**` pushes race to push `main`; a hung fetch can burn hours of Actions).

---

## P3 — Doc / copy drift
- CLAUDE.md says migrations "001-055" (project-structure line) while the rev-46 header describes 061; disk has 001-061 (62 files, duplicate `053_` prefix). CLAUDE.md still lists a "cipher" game (no such directory) and `fetch=80 / CATEGORY_CAP=12` (HomeContent is `FETCH_LIMIT=100`, no category cap).
- `PipelineFlow.tsx:259,233,271` still describes `edition_ranker.py` writing `rank_us/rank_europe/rank_south_asia` (module deleted, columns dropped) — stale public-facing copy on `/pipeline`.
- CLAUDE.md quick-ref points to `/diag.html`; `frontend/public/` has no `diag.html`.
- `DeepDive.tsx:1443` "Read All Sides &mdash; {n} sources" violates the no-em-dash rule for frontend microcopy.
- `feedCache.ts:16` / `audit-db.yml:7-10` reference a 3×/day pipeline; cadence is 1×/day. `ig_caption` is documented with a Gemini fallback but is Claude-only.

---

## Implementation plan

**Phase 0 — stop the bleeding (P0, ~1 hr, one-liners):**
1. `main.py:2287` `section_val` → `"feed"`, move print out of loop. *(daily pipeline crash)*
2. `weekly_digest_generator.py:466-470` `cluster` → `lead`. *(weekly crash)*
3. `PaperContent.tsx:531` trim select to `rank_world`; drop `:181,183` fallbacks; check `error`. *(blank /paper)*
Each is independently shippable. Add a ground-truth fixture for the recency-gate path so P0-1 can't regress.

**Phase 1 — security migration 062 + workflow gate (P0/P1 security, ~half day):**
4. New migration: RLS on `article_claims`, `source_claim_accuracy`, `_migrations`; fix `weekly_digests` write policy to service-role; drop dead `sandbox_runs` anon policies; size-cap `ship_*` JSONB.
5. `auto-merge-claude.yml`: remove `|| echo`; require `validate-bias` + `validate-clustering`. Scope `migrate.yml` to `main`.

**Phase 2 — restore dead subsystems (P1, ~1 day):**
6. `main.py` step-8: `cluster["_db_id"] = cluster_id` write-back; reorder brief generation after step 8 (unlocks image cache + brief linkage + step-8d sync + title dedup).
7. Paginate `rerank.py:74` and `main.py:1474` selects.
8. Rewrite `feed_ranker` pool ordering into `rank_world`.
9. Frontend: remove `/world` link; fix double-prefixed hrefs; basePath-template manifest/SW/icons + `_redirects` stopgap; gate `AudioProvider`'s `<audio>`.
10. Dead selects: `supabase.ts` `excerpt`→`summary`; `ig_generator` `lean_label/score`→`political_lean_baseline`; `pipeline_health` `generated_at`→`created_at`. Ship-vote RPC. `weekly EDITIONS`→`["world"]`.

**Phase 3 — hardening (P2, schedule):**
11. `summary_tier` real label; wire flags in 36h lookback; transitive merge ceiling; append (not overwrite) `pipeline_runs.errors`; index-safe claims upsert; RSS global-timeout sizing; rewrite migration 003 + idempotency pass; `metadataBase`→CF origin; SW cache version + offline fallback; `Sigil` `Math.round`; render `Methodology`; quote `generate-history-audio` input; add `concurrency`/`timeout-minutes`.

**Phase 4 — doc sweep (P3):** reconcile CLAUDE.md (migrations, cipher, fetch constants, cadence), PipelineFlow copy, em-dash microcopy.

**Suggested first PR:** Phase 0 (3 one-liners) + Phase 1 (security) — highest blast-radius, lowest review cost.
