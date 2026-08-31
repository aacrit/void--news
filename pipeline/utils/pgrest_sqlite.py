"""
pgrest_sqlite.py — a SQLite-backed drop-in replacement for the subset of the
supabase-py / postgrest-py fluent API that the Void News pipeline uses.

Goal: run the ENTIRE pipeline against a local SQLite file with NO changes to
the ~40 call-site files. This module is the sole thing that must be swapped in
place of ``supabase.create_client(url, key)`` (see the companion
``supabase_client.py`` shim / env wiring in the migration branch).

Why this exists
---------------
The pipeline is migrating off Supabase (Postgres + PostgREST) onto Cloudflare.
In GitHub Actions the pipeline will run against a local SQLite working DB that
is synced to R2. Every pipeline module imports one module-level ``supabase``
client and calls the PostgREST fluent API on it:

    supabase.table("story_clusters").select("id,title").eq(...).order(...).execute()
    supabase.rpc("cleanup_stale_articles", {"days": 7}).execute()
    supabase.storage.from_("bucket").upload(path, data, opts)

``SqliteClient`` mirrors that surface against sqlite3.

Design notes / PostgREST-fidelity decisions
--------------------------------------------
* **JSONB round-trip.** Postgres jsonb columns come back as parsed Python
  objects and accept Python dict/list on write. SQLite stores TEXT. On read we
  best-effort ``json.loads`` any value whose text starts with ``{``/``[``. On
  write we ``json.dumps`` any dict/list value. This is how the pipeline reads
  ``bias_diversity``, ``consensus_points``, ``rationale`` etc. as objects.
* **Postgres text[] arrays** are stored by the staged DB as ``{world}`` (pg
  array literal). We parse both ``{...}`` array literals and JSON arrays on
  read, and ``.contains("sections", ["world"])`` does subset membership in
  Python.
* **Numeric ordering.** The staged DB stores every column as TEXT, so a naive
  ``ORDER BY rank_world`` would sort lexically. We order by ``("col" + 0)`` as
  the primary key (SQLite coerces numeric-looking text to a number, non-numeric
  text to 0) and the raw text as a tiebreak. This yields correct numeric order
  for numeric columns and correct lexical order for text columns, on both the
  TEXT-typed staged DB and a properly-typed production DB.
* **Embedded resources.** PostgREST ``select("a, foo(b, bar(c))")`` embeds
  are resolved recursively via FK-name heuristics (``source_id`` -> ``sources``
  to-one; reverse ``bias_scores`` where ``article_id = articles.id`` to-many).
  Column aliases (``article:articles(...)``) are honored.

TODO (integration): swap the ``.storage`` local-filesystem stub for a real
Cloudflare R2 (S3-compatible) client.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# JSON / pg-array (de)serialization
# ---------------------------------------------------------------------------

def _maybe_parse_json(value: Any) -> Any:
    """Best-effort: turn a stored TEXT value into a Python object.

    * JSON objects/arrays (``{...}`` / ``[...]``) -> parsed dict/list.
    * A Postgres array literal (``{world}``, ``{a,b}``) that is NOT valid JSON
      -> parsed to a Python list of strings.
    * Anything else -> returned unchanged.
    """
    if not isinstance(value, str):
        return value
    s = value.strip()
    if not s:
        return value
    first = s[0]
    if first in "{[":
        try:
            return json.loads(s)
        except (ValueError, TypeError):
            # Not JSON. If it looks like a pg array literal, parse that.
            if first == "{" and s.endswith("}"):
                parsed = _parse_pg_array(s)
                if parsed is not None:
                    return parsed
            return value
    return value


def _parse_pg_array(s: str) -> list | None:
    """Parse a Postgres array literal like ``{world}`` or ``{a,b,c}`` into a
    Python list. Returns None if it does not look like one. Handles simple
    double-quoted elements. Does not attempt nested arrays."""
    s = s.strip()
    if not (s.startswith("{") and s.endswith("}")):
        return None
    inner = s[1:-1]
    if inner == "":
        return []
    out: list[str] = []
    buf: list[str] = []
    in_quote = False
    i = 0
    while i < len(inner):
        ch = inner[i]
        if in_quote:
            if ch == "\\" and i + 1 < len(inner):
                buf.append(inner[i + 1])
                i += 2
                continue
            if ch == '"':
                in_quote = False
                i += 1
                continue
            buf.append(ch)
        elif ch == '"':
            in_quote = True
        elif ch == ",":
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    out.append("".join(buf))
    return [e.strip() if e is not None else e for e in out]


def _to_array_value(value: Any) -> list | None:
    """Coerce a stored column value into a Python list for containment checks.
    Accepts an already-parsed list, a JSON array string, or a pg-array literal.
    Returns None if it cannot be interpreted as an array."""
    if isinstance(value, list):
        return value
    parsed = _maybe_parse_json(value)
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, str):
        arr = _parse_pg_array(parsed)
        return arr
    return None


def _encode_for_storage(value: Any) -> Any:
    """Serialize a Python value for storage. dict/list -> JSON text, bool ->
    handled by sqlite (0/1), datetime -> ISO. Everything else unchanged."""
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        # sqlite3 stores bool as 0/1 natively; leave as-is so IntegrityError /
        # comparisons behave. But keep it explicit for readability.
        return 1 if value else 0
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _decode_row(row: sqlite3.Row) -> dict:
    """Turn a sqlite3.Row into a plain dict, JSON-decoding jsonb-ish text."""
    out: dict[str, Any] = {}
    for key in row.keys():
        out[key] = _maybe_parse_json(row[key])
    return out


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

class _Result:
    """Mirrors the postgrest APIResponse: ``.data`` + ``.count``."""

    __slots__ = ("data", "count")

    def __init__(self, data: Any, count: int | None = None):
        self.data = data
        if count is None:
            count = len(data) if isinstance(data, list) else (0 if data is None else 1)
        self.count = count

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        n = len(self.data) if isinstance(self.data, list) else self.data
        return f"_Result(count={self.count}, data={n})"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class SqliteRestError(Exception):
    """Raised for shim-level errors (schema drift, single()-count mismatch,
    constraint violations). Messages are crafted so the pipeline's existing
    ``"duplicate" in str(e).lower()`` / ``"unique" in ...`` / ``"does not
    exist"`` catches keep working."""


