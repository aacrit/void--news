# Diagnostic Lab — `/diag.html`

Standalone single-file diagnostic UI for the void --news pipeline. Lives at `frontend/public/diag.html`; deploys with the rest of the static site to `void-news.pages.dev/diag.html`. Press & Precision aesthetic — sepia parchment + ink cards + Playfair / Inter / Plex Mono.

## What it does

1. **Visualizes** every step the engine takes each day, color-coded by type so LLM steps (crimson) jump out from rule-based steps (green / blue / brass / etc.)
2. **Pulls live DB examples** on double-click — the latest rows that step actually produced
3. **Surfaces cost in real time** — today's Sonnet call count + 7-day average + a "DISABLE_ANTHROPIC" kill-switch command copier
4. **Traces a specific cluster** through every step — paste a cluster_id or headline keyword, see which phase merged it, which gate it failed, what its final headline_rank is
5. **Re-runs the rule-based engine** with parameter overrides at $0 cost via three trigger paths (local sidecar / clipboard CLI / GitHub Actions workflow_dispatch)
6. **Compares pipeline runs** side-by-side (run picker + compare-to dropdown)

## First-time setup

1. **Apply migrations 057 + 058** to your Supabase project — they create `engine_runs`, `engine_snapshots`, `sandbox_runs` plus RLS policies.
2. **Trigger one production pipeline run** so `engine_snapshots` has at least one row to baseline against.
3. Open `frontend/public/diag.html` — either locally (`file://...`) or hosted at `void-news.pages.dev/diag.html`. The first load prompts for your Supabase URL + anon key; both are saved to localStorage thereafter.

## Anatomy

```
+----------------------------------------------------------+
| Masthead — title, run timestamp, snapshot id            |
+--------------+-----------------------+-------------------+
| Left rail    | Main column           | Right rail        |
| Run picker   | 32 numbered step      | Claude cost panel |
| Step TOC     |   cards (vertical     | Cluster trace     |
|   w/ health  |   newspaper layout)   | Knob drawer       |
|   dots       |   click=expand        | Re-run triggers   |
|              |   dblclick=DB pull    |                   |
+--------------+-----------------------+-------------------+
```

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
