#!/usr/bin/env node
// Mobile-focused UAT — covers 6 mobile/tablet widths against the static build
// of the current branch (claude/uat-prelaunch-sweep-2026-05-13). Targets the
// fixes shipped in 2d0be89/e68a47f/5d075ba: h1 hierarchy, no duplicate lead,
// MobileBottomNav on /, ≥44px nav tap targets, 21:9 hero banner, summary
// clamp=3 lines, TL;DR=3 sentences, DeepDive lens index, no React #418 on
// /games/undertow, no broken Unsplash, no horizontal overflow.
//
// Run:  node uat-mobile.mjs
// Out:  /tmp/uat-mobile-2026-05-13/{report.json, screenshots, summary.md}

import { firefox } from "playwright";
import fs from "node:fs/promises";
import path from "node:path";

const BASE = process.env.BASE_URL || "http://localhost:8765";
const OUT = "/tmp/uat-mobile-2026-05-13";
await fs.mkdir(OUT, { recursive: true });

const ROUTES = [
  { name: "home",              url: "/" },
  { name: "home-deepdive",     url: "/", action: "open-deep-dive" },
  { name: "history",           url: "/history/" },
  { name: "history-event",     url: "/history/partition-of-india/" },
  { name: "history-threads",   url: "/history/threads/" },
  { name: "weekly",            url: "/weekly/" },
  { name: "paper",             url: "/paper/" },
  { name: "sources",           url: "/sources/" },
  { name: "about",             url: "/about/" },
  { name: "ship",              url: "/ship/" },
  { name: "games",             url: "/games/" },
  { name: "games-wire",        url: "/games/wire/" },
  { name: "games-frame",       url: "/games/frame/" },
  { name: "games-undertow",    url: "/games/undertow/" },
];

// Mobile-first viewport matrix. Tablet portrait included to catch breakpoint
// confusion between mobile (<768) and small-desktop (≥1024).
const VIEWPORTS = [
  { label: "android-s8",   width: 360, height: 800,  isMobile: true },
  { label: "iphone-se",    width: 375, height: 667,  isMobile: true },
  { label: "iphone-13",    width: 390, height: 844,  isMobile: true },
  { label: "iphone-15pm",  width: 430, height: 932,  isMobile: true },
  { label: "ipad-portrait",width: 768, height: 1024, isMobile: true },
];

const iPhoneUA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1";
const AndroidUA = "Mozilla/5.0 (Linux; Android 14; SM-S908B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36";

const browser = await firefox.launch({ headless: true });
const findings = [];