# ---------------------------------------------------------------------------
# Embedded-resource (join) select parsing
# ---------------------------------------------------------------------------

class _Embed:
    """A parsed embedded resource in a select spec: ``alias:table(subspec)``."""

    __slots__ = ("alias", "table", "columns", "embeds")

    def __init__(self, alias: str, table: str, columns: list[str], embeds: list["_Embed"]):
        self.alias = alias
        self.table = table
        self.columns = columns
        self.embeds = embeds


def _split_top_level(spec: str) -> list[str]:
    """Split a select spec on top-level commas (ignoring commas inside parens)."""
    parts: list[str] = []
    depth = 0
    buf: list[str] = []
    for ch in spec:
        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return [p for p in parts if p]


def _parse_select(spec: str) -> tuple[list[str], list[_Embed]]:
    """Parse a PostgREST select spec into (plain_columns, embeds).

    Supports ``*``, plain columns, aliased columns (``a:b`` — treated as plain
    column ``b`` for our purposes / rarely used in the pipeline), and embedded
    resources ``[alias:]table(subspec)`` nested arbitrarily deep.
    """
    columns: list[str] = []
    embeds: list[_Embed] = []
    for part in _split_top_level(spec):
        if "(" in part:
            # embedded resource: optional alias before ':'
            head, _, rest = part.partition("(")
            subspec = rest.rsplit(")", 1)[0]
            alias = head.strip()
            table = alias
            if ":" in alias:
                alias, table = alias.split(":", 1)
                alias = alias.strip()
                table = table.strip()
            sub_cols, sub_embeds = _parse_select(subspec)
            embeds.append(_Embed(alias, table, sub_cols, sub_embeds))
        else:
            columns.append(part.strip())
    return columns, embeds


# ---------------------------------------------------------------------------
# The chainable query builder
# ---------------------------------------------------------------------------

