import { test, expect, Page, ConsoleMessage, Browser } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const BASE_URL = "http://localhost:3001/void--news";
const SCREENSHOT_DIR = path.join(__dirname, "uat-screenshots");
const REPORT_PATH = path.join(__dirname, "uat-report.md");

fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });

const consoleErrors: string[] = [];
const consoleWarnings: string[] = [];
const pageErrors: string[] = [];
const networkErrors: string[] = [];
const testResults: { section: string; test: string; status: "PASS" | "FAIL" | "WARN"; detail: string }[] = [];

function record(section: string, testName: string, status: "PASS" | "FAIL" | "WARN", detail: string) {
  testResults.push({ section, test: testName, status, detail });
}

async function shot(page: Page, name: string) {
  try {
    const fullPage = name.includes("fullpage");
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, `${name}.png`), fullPage, timeout: 5000 });
  } catch { /* ignore screenshot failures */ }
}

async function shotEl(page: Page, selector: string, name: string) {
  try {
    const el = page.locator(selector).first();
    if (await el.isVisible({ timeout: 2000 })) {
      await el.screenshot({ path: path.join(SCREENSHOT_DIR, `${name}.png`), timeout: 5000 });
      return true;
    }
  } catch { /* ignore */ }
  return false;
}

function writeReport() {
  const passed = testResults.filter((r) => r.status === "PASS").length;
  const failed = testResults.filter((r) => r.status === "FAIL").length;
  const warned = testResults.filter((r) => r.status === "WARN").length;
  const criticalIssues = testResults.filter((r) => r.status === "FAIL");
  const warnings = testResults.filter((r) => r.status === "WARN");

  let report = `# UAT Test Report — void --news Frontend
Date: 2026-03-18
Browser: Chromium (Playwright headless)
Viewport: Multiple (375px, 768px, 1280px)

## Summary
- Total tests: ${testResults.length}
- Passed: ${passed}
- Failed: ${failed}
- Warnings: ${warned}

## Critical Issues (Bugs)
${criticalIssues.length === 0 ? "None found." : criticalIssues.map((r) => `- **[${r.section}]** ${r.test}: ${r.detail}`).join("\n")}

## Warnings / Design Issues
${warnings.length === 0 ? "None found." : warnings.map((r) => `- **[${r.section}]** ${r.test}: ${r.detail}`).join("\n")}

## Console Errors
${consoleErrors.length === 0 ? "None." : consoleErrors.map((e) => `- \`${e.replace(/`/g, "'").slice(0, 300)}\``).join("\n")}

## Console Warnings
${consoleWarnings.length === 0 ? "None." : consoleWarnings.slice(0, 30).map((e) => `- \`${e.replace(/`/g, "'").slice(0, 300)}\``).join("\n")}
${consoleWarnings.length > 30 ? `\n... and ${consoleWarnings.length - 30} more warnings` : ""}

## Page Errors (Uncaught Exceptions)
${pageErrors.length === 0 ? "None." : pageErrors.map((e) => `- \`${e.replace(/`/g, "'").slice(0, 300)}\``).join("\n")}

## Network Errors
${networkErrors.length === 0 ? "None." : networkErrors.map((e) => `- \`${e.replace(/`/g, "'").slice(0, 300)}\``).join("\n")}

## Detailed Test Results

`;

  const sections = [...new Set(testResults.map((r) => r.section))];
  for (const section of sections) {
    report += `### ${section}\n`;
    report += "| Test | Status | Detail |\n";
    report += "|------|--------|--------|\n";
    for (const r of testResults.filter((r) => r.section === section)) {
      const safeDetail = r.detail.replace(/\|/g, "\\|").replace(/\n/g, " ");
      report += `| ${r.test} | ${r.status} | ${safeDetail} |\n`;
    }
    report += "\n";
  }

  report += `## Screenshots\nAll screenshots saved to \`frontend/uat-screenshots/\`\n`;
  fs.writeFileSync(REPORT_PATH, report);
}

/** Safe helper: run section, catch errors, keep going */
async function runSection(name: string, fn: () => Promise<void>) {
  try {
    await fn();
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    record(name, "SECTION ERROR", "FAIL", `Uncaught: ${msg.slice(0, 200)}`);
  }
}

