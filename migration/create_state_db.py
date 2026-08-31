"""Build the pipeline's persistent SQLite state DB: schema + rescued data.

The staging DB (void_local.db) has all-TEXT columns and NO constraints/indexes,
so it cannot be the pipeline's working DB (e.g. articles.url UNIQUE dedup would
not fire). This applies the consolidated, typed, constrained schema
(migration/schema_pipeline.sql) to a fresh DB, then copies every row from the
staging DB into it (SQLite coerces TEXT into the typed columns per affinity;
JSONB/array columns are TEXT in both). The result, pipeline_state.db, is the
seed uploaded to Cloudflare R2 and pulled at the start of each pipeline run.

Usage: python create_state_db.py <schema.sql> <staging.db> <out_state.db>
"""
import os
import sqlite3
import sys

SCHEMA = sys.argv[1] if len(sys.argv) > 1 else "schema_pipeline.sql"
STAGING = sys.argv[2] if len(sys.argv) > 2 else "../../rescue/void_local.db"
OUT = sys.argv[3] if len(sys.argv) > 3 else "pipeline_state.db"

if os.path.exists(OUT):
    os.remove(OUT)

# 1) Apply the typed schema.
dst = sqlite3.connect(OUT)
dst.execute("PRAGMA foreign_keys=OFF")  # off during bulk copy; parents/children any order
with open(SCHEMA, "r", encoding="utf-8") as fh:
    dst.executescript(fh.read())
dst.commit()

# Map of table -> [columns] in the destination schema.
dst_tables = {}
for (name,) in dst.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall():
    cols = [r[1] for r in dst.execute(f'PRAGMA table_info("{name}")').fetchall()]
    dst_tables[name] = cols

# 2) Attach the staging DB and copy intersecting rows table by table.
src = sqlite3.connect(STAGING)
src.row_factory = sqlite3.Row
src_tables = {
    r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
}

copied = {}
skipped_rows = {}
for table, dcols in dst_tables.items():
    if table not in src_tables:
        continue
    scols = [r[1] for r in src.execute(f'PRAGMA table_info("{table}")').fetchall()]
    use = [c for c in dcols if c in scols]
    if not use:
        continue
    collist = ", ".join(f'"{c}"' for c in use)
    ph = ", ".join("?" for _ in use)
    ins = f'INSERT OR IGNORE INTO "{table}" ({collist}) VALUES ({ph})'
    n_ok = 0
    n_skip = 0
    batch = []
    for row in src.execute(f'SELECT {collist} FROM "{table}"'):
        batch.append(tuple(row[c] for c in use))
        if len(batch) >= 2000:
            try:
                dst.executemany(ins, batch)
                n_ok += len(batch)
            except sqlite3.Error:
                for b in batch:  # fall back row-by-row so one bad row can't drop the batch
                    try:
                        dst.execute(ins, b); n_ok += 1
                    except sqlite3.Error:
                        n_skip += 1
            batch = []
    if batch:
        try:
            dst.executemany(ins, batch); n_ok += len(batch)
        except sqlite3.Error:
            for b in batch:
                try:
                    dst.execute(ins, b); n_ok += 1
                except sqlite3.Error:
                    n_skip += 1
    dst.commit()
    copied[table] = n_ok
    if n_skip:
        skipped_rows[table] = n_skip

dst.execute("PRAGMA foreign_keys=ON")
dst.commit()

# 3) Report.
print("Copied rows into pipeline_state.db:")
for t in sorted(copied, key=lambda x: -copied[x]):
    if copied[t]:
        extra = f"  ({skipped_rows[t]} skipped)" if t in skipped_rows else ""
        print(f"  {copied[t]:>7}  {t}{extra}")
missing_in_src = sorted(set(dst_tables) - src_tables)
print(f"\nSchema tables with no staging data (start empty): {len(missing_in_src)}")
sz = os.path.getsize(OUT)
print(f"pipeline_state.db: {sz/1e6:.1f} MB")

# 4) Integrity check.
ic = dst.execute("PRAGMA integrity_check").fetchone()[0]
print(f"integrity_check: {ic}")
dst.close()
src.close()
