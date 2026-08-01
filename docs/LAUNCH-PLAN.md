# Plan: Take void --news live (experimental launch → 3-month friends-first rollout)

## Context

void --news is feature-complete and already deployed to a single live surface (`https://void-news.pages.dev`, Cloudflare Pages, root basePath). The daily pipeline, 7-phase clustering, 6-axis bias engine, daily/weekly briefs, and seven live products (news, history, revolt, weekly, sources, ship, about) all work. What's missing is not features — it's the **launch scaffolding**: a way to open it to real people safely, a public "this is experimental" posture, a distribution story (web + app stores), and a single place to drive the whole go-live sequence.

Goal: soft-launch to people the CEO knows, clearly tagged **experimental**, and over ~3 months grow to a wider set of real users. This mirrors Ground News's own path (rough beta → most-active users → feedback → public launch) and the 2025 indie consensus (warm list first, niche boards next, Product Hunt/Show HN last — the PH spike fades fast).

**Locked decisions (CEO, this session):**
1. **Merge history + revolt** into one tabbed `/archive` section (two voices, one roof).
2. **Ship to both app stores** (Apple + Google), signed and submitted — native, not PWA-only.
3. **Dev/prod = frontend preview only** — keep the single Supabase DB; add a Cloudflare preview branch for a staging UI URL.
4. **Stay on `void-news.pages.dev`** (no custom domain yet).
5. **void --ship becomes a simple feedback page** (no build tracking).
6. A visible **"experimental" tag** across the product.

**Hard constraint:** CEO is on Windows 11. iOS build/sign/submit requires macOS + Xcode → must run on a cloud Mac (Codemagic recommended) or a physical Mac. Android is fine on Windows.

**Deliverable the CEO asked for:** a fresh, simple, interactive HTML tracker (`docs/LAUNCH-TRACKER.html`) that is the one-stop shop to take this live — cloning the proven pattern of the existing `docs/IG-LAUNCH-CHECKLIST.html` (brand-styled checkboxes + progress bar + persisted state), kept up to date by Claude as CLI work completes.

---

## Workstream A — Product consolidation (code)

All changes follow the Press & Precision design system and the "no em dash / show-don't-tell" editorial rules.

### A1. Merge History + Revolt into `/archive` (tabbed)
- New route `frontend/app/archive/page.tsx` renders a shared shell with a tab switcher: **History** | **Revolt**. Each tab mounts the *existing* landing component (`HistoryLanding`, `RevoltLanding`) — no rewrite of their internals or data layers.
- Keep all existing deep routes resolving (`/history/[slug]`, `/history/era/*`, `/history/region/*`, `/history/threads`, `/revolt/[slug]`, `/revolt/active`, `/revolt/compare`, `/revolt/outcome/*`, `/revolt/phase/*`). This is an entry-point + navigation merge, not a data re-architecture, which caps the risk.
- Add `_redirects` entries: `/history → /archive` and `/revolt → /archive?tab=revolt` (301), so old links and the current nav still land correctly. Tab state via `?tab=` query param.
- Nav change: replace the two separate links (History, Revolt) with a single **Archive** link in `NavBar.tsx`, `Footer.tsx`, `MobileSidePanel.tsx`, `MobileTabBar.tsx`.
- Files: new `frontend/app/archive/page.tsx` + a small `ArchiveTabs.tsx` client component; edit the 4 nav components; `frontend/public/_redirects`.

### A2. void --ship → simple feedback page
- Replace the full Kanban/voting/build-tracker `ShipBoard.tsx` with a minimal **FeedbackForm** (title + message + category select + honeypot). Reuse the *existing* plumbing in `frontend/app/lib/supabase.ts` — `submitShipRequest`, `generateFingerprint`, the localStorage rate limit — so it writes to the same `ship_requests` table with zero new migration; just stop rendering the board, votes, replies, `PulseGraph`, `void --log`, and all `claude_branch`/`shipped_commit`/`shipped_diff_summary`/ship-clock fields.
- Show a "thanks, we read every note" confirmation state. Rename the product surface to **Feedback** (nav label + page title). Keep the route as `/ship` (or add `/feedback` and redirect) — decide during build; `/feedback` reads cleaner.
- The CEO still sees submissions in Supabase directly (or via `/command-center`), so no build-status UI is needed.
- Files: new `frontend/app/components/FeedbackForm.tsx`; edit `frontend/app/ship/page.tsx` (or new `frontend/app/feedback/page.tsx` + redirect); nav labels.

