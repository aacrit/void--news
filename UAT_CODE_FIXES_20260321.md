# UAT Code Fixes — void --news Frontend
**Date:** 2026-03-21

---

## CRITICAL FIX 1: Remove Hardcoded Supabase Credentials

**File:** `frontend/app/lib/supabase.ts:1-7`

### Current (Vulnerable):
```typescript
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://xryzskhgfuafyotrcdvj.supabase.co';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhyeXpza2hnZnVhZnlvdHJjZHZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4MTI4NTYsImV4cCI6MjA4OTM4ODg1Nn0._AnBvpTBUa7sqyU_T49bPGi-YOKDkiSptVPGn6YHpRE';
```

### Recommended Fix:
```typescript
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase environment variables. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in .env.local');
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
```

**Why:** Hardcoded credentials in source code is a security risk. If the key is rotated, the fallback exposes an outdated key. Better to fail fast during build if env vars are missing.

**Deployment Impact:** Ensure GitHub Actions workflow and .env.local both set these variables before rebuilding.

---

## CRITICAL FIX 2: Implement Edition Routes

**File:** Create two new files + update HomeContent export

### Add: `frontend/app/us/page.tsx`
```typescript
import HomeContent from "../components/HomeContent";

export default function USEdition() {
  return <HomeContent initialEdition="us" />;
}
```

### Add: `frontend/app/india/page.tsx`
```typescript
import HomeContent from "../components/HomeContent";

export default function IndiaEdition() {
  return <HomeContent initialEdition="india" />;
}
```

### Update: `frontend/app/page.tsx`
```typescript
import HomeContent from "./components/HomeContent";

export default function Home() {
  return <HomeContent initialEdition="world" />;
}
```

**Why:** NavBar links to `/us` and `/india` but those routes don't exist, causing 404. With these route handlers, each edition loads its own data filtered by the correct section.

**Test:**
```
1. Load http://localhost:3000 → world edition ✓
2. Click "US" tab → Navigate to /us → Load US stories ✓
3. Click "India" tab → Navigate to /india → Load India stories ✓
4. Browser back button works correctly ✓
```

---

## CRITICAL FIX 3: Fix DeepDive Fetch Race Condition

**File:** `frontend/app/components/DeepDive.tsx:107-117`

### Current (Problematic):
```typescript
async function loadClusterData() {
  setIsLoadingData(true);
  // Safety timeout: force-close spinner after 5s if fetch never resolves
  const safetyTimeout = setTimeout(() => {
    if (!cancelled) setIsLoadingData(false);  // ← Problem: spinner gone, data maybe still loading
  }, 5000);
  try {
    const raw = await fetchDeepDiveData(story.id);
    if (cancelled || !raw || raw.length === 0) {
      setIsLoadingData(false);
      return;
    }
    // ... process data
    setLiveData({...});
  } catch {
    // Silently fall back
  } finally {
    clearTimeout(safetyTimeout);
    if (!cancelled) setIsLoadingData(false);  // ← Always called, even if data received after timeout
  }
}
```

### Recommended Fix:
```typescript
async function loadClusterData() {
  setIsLoadingData(true);
  const abortController = new AbortController();
  // 8-second timeout: abort fetch if it takes too long
  const timeoutId = setTimeout(() => abortController.abort(), 8000);

  try {
    const raw = await fetchDeepDiveData(story.id, { signal: abortController.signal });

    if (cancelled) return;

    if (!raw || raw.length === 0) {
      setIsLoadingData(false);
      return;
    }

    // Process data and set state
    const dedupedSourceList = [...];
    setLiveData({
      consensus: [...],
      divergence: [...],
      sources: dedupedSourceList,
    });
    setIsLoadingData(false);  // ← Only clear when data arrives
  } catch (err) {
    if (cancelled) return;

    if (err instanceof Error && err.name === 'AbortError') {
      // Fetch timed out
      console.warn('Deep Dive data fetch timeout');
      setLiveData({
        consensus: ['Data fetch timed out. Using cached information.'],
        divergence: [],
        sources: [],
      });
    }
    // Other errors: silently fall back
    setIsLoadingData(false);
  } finally {
    clearTimeout(timeoutId);
  }
}
```

