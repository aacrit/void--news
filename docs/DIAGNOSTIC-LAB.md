# Diagnostic Lab — `/diag.html`

Standalone single-file diagnostic UI for the void --news pipeline. Lives at `frontend/public/diag.html`; deploys with the rest of the static site to `void-news.pages.dev/diag.html`.

**Dark premium theme** — warm-black ink + gold accent + terminal-grade typography (Playfair Display / Inter / IBM Plex Mono). 39 pipeline steps mapped, color-coded by type, with live DB examples and a $0 sandbox.

**Mobile-optimized layout** — below 768px, the page switches from 3-column desktop to a single-column app with sticky top bar (logo + cost chip + settings) and bottom tab bar (Steps · Trace · Tune · Run). Not a responsive squash — a separate optimized view with bigger tap targets and bottom-sheet panels.

## What it does

1. **Visualizes** every step the engine takes each day, color-coded by type so LLM steps (crimson) jump out from rule-based steps (green / blue / brass / etc.)
2. **Pulls live DB examples** on double-click — the latest rows that step actually produced
3. **Surfaces cost in real time** — today's Sonnet call count + 7-day average + a "DISABLE_ANTHROPIC" kill-switch command copier
4. **Traces a specific cluster** through every step — paste a cluster_id or headline keyword, see which phase merged it, which gate it failed, what its final headline_rank is
5. **Re-runs the rule-based engine** with parameter overrides at $0 cost via three trigger paths (local sidecar / clipboard CLI / GitHub Actions workflow_dispatch)
6. **Compares pipeline runs** side-by-side (run picker + compare-to dropdown)

## First-time setup

1. Open `frontend/public/diag.html` — either locally (`file://...`) or hosted at `void-news.pages.dev/diag.html`.
2. **Settings modal opens automatically** on first load. Paste your Supabase project URL + the anon key (NEVER the service role). Both come from your project's `.env`. Hit **Test connection** to confirm before saving.
3. Saved credentials live in `localStorage` only. Nothing leaves your device. The anon key is meant to be public — RLS policies enforce access control server-side.
4. The connection diagnostic banner under the masthead tells you what works:
   - **Red** — no creds or auth failed. Click "Configure".
   - **Yellow** — connected, but migrations 057 + 058 aren't applied yet. Step examples still work; sandbox + run picker are limited.
   - **Green** — everything live.
5. To unlock the sandbox: apply `supabase/migrations/057_engine_snapshots.sql` + `058_sandbox_rls.sql` (creates `engine_runs`, `engine_snapshots`, `sandbox_runs` with RLS) and trigger one production pipeline run so `engine_snapshots` has a baseline.

## Anatomy

**Desktop (≥768px)**
```
+----------------------------------------------------------+
| Masthead — title, run, snapshot, settings gear           |
+----------------------------------------------------------+
| Connection diagnostic banner (red/yellow/green)          |
+--------------+-----------------------+-------------------+
| Left rail    | Main column           | Right rail        |
| Run picker   | 39 numbered step      | Claude cost panel |
| Step TOC     |   cards (vertical     | Cluster trace     |
|   w/ dots    |   newspaper layout)   | Knob drawer       |
|   + health   |   click=expand        | Re-run triggers   |
|              |   dblclick=DB pull    |                   |
+--------------+-----------------------+-------------------+
```

**Mobile (<768px)**
```
+----------------------------------+
| Top bar — brand + cost + gear   |
| Banner strip (1-line status)    |
+----------------------------------+
|                                  |
|  Active tab content              |
|  (Steps · Trace · Tune · Run)    |
|                                  |
+----------------------------------+
| Bottom tab bar (4 tabs)         |
+----------------------------------+
```

Keyboard shortcuts (desktop): <kbd>S</kbd> open settings · <kbd>/</kbd> or <kbd>T</kbd> focus trace input · <kbd>Esc</kbd> close modal.

## Step type colors

| Type        | Color           | Step examples                                     |
|-------------|-----------------|---------------------------------------------------|
| FETCH       | Ink black       | Load sources, fetch RSS, scrape article text     |
| PARSE       | Graphite        | Filter known URLs, wire-aware dedup              |
| CLUSTER     | Forest green    | The 7-phase clustering engine                    |
| ANALYZE     | Slate blue      | The 6 bias axes                                  |
| CATEGORIZE  | Terracotta      | URL+section+NLP categorizer                      |
| RANK        | Brass           | 10-signal importance ranker                      |
| RERANK      | Claret          | Holistic rerank, diversity cap, recency gate     |
| SUMMARIZE   | Crimson         | LLM steps (cluster summary, daily brief) — $$    |
| CACHE       | Silver          | WebP image cache                                 |
| OUTPUT      | Bronze          | DB writes                                        |

