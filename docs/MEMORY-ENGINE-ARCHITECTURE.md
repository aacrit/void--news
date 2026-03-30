# News Memory Engine — Architecture Diagram

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    void --news Platform                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────────┐         ┌──────────────────────┐          │
│  │  Main Pipeline       │         │  Live Poller         │          │
│  │  (4x daily)          │         │  (every 30 min)      │          │
│  │                      │         │                      │          │
│  │  • RSS fetch (409)   │         │  • RSS fetch (15-20) │          │
│  │  • Cluster           │         │  • Scrape full text  │          │
│  │  • Bias analyze      │         │  • Gemini summary    │          │
│  │  • Rank              │         │  • Insert to DB      │          │
│  │  • Update memory     │         │  • Update timestamp  │          │
│  └──────────┬───────────┘         └──────────┬───────────┘          │
│             │                                 │                      │
│             └─────────────────┬───────────────┘                      │
│                               │                                       │
│                    ┌──────────▼──────────┐                           │
│                    │    Supabase         │                           │
│                    │    PostgreSQL       │                           │
│                    ├─────────────────────┤                           │
│                    │ story_memory        │  ◄─── Tracks continuity  │
│                    │ live_updates        │  ◄─── Delta articles     │
│                    │ story_clusters      │                          │
│                    │ articles            │                          │
│                    │ bias_scores         │                          │
│                    │ sources             │                          │
│                    │ pipeline_runs       │                          │
│                    └──────────┬──────────┘                           │
│                               │                                      │
│                    ┌──────────▼──────────┐                           │
│                    │  Next.js Frontend   │                           │
│                    │  (GitHub Pages)     │                           │
│                    ├─────────────────────┤                           │
│                    │ LeadStory badge     │ ◄─── "Updated 5 min ago" │
│                    │ LiveUpdatesSection  │ ◄─── Fresh articles      │
│                    │ HomeContent feed    │                          │
│                    └─────────────────────┘                           │
│                               │                                      │
│                               ▼                                      │
│                         (User device)                                │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Diagram

### Pipeline Run Cycle (every 6 hours)

```
Pipeline run → memory_orchestrator → story_memory table
                ↓
           Extract top cluster
                ↓
           Map sources to slugs
                ↓
           Create/update story_memory
                ↓
           flag: is_top_story=true
```

### Live Poller Cycle (every 30 minutes)

```
Query active top story
        ↓
Extract source_ids
        ↓
Fetch RSS (15-20 sources)
        ↓
Find new articles
        ↓
Scrape full text
        ↓
Summarize with Gemini
        ↓
Insert into live_updates
        ↓
Update story_memory timestamp
```

---

## Cost & Performance

| Metric | Current | New | Total |
|--------|---------|-----|-------|
| RPD/day | 116 | 50 | 166 |
| % of 1500 free tier | 8% | 3% | 11% |
| Operational cost | $0 | $0 | $0 |

---

## Deployment Timeline

- Phase 1 (Backend): Days 1-3
- Phase 2 (Live Poller): Days 4-7
- Phase 3 (Frontend): Days 8-14
- Phase 4 (Polish): Days 15-21

**Total: 3-4 weeks**

---

Last updated: 2026-03-24
