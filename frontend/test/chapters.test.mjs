/**
 * Chapter rail arithmetic, without a test framework.
 *
 * The On Air daily brief is a radio show with real chapters. Every player
 * surface (the /onair rail, the FloatingPlayer, the mobile strip, the lock
 * screen metadata) answers the same question from the same helper: given a
 * playhead in seconds, which chapter is on air? That helper is pure and lives
 * in app/lib/chapters.ts precisely so it can be asserted here.
 *
 * What this guards:
 *
 * 1. THE LEGACY CASE STAYS LEGACY. A null / empty / malformed chapter list
 *    must degrade to "no chapters" at every entry point, never throw and never
 *    invent a chapter. Weekly issues, history accounts and every episode
 *    recorded before the rebuild rely on that to keep the old News / Opinion
 *    transport. A thrown error here would take down the whole player.
 *
 * 2. NOTHING IS FABRICATED. -1 means the reader is between chapters (in the
 *    ident, in a gap, past a declared end). The player shows the show name
 *    there. The predecessor of this rail drew an "Opinion" mark at 60% of the
 *    episode whenever the real timestamp was missing, pointing readers at a
 *    moment nobody had measured; these assertions pin the boundaries so a
 *    guess cannot creep back in.
 *
 * Run: node test/chapters.test.mjs   (compiles the TS it needs first)
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, readdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const ROOT = resolve(import.meta.dirname, "..");
const out = mkdtempSync(join(tmpdir(), "void-chapters-"));
let failures = 0;

function check(name, cond, detail = "") {
  if (cond) return;
  failures += 1;
  console.log(`FAIL  ${name}${detail ? `: ${detail}` : ""}`);
}

execFileSync("npx", ["tsc", "app/lib/chapters.ts",
  "--outDir", out, "--module", "es2022", "--target", "es2022",
  "--moduleResolution", "bundler", "--skipLibCheck"],
  { cwd: ROOT, stdio: "pipe" });

/* tsc puts the output at a path relative to the COMMON ROOT of everything it
   pulled in, so chapters.js lands at the top of outDir only while every import
   chain stays inside app/lib. It does not: lib/types.ts re-exports the weekly
   types from app/weekly/types.ts, which moves the common root to app/ and the
   emitted file to <out>/lib/chapters.js. This test asserts what chapters.ts
   DOES, not where tsc happens to put it, so it finds the file. */
function findEmitted(dir, name) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) {
      const hit = findEmitted(path, name);
      if (hit) return hit;
    } else if (entry.name === name) {
      return path;
    }
  }
  return null;
}

const emitted = findEmitted(out, "chapters.js");
if (!emitted) {
  console.log("FAIL  tsc emitted no chapters.js");
  process.exit(1);
}
const ch = await import(pathToFileURL(emitted).href);

/* A realistic running order: ident and sign-on run to 0:18, then the menu,
   five stories, the briefs, the closer, the editorial. */
const SHOW = [
  { startTime: 18,   title: "Headlines",            kind: "headlines" },
  { startTime: 52,   title: "Fed raises rates",     kind: "story", rank: 1, url: "/story/aaa/" },
  { startTime: 214,  title: "Gaza ceasefire talks", kind: "story", rank: 2 },
  { startTime: 366,  title: "Delhi air quality",    kind: "story", rank: 3 },
  { startTime: 498,  title: "Also today",           kind: "briefs" },
  { startTime: 612,  title: "And finally",          kind: "finally" },
  { startTime: 690,  title: "Opinion",              kind: "opinion",
    subtitle: "The deficit is a choice" },
];
const DURATION = 840;

/* ---- 1. the legacy case degrades, it does not throw -------------------- */

for (const empty of [null, undefined, []]) {
  const tag = JSON.stringify(empty);
  check(`findChapterIndex(${tag}) is -1`, ch.findChapterIndex(empty, 30) === -1);
  check(`chapterProgress(${tag}) is 0`, ch.chapterProgress(empty, 0, 30) === 0);
  check(`chapterMarks(${tag}) is empty`, ch.chapterMarks(empty, DURATION).length === 0);
  check(`findEditorialIndex(${tag}) is -1`, ch.findOpinionIndex(empty) === -1);
  check(`chapterEnd(${tag}) is null`, ch.chapterEnd(empty, 0, DURATION) === null);
}