for (const vp of VIEWPORTS) {
  const ctx = await browser.newContext({
    viewport: { width: vp.width, height: vp.height },
    hasTouch: true,
    userAgent: vp.label.startsWith("android") ? AndroidUA : iPhoneUA,
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
      if (/favicon|google\.com\/s2|gstatic|googletagmanager/.test(url)) return;
      failedRequests.push(`${req.method()} ${url} :: ${req.failure()?.errorText || "unknown"}`);
    });

    try {
      await page.goto(BASE + route.url, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForTimeout(600);

      if (route.action === "open-deep-dive") {
        // Tap the first story card / digest item
        const firstStory = page.locator(
          'a[href*="/story/"], button[data-deepdive], [data-storycard], .story-card, .msc, .digest-card'
        ).first();
        if (await firstStory.count()) {
          await firstStory.scrollIntoViewIfNeeded();
          await firstStory.tap({ timeout: 5000 }).catch(() => {});
          await page.waitForTimeout(1200);
        }
      }

      const audit = await page.evaluate(() => {
        const out = { issues: [], stats: {}, pass: {} };
        const docW = document.documentElement.clientWidth;
        const docH = document.documentElement.scrollHeight;
        out.stats.viewport = `${docW}x${window.innerHeight}`;
        out.stats.scrollHeight = docH;

        // ── 1. Horizontal overflow ──────────────────────────────────────
        const scrollW = document.documentElement.scrollWidth;
        if (scrollW > docW + 1) {
          out.issues.push(`horizontal-overflow: scrollWidth=${scrollW} > clientWidth=${docW}`);
          const culprits = [];
          for (const el of document.body.querySelectorAll("*")) {
            const r = el.getBoundingClientRect();
            if (r.width === 0 || r.height === 0) continue;
            if (r.right > docW + 4 && el.tagName !== "HTML") {
              culprits.push({
                tag: el.tagName.toLowerCase(),
                cls: (el.className || "").toString().slice(0, 80),
                right: Math.round(r.right),
                width: Math.round(r.width),
              });
              if (culprits.length >= 5) break;
            }
          }
          out.stats.overflowCulprits = culprits;
        }

        // ── 2. Semantic HTML: h1 + empty heading audit ──────────────────
        const h1s = document.querySelectorAll("h1");
        out.stats.h1Count = h1s.length;
        out.pass.h1Present = h1s.length >= 1;
        if (h1s.length === 0) out.issues.push("h1-missing: no <h1> on page");
        if (h1s.length > 1) out.issues.push(`h1-multiple: ${h1s.length} <h1> elements (expected exactly 1)`);

        const allHeadings = document.querySelectorAll("h1,h2,h3,h4,h5,h6");
        const empties = [...allHeadings].filter((h) => !h.textContent.trim() && h.offsetHeight > 0);
        out.stats.emptyHeadings = empties.length;
        if (empties.length > 0) {
          out.issues.push(`empty-headings: ${empties.length} visible heading(s) with no text`);
          out.stats.emptyHeadingsExamples = empties.slice(0, 3).map((h) => ({
            tag: h.tagName.toLowerCase(),
            cls: (h.className || "").toString().slice(0, 60),
          }));
        }

        // ── 3. Mobile tap-target audit (interactive elements only) ──────
        const interactiveSel = "a, button, [role='button'], [role='link'], input[type='button'], input[type='submit']";
        const interactives = document.querySelectorAll(interactiveSel);
        let smallTaps = 0;
        const smallTapsSamples = [];
        for (const el of interactives) {
          const r = el.getBoundingClientRect();
          if (r.width === 0 || r.height === 0) continue;
          // Visible-only — skip offscreen menus and skip-link a11y patterns
          if (r.bottom < 0 || r.top > window.innerHeight) continue;
          if (r.left < -100 || r.right > window.innerWidth + 100) continue;
          if (el.className && /\bskip-to-content\b|\bsr-only\b|\bvisually-hidden\b/.test(String(el.className))) continue;
          if (r.width < 44 || r.height < 44) {
            smallTaps++;
            if (smallTapsSamples.length < 5) {
              smallTapsSamples.push({
                tag: el.tagName.toLowerCase(),
                cls: (el.className || "").toString().slice(0, 50),
                role: el.getAttribute("role") || "",
                text: (el.textContent || "").trim().slice(0, 30),
                w: Math.round(r.width),
                h: Math.round(r.height),
              });
            }
          }
        }
        out.stats.tapTargets = { total: interactives.length, small: smallTaps };
        out.pass.tapTargets = smallTaps === 0;
        if (smallTaps > 0) {
          out.issues.push(`tap-targets-small: ${smallTaps}/${interactives.length} interactive elements <44px`);
          out.stats.smallTapsSamples = smallTapsSamples;
        }

        // ── 4. MobileBottomNav presence on / (mobile widths only — iPad shows desktop nav by design) ───
        const mbn = document.querySelector(".mob-nav, .mbn, [data-mobile-bottom-nav], .mobile-bottom-nav, nav[class*='bottom']");
        out.stats.hasMobileBottomNav = !!mbn;
        const isMobileWidth = window.innerWidth <= 767;
        if ((window.location.pathname === "/" || window.location.pathname === "") && isMobileWidth) {
          out.pass.bottomNavOnHome = !!mbn;
          if (!mbn) out.issues.push("mobile-bottom-nav-missing on /");
        }

        // ── 5. Duplicate lead-story detection ───────────────────────────
        const leads = document.querySelectorAll("article.lead-story, .lead-split, [data-lead-story], .lead");
        // Only count those that render the same headline
        const leadHeadlines = new Map();
        for (const lead of leads) {
          const h = lead.querySelector("h1, h2, .lead-headline, .lead-story__headline");
          if (!h) continue;
          const txt = h.textContent.trim().slice(0, 80);
          leadHeadlines.set(txt, (leadHeadlines.get(txt) || 0) + 1);
        }
        const dupes = [...leadHeadlines.values()].filter((v) => v > 1).length;
        out.stats.leadCount = leads.length;
        out.stats.uniqueLeadHeadlines = leadHeadlines.size;
        out.pass.leadStoryUnique = dupes === 0;
        if (dupes > 0) {
          out.issues.push(`duplicate-lead-story: ${dupes} headline(s) appear in multiple lead containers`);
        }

        // ── 6. Hero image — banner above headline, NOT side column ─────
        if (window.location.pathname === "/" || window.location.pathname === "") {
          const leadImage = document.querySelector(
            ".lead-split__image-frame img, .lead-story__image img, .mobile-feed img, [data-slot='image'] img, .msc--hero img"
          );
          if (leadImage) {
            const ir = leadImage.getBoundingClientRect();
            const ratio = ir.width > 0 ? ir.height / ir.width : 0;
            out.stats.heroImageAspectRatio = ratio.toFixed(3);
            out.stats.heroImageBox = `${Math.round(ir.width)}x${Math.round(ir.height)}`;
            // Banner should be wide-ish (height/width < 0.8); portrait crop is > 1.0
            out.pass.heroIsBanner = ratio < 0.85;
            if (ratio >= 0.85) {
              out.issues.push(`hero-image-not-banner: aspect=${ratio.toFixed(2)} (expected <0.85 = wide banner)`);
            }
            // Hero should be ABOVE the headline (top of image < top of any h1)
            const h1 = document.querySelector("h1");
            if (h1) {
              const hr = h1.getBoundingClientRect();
              out.pass.heroAboveHeadline = ir.top < hr.top + 2;
              if (ir.top >= hr.top + 2) {
                out.issues.push(`hero-not-above-h1: image.top=${Math.round(ir.top)} >= h1.top=${Math.round(hr.top)}`);
              }
            }
          } else {
            out.stats.heroImageFound = false;
          }
        }

        // ── 7. Summary line-clamp — should be 3 on mobile ───────────────
        const summaryEls = document.querySelectorAll(
          ".story-card__summary, .msc__summary, .lead-summary, .lead-story__summary, .mbp__preview--tldr"
        );
        const clampStats = [];
        for (const el of summaryEls) {
          const cs = getComputedStyle(el);
          const clamp = cs.webkitLineClamp || cs.getPropertyValue("-webkit-line-clamp") || "none";
          clampStats.push({ cls: (el.className || "").toString().slice(0, 40), clamp });
        }
        // Aggregate
        const clampMap = {};
        for (const c of clampStats) {
          const k = `${c.cls} :: ${c.clamp}`;
          clampMap[k] = (clampMap[k] || 0) + 1;
        }
        out.stats.summaryClamps = clampMap;

        // ── 8. DeepDive lens index (when modal open) ────────────────────
        const ddOpen = document.querySelector(".dd, .deep-dive, [data-deepdive-open]");
        if (ddOpen) {
          const lensIndex = document.querySelector(".dd-lens-index, [data-lens-index], nav.dd-lens-index");
          out.stats.deepDiveOpen = true;
          out.pass.lensIndexPresent = !!lensIndex;
          if (!lensIndex) out.issues.push("dd-lens-index-missing: DeepDive open but no .dd-lens-index nav");
          else {
            const links = lensIndex.querySelectorAll("a, button");
            out.stats.lensIndexLinks = links.length;
            if (links.length < 4) out.issues.push(`dd-lens-index-sparse: only ${links.length} links (expected 6 lenses)`);
          }
        }

        // ── 9. Broken images ────────────────────────────────────────────
        let brokenImgs = 0;
        const brokenSrcs = [];
        for (const img of document.querySelectorAll("img")) {
          if (img.complete && img.naturalWidth === 0 && img.src) {
            brokenImgs++;
            if (brokenSrcs.length < 3) brokenSrcs.push(img.src.slice(0, 100));
          }
        }
        if (brokenImgs > 0) {
          out.issues.push(`broken-images: ${brokenImgs}`);
          out.stats.brokenSrcs = brokenSrcs;
        }
        out.pass.noBrokenImages = brokenImgs === 0;

        // ── 10. Safe-area-inset usage (iOS notch / home indicator) ──────
        const fixedEls = [...document.querySelectorAll("*")].filter((el) => {
          const cs = getComputedStyle(el);
          return cs.position === "fixed" && el.getBoundingClientRect().height > 0;
        });
        out.stats.fixedElements = fixedEls.length;

        return out;
      });

      const shotPath = path.join(OUT, `${vp.label}-${route.name}.png`);
      await page.screenshot({ path: shotPath, fullPage: false });

      findings.push({
        viewport: vp.label,
        viewportSize: `${vp.width}x${vp.height}`,
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
        viewportSize: `${vp.width}x${vp.height}`,
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

await fs.writeFile(path.join(OUT, "report.json"), JSON.stringify(findings, null, 2));

// Compact console summary
console.log(`\n=== MOBILE UAT REPORT ${OUT}/report.json ===\n`);
let totalIssues = 0;
let totalFatals = 0;
for (const f of findings) {
  const tag = `[${f.viewport.padEnd(14)}] ${f.route.padEnd(18)}`;
  if (f.fatal) {
    totalFatals++;
    console.log(`✗ ${tag} FATAL: ${f.fatal.slice(0, 100)}`);
    continue;
  }
  const issues = f.audit?.issues || [];
  totalIssues += issues.length;
  const pErrs = f.pageErrors || [];
  const cErrs = (f.consoleErrors || []).filter((m) => m.type === "error");
  const flag = (issues.length || pErrs.length || cErrs.length) ? "⚠" : "✓";
  console.log(`${flag} ${tag} issues=${issues.length} page-err=${pErrs.length} console-err=${cErrs.length}`);
  for (const i of issues) console.log(`   • ${i}`);
  for (const e of pErrs.slice(0, 2)) console.log(`   ! page-error: ${e.slice(0, 160)}`);
  for (const e of cErrs.slice(0, 2)) console.log(`   ! console-error: ${e.text.slice(0, 160)}`);
}
console.log(`\n=== TOTAL ${findings.length} runs · ${totalIssues} layout/a11y issues · ${totalFatals} fatals ===`);
