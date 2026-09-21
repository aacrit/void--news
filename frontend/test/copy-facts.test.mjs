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
const stale = files.filter((p) =>
  /\b(?:50|fifty)\s+stories\b|\btop\s+50\b/i.test(read(p)));
ok("no component restates the feed size in prose",
   stale.length === 0, stale.map((p) => p.replace(ROOT, "")).join(", "));

// 2. The source and country counts the copy states must match the roster.
const countries = new Set(sourceRows.map((s) => s.country).filter(Boolean));
for (const p of files) {
  const txt = read(p);
  for (const m of txt.matchAll(/\b(1,?0\d\d)\s+sources\b/g)) {
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

if (fail.length) {
  console.error("\n" + fail.map((f) => `FAIL  ${f}`).join("\n"));
  console.error(`\n${fail.length} copy-fact failure(s)`);
  process.exit(1);
}
console.log(`\nPASS  self-descriptive copy agrees with ${sourceRows.length} sources, ${countries.size} countries, feed of ${cfg.displayed}`);
