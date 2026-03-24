# News Memory Engine — Technical Runbook
**Implementation Guide for Engineering Team**

Date: 2026-03-24
Status: Pre-Implementation

---

## Quick Start

This runbook guides implementation of the News Memory Engine across the full stack.

### Key Terms
- **Top Story** — The #1 ranked cluster from the latest pipeline run (highest importance_score)
- **Story Memory** — Metadata record tracking a cluster across pipeline runs (in story_memory table)
- **Live Update** — New article discovered by the live poller that matches the top story (in live_updates table)
- **Live Poller** — Lightweight daemon that polls only the top story's sources every 30 min
- **Memory Orchestrator** — Backend logic that syncs story_memory state with pipeline rankings

---

## Phase 1: Database & Backend (Days 1-3)

### Step 1.1: Create Migration 022

**File:** `supabase/migrations/022_story_memory.sql`

Copy the full migration from the proposal (Appendix above). Key tables:
- `story_memory` — tracks cluster continuity, source list, state flags
- `live_updates` — captures articles discovered between pipeline runs

**Testing:**
```bash
# After merging to main, confirm migration runs via GitHub Actions
# Check via Supabase Dashboard: Storage > SQL Editor
SELECT COUNT(*) FROM story_memory;  -- should be 0 initially
SELECT COUNT(*) FROM live_updates;  -- should be 0 initially
```

### Step 1.2: Implement memory_orchestrator.py

**File:** `pipeline/memory/memory_orchestrator.py`

Core logic (see proposal pseudocode):

1. **After each pipeline run**, deactivate old top story, activate new top story
2. **Extract source IDs** from cluster articles
3. **Map source UUIDs to slugs** (lookup in sources table)
4. **Create or update story_memory record**

**Key functions:**
```python
def update_memory_after_pipeline_run(pipeline_run_id: str, top_story_cluster_id: str) -> dict
def cleanup_old_memories(ttl_hours: int = 48) -> dict
def extract_source_slugs_from_cluster(cluster_id: str) -> list[str]
```

