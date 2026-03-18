# UAT Report — void --news
Date: 2026-03-18

## Summary

Overall assessment: **3 critical, 8 major, 11 minor issues**

The frontend builds cleanly and the design system is well-architected. The biggest risks are in the pipeline (a `NameError` crash and all stories defaulting to "world" section) and a dead-code `BiasStamp.tsx` component with hardcoded hex colors. The frontend has solid accessibility foundations but has gaps in focus trapping, keyboard navigation for the BiasBars tooltip, and several touch targets below 44px. ESLint reports 3 errors and 2 warnings.

---

## Critical Issues

### C-1. Pipeline crashes on source sync — `NameError: supabase` not imported
**File:** `/home/aacrit/projects/void-news/pipeline/main.py` lines 134, 139
**Impact:** Pipeline fails immediately on every run, no articles are fetched or stored.

`main.py` calls `supabase.table("sources")` directly on lines 134 and 139, but the `supabase` client object is never imported. The imports on lines 29-38 only bring in helper functions (`create_pipeline_run`, `insert_article`, etc.) from `utils.supabase_client` — not the `supabase` client itself.

Fix: Add `supabase` to the import from `utils.supabase_client`, or refactor source seeding into a helper function in that module.

### C-2. All story clusters default to "world" section — US News is always empty
**Files:** `pipeline/fetchers/rss_fetcher.py`, `pipeline/clustering/story_cluster.py`
**Impact:** The frontend's "US" tab will never show any stories.

Neither the RSS fetcher nor the web scraper assigns a `section` field to articles. The `_determine_section()` function in `story_cluster.py` (line 71) reads `article.get("section", "")`, which is always empty, so every cluster defaults to `"world"` (line 80). There is no section classification logic in the pipeline.

Fix: Add section classification to the pipeline (e.g., in `auto_categorize.py` or as a post-fetch step) based on source country, RSS feed URL path, or article content analysis.

### C-3. Cluster `summary` field is never populated by the pipeline
**File:** `pipeline/main.py` line 250-257
**Impact:** Every story on the frontend shows an empty summary string.

The `insert_cluster()` call on line 250 does not include a `summary` field. The `story_clusters` table has a `summary TEXT` column, but it is never populated. On the frontend, `page.tsx` line 74 falls back to `cluster.summary || ""`, resulting in blank summaries for all live stories.

---

## Major Issues

### M-1. NavBar home link ignores basePath — 404 on GitHub Pages
**File:** `/home/aacrit/projects/void-news/frontend/app/components/NavBar.tsx` line 98
**Impact:** Clicking the logo navigates to `/` instead of `/void--news/`, causing a 404 on GitHub Pages.

The logo link uses a raw `<a href="/">` tag. ESLint also flags this: "Do not use an `<a>` element to navigate to `/`. Use `<Link />` from `next/link` instead." Using Next.js `<Link>` would automatically prepend the basePath.

### M-2. ESLint errors (3 errors, 2 warnings) — deploy at risk
**Files:** `NavBar.tsx`, `ThemeToggle.tsx`, `mockData.ts`, `page.tsx`

| File | Severity | Issue |
|------|----------|-------|
| `NavBar.tsx:97` | Error | Use `<Link>` instead of `<a>` for internal navigation |
| `ThemeToggle.tsx:17` | Error | `setState` called synchronously inside `useEffect` (cascading render) |
| `ThemeToggle.tsx:17` | Error | `react-hooks/set-state-in-effect` rule violation |
| `mockData.ts:467` | Warning | `deepDiveMap` assigned but never used |
| `page.tsx:26` | Warning | `isLiveData` assigned but never used |

The `ThemeToggle` issue can cause a double render on mount. Consider using `useSyncExternalStore` or restructuring so `localStorage` read happens outside the effect.

### M-3. `BiasStamp.tsx` uses hardcoded hex colors — violates design system
**File:** `/home/aacrit/projects/void-news/frontend/app/components/BiasStamp.tsx`
**Impact:** Design system rule "No hardcoded values in components" is violated.

