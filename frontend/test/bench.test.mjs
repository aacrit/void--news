/**
 * The Bench's packing arithmetic.
 *
 * The Bench is a unit histogram: one mark per source, stacked in the column of
 * its lean rung, column height = count. That reading only survives if every
 * mark in a story is the same size, and the page only holds it if that size is
 * chosen from the data. `packBench` is where both happen, so this file holds
 * it to the corpus it was designed against.
 *
 * The corpus: the 2026-09-21 feed, 35 clusters, one entry per source name,
 * `lean_unscored` rows excluded. The busiest bucket in a story runs 2..40,
 * median 11. Those are the numbers in BUSIEST below; regenerate with
 *   python3 tests/bench_corpus.py
 *
 * Run: node test/bench.test.mjs   (compiles the TS it needs first)
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const ROOT = resolve(import.meta.dirname, "..");
const out = mkdtempSync(join(tmpdir(), "void-bench-"));
let failures = 0;

function check(name, cond, detail = "") {
  if (cond) return;
  failures += 1;
  console.log(`FAIL  ${name}${detail ? `: ${detail}` : ""}`);
}

execFileSync("npx", ["tsc", "app/lib/bench.ts",
  "--outDir", out, "--module", "es2022", "--target", "es2022",
  "--moduleResolution", "bundler", "--skipLibCheck"],
  { cwd: ROOT, stdio: "pipe" });

const {
  packBench, benchRows, BENCH_MARK_MAX, BENCH_MARK_MIN, BENCH_GAP,
} = await import(pathToFileURL(join(out, "bench.js")).href);

/* The tallest bucket in each of the 35 clusters on the 2026-09-21 feed. */
const BUSIEST = [
  40, 35, 34, 30, 27, 25, 22, 22, 20, 19, 14, 14, 13, 13, 12, 12, 11, 11,
  10, 10, 10, 9, 8, 7, 7, 7, 6, 6, 6, 5, 5, 5, 4, 4, 2,
];

/* The two geometries the component actually mounts in: a Deep Dive modal at
   1024px and up, and a phone. Column width is (width - 6*gap) / 7. */
const DESKTOP = { colWidth: (640 - 6 * 8) / 7, maxHeight: 176 };
const PHONE = { colWidth: (340 - 6 * 4) / 7, maxHeight: 132 };
const EXPANDED_DESKTOP = { colWidth: DESKTOP.colWidth, maxHeight: 440 };
const EXPANDED_PHONE = { colWidth: PHONE.colWidth, maxHeight: 440 };

/* ---- 1. the invariant: what is packed fits the box -------------------- */

for (const geom of [DESKTOP, PHONE, EXPANDED_DESKTOP, EXPANDED_PHONE]) {
  for (const tallest of BUSIEST) {
    const p = packBench({ ...geom, tallest });
    const pitch = p.mark + BENCH_GAP;
    check(
      `fits box (w=${Math.round(geom.colWidth)} h=${geom.maxHeight} n=${tallest})`,
      p.rows * pitch <= geom.maxHeight,
      `${p.rows} rows x ${pitch}px = ${p.rows * pitch} > ${geom.maxHeight}`,
    );
    check(
      `fits width (w=${Math.round(geom.colWidth)} n=${tallest})`,
      p.perRow * pitch <= geom.colWidth + pitch,
      `${p.perRow} x ${pitch} = ${p.perRow * pitch} > ${Math.round(geom.colWidth)}`,
    );
    check(
      `mark in range (h=${geom.maxHeight} n=${tallest})`,
      p.mark >= BENCH_MARK_MIN && p.mark <= BENCH_MARK_MAX,
      `mark ${p.mark}`,
    );
    const drawn = p.capPerColumn === Infinity ? tallest : p.capPerColumn;
    check(
      `rows hold what is drawn (h=${geom.maxHeight} n=${tallest})`,
      p.rows * p.perRow >= drawn,
      `rows ${p.rows} x perRow ${p.perRow} < ${drawn}`,
    );
  }
}

/* ---- 2. the height is the count ---------------------------------------- */

/* THE regression this section exists for. The first draft took the WIDEST
   sub-row the column allowed, which packed a bucket of 4 and a bucket of 5
   into one row each: counts 1, 2, 3, 4 and 5 all drew a column exactly one
   mark high. Measured at 1440px on the 2026-09-21 feed, that collapsed five
   distinct counts into one bar on every story in the corpus. The Bench makes
   exactly one claim, that the height of a column is the count in that bucket,
   and that draft broke it everywhere the count was small. */
for (const geom of [DESKTOP, PHONE]) {
  for (const tallest of BUSIEST) {
    const p = packBench({ ...geom, tallest });
    const rowsFor = (n) => Math.ceil(n / p.perRow);
    check(
      `1 and 5 are different heights (h=${geom.maxHeight} n=${tallest})`,
      rowsFor(5) > rowsFor(1),
      `perRow ${p.perRow} puts both in ${rowsFor(1)} row(s)`,
    );
    check(
      `a bigger bucket is never a shorter column (h=${geom.maxHeight} n=${tallest})`,
      Array.from({ length: tallest }, (_, i) => rowsFor(i + 1))
        .every((r, i, a) => i === 0 || r >= a[i - 1]),
    );
  }
}

/* The search takes the fewest marks per sub-row it can, because perRow IS the
   histogram's resolution: at 1 every count has its own height, at 2 they step
   in pairs. A mark shrinks before the resolution is given up, so no narrower
   sub-row may admit any legible mark. */