check("coerceChapters(null) is null", ch.coerceChapters(null) === null);
check("coerceChapters([]) is null", ch.coerceChapters([]) === null);
check("coerceChapters of a non-array is null", ch.coerceChapters({ startTime: 0 }) === null);
check("coerceChapters of broken JSON is null", ch.coerceChapters("{not json") === null);
check("coerceChapters of a JSON string parses",
  ch.coerceChapters(JSON.stringify(SHOW))?.length === SHOW.length);
check("coerceChapters keeps a real array", ch.coerceChapters(SHOW)?.length === SHOW.length);
check("coerceChapters drops entries with no usable start",
  ch.coerceChapters([{ title: "x", kind: "story" }, { startTime: 5, title: "y", kind: "story" }])
    ?.length === 1);
check("coerceChapters of an all-broken array is null",
  ch.coerceChapters([{ title: "x" }, { startTime: "12" }]) === null);

/* ---- 2. which chapter is on air --------------------------------------- */

check("before the first chapter is -1 (the ident)", ch.findChapterIndex(SHOW, 0) === -1);
check("one second before chapter 1 is still -1", ch.findChapterIndex(SHOW, 17.9) === -1);
check("the boundary belongs to the chapter it opens", ch.findChapterIndex(SHOW, 18) === 0);
check("inside the headlines", ch.findChapterIndex(SHOW, 40) === 0);
check("the second boundary", ch.findChapterIndex(SHOW, 52) === 1);
check("mid-story", ch.findChapterIndex(SHOW, 100) === 1);
check("last chapter runs to the end of the file", ch.findChapterIndex(SHOW, 839) === 6);
check("past the file is still the last chapter (no declared end)",
  ch.findChapterIndex(SHOW, 100000) === 6);

// Sweep: the index must never move backwards as the playhead advances.
let prev = -1;
for (let t = 0; t <= DURATION; t += 0.5) {
  const i = ch.findChapterIndex(SHOW, t);
  check(`monotonic at ${t}`, i >= prev, `${prev} -> ${i}`);
  prev = i;
}

// Garbage playheads never produce a chapter.
for (const bad of [-1, NaN, Infinity, "42", null, undefined]) {
  check(`findChapterIndex(t=${String(bad)}) is -1`, ch.findChapterIndex(SHOW, bad) === -1);
}

/* ---- 3. declared ends are honoured (a gap is not a chapter) ------------ */

const WITH_END = [
  { startTime: 10, endTime: 40, title: "Headlines", kind: "headlines" },
  { startTime: 90, title: "Fed raises rates", kind: "story", rank: 1 },
];
check("inside a chapter that declares its end", ch.findChapterIndex(WITH_END, 39) === 0);
check("at its declared end the reader is between chapters",
  ch.findChapterIndex(WITH_END, 40) === -1);
check("in the gap, still between chapters", ch.findChapterIndex(WITH_END, 75) === -1);
check("the next chapter picks up at its start", ch.findChapterIndex(WITH_END, 90) === 1);

/* ---- 4. progress through a chapter ------------------------------------ */

check("progress before the chapter is 0", ch.chapterProgress(SHOW, 1, 52, DURATION) === 0);
check("progress at the midpoint is 0.5",
  Math.abs(ch.chapterProgress(SHOW, 1, (52 + 214) / 2, DURATION) - 0.5) < 1e-9,
  String(ch.chapterProgress(SHOW, 1, (52 + 214) / 2, DURATION)));
check("progress at the next chapter's start is 1",
  ch.chapterProgress(SHOW, 1, 214, DURATION) === 1);
check("the final chapter measures against the duration",
  Math.abs(ch.chapterProgress(SHOW, 6, 765, DURATION) - 0.5) < 1e-9,
  String(ch.chapterProgress(SHOW, 6, 765, DURATION)));
check("with no duration the final chapter has no measurable length",
  ch.chapterProgress(SHOW, 6, 765) === 0);
check("an out-of-range index is 0", ch.chapterProgress(SHOW, 99, 100, DURATION) === 0);

// Progress is always a fraction, never a percentage and never out of band.
for (let t = 0; t <= DURATION; t += 1) {
  const i = ch.findChapterIndex(SHOW, t);
  if (i < 0) continue;
  const p = ch.chapterProgress(SHOW, i, t, DURATION);
  check(`progress in band at ${t}`, p >= 0 && p <= 1, String(p));
}