**Error handling:**
- If source lookup fails, log warning but continue (story_memory still created)
- If Supabase write fails, log error and raise (pipeline alerts on this)
- Graceful degradation: story_memory creation optional (main pipeline doesn't depend on it)

**Testing locally:**
```bash
cd /home/user/void--news
python -c "
from pipeline.memory.memory_orchestrator import update_memory_after_pipeline_run
import uuid

# Test with dummy cluster ID (won't work without real pipeline run, but tests syntax)
try:
    result = update_memory_after_pipeline_run(str(uuid.uuid4()), str(uuid.uuid4()))
    print('✓ Function callable')
except Exception as e:
    print(f'✗ Error: {e}')
"
```

### Step 1.3: Integrate Into main.py

**File:** `pipeline/main.py`

After step 11 (ranking), before step 12 (write clusters to DB):

```python
# Step 11b: Update memory engine with new top story
if MEMORY_AVAILABLE:
    try:
        from memory.memory_orchestrator import update_memory_after_pipeline_run
        top_cluster_id = ranked_clusters[0]['id']
        memory_result = update_memory_after_pipeline_run(pipeline_run.id, top_cluster_id)
        print(f"[✓] Memory engine: {memory_result}")
    except Exception as e:
        print(f"[warn] Memory engine update failed: {e}")
        # Don't crash pipeline — memory is optional
```

**Testing:**
```bash
# Manual pipeline run with --quick flag
python pipeline/main.py --quick

# Then check memory was created:
python -c "
from pipeline.utils.supabase_client import supabase
result = supabase.table('story_memory').select('*').order('created_at', desc=True).limit(1).execute()
if result.data:
    print(f'✓ Top story memory: {result.data[0][\"headline\"]}')
else:
    print('✗ No story_memory created')
"
```

### Step 1.4: Integration Testing

**Checklist:**
- [ ] Migration 022 runs without errors
- [ ] story_memory table exists with correct columns
- [ ] live_updates table exists with correct columns
- [ ] Full pipeline run completes without errors
- [ ] story_memory record created for top cluster
- [ ] source_ids array populated correctly
- [ ] is_top_story flag = true for top cluster

---

## Phase 2: Live Polling (Days 4-7)

### Step 2.1: Implement live_poller.py

**File:** `pipeline/memory/live_poller.py`

Core flow:

```python
def live_poll_for_top_story() -> dict:
    """Main entry point."""

    # 1. Get active top story
    # 2. Load target sources
    # 3. Fetch RSS from those sources
    # 4. Find new articles (not in live_updates)
    # 5. Scrape full text (reuse scraper)
    # 6. Summarize with Gemini
    # 7. Insert into live_updates
    # 8. Update story_memory timestamp
    # 9. Return report

if __name__ == '__main__':
    import json
    result = live_poll_for_top_story()
    print(json.dumps(result, indent=2, default=str))
```

**Key design decisions:**

1. **Reuse existing scrapers/fetchers:**
   ```python
   from pipeline.fetchers.rss_fetcher import fetch_from_rss
   from pipeline.fetchers.web_scraper import scrape_article
   ```

2. **Gemini prompt for delta summary:**
   ```python
   DELTA_SUMMARY_PROMPT = """Summarize the KEY UPDATE in this article.
   What is NEW compared to prior reporting on {story_headline}?
   Focus on new facts, quotes, policy changes, not context.
   Write 1-2 sentences max.

   Title: {title}
   Source: {source}
   Summary: {summary}
   Body: {body_first_2000_chars}
   """
   ```

3. **Error handling:**
   - Scrape failure: skip article, log warning (don't crash)
   - Gemini failure: insert without summary, mark summarized_at = null
   - RSS fetch timeout: log and continue to next source

4. **Rate limiting:**
   ```python
   # Max 10 Gemini calls per run, queue overflow
   new_articles = new_articles[:10]
   ```

**Testing locally:**

```bash
# First, ensure there's a top story in story_memory
python pipeline/main.py --quick

# Then run the poller manually
cd /home/user/void--news
SUPABASE_URL=xxx SUPABASE_KEY=yyy GEMINI_API_KEY=zzz \
python pipeline/memory/live_poller.py

# Check live_updates were created
python -c "
from pipeline.utils.supabase_client import supabase
result = supabase.table('live_updates').select('*').order('created_at', desc=True).limit(5).execute()
print(f'Found {len(result.data)} live updates')
for u in result.data:
    print(f'  - {u[\"source_name\"]}: {u[\"title\"][:60]}')
"
```

### Step 2.2: Create GitHub Actions Workflow

**File:** `.github/workflows/live-poll.yml`

Trigger: every 30 minutes, 24/7

```yaml
name: Live Story Polling
on:
  schedule:
    - cron: '0,30 * * * *'  # Every 30 min (48 runs/day)
  workflow_dispatch:

jobs:
  live-poll:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
          cache-dependency-path: pipeline/requirements.txt
      - name: Install dependencies
        run: pip install -r pipeline/requirements.txt
      - name: Install Playwright
        run: playwright install chromium --with-deps
      - name: Run live poller
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: python pipeline/memory/live_poller.py --json > /tmp/poll-result.json
      - name: Report status
        if: always()
        run: cat /tmp/poll-result.json || echo "{\"status\": \"failed\"}"
```

**Testing the workflow:**
1. Commit and push to `claude/*` branch
2. Manually trigger via GitHub Actions UI: "Live Story Polling" > "Run workflow" > "Run workflow"
3. Check logs for success/failure
4. Verify live_updates created in Supabase

### Step 2.3: Load Testing

**Scenario:** Simulate a major breaking news event (50 new articles in 30 min)

```python
# Script: test-live-poller-load.py
import time
from pipeline.memory.live_poller import live_poll_for_top_story

start = time.time()
for i in range(3):  # Simulate 3 consecutive polls
    result = live_poll_for_top_story()
    print(f"Run {i+1}: {result}")
    time.sleep(1)

elapsed = time.time() - start
print(f"Total time: {elapsed:.1f}s")
print(f"Avg time/run: {elapsed/3:.1f}s")
```

**Expected results:**
- Completes in <30s per run
- Gemini calls <30 RPD total
- No database errors

---

## Phase 3: Frontend (Days 8-14)

### Step 3.1: Create Migration 023 (Denormalization)

**File:** `supabase/migrations/023_top_story_denorm.sql`

Add columns to `story_clusters` for fast frontend queries:

```sql
ALTER TABLE story_clusters
  ADD COLUMN IF NOT EXISTS is_top_story BOOLEAN DEFAULT false,
  ADD COLUMN IF NOT EXISTS live_update_count INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_live_update_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS story_memory_id UUID REFERENCES story_memory(id) ON DELETE SET NULL;

CREATE INDEX idx_clusters_top_story ON story_clusters(is_top_story);
CREATE INDEX idx_clusters_top_story_updated ON story_clusters(is_top_story, last_live_update_at DESC);
```

**Why denormalize?**
- Frontend fetch pattern: `SELECT * FROM story_clusters WHERE section = $1 ORDER BY importance_score DESC`
- Adding joins to story_memory for every query is expensive
- Denormalizing means one UPDATE after memory_orchestrator runs

**Keep in sync:**
```python
# In memory_orchestrator.py, when updating story_memory:
supabase.table('story_clusters').update({
    'is_top_story': True,
    'story_memory_id': memory_id,
}).eq('id', cluster_id).execute()
```

### Step 3.2: Update LeadStory Component

**File:** `frontend/app/components/LeadStory.tsx`

Add live update badge:

```tsx
import { timeAgo } from "../lib/utils";

interface LeadStoryProps {
  story: Story;
  // ... existing props
}

export default function LeadStory({ story, ...props }: LeadStoryProps) {
  const isTopStory = story.is_top_story;
  const liveUpdateCount = story.live_update_count || 0;
  const lastLiveUpdate = story.last_live_update_at
    ? new Date(story.last_live_update_at)
    : null;

  return (
    <article className="lead-story" {...props}>
      {isTopStory && (
        <div className="lead-story__badge">
          <span className="badge-icon" aria-hidden="true">●</span>
          <span className="badge-text">Top Story</span>
          {lastLiveUpdate && (
            <time className="badge-time" dateTime={lastLiveUpdate.toISOString()}>
              Updated {timeAgo(lastLiveUpdate)}
            </time>
          )}
          {liveUpdateCount > 0 && (
            <span className="badge-count" aria-label={`${liveUpdateCount} live updates`}>
              +{liveUpdateCount}
            </span>
          )}
        </div>
      )}
      {/* Existing lead story content */}
    </article>
  );
}
```

**Testing:**
- Render with `is_top_story: true`, verify badge appears
- Render with `is_top_story: false`, verify badge hidden
- Render with `live_update_count: 3`, verify "+3" badge shows

### Step 3.3: Create LiveUpdatesSection Component

**File:** `frontend/app/components/LiveUpdatesSection.tsx` (NEW)

```tsx
"use client";

import { useState, useEffect } from "react";
import { supabase } from "../lib/supabase";
import type { LiveUpdate } from "../lib/types";
import { timeAgo } from "../lib/utils";

interface LiveUpdatesSectionProps {
  storyMemoryId: string;
}

export default function LiveUpdatesSection({ storyMemoryId }: LiveUpdatesSectionProps) {
  const [updates, setUpdates] = useState<LiveUpdate[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchUpdates = async () => {
      try {
        const { data, error } = await supabase
          .from("live_updates")
          .select("*")
          .eq("story_memory_id", storyMemoryId)
          .is("merged_into_cluster_id", null)  -- exclude merged articles
          .order("discovered_at", { ascending: false })
          .limit(10);

        if (error) throw error;
        setUpdates(data || []);
      } finally {
        setIsLoading(false);
      }
    };

    fetchUpdates();

    // Poll every 90 seconds (don't overwhelm Supabase)
    const interval = setInterval(fetchUpdates, 90000);
    return () => clearInterval(interval);
  }, [storyMemoryId]);

  if (isLoading) {
    return (
      <div className="live-updates-section" aria-busy="true">
        <div className="live-updates__skeleton" />
      </div>
    );
  }

  if (!updates.length) {
    return null;  -- Only show if there are updates
  }

  return (
    <section className="live-updates-section" role="region" aria-label="Live Updates">
      <h3 className="live-updates__header">
        <span className="live-updates__icon" aria-hidden="true">●</span>
        Latest Updates ({updates.length})
      </h3>

      <div className="live-updates__list">
        {updates.map((update) => (
          <a
            key={update.id}
            href={update.article_url}
            className="live-update-card"
            target="_blank"
            rel="noopener noreferrer"
          >
            <div className="live-update__meta">
              <time className="live-update__time">
                {timeAgo(new Date(update.discovered_at))}
              </time>
              <span className="live-update__source">{update.source_name}</span>
            </div>
            <h4 className="live-update__title">{update.title}</h4>
            {update.update_summary && (
              <p className="live-update__summary">{update.update_summary}</p>
            )}
          </a>
        ))}
      </div>
    </section>
  );
}
```

**Key details:**
- Polls every 90 seconds (not 30 min) for responsive feel
- Excludes merged articles (so they don't reappear when main cluster updates)
- Opens links in new tab (external articles, not internal navigation)
- Accessible: proper time elements, aria labels

### Step 3.4: Integrate Into HomeContent

**File:** `frontend/app/components/HomeContent.tsx`

Add after LeadStory:

```tsx
import LiveUpdatesSection from "./LiveUpdatesSection";

// In the render:
{leadStory && (
  <>
    <LeadStory story={leadStory} />
    {leadStory.story_memory_id && (
      <LiveUpdatesSection storyMemoryId={leadStory.story_memory_id} />
    )}
  </>
)}

{/* Rest of feed below */}
```

### Step 3.5: Add Type Definitions

**File:** `frontend/app/lib/types.ts`

```typescript
export interface LiveUpdate {
  id: string;
  story_memory_id: string;
  article_url: string;
  title: string;
  summary?: string;
  source_slug: string;
  source_name: string;
  published_at?: string;
  update_summary?: string;
  discovered_at: string;
  merged_into_cluster_id?: string;
  created_at: string;
}

export interface StoryMemory {
  id: string;
  cluster_id: string;
  headline: string;
  category?: string;
  source_ids: string[];
  source_count: number;
  is_top_story: boolean;
  is_active: boolean;
  last_live_update_at?: string;
  live_update_count: number;
  activated_at?: string;
  deactivated_at?: string;
  created_at: string;
  updated_at: string;
}

// Extend Story interface
export interface Story {
  // ... existing fields
  is_top_story?: boolean;
  live_update_count?: number;
  last_live_update_at?: string;
  story_memory_id?: string;
}
```

### Step 3.6: Add Styling

**File:** `frontend/app/styles/components.css`

```css
/* Lead story badge */
.lead-story__badge {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: linear-gradient(135deg, var(--bg-accent-light) 0%, var(--bg-primary) 100%);
  border-left: 3px solid var(--fg-accent);
  border-radius: 4px;
  margin-bottom: var(--space-3);
  font-family: var(--font-meta);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  line-height: 1.4;
}

.badge-icon {
  color: var(--fg-accent);
  animation: pulse 2s ease-in-out infinite;
  flex-shrink: 0;
}

.badge-text {
  font-weight: 700;
  color: var(--fg-primary);
}

.badge-time {
  font-style: italic;
  color: var(--fg-secondary);
  margin-left: auto;
}

.badge-count {
  margin-left: auto;
  background-color: var(--fg-accent);
  color: var(--bg-primary);
  border-radius: 12px;
  padding: 2px 8px;
  font-size: 0.7rem;
  font-weight: 700;
  white-space: nowrap;
}

@media (max-width: 767px) {
  .lead-story__badge {
    flex-wrap: wrap;
    padding: var(--space-2);
  }

  .badge-time,
  .badge-count {
    margin-left: 0;
    margin-top: var(--space-1);
    flex-basis: 100%;
  }
}

/* Live updates section */
.live-updates-section {
  margin: var(--space-4) 0;
  padding: var(--space-4) var(--space-3);
  background-color: var(--bg-secondary);
  border-left: 3px solid var(--fg-accent);
  border-radius: 4px;
}

.live-updates__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 0.75rem;
  font-family: var(--font-meta);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 700;
  margin: 0 0 var(--space-3) 0;
  color: var(--fg-primary);
}

.live-updates__icon {
  color: var(--fg-accent);
  animation: pulse 2s ease-in-out infinite;
  flex-shrink: 0;
}

.live-updates__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.live-update-card {
  display: block;
  padding: var(--space-3);
  background-color: var(--bg-primary);
  border-left: 2px solid var(--fg-accent);
  border-radius: 4px;
  text-decoration: none;
  transition: all var(--dur-fast) ease-out;
}

.live-update-card:hover {
  background-color: var(--bg-secondary);
  transform: translateX(4px);
}

.live-update-card:focus {
  outline: 2px solid var(--fg-accent);
  outline-offset: 2px;
}

.live-update__meta {
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-1);
  font-size: 0.75rem;
  font-family: var(--font-meta);
}

.live-update__time {
  color: var(--fg-secondary);
  text-transform: uppercase;
}

.live-update__source {
  color: var(--fg-secondary);
  font-weight: 600;
}

.live-update__title {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--fg-primary);
  line-height: 1.4;
  margin: 0 0 var(--space-2) 0;
}

.live-update__summary {
  font-size: 0.85rem;
  color: var(--fg-secondary);
  line-height: 1.5;
  margin: 0;
}

/* Pulse animation */
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

/* Loading skeleton */
.live-updates__skeleton {
  height: 100px;
  background: linear-gradient(
    90deg,
    var(--bg-primary) 25%,
    var(--bg-secondary) 50%,
    var(--bg-primary) 75%
  );
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
  border-radius: 4px;
}

@keyframes loading {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (max-width: 767px) {
  .live-updates-section {
    padding: var(--space-3) var(--space-2);
    margin: var(--space-3) 0;
  }

  .live-updates__header {
    font-size: 0.7rem;
  }

  .live-update-card {
    padding: var(--space-2);
  }

  .live-update__title {
    font-size: 0.9rem;
  }
}
```

### Step 3.7: Testing

**Unit tests (frontend):**

```typescript
// frontend/__tests__/LiveUpdatesSection.test.tsx
import { render, screen } from "@testing-library/react";
import LiveUpdatesSection from "@/app/components/LiveUpdatesSection";

describe("LiveUpdatesSection", () => {
  it("renders section when updates exist", () => {
    const { container } = render(
      <LiveUpdatesSection storyMemoryId="test-id" />
    );
    expect(container.querySelector(".live-updates-section")).toBeTruthy();
  });

  it("opens links in new tab", () => {
    const { container } = render(
      <LiveUpdatesSection storyMemoryId="test-id" />
    );
    const links = container.querySelectorAll("a[target='_blank']");
    links.forEach((link) => {
      expect(link.getAttribute("rel")).toContain("noopener");
    });
  });
});
```

**Integration test (e2e):**

```typescript
// e2e/live-updates.e2e.ts
import { test, expect } from "@playwright/test";

test("Lead story shows live update badge", async ({ page }) => {
  await page.goto("http://localhost:3000");

  // Wait for lead story
  const leadStory = page.locator(".lead-story");
  await leadStory.waitFor();

  // Check for badge
  const badge = leadStory.locator(".lead-story__badge");

  // If top story exists, badge should be visible
  if (await badge.isVisible()) {
    expect(await badge.locator(".badge-text").textContent()).toBe("Top Story");
  }
});

test("Live updates section displays new articles", async ({ page }) => {
  await page.goto("http://localhost:3000");

  // Scroll to live updates section
  const liveSection = page.locator(".live-updates-section");
  await liveSection.scrollIntoViewIfNeeded();

  // Verify structure
  if (await liveSection.isVisible()) {
    const cards = liveSection.locator(".live-update-card");
    const count = await cards.count();
    expect(count).toBeGreaterThan(0);

    // Verify first card has title and source
    const firstCard = cards.first();
    expect(await firstCard.locator(".live-update__title").isVisible()).toBeTruthy();
    expect(await firstCard.locator(".live-update__source").isVisible()).toBeTruthy();
  }
});
```

---

## Phase 4: Polish & Monitoring (Days 15-21)

### Step 4.1: Create Operational Runbook

**File:** `docs/MEMORY-ENGINE-OPS.md` (NEW)

Document:
- How to manually deactivate a top story (SQL or Supabase UI)
- How to monitor live_updates table growth
- Troubleshooting: live poller failing, story_memory not created, etc.
- Rollback procedure: how to disable memory engine if needed

### Step 4.2: Set Up Monitoring

**Supabase Alerts:**
- live_updates row count growth >20/hour (potential runaway)
- story_memory table size >50 rows (manual cleanup needed)
- Average query time on live_updates >500ms (index performance degradation)

**GitHub Actions Monitoring:**
- Set up notifications for live-poll.yml failures
- Track RPD consumption via Gemini quota API
- Alert if any run takes >2 min (performance regression)

### Step 4.3: Manual Testing Scenarios

**Scenario 1: Normal operation**
- Run main pipeline
- Verify story_memory created with top story
- Wait 30 min
- Run live poller manually
- Verify live_updates created
- Check frontend: badge appears, live updates display

**Scenario 2: Breaking news spike**
- Manually insert 20 test articles into live_updates for top story
- Run live poller (should gracefully rate-limit to 10)
- Verify Gemini calls capped at 10
- Verify no RPD overage

**Scenario 3: Story deactivation**
- Manually update story_memory: `is_active = false`
- Run live poller
- Verify it skips deactivated story
- Run main pipeline
- Verify new top story becomes active

**Scenario 4: Mobile responsive**
- Open app on iPhone 12
- Verify badge text wraps correctly
- Verify live updates section doesn't overflow
- Test tap interactions (open link, etc.)

### Step 4.4: Accessibility Audit

**Checklist:**
- [ ] Live update badge has appropriate aria-labels
- [ ] Live updates section is a proper `<section role="region">`
- [ ] Time elements use `<time>` with dateTime attribute
- [ ] Links have sufficient color contrast
- [ ] Touch targets ≥44×44px (mobile)
- [ ] Keyboard navigation works (Tab through all controls)
- [ ] Screen reader announces badge + update count

**Testing:**
```bash
# Use axe DevTools or WAVE browser extension
# Run Lighthouse accessibility audit
npx next build
npx http-server out/
# Open in Chrome, run Lighthouse
```

### Step 4.5: Documentation

Update **CLAUDE.md** with new section:

```markdown
## News Memory Engine

Enables live updates for the #1 developing story between scheduled pipeline runs.

### How it works
1. **Pipeline integration** (step 11b): After ranking, stores top cluster in story_memory
2. **Live polling** (every 30 min): live_poller.py checks only that story's source RSS feeds
3. **Delta summarization**: Gemini generates 1-2 sentence summary for each new article
4. **Frontend display**: Lead story shows "Updated X min ago" badge + live updates section

### Tables
- `story_memory` — tracks cluster continuity, source list, state
- `live_updates` — delta articles discovered between pipeline runs

### Workflows
- Main pipeline: runs 4x/day (00:00, 06:00, 12:00, 18:00 UTC)
- Live poller: runs every 30 min (GitHub Actions)
- Cleanup: auto-deletes stories older than 48h

### Cost
- Adds ~50-80 RPD/day (stays under 1500 free tier)
- Uses ~3-5 Gemini calls per 30-min poll window
```

---

## Troubleshooting Guide

### Problem: story_memory not created after pipeline run

**Diagnosis:**
```sql
SELECT * FROM story_memory ORDER BY created_at DESC LIMIT 1;
```

**Causes:**
1. Memory orchestrator not imported in main.py
2. MEMORY_AVAILABLE flag = False (check imports)
3. Supabase connection failed silently

**Fix:**
- Verify `from memory.memory_orchestrator import...` in main.py
- Check pipeline logs for "Memory engine" message
- Test orchestrator in isolation: `python -c "from pipeline.memory.memory_orchestrator import *"`

---

### Problem: live_poller finding no new articles

**Diagnosis:**
```bash
python pipeline/memory/live_poller.py --verbose
```

**Causes:**
1. No active top story in story_memory (run main pipeline first)
2. Sources haven't published anything new
3. All new articles already in live_updates

**Fix:**
- Verify `SELECT * FROM story_memory WHERE is_active=true;` returns a row
- Manually check RSS feeds: `curl https://rss-url.com/ | head -20`
- Check live_updates table size: should grow over time

---

### Problem: live poller using too much RPD

**Diagnosis:**
```bash
# Check Gemini quota
curl -s https://generativelanguage.googleapis.com/v1beta/quotas?key=$GEMINI_API_KEY
```

**Causes:**
1. Rate limiting not working (capping >10 articles)
2. Scraper is sending huge texts to Gemini

**Fix:**
- Verify `new_articles[:10]` limit in live_poller.py
- Check scrape_article output: should be capped at 5000 chars
- Reduce polling frequency from 30 to 60 minutes

---

### Problem: Mobile badge layout broken

**Causes:**
1. Missing media query in CSS
2. Flex wrap not applied

**Fix:**
- Add to `frontend/app/styles/responsive.css`:
```css
@media (max-width: 767px) {
  .lead-story__badge {
    flex-wrap: wrap;
  }
  .badge-time, .badge-count {
    margin-left: 0;
    margin-top: var(--space-1);
    flex-basis: 100%;
  }
}
```

---

## Deployment Checklist

Before going live, verify:

### Backend
- [ ] All migrations (022, 023) deployed
- [ ] memory_orchestrator.py tested locally
- [ ] live_poller.py tested against staging Supabase
- [ ] live-poll.yml workflow created and tested
- [ ] GitHub Actions secrets configured (SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY)

### Frontend
- [ ] LeadStory component updated
- [ ] LiveUpdatesSection component created
- [ ] HomeContent integration complete
- [ ] Styling complete and responsive
- [ ] Types updated (LiveUpdate, StoryMemory)
- [ ] Component tests passing
- [ ] e2e tests passing
- [ ] Lighthouse score >90
- [ ] WCAG 2.1 AA audit passing

### Operations
- [ ] Monitoring set up (Supabase alerts, GitHub Actions)
- [ ] Runbook written and reviewed
- [ ] Rollback procedure documented
- [ ] On-call engineer briefed

### Launch
- [ ] Feature flag disabled by default (until team green-lights)
- [ ] Soft launch: 10% of traffic for 24h
- [ ] Monitor: error rate, RPD consumption, engagement metrics
- [ ] Full launch: roll out to 100%

---

## Post-Launch Metrics to Track

**Daily:**
- RPD consumption (target: <250/day)
- live_updates table row count
- live_poller run success rate (should be >99%)

**Weekly:**
- user clicks on live updates (engagement)
- story_memory table size (should stabilize ~10-20 active)
- Gemini error rate (<5%)
- time-to-update (from publication to appearing on app)

**Monthly:**
- user retention (do people return more if they see live updates?)
- story recency (is #1 story staying fresh, or staling?)
- feature feedback (NPS, UX comments)

---

**Last updated:** 2026-03-24
**Maintained by:** [Engineering Team]
