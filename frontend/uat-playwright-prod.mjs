#!/usr/bin/env node
// UAT smoke test — capture console errors, screenshots, and CSS/layout signals
// across every key route. Compares mobile (375px) and desktop (1440px) viewports.

import { firefox } from "playwright";
const chromium = firefox; // Use Firefox (libs bundled) — chromium needs libnspr4 not installed in WSL
import fs from "node:fs/promises";
import path from "node:path";

const BASE = process.env.BASE_URL || "https://void-news.pages.dev";
const OUT = "/tmp/uat-prod-2026-05-13";
await fs.mkdir(OUT, { recursive: true });

const ROUTES = [
  { name: "home",            url: "/" },
  { name: "deepdive-open",   url: "/", action: "open-deep-dive" },
  { name: "history",         url: "/history" },
  { name: "history-event",   url: "/history/partition-of-india" },
  { name: "history-threads", url: "/history/threads" },
  { name: "weekly",          url: "/weekly" },
  { name: "paper",           url: "/paper" },
  { name: "sources",         url: "/sources" },
  { name: "about",           url: "/about" },
  { name: "ship",            url: "/ship" },
  { name: "command-center",  url: "/command-center" },
  { name: "games",           url: "/games" },
  { name: "games-wire",      url: "/games/wire" },
  { name: "games-frame",     url: "/games/frame" },
  { name: "games-undertow",  url: "/games/undertow" },
];

const VIEWPORTS = [
  { label: "desktop", width: 1440, height: 900, isMobile: false },
  { label: "mobile",  width: 390,  height: 844, isMobile: true  },
];

const browser = await chromium.launch({ headless: true });
const findings = [];

