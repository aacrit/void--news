/* ===========================================================================
   verify-responsive.mjs: nothing may exceed the viewport, and sticky must stick.

   Two defects shipped on the History page and neither was visible by reading
   the CSS:

   1. The spine overflowed by exactly four column gaps at phone widths. The
      text track is min(--hist-measure, 100%), so below the measure it claimed
      the whole content box and the gaps had nowhere to go. A full-bleed rest
      measured 438px against a 390px viewport. It did not scroll, it CROPPED,
      because an ancestor clipped it.
   2. `position: sticky` had never held on any History page. Four ancestors
      set `overflow-x: hidden`, and `hidden` establishes a scroll container,
      which kills sticky in every descendant. The rail sat at y = -3130.

   Both were hidden BY the clipping, which is why this gate neutralises
   overflow before it measures (measureOverflow in lib/headless.mjs, which
   also documents the two traps: never file://, never `playwright install`).

   Run:  cd frontend && node scripts/verify-responsive.mjs
   Needs: a completed `next build`.
   =========================================================================== */
import { readBasePath, serve, launchChromium, isStyled, measureOverflow } from "./lib/headless.mjs";

const BASE = await readBasePath();
const PORT = 8899;
const WIDTHS = [390, 768, 1024, 1440];

/* Pages that carry the layouts most likely to break: the Hearing's named-line
   grid, the History landing, the weekly's measure, and the feed. */
const PAGES = [
  "/history/partition-of-india/",
  "/history/",
  "/paper/",
  "/weekly/",
  "/",
];

const failures = [];
const note = (s) => console.log(s);

const server = await serve(BASE, PORT);
const browser = await launchChromium();

for (const path of PAGES) {
  note(`\n${path}`);
  for (const width of WIDTHS) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    await page.goto(`http://localhost:${PORT}${BASE}${path}`, { waitUntil: "networkidle" });
    await page.waitForTimeout(250);

    if (!(await isStyled(page))) {
      failures.push(`${path} @${width}: no stylesheet loaded, measurement is meaningless`);
      await page.close();
      continue;
    }

    const r = await measureOverflow(page);
    if (r.sw > r.vw + 1) {
      failures.push(`${path} @${width}: document is ${r.sw - r.vw}px wider than the viewport`);
      note(`  [FAIL] ${width}px: scrollWidth ${r.sw} vs viewport ${r.vw} (+${r.sw - r.vw})`);
      r.culprits.forEach((c) => note(`           ${c}`));
    } else {
      note(`  [ok]   ${width}px: scrollWidth ${r.sw} == viewport, clipping neutralised`);
    }
    await page.close();
  }
}

/* Sticky must actually stick. A rail that never pinned looked identical to
   one that did, from the CSS. The masthead is the one mounted in
   app/layout.tsx (.nav-header); the History topbar it used to look for was
   deleted on 2026-09-21, and a selector that matches nothing skips forever. */
note("\nsticky");
for (const width of [1024, 1440]) {
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  await page.goto(`http://localhost:${PORT}${BASE}/history/partition-of-india/`, { waitUntil: "networkidle" });
  await page.evaluate(() => window.scrollTo(0, 4000));
  await page.waitForTimeout(350);
  const tops = await page.evaluate(() => {
    const at = (s) => {
      const el = document.querySelector(s);
      return el ? Math.round(el.getBoundingClientRect().top) : null;
    };
    return { rail: at(".hist-rail-slot") ?? at(".hist-rail"), masthead: at(".nav-header") };
  });
  for (const [name, top] of Object.entries(tops)) {
    if (top === null) { note(`  [skip] ${width}px ${name} not on this page`); continue; }
    /* Pinned means "still in the viewport after scrolling 4000px". An element
       that scrolled away reads as a large negative number. */
    if (top < 0 || top > 400) {
      failures.push(`sticky @${width}: ${name} did not stick, top=${top}`);
      note(`  [FAIL] ${width}px ${name} top=${top}: it scrolled away`);
    } else {
      note(`  [ok]   ${width}px ${name} top=${top}`);
    }
  }
  await page.close();
}

await browser.close();
server.close();

if (failures.length) {
  console.log(`\nFAIL  ${failures.length} responsive check(s)`);
  failures.forEach((f) => console.log(`  - ${f}`));
  process.exit(1);
}
console.log(`\nPASS  ${PAGES.length} page(s) x ${WIDTHS.length} width(s): nothing exceeds the viewport, and sticky sticks`);
