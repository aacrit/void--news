---
name: ship-queue
description: "void --ship queue: fetch triaged requests from Supabase, present to CEO, pick items to build, update status on completion."
user-invocable: true
disable-model-invocation: false
allowed-tools: Bash, Read, Grep, Glob, Edit, Write, Agent, TaskCreate, TaskUpdate, TaskList
---

# /ship-queue — void --ship Work Queue

You are the orchestrator for the **void --ship** feature request pipeline. This skill connects user-submitted requests to Claude CLI agent work.

## Objective

Query the `ship_requests` table in Supabase, present the prioritized queue to the CEO, and manage the build lifecycle.

## Workflow

### Step 1: Fetch Queue

Run this query against Supabase to get the current queue:

```bash
cd /home/aacrit/projects/void-news
python3 -c "
import os, json
from supabase import create_client
from dotenv import load_dotenv
load_dotenv()
url = os.environ.get('NEXT_PUBLIC_SUPABASE_URL') or os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ.get('NEXT_PUBLIC_SUPABASE_ANON_KEY')
sb = create_client(url, key)
res = sb.table('ship_requests').select('*').in_('status', ['submitted','triaged','building']).order('votes', desc=True).execute()
print(json.dumps(res.data, indent=2, default=str))
"
```

### Step 2: Present Queue to CEO

Display the queue in a formatted table:

| # | Priority | Title | Category | Area | Votes | Status | Age |
|---|----------|-------|----------|------|-------|--------|-----|

Group by status: **Building** first, then **Triaged**, then **Submitted**.

Ask the CEO which item to work on. If no triaged items, suggest the highest-voted submitted item.

### Step 3: Pick & Build

When the CEO picks an item:

1. **Update status to "building"** in Supabase (use SUPABASE_SERVICE_ROLE_KEY)
2. **Create a new branch**: `git checkout -b claude/ship-{short-description}`
3. **Implement the request** using the appropriate agents
4. **On completion, update status to "shipped"** with commit SHA and shipped_at
5. **Commit and push** per CLAUDE.md git workflow

### Step 4: Triage (Optional)

If the CEO wants to triage items instead of building:

- **Approve**: Set status to "triaged", add priority (p0-p3), add ceo_response
- **Reject**: Set status to "wontship", add ceo_response explaining why

## Status Lifecycle

```
submitted -> triaged -> building -> shipped
                    \-> wontship
```

## Notes

- Always use `SUPABASE_SERVICE_ROLE_KEY` for updates (bypasses RLS)
- The frontend at `/ship` shows realtime updates — status changes appear live
- Each shipped item should link to its commit SHA
- Follow CLAUDE.md branch naming: `claude/ship-{description}`
