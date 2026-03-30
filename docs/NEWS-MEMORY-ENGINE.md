# News Memory Engine — Strategic Proposal

**Status:** Strategic Concept (Ready for Implementation)
**Date:** 2026-03-24
**Cost Impact:** $0 (stays within existing Gemini free tier)
**Timeline:** Phase 1 (4 weeks), Phase 2+ (rolling)

---

## Executive Summary

The News Memory Engine enables void --news to track **developing stories across pipeline runs** (4x daily) and surface a **single "#1 Top Story" pinned section** with live updates. Instead of refreshing all 409 sources every 6 hours, the system intelligently re-fetches RSS feeds only for sources covering the top story, keeping costs at $0.

**Key outcomes:**
- Users see evolving stories (e.g., Iran War, Gaza, Taiwan tensions) updating continuously
- Pinned top story displays on homepage with live badge and "Updated X minutes ago" timestamp
- Economical: targeted RSS polling for ~5-10 relevant sources instead of all 409
- No new API costs: uses existing Gemini free tier for brief updates
- Backward compatible: existing pipeline runs unchanged; memory engine is an optional supplement

---

## Problem Statement

**Current behavior:** void --news refreshes all 409 sources on a 6-hour cron cycle (4x daily). Each run produces a completely fresh story list, ranked by importance. A developing story (e.g., Iran War) appears, disappears, and reappears based on clustering + ranking logic, not because the situation changed—but because our fixed-window sampling shifted.

**User experience gap:**
- "Did the Iran situation resolve, or did coverage just drop out of the top 10?"
- "What's the latest on Taiwan? Do I need to check other sites?"
- No sense of **story continuity** across news cycles
- Live updates buried in the feed unless the story maintains top-10 ranking

**Why this matters:** News is a **living thing**. A developing conflict, policy decision, or market event unfolds over hours/days. void --news should honor that reality and let users follow a single thread without losing the thread.

---

## Architecture Overview

### Core Principle: Persistent Story Memory + Economical Live Polling

