# void --news Deployment Runbook

**Last updated**: 2026-08-01 (rev 4 — Cloudflare-Pages-only reality; GitHub Pages removed; staging/preview split + branch protection documented)
**Status**: Single production surface, live at https://void-news.pages.dev (Cloudflare Pages, root basePath). PWA installable. Capacitor iOS/Android shells initialized, awaiting signing. GitHub Pages retired (the old `deploy.yml` no longer exists).

---

## Current State

```
push claude/* branch
   │
   ▼
Auto-merge Claude branches  (.github/workflows/auto-merge-claude.yml)
   │  gate: build-check + validate-bias + validate-clustering
   │  → merge --no-ff into main → push main
   │  → apply pending Supabase migrations
   ▼
merge to main triggers (workflow_run)
   │
   ▼
Deploy to Cloudflare Pages  (.github/workflows/deploy-cloudflare.yml)
   → next build (static export → frontend/out)
   → wrangler pages deploy → https://void-news.pages.dev

Pipeline cron 11:00 UTC writes Supabase; the static site polls the same DB at runtime.
```

| Surface | Workflow | Status | Notes |
|---|---|---|---|
| Cloudflare Pages | `.github/workflows/deploy-cloudflare.yml` | **live (production)** | CF Pages project `void-news`, production branch `main`. Root basePath (`NEXT_PUBLIC_BASE_PATH=""`). Honors `frontend/public/_headers` + `_redirects` at the edge |
| GitHub Pages | (removed) | **retired** | `deploy.yml` deleted. No `aacrit.github.io/void--news/` surface. `_redirects` still 301s any stray `/void--news/*` deep link to the root path |

There is exactly one production URL: **https://void-news.pages.dev**.

---

## Deploy Flow (branch → prod)

The whole chain is triggered by pushing a `claude/*` branch. No one pushes to `main` by hand (branch protection is being added — see below).

1. **Push a `claude/*` branch.** `auto-merge-claude.yml` fires on `push` to `claude/**`.
2. **Gate.** Three jobs must pass before the merge job runs (`needs: [build-check, validate-bias, validate-clustering]`):
   - `build-check` — `npm ci` + `next build` in `frontend/` (retries the build up to 3x for flaky installs; a real build failure fails the gate).
   - `validate-bias` — `pipeline/validation/runner.py`; fails on any CATASTROPHIC or WRONG bias score.
   - `validate-clustering` — `pipeline.validation.clustering.runner`; fails on CATASTROPHIC (pre-existing WRONG cases warn only).
   These checks are duplicated inside auto-merge because the merge job can only `needs:` jobs in the same workflow (branch protection on `main` did not exist historically — that is changing).
3. **Merge.** The `auto-merge` job merges `origin/<branch>` into `main` with `--no-ff` and pushes `main`.
4. **Migrate.** The `migrate` job (`needs: auto-merge`) applies any new `supabase/migrations/*.sql` to the production Supabase DB. Idempotent: the `_migrations` table tracks applied files by name; "already exists" errors are recorded as applied. Runs here (not only in `migrate.yml`) because the merge push uses `GITHUB_TOKEN`, which does not trigger other workflows.
5. **Deploy.** The merge commit on `main` fires `deploy-cloudflare.yml` via `workflow_run` (it also runs on direct `push` to `main` and on `workflow_dispatch`). It builds the static export and deploys it to Cloudflare Pages.

> Migrations auto-apply to the single production DB on every merge. Treat every migration as production-affecting. There is no separate database for staging (see Dev / Prod-Preview Split).

---

## `deploy-cloudflare.yml` — what it actually does

Steps, in order:

1. `actions/checkout@v4` with `ref: main`.
2. `actions/setup-node@v4`, Node 20, npm cache keyed on `frontend/package-lock.json`.
3. `cd frontend && npm ci`.
4. **Build** (`cd frontend && npm run build`) with the env contract below.
5. **Ensure Cloudflare Pages project exists** — `wrangler pages project create void-news --production-branch main`, `continue-on-error: true` (wrangler 3.x in non-TTY mode will not auto-create the project; this swallows the idempotent "already exists" error after the first run).
6. **Deploy** — `wrangler pages deploy frontend/out --project-name=void-news --branch=main --commit-dirty=true`.

`concurrency: cloudflare-pages` with `cancel-in-progress: false` serializes deploys so two merges cannot race a deploy.

---

## Env-Var Contract

### Build-time (GitHub Actions → `next build`)

Set in `deploy-cloudflare.yml` under the Build step. `NEXT_PUBLIC_*` values are inlined into the browser bundle at build time (a plain env var would only reach the Node build process, not the client).

