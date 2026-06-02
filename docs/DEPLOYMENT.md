# void --news Deployment Runbook

**Last updated**: 2026-05-03 (rev 3 — added PWA + Capacitor sections)
**Status**: Dual deploy in flight — GH Pages live, Cloudflare Pages scaffolded. PWA installable now via service worker + manifest. Capacitor iOS/Android shells initialized; awaiting signing.

---

## Current State

```
                   ┌─→  GitHub Pages    →  https://aacrit.github.io/void--news/   (LIVE)
push to main  ──┬──┤
                │  └─→  Cloudflare Pages →  https://*.pages.dev                   (PENDING SECRETS)
                │
                └──→   Pipeline cron 11:00 UTC writes Supabase; both surfaces poll the same DB
```

| Surface | Workflow | Status | Notes |
|---|---|---|---|
| GH Pages | `.github/workflows/deploy.yml` | **active** | basePath `/void--news`. `Cache-Control: max-age=600` global cap (Lighthouse Best-Practices ceiling) |
| CF Pages | `.github/workflows/deploy-cloudflare.yml` | **scaffolded** | Awaits `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` GitHub secrets. basePath empty (root deploy). Honors `frontend/public/_headers` |

Both deploys run on the same triggers: push to `main` + `workflow_run` from auto-merge + `workflow_dispatch`. They are independent — failure of one does not block the other.

---

## basePath Env Contract

`frontend/next.config.ts` and `frontend/app/lib/utils.ts` both read:

```ts
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "/void--news";
```

| Deploy | `NEXT_PUBLIC_BASE_PATH` | basePath at runtime |
|---|---|---|
| GH Pages | unset | `/void--news` (default — keeps existing URL working) |
| CF Pages | `""` (empty string) | root |

The `NEXT_PUBLIC_` prefix is required — Next.js inlines the value into the browser bundle at build time. A regular env var would only be available to the Node build process and would not affect client-side route resolution.

---

## `frontend/public/_headers` (Cloudflare-only)

Cloudflare Pages reads this file at deploy time and applies the rules to every request. GitHub Pages ignores the file entirely — no risk of conflict during the parallel-deploy window.

Highlights:
- `/_next/static/*`, `/*.css`, `/*.js`, `/*.woff2`, hashed images: `Cache-Control: public, max-age=31536000, immutable`
- HTML pages: `Cache-Control: public, max-age=600, must-revalidate` — post-pipeline-run feeds land within ~10 min of deploy
- Security: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, restrictive `Permissions-Policy`

This is the lever that lifts the Lighthouse Best-Practices ceiling that GH Pages globally caps at `max-age=600`.

---

## Adding Cloudflare Secrets (One-Time Setup)

1. Sign in to Cloudflare → My Profile → API Tokens → **Create Token** with template "Edit Cloudflare Workers". Restrict to the target account.
2. Copy the token value — you only see it once.
3. From the Cloudflare dashboard URL, copy the Account ID (`https://dash.cloudflare.com/<ACCOUNT_ID>`).
4. In GitHub: repo → Settings → Secrets and variables → Actions → **New repository secret**:
   - `CLOUDFLARE_API_TOKEN` = the token from step 2
   - `CLOUDFLARE_ACCOUNT_ID` = the account ID from step 3
5. Trigger a deploy: push any commit to `main` or run `gh workflow run deploy-cloudflare.yml`.
6. The first run prints the live `*.pages.dev` URL in the workflow summary.

Reference: https://developers.cloudflare.com/pages/configuration/git-integration/github-integration/

---

## Cutover Plan (GH Pages → CF Pages)

Stay parallel for at least one full pipeline cycle to confirm CF deploy + cache + feed freshness behave correctly.

1. **Verify** `*.pages.dev` URL: feed renders, edition tabs route, Deep Dive opens, audio plays, Lighthouse mobile ≥ 90.
2. **(Optional) Custom domain** — point a CNAME at the `*.pages.dev` host via the Cloudflare dashboard.
3. **Disable GH Pages workflow** — comment out the `on:` triggers in `.github/workflows/deploy.yml`, keep the file for rollback. Do not delete the gh-pages branch yet.
4. **Update CLAUDE.md** + `docs/PROJECT-CHARTER.md` to point at the CF URL.
5. **Hold rollback for 7 days** — re-enabling the GH workflow gets the old URL back instantly if needed.

---

## Rollback

If CF Pages is misbehaving and GH Pages is still active (current state):
- Just route users back to `https://aacrit.github.io/void--news/`. No action needed — both deploys are running.

If GH Pages is disabled and we need to roll back:
- Uncomment the `on:` triggers in `deploy.yml` and `git push` — next push to `main` redeploys to gh-pages.
- The old URL `https://aacrit.github.io/void--news/` resumes serving within ~5 min of the workflow completing.

