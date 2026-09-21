/* ===========================================================================
   verify_responsive.mjs — nothing may exceed the viewport, and sticky must stick.

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
   overflow before it measures. A responsive check that runs against the page's
   own clipping reports green on a page that is cropping images.

   TWO TRAPS, both hit while writing this, both cheap to repeat:

   * NEVER measure over file://. The pages link CSS at an absolute
     /void--news/_next/... path, which resolves to the filesystem root and
     404s, so the page measures as if it had no stylesheet at all. Doing this
     produced a confident, entirely fictional "938px overflow" report. This
     script serves `out/` over HTTP with the base path mapped, and asserts the
     stylesheet actually loaded before it believes a single measurement.
   * The bundled Playwright wants a Chromium build this container does not
     carry. Launch with an explicit executablePath rather than running
     `playwright install`.

   Run:  cd frontend && node scripts/verify-responsive.mjs
   Needs: a completed `next build`. It lives under frontend/ so that
          `playwright` resolves from frontend/node_modules.
   =========================================================================== */
import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { join, extname, resolve } from "node:path";

const OUT = resolve(new URL("../out", import.meta.url).pathname);
/* The base path is NOT fixed. Local builds use /void--news; CI's build-check
   sets NEXT_PUBLIC_BASE_PATH to "". Hardcoding it would make this gate serve
   404s in CI and measure an unstyled page, which is the same failure the
   file:// trap produces and just as quiet. Read it back off the built HTML. */
const BASE = await (async () => {
  const html = await readFile(join(OUT, "index.html"), "utf8");
  const href = html.match(/href="([^"]*)\/_next\/static\//)?.[1] ?? "";
  return href;
})();
const PORT = 8899;
const WIDTHS = [390, 768, 1024, 1440];

/* Pages that carry the layouts most likely to break: the Hearing's named-line
   grid, the History landing, the weekly's measure, and the feed. */
const PAGES = [
  "/history/partition-of-india/",
  "/history/",
  "/weekly/",
  "/",
];

/* Elements that sit outside the viewport ON PURPOSE. Each needs a reason, so
   that adding one is a decision somebody made rather than a line somebody
   pasted to make the gate quiet. */
const OFF_CANVAS = {
  "skip-to-content": "the skip link is parked at -9999px until focused",
  msp: "the mobile side panel is a closed drawer, off to the right by design",
  "msp__header": "inside the closed drawer",
  "msp__body": "inside the closed drawer",
  "msp__footer": "inside the closed drawer",
  "sigil-word": "inside the closed drawer",
};

const MIME = {
  ".html": "text/html", ".css": "text/css", ".js": "text/javascript",
  ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png",
  ".jpg": "image/jpeg", ".webp": "image/webp", ".woff2": "font/woff2",
  ".mp3": "audio/mpeg", ".xml": "application/xml", ".ico": "image/x-icon",
};

function serve() {
  return createServer(async (req, res) => {
    let p = decodeURIComponent(req.url.split("?")[0]);
    if (p.startsWith(BASE)) p = p.slice(BASE.length);
    let file = join(OUT, p);
    try {
      if ((await stat(file)).isDirectory()) file = join(file, "index.html");
    } catch { /* fall through to the read */ }
    try {
      const body = await readFile(file);
      res.writeHead(200, { "content-type": MIME[extname(file)] ?? "application/octet-stream" });
      res.end(body);
    } catch {
      res.writeHead(404).end("not found");
    }
  });
}

const failures = [];
const note = (s) => console.log(s);

const server = serve();
await new Promise((r) => server.listen(PORT, r));
const browser = await chromium.launch({
  executablePath: process.env.VOID_CHROMIUM
    || "/opt/pw-browsers/chromium-1194/chrome-linux/chrome",
});

for (const path of PAGES) {
  note(`\n${path}`);
  for (const width of WIDTHS) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    await page.goto(`http://localhost:${PORT}${BASE}${path}`, { waitUntil: "networkidle" });
    await page.waitForTimeout(250);

    /* Believe nothing until the stylesheet is proven to have loaded. This is
       the file:// trap: an unstyled page measures cleanly and means nothing. */
    const styled = await page.evaluate(() => {
      if (document.styleSheets.length === 0) return false;
      const b = getComputedStyle(document.body);
      return b.fontFamily !== "" && b.margin !== "";
    });
    if (!styled) {
      failures.push(`${path} @${width}: no stylesheet loaded, measurement is meaningless`);
      await page.close();
      continue;
    }

    const r = await page.evaluate((offCanvas) => {
      /* Un-hide the DOCUMENT's clipping only. Both defects this gate exists
         for were masked by `overflow-x: hidden` on the page wrappers, so a
         check that runs inside that clipping reports green on a page that is
         cropping content.

         Deliberately NOT every element: a cover image cropped by its own
         container (object-fit: cover) and a horizontal reel with its own
         overflow-x are both correct, and neutralising those turns good design
         into a failure. They do not contribute to the document's scroll width,
         which is exactly why the document is the right thing to measure. */
      for (const el of [document.documentElement, document.body,
                        ...document.querySelectorAll("main, .hist-page, #main-content, .hist-event-detail, .page-container")]) {
        el.style.setProperty("overflow", "visible", "important");
      }
      const vw = document.documentElement.clientWidth;
      const sw = document.documentElement.scrollWidth;

      /* Diagnostics only: name what is pushing the document wide, so a failure
         is actionable rather than a number. */
      const culprits = [];
      if (sw > vw + 1) {
        for (const el of document.querySelectorAll("body *")) {
          const b = el.getBoundingClientRect();
          if (b.width === 0 || b.height === 0) continue;
          const cls = (el.className?.baseVal ?? el.className ?? "").toString();
          const first = cls.split(/\s+/)[0] || el.tagName.toLowerCase();
          if (Object.prototype.hasOwnProperty.call(offCanvas, first)) continue;
          if (el.closest("[data-off-canvas], .msp")) continue;
          if (b.right > vw + 1) {
            culprits.push(`${first} right=${Math.round(b.right)} w=${Math.round(b.width)}`);
          }
        }
      }
      return { vw, sw, culprits: culprits.slice(0, 5), n: culprits.length };
    }, OFF_CANVAS);

    if (r.sw > r.vw + 1) {
      failures.push(`${path} @${width}: document is ${r.sw - r.vw}px wider than the viewport`);
      note(`  [FAIL] ${width}px — scrollWidth ${r.sw} vs viewport ${r.vw} (+${r.sw - r.vw})`);
      r.culprits.forEach((c) => note(`           ${c}`));
    } else {
      note(`  [ok]   ${width}px — scrollWidth ${r.sw} == viewport, clipping neutralised`);
    }
    await page.close();
  }
}

/* ── Sticky must actually stick ──
   A rail that never pinned looked identical to one that did, from the CSS. */
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
    return { rail: at(".hist-rail-slot") ?? at(".hist-rail"), topbar: at(".hist-topbar") };
  });
  for (const [name, top] of Object.entries(tops)) {
    if (top === null) { note(`  [skip] ${width}px ${name} not on this page`); continue; }
    /* Pinned means "still in the viewport after scrolling 4000px". An element
       that scrolled away reads as a large negative number. */
    if (top < 0 || top > 400) {
      failures.push(`sticky @${width}: ${name} did not stick, top=${top}`);
      note(`  [FAIL] ${width}px ${name} top=${top} — it scrolled away`);
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
