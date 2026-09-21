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
import { readFileSync, existsSync, readdirSync, statSync, mkdirSync, writeFileSync } from "node:fs";
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
  "/listen/", "/sources/", "/about/", "/ship/", "/press/", "/privacy/",
  "/history/threads/",
];
const QUICK_ROUTES = ["/", "/history/", "/weekly/", "/paper/", "/onair/"];

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
    case "listen": return "listen";
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
const LINKED_SECTIONS = new Set(["onair", "history", "weekly", "listen", "sources", "ship", "about"]);
/* Landings whose nameplate is the current page. */
const NAMEPLATE_LANDINGS = new Set(["/history/", "/weekly/", "/paper/"]);

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
async function openPage(browser, { width, scheme, route, storage = {}, session = {}, reducedMotion = "no-preference" }) {
  const context = await browser.newContext({
    viewport: { width, height: width < 768 ? 844 : 900 },
    colorScheme: scheme,
    reducedMotion,
    isMobile: width < 768,
    hasTouch: width < 768,
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
      await page.addScriptTag({ content: axeSource });
      const axe = await page.evaluate(async () => {
        const r = await window.axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] }, resultTypes: ["violations"] });
        return r.violations.map((v) => ({ id: v.id, impact: v.impact, n: v.nodes.length, target: v.nodes[0]?.target?.join(" ") ?? "", help: v.help }));
      });
      const serious = axe.filter((v) => v.impact === "critical" || v.impact === "serious");
      const lesser = axe.filter((v) => !(v.impact === "critical" || v.impact === "serious"));
      for (const v of serious) F("axe", `${v.id} (${v.impact}, ${v.n} node${v.n === 1 ? "" : "s"}) ${v.help}; first: ${v.target.slice(0, 80)}`);
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
  /* The floating player: on the news, On Air and Weekly pages; not on Ship,
     not on History (the event page carries its own Listen). */
  for (const [route, expect] of [["/", true], ["/onair/", true], ["/weekly/", true], ["/ship/", false], ["/history/", false]]) {
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

  await brandChecks(browser);
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
  await withPage(browser, { width: 1440, route: "/" }, "nameplate-draw-off-section", async (page) => {
    /* On the front page there is no nameplate; the section links carry the
       same rule and are undrawn until hovered. */
    const scale = (sel) => page.evaluate((sel) => {
      const el = document.querySelector(sel); if (!el) return null;
      const cs = getComputedStyle(el, "::before");
      const m = cs.transform.match(/matrix\(([^,]+),/);
      return { content: cs.content, x: m ? Number(m[1]) : (cs.transform === "none" ? 1 : NaN) };
    }, sel);
    const link = ".nav-sections .nav-page[data-section='history']";
    const rest = await scale(link);
    if (!rest || rest.content === "none") { skip("section-link-draw", "no ::before rule on the section link"); return; }
    await page.locator(link).hover();
    await page.waitForTimeout(500);
    const hover = await scale(link);
    assert(rest.x < 0.05 && hover.x > 0.95, "section-link-draw", `scaleX rest ${rest.x.toFixed(2)} -> hover ${hover.x.toFixed(2)}`);
  });
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
      /* Twice, with a pause: lazy sections below the fold add height after
         the first scroll, and the timeline covers the document as it is. */
      for (let i = 0; i < 2; i++) {
        await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
        await page.waitForTimeout(500);
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
