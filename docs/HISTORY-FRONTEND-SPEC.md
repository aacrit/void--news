# void --history Frontend Spec

Reference doc for the historyUI session. All backend/data work is complete — this doc covers what the frontend needs to implement.

Last updated: 2026-04-05

---

## 1. Current State (already shipped)

### 25 Events (YAML complete, ready for Supabase)

All events in `data/history/events/`. Run `python3 pipeline/history/content_loader.py` to load.

| Era | Events |
|-----|--------|
| Ancient | Ashoka & Maurya Empire (268 BCE) |
| Classical | Peloponnesian War (431 BCE), Fall of Rome (476 CE) |
| Medieval | Mongol Conquest of Baghdad (1258), The Crusades (1095), Mali Empire / Mansa Musa (1324) |
| Early Modern | Transatlantic Slave Trade, Haitian Revolution |
| Modern | Scramble for Africa, Opium Wars, French Revolution, Trail of Tears, Armenian Genocide, Holodomor, Congo Free State, Meiji Restoration, Treaty of Waitangi, Bolivarian Revolutions |
| Contemporary | Partition of India, Hiroshima, Rwanda, Israel/Nakba, Berlin Wall, Tiananmen Square, Cambodian Genocide |

### HOOKS and CTAS (already in HistoryLanding.tsx)

All 25 events have story-specific hooks (arrive-late one-liners) and CTAs in the `HOOKS` and `CTAS` record maps. The historyUI session has already evolved the poster rendering (PosterImage fallback chain, severity classes, hover-reveal perspective names, stark data lines).

### MockData (needs update)

`mockData.ts` currently has 3 published mock events + 5 redacted stubs. With all classified events now published as YAML, the REDACTED_EVENTS array should be cleared entirely. Consider whether mockData needs updating for all 25 events or if Supabase is the sole source.

---

## 2. New Feature: History Arcs (CEO Decision Required)

### The Question

Should void --history add a new content type for century-spanning topics? First topic: "Capitalism and Communism" (1848-present).

### Option A: Lightweight Arc Pages (ceo-advisor recommendation)

**Don't build a new data model.** Use the existing `EventConnection` system:

- New route: `/history/arc/[slug]`
- A simple table `history_arcs` with: slug, title, date_range, lede (150 words)
- A join table `arc_events` linking arcs to existing events
- The Arc page renders a timeline of existing event cards with a lede paragraph
- No new perspectives, no new content authoring, no new component architecture
- Build time: 2-3 days
- The arc emerges from the connection graph, not from top-down taxonomy

### Option B: Full Arc System (agent-architect design)

**New content type with chapters x perspectives matrix:**

- 6 new Supabase tables (migration 042 already written)
- New TypeScript types (already in `types.ts`)
- YAML schema (already at `data/history/arcs/capitalism-and-communism.yaml`)
- 10 new frontend components needed (see below)
- Each arc has N chapters, each chapter has M perspectives
- Two reading modes: Chapter mode (read across perspectives) and Thread mode (follow one perspective through time)
- Statistical time series with chart rendering

#### New Types (already in types.ts)

```typescript
LongArcTopic        // Top-level container
ArcPerspective      // An ideological tradition spanning the full arc
ArcChapter          // A sequential phase (e.g., "The Gilded Age, 1870-1914")
ArcChapterPerspective // The matrix cell: perspective X reads chapter Y
ArcKeyMoment        // A turning point within a chapter (optional link to event)
StatisticalSeries   // Time series for charts (GDP, Gini, labor share)
```

#### New Components Needed

