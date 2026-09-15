import { firefox } from "playwright";
const b = await firefox.launch({ headless: true });
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
const p = await ctx.newPage();
await p.goto("http://localhost:8765/", { waitUntil: "networkidle", timeout: 30000 });
await p.waitForTimeout(1500);
const sizes = await p.evaluate(() => {
  const out = { digest: [], wire: [] };
  for (const el of document.querySelectorAll('.story-card[data-variant="digest"] .story-card__headline')) {
    out.digest.push(getComputedStyle(el).fontSize);
  }
  for (const el of document.querySelectorAll('.story-card[data-variant="wire"] .story-card__headline')) {
    out.wire.push(getComputedStyle(el).fontSize);
  }
  return out;
});
console.log("Digest headline sizes:", [...new Set(sizes.digest)], "count:", sizes.digest.length);
console.log("Wire   headline sizes:", [...new Set(sizes.wire)], "count:", sizes.wire.length);
await b.close();
