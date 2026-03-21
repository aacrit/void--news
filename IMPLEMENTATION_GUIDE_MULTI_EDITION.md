# Implementation Guide: Multi-Edition System
**Issue:** F-001 CRITICAL — Multi-Edition System Not Implemented
**Objective:** Add support for 5 editions (World, US, India, Nepal, Germany)
**Estimated Effort:** 4-6 hours
**Files to Modify:** 8 files

---

## Overview

The frontend currently only supports 2 sections ("world", "us"), but the test brief requires 5 editions:
1. World
2. US
3. India
4. Nepal
5. Germany

This guide provides step-by-step instructions to implement full multi-edition support.

---

## Step 1: Update TypeScript Types

**File:** `/home/aacrit/projects/void-news/frontend/app/lib/types.ts`

**Current (line 158):**
```typescript
export type Section = "world" | "us";
```

**Change to:**
```typescript
export type Section = "world" | "us" | "india" | "nepal" | "germany";
```

**Rationale:** This is the single source of truth for edition types throughout the frontend. All components that reference `Section` will automatically support 5 editions once this type is updated.

---

## Step 2: Update NavBar Component

**File:** `/home/aacrit/projects/void-news/frontend/app/components/NavBar.tsx`

### 2a. Add Edition Constants

**After line 28, add:**
```typescript
const EDITIONS: Section[] = ["world", "us", "india", "nepal", "germany"];

const EDITION_LABELS: Record<Section, string> = {
  world: "World",
  us: "US",
  india: "India",
  nepal: "Nepal",
  germany: "Germany",
};

const EDITION_ICONS: Record<Section, React.ReactNode> = {
  world: <Globe size={14} weight="light" aria-hidden="true" />,
  us: <Flag size={14} weight="light" aria-hidden="true" />,
  india: <Globe size={14} weight="light" aria-hidden="true" />,
  nepal: <Globe size={14} weight="light" aria-hidden="true" />,
  germany: <Globe size={14} weight="light" aria-hidden="true" />,
};
```

You can customize icons for each edition later (e.g., flag emojis or different icon sets).

### 2b. Update Dateline Format

**Line 66-68, replace with:**
```typescript
{getEditionLabel()} · {capitalize(activeSection)} Edition · {formatDateCompact()}
```

This makes the dateline show: "Morning Edition · World Edition · Mar 20"

### 2c. Update Desktop Edition Tabs

**Line 76-93, replace the hardcoded `.map()` with:**
```typescript
{EDITIONS.map((edition) => (
  <button
    key={edition}
    onClick={() => onSectionChange(edition)}
    aria-current={activeSection === edition ? "page" : undefined}
    className={`nav-tab${activeSection === edition ? " nav-tab--active" : ""}`}
  >
    <span className="nav-tab__inner">
      {EDITION_ICONS[edition]}
      {EDITION_LABELS[edition]}
    </span>
  </button>
))}
```

### 2d. Update Mobile Bottom Navigation

**Line 130-146, replace with:**
```tsx
<nav className="nav-bottom" aria-label="Edition navigation">
  {EDITIONS.map((edition) => (
    <button
      key={`mobile-${edition}`}
      onClick={() => onSectionChange(edition)}
      aria-pressed={activeSection === edition}
      className={`nav-bottom-tab${activeSection === edition ? " nav-bottom-tab--active" : ""}`}
    >
      <span className="nav-tab__inner">
        {EDITION_ICONS[edition]}
        {EDITION_LABELS[edition]}
      </span>
    </button>
  ))}
</nav>
```

**Important:** On mobile at 375px, 5 buttons will be 44px each = 220px total height. Consider:
- Scrollable bottom nav (overflow-y: scroll, max-height: 100px)
- Or tabbed carousel pattern with dots
- Or multi-row grid layout

Choose based on mobile UX testing.

---

## Step 3: Update Page.tsx Queries

**File:** `/home/aacrit/projects/void-news/frontend/app/page.tsx`

### 3a. Update State Initialization

**Line 54, change from:**
```typescript
const [activeSection, setActiveSection] = useState<Section>("world");
```

**To:**
```typescript
const [activeSection, setActiveSection] = useState<Section>("world"); // Default to World
```

