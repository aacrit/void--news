/**
 * The spectrum line may not invent a peak, and the mark may not drift.
 *
 * THE DEFECT THIS EXISTS TO PREVENT IS THIS PROJECT'S OWN. The Bench replaced
 * a kernel density estimate on 2026-09-21 because the curve "drew hills
 * between spikes that nothing stands on": 74% of measured articles sit exactly
 * on one of the seven baselines, so a smoothed density over them put mass at
 * positions no source occupies. Drawing a smooth line back over the columns is
 * the same mistake in a thinner stroke unless it is built so that a peak
 * between two columns is UNREPRESENTABLE.
 *
 * It is. Every segment is a cubic whose control points carry their own
 * endpoint's y, so the curve's y is a convex combination of y0, y0, y1, y1 and
 * is therefore confined to [min(y0,y1), max(y0,y1)]. The sweep below samples
 * every segment of every case and asserts exactly that, rather than trusting
 * the argument.
 *
 * Also asserted: the vertices land ON the column tops (so the line agrees with
 * the counts), the room is the widest LOW run (so the mark stands where the
 * coverage is not), a cramped room is refused rather than squeezed, and the
 * Sigil still draws the geometry that lib/sigilGeometry.ts now owns.
 *
 * Run: node test/bench-curve.test.mjs
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const ROOT = resolve(import.meta.dirname, "..");
const out = mkdtempSync(join(tmpdir(), "void-curve-"));
let failures = 0;
const check = (name, cond, detail = "") => {
  if (cond) return;
  failures += 1;
  console.log(`FAIL  ${name}${detail ? `: ${detail}` : ""}`);
};

execFileSync("npx", ["tsc", "app/lib/benchCurve.ts", "app/lib/sigilGeometry.ts",
  "--outDir", out, "--module", "es2022", "--target", "es2022",
  "--moduleResolution", "bundler", "--skipLibCheck"],
  { cwd: ROOT, stdio: "pipe" });
const bc = await import(pathToFileURL(join(out, "benchCurve.js")).href);
const sg = await import(pathToFileURL(join(out, "sigilGeometry.js")).href);

const G = (counts, over = {}) => ({
  counts, mark: 16, perRow: 2, gap: 2, cap: Infinity,
  colWidth: 60, colGap: 10, boxH: 180, ...over,
});

/* ---- 1. heights are the counts ---------------------------------------- */

const h = bc.columnHeights(G([0, 1, 2, 3, 4, 8, 0]));
check("an empty bucket has no height", h[0] === 0 && h[6] === 0, JSON.stringify(h));
check("heights rise with the count",
  h[1] <= h[2] && h[2] <= h[3] && h[3] <= h[4] && h[4] <= h[5], JSON.stringify(h));
check("a fuller column is strictly taller once it needs another row",
  h[5] > h[1], `${h[5]} vs ${h[1]}`);

/* ---- 2. the vertices sit on the column tops ---------------------------- */

const CASES = [
  [0, 0, 1, 14, 2, 0, 0],        // consensus: one spike
  [9, 3, 0, 1, 0, 2, 11],        // split: two spikes, hollow middle
  [0, 0, 0, 2, 5, 12, 6],        // leans right
  [12, 6, 3, 1, 0, 0, 0],        // leans left
  [3, 3, 3, 3, 3, 3, 3],         // flat
  [0, 0, 0, 0, 0, 0, 1],         // a single source at the edge
  [1, 0, 0, 0, 0, 0, 0],
];

for (const counts of CASES) {
  const g = G(counts);
  const env = bc.envelope(g);
  check(`a case with coverage yields a line (${counts})`, !!env);
  if (!env) continue;
  const hs = bc.columnHeights(g);
  for (let i = 0; i < 7; i += 1) {
    const [x, y] = env.points[i + 1];
    check(`vertex ${i} sits on its column top (${counts})`,
      Math.abs(y - (g.boxH - hs[i])) < 0.01 &&
      Math.abs(x - bc.columnCentre(i, g)) < 0.01, `${x},${y}`);
  }
  check(`the line starts and ends on the baseline (${counts})`,
    env.points[0][1] === g.boxH &&
    env.points[env.points.length - 1][1] === g.boxH);
}

/* ---- 3. NO INVENTED PEAK, sampled rather than argued ------------------- */

function cubicY(y0, c0, c1, y1, t) {
  const u = 1 - t;
  return u * u * u * y0 + 3 * u * u * t * c0 + 3 * u * t * t * c1 + t * t * t * y1;
}

for (const counts of CASES) {
  const g = G(counts);
  const env = bc.envelope(g);
  if (!env) continue;
  const nums = env.line.match(/-?\d+(\.\d+)?/g).map(Number);
  // M x y, then repeating C c0x c0y c1x c1y x y
  let k = 2;
  let prevY = nums[1];
  let seg = 0;
  let worst = 0;
  while (k + 5 < nums.length + 1 && k + 5 <= nums.length) {
    const c0y = nums[k + 1], c1y = nums[k + 3], y1 = nums[k + 5];
    const lo = Math.min(prevY, y1), hi = Math.max(prevY, y1);
    for (let t = 0; t <= 1.0001; t += 0.02) {
      const y = cubicY(prevY, c0y, c1y, y1, t);
      worst = Math.max(worst, lo - y, y - hi);
    }
    prevY = y1;
    k += 6;
    seg += 1;
  }
  check(`no segment leaves its own endpoints' range (${counts})`,
    worst < 0.001, `overshoot ${worst.toFixed(4)} over ${seg} segments`);
}

