import { firefox } from "playwright";
const b = await firefox.launch({ headless: true });
for (const [w, h] of [[360, 800], [375, 667], [390, 844], [430, 932]]) {
  const ctx = await b.newContext({
    viewport: { width: w, height: h },
    hasTouch: true,
    userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
  });
  const p = await ctx.newPage();
  await p.goto("http://localhost:8765/", { waitUntil: "networkidle", timeout: 30000 });
  await p.waitForTimeout(1500);
  const data = await p.evaluate(() => {
    const fold = window.innerHeight;
    const pill = document.querySelector(".mbp--stacked, .mbp");
    const hero = document.querySelector("article.lead-story, article.msc--hero, .msc--hero");
    const heroHeadline = document.querySelector(".msc__headline--hero, .lead-headline, .msc h1");
    const get = (el) => el ? (() => { const r = el.getBoundingClientRect(); return { top: Math.round(r.top), bottom: Math.round(r.bottom), h: Math.round(r.height) }; })() : null;
    return {
      fold,
      pill: get(pill),
      pillClass: pill?.className?.slice(0, 80),
      hero: get(hero),
      heroClass: hero?.className?.slice(0, 80),
      heroHeadline: get(heroHeadline),
      // also: is hero headline above fold?
      heroHeadlineVisible: heroHeadline ? heroHeadline.getBoundingClientRect().bottom <= fold : null,
    };
  });
  console.log(`\n=== ${w}×${h} (fold=${data.fold}) ===`);
  console.log(JSON.stringify(data, null, 2));
  await p.close();
  await ctx.close();
}
await b.close();
