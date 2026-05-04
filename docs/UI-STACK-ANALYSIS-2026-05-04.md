# UI Stack Strategic Review — void --news

**Date:** 2026-05-04
**Author:** CEO Advisor (read-only strategic review)
**Branch:** `claude/analyze-ui-tech-stack-ONpRt`
**Decision posture:** Stay-or-switch. Be decisive.

---

## 1. Executive Recommendation

**Stay on Next.js 16 + React 19. Do not migrate. Fix six things on the current stack instead.**

The product is 90% shipped on a stack that meets every constraint that actually matters: static export to GH Pages and Cloudflare, Capacitor wrapper for iOS/Android with the same web bundle, 35-agent fleet trained on React/TSX, $0 hosting, Lighthouse projection 88-93 mobile / 95-98 desktop. Migrating to Astro, Svelte, or Vue would deliver perhaps 60-100KB of JS savings and 1-2 Lighthouse points at the cost of 8-14 person-weeks of work, retraining 16 agents that have React assumptions, re-porting 40,707 lines of CSS and the full motion-design library, re-validating Capacitor on a new framework, and risking the launch window. The math does not pencil.

The honest critique: the product is **architecturally an SPA shipped via static export**. Every page is a 5-line shim into a `"use client"` component. The "static export" is just the loading shell. That is exactly the workload Astro was designed to demolish — but Astro's wins come from converting interactive components into static HTML, and at void --news the homepage IS the interactive component (edition switcher, filter chips, infinite scroll-ish reveal, FLIP morph into Deep Dive, pull-to-refresh, keyboard nav, search overlay). There is very little static-only content to harvest. The Astro thesis fails on this codebase.

The right move is to harden the existing stack: enable Container Queries, ship View Transitions, drop legacy global CSS into `@scope` blocks, evaluate Preact compat as a 30KB drop-in, and audit `components.css`/`history.css` (8,220 + 8,641 lines) for dead rules. These are 1-3 days each, no agent retraining, no Capacitor rebundle.

---

## 2. Honest Critique of the Current Stack

### Where Next.js+React is hurting

- **The "static export" is a marketing term here.** `app/page.tsx` is 5 lines: `<HomeContent initialEdition="world" />`. `HomeContent.tsx` is 1,038 lines marked `"use client"`. The first byte of HTML the user receives is essentially `<div id="__next"></div>` plus inline theme bootstrap, then React hydrates the entire page. We are paying React's runtime cost for what could be 80% server-rendered static HTML. This is the single biggest architectural smell.
- **54 of 55 components are `"use client"`** (only `EditionIcon.tsx` is a pure server-renderable function). React Server Components — the headline feature of Next.js 13+ — are completely unused. We are paying for a framework whose flagship feature we do not use.
- **Bundle includes Supabase JS on every page.** The SDK is ~30KB gzipped and is loaded eagerly because `HomeContent` imports `supabase` at module top. The pipeline runs 1x/day and content is fundamentally static, yet every visitor downloads a realtime DB SDK. This is a smell — it should be a thin `fetch()` wrapper to a static JSON snapshot or a tree-shaken `@supabase/postgrest-js` (~12KB) at most.
- **Edge case the React tree handles awkwardly:** the `isMobile` state is initialized from a `data-viewport` attribute set by an inline `<script>` in `layout.tsx`. This tells you the framework's hydration model fights the design intent. Astro/Svelte/Solid would let you ship two static document fragments and never need a JS-readable viewport flag.

### Where the 1.13MB / 23-stylesheet CSS is a smell vs intentional