No change needed; default is still World. But add a comment for clarity.

### 3b. Verify Supabase Queries

**Lines 81-94**, the queries already use `.eq("section", activeSection)`, so they'll automatically work with all 5 editions once the backend supports them.

**But verify:** The database must have stories with `section IN ('world', 'us', 'india', 'nepal', 'germany')` in the `story_clusters` table.

---

## Step 4: Database Schema Update (Supabase)

**Create new migration file:** `/home/aacrit/projects/void-news/supabase/migrations/010_add_multi_editions.sql`

```sql
-- Add support for India, Nepal, Germany editions
-- Modify CHECK constraints in story_clusters and articles tables

ALTER TABLE story_clusters
  DROP CONSTRAINT IF EXISTS story_clusters_section_check;

ALTER TABLE story_clusters
  ADD CONSTRAINT story_clusters_section_check
    CHECK (section IN ('world', 'us', 'india', 'nepal', 'germany'));

ALTER TABLE articles
  DROP CONSTRAINT IF EXISTS articles_section_check;

ALTER TABLE articles
  ADD CONSTRAINT articles_section_check
    CHECK (section IN ('world', 'us', 'india', 'nepal', 'germany', 'other'));

-- Update default section (still 'world')
-- No change needed; existing DEFAULT 'world' is fine

-- Create indexes for the new editions
CREATE INDEX IF NOT EXISTS idx_clusters_india ON story_clusters(section, headline_rank DESC)
  WHERE section = 'india';

CREATE INDEX IF NOT EXISTS idx_clusters_nepal ON story_clusters(section, headline_rank DESC)
  WHERE section = 'nepal';

CREATE INDEX IF NOT EXISTS idx_clusters_germany ON story_clusters(section, headline_rank DESC)
  WHERE section = 'germany';

-- Add indexes for articles
CREATE INDEX IF NOT EXISTS idx_articles_india ON articles(section)
  WHERE section = 'india';

CREATE INDEX IF NOT EXISTS idx_articles_nepal ON articles(section)
  WHERE section = 'nepal';

CREATE INDEX IF NOT EXISTS idx_articles_germany ON articles(section)
  WHERE section = 'germany';
```

---

## Step 5: Update Data Sources

**File:** `/home/aacrit/projects/void-news/data/sources.json`

The brief mentions "22 new India/Nepal/Germany sources added". Verify:
1. New sources include `"section"` field set to "india", "nepal", or "germany"
2. Each source has RSS feed URL and proper configuration
3. Sources are in the 3-tier structure (us_major, international, independent)

**Example entry:**
```json
{
  "name": "The Indian Express",
  "slug": "the-indian-express",
  "url": "https://indianexpress.com",
  "rss_url": "https://indianexpress.com/feed/",
  "tier": "international",
  "section": "india",
  "country": "IN",
  "political_lean": 45
}
```

---

## Step 6: Update Pipeline (Optional - Not Blocking Frontend)

**File:** `/home/aacrit/projects/void-news/pipeline/main.py`

The pipeline must assign new sources to the correct edition during clustering:

**In the CLUSTER step (step 6), verify:**
```python
# Assign articles to editions based on source.section
cluster_section = determine_cluster_section(cluster_articles)
# If all articles from Indian sources → section = 'india'
# If mixed → use majority or default to 'world'
```

This is backend logic and can be implemented in a follow-up task.

---

## Step 7: Update CSS (Mobile Layout)

**File:** `/home/aacrit/projects/void-news/frontend/app/styles/responsive.css`

Add styles to handle 5 edition buttons on mobile. If using scrollable bottom nav:

```css
.nav-bottom {
  display: flex;
  overflow-x: auto;
  max-height: 60px;
  gap: var(--space-2);
  padding: var(--space-2);
  scroll-snap-type: x mandatory;
}

.nav-bottom-tab {
  flex-shrink: 0;
  scroll-snap-align: center;
  width: 80px; /* Adjust based on 5 buttons */
  min-height: 44px;
}

/* Or use a multi-row grid layout */
@media (min-width: 375px) and (max-width: 500px) {
  .nav-bottom {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--space-2);
    max-height: 120px;
  }

  .nav-bottom-tab {
    width: auto;
    min-height: 44px;
  }
}
```