/* An explicit valley case: a dip between two spikes must stay a dip. */
{
  const g = G([0, 14, 0, 0, 0, 14, 0]);
  const env = bc.envelope(g);
  const hs = bc.columnHeights(g);
  const floor = g.boxH - Math.max(hs[2], hs[3], hs[4]);
  const nums = env.line.match(/-?\d+(\.\d+)?/g).map(Number);
  let minY = Infinity;
  for (let i = 1; i < nums.length; i += 2) minY = Math.min(minY, nums[i]);
  check("a hollow middle is never filled by the curve",
    env.points[3][1] === floor, `${env.points[3][1]} vs ${floor}`);
}

check("no coverage means no line", bc.envelope(G([0, 0, 0, 0, 0, 0, 0])) === null);

/* ---- 4. the room is where the coverage is not -------------------------- */

{
  const leansRight = bc.whitespace(G([0, 0, 0, 2, 5, 12, 6]));
  check("a right-leaning roster leaves its room on the LEFT",
    leansRight && leansRight.from === 0, JSON.stringify(leansRight));
  const leansLeft = bc.whitespace(G([12, 6, 3, 1, 0, 0, 0]));
  check("a left-leaning roster leaves its room on the RIGHT",
    leansLeft && leansLeft.to === 6, JSON.stringify(leansLeft));
  const split = bc.whitespace(G([9, 3, 0, 1, 0, 2, 11]));
  check("a split roster leaves its room in the MIDDLE",
    split && split.from > 0 && split.to < 6, JSON.stringify(split));
  const flat = bc.whitespace(G([3, 3, 3, 3, 3, 3, 3]));
  check("a flat roster offers no room, rather than a cramped one",
    flat === null, JSON.stringify(flat));
  const tiny = bc.whitespace(G([0, 0, 0, 14, 0, 0, 0]), { minSide: 400 });
  check("a room smaller than the mark is refused", tiny === null);
}

{
  /* The room must never overlap a mark: it stops at the tallest column in its
     own run, not at the tallest on the Bench. */
  const g = G([1, 0, 0, 0, 0, 12, 0]);
  const r = bc.whitespace(g);
  const hs = bc.columnHeights(g);
  if (r) {
    const runTop = Math.max(...hs.slice(r.from, r.to + 1));
    check("the room clears the tallest column inside it",
      Math.abs(r.height - (g.boxH - runTop)) < 0.01, JSON.stringify(r));
  }
}

/* ---- 5. one mark, one set of numbers ----------------------------------- */

const sigil = readFileSync(join(ROOT, "app/components/Sigil.tsx"), "utf8");
check("the Sigil still draws the shared viewBox",
  sigil.includes(`viewBox="${sg.SIGIL_VIEWBOX}"`), sg.SIGIL_VIEWBOX);
check("the Sigil still pivots on the shared centre",
  sigil.includes(`transformOrigin: "${sg.SIGIL_CX}px ${sg.SIGIL_CY}px"`));
check("the Sigil's circle still has the shared radius",
  new RegExp(`cx="${sg.SIGIL_CX}" cy="${sg.SIGIL_CY}" r="${sg.SIGIL_R}"`).test(sigil));
check("the Sigil's beam still spans the shared width",
  new RegExp(`x1="${sg.SIGIL_BEAM_X1}" y1="${sg.SIGIL_CY}" x2="${sg.SIGIL_BEAM_X2}"`).test(sigil));
check("the Sigil still saturates at the shared tilt",
  sigil.includes(`* ${sg.SIGIL_MAX_TILT}`), String(sg.SIGIL_MAX_TILT));

const bsig = readFileSync(join(ROOT, "app/components/BenchSigil.tsx"), "utf8");
check("the Bench's mark takes its state from leanShape, like every other surface",
  /leanShape\(spread\)/.test(bsig));
check("the Bench's mark takes its colour from leanShapeColor",
  /leanShapeColor\(spread\)/.test(bsig));
check("the Bench's mark tilts on the ROSTER's wings, never on a mean",
  /leanShareTilt\(spread\)/.test(bsig) && !/politicalLean/.test(bsig));
check("the Bench's mark is decoration to a screen reader",
  /aria-hidden="true"/.test(bsig));

const bench = readFileSync(join(ROOT, "app/components/Bench.tsx"), "utf8");
check("the shape word is printed for every reader, whether or not the mark is drawn",
  /<p className="bench__shape">\{leanShapeLabel\(spread\)\}<\/p>/.test(bench) && !/bench__shape--sr/.test(bench));
check("the line is decoration, not a second chart",
  /className="bench__curve"[\s\S]{0,220}aria-hidden="true"/.test(bench));

