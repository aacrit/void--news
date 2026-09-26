/* ===========================================================================
   verify-headless.mjs: the product, in a browser, as one system.

   Every other gate reads a file. verify_production.py reads the served HTML,
   copy-facts reads the source, css-parity reads the stylesheets, and
   verify-responsive measures five pages for width. None of them can see a
   console error, a hydration mismatch, a link to a page that does not exist,
   a button with no name, a theme toggle that leaves the status bar the wrong
   colour, or a drawer that lets focus escape. This one loads every route
   family at four widths in both colour modes and asserts the things a reader
   would hit in the first minute.

   Two modes:
     node scripts/verify-headless.mjs            every route family x 4 widths
                                                  x dark and light, plus the
                                                  scenarios (about 5 minutes)
     node scripts/verify-headless.mjs --quick    five routes x 390 and 1440,
                                                  dark, plus the scenarios
                                                  (about a minute; CI runs this)
     node scripts/verify-headless.mjs --route=/history/   one route, full grid

   Output: [ok]/[FAIL]/[skip]/[warn] lines, out/.verify-headless.json, and a
   screenshot per failing page under out/.verify-headless/. Exit 1 on any
   FAIL. An allowlist lives beside this file (verify-headless.allow.json):
   every entry names the check, a substring of the failure and a reason, so
   silencing a finding is a decision somebody wrote down.

   Needs: a completed `next build` (frontend/out). Serving and Chromium are
   shared with verify-responsive.mjs through lib/headless.mjs.
   =========================================================================== */
import { readFileSync, existsSync, readdirSync, statSync, mkdirSync, writeFileSync, unlinkSync } from "node:fs";
import { join } from "node:path";
import { OUT, readBasePath, serve, launchChromium, isStyled, measureOverflow } from "./lib/headless.mjs";

const args = process.argv.slice(2);
const QUICK = args.includes("--quick");
const ONLY = args.find((a) => a.startsWith("--route="))?.slice("--route=".length);
const BASE = await readBasePath();
const PORT = 8898;
const ORIGIN = `http://localhost:${PORT}`;
const SITE = "https://news.voidvision.org";
const TAGLINE_TITLE = "Void News. See through the void.";

/* ── Routes ──────────────────────────────────────────────────────────────
   The thirteen static routes, then one sample per dynamic family, read from
   the build so the sweep cannot name a page that was not exported. */
const STATIC_ROUTES = [
  "/", "/onair/", "/history/", "/weekly/", "/weekly/archive/", "/paper/",
  "/audio/", "/sources/", "/about/", "/ship/", "/press/", "/privacy/",
  "/history/threads/",
];
const QUICK_ROUTES = ["/", "/history/", "/weekly/", "/paper/", "/onair/", "/audio/"];

function firstDir(rel, skip = []) {
  const dir = join(OUT, rel);
  if (!existsSync(dir)) return null;
  const names = readdirSync(dir)
    .filter((n) => !skip.includes(n) && statSync(join(dir, n)).isDirectory() && existsSync(join(dir, n, "index.html")))
    .sort();
  return names[0] ?? null;
}
function dynamicRoutes() {
  const out = [];
  const event = existsSync(join(OUT, "history/partition-of-india/index.html"))
    ? "partition-of-india"
    : firstDir("history", ["era", "region", "threads"]);
  if (event) out.push(`/history/${event}/`);
  const era = firstDir("history/era");
  if (era) out.push(`/history/era/${era}/`);
  const region = firstDir("history/region");
  if (region) out.push(`/history/region/${region}/`);
  const issues = existsSync(join(OUT, "weekly"))
    ? readdirSync(join(OUT, "weekly")).filter((n) => /^\d{4}-\d{2}-\d{2}$/.test(n)).sort()
    : [];
  if (issues.length) out.push(`/weekly/${issues[issues.length - 1]}/`);
  const story = firstDir("story");
  if (story) out.push(`/story/${story}/`);
  return out;
}
/* The 404 is a route family too: Pages serves out/404.html for any unknown
   path, and until 2026-09-21 it was the framework's white default. */
const NOT_FOUND_ROUTE = "/this-page-does-not-exist/";

const ROUTES = ONLY ? [ONLY]
  : QUICK ? QUICK_ROUTES
  : [...STATIC_ROUTES, ...dynamicRoutes(), NOT_FOUND_ROUTE];
const WIDTHS = ONLY ? [390, 768, 1024, 1440] : QUICK ? [390, 1440] : [390, 768, 1024, 1440];
const SCHEMES = ONLY || !QUICK ? ["dark", "light"] : ["dark"];

/* ── The section map, ported from NavBar.tsx ─────────────────────────────
   If sectionForPath changes there and not here, the data-section check fails
   on every page, which is the point: the masthead's idea of where it is must
   match the URL's. */
function sectionForPath(path) {
  const p = path || "/";
  if (p === "/") return "news";
  const head = p.split("/").filter(Boolean)[0];
  switch (head) {
    case "history": return "history";
    case "weekly": return "weekly";
    case "paper": return "paper";
    case "onair": return "onair";
    case "audio":
    case "listen": return "audio";
    case "sources": return "sources";
    case "ship":
    case "feedback": return "ship";
    case "about": return "about";
    case "press": return "press";
    case "privacy": return "privacy";
    case "story": return "story";
    default: return "other";
  }
}
/* Sections that have a link in the masthead (SECTION_LINKS + PAGE_LINKS). */
const LINKED_SECTIONS = new Set(["audio", "onair", "history", "weekly", "sources", "ship", "about"]);
/* Landings whose nameplate is the current page. */
const NAMEPLATE_LANDINGS = new Set(["/history/", "/weekly/", "/paper/", "/audio/"]);

/* ── Redirect prefixes from public/_redirects: a link into one of these is a
   301 at the edge, not a dangling link. ── */