**Why:** The timeout should abort the fetch, not just hide the spinner. Spinner should only disappear when data actually arrives or fetch fails definitively.

**Alternative (Simpler):** Remove the timeout entirely; let native browser timeout (60s default) handle it.
```typescript
// Much simpler: let Supabase client handle timeout
const raw = await fetchDeepDiveData(story.id);  // Supabase client already has built-in timeout
if (cancelled || !raw) {
  setIsLoadingData(false);
  return;
}
// Process and set
setLiveData({...});
setIsLoadingData(false);
```

---

## HIGH FIX 1: Add Story Title Null Check

**File:** `frontend/app/components/DeepDive.tsx:420`

### Current:
```typescript
<h2 className="text-xl" style={{ color: "var(--fg-primary)", marginTop: "var(--space-3)" }}>
  {story.title}
</h2>
```

### Fixed:
```typescript
<h2 className="text-xl" style={{ color: "var(--fg-primary)", marginTop: "var(--space-3)" }}>
  {story.title || "Untitled"}
</h2>
```

**Why:** If Supabase returns a cluster without title (edge case), header renders empty. Fallback ensures visible UI.

---

## HIGH FIX 2: Fix Lean Filter Overlapping Ranges

**File:** `frontend/app/components/FilterBar.tsx:17-22`

### Current (Overlapping):
```typescript
export const LEAN_RANGES: Record<LeanChip, { min: number; max: number } | null> = {
  All: null,
  Left: { min: 0, max: 46 },      // Includes 35-46
  Center: { min: 35, max: 65 },   // Includes 35-46, 54-65
  Right: { min: 54, max: 100 },   // Includes 54-65
};
```

### Fixed (Non-Overlapping):
```typescript
export const LEAN_RANGES: Record<LeanChip, { min: number; max: number } | null> = {
  All: null,
  Left: { min: 0, max: 44 },      // 0-44
  Center: { min: 45, max: 55 },   // 45-55 (strict 10-point center band)
  Right: { min: 56, max: 100 },   // 56-100
};
```

**Why:** With overlapping ranges, a story with lean=50 would match both Left and Center, causing confusion. Strict boundaries ensure each story matches exactly one range.

**Alternative (Asymmetric):**
```typescript
export const LEAN_RANGES: Record<LeanChip, { min: number; max: number } | null> = {
  All: null,
  Left: { min: 0, max: 42 },      // 0-42 (left-leaning)
  Center: { min: 43, max: 57 },   // 43-57 (center-ish)
  Right: { min: 58, max: 100 },   // 58-100 (right-leaning)
};
```

Either version works; choose based on desired "center" band width.

---

## HIGH FIX 3: Add Error State for Failed Queries

**File:** `frontend/app/lib/supabase.ts:9-37`

### Current (Silent Failure):
```typescript
export async function fetchDeepDiveData(clusterId: string) {
  const { data, error } = await supabase
    .from('cluster_articles')
    .select(`...`)
    .eq('cluster_id', clusterId);

  if (error) return null;  // ← Silently returns null; caller doesn't know why
  // ... process data
  return data;
}
```

### Recommended Fix:
```typescript
export interface FetchResult<T> {
  data: T | null;
  error: string | null;
}

export async function fetchDeepDiveData(
  clusterId: string
): Promise<FetchResult<any[]>> {
  const { data, error } = await supabase
    .from('cluster_articles')
    .select(`...`)
    .eq('cluster_id', clusterId);

  if (error) {
    return {
      data: null,
      error: `Failed to fetch cluster articles: ${error.message}`,
    };
  }

  // ... process data
  return { data, error: null };
}
```