/* ---- 5. ends ----------------------------------------------------------- */

check("chapterEnd prefers the next start", ch.chapterEnd(SHOW, 1, DURATION) === 214);
check("chapterEnd prefers its own endTime", ch.chapterEnd(WITH_END, 0, 200) === 40);
check("chapterEnd falls back to the duration", ch.chapterEnd(SHOW, 6, DURATION) === DURATION);
check("chapterEnd with nothing to go on is null", ch.chapterEnd(SHOW, 6, null) === null);

/* ---- 6. seek marks ----------------------------------------------------- */

const marks = ch.chapterMarks(SHOW, DURATION);
check("one mark per chapter", marks.length === SHOW.length);
check("marks are percentages of the episode",
  Math.abs(marks[1].pct - (52 / 840) * 100) < 1e-9, String(marks[1].pct));
check("every mark sits on the bar",
  marks.every((m) => m.pct >= 0 && m.pct <= 100));
check("marks carry their index", marks[3].index === 3);
check("an unknown duration draws no marks", ch.chapterMarks(SHOW, null).length === 0);
check("a zero duration draws no marks", ch.chapterMarks(SHOW, 0).length === 0);
check("a chapter past the known duration is dropped, not stacked on the end",
  ch.chapterMarks([{ startTime: 10, title: "a", kind: "story" },
                   { startTime: 900, title: "b", kind: "story" }], DURATION).length === 1);

/* ---- 7. the editorial jump -------------------------------------------- */

check("the opinion chapter is found", ch.findOpinionIndex(SHOW) === 6);
// Episodes rendered before 2026-09-19 carry kind "editorial"; the jump and the
// label must keep resolving for them or the two shows already on the CDN lose
// their Opinion button.
const LEGACY = SHOW.map((c) => (c.kind === "opinion" ? { ...c, kind: "editorial", title: "Editorial" } : c));
check("a legacy editorial chapter still resolves", ch.findOpinionIndex(LEGACY) === 6);
check("legacy label reads Opinion", ch.chapterKindLabel(LEGACY[6]) === "Opinion");
check("a show with no opinion reports -1",
  ch.findOpinionIndex(SHOW.filter((c) => c.kind !== "opinion")) === -1);
check("the opinion start is where opinion_start_seconds points",
  SHOW[ch.findOpinionIndex(SHOW)].startTime === 690);

/* ---- 8. labels and timecodes ------------------------------------------ */

check("a story row names its rank", ch.chapterKindLabel(SHOW[1]) === "No. 1");
check("a rankless story still has a label",
  ch.chapterKindLabel({ startTime: 0, title: "x", kind: "story" }) === "Story");
check("headlines label", ch.chapterKindLabel(SHOW[0]) === "Headlines");
check("briefs label", ch.chapterKindLabel(SHOW[4]) === "In brief");
check("finally label", ch.chapterKindLabel(SHOW[5]) === "Finally");
check("opinion label", ch.chapterKindLabel(SHOW[6]) === "Opinion");

check("timecode pads the seconds", ch.formatChapterTime(690) === "11:30");
check("timecode of zero", ch.formatChapterTime(0) === "0:00");
check("timecode floors", ch.formatChapterTime(59.9) === "0:59");
check("a garbage timecode reads 0:00", ch.formatChapterTime(NaN) === "0:00");
check("a negative timecode reads 0:00", ch.formatChapterTime(-5) === "0:00");

/* ---- 9. unsorted input still resolves --------------------------------- */

const SHUFFLED = [SHOW[3], SHOW[0], SHOW[6], SHOW[1], SHOW[5], SHOW[2], SHOW[4]];
for (let t = 0; t <= DURATION; t += 7) {
  const a = ch.findChapterIndex(SHOW, t);
  const b = ch.findChapterIndex(SHUFFLED, t);
  const same = a === -1 ? b === -1 : SHUFFLED[b]?.startTime === SHOW[a].startTime;
  check(`order-independent at ${t}`, same, `${a} vs ${b}`);
}

rmSync(out, { recursive: true, force: true });

if (failures) {
  console.log(`\n${failures} chapter rail failure(s)`);
  process.exit(1);
}
console.log("PASS  chapter index, progress, marks, editorial jump, legacy degradation");
