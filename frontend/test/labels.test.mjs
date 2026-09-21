/**
 * Label and hygiene parity, without a test framework.
 *
 * Two things this file guards, both of which shipped broken:
 *
 * 1. ONE LEAN LADDER. leanToBucket, leanLabel and the deleted tiltLabel and
 *    sigilLabelInfo used to cut the same 0-100 number at three different sets
 *    of boundaries, so a story at lean 60 read "Right" on the feed card,
 *    "Right Tilt" in the Sigil popup and "Center-Right" in the Deep Dive. On
 *    the 2026-09-06 feed every confidently-labelled story disagreed with
 *    itself across surfaces. The assertions below sweep 0..100 and require
 *    the bucket, the label and the abbreviation to agree at every value.
 *
 * 2. THE PYTHON AND TYPESCRIPT SUMMARY HYGIENE AGREE. summaryHygiene.ts and
 *    utils/summary_hygiene.py are hand-kept in lock-step; the fixture list
 *    here is asserted from both sides (tests/test_summary_hygiene_parity.py
 *    runs the same strings through the Python).
 *
 * Run: node test/labels.test.mjs   (compiles the TS it needs first)
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const ROOT = resolve(import.meta.dirname, "..");
const out = mkdtempSync(join(tmpdir(), "void-labels-"));
let failures = 0;

function check(name, cond, detail = "") {
  if (cond) return;
  failures += 1;
  console.log(`FAIL  ${name}${detail ? `: ${detail}` : ""}`);
}

function compile(files) {
  execFileSync("npx", ["tsc", ...files,
    "--outDir", out, "--module", "es2022", "--target", "es2022",
    "--moduleResolution", "bundler", "--skipLibCheck"],
    { cwd: ROOT, stdio: "pipe" });
}

// biasColors reads CSS variables through getColors(); under Node there is no
// document, so it falls back to the SSR palette. No stub needed.
compile(["app/lib/biasColors.ts", "app/lib/summaryHygiene.ts"]);

const bias = await import(pathToFileURL(join(out, "biasColors.js")).href);
const hygiene = await import(pathToFileURL(join(out, "summaryHygiene.js")).href);

/* ---- 1. one ladder ---------------------------------------------------- */

const BANDS = [
  [0, 20, "far-left", "Far Left", "FL"],
  [21, 35, "left", "Left", "L"],
  [36, 45, "center-left", "Center-Left", "CL"],
  [46, 55, "center", "Center", "C"],
  [56, 65, "center-right", "Center-Right", "CR"],
  [66, 80, "right", "Right", "R"],
  [81, 100, "far-right", "Far Right", "FR"],
];

for (const [lo, hi, bucket, label, abbr] of BANDS) {
  for (let v = lo; v <= hi; v++) {
    check(`leanToBucket(${v})`, bias.leanToBucket(v) === bucket, bias.leanToBucket(v));
    check(`leanLabel(${v})`, bias.leanLabel(v) === label, bias.leanLabel(v));
    check(`leanLabelAbbr(${v})`, bias.leanLabelAbbr(v) === abbr, bias.leanLabelAbbr(v));
  }
}

// tiltToBucket survives only as an alias. If it ever becomes a second ladder
// again, this fails at the first value where they diverge.
for (let v = 0; v <= 100; v++) {
  check(`tiltToBucket(${v}) is leanToBucket`,
    bias.tiltToBucket(v) === bias.leanToBucket(v));
}

// tiltDescriptor must describe the band the label names, never another one.
const LEFTISH = new Set(["far-left", "left", "center-left"]);
const RIGHTISH = new Set(["far-right", "right", "center-right"]);
for (let v = 0; v <= 100; v++) {
  const d = bias.tiltDescriptor(v).toLowerCase();
  const b = bias.leanToBucket(v);
  if (LEFTISH.has(b)) check(`tiltDescriptor(${v}) says left`, d.includes("left"), d);
  else if (RIGHTISH.has(b)) check(`tiltDescriptor(${v}) says right`, d.includes("right"), d);
  else check(`tiltDescriptor(${v}) says balanced`, d.includes("balanced"), d);
}

/* ---- storyLeanLabel is the gate AND the ladder ------------------------- */