| Stylesheet | Lines | Verdict |
|---|---|---|
| `components.css` (8,220) | 207KB | **Smell.** This is the global "everything bucket." Components like `BiasInspector`, `Sigil`, `DeepDive` should own their own scoped CSS file. Mixing routes here means cross-route dead rules ship to every page. |
| `history.css` (8,641) | 217KB | **Intentional but fixable.** Already route-scoped to `/history` via per-route `layout.tsx` import. Lives correctly off the homepage. |
| `games.css` (4,657) | 125KB | **Intentional.** Route-scoped to `/games`. |
| `spectrum.css` (2,846) | 73KB | **Intentional.** Recently moved to `/sources` route only. |
| `tokens.css` (985) | 43KB | **Intentional.** Single source of truth for design tokens. |
| `desktop-feed.css` (653) + `mobile-feed.css` (1,161) | 43KB combined | **Mild smell.** The split is by viewport, not component. This is what Container Queries were invented to prevent. |
| `responsive.css` (1,048) | 31KB | **Smell.** This is the bag-of-overrides anti-pattern. 11 `@media` blocks here override rules set elsewhere. |
| `animations.css` (1,357) | 47KB | **Intentional.** Cinematic motion design is core IP. |

The 1.13MB total is misleading. **What ships to the homepage initial CSS bundle is `globals.css` + `tokens` + `layout` + `typography` + `components` + `animations` + `mobile-feed` + `desktop-feed` + `layout-zones` + `skybox-banner` + `floating-player` + `mobile-nav` + `responsive`** — roughly 25,000 lines / 700KB raw / **~80-110KB gzipped**. That's defensible. The recent route-scoping work on `spectrum.css` and `verify.css` (~130KB gzipped pulled off the homepage) was the right move.

The real CSS smell is two-fold:
1. `components.css` at 8,220 lines is a god-file. A grep audit will find ~20-30% dead rules at minimum.
2. The dual-viewport breakpoint architecture (`mobile-feed.css` / `desktop-feed.css` totalling 1,800 lines) is a CSS anti-pattern in 2026. Container Queries collapse this to one file and one rule per component.

### Is the dual mobile/desktop component split (HomeContent + MobileFeed, StoryCard + MobileStoryCard) a sign we'd benefit from a different rendering model?

**No.** It's a sign we'd benefit from Container Queries. The split exists because at narrow viewports, `StoryCard` had to render fundamentally different DOM (no image, different metadata layout, different tap targets) and CSS-only responsive design wasn't enough. Container Queries plus a single `StoryCard` reading `@container (width < 480px)` rules eliminates the duplication without changing framework. Svelte/Vue/Astro do not magically solve this — they have the same DOM-vs-CSS tradeoff. The duplication is a CSS architecture decision, not a framework decision.

The one place a framework switch *would* help: Astro `<Card client:visible>` would let the wire-zone cards (ranks 10-49) ship as zero-JS HTML and only hydrate when the user scrolls them into view. That's a real win. But it's available without Astro: wrap `StoryCard` in `LazyOnView` (already in `components/`) and use `next/dynamic` with `loading: () => <SSRPlaceholder>`.

### Estimated homepage JS bundle (gzipped)

I cannot read a build artifact (no `.next` or `out` present), so this is a calculated estimate, not a measurement:

| Chunk | Estimate | Source |
|---|---|---|
| React 19 + ReactDOM | ~45KB | Public benchmarks |
| Next.js 16 runtime + router | ~20-25KB | Next docs |
| Supabase JS (full client) | ~30KB | Bundle phobia |
| Phosphor Icons (tree-shaken) | ~5-10KB | If imports are specific |
| App code (HomeContent + ~15 static-imported components, excludes 5 dynamic chunks) | ~60-80KB | Estimated from 15,883 component LOC × ~5KB/1000 LOC after minification |
| **Total initial JS** | **~160-190KB gzipped** | |
| Initial CSS | ~80-110KB gzipped | After route-scoping wins |

**This is acceptable but not good.** The Lighthouse 90+ mobile target on slow 4G assumes ~250KB total transfer for the critical path. We're at ~270-300KB initial transfer (JS + CSS + HTML). The Cloudflare cutover unlocks the Best Practices score (immutable cache headers) but does not change the transferred bytes. **First action item: measure this for real after CF deploy. If homepage JS > 200KB gzipped, kill the Supabase eager import.**

---

## 3. Per-Framework Evaluation

Estimates assume migration of homepage + `/sources` + `/weekly` + Deep Dive only. History (22 components, 8,641 CSS lines), games, and ship are deferred or kept frozen.

