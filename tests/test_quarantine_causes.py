#!/usr/bin/env python3
"""Every quarantined feed carries the cause of its failures (P2-6, rev 85).

260 of 1,061 sources were quarantined on 2026-10-01 under statuses that could
not tell a 429 rate limit from a 403 block from a dead URL ("http_4xx"), an SSL
failure from a refused connection ("other"), or an empty Google News search
from a broken feed ("parse_error"). The fetcher now records a named cause on
every failure, and `scripts/roster/quarantine_report.py` counts them.

Asserts, with no network:
  - each failure class maps to its cause (planted exceptions and planted feeds);
  - every status the fetcher can write is one the report recognises;
  - the health update writes a cause on every failure, so a feed that crosses
    the threshold is quarantined WITH its cause, on the real schema;
  - the report counts per cause and fails on a quarantined row with none;
  - nothing here, or in the report, releases a quarantined feed.
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import sqlite3
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
_tmp = tempfile.mkdtemp(prefix="void-quarantine-")
DB = os.path.join(_tmp, "state.db")
os.environ["VOID_SQLITE_PATH"] = DB
_c = sqlite3.connect(DB)
_c.executescript((ROOT / "migration" / "schema_pipeline.sql").read_text(encoding="utf-8"))
_c.close()
sys.path.insert(0, str(ROOT / "pipeline"))

import requests  # noqa: E402
from fetchers import rss_fetcher as rf  # noqa: E402
from utils.safe_requests import BlockedAddressError  # noqa: E402

failures: list[str] = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        failures.append(name)


# --- 1. Exceptions map to causes -----------------------------------------------
def http_error(code):
    resp = requests.Response()
    resp.status_code = code
    return requests.exceptions.HTTPError(response=resp)


PLANTED = [
    (requests.exceptions.ReadTimeout(), "timeout"),
    (http_error(429), "http_429"),
    (http_error(403), "http_403"),
    (http_error(503), "http_503"),
    (requests.exceptions.SSLError("certificate verify failed"), "ssl"),
    (requests.exceptions.ConnectionError("Max retries exceeded ([SSL: WRONG_VERSION_NUMBER])"), "ssl"),
    (requests.exceptions.ConnectionError("Temporary failure in name resolution"), "dns"),
    (requests.exceptions.ConnectionError("Connection refused"), "connection"),
    (BlockedAddressError("DNS resolution failed for x.example: gaierror"), "dns"),
    (BlockedAddressError("Blocked IP literal: 169.254.169.254"), "blocked"),
    (ValueError("boom"), "other"),
]
for exc, want in PLANTED:
    got = rf.classify_fetch_error(exc)
    check(f"{type(exc).__name__} -> {want}", got == want, got)
    check(f"'{got}' is a status the report recognises", rf.is_known_status(got))

# --- 2. Planted feeds ------------------------------------------------------------
class _Resp:
    def __init__(self, body: bytes, code: int = 200):
        self.content = body
        self.text = body.decode("utf-8", "replace")
        self.status_code = code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise http_error(self.status_code)


def feed(items: str) -> bytes:
    return (f'<?xml version="1.0"?><rss version="2.0"><channel><title>T</title>'
            f'<link>https://x.example/</link><description>d</description>{items}'
            f'</channel></rss>').encode()


OLD = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(time.time() - 40 * 86400))
NEW = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime(time.time() - 3600))
CASES = [
    ("a well-formed feed with no entries is 'empty', not a parse error", _Resp(feed("")), "empty"),
    ("an HTML page is a parse error", _Resp(b"<html><body>Not a feed</body></html>"), "parse_error"),
    ("a feed whose every entry is past the age limit is 'stale'",
     _Resp(feed(f"<item><title>An old story about the harbour</title><link>https://x.example/a</link>"
                f"<pubDate>{OLD}</pubDate></item>")), "stale"),
    ("a live feed is 'ok'",
     _Resp(feed(f"<item><title>A new story about the harbour</title><link>https://x.example/b</link>"
                f"<pubDate>{NEW}</pubDate></item>")), "ok"),
    ("a 429 keeps its code", _Resp(b"", 429), "http_429"),
]
_real = rf.safe_get
for name, resp, want in CASES:
    rf.safe_get = lambda *a, _r=resp, **k: _r
    try:
        _, status = rf._fetch_single_feed({"name": "X", "rss_url": "https://x.example/rss", "id": "x"})
    finally:
        rf.safe_get = _real
    check(name, status == want, status)
check("'stale' is not a failure (it resets the counter like ok)",
      "stale" in rf.NON_FAILURE_STATUSES and "stale" not in rf.FAILURE_CAUSES)
check("the retired coarse statuses are not written any more",
      not any(s in (ROOT / "pipeline" / "fetchers" / "rss_fetcher.py").read_text(encoding="utf-8")
              for s in ('"http_4xx"', '"http_5xx"')))

# --- 3. The health update quarantines with a cause, on the real schema -----------
from utils.supabase_client import supabase  # noqa: E402

for sid, cff in (("s-rate", 4), ("s-ok", 4), ("s-stale", 2), ("s-ssl", 0)):
    supabase.table("sources").insert({
        "id": sid, "slug": sid, "name": sid, "url": "https://x.example", "tier": "independent",
        "country": "US", "type": "commercial", "consecutive_fetch_failures": cff}).execute()
rf._update_source_health({"s-rate": "http_429", "s-ok": "ok", "s-stale": "stale", "s-ssl": "ssl"})
rows = {r["id"]: r for r in supabase.table("sources").select(
    "id,consecutive_fetch_failures,last_fetch_status").execute().data}
check("a fifth failure quarantines the feed and records why",
      rows["s-rate"]["consecutive_fetch_failures"] == rf.QUARANTINE_THRESHOLD
      and rows["s-rate"]["last_fetch_status"] == "http_429", str(rows["s-rate"]))
check("a failure below the threshold records its cause too", rows["s-ssl"]["last_fetch_status"] == "ssl")
check("ok resets the counter", rows["s-ok"]["consecutive_fetch_failures"] == 0)
check("stale resets the counter and says stale",
      rows["s-stale"]["consecutive_fetch_failures"] == 0 and rows["s-stale"]["last_fetch_status"] == "stale")

# --- 4. The report ------------------------------------------------------------------
spec = importlib.util.spec_from_file_location("quarantine_report", ROOT / "scripts" / "roster" / "quarantine_report.py")
qr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qr)
check("the report reads the fetcher's threshold and causes",
      qr.THRESHOLD == rf.QUARANTINE_THRESHOLD and tuple(qr.FAILURE_CAUSES) == tuple(rf.FAILURE_CAUSES))
conn = sqlite3.connect(DB)
for sid, cff, st in (("q-legacy", 16, "http_4xx"), ("q-empty", 6, "empty"), ("q-none", 9, None)):
    conn.execute("insert into sources(id, slug, name, url, tier, country, type, rss_url, "
                 "consecutive_fetch_failures, last_fetch_status, last_fetch_at) "
                 "values (?,?,?,?,?,?,?,?,?,?,?)",
                 (sid, sid, sid, "https://x.example", "independent", "US", "commercial",
                  "https://news.google.com/rss/search?q=site:x" if sid == "q-empty" else "https://x.example/rss",
                  cff, st, "2026-09-06T11:00:00+00:00"))
conn.commit()
rep = qr.report(conn, [{"id": "q-empty", "rss_url": "https://x.example/new.xml"}])
check("the report counts per cause",
      rep["by_cause"].get("http_429") == 1 and rep["by_cause"].get("empty") == 1, str(rep["by_cause"]))
check("a pre-rev-85 status is named as legacy, not guessed",
      rep["by_cause"].get("legacy: http 4xx, code not recorded") == 1)
check("a quarantined row with no cause is listed as unrecorded", rep["unrecorded"] == ["q-none"])
check("a feed whose roster URL changed since is flagged", rep["url_changed_since"] == ["q-empty"])
check("Google News feeds are told apart", rep["by_feed_class"].get("google_news") == 1)
rc = os.system(f'"{sys.executable}" "{ROOT / "scripts" / "roster" / "quarantine_report.py"}" '
               f'--db "{DB}" > /dev/null 2>&1')
check("the script exits non-zero while a quarantined row has no cause", rc != 0)
conn.execute("update sources set last_fetch_status='timeout' where id='q-none'")
conn.commit()
check("and zero once every quarantined row carries one", qr.report(conn)["unrecorded"] == [])
before = conn.execute("select sum(consecutive_fetch_failures) from sources").fetchone()[0]
qr.report(conn)
check("the report releases nothing", conn.execute(
    "select sum(consecutive_fetch_failures) from sources").fetchone()[0] == before)
src = (ROOT / "scripts" / "roster" / "quarantine_report.py").read_text(encoding="utf-8")
check("the report never writes to the DB", not any(w in src.lower() for w in ("update sources", "insert into", "delete from")))

if failures:
    print(f"\nFAIL  {len(failures)} quarantine-cause check(s)")
    sys.exit(1)
print("\nPASS  every quarantined feed says why, and nothing is released automatically")