### Update Caller (DeepDive.tsx):
```typescript
async function loadClusterData() {
  setIsLoadingData(true);
  try {
    const { data: raw, error: fetchError } = await fetchDeepDiveData(story.id);

    if (fetchError) {
      console.error('Deep Dive fetch error:', fetchError);
      // Render error UI or fallback
      setLiveData({
        consensus: [],
        divergence: [`Data unavailable: ${fetchError}`],
        sources: [],
      });
      setIsLoadingData(false);
      return;
    }

    if (!raw || raw.length === 0) {
      setIsLoadingData(false);
      return;
    }

    // Process and set
    const dedupedSourceList = [...];
    setLiveData({...});
    setIsLoadingData(false);
  } catch (err) {
    // Unhandled exception
    console.error('Deep Dive load error:', err);
    setIsLoadingData(false);
  }
}
```

**Why:** Distinguishing between "no data" and "fetch failed" allows proper error UI. Users get feedback instead of blank pane.

---

## HIGH FIX 4: Mobile Press Analysis Panel Overflow

**File:** `frontend/app/styles/components.css` or new mobile-specific rule

### Add to CSS (or inline styles in DeepDive.tsx:543):
```css
@media (max-width: 767px) {
  .dd-press-expand {
    max-height: calc(60vh - 120px);  /* Leave room for header and spacing */
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;  /* Smooth scroll on iOS */
  }

  .dd-press-expand__inner {
    /* Ensure padding is inside the scrollable area */
    padding: var(--space-3);
  }
}

@media (min-width: 768px) {
  .dd-press-expand {
    /* Desktop: no height constraint, expands naturally */
    max-height: none;
  }
}
```

**Why:** On mobile bottom-sheet (maxHeight: 80vh), nested expandable content should have its own scroll container so it doesn't overflow the parent.

---

## HIGH FIX 5: FilterBar Chips Overlap on 375px

**File:** `frontend/app/styles/components.css`

### Add Responsive Rule:
```css
/* Mobile: Categories in first row, Lean in second row */
@media (max-width: 575px) {
  .filter-bar {
    display: grid;
    grid-template-columns: auto auto auto auto auto auto;  /* 6 category chips */
    gap: var(--space-2);
    margin-bottom: var(--space-3);
  }

  .filter-bar::after {
    content: '';
    grid-column: 1 / -1;  /* Force wrap */
  }

  /* Lean chips in separate row */
  .lean-chips-row {
    display: flex;
    gap: var(--space-2);
    flex-wrap: wrap;
    justify-content: center;
  }
}

/* Tablet and up: single row */
@media (min-width: 576px) {
  .filter-bar {
    display: flex;
    gap: var(--space-2);
    flex-wrap: wrap;
  }
}
```

### Update FilterBar Component Structure:
Instead of all chips in one `.filter-bar`, separate them into category and lean sections (or keep single row but allow wrap).

**Simpler Approach:** Just allow flex-wrap with ellipsis:
```css
.filter-bar {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
  justify-content: flex-start;
}

/* On 375px, chips will naturally wrap to 2 rows */
@media (max-width: 375px) {
  .filter-bar {
    justify-content: center;  /* Center wrap on tiny screens */
  }
}
```

---

## MEDIUM FIX 1: Sigil Divergence Visual Feedback

**File:** `frontend/app/styles/components.css`

### Add CSS Classes:
```css
.sigil {
  /* Base styles */
}

.sigil--divergent svg circle[opacity="0.9"] {
  /* The fill ring */
  stroke: var(--divergence-color, #EF4444);
  stroke-dasharray: none;  /* Switch to dashed if desired */
  stroke-width: 2.2;  /* Slightly thicker ring */
  opacity: 1;
  animation: sigil-pulse 2s ease-in-out infinite;
}

.sigil--divergent::after {
  /* Outer glow or indicator dot */
  content: '';
  position: absolute;
  top: -2px;
  right: -2px;
  width: 8px;
  height: 8px;
  background: var(--divergence-color, #EF4444);
  border-radius: 50%;
  box-shadow: 0 0 4px var(--divergence-color, #EF4444);
}

.sigil--consensus svg circle[opacity="0.9"] {
  /* The fill ring */
  stroke: var(--consensus-color, #22C55E);
  stroke-width: 1.8;  /* Slightly thinner ring for "unified" feel */
  opacity: 0.9;
}

@keyframes sigil-pulse {
  0%, 100% { opacity: 0.9; }
  50% { opacity: 1; }
}
```

