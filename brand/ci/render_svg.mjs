// Reusable Playwright SVG -> transparent PNG renderer (self-contained in brand/).
// Resolves Playwright from ../../frontend/node_modules (the workspace that has
// it installed). Run: node brand/ci/render_svg.mjs <jobs.json>
//   jobs.json = [{ svg:"<abs path>", out:"<abs path>", width:<px> }, ...]
// Renders each SVG at the given pixel width (height from viewBox aspect) on a
// transparent ground. Font: whatever the SVG font stack resolves to on this
// machine -- Playfair Display if installed (CI), else Georgia (dev box). The
// Sigil geometry is exact regardless; only the wordmark face falls back.
import { createRequire } from 'module';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';

const require = createRequire(new URL('../../frontend/package.json', import.meta.url));
const { chromium } = require('playwright');

const jobs = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const browser = await chromium.launch();
const page = await browser.newPage({ deviceScaleFactor: 1 });

for (const job of jobs) {
  let svg = readFileSync(job.svg, 'utf8');
  const vb = svg.match(/viewBox="0 0 ([\d.]+) ([\d.]+)"/);
  const vw = parseFloat(vb[1]), vh = parseFloat(vb[2]);
  const h = Math.round(job.width * vh / vw);
  svg = svg.replace(/<svg /, `<svg width="${job.width}" height="${h}" `);
  const html = `<!doctype html><html><head><meta charset="utf-8">
    <style>html,body{margin:0;padding:0;background:transparent}svg{display:block}</style>
    </head><body>${svg}</body></html>`;
  await page.setViewportSize({ width: job.width, height: h });
  await page.setContent(html, { waitUntil: 'networkidle' });
  const el = await page.$('svg');
  await el.screenshot({ path: job.out, omitBackground: true });
  console.log(`  ${job.out.split(/[\\/]/).pop()}  ${job.width}x${h}`);
}
await browser.close();
console.log('done');