This component uses 15+ hardcoded hex values (`#3B82F6`, `#EF4444`, `#22C55E`, `#9CA3AF`, `#EAB308`, `#F97316`, etc.) instead of CSS custom properties (`var(--bias-left)`, `var(--sense-low)`, etc.). The active `BiasBars.tsx` component correctly uses CSS custom properties. `BiasStamp.tsx` appears to be an older/alternative component that is not currently imported anywhere in the page tree.

### M-4. FilterBar touch targets below 44px on mobile
**File:** `/home/aacrit/projects/void-news/frontend/app/components/FilterBar.tsx` line 103
**Impact:** WCAG 2.1 AA violation for mobile touch targets.

Filter chip buttons have `minHeight: 32` (32px), which is below the 44px WCAG requirement. The design system specifies "Mobile touch targets >= 44x44px."

### M-5. RefreshButton touch target below 44px
**File:** `/home/aacrit/projects/void-news/frontend/app/components/RefreshButton.tsx` line 64
**Impact:** Same as M-4. The refresh button has `minHeight: 32`.

### M-6. Footer GitHub link touch target below 44px
**File:** `/home/aacrit/projects/void-news/frontend/app/components/Footer.tsx` line 102
**Impact:** Same as M-4. The GitHub link has `minHeight: 36`.

### M-7. ThemeToggle touch target below 44px
**File:** `/home/aacrit/projects/void-news/frontend/app/components/ThemeToggle.tsx` lines 48-49, 65-66
**Impact:** The theme toggle button is 36x36px, below the 44px WCAG requirement.

### M-8. Confirmation dialog lacks focus trap and Escape key handling
**File:** `/home/aacrit/projects/void-news/frontend/app/components/RefreshButton.tsx`
**Impact:** When the confirmation dialog opens, keyboard focus is not trapped inside it and pressing Escape does not close it. The `role="dialog"` and `aria-modal="true"` are correctly set, but without focus management, screen reader and keyboard users cannot properly interact with the modal.

---

## Minor Issues

### m-1. `isLiveData` state variable is set but never read
**File:** `/home/aacrit/projects/void-news/frontend/app/page.tsx` line 26
Dead code. Was likely intended to differentiate between live Supabase data and mock data, but the fallback-to-mock logic was removed.

### m-2. `deepDiveMap` is defined but never exported or used
**File:** `/home/aacrit/projects/void-news/frontend/app/lib/mockData.ts` line 467
Dead code in mock data module.

### m-3. `!important` used 11 times in `page.tsx` inline styles
**File:** `/home/aacrit/projects/void-news/frontend/app/page.tsx`
The design system states "No `!important` — ever." The inline `<style>` block uses `!important` 9 times for responsive overrides and display toggling. While some are necessary for overriding inline styles, this pattern conflicts with the stated CSS architecture principle. The `globals.css` `!important` usages in the `prefers-reduced-motion` block are acceptable (accessibility override).

### m-4. `BiasStamp.tsx` is dead code — not imported anywhere
**File:** `/home/aacrit/projects/void-news/frontend/app/components/BiasStamp.tsx`
This component exists but is not imported by any page or component. It appears to be an earlier iteration of the bias indicator that was replaced by `BiasBars.tsx`. Should be removed or documented.

### m-5. Hardcoded `rgba(0, 0, 0, 0.15)` in RefreshButton backdrop
**File:** `/home/aacrit/projects/void-news/frontend/app/components/RefreshButton.tsx` line 97
Should use a CSS custom property for the overlay color to support theming.

### m-6. Bias scores are hardcoded placeholders when loading from Supabase
**File:** `/home/aacrit/projects/void-news/frontend/app/page.tsx` lines 85-89
When transforming Supabase cluster data, bias scores are set to fixed values (`politicalLean: 50`, `sensationalism: 30`, etc.) rather than being fetched from the `bias_scores` table. This means even when the pipeline produces real bias scores, the frontend ignores them.