### A3. "Experimental" tag (visible, brand-consistent)
- New `ExperimentalBadge.tsx` component (small pill, using existing tokens: `--accent-warm`/`--fg-accent` aged brass on the newsprint bg, mono type). No badge component exists today, so this is net-new but tiny.
- Placements: in the masthead beside the `LogoFull` wordmark (desktop `NavBar.tsx` + mobile), and a one-line dismissible banner on first visit ("void --news is experimental. Things will change. Tell us what breaks →" linking to Feedback). Persist dismissal in localStorage.
- Wire the same "experimental" wording into `layout.tsx` metadata/OG description and `manifest.json` (`name`/`description`) so shared links and the installed app read as experimental too.
- Files: new `ExperimentalBadge.tsx` + a small `ExperimentalBanner.tsx`; edit `NavBar.tsx`, mobile nav, `layout.tsx`, `manifest.json`.

### A4. Pre-launch nav/product hygiene
- Confirm parked products stay hidden from nav but still resolve: `/paper`, `/games` (already hidden), `/onair` (gated by `AUDIO_ENABLED`). Leave as-is.
- Decide audio: `void --onair` is currently enabled (`NEXT_PUBLIC_DISABLE_AUDIO=0`). Keep on for launch (it's a differentiator) unless a QA pass finds it unstable — verify on the pre-launch run.

---

## Workstream B — Dev/prod (frontend preview only)

Per decision #3: keep one Supabase DB; add a **staging frontend surface** so UI changes can be seen before they hit the public site.

- Create a long-lived `staging` branch. In Cloudflare Pages, preview deployments are automatic for non-production branches → `staging` deploys to a stable preview URL (`staging.void-news.pages.dev`-style). No new CF project needed.
- Note the known CF limitation: **all preview branches share one set of preview env vars** (separate from Production's). Set the preview env (Supabase URL/anon key, `NEXT_PUBLIC_BASE_PATH=""`, `NEXT_PUBLIC_DISABLE_AUDIO`) in the CF dashboard Preview scope, pointing at the *same* Supabase (per decision) — or at a read-only view later if desired.
- Because the DB is shared, add two cheap safety nets before opening to the public:
  - **Nightly Supabase backup** (Supabase dashboard scheduled backup / or a `pg_dump` step in a GitHub Action). The DB is ~410 MB (82% of free cap per CLAUDE.md) — confirm backup fits and prune via the existing retention RPC if needed.
  - **Pre-migration checklist** item in the tracker (migrations still auto-apply post-merge to the single prod DB via `auto-merge-claude.yml`; treat every migration as production-affecting).
- Fix `main` safety: today there's **no branch protection** and direct pushes to `main` deploy instantly. Add GitHub branch protection requiring the existing `build-check` / `validate-bias` / `validate-clustering` checks, so the gates that currently live *inside* auto-merge also guard any direct push. (Manual step — CEO does this in GitHub settings; tracker item.)
- Files/actions: new `staging` branch; CF dashboard preview env config (manual); optional `.github/workflows/backup-db.yml`; GitHub branch-protection settings (manual).

---

## Workstream C — Social launch (friends-first → 3 months)

Reuse the existing `docs/IG-LAUNCH-CHECKLIST.html` (the @void.news Instagram automation is already built) and layer the phased rollout on top.

- **Phase 0 (now → launch): private hardening.** Everything experimental-tagged, feedback page live, staging in place. No sharing yet.
- **Phase 1 (Weeks 1-2): friends & family.** Share `void-news.pages.dev` directly to a small warm list (text/DM/email), explicitly "experimental, tell me what's broken." Point them at the Feedback page. This is exactly Ground News's step one. Collect qualitative feedback; watch which product (feed vs archive vs bias view) makes people say "oh, that's useful."
- **Phase 2 (Weeks 3-6): warm-network broadcast.** Personal social posts (the CEO's own IG/X/LinkedIn), the @void.news IG account going active on its automated cadence, and any relevant group chats/communities. Still "experimental."
- **Phase 3 (Weeks 7-12): niche indie boards.** BetaList / Uneed / Fazier / SaaSHub, then Show HN and (last) Product Hunt once the product has survived real users. Have testimonials + a crisp one-liner ready by now.
- Prepare launch assets: a one-line pitch, 3-4 screenshots/GIF (the bias sigil + Deep Dive is the hook), and a short "why void" note that leans on the existing brand voice ("See through the void").
- Success metric for the experiment: sustained returning users (not raw signups — there are no accounts), plus a steady feedback stream.

---

## Workstream D — App stores (both, signed & submitted)

### D0. Accounts & the Windows/iOS constraint (manual, do first)
- **Apple Developer Program** — $99/yr. Requires an Apple ID; enrollment can take 24-48h.
- **Google Play Developer** — $25 one-time.
- **iOS build environment:** CEO is on Windows → cannot run Xcode locally. Recommended path: **Codemagic** (native Capacitor support, cloud macOS, can auto-sign via App Store Connect API key and publish to TestFlight/App Store). Alternative: GitHub Actions `macos-latest` + fastlane, or a rented/physical Mac. This is a real decision item surfaced in the tracker; Codemagic is the lowest-friction for a Windows solo dev.

### D1. Android (buildable on Windows)
- Install Android Studio + JDK 17. `cd frontend && npm run build && npx cap sync android`.
- **Generate a signing keystore and back it up offline** (losing it means never being able to update the app). Configure `android/app/build.gradle` `versionCode`/`versionName` and signing config.
- Build a signed AAB → upload to Play Console. Review ~2-4h. (Optional: a direct signed APK for sideloading to beta testers immediately, bypassing review, is a fast path for the friends phase.)

### D2. iOS (via Codemagic/cloud Mac)
- `npx cap sync ios`. Set Bundle ID (`com.void.news` or similar — note `capacitor.config.ts` uses `appId: 'void.news'`; confirm a reverse-DNS ID Apple accepts), Team, Signing & Capabilities.
- Archive → distribute to **TestFlight** first (perfect for the friends phase — no public store listing needed, invite by email), then submit to App Store review (~24-48h).
- **Risk: App Store Guideline 4.2 (minimum functionality).** A Capacitor wrapper of a website can be rejected as "just a web view." Mitigations: ensure it feels native (splash, offline fallback via existing `offline.html`/`sw.js`, share target, home-screen icon), and lean on real app value (the daily brief, audio, offline reading). Have a rebuttal ready. TestFlight distribution is unaffected by this even if App Store review is slow.

### D3. Store listing assets (both)
- App icon exists (`icon-512.png`); generate the full icon set + screenshots per device size (iPhone 6.7"/6.5", iPad, Android phone/tablet). The bias-sigil feed + Deep Dive make the strongest screenshots.
- Copy: name (`void --news` — confirm store rules allow the `--`; may need `void news` as the store display name with `--news` in subtitle), subtitle, description (experimental framing), keywords, **News** category, age rating.
- **Privacy disclosures** (Apple nutrition label + Google Data Safety): no accounts, no personalization. Disclose what *is* collected — the Feedback form's free text and the fingerprint used for rate-limiting; Supabase anon reads. Point both at the existing `/privacy` page. This is simple because there's no tracking/PII by design.

---

## Workstream E — Launch readiness (quality + docs)

- **Lighthouse 90+** verified on the deployed site (charter has this unchecked). Run against prod; fix regressions (perf-optimizer agent).
- **WCAG 2.1 AA** pass (charter unchecked). Prior work did a tap-target/contrast sweep; do a focused audit (uat-tester) and fix gaps.
- **Cross-browser + mobile-gesture** smoke test (Safari iOS especially, since PWA + Capacitor wrap it).
- **Security pre-launch:** RLS is already hardened (migration 062). Do a final void-ciso pass now that the surface is public: confirm the feedback form can't be abused (honeypot + rate limit present), anon keys are anon-only, service-role key never ships to client, CSP still correct in `_headers`.
- **Docs refresh (stale):** `docs/DEPLOYMENT.md` still says GH Pages is live and CF is "pending secrets" — rewrite to reflect CF-Pages-only reality. Update `docs/PROJECT-CHARTER.md` §11 and `docs/APP-BUILD-GUIDE.md` as the store submissions progress.

---

## Workstream F — The interactive launch tracker (the CEO's one-stop shop)

Build `docs/LAUNCH-TRACKER.html` — a fresh, self-contained, brand-styled page cloning the proven mechanics of `docs/IG-LAUNCH-CHECKLIST.html`:
- Self-contained HTML/CSS/JS, Press & Precision palette, **interactive checkboxes with localStorage-persisted state**, a **progress bar**, and an "all done" banner.
- Every item tagged **[AUTO]** (Claude does it via CLI) or **[MANUAL]** (CEO must do it — buy accounts, sign, click GitHub settings, share posts, submit to stores). Manual items include a short "how" line.
- Sections mirror the workstreams: **A Product consolidation · B Dev/prod · C Social launch · D App stores · E Readiness · F Go-live**. Each checklist item has a stable `id` so Claude can programmatically check items off (edit the HTML `checked`/`data-done` attribute) as CLI work lands — the CEO reopens the file and sees updated progress.
- A top summary strip: overall % complete, count of manual blockers remaining, and the current launch phase (0-3).
- Lives in `docs/` (internal, not shipped to the public build). CEO opens it locally in a browser.
- This is the artifact that stays live across the whole journey; treat it as the source of truth for "what's left."

---

## Sequencing (recommended order)

1. **Build F (the tracker)** first — so the CEO has the dashboard from day one, and everything below checks off inside it.
2. **A (product consolidation)** — archive merge, feedback page, experimental tag, nav hygiene. One `claude/*` branch, auto-merges, deploys.
3. **B (dev/prod)** — staging branch + CF preview env + branch protection + DB backup. (Manual bits flagged in tracker.)
4. **E (readiness)** — Lighthouse, WCAG, security, docs. Gate before any sharing.
5. **C Phase 1 (friends)** — share the URL. Runs in parallel with D.
6. **D (app stores)** — accounts → Android (fast, Windows-native, TestFlight-equivalent via APK/internal testing) → iOS via Codemagic → TestFlight → store review. Longest lead time; start accounts early.
7. **C Phases 2-3** — broaden over the 3 months as feedback confirms the product.

---

## Verification

- **A:** `cd frontend && npm run build` clean; `/archive` renders both tabs; `/history` and `/revolt` redirect correctly; deep sub-routes still resolve; feedback form writes a row to `ship_requests` in Supabase; experimental badge/banner visible on desktop + mobile; dismissal persists. Verify live on the CF deploy after auto-merge.
- **B:** push to `staging` → a preview URL builds and serves; a test migration/PR is previewable before `main`; branch protection blocks an unchecked direct push; a backup file is produced.
- **D:** Android internal-testing track receives the AAB; iOS build succeeds on Codemagic and lands in TestFlight; a test device installs both.
- **E:** Lighthouse ≥90 on prod; axe/uat WCAG pass with no criticals; void-ciso no criticals.
- **F:** open `docs/LAUNCH-TRACKER.html` in a browser — checkboxes toggle, progress bar moves, state persists across reload; Claude can edit an item to `checked` and the CEO sees it.

---

## Open items / decisions to surface in the tracker (not blockers to start)

- **iOS build host:** Codemagic vs physical Mac vs GitHub macOS runner. (Recommend Codemagic.)
- **Store display name:** whether Apple/Google accept `void --news` literally, or need `void news` + subtitle.
- **App Store 4.2 rejection risk** — have the "real app value" rebuttal ready; TestFlight covers the friends phase regardless.
- **DB headroom:** at ~82% of the free Supabase cap; confirm backups fit and prune before opening the tap wider. A paid Supabase tier may become necessary as users grow (revisit in month 2-3).
- **Custom domain:** deferred by decision, but needed before a serious public/app-store push — park as a month-2 item.
