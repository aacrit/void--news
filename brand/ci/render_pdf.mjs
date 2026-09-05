// Render the print guidelines HTML to a real A4 PDF via chromium.
// Resolves Playwright from ../../frontend/node_modules.
// Usage: node brand/ci/render_pdf.mjs <html-abs-path> <pdf-abs-path>
import { createRequire } from 'module';
import { pathToFileURL } from 'url';

const require = createRequire(new URL('../../frontend/package.json', import.meta.url));
const { chromium } = require('playwright');

const [htmlPath, pdfPath] = process.argv.slice(2);
const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto(pathToFileURL(htmlPath).href, { waitUntil: 'networkidle' });
await page.emulateMedia({ media: 'print' });
await page.pdf({
  path: pdfPath, format: 'A4', printBackground: true,
  margin: { top: '0', bottom: '0', left: '0', right: '0' },
});
await browser.close();
console.log('wrote', pdfPath);
