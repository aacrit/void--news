/* Self-descriptive copy must agree with the data it describes.
 *
 * The site said "50 stories" in six places for two weeks after the feed became
 * 20 on 2026-09-07, including the press page's boilerplate labelled "Copy it as
 * written" for journalists to quote. The homepage was correct throughout,
 * because it reads frontend/config/feed.json; the prose was wrong, because it
 * did not.
 *
 * feedConfig.ts already carried the warning ("Never restate these numbers as
 * literals in a component") and the prose restated them anyway. A warning in a
 * header is not a control. This is.
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const ROOT = new URL("..", import.meta.url).pathname;
const fail = [];
const ok = (name, cond, detail = "") =>
  cond ? console.log(`PASS  ${name}`) : fail.push(`${name}${detail ? ": " + detail : ""}`);

const cfg = JSON.parse(readFileSync(join(ROOT, "config/feed.json"), "utf8"));
const sources = JSON.parse(readFileSync(join(ROOT, "../data/sources.json"), "utf8"));
const sourceRows = Array.isArray(sources) ? sources : sources.sources;

function walk(dir) {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    if (f === "node_modules" || f === ".next") return [];
    return statSync(p).isDirectory() ? walk(p) : p.endsWith(".ts") || p.endsWith(".tsx") ? [p] : [];
  });
}
const files = walk(join(ROOT, "app"));
const read = (p) => readFileSync(p, "utf8");

// 1. No component may restate the feed size as a literal in prose. The numbers
//    that drifted were always the ones written out by hand.
//
//    The first regex here matched "50 stories" and "top 50" only, and the press
//    page kept "<div>50</div> <div>Stories in one daily edition</div>" and "The
//    fifty most important stories" for two weeks under a heading telling
//    journalists to copy it as written (brand audit 2026-09-21, F-01). On the
//    pages whose job is to describe the site, the old values may not appear
//    within reach of "stories" at all, across tags and line breaks. Comments
//    are stripped first: a stale comment is a lie to the next engineer, not to
//    a reader, and belongs to a different check.
const OLD_FEED_SIZES = "50|fifty";
const SELF_DESCRIBING = ["app/press", "app/about", "app/components/about",
                         "app/layout.tsx", "app/page.tsx"].map((d) => join(ROOT, d));
const uncommented = (txt) =>
  txt.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
const stale = files.filter((p) => {
  const txt = uncommented(read(p));
  if (new RegExp(`\\b(?:${OLD_FEED_SIZES})\\s+stories\\b|\\btop\\s+(?:${OLD_FEED_SIZES})\\b`, "i").test(txt)) return true;
  if (!SELF_DESCRIBING.some((d) => p === d || p.startsWith(d + "/"))) return false;
  return new RegExp(`\\b(?:${OLD_FEED_SIZES})\\b[\\s\\S]{0,120}?\\bstories\\b`, "i").test(txt)
      || new RegExp(`\\bstories\\b[\\s\\S]{0,60}?\\b(?:${OLD_FEED_SIZES})\\b`, "i").test(txt);
});
ok("no component restates the feed size in prose",
   stale.length === 0, stale.map((p) => p.replace(ROOT, "")).join(", "));

// 2. The source and country counts the copy states must match the roster.
//
//    Two widenings, 2026-09-22. The pattern was /1,?0\d\d/, which matches only
//    1000-1099 and would have SILENTLY STOPPED MATCHING the day the roster
//    passed 1,099: a gate that quietly stops asserting is worse than no gate.
//    And the scan covered app/ only, while frontend/public/manifest.json is
//    SERVED and carries the same sentence, so the count a browser installs the
//    app with was never checked. Both fixed here.
const countries = new Set(sourceRows.map((s) => s.country).filter(Boolean));
const MANIFEST = join(ROOT, "public/manifest.json");
const scanned = [...files, MANIFEST];
for (const p of scanned) {
  //  Comments are stripped, as in check 1 and for the same reason: a stale
  //  comment lies to the next engineer, not to a reader. Two files quote
  //  "1,016 sources" on purpose, to record why the number stopped being
  //  written out (lib/ogCard.tsx and lib/rosterConfig.ts), and a gate that
  //  fails on its own explanation teaches people to delete explanations.
  const txt = uncommented(read(p));
  for (const m of txt.matchAll(/\b(\d{1,2},?\d{3})\s+sources\b/g)) {
    ok(`${p.replace(ROOT, "")} source count`,
       Number(m[1].replace(",", "")) === sourceRows.length,
       `copy says ${m[1]}, roster holds ${sourceRows.length}`);
  }
  for (const m of txt.matchAll(/\b(\d{2,3})\s+countries\b/g)) {
    ok(`${p.replace(ROOT, "")} country count`,
       Number(m[1]) === countries.size,
       `copy says ${m[1]}, roster holds ${countries.size}`);
  }
}

// 3. The About page's ranking chart must sum to 100. It summed to 94: it had
//    perspective diversity at 6% where the engine uses 9%, and omitted the 3%
//    velocity term entirely, so two live pages disagreed about the same number
//    and one was provably wrong against importance_ranker.py.
const dataTs = read(join(ROOT, "app/film/data.ts"));
const block = dataTs.split("RANKING_SIGNALS")[1]?.split("];")[0] ?? "";
const weights = [...block.matchAll(/weight:\s*(\d+)/g)].map((m) => Number(m[1]));
const total = weights.reduce((a, b) => a + b, 0);
ok("ranking weights sum to 100", total === 100, `they sum to ${total}`);

// 4. The weights must match the engine, which is the only source of truth.
const ranker = readFileSync(join(ROOT, "../pipeline/ranker/importance_ranker.py"), "utf8");
const formula = ranker.split("headline_rank = (")[1]?.split(")")[0] ?? "";
const engine = [...formula.matchAll(/\*\s*0\.(\d+)/g)].map((m) => Number(m[1].padEnd(2, "0")));
ok("ranking weights match the engine",
   JSON.stringify([...weights].sort((a, b) => a - b)) ===
   JSON.stringify([...engine].sort((a, b) => a - b)),
   `copy ${[...weights].sort((a,b)=>a-b)} vs engine ${[...engine].sort((a,b)=>a-b)}`);

// 5. No em dash, no en dash, and no kill-list word in anything the frontend
//    renders. Three live components shipped "Sources disagree significantly",
//    "differ significantly" and "notably more sensational" for months: the
//    editorial standard runs on pipeline card text, and verify_production.py
//    reads the served homepage, where those strings appear only after a click.
//    Nothing read the source. This does.
//
//    Scanned: the source with comments and regex literals removed, which
//    leaves exactly the two things that reach a reader, JSX text nodes and
//    string literals, plus identifiers (which never carry a dash anyway).
//    A comment may say what it likes; a regex that STRIPS dashes has to be
//    able to spell one (app/lib/summaryHygiene.ts).
//
//    History is scanned too since 2026-09-21 (its era ranges, hooks and
//    aria-labels lost their dashes, brand audit F-09).
const SCAN_SKIP_DIRS = new Set(["games", "revolt", "ig", "node_modules", ".next"]);
// Files that CONSUME dashes rather than render them: history/stats.ts parses
// "1914-1918" style ranges through a RegExp built from a template literal, so
// its character classes have to be able to spell both dashes.
const SCAN_SKIP_FILES = new Set(["stats.ts"]);
/* A dash the reader sees is a dash, however it was spelled in the source. The
   literal characters below were the only forms checked until 2026-09-21, so
   three rendered dashes shipped past this gate: "\u2013" as the chapter-rail
   placeholder in three player surfaces, and &mdash; as the wire separator in
   ComparativeView. Every escape that resolves to one of the two banned
   characters is named here now, so the next one cannot pass by being written
   differently. */