const wide = { leanLeftCount: 2, leanCenterCount: 4, leanRightCount: 9,
               polarization: 40, aggregateConfidence: 0.8, leanMeasuredCount: 15 };

const confident = bias.storyLeanLabel(62, wide, 20);
check("confident label uses the one ladder",
  confident.text === bias.leanLabel(62) && confident.abbr === bias.leanLabelAbbr(62),
  `${confident.text}/${confident.abbr}`);
check("confident label is not suppressed", confident.suppressed === false);

// 4b: the lean must be MEASURED from at least LABEL_MIN_MEASURED articles.
const thin = { ...wide, leanMeasuredCount: bias.LABEL_MIN_MEASURED - 1 };
check("a lean measured from too few articles is suppressed",
  bias.storyLeanLabel(62, thin, 20).suppressed === true);
check("... and says so: Not measured, never Balanced",
  bias.storyLeanLabel(62, thin, 20).text === "Not measured" &&
  bias.storyLeanLabel(62, thin, 20).state === "unmeasured");
check("a measured story at the centre reads Balanced",
  bias.storyLeanLabel(50, { leanLeftCount: 3, leanCenterCount: 6, leanRightCount: 3,
                            polarization: 5, aggregateConfidence: 0.9,
                            leanMeasuredCount: 20 }, 20).text === "Balanced");
check("the word Flat is gone",
  !Object.values(bias).some((v) => v === "Flat"));
const atFloor = { ...wide, leanMeasuredCount: bias.LABEL_MIN_MEASURED };
check("exactly LABEL_MIN_MEASURED is enough",
  bias.storyLeanLabel(62, atFloor, 20).suppressed === false);
check("a payload with no measured count keeps the old behaviour",
  bias.storyLeanLabel(62, { ...wide, leanMeasuredCount: undefined }, 20)
    .suppressed === false);

check("unscored beats everything",
  bias.storyLeanLabel(62, wide, 20, true).text === "Unscored");
check("a suppressed label withholds the score",
  bias.storyLeanLabel(50, { leanLeftCount: 0, leanCenterCount: 5, leanRightCount: 0,
                            polarization: 0, aggregateConfidence: 0.9,
                            leanMeasuredCount: 20 }, 20).suppressed === true);

/* ---- leanShareTilt: wings only, and enough of them -------------------- */
/*
   The denominator was left + center + right until 2026-09-21, so neutral wire
   volume diluted a real split out of existence: a story carried 14 left to 5
   right landed at 0.153 against a 0.20 threshold purely because 40 centre
   articles sat in the denominator, while a nearly identical 16:6 story passed.

   Fixing the denominator alone trades that for a worse lie, which is why
   LABEL_MIN_WING_ARTICLES exists: measured on the 2026-09-20 feed, five
   clusters had one or two wing articles and would have read as a FULLY
   lopsided roster (tilt +/-1.0) on the new denominator. Those cases are here
   by number.
*/
const tilt = (L, C, R) => bias.leanShareTilt(
  { leanLeftCount: L, leanCenterCount: C, leanRightCount: R });

check("wire volume no longer dilutes a real split",
  Math.abs(tilt(14, 40, 5) + 9 / 19) < 1e-9,
  `14L/40C/5R -> ${tilt(14, 40, 5)}`);
check("... and that split now clears the threshold",
  Math.abs(tilt(14, 40, 5)) >= bias.LABEL_MIN_SHARE_TILT);
check("a symmetric roster reads zero", tilt(6, 30, 6) === 0);

/* The five shapes from the measured feed that MUST stay silent. */
check("one left article out of six is not a lopsided roster",
  tilt(1, 5, 0) === 0, `1L/5C/0R -> ${tilt(1, 5, 0)}`);
check("two left out of nine is not a lopsided roster",
  tilt(2, 7, 0) === 0, `2L/7C/0R -> ${tilt(2, 7, 0)}`);
check("one right article out of three is not a lopsided roster",
  tilt(0, 2, 1) === 0, `0C/2C/1R -> ${tilt(0, 2, 1)}`);
check("three left out of eight is not a lopsided roster",
  tilt(3, 5, 0) === 0, `3L/5C/0R -> ${tilt(3, 5, 0)}`);