| Component | Purpose |
|-----------|---------|
| `ArcDetail` | Top-level container (replaces EventDetail for arc slugs) |
| `ArcChapterNav` | Horizontal chapter tabs (desktop) / swipeable cards (mobile) |
| `ArcChapterView` | Renders neutral narrative + active perspective's reading |
| `ArcPerspectiveBar` | Persistent perspective selector (ideology name + color dot) |
| `ArcPerspectiveThread` | "Follow one perspective" mode across all chapters |
| `ArcTimeline` | Horizontal timeline with chapter boundaries + event nodes |
| `ArcStatChart` | Line/area chart for statistical series |
| `ArcKeyMomentCard` | Compact card for turning points within chapters |
| `ArcOmissionsPanel` | What this perspective emphasizes/omits per chapter |
| `ArcSourceList` | Canonical works + chapter-specific sources |

#### Navigation Model

Two axes, both always visible:
1. **Chapters** (horizontal, top) — sequential, time-ordered
2. **Perspectives** (vertical sidebar or sticky bar) — persistent lens selector

Default: neutral chapter narrative. Selecting a perspective overlays that perspective's reading.

#### Route Structure

```
/history                  -> Landing (events + arcs listed)
/history/[slug]           -> Event detail (existing)
/history/arc/[slug]       -> Arc detail (new)
```

#### Design Language

Same "Archival Cinema" palette (burnt umber, aged brass, foxed vellum). Arc pages should feel like opening a long-form journal article vs. the spotlight-exhibit feel of event pages. Think: scrolling through a Longform.org piece, but with perspective switching.

---

## 3. Redacted Stubs Cleanup

All 5 previously classified events are now published YAML:
- Armenian Genocide -> `armenian-genocide.yaml`
- Congo Free State -> `congo-free-state.yaml`
- Tiananmen Square -> `tiananmen-square.yaml`
- Holodomor -> `holodomor.yaml`
- Cambodian Genocide -> `cambodian-genocide.yaml`

**Action**: Clear `REDACTED_EVENTS` array in `mockData.ts`. Remove the classified section from HistoryLanding (or keep it empty — the `redacted.length > 0` guard already handles this).

---

## 4. Era Coverage (for landing page filters)

After all 25 events, era distribution:

| Era | Count | Slugs |
|-----|-------|-------|
| Ancient | 1 | ashoka-maurya-empire |
| Classical | 2 | peloponnesian-war, fall-of-rome |
| Medieval | 3 | mongol-conquest-baghdad, the-crusades, mali-empire-mansa-musa |
| Early Modern | 2 | transatlantic-slave-trade, haitian-revolution |
| Modern | 10 | french-revolution, opium-wars, scramble-for-africa, trail-of-tears, armenian-genocide, holodomor, congo-free-state, meiji-restoration, treaty-of-waitangi, bolivarian-revolutions |
| Contemporary | 7 | partition-of-india, hiroshima-nagasaki, rwandan-genocide, creation-of-israel-nakba, fall-of-berlin-wall, tiananmen-square, cambodian-genocide |

---

## 5. Source Enricher CLI

Available for image/source discovery per event:

```bash
python3 pipeline/history/source_enricher.py --event <slug>  # all APIs
python3 pipeline/history/source_enricher.py --list-apis     # see what's available
```

15 free APIs, 12 ready with no config. Output goes to `data/history/enrichment/<slug>.json` for editorial review.

---

## 6. Files Reference

| Path | What |
|------|------|
| `data/history/events/*.yaml` | 25 event content files |
| `data/history/arcs/capitalism-and-communism.yaml` | Arc pilot content (if approved) |
| `frontend/app/history/types.ts` | TypeScript types (events + arcs) |
| `frontend/app/history/mockData.ts` | Mock fallback (needs REDACTED cleanup) |
| `frontend/app/history/components/HistoryLanding.tsx` | Landing page (HOOKS/CTAS for all 25) |
| `supabase/migrations/039_history_tables.sql` | Event tables |
| `supabase/migrations/042_history_arcs.sql` | Arc tables (if approved) |
| `pipeline/history/content_loader.py` | Event YAML -> Supabase |
| `pipeline/history/source_enricher.py` | API source discovery CLI |