## Interactions

| Trigger | Effect |
|---|---|
| **Single click on step card** | Expand inline detail: rationale, inputs, outputs, gates, failure mode, gotchas, file:line |
| **Double click on step card** | Fire live Supabase query; render the latest rows that step produced |
| **Right click on step card** | (Planned) Trace a specific cluster's behavior at that step across runs |
| **TOC item click** | Scroll to step card; health dot is colored by step's 7-day failure rate |
| **Knob input change** | Highlights changed in claret; included in next replay's overrides |

## Re-run paths

Three ways to trigger a $0 replay. All converge on `pipeline.sandbox_replay.replay()`.

### 1. Local sidecar (fastest, 5-15s)

```bash
pip install fastapi uvicorn  # one-time
python -m pipeline.sandbox_server
```

Then in the UI click "Sidecar (fastest)". Result lands in `sandbox_runs.result_payload` and the UI updates immediately.

### 2. Copy CLI (offline-friendly)

Click "Copy CLI". UI puts `python -m pipeline.sandbox_replay --params '{...}'` on your clipboard. Paste into any terminal. UI polls `sandbox_runs.status`.

### 3. GitHub Actions (zero local deps)

Click "GitHub Actions". UI copies the overrides JSON. Open Actions → "Sandbox Replay" → "Run workflow" → paste overrides → dispatch. Runs in ~1-2 min on ubuntu-latest.

## How to add a new step card

1. Open `frontend/public/diag.html`, find the `STEPS = [...]` array.
2. Append a new step object:
   ```js
   { n: 33, name: "Your step name", type: "ANALYZE", file: "module/file.py · function()",
     purpose: "One sentence describing what this step does and why.",
     inputs: "what tables/state it reads",
     outputs: "what tables/state it writes",
     gates: "any env vars, thresholds, or conditional skips",
     fail: "what happens when this step fails",
     gotcha: "optional — recent fix annotation or known surprise",
     example_query: { table: "...", select: "id,col1,col2", order: ["created_at", false], limit: 5 } }
   ```
3. Pick a `type` from the palette table above; the card + TOC dot get colored automatically.
4. `example_query` is what fires on double-click. Use the [supabase-js query builder syntax](https://supabase.com/docs/reference/javascript/select).
5. No build step. Reload the page; the new card appears.

## How to add a new tuneable knob

1. In `frontend/public/diag.html`, find the `KNOBS = {...}` object.
2. Add the knob to its category (`clustering`, `ranker`, `bias`, `categorizer`) with the production default value.
3. In `pipeline/sandbox_replay.py`, `_apply_<category>_overrides()` already patches `setattr(module, key, val)` for any matching attr — works automatically if the constant lives in the corresponding module (`clustering.story_cluster` or `ranker.importance_ranker`).
4. For knobs that live elsewhere (e.g. categorizer URL pattern priorities), extend `_apply_*_overrides()` with the patching logic.

## Engine snapshot contract

The lab depends on `engine_snapshots.payload` (jsonb), written at end of pipeline step 8c.6. Shape:

```json
{
  "schema_version": 1,
  "created_at": "ISO timestamp",
  "articles":     [{...}],
  "clusters":     [{...}],
  "rankings":     {"top_50_world": [cluster_ids], "per_section": {...}},
  "phase_traces": {"phase_2_6_merges": [...], "phase_5_caps": [...]}
}
```

Production runs write this at the end of the rule-based stage; the editorial layer (Stage B: cluster summarizer, daily brief, etc.) reads from here without touching engine state. Sandbox replays use this as the baseline for parameter-overridden re-runs.

## Why this exists

Before the lab, every pipeline regression took 4-6 hours to debug:

1. Spot a wrong result on the homepage
2. Read logs from GitHub Actions
3. Write ad-hoc SQL to triangulate
4. Guess at the offending step
5. Patch + push + wait for next 11:00 UTC run + check tomorrow

With the lab:

1. Spot wrong result
2. Paste cluster_id into trace tool — see exactly which phase touched it
3. Drop knob in the drawer (e.g. `ANCHOR_DOC_FREQ_FRACTION: 0.015`)
4. Click "Re-run (sidecar)"
5. 8s later: see if the change fixes the cluster
6. If yes: ship the constant change. If no: try the next knob.

30 seconds vs 6 hours. The cost emergency that motivated this (Anthropic balance ~$10, Sonnet at $1/day) makes the savings tangible: the lab pays for itself in a single avoided overspend cycle.
