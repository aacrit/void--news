/**
 * CSS class parity, without a test framework.
 *
 * A quarter of the stylesheet targeted classes that no longer existed (brand
 * audit 2026-09-21, B-02). Deleting them once is worthless unless something
 * stops the next retired feature from leaving its CSS behind, so this file is
 * a gate, not a report.
 *
 * Forward direction (FAILS): a class selector defined in CSS that nothing in
 * the app source references. The allowlist below the code holds the classes
 * that were already dead when the gate went in, plus deliberate exceptions.
 *
 * Reverse direction (INFORMATIONAL): a class written in TSX that no stylesheet
 * defines. Often legitimate (utility hooks, JS-only markers), so it prints and
 * does not fail.
 *
 * What counts as a reference, deliberately generous, because a false "dead"
 * reading deletes live CSS:
 *   - the exact class name as a word anywhere in .tsx/.ts/.js/.mjs under app/
 *     (this covers classList.add("x") and any other JS string)
 *   - a template-literal prefix: `hist-tl-card__` in source keeps
 *     .hist-tl-card__title alive
 *   - a class named inside :has() in any stylesheet
 *   - the same name anywhere in public/*.html
 *
 * Run:  node test/css-parity.test.mjs            (gate)
 *       node test/css-parity.test.mjs --report   (full report to stdout)
 */