# Filters we can express directly in SQL (col, op, value) -> (sql, params).
class _QueryBuilder:
    def __init__(self, client: "SqliteClient", table: str):
        self._client = client
        self._table = table
        self._op: str | None = None          # select/insert/update/upsert/delete
        self._select_spec: str = "*"
        self._plain_cols: list[str] = ["*"]
        self._embeds: list[_Embed] = []
        self._payload: Any = None            # for insert/update/upsert
        self._on_conflict: str | None = None
        self._ignore_duplicates: bool = False
        # SQL-expressible filters as (sql_fragment, params_list)
        self._where: list[tuple[str, list]] = []
        # contains filters, applied in Python: list of (col, required_elements)
        self._contains: list[tuple[str, list]] = []
        self._orders: list[tuple[str, bool]] = []   # (col, desc)
        self._limit: int | None = None
        self._offset: int | None = None
        self._single: str | None = None      # None | 'single' | 'maybe'
        self._pending_negate: bool = False

    # -- column validation -------------------------------------------------
    def _cols(self) -> set[str]:
        return self._client._columns(self._table)

    def _check_col(self, col: str) -> None:
        cols = self._cols()
        if cols and col not in cols:
            raise SqliteRestError(
                f"column \"{col}\" does not exist on table \"{self._table}\" "
                f"(known columns: {sorted(cols)})"
            )

    # -- negation modifier -------------------------------------------------
    @property
    def not_(self) -> "_QueryBuilder":
        self._pending_negate = True
        return self

    def _add_where(self, sql: str, params: list) -> None:
        if self._pending_negate:
            sql = f"NOT ({sql})"
            self._pending_negate = False
        self._where.append((sql, params))

    def _cmp(self, col: str, op: str, val: Any) -> tuple[str, list]:
        """Build a comparison fragment. Numeric values coerce the (TEXT-affinity)
        column numerically via ``("col" + 0)`` so ``word_count >= 100`` is a
        number comparison, not a storage-class one. String values (e.g. ISO
        timestamps) keep plain text comparison so ``published_at >= '2026-...'``
        stays lexical == chronological."""
        if isinstance(val, bool):
            return f'("{col}" + 0) {op} ?', [1 if val else 0]
        if isinstance(val, (int, float)):
            return f'("{col}" + 0) {op} ?', [val]
        return f'"{col}" {op} ?', [_encode_for_storage(val)]

    # -- selection / mutation verbs ---------------------------------------
    def select(self, columns: str = "*", count: str | None = None) -> "_QueryBuilder":
        if self._op is None:
            self._op = "select"
        self._select_spec = columns or "*"
        self._plain_cols, self._embeds = _parse_select(self._select_spec)
        # Validate plain columns (skip '*'). Embedded tables validated lazily.
        if self._plain_cols != ["*"]:
            for c in self._plain_cols:
                if c and c != "*":
                    self._check_col(c)
        return self

    def insert(self, rows: dict | list[dict]) -> "_QueryBuilder":
        self._op = "insert"
        self._payload = rows
        return self

    def update(self, values: dict) -> "_QueryBuilder":
        self._op = "update"
        self._payload = values
        return self

    def upsert(
        self,
        rows: dict | list[dict],
        on_conflict: str | None = None,
        ignore_duplicates: bool = False,
    ) -> "_QueryBuilder":
        self._op = "upsert"
        self._payload = rows
        self._on_conflict = on_conflict
        self._ignore_duplicates = ignore_duplicates
        return self

    def delete(self) -> "_QueryBuilder":
        self._op = "delete"
        return self

    # -- filters -----------------------------------------------------------
    def eq(self, col: str, val: Any) -> "_QueryBuilder":
        self._check_col(col)
        sql, params = self._cmp(col, "=", val)
        self._add_where(sql, params)
        return self

    def neq(self, col: str, val: Any) -> "_QueryBuilder":
        self._check_col(col)
        # PostgREST neq keeps rows where col <> val; NULLs are excluded (SQL).
        sql, params = self._cmp(col, "<>", val)
        self._add_where(sql, params)
        return self

    def gt(self, col: str, val: Any) -> "_QueryBuilder":
        self._check_col(col)
        sql, params = self._cmp(col, ">", val)
        self._add_where(sql, params)
        return self

    def gte(self, col: str, val: Any) -> "_QueryBuilder":
        self._check_col(col)
        sql, params = self._cmp(col, ">=", val)
        self._add_where(sql, params)
        return self

    def lt(self, col: str, val: Any) -> "_QueryBuilder":
        self._check_col(col)
        sql, params = self._cmp(col, "<", val)
        self._add_where(sql, params)
        return self

    def lte(self, col: str, val: Any) -> "_QueryBuilder":
        self._check_col(col)
        sql, params = self._cmp(col, "<=", val)
        self._add_where(sql, params)
        return self

    def in_(self, col: str, values: Iterable) -> "_QueryBuilder":
        self._check_col(col)
        vals = list(values)
        if not vals:
            # PostgREST .in_([]) matches nothing.
            self._add_where("0 = 1", [])
            return self
        placeholders = ",".join("?" for _ in vals)
        self._add_where(
            f'"{col}" IN ({placeholders})',
            [_encode_for_storage(v) for v in vals],
        )
        return self

    def is_(self, col: str, val: Any) -> "_QueryBuilder":
        self._check_col(col)
        # PostgREST .is_(col, None) / .is_(col, 'null') -> IS NULL.
        if val is None or (isinstance(val, str) and val.lower() == "null"):
            self._add_where(f'"{col}" IS NULL', [])
        elif isinstance(val, bool) or (isinstance(val, str) and val.lower() in ("true", "false")):
            b = val if isinstance(val, bool) else (val.lower() == "true")
            self._add_where(f'"{col}" = ?', [1 if b else 0])
        else:
            self._add_where(f'"{col}" IS ?', [_encode_for_storage(val)])
        return self

    def match(self, criteria: dict) -> "_QueryBuilder":
        for col, val in criteria.items():
            self.eq(col, val)
        return self

    def contains(self, col: str, value: list | dict) -> "_QueryBuilder":
        """PostgREST array/jsonb containment (``@>``). Applied in Python: the
        stored value must contain every element (list) / key-value pair (dict)
        given in ``value``."""
        if self._pending_negate:
            raise SqliteRestError("negated .contains() is not supported by the shim")
        self._check_col(col)
        self._contains.append((col, value))
        return self

    # -- modifiers ---------------------------------------------------------
    def order(self, col: str, desc: bool | None = None, ascending: bool | None = None,
              **kwargs) -> "_QueryBuilder":
        self._check_col(col)
        # supabase-py uses order(col, desc=True/False). Also accept an
        # ascending= kwarg (some client versions) and a dict-style options arg.
        if desc is None:
            if ascending is not None:
                desc = not ascending
            elif "ascending" in kwargs:
                desc = not kwargs["ascending"]
            else:
                desc = False
        self._orders.append((col, bool(desc)))
        return self

    def limit(self, n: int) -> "_QueryBuilder":
        self._limit = int(n)
        return self

    def offset(self, n: int) -> "_QueryBuilder":
        self._offset = int(n)
        return self

    def range(self, start: int, end: int) -> "_QueryBuilder":
        # PostgREST .range(a, b) is inclusive, 0-indexed.
        start = int(start)
        end = int(end)
        self._offset = start
        self._limit = end - start + 1
        return self

    def single(self) -> "_QueryBuilder":
        self._single = "single"
        return self

    def maybe_single(self) -> "_QueryBuilder":
        self._single = "maybe"
        return self

    # -- terminal ----------------------------------------------------------
    def execute(self) -> _Result:
        op = self._op or "select"
        if op == "select":
            return self._exec_select()
        if op == "insert":
            return self._exec_insert()
        if op == "update":
            return self._exec_update()
        if op == "upsert":
            return self._exec_upsert()
        if op == "delete":
            return self._exec_delete()
        raise SqliteRestError(f"unknown operation {op!r}")

    # -- SELECT ------------------------------------------------------------
    def _where_sql(self) -> tuple[str, list]:
        if not self._where:
            return "", []
        frags = [f for f, _ in self._where]
        params: list = []
        for _, p in self._where:
            params.extend(p)
        return " WHERE " + " AND ".join(frags), params

    def _order_sql(self) -> str:
        if not self._orders:
            return ""
        clauses = []
        for col, desc in self._orders:
            direction = "DESC" if desc else "ASC"
            # numeric-aware: ("col" + 0) coerces numeric text to number,
            # non-numeric to 0; raw text as the tiebreak.
            clauses.append(f'("{col}" + 0) {direction}, "{col}" {direction}')
        return " ORDER BY " + ", ".join(clauses)

    def _exec_select(self) -> _Result:
        where_sql, params = self._where_sql()
        order_sql = self._order_sql()
        cur = self._client._conn.cursor()

        if self._contains:
            # Must post-filter in Python; push down WHERE + ORDER only.
            sql = f'SELECT * FROM "{self._table}"{where_sql}{order_sql}'
            cur.execute(sql, params)
            rows = [_decode_row(r) for r in cur.fetchall()]
            rows = [r for r in rows if self._passes_contains(r)]
            # apply offset/limit in Python (order already applied by SQL)
            if self._offset:
                rows = rows[self._offset:]
            if self._limit is not None:
                rows = rows[: self._limit]
        else:
            limit_sql = ""
            if self._limit is not None:
                limit_sql = f" LIMIT {int(self._limit)}"
                if self._offset:
                    limit_sql += f" OFFSET {int(self._offset)}"
            elif self._offset:
                # OFFSET requires a LIMIT in SQLite; use -1 (unbounded).
                limit_sql = f" LIMIT -1 OFFSET {int(self._offset)}"
            sql = f'SELECT * FROM "{self._table}"{where_sql}{order_sql}{limit_sql}'
            cur.execute(sql, params)
            rows = [_decode_row(r) for r in cur.fetchall()]

        # Resolve embedded resources, then project columns.
        if self._embeds:
            for row in rows:
                for emb in self._embeds:
                    self._resolve_embed(row, emb)
        rows = [self._project(r) for r in rows]

        return self._finish_select(rows)

    def _project(self, row: dict) -> dict:
        """Restrict a row to the requested plain columns + embedded aliases.
        ``*`` keeps everything (plus any embeds already attached)."""
        if self._plain_cols == ["*"] or "*" in self._plain_cols:
            return row
        keep = set(c for c in self._plain_cols if c)
        # embedded aliases are added under their alias/table key already
        for emb in self._embeds:
            keep.add(emb.alias or emb.table)
        return {k: v for k, v in row.items() if k in keep}

    def _passes_contains(self, row: dict) -> bool:
        for col, needed in self._contains:
            stored = row.get(col)
            if isinstance(needed, dict):
                obj = stored if isinstance(stored, dict) else _maybe_parse_json(stored)
                if not isinstance(obj, dict):
                    return False
                for k, v in needed.items():
                    if obj.get(k) != v:
                        return False
            else:
                arr = _to_array_value(stored)
                if arr is None:
                    return False
                arr_set = set(map(_norm_scalar, arr))
                for elem in needed:
                    if _norm_scalar(elem) not in arr_set:
                        return False
        return True

    def _finish_select(self, rows: list[dict]) -> _Result:
        count = len(rows)
        if self._single == "single":
            if len(rows) != 1:
                raise SqliteRestError(
                    f"JSON object requested, multiple (or no) rows returned "
                    f"({len(rows)} rows) for table \"{self._table}\""
                )
            return _Result(rows[0], count=1)
        if self._single == "maybe":
            if len(rows) == 0:
                return _Result(None, count=0)
            if len(rows) > 1:
                raise SqliteRestError(
                    f"maybe_single(): multiple rows returned ({len(rows)}) "
                    f"for table \"{self._table}\""
                )
            return _Result(rows[0], count=1)
        return _Result(rows, count=count)

    # -- embedded-resource resolution -------------------------------------
    def _resolve_embed(self, row: dict, emb: _Embed) -> None:
        base = self._table
        target = emb.table
        key = emb.alias or emb.table
        cols_base = self._client._columns(base)
        cols_target = self._client._columns(target)

        fk_to_one = f"{_singular(target)}_id"   # e.g. sources -> source_id on base
        fk_to_many = f"{_singular(base)}_id"    # e.g. articles -> article_id on target

        cur = self._client._conn.cursor()
        if fk_to_one in cols_base:
            # to-one: target.id == base[fk_to_one]
            fk_val = row.get(fk_to_one)
            if fk_val is None:
                row[key] = None
                return
            cur.execute(f'SELECT * FROM "{target}" WHERE "id" = ? LIMIT 1',
                        [_encode_for_storage(fk_val)])
            sub = cur.fetchone()
            sub_row = _decode_row(sub) if sub else None
            if sub_row is not None:
                for sub_emb in emb.embeds:
                    self._resolve_embed_for(target, sub_row, sub_emb)
                sub_row = _project_cols(sub_row, emb)
            row[key] = sub_row
        elif fk_to_many in cols_target:
            # to-many (reverse FK): target rows where target[fk_to_many] == base.id
            base_id = row.get("id")
            cur.execute(f'SELECT * FROM "{target}" WHERE "{fk_to_many}" = ?',
                        [_encode_for_storage(base_id)])
            subs = [_decode_row(r) for r in cur.fetchall()]
            for sub_row in subs:
                for sub_emb in emb.embeds:
                    self._resolve_embed_for(target, sub_row, sub_emb)
            subs = [_project_cols(r, emb) for r in subs]
            row[key] = subs
        else:
            raise SqliteRestError(
                f"cannot resolve embedded resource \"{target}\" from \"{base}\": "
                f"no FK column \"{fk_to_one}\" on \"{base}\" and no reverse FK "
                f"\"{fk_to_many}\" on \"{target}\". Embedded selects rely on "
                f"<singular>_id naming; add an explicit resolver if needed."
            )

    def _resolve_embed_for(self, base_table: str, row: dict, emb: _Embed) -> None:
        """Same as _resolve_embed but with an explicit base table (for nested
        embeds where the base is not self._table)."""
        saved = self._table
        self._table = base_table
        try:
            self._resolve_embed(row, emb)
        finally:
            self._table = saved

    # -- INSERT ------------------------------------------------------------
    def _normalize_rows(self, payload: Any) -> list[dict]:
        if payload is None:
            return []
        if isinstance(payload, dict):
            return [payload]
        return list(payload)

    def _prepare_row_for_write(self, row: dict, is_insert: bool) -> dict:
        cols = self._cols()
        prepared: dict[str, Any] = {}
        for k, v in row.items():
            if cols and k not in cols:
                raise SqliteRestError(
                    f"column \"{k}\" does not exist on table \"{self._table}\" "
                    f"(known columns: {sorted(cols)})"
                )
            prepared[k] = _encode_for_storage(v)
        if is_insert:
            # gen_random_uuid() default for an id column.
            if "id" in cols and prepared.get("id") in (None,) and "id" not in row:
                prepared["id"] = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()
            if "created_at" in cols and "created_at" not in prepared:
                prepared["created_at"] = now
            if "updated_at" in cols and "updated_at" not in prepared:
                prepared["updated_at"] = now
        return prepared

    def _exec_insert(self) -> _Result:
        rows = self._normalize_rows(self._payload)
        inserted: list[dict] = []
        cur = self._client._conn.cursor()
        for raw in rows:
            prepared = self._prepare_row_for_write(raw, is_insert=True)
            cols = list(prepared.keys())
            placeholders = ",".join("?" for _ in cols)
            col_sql = ",".join(f'"{c}"' for c in cols)
            sql = f'INSERT INTO "{self._table}" ({col_sql}) VALUES ({placeholders})'
            try:
                cur.execute(sql, [prepared[c] for c in cols])
            except sqlite3.IntegrityError as e:
                self._client._conn.rollback()
                raise _wrap_integrity(e)
            inserted.append(self._read_back(cur, prepared))
        self._client._conn.commit()
        return _Result(inserted, count=len(inserted))

    def _read_back(self, cur: sqlite3.Cursor, prepared: dict) -> dict:
        """Return the stored row as PostgREST would (return=representation)."""
        cols = self._cols()
        if "id" in cols and prepared.get("id") is not None:
            cur.execute(f'SELECT * FROM "{self._table}" WHERE "id" = ? LIMIT 1',
                        [prepared["id"]])
            got = cur.fetchone()
            if got:
                return _decode_row(got)
        # No id: reconstruct from prepared values (decode json-ish).
        return {k: _maybe_parse_json(v) for k, v in prepared.items()}

    # -- UPDATE ------------------------------------------------------------
    def _exec_update(self) -> _Result:
        values = dict(self._payload or {})
        cols = self._cols()
        # updated_at bump if present and not explicitly set (mirrors triggers).
        if "updated_at" in cols and "updated_at" not in values:
            values["updated_at"] = datetime.now(timezone.utc).isoformat()
        set_cols = []
        set_params: list = []
        for k, v in values.items():
            if cols and k not in cols:
                raise SqliteRestError(
                    f"column \"{k}\" does not exist on table \"{self._table}\""
                )
            set_cols.append(f'"{k}" = ?')
            set_params.append(_encode_for_storage(v))
        where_sql, where_params = self._where_sql()
        # capture affected ids first (for return=representation)
        cur = self._client._conn.cursor()
        affected_ids: list = []
        if "id" in cols:
            cur.execute(f'SELECT "id" FROM "{self._table}"{where_sql}', where_params)
            affected_ids = [r["id"] for r in cur.fetchall()]
        sql = f'UPDATE "{self._table}" SET {", ".join(set_cols)}{where_sql}'
        try:
            cur.execute(sql, set_params + where_params)
        except sqlite3.IntegrityError as e:
            self._client._conn.rollback()
            raise _wrap_integrity(e)
        self._client._conn.commit()
        # read back affected rows
        rows: list[dict] = []
        if "id" in cols and affected_ids:
            placeholders = ",".join("?" for _ in affected_ids)
            cur.execute(f'SELECT * FROM "{self._table}" WHERE "id" IN ({placeholders})',
                        affected_ids)
            rows = [_decode_row(r) for r in cur.fetchall()]
        else:
            # best-effort: re-run the WHERE to fetch current state
            cur.execute(f'SELECT * FROM "{self._table}"{where_sql}', where_params)
            rows = [_decode_row(r) for r in cur.fetchall()]
        return _Result(rows, count=len(rows))

    # -- UPSERT ------------------------------------------------------------
    def _exec_upsert(self) -> _Result:
        rows = self._normalize_rows(self._payload)
        conflict_cols = [c.strip() for c in (self._on_conflict or "id").split(",") if c.strip()]
        cols_known = self._cols()
        result_rows: list[dict] = []
        cur = self._client._conn.cursor()
        for raw in rows:
            prepared = self._prepare_row_for_write(raw, is_insert=True)
            insert_cols = list(prepared.keys())
            placeholders = ",".join("?" for _ in insert_cols)
            col_sql = ",".join(f'"{c}"' for c in insert_cols)
            conflict_sql = ",".join(f'"{c}"' for c in conflict_cols)
            if self._ignore_duplicates:
                action = "DO NOTHING"
            else:
                update_targets = [c for c in insert_cols if c not in conflict_cols]
                if update_targets:
                    set_sql = ",".join(f'"{c}" = excluded."{c}"' for c in update_targets)
                    action = f"DO UPDATE SET {set_sql}"
                else:
                    action = "DO NOTHING"
            sql = (
                f'INSERT INTO "{self._table}" ({col_sql}) VALUES ({placeholders}) '
                f'ON CONFLICT ({conflict_sql}) {action}'
            )
            try:
                cur.execute(sql, [prepared[c] for c in insert_cols])
            except sqlite3.IntegrityError as e:
                self._client._conn.rollback()
                raise _wrap_integrity(e)
            result_rows.append(self._read_back_upsert(cur, prepared, conflict_cols))
        self._client._conn.commit()
        return _Result(result_rows, count=len(result_rows))

    def _read_back_upsert(self, cur, prepared: dict, conflict_cols: list[str]) -> dict:
        # Read back by conflict key (works for id or a unique column like url).
        where = " AND ".join(f'"{c}" = ?' for c in conflict_cols)
        params = [prepared.get(c) for c in conflict_cols]
        if all(p is not None for p in params):
            cur.execute(f'SELECT * FROM "{self._table}" WHERE {where} LIMIT 1', params)
            got = cur.fetchone()
            if got:
                return _decode_row(got)
        return {k: _maybe_parse_json(v) for k, v in prepared.items()}

    # -- DELETE ------------------------------------------------------------
    def _exec_delete(self) -> _Result:
        cols = self._cols()
        where_sql, where_params = self._where_sql()
        cur = self._client._conn.cursor()
        # capture rows to return (representation)
        cur.execute(f'SELECT * FROM "{self._table}"{where_sql}', where_params)
        deleted = [_decode_row(r) for r in cur.fetchall()]
        cur.execute(f'DELETE FROM "{self._table}"{where_sql}', where_params)
        self._client._conn.commit()
        return _Result(deleted, count=len(deleted))