for (const geom of [DESKTOP, PHONE, EXPANDED_DESKTOP, EXPANDED_PHONE]) {
  for (const tallest of BUSIEST) {
    const p = packBench({ ...geom, tallest });
    if (p.capPerColumn !== Infinity) continue; // the capped fallback is not a choice
    for (let narrower = 1; narrower < p.perRow; narrower++) {
      const rows = Math.ceil(tallest / narrower);
      let admits = false;
      for (let mark = BENCH_MARK_MAX; mark >= BENCH_MARK_MIN; mark--) {
        const pitch = mark + BENCH_GAP;
        if (rows * pitch <= geom.maxHeight && narrower * pitch <= geom.colWidth) {
          admits = true;
          break;
        }
      }
      check(
        `perRow is the smallest that fits (h=${geom.maxHeight} n=${tallest})`,
        !admits,
        `took ${p.perRow}, but ${narrower} fits too`,
      );
    }
  }
}

/* Half the feed is a true single file. Twenty of the 35 clusters have a
   busiest bucket of 14 or fewer, and on the desktop geometry those pack one
   mark to a row: every count between 1 and the tallest gets its own height,
   with nothing to read off but the stack. */
for (const tallest of BUSIEST.filter((n) => n <= 14)) {
  check(
    `a quiet story is a single file (n=${tallest})`,
    packBench({ ...DESKTOP, tallest }).perRow === 1,
    `perRow ${packBench({ ...DESKTOP, tallest }).perRow}`,
  );
}
check(
  "single file covers at least half the feed",
  BUSIEST.filter((n) => n <= 14).length * 2 >= BUSIEST.length,
  `${BUSIEST.filter((n) => n <= 14).length} of ${BUSIEST.length}`,
);

/* A quiet story keeps the full-size mark. It has the height budget for it, so
   paying for the crowded stories would be a cost with nothing bought. */
for (const tallest of [2, 4, 5, 6, 7, 8]) {
  check(
    `small story keeps the big mark (n=${tallest})`,
    packBench({ ...DESKTOP, tallest }).mark === BENCH_MARK_MAX,
    `n=${tallest} got ${packBench({ ...DESKTOP, tallest }).mark}px`,
  );
}

/* ---- 3. nothing is cut on the desktop collapsed view ------------------ */

/* The measured worst case is 40. If the collapsed desktop Bench had to cap,
   the "Show all N sources" toggle would be the norm rather than the exception,
   and the column heights on the busiest stories would all read as the cap. */
for (const tallest of BUSIEST) {
  check(
    `desktop draws every source (n=${tallest})`,
    packBench({ ...DESKTOP, tallest }).capPerColumn === Infinity,
    `capped at ${packBench({ ...DESKTOP, tallest }).capPerColumn}`,
  );
}

/* ---- 4. a cap, when it comes, is honest ------------------------------- */

/* Forced: a box too short for even the smallest mark. The pack must report a
   finite cap so the component can draw the "+N" and offer the toggle, rather
   than silently dropping sources. */
const tiny = packBench({ colWidth: 30, maxHeight: 30, tallest: 40 });
check("a cramped box caps", tiny.capPerColumn !== Infinity, `${tiny.capPerColumn}`);
check("a cramped box uses the floor mark", tiny.mark === BENCH_MARK_MIN, `${tiny.mark}`);
check("a cramped box draws at least one row", tiny.rows >= 1, `${tiny.rows}`);

/* And the toggle's promise holds: the expanded box draws everything the
   collapsed one cut, at both geometries, for every story on the feed. */
for (const tallest of BUSIEST) {
  for (const geom of [EXPANDED_DESKTOP, EXPANDED_PHONE]) {
    check(
      `expanded draws every source (h=${geom.maxHeight} n=${tallest})`,
      packBench({ ...geom, tallest }).capPerColumn === Infinity,
      `capped at ${packBench({ ...geom, tallest }).capPerColumn}`,
    );
  }
}

/* ---- 5. degenerate inputs -------------------------------------------- */

const none = packBench({ ...DESKTOP, tallest: 0 });
check("an empty bucket set asks for no rows", none.rows === 0, `${none.rows}`);
check("an empty bucket set cuts nothing", none.capPerColumn === Infinity);

const zeroW = packBench({ colWidth: 0, maxHeight: 176, tallest: 5 });
check("zero width still places one per row", zeroW.perRow === 1, `${zeroW.perRow}`);

/* ---- 6. benchRows chunks without losing or duplicating ---------------- */

for (const n of [1, 2, 3, 5, 7]) {
  for (const len of [0, 1, 4, 11, 40]) {
    const items = Array.from({ length: len }, (_, i) => i);
    const rows = benchRows(items, n);
    check(`benchRows keeps every item (perRow=${n} len=${len})`,
      rows.flat().length === len, `${rows.flat().length}`);
    check(`benchRows keeps order (perRow=${n} len=${len})`,
      rows.flat().every((v, i) => v === i));
    check(`benchRows respects perRow (perRow=${n} len=${len})`,
      rows.every((r) => r.length <= n));
    check(`benchRows uses the fewest rows (perRow=${n} len=${len})`,
      rows.length === Math.ceil(len / n), `${rows.length}`);
  }
}
check("benchRows survives a nonsense perRow",
  benchRows([1, 2, 3], 0).flat().length === 3);

/* ---------------------------------------------------------------------- */

if (failures) {
  console.log(`\nFAIL  bench: ${failures} failure(s)`);
  process.exit(1);
}
console.log("PASS  bench: every pack fits its box, the height is the count, nothing is dropped silently");