const REDIRECTS = (() => {
  const file = join(OUT, "_redirects");
  if (!existsSync(file)) return [];
  return readFileSync(file, "utf8").split("\n")
    .map((l) => l.trim()).filter((l) => l && !l.startsWith("#"))
    .map((l) => l.split(/\s+/)[0].replace(/\/?\*$/, ""))
    .filter((p) => p && p !== "/");
})();
function isRedirected(path) {
  return REDIRECTS.some((r) => path === r || path === r + "/" || path.startsWith(r + "/"));
}
function resolvesInOut(path) {
  const clean = path.replace(/[?#].*$/, "");
  const rel = clean.replace(/^\//, "");
  if (rel === "") return true;
  const candidates = [join(OUT, rel), join(OUT, rel, "index.html"), join(OUT, rel.replace(/\/$/, "") + ".html")];
  return candidates.some((c) => existsSync(c) && (statSync(c).isFile() || existsSync(join(c, "index.html"))));
}

/* ── Allowlist ── */
const ALLOW_FILE = new URL("./verify-headless.allow.json", import.meta.url).pathname;
const ALLOW = existsSync(ALLOW_FILE) ? JSON.parse(readFileSync(ALLOW_FILE, "utf8")) : [];
for (const a of ALLOW) {
  if (!a.check || !a.match || !a.reason) throw new Error(`allowlist entry needs check, match and reason: ${JSON.stringify(a)}`);
}
function allowed(check, route, detail) {
  return ALLOW.find((a) => a.check === check && (!a.route || a.route === route) && detail.includes(a.match));
}

/* ── Reporting ── */
const results = [];
const failures = [];
let current = "";
function ctx(route, width, scheme) { current = `${route} @${width} ${scheme}`; }
function ok(check, detail = "") { results.push({ where: current, check, status: "ok", detail }); console.log(`  [ok]   ${check}${detail ? ": " + detail : ""}`); }
function skip(check, detail = "") { results.push({ where: current, check, status: "skip", detail }); console.log(`  [skip] ${check}${detail ? ": " + detail : ""}`); }
function warn(check, detail = "") { results.push({ where: current, check, status: "warn", detail }); console.log(`  [warn] ${check}${detail ? ": " + detail : ""}`); }
function fail(check, detail, route = current.split(" @")[0]) {
  const a = allowed(check, route, detail);
  if (a) { results.push({ where: current, check, status: "allowed", detail, reason: a.reason }); console.log(`  [allow] ${check}: ${detail} (${a.reason})`); return false; }
  results.push({ where: current, check, status: "FAIL", detail });
  failures.push(`${current}: ${check}: ${detail}`);
  console.log(`  [FAIL] ${check}: ${detail}`);
  return true;
}
function assert(cond, check, detail) { return cond ? (ok(check, detail), true) : (fail(check, detail), false); }
const SHOTS = join(OUT, ".verify-headless");
mkdirSync(SHOTS, { recursive: true });
async function shot(page, name) {
  try { await page.screenshot({ path: join(SHOTS, name.replace(/[^a-z0-9]+/gi, "-") + ".png"), fullPage: false }); } catch { /* a closed page is not a second failure */ }
}
const DASH = /[–—]/;

/* ── A page with its console, its network and its colour mode wired ── */
async function openPage(browser, { width, scheme, route, storage = {}, session = {}, reducedMotion = "no-preference", permissions = [] }) {
  const context = await browser.newContext({
    viewport: { width, height: width < 768 ? 844 : 900 },
    colorScheme: scheme,
    reducedMotion,
    isMobile: width < 768,
    hasTouch: width < 768,
    permissions,
  });
  /* The theme is decided before first paint by the inline script in
     app/layout.tsx from localStorage.void-news-theme, so the mode is set the
     way a reader's browser would set it, not by poking the attribute after. */
  await context.addInitScript(({ scheme, storage, session }) => {
    try {
      localStorage.setItem("void-news-theme", scheme);
      for (const [k, v] of Object.entries(storage)) localStorage.setItem(k, v);
      for (const [k, v] of Object.entries(session)) sessionStorage.setItem(k, v);
    } catch { /* storage may be unavailable */ }
  }, { scheme, storage, session });
  const page = await context.newPage();
  const log = { console: [], errors: [], bad: [], failed: [] };
  page.on("console", (m) => {
    if (m.type() !== "error" && m.type() !== "warning") return;
    /* A resource that failed to load on ANOTHER origin is the network this
       runs on (Wikimedia images behind a proxy), not the page. Same-origin
       failures are caught by the response and requestfailed hooks. */
    const at = m.location()?.url ?? "";
    if (/Failed to load resource/.test(m.text()) && at && !at.startsWith(ORIGIN)) return;
    /* The 404 route's own document is a 404 by definition. */
    if (/Failed to load resource/.test(m.text()) && route === NOT_FOUND_ROUTE && at.endsWith(route)) return;
    log.console.push(`${m.type()}: ${m.text()}`);
  });
  page.on("pageerror", (e) => log.errors.push(String(e?.message ?? e)));
  page.on("response", (r) => {
    const u = r.url();
    if (u.startsWith(ORIGIN) && r.status() >= 400) log.bad.push(`${r.status()} ${u.slice(ORIGIN.length)}`);
  });
  page.on("requestfailed", (r) => {
    const u = r.url();
    const err = r.failure()?.errorText ?? "";
    /* A prefetch cancelled by navigation is not a broken resource. */
    if (u.startsWith(ORIGIN) && !/ERR_ABORTED/.test(err)) log.failed.push(`${err} ${u.slice(ORIGIN.length)}`);
  });
  if (route !== undefined) {
    await page.goto(`${ORIGIN}${BASE}${route}`, { waitUntil: "networkidle", timeout: 60_000 });
    await page.waitForTimeout(300);
  }
  return { context, page, log };
}

/* ── Per-page audit ─────────────────────────────────────────────────────── */
async function auditPage(browser, route, width, scheme, axeSource) {
  ctx(route, width, scheme);
  console.log(`\n${current}`);
  const { context, page, log } = await openPage(browser, { width, scheme, route });
  const isNotFound = route === NOT_FOUND_ROUTE;
  let failed = false;
  const F = (check, detail) => { if (fail(check, detail)) failed = true; };

  try {
    /* 1. Console, page errors, hydration. */
    const hydration = log.console.filter((m) => /hydrat|#418\b|#423\b|#425\b|#310\b/i.test(m));
    if (hydration.length) F("hydration", hydration[0].slice(0, 200)); else ok("hydration", "no mismatch");
    const consoleErrors = log.console.filter((m) => m.startsWith("error:"));
    if (consoleErrors.length) F("console-errors", `${consoleErrors.length}: ${consoleErrors[0].slice(0, 200)}`); else ok("console-errors", "none");
    if (log.errors.length) F("page-errors", log.errors[0].slice(0, 200)); else ok("page-errors", "none");

    /* 2. Network: nothing same-origin came back >= 400 except the 404
       document itself; nothing failed to load. */
    const bad = log.bad.filter((b) => !(isNotFound && b.startsWith("404 ") && b.endsWith(route)));
    if (bad.length) F("responses", bad.slice(0, 3).join(", ")); else ok("responses", "no 4xx/5xx");
    if (log.failed.length) F("requests-failed", log.failed.slice(0, 3).join(", ")); else ok("requests-failed", "none");

    /* 3. Styled, then measured. */
    if (!(await isStyled(page))) { F("stylesheet", "no stylesheet loaded, the rest of this page is meaningless"); return; }
    const ov = await measureOverflow(page);
    if (ov.sw > ov.vw + 1) F("overflow", `document ${ov.sw - ov.vw}px wider than the viewport: ${ov.culprits.join("; ")}`);
    else ok("overflow", `scrollWidth ${ov.sw} == viewport`);

    /* 4. One h1. */
    const h1 = await page.evaluate(() => [...document.querySelectorAll("h1")].map((h) => h.textContent.trim().slice(0, 60)));
    if (h1.length !== 1) F("one-h1", `${h1.length} h1: ${JSON.stringify(h1)}`); else ok("one-h1", h1[0]);

    /* 5. Title grammar: the front page is the tagline; every other page is
       "Page | Void News" or "Page | Section | Void News". */
    const title = await page.title();
    const titleOk = route === "/" ? title === TAGLINE_TITLE
      : /^.+ \| Void News$/.test(title) || /^.+ \| (History|Weekly|On Air|Paper) \| Void News$/.test(title);
    if (!titleOk) F("title-grammar", JSON.stringify(title)); else ok("title-grammar", title);
    if (DASH.test(title)) F("no-dash", `title: ${title}`);

    /* 6. The one masthead and footer, and the masthead's idea of where it is. */
    const chrome = await page.evaluate(() => ({
      headers: document.querySelectorAll(".nav-header").length,
      footers: document.querySelectorAll(".site-footer").length,
      section: document.querySelector(".nav-header")?.getAttribute("data-section") ?? null,
      nameplateCurrent: !!document.querySelector(".nav-nameplate[aria-current='page']"),
      pageCurrent: document.querySelectorAll(".nav-page[aria-current='page']").length,
      tabbar: !!document.querySelector(".mtb"),
      homeCurrent: !!document.querySelector(".mtb__home[aria-current='page']"),
    }));
    if (chrome.headers !== 1) F("one-masthead", `${chrome.headers} .nav-header`); else ok("one-masthead");
    if (chrome.footers !== 1) F("one-footer", `${chrome.footers} .site-footer`); else ok("one-footer");
    const expectSection = isNotFound ? "other" : sectionForPath(route);
    if (chrome.section !== expectSection) F("data-section", `masthead says ${chrome.section}, URL says ${expectSection}`); else ok("data-section", chrome.section);
    const expectNameplate = NAMEPLATE_LANDINGS.has(route);
    if (chrome.nameplateCurrent !== expectNameplate) F("aria-current-nameplate", `expected ${expectNameplate}, got ${chrome.nameplateCurrent}`); else ok("aria-current-nameplate", String(chrome.nameplateCurrent));
    const expectPages = LINKED_SECTIONS.has(expectSection) ? 1 : 0;
    if (chrome.pageCurrent !== expectPages) F("aria-current-page", `expected ${expectPages} current link(s), got ${chrome.pageCurrent}`); else ok("aria-current-page", String(chrome.pageCurrent));
    if (width < 768) {
      if (!chrome.tabbar) F("mobile-tabbar", "no .mtb at phone width"); else ok("mobile-tabbar");
      if (route === "/" && !chrome.homeCurrent) F("mobile-tabbar-home", ".mtb__home is not aria-current on the front page");
    }

    /* 7. Every internal link resolves in the export or is a known 301. */
    const hrefs = await page.evaluate(() => [...document.querySelectorAll("a[href]")].map((a) => a.getAttribute("href")));
    const dangling = new Set();
    let checked = 0;
    for (const href of hrefs) {
      if (!href || href.startsWith("#") || /^(mailto|tel|javascript):/.test(href)) continue;
      let path;
      if (href.startsWith(ORIGIN)) path = href.slice(ORIGIN.length);
      else if (href.startsWith(SITE)) path = href.slice(SITE.length);
      else if (href.startsWith("/")) path = href;
      else continue;
      if (BASE && path.startsWith(BASE)) path = path.slice(BASE.length);
      path = path || "/";
      checked++;
      if (isRedirected(path)) continue;
      if (!resolvesInOut(path)) dangling.add(path);
    }
    if (dangling.size) F("links-resolve", `${dangling.size} dangling: ${[...dangling].slice(0, 5).join(", ")}`);
    else ok("links-resolve", `${checked} internal link(s)`);

    /* 8. Images and names. */
    const a11y = await page.evaluate(() => {
      const noAlt = [...document.querySelectorAll("img:not([alt])")].map((i) => i.getAttribute("src")?.slice(0, 80) ?? "?");
      const nameOf = (el) => {
        const lab = el.getAttribute("aria-label");
        if (lab && lab.trim()) return lab.trim();
        const by = el.getAttribute("aria-labelledby");
        if (by) { const t = by.split(/\s+/).map((id) => document.getElementById(id)?.textContent ?? "").join(" ").trim(); if (t) return t; }
        const text = (el.textContent ?? "").trim();
        if (text) return text;
        const img = el.querySelector("img[alt]"); if (img && img.getAttribute("alt").trim()) return img.getAttribute("alt");
        const svgT = el.querySelector("svg title"); if (svgT && svgT.textContent.trim()) return svgT.textContent;
        if (el.getAttribute("title")) return el.getAttribute("title");
        return "";
      };
      const unnamed = [];
      for (const el of document.querySelectorAll("a[href], button")) {
        if (el.closest("[hidden], [aria-hidden='true']")) continue;
        if (!nameOf(el)) {
          const cls = (el.className?.baseVal ?? el.className ?? "").toString().split(/\s+/)[0];
          unnamed.push(`${el.tagName.toLowerCase()}.${cls || "?"}`);
        }
      }
      return { noAlt, unnamed };
    });
    if (a11y.noAlt.length) F("img-alt", `${a11y.noAlt.length}: ${a11y.noAlt.slice(0, 3).join(", ")}`); else ok("img-alt");
    if (a11y.unnamed.length) F("accessible-names", `${a11y.unnamed.length}: ${[...new Set(a11y.unnamed)].slice(0, 5).join(", ")}`); else ok("accessible-names");

    /* 9. Dashes where the house cannot have them: attributes, chrome, dialogs
       and buttons always fail. The whole page is a warning in full mode,
       because a History quotation is allowed to carry what its source wrote. */
    const dashes = await page.evaluate(() => {
      const hits = [];
      const re = /[–—]/;
      for (const el of document.querySelectorAll("[aria-label]")) if (re.test(el.getAttribute("aria-label"))) hits.push(`aria-label: ${el.getAttribute("aria-label").slice(0, 60)}`);
      for (const el of document.querySelectorAll("img[alt]")) if (re.test(el.getAttribute("alt"))) hits.push(`alt: ${el.getAttribute("alt").slice(0, 60)}`);
      for (const el of document.querySelectorAll("[title]")) if (re.test(el.getAttribute("title"))) hits.push(`title attr: ${el.getAttribute("title").slice(0, 60)}`);
      for (const el of document.querySelectorAll(".nav-header, .site-footer, .mtb, .msp, [role='dialog'], button, .exp-banner")) {
        const t = el.innerText ?? el.textContent ?? "";
        if (re.test(t)) hits.push(`${el.className?.toString().split(/\s+/)[0] ?? el.tagName}: ${t.match(/.{0,30}[–—].{0,30}/)?.[0]}`);
      }
      const body = document.body.innerText ?? "";
      const bodyHits = (body.match(/.{0,30}[–—].{0,30}/g) ?? []).slice(0, 3);
      return { hits: [...new Set(hits)], bodyHits };
    });
    if (dashes.hits.length) F("no-dash", dashes.hits.slice(0, 3).join(" | ")); else ok("no-dash", "chrome, dialogs, attributes clean");
    if (dashes.bodyHits.length) warn("no-dash-body", dashes.bodyHits.join(" | "));

    /* 10. Invisible text: an element whose text colour equals the first
        painted background behind it, with no image in between. */
    const invisible = await page.evaluate(() => {
      const same = (a, b) => a === b;
      const bgOf = (el) => {
        let n = el;
        while (n && n !== document.documentElement) {
          const cs = getComputedStyle(n);
          if (cs.backgroundImage !== "none") return null;
          if (cs.backgroundColor && cs.backgroundColor !== "rgba(0, 0, 0, 0)" && cs.backgroundColor !== "transparent") return cs.backgroundColor;
          n = n.parentElement;
        }
        return getComputedStyle(document.documentElement).backgroundColor;
      };
      const out = [];
      let n = 0;
      for (const el of document.querySelectorAll("p, h1, h2, h3, h4, h5, h6, a, span, li, td, dt, dd, label, button, figcaption, small, time")) {
        if (n++ > 4000) break;
        if (el.children.length && !el.childNodes.length) continue;
        const text = [...el.childNodes].filter((c) => c.nodeType === 3).map((c) => c.textContent).join("").trim();
        if (!text) continue;
        const r = el.getBoundingClientRect();
        if (r.width === 0 || r.height === 0) continue;
        const cs = getComputedStyle(el);
        if (cs.visibility === "hidden" || cs.opacity === "0" || cs.display === "none") continue;
        if (cs.color === "rgba(0, 0, 0, 0)") continue;
        const bg = bgOf(el);
        if (bg && same(cs.color, bg)) {
          const cls = (el.className?.baseVal ?? el.className ?? "").toString().split(/\s+/)[0];
          out.push(`${el.tagName.toLowerCase()}.${cls || "?"} "${text.slice(0, 30)}" ${cs.color}`);
        }
      }
      return out;
    });
    if (invisible.length) F("invisible-text", `${invisible.length}: ${invisible.slice(0, 3).join(" | ")}`); else ok("invisible-text");

    /* 11. Focus order at 1440: Tab lands on the skip link, then the wordmark,
        and the first three tabbables show a visible focus ring. */
    if (width === 1440) {
      const seq = [];
      for (let i = 0; i < 3; i++) {
        await page.keyboard.press("Tab");
        seq.push(await page.evaluate(() => {
          const el = document.activeElement;
          if (!el || el === document.body) return { id: "body", ring: false };
          const cs = getComputedStyle(el);
          const ring = (cs.outlineStyle !== "none" && parseFloat(cs.outlineWidth) > 0 && !/rgba\(0, 0, 0, 0\)|transparent/.test(cs.outlineColor))
            || (cs.boxShadow && cs.boxShadow !== "none");
          const cls = (el.className?.baseVal ?? el.className ?? "").toString().split(/\s+/)[0];
          return { id: `${el.tagName.toLowerCase()}.${cls || el.id || "?"}`, ring };
        }));
      }
      const order = seq.map((s) => s.id).join(" > ");
      if (seq[0]?.id !== "a.skip-to-content") F("focus-order", `first Tab landed on ${seq[0]?.id}, not the skip link (${order})`);
      else if (seq[1]?.id !== "a.nav-logo") F("focus-order", `second Tab landed on ${seq[1]?.id}, not the wordmark (${order})`);
      else ok("focus-order", order);
      const noRing = seq.filter((s) => !s.ring).map((s) => s.id);
      if (noRing.length) F("focus-visible", `no visible ring on ${noRing.join(", ")}`); else ok("focus-visible");
    }

    /* 12. axe-core, WCAG 2.1 AA, at the two widths that matter most. */
    if (axeSource && (width === 390 || width === 1440)) {
      /* Let the entrances land first. Every feed card fades in from opacity 0
         over 260ms, and axe measures whatever opacity it catches: it read a
         lean label mid-entrance as #CB5A4F on #1C1A17, 4.22:1, when the label
         renders #EA6559 at 5.4:1 the moment the card settles. That is the
         animation, not the palette, and any coloured text on any fading card
         would report it. Finite animations only, or the wordmark's beam and
         the unscored pulse never resolve. */
      await page.evaluate(() => Promise.race([
        Promise.all(document.getAnimations()
          .filter((a) => a.effect?.getTiming?.().iterations !== Infinity)
          .map((a) => a.finished.catch(() => {}))),
        new Promise((r) => setTimeout(r, 2500)),
      ])).catch(() => {});
      await page.addScriptTag({ content: axeSource });
      const raw = await page.evaluate(async () => {
        const r = await window.axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] }, resultTypes: ["violations"] });
        return r.violations.map((v) => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.map((n) => ({ target: n.target.join(" "), html: n.html.slice(0, 160), data: n.any?.[0]?.data ?? null })) }));
      });
      /* The allowlist is applied per NODE, so an exempt logotype beside a
         real finding hides only itself. */
      const axe = raw.map((v) => {
        const nodes = v.nodes.filter((n) => {
          const a = allowed("axe", route, `${v.id} ${n.target} ${n.html}`);
          if (a) results.push({ where: current, check: "axe", status: "allowed", detail: `${v.id} ${n.target.slice(0, 80)}`, reason: a.reason });
          return !a;
        });
        const first = nodes[0];
        const colour = first?.data?.contrastRatio ? ` ${first.data.fgColor} on ${first.data.bgColor} = ${first.data.contrastRatio}` : "";
        return { id: v.id, impact: v.impact, n: nodes.length, target: (first?.target ?? "") + colour, help: v.help };
      }).filter((v) => v.n > 0);
      const serious = axe.filter((v) => v.impact === "critical" || v.impact === "serious");
      const lesser = axe.filter((v) => !(v.impact === "critical" || v.impact === "serious"));
      for (const v of serious) F("axe", `${v.id} (${v.impact}, ${v.n} node${v.n === 1 ? "" : "s"}) ${v.help}; first: ${v.target.slice(0, 220)}`);
      if (!serious.length) ok("axe", `no critical or serious violations${lesser.length ? `, ${lesser.length} lesser` : ""}`);
      for (const v of lesser) warn("axe-lesser", `${v.id} (${v.impact}, ${v.n}) ${v.help}`);
    }
  } catch (e) {
    F("exception", String(e?.message ?? e).slice(0, 300));
  } finally {
    if (failed) await shot(page, current);
    await context.close();
  }
}

