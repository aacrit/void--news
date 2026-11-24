/**
 * A minimal in-memory D1 for tests: node:sqlite behind the slice of the
 * D1Database API the Worker uses (prepare / bind / first / all / run).
 * Loads schema.sql and then every file in migrations/, in order, exactly as
 * `npm run db:init` does against the real database.
 */
import { DatabaseSync } from "node:sqlite";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(__dirname, "..");

class Stmt {
  constructor(
    private db: DatabaseSync,
    private sql: string,
    private args: unknown[] = [],
  ) {}
  bind(...args: unknown[]): Stmt {
    return new Stmt(this.db, this.sql, args);
  }
  async first<T = Record<string, unknown>>(): Promise<T | null> {
    const row = this.db.prepare(this.sql).get(...(this.args as never[]));
    return (row as T) ?? null;
  }
  async all<T = Record<string, unknown>>(): Promise<{ results: T[] }> {
    return { results: this.db.prepare(this.sql).all(...(this.args as never[])) as T[] };
  }
  async run(): Promise<{ success: true }> {
    this.db.prepare(this.sql).run(...(this.args as never[]));
    return { success: true };
  }
}

export function makeD1(): { d1: D1Database; raw: DatabaseSync } {
  const raw = new DatabaseSync(":memory:");
  raw.exec("PRAGMA foreign_keys = ON;");
  raw.exec(readFileSync(join(ROOT, "schema.sql"), "utf8"));
  const dir = join(ROOT, "migrations");
  for (const f of readdirSync(dir).filter((x) => x.endsWith(".sql")).sort()) {
    raw.exec(readFileSync(join(dir, f), "utf8"));
  }
  const d1 = { prepare: (sql: string) => new Stmt(raw, sql) } as unknown as D1Database;
  return { d1, raw };
}
