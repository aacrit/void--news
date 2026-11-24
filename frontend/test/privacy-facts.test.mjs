/* The privacy page must name every field the live database writes.
 *
 * Until 2026-10-02 /privacy said feedback stored "a coarse one-way hash of
 * your browser profile". The Worker stored the full browser user agent and a
 * salted SHA-256 of the IP address, and the page named neither (audit 5 M3).
 * Copy that describes a schema drifts the moment the schema moves, so this
 * reads the schema.
 *
 * Every column in worker/schema.sql, plus every column a file in
 * worker/migrations/ adds, must appear on the page inside a <code> tag. A new
 * column fails here until the page says what it holds.
 */
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

const ROOT = new URL("..", import.meta.url).pathname;
const WORKER = join(ROOT, "../worker");
const fail = [];
const ok = (name, cond, detail = "") =>
  cond ? console.log(`PASS  ${name}`) : fail.push(`${name}${detail ? ": " + detail : ""}`);

const schema = readFileSync(join(WORKER, "schema.sql"), "utf8");
const migDir = join(WORKER, "migrations");
const migrations = readdirSync(migDir)
  .filter((f) => f.endsWith(".sql"))
  .sort()
  .map((f) => readFileSync(join(migDir, f), "utf8"));

const stripSql = (s) => s.replace(/--.*$/gm, "");
const columns = new Map(); // table -> Set(column)

for (const m of stripSql(schema).matchAll(/CREATE TABLE IF NOT EXISTS (\w+)\s*\(([\s\S]*?)\n\);/g)) {
  const cols = new Set();
  for (const line of m[2].split("\n")) {
    const name = line.trim().match(/^([a-z_]+)\s+(TEXT|INTEGER|REAL|BLOB)\b/i);
    if (name) cols.add(name[1]);
  }
  columns.set(m[1], cols);
}
for (const sql of migrations) {
  for (const m of stripSql(sql).matchAll(/ALTER TABLE (\w+) ADD COLUMN (\w+)/gi)) {
    if (!columns.has(m[1])) columns.set(m[1], new Set());
    columns.get(m[1]).add(m[2]);
  }
}

ok("schema parsed: ship_requests, ship_votes, ship_replies",
   ["ship_requests", "ship_votes", "ship_replies"].every((t) => (columns.get(t)?.size ?? 0) > 2),
   JSON.stringify([...columns].map(([t, c]) => [t, c.size])));

const page = readFileSync(join(ROOT, "app/privacy/page.tsx"), "utf8");
const named = new Set([...page.matchAll(/<code>([a-z_]+)<\/code>/g)].map((m) => m[1]));

for (const [table, cols] of columns) {
  const missing = [...cols].filter((c) => !named.has(c));
  ok(`/privacy names every ${table} column`, missing.length === 0,
     `not named in a <code> tag: ${missing.join(", ")}`);
}

// The field families a reader needs in words, not only as column names.
for (const [label, re] of [
  ["the IP hash and the salt", /hash of your IP address[\s\S]{0,40}salt/i],
  ["that the IP address itself is not stored", /IP address itself is not stored/i],
  ["the device class", /device class/i],
  ["retention", /no automatic expiry/i],
]) ok(`/privacy states ${label}`, re.test(page));

// The form must send the class, never the raw user agent.
const form = readFileSync(join(ROOT, "app/components/FeedbackForm.tsx"), "utf8");
ok("FeedbackForm does not send navigator.userAgent as device_info",
   !/userAgent\.slice|device_info:\s*navigator/.test(form));

if (fail.length) {
  console.error("\n" + fail.map((f) => `FAIL  ${f}`).join("\n"));
  console.error(`\n${fail.length} privacy-fact failure(s)`);
  process.exit(1);
}
const total = [...columns.values()].reduce((a, c) => a + c.size, 0);
console.log(`\nPASS  /privacy names all ${total} stored columns across ${columns.size} tables`);