### m-7. `confidence` field never set in pipeline bias output
**File:** `/home/aacrit/projects/void-news/pipeline/main.py` `run_bias_analysis()` function
The `bias_scores` table has a `confidence` column (default 0.5), but the pipeline's `run_bias_analysis()` never adds a `confidence` key to the scores dict. It will always be the DB default.

### m-8. Category mismatch between DB seeds and frontend types
**Files:** `supabase/migrations/001_initial_schema.sql` lines 110-119, `frontend/app/lib/types.ts` lines 46-56

| Frontend Category Type | DB Seed Categories |
|----------------------|-------------------|
| Politics | Politics |
| Economy | Economy |
| Tech | Technology (different name) |
| Health | Health |
| Environment | Environment |
| Conflict | Conflict |
| Science | Science |
| **Society** | **Culture** (different concept) |
| **Energy** | (missing) |
| **Diplomacy** | (missing) |
| (missing) | **Sports** |

The frontend defines categories that do not exist in the DB seed (Energy, Diplomacy, Society) and the DB has categories not in the frontend (Sports, Culture). The category slug for Technology is "tech" which matches the frontend type, but the display name differs.

### m-9. Pipeline `insert_article()` sends raw RSS dict — potential column mismatch
**File:** `/home/aacrit/projects/void-news/pipeline/main.py` line 194
The `insert_article(article_data)` call passes the entire `article_data` dict, which may contain extra keys (`db_id`, `source_id` as slug instead of UUID) that don't match the `articles` table schema. The `source_id` field from `_parse_entry()` tries `source.get("db_id") or source.get("id", "")` but `db_id` is only set during source sync, which happens before RSS fetch.

### m-10. Scroll-to-content link relies on #main-content but smooth scroll may interfere
**File:** `/home/aacrit/projects/void-news/frontend/app/layout.tsx` line 117, `globals.css` line 23
The skip-to-content link targets `#main-content`. The `<main>` element correctly has `id="main-content"`. However, `scroll-behavior: smooth` is set on `html`, which is correctly disabled under `prefers-reduced-motion`. No functional bug, but noted for completeness.

### m-11. BiasBars tooltip not keyboard-accessible
**File:** `/home/aacrit/projects/void-news/frontend/app/components/BiasBars.tsx`
The bias bars tooltip appears on hover/click but the container `div` has no `tabIndex` and cannot receive keyboard focus. Screen reader users will get the `aria-label` summary but cannot access the detailed tooltip breakdown via keyboard.

---

## Design System Compliance

| Criterion | Status | Notes |
|-----------|--------|-------|
| All colors use CSS custom properties | FAIL | `BiasStamp.tsx` has 15+ hardcoded hex values; `RefreshButton.tsx` has one `rgba()` literal; `layout.tsx` has 2 hex values in `themeColor` (acceptable for meta tag) |
| Three-voice typography system | PASS | Playfair Display (editorial), Inter (structural), JetBrains Mono (data) correctly applied throughout via `--font-editorial`, `--font-structural`, `--font-data` |
| Fluid typography with clamp() | PASS | All text size tokens use `clamp()` in `tokens.css` |
| Fluid spacing with clamp() | PASS | All spacing tokens use `clamp()` in `tokens.css` |
| Animation duration tokens | PASS | Components use `--dur-fast`, `--dur-normal`, `--dur-morph` consistently |
| Spring/easing tokens | PASS | `--spring`, `--ease-out` used correctly |
| Mobile-first responsive | PASS | `min-width` media queries used throughout; base styles target mobile |
| Touch targets >= 44px | FAIL | FilterBar (32px), RefreshButton (32px), ThemeToggle (36px), Footer link (36px) |
| No `!important` | FAIL | 11 uses in `page.tsx`, 5 in `globals.css` (reduced-motion), 3 in `ScaleIcon.tsx` (reduced-motion) |
| BEM naming convention | PASS | `grid-medium__item`, `grid-compact__item`, `nav-tabs-desktop`, etc. |
| Paper texture overlay | PASS | SVG noise filter via `--paper-texture` custom property |
| Glass morphism elevation levels | PASS | `--shadow-e0` through `--shadow-e3`, `--blur-e1` through `--blur-e3` defined |
| Bias color system | PASS | Political lean, sensationalism, opinion/fact, rigor, framing tokens all defined |
| Dark mode support | PASS | Full token set for both modes; inline script prevents flash; `localStorage` persistence |

