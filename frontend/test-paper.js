const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

async function testPaperPage() {
  const browser = await chromium.launch();
  const context = await browser.createContext();
  const page = await context.newPage();

  // Create screenshot directory
  const screenshotDir = '/tmp/void-news-paper-screenshots';
  if (!fs.existsSync(screenshotDir)) {
    fs.mkdirSync(screenshotDir, { recursive: true });
  }

  const tests = [
    { url: 'https://aacrit.github.io/void--news/paper', name: 'world-desktop', width: 1440, height: 900 },
    { url: 'https://aacrit.github.io/void--news/paper', name: 'world-tablet', width: 1024, height: 900 },
    { url: 'https://aacrit.github.io/void--news/paper', name: 'world-mobile', width: 375, height: 812 },
    { url: 'https://aacrit.github.io/void--news/paper/us', name: 'us-desktop', width: 1440, height: 900 },
    { url: 'https://aacrit.github.io/void--news/paper/us', name: 'us-tablet', width: 1024, height: 900 },
    { url: 'https://aacrit.github.io/void--news/paper/us', name: 'us-mobile', width: 375, height: 812 },
    { url: 'https://aacrit.github.io/void--news/paper/india', name: 'india-desktop', width: 1440, height: 900 },
    { url: 'https://aacrit.github.io/void--news/paper/india', name: 'india-tablet', width: 1024, height: 900 },
    { url: 'https://aacrit.github.io/void--news/paper/india', name: 'india-mobile', width: 375, height: 812 },
  ];

  for (const test of tests) {
    try {
      console.log(`Testing ${test.name} (${test.width}x${test.height})...`);
      await page.setViewportSize({ width: test.width, height: test.height });
      await page.goto(test.url, { waitUntil: 'networkidle', timeout: 30000 });

      // Wait for content to load
      await page.waitForTimeout(2000);

      const screenshotPath = path.join(screenshotDir, `${test.name}.png`);
      await page.screenshot({ path: screenshotPath, fullPage: true });
      console.log(`  Saved: ${screenshotPath}`);
    } catch (err) {
      console.error(`  Error: ${err.message}`);
    }
  }

  await browser.close();
  console.log(`Screenshots saved to: ${screenshotDir}`);
}

testPaperPage().catch(console.error);
