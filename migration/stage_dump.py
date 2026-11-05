"""Stage a Postgres pg_dump (plain, COPY format, gzipped) into a local SQLite DB.

Loads EVERY `COPY public.<table> (...) FROM stdin;` block as an all-TEXT table
(SQLite is dynamically typed; JSONB/arrays are kept as their dumped text form).
This staging DB is the single source for: static-JSON emit, the pipeline working
DB seed, and the D1 write-table seed. The 147 MB dump is streamed, never held in
memory whole, and nothing here is printed except summary counts.
"""
import gzip
import os
import re
import sqlite3
import sys

DUMP = sys.argv[1] if len(sys.argv) > 1 else "backup-2026-08-30.sql.gz"
OUT = sys.argv[2] if len(sys.argv) > 2 else "void_local.db"

if os.path.exists(OUT):
    os.remove(OUT)

conn = sqlite3.connect(OUT)
conn.execute("PRAGMA journal_mode=OFF")
conn.execute("PRAGMA synchronous=OFF")

COPY_RE = re.compile(r"^COPY public\.(\S+)\s*\(([^)]*)\)\s+FROM stdin;")

_UNESCAPE = {
    "\\N": None,  # handled separately (whole-field)
}


def unescape(field: str):
    if field == "\\N":
        return None
    # Order matters: handle backslash escapes pg_dump emits in COPY text format.
    out = []
    i = 0
    n = len(field)
    while i < n:
        c = field[i]
        if c == "\\" and i + 1 < n:
            nxt = field[i + 1]
            mapping = {"t": "\t", "n": "\n", "r": "\r", "\\": "\\"}
            if nxt in mapping:
                out.append(mapping[nxt])
                i += 2
                continue
        out.append(c)
        i += 1
    return "".join(out)


def ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


tables_loaded = {}
cur = conn.cursor()

with gzip.open(DUMP, "rt", encoding="utf-8", errors="replace") as fh:
    in_copy = False
    table = None
    cols = None
    insert_sql = None
    batch = []
    BATCH = 5000
    for line in fh:
        if not in_copy:
            m = COPY_RE.match(line)
            if m:
                table = m.group(1)
                cols = [c.strip().strip('"') for c in m.group(2).split(",")]
                coldefs = ", ".join(ident(c) + " TEXT" for c in cols)
                cur.execute(f"DROP TABLE IF EXISTS {ident(table)}")
                cur.execute(f"CREATE TABLE {ident(table)} ({coldefs})")
                placeholders = ", ".join("?" for _ in cols)
                collist = ", ".join(ident(c) for c in cols)
                insert_sql = f"INSERT INTO {ident(table)} ({collist}) VALUES ({placeholders})"
                in_copy = True
                batch = []
                tables_loaded[table] = 0
            continue
        # inside a COPY block
        if line.rstrip("\n") == "\\.":
            if batch:
                cur.executemany(insert_sql, batch)
                batch = []
            in_copy = False
            table = None
            continue
        row = line.rstrip("\n").split("\t")
        # COPY rows have exactly len(cols) fields; be defensive on mismatch.
        if len(row) != len(cols):
            # pad/truncate defensively (rare; malformed embedded control chars)
            if len(row) < len(cols):
                row = row + ["\\N"] * (len(cols) - len(row))
            else:
                row = row[: len(cols)]
        batch.append(tuple(unescape(f) for f in row))
        tables_loaded[table] += 1
        if len(batch) >= BATCH:
            cur.executemany(insert_sql, batch)
            batch = []

conn.commit()

# Report
print("Staged tables (rows):")
for t in sorted(tables_loaded, key=lambda x: -tables_loaded[x]):
    print(f"  {tables_loaded[t]:>7}  {t}")
sz = os.path.getsize(OUT)
print(f"\nSQLite staging DB: {OUT}  ({sz/1e6:.1f} MB)")
conn.close()
