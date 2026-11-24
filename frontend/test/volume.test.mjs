/* Volume and number.
 *
 * Void Weekly launched as a Sunday magazine on 2026-09-20 with the week of
 * September 14 — epoch issue 26, published as Vol. I, No. 1. The old helper
 * clamped with `Math.max(1, ...)`, which would have collapsed EVERY
 * pre-launch issue onto No. 1 alongside the launch issue: two different
 * issues with the same name in the same archive.
 *
 * Compiled with the installed typescript, like labels.test.mjs, so it needs
 * no new dependency.
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, readdirSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import assert from "node:assert/strict";

const out = mkdtempSync(join(tmpdir(), "void-vol-"));
execFileSync("npx", ["tsc", "app/weekly/format.ts", "--outDir", out,
                     "--module", "es2022", "--target", "es2022", "--moduleResolution", "bundler"],
             { stdio: "inherit" });

function findEmitted(dir, name) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const p = join(dir, e.name);
    if (e.isDirectory()) { const hit = findEmitted(p, name); if (hit) return hit; }
    else if (e.name === name) return p;
  }
  return null;
}
const mod = await import(findEmitted(out, "format.js"));
const { issueRef, issueLabel, issueFolio, issueShort, romanNumeral,
        WEEKLY_LAUNCH_ISSUE, WEEKS_PER_VOLUME } = mod;

// ── The launch ──────────────────────────────────────────────────────────────
assert.equal(WEEKLY_LAUNCH_ISSUE, 26, "the launch issue is the week of 2026-09-14");
assert.deepEqual(issueRef(26), { pilot: false, volume: 1, number: 1, serial: 1 });
assert.equal(issueLabel(26), "Vol. I, No. 1");
assert.equal(issueFolio(26), "I.01");
assert.equal(issueShort(26), "No. 1");

// ── Pilots stay pilots, and never collide with the launch ───────────────────
for (const raw of [23, 25, 19, 1, 0]) {
  const r = issueRef(raw);
  assert.equal(r.pilot, true, `issue ${raw} predates the volume system`);
  assert.equal(issueLabel(raw), "Pilot issue");
  assert.equal(issueFolio(raw), "Pilot");
  assert.equal(issueShort(raw), "Pilot");
}
assert.notEqual(issueLabel(23), issueLabel(26), "a pilot must not share the launch's name");

// ── The volume turns over instead of the number climbing ────────────────────
assert.deepEqual(issueRef(26 + WEEKS_PER_VOLUME - 1),
                 { pilot: false, volume: 1, number: 52, serial: 52 });
assert.deepEqual(issueRef(26 + WEEKS_PER_VOLUME),
                 { pilot: false, volume: 2, number: 1, serial: 53 });
assert.equal(issueLabel(26 + WEEKS_PER_VOLUME), "Vol. II, No. 1");
assert.equal(issueFolio(26 + WEEKS_PER_VOLUME), "II.01");

// A number never exceeds the volume length, and never reaches zero.
for (let raw = 26; raw < 26 + 260; raw++) {
  const r = issueRef(raw);
  assert.ok(r.number >= 1 && r.number <= WEEKS_PER_VOLUME, `number out of range at ${raw}`);
  assert.ok(r.volume >= 1, `volume out of range at ${raw}`);
  assert.equal(r.serial, raw - 26 + 1);
}

// Serial is strictly increasing, so the archive can still sort by it.
let prev = 0;
for (let raw = 26; raw < 26 + 120; raw++) {
  const s = issueRef(raw).serial;
  assert.ok(s > prev, `serial not increasing at ${raw}`);
  prev = s;
}

// ── Roman numerals ──────────────────────────────────────────────────────────
for (const [n, sym] of [[1,"I"],[4,"IV"],[5,"V"],[9,"IX"],[14,"XIV"],[40,"XL"],
                        [49,"XLIX"],[90,"XC"],[400,"CD"],[1994,"MCMXCIV"]]) {
  assert.equal(romanNumeral(n), sym, `roman ${n}`);
}
assert.equal(romanNumeral(0), "", "a volume below one has no numeral");
assert.equal(romanNumeral(-3), "");

// ── Nulls degrade to a pilot rather than throwing ───────────────────────────
for (const bad of [null, undefined, NaN]) {
  assert.equal(issueRef(bad).pilot, true);
  assert.equal(issueLabel(bad), "Pilot issue");
}

console.log("PASS  volume/number, pilots, roman numerals, the 52-week turnover");
