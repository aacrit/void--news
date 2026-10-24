/* ===========================================================================
   verification.test.mjs: the "Not yet verified" label (rev 86).

   The pipeline reads every TL;DR, Opinion and On Air sentence against its own
   story. When that pass cannot complete the product ships anyway, wearing a
   label (CEO, 2026-10-03), and tests/test_rigor.py F-3 fails a run that ships
   one unlabelled. This holds the frontend half:

     - only an explicit false labels; a missing flag (a brief written before
       the flag existed) and true do not; a JSON string is read like an object;
     - every surface that prints the TL;DR or the Opinion renders the label off
       the flag, and the On Air page renders it for the broadcast;
     - the label's copy carries no dash.
   =========================================================================== */
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, existsSync, readdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const ROOT = resolve(import.meta.dirname, "..");
const out = mkdtempSync(join(tmpdir(), "void-verif-"));
let failures = 0;
function check(name, cond, detail = "") {
  if (cond) return;
  failures += 1;
  console.log(`FAIL  ${name}${detail ? `: ${detail}` : ""}`);
}

execFileSync("npx", ["tsc", join(ROOT, "app/lib/verification.ts"),
  "--outDir", out, "--module", "es2022", "--target", "es2022",
  "--moduleResolution", "bundler", "--skipLibCheck"], { stdio: "inherit" });
const find = (name) => {
  for (const dir of [out, join(out, "lib"), join(out, "app/lib")]) {
    if (existsSync(join(dir, name))) return join(dir, name);
  }
  throw new Error(`compiled ${name} not found under ${out}: ${readdirSync(out)}`);
};
const v = await import(pathToFileURL(find("verification.js")).href);

// --- the rule -------------------------------------------------------------
check("false labels", v.isUnverified({ grounding_ran: { tldr: false } }, "tldr") === true);
check("true does not label", v.isUnverified({ grounding_ran: { tldr: true } }, "tldr") === false);
check("a missing flag does not label (predates the flag)",
  v.isUnverified({}, "tldr") === false && v.isUnverified(null, "opinion") === false);
check("null does not label", v.isUnverified({ grounding_ran: { opinion: null } }, "opinion") === false);
check("one product's flag never labels another",
  v.isUnverified({ grounding_ran: { tldr: false, onair: true } }, "onair") === false);
check("a JSON string is read",
  v.isUnverified({ grounding_ran: '{"onair": false}' }, "onair") === true);
check("a malformed string labels nothing", v.isUnverified({ grounding_ran: "{" }, "tldr") === false);

// --- the copy ---------------------------------------------------------------
const DASH = /[\u2013\u2014]|&mdash;|&ndash;/;
check("label copy has no dash", !DASH.test(v.UNVERIFIED_LABEL) && !DASH.test(v.UNVERIFIED_TITLE));
check("the label says what it is", v.UNVERIFIED_LABEL === "Not yet verified");

// --- the wiring -------------------------------------------------------------
const SURFACES = {
  "app/components/SkyboxBanner.tsx": ["tldr", "opinion"],
  "app/components/MobileBriefPill.tsx": ["tldr", "opinion"],
  "app/components/OnAirPanel.tsx": ["tldr", "opinion"],
  "app/components/OnAirPage.tsx": ["tldr", "opinion", "onair"],
};
for (const [file, products] of Object.entries(SURFACES)) {
  const src = readFileSync(join(ROOT, file), "utf8");
  check(`${file} imports the label`, src.includes('import UnverifiedLabel from "./UnverifiedLabel"'));
  for (const p of products) {
    check(`${file} labels ${p} off its flag`,
      src.includes(`isUnverified(brief, "${p}") && <UnverifiedLabel />`));
  }
}
const css = readFileSync(join(ROOT, "app/styles/components.css"), "utf8");
check("the label is styled", css.includes(".unverified-label {"));

if (failures) {
  console.log(`\nverification: ${failures} failure(s)`);
  process.exit(1);
}
console.log("verification: the label renders off the flag, on every surface, without a dash");