| Var | Value (production) | Purpose |
|---|---|---|
| `NEXT_PUBLIC_BASE_PATH` | `""` (empty string) | Root deploy. Read by `frontend/next.config.ts` and `frontend/app/lib/utils.ts`, which default to `/void--news` when unset — so the empty string is required for the pages.dev root serve |
| `NEXT_PUBLIC_SUPABASE_URL` | `${{ secrets.SUPABASE_URL }}` | Supabase project URL for client reads |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `${{ secrets.SUPABASE_ANON_KEY }}` | Anon key — anon read only; RLS enforces write policy. Never ship the service-role key to the client bundle |
| `NEXT_PUBLIC_DISABLE_AUDIO` | `"0"` | void --onair enabled. Mirrors `pipeline.yml` `DISABLE_AUDIO=0`. Flip both back to `"1"` together to re-park audio (`frontend/app/lib/audioGate.ts` default is also `0`) |

GitHub secrets consumed by the deploy workflow:

| Secret | Used by |
|---|---|
| `SUPABASE_URL`, `SUPABASE_ANON_KEY` | Build step (inlined into the client bundle) |
| `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID` | wrangler project-create + deploy steps |

The `migrate` job in `auto-merge-claude.yml` additionally uses `SUPABASE_DB_PASSWORD` and `SUPABASE_PROJECT_REF`.

### Runtime (Cloudflare Pages Function bindings)

The IG webhook Pages Function (`frontend/functions/api/ig/webhook.ts`, served at `/api/ig/webhook`) runs on Cloudflare's edge and reads bindings configured in **Cloudflare Pages → Settings → Environment variables** (NOT baked into the static build, and NOT `NEXT_PUBLIC_`):

| Binding | Purpose |
|---|---|
| `META_APP_SECRET` | Verifies the `X-Hub-Signature-256` header on incoming Meta webhook POSTs |
| `META_WEBHOOK_VERIFY_TOKEN` | Arbitrary string chosen by the operator; echoed back during Meta webhook subscription (`GET ...hub.verify_token=`) |
| `SUPABASE_URL` | Supabase REST base for the function's inserts |
| `SUPABASE_SERVICE_ROLE_KEY` | Service-role key for writing `ig_comments` / `ig_mentions` / `ig_dms`. Server-side only — lives in the CF binding, never in the client bundle |

Set these in the CF dashboard under both the **Production** and **Preview** environment scopes if the webhook is exercised on staging.

---

## `frontend/public/_headers` (Cloudflare edge)

Cloudflare Pages reads this file at deploy time and applies rules per request. Cloudflare ACCUMULATES headers from every matching rule, so the file is written to avoid overlapping `Cache-Control` directives:

- **Global `/*`** sets security headers only: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy`, and the full `Content-Security-Policy` (including `frame-ancestors 'none'`, which CSP3 ignores from a `<meta>` tag so it must be an HTTP header, and `connect-src`/`media-src` allowing `https://*.supabase.co` + `wss://*.supabase.co` for Realtime).
- **Hashed assets** (`/_next/static/*`, `/*.woff2`): `Cache-Control: public, max-age=31536000, immutable`.
- **HTML routes** (`/`, `/paper`, `/weekly`, `/sources`, `/about`, the engineering `.html` pages): short `max-age` + `stale-while-revalidate` so a 1x/day pipeline update is visible quickly while repeat visits hit the browser cache instead of re-fetching Supabase on every mount.

## `frontend/public/_redirects` (Cloudflare edge)

301s applied at the edge before any HTML is served:

- Old multi-edition URLs (`/world`, `/us`, `/europe`, `/south-asia` and their subpaths) → `/` (single-feed collapse, 2026-06-02).
- `/void--news/*` → `/:splat` (any stray legacy GitHub-Pages project-path deep link resolves to the equivalent root path). Placed last; first match wins, so the edition rules take precedence.

---

## Dev / Prod-Preview Split (staging)

The database stays single (one Supabase project). The split is **frontend-preview only**: a staging UI URL that lets a change be seen before it reaches the public site.

- A long-lived **`staging` branch** exists. Cloudflare Pages builds a **preview deployment** automatically for any non-production branch, so `staging` deploys to a stable preview URL (a `staging.void-news.pages.dev`-style host) without a second CF project.
- **Preview env-var scope.** CF Pages gives Preview deployments their own environment-variable set, separate from Production. Set the preview `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` / `NEXT_PUBLIC_BASE_PATH=""` / `NEXT_PUBLIC_DISABLE_AUDIO` in the CF dashboard Preview scope. Note the CF limitation: **all preview branches share one Preview env set** (distinct from Production).
- **Shared DB caveat.** Preview points at the same Supabase as Production (locked decision — no separate DB). Because migrations auto-apply to that one DB on merge to `main`, a preview build already sees post-migration schema. Keep a nightly Supabase backup before opening the tap to real users.
- **Branch protection on `main`** is being added: require the `build-check` / `validate-bias` / `validate-clustering` checks so the gates that currently live only inside `auto-merge-claude.yml` also guard any direct push. This is a manual step in GitHub → Settings → Branches. Until it lands, a direct push to `main` deploys instantly with no gate.

Production remains: `claude/*` → gated auto-merge → `main` → Cloudflare Production deploy at `void-news.pages.dev`.

---

## Rollback

