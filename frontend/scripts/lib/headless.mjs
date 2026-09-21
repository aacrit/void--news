/* ===========================================================================
   scripts/lib/headless.mjs: the one harness under every browser-level gate.

   verify-responsive.mjs and verify-headless.mjs both need the same four
   things, and each was about to carry its own copy: the built export served
   over HTTP with the base path mapped (never file://, see the trap below), a
   Chromium that launches on this container AND on the CI runner, the list of
   elements that sit off-canvas on purpose, and the overflow measurement that
   neutralises the document's own clipping before it believes a number.

   TWO TRAPS, both hit while writing the first gate, both cheap to repeat:

   * NEVER measure over file://. The pages link CSS at an absolute
     <base>/_next/... path, which resolves to the filesystem root and 404s, so
     the page measures as if it had no stylesheet at all. Serve `out/` over
     HTTP with the base path mapped, and assert the stylesheet loaded before
     believing a single measurement (`isStyled`).
   * The bundled Playwright wants a Chromium build this container does not
     carry. Launch with an explicit executablePath rather than running
     `playwright install`; CI installs the browser where Playwright looks.

   Needs: a completed `next build`. Lives under frontend/ so `playwright`
   resolves from frontend/node_modules.
   =========================================================================== */
import { chromium } from "playwright";
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { existsSync, readFileSync } from "node:fs";
import { join, extname, resolve } from "node:path";

export const OUT = resolve(new URL("../../out", import.meta.url).pathname);

/* The base path is NOT fixed. Local builds use /void--news; CI's build-check
   sets NEXT_PUBLIC_BASE_PATH to "". Hardcoding it would make a gate serve
   404s in CI and measure an unstyled page, which is the same failure the
   file:// trap produces and just as quiet. Read it back off the built HTML. */
export async function readBasePath() {
  const html = await readFile(join(OUT, "index.html"), "utf8");
  return html.match(/href="([^"]*)\/_next\/static\//)?.[1] ?? "";
}

export const MIME = {
  ".html": "text/html", ".css": "text/css", ".js": "text/javascript",
  ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png",
  ".jpg": "image/jpeg", ".webp": "image/webp", ".woff2": "font/woff2",
  ".mp3": "audio/mpeg", ".xml": "application/xml", ".ico": "image/x-icon",
  ".txt": "text/plain", ".webmanifest": "application/manifest+json",
};

/* Serve `out/` the way Cloudflare Pages does: a directory is its index.html,
   a bare path may be a .html file, and anything else is the site's own 404
   page with a 404 status (Pages serves out/404.html for unknown routes). */
export function serve(base, port) {
  const notFound = existsSync(join(OUT, "404.html"))
    ? readFileSync(join(OUT, "404.html"))
    : Buffer.from("not found");
  const server = createServer(async (req, res) => {
    let p = decodeURIComponent(req.url.split("?")[0]);
    if (base && p.startsWith(base)) p = p.slice(base.length);
    let file = join(OUT, p);
    try {
      if ((await stat(file)).isDirectory()) file = join(file, "index.html");
    } catch {
      if (existsSync(file + ".html")) file = file + ".html";
    }
    try {
      const body = await readFile(file);
      res.writeHead(200, { "content-type": MIME[extname(file)] ?? "application/octet-stream" });
      res.end(body);
    } catch {
      res.writeHead(404, { "content-type": "text/html" }).end(notFound);
    }
  });
  return new Promise((r) => server.listen(port, () => r(server)));
}

/* Use an explicit binary ONLY when one is actually there. This container
   carries Chromium at a fixed path and the bundled Playwright expects a build
   it does not have, so pointing at it is required locally. CI runs
   `playwright install`, which puts the browser where Playwright looks by
   default, and hardcoding the local path there made the first gate fail on
   a binary that does not exist on the runner. Prefer the env var, then the
   known local path if it is real, then let Playwright resolve. */
const LOCAL_CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome";
export function launchChromium() {
  const explicit = process.env.VOID_CHROMIUM
    || (existsSync(LOCAL_CHROMIUM) ? LOCAL_CHROMIUM : undefined);
  return chromium.launch(explicit ? { executablePath: explicit } : {});
}

/* Elements that sit outside the viewport ON PURPOSE. Each needs a reason, so
   that adding one is a decision somebody made rather than a line somebody
   pasted to make the gate quiet. */
export const OFF_CANVAS = {
  "skip-to-content": "the skip link is parked at -9999px until focused",
  msp: "the mobile side panel is a closed drawer, off to the right by design",
  "msp__header": "inside the closed drawer",
  "msp__body": "inside the closed drawer",
  "msp__footer": "inside the closed drawer",
  "sigil-word": "inside the closed drawer",
};

/* Believe nothing until the stylesheet is proven to have loaded. This is the
   file:// trap: an unstyled page measures cleanly and means nothing. */
export function isStyled(page) {
  return page.evaluate(() => {
    if (document.styleSheets.length === 0) return false;
    const b = getComputedStyle(document.body);
    return b.fontFamily !== "" && b.margin !== "";
  });
}

/* Un-hide the DOCUMENT's clipping only, then measure. Both defects the
   responsive gate exists for were masked by `overflow-x: hidden` on the page
   wrappers, so a check that runs inside that clipping reports green on a
   page that is cropping content.

   Deliberately NOT every element: a cover image cropped by its own container
   (object-fit: cover) and a horizontal reel with its own overflow-x are both
   correct, and neutralising those turns good design into a failure. They do
   not contribute to the document's scroll width, which is exactly why the
   document is the right thing to measure. */
export function measureOverflow(page) {
  return page.evaluate((offCanvas) => {
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
}