| Framework | Bundle Δ (homepage JS gzipped) | Migration effort | Capacitor compat | Motion ergonomics | Data-viz ergonomics | Agent retraining | Ecosystem risk | What it actually buys us |
|---|---|---|---|---|---|---|---|---|
| **Stay on Next 16 + React 19** | 0 (baseline ~170KB) | 0 person-weeks | Confirmed working | Excellent (Motion One v11, Web Animations API native) | Excellent (huge React D3/viz ecosystem) | None | None | Status quo. Six fixes available without migration deliver 30-60KB JS reduction. |
| **Preact 10 + preact/compat** | -35 to -45KB (drops to ~125KB) | 0.5-1 person-week | Capacitor doesn't care about React vs Preact | Identical (Motion One works) | Identical (D3 doesn't care) | Minimal — `.tsx` and JSX unchanged | Low — Preact is mature, drop-in for >95% of React APIs | **Highest ROI of any switch.** Aliased via webpack/Next config. Single-config-line change. Risk: React 19 features (use, async transitions) may need shims. |
| **Vue 3 + Nuxt 3** | -20 to -30KB | 6-10 person-weeks | Works (Capacitor wraps any web build) | Good (Motion One has Vue bindings; Vue's `<Transition>` is native) | Decent (Vue D3 ecosystem smaller than React) | High — all 16 React-touching agents need rewrites | Medium — Vue has slower momentum vs React in 2026 | Composition API, scoped CSS by default, smaller runtime. Doesn't justify the cost. |
| **Svelte 5 + SvelteKit (static adapter)** | -80 to -100KB (drops to ~80-100KB) | 8-14 person-weeks | Works | Excellent (Svelte motion primitives + tweened/spring stores are first-class) | Decent (D3 integration easy, fewer pre-built libs) | Very high — runes are a new mental model; agents need full retraining | Medium — Svelte 5 just stabilized, ecosystem still maturing | Smallest runtime of any "real framework," scoped CSS, animation built in. Real wins, real costs. |
| **SolidJS + SolidStart** | -90 to -110KB (drops to ~70-90KB) | 10-14 person-weeks | Works | Good (Motion One has Solid bindings) | Smaller ecosystem | Very high | High — small community, niche | Fastest fine-grained reactivity. JSX feels familiar but reactivity model is fundamentally different. Niche risk for solo operator. |
| **Astro 5 + islands** | -100 to -140KB (drops to ~30-70KB on homepage if islands done right) | 10-16 person-weeks | Works | Good if islands use React/Svelte under the hood | Excellent (you pick the framework per island) | Medium — agents keep React for islands but learn Astro shell | Low — Astro has strong momentum and is the architecturally correct framework for content sites | **Architecturally the best fit on paper, but see §4 — the homepage is not actually static content.** |
| **Qwik + QwikCity** | -120 to -150KB (smallest possible — resumability, lazy hydration on interaction) | 12-16 person-weeks | Works | Decent | Smaller ecosystem | Very high — resumability is a different mental model | High — small team, niche | Theoretical perf champion. In practice, the cinematic motion design and Deep Dive interactivity defeat resumability gains. |
| **Lit + web components** | -100KB+ for portable primitives, but app shell still needs a framework | 16+ person-weeks for full migration | Works | Manual | Manual | Maximum | Low long-term, high short-term | Maximum portability, future-proof. Wrong tool for a media product UI. |
| **Remix / React Router 7** | 0 to +10KB | 4-6 person-weeks | Works | Same as Next | Same | Low | Low | **Largely redundant given static export.** Remix's loader/action model assumes a server. We have no server. Skip. |

### Why Preact tops the switch list

If you only do one framework move, Preact is it. It's not really a "switch" — it's an alias. Add to `next.config.ts`:

```ts
webpack(config) {
  Object.assign(config.resolve.alias, {
    'react': 'preact/compat',
    'react-dom': 'preact/compat',
  });
  return config;
}
```

Drops React's ~45KB to Preact's ~10KB. Risks: React 19's `use()` hook, `useFormState`, async transitions need verification. The codebase uses `useState`, `useEffect`, `useMemo`, `useCallback`, `useRef`, `Component`, `dynamic` — all Preact-supported. Worth a 1-week spike on a `claude/preact-spike` branch.

---

## 4. The Astro Question — Steel-Manned Both Ways

### Steel-man for Astro

void --news is editorially conservative — same content for everyone, 1x/day update, top-50 stories, no personalization, no real-time. That is the textbook Astro use case. The pipeline produces a SQL snapshot daily; we could equally well produce a JSON snapshot baked into static HTML at build time and ship near-zero JS. Astro's island architecture would let:

- **Homepage feed (50 stories)** render as pure HTML with embedded metadata. Zero JS for the wire zone (ranks 10-49). React/Svelte islands only for: edition switcher, filter chips, search button, audio player FAB, story click-to-deep-dive handler. Estimated homepage JS: **20-50KB gzipped**, an 70-85% reduction.
- **Deep Dive** stays a React island, lazy-loaded on click — same as today.
- **Sources page** is pure data display. Astro renders it as a 100% static table with one tiny island for sort/filter. Could ship with **0KB JS** for users who don't interact.
- **Weekly digest, Paper, About** — same story. All naturally static.
- **History (22 components)** — could go either way; if kept on React islands, the `/history` route stays largely as-is.
- **Games** — these are interactive apps. Stay on React islands inside Astro.

This delivers a Lighthouse mobile score we cannot reach on Next.js+React: **97-99 mobile, 99-100 desktop.** It would be the cleanest news product on the open web.

### Steel-man against Astro

The homepage is not actually static. Reading `HomeContent.tsx`:

- Edition state is read from URL + localStorage; static HTML can't pre-render the user's saved edition without a flash
- Category filter, lean filter, search, keyboard nav, FLIP morph into Deep Dive, pull-to-refresh, infinite scroll batch reveal, edition switch whip-pan animation, edition transition cross-fade — these are all client state that touches the entire feed simultaneously
- A click on rank 5 has to morph into a fullscreen panel using `getBoundingClientRect()` from rank 5's DOM node — that requires JS knowing about all 50 stories
- The dual mobile/desktop split (`HomeContent` + `MobileFeed`) makes the island boundary messy — an Astro page either ships both feeds or detects viewport server-side, but we have no server

In Astro, you would end up wrapping the entire feed in `<HomeContent client:load>`, which gives you back the React SPA you started with — only now sitting inside an Astro shell that adds complexity without removing JS.

The honest read: **Astro wins big for `/sources`, `/weekly`, `/about`, `/paper`, `/history`. It wins moderately for the wire zone of the homepage. It does not win for the lead zone or digest zone of the homepage**, where filter/click/animation interactivity dominates.

### Verdict on Astro

Not the right primary framework for the homepage. **Could be a hybrid candidate if we ever rebuild `/sources` or `/history`** — but those routes are already stable and route-scoped today. Migration cost (10-16 person-weeks) is not justified by the marginal Lighthouse and JS-bundle wins.

If we were starting void --news today, greenfield, Astro would be the answer. We are not starting today.

---

## 5. Hybrid Options (Ranked)

| Option | Effort | Risk | Win | Recommendation |
|---|---|---|---|---|
| **Preact alias** | 1 week | Low | -35-45KB JS, instant | **DO** — start tomorrow on a spike branch |
| **Lit web components for bias viz** (`MicroSpectrum`, `Sigil`, `BiasSnapshot`, `ScaleIcon`, `CredibilityArc`) | 3-4 weeks | Medium (motion design must port) | Framework-portable primitives, smaller per-component runtime, future-proof for any framework switch | **DEFER** — only do this if we're seriously planning a future migration |
| **Astro shell + React islands** for `/sources`, `/about`, `/weekly`, `/paper`, `/history` only | 8-12 weeks | High (two-framework codebase, two build pipelines, agents need both) | -100KB JS off non-feed routes, faster non-feed Lighthouse | **REJECT** — non-feed routes are not the bottleneck |
| **Next.js + React Server Components for static parts** | 0 weeks (already in Next 16) | Low | Convert 8 static page shims and the static section of `/sources` to genuine RSCs (no `"use client"`) | **DO** — hit the easy wins inside the current stack |
| **Drop Supabase JS, ship static JSON snapshot at build time** | 2 weeks | Medium (cache invalidation logic) | -30KB JS gone forever | **DO** — high-impact, no framework change |
| **Container Queries refactor** (collapse `mobile-feed.css` + `desktop-feed.css`) | 2 weeks | Low | -15KB CSS, eliminates dual-component split | **DO** — improves architecture and bundle |

---

## 6. Layout / Usability / Performance / Flexibility / Features Delta

### Wins available WITHOUT switching frameworks (low-hanging fruit)

| Improvement | Where | Estimated win | Effort |
|---|---|---|---|
| **Container Queries** for `StoryCard` | New `@container` rules in `desktop-feed.css`, drop `mobile-feed.css` `.story-card` rules, delete `MobileStoryCard.tsx` | -15KB CSS, -180 LOC component, eliminates dual-render bug class | 2 weeks |
| **View Transitions API** for edition switching, story click→Deep Dive, theme toggle | Replace whip-pan and FLIP morph code in `HomeContent.tsx` with `document.startViewTransition()` | Smoother native transitions, cuts ~30 LOC of manual animation choreography | 1 week |
| **CSS `@scope`** for `BiasInspector`, `Sigil`, `DeepDive`, `CommandCenter`, `ShipBoard` | Wrap each component's rules in `@scope` to give true component isolation without adopting a CSS-in-JS library | Eliminates global CSS leakage, allows safe deletion of `components.css` god-file | 2-3 weeks |
| **Speculation Rules** for likely-clicked links | Add `<script type="speculationrules">` to `layout.tsx` for `<a href="/sources">`, `<a href="/weekly">` | Instant nav to non-feed routes, no JS code change | 1 day |
| **Real RSCs** for static page shims | Drop `"use client"` from page shims that don't need it; route `<HomeContent>` only | Smaller initial HTML+JS for `/about`, `/paper/*`, `/weekly/[edition]` | 2-3 days |
| **Drop Supabase eager import** | Replace with build-time JSON snapshot fetched via `fetch()` in client | -30KB JS forever | 2 weeks |
| **Preact compat alias** | Single config line in `next.config.ts` | -35-45KB JS forever | 1 week (with QA) |
| **Audit `components.css`** (8,220 lines) | Run `purgecss` against all routes | Likely -20-30% file size, possibly -40KB CSS gzipped | 1 week |
| **Phosphor icon tree-shake audit** | Verify `@phosphor-icons/react` imports are specific not barrel | Possible -5-10KB JS | 1 day |
| **Adopt `loading="lazy"` + `fetchpriority` on lead image** | `LeadStory.tsx` | LCP improvement on mobile | 1 day |

**Total achievable on current stack:** ~80-130KB JS reduction, ~40-60KB CSS reduction, smoother UX via View Transitions, cleaner component model via Container Queries, better Lighthouse mobile (projected 95+ post-changes). **All without switching frameworks.**

### Wins ONLY available by switching framework

| Switch target | Unique win |
|---|---|
| Astro | True zero-JS for `/sources`, `/weekly`, `/about`, `/paper` if rewritten as native Astro |
| Svelte | Smallest "real framework" runtime; built-in scoped CSS without `@scope` polyfill concerns |
| Qwik | Resumability — JS only loads on user interaction |
| Solid | Fastest fine-grained reactivity benchmarks |

These wins exist but the **delta over the optimized current stack is 30-80KB at best, not 200KB**. The framework switch math does not pencil.

### Layout & Usability dimensions

| CEO question | Switch? | Without switch |
|---|---|---|
| **Desktop layout improvements** | No framework helps here | Container Queries refactor + audit `layout-zones.css` for tablet/4K gaps |
| **Mobile layout improvements** | No framework helps here | Already shipped Phase 1-4 mobile redesign; next gain is Container Queries + bottom-sheet pattern audit |
| **Usability** | Astro could speed `/sources` | View Transitions for native feel; Speculation Rules for instant nav |
| **Performance** | Preact, Astro, Svelte all win | Preact alias + drop Supabase eager + RSC the page shims = ~70-90KB win |
| **Features** | None enable new features | Current stack supports everything we need |
| **Flexibility** | Lit web components portable; otherwise framework neutral | `@scope` and Container Queries make components more portable in place |

---

## 7. Risks & Costs of Migration (Pricing the Hypothetical)

If we migrated to Svelte (the strongest non-Astro candidate):

| Cost line item | Estimate |
|---|---|
| Component port (55 components, ~15,883 LOC) | 6-8 weeks for solo operator + agents |
| CSS architecture port (40,707 lines, 23 stylesheets, swap to scoped CSS) | 2-3 weeks |
| Animation choreography port (Web Animations API → Svelte motion stores; scroll-driven CSS keeps working) | 1-2 weeks |
| Capacitor re-bundle and re-test on iOS + Android | 1 week |
| Test suite port (Playwright largely framework-agnostic, but selectors and component test IDs need audit) | 3-5 days |
| GitHub Actions deploy pipeline rewrite for SvelteKit static adapter | 2-3 days |
| **35-agent fleet retraining**: 16 agents have React/Next assumptions baked into prompts and skill files | 1-2 weeks of agent prompt rewrites + validation |
| Risk buffer (unforeseen Capacitor incompatibility, Supabase JS Svelte ergonomics, edge cases) | 2 weeks |
| **Total** | **14-19 person-weeks** |

For a solo operator that is **3-5 calendar months of zero new feature work**. The product launch slips by a quarter. Competitors do not.

For Astro, add 4 more weeks because of the dual-framework boundary management for islands. For Vue, similar to Svelte but with weaker animation primitive payoff.

For Preact, the cost is **5 days, including Capacitor regression testing**. That's the only option that survives cost-benefit.

---

## 8. Decision Tree — Operationally When to Re-Evaluate

```
IF Lighthouse mobile < 88 after CF Pages cutover (post-immutable-headers):
  AND homepage JS gzipped > 200KB
  AND Preact alias spike already shipped
  THEN evaluate Astro shell migration for non-feed routes
  ELSE the bottleneck is bytes, not framework — fix bytes first

IF FCP > 1.8s on slow 4G after Preact + Supabase-dejunk:
  THEN evaluate genuine RSC adoption (drop "use client" from leaf components)
  ELSE no framework action

IF Capacitor cold-start on iOS > 2.5s:
  THEN evaluate offline-first JSON snapshot bundled in app shell, not framework switch

IF agent fleet expands to support video / live updates / personalization:
  THEN re-evaluate — those workloads benefit from Svelte's reactive model and SolidJS's fine-grained updates
  ELSE current stack matches workload

IF TWO of these are true:
  - Greenfield rebuild of /history, /sources, /weekly simultaneously
  - Solo operator capacity > 6 person-weeks
  - Lighthouse cap on current stack measurably blocking growth
  THEN evaluate Astro hybrid
  ELSE STAY
```

**Today, none of those triggers fire.** The Lighthouse projection is 88-93 mobile / 95-98 desktop. We have not yet measured post-CF. Wait for real measurement before any framework decision.

---

## 9. 30 / 60 / 90 Day Action Plan (Recommendation: Stay)

### Days 0-30 (Measurement + Easy Wins)

1. **Cloudflare Pages cutover** — provision `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` secrets, verify the parallel deploy at the `*.pages.dev` URL, run real Lighthouse, validate Best Practices score lifts to 90+. **This is the prerequisite to all framework decisions.** Without real numbers, everything else is theater.
2. **Preact alias spike** on `claude/preact-spike` branch. Build, smoke-test all 21 routes, run Capacitor build for iOS + Android, compare bundle. Merge if no regressions; bin if any motion-design or animation glitch.
3. **Drop Supabase eager import** — replace with build-time snapshot fetched at deploy. Saves ~30KB JS.
4. **Phosphor icon import audit** — verify all `@phosphor-icons/react` imports are named, not barrel.
5. **Add Speculation Rules** for `/sources`, `/weekly`, `/about` nav links.

**Expected outcome:** -60 to -80KB JS, +2-4 Lighthouse mobile points, zero framework risk.

### Days 30-60 (CSS Architecture)

6. **Container Queries refactor** for `StoryCard` and `MobileStoryCard` → unify into single `StoryCard` with `@container` rules. Delete `MobileStoryCard.tsx`. Audit `mobile-feed.css` and `desktop-feed.css` for fold-in opportunities.
7. **`@scope` rollout** for `BiasInspector`, `Sigil`, `DeepDive`, `CommandCenter` — gives component isolation without CSS-in-JS overhead.
8. **`components.css` audit** — `purgecss` pass + manual review. Target 30% reduction.
9. **View Transitions API** for theme toggle and edition switch.

**Expected outcome:** -30 to -50KB CSS, simpler component model, smoother native transitions.

### Days 60-90 (Polish + Pre-launch)

10. **WCAG 2.1 AA audit** (already in pipeline charter).
11. **Cross-browser smoke** (already in charter).
12. **Real device testing** on iOS + Android for Capacitor cold start, particularly low-end Android.
13. **First store submission** — Apple Dev membership ($99/yr) + Google Play ($25) per `docs/APP-BUILD-GUIDE.md`.
14. **Document the framework decision** in `docs/STACK-DECISION.md` so future contributors understand the "why we stayed."

**Expected outcome:** Launch-ready, Lighthouse 95+ mobile achievable, no framework risk taken.

---

## 10. Final Recommendation Block

```
RECOMMENDATION: STAY on Next.js 16 + React 19. Switch React → Preact via compat alias (1-week spike).

DO NOT MIGRATE TO:    Vue, Svelte, Solid, Qwik, Lit, Astro (full)
ONE-LINE WHY:         The homepage is interactive, not content. Astro's win
                      doesn't apply. Other frameworks deliver 30-80KB savings
                      at 8-14 person-weeks of cost; the product slips a quarter.

THE ONE THING:        Ship Cloudflare Pages cutover, then Preact alias.
                      Measure. If Lighthouse mobile still < 88 after both,
                      RE-EVALUATE. Do not pre-decide.

KILL LIST:            - Astro full migration evaluation
                      - SvelteKit POC
                      - Vue/Nuxt evaluation
                      - Lit web components rebuild of bias viz primitives
                      - Any framework conversation that begins
                        "what if we rewrote..."

WHAT IS LOAD-BEARING ON THIS DECISION:
  - 35-agent fleet, 16 with React assumptions baked in
  - 40,707 lines of CSS, 1.13MB raw, route-architected for current stack
  - Capacitor iOS + Android shells already initialized for current bundle
  - 21 routes already shipped, 5 dynamic-imported chunks already split
  - Lighthouse projection 88-93 / 95-98 on the current stack pre-CF cutover
  - Solo operator + launch window
```

---

## Files referenced in this analysis

- `frontend/next.config.ts`
- `frontend/capacitor.config.ts`
- `frontend/package.json`
- `frontend/app/layout.tsx`
- `frontend/app/page.tsx`
- `frontend/app/globals.css`
- `frontend/app/components/HomeContent.tsx`
- `frontend/app/components/MobileFeed.tsx`
- `frontend/app/components/MobileStoryCard.tsx`
- `frontend/app/components/StoryCard.tsx`
- `frontend/app/components/DeepDiveSpectrum.tsx`
- `frontend/app/components/EditionIcon.tsx` (only non-`"use client"` component)
- `frontend/app/styles/components.css` (8,220 lines — god-file candidate for purge)
- `frontend/app/styles/history.css` (8,641 lines — already route-scoped)
- `frontend/app/styles/layout-zones.css`
- `frontend/app/styles/desktop-feed.css`
- `frontend/app/styles/mobile-feed.css`
- `frontend/app/styles/responsive.css`
- `docs/PERF-REPORT-2026-04-29.md`
- `docs/DESIGN-SYSTEM.md`
