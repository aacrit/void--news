"""A run that is still running must never be marked stuck by its own cleanup.

`cleanup_stuck_pipeline_runs` fails any run still 'running' after 180 minutes.
`started_at` defaults to SQLite's CURRENT_TIMESTAMP ("2026-10-02 11:07:00")
while the cutoff was Python's isoformat ("2026-10-02T09:07:00+00:00"), and the
two were compared as strings. A space sorts before "T", so a run started on the
cutoff's own date always read as older than it: every run from 09-29 to 10-01
marked ITSELF failed with "timed out (stuck in running state)" and carried
that false error into its record. The comparison is julianday() on both sides.

Planted cases: a run started minutes ago in each stored format must survive;
runs started hours ago in each format must be cleaned.

Run: python3 tests/test_stuck_runs.py   (also collected by pytest)
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.utils.pgrest_sqlite import SqliteClient  # noqa: E402

SCHEMA = (
    "CREATE TABLE pipeline_runs (id TEXT PRIMARY KEY, "
    "started_at TEXT DEFAULT CURRENT_TIMESTAMP, completed_at TEXT, "
    "status TEXT DEFAULT 'running', errors TEXT DEFAULT '[]')"
)


def _status_after_cleanup(rows: list[tuple[str, str | None]]) -> dict[str, str]:
    with tempfile.TemporaryDirectory() as d:
        client = SqliteClient(os.path.join(d, "state.db"))
        client._conn.execute(SCHEMA)
        for rid, started in rows:
            if started is None:  # the column default, exactly as production writes it
                client._conn.execute("INSERT INTO pipeline_runs (id) VALUES (?)", [rid])
            else:
                client._conn.execute(
                    "INSERT INTO pipeline_runs (id, started_at) VALUES (?, ?)", [rid, started])
        client._conn.commit()
        client.rpc("cleanup_stuck_pipeline_runs", {"max_minutes": 180}).execute()
        return {r["id"]: r["status"] for r in
                client._conn.execute("SELECT id, status FROM pipeline_runs").fetchall()}


def test_running_run_is_not_its_own_victim():
    now = datetime.now(timezone.utc)
    recent = now - timedelta(minutes=100)
    old = now - timedelta(hours=5)
    got = _status_after_cleanup([
        ("default-now", None),
        ("space-recent", recent.strftime("%Y-%m-%d %H:%M:%S")),
        ("iso-recent", recent.isoformat()),
        ("space-old", old.strftime("%Y-%m-%d %H:%M:%S")),
        ("iso-old", old.isoformat()),
    ])
    assert got["default-now"] == "running", got
    assert got["space-recent"] == "running", got
    assert got["iso-recent"] == "running", got
    assert got["space-old"] == "failed", got
    assert got["iso-old"] == "failed", got


if __name__ == "__main__":
    test_running_run_is_not_its_own_victim()
    print("PASS  a running run is never cleaned by its own run; a stuck one is, in either timestamp format")
