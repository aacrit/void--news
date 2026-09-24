/**
 * A mark drawn from a headline must not be drawn as a reading of an article.
 *
 * WHAT SHIPPED BROKEN. `bias_scores.confidence` is `min(1, word_count / 150)`:
 * the share of the text's movement budget an article was long enough to earn.
 * It is exported per article, `DeepDive` folds it into a composite `coverage`
 * number, and `DeepDiveSpectrum` declared it on its props and never read it. So
 * the Bench drew a mark placed from an 11-word RSS stub identically to one read
 * off a 900-word article: same column, same colour, same tooltip, no difference
 * a reader could see.
 *
 * That is not cosmetic. Measured 2026-09-23 against run #375: 367 outlets have
 * 20+ articles and ZERO reaching 150 words, 13 of them us_major (AP, Reuters,
 * the NYT, the Washington Post, the WSJ, CNN, Bloomberg, USA Today, UPI, The
 * Hill, Chicago Tribune, HuffPost, Newsmax). They block non-browser clients.
 * 334 of the 367 reach the front page. Every one of those marks asserted a
 * reading Void had not taken.
 *
 * WHAT IS ASSERTED HERE.
 *   1. The cut agrees with the pipeline's own full-confidence word count, read
 *      out of political_lean.py rather than copied into this file.
 *   2. A missing confidence reads as `headline`, never as `article`. An export
 *      that carries no value cannot support the claim that we had the text.
 *   3. The note fires on exactly one side of the cut, and carries no dash.
 *   4. The three consumers agree: the mark's data attribute, the detail card
 *      and the screen-reader label all come from the one function, and the CSS
 *      carries a rule for the state the mark can be in.
 *
 * Run: node test/text-authority.test.mjs
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const ROOT = resolve(import.meta.dirname, "..");
const REPO = resolve(ROOT, "..");
const out = mkdtempSync(join(tmpdir(), "void-authority-"));
let failures = 0;

function check(name, cond, detail = "") {
  if (cond) return;
  failures += 1;
  console.log(`FAIL  ${name}${detail ? `: ${detail}` : ""}`);
}

execFileSync("npx", ["tsc", "app/lib/textAuthority.ts",
  "--outDir", out, "--module", "es2022", "--target", "es2022",
  "--moduleResolution", "bundler", "--skipLibCheck"],
  { cwd: ROOT, stdio: "pipe" });
const ta = await import(pathToFileURL(join(out, "textAuthority.js")).href);

/* ---- 1. the cut is the pipeline's, not a second opinion ---------------- */

const lean = readFileSync(join(REPO, "pipeline/analyzers/political_lean.py"), "utf8");
const m = lean.match(/_LENGTH_FULL_CONFIDENCE\s*=\s*(\d+)/);
check("political_lean.py still names _LENGTH_FULL_CONFIDENCE", !!m);
if (m) {
  check("the word count agrees with the pipeline",
    Number(m[1]) === ta.FULL_CONFIDENCE_WORDS,
    `pipeline ${m[1]}, textAuthority.ts ${ta.FULL_CONFIDENCE_WORDS}`);
}
check("the cut is inside 0..1 and not a degenerate bound",
  ta.AUTHORITY_CUT > 0 && ta.AUTHORITY_CUT < 1);

/* ---- 2. absence is never read as evidence ----------------------------- */

for (const missing of [undefined, null, NaN]) {
  check(`a missing confidence (${String(missing)}) reads as headline`,
    ta.textAuthority(missing) === "headline", ta.textAuthority(missing));
}

/* ---- 3. the two states, and nothing in between ------------------------ */

const CUT = ta.AUTHORITY_CUT;
const cases = [
  [0, "headline"], [0.07, "headline"], [CUT - 0.001, "headline"],
  [CUT, "article"], [0.8, "article"], [1, "article"],
];
for (const [c, want] of cases) {
  check(`confidence ${c} reads as ${want}`, ta.textAuthority(c) === want,
    ta.textAuthority(c));
}
for (let i = 0; i <= 100; i += 1) {
  const v = i / 100;
  const got = ta.textAuthority(v);
  check(`every value is one of the two states (${v})`,
    got === "article" || got === "headline", got);
  check(`the note fires exactly on the headline side (${v})`,
    (ta.authorityNote(v) === null) === (got === "article"));
}

/* The note is page-facing prose, so the dash ban applies to it. */
const note = ta.authorityNote(0);
check("the note exists", typeof note === "string" && note.length > 0);
check("the note carries no dash", !/[–—]/.test(note || ""), note || "");

check("headlineOnlyCount counts the headline side",
  ta.headlineOnlyCount([{ confidence: 1 }, { confidence: 0.1 }, {}]) === 2);

/* ---- 4. the consumers all come from this one function ----------------- */

const bench = readFileSync(join(ROOT, "app/components/Bench.tsx"), "utf8");
const spectrum = readFileSync(join(ROOT, "app/components/DeepDiveSpectrum.tsx"), "utf8");
const css = readFileSync(join(ROOT, "app/styles/bench.css"), "utf8");

check("Bench imports the one definition", /from "\.\.\/lib\/textAuthority"/.test(bench));
check("the mark carries the state as an attribute", /data-authority=/.test(bench));
check("the detail card carries the note", /authorityNote\(/.test(bench));
check("the head states the count", /headlineOnlyCount\(/.test(bench));
check("the screen-reader label says it too",
  /scored from the headline/.test(bench));
check("BenchSource carries confidence", /confidence\?: number/.test(bench));
check("DeepDiveSpectrum passes confidence through, it does not drop it",
  /confidence: s\.confidence/.test(spectrum));
check("the CSS draws the headline state differently",
  /\[data-authority="headline"\]/.test(css));
/* The mark must keep its lean colour: the column it sits in is the reading,
   and a second hue would be a second, disagreeing claim about its politics. */
const rule = css.slice(css.indexOf('[data-authority="headline"]'));
check("the headline state spends no bias colour",
  !/--bias-/.test(rule.slice(0, rule.indexOf("}"))));

rmSync(out, { recursive: true, force: true });
console.log(failures ? `\n${failures} failure(s)` : "\ntext authority: all checks pass");
process.exit(failures ? 1 : 0);