/* ── Scenarios ──────────────────────────────────────────────────────────── */
async function withPage(browser, opts, name, fn) {
  ctx(opts.route ?? "/", opts.width, opts.scheme ?? "dark");
  console.log(`\nscenario: ${name} (${current})`);
  const { context, page, log } = await openPage(browser, { scheme: "dark", ...opts });
  const before = failures.length;
  try { await fn(page, log, context); }
  catch (e) { fail("exception", `${name}: ${String(e?.message ?? e).slice(0, 300)}`); }
  finally {
    if (failures.length > before) await shot(page, `scenario ${name} ${current}`);
    await context.close();
  }
}

function hexOf(rgb) {
  const m = rgb.match(/\d+(\.\d+)?/g);
  if (!m || m.length < 3) return rgb;
  return "#" + m.slice(0, 3).map((n) => Math.round(Number(n)).toString(16).padStart(2, "0")).join("").toUpperCase();
}

async function scenarios(browser) {
  /* Deep Dive, desktop: inline under the card. */
  await withPage(browser, { width: 1440, route: "/" }, "deep-dive-inline", async (page) => {
    await page.locator("[data-story-index='0'] .story-card__stretch-link, .lead-story a.story-card__stretch-link, .story-card__stretch-link").first().click();
    const inline = page.locator(".inline-dd");
    await inline.first().waitFor({ state: "visible", timeout: 5000 }).catch(() => {});
    assert(await inline.count() > 0, "deep-dive-inline-opens", "click on the first card renders .inline-dd");
    assert(await page.locator(".dd-page").count() === 0, "deep-dive-inline-not-page", "no full-page Deep Dive at 1440");
  });
  /* The Bench: the Deep Dive's lean panel. One mark per source, seated in the
     column of its lean rung, and the HEIGHT of a column is the count in that
     bucket. That last claim is the only one the panel makes, and the first
     draft of the packing broke it (a bucket of 1, 2, 3, 4 and 5 all drew one
     row), so it is asserted here against the served page as well as in
     test/bench.test.mjs against the arithmetic. */
  for (const width of [1440, 390]) {
    await withPage(browser, { width, route: "/" }, `bench @${width}`, async (page) => {
      await page.locator("[data-story-index='0'] .story-card__stretch-link, .lead-story a.story-card__stretch-link, .story-card__stretch-link").first().click();
      const bench = page.locator(".bench").first();
      await bench.waitFor({ state: "visible", timeout: 8000 }).catch(() => {});
      if (!assert(await page.locator(".bench").count() > 0, `bench-renders`, "the Deep Dive draws a Bench")) return;
      /* The columns rise off the rule on a 40ms stagger, so the last one is
         still moving ~240ms in. Measuring or hovering through that reads a
         mark where it is passing rather than where it lands. */
      await page.waitForTimeout(800);
      const read = await page.evaluate(() => {
        const b = document.querySelector(".bench");
        const cols = [...b.querySelectorAll(".bench__col")];
        const colOf = (c) => {
          const rows = [...c.querySelectorAll(".bench__row")];
          if (!rows.length) return 0;
          const top = Math.min(...rows.map((r) => r.getBoundingClientRect().top));
          const bot = Math.max(...rows.map((r) => r.getBoundingClientRect().bottom));
          return Math.round(bot - top);
        };
        const disc = b.querySelector(".bench__disc");
        const d = disc ? disc.getBoundingClientRect() : null;
        return {
          columns: cols.length,
          tallies: cols.map((c) => Number(c.querySelector(".bench__tally").textContent)),
          drawn: cols.map((c) => c.querySelectorAll(".bench__mark").length),
          more: cols.map((c) => {
            const m = c.querySelector(".bench__more");
            return m ? Number(m.textContent.replace("+", "")) : 0;
          }),
          heights: cols.map(colOf),
          shape: b.querySelector(".bench__shape")?.textContent ?? "",
          count: b.querySelector(".bench__count")?.textContent ?? "",
          markBox: d ? [Math.round(d.width), Math.round(d.height)] : null,
          markRadius: disc ? getComputedStyle(disc).borderRadius : "",
          markSizes: [...b.querySelectorAll(".bench__disc")].map((e) => Math.round(e.getBoundingClientRect().width)),
          overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        };
      });
      assert(read.columns === 7, "bench-seven-columns", `${read.columns} columns, one per lean rung`);
      /* Nothing is dropped without saying so: every source is either drawn or
         counted in its column's overflow chip. */
      const accounted = read.tallies.every((t, i) => read.drawn[i] + read.more[i] === t);
      assert(accounted, "bench-nothing-dropped", `tallies ${read.tallies.join("/")} vs drawn ${read.drawn.join("/")} + more ${read.more.join("/")}`);
      /* The headline claim. Sort the columns by count and require the heights
         to rise with them: a bigger bucket is never a shorter column, and the
         busiest bucket is strictly taller than the emptiest non-zero one. */
      const pairs = read.tallies.map((t, i) => [t, read.heights[i]]).sort((a, b) => a[0] - b[0]);
      assert(pairs.every((p, i) => i === 0 || p[1] >= pairs[i - 1][1]), "bench-height-is-the-count",
        `counts ${pairs.map((p) => p[0]).join("/")} -> heights ${pairs.map((p) => p[1]).join("/")}`);
      const nonzero = pairs.filter((p) => p[0] > 0);
      if (nonzero.length > 1 && nonzero[nonzero.length - 1][0] > nonzero[0][0]) {
        assert(nonzero[nonzero.length - 1][1] > nonzero[0][1], "bench-busiest-stands-tallest",
          `${nonzero[0][0]} -> ${nonzero[0][1]}px, ${nonzero[nonzero.length - 1][0]} -> ${nonzero[nonzero.length - 1][1]}px`);
      }
      /* One mark size for the whole story, or the heights are not comparable. */
      assert(new Set(read.markSizes).size === 1, "bench-one-mark-size", `sizes ${[...new Set(read.markSizes)].join(",")}`);
      assert(read.markBox && read.markBox[0] === read.markBox[1] && read.markRadius.startsWith("50%"),
        "bench-marks-are-circles", `${read.markBox?.join("x")} radius ${read.markRadius}`);
      /* The panel counts what it seated, and says out loud what it held back. */
      const placed = Number((read.count.match(/^(\d+)/) ?? [])[1] ?? -1);
      assert(placed === read.tallies.reduce((a, b) => a + b, 0), "bench-count-agrees",
        `"${read.count}" vs tallies summing to ${read.tallies.reduce((a, b) => a + b, 0)}`);
      assert(read.overflow <= 0, "bench-no-overflow", `${read.overflow}px past the viewport`);
      /* A mark names its source. On a phone the marks are buttons, so press;
         on a desktop they are links, so hover. */
      const mark = page.locator(".bench__mark").first();
      const label = await mark.getAttribute("aria-label");
      await mark.scrollIntoViewIfNeeded();
      await page.waitForTimeout(200);
      if (width === 390) await mark.click(); else await mark.hover();
      await page.waitForTimeout(500);
      const card = await page.evaluate(() => {
        const c = document.querySelector(".bench__card");
        if (!c) return null;
        const r = c.getBoundingClientRect();
        const sib = [...document.querySelectorAll(".bench__mark")].find((m) => m.dataset.focused !== "true");
        return {
          name: c.querySelector(".bench__card-name")?.textContent ?? "",
          text: c.innerText,
          onscreen: r.left >= -1 && r.top >= -1 && r.right <= innerWidth + 1,
          siblingOpacity: sib ? Number(getComputedStyle(sib).opacity) : 1,
        };
      });
      if (assert(card != null, "bench-mark-names-its-source", "a card appears")) {
        assert(label.startsWith(card.name), "bench-card-is-that-mark", `"${card.name}" vs aria-label "${label}"`);
        assert(/Open article/.test(card.text), "bench-card-opens-the-article", card.text.replace(/\n/g, " | ").slice(0, 120));
        assert(card.onscreen, "bench-card-onscreen", "the card sits inside the viewport");
        assert(card.siblingOpacity < 0.6, "bench-rack-focus", `siblings at ${card.siblingOpacity}`);
      }
    });
  }
  /* Every lean label on the feed clears AA against the paper it sits on.
     The bias tokens are tuned to clear it at FULL strength and nothing more
     (--bias-far-right is 4.7:1 on the dark paper), so any opacity fade on the
     label spends the whole margin: at 0.75 --bias-right rendered #C75F52,
     4.28:1, and shipped that way until the register started speaking on 30 of
     35 stories and axe happened to sample a card carrying it. axe samples;
     this measures all twenty. */
  for (const scheme of ["dark", "light"]) {
    await withPage(browser, { width: 1440, route: "/", scheme }, `lean-label-contrast ${scheme}`, async (page) => {
      /* Settled state only. Every card fades in from opacity 0 over 260ms and
         a colour measured through that fade is the animation, not the
         palette. Finite animations only, or the wordmark's beam never ends. */
      await page.evaluate(() => Promise.race([
        Promise.all(document.getAnimations()
          .filter((a) => a.effect?.getTiming?.().iterations !== Infinity)
          .map((a) => a.finished.catch(() => {}))),
        new Promise((r) => setTimeout(r, 2500)),
      ])).catch(() => {});
      const rows = await page.evaluate(() => {
        /* getComputedStyle hands back rgb(), rgba() OR color(srgb a b c) here,
           because the lean colour is a color-mix() of two tokens and Chromium
           serialises that in the srgb colour space with 0..1 channels. Reading
           all three shapes with one "first three numbers" regex multiplied
           every mixed colour by 255 and produced ratios like 1.21:1. */
        const chan = (str) => {
          const nums = (str.match(/-?\d*\.?\d+(e[-+]?\d+)?/gi) ?? []).map(Number);
          if (nums.length < 3) return null;
          const [a, b, c] = nums;
          return /^color\(/i.test(str.trim())
            ? [a * 255, b * 255, c * 255]
            : [a, b, c];
        };
        const lum = (ch) => {
          const [r, g, b] = ch.map((v) => {
            const c = Math.min(255, Math.max(0, v)) / 255;
            return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
          });
          return 0.2126 * r + 0.7152 * g + 0.0722 * b;
        };
        const paperOf = (el) => {
          for (let n = el; n; n = n.parentElement) {
            const bg = getComputedStyle(n).backgroundColor;
            const a = bg.match(/-?\d*\.?\d+/g);
            if (a && (a.length < 4 || Number(a[3]) > 0.9)) return bg;
          }
          /* Every ancestor is transparent on the feed, so the paper is the
             body's. documentElement is not it: it is transparent too, and
             falling through to it returned the UA default white and read the
             dark mode as a light one. */
          const b = getComputedStyle(document.body).backgroundColor;
          const a = b.match(/-?\d*\.?\d+/g);
          return a && (a.length < 4 || Number(a[3]) > 0.9)
            ? b : getComputedStyle(document.documentElement).backgroundColor;
        };
        return [...document.querySelectorAll(".sigil__lean-label")].map((el) => {
          const cs = getComputedStyle(el);
          const op = Number(cs.opacity);
          const fg = chan(cs.color);
          const bg = chan(paperOf(el));
          if (!fg || !bg) return { text: el.textContent.trim().slice(0, 24), ratio: -1, op, raw: cs.color };
          /* Flatten the element's own opacity onto its paper, which is what
             the reader's eye receives. */
          const mixed = fg.map((c, i) => c * op + bg[i] * (1 - op));
          const L1 = lum(mixed);
          const L2 = lum(bg);
          const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
          return { text: el.textContent.trim().slice(0, 24), ratio: Math.round(ratio * 100) / 100, op, raw: cs.color };
        });
      });
      if (!assert(rows.length > 0, "lean-label-present", "the feed carries lean labels")) return;
      const bad = rows.filter((r) => r.ratio < 4.5);
      assert(bad.length === 0, "lean-label-contrast",
        bad.length ? bad.slice(0, 4).map((r) => `"${r.text}" ${r.ratio}:1 (${r.raw}) at opacity ${r.op}`).join("; ")
                   : `${rows.length} labels, lowest ${Math.min(...rows.map((r) => r.ratio))}:1`);
    });
  }

  /* Deep Dive, phone: the full page, and Back returns to the feed. */
  await withPage(browser, { width: 390, route: "/" }, "deep-dive-page", async (page) => {
    await page.locator("[data-story-index='0'] .story-card__stretch-link, .story-card__stretch-link").first().click();
    const dd = page.locator(".dd-page");
    await dd.first().waitFor({ state: "visible", timeout: 5000 }).catch(() => {});
    if (!assert(await dd.count() > 0, "deep-dive-page-opens", "tap on the first card renders .dd-page")) return;
    assert(await page.locator(".nav-header").count() === 1, "deep-dive-page-masthead", "the one masthead stays mounted");
    await page.locator(".dd-page__back").first().click();
    await page.locator(".dd-page").first().waitFor({ state: "detached", timeout: 5000 }).catch(() => {});
    assert(await page.locator(".dd-page").count() === 0 && await page.locator("[data-story-index]").count() > 0, "deep-dive-page-back", "Back to feed restores the cards");
  });
  /* Search: the shortcut, the masthead button, and the slash. */
  await withPage(browser, { width: 1440, route: "/" }, "search", async (page) => {
    await page.keyboard.press("Control+k");
    const overlay = page.locator(".search-overlay[role='dialog']");
    await overlay.waitFor({ state: "visible", timeout: 3000 }).catch(() => {});
    assert(await overlay.isVisible().catch(() => false), "search-ctrl-k", "Ctrl+K opens the search dialog");
    assert(await page.evaluate(() => document.activeElement?.classList.contains("search-overlay__input")), "search-focus", "focus lands in the input");
    await page.keyboard.press("Escape");
    await page.waitForTimeout(400);
    assert(!(await overlay.isVisible().catch(() => false)), "search-escape", "Escape closes it");
    await page.locator(".nav-search-btn").click();
    await overlay.waitFor({ state: "visible", timeout: 3000 }).catch(() => {});
    assert(await overlay.isVisible().catch(() => false), "search-masthead-button", "the masthead button opens it");
    await page.keyboard.press("Escape");
    await page.waitForTimeout(400);
    await page.keyboard.press("/");
    await overlay.waitFor({ state: "visible", timeout: 3000 }).catch(() => {});
    assert(await overlay.isVisible().catch(() => false), "search-slash", "/ opens it (the shortcut the overlay lists)");
  });
  /* Theme: the toggle flips the mode and both theme-color metas follow the
     masthead's real background, in every section. */
  for (const route of ["/", "/history/", "/weekly/"]) {
    await withPage(browser, { width: 1440, route }, `theme-toggle ${route}`, async (page) => {
      const read = () => page.evaluate(() => ({
        mode: document.documentElement.getAttribute("data-mode"),
        metas: [...document.querySelectorAll("meta[name='theme-color']")].map((m) => m.getAttribute("content").toUpperCase()),
        nav: getComputedStyle(document.querySelector(".nav-header")).backgroundColor,
        html: getComputedStyle(document.documentElement).backgroundColor,
      }));
      const a = await read();
      assert(a.mode === "dark", "theme-initial", `data-mode=${a.mode} from localStorage`);
      const dark = hexOf(a.nav === "rgba(0, 0, 0, 0)" ? a.html : a.nav);
      /* Before any toggle the two metas are the served pair, one per media
         query; the one for the current scheme must be the masthead's paper.
         After a toggle both are rewritten to the new paper. */
      assert(a.metas.length === 2 && a.metas.includes(dark), "theme-color-dark", `metas ${a.metas.join(",")} include masthead ${dark}`);
      await page.locator(".nav-header .theme-toggle:not(.theme-toggle--placeholder)").first().click();
      await page.waitForTimeout(500);
      const b = await read();
      assert(b.mode === "light", "theme-toggle-flips", `data-mode=${b.mode}`);
      const light = hexOf(b.nav === "rgba(0, 0, 0, 0)" ? b.html : b.nav);
      assert(b.metas.length === 2 && b.metas.every((m) => m === light), "theme-color-light", `metas ${b.metas.join(",")} vs masthead ${light}`);
      assert(await page.evaluate(() => localStorage.getItem("void-news-theme")) === "light", "theme-persists", "localStorage carries the choice");
    });
  }
  /* One lean word per story (2026-09-26). The card printed the roster's word
     while its aria-label and popup heading read the gated mean, so a card
     showing "Leans left" was announced as "Not measured". All three must be
     the same word on every card. */
  await withPage(browser, { width: 1440, route: "/" }, "lean-word-one-rule", async (page) => {
    const rows = await page.evaluate(() => [...document.querySelectorAll(".sigil[role='button']")].map((el) => ({
      aria: (el.getAttribute("aria-label") ?? "").match(/^Coverage: (.+?)\. \d+ sources?\./)?.[1] ?? `(unparsed) ${el.getAttribute("aria-label")}`,
      printed: el.querySelector(".sigil__lean-label")?.textContent?.trim() ?? "",
    })));
    if (!assert(rows.length > 0, "lean-word-present", "the feed carries Sigils")) return;
    const bad = rows.filter((r) => r.aria !== r.printed);
    assert(bad.length === 0, "lean-word-aria", bad.length
      ? bad.slice(0, 4).map((r) => `printed "${r.printed}" but aria says "${r.aria}"`).join("; ")
      : `${rows.length} Sigils, aria-label = printed word`);
    const popupBad = [];
    for (let i = 0; i < Math.min(4, rows.length); i++) {
      await page.locator(".sigil[role='button']").nth(i).hover();
      await page.waitForSelector(".sigil-popup__label", { timeout: 2000 }).catch(() => {});
      const heading = (await page.locator(".sigil-popup__label").first().textContent().catch(() => ""))?.trim();
      if (heading !== rows[i].printed) popupBad.push(`card ${i}: printed "${rows[i].printed}", popup "${heading}"`);
      await page.mouse.move(2, 2);
      await page.waitForTimeout(250);
    }
    assert(popupBad.length === 0, "lean-word-popup", popupBad.length ? popupBad.join("; ") : "popup heading = printed word on the first four cards");
  });
  /* The Menu drawer's edition time is the masthead's (2026-09-26). It fell
     back to the reader's clock and printed "Edition as of 2:00 AM" under a
     masthead reading "as of 6:00 PM". */
  await withPage(browser, { width: 390, route: "/" }, "drawer-edition-time", async (page) => {
    const mast = (await page.locator(".nav-dateline-line__time").first().textContent().catch(() => ""))?.replace(/^\s*as of\s*/i, "").trim();
    await page.locator("button[aria-label='Menu']").first().click();
    await page.waitForSelector(".msp--open", { timeout: 3000 }).catch(() => {});
    const line = (await page.locator(".msp__info-line").first().textContent().catch(() => ""))?.trim() ?? "";
    const drawer = line.replace(/^Edition as of\s*/i, "").trim();
    assert(!!mast && drawer === mast, "drawer-edition-time", `masthead "${mast}", drawer "${line}"`);
  });
  /* Without JavaScript every story is still on the page (2026-09-26). Cards
     enter at opacity 0 and a client hook lifts them; with no script 18 of 20
     stayed invisible. */
  {
    ctx("/", 1440, "light");
    console.log(`\nscenario: no-js-cards-visible (${current})`);
    const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, javaScriptEnabled: false });
    const page = await context.newPage();
    try {
      await page.goto(`${ORIGIN}${BASE}/`, { waitUntil: "load", timeout: 60_000 });
      const ops = await page.evaluate(() => [...document.querySelectorAll("article")].map((a) => Number(getComputedStyle(a).opacity)));
      const hidden = ops.filter((o) => o < 0.99).length;
      assert(ops.length > 0 && hidden === 0, "no-js-cards-visible", `${ops.length - hidden} of ${ops.length} cards visible with scripting off`);
    } catch (e) { fail("exception", `no-js-cards-visible: ${String(e?.message ?? e).slice(0, 300)}`); }
    finally { await context.close(); }
  }
  /* The drawer traps focus and gives it back. */
  await withPage(browser, { width: 390, route: "/" }, "drawer", async (page) => {
    const btn = page.locator("button[aria-label='Menu']").first();
    await btn.click();
    const isOpen = () => page.evaluate(() => document.querySelector(".msp[role='dialog']")?.classList.contains("msp--open") ?? false);
    await page.waitForSelector(".msp--open", { timeout: 3000 }).catch(() => {});
    if (!assert(await isOpen(), "drawer-opens", "Menu opens the side panel (.msp--open)")) return;
    let escaped = null;
    for (let i = 0; i < 12; i++) {
      await page.keyboard.press("Tab");
      const inside = await page.evaluate(() => !!document.activeElement?.closest(".msp"));
      if (!inside) { escaped = await page.evaluate(() => document.activeElement?.className?.toString()); break; }
    }
    assert(escaped === null, "drawer-focus-trap", escaped === null ? "12 Tabs stayed inside" : `focus escaped to ${escaped}`);
    await page.keyboard.press("Escape");
    await page.waitForTimeout(500);
    assert(!(await isOpen()), "drawer-escape", "Escape closes it");
    assert(await page.evaluate(() => document.activeElement?.getAttribute("aria-label") === "Menu"), "drawer-restores-focus", "focus returns to the Menu button");
  });
  /* The Sigil: hover opens, and the popup it points at exists. */
  await withPage(browser, { width: 1440, route: "/" }, "sigil", async (page) => {
    const sigil = page.locator(".sigil[role='button']").first();
    await sigil.hover({ force: true });
    await page.waitForTimeout(400);
    const s = await page.evaluate(() => {
      const el = document.querySelector(".sigil[role='button']");
      const id = el?.getAttribute("aria-controls");
      return { expanded: el?.getAttribute("aria-expanded"), id, resolves: !!(id && document.getElementById(id)) };
    });
    assert(s.expanded === "true", "sigil-hover-expands", `aria-expanded=${s.expanded}`);
    assert(s.resolves, "sigil-aria-controls", `aria-controls=${s.id} ${s.resolves ? "resolves" : "does not resolve"}`);
  });
  /* The shortcuts overlay tells the truth about the keys that work. */
  await withPage(browser, { width: 1440, route: "/" }, "shortcuts", async (page) => {
    await page.keyboard.press("?");
    const ov = page.locator(".kbd-overlay");
    await ov.waitFor({ state: "visible", timeout: 3000 }).catch(() => {});
    if (!assert(await ov.isVisible().catch(() => false), "shortcuts-opens", "? opens the overlay")) return;
    const keys = await page.evaluate(() => [...document.querySelectorAll(".kbd-overlay__key")].map((k) => k.textContent.trim()));
    assert(keys.includes("O"), "shortcuts-lists-o", `keys: ${keys.join(" ")}`);
    assert(keys.includes("/"), "shortcuts-lists-slash", `keys: ${keys.join(" ")}`);
    await page.keyboard.press("Escape");
    await page.waitForTimeout(300);
    assert(!(await ov.isVisible().catch(() => false)), "shortcuts-escape", "Escape closes it");
    /* j and k move the keyboard focus ring down and up the feed. */
    const focusedIndex = () => page.evaluate(() => {
      const el = document.querySelector(".story-card--kbd-focus");
      if (!el) return null;
      /* Story cards carry data-story-index; the lead cards do not, and their
         index is their position among the leads (rank 0, then the twin). */
      return el.getAttribute("data-story-index")
        ?? (el.classList.contains("lead-story") ? String([...document.querySelectorAll(".lead-story")].indexOf(el)) : "?");
    });
    await page.keyboard.press("j");
    await page.waitForTimeout(200);
    const first = await focusedIndex();
    await page.keyboard.press("j");
    await page.waitForTimeout(200);
    const second = await focusedIndex();
    await page.keyboard.press("k");
    await page.waitForTimeout(200);
    const third = await focusedIndex();
    assert(first === "0" && second === "1" && third === "0", "j-k-navigation", `j -> ${first}, j -> ${second}, k -> ${third}`);
  });
  /* The experimental banner: not on the first visit, present on the second. */
  await withPage(browser, { width: 1440, route: "/" }, "banner-first-visit", async (page) => {
    assert(await page.locator(".exp-banner").count() === 0, "banner-absent-first-visit", "no banner on a first visit");
  });
  await withPage(browser, { width: 1440, route: "/", storage: { "void-exp-banner-visits": "1" } }, "banner-second-visit", async (page) => {
    const b = page.locator(".exp-banner");
    await b.waitFor({ state: "visible", timeout: 3000 }).catch(() => {});
    if (assert(await b.count() > 0, "banner-present-second-visit", "banner on the second visit")) {
      const below = await page.evaluate(() => {
        const nav = document.querySelector(".nav-header")?.getBoundingClientRect();
        const ban = document.querySelector(".exp-banner")?.getBoundingClientRect();
        return nav && ban && ban.top >= nav.bottom - 1;
      });
      assert(!!below, "banner-below-masthead", "the banner sits under the masthead, not above it");
      assert(!(await page.evaluate(() => /[–—]/.test(document.querySelector(".exp-banner")?.textContent ?? ""))), "banner-no-dash");
      await page.locator(".exp-banner__dismiss").click();
      await page.waitForTimeout(300);
      assert(await page.locator(".exp-banner").count() === 0, "banner-dismiss", "dismiss removes it");
    }
  });
  /* The floating player: on the news, Audio and Weekly pages; not on Ship,
     not on History (the event page carries its own Listen), and NOT on /onair,
     where the page's own portal is the transport. It used to appear there too,
     so at 1440 two transports showed the same episode through two
     implementations. See the no-double-transport scenario. */
  for (const [route, expect] of [["/", true], ["/onair/", false], ["/audio/", true], ["/weekly/", true], ["/ship/", false], ["/history/", false]]) {
    await withPage(browser, { width: 1440, route }, `floating-player ${route}`, async (page) => {
      await page.waitForTimeout(500);
      const n = await page.locator(".fp").count();
      assert((n > 0) === expect, "floating-player", `${route}: ${n} .fp, expected ${expect ? "present" : "absent"}`);
    });
  }
  /* Paper carries the front page's twenty, in order (the same extraction
     tests/test_paper.py uses, so this fails if either page renames its class). */
  ctx("/paper/", 0, "fs");
  console.log(`\nscenario: paper-parity`);
  try {
    const home = readFileSync(join(OUT, "index.html"), "utf8");
    const paper = readFileSync(join(OUT, "paper/index.html"), "utf8");
    const HOME_RE = /class="(?:lead-headline__text|lead-story__headline-text|story-card__headline-text)"[^>]*>([^<]*)</g;
    const PAPER_RE = /class="np-article__headline-text"[^>]*>([^<]*)</g;
    const decode = (s) => s.replace(/&#x27;|&rsquo;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").trim();
    const h = [...home.matchAll(HOME_RE)].map((m) => decode(m[1]));
    const p = [...paper.matchAll(PAPER_RE)].map((m) => decode(m[1]));
    const uniqueHome = [...new Set(h)];
    assert(p.length === 20, "paper-twenty", `${p.length} headlines on Paper`);
    assert(uniqueHome.length >= 20 && p.every((t, i) => t === uniqueHome[i]), "paper-order", p.every((t, i) => t === uniqueHome[i]) ? "same twenty, same order" : `first divergence at ${p.findIndex((t, i) => t !== uniqueHome[i])}`);
  } catch (e) { fail("paper-parity", String(e?.message ?? e)); }

  await journeys(browser);
  await brandChecks(browser);
}

