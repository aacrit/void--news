import { test, expect, Page, ConsoleMessage } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

const BASE_URL = "http://localhost:3001/void--news";
const SCREENSHOT_DIR = path.join(__dirname, "uat-screenshots", "round2");
const REPORT_PATH = path.join(__dirname, "uat-report-round2.md");

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

  let report = `# UAT Test Report Round 2 — void --news Frontend (Mock Data)

Date: 2026-03-18
Browser: Chromium (Playwright headless)
Viewport: Multiple (375px, 768px, 1280px)
Data: Mock data injected via Playwright route interception

## Summary
- Total tests: ${testResults.length}
- Passed: ${passed}
- Failed: ${failed}
- Warnings: ${warned}

## Purpose
Round 1 UAT found the Supabase database had no data, so story cards, BiasStamp tooltips, Deep Dive panel, grid layouts, category filtering, and edition line could not be tested. This round injects mock data via Playwright \`page.route()\` to test all those features.

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

  report += `## Screenshots\nAll screenshots saved to \`frontend/uat-screenshots/round2/\`\n`;
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

// ============================================================================
// MOCK DATA
// ============================================================================

const mockClustersWorld = [
  {
    id: "cluster-001",
    title: "EU-China Trade Agreement Reshapes Global Commerce",
    summary: "The European Union and China finalized a sweeping trade agreement covering semiconductors, green technology, and agricultural exports, marking a significant shift in global trade dynamics that could reshape supply chains worldwide.",
    category: "economy",
    section: "world",
    importance_score: 85,
    source_count: 5,
    first_published: "2026-03-18T06:30:00Z",
    last_updated: "2026-03-18T07:45:00Z",
    divergence_score: 0.35,
    headline_rank: 95,
    coverage_velocity: 8,
    bias_diversity: {
      avg_political_lean: 48,
      avg_sensationalism: 15,
      avg_opinion_fact: 12,
      avg_factual_rigor: 88,
      avg_framing: 22,
      lean_spread: 18,
      framing_spread: 12,
      lean_range: 30,
      sensationalism_spread: 8,
      opinion_spread: 15,
      aggregate_confidence: 0.85,
      analyzed_count: 5,
    },
  },
  {
    id: "cluster-002",
    title: "UN Climate Summit Reaches Historic Emissions Agreement",
    summary: "World leaders at the UN Climate Change Conference agreed to binding emission targets that would reduce global carbon output by 40% by 2035, with enforcement mechanisms unprecedented in international environmental law.",
    category: "environment",
    section: "world",
    importance_score: 80,
    source_count: 7,
    first_published: "2026-03-18T05:00:00Z",
    last_updated: "2026-03-18T07:00:00Z",
    divergence_score: 0.42,
    headline_rank: 88,
    coverage_velocity: 12,
    bias_diversity: {
      avg_political_lean: 38,
      avg_sensationalism: 25,
      avg_opinion_fact: 20,
      avg_factual_rigor: 82,
      avg_framing: 35,
      lean_spread: 25,
      framing_spread: 20,
      lean_range: 45,
      sensationalism_spread: 15,
      opinion_spread: 18,
      aggregate_confidence: 0.78,
      analyzed_count: 7,
    },
  },
  {
    id: "cluster-003",
    title: "Japan Unveils Next-Generation Quantum Computing Chip",
    summary: "Japanese researchers at RIKEN announced a breakthrough quantum processor capable of 1,000 logical qubits, potentially accelerating drug discovery and cryptography applications by several years.",
    category: "tech",
    section: "world",
    importance_score: 72,
    source_count: 4,
    first_published: "2026-03-18T04:15:00Z",
    last_updated: "2026-03-18T06:30:00Z",
    divergence_score: 0.18,
    headline_rank: 78,
    coverage_velocity: 6,
    bias_diversity: {
      avg_political_lean: 50,
      avg_sensationalism: 32,
      avg_opinion_fact: 15,
      avg_factual_rigor: 90,
      avg_framing: 18,
      lean_spread: 8,
      framing_spread: 10,
      lean_range: 15,
      sensationalism_spread: 12,
      opinion_spread: 10,
      aggregate_confidence: 0.92,
      analyzed_count: 4,
    },
  },
  {
    id: "cluster-004",
    title: "WHO Declares New Avian Flu Strain Global Health Emergency",
    summary: "The World Health Organization elevated the H7N9 variant to a global public health emergency after confirmed human-to-human transmission in three Southeast Asian countries.",
    category: "health",
    section: "world",
    importance_score: 90,
    source_count: 8,
    first_published: "2026-03-18T03:00:00Z",
    last_updated: "2026-03-18T07:30:00Z",
    divergence_score: 0.28,
    headline_rank: 75,
    coverage_velocity: 15,
    bias_diversity: {
      avg_political_lean: 45,
      avg_sensationalism: 42,
      avg_opinion_fact: 18,
      avg_factual_rigor: 85,
      avg_framing: 30,
      lean_spread: 12,
      framing_spread: 18,
      lean_range: 22,
      sensationalism_spread: 25,
      opinion_spread: 12,
      aggregate_confidence: 0.80,
      analyzed_count: 8,
    },
  },
  {
    id: "cluster-005",
    title: "Ukraine-Russia Ceasefire Negotiations Enter Critical Phase",
    summary: "Mediators from Turkey and the UAE reported progress on a potential ceasefire framework as both sides agreed to a 48-hour pause in hostilities along the eastern front.",
    category: "conflict",
    section: "world",
    importance_score: 88,
    source_count: 6,
    first_published: "2026-03-18T02:00:00Z",
    last_updated: "2026-03-18T06:45:00Z",
    divergence_score: 0.55,
    headline_rank: 72,
    coverage_velocity: 10,
    bias_diversity: {
      avg_political_lean: 52,
      avg_sensationalism: 35,
      avg_opinion_fact: 28,
      avg_factual_rigor: 78,
      avg_framing: 45,
      lean_spread: 30,
      framing_spread: 25,
      lean_range: 50,
      sensationalism_spread: 20,
      opinion_spread: 22,
      aggregate_confidence: 0.72,
      analyzed_count: 6,
    },
  },
  {
    id: "cluster-006",
    title: "CERN Discovers New Subatomic Particle Challenging Standard Model",
    summary: "Physicists at the Large Hadron Collider announced the detection of an exotic particle that does not fit within the current Standard Model of particle physics, opening new avenues for theoretical research.",
    category: "science",
    section: "world",
    importance_score: 65,
    source_count: 3,
    first_published: "2026-03-17T22:00:00Z",
    last_updated: "2026-03-18T04:00:00Z",
    divergence_score: 0.10,
    headline_rank: 65,
    coverage_velocity: 4,
    bias_diversity: {
      avg_political_lean: 50,
      avg_sensationalism: 20,
      avg_opinion_fact: 10,
      avg_factual_rigor: 95,
      avg_framing: 12,
      lean_spread: 5,
      framing_spread: 8,
      lean_range: 10,
      sensationalism_spread: 6,
      opinion_spread: 5,
      aggregate_confidence: 0.95,
      analyzed_count: 3,
    },
  },
];

