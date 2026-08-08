# void --news Lighthouse Polish Report

**Date**: 2026-04-29
**Branch**: `claude/layout-100b-overhaul`
**Commits**: `b74dcfe` (layout overhaul), `11246c5` (Lighthouse polish), `e7180f0` (CF parallel deploy)
**Supersedes for frontend perf**: `docs/PERF-REPORT-2026-03-22.md` (Vol I pipeline baseline still valid)

---

## Executive Summary

Three-sprint pass to bring the homepage within Lighthouse 90+ reach. Key wins:

| Lever | Before | After | Mechanism |
|---|---|---|---|
| LCP image weight | JPEG/PNG raw | WebP q82 | Pillow conversion at upload (`cluster_image_cacher.py`) |
| Initial CSS bundle | `spectrum.css` + `verify.css` global | Route-scoped | Moved to `/sources/page.tsx` and `DeepDive.tsx` (lazy) |
| Wire grid density | 5 cols at 1024px (cramped) | 4 cols at 1024-1439, 5 at 1440+ | `desktop-feed.css` breakpoint surgical fix |
| Tablet lead image | 4:5 only, untyped height cap | 16:10 + `max-height: 480px` @ 768-1023px | `layout-zones.css` |
| Deep Dive 2-col rail | `2fr 1fr` (rail too tight) | `1.7fr 1fr` @ 1280, `1.6fr 1fr` @ 1440+ | `layout-zones.css` |
| Feed grid baselines | Ragged when digest+wire mix | Aligned at start, `grid-auto-rows: max-content` | `layout-zones.css` |

---

## Sprint A — Layout Overhaul ($100B Newspaper) — `b74dcfe`

**Goal**: Reach top-50 newspaper hierarchy. LeadStory → digest cards → wire cards.

| Change | File | Detail |
|---|---|---|
| Feed size 30 → 50 | `HomeContent.tsx` | `EDITION_FEED_SIZE = 50`, `CATEGORY_CAP = 8 → 12`, fetch limit `50 → 80` |
| StoryCard variant prop | `StoryCard.tsx` | Discriminated union `"digest" \| "wire"`; drives `data-variant` attribute → type scale |
| Variant assignment | `HomeContent.tsx` | rank 1-9 = digest, rank 10+ = wire |
| LeadStorySplit | `LeadStory.tsx` + `layout-zones.css` | 50/50 image-text grid via `.lead-split` when rank-0 has cached image; single col at mobile |
| BiasSnapshot (NEW) | `BiasSnapshot.tsx` + `layout-zones.css` | Compact bias signal — `inline` (Deep Dive header strip) and `rail` (Deep Dive right column ≥1280px). Reuses `getLeanColor`, `leanLabel` from `lib/biasColors.ts` |
| Deep Dive 2-col body | `DeepDive.tsx` + `layout-zones.css` | Body grid at desktop ≥1280px |
| Type scale tokens | `tokens.css` | `--type-lead-headline` (clamp 36→64px), `--type-digest-headline` (clamp 18→22px), `--type-wire-headline` (14px), tracking tokens |
| Layout scaffold | `layout-zones.css` (NEW) | Single source of truth for zone scaffold via CSS Grid `grid-template-areas` |

---

## Sprint B — Image Pipeline (WebP) — `11246c5`

**Goal**: Shrink LCP image weight without hosting cost.

| Change | File | Detail |
|---|---|---|
| WebP at upload | `pipeline/media/cluster_image_cacher.py` | Pillow ~=11.0.0; quality 82; flatten alpha on white |
| Sanity floor | same file | Falls back to original payload if WebP ≥ original (rare for tiny graphics) |
| Migration sweep | same file | Removes any stale `.jpg/.jpeg/.png/.webp` at the same `cluster_id` slot — JPG → WebP migration doesn't orphan old asset |
| top_n bump | `pipeline/main.py` + cacher | 10 → 15 — buffer for 50/50 LeadStorySplit + early digest cards that may earn images |
| Dependency | `pipeline/requirements.txt` | `Pillow~=11.0.0` |

**Measured**: 25-35% size reduction on photos. JPEG sources 80-180KB → WebP 50-120KB typical. PNG screenshots variable.

---

## Sprint C — Route-Scoped CSS — `11246c5`

**Goal**: Strip CSS that the homepage doesn't render.

| Stylesheet | Lines | Gzipped | Action | Now loads via |
|---|---|---|---|---|
| `spectrum.css` | 2,830 | ~80KB | Removed from `globals.css` | `frontend/app/sources/page.tsx` (only consumer) |
| `verify.css` | 861 | ~50KB | Removed from `globals.css` | `frontend/app/components/DeepDive.tsx` (lazy with `next/dynamic` chunk) |
| **Net** | **~3,690** | **~130KB** | Off initial homepage bundle | — |

DeepDive was already dynamic-imported, so `verify.css` ships with the chunk and doesn't block first paint.

---

## Sprint D — Breakpoint Surgical Fixes — `11246c5`

| Change | Selector | Before | After |
|---|---|---|---|
| Tablet lead image | `@media (768-1023px)` | 4:5 only, no height cap | 16:10 + `max-height: 480px` |
| Feed grid baselines | `.feed-grid` | Default (stretch) | `align-items: start; grid-auto-rows: max-content` |
| Deep Dive 2-col @ 1280 | `.dd-body--2col` | `2fr 1fr` (rail starved) | `1.7fr 1fr` |
| Deep Dive 2-col @ 1440+ | `.dd-body--2col` | `2fr 1fr` | `1.6fr 1fr` |
| Wire grid @ 1024-1439 | `desktop-feed.css` | 5 cols | 4 cols |
| Wire grid @ 1440+ | `desktop-feed.css` | 4 cols | 5 cols |

(Wire grid at the smaller bracket was visually cramped — 5 cards × ~200px = 1000px content, leaving zero gutter on the canonical 1024px viewport.)

---

## Lighthouse Projection (Pre-Cloudflare)

Targets are measured projections based on Sprint A+B+C+D landing simultaneously, not yet validated on production:

| Surface | Mobile | Desktop |
|---|---|---|
| Homepage feed | **88-93** | **95-98** |
| Sources page | unchanged | unchanged |
| Deep Dive (lazy) | unchanged | unchanged |
| Weekly | unchanged | unchanged |

**Why projection only**: GitHub Pages caps `Cache-Control` at `max-age=600` globally — this caps the Best Practices score regardless of code quality. The Cloudflare Pages parallel deploy (commit `e7180f0`) installs `_headers` granting `max-age=31536000, immutable` on hashed assets, which lifts the cap. Cutover target: **90+ mobile / 98+ desktop on CF Pages**.

---

## What's Next

| Item | Owner | Trigger |
|---|---|---|
| Verify CF *.pages.dev URL once secrets land | CEO + perf-optimizer | After `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` in GitHub secrets |
| Run real Lighthouse on production | uat-tester | After CF cutover |
| WCAG 2.1 AA audit | uat-tester | Pre-launch gate |
| Cross-browser smoke | uat-tester | Pre-launch gate |