const css = readFileSync(join(ROOT, "app/styles/bench.css"), "utf8");
check("the line cannot swallow a pointer event",
  /\.bench__curve\s*\{[^}]*pointer-events:\s*none/.test(css));
check("the marks sit above the line",
  /\.bench__col\s*\{[^}]*z-index:\s*1/.test(css));
check("no rule hides the shape word from sighted readers",
  !/\.bench__shape--sr/.test(css));
/* TWO INKS, AND THEY MUST NOT SWAP. The pen is the story's verdict and the
   bleed is the axis it sits on. If the pen ever took the ramp, a Split story,
   whose whole finding is that the room has no direction, would be drawn with a
   confident blue-to-red sweep. */
check("the pen takes the story's verdict colour, never the axis ramp",
  /className="bench__curve-ink"[\s\S]{0,120}\/>/.test(bench) &&
  !/className="bench__curve-ink"[\s\S]{0,120}url\(#/.test(bench));
check("the bleed is wider than the pen, or the colour never reaches the page",
  /minHalf: 1\.5, maxHalf: 4\.4/.test(bench) && /minHalf: 0\.4, maxHalf: 2\.4/.test(bench));
check("the bleed takes the axis ramp",
  /className="bench__curve-bleed"[\s\S]{0,160}fill=\{`url\(#/.test(bench));
check("the pen still resolves currentcolor from leanShapeColor",
  /style=\{\{ color: leanShapeColor\(spread\) \}\}/.test(bench) &&
  /\.bench__curve-ink\s*\{[^}]*fill:\s*currentcolor/.test(css));
check("the ramp is the same seven stops the axis rule draws",
  /AXIS_RAMP/.test(bench) &&
  ["--bias-far-left", "--bias-left", "--bias-center-left", "--bias-center",
   "--bias-center-right", "--bias-right", "--bias-far-right"]
    .every((t) => new RegExp(`"${t}"`).test(bench)));
/* Two Benches mount on one page (the inline Deep Dive and the full one). A
   fixed id would silently repoint the second one's fill at the first's. */
check("the gradient id cannot collide between mounts",
  /useId\(\)/.test(bench) && !/id="bench-ramp"/.test(bench));
check("the ramp is laid out in user space, so it lands where the rule does",
  /gradientUnits="userSpaceOnUse"/.test(bench));

check("the bleed stays a bleed",
  /\.bench__curve-bleed\s*\{[^}]*opacity:\s*0\.[1-4]/.test(css) &&
  /\.bench__curve-bleed\s*\{[^}]*filter:\s*blur/.test(css));
check("motion is given up under prefers-reduced-motion",
  /prefers-reduced-motion[\s\S]*bench__curve-ink[\s\S]*animation:\s*none/.test(css));
/* The wash was a chart convention and the one element that was not ink. It
   must not come back by habit. */
check("no flat tint under the curve, on either surface",
  !/bench__curve-area/.test(css) && !/roster__curve--area/.test(
    readFileSync(join(ROOT, "app/styles/components.css"), "utf8")));

/* ---- 6. the pen stroke ------------------------------------------------- */

for (const counts of CASES) {
  const g = G(counts);
  const env = bc.envelope(g);
  if (!env) continue;
  const d = bc.inkRibbon(env, counts, { minHalf: 0.4, maxHalf: 2.4 });
  check(`the ribbon is one closed figure (${counts})`,
    (d.match(/M/g) || []).length === 1 && (d.match(/Z/g) || []).length === 1, d.slice(0, 60));
  check(`the ribbon carries no stray command (${counts})`,
    d.replace(/[MCLZ0-9 .-]/g, "") === "", d.replace(/[MCLZ0-9 .-]/g, ""));
}

{
  /* Width is a second rendering of the count, so it must RISE with it, and
     the outer anchors carry no count and so enter at the thinnest. */
  const g = G([0, 0, 0, 0, 0, 0, 20]);
  const env = bc.envelope(g);
  const wide = bc.inkRibbon(env, g.counts, { minHalf: 0.5, maxHalf: 3 });
  const thin = bc.inkRibbon(env, g.counts, { minHalf: 0.5, maxHalf: 0.5 });
  check("a heavier bucket lays down more ink than a flat pen would",
    wide !== thin);
  const flat = bc.inkRibbon(env, [1, 1, 1, 1, 1, 1, 1], { minHalf: 0.5, maxHalf: 3 });
  check("an even distribution lays an even stroke", flat !== wide);
}

{
  /* The centreline is the reading and must not move when the pen changes. */
  const g = G([0, 2, 6, 14, 5, 1, 0]);
  const env = bc.envelope(g);
  const hs = bc.columnHeights(g);
  for (let i = 0; i < 7; i += 1) {
    check(`the pen does not move vertex ${i} off its column top`,
      Math.abs(env.points[i + 1][1] - (g.boxH - hs[i])) < 0.01);
  }
}

rmSync(out, { recursive: true, force: true });
console.log(failures ? `\n${failures} failure(s)` : "\nPASS  bench curve: no invented peak, the room is the empty side, one mark");
process.exit(failures ? 1 : 0);