def _norm_scalar(v: Any) -> Any:
    """Normalize a scalar for array-membership comparison (str-compare)."""
    if isinstance(v, str):
        return v
    return str(v)


def _singular(table: str) -> str:
    """Very small pluralization inverse: sources->source, articles->article,
    categories->category, stories->story. Good enough for FK-name heuristics."""
    if table.endswith("ies"):
        return table[:-3] + "y"
    if table.endswith("ses") or table.endswith("xes") or table.endswith("zes"):
        return table[:-2]
    if table.endswith("s"):
        return table[:-1]
    return table


def _project_cols(row: dict, emb: _Embed) -> dict:
    """Project an embedded row to its requested columns (+ nested aliases)."""
    if emb.columns == ["*"] or "*" in emb.columns or not emb.columns:
        return row
    keep = set(c for c in emb.columns if c)
    for sub in emb.embeds:
        keep.add(sub.alias or sub.table)
    return {k: v for k, v in row.items() if k in keep}


def _wrap_integrity(e: sqlite3.IntegrityError) -> SqliteRestError:
    """Re-raise a sqlite IntegrityError as a SqliteRestError whose message
    always contains 'unique'/'duplicate' when it is a uniqueness violation, so
    the pipeline's substring catches keep working."""
    msg = str(e)
    low = msg.lower()
    if "unique" in low or "primary key" in low:
        return SqliteRestError(f"duplicate key value violates unique constraint: {msg}")
    return SqliteRestError(msg)


