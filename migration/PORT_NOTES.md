# PORT_NOTES.md — Supabase → SQLite/D1 migration

Everything SQLite cannot express that was present in `supabase/migrations/001`–`079`.
Each line says what the object did and **where its logic must be re-implemented**:
**Worker** (Cloudflare Worker in front of D1, runtime), **Pipeline** (Python, the
local SQLite working DB), or **Dropped** (no longer needed / diagnostic-only).

Consolidated migrations: 001–079 (includes both files numbered 053:
`053_ig_engagement.sql` and `053_is_international.sql`).

Summary counts:
- **RLS**: 8 `ENABLE ROW LEVEL SECURITY`-bearing migrations, ~45 tables RLS-enabled, ~90 `CREATE POLICY` statements — all dropped.
- **Functions / RPCs**: 13 `CREATE FUNCTION` (incl. 4 SECURITY DEFINER RPCs callable from the client) — all dropped.
- **Triggers**: 8 `CREATE TRIGGER` (1 generic `updated_at` fn reused across 6 tables + 2 rate-limit triggers) — all dropped.
- **Views**: 3 (`cluster_bias_summary`, `cluster_claim_summary`, and the redefinitions in 076/078) — all dropped.
- **Extensions / server objects**: `gen_random_uuid()`, `storage.buckets`/`storage.objects`, `supabase_realtime` publication, `auth.role()`, `_migrations` — all dropped/replaced.
- **GIN indexes**: 3 dropped. **Generated tsvector column + its GIN index**: 1 dropped.

---

## 1. Extensions & server-provided objects

| Object | Migrations | What it did | Re-implement |
|---|---|---|---|
| `gen_random_uuid()` (pgcrypto) | 001, 006, 016–075 (every UUID PK default) | Server-side UUID generation for PK defaults. | **Worker + Pipeline** — generate UUIDv4 strings app-side (e.g. `crypto.randomUUID()` in Worker, `uuid4()` in Python) and pass them in INSERTs. SQLite columns are `TEXT PRIMARY KEY` with no default. |
| `now()` default | all timestamptz columns | Server timestamp default. | Translated to SQLite `DEFAULT CURRENT_TIMESTAMP` (UTC ISO-8601). Behaviour-equivalent. |
| `storage.buckets` / `storage.objects` (`ig-renders` public bucket + read/write policies) | 052 | Supabase Storage bucket for rendered IG PNGs (public read, service write) so the Graph API could fetch `image_url`. | **Dropped** — social posting is parked/generate-only. If revived, host renders on **R2** (Cloudflare) and gate writes in the Worker; there is no SQLite analog. |
| `supabase_realtime` publication (`ALTER PUBLICATION ... ADD TABLE ship_requests / ship_replies`) | 037, 038 | Enabled Postgres logical-replication realtime so the frontend Kanban/thread updated live. | **Worker** — D1 has no realtime. Re-implement via polling, a Durable Object, or WebSocket/SSE from the Worker if live ship board is still wanted. |
| `auth.role() = 'service_role'` (used in ~40 write policies) | 022, 034, 037, 038, 039, 042, 066, 062, 075 | Supabase JWT role check distinguishing pipeline (service) from public (anon). | **Worker** — no JWT/role system in D1. The Worker is the sole writer for content tables; enforce "only the pipeline/admin may write" via Worker auth (a shared secret / Cloudflare Access), not per-row SQL. |
| `_migrations` tracker table (RLS enabled, no policies) | 062 | Migration bookkeeping written by `migrate.yml`; RLS locked anon out. | **Dropped** — replace with your own SQLite migration tracker (e.g. a `schema_migrations` table or wrangler d1 migrations). |

---

## 2. Row-Level Security (ALL dropped — SQLite has no RLS)

SQLite has no row-level security. **Every** `ENABLE ROW LEVEL SECURITY` and
`CREATE POLICY` is dropped. Access control moves to the **Worker** (for D1
write tables) or is **moot** (pipeline SQLite is a trusted local/server file;
the read side is served as a static export + build-time reads).

### 2a. Public-read policies (dropped — reads are now open at the SQLite/Worker layer)
`FOR SELECT USING (true)` on: sources, articles, bias_scores, story_clusters,
cluster_articles, categories, article_categories, pipeline_runs (001);
source_topic_lean (006); cluster_archive (016); daily_briefs (017);
story_memory, live_updates (022); weekly_digests (034); ship_requests,
ship_votes (037); ship_replies (038); history_events, history_perspectives,
history_media, history_connections (039); history_arcs + 5 arc tables (042);
article_claims, source_claim_accuracy (062, added to 041 tables); engine_runs,
engine_snapshots, sandbox_runs (058); revolt_events + 4 revolt tables (066);
printed_days, printed_stories (075).
→ **Re-implement**: nothing to enforce for reads (public data). The Worker
should expose read endpoints (or the static build reads the SQLite file directly).