### Update Component (Sigil.tsx:504-510):
```typescript
const ringClass = data.divergenceFlag === "divergent"
  ? " sigil--divergent"
  : data.divergenceFlag === "consensus"
    ? " sigil--consensus"
    : "";

return (
  <div ref={ref} className={`sigil${ringClass}`}
    title={ringTitle}
    // ... rest
  >
```

**Why:** Visual distinction helps users see at a glance whether sources agree or disagree. Animation draws attention without being distracting.

---

## MEDIUM FIX 2: "Why This Story" Mobile Accessibility

**File:** `frontend/app/components/StoryCard.tsx:74-90`

### Current (Hidden on Mobile):
```typescript
{(() => {
  const reasons = whyThisStory({...});
  return reasons.length > 0 ? (
    <span className="story-card__why" title={reasons.join(" / ")}>
      {reasons[0]}
    </span>
  ) : null;
})()}
```

### Option A: Show on Mobile, Hide on Desktop
```typescript
{(() => {
  const reasons = whyThisStory({...});
  return reasons.length > 0 ? (
    <>
      {/* Mobile: visible text */}
      <span className="story-card__why story-card__why--mobile"
        style={{ display: "block", fontSize: "var(--text-xs)", color: "var(--fg-tertiary)" }}>
        {reasons[0]}
      </span>
      {/* Desktop: title tooltip */}
      <span className="story-card__why story-card__why--tooltip"
        title={reasons.join(" / ")}>
        Why this story
      </span>
    </>
  ) : null;
})()}

@media (max-width: 767px) {
  .story-card__why--tooltip { display: none; }
}

@media (min-width: 768px) {
  .story-card__why--mobile { display: none !important; }
}
```

### Option B: Add to Sigil Popup (Best UX)
```typescript
// In Sigil.tsx SigilPopup, add a section:
<div style={{ padding: "10px 16px", borderTop: "1px solid var(--border-subtle)" }}>
  <span style={{ fontSize: "var(--text-xs)", color: "var(--fg-tertiary)" }}>
    Why this story
  </span>
  <p style={{ fontSize: "var(--text-sm)", marginTop: "4px" }}>
    {reasons.join(" • ")}
  </p>
</div>
```

**Why:** "Why This Story" is a ranking signal explanation; should be accessible both via tooltip (desktop) and visible context (mobile).

---

## Summary of Changes

| Fix | File | Lines | Complexity | Effort |
|-----|------|-------|-----------|--------|
| Remove credentials | supabase.ts | 4-5 | Low | 5 min |
| Add routes | pages | new | Low | 15 min |
| Fix fetch race | DeepDive.tsx | 107-117 | Medium | 10 min |
| Add error state | supabase.ts + DeepDive.tsx | 9-37 + 110+ | Medium | 20 min |
| Story title null | DeepDive.tsx | 420 | Low | 2 min |
| Lean ranges | FilterBar.tsx | 17-22 | Low | 5 min |
| Mobile press panel | CSS/inline | new rule | Low | 10 min |
| FilterBar mobile | CSS | new rule | Low | 15 min |
| Sigil divergence | CSS + Sigil.tsx | new + 504 | Medium | 20 min |
| Why story mobile | StoryCard.tsx | 74-90 | Low | 15 min |

**Total Estimated Time:** ~117 minutes (1 hour 57 minutes)

---

**All changes are backward-compatible and follow the existing codebase patterns.**