```
┌─────────────────────────────────────────────────────────────────┐
│  Pipeline Run (4x daily) → Standard clustering + ranking        │
│  → Identifies top 5 stories per section, picks #1 → memory_key │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  Story Memory Table (Supabase)                                  │
│  - cluster_id (current primary story)                           │
│  - memory_key (persistent hash of story topic)                  │
│  - pinned_at (when story became #1)                            │
│  - confidence (how certain we are this is "the same story")     │
│  - relevant_source_slugs (cached list of sources covering it)   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  Lightweight Live Refresh (optional, independent of main run)   │
│  - Cron: every 2 hours (or manually triggered)                  │
│  - Fetch only ~5-10 relevant sources (not all 409)              │
│  - Scrape + analyze only new articles                          │
│  - Upsert into DB (may create new articles or update summary)   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  Frontend: Top Story Section                                    │
│  - Pinned to top of feed (above lead story)                    │
│  - Displays cluster summary + "Live • Updated 5 min ago"       │
│  - Source count badge increments live                          │
│  - Click to open Deep Dive (same as regular stories)           │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. **Story Memory Table** (`story_memory`)
Tracks which cluster is "the top story" and persists across pipeline runs.

```sql
CREATE TABLE story_memory (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Current cluster being tracked as "top story"
  cluster_id UUID REFERENCES story_clusters(id) ON DELETE SET NULL,

  -- Persistent topic hash (e.g., "iran_war_2026_mar")
  -- Survives cluster deduping — if the old cluster is deleted,
  -- we can match new articles to the same memory_key
  memory_key TEXT NOT NULL UNIQUE,

  -- High-confidence keywords that define "this story"
  -- Used to re-match articles to this topic across runs
  memory_keywords TEXT[] DEFAULT ARRAY[]::TEXT[],

  -- Geographic/entity anchors (normalized: "iran", "usa", "us military")
  memory_entities TEXT[] DEFAULT ARRAY[]::TEXT[],

  -- When did this story become #1?
  pinned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- How certain are we this is still "the same story"?
  -- Decays over time if no new articles match the keywords
  -- Range: 0.0 to 1.0; below 0.3 → unpins automatically
  confidence REAL NOT NULL DEFAULT 0.9,

  -- Section ("world" or "us")
  section TEXT NOT NULL CHECK (section IN ('world', 'us')),

  -- Edition(s) where this is pinned
  editions TEXT[] NOT NULL DEFAULT ARRAY['world'],

  -- Cached list of source slugs covering this story
  -- Updated after each live refresh + cluster update
  relevant_source_slugs TEXT[] DEFAULT ARRAY[]::TEXT[],

  -- Article count at last refresh (for "Updated with X new articles")
  article_count_at_pin INT DEFAULT 0,
  article_count_current INT DEFAULT 0,

  -- When was the last live refresh?
  last_live_refresh TIMESTAMPTZ,

  -- How many live refreshes have we done for this story?
  refresh_count INT DEFAULT 0,

  -- When should we auto-unpin? (pin duration limit)
  auto_unpin_at TIMESTAMPTZ,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_story_memory_cluster ON story_memory(cluster_id);
CREATE INDEX idx_story_memory_section_edition ON story_memory(section, editions);
CREATE INDEX idx_story_memory_pinned_at ON story_memory(pinned_at DESC);

-- RLS: public read
ALTER TABLE story_memory ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read" ON story_memory FOR SELECT USING (true);
```

#### 2. **Live Refresh Mechanism** (`pipeline/memory/live_refresh.py`)

Lightweight script that:
- Fetches only sources relevant to the top story (~5-10 sources)
- Scrapes new articles (last 2 hours)
- Analyzes bias + clusters with existing story
- Updates article count + summary (optional: via rule-based TL;DR if Gemini unavailable)
- Runs independently of main pipeline (can run every 2 hours)

```python
# Pseudocode structure (actual code in Phase 1)

def live_refresh_top_story(memory_record: dict) -> dict:
    """
    Refresh articles for the top story without re-running full pipeline.

    Returns: {
      'new_articles_count': N,
      'sources_fetched': [slugs],
      'cluster_id': UUID,
      'updated_summary': str (or None if Gemini unavailable),
      'status': 'ok' | 'no_change' | 'unpin_confidence_too_low'
    }
    """
    # 1. Fetch only from relevant_source_slugs
    # 2. Scrape full text for new articles
    # 3. Analyze bias (same 5-axis scoring)
    # 4. Cluster with existing cluster (likely 1-2 new articles)
    # 5. Update article_count_current + last_live_refresh
    # 6. If article count increased: optionally re-generate brief (1 Gemini call, within budget)
    # 7. Return stats
```

**Cost:**
- RSS fetch (~5-10 sources): ~1s
- Web scraping (2-3 articles): ~5s
- Bias analysis (2-3 articles): ~2s
- Optional Gemini brief (1 call): 0 extra cost (uses separate 3-call/run budget, we're at ~7% capacity)
- **Total:** ~8-10s runtime, $0 cost

#### 3. **Story Continuity Logic** (`pipeline/memory/story_matcher.py`)

When a new cluster is ranked #1, determine if it's a **continuation** of the current pinned story or a **new story**.

```python
def should_pin_as_new_story(
    new_cluster: dict,
    current_memory: dict,
    all_recent_clusters: list[dict]
) -> bool:
    """
    Decide: is new_cluster a continuation of current_memory,
    or is it a genuinely new top story?

    Signals:
    - Entity overlap (do they mention same countries/people?)
    - Keyword overlap (cosine similarity on memory_keywords vs cluster title)
    - Time gap (how long since last article in current story?)
    - Importance delta (is new story >30 points higher ranked?)
    """
    entity_overlap = len(set(new_cluster['entities']) & set(current_memory['memory_entities'])) > 0
    keyword_sim = cosine_similarity(new_cluster_tfidf, memory_keywords_tfidf)

    # If 2+ days since last article + new story >30 points higher → unpin old
    # If entity/keyword overlap + <24h gap → continue (increment refresh_count)
    # Otherwise → new story (create new memory_key)

    if keyword_sim > 0.6 or (entity_overlap and time_gap < 24h):
        return False  # Continue old story
    elif time_gap > 48h and new_importance > old_importance + 30:
        return True  # New story (old naturally expired)
    else:
        return False  # Ambiguous: prefer continuity
```

---

## Database Changes

### New Table: `story_memory`
**Migration file:** `supabase/migrations/021_story_memory.sql`

See schema above. ~50 lines. No breaking changes to existing tables.

### New Columns: `story_clusters`
Add to identify stories linked to a memory record (optional denormalization):

```sql
ALTER TABLE story_clusters ADD COLUMN IF NOT EXISTS memory_id UUID REFERENCES story_memory(id) ON DELETE SET NULL;
ALTER TABLE story_clusters ADD COLUMN IF NOT EXISTS is_live_updated BOOLEAN DEFAULT FALSE;
ALTER TABLE story_clusters ADD COLUMN IF NOT EXISTS live_update_count INT DEFAULT 0;

CREATE INDEX idx_clusters_memory_id ON story_clusters(memory_id);
```

---

## Pipeline Changes

### Phase 1: Integration Points

#### Step 7.1 (New): **Pin Top Story to Memory**
**File:** `pipeline/main.py` (add after step 7: categorization & ranking)

```python
# After ranking, before storing clusters:
def pin_top_story_to_memory(ranked_clusters: list[dict], section: str, editions: list[str]):
    """
    Take the #1 cluster per section and pin it to story_memory.
    Called once per section per pipeline run (e.g., world top story).
    """
    if not ranked_clusters:
        return

    top_cluster = ranked_clusters[0]

    # Check: is this a continuation of the current pinned story?
    current_memory = get_current_memory(section=section, edition=editions[0])

    if current_memory and should_continue_story(top_cluster, current_memory):
        # Update existing memory record
        update_memory_record(
            memory_id=current_memory['id'],
            cluster_id=top_cluster['id'],
            article_count_current=top_cluster['source_count'],
            refresh_count=current_memory['refresh_count'] + 1,
            confidence=min(1.0, current_memory['confidence'] + 0.05)  # slight bump
        )
    else:
        # New story: create new memory record
        memory_key = generate_memory_key(top_cluster)  # e.g., "iran_war_2026_mar"
        keywords = extract_memory_keywords(top_cluster)
        entities = extract_memory_entities(top_cluster)

        create_memory_record(
            cluster_id=top_cluster['id'],
            memory_key=memory_key,
            memory_keywords=keywords,
            memory_entities=entities,
            section=section,
            editions=editions,
            relevant_source_slugs=get_sources_for_cluster(top_cluster),
            article_count_at_pin=top_cluster['source_count'],
            auto_unpin_at=now() + timedelta(days=5)  # max pin duration
        )
```

**Effort:** ~150 lines. Integrate before step 8 (store clusters).

#### Step 7.2 (New): **Confidence Decay Over Time**
**File:** `pipeline/utils/memory_utils.py`

```python
def decay_memory_confidence(memory_record: dict) -> float:
    """
    Decay confidence if no new articles have arrived.
    Called daily. If confidence < 0.3, story is auto-unpinned.
    """
    age_hours = (datetime.now(tz=UTC) - memory_record['last_live_refresh']).total_seconds() / 3600

    # No articles in 24h → -0.1/day
    # No articles in 48h → -0.25/day
    # No articles in 72h+ → -0.5/day (fast unpin)

    decay_rate = 0.1 if age_hours < 24 else (0.25 if age_hours < 48 else 0.5)
    new_confidence = memory_record['confidence'] - (decay_rate * (age_hours / 24))
    return max(0.0, min(1.0, new_confidence))
```

**Effort:** ~30 lines.

### Phase 1.5: Live Refresh Cron Job
**File:** `pipeline/memory/live_refresh.py` + new GitHub Actions workflow

New standalone script that runs every 2 hours (or on-demand):

```yaml
# .github/workflows/live-refresh.yml
name: Live Refresh Top Story
on:
  schedule:
    # Every 2 hours: 00:00, 02:00, 04:00, ..., 22:00 UTC
    - cron: '0 */2 * * *'
  workflow_dispatch:  # Manual trigger

jobs:
  live-refresh:
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
      - name: Run live refresh
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_KEY: ${{ secrets.SUPABASE_KEY }}
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: |
          python pipeline/memory/live_refresh.py --editions world,us
```

**Effort:** ~300 lines (Python) + 30 lines (YAML workflow).

---

## Frontend Changes

### 1. Top Story Section (`frontend/app/components/TopStorySection.tsx`)

New component displayed between NavBar and FilterBar on homepage.

**Design:**
- Full-width card (same width as story cards)
- Large headline (Playfair Display, 2.5em)
- Summary (3-4 sentences, justified text)
- Metadata row: source count badge + "Live • Updated 5 min ago" + edit timestamp
- CTA: "See all perspectives ▶" (opens Deep Dive)
- Visual distinction: thin left border (brand color), slightly different card bg

**Code:**
```tsx
// frontend/app/components/TopStorySection.tsx

export function TopStorySection({ memory }: { memory: StoryMemory }) {
  const [isLive, setIsLive] = useState(false);

  // Check if last update was <2 minutes ago
  useEffect(() => {
    if (!memory.last_live_refresh) return;
    const age_ms = Date.now() - new Date(memory.last_live_refresh).getTime();
    setIsLive(age_ms < 2 * 60 * 1000);
  }, [memory.last_live_refresh]);

  return (
    <div className="top-story-section">
      <div className="top-story-badge">
        {isLive && <div className="live-pulse">●</div>}
        Top Story
      </div>

      <h1 className="top-story-headline">{memory.cluster?.title}</h1>

      <p className="top-story-summary">{memory.cluster?.summary}</p>

      <div className="top-story-meta">
        <div className="source-count-badge">
          {memory.cluster?.source_count} sources
        </div>
        <div className="update-time">
          Updated {timeAgo(new Date(memory.last_live_refresh || memory.pinned_at))}
        </div>
        <button
          onClick={() => openDeepDive(memory.cluster)}
          className="deep-dive-cta"
        >
          See all perspectives ▶
        </button>
      </div>
    </div>
  );
}
```

**Effort:** ~80 lines (component) + ~40 lines (CSS).

### 2. Frontend Hook: `useLiveMemory`

```tsx
// frontend/app/lib/hooks/useLiveMemory.ts

export function useLiveMemory(section: string) {
  const [memory, setMemory] = useState<StoryMemory | null>(null);

  // Fetch current memory record
  useEffect(() => {
    const fetch = async () => {
      const res = await supabase
        .from('story_memory')
        .select(`
          *,
          cluster:cluster_id (*)
        `)
        .eq('section', section)
        .eq('editions', [section])
        .single();

      if (res.data) {
        setMemory(res.data);
      }
    };

    fetch();

    // Poll for updates every 30 seconds
    const interval = setInterval(fetch, 30_000);
    return () => clearInterval(interval);
  }, [section]);

  return memory;
}
```

### 3. HomeContent Integration

```tsx
// frontend/app/components/HomeContent.tsx

export default function HomeContent() {
  const edition = useEdition(); // 'world' | 'us' | 'india'
  const memory = useLiveMemory(edition);

  return (
    <>
      <NavBar />
      {memory && <TopStorySection memory={memory} />}
      <FilterBar />
      <LeadStory /> {/* Or skip if memory already shows top story */}
      <StoriesFeed />
    </>
  );
}
```

**Total frontend effort:** ~150 lines (components) + ~60 lines (CSS) + ~40 lines (hook).

---

## Cost Analysis

### Current Gemini Usage
- Cluster summarization: ~26 calls/run × 4 runs/day = 104 RPD (7% of 1500 free limit)
- Daily brief: 3 calls/run × 4 runs/day = 12 RPD (0.8% of limit)
- **Total:** ~116 RPD (7.7% of limit)

### Memory Engine Additions
- Live refresh brief (optional): 1 call every 2 hours when top story has new articles = ~12 calls/day = 12 RPD (0.8% of limit)
- **New total:** ~128 RPD (8.5% of limit)

**Cost impact:** $0. Still under free tier.

---

## Implementation Phases

### Phase 1: Core Memory Engine (4 weeks)
**Milestone:** Pinned top story with continuity tracking

1. **Week 1:** Database schema + migration
   - Create `story_memory` table
   - Add `memory_id`, `is_live_updated` columns to `story_clusters`
   - RLS policies

2. **Week 2:** Pipeline integration
   - Implement `story_matcher.py` (entity/keyword overlap logic)
   - Add `pin_top_story_to_memory()` to `main.py` step 7.1
   - Implement confidence decay logic
   - Unit tests (fixtures: Iran war, Ukraine conflict, Taiwan tension)

3. **Week 3:** Frontend Top Story Section
   - Build `TopStorySection.tsx` component
   - Add `useLiveMemory()` hook
   - Integrate with `HomeContent.tsx`
   - Mobile responsive (full-width on mobile, same card style as leads)

4. **Week 4:** Polish + testing
   - QA: manual testing with live cron
   - Performance: verify <2s fetch time for live refresh
   - Mobile: test on iPhone 12/Android
   - Deploy: push to main, verify GH Pages deploy

**Deliverables:**
- Schema migration (024_story_memory.sql)
- `pipeline/memory/story_matcher.py`
- `pipeline/memory/memory_utils.py`
- Updated `pipeline/main.py` (steps 7.1-7.2)
- `TopStorySection.tsx` + `useLiveMemory.ts`
- CSS for top story styling
- Unit tests + fixtures

**Effort:** ~3 weeks dev, 1 week QA/deploy.

### Phase 1.5: Live Refresh Cron (2 weeks, parallel to Phase 1)
**Milestone:** Every 2 hours, refresh top story independently

1. **Week 1:** Live refresh script
   - Implement `pipeline/memory/live_refresh.py`
   - Targeted RSS fetch + scrape (only relevant sources)
   - Bias analysis on new articles only
   - Cluster matching + article upsert

2. **Week 2:** GitHub Actions + monitoring
   - New workflow: `.github/workflows/live-refresh.yml`
   - Logging + error reporting
   - Manual trigger button for testing
   - Monitor: RSS fetch success rate

**Deliverables:**
- `pipeline/memory/live_refresh.py` (~300 lines)
- `.github/workflows/live-refresh.yml`
- Monitoring/logging

**Effort:** ~1 week dev, ~3 days ops.

### Phase 2: Enhanced Brief Updates (Post-Launch)
**Milestone:** Live refresh generates brief updates with Gemini

- When live refresh finds 3+ new articles: call Gemini to generate "What's new" brief
- Brief focuses on **changes since last update**, not full story recap
- Stored in separate table (`story_memory_updates`) with timestamps
- Frontend displays "2 new developments in the last 30 min" expandable section

**Effort:** ~2 weeks.

### Phase 3: Story Expiration + Archival (Post-Launch)
**Milestone:** Graceful auto-unpin when stories go stale

- Auto-unpin when `confidence < 0.3` OR `auto_unpin_at` reached
- Archive story to `story_archive` table (for "Recent Top Stories" widget)
- Frontend: "Recent Top Stories" carousel showing last 5 top stories

**Effort:** ~1 week.

### Phase 4: Cross-Story Divergence Views (Post-Launch)
**Milestone:** Compare how different stories are covered across sources

- If a new story pins while old story is still getting articles: show "Related coverage" sidebar
- Example: Iran war pinned + Palestine coverage still rolling → show divergence in tone/coverage

**Effort:** ~2 weeks.

---

## Risk Assessment & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Story continuity logic incorrectly links unrelated stories (e.g., "Iran nuclear" + "Iran elections") | Medium | High | Extensive testing with real clusters; keyword+entity thresholds tuned conservatively; manual override button for curation |
| Live refresh RSS fetcher times out or misses articles | Low | Medium | Timeout set to 10s per source; error logging; manual re-trigger workflow |
| Gemini API rate limit hit during peak updates | Low | Medium | Keep budget well under free tier (8.5% vs 7.7%); separate live refresh budget from main pipeline |
| Frontend memory hook polls Supabase too aggressively (30s interval × 100 users) | Low | Low | Use edge caching (Supabase can cache reads); increase poll interval to 60s if needed |
| Old pinned story still shows as "top" after new story should have taken over | Low | High | Strong unit tests on story_matcher logic; confidence decay logic well-tuned; manual monitoring first 2 weeks |
| Database performance: story_memory queries become slow with 100+ stories archived | Low | Low | Archive old records; keep active memory records <10; index on `pinned_at DESC` and `section` |

**Mitigations:**
1. **Testing:** Create fixture set with 10 real story pairs (Iran war + elections, Gaza + humanitarian crisis, Taiwan + trade, etc.) and validate matcher logic pre-launch
2. **Monitoring:** Log all story_matcher decisions for 2 weeks; notify team of any continuity errors
3. **Manual override:** CEO/editor can manually pin/unpin a story via Supabase UI or admin panel (future)
4. **Gradual rollout:** Launch with top story visible but live refresh disabled; enable after 1 week of testing

---

## Competitive Positioning

| Feature | void --news | Ground News | Apple News | Google News |
|---------|------------|-------------|-----------|------------|
| Develops story tracking | NEW | Manual collections | Editorial curation | Implicit (via ranking) |
| Live updates within 6h window | NEW | Manual (16 sources) | Manual | Implicit |
| Economical live polling (not all 409) | NEW | N/A | N/A | Proprietary |
| Per-article bias transparency | Yes | No (source-level) | No | No |
| Pinned top story | NEW | No | Limited | No |

**Narrative:** "void --news remembers what's happening. Developing stories surface continuously, not just when they hit your refresh cycle. All at zero cost."

---

## Technical Debt & Cleanup

- Current: `headline_rank` field in `story_clusters` is the primary sort key. Memory engine doesn't change this, but frontend should eventually distinguish between "top story via rank" and "top story via memory." Consider adding `is_memory_pinned BOOLEAN` column for clarity.
- Cluster deduping (step 8b) should respect memory links: if an old cluster is merged into a new cluster, memory pointer should follow.

---

## Success Metrics (MVP)

1. **Functional:**
   - Top story pinned on every pipeline run (4x/day)
   - Story continuity maintained >90% of the time (manual review of 10 top stories)
   - Live refresh runs successfully every 2 hours (error rate <5%)

2. **Performance:**
   - Live refresh runtime: <15 seconds (target 8-10s)
   - Frontend "Updated X min ago" updates in real-time (poll latency <2s)
   - No Supabase rate limiting (queries stay under 10/sec peak)

3. **User:**
   - Top story visible on homepage (100% of visitors see it)
   - Click-through to Deep Dive works seamlessly
   - No layout shift when top story refreshes (CSS-based animation)

---

## Locked Decisions

1. **Memory persistence:** Story memory survives cluster deduping + re-analysis. If the #1 story's articles are re-clustered, memory pointer updates; story stays pinned.
2. **Live refresh scope:** Only top story (world OR us, not all sections). Keeps cost/complexity minimal.
3. **Live refresh frequency:** Every 2 hours (not continuous). Balances freshness + simplicity.
4. **Confidence decay:** Linear decay, auto-unpin at 0.3. Prevents stale stories from lingering.
5. **Gemini budget:** Live refresh brief uses separate budget (not charged against 25-call summarization cap). Keeps existing pipeline unaffected.

---

## Questions for CEO Approval

1. **Scope:** Should we track top story for both world + us editions, or just world initially?
   - Recommendation: Start with world only (simpler, most global interest). Add us in Phase 2.

2. **Auto-unpin duration:** Currently set to 5 days max. Too long? Too short?
   - Recommendation: 5 days for major stories (wars, policy), 3 days for mid-tier (elections). Make configurable per story.

3. **Live refresh frequency:** 2 hours or more/less frequently?
   - Recommendation: 2 hours is right balance. 1 hour = higher cost/ops, 4 hours = less "live" feeling.

4. **Editor control:** Should editors be able to manually pin/unpin stories, or fully automatic?
   - Recommendation: MVP is fully automatic. Phase 2: add manual override UI.

5. **Narrative focus:** Does the top story brief focus on "what's new since last update" or "full story recap"?
   - Recommendation: Start with recap (simpler); Phase 2 adds "what's new" deltas.

---

## Next Steps

1. **Get CEO approval** on scope + locked decisions above
2. **Week 1:** Begin Phase 1 (database schema), Phase 1.5 (live refresh script) in parallel
3. **Soft launch:** Enable memory engine + live refresh on 2026-04-21 (4 weeks)
4. **Monitor:** Log story continuity decisions; gather user feedback
5. **Phase 2 planning:** Based on launch metrics, prioritize phase 2 features

---

## Appendix A: Sample Story Memory Records

### Example 1: Iran Escalation (Continuation)

```json
{
  "id": "mem-001",
  "cluster_id": "cluster-2842",
  "memory_key": "iran_military_escalation_2026_mar",
  "memory_keywords": ["Iran", "military", "escalation", "drone", "ballistic missile", "US"],
  "memory_entities": ["Iran", "USA", "IRGC"],
  "section": "world",
  "editions": ["world"],
  "pinned_at": "2026-03-20T14:30:00Z",
  "confidence": 0.92,
  "relevant_source_slugs": ["ap-news", "reuters", "bbc", "al-jazeera", "rte-farsi"],
  "article_count_at_pin": 24,
  "article_count_current": 31,
  "last_live_refresh": "2026-03-24T10:15:00Z",
  "refresh_count": 6,
  "auto_unpin_at": "2026-03-25T14:30:00Z"
}
```

**Timeline:**
- 2026-03-20 14:30 UTC: Iran escalation ranked #1 → pinned
- 2026-03-20 16:00 UTC: Live refresh finds 2 new articles → article_count 26
- 2026-03-21 10:00 UTC: Live refresh finds 3 new articles → article_count 29
- 2026-03-21 20:00 UTC: Full pipeline run; same story still #1 → confidence bumped to 0.94
- 2026-03-22 12:00 UTC: Live refresh finds 1 new article → article_count 30
- 2026-03-23 18:00 UTC: Live refresh finds 2 new articles → article_count 32
- 2026-03-24 10:15 UTC: Live refresh finds 1 new article → article_count 33

### Example 2: New Story Takes Over (Story Pivot)

```json
{
  "id": "mem-002",
  "cluster_id": "cluster-3051",
  "memory_key": "us_election_2026_primary",
  "memory_keywords": ["primary", "election", "campaign", "votes", "Iowa"],
  "memory_entities": ["USA", "Iowa"],
  "section": "us",
  "editions": ["us"],
  "pinned_at": "2026-03-22T18:45:00Z",
  "confidence": 0.88,
  "relevant_source_slugs": ["nyt", "washington-post", "politico", "cnn"],
  "article_count_at_pin": 18,
  "article_count_current": 25,
  "last_live_refresh": "2026-03-24T08:30:00Z",
  "refresh_count": 3,
  "auto_unpin_at": "2026-03-25T18:45:00Z"
}
```

**Event:** Old top story (Iran escalation, confidence 0.3 after 4+ days) auto-unpins. New top story (US primary) takes over on 2026-03-22.

---

## Appendix B: Story Matcher Pseudocode

```python
def should_continue_story(new_cluster: dict, current_memory: dict) -> bool:
    """
    Decide if new_cluster is a continuation of current_memory,
    or if the old story should be unpinned.
    """

    # 1. Entity overlap (strongest signal)
    new_entities = set(extract_entities_from_cluster(new_cluster))
    memory_entities = set(current_memory['memory_entities'])
    entity_overlap_score = len(new_entities & memory_entities) / max(len(new_entities), len(memory_entities))

    # 2. Keyword overlap (secondary signal)
    new_title_words = set(new_cluster['title'].lower().split())
    memory_keywords = set(current_memory['memory_keywords'])
    keyword_overlap_score = len(new_title_words & memory_keywords) / len(memory_keywords)

    # 3. Time gap since last article in old story
    old_cluster = fetch_cluster(current_memory['cluster_id'])
    time_gap_hours = (now() - old_cluster['last_updated']).total_seconds() / 3600

    # 4. Ranking delta (is new story significantly higher ranked?)
    ranking_delta = new_cluster['importance_score'] - current_memory['cluster_importance_score']

    # Decision logic
    if entity_overlap_score > 0.5:  # Strong entity match → likely continuation
        return True
    elif keyword_overlap_score > 0.4 and time_gap_hours < 24:  # Weak keyword match but recent
        return True
    elif time_gap_hours > 48 and ranking_delta > 30:  # Old story stale, new one much stronger
        return False  # Unpin old story
    elif time_gap_hours > 72:  # Very old story with no new articles
        return False  # Unpin
    else:
        return None  # Ambiguous → keep pinned but lower confidence
```

---

## Appendix C: RLS & Security

All `story_memory` data is public read (no auth required), matching existing RLS policy:

```sql
ALTER TABLE story_memory ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read story_memory"
  ON story_memory FOR SELECT
  USING (true);
```

Future admin control (Phase 3):
```sql
-- Allow authenticated admins to update story_memory (manual pin/unpin)
CREATE POLICY "Admin update story_memory"
  ON story_memory FOR UPDATE
  USING (auth.role() = 'authenticated' AND auth.claims()->>'email' LIKE '%@void-news.com')
  WITH CHECK (same);
```

---

**Document Version:** 1.0
**Last Updated:** 2026-03-24
**Status:** Ready for Development
**Approval:** [CEO Signature]
