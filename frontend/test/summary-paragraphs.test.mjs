/* ===========================================================================
   summary-paragraphs.test.mjs: the Deep Dive's paragraphs never change a word.

   lib/summaryParagraphs.ts splits a one-string summary into a lede and
   paragraphs in the renderer. Because it touches every story's text, the
   control runs over the REAL summaries: today's feed and the whole printed
   archive (build-data/feed.json, build-data/archive.json).

     - joined back with single spaces, the paragraphs ARE the input with its
       whitespace runs collapsed, exactly (Rule 1: a split may read badly, it
       may never change the text);
     - no break directly after an abbreviation or an initial ("U.S.", "Dr.",
       "Ihor M."), and none inside an open quotation;
     - a summary over 120 words gets at least two paragraphs;
     - no body paragraph (after the lede) is under 25 words;
     - a protected range (a disputed-claim mark) is never split.
   Also: splitSummaryForCard shows whole sentences and keeps the rest.
   =========================================================================== */
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, readFileSync, writeFileSync, existsSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const ROOT = resolve(import.meta.dirname, "..");
const out = mkdtempSync(join(tmpdir(), "void-paras-"));
let failures = 0;
function check(name, cond, detail = "") {
  if (cond) return;
  failures += 1;
  if (failures <= 25) console.log(`FAIL  ${name}${detail ? `: ${detail}` : ""}`);
}

execFileSync("npx", ["tsc", join(ROOT, "app/lib/summaryParagraphs.ts"), join(ROOT, "app/lib/utils.ts"),
  "--outDir", out, "--module", "es2022", "--target", "es2022",
  "--moduleResolution", "bundler", "--skipLibCheck"], { stdio: "inherit" });
/* The sources import each other without extensions (the bundler resolves
   them); Node's ESM loader does not, so the compiled files get ".js". */
for (const dir of [out, join(out, "lib"), join(out, "app/lib")]) {
  if (!existsSync(dir)) continue;
  for (const f of readdirSync(dir).filter((x) => x.endsWith(".js"))) {
    const p = join(dir, f);
    writeFileSync(p, readFileSync(p, "utf8").replace(/(from\s+["']\.\/[\w-]+)(["'])/g, "$1.js$2"));
  }
}
const find = (name) => {
  for (const p of [join(out, name), join(out, "lib", name), join(out, "app/lib", name)]) if (existsSync(p)) return p;
  throw new Error(`compiled ${name} not found under ${out}`);
};
const { summaryParagraphs } = await import(pathToFileURL(find("summaryParagraphs.js")).href);
const { splitSummaryForCard } = await import(pathToFileURL(find("utils.js")).href);

const collapse = (s) => s.replace(/\s+/g, " ").trim();
const words = (s) => (s.match(/\S+/g) ?? []).length;

const summaries = [];
for (const f of ["build-data/feed.json", "build-data/archive.json"]) {
  const p = join(ROOT, f);
  if (!existsSync(p)) continue;
  const d = JSON.parse(readFileSync(p, "utf8"));
  const rows = Array.isArray(d) ? d : d.clusters ?? [];
  for (const r of rows) if (typeof r.summary === "string" && r.summary.trim()) summaries.push(r.summary);
}
check("there are real summaries to test", summaries.length > 20, `${summaries.length}`);

const ABBREV_END = /(?:\b[A-Z][a-z]{0,2}|\b(?:[A-Za-z]\.)+[A-Za-z]|\bNo|\bvs|\betc)\.$/;
let split = 0;
for (const s of summaries) {
  const { paragraphs, offsets } = summaryParagraphs(s);
  check("text unchanged", collapse(paragraphs.join(" ")) === collapse(s), s.slice(0, 60));
  check("offsets point at their paragraphs", paragraphs.every((p, i) => s.slice(offsets[i], offsets[i] + p.length) === p), s.slice(0, 60));
  for (let i = 0; i < paragraphs.length - 1; i++) {
    const p = paragraphs[i];
    check("no break after an abbreviation or initial", !ABBREV_END.test(p), p.slice(-30));
    const upto = s.slice(0, offsets[i] + p.length);
    const straight = (upto.match(/"/g) ?? []).length % 2 === 1;
    const curly = (upto.match(/“/g) ?? []).length > (upto.match(/”/g) ?? []).length;
    check("no break inside a quotation", !straight && !curly, p.slice(-40));
  }
  if (words(s) > 120) check("long summaries get paragraphs", paragraphs.length >= 2, `${words(s)} words, ${paragraphs.length} paragraph`);
  paragraphs.forEach((p, i) => {
    // The lede (paragraph 0) is short by design: one sentence, or two when
    // the first is under 15 words. Only the body paragraphs have a floor.
    if (paragraphs.length > 1 && i > 0) check("no stub paragraph", words(p) >= 25, `${words(p)} words: ${p.slice(0, 50)}`);
  });
  if (paragraphs.length > 1) split += 1;
}

// Planted cases.
const planted = "The U.S. Senate met on Thursday. " + "Senators debated the measure at length and in detail today. ".repeat(12) + "Dr. Smith said \"The vote. It failed.\" and left. " + "Then the chamber adjourned for the week after the vote. ".repeat(6);
const pp = summaryParagraphs(planted);
check("planted: text unchanged", collapse(pp.paragraphs.join(" ")) === collapse(planted));
check("planted: no break after U.S.", !pp.paragraphs.some((p) => /U\.S\.$/.test(p)));
check("planted: no break inside the quote", !pp.paragraphs.some((p) => /"The vote\.$/.test(p)));
const protStart = planted.indexOf("Senators debated");
const protEnd = planted.indexOf("Dr. Smith");
const prot = summaryParagraphs(planted, [{ start: protStart, end: protEnd }]);
check("planted: a protected range is never split", prot.offsets.every((o) => o <= protStart || o >= protEnd));

// Card summaries: whole sentences shown, nothing lost.
for (const s of summaries.slice(0, 400)) {
  const [shown, rest] = splitSummaryForCard(s, 170);
  check("card split loses nothing", shown + rest === s.trim(), s.slice(0, 50));
  if (rest) check("card shows whole sentences", /[.!?]["”’)]?$/.test(shown), shown.slice(-30));
}

rmSync(out, { recursive: true, force: true });
if (failures) {
  console.log(`FAIL  summary paragraphs: ${failures} problem(s) over ${summaries.length} summaries`);
  process.exit(1);
}
console.log(`PASS  summary paragraphs: ${summaries.length} real summaries, text unchanged, ${split} split, no break inside an abbreviation, a quote or a mark`);
