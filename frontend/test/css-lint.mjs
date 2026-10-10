// The CSS lint gate: stylelint with the three rules in .stylelintrc.json and
// nothing else. Runs every stylesheet under app/ and fails on any problem,
// including a stylelint-disable comment that no longer disables anything.
//
//   1. No raw cubic-bezier() outside tokens.css: a curve is a named --ease-* token.
//   2. font-family names one of the four semantic tokens (or Paper's --np-font-*
//      aliases of them, or inherit).
//   3. border-radius is 0, 50%, inherit or a var(). A literal radius that predates
//      the scale carries a disable comment on the line above it, so the list of
//      exceptions is visible in place and can only shrink.
//
// games.css and revolt.css (hidden routes) are exempt from all three, as they are
// from the class parity gate. Run alone: node test/css-lint.mjs
import stylelint from 'stylelint';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const result = await stylelint.lint({
  files: ['app/**/*.css'],
  cwd: root,
  formatter: 'string',
  reportNeedlessDisables: true,
});

let problems = 0;
for (const r of result.results) {
  problems += r.warnings.length;
  for (const d of r.deprecations) console.error(`deprecation in ${r.source}: ${d.text}`);
  for (const e of r.invalidOptionWarnings) { problems++; console.error(`invalid option in ${r.source}: ${e.text}`); }
}
if (result.report) process.stdout.write(result.report);
const files = result.results.length;
if (problems) {
  console.error(`css-lint: ${problems} problem(s) across ${files} stylesheets`);
  process.exit(1);
}
console.log(`css-lint: ${files} stylesheets, no raw curve, no stray font, no literal radius without a disable`);