/* ── Journeys, round two: the elements the first round did not touch. ── */
async function journeys(browser) {
  /* Search, to the end: type, get results, choose one, read it. */
  await withPage(browser, { width: 1440, route: "/" }, "search-select", async (page) => {
    const word = await page.evaluate(() => (document.querySelector(".lead-headline__text, .lead-story__headline-text, .story-card__headline-text")?.textContent ?? "").trim().split(/\s+/).find((w) => w.length > 4) ?? "");
    if (!word) { skip("search-select", "no headline word to search for"); return; }
    await page.keyboard.press("Control+k");
    await page.locator(".search-overlay__input").waitFor({ state: "visible", timeout: 3000 });
    await page.locator(".search-overlay__input").fill(word);
    await page.waitForTimeout(600);
    const n = await page.locator(".search-overlay__result").count();
    if (!assert(n > 0, "search-results", `"${word}" returns ${n} result(s)`)) return;
    await page.keyboard.press("Enter");
    await page.waitForTimeout(800);
    const opened = await page.evaluate(() => ({ overlay: !!document.querySelector(".search-overlay"), inline: !!document.querySelector(".inline-dd"), page: !!document.querySelector(".dd-page") }));
    assert(!opened.overlay && (opened.inline || opened.page), "search-select-opens", `Enter on the first result: overlay ${opened.overlay ? "still open" : "closed"}, Deep Dive ${opened.inline ? "inline" : opened.page ? "page" : "absent"}`);
  });
  /* Share from the phone Deep Dive falls back to the clipboard with the permalink. */
  await withPage(browser, { width: 390, route: "/", permissions: ["clipboard-read", "clipboard-write"] }, "deep-dive-share", async (page) => {
    await page.locator("[data-story-index='0'] .story-card__stretch-link, .story-card__stretch-link").first().click();
    await page.locator(".dd-page").first().waitFor({ state: "visible", timeout: 5000 }).catch(() => {});
    if (await page.locator(".dd-page__share").count() === 0) { skip("deep-dive-share", "no share button on this page"); return; }
    await page.locator(".dd-page__share").first().click();
    await page.waitForTimeout(500);
    const text = await page.evaluate(() => navigator.clipboard.readText().catch(() => ""));
    assert(/\/story\/[0-9a-f-]+/.test(text), "deep-dive-share", `clipboard: ${JSON.stringify(text.slice(0, 80))}`);
  });
  /* History: the landing's long-view toggle, and the event's Listen island. */
  await withPage(browser, { width: 1440, route: "/history/" }, "history-longview", async (page) => {
    const btns = page.locator(".hist-longview-toggle__btn");
    if (await btns.count() < 2) { skip("history-longview", "no toggle on the landing"); return; }
    await btns.nth(1).click();
    await page.waitForTimeout(500);
    const state = await page.evaluate(() => [...document.querySelectorAll(".hist-longview-toggle__btn")].map((b) => b.classList.contains("hist-longview-toggle__btn--active")));
    assert(state[1] === true && state[0] === false, "history-longview", `active after clicking the second: ${state.join(",")}`);
  });
  await withPage(browser, { width: 1440, route: "/history/partition-of-india/" }, "hearing-listen", async (page) => {
    if (await page.locator(".hist-hero-listen").count() === 0) { skip("hearing-listen", "no Listen island on this event"); return; }
    await page.locator(".hist-hero-listen").first().click();
    await page.waitForTimeout(1200);
    const title = await page.evaluate(() => document.querySelector(".fp__title")?.textContent?.trim() ?? null);
    assert(title === "History", "hearing-listen", `player title after Listen: ${title}`);
  });
  /* Weekly offers The Argument to an idle player on arrival, and the player
     names the PROGRAMME. It used to read "Weekly", the section, because the
     label was a constant picked from which slot had been written last. */
  await withPage(browser, { width: 1440, route: "/weekly/" }, "weekly-argument", async (page) => {
    await page.waitForTimeout(1200);
    const title = await page.evaluate(() => document.querySelector(".fp__title")?.textContent?.trim() ?? null);
    assert(title === "The Argument", "weekly-argument-loaded", `player title on the issue: ${title}`);
  });
  /* Sources: the picker and the six-axis dots. */
  await withPage(browser, { width: 1440, route: "/sources/" }, "sources-picker", async (page) => {
    const rows = page.locator(".meth-picker__row");
    if (await rows.count() < 2) { skip("sources-picker", "fewer than two picker rows"); return; }
    await rows.nth(1).click();
    await page.waitForTimeout(500);
    assert(await rows.nth(1).evaluate((el) => el.classList.contains("meth-picker__row--active")), "sources-picker-select", "the second row becomes active");
    const dot = page.locator(".meth-dot").first();
    await dot.click();
    await page.waitForTimeout(500);
    const d = await page.evaluate(() => { const b = document.querySelector(".meth-dot"); const id = b?.getAttribute("aria-controls"); return { expanded: b?.getAttribute("aria-expanded"), open: !!document.querySelector(".meth-dot-detail--open"), resolves: !!(id && document.getElementById(id)) }; });
    assert(d.expanded === "true" && d.open && d.resolves, "sources-dot-detail", `aria-expanded ${d.expanded}, detail open ${d.open}, aria-controls resolves ${d.resolves}`);
  });
  /* About: the Sigil demo answers its sliders. */
  await withPage(browser, { width: 1440, route: "/about/" }, "about-demo", async (page) => {
    const slider = page.locator("input[aria-label='Political lean']");
    if (await slider.count() === 0) { skip("about-demo", "no lean slider"); return; }
    const before = await page.evaluate(() => document.querySelector(".sigdemo__readout dd")?.textContent ?? "");
    await slider.evaluate((el) => { const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set; set.call(el, "12"); el.dispatchEvent(new Event("input", { bubbles: true })); el.dispatchEvent(new Event("change", { bubbles: true })); });
    await page.waitForTimeout(400);
    const after = await page.evaluate(() => document.querySelector(".sigdemo__readout dd")?.textContent ?? "");
    assert(after !== before && after.length > 0, "about-demo", `lean readout ${JSON.stringify(before)} -> ${JSON.stringify(after)}`);
  });
  /* Feedback: an empty submit is refused in the page, not on the wire. */
  await withPage(browser, { width: 1440, route: "/ship/" }, "feedback-empty-submit", async (page, log) => {
    if (await page.locator(".fb-submit").count() === 0) { skip("feedback-empty-submit", "no form on /ship/"); return; }
    const posts = [];
    page.on("request", (r) => { if (r.method() === "POST") posts.push(r.url()); });
    await page.locator(".fb-submit").first().click();
    await page.waitForTimeout(600);
    const errors = await page.locator(".fb-field-error:visible").count();
    assert(errors >= 1 && posts.length === 0, "feedback-empty-submit", `${errors} field error(s) shown, ${posts.length} POST(s) sent`);
  });
  /* The files an app or a crawler asks for by name. */
  ctx("/", 0, "fs");
  console.log(`\nscenario: static-files`);
  for (const f of ["podcast-world.xml", "podcast-weekly.xml", "podcast-history.xml"]) {
    const path = join(OUT, f);
    const head = existsSync(path) ? readFileSync(path, "utf8").slice(0, 400) : "";
    assert(/<rss[\s>]/.test(head) && /<channel>/.test(head), `static-${f}`, existsSync(path) ? "rss with a channel" : "missing");
  }
  try { const m = JSON.parse(readFileSync(join(OUT, "manifest.json"), "utf8")); assert(!!m.name && Array.isArray(m.icons) && m.icons.length > 0, "static-manifest", `${m.name}, ${m.icons?.length ?? 0} icon(s)`); } catch (e) { fail("static-manifest", String(e?.message ?? e)); }
  assert(existsSync(join(OUT, "sw.js")) && existsSync(join(OUT, "offline.html")), "static-sw", "sw.js and offline.html present");
  const robots = existsSync(join(OUT, "robots.txt")) ? readFileSync(join(OUT, "robots.txt"), "utf8") : "";
  assert(/Sitemap:/.test(robots) && /Disallow: \/admin/.test(robots), "static-robots", "sitemap named, /admin disallowed");
}