check("exactly LABEL_MIN_WING_ARTICLES wings is enough to read",
  tilt(0, 10, bias.LABEL_MIN_WING_ARTICLES) === 1,
  `0L/10C/${bias.LABEL_MIN_WING_ARTICLES}R -> ${tilt(0, 10, bias.LABEL_MIN_WING_ARTICLES)}`);
check("one wing short of the floor reads zero",
  tilt(0, 10, bias.LABEL_MIN_WING_ARTICLES - 1) === 0);

/* The threshold was re-derived for the new denominator, not carried over:
   on wings-only, 3:2 is not lopsided and 4:1 is. */
check("a 3:2 wing split is not lopsided",
  Math.abs(tilt(3, 20, 2)) < bias.LABEL_MIN_SHARE_TILT,
  `3L/2R -> ${tilt(3, 20, 2)}`);
check("a 4:1 wing split is lopsided",
  Math.abs(tilt(1, 20, 4)) >= bias.LABEL_MIN_SHARE_TILT,
  `1L/4R -> ${tilt(1, 20, 4)}`);
check("the full analyzed count still gates a three-article cluster",
  tilt(1, 0, 1) === 0);
check("no spread at all reads zero", bias.leanShareTilt(null) === 0);

/* End to end: the two cards that changed state on the measured feed, and one
   that correctly did not. Route 2 also needs the mean to agree in sign. */
const lopsidedLeft = { leanLeftCount: 12, leanCenterCount: 78, leanRightCount: 5,
                       polarization: 11, aggregateConfidence: 0.67,
                       leanMeasuredCount: 95 };
check("12 left vs 5 right across 72 sources reads a direction",
  bias.storyLeanLabel(48, lopsidedLeft, 72).state === "confident",
  bias.storyLeanLabel(48, lopsidedLeft, 72).text);
const allRight = { leanLeftCount: 0, leanCenterCount: 29, leanRightCount: 6,
                   polarization: 0, aggregateConfidence: 0.65,
                   leanMeasuredCount: 35 };
check("0 left vs 6 right across 24 sources reads a direction",
  bias.storyLeanLabel(55, allRight, 24).state === "confident",
  bias.storyLeanLabel(55, allRight, 24).text);
const oneWing = { leanLeftCount: 1, leanCenterCount: 11, leanRightCount: 0,
                  polarization: 0, aggregateConfidence: 0.67,
                  leanMeasuredCount: 12 };
check("one wing article does NOT read a direction",
  bias.storyLeanLabel(49, oneWing, 10).state !== "confident",
  bias.storyLeanLabel(49, oneWing, 10).text);

/* ---- 2. summary hygiene parity ---------------------------------------- */

// The Python side asserts the SAME expectations on the same strings.
const RAW_EXCERPT = [
  "Sign up for our newsletter to get the day's top stories.",
  "Why it matters: the vote splits the caucus three ways.",
  "The minister resigned on Tuesday. Photo: Getty Images",
  "Troops entered the city at dawn - reuters.com",
  "The council met on Tuesday (Ahmed Gomaa/Anadolu)",
  "The governmentSaid the investigationContinues into the collapse.",
];
const CLEAN = [
  "The Senate voted 61 to 38 on Tuesday to confirm the nominee. Two Republicans crossed over.",
  "Pfizer said the mRNA candidate cut hospitalisations by 42 percent in the mRNA arm of the trial.",
  "Apple shipped 4.2 million iPhone units in the quarter, up from 3.8 million a year earlier.",
];
for (const s of RAW_EXCERPT) {
  check(`isRawExcerpt(${s.slice(0, 28)}...)`, hygiene.isRawExcerpt(s) === true);
}
for (const s of CLEAN) {
  check(`clean summary kept (${s.slice(0, 28)}...)`, hygiene.isRawExcerpt(s) === false);
}

writeFileSync(join(out, ".done"), "");
rmSync(out, { recursive: true, force: true });

if (failures) {
  console.log(`\n${failures} label/hygiene parity failure(s)`);
  process.exit(1);
}
console.log("PASS  one lean ladder across 0..100, storyLeanLabel gate, hygiene parity");