const mockClustersUS = [
  {
    id: "cluster-101",
    title: "Supreme Court Rules on Federal Agency Regulatory Power",
    summary: "In a landmark 5-4 decision, the Supreme Court significantly limited the Environmental Protection Agency's authority to regulate carbon emissions from power plants, sending the case back to lower courts.",
    category: "politics",
    section: "us",
    importance_score: 92,
    source_count: 9,
    first_published: "2026-03-18T07:00:00Z",
    last_updated: "2026-03-18T08:00:00Z",
    divergence_score: 0.65,
    headline_rank: 96,
    coverage_velocity: 18,
    bias_diversity: {
      avg_political_lean: 55,
      avg_sensationalism: 38,
      avg_opinion_fact: 35,
      avg_factual_rigor: 75,
      avg_framing: 48,
      lean_spread: 35,
      framing_spread: 30,
      lean_range: 60,
      sensationalism_spread: 22,
      opinion_spread: 28,
      aggregate_confidence: 0.70,
      analyzed_count: 9,
    },
  },
  {
    id: "cluster-102",
    title: "Federal Reserve Signals Potential Rate Cut in April Meeting",
    summary: "Fed Chair indicated the central bank is closely monitoring inflation data and labor market conditions, suggesting a possible quarter-point rate reduction at the next FOMC meeting.",
    category: "economy",
    section: "us",
    importance_score: 78,
    source_count: 6,
    first_published: "2026-03-18T05:30:00Z",
    last_updated: "2026-03-18T07:15:00Z",
    divergence_score: 0.25,
    headline_rank: 85,
    coverage_velocity: 9,
    bias_diversity: {
      avg_political_lean: 50,
      avg_sensationalism: 22,
      avg_opinion_fact: 18,
      avg_factual_rigor: 88,
      avg_framing: 25,
      lean_spread: 15,
      framing_spread: 12,
      lean_range: 28,
      sensationalism_spread: 10,
      opinion_spread: 14,
      aggregate_confidence: 0.88,
      analyzed_count: 6,
    },
  },
  {
    id: "cluster-103",
    title: "California Wildfires Force Evacuation of 50,000 Residents",
    summary: "Fast-moving wildfires in Southern California have burned over 30,000 acres, destroying hundreds of structures and prompting mandatory evacuations across three counties amid extreme heat and Santa Ana winds.",
    category: "environment",
    section: "us",
    importance_score: 85,
    source_count: 5,
    first_published: "2026-03-18T04:00:00Z",
    last_updated: "2026-03-18T07:30:00Z",
    divergence_score: 0.20,
    headline_rank: 80,
    coverage_velocity: 11,
    bias_diversity: {
      avg_political_lean: 42,
      avg_sensationalism: 48,
      avg_opinion_fact: 15,
      avg_factual_rigor: 82,
      avg_framing: 32,
      lean_spread: 20,
      framing_spread: 15,
      lean_range: 35,
      sensationalism_spread: 18,
      opinion_spread: 12,
      aggregate_confidence: 0.82,
      analyzed_count: 5,
    },
  },
  {
    id: "cluster-104",
    title: "Major Tech Companies Face New Antitrust Legislation in Senate",
    summary: "A bipartisan Senate bill targeting Big Tech monopolies advanced through committee, proposing structural separation of platform and marketplace operations for companies exceeding $500 billion market cap.",
    category: "tech",
    section: "us",
    importance_score: 70,
    source_count: 4,
    first_published: "2026-03-18T06:00:00Z",
    last_updated: "2026-03-18T07:00:00Z",
    divergence_score: 0.40,
    headline_rank: 74,
    coverage_velocity: 7,
    bias_diversity: {
      avg_political_lean: 45,
      avg_sensationalism: 30,
      avg_opinion_fact: 25,
      avg_factual_rigor: 80,
      avg_framing: 38,
      lean_spread: 22,
      framing_spread: 18,
      lean_range: 40,
      sensationalism_spread: 14,
      opinion_spread: 20,
      aggregate_confidence: 0.76,
      analyzed_count: 4,
    },
  },
];

function makeMockDeepDiveArticles(clusterId: string) {
  const sourcesByCluster: Record<string, Array<{ name: string; tier: string; url: string; lean: number; sense: number; opinion: number; rigor: number; framing: number }>> = {
    "cluster-001": [
      { name: "Reuters", tier: "international", url: "https://reuters.com/article/eu-china-trade", lean: 48, sense: 10, opinion: 8, rigor: 92, framing: 18 },
      { name: "BBC News", tier: "international", url: "https://bbc.com/news/eu-china", lean: 45, sense: 12, opinion: 10, rigor: 90, framing: 20 },
      { name: "Wall Street Journal", tier: "us_major", url: "https://wsj.com/articles/eu-china", lean: 60, sense: 18, opinion: 15, rigor: 88, framing: 25 },
      { name: "Al Jazeera", tier: "international", url: "https://aljazeera.com/economy/eu-china", lean: 40, sense: 15, opinion: 12, rigor: 85, framing: 22 },
      { name: "ProPublica", tier: "independent", url: "https://propublica.org/article/eu-china", lean: 35, sense: 8, opinion: 14, rigor: 92, framing: 28 },
    ],
    "cluster-002": [
      { name: "AP News", tier: "us_major", url: "https://apnews.com/climate-summit", lean: 48, sense: 15, opinion: 12, rigor: 90, framing: 22 },
      { name: "The Guardian", tier: "international", url: "https://theguardian.com/environment/climate", lean: 32, sense: 28, opinion: 22, rigor: 85, framing: 38 },
      { name: "Bloomberg", tier: "us_major", url: "https://bloomberg.com/climate-deal", lean: 52, sense: 20, opinion: 18, rigor: 88, framing: 30 },
      { name: "DW News", tier: "international", url: "https://dw.com/climate-agreement", lean: 42, sense: 22, opinion: 16, rigor: 82, framing: 32 },
      { name: "The Intercept", tier: "independent", url: "https://theintercept.com/climate", lean: 28, sense: 30, opinion: 25, rigor: 80, framing: 42 },
      { name: "France24", tier: "international", url: "https://france24.com/climate", lean: 40, sense: 18, opinion: 15, rigor: 78, framing: 28 },
      { name: "NPR", tier: "us_major", url: "https://npr.org/climate-deal", lean: 38, sense: 14, opinion: 20, rigor: 85, framing: 25 },
    ],
    "cluster-101": [
      { name: "CNN", tier: "us_major", url: "https://cnn.com/scotus-ruling", lean: 35, sense: 45, opinion: 40, rigor: 72, framing: 52 },
      { name: "Fox News", tier: "us_major", url: "https://foxnews.com/scotus-epa", lean: 75, sense: 42, opinion: 38, rigor: 70, framing: 55 },
      { name: "New York Times", tier: "us_major", url: "https://nytimes.com/scotus-agency", lean: 38, sense: 30, opinion: 32, rigor: 82, framing: 42 },
      { name: "Washington Post", tier: "us_major", url: "https://washingtonpost.com/scotus", lean: 40, sense: 35, opinion: 35, rigor: 80, framing: 45 },
      { name: "AP News", tier: "us_major", url: "https://apnews.com/scotus-ruling", lean: 50, sense: 15, opinion: 10, rigor: 92, framing: 20 },
      { name: "Reuters", tier: "international", url: "https://reuters.com/scotus", lean: 50, sense: 12, opinion: 8, rigor: 90, framing: 18 },
      { name: "The Intercept", tier: "independent", url: "https://theintercept.com/scotus", lean: 25, sense: 48, opinion: 55, rigor: 75, framing: 60 },
      { name: "Bellingcat", tier: "independent", url: "https://bellingcat.com/analysis/scotus", lean: 42, sense: 20, opinion: 30, rigor: 85, framing: 35 },
      { name: "PBS NewsHour", tier: "us_major", url: "https://pbs.org/scotus-ruling", lean: 45, sense: 18, opinion: 22, rigor: 88, framing: 28 },
    ],
  };

  const sources = sourcesByCluster[clusterId] || [
    { name: "Reuters", tier: "international", url: "https://reuters.com/generic", lean: 50, sense: 15, opinion: 10, rigor: 90, framing: 20 },
    { name: "AP News", tier: "us_major", url: "https://apnews.com/generic", lean: 50, sense: 12, opinion: 8, rigor: 88, framing: 18 },
    { name: "The Guardian", tier: "international", url: "https://theguardian.com/generic", lean: 35, sense: 22, opinion: 20, rigor: 82, framing: 30 },
  ];

  return sources.map((src, i) => ({
    article: {
      id: `art-${clusterId}-${i}`,
      title: `Coverage by ${src.name}`,
      url: src.url,
      summary: `${src.name} reports on this story with their characteristic perspective and editorial focus.`,
      author: null,
      published_at: "2026-03-18T06:00:00Z",
      source: {
        name: src.name,
        tier: src.tier,
        url: src.url,
        political_lean_baseline: src.lean,
      },
      bias_scores: [{
        political_lean: src.lean,
        sensationalism: src.sense,
        opinion_fact: src.opinion,
        factual_rigor: src.rigor,
        framing: src.framing,
        confidence: 0.85,
      }],
    },
  }));
}