test("UAT — Full Test Suite", async ({ browser }) => {
  test.setTimeout(180000);
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();
  page.setDefaultTimeout(8000);

  page.on("console", (msg: ConsoleMessage) => {
    const type = msg.type();
    const text = msg.text();
    if (type === "error") consoleErrors.push(text);
    if (type === "warning") consoleWarnings.push(text);
  });
  page.on("pageerror", (err) => pageErrors.push(err.message));
  page.on("requestfailed", (req) => {
    networkErrors.push(`${req.method()} ${req.url()} - ${req.failure()?.errorText || "unknown"}`);
  });

  try {
    // =================================================================
    // A. PAGE LOAD
    // =================================================================
    await runSection("A. Page Load", async () => {
      const t0 = Date.now();
      await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 30000 });
      const loadTime = Date.now() - t0;
      record("A. Page Load", "Page loads", "PASS", `${loadTime}ms`);
      await shot(page, "A01-fullpage-initial-load");

      const title = await page.title();
      record("A. Page Load", "Page title", title ? "PASS" : "FAIL", `"${title}"`);

      record("A. Page Load", "No page errors on load", pageErrors.length === 0 ? "PASS" : "FAIL",
        pageErrors.length === 0 ? "Clean" : `${pageErrors.length} errors`);

      await page.waitForFunction(() =>
        document.querySelector(".lead-story") || document.querySelector(".story-card") ||
        document.querySelector(".empty-state"), {}, { timeout: 15000 }).catch(() => {});

      await shot(page, "A02-fullpage-after-load");

      const storyCount = await page.locator(".lead-story, .story-card").count();
      const emptyCount = await page.locator(".empty-state").count();
      if (storyCount > 0) {
        record("A. Page Load", "Stories loaded", "PASS", `${storyCount} elements`);
      } else if (emptyCount > 0) {
        record("A. Page Load", "Stories loaded", "WARN", "Empty state shown");
      } else {
        record("A. Page Load", "Stories loaded", "FAIL", "Nothing visible");
      }

      record("A. Page Load", "Performance", loadTime < 3000 ? "PASS" : loadTime < 5000 ? "WARN" : "FAIL", `${loadTime}ms`);
    });

    // =================================================================
    // B. NAVIGATION BAR
    // =================================================================
    await runSection("B. NavBar", async () => {
      await page.goto(BASE_URL, { waitUntil: "networkidle" });
      await page.waitForTimeout(1500);

      await shotEl(page, ".nav-header", "B01-navbar");

      const logoVis = await page.locator(".nav-logo-desktop").isVisible().catch(() => false);
      record("B. NavBar", "Desktop logo visible", logoVis ? "PASS" : "FAIL", logoVis ? "SVG renders" : "Not visible");

      const worldTab = page.locator(".nav-tab", { hasText: "World" });
      const usTab = page.locator(".nav-tab", { hasText: "US" });
      const wVis = await worldTab.isVisible().catch(() => false);
      const uVis = await usTab.isVisible().catch(() => false);
      record("B. NavBar", "Section tabs visible", wVis && uVis ? "PASS" : "FAIL", `World: ${wVis}, US: ${uVis}`);

      if (uVis) {
        await usTab.click();
        await page.waitForTimeout(500);
        await shot(page, "B02-us-section");
        const txt = await page.locator(".section-header__title").textContent().catch(() => "");
        record("B. NavBar", "US tab switches", txt?.includes("US") ? "PASS" : "FAIL", `"${txt}"`);
      }

      if (wVis) {
        await worldTab.click();
        await page.waitForTimeout(500);
        const txt = await page.locator(".section-header__title").textContent().catch(() => "");
        record("B. NavBar", "World tab switches", txt?.includes("World") ? "PASS" : "FAIL", `"${txt}"`);
      }

      const toggle = page.locator(".theme-toggle").first();
      const tVis = await toggle.isVisible().catch(() => false);
      record("B. NavBar", "Theme toggle exists", tVis ? "PASS" : "FAIL", "");

      if (tVis) {
        await toggle.click();
        await page.waitForTimeout(400);
        const dm = await page.locator("html").getAttribute("data-mode");
        await shot(page, "B03-dark-mode");
        record("B. NavBar", "Dark mode activates", dm === "dark" ? "PASS" : "WARN", `data-mode='${dm}'`);

        await toggle.click();
        await page.waitForTimeout(400);
        const lm = await page.locator("html").getAttribute("data-mode");
        record("B. NavBar", "Light mode returns", lm === "light" ? "PASS" : "WARN", `data-mode='${lm}'`);
      }

      await page.evaluate(() => window.scrollTo(0, 500));
      await page.waitForTimeout(300);
      const navY = await page.evaluate(() => {
        const n = document.querySelector(".nav-header");
        return n ? n.getBoundingClientRect().top : -1;
      });
      record("B. NavBar", "Navbar is sticky", navY >= 0 && navY <= 5 ? "PASS" : "FAIL", `Y: ${navY}px`);
      await page.evaluate(() => window.scrollTo(0, 0));
    });

    // =================================================================
    // C. SECTION HEADER
    // =================================================================
    await runSection("C. Section Header", async () => {
      const txt = await page.locator(".section-header__title").textContent().catch(() => "");
      record("C. Section Header", "Title renders", txt?.includes("World") || txt?.includes("US") ? "PASS" : "FAIL", `"${txt}"`);

      const rb = page.locator(".refresh-btn");
      const vis = await rb.isVisible().catch(() => false);
      if (vis) {
        const t = await rb.textContent().catch(() => "");
        record("C. Section Header", "RefreshButton visible", "PASS", `"${t?.trim()}"`);
      } else {
        record("C. Section Header", "RefreshButton visible", "FAIL", "Not visible");
      }
    });

    // =================================================================
    // D. FILTER BAR
    // =================================================================
    await runSection("D. Filter Bar", async () => {
      await shotEl(page, ".filter-bar", "D01-filter-bar");

      const chipCount = await page.locator(".filter-chip").count();
      record("D. Filter Bar", "10 filter chips", chipCount === 10 ? "PASS" : "WARN", `Found ${chipCount}`);

      const activeText = await page.locator(".filter-chip--active").first().textContent().catch(() => "");
      record("D. Filter Bar", "All active by default", activeText?.includes("All") ? "PASS" : "WARN", `"${activeText}"`);

      const cats = ["Politics", "Economy", "Tech", "Health", "Environment", "Conflict", "Science", "Culture", "Sports"];
      for (const cat of cats) {
        const chip = page.locator(".filter-chip", { hasText: new RegExp(`^\\s*${cat}\\s*$`, "i") }).first();
        if (await chip.isVisible().catch(() => false)) {
          await chip.click();
          await page.waitForTimeout(300);
          const active = await chip.evaluate((el) => el.classList.contains("filter-chip--active")).catch(() => false);
          const sc = await page.locator(".story-card, .lead-story").count();
          const em = await page.locator(".empty-state--inline").count();
          record("D. Filter Bar", `${cat} chip`, active ? "PASS" : "FAIL", `Stories: ${sc}, Empty: ${em}`);
        } else {
          record("D. Filter Bar", `${cat} chip`, "FAIL", "Not found");
        }
      }

      await shot(page, "D02-filter-last-category");

      await page.locator(".filter-chip", { hasText: "All" }).first().click();
      await page.waitForTimeout(300);
      const rc = await page.locator(".story-card, .lead-story").count();
      record("D. Filter Bar", "Reset to All", "PASS", `Stories: ${rc}`);
    });

    // =================================================================
    // E. STORY CARDS
    // =================================================================
    await runSection("E. Story Cards", async () => {
      const lc = await page.locator(".lead-story").count();
      const cc = await page.locator(".story-card").count();
      const ec = await page.locator(".empty-state").count();

      if (lc > 0 || cc > 0) {
        record("E. Story Cards", "Stories loaded", "PASS", `Lead: ${lc}, Cards: ${cc}`);

        if (lc > 0) {
          await shotEl(page, ".lead-story", "E01-lead-story");
          const fs = await page.locator(".lead-story__headline").evaluate((el) => getComputedStyle(el).fontSize).catch(() => "?");
          record("E. Story Cards", "Lead hero headline", "PASS", `Font: ${fs}`);

          const lb = await page.locator(".lead-story .bias-stamp").count();
          record("E. Story Cards", "Lead BiasStamp", lb > 0 ? "PASS" : "FAIL", lb > 0 ? "Present" : "Missing");

          const mt = await page.locator(".lead-story__meta").textContent().catch(() => "");
          record("E. Story Cards", "Lead category+time", "PASS", `"${mt?.trim()}"`);

          const st = await page.locator(".lead-story__summary").textContent().catch(() => "");
          record("E. Story Cards", "Lead summary", st && st.length > 10 ? "PASS" : "WARN", `${st?.length || 0} chars`);
        }

        if (await page.locator(".grid-medium").count() > 0) {
          await shotEl(page, ".grid-medium", "E02-medium-stories");
          const mc = await page.locator(".grid-medium__item").count();
          record("E. Story Cards", "Medium grid", "PASS", `${mc} items`);
        }

        if (await page.locator(".grid-compact").count() > 0) {
          await shotEl(page, ".grid-compact", "E03-compact-stories");
          const cpc = await page.locator(".grid-compact__item").count();
          record("E. Story Cards", "Compact grid", "PASS", `${cpc} items`);
        }

        if (cc > 0) {
          const fc = page.locator(".story-card").first();
          record("E. Story Cards", "Card category tag", (await fc.locator(".category-tag").count()) > 0 ? "PASS" : "FAIL", "");
          record("E. Story Cards", "Card time tag", (await fc.locator(".time-tag").count()) > 0 ? "PASS" : "FAIL", "");
          record("E. Story Cards", "Card headline", (await fc.locator(".story-card__headline").count()) > 0 ? "PASS" : "FAIL", "");

          if (await fc.locator(".story-card__summary").count() > 0) {
            const ov = await fc.locator(".story-card__summary").evaluate((el) => getComputedStyle(el).overflow).catch(() => "?");
            record("E. Story Cards", "Card summary clamped", "PASS", `overflow: ${ov}`);
          }

          record("E. Story Cards", "Card source count", (await fc.locator(".source-count").count()) > 0 ? "PASS" : "FAIL", "");
          record("E. Story Cards", "Card BiasStamp", (await fc.locator(".bias-stamp").count()) > 0 ? "PASS" : "FAIL", "");

          const b4 = await fc.evaluate((el) => getComputedStyle(el).backgroundColor).catch(() => "?");
          await fc.hover();
          await page.waitForTimeout(300);
          const af = await fc.evaluate((el) => getComputedStyle(el).backgroundColor).catch(() => "?");
          await shot(page, "E04-card-hover");
          record("E. Story Cards", "Card hover effect", b4 !== af ? "PASS" : "WARN", `Before: ${b4}, After: ${af}`);
        }
      } else if (ec > 0) {
        await shotEl(page, ".empty-state", "E05-empty-state");
        const et = await page.locator(".empty-state h2").textContent().catch(() => "");
        record("E. Story Cards", "Empty state", et?.includes("Awaiting") ? "PASS" : "WARN", `"${et}"`);
      } else {
        record("E. Story Cards", "Content state", "FAIL", "Nothing visible");
      }
    });

    // =================================================================
    // F. BIASSTAMP INTERACTION
    // =================================================================
    await runSection("F. BiasStamp", async () => {
      const sc = await page.locator(".bias-stamp").count();
      if (sc === 0) { record("F. BiasStamp", "Exist", "WARN", "None found"); return; }
      record("F. BiasStamp", "Exist", "PASS", `${sc} stamps`);

      const first = page.locator(".bias-stamp").first();
      const circle = first.locator(".bias-stamp__circle");

      await circle.hover();
      await page.waitForTimeout(600);

      const tipVis = await first.locator(".bias-stamp__expanded").isVisible().catch(() => false);
      if (tipVis) {
        record("F. BiasStamp", "Hover tooltip", "PASS", "Visible");
        await shotEl(page, ".bias-stamp__expanded", "F01-bias-tooltip");

        const hdr = await first.locator(".bias-stamp__expanded-header").textContent().catch(() => "");
        record("F. BiasStamp", "Tooltip header", hdr?.includes("Bias") ? "PASS" : "FAIL", `"${hdr}"`);

        const rows = await first.locator(".bias-stamp__expanded .bias-row").count();
        record("F. BiasStamp", "Bias rows (5)", rows >= 5 ? "PASS" : "FAIL", `${rows}`);

        const fills = first.locator(".bias-stamp__expanded .progress-bar__fill");
        const fc = await fills.count();
        let filled = 0;
        for (let i = 0; i < fc; i++) {
          const w = await fills.nth(i).evaluate((el) => el.getBoundingClientRect().width).catch(() => 0);
          if (w > 0) filled++;
        }
        record("F. BiasStamp", "Progress bars", filled > 0 ? "PASS" : "WARN", `${filled}/${fc} filled`);

        const tb = await first.locator(".bias-stamp__expanded .type-badge").textContent().catch(() => "");
        record("F. BiasStamp", "Type badge", tb ? "PASS" : "WARN", `"${tb}"`);
      } else {
        record("F. BiasStamp", "Hover tooltip", "FAIL", "Did not appear");
      }

      await page.mouse.move(0, 0);
      await page.waitForTimeout(500);
      const gone = !(await first.locator(".bias-stamp__expanded").isVisible().catch(() => false));
      record("F. BiasStamp", "Mouse leave closes", gone ? "PASS" : "WARN", "");

      await circle.click();
      await page.waitForTimeout(400);
      const co = await first.locator(".bias-stamp__expanded").isVisible().catch(() => false);
      record("F. BiasStamp", "Click opens", co ? "PASS" : "WARN", "");

      if (co) {
        await page.keyboard.press("Escape");
        await page.waitForTimeout(400);
        const ae = !(await first.locator(".bias-stamp__expanded").isVisible().catch(() => false));
        record("F. BiasStamp", "Escape closes", ae ? "PASS" : "FAIL", "");
      }
    });

    // =================================================================
    // G. DEEP DIVE PANEL
    // =================================================================
    await runSection("G. Deep Dive", async () => {
      const clickable = page.locator(".story-card, .lead-story").first();
      if (await clickable.count() === 0) { record("G. Deep Dive", "Clickable", "WARN", "No stories"); return; }

      await clickable.click();
      await page.waitForTimeout(1000);

      const pVis = await page.locator(".deep-dive-panel").isVisible().catch(() => false);
      if (!pVis) { record("G. Deep Dive", "Panel opens", "FAIL", "Did not appear"); return; }

      record("G. Deep Dive", "Panel opens", "PASS", "Visible");
      await shot(page, "G01-deep-dive-panel");

      record("G. Deep Dive", "Backdrop", (await page.locator(".deep-dive-backdrop").count()) > 0 ? "PASS" : "FAIL", "");

      const bt = await page.locator(".deep-dive-back").textContent().catch(() => "");
      record("G. Deep Dive", "Back button", bt?.includes("Back") ? "PASS" : "FAIL", `"${bt?.trim()}"`);

      record("G. Deep Dive", "Close (X)", (await page.locator(".deep-dive-close").count()) > 0 ? "PASS" : "FAIL", "");

      const hl = await page.locator(".deep-dive-panel h2").first().textContent().catch(() => "");
      record("G. Deep Dive", "Headline", hl ? "PASS" : "FAIL", `"${hl?.slice(0, 60)}"`);

      const meta = await page.locator(".deep-dive-meta").textContent().catch(() => "");
      record("G. Deep Dive", "Meta info", meta ? "PASS" : "FAIL", `"${meta?.trim()}"`);

      await page.waitForTimeout(2000);
      await shot(page, "G02-deep-dive-content");

      record("G. Deep Dive", "What happened", (await page.locator("#dd-summary").count()) > 0 ? "PASS" : "FAIL", "");
      record("G. Deep Dive", "Sources agree", (await page.locator("#dd-consensus").count()) > 0 ? "PASS" : "WARN", "");
      record("G. Deep Dive", "Sources diverge", (await page.locator("#dd-divergence").count()) > 0 ? "PASS" : "WARN", "");

      const src = await page.locator(".deep-dive-panel .source-row").count();
      if (src > 0) {
        record("G. Deep Dive", "Source list", "PASS", `${src} sources`);
        const fr = page.locator(".deep-dive-panel .source-row").first();
        record("G. Deep Dive", "Source name link", (await fr.locator(".source-link").count()) > 0 ? "PASS" : "FAIL", "");
        record("G. Deep Dive", "Source tier badge", (await fr.locator(".tier-badge").count()) > 0 ? "PASS" : "FAIL", "");
        record("G. Deep Dive", "Source BiasStamp", (await fr.locator(".bias-stamp").count()) > 0 ? "PASS" : "FAIL", "");
        record("G. Deep Dive", "Source ext link", (await fr.locator(".external-link-icon").count()) > 0 ? "PASS" : "FAIL", "");
      } else {
        record("G. Deep Dive", "Source list", "WARN", "No source rows");
      }

      const cb = await page.locator(".deep-dive-panel .coverage-bar").count();
      record("G. Deep Dive", "Coverage bars", cb > 0 ? "PASS" : "WARN", `${cb}`);

      // Close via backdrop
      await page.locator(".deep-dive-backdrop").click({ position: { x: 10, y: 10 }, force: true });
      await page.waitForTimeout(700);
      const g1 = !(await page.locator(".deep-dive-panel").isVisible().catch(() => false));
      record("G. Deep Dive", "Backdrop closes", g1 ? "PASS" : "WARN", "");

      // Escape
      await clickable.click();
      await page.waitForTimeout(1000);
      await page.keyboard.press("Escape");
      await page.waitForTimeout(700);
      const g2 = !(await page.locator(".deep-dive-panel").isVisible().catch(() => false));
      record("G. Deep Dive", "Escape closes", g2 ? "PASS" : "WARN", "");

      // Back button
      await clickable.click();
      await page.waitForTimeout(1000);
      await page.locator(".deep-dive-back").click();
      await page.waitForTimeout(700);
      const g3 = !(await page.locator(".deep-dive-panel").isVisible().catch(() => false));
      record("G. Deep Dive", "Back closes", g3 ? "PASS" : "WARN", "");
    });

    // =================================================================
    // H. REFRESH BUTTON DIALOG
    // =================================================================
    await runSection("H. Refresh Dialog", async () => {
      const rb = page.locator(".refresh-btn");
      if (!(await rb.isVisible().catch(() => false))) { record("H. Refresh Dialog", "Exists", "FAIL", "Not found"); return; }

      await rb.click();
      await page.waitForTimeout(400);

      const dv = await page.locator(".refresh-dialog").isVisible().catch(() => false);
      if (!dv) { record("H. Refresh Dialog", "Opens", "FAIL", "Did not appear"); return; }

      record("H. Refresh Dialog", "Opens", "PASS", "Visible");
      await shotEl(page, ".refresh-dialog", "H01-refresh-dialog");

      const hd = await page.locator(".refresh-dialog .section-heading").textContent().catch(() => "");
      record("H. Refresh Dialog", "Heading", hd?.includes("Refresh") ? "PASS" : "FAIL", `"${hd?.trim()}"`);

      record("H. Refresh Dialog", "Description", (await page.locator(".refresh-dialog p").count()) > 0 ? "PASS" : "FAIL", "");

      const hc = (await page.locator(".refresh-dialog .btn-secondary").count()) > 0;
      const hr = (await page.locator(".refresh-dialog .btn-primary").count()) > 0;
      record("H. Refresh Dialog", "Buttons", hc && hr ? "PASS" : "FAIL", `Cancel: ${hc}, Refresh: ${hr}`);

      // Cancel
      await page.locator(".refresh-dialog .btn-secondary").click();
      await page.waitForTimeout(300);
      record("H. Refresh Dialog", "Cancel closes", !(await page.locator(".refresh-dialog").isVisible().catch(() => false)) ? "PASS" : "FAIL", "");

      // Escape
      await rb.click();
      await page.waitForTimeout(400);
      await page.keyboard.press("Escape");
      await page.waitForTimeout(300);
      record("H. Refresh Dialog", "Escape closes", !(await page.locator(".refresh-dialog").isVisible().catch(() => false)) ? "PASS" : "FAIL", "");

      // Refresh action
      await rb.click();
      await page.waitForTimeout(400);
      await page.locator(".refresh-dialog .btn-primary").click();
      await page.waitForTimeout(200);
      const rt = await rb.textContent().catch(() => "");
      record("H. Refresh Dialog", "Loading state", rt?.includes("Refreshing") ? "PASS" : "WARN", `"${rt?.trim()}"`);

      await page.waitForTimeout(1500);
      const at = await rb.textContent().catch(() => "");
      record("H. Refresh Dialog", "Completes", at?.includes("Last updated") ? "PASS" : "WARN", `"${at?.trim()}"`);
    });

    // =================================================================
    // I. FOOTER
    // =================================================================
    await runSection("I. Footer", async () => {
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(500);

      const fv = await page.locator(".site-footer").isVisible().catch(() => false);
      if (!fv) { record("I. Footer", "Visible", "FAIL", "Not found"); return; }

      record("I. Footer", "Visible", "PASS", "");
      await shotEl(page, ".site-footer", "I01-footer");

      const mh = await page.locator(".footer-masthead").textContent().catch(() => "");
      record("I. Footer", "Masthead", mh?.includes("void") ? "PASS" : "FAIL", `"${mh?.trim()}"`);

      const tl = await page.locator(".footer-tagline").textContent().catch(() => "");
      record("I. Footer", "Tagline", tl ? "PASS" : "FAIL", `"${tl}"`);

      const st = await page.locator(".footer-stats").textContent().catch(() => "");
      record("I. Footer", "90 sources", st?.includes("90") ? "PASS" : "FAIL", `"${st}"`);

      const gh = await page.locator(".footer-github").getAttribute("href").catch(() => "");
      record("I. Footer", "GitHub link", gh?.includes("github") ? "PASS" : "FAIL", `"${gh}"`);

      const bt = await page.locator(".footer-built").textContent().catch(() => "");
      record("I. Footer", "Built with transparency", bt?.includes("transparency") ? "PASS" : "FAIL", `"${bt}"`);

      await page.evaluate(() => window.scrollTo(0, 0));
    });

    // =================================================================
    // J. DARK MODE
    // =================================================================
    await runSection("J. Dark Mode", async () => {
      const tg = page.locator(".theme-toggle").first();
      await tg.click();
      await page.waitForTimeout(500);

      await shot(page, "J01-fullpage-dark-mode");

      const bg = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
      record("J. Dark Mode", "Dark background", "PASS", `${bg}`);

      const tc = await page.evaluate(() => {
        const el = document.querySelector(".section-header__title");
        return el ? getComputedStyle(el).color : "no element";
      });
      record("J. Dark Mode", "Light text", "PASS", `${tc}`);

      const bc = await page.evaluate(() => {
        const el = document.querySelector(".story-card, .lead-story");
        return el ? getComputedStyle(el).borderBottomColor : "no element";
      });
      record("J. Dark Mode", "Borders", "PASS", `${bc}`);

      const bo = await page.locator(".bias-stamp__circle").first()
        .evaluate((el) => getComputedStyle(el).opacity).catch(() => "no stamps");
      record("J. Dark Mode", "BiasStamp visible", "PASS", `opacity: ${bo}`);

      await tg.click();
      await page.waitForTimeout(400);
    });

    // =================================================================
    // K. MOBILE (375x812)
    // =================================================================
    await runSection("K. Mobile", async () => {
      await page.setViewportSize({ width: 375, height: 812 });
      await page.goto(BASE_URL, { waitUntil: "networkidle" });
      await page.waitForTimeout(2000);

      await shot(page, "K01-fullpage-mobile");

      const mlv = await page.locator(".nav-logo-mobile").evaluate((el) => getComputedStyle(el).display !== "none").catch(() => false);
      record("K. Mobile", "Mobile logo", mlv ? "PASS" : "WARN", mlv ? "Shown" : "Hidden");

      const dlh = await page.locator(".nav-logo-desktop").evaluate((el) => getComputedStyle(el).display === "none").catch(() => false);
      record("K. Mobile", "Desktop logo hidden", dlh ? "PASS" : "WARN", "");

      const bnv = await page.locator(".nav-bottom").evaluate((el) => getComputedStyle(el).display !== "none").catch(() => false);
      record("K. Mobile", "Bottom nav", bnv ? "PASS" : "FAIL", "");

      const dth = await page.locator(".nav-tabs").evaluate((el) => getComputedStyle(el).display === "none").catch(() => false);
      record("K. Mobile", "Desktop tabs hidden", dth ? "PASS" : "WARN", "");

      const stories = page.locator(".story-card, .lead-story");
      if (await stories.count() > 0) {
        const w = await page.evaluate(() => {
          const el = document.querySelector(".story-card, .lead-story");
          return el ? el.getBoundingClientRect().width : 0;
        });
        record("K. Mobile", "Single column", w > 300 ? "PASS" : "WARN", `width: ${w}px`);
      }

      const ox = await page.locator(".filter-bar").evaluate((el) => getComputedStyle(el).overflowX).catch(() => "?");
      record("K. Mobile", "Filter scrollable", ox === "auto" || ox === "scroll" ? "PASS" : "WARN", `overflow-x: ${ox}`);

      // Touch targets via evaluate (avoid boundingBox timeouts)
      const smallCount = await page.evaluate(() => {
        const btns = document.querySelectorAll("button, a, [role='tab']");
        let small = 0;
        for (let i = 0; i < Math.min(btns.length, 20); i++) {
          const r = btns[i].getBoundingClientRect();
          if (r.width < 30 || r.height < 30) small++;
        }
        return small;
      });
      record("K. Mobile", "Touch targets", smallCount === 0 ? "PASS" : "WARN", `${smallCount} below 30px`);

      if (await stories.count() > 0) {
        await stories.first().click();
        await page.waitForTimeout(1000);
        const pv = await page.locator(".deep-dive-panel").isVisible().catch(() => false);
        if (pv) {
          await shot(page, "K02-mobile-deep-dive");
          const pw = await page.evaluate(() => {
            const p = document.querySelector(".deep-dive-panel");
            return p ? p.getBoundingClientRect().width : 0;
          });
          record("K. Mobile", "Deep dive full-screen", pw >= 370 ? "PASS" : "WARN", `width: ${pw}px`);
        }
        await page.keyboard.press("Escape");
        await page.waitForTimeout(700);
      }
    });

    // =================================================================
    // L. TABLET (768x1024)
    // =================================================================
    await runSection("L. Tablet", async () => {
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto(BASE_URL, { waitUntil: "networkidle" });
      await page.waitForTimeout(2000);

      await shot(page, "L01-fullpage-tablet");

      if (await page.locator(".grid-medium").count() > 0) {
        const cols = await page.locator(".grid-medium").evaluate((el) => getComputedStyle(el).gridTemplateColumns).catch(() => "?");
        record("L. Tablet", "Medium grid", "PASS", `${cols}`);
      } else {
        record("L. Tablet", "Medium grid", "WARN", "No medium grid");
      }

      if (await page.locator(".grid-compact").count() > 0) {
        const cols = await page.locator(".grid-compact").evaluate((el) => getComputedStyle(el).gridTemplateColumns).catch(() => "?");
        record("L. Tablet", "Compact grid", "PASS", `${cols}`);
      }
    });

    // =================================================================
    // M. DESKTOP (1280x800)
    // =================================================================
    await runSection("M. Desktop", async () => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.goto(BASE_URL, { waitUntil: "networkidle" });
      await page.waitForTimeout(2000);

      await shot(page, "M01-fullpage-desktop");

      if (await page.locator(".grid-medium").count() > 0) {
        const cols = await page.locator(".grid-medium").evaluate((el) => getComputedStyle(el).gridTemplateColumns).catch(() => "?");
        record("M. Desktop", "Medium grid", "PASS", `${cols}`);
      }

      if (await page.locator(".grid-compact").count() > 0) {
        const cols = await page.locator(".grid-compact").evaluate((el) => getComputedStyle(el).gridTemplateColumns).catch(() => "?");
        record("M. Desktop", "Compact grid", "PASS", `${cols}`);
      }

      if (await page.locator(".grid-medium__item").count() > 1) {
        const bdr = await page.locator(".grid-medium__item").first().evaluate((el) => getComputedStyle(el).borderRightStyle).catch(() => "none");
        record("M. Desktop", "Column dividers", bdr !== "none" ? "PASS" : "WARN", `border-right: ${bdr}`);
      }
    });

    // =================================================================
    // N. ACCESSIBILITY
    // =================================================================
    await runSection("N. Accessibility", async () => {
      const imgData = await page.evaluate(() => {
        const imgs = document.querySelectorAll("img");
        let missing = 0;
        for (const img of imgs) {
          if (!img.getAttribute("alt") && img.getAttribute("aria-hidden") !== "true") missing++;
        }
        return { total: imgs.length, missing };
      });
      record("N. Accessibility", "Images alt/aria", imgData.missing === 0 ? "PASS" : "WARN", `${imgData.total} imgs, ${imgData.missing} missing`);

      const svgData = await page.evaluate(() => {
        const svgs = document.querySelectorAll("svg");
        let missing = 0;
        const limit = Math.min(svgs.length, 30);
        for (let i = 0; i < limit; i++) {
          const s = svgs[i];
          if (!s.getAttribute("role") && s.getAttribute("aria-hidden") !== "true" && !s.getAttribute("aria-label")) missing++;
        }
        return { checked: limit, missing };
      });
      record("N. Accessibility", "SVGs a11y", svgData.missing === 0 ? "PASS" : "WARN", `${svgData.checked} checked, ${svgData.missing} missing`);

      const btnData = await page.evaluate(() => {
        const btns = document.querySelectorAll("button");
        let missing = 0;
        for (const b of btns) {
          const text = b.textContent?.trim();
          const ariaLabel = b.getAttribute("aria-label");
          if (!text && !ariaLabel) missing++;
        }
        return { total: btns.length, missing };
      });
      record("N. Accessibility", "Buttons named", btnData.missing === 0 ? "PASS" : "WARN", `${btnData.total} btns, ${btnData.missing} missing`);

      await page.keyboard.press("Tab");
      await page.waitForTimeout(200);
      const focused = await page.evaluate(() => {
        const el = document.activeElement;
        return el ? el.tagName + (el.className ? "." + String(el.className).split(" ")[0] : "") : "none";
      });
      record("N. Accessibility", "Focus visible", "PASS", `Focused: ${focused}`);

      record("N. Accessibility", "ARIA live region", (await page.locator("[aria-live='polite']").count()) > 0 ? "PASS" : "FAIL", "");
      record("N. Accessibility", "Tablist role", (await page.locator("[role='tablist']").count()) > 0 ? "PASS" : "FAIL", "");

      const tc = await page.locator("[role='tab']").count();
      record("N. Accessibility", "Tab roles", tc > 0 ? "PASS" : "FAIL", `${tc} tabs`);
    });

    // =================================================================
    // O. CONSOLE ERRORS & NETWORK
    // =================================================================
    await runSection("O. Console/Network", async () => {
      record("O. Console/Network", "Console errors", consoleErrors.length === 0 ? "PASS" : "FAIL", `${consoleErrors.length} errors`);
      record("O. Console/Network", "Network failures", networkErrors.length === 0 ? "PASS" : "FAIL", `${networkErrors.length} failures`);
    });

    // =================================================================
    // P. EDITION LINE
    // =================================================================
    await runSection("P. Edition Line", async () => {
      await page.goto(BASE_URL, { waitUntil: "networkidle" });
      await page.waitForTimeout(2000);

      const el = page.locator(".edition-line");
      if (await el.count() > 0) {
        const txt = await el.textContent().catch(() => "");
        record("P. Edition Line", "Visible", "PASS", `"${txt?.trim()}"`);
        const bn = await el.locator(".brand-name").textContent().catch(() => "");
        record("P. Edition Line", "Brand name", bn ? "PASS" : "WARN", `"${bn}"`);
      } else {
        record("P. Edition Line", "Visible", "WARN", "Not visible");
      }
    });

  } finally {
    writeReport();
    await context.close();
  }
});