for (const vp of VIEWPORTS) {
  // Firefox does not support isMobile/deviceScaleFactor in newContext; omit when using firefox.
  const ctx = await browser.newContext({
    viewport: { width: vp.width, height: vp.height },
    hasTouch: vp.isMobile,
    userAgent: vp.isMobile
      ? "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
      : undefined,
  });

  for (const route of ROUTES) {
    const page = await ctx.newPage();
    const consoleErrors = [];
    const pageErrors = [];
    const failedRequests = [];

    page.on("console", (m) => {
      if (m.type() === "error" || m.type() === "warning") {
        consoleErrors.push({ type: m.type(), text: m.text() });
      }
    });
    page.on("pageerror", (e) => pageErrors.push(String(e.message || e)));
    page.on("requestfailed", (req) => {
      const url = req.url();
      // Ignore favicon/analytics noise
      if (/favicon|google\.com\/s2|gstatic|googletagmanager/.test(url)) return;
      failedRequests.push(`${req.method()} ${url} :: ${req.failure()?.errorText || "unknown"}`);
    });

    try {
      await page.goto(BASE + route.url, { waitUntil: "networkidle", timeout: 60000 });
      await page.waitForTimeout(800);

      // Drive an action if specified
      if (route.action === "open-deep-dive") {
        // First story card on the homepage
        const firstStory = await page.locator(
          'a[href*="/story/"], button[data-deepdive], .story-card a, [data-storycard], a[data-story-link]'
        ).first();
        if (await firstStory.count()) {
          await firstStory.scrollIntoViewIfNeeded();
          await firstStory.click({ timeout: 5000 }).catch(() => {});
          await page.waitForTimeout(1500);
        }
      }

      // ── CSS/layout signal collection ─────────────────────────────────
      const audit = await page.evaluate(() => {
        const out = { issues: [], stats: {} };
        const docW = document.documentElement.clientWidth;
        const docH = document.documentElement.scrollHeight;
        out.stats.viewport = `${docW}x${window.innerHeight}`;
        out.stats.scrollHeight = docH;

        // 1) Horizontal overflow detection
        if (document.documentElement.scrollWidth > docW + 1) {
          out.issues.push(
            `horizontal-overflow: scrollWidth=${document.documentElement.scrollWidth} > clientWidth=${docW}`
          );
        }

        // 2) Element-level x-overflow culprits
        const overflowCulprits = [];
        for (const el of document.body.querySelectorAll("*")) {
          const r = el.getBoundingClientRect();
          if (r.width === 0 || r.height === 0) continue;
          if (r.right > docW + 4 && el.tagName !== "HTML") {
            overflowCulprits.push({
              tag: el.tagName.toLowerCase(),
              cls: (el.className || "").toString().slice(0, 80),
              right: Math.round(r.right),
              width: Math.round(r.width),
            });
            if (overflowCulprits.length >= 5) break;
          }
        }
        if (overflowCulprits.length) out.stats.overflowCulprits = overflowCulprits;

        // 3) Unstyled-text heuristic — any element where text-transform is set in CSS
        //    we can't easily detect missing rules. Instead, look for known-class
        //    elements whose computed font-family is the platform default (a sign that
        //    component CSS didn't load).
        const sentinels = [
          { sel: ".dd-sv__axis-label", expectTransform: "uppercase" },
          { sel: ".dd-sv-view__svg",   expectDisplay: "block" },
          { sel: ".weekly-cover",      expectDisplay: "block" },
          { sel: ".history-hero",      expectDisplay: "block" },
        ];
        for (const s of sentinels) {
          const el = document.querySelector(s.sel);
          if (!el) continue;
          const cs = getComputedStyle(el);
          if (s.expectTransform && cs.textTransform !== s.expectTransform) {
            out.issues.push(
              `css-not-applied: ${s.sel} text-transform=${cs.textTransform} (expected ${s.expectTransform})`
            );
          }
          if (s.expectDisplay && cs.display === "inline") {
            out.issues.push(
              `css-not-applied: ${s.sel} display=inline (expected ${s.expectDisplay})`
            );
          }
        }

        // 4) Layout-zones smoke — feed should have a grid / flex parent
        const lead = document.querySelector(".lead-story-split, [data-lead-story]");
        if (lead) {
          const cs = getComputedStyle(lead);
          if (cs.display === "block" || cs.display === "inline") {
            out.issues.push(`lead-story-split: display=${cs.display} (expected grid/flex)`);
          }
        }

        // 5) Detect text overlapping (very basic — sibling text rects collision)
        //    Skip for now — too noisy without dedicated logic.

        // 6) Check for clipped headlines (line-clamp leaving 0 height)
        const clamps = document.querySelectorAll("[class*='clamp'], h1, h2, h3");
        let zeroHeightHeadings = 0;
        for (const el of clamps) {
          const r = el.getBoundingClientRect();
          if (r.height === 0 && el.textContent && el.textContent.trim().length > 0) {
            zeroHeightHeadings++;
          }
        }
        if (zeroHeightHeadings > 0) {
          out.issues.push(`zero-height-headings: ${zeroHeightHeadings} elements`);
        }

        // 7) Image broken / missing src
        let brokenImgs = 0;
        for (const img of document.querySelectorAll("img")) {
          if (img.complete && img.naturalWidth === 0 && img.src) brokenImgs++;
        }
        if (brokenImgs > 0) out.issues.push(`broken-images: ${brokenImgs}`);

        // 8) Body color contrast — looking for "white on white" or "black on black"
        //    is too heuristic; skip.

        // 9) Specific Deep Dive sentinels (only meaningful when DD open)
        const ddOpen = document.querySelector(".dd, .deep-dive, [data-deepdive-open]");
        out.stats.deepDiveOpen = !!ddOpen;
        if (ddOpen) {
          const axis = document.querySelector(".dd-sv__axis-labels");
          if (axis) {
            const labels = axis.querySelectorAll(".dd-sv__axis-label");
            const cs = axis ? getComputedStyle(axis) : null;
            out.stats.ddAxisDisplay = cs?.display;
            out.stats.ddAxisJustify = cs?.justifyContent;
            out.stats.ddAxisLabelCount = labels.length;
            if (cs?.display !== "flex" || cs?.justifyContent !== "space-between") {
              out.issues.push(
                `dd-axis-css: display=${cs?.display} justify=${cs?.justifyContent}`
              );
            }
          } else {
            out.stats.ddAxisFound = false;
          }
        }
        return out;
      });

      // Take a screenshot
      const shotPath = path.join(OUT, `${vp.label}-${route.name}.png`);
      await page.screenshot({ path: shotPath, fullPage: false });

      findings.push({
        viewport: vp.label,
        route: route.name,
        url: route.url,
        screenshot: shotPath,
        consoleErrors: consoleErrors.slice(0, 10),
        pageErrors: pageErrors.slice(0, 10),
        failedRequests: failedRequests.slice(0, 10),
        audit,
      });
    } catch (e) {
      findings.push({
        viewport: vp.label,
        route: route.name,
        url: route.url,
        fatal: String(e.message || e),
      });
    }
    await page.close();
  }
  await ctx.close();
}

await browser.close();

await fs.writeFile(
  path.join(OUT, "report.json"),
  JSON.stringify(findings, null, 2),
);

// Compact console summary
console.log(`\n=== UAT REPORT ${OUT}/report.json ===\n`);
for (const f of findings) {
  const tag = `[${f.viewport.padEnd(7)}] ${f.route.padEnd(20)}`;
  if (f.fatal) {
    console.log(`${tag} FATAL: ${f.fatal}`);
    continue;
  }
  const issues = f.audit?.issues || [];
  const pErrs = f.pageErrors || [];
  const fReqs = f.failedRequests || [];
  const cErrs = (f.consoleErrors || []).filter((m) => m.type === "error");
  const flag = (issues.length || pErrs.length || fReqs.length || cErrs.length) ? "⚠ " : "✓ ";
  console.log(`${flag}${tag} issues=${issues.length} page-err=${pErrs.length} req-fail=${fReqs.length} console-err=${cErrs.length}`);
  if (issues.length) for (const i of issues) console.log(`   • ${i}`);
  if (pErrs.length) for (const e of pErrs.slice(0, 3)) console.log(`   ! page-error: ${e.slice(0, 200)}`);
  if (cErrs.length) for (const e of cErrs.slice(0, 3)) console.log(`   ! console-error: ${e.text.slice(0, 200)}`);
  if (fReqs.length) for (const r of fReqs.slice(0, 3)) console.log(`   ! ${r.slice(0, 200)}`);
}