Production is a static export on Cloudflare Pages, so rollback is a redeploy of a known-good build. Options, fastest first:

1. **Roll back to a previous deployment (CF dashboard).** Cloudflare Pages → project `void-news` → Deployments → pick the last-good deployment → **Rollback to this deployment**. This re-points production at that build's assets immediately, no rebuild.
2. **Redeploy `main` via CI.** `gh workflow run deploy-cloudflare.yml` (or push an empty commit / merge a revert to `main`) rebuilds from the current `main` and deploys.
3. **Revert the offending change.** Land a revert on `main` through the normal `claude/*` → auto-merge flow; the merge triggers a fresh deploy.

Migrations are forward-only and idempotent: a frontend rollback does NOT roll back schema. If a bad migration is the problem, write a corrective migration (do not delete an applied one — `_migrations` tracks it as applied).

---

## Pipeline Cron (Reference)

The data pipeline runs **1x/day at 11:00 UTC** (`pipeline.yml`) and writes Supabase. The site reads Supabase JSON at runtime, so a fresh feed appears without a redeploy; the `_headers` HTML cache (short `max-age` + `stale-while-revalidate`) means visitors see the new feed within minutes. The daily brief can refresh separately via `refresh-brief.yml`; the weekly digest runs Sunday via `weekly-digest.yml`.

---

## First-Time Cloudflare Setup (reference)

Already configured for the live project; documented for a rebuild or a new account.

1. Cloudflare → My Profile → API Tokens → **Create Token** (Pages edit permission), scoped to the target account.
2. From the dashboard URL, copy the Account ID (`https://dash.cloudflare.com/<ACCOUNT_ID>`).
3. In GitHub → repo → Settings → Secrets and variables → Actions, add `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` (plus `SUPABASE_URL` / `SUPABASE_ANON_KEY` for the build).
4. In Cloudflare Pages → project `void-news` → Settings → Environment variables, add the IG webhook runtime bindings (`META_APP_SECRET`, `META_WEBHOOK_VERIFY_TOKEN`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`) under Production (and Preview if used).
5. Trigger a deploy: merge a `claude/*` branch, or `gh workflow run deploy-cloudflare.yml`. The workflow creates the Pages project on first run (idempotent) and deploys.

Reference: https://developers.cloudflare.com/pages/

---

## PWA Distribution (Active)

void --news ships as an installable Progressive Web App. No separate build step — every static export emits the PWA assets alongside the HTML.

| Asset | Path | Purpose |
|---|---|---|
| Manifest | `frontend/public/manifest.json` | `display: standalone`, single "Today's feed" shortcut (single-feed collapse), `launch_handler.client_mode: focus-existing` |
| Service worker | `frontend/public/sw.js` | Core / assets / API cache buckets. Network-first for HTML + Supabase API; cache-first for hashed assets |
| Offline page | `frontend/public/offline.html` | Self-contained dark-mode fallback served when network + cache both miss |
| Icons / splash | `frontend/public/icon-*.{png,svg}`, `apple-touch-icon.*`, `splash-*.png` | Manifest + iOS home-screen icons + launch images |

**Install flow:**
- iOS Safari → Share → Add to Home Screen → standalone (no browser chrome).
- Android Chrome → menu → Install app → standalone PWA in the app drawer.
- Desktop Chrome/Edge → omnibox install icon → windowed app.

**basePath note:** the production deploy uses the root basePath (`NEXT_PUBLIC_BASE_PATH=""`), so the manifest, service-worker scope, and `start_url` resolve at `/` on `void-news.pages.dev` — consistent with the CF root serve. (The old `/void--news/` GitHub-Pages scoping is gone.)

**Cache invalidation:** bump the `CACHE_NAME` constants in `frontend/public/sw.js` before any breaking change to cached asset shape. Existing clients pick up the new SW on next visit.

---

## Capacitor Native Apps (Initialized, Awaiting Signing)

iOS and Android shells live in the repo and wrap the same `frontend/out` static export. Not yet signed or submitted.

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
| iOS | Apple Developer | $99 / year | Create App ID; configure Team + Bundle Identifier in Xcode → Signing & Capabilities. CEO is on Windows, so the iOS archive must run on a cloud Mac (Codemagic recommended) or a physical Mac |
| Android | Google Play Console | $25 one-time | Generate keystore (keep an offline backup; required for every future update); create the app listing |

**Direct APK distribution (Android, optional):**

```bash
npx cap build android --release
# → frontend/android/app/build/outputs/apk/release/app-release.apk
```

Users sideload after enabling "Install from unknown sources." Useful for a beta cohort before Play Store review.

**Full step-by-step (provisioning, store metadata, iOS-on-Windows via Codemagic, troubleshooting, version management) lives in `docs/APP-BUILD-GUIDE.md`.** This runbook covers only the deployment-pipeline shape.

**Sync cadence:** native apps are not on the daily cron. They load live Supabase data, so new content appears automatically, but new UI/JS requires a `npx cap sync` + store re-submission.