const mockPipelineRun = [
  {
    completed_at: "2026-03-18T06:15:00Z",
    articles_fetched: 150,
    status: "completed",
  },
];

// ============================================================================
// ROUTE INTERCEPTION SETUP
// ============================================================================

async function setupMockRoutes(page: Page) {
  const SUPABASE_URL = "xryzskhgfuafyotrcdvj.supabase.co";

  await page.route(`**/${SUPABASE_URL}/rest/v1/**`, async (route) => {
    const url = route.request().url();

    if (url.includes("story_clusters")) {
      // Determine which section is being requested
      const isUS = url.includes("section%22%3A%22us") || url.includes('section"="us') || url.includes("section=eq.us") || url.includes("section%22%3Aeq.us");
      const isWorld = url.includes("section%22%3A%22world") || url.includes('section"="world') || url.includes("section=eq.world") || url.includes("section%22%3Aeq.world");

      let data = [...mockClustersWorld, ...mockClustersUS];
      if (isUS && !isWorld) {
        data = mockClustersUS;
      } else if (isWorld && !isUS) {
        data = mockClustersWorld;
      }

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        headers: {
          "content-range": `0-${data.length - 1}/${data.length}`,
          "access-control-allow-origin": "*",
        },
        body: JSON.stringify(data),
      });
    } else if (url.includes("cluster_articles")) {
      // Extract cluster_id from the URL
      const clusterIdMatch = url.match(/cluster_id=eq\.([^&]+)/);
      const clusterId = clusterIdMatch ? decodeURIComponent(clusterIdMatch[1]) : "cluster-001";

      const articles = makeMockDeepDiveArticles(clusterId);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify(articles),
      });
    } else if (url.includes("pipeline_runs")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify(mockPipelineRun[0]),
      });
    } else if (url.includes("cluster_bias_summary")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        headers: { "access-control-allow-origin": "*" },
        body: JSON.stringify([]),
      });
    } else {
      await route.continue();
    }
  });
}

// ============================================================================
// TEST
// ============================================================================