---

## Pipeline Cron (Reference)

Pipeline runs **1x/day at 11:00 UTC** (`pipeline.yml`). The `_headers` HTML rule (`max-age=600 must-revalidate`) means CF Pages visitors see fresh feeds within ~10 min of the workflow finishing. GH Pages enforces `max-age=600` globally, so the same freshness applies there.

Daily Brief refresh runs separately via `refresh-brief.yml`.

---

## PWA Distribution (Active)

void --news ships as an installable Progressive Web App. No separate build step — every static export emits the PWA assets alongside the regular HTML.

| Asset | Path | Purpose |
|---|---|---|
| Manifest | `frontend/public/manifest.json` | `display: standalone`, `start_url`/`scope` honor `/void--news/` basePath, 4 edition shortcuts (World/US/EU/SA), `share_target` POST handler, `launch_handler.client_mode: focus-existing` |
| Service worker | `frontend/public/sw.js` | Caches `void-news-v1` (core), `void-news-assets-v1` (JS/CSS/fonts/images), `void-news-api-v1` (Supabase). Network-first for HTML + API; cache-first for hashed assets |
| Offline page | `frontend/public/offline.html` | Self-contained dark-mode HTML fallback (no external CSS) served when network + cache both miss |
| Splash screens | `frontend/public/splash-*.png` | iOS launch images at 7 viewport sizes (375x667 → 430x932) |
| Icons | `frontend/public/icon-{192,512}.{png,svg}`, `apple-touch-icon.{png,svg}` | Manifest + iOS home-screen icons |

**Install flow:**
- iOS Safari → Share → Add to Home Screen → launches in standalone (no browser chrome)
- Android Chrome → menu → Install app → standalone PWA, appears in app drawer
- Desktop Chrome/Edge → omnibox install icon → opens as windowed app

**Cache strategy (network-first for fresh content):**
1. HTML and `/api/*` requests: try network, fall back to cache, fall back to `offline.html`
2. Hashed `_next/static/*`, fonts, WebP images: cache-first with `immutable` semantics
3. New service worker activates on next page load; old caches purged on `activate`

**Cache invalidation:** bump `CACHE_NAME` constants in `frontend/public/sw.js` (currently `void-news-v1`) before any breaking change to cached asset shape. Existing clients pull the new SW within 24h or on next visit, whichever is sooner.

PWA is fully compatible with both GH Pages and CF Pages deploys. The basePath `/void--news/` is baked into the manifest because that is the live GH Pages path; CF Pages root deploys serve the manifest unchanged but the install will scope to `/void--news/` (planned: emit a basePath-aware manifest at build time once CF cutover is committed).

---

## Capacitor Native Apps (Initialized, Awaiting Signing)

iOS and Android shells live in the repo and wrap the same `frontend/out` static export served by the web. They are not yet signed or submitted.

| Path | Purpose |
|---|---|
| `frontend/capacitor.config.ts` | `appId: 'void.news'`, `appName: 'void--news'`, `webDir: 'out'` |
| `frontend/ios/` | Xcode project, ready for Signing & Capabilities + archive |
| `frontend/android/` | Gradle project, ready for keystore + AAB build |

**Build loop after web changes:**

```bash
cd frontend
npm run build          # static export → frontend/out
npx cap sync           # copies out/ into ios/ and android/
npx cap open ios       # → Xcode: Archive → App Store Connect
npx cap open android   # → Android Studio: Generate Signed Bundle (AAB) or APK
```

**One-time setup before first store submission:**

| Platform | Account | Cost | Action |
|---|---|---|---|
| iOS | Apple Developer | $99 / year | Create App ID in Apple Developer portal; configure Team + Bundle Identifier in Xcode → Signing & Capabilities |
| Android | Google Play Console | $25 one-time | Generate keystore (keep offline backup; required for every future update); create app listing |

**Direct APK distribution (Android, optional):**

```bash
npx cap build android --release
# → frontend/android/app/build/outputs/apk/release/app-release.apk
```

Users sideload after enabling "Install from unknown sources." Useful for beta cohorts before Play Store review.

**Full step-by-step (provisioning, store metadata, troubleshooting, version management, CI/CD example) lives in `docs/APP-BUILD-GUIDE.md`.** This runbook only covers the deployment-pipeline shape; the App Build Guide covers the manual signing flow.

**Sync cadence:** native apps are not on the daily pipeline cron — they re-sync on demand only. The web tier (GH Pages + CF Pages) updates 1x/day; native shells pick up new content automatically because they load the live Supabase data, but new UI/JS requires a `npx cap sync` + store re-submission.