### 2b. Service-role-write policies (dropped — Worker is the sole writer)
`FOR INSERT/UPDATE/DELETE ... auth.role() = 'service_role'` on: story_memory,
live_updates (022); weekly_digests (034, **fixed in 062** — the 034 version was
`USING(true)`, anon-writable; 062 recreated it with a real role check);
history_* (039, 042); revolt_* (066).
→ **Worker/Pipeline**: these tables are written only by the pipeline. Keep them
out of the D1 write surface entirely; the pipeline writes them into the local
SQLite working DB directly.

### 2c. Deny-all policies (dropped)
`ig_posts_no_anon` (052) and `ig_engagement_no_anon_*` on ig_comments/ig_dms/
ig_mentions/ig_hashtag_candidates (053): `FOR ALL TO anon USING(false)`.
→ **Dropped** — these tables have no browser access at all; keep them
pipeline/server-only (never expose via the Worker's public API).

### 2d. Public INSERT policies (the security-relevant ones → Worker)
- `ship_requests_public_insert` (037, **hardened in 068**): 068 replaced the
  open `WITH CHECK (true)` with a strict check — anon insert allowed **only** when
  `status='submitted' AND votes=0 AND priority IS NULL AND ceo_response IS NULL
  AND claude_branch IS NULL AND shipped_commit IS NULL AND shipped_diff_summary
  IS NULL AND triaged_at IS NULL AND shipped_at IS NULL AND ip_hash IS NOT NULL`.
  → **Worker (REQUIRED)**: enforce exactly these constraints on the public
  submit endpoint. Do not accept client-supplied privileged columns; set
  `status='submitted'`, `votes=0` server-side; require an `ip_hash`.
- `ship_votes_public_insert` (037): open insert, dedup by `UNIQUE(request_id,
  fingerprint)` (kept as a table constraint in D1).
  → **Worker**: accept the vote; the UNIQUE index rejects duplicates.
- `ship_replies_public_insert` (038): open insert.
  → **Worker**: accept + apply rate limits (see §4).

### 2e. Column-level privilege revoke (068)
`REVOKE SELECT (device_info, ip_hash) ON ship_requests FROM anon, authenticated`.
→ **Worker (REQUIRED)**: never return `device_info` / `ip_hash` in the public
read endpoint. The frontend already selects an explicit column list that omits
them (`fetchShipRequests`); the Worker's read query must do the same.

### 2f. sandbox_runs anon write (058) — later revoked (062)
058 granted anon INSERT + UPDATE-recent on `sandbox_runs`; 062 dropped both
(dead diag.html consumer, DB-fill DoS risk). Net: no anon writes. → **Dropped.**

---

## 3. Functions / RPCs (ALL dropped — SQLite has no PL/pgSQL or callable RPCs)

| Function | Migrations | What it did | Re-implement |
|---|---|---|---|
| `sync_ship_votes(uuid)` — **SECURITY DEFINER, client-callable** | 062 | Recounts `ship_votes` for a request and writes `COUNT(*)` into `ship_requests.votes` (idempotent; anon can't UPDATE votes directly under RLS). Called by the browser via `.rpc('sync_ship_votes', ...)` in `voteOnShipRequest`. | **Worker (REQUIRED)** — expose a `/vote` endpoint that (1) inserts the ship_vote (dedup via UNIQUE), then (2) `UPDATE ship_requests SET votes = (SELECT count(*) FROM ship_votes WHERE request_id = ?) WHERE id = ?` and returns the new count. Idempotent recount preserves the anti-inflation property. |
| `refresh_cluster_enrichment(uuid)` — **SECURITY DEFINER** | 002, 004, 076, 078 (redefined 4×) | Reads `cluster_bias_summary`, computes divergence_score + the whole `bias_diversity` JSON (avg lean/sensationalism/opinion/rigor/framing, spreads, tier_breakdown, coverage_score, opinion_label, aggregate_confidence, 7-bucket lean histogram, L/C/R counts, polarization, lean_measured/total counts), writes both back to `story_clusters`. Latest logic (078) computes lean aggregates over the **measured** subset (`lean_unscored = FALSE`). | **Pipeline** — already mirrored in `pipeline/utils/bias_aggregation.py` (the doc/migrations say the Python fallback matches the RPC byte-for-byte). Compute `divergence_score` + `bias_diversity` in Python and write to the SQLite `story_clusters` row. The SQL view/RPC is not needed. |
| `cleanup_stale_articles(int=8)` — SECURITY (revoked from anon) | 050 | `DELETE FROM articles WHERE published_at < now() - N days` (cascades to bias_scores, cluster_articles, article_categories). | **Pipeline** — run the equivalent `DELETE` in Python during the cleanup phase (SQLite cascades via `ON DELETE CASCADE` with `PRAGMA foreign_keys=ON`). |
| `cleanup_stale_clusters(int=7)` | 003 | `DELETE FROM story_clusters WHERE first_published < now() - N days`. | **Pipeline** — Python `DELETE`. |
| `cleanup_stuck_pipeline_runs(int=30)` | 003 | Marks `running` runs older than N minutes as `failed` and appends an error JSON. | **Pipeline** — Python `UPDATE`. |
| `cleanup_stale_engine_snapshots(int=3)` (SECURITY DEFINER) | 060 | Prune engine_snapshots older than N days. | **Pipeline** (or Dropped — writer disabled). |
| `cleanup_stale_engine_runs(int=14)` (SECURITY DEFINER) | 060 | Prune engine_runs. | **Pipeline** / Dropped. |
| `cleanup_stale_sandbox_runs(int=7)` (SECURITY DEFINER) | 060 | Prune sandbox_runs. | **Pipeline** / Dropped. |
| `cleanup_diagnostic_tables(int,int,int)` (SECURITY DEFINER) | 060 | Master prune of the 3 diagnostic tables; returns a JSON breakdown + `pg_database_size`. | **Pipeline** / Dropped. `pg_database_size` has no SQLite analog (use file size). |
| `printed_archive_stats()` — **SECURITY DEFINER, client-callable** | 075 | Returns `{days, stories, total_mb, kb_per_day}` via `pg_total_relation_size`. | **Worker** (if the archive-size UI is kept) — compute counts with SQL; approximate size from `page_count*page_size` (PRAGMA) or `dbstat`. Or **Pipeline**-precomputed. |
| `search_printed_stories(text,int,int,date,date,text,bool)` — **SECURITY DEFINER, client-callable** | 075 | Full-text search over `printed_stories` using `websearch_to_tsquery` + `ts_rank_cd`, scaled by coverage breadth and age decay; `collapse_threads` returns one hit per story thread. | **Worker (REQUIRED if archive search ships)** — Postgres FTS has no SQLite equivalent as-is. Build an **FTS5** virtual table over (title, summary, search_terms) and re-implement ranking (`bm25()` + the source_count/age multipliers) and the thread-collapse (`GROUP BY story_thread_id` picking best rank) in the Worker query. |
| `update_updated_at_column()` (trigger fn) | 005 | Generic `NEW.updated_at = now()` used by 6 triggers. | **Pipeline/Worker** — set `updated_at` explicitly in UPDATE statements, or add per-table SQLite `AFTER UPDATE` triggers (see §4). |
| `set_ig_posts_updated_at()` (trigger fn) | 052 | ig_posts-specific updated_at bump. | Same as above. |
| `ship_requests_rate_limit()` (trigger fn, SECURITY DEFINER) | 068 | See §4. | **Worker.** |
| `ship_replies_rate_limit()` (trigger fn, SECURITY DEFINER) | 068, 070 | See §4. | **Worker.** |

GRANT/REVOKE statements (029, 050, 060, 062, 075) that scoped EXECUTE on these
functions to `service_role` / `anon` are **dropped** with the functions.

---

## 4. Triggers (ALL dropped — logic moves to Worker or Pipeline)

| Trigger | Table(s) | Migrations | What it did | Re-implement |
|---|---|---|---|---|
| `set_articles_updated_at`, `set_story_clusters_updated_at` | articles, story_clusters | 005 | `updated_at = now()` before UPDATE. | **Pipeline** — set explicitly or add a SQLite `CREATE TRIGGER ... AFTER UPDATE ... SET updated_at = CURRENT_TIMESTAMP`. |
| `update_daily_briefs_updated_at` | daily_briefs | 017 | updated_at bump. | Pipeline. |
| `update_story_memory_updated_at` | story_memory | 022 | updated_at bump. | Pipeline. |
| `set_ship_requests_updated_at` | ship_requests | 037 | updated_at bump. | **Worker** — set `updated_at = CURRENT_TIMESTAMP` on every UPDATE, or add a D1 AFTER UPDATE trigger. |
| `set_history_events_updated_at`, `set_history_arcs_updated_at`, `set_revolt_events_updated_at` | history_events, history_arcs, revolt_events | 039, 042, 066 | updated_at bump. | Pipeline. |
| `trg_ig_posts_updated_at` | ig_posts | 052 | updated_at bump. | Pipeline/server. |
| `ship_requests_rate_limit_trg` (BEFORE INSERT) | ship_requests | 068 | Rejects insert if the same `ip_hash` submitted **≥5 in the last hour**, or if **≥120 total inserts in the last hour** (global anti-DoS backstop). | **Worker (REQUIRED)** — count recent rows by ip_hash and globally before inserting; reject over threshold. D1/SQLite can't run the SECURITY DEFINER count in a trigger portably. |
| `ship_replies_rate_limit_trg` (BEFORE INSERT) | ship_replies | 068 (per-fp), 070 (global) | Rejects insert if the same `fingerprint` posted **≥15 in the last hour**, or if **≥200 total replies in the last hour** (global backstop, added 070). | **Worker (REQUIRED)** — same pattern: per-fingerprint + global hourly caps. |

---

## 5. Views (dropped — SQLite lacks STDDEV / FILTER-in-aggregate portability)

| View | Migrations | What it did | Re-implement |
|---|---|---|---|
| `cluster_bias_summary` | 002, redefined 076, redefined 078 | Per-cluster aggregation of `bias_scores`: rigor-weighted mean lean, avg sensationalism/opinion/rigor/framing, STDDEV spreads, lean_range, `aggregate_confidence`, 3-segment L/C/R + 7-bucket histogram, `lean_measured_count`/`lean_total_count`. Latest (078) filters lean aggregates to `lean_unscored = FALSE`. Consumed by `refresh_cluster_enrichment`. | **Pipeline** — reproduced in `pipeline/utils/bias_aggregation.py`. Do the aggregation in Python (SQLite has no `STDDEV`; `FILTER` is supported in modern SQLite but the whole view is redundant once the pipeline computes `bias_diversity` directly). |
| `cluster_claim_summary` | 041 | Flattens `story_clusters.claim_consensus` JSON into columns (consensus_ratio, total_claims, disputed_count, consensus_summary) for the frontend. | **Worker/Pipeline** — read `claim_consensus` JSON with SQLite `json_extract()` at query time, or precompute columns in the pipeline. |

---

## 6. GIN / GiST indexes (dropped — no SQLite equivalent)

| Index | Migration | On | Re-implement |
|---|---|---|---|
| `idx_clusters_sections_gin` | 011 | `story_clusters USING GIN(sections)` (array containment `@> ARRAY['india']`). | **Dropped** — editions collapsed to single "world" feed (061); `sections` is always `["world"]`. If array queries return, use `json_each()` or a bridge table. |
| `idx_cluster_archive_section` | 016 | `cluster_archive USING GIN(sections)`. | **Dropped** — same; query via `json_each()` if needed. |
| `idx_printed_search` (+ generated `search_tsv tsvector` column) | 075 | GIN full-text index over a `STORED` generated `tsvector` of title(A)/summary(B)/search_terms(C). | **Worker** — SQLite has no `tsvector`. The generated column is dropped in `schema_pipeline.sql`. Build an **FTS5** virtual table `printed_stories_fts(title, summary, search_terms)` kept in sync by the pipeline (or SQLite triggers) and query it for `/story` archive search (pairs with the `search_printed_stories` re-implementation in §3). |

Also note: many **partial** indexes (`WHERE ...`) were preserved — SQLite
supports partial indexes. Boolean predicates were rewritten `= TRUE`/`= FALSE`
→ `= 1`/`= 0`. No partial index used a non-deterministic predicate (e.g. `now()`),
so all were portable.

---

## 7. Data-migration / one-shot statements (not schema — informational)

Several migrations ran one-shot data fixes that are **not** part of a fresh
schema and were not carried over: orphaned-article backfills (014, 048),
junction-table cascade cleanups (046, 047), section-value re-routes (012, 032,
036), CGTN/slug corrections (015), mega-cluster cap backfill (056, 059),
`is_international` backfill (053), and the 060 one-shot `DELETE FROM
engine_snapshots`. Fresh SQLite DBs start empty; these are historical.

---

## 8. CHECK constraints dropped as non-portable

None required dropping for PG-only functions — all surviving CHECKs use plain
comparisons / `IN (...)` / `BETWEEN`, which SQLite supports. Two `char_length()`
CHECKs (ship_requests.description ≤2000, ship_replies.body ≤280) were rewritten
to SQLite `length()` and **kept**. The `printed_stories` generated `tsvector`
column (not a CHECK) was dropped (see §6).