/* ── Brand checks: the subtle layer, each one a token-driven touch a reader
   feels rather than notices, asserted so they cannot quietly rot. ── */
async function brandChecks(browser) {
  /* 404: an h1, the right title, and a way into every section. */
  await withPage(browser, { width: 1440, route: NOT_FOUND_ROUTE }, "not-found", async (page) => {
    assert(await page.locator("h1").count() === 1, "404-h1", "the line is the h1");
    assert(await page.title() === "Not found | Void News", "404-title", await page.title());
    const links = await page.evaluate(() => [...document.querySelectorAll(".notfound__sections a")].map((a) => a.textContent.trim()));
    assert(["History", "Weekly", "On Air"].every((l) => links.includes(l)), "404-sections", `links: ${links.join(", ")}`);
  });
  /* Scrollbar and selection wear the section's colour, through tokens. */
  for (const [route, scheme] of [["/", "dark"], ["/", "light"], ["/history/", "dark"], ["/weekly/", "light"]]) {
    await withPage(browser, { width: 1440, route, scheme }, `chrome-colour ${route} ${scheme}`, async (page) => {
      const s = await page.evaluate(() => {
        const cs = getComputedStyle(document.documentElement);
        const thumb = cs.getPropertyValue("--scrollbar-thumb").trim();
        const rules = [];
        for (const sheet of document.styleSheets) {
          let list; try { list = sheet.cssRules; } catch { continue; }
          for (const r of list) if (r.selectorText && /::selection/.test(r.selectorText)) rules.push(r.cssText.slice(0, 120));
        }
        return { scrollbarWidth: cs.scrollbarWidth, scrollbarColor: cs.scrollbarColor, thumb, selection: rules.length };
      });
      assert(s.scrollbarWidth === "thin" && s.scrollbarColor && s.scrollbarColor !== "auto", "scrollbar-tokens", `scrollbar-width ${s.scrollbarWidth}, scrollbar-color ${s.scrollbarColor}`);
      assert(s.selection > 0, "selection-rule", `${s.selection} ::selection rule(s)`);
    });
  }
  /* The nameplate draws its rule in on hover. */
  await withPage(browser, { width: 1440, route: "/history/" }, "nameplate-draw", async (page) => {
    const np = page.locator(".nav-nameplate").first();
    const scale = () => page.evaluate(() => {
      const cs = getComputedStyle(document.querySelector(".nav-nameplate"), "::after");
      const m = cs.transform.match(/matrix\(([^,]+),/);
      return { content: cs.content, x: m ? Number(m[1]) : (cs.transform === "none" ? 1 : NaN) };
    });
    const before = await scale();
    assert(before.content !== "none", "nameplate-rule-exists", `::after content ${before.content}`);
    await page.mouse.move(0, 0);
    await page.locator(".nav-logo").hover();
    await page.waitForTimeout(400);
    const rest = await scale();
    await np.hover();
    await page.waitForTimeout(500);
    const hover = await scale();
    /* On its own landing the nameplate is aria-current, so it is drawn at
       rest; the check is that hover never undraws it and the rule is real. */
    assert(hover.x >= 0.95, "nameplate-drawn-on-hover", `scaleX at rest ${rest.x.toFixed(2)}, on hover ${hover.x.toFixed(2)}`);
  });
  await withPage(browser, { width: 1440, route: "/" }, "section-link-draw", async (page) => {
    /* On the front page no section link is current; each draws its own
       accent in on hover and is undrawn at rest. */
    const scale = (sel) => page.evaluate((sel) => {
      const el = document.querySelector(sel); if (!el) return null;
      const cs = getComputedStyle(el, "::after");
      const m = cs.transform.match(/matrix\(([^,]+),/);
      return { content: cs.content, x: m ? Number(m[1]) : (cs.transform === "none" ? 1 : NaN), bg: cs.backgroundColor };
    }, sel);
    for (const sec of ["history", "weekly", "audio"]) {
      const link = `.nav-sections .nav-page[data-section='${sec}']`;
      await page.mouse.move(5, 5);
      await page.waitForTimeout(350);
      const rest = await scale(link);
      if (!rest || rest.content === "none") { fail("section-link-draw", `${sec}: no ::after rule on the section link`); continue; }
      await page.locator(link).hover();
      await page.waitForTimeout(500);
      const hover = await scale(link);
      assert(rest.x < 0.05 && hover.x > 0.95, "section-link-draw", `${sec}: scaleX rest ${rest.x.toFixed(2)} -> hover ${hover.x.toFixed(2)} in ${hover.bg}`);
    }
  });
  /* Client-side navigation lands at the top, under nothing: the masthead
     un-compacts and the page's first pixel is below the bar. */
  await withPage(browser, { width: 1440, route: "/" }, "navigation-lands-at-top", async (page) => {
    await page.evaluate(() => window.scrollTo(0, 1200));
    await page.waitForTimeout(400);
    await page.locator(".nav-sections .nav-page[data-section='history']").click();
    await page.waitForURL(/\/history\//, { timeout: 10000 });
    await page.waitForTimeout(800);
    const h = await page.evaluate(() => ({ y: window.scrollY, compact: document.querySelector(".nav-header").getAttribute("data-scroll-compact"), mainTop: Math.round(document.querySelector("main").getBoundingClientRect().top), navBottom: Math.round(document.querySelector(".nav-header").getBoundingClientRect().bottom) }));
    assert(h.y === 0 && h.mainTop >= h.navBottom - 1, "navigation-lands-at-top", `/history/: scrollY ${h.y}, main top ${h.mainTop}, masthead bottom ${h.navBottom}, compact ${h.compact}`);
    await page.locator(".nav-logo").click();
    await page.waitForURL(/\/$/, { timeout: 10000 });
    await page.waitForTimeout(800);
    const back = await page.evaluate(() => ({ y: window.scrollY, compact: document.querySelector(".nav-header").getAttribute("data-scroll-compact"), navH: Math.round(document.querySelector(".nav-header").getBoundingClientRect().height), mainTop: Math.round(document.querySelector("main").getBoundingClientRect().top) }));
    assert(back.y === 0 && back.compact !== "true" && back.mainTop >= back.navH - 1, "navigation-back-uncompacts", `/: scrollY ${back.y}, compact ${back.compact}, masthead ${back.navH}px, main top ${back.mainTop}`);
  });
  /* The Thesis: a note, its sidenote, its source, the play glyph, the source
     marks and the one way back. The routes come from the served index the
     exporter writes (data/history-theses.json lists published theses only;
     EVERY published thesis is walked, not the first), or from
     --thesis=<slug> for a local draft export built with
     NEXT_PUBLIC_HISTORY_DRAFTS=1. With neither, the journey is skipped and
     says so: a thesis that is not published has no page. */
  {
    const thesisArg = process.argv.find((a) => a.startsWith("--thesis="))?.slice("--thesis=".length) ?? null;
    let thesisSlugs = thesisArg ? [thesisArg] : [];
    if (!thesisArg) {
      try {
        const idx = JSON.parse(readFileSync(join(OUT, "data/history-theses.json"), "utf8"));
        thesisSlugs = (idx?.theses ?? []).map((t) => t.slug).filter(Boolean);
      } catch { thesisSlugs = []; }
    }
    thesisSlugs = thesisSlugs.filter((slug) => existsSync(join(OUT, "history", slug, "index.html")));
    if (thesisSlugs.length === 0) {
      ctx("/history/", 1440, "dark"); console.log(`\nscenario: thesis-notes`);
      skip("thesis-notes", "no published thesis in this export");
    } else for (const thesisSlug of thesisSlugs) {
      for (const width of [1440, 390]) {
        await withPage(browser, { width, route: `/history/${thesisSlug}/` }, `thesis-notes @${width}`, async (page) => {
          assert(await page.locator(".hist-thesis-page").count() === 1, "thesis-page", "the route renders the Thesis, not the Hearing");
          const ref = page.locator("sup.hist-th-sup a.hist-th-ref").first();
          assert(await ref.count() === 1, "thesis-ref", "a citation number in the text");
          const n = (await ref.textContent())?.trim();
          const noteVisible = await page.locator(`#n${n}`).count();
          assert(noteVisible === 1, "thesis-note-target", `note ${n} exists in the Notes section`);
          if (width >= 1024) {
            const side = page.locator(`#sn${n}`);
            assert(await side.count() === 1 && await side.isVisible(), "thesis-sidenote", `sidenote ${n} beside the paragraph at ${width}`);
            assert(await page.locator(".hist-th-inline").first().isVisible() === false, "thesis-inline-hidden", "the inline disclosure yields to the sidenote");
          } else {
            const det = page.locator(".hist-th-inline").first();
            assert(await det.isVisible(), "thesis-inline", "the inline note disclosure is the phone's sidenote");
            await det.locator("summary").click();
            await page.waitForTimeout(200);
            assert(await det.evaluate((el) => el.open), "thesis-inline-opens", "tapping the summary opens the notes under the paragraph");
            assert(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1), "thesis-no-overflow", "no horizontal scroll at phone width");
          }
          await ref.click();
          /* The page scrolls smoothly (globals.css), and the Notes sit at the
             foot of a 2,500-word page, so the jump is polled until it settles
             rather than sampled once. */
          let landed = false;
          for (let i = 0; i < 12 && !landed; i++) {
            await page.waitForTimeout(250);
            landed = await page.evaluate((id) => {
              const el = document.getElementById(id); if (!el) return false;
              const r = el.getBoundingClientRect();
              return location.hash === `#${id}` && r.top >= -1 && r.top < window.innerHeight;
            }, `n${n}`);
          }
          assert(landed, "thesis-note-jump", `clicking ${n} lands on note ${n}`);
          /* The one way back (2026-09-25). There is no RETURN link on any
             note any more: a single fixed control offers the way back after a
             jump, names the note it returns to, and puts the reader back on
             the citation they left with focus on it. */
          assert(await page.locator(".hist-th-note__back").count() === 0, "thesis-no-per-note-return", "no note carries its own Return link");
          const ret = page.locator(".hist-th-return");
          assert(await ret.count() === 1, "thesis-return-single", `${await ret.count()} return control(s) on the page`);
          const retState = await ret.evaluate((el) => ({ mode: el.getAttribute("data-mode"), label: el.getAttribute("aria-label"), vis: getComputedStyle(el).visibility, pos: getComputedStyle(el).position, r: el.getBoundingClientRect().toJSON(), vw: window.innerWidth, vh: window.innerHeight }));
          assert(retState.mode === "return" && retState.vis === "visible" && retState.label === `Back to the text at note ${n}`, "thesis-return-offered", `after the jump: mode ${retState.mode}, ${retState.vis}, "${retState.label}"`);
          assert(retState.pos === "fixed" && retState.r.right <= retState.vw && retState.r.bottom <= retState.vh && retState.r.left > retState.vw / 2 && retState.r.height >= 44, "thesis-return-placed", `fixed at ${Math.round(retState.r.left)},${Math.round(retState.r.top)} ${Math.round(retState.r.width)}x${Math.round(retState.r.height)} in ${retState.vw}x${retState.vh}, right half`);
          await ret.click();
          let back = null;
          for (let i = 0; i < 12; i++) {
            await page.waitForTimeout(250);
            back = await page.evaluate((id) => {
              const el = document.getElementById(id); if (!el) return null;
              const r = el.getBoundingClientRect();
              return { inView: r.top >= 0 && r.bottom <= window.innerHeight, focused: document.activeElement === el, mode: document.querySelector(".hist-th-return")?.getAttribute("data-mode") };
            }, `ref${n}`);
            if (back?.inView && back?.focused) break;
          }
          assert(!!back?.inView && !!back?.focused && back?.mode !== "return", "thesis-return-lands", `the control returns to citation ${n}: in view ${back?.inView}, focused ${back?.focused}, mode now ${back?.mode}`);
          /* Deep in the page with no jump pending the same control is "Top". */
          await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
          await page.waitForTimeout(400);
          const topState = await ret.evaluate((el) => ({ mode: el.getAttribute("data-mode"), label: el.getAttribute("aria-label") }));
          assert(topState.mode === "top" && topState.label === "Back to the top of the page", "thesis-return-top", `at the foot: mode ${topState.mode}, "${topState.label}"`);
          /* Every source mark is an icon with a name that says what it opens,
             and the words FREE COPY are no longer printed as a label. */
          const marks = await page.evaluate(() => [...document.querySelectorAll("a.hist-th-srcmark")].map((a) => ({ label: a.getAttribute("aria-label") ?? "", title: a.getAttribute("title") ?? "", href: a.getAttribute("href") ?? "", svg: !!a.querySelector("svg"), insecure: a.getAttribute("data-origin") ?? "" })));
          /* An http link is allowed only to a host in frontend/config/insecure-origins.json
             (a free copy served over http alone, checked and dated there), and
             the page must mark it data-origin="insecure". */
          const insecureHosts = new Set(JSON.parse(readFileSync(join(OUT, "..", "config/insecure-origins.json"), "utf8")).hosts.map((h) => h.host));
          const absolute = (m) => /^https:\/\//.test(m.href) || (/^http:\/\//.test(m.href) && insecureHosts.has(new URL(m.href).hostname) && m.insecure === "insecure");
          const badMarks = marks.filter((m) => !/^Open the (free copy|file page) of \S.+ \(opens in a new tab\)$/.test(m.label) || !m.title || !m.svg || !absolute(m));
          assert(marks.length > 0 && badMarks.length === 0, "thesis-source-marks", `${marks.length} source marks, ${badMarks.length} without a proper name, tooltip, glyph or absolute address${badMarks[0] ? `: ${JSON.stringify(badMarks[0]).slice(0, 160)}` : ""}`);
          const printed = await page.evaluate(() => [...document.querySelectorAll(".hist-th-cite__meta, .hist-th-exhibit__prov")].filter((el) => /\bfree copy\b/i.test(el.innerText)).length
            + [...document.querySelectorAll(".hist-th-notes a")].filter((a) => /^\s*return\s*$/i.test(a.textContent ?? "")).length);
          assert(printed === 0, "thesis-no-label-text", `${printed} note, source or exhibit row still prints FREE COPY or RETURN as text`);
          const struck = await page.evaluate(() => [...document.querySelectorAll(".hist-th-srcmark--none:not([aria-hidden])")].filter((el) => el.getAttribute("role") !== "img" || el.getAttribute("aria-label") !== "No free copy").length);
          assert(struck === 0, "thesis-no-free-copy-mark", `${struck} "no free copy" marks without their accessible name`);
          const src = page.locator("#sources .hist-th-source__link").first();
          assert(await src.count() === 1 && /^https:\/\//.test((await src.getAttribute("href")) ?? ""), "thesis-source-link", "the first source link is absolute");
          const glyph = page.locator(".hist-th-episode__play").first();
          if (await glyph.count() === 0) { skip("thesis-play-glyph", "no episode in the manifest for this event"); return; }
          const label = await glyph.getAttribute("aria-label");
          assert(!!label && /^Listen from /.test(label), "thesis-play-glyph", `the play glyph is labelled: ${label}`);
          const exhibits = await page.locator(".hist-th-exhibit").count();
          const provs = await page.locator(".hist-th-exhibit .hist-th-exhibit__prov").count();
          assert(exhibits > 0 && exhibits === provs, "thesis-exhibit-provenance", `${provs} of ${exhibits} exhibits carry a provenance line`);
        });
      }
    }
  }
  /* The Audio section: every programme, one place, each loading into the one
     shared player. */
  await withPage(browser, { width: 1440, route: "/audio/" }, "audio-hub", async (page) => {
    const kinds = await page.evaluate(() => [...document.querySelectorAll(".audio-play")].map((b) => b.getAttribute("data-kind")));
    assert(kinds.includes("daily") && kinds.includes("weekly") && kinds.includes("history"), "audio-hub-programmes", `play buttons: ${kinds.join(", ")}`);
    assert(await page.locator(".nav-nameplate[aria-current='page']").count() === 1, "audio-hub-nameplate", "the Audio nameplate is current");
    assert((await page.locator(".audio-feed__url").allTextContents()).filter((t) => /podcast-(world|weekly|history)\.xml$/.test(t)).length === 3, "audio-hub-feeds", "three feed addresses");
    await page.locator(".audio-play[data-kind='history']").first().click();
    await page.waitForTimeout(1200);
    const fp = await page.evaluate(() => ({ title: document.querySelector(".fp__title")?.textContent?.trim() ?? null, state: document.querySelector(".audio-play[data-kind='history']")?.getAttribute("data-state") }));
    assert(fp.title === "History" && fp.state !== "idle", "audio-hub-plays-history", `player title ${fp.title}, button state ${fp.state}`);
  });
  /* ─────────────────────────────────────────────────────────────────────
     THE ON AIR SYSTEM

     Eight scenarios, one per reader-visible defect measured in a browser on
     2026-09-21 before the two-slot restructure. Each one failed then. The
     root cause was a single `brief` slot that all three programmes wrote
     into, read everywhere as if it were always the daily edition, with no
     element listeners under `isPlaying` and the transport built twice.

     A History episode's MP3 lives in a GitHub release rather than the repo
     (deploy-cloudflare.yml fetches it into out/audio/history at build time),
     so a local export carries the chapter JSON and no audio. serveHistoryAudio
     stands a real file in for it; without that the press rule could only be
     asserted on two of the three programmes, which is where the silent
     History Play button hid in the first place.
     ───────────────────────────────────────────────────────────────────── */
  const STAND_IN_MP3 = ["audio/world", "audio/weekly-world"]
    .map((d) => join(OUT, d))
    .flatMap((d) => existsSync(d) ? readdirSync(d).filter((f) => f.endsWith(".mp3")).map((f) => join(d, f)) : [])[0] ?? null;

  /* Playwright's route interception does not reach Chromium's media loader:
     a fulfilled response (200 or a correct 206 for the range it asks for)
     leaves the element with the src set, paused at 0 and raising nothing.
     Measured, twice. So the stand-in goes on DISK, where the sweep's own
     static server will serve it, which is also what the deploy does for real
     (deploy-cloudflare.yml fetches the release into out/audio/history).
     Removed again in a finally, so a local export is left as it was found. */
  function standInHistoryAudio() {
    if (!STAND_IN_MP3) return { ok: false, clean() {} };
    const manifest = join(OUT, "data/history-audio.json");
    if (!existsSync(manifest)) return { ok: false, clean() {} };
    let episodes;
    try { episodes = JSON.parse(readFileSync(manifest, "utf8")).episodes ?? {}; }
    catch { return { ok: false, clean() {} }; }
    const body = readFileSync(STAND_IN_MP3);
    const written = [];
    for (const e of Object.values(episodes)) {
      const rel = String(e?.url ?? "").split("?")[0].replace(/^\//, "");
      if (!rel.startsWith("audio/history/")) continue;
      const path = join(OUT, rel);
      if (existsSync(path)) continue;
      mkdirSync(join(OUT, "audio/history"), { recursive: true });
      writeFileSync(path, body);
      written.push(path);
    }
    return { ok: true, clean() { for (const f of written) try { unlinkSync(f); } catch {} } };
  }

  /* What the element is really doing, and what every surface claims. */
  const REPORT = `(() => {
    const a = document.querySelector("audio");
    const beam = document.querySelector(".nav-logo [data-playing], .nav-logo[data-playing]");
    return {
      src: a ? (a.currentSrc || a.src || "").split("/").pop().split("?")[0] : null,
      paused: a ? a.paused : null,
      t: a ? Math.round(a.currentTime * 10) / 10 : null,
      claimsPlaying: {
        pill: !!document.querySelector(".fp--playing"),
        tab: !!document.querySelector(".mtb__tab--onair-live"),
        beam: !!beam,
        hubButtons: [...document.querySelectorAll(".audio-play")].map((b) => b.getAttribute("data-state")),
        onairPortal: !!document.querySelector(".onair__portal--live"),
      },
      label: document.querySelector(".fp__title")?.textContent?.trim() ?? null,
    };
  })()`;

  /* 1. ONE PLAY BUTTON. Every hub button plays on the first press and pauses
        on the second. Before this, Play on a History episode loaded the
        episode and played nothing at all. */
  const standIn = standInHistoryAudio();
  try {
  await withPage(browser, { width: 1440, route: "/audio/" }, "one-play-button", async (page) => {
    const stood = standIn.ok;
    for (const kind of ["daily", "weekly", "history"]) {
      const btn = page.locator(`.audio-play[data-kind='${kind}']`).first();
      if (await btn.count() === 0) { skip(`one-play-button-${kind}`, "no button for this programme"); continue; }
      if (kind === "history" && !stood) { skip("one-play-button-history", "no stand-in mp3 in this export"); continue; }
      await btn.click();
      await page.waitForTimeout(1800);
      const playing = await page.evaluate(REPORT);
      assert(playing.paused === false && playing.t > 0, `one-play-button-${kind}`,
        `${kind}: paused ${playing.paused}, currentTime ${playing.t}, src ${playing.src}`);
      assert((await btn.textContent())?.includes("Pause"), `one-play-button-${kind}-reads-pause`,
        `${kind} button reads ${JSON.stringify((await btn.textContent())?.trim())}`);
      await btn.click();
      await page.waitForTimeout(600);
      assert((await page.evaluate(REPORT)).paused === true, `one-play-button-${kind}-toggles`,
        `${kind}: a second press paused it`);
    }
  });

  /* The element survives a CLIENT navigation, which is what the provider can
     promise: a full document load builds a new one by definition. So these
     walk the site the way a reader does, by clicking links, never by goto. */
  async function clickTo(page, href) {
    const link = page.locator(`a[href$="${href}"]`).first();
    if (await link.count() === 0) return false;
    await link.click();
    await page.waitForURL((u) => u.pathname.endsWith(href), { timeout: 10_000 }).catch(() => {});
    await page.waitForTimeout(1200);
    return true;
  }

  /* 2. AUDIO SURVIVES NAVIGATION. Playing the brief and walking the site used
        to pause it and swap the source, twice over: /weekly seized the
        element on mount, and returning home detached what was playing. */
  await withPage(browser, { width: 1440, route: "/audio/" }, "audio-survives-navigation", async (page) => {
    const btn = page.locator(".audio-play[data-kind='daily']").first();
    if (await btn.count() === 0) { skip("audio-survives-navigation", "no daily programme in this export"); return; }
    await btn.click();
    await page.waitForTimeout(1500);
    const started = await page.evaluate(REPORT);
    if (!assert(started.paused === false, "audio-survives-navigation-starts", `paused ${started.paused}`)) return;
    for (const href of ["/weekly/", "/", "/audio/"]) {
      if (!(await clickTo(page, href))) { skip(`audio-survives-navigation ${href}`, "no link to this route on the page"); continue; }
      const now = await page.evaluate(REPORT);
      assert(now.src === started.src && now.paused === false && now.t >= started.t,
        `audio-survives-navigation ${href}`,
        `src ${now.src} (was ${started.src}), paused ${now.paused}, t ${now.t} (was ${started.t})`);
    }
  });

  /* 3. WEEKLY OFFERS, IT DOES NOT SEIZE. Opening the issue while the brief
        plays used to pause it mid-sentence and swap the source with no
        gesture. It may still offer the Argument to an idle player. */
  await withPage(browser, { width: 1440, route: "/audio/" }, "weekly-does-not-seize", async (page) => {
    const btn = page.locator(".audio-play[data-kind='daily']").first();
    if (await btn.count() === 0) { skip("weekly-does-not-seize", "no daily programme in this export"); return; }
    await btn.click();
    await page.waitForTimeout(1500);
    const before = await page.evaluate(REPORT);
    if (!assert(before.paused === false, "weekly-does-not-seize-starts", `paused ${before.paused}`)) return;
    if (!(await clickTo(page, "/weekly/"))) { skip("weekly-does-not-seize", "no link to /weekly on the hub"); return; }
    await page.waitForTimeout(800);
    const after = await page.evaluate(REPORT);
    assert(after.src === before.src && after.paused === false, "weekly-does-not-seize",
      `on /weekly the element holds ${after.src} paused ${after.paused}, was ${before.src}`);
  });

  /* 4. A TAB RESUME KEEPS ITS PROGRAMME. Backgrounding /weekly and returning
        used to swap the daily MP3 in and stop it, while every label still
        said Weekly. The refetch writes today's edition now; it cannot reach
        the element. */
  await withPage(browser, { width: 1440, route: "/weekly/" }, "tab-resume-keeps-its-programme", async (page) => {
    await page.waitForTimeout(1500);
    const before = await page.evaluate(REPORT);
    if (!before.src) { skip("tab-resume-keeps-its-programme", "no audio loaded on the issue"); return; }
    await page.evaluate(() => {
      Object.defineProperty(document, "visibilityState", { value: "hidden", configurable: true });
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await page.waitForTimeout(300);
    await page.evaluate(() => {
      Object.defineProperty(document, "visibilityState", { value: "visible", configurable: true });
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await page.waitForTimeout(2000);
    const after = await page.evaluate(REPORT);
    assert(after.src === before.src, "tab-resume-keeps-its-programme",
      `after the resume the element holds ${after.src}, was ${before.src}`);
    assert(after.label === before.label, "tab-resume-keeps-its-label",
      `player label ${after.label}, was ${before.label}`);
  });

  /* 5. /onair TELLS THE TRUTH. It used to print "ON AIR, World Edition,
        23 min" over the Weekly's cover headline and over a documentary. The
        page's subject is today's broadcast; another programme in the element
        is named in one line rather than wearing today's dateline. */
  await withPage(browser, { width: 1440, route: "/audio/" }, "onair-tells-the-truth", async (page) => {
    const stood = standIn.ok;
    const hist = page.locator(".audio-play[data-kind='history']").first();
    if (await hist.count() === 0 || !stood) { skip("onair-tells-the-truth", "no history episode to load"); return; }
    const episodeTitle = (await page.locator(".audio-episode").first().locator(".audio-episode__title").textContent())?.trim();
    await hist.click();
    await page.waitForTimeout(1500);
    if (!(await clickTo(page, "/onair/"))) { skip("onair-tells-the-truth", "no link to /onair on the hub"); return; }
    await page.waitForTimeout(600);
    const p = await page.evaluate(() => ({
      elsewhere: document.querySelector(".onair__elsewhere")?.textContent?.trim() ?? null,
      headline: document.querySelector(".onair__np-headline")?.textContent?.trim() ?? null,
      edition: document.querySelector(".onair__dateline-edition")?.textContent?.trim() ?? null,
      live: !!document.querySelector(".onair__portal--live"),
    }));
    assert(!!p.elsewhere && p.elsewhere.includes("History"), "onair-names-what-is-playing",
      `notice: ${JSON.stringify(p.elsewhere)}`);
    assert(!p.headline || p.headline !== episodeTitle, "onair-does-not-wear-another-episode",
      `page headline ${JSON.stringify(p.headline)} vs loaded ${JSON.stringify(episodeTitle)}`);
    assert(p.live === false, "onair-portal-not-live-for-another-programme",
      `portal live while History owns the element: ${p.live}`);
  });

  } finally { standIn.clean(); }

  /* 6. PLAY STATE CANNOT LIE. Losing audio to a call, a Bluetooth drop or the
        OS left the pill's pause icon, the tab bar's live dot and the
        wordmark's beam all claiming to play: `isPlaying` was set optimistically
        beside play(), with no listener on the element. */
  await withPage(browser, { width: 390, route: "/audio/" }, "play-state-cannot-lie", async (page) => {
    const btn = page.locator(".audio-play[data-kind='daily']").first();
    if (await btn.count() === 0) { skip("play-state-cannot-lie", "no daily programme in this export"); return; }
    await btn.click();
    await page.waitForTimeout(1500);
    const on = await page.evaluate(REPORT);
    if (!assert(on.paused === false, "play-state-cannot-lie-starts", `paused ${on.paused}`)) return;
    assert(on.claimsPlaying.tab === true || on.claimsPlaying.pill === true,
      "play-state-lights-up", `live while playing: ${Object.entries(on.claimsPlaying).filter(([k, v]) => k !== "hubButtons" && v === true).map(([k]) => k).join(", ") || "none"}`);
    /* Pause the ELEMENT, the way the OS would: outside React entirely. */
    await page.evaluate(() => document.querySelector("audio").pause());
    await page.waitForTimeout(700);
    const off = await page.evaluate(REPORT);
    const lying = Object.entries(off.claimsPlaying)
      .filter(([k, v]) => k !== "hubButtons" && v === true)
      .map(([k]) => k);
    const buttonsLying = (off.claimsPlaying.hubButtons ?? []).filter((s) => s === "playing");
    assert(off.paused === true && lying.length === 0 && buttonsLying.length === 0,
      "play-state-cannot-lie",
      `element paused ${off.paused}; still claiming to play: ${[...lying, ...buttonsLying].join(", ") || "nothing"}`);
  });

  /* 7. NO DOUBLE TRANSPORT. At 1440 the page's portal and the pill's console
        were both on screen, showing the same episode through two
        implementations (onair.css:5 admitted the duplication). */
  await withPage(browser, { width: 1440, route: "/onair/" }, "no-double-transport", async (page) => {
    await page.waitForTimeout(900);
    const n = await page.evaluate(() => ({
      portal: document.querySelectorAll(".onair__portal").length,
      pill: document.querySelectorAll(".fp").length,
      panel: document.querySelectorAll(".oap").length,
    }));
    assert(n.portal === 1 && n.pill === 0 && n.panel === 0, "no-double-transport",
      `/onair carries ${n.portal} portal, ${n.pill} floating player, ${n.panel} panel`);
  });

  /* 8. THE PANEL OPENS WHERE THE READER IS. On Air used to push a route,
        costing a reader their place to reach a transport already on screen.
        A dialog: right-anchored at 1440, Escape restores focus to the
        opener, the URL does not change, and the pill stands down. */
  for (const width of [1440, 390]) {
    await withPage(browser, { width, route: "/" }, `onair-panel @${width}`, async (page) => {
      await page.waitForTimeout(1200);
      const opener = width >= 768 ? ".fp__info" : ".mtb__tab--onair";
      if (await page.locator(opener).count() === 0) { skip("onair-panel", `no ${opener} at ${width}`); return; }
      const urlBefore = page.url();
      /* Below 1700px the desktop pill rests folded to its mark and unfolds
         under the pointer (floating-player.css F11), so a reader hovers it
         before the title is there to press. */
      if (width >= 768) await page.locator(".fp__pill").hover();
      await page.locator(opener).click();
      await page.waitForTimeout(700);
      const o = await page.evaluate(() => {
        const p = document.querySelector(".oap");
        const b = p?.getBoundingClientRect();
        return {
          open: !!p,
          role: p?.getAttribute("role"),
          modal: p?.getAttribute("aria-modal"),
          labelled: !!p?.getAttribute("aria-label"),
          right: b ? Math.round(innerWidth - b.right) : null,
          width: b ? Math.round(b.width) : null,
          scrim: !!document.querySelector(".oap__scrim"),
          pill: !!document.querySelector(".fp__pill"),
          focusInside: !!document.activeElement.closest(".oap"),
          overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        };
      });
      if (!assert(o.open, "onair-panel-opens", `press on ${opener}: panel ${o.open ? "open" : "not opened"}`)) return;
      assert(page.url() === urlBefore, "onair-panel-keeps-the-page", `url ${page.url()} was ${urlBefore}`);
      assert(o.role === "dialog" && o.labelled, "onair-panel-is-a-dialog", `role ${o.role}, labelled ${o.labelled}`);
      assert(o.focusInside, "onair-panel-takes-focus", `focus is ${o.focusInside ? "inside" : "outside"} the panel`);
      assert(!o.pill, "onair-panel-hides-the-pill", `pill behind the panel: ${o.pill ? "present" : "none"}`);
      assert(o.overflowX === 0, "onair-panel-no-overflow", `${o.overflowX}px past the viewport`);
      if (width >= 1024) {
        /* A pane beside the page, not over it: right-anchored, and it must not
           claim aria-modal while the page behind stays scrollable. */
        assert(o.right === 0 && o.width >= 360 && o.width <= 480, "onair-panel-right-anchored",
          `${o.width}px, ${o.right}px from the right edge`);
        assert(o.modal === null && !o.scrim, "onair-panel-pane-is-not-modal",
          `aria-modal ${o.modal}, scrim ${o.scrim}`);
      } else {
        assert(o.modal === "true" && o.scrim, "onair-panel-sheet-is-modal",
          `aria-modal ${o.modal}, scrim ${o.scrim}`);
      }
      await page.keyboard.press("Escape");
      await page.waitForTimeout(700);
      const c = await page.evaluate((sel) => ({
        open: !!document.querySelector(".oap"),
        focusOnOpener: document.activeElement?.matches(sel) ?? false,
        focusTag: document.activeElement?.tagName,
      }), opener);
      assert(!c.open, "onair-panel-escape-closes", `after Escape the panel is ${c.open ? "still open" : "closed"}`);
      assert(c.focusOnOpener, "onair-panel-restores-focus",
        `focus landed on ${c.focusOnOpener ? opener : c.focusTag}`);
    });
  }
  /* Reading progress on long reads: a brass rule under the masthead that
     tracks the scroll, with no JavaScript. */
  const longRead = dynamicRoutes().find((r) => r.startsWith("/story/")) ?? null;
  for (const route of [longRead, "/history/partition-of-india/", "/weekly/"].filter(Boolean)) {
    if (!existsSync(join(OUT, route.slice(1), "index.html"))) continue;
    await withPage(browser, { width: 1440, route }, `reading-progress ${route}`, async (page) => {
      const supported = await page.evaluate(() => CSS.supports("animation-timeline: scroll()"));
      if (!supported) { skip("reading-progress", "animation-timeline unsupported in this Chromium"); return; }
      const read = () => page.evaluate(() => {
        const cs = getComputedStyle(document.querySelector(".nav-header"), "::after");
        const m = cs.transform.match(/matrix\(([^,]+),/);
        return { content: cs.content, x: m ? Number(m[1]) : (cs.transform === "none" ? 1 : NaN), name: cs.animationName };
      });
      const top = await read();
      if (top.content === "none") { fail("reading-progress", `no ::after on the masthead at ${route}`); return; }
      /* Instant, not smooth (globals.css sets scroll-behavior: smooth, and
         on the CI runner a smooth scroll was still travelling at 92% when
         the value was read), and repeated until the page stops growing:
         lazy sections below the fold add height after the first scroll,
         and the timeline covers the document as it is. */
      for (let i = 0; i < 5; i++) {
        const before = await page.evaluate(() => document.documentElement.scrollHeight);
        await page.evaluate(() => window.scrollTo({ top: document.documentElement.scrollHeight, left: 0, behavior: "instant" }));
        await page.waitForTimeout(400);
        const after = await page.evaluate(() => document.documentElement.scrollHeight);
        if (after === before && i > 0) break;
      }
      const bottom = await read();
      const ratio = await page.evaluate(() => { const d = document.documentElement; return (d.scrollTop / (d.scrollHeight - d.clientHeight)).toFixed(2); });
      assert(top.x < 0.05 && bottom.x > 0.95, "reading-progress", `scaleX top ${top.x.toFixed(2)} -> bottom ${bottom.x.toFixed(2)} at scroll ratio ${ratio} (${top.name})`);
    });
    await withPage(browser, { width: 1440, route, reducedMotion: "reduce" }, `reading-progress-reduced ${route}`, async (page) => {
      const c = await page.evaluate(() => getComputedStyle(document.querySelector(".nav-header"), "::after").content);
      assert(c === "none", "reading-progress-reduced-motion", `::after content under reduced motion: ${c}`);
    });
  }
  /* The status bar wears the section's paper. */
  for (const [route, scheme] of [["/history/", "dark"], ["/history/", "light"], ["/weekly/", "dark"], ["/weekly/", "light"]]) {
    await withPage(browser, { width: 1440, route, scheme }, `section-theme-color ${route} ${scheme}`, async (page) => {
      const s = await page.evaluate(() => ({
        metas: [...document.querySelectorAll("meta[name='theme-color']")].map((m) => ({ media: m.getAttribute("media") ?? "", content: m.getAttribute("content").toUpperCase() })),
        nav: getComputedStyle(document.querySelector(".nav-header")).backgroundColor,
        html: getComputedStyle(document.documentElement).backgroundColor,
      }));
      const want = hexOf(s.nav === "rgba(0, 0, 0, 0)" ? s.html : s.nav);
      const mine = s.metas.find((m) => m.media.includes(scheme))?.content;
      assert(s.metas.length === 2, "theme-color-count", `${s.metas.length} theme-color metas`);
      assert(mine === want, "section-theme-color", `${scheme} meta ${mine} vs masthead ${want}`);
    });
  }
  /* On air: while audio plays the wordmark's beam rocks in brass; never
     under reduced motion. */
  await withPage(browser, { width: 1440, route: "/onair/" }, "on-air-beam", async (page) => {
    const name = await page.evaluate(() => {
      const h = document.querySelector(".nav-header"); h.setAttribute("data-playing", "true");
      const beam = h.querySelector(".sigil-word__beam, .nav-logo .sigil__beam-group, .nav-logo [class*='beam']");
      return beam ? getComputedStyle(beam).animationName : "no-beam";
    });
    assert(name === "brand-on-air", "on-air-beam", `animationName ${name} with data-playing`);
  });
  await withPage(browser, { width: 1440, route: "/onair/", reducedMotion: "reduce" }, "on-air-beam-reduced", async (page) => {
    const name = await page.evaluate(() => {
      const h = document.querySelector(".nav-header"); h.setAttribute("data-playing", "true");
      const beam = h.querySelector(".sigil-word__beam, .nav-logo .sigil__beam-group, .nav-logo [class*='beam']");
      return beam ? getComputedStyle(beam).animationName : "no-beam";
    });
    assert(name === "none" || name === "no-beam", "on-air-beam-reduced-motion", `animationName ${name} under reduced motion`);
  });
  /* Print: a story and a History event print as a sheet, with the print
     masthead and none of the chrome. */
  for (const route of [longRead, "/history/partition-of-india/"].filter(Boolean)) {
    if (!existsSync(join(OUT, route.slice(1), "index.html"))) continue;
    await withPage(browser, { width: 1024, route }, `print ${route}`, async (page) => {
      await page.emulateMedia({ media: "print" });
      await page.waitForTimeout(600);
      const s = await page.evaluate(() => {
        const vis = (sel) => { const el = document.querySelector(sel); if (!el) return null; const cs = getComputedStyle(el); return cs.display !== "none" && cs.visibility !== "hidden"; };
        return { nav: vis(".nav-header"), footer: vis(".site-footer"), mast: vis(".print-mast"), body: getComputedStyle(document.body).backgroundColor, mtb: vis(".mtb") };
      });
      assert(s.nav === false && s.footer === false && s.mtb !== true, "print-hides-chrome", `masthead ${s.nav}, footer ${s.footer}, tabbar ${s.mtb}`);
      assert(s.mast === true, "print-mast", `.print-mast visible: ${s.mast}`);
      assert(/^rgb\(255, 255, 255\)$|rgba\(0, 0, 0, 0\)/.test(s.body), "print-white", `body background ${s.body}`);
    });
  }
}

/* ── Sitemap: every URL it advertises exists in the export ── */
function checkSitemap() {
  ctx("/sitemap.xml", 0, "fs");
  console.log(`\nsitemap`);
  const file = join(OUT, "sitemap.xml");
  if (!existsSync(file)) { fail("sitemap", "out/sitemap.xml missing"); return; }
  const urls = [...readFileSync(file, "utf8").matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1]);
  const missing = urls.map((u) => u.replace(SITE, "")).filter((p) => !resolvesInOut(p));
  if (missing.length) fail("sitemap", `${missing.length} advertised URL(s) missing from the export: ${missing.slice(0, 5).join(", ")}`);
  else ok("sitemap", `${urls.length} URL(s) all resolve`);
}

/* ── Run ── */
const server = await serve(BASE, PORT);
const browser = await launchChromium();
const axePath = new URL("../node_modules/axe-core/axe.min.js", import.meta.url).pathname;
const axeSource = existsSync(axePath) ? readFileSync(axePath, "utf8") : null;
if (!axeSource) console.log("[warn] axe-core not installed; accessibility rules skipped");

console.log(`verify-headless: ${ROUTES.length} route(s) x ${WIDTHS.length} width(s) x ${SCHEMES.join("+")} ${QUICK ? "(quick)" : "(full)"}, base path "${BASE}"`);
for (const route of ROUTES) {
  for (const scheme of SCHEMES) {
    for (const width of WIDTHS) {
      await auditPage(browser, route, width, scheme, axeSource);
    }
  }
}
if (!ONLY) {
  if (!QUICK) checkSitemap();
  await scenarios(browser);
}

await browser.close();
server.close();

const summary = {
  mode: ONLY ? `route ${ONLY}` : QUICK ? "quick" : "full",
  routes: ROUTES, widths: WIDTHS, schemes: SCHEMES,
  counts: { ok: results.filter((r) => r.status === "ok").length, fail: failures.length, warn: results.filter((r) => r.status === "warn").length, skip: results.filter((r) => r.status === "skip").length, allowed: results.filter((r) => r.status === "allowed").length },
  failures, results,
};
writeFileSync(join(OUT, ".verify-headless.json"), JSON.stringify(summary, null, 2));

if (failures.length) {
  console.log(`\nFAIL  ${failures.length} headless check(s); report in out/.verify-headless.json, screenshots in out/.verify-headless/`);
  failures.forEach((f) => console.log(`  - ${f}`));
  process.exit(1);
}
console.log(`\nPASS  headless sweep: ${summary.counts.ok} checks across ${ROUTES.length} route(s), ${WIDTHS.length} width(s), ${SCHEMES.length} scheme(s)${summary.counts.warn ? `, ${summary.counts.warn} warning(s)` : ""}${summary.counts.allowed ? `, ${summary.counts.allowed} allowlisted` : ""}`);