import { readFileSync, readdirSync, existsSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.join(HERE, '..');
const APP = path.join(ROOT, 'app');
const PUBLIC = path.join(ROOT, 'public');
const ALLOWLIST_FILE = path.join(HERE, 'css-parity-allowlist.txt');

/* Hidden routes. Their CSS is kept on purpose until the route comes back. */
const SKIPPED_FILES = new Set(['games.css', 'games-brand.css', 'revolt.css']);

/* ------------------------------------------------------------------ files */

function walk(dir, pred, out = []) {
  if (!existsSync(dir)) return out;
  for (const name of readdirSync(dir)) {
    const p = path.join(dir, name);
    const s = statSync(p);
    if (s.isDirectory()) walk(p, pred, out);
    else if (pred(p)) out.push(p);
  }
  return out;
}

function cssFiles() {
  const list = walk(path.join(APP, 'styles'), (p) => p.endsWith('.css'));
  for (const extra of ['paper/paper.css', 'audio/audio.css', 'press/press.css', 'privacy/privacy.css']) {
    const p = path.join(APP, extra);
    if (existsSync(p)) list.push(p);
  }
  return list.sort();
}

const rel = (p) => path.relative(ROOT, p);

/* ------------------------------------------------------------------- CSS */

const stripComments = (css) => css.replace(/\/\*[\s\S]*?\*\//g, ' ');
const stripUrls = (css) => css.replace(/url\((?:[^()\\]|\\.)*\)/g, 'url()');

/** Every selector prelude in a stylesheet (the text before each `{`). */
function preludes(css) {
  const src = stripUrls(stripComments(css));
  const out = [];
  let buf = '';
  let i = 0;
  while (i < src.length) {
    const ch = src[i];
    if (ch === '"' || ch === "'") {
      const q = ch;
      i += 1;
      while (i < src.length && src[i] !== q) {
        if (src[i] === '\\') i += 1;
        i += 1;
      }
      i += 1;
      buf += ' ';
      continue;
    }
    if (ch === '{') { out.push(buf); buf = ''; i += 1; continue; }
    if (ch === '}' || ch === ';') { buf = ''; i += 1; continue; }
    buf += ch;
    i += 1;
  }
  return out;
}

const CLASS_RE = /\.(-?[_a-zA-Z][A-Za-z0-9_-]*)/g;

function classesIn(text) {
  const out = [];
  let m;
  CLASS_RE.lastIndex = 0;
  while ((m = CLASS_RE.exec(text)) !== null) out.push(m[1]);
  return out;
}

/** Classes named inside :has(...) anywhere: one stylesheet skinning another. */
function hasRefs(prelude) {
  const out = [];
  const re = /:has\(/g;
  let m;
  while ((m = re.exec(prelude)) !== null) {
    let depth = 1;
    let i = m.index + m[0].length;
    const start = i;
    while (i < prelude.length && depth > 0) {
      if (prelude[i] === '(') depth += 1;
      else if (prelude[i] === ')') depth -= 1;
      i += 1;
    }
    out.push(...classesIn(prelude.slice(start, i - 1)));
  }
  return out;
}

/* ---------------------------------------------------------------- sources */

const SOURCE_EXT = /\.(tsx|ts|jsx|js|mjs)$/;

function sourceCorpus() {
  const files = walk(APP, (p) => SOURCE_EXT.test(p) && !p.endsWith('.d.ts'));
  files.push(...walk(PUBLIC, (p) => p.endsWith('.html')));
  return files.map((p) => readFileSync(p, 'utf8')).join('\n');
}

/** Whole tokens plus template-literal prefixes, e.g. `hist-tl-card__`. */
function sourceTokens(corpus) {
  const exact = new Set();
  const prefixes = new Set();
  const re = /[A-Za-z0-9_-]+/g;
  let m;
  while ((m = re.exec(corpus)) !== null) {
    const t = m[0];
    exact.add(t);
    if (t.length >= 3 && /[-_]$/.test(t)) prefixes.add(t);
  }
  return { exact, prefixes: [...prefixes].sort() };
}

/** Classes written into className / classList in the app source. */
function classesWrittenInSource() {
  const files = walk(APP, (p) => SOURCE_EXT.test(p) && !p.endsWith('.d.ts'));
  const out = new Set();
  const attr = /\bclassName\s*=\s*(?:"([^"]*)"|'([^']*)'|\{([\s\S]{0,600}?)\})/g;
  const listOp = /\bclassList\s*\.\s*(?:add|remove|toggle|contains)\s*\(([^)]*)\)/g;
  const strInside = /["'`]([^"'`\n]*)["'`]/g;
  const take = (chunk, strict) => {
    for (const word of String(chunk).split(/[\s$]+/)) {
      const w = word.trim();
      if (!w || !/^-?[_a-zA-Z][A-Za-z0-9_-]*$/.test(w)) continue;
      // Inside a {...} expression any string literal is a candidate, so keep
      // only kebab-case names: every class in this codebase carries a dash.
      if (strict && !w.includes('-')) continue;
      out.add(w);
    }
  };
  for (const f of files) {
    const src = readFileSync(f, 'utf8');
    let m;
    attr.lastIndex = 0;
    while ((m = attr.exec(src)) !== null) {
      if (m[1] !== undefined) take(m[1], false);
      else if (m[2] !== undefined) take(m[2], false);
      else {
        let s;
        strInside.lastIndex = 0;
        while ((s = strInside.exec(m[3])) !== null) take(s[1], true);
      }
    }
    listOp.lastIndex = 0;
    while ((m = listOp.exec(src)) !== null) {
      let s;
      strInside.lastIndex = 0;
      while ((s = strInside.exec(m[1])) !== null) take(s[1], false);
    }
  }
  return out;
}

/* ------------------------------------------------------------------- run */

const files = cssFiles();
const definedIn = new Map(); // class -> Set(file)
const cssHasRefs = new Set();

const definedAnywhere = new Set(); // includes the skipped, hidden-route files

for (const f of files) {
  const css = readFileSync(f, 'utf8');
  const skipped = SKIPPED_FILES.has(path.basename(f));
  for (const prelude of preludes(css)) {
    for (const c of hasRefs(prelude)) cssHasRefs.add(c);
    for (const c of classesIn(prelude)) {
      definedAnywhere.add(c);
      if (skipped) continue;
      if (!definedIn.has(c)) definedIn.set(c, new Set());
      definedIn.get(c).add(rel(f));
    }
  }
}

const corpus = sourceCorpus();
const { exact, prefixes } = sourceTokens(corpus);

function isUsed(cls) {
  if (exact.has(cls)) return true;
  if (cssHasRefs.has(cls)) return true;
  for (const p of prefixes) if (cls.length > p.length && cls.startsWith(p)) return true;
  return false;
}

const dead = [];
for (const [cls, where] of definedIn) {
  if (!isUsed(cls)) dead.push({ cls, files: [...where].sort() });
}
dead.sort((a, b) => a.cls.localeCompare(b.cls));

const written = classesWrittenInSource();
const undefinedInCss = [...written].filter((c) => !definedAnywhere.has(c)).sort();

const byFile = new Map();
for (const d of dead) for (const f of d.files) {
  if (!byFile.has(f)) byFile.set(f, []);
  byFile.get(f).push(d.cls);
}

const report = [];
report.push('CSS CLASS PARITY');
report.push('');
report.push(`stylesheets scanned : ${files.length} (${[...SKIPPED_FILES].join(', ')} skipped, hidden routes)`);
report.push(`classes defined     : ${definedIn.size}`);
report.push(`classes with no reference in app source: ${dead.length}`);
report.push('');
report.push('DEAD BY FILE');
for (const f of [...byFile.keys()].sort()) {
  report.push(`\n  ${f}  (${byFile.get(f).length})`);
  for (const c of byFile.get(f).sort()) report.push(`    .${c}`);
}
report.push('');
report.push(`REVERSE (informational): ${undefinedInCss.length} class(es) written in source with no stylesheet rule`);
for (const c of undefinedInCss) report.push(`    .${c}`);
report.push('');

if (process.argv.includes('--classes')) {
  console.log(JSON.stringify([...definedIn.keys()].sort(), null, 0));
  process.exit(0);
}

if (process.argv.includes('--report')) {
  console.log(report.join('\n'));
  process.exit(0);
}

let allow = new Set();
if (existsSync(ALLOWLIST_FILE)) {
  allow = new Set(
    readFileSync(ALLOWLIST_FILE, 'utf8')
      .split('\n')
      .map((l) => l.replace(/#.*$/, '').trim().replace(/^\./, ''))
      .filter(Boolean)
  );
}

const unexpected = dead.filter((d) => !allow.has(d.cls));
const stale = [...allow].filter((c) => !definedIn.has(c) || isUsed(c)).sort();

console.log(`\nclasses defined ${definedIn.size}, dead ${dead.length}, allowlisted ${allow.size}`);
console.log(`reverse direction (informational): ${undefinedInCss.length} class(es) in source with no rule`);

if (unexpected.length) {
  console.log('\nFAIL  dead CSS class(es) not on the allowlist:');
  for (const d of unexpected) console.log(`  .${d.cls}  ${d.files.join(', ')}`);
  console.log('\nDelete the rules, or add the name to test/css-parity-allowlist.txt with a reason.');
  process.exit(1);
}

if (stale.length) {
  console.log('\nFAIL  allowlist entries that are no longer dead (delete these lines):');
  for (const c of stale) console.log(`  .${c}`);
  process.exit(1);
}

console.log('\nPASS  every CSS class selector is referenced, or allowlisted');