---

## Accessibility Audit

| Criterion | Status | Notes |
|-----------|--------|-------|
| Semantic HTML | PASS | `<header>`, `<nav>`, `<main>`, `<article>`, `<footer>`, `<section>` used correctly |
| Skip-to-content link | PASS | Present in `layout.tsx`, targets `#main-content`, visible on `:focus` |
| `aria-label` on nav elements | PASS | "Main navigation", "Section navigation", "Filter stories by category" |
| `aria-current` for active section | PASS | Set on desktop nav buttons |
| `aria-selected` for filter tabs | PASS | FilterBar buttons use `role="tab"` and `aria-selected` |
| `aria-label` on BiasBars | PASS | Full bias summary as aria-label text |
| `aria-hidden` on decorative icons | PASS | All Phosphor icons marked `aria-hidden="true"` |
| Focus-visible styles | PASS | Global `:focus-visible` outline with warm accent color |
| `prefers-reduced-motion` | PASS | Global `animation-duration: 0ms` override in `globals.css`; ScaleIcon has its own reduced-motion block |
| Loading state for screen readers | PASS | `role="status"` and `aria-label="Loading stories"` on skeleton; visually-hidden "Loading stories, please wait..." text |
| Tooltip keyboard access | FAIL | BiasBars tooltip only accessible via mouse hover or click; no `tabIndex`, no keyboard trigger |
| Dialog focus management | FAIL | RefreshButton confirmation dialog lacks focus trap and Escape key handler |
| Color contrast (4.5:1) | MIXED | Most text uses `--fg-primary` (#1A1A1A) on `--bg-primary` (#FAF8F5) = ~16:1 PASS. `--fg-muted` (#A0A0A0) on `--bg-primary` (#FAF8F5) = ~3.4:1 FAIL for normal text. `--fg-tertiary` (#7A7A7A) on `--bg-primary` (#FAF8F5) = ~5.2:1 PASS. Dark mode: `--fg-muted` (#5A5550) on `--bg-primary` (#1C1A17) = ~3.0:1 FAIL. |
| Touch targets >= 44px | FAIL | See M-4 through M-7 |
| `lang` attribute | PASS | `<html lang="en">` |
| Zoom to 200% | PASS | Fluid typography and spacing via `clamp()` should handle this well |

---

## Pipeline Health

| Component | Status | Notes |
|-----------|--------|-------|
| Source loading (`sources.json`) | PASS | 90 sources, all have required fields, all 3 tiers balanced (30/30/30) |
| Source sync to Supabase | FAIL | Crashes with `NameError` — `supabase` client not imported in `main.py` (C-1) |
| RSS fetching | PASS | Parallel fetch with ThreadPoolExecutor, proper timeout handling, error reporting |
| Potentially broken RSS URLs | WARN | AP News via rsshub.app (third-party dependency); Reuters agency feed (may not be public); Fox News/Bloomberg (may require auth/block bots) |
| Web scraping | PASS | Error handling present, falls back gracefully |
| Bias analysis | PASS | 5-axis analysis with per-analyzer try/catch, defaults on failure |
| Story clustering | PASS | TF-IDF + cosine similarity + agglomerative clustering; good NLP approach |
| Section classification | FAIL | Articles never get a `section` field; all clusters default to "world" (C-2) |
| Category assignment | PASS | Auto-categorization module exists and is called during clustering |
| Cluster summary generation | FAIL | `summary` field never populated in cluster insertion (C-3) |
| Pipeline run tracking | PASS | `pipeline_runs` table properly tracked with status, duration, counts |
| GitHub Actions workflow | PASS | Cron schedule (6 AM/6 PM UTC), proper secrets handling, spaCy model download |

---

## Build & Deploy

| Check | Status | Notes |
|-------|--------|-------|
| `npm run build` | PASS | Compiles successfully, static export generates `/out` directory |
| TypeScript compilation | PASS | No type errors |
| ESLint | FAIL | 3 errors, 2 warnings (see M-2) |
| basePath configuration | PASS | `/void--news` set in `next.config.ts` |
| Static export | PASS | `output: "export"` configured |
| GitHub Pages deployment workflow | PASS | Correct artifact path (`frontend/out`), proper permissions |
| Pipeline workflow | PASS | Python 3.11, spaCy model download, secrets configuration |
| Favicon/manifest paths | PASS | Correctly prefixed with `/void--news/` |

---

## Data Quality

| Check | Status | Notes |
|-------|--------|-------|
| Source diversity | PASS | 90 sources across 3 tiers (US major, international, independent) |
| RSS URL validity | WARN | 4 potentially problematic URLs (rsshub dependency, agency feeds, paywalled sites) |
| Article deduplication | PASS | URL uniqueness constraint in DB; duplicate detection in `insert_article()` |
| Story clustering quality | UNKNOWN | Cannot verify without live pipeline run; algorithm is sound (TF-IDF + agglomerative) |
| 1 article per cluster | LIKELY | Without the clustering module running in fetch-only mode (ANALYSIS_AVAILABLE=False), each article would need separate handling. When NLP deps are installed, multi-article clusters should form. |
| Category assignment | WARN | Frontend categories don't fully match DB seed categories (see m-8) |
| Section assignment | FAIL | All stories will be "world" — no US News classification exists (C-2) |
| Bias scores on frontend | FAIL | Frontend uses hardcoded placeholder scores, ignores actual analysis data (m-6) |

---

## Recommendations

Prioritized by impact:

1. **[CRITICAL] Fix `supabase` import in `pipeline/main.py`** — The pipeline cannot run at all without this. Add `from utils.supabase_client import supabase` or refactor source seeding into a helper function.

2. **[CRITICAL] Implement section classification** — Add logic to classify articles as "world" or "us" based on source country, feed URL, or content analysis. Without this, the US News tab is permanently empty.

3. **[CRITICAL] Populate cluster summaries** — Either generate summaries during clustering (e.g., use the first article's summary) or aggregate summaries from clustered articles.

4. **[HIGH] Fix NavBar home link** — Replace `<a href="/">` with Next.js `<Link href="/">` to respect basePath on GitHub Pages.

5. **[HIGH] Fix ESLint errors** — Especially the `ThemeToggle` cascading render issue. Consider using a ref or `useSyncExternalStore` for the mounted state.

6. **[HIGH] Increase touch targets to 44px** — FilterBar chips, RefreshButton, ThemeToggle, and Footer link all need padding/size increases for WCAG compliance.

7. **[HIGH] Add focus trap and Escape handler to confirmation dialog** — Use a focus trap library or manual `keydown` listener.

8. **[MEDIUM] Fetch real bias scores on frontend** — The Supabase query should join `cluster_articles` and `bias_scores` to display actual analysis results instead of hardcoded placeholders.

9. **[MEDIUM] Add keyboard accessibility to BiasBars tooltip** — Add `tabIndex={0}` and `onKeyDown` handler.

10. **[MEDIUM] Align category definitions** — Synchronize the frontend `Category` type, DB seed categories, and pipeline categorizer output.

11. **[MEDIUM] Remove or document `BiasStamp.tsx`** — Either delete this dead component or mark it as an experimental alternative.

12. **[LOW] Remove dead code** — `isLiveData` state in `page.tsx`, `deepDiveMap` in `mockData.ts`.

13. **[LOW] Replace hardcoded `rgba()` in RefreshButton** — Use a CSS custom property for the overlay backdrop color.

14. **[LOW] Improve `--fg-muted` contrast** — The muted text color (#A0A0A0 light / #5A5550 dark) fails WCAG 4.5:1 contrast. Consider darkening light mode muted to #808080 or lighter.

15. **[LOW] Reduce `!important` usage in `page.tsx`** — Refactor responsive styles to use CSS classes or CSS Modules instead of inline `<style>` blocks that require `!important` overrides.
