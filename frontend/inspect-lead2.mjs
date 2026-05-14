import { firefox } from "playwright";
const b = await firefox.launch({ headless: true });
for (const w of [768, 1024, 1440, 1920]) {
  const ctx = await b.newContext({ viewport: { width: w, height: 1000 } });
  const p = await ctx.newPage();
  await p.goto("http://localhost:8765/", { waitUntil: "networkidle", timeout: 30000 });
  await p.waitForTimeout(1500);
  const data = await p.evaluate(() => {
    const out = {};
    const article = document.querySelector("article.lead-story");
    if (article) {
      const r = article.getBoundingClientRect();
      out.article = { w: Math.round(r.width), left: Math.round(r.left), right: Math.round(r.right) };
    }
    const text = document.querySelector(".lead-split__text");
    if (text) {
      const r = text.getBoundingClientRect();
      const cs = getComputedStyle(text);
      out.text = { w: Math.round(r.width), maxWidth: cs.maxWidth, left: Math.round(r.left), right: Math.round(r.right), display: cs.display };
    }
    const headline = document.querySelector(".lead-headline");
    if (headline) {
      const r = headline.getBoundingClientRect();
      const cs = getComputedStyle(headline);
      out.headline = { w: Math.round(r.width), maxWidth: cs.maxWidth, fontSize: cs.fontSize, left: Math.round(r.left), right: Math.round(r.right) };
    }
    const summary = document.querySelector(".lead-summary");
    if (summary) {
      const r = summary.getBoundingClientRect();
      const cs = getComputedStyle(summary);
      out.summary = { w: Math.round(r.width), maxWidth: cs.maxWidth, left: Math.round(r.left), right: Math.round(r.right) };
    }
    return out;
  });
  console.log(`\n=== ${w}px ===`);
  console.log(JSON.stringify(data, null, 2));
  await p.close();
  await ctx.close();
}
await b.close();