Test and choose the layout that fits best.

---

## Step 8: Testing Checklist

### Phase 1: Type System
- [ ] TypeScript compiles with no errors
- [ ] All Section references accept 5 editions
- [ ] NavBar component renders without type errors

### Phase 2: UI Display
- [ ] Desktop: 5 edition tabs visible in header (World, US, India, Nepal, Germany)
- [ ] Mobile: 5 edition buttons visible in bottom nav (44px+ touch targets)
- [ ] Dateline shows edition branding (e.g., "World Edition · Morning Edition · Mar 20")
- [ ] Active edition tab/button is highlighted

### Phase 3: Navigation
- [ ] Clicking each edition tab changes activeSection state
- [ ] Clicking each mobile button changes activeSection state
- [ ] "All" category filter resets when switching editions
- [ ] Facts/Opinion toggle preserves when switching editions

### Phase 4: Data Loading
- [ ] World edition loads stories with section='world'
- [ ] US edition loads stories with section='us'
- [ ] India edition shows "Presses Warming Up" (no data yet)
- [ ] Nepal edition shows "Presses Warming Up" (no data yet)
- [ ] Germany edition shows "Presses Warming Up" (no data yet)

### Phase 5: Deep Dive
- [ ] Story cards remain clickable across all editions
- [ ] Deep Dive panel opens and displays bias data
- [ ] Deep Dive closes and returns to edition feed

### Phase 6: Mobile Layout
- [ ] Mobile bottom nav does not cause horizontal overflow
- [ ] Touch targets are accessible and clearly identifiable
- [ ] Mobile view is readable at 375px width

---

## Code Locations Summary

| File | Change | Lines |
|------|--------|-------|
| `frontend/app/lib/types.ts` | Update Section type | 158 |
| `frontend/app/components/NavBar.tsx` | Add EDITIONS constants, update dateline, render 5 tabs | 28-147 |
| `frontend/app/page.tsx` | Verify Supabase queries (no changes needed) | 81-94 |
| `supabase/migrations/010_add_multi_editions.sql` | Create migration | NEW |
| `data/sources.json` | Verify 22 new India/Nepal/Germany sources | ALL |
| `frontend/app/styles/responsive.css` | Add mobile nav layout styles | NEW |
| `pipeline/main.py` | Update edition assignment logic (optional) | TBD |
| `frontend/app/components/*.tsx` | No changes needed | - |

---

## Deployment Order

1. **Local Testing:** Implement Steps 1-3, test locally
2. **Database Migration:** Apply Step 4 migration to Supabase
3. **Source Data:** Populate Step 5 sources in data/sources.json
4. **Pipeline Update:** Implement Step 6 in pipeline (can be async)
5. **CSS Polish:** Apply Step 7 styles based on testing
6. **Regression Testing:** Full test suite per Step 8
7. **Deploy:** Push to GitHub Pages

---

## Known Risks

1. **Mobile Layout Overflow:** 5 buttons on 375px may not fit. Plan for scroll/grid fallback.
2. **Empty State:** India/Nepal/Germany will show "Presses Warming Up" until pipeline populates data. This is OK.
3. **Source Configuration:** Ensure all 22 new sources have correct `section` field set in sources.json.
4. **Supabase Migration:** Test migration in dev database first before applying to production.

---

## Success Criteria

✓ All 5 editions (World, US, India, Nepal, Germany) available in UI
✓ Clicking each edition loads correct stories or shows empty state
✓ Dateline shows edition branding
✓ Mobile layout handles 5 tabs without overflow
✓ No TypeScript errors
✓ No console errors in browser
✓ Keyboard navigation works for all 5 editions
✓ Accessibility (WCAG 2.1 AA) maintained

---

## References

- CLAUDE.md: Multi-edition system specification
- Frontend type system: `/home/aacrit/projects/void-news/frontend/app/lib/types.ts`
- NavBar component: `/home/aacrit/projects/void-news/frontend/app/components/NavBar.tsx`
- Database schema: `/home/aacrit/projects/void-news/supabase/migrations/001_initial_schema.sql`
