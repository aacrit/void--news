import { firefox } from "playwright";
const b = await firefox.launch({ headless: true });
for (const w of [375, 1024, 1440]) {
  const ctx = await b.newContext({ viewport: { width: w, height: 900 } });
  const p = await ctx.newPage();
  await p.goto("http://localhost:8765/", { waitUntil: "networkidle", timeout: 30000 });
  await p.waitForTimeout(1500);
  const data = await p.evaluate(() => {
    const out = {};
    const article = document.querySelector("article.lead-story");
    if (article) {
      const r = article.getBoundingClientRect();
      out.article = { class: article.className, w: Math.round(r.width), h: Math.round(r.height), left: Math.round(r.left), right: Math.round(r.right) };
    }
    const split = document.querySelector(".lead-split");
    if (split) {
      const r = split.getBoundingClientRect();
      out.split = { w: Math.round(r.width), left: Math.round(r.left), right: Math.round(r.right) };
    }
    const text = document.querySelector(".lead-split__text, [data-slot='text']");
    if (text) {
      const r = text.getBoundingClientRect();
      const cs = getComputedStyle(text);
      out.text = { w: Math.round(r.width), maxWidth: cs.maxWidth, left: Math.round(r.left), right: Math.round(r.right) };
    }
    const image = document.querySelector(".lead-split__image-frame");
    if (image) {
      const r = image.getBoundingClientRect();
      out.image = { w: Math.round(r.width), h: Math.round(r.height), aspect: (r.width/r.height).toFixed(2) };
    }
    const badge = document.querySelector(".lead-story__badge");
    if (badge) {
      const r = badge.getBoundingClientRect();
      const cs = getComputedStyle(badge);
      // ::before computed
      const beforeCs = getComputedStyle(badge, "::before");
      out.badge = {
        text: badge.textContent,
        w: Math.round(r.width),
        h: Math.round(r.height),
        left: Math.round(r.left),
        top: Math.round(r.top),
        display: cs.display,
        padding: cs.padding,
        beforeInset: `${beforeCs.top} ${beforeCs.right} ${beforeCs.bottom} ${beforeCs.left}`,
        beforeBg: beforeCs.backgroundImage.slice(0, 60),
        beforeTransform: beforeCs.transform,
      };
    }
    const headline = document.querySelector(".lead-headline, .lead-story__headline");
    if (headline) {
      const r = headline.getBoundingClientRect();
      out.headline = { w: Math.round(r.width), left: Math.round(r.left), right: Math.round(r.right) };
    }
    const canvas = document.querySelector("main, .home-feed-zones, .canvas, body");
    if (canvas) {
      const r = canvas.getBoundingClientRect();
      out.canvas = { w: Math.round(r.width), left: Math.round(r.left), right: Math.round(r.right) };
    }
    return out;
  });
  console.log(`\n=== ${w}px ===`);
  console.log(JSON.stringify(data, null, 2));
  await p.close();
  await ctx.close();
}
await b.close();