const KILL = [
  ["em dash (U+2014)", /—/],
  ["en dash (U+2013)", /–/],
  ["escaped em dash (\\u2014, \\x{2014}, &mdash;, &#8212;, &#x2014;)",
    /\\u\{?2014\}?|\\x\{2014\}|&mdash;|&#8212;|&#x2014;/i],
  ["escaped en dash (\\u2013, \\x{2013}, &ndash;, &#8211;, &#x2013;)",
    /\\u\{?2013\}?|\\x\{2013\}|&ndash;|&#8211;|&#x2013;/i],
  ["significantly", /\bsignificantly\b/i],
  ["notably", /\bnotably\b/i],
  ["it should be noted", /\bit\s+should\s+be\s+noted\b/i],
  ["interestingly", /\binterestingly\b/i],
  ["crucially", /\bcrucially\b/i],
];

function scanFiles(dir) {
  return readdirSync(dir).flatMap((f) => {
    const p = join(dir, f);
    if (statSync(p).isDirectory()) return SCAN_SKIP_DIRS.has(f) ? [] : scanFiles(p);
    if (!/\.tsx?$/.test(f)) return [];
    if (/^mock/i.test(f) || /\.test\./.test(f) || SCAN_SKIP_FILES.has(f)) return [];
    return [p];
  });
}

/* Blank out comments and regex literals, keep everything else on its own line
   so a hit still reports a usable line number. Quote-aware, so a "//" inside a
   string is not a comment and a "/" after an identifier is division, not the
   start of a regex. */
function strippable(src) {
  let out = "";
  let prev = "";           // last significant code character
  let i = 0;
  while (i < src.length) {
    const c = src[i];
    const c2 = src[i + 1];
    if (c === "/" && c2 === "/") {
      while (i < src.length && src[i] !== "\n") i++;
      continue;
    }
    if (c === "/" && c2 === "*") {
      i += 2;
      while (i < src.length && !(src[i] === "*" && src[i + 1] === "/")) {
        if (src[i] === "\n") out += "\n";
        i++;
      }
      i += 2;
      continue;
    }
    if (c === '"' || c === "'" || c === "`") {
      const q = c;
      out += c;
      i++;
      while (i < src.length) {
        if (src[i] === "\\") { out += src[i] + (src[i + 1] ?? ""); i += 2; continue; }
        out += src[i];
        if (src[i] === q) { i++; break; }
        i++;
      }
      prev = q;
      continue;
    }
    // A regex literal, not division: "/" may only open one where a value may
    // begin. After an identifier, a number, ")" or "]" it is division.
    if (c === "/" && !/[A-Za-z0-9_$)\]'"`]/.test(prev)) {
      i++;
      while (i < src.length && src[i] !== "\n") {
        if (src[i] === "\\") { i += 2; continue; }
        if (src[i] === "[") { while (i < src.length && src[i] !== "]" && src[i] !== "\n") i++; }
        if (src[i] === "/") { i++; break; }
        i++;
      }
      while (i < src.length && /[dgimsuvy]/.test(src[i])) i++;
      prev = ")";
      continue;
    }
    out += c;
    if (!/\s/.test(c)) prev = c;
    i++;
  }
  return out;
}

const dirty = [];
for (const p of scanFiles(join(ROOT, "app"))) {
  strippable(read(p)).split("\n").forEach((line, n) => {
    for (const [label, re] of KILL) {
      if (re.test(line)) dirty.push(`${p.replace(ROOT, "")}:${n + 1} [${label}] ${line.trim().slice(0, 90)}`);
    }
  });
}
ok("no dash or kill-list word in frontend source copy", dirty.length === 0,
   "\n      " + dirty.slice(0, 12).join("\n      "));

if (fail.length) {
  console.error("\n" + fail.map((f) => `FAIL  ${f}`).join("\n"));
  console.error(`\n${fail.length} copy-fact failure(s)`);
  process.exit(1);
}
console.log(`\nPASS  self-descriptive copy agrees with ${sourceRows.length} sources, ${countries.size} countries, feed of ${cfg.displayed}`);