# ---------------------------------------------------------------------------
# Storage stub (local filesystem; TODO: swap for Cloudflare R2 S3 client)
# ---------------------------------------------------------------------------

class _StorageBucket:
    def __init__(self, root: str, bucket: str):
        self._root = root
        self._bucket = bucket

    def _path(self, path: str) -> str:
        safe = path.lstrip("/")
        return os.path.join(self._root, self._bucket, *safe.split("/"))

    def upload(self, path: str, data: bytes, file_options: dict | None = None, **kwargs):
        """Write bytes to ._r2_stage/<bucket>/<path>.

        TODO(migration): replace with a Cloudflare R2 (S3-compatible) PutObject.
        Signature mirrors storage3: upload(path, file, file_options)."""
        dest = self._path(path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if isinstance(data, str):
            data = data.encode("utf-8")
        with open(dest, "wb") as fh:
            fh.write(data)
        return {"path": path, "fullPath": f"{self._bucket}/{path}"}

    def get_public_url(self, path: str) -> str:
        # TODO(migration): return the real R2/CDN URL for the object.
        return f"file://{self._path(path)}"

    def remove(self, paths):
        removed = []
        for p in (paths if isinstance(paths, (list, tuple)) else [paths]):
            fp = self._path(p)
            try:
                os.remove(fp)
                removed.append(p)
            except OSError:
                pass
        return removed

    def list(self, path: str = "", **kwargs):
        base = self._path(path) if path else os.path.join(self._root, self._bucket)
        try:
            return [{"name": n} for n in os.listdir(base)]
        except OSError:
            return []


class _Storage:
    def __init__(self, root: str):
        self._root = root

    def from_(self, bucket: str) -> _StorageBucket:
        return _StorageBucket(self._root, bucket)

    # storage3 also exposes create_bucket/get_bucket; provide no-op stubs.
    def create_bucket(self, *args, **kwargs):
        return {"name": args[0] if args else kwargs.get("id")}

    def get_bucket(self, *args, **kwargs):
        return {"name": args[0] if args else kwargs.get("id")}


# ---------------------------------------------------------------------------
# The client
# ---------------------------------------------------------------------------

class SqliteClient:
    """Drop-in replacement for a supabase-py Client, backed by SQLite."""

    def __init__(self, db_path: str, storage_root: str | None = None):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        try:
            self._conn.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error:
            pass
        self._col_cache: dict[str, set[str]] = {}
        if storage_root is None:
            storage_root = os.path.join(os.path.dirname(os.path.abspath(db_path)), "._r2_stage")
        self.storage = _Storage(storage_root)

    # -- schema introspection ---------------------------------------------
    def _columns(self, table: str) -> set[str]:
        if table not in self._col_cache:
            cur = self._conn.cursor()
            try:
                cur.execute(f'PRAGMA table_info("{table}")')
                cols = {r["name"] for r in cur.fetchall()}
            except sqlite3.Error:
                cols = set()
            if not cols:
                # Unknown table — leave cache empty set so filters skip
                # validation (fail-open) but reads/writes will still error at
                # SQL level with a clear message.
                self._col_cache[table] = set()
            else:
                self._col_cache[table] = cols
        return self._col_cache[table]

    # -- fluent entry points ----------------------------------------------
    def table(self, name: str) -> _QueryBuilder:
        return _QueryBuilder(self, name)

    # supabase-py exposes .from_ as an alias for .table
    def from_(self, name: str) -> _QueryBuilder:
        return _QueryBuilder(self, name)

    def close(self) -> None:
        try:
            self._conn.close()
        except sqlite3.Error:
            pass

    # -- RPCs --------------------------------------------------------------
    def rpc(self, name: str, params: dict | None = None) -> "_RpcCall":
        return _RpcCall(self, name, params or {})


class _RpcCall:
    """Deferred RPC so callers can do ``supabase.rpc(name, params).execute()``."""

    def __init__(self, client: SqliteClient, name: str, params: dict):
        self._client = client
        self._name = name
        self._params = params

    def execute(self) -> _Result:
        handler = _RPC_HANDLERS.get(self._name)
        if handler is None:
            # Unknown RPC. Craft a message the pipeline recognizes as a missing
            # function so its fallback paths engage.
            raise SqliteRestError(
                f"function {self._name}(...) does not exist"
            )
        return handler(self._client, self._params)


# ---------------------------------------------------------------------------
# RPC implementations
# ---------------------------------------------------------------------------

def _iso_days_ago(days: int) -> str:
    from datetime import timedelta
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _iso_minutes_ago(minutes: int) -> str:
    from datetime import timedelta
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


def _rpc_refresh_cluster_enrichment(client: SqliteClient, params: dict) -> _Result:
    """Dropped Postgres RPC (migrations 002/004/076/078). The pipeline
    (main.py `_enrich_cluster` / bias_aggregation.py) already contains a
    byte-for-byte Python fallback that fires when this function 'does not
    exist'. We deliberately raise that exact error so the pipeline computes
    `divergence_score` + `bias_diversity` in Python. See PORT_NOTES.md §3."""
    raise SqliteRestError(
        "function refresh_cluster_enrichment(uuid) does not exist "
        "(re-implemented in pipeline/utils/bias_aggregation.py — Python fallback)"
    )


def _rpc_cleanup_stale_clusters(client: SqliteClient, params: dict) -> _Result:
    days = int(params.get("max_age_days", params.get("days", 7)) or 7)
    cutoff = _iso_days_ago(days)
    cur = client._conn.cursor()
    cur.execute("DELETE FROM story_clusters WHERE first_published < ?", [cutoff])
    n = cur.rowcount
    client._conn.commit()
    return _Result(n, count=n)


def _rpc_cleanup_stuck_pipeline_runs(client: SqliteClient, params: dict) -> _Result:
    minutes = int(params.get("max_minutes", 30) or 30)
    cutoff = _iso_minutes_ago(minutes)
    cur = client._conn.cursor()
    cur.execute(
        "SELECT id, errors FROM pipeline_runs "
        "WHERE status = 'running' AND started_at < ?",
        [cutoff],
    )
    stuck = cur.fetchall()
    now = datetime.now(timezone.utc).isoformat()
    err_entry = {
        "error": "Pipeline run timed out (stuck in running state)",
        "timestamp": now,
    }
    for r in stuck:
        existing = _maybe_parse_json(r["errors"]) or []
        if not isinstance(existing, list):
            existing = []
        existing.append(err_entry)
        cur.execute(
            "UPDATE pipeline_runs SET status='failed', completed_at=?, errors=? "
            "WHERE id=?",
            [now, json.dumps(existing), r["id"]],
        )
    n = len(stuck)
    client._conn.commit()
    return _Result(n, count=n)


def _rpc_cleanup_stale_articles(client: SqliteClient, params: dict) -> _Result:
    days = int(params.get("days", 8) or 8)
    cutoff = _iso_days_ago(days)
    cur = client._conn.cursor()
    cur.execute("DELETE FROM articles WHERE published_at < ?", [cutoff])
    n = cur.rowcount
    client._conn.commit()
    return _Result(n, count=n)


def _rpc_cleanup_diagnostic_tables(client: SqliteClient, params: dict) -> _Result:
    snapshot_days = int(params.get("snapshot_days", 3) or 3)
    run_days = int(params.get("run_days", 14) or 14)
    sandbox_days = int(params.get("sandbox_days", 7) or 7)
    cur = client._conn.cursor()

    def _prune(table: str, days: int) -> int:
        if not client._columns(table):
            return 0
        cutoff = _iso_days_ago(days)
        try:
            cur.execute(f'DELETE FROM "{table}" WHERE created_at < ?', [cutoff])
            return cur.rowcount
        except sqlite3.Error:
            return 0

    snap_n = _prune("engine_snapshots", snapshot_days)
    sandbox_n = _prune("sandbox_runs", sandbox_days)
    run_n = _prune("engine_runs", run_days)
    client._conn.commit()

    try:
        db_bytes = os.path.getsize(client._db_path)
    except OSError:
        db_bytes = 0
    db_size_mb = round(db_bytes / (1024 * 1024), 1)

    payload = {
        "engine_snapshots_pruned": snap_n,
        "engine_runs_pruned": run_n,
        "sandbox_runs_pruned": sandbox_n,
        "db_size_mb": db_size_mb,
    }
    return _Result(payload, count=1)


def _rpc_printed_archive_stats(client: SqliteClient, params: dict) -> _Result:
    cur = client._conn.cursor()

    def _count(table: str) -> int:
        if not client._columns(table):
            return 0
        try:
            cur.execute(f'SELECT COUNT(*) AS n FROM "{table}"')
            return int(cur.fetchone()["n"])
        except sqlite3.Error:
            return 0

    days = _count("printed_days")
    stories = _count("printed_stories")
    # Approximate the two tables' on-disk size via dbstat if available,
    # else fall back to a rough per-row estimate.
    total_bytes = 0.0
    try:
        cur.execute(
            "SELECT SUM(pgsize) AS b FROM dbstat WHERE name IN "
            "('printed_stories','printed_days')"
        )
        row = cur.fetchone()
        if row and row["b"] is not None:
            total_bytes = float(row["b"])
    except sqlite3.Error:
        total_bytes = 0.0
    if total_bytes == 0.0:
        # rough estimate: ~2 KB/story + ~0.2 KB/day
        total_bytes = stories * 2048 + days * 200

    total_mb = round(total_bytes / 1048576.0, 2)
    kb_per_day = round(total_bytes / 1024.0 / days, 1) if days > 0 else 0
    payload = {
        "days": days,
        "stories": stories,
        "total_mb": total_mb,
        "kb_per_day": kb_per_day,
    }
    return _Result(payload, count=1)


_RPC_HANDLERS = {
    "refresh_cluster_enrichment": _rpc_refresh_cluster_enrichment,
    "cleanup_stale_clusters": _rpc_cleanup_stale_clusters,
    "cleanup_stuck_pipeline_runs": _rpc_cleanup_stuck_pipeline_runs,
    "cleanup_stale_articles": _rpc_cleanup_stale_articles,
    "cleanup_diagnostic_tables": _rpc_cleanup_diagnostic_tables,
    "printed_archive_stats": _rpc_printed_archive_stats,
    # NOTE: search_printed_stories (migration 075, Postgres FTS) is intentionally
    # NOT implemented here — it is a Worker/D1 concern (FTS5 + bm25 ranking), not
    # a pipeline call. It has no `.rpc(` call site in pipeline/. See PORT_NOTES §3.
}


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_client(db_path: str, key: str | None = None, **kwargs) -> SqliteClient:
    """Factory mirroring supabase.create_client(url, key). Here ``db_path`` is
    a path to the local SQLite working DB. ``key`` is ignored (kept for
    signature compatibility)."""
    storage_root = kwargs.pop("storage_root", None)
    return SqliteClient(db_path, storage_root=storage_root)