test("UAT Round 2 — Full Test Suite with Mock Data", async ({ browser }) => {
  test.setTimeout(300000);
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();
  page.setDefaultTimeout(10000);

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
    // A. PAGE LOAD WITH MOCK DATA
    // =================================================================
    await runSection("A. Page Load (Mock Data)", async () => {
      await setupMockRoutes(page);

      const t0 = Date.now();
      await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 30000 });
      const loadTime = Date.now() - t0;
      record("A. Page Load (Mock Data)", "Page loads", "PASS", `${loadTime}ms`);

      // Wait for stories to render
      await page.waitForFunction(
        () => document.querySelector(".lead-story") || document.querySelector(".story-card"),
        {},
        { timeout: 15000 }
      ).catch(() => {});

      await page.waitForTimeout(1500);
      await shot(page, "A01-fullpage-with-data");

      const storyCount = await page.locator(".lead-story, .story-card").count();
      const emptyCount = await page.locator(".empty-state").count();

      if (storyCount > 0) {
        record("A. Page Load (Mock Data)", "Stories rendered", "PASS", `${storyCount} story elements visible`);
      } else if (emptyCount > 0) {
        record("A. Page Load (Mock Data)", "Stories rendered", "FAIL", "Empty state shown instead of mock data");
      } else {
        record("A. Page Load (Mock Data)", "Stories rendered", "FAIL", "No stories and no empty state");
      }

      record("A. Page Load (Mock Data)", "No page errors", pageErrors.length === 0 ? "PASS" : "WARN", `${pageErrors.length} errors`);
    });

    // =================================================================
    // B. STORY CARDS
    // =================================================================
    await runSection("B. Story Cards", async () => {
      // Lead story
      const leadCount = await page.locator(".lead-story").count();
      record("B. Story Cards", "Lead story present", leadCount > 0 ? "PASS" : "FAIL", `${leadCount} lead stories`);

      if (leadCount > 0) {
        const hasLeadClass = await page.locator(".lead-story").first().evaluate(
          (el) => el.classList.contains("lead-story")
        );
        record("B. Story Cards", "Lead story .lead-story class", hasLeadClass ? "PASS" : "FAIL", "");

        await shotEl(page, ".lead-story", "B01-lead-story");

        // Check hero-sized headline
        const leadFontSize = await page.locator(".lead-story__headline").first().evaluate(
          (el) => parseFloat(getComputedStyle(el).fontSize)
        ).catch(() => 0);
        record("B. Story Cards", "Lead hero headline size", leadFontSize >= 24 ? "PASS" : "WARN", `${leadFontSize}px`);

        // Lead story components
        const leadCat = await page.locator(".lead-story .category-tag").count();
        record("B. Story Cards", "Lead category tag", leadCat > 0 ? "PASS" : "FAIL", "");

        const leadTime = await page.locator(".lead-story .time-tag").count();
        record("B. Story Cards", "Lead timestamp", leadTime > 0 ? "PASS" : "FAIL", "");

        const leadSummary = await page.locator(".lead-story__summary").textContent().catch(() => "");
        record("B. Story Cards", "Lead summary text", (leadSummary?.length || 0) > 20 ? "PASS" : "FAIL", `${leadSummary?.length || 0} chars`);

        const leadSourceCount = await page.locator(".lead-story .source-count").textContent().catch(() => "");
        record("B. Story Cards", "Lead source count", leadSourceCount?.includes("sources") ? "PASS" : "FAIL", `"${leadSourceCount?.trim()}"`);

        const leadBias = await page.locator(".lead-story .bias-stamp").count();
        record("B. Story Cards", "Lead BiasStamp", leadBias > 0 ? "PASS" : "FAIL", "");
      }

      // Medium stories grid
      const mediumGrid = await page.locator(".grid-medium").count();
      if (mediumGrid > 0) {
        await shotEl(page, ".grid-medium", "B02-medium-grid");
        const mediumItems = await page.locator(".grid-medium__item").count();
        record("B. Story Cards", "Medium grid items", mediumItems >= 2 ? "PASS" : "WARN", `${mediumItems} items`);

        // Check that grid has multiple columns at desktop
        const mediumCols = await page.locator(".grid-medium").evaluate(
          (el) => getComputedStyle(el).gridTemplateColumns
        ).catch(() => "none");
        const colCount = mediumCols.split(/\s+/).filter((s: string) => s.match(/\d/)).length;
        record("B. Story Cards", "Medium grid multi-column", colCount >= 2 ? "PASS" : "WARN", `Columns: ${colCount} (${mediumCols})`);
      } else {
        record("B. Story Cards", "Medium grid exists", "WARN", "No .grid-medium found");
      }

      // Compact stories grid
      const compactGrid = await page.locator(".grid-compact").count();
      if (compactGrid > 0) {
        await shotEl(page, ".grid-compact", "B03-compact-grid");
        const compactItems = await page.locator(".grid-compact__item").count();
        record("B. Story Cards", "Compact grid items", compactItems >= 1 ? "PASS" : "WARN", `${compactItems} items`);

        const compactCols = await page.locator(".grid-compact").evaluate(
          (el) => getComputedStyle(el).gridTemplateColumns
        ).catch(() => "none");
        record("B. Story Cards", "Compact grid density", "PASS", `Columns: ${compactCols}`);
      } else {
        record("B. Story Cards", "Compact grid exists", "WARN", "No .grid-compact found");
      }

      // Total visible stories
      const totalStories = await page.locator(".lead-story, .story-card").count();
      record("B. Story Cards", "Total visible stories", totalStories >= 4 ? "PASS" : "WARN", `${totalStories} stories`);

      // Check individual story card structure
      const cards = page.locator(".story-card");
      const cardCount = await cards.count();
      if (cardCount > 0) {
        const firstCard = cards.first();

        const hasCat = (await firstCard.locator(".category-tag").count()) > 0;
        record("B. Story Cards", "Card has category tag", hasCat ? "PASS" : "FAIL", "");

        const hasTime = (await firstCard.locator(".time-tag").count()) > 0;
        record("B. Story Cards", "Card has timestamp", hasTime ? "PASS" : "FAIL", "");

        const hasHeadline = (await firstCard.locator(".story-card__headline").count()) > 0;
        record("B. Story Cards", "Card has headline", hasHeadline ? "PASS" : "FAIL", "");

        if (await firstCard.locator(".story-card__summary").count() > 0) {
          const overflowVal = await firstCard.locator(".story-card__summary").evaluate(
            (el) => getComputedStyle(el).overflow
          ).catch(() => "?");
          record("B. Story Cards", "Card summary clamped", "PASS", `overflow: ${overflowVal}`);
        }

        const hasSrcCount = (await firstCard.locator(".source-count").count()) > 0;
        record("B. Story Cards", "Card has source count", hasSrcCount ? "PASS" : "FAIL", "");

        const hasBias = (await firstCard.locator(".bias-stamp").count()) > 0;
        record("B. Story Cards", "Card has BiasStamp", hasBias ? "PASS" : "FAIL", "");

        // Hover effect
        const bgBefore = await firstCard.evaluate((el) => getComputedStyle(el).backgroundColor).catch(() => "?");
        await firstCard.hover();
        await page.waitForTimeout(300);
        const bgAfter = await firstCard.evaluate((el) => getComputedStyle(el).backgroundColor).catch(() => "?");
        await shot(page, "B04-card-hover");
        record("B. Story Cards", "Card hover effect", bgBefore !== bgAfter ? "PASS" : "WARN", `Before: ${bgBefore}, After: ${bgAfter}`);
      }

      // Column dividers
      if (await page.locator(".grid-medium__item").count() > 1) {
        const borderRight = await page.locator(".grid-medium__item").first().evaluate(
          (el) => getComputedStyle(el).borderRightStyle
        ).catch(() => "none");
        record("B. Story Cards", "Column dividers", borderRight !== "none" ? "PASS" : "WARN", `border-right-style: ${borderRight}`);
      }
    });

    // =================================================================
    // C. BIASSTAMP
    // =================================================================
    await runSection("C. BiasStamp", async () => {
      const stampCount = await page.locator(".bias-stamp").count();
      record("C. BiasStamp", "Stamps present", stampCount > 0 ? "PASS" : "FAIL", `${stampCount} stamps`);

      if (stampCount === 0) return;

      const firstStamp = page.locator(".bias-stamp").first();
      const circle = firstStamp.locator(".bias-stamp__circle");

      // Hover to open tooltip
      await circle.hover();
      await page.waitForTimeout(600);

      const tooltipVisible = await firstStamp.locator(".bias-stamp__expanded").isVisible().catch(() => false);
      if (tooltipVisible) {
        record("C. BiasStamp", "Hover opens tooltip", "PASS", "Tooltip visible");
        await shotEl(page, ".bias-stamp__expanded", "C01-bias-tooltip");

        // Check tooltip header
        const header = await firstStamp.locator(".bias-stamp__expanded-header").textContent().catch(() => "");
        record("C. BiasStamp", "Tooltip header 'Bias Analysis'", header?.includes("Bias Analysis") ? "PASS" : "FAIL", `"${header}"`);

        // Check bias rows
        const biasRows = await firstStamp.locator(".bias-stamp__expanded .bias-row").count();
        record("C. BiasStamp", "5 bias rows", biasRows >= 5 ? "PASS" : "FAIL", `${biasRows} rows`);

        // Check Lean label exists
        const leanLabel = await firstStamp.locator(".bias-stamp__expanded .bias-row .bias-row__label").first().textContent().catch(() => "");
        record("C. BiasStamp", "Lean label present", leanLabel === "Lean" ? "PASS" : "WARN", `"${leanLabel}"`);

        // Check Rigor bar
        const rigorRow = firstStamp.locator(".bias-stamp__expanded .bias-row").nth(1);
        const rigorLabel = await rigorRow.locator(".bias-row__label").textContent().catch(() => "");
        record("C. BiasStamp", "Rigor bar present", rigorLabel === "Rigor" ? "PASS" : "WARN", `"${rigorLabel}"`);

        // Check Tone bar
        const toneRow = firstStamp.locator(".bias-stamp__expanded .bias-row").nth(2);
        const toneLabel = await toneRow.locator(".bias-row__label").textContent().catch(() => "");
        record("C. BiasStamp", "Tone bar present", toneLabel === "Tone" ? "PASS" : "WARN", `"${toneLabel}"`);

        // Check Type badge
        const typeBadge = await firstStamp.locator(".bias-stamp__expanded .type-badge").textContent().catch(() => "");
        record("C. BiasStamp", "Type badge present", typeBadge ? "PASS" : "FAIL", `"${typeBadge}"`);

        // Check Framing bar
        const framingRow = firstStamp.locator(".bias-stamp__expanded .bias-row").nth(4);
        const framingLabel = await framingRow.locator(".bias-row__label").textContent().catch(() => "");
        record("C. BiasStamp", "Framing bar present", framingLabel === "Framing" ? "PASS" : "WARN", `"${framingLabel}"`);

        // Check progress bar widths > 0
        const fills = firstStamp.locator(".bias-stamp__expanded .progress-bar__fill");
        const fillCount = await fills.count();
        let filledBars = 0;
        for (let i = 0; i < fillCount; i++) {
          const width = await fills.nth(i).evaluate((el) => el.getBoundingClientRect().width).catch(() => 0);
          if (width > 0) filledBars++;
        }
        record("C. BiasStamp", "Progress bars animated (width > 0)", filledBars > 0 ? "PASS" : "WARN", `${filledBars}/${fillCount} filled`);

        // Check lean spectrum dot position
        const leanDots = firstStamp.locator(".bias-stamp__expanded div[style*='borderRadius']");
        // Use broader selector for the spectrum dot
        const spectrumExists = await firstStamp.locator(".bias-stamp__expanded .bias-row").first().evaluate(
          (el) => {
            const dot = el.querySelector("div[style*='border-radius: 50%'], div[style*='borderRadius']");
            return dot ? true : false;
          }
        ).catch(() => false);
        record("C. BiasStamp", "Lean spectrum dot exists", spectrumExists ? "PASS" : "WARN", "");
      } else {
        record("C. BiasStamp", "Hover opens tooltip", "FAIL", "Tooltip did not appear");
      }

      // Move mouse away - verify tooltip closes
      await page.mouse.move(0, 0);
      await page.waitForTimeout(500);
      const tooltipGone = !(await firstStamp.locator(".bias-stamp__expanded").isVisible().catch(() => false));
      record("C. BiasStamp", "Mouse leave closes tooltip", tooltipGone ? "PASS" : "WARN", "");

      // Click to toggle open
      await circle.click();
      await page.waitForTimeout(400);
      const clickOpens = await firstStamp.locator(".bias-stamp__expanded").isVisible().catch(() => false);
      record("C. BiasStamp", "Click opens tooltip", clickOpens ? "PASS" : "WARN", "");

      // Escape closes
      if (clickOpens) {
        await page.keyboard.press("Escape");
        await page.waitForTimeout(400);
        const escCloses = !(await firstStamp.locator(".bias-stamp__expanded").isVisible().catch(() => false));
        record("C. BiasStamp", "Escape closes tooltip", escCloses ? "PASS" : "FAIL", "");
      }
    });

    // =================================================================
    // D. DEEP DIVE PANEL
    // =================================================================
    await runSection("D. Deep Dive Panel", async () => {
      // Click on the lead story
      const clickable = page.locator(".lead-story, .story-card").first();
      if (await clickable.count() === 0) {
        record("D. Deep Dive Panel", "Clickable story", "FAIL", "No stories to click");
        return;
      }

      // Get the headline text before clicking
      const clickedTitle = await clickable.locator(".lead-story__headline, .story-card__headline").first().textContent().catch(() => "");

      await clickable.click();
      await page.waitForTimeout(1500);

      const panelVisible = await page.locator(".deep-dive-panel").isVisible().catch(() => false);
      if (!panelVisible) {
        record("D. Deep Dive Panel", "Panel opens", "FAIL", "Panel did not appear");
        return;
      }

      record("D. Deep Dive Panel", "Panel opens on click", "PASS", "Panel visible");
      await shot(page, "D01-deep-dive-panel");

      // Backdrop overlay
      const backdropExists = (await page.locator(".deep-dive-backdrop").count()) > 0;
      record("D. Deep Dive Panel", "Backdrop overlay visible", backdropExists ? "PASS" : "FAIL", "");

      // Headline matches clicked story
      const panelHeadline = await page.locator(".deep-dive-panel h2").first().textContent().catch(() => "");
      const headlineMatches = clickedTitle && panelHeadline && panelHeadline.includes(clickedTitle.trim().slice(0, 20));
      record("D. Deep Dive Panel", "Headline matches clicked story", headlineMatches ? "PASS" : "WARN", `Panel: "${panelHeadline?.slice(0, 60)}", Clicked: "${clickedTitle?.trim().slice(0, 60)}"`);

      // "What happened" section
      const whatHappened = (await page.locator("#dd-summary").count()) > 0;
      record("D. Deep Dive Panel", "'What happened' section", whatHappened ? "PASS" : "FAIL", "");

      // Wait for live data to load
      await page.waitForTimeout(3000);
      await shot(page, "D02-deep-dive-loaded");

      // Source coverage list
      const sourceRows = await page.locator(".deep-dive-panel .source-row").count();
      if (sourceRows > 0) {
        record("D. Deep Dive Panel", "Source coverage list", "PASS", `${sourceRows} sources`);

        const firstSource = page.locator(".deep-dive-panel .source-row").first();

        // Source name link
        const nameLink = await firstSource.locator(".source-link").count();
        record("D. Deep Dive Panel", "Source name link", nameLink > 0 ? "PASS" : "FAIL", "");

        // Tier badge
        const tierBadge = await firstSource.locator(".tier-badge").count();
        const tierText = await firstSource.locator(".tier-badge").textContent().catch(() => "");
        record("D. Deep Dive Panel", "Tier badge (US/Intl/Ind)", tierBadge > 0 ? "PASS" : "FAIL", `"${tierText}"`);

        // BiasStamp per source
        const srcBias = await firstSource.locator(".bias-stamp").count();
        record("D. Deep Dive Panel", "Source BiasStamp", srcBias > 0 ? "PASS" : "FAIL", "");

        // External link
        const extLink = await firstSource.locator(".external-link-icon").count();
        record("D. Deep Dive Panel", "Source external link", extLink > 0 ? "PASS" : "FAIL", "");

        // Check external link target="_blank"
        const targetBlank = await firstSource.locator("a[target='_blank']").count();
        record("D. Deep Dive Panel", "External link target=_blank", targetBlank > 0 ? "PASS" : "FAIL", `${targetBlank} links with target=_blank`);

        await shotEl(page, ".deep-dive-panel .source-row:first-child", "D03-source-row");
      } else {
        record("D. Deep Dive Panel", "Source coverage list", "WARN", "No source rows loaded");
      }

      // Coverage breakdown bars
      const coverageBars = await page.locator(".deep-dive-panel .coverage-bar").count();
      record("D. Deep Dive Panel", "Coverage breakdown bars", coverageBars > 0 ? "PASS" : "WARN", `${coverageBars} bars`);

      if (coverageBars > 0) {
        await shotEl(page, "#dd-breakdown", "D04-coverage-breakdown");
      }

      // Where sources agree / diverge
      const consensus = (await page.locator("#dd-consensus").count()) > 0;
      record("D. Deep Dive Panel", "Where sources agree", consensus ? "PASS" : "WARN", "");

      const divergence = (await page.locator("#dd-divergence").count()) > 0;
      record("D. Deep Dive Panel", "Where sources diverge", divergence ? "PASS" : "WARN", "");

      // --- Close via Escape ---
      await page.keyboard.press("Escape");
      await page.waitForTimeout(700);
      const escCloses = !(await page.locator(".deep-dive-panel").isVisible().catch(() => false));
      record("D. Deep Dive Panel", "Escape closes panel", escCloses ? "PASS" : "FAIL", "");

      // --- Re-open, close via backdrop ---
      await clickable.click();
      await page.waitForTimeout(1000);
      if (await page.locator(".deep-dive-panel").isVisible().catch(() => false)) {
        await page.locator(".deep-dive-backdrop").click({ position: { x: 10, y: 10 }, force: true });
        await page.waitForTimeout(700);
        const backdropCloses = !(await page.locator(".deep-dive-panel").isVisible().catch(() => false));
        record("D. Deep Dive Panel", "Backdrop click closes panel", backdropCloses ? "PASS" : "FAIL", "");
      } else {
        record("D. Deep Dive Panel", "Backdrop click closes panel", "WARN", "Could not reopen panel");
      }

      // --- Re-open, close via Back button ---
      await clickable.click();
      await page.waitForTimeout(1000);
      if (await page.locator(".deep-dive-panel").isVisible().catch(() => false)) {
        await page.locator(".deep-dive-back").click();
        await page.waitForTimeout(700);
        const backCloses = !(await page.locator(".deep-dive-panel").isVisible().catch(() => false));
        record("D. Deep Dive Panel", "Back button closes panel", backCloses ? "PASS" : "FAIL", "");
      } else {
        record("D. Deep Dive Panel", "Back button closes panel", "WARN", "Could not reopen panel");
      }
    });

    // =================================================================
    // E. GRID LAYOUTS AT DIFFERENT VIEWPORTS
    // =================================================================
    await runSection("E. Grid Layouts", async () => {
      // Desktop 1280px
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForFunction(
        () => document.querySelector(".lead-story") || document.querySelector(".story-card"),
        {},
        { timeout: 15000 }
      ).catch(() => {});
      await page.waitForTimeout(1500);

      if (await page.locator(".grid-medium").count() > 0) {
        const medCols = await page.locator(".grid-medium").evaluate(
          (el) => getComputedStyle(el).gridTemplateColumns
        ).catch(() => "?");
        const medColCount = medCols.split(/\s+/).filter((s: string) => s.match(/\d/)).length;
        record("E. Grid Layouts", "Desktop 1280px: medium grid 3 columns", medColCount === 3 ? "PASS" : "WARN", `${medColCount} columns (${medCols})`);
      } else {
        record("E. Grid Layouts", "Desktop 1280px: medium grid", "WARN", "No medium grid");
      }

      if (await page.locator(".grid-compact").count() > 0) {
        const compCols = await page.locator(".grid-compact").evaluate(
          (el) => getComputedStyle(el).gridTemplateColumns
        ).catch(() => "?");
        const compColCount = compCols.split(/\s+/).filter((s: string) => s.match(/\d/)).length;
        record("E. Grid Layouts", "Desktop 1280px: compact grid 4 columns", compColCount === 4 ? "PASS" : "WARN", `${compColCount} columns (${compCols})`);
      } else {
        record("E. Grid Layouts", "Desktop 1280px: compact grid", "WARN", "No compact grid");
      }

      await shot(page, "E01-fullpage-desktop-1280");

      // Tablet 768px
      await page.setViewportSize({ width: 768, height: 1024 });
      await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForFunction(
        () => document.querySelector(".lead-story") || document.querySelector(".story-card"),
        {},
        { timeout: 15000 }
      ).catch(() => {});
      await page.waitForTimeout(1500);

      if (await page.locator(".grid-medium").count() > 0) {
        const tabMedCols = await page.locator(".grid-medium").evaluate(
          (el) => getComputedStyle(el).gridTemplateColumns
        ).catch(() => "?");
        const tabMedColCount = tabMedCols.split(/\s+/).filter((s: string) => s.match(/\d/)).length;
        record("E. Grid Layouts", "Tablet 768px: medium grid 2 columns", tabMedColCount === 2 ? "PASS" : "WARN", `${tabMedColCount} columns (${tabMedCols})`);
      }

      if (await page.locator(".grid-compact").count() > 0) {
        const tabCompCols = await page.locator(".grid-compact").evaluate(
          (el) => getComputedStyle(el).gridTemplateColumns
        ).catch(() => "?");
        const tabCompColCount = tabCompCols.split(/\s+/).filter((s: string) => s.match(/\d/)).length;
        record("E. Grid Layouts", "Tablet 768px: compact grid 2 columns", tabCompColCount === 2 ? "PASS" : "WARN", `${tabCompColCount} columns (${tabCompCols})`);
      }

      await shot(page, "E02-fullpage-tablet-768");

      // Mobile 375px
      await page.setViewportSize({ width: 375, height: 812 });
      await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForFunction(
        () => document.querySelector(".lead-story") || document.querySelector(".story-card"),
        {},
        { timeout: 15000 }
      ).catch(() => {});
      await page.waitForTimeout(1500);

      if (await page.locator(".grid-medium").count() > 0) {
        const mobMedCols = await page.locator(".grid-medium").evaluate(
          (el) => getComputedStyle(el).gridTemplateColumns
        ).catch(() => "?");
        const mobMedColCount = mobMedCols.split(/\s+/).filter((s: string) => s.match(/\d/)).length;
        record("E. Grid Layouts", "Mobile 375px: single column", mobMedColCount === 1 ? "PASS" : "WARN", `${mobMedColCount} columns (${mobMedCols})`);
      }

      await shot(page, "E03-fullpage-mobile-375");

      // Reset to desktop
      await page.setViewportSize({ width: 1280, height: 800 });
    });

    // =================================================================
    // F. CATEGORY FILTERING
    // =================================================================
    await runSection("F. Category Filtering", async () => {
      await page.setViewportSize({ width: 1280, height: 800 });
      await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForFunction(
        () => document.querySelector(".lead-story") || document.querySelector(".story-card"),
        {},
        { timeout: 15000 }
      ).catch(() => {});
      await page.waitForTimeout(1500);

      // Count stories with "All" filter
      const allCount = await page.locator(".lead-story, .story-card").count();
      record("F. Category Filtering", "All filter story count", allCount > 0 ? "PASS" : "FAIL", `${allCount} stories`);

      // Click Economy
      const economyChip = page.locator(".filter-chip", { hasText: /^\s*Economy\s*$/i }).first();
      if (await economyChip.isVisible().catch(() => false)) {
        await economyChip.click();
        await page.waitForTimeout(500);
        const econCount = await page.locator(".lead-story, .story-card").count();
        const econEmpty = await page.locator(".empty-state--inline").count();
        record("F. Category Filtering", "Economy filter", econCount < allCount || econEmpty > 0 ? "PASS" : "WARN", `Stories: ${econCount}, Empty: ${econEmpty} (was ${allCount})`);
        await shot(page, "F01-filter-economy");
      }

      // Click Politics
      const politicsChip = page.locator(".filter-chip", { hasText: /^\s*Politics\s*$/i }).first();
      if (await politicsChip.isVisible().catch(() => false)) {
        await politicsChip.click();
        await page.waitForTimeout(500);
        const polCount = await page.locator(".lead-story, .story-card").count();
        const polEmpty = await page.locator(".empty-state--inline").count();
        record("F. Category Filtering", "Politics filter", polCount + polEmpty > 0 ? "PASS" : "FAIL", `Stories: ${polCount}, Empty: ${polEmpty}`);
        await shot(page, "F02-filter-politics");
      }

      // Click a category that should have 0 world stories (e.g., Sports)
      const sportsChip = page.locator(".filter-chip", { hasText: /^\s*Sports\s*$/i }).first();
      if (await sportsChip.isVisible().catch(() => false)) {
        await sportsChip.click();
        await page.waitForTimeout(500);
        const sportsCount = await page.locator(".lead-story, .story-card").count();
        const sportsEmpty = await page.locator(".empty-state--inline").count();

        if (sportsCount === 0 && sportsEmpty > 0) {
          const emptyText = await page.locator(".empty-state--inline").textContent().catch(() => "");
          record("F. Category Filtering", "Empty category message", emptyText?.includes("No stories") ? "PASS" : "WARN", `"${emptyText?.trim().slice(0, 80)}"`);
          await shot(page, "F03-filter-empty");
        } else {
          record("F. Category Filtering", "Sports filter", "PASS", `Stories: ${sportsCount}`);
        }
      }

      // Reset to All
      const allChip = page.locator(".filter-chip", { hasText: /^\s*All\s*$/i }).first();
      await allChip.click();
      await page.waitForTimeout(500);
      const resetCount = await page.locator(".lead-story, .story-card").count();
      record("F. Category Filtering", "Reset to All restores stories", resetCount === allCount ? "PASS" : "WARN", `Before: ${allCount}, After: ${resetCount}`);
    });

    // =================================================================
    // G. EDITION LINE
    // =================================================================
    await runSection("G. Edition Line", async () => {
      // Should already be on the page from above
      await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
      await page.waitForTimeout(500);

      const editionLine = page.locator(".edition-line");
      if (await editionLine.count() > 0) {
        const editionText = await editionLine.textContent().catch(() => "");
        record("G. Edition Line", "Edition line visible", "PASS", `"${editionText?.trim()}"`);

        const hasWorldEdition = editionText?.includes("World Edition");
        record("G. Edition Line", "Shows 'World Edition'", hasWorldEdition ? "PASS" : "FAIL", "");

        const hasStoryCount = editionText?.match(/\d+ stories/);
        record("G. Edition Line", "Shows story count", hasStoryCount ? "PASS" : "FAIL", `"${hasStoryCount?.[0]}"`);

        await shotEl(page, ".edition-line", "G01-edition-line");

        // Brand name
        const brandName = await editionLine.locator(".brand-name").textContent().catch(() => "");
        record("G. Edition Line", "Brand name", brandName?.includes("void") ? "PASS" : "WARN", `"${brandName}"`);
      } else {
        record("G. Edition Line", "Edition line visible", "FAIL", "Not found");
      }

      // Switch to US section
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(300);

      const usTab = page.locator(".nav-tab", { hasText: "US" });
      if (await usTab.isVisible().catch(() => false)) {
        await usTab.click();
        await page.waitForTimeout(1500);

        // Wait for US stories
        await page.waitForFunction(
          () => document.querySelector(".lead-story") || document.querySelector(".story-card") || document.querySelector(".empty-state--inline"),
          {},
          { timeout: 10000 }
        ).catch(() => {});
        await page.waitForTimeout(500);

        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await page.waitForTimeout(500);

        const usEdition = page.locator(".edition-line");
        if (await usEdition.count() > 0) {
          const usText = await usEdition.textContent().catch(() => "");
          record("G. Edition Line", "US section shows 'US Edition'", usText?.includes("US Edition") ? "PASS" : "FAIL", `"${usText?.trim()}"`);
          await shotEl(page, ".edition-line", "G02-edition-line-us");
        } else {
          record("G. Edition Line", "US section edition line", "WARN", "Not visible (maybe no US stories?)");
        }

        // Switch back to World
        await page.evaluate(() => window.scrollTo(0, 0));
        const worldTab = page.locator(".nav-tab", { hasText: "World" });
        if (await worldTab.isVisible().catch(() => false)) {
          await worldTab.click();
          await page.waitForTimeout(1000);
        }
      }
    });

    // =================================================================
    // H. REFRESH BUTTON WITH DATA
    // =================================================================
    await runSection("H. Refresh Button (with data)", async () => {
      const rb = page.locator(".refresh-btn");
      if (!(await rb.isVisible().catch(() => false))) {
        record("H. Refresh Button (with data)", "Exists", "FAIL", "Not found");
        return;
      }

      const btnText = await rb.textContent().catch(() => "");
      record("H. Refresh Button (with data)", "Shows pipeline time", btnText?.includes("Last updated") ? "PASS" : "WARN", `"${btnText?.trim()}"`);
      await shotEl(page, ".refresh-btn", "H01-refresh-button");

      // Trigger refresh
      await rb.click();
      await page.waitForTimeout(400);

      const dialogVis = await page.locator(".refresh-dialog").isVisible().catch(() => false);
      if (dialogVis) {
        record("H. Refresh Button (with data)", "Confirmation dialog", "PASS", "Visible");

        // Click Refresh
        await page.locator(".refresh-dialog .btn-primary").click();
        await page.waitForTimeout(200);

        const refreshText = await rb.textContent().catch(() => "");
        record("H. Refresh Button (with data)", "Loading state", refreshText?.includes("Refreshing") ? "PASS" : "WARN", `"${refreshText?.trim()}"`);

        await page.waitForTimeout(1500);
        const afterText = await rb.textContent().catch(() => "");
        record("H. Refresh Button (with data)", "Completed state", afterText?.includes("Last updated") ? "PASS" : "WARN", `"${afterText?.trim()}"`);
      } else {
        record("H. Refresh Button (with data)", "Confirmation dialog", "FAIL", "Did not appear");
      }
    });

    // =================================================================
    // I. DEEP DIVE WITH US STORY (different sources)
    // =================================================================
    await runSection("I. Deep Dive — US Story", async () => {
      // Switch to US
      const usTab = page.locator(".nav-tab", { hasText: "US" });
      if (await usTab.isVisible().catch(() => false)) {
        await usTab.click();
        await page.waitForTimeout(1500);

        await page.waitForFunction(
          () => document.querySelector(".lead-story") || document.querySelector(".story-card"),
          {},
          { timeout: 10000 }
        ).catch(() => {});
        await page.waitForTimeout(500);

        const usStories = await page.locator(".lead-story, .story-card").count();
        record("I. Deep Dive — US Story", "US stories loaded", usStories > 0 ? "PASS" : "FAIL", `${usStories} stories`);

        if (usStories > 0) {
          await page.locator(".lead-story, .story-card").first().click();
          await page.waitForTimeout(1500);

          const panelVis = await page.locator(".deep-dive-panel").isVisible().catch(() => false);
          if (panelVis) {
            record("I. Deep Dive — US Story", "Panel opens", "PASS", "");

            // Wait for sources to load
            await page.waitForTimeout(3000);
            await shot(page, "I01-deep-dive-us-story");

            const srcCount = await page.locator(".deep-dive-panel .source-row").count();
            record("I. Deep Dive — US Story", "Source rows loaded", srcCount > 0 ? "PASS" : "WARN", `${srcCount} sources`);

            // Check tier variety
            if (srcCount > 0) {
              const tiers = await page.locator(".deep-dive-panel .tier-badge").allTextContents();
              const uniqueTiers = [...new Set(tiers)];
              record("I. Deep Dive — US Story", "Multiple tiers represented", uniqueTiers.length >= 2 ? "PASS" : "WARN", `Tiers: ${uniqueTiers.join(", ")}`);
            }

            // Coverage breakdown
            const coverageCount = await page.locator(".deep-dive-panel .coverage-bar").count();
            record("I. Deep Dive — US Story", "Coverage breakdown", coverageCount > 0 ? "PASS" : "WARN", `${coverageCount} bars`);

            if (coverageCount > 0) {
              await shotEl(page, "#dd-breakdown", "I02-coverage-us");
            }

            // Close
            await page.keyboard.press("Escape");
            await page.waitForTimeout(700);
          } else {
            record("I. Deep Dive — US Story", "Panel opens", "FAIL", "Did not appear");
          }
        }
      }

      // Switch back to World
      const worldTab = page.locator(".nav-tab", { hasText: "World" });
      if (await worldTab.isVisible().catch(() => false)) {
        await worldTab.click();
        await page.waitForTimeout(1000);
      }
    });

    // =================================================================
    // J. DARK MODE WITH DATA
    // =================================================================
    await runSection("J. Dark Mode with Data", async () => {
      const tg = page.locator(".theme-toggle").first();
      await tg.click();
      await page.waitForTimeout(500);

      await shot(page, "J01-fullpage-dark-with-data");

      // Check story cards render in dark mode
      const storiesInDark = await page.locator(".lead-story, .story-card").count();
      record("J. Dark Mode with Data", "Stories visible in dark mode", storiesInDark > 0 ? "PASS" : "FAIL", `${storiesInDark} stories`);

      // Check bias stamp visibility in dark mode
      const stampVisible = await page.locator(".bias-stamp__circle").first().isVisible().catch(() => false);
      record("J. Dark Mode with Data", "BiasStamp visible in dark", stampVisible ? "PASS" : "WARN", "");

      // Open deep dive in dark mode
      await page.locator(".lead-story, .story-card").first().click();
      await page.waitForTimeout(1500);
      await page.waitForTimeout(2000);
      await shot(page, "J02-deep-dive-dark");

      const panelDark = await page.locator(".deep-dive-panel").isVisible().catch(() => false);
      record("J. Dark Mode with Data", "Deep dive in dark mode", panelDark ? "PASS" : "WARN", "");

      await page.keyboard.press("Escape");
      await page.waitForTimeout(700);

      // Switch back to light
      await tg.click();
      await page.waitForTimeout(400);
    });

    // =================================================================
    // K. MOBILE WITH DATA (375px)
    // =================================================================
    await runSection("K. Mobile with Data", async () => {
      await page.setViewportSize({ width: 375, height: 812 });
      await page.goto(BASE_URL, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForFunction(
        () => document.querySelector(".lead-story") || document.querySelector(".story-card"),
        {},
        { timeout: 15000 }
      ).catch(() => {});
      await page.waitForTimeout(1500);

      await shot(page, "K01-fullpage-mobile-with-data");

      const mobileStories = await page.locator(".lead-story, .story-card").count();
      record("K. Mobile with Data", "Stories render on mobile", mobileStories > 0 ? "PASS" : "FAIL", `${mobileStories} stories`);

      // Verify single column
      if (await page.locator(".grid-medium").count() > 0) {
        const cols = await page.locator(".grid-medium").evaluate(
          (el) => getComputedStyle(el).gridTemplateColumns
        ).catch(() => "?");
        const colCount = cols.split(/\s+/).filter((s: string) => s.match(/\d/)).length;
        record("K. Mobile with Data", "Single column layout", colCount === 1 ? "PASS" : "WARN", `${colCount} columns`);
      }

      // Open deep dive on mobile
      if (mobileStories > 0) {
        await page.locator(".lead-story, .story-card").first().click();
        await page.waitForTimeout(1500);

        const mobilePanelVis = await page.locator(".deep-dive-panel").isVisible().catch(() => false);
        if (mobilePanelVis) {
          await page.waitForTimeout(2000);
          await shot(page, "K02-mobile-deep-dive-with-data");

          const panelWidth = await page.evaluate(() => {
            const p = document.querySelector(".deep-dive-panel");
            return p ? p.getBoundingClientRect().width : 0;
          });
          record("K. Mobile with Data", "Deep dive full-screen width", panelWidth >= 370 ? "PASS" : "WARN", `width: ${panelWidth}px`);

          await page.keyboard.press("Escape");
          await page.waitForTimeout(700);
        }
      }

      // Reset to desktop
      await page.setViewportSize({ width: 1280, height: 800 });
    });

  } finally {
    writeReport();
    await context.close();
  }
});
