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
