"""The SQLite shim is shared by every thread; its statements must not interleave.

Step 9 of the pipeline enriches clusters with four workers over the one
module-level client. On 2026-09-30 (run #384) 265 of those writes failed with
"cannot commit - no transaction is active", "another row available" and
"error return without exception set": the workers were interleaving cursors on
one sqlite3 connection. Each failure left a cluster without its bias rollup.
This drives the same shape (an update that selects, writes, commits and reads
back) from several threads and asserts every call lands.
"""
from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.utils.pgrest_sqlite import SqliteClient  # noqa: E402


def test_concurrent_updates_do_not_interleave(tmp_path):
    db = tmp_path / "state.db"
    client = SqliteClient(str(db))
    client._conn.execute(
        'CREATE TABLE story_clusters (id TEXT PRIMARY KEY, n INTEGER, note TEXT)'
    )
    client._conn.commit()
    ids = [f"c{i}" for i in range(400)]
    client.table("story_clusters").insert(
        [{"id": i, "n": 0, "note": ""} for i in ids]
    ).execute()

    def work(cid: str) -> int:
        client.table("story_clusters").select("id,n").eq("id", cid).execute()
        res = client.table("story_clusters").update(
            {"n": 1, "note": "x" * 50}
        ).eq("id", cid).execute()
        return len(res.data)

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(work, ids))  # re-raises the first failure

    assert results == [1] * len(ids)
    rows = client.table("story_clusters").select("n").execute().data
    assert sum(r["n"] for r in rows) == len(ids)


def test_prose_columns_come_back_as_stored(tmp_path):
    """2026-09-28: a body or headline SHAPED like JSON or a pg array was
    decoded to a list, and clustering died calling .split() on it."""
    client = SqliteClient(str(tmp_path / "prose.db"))
    client._conn.execute(
        "CREATE TABLE articles (id TEXT PRIMARY KEY, title TEXT, full_text TEXT,"
        " summary TEXT, rationale TEXT)"
    )
    client._conn.commit()
    row = {
        "id": "a1",
        "title": "{Unknown}",
        "full_text": '[{"@context": "https://schema.org", "@type": "NewsArticle"}]',
        "summary": "[1, 2, 3]",
        "rationale": '{"lean": 50}',
    }
    client.table("articles").insert(row).execute()
    got = client.table("articles").select("*").eq("id", "a1").execute().data[0]
    for col in ("title", "full_text", "summary"):
        assert got[col] == row[col], (col, got[col])
    # a jsonb-typed column still round-trips as an object
    assert got["rationale"] == {"lean": 50}


if __name__ == "__main__":
    import pathlib
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        try:
            test_concurrent_updates_do_not_interleave(pathlib.Path(d))
            test_prose_columns_come_back_as_stored(pathlib.Path(d))
        except Exception as e:  # noqa: BLE001
            print(f"FAIL  concurrent shim writes interleaved: {type(e).__name__}: {e}")
            sys.exit(1)
    print("PASS  the SQLite shim serialises statements across threads and returns prose as stored")
