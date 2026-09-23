#!/usr/bin/env python3
"""Re-fetch article bodies we already have URLs for, keep only the phrase counts.

WHY THIS EXISTS, and why it replaces a three-week wait. `lexicon_derive.py` needs
article bodies. The stored corpus has none: `full_text` is truncated to 300 characters
after analysis (`main.py` step 10, the top control in `docs/IP-COMPLIANCE.md`), so a
derivation over it ranks CMS boilerplate above politics and rediscovers zero of the 318
hand-written phrases (`docs/audits/LEAN-SIGNAL-2026-09-22.md`).

The plan was to accumulate counts from live runs and wait two to three weeks.
Unnecessary: the corpus stores **29,381 real publisher URLs**, 37.5% of it. The bodies
are still out there. We do not need new articles, we need the ones we already indexed.

WHAT IS KEPT. Phrase counts per outlet, nothing else. The fetched body is counted and
dropped inside one function and never written anywhere. That is the same argument the
grounding index and `phrase_counts.py` already won: a count is derived data, cannot be
read as journalism, and answers the only question the derivation asks.

POLITENESS AND PERMISSION, because this fetches at volume where the daily pipeline
fetches a handful:
  - `web_scraper._check_robots_txt` decides every fetch, so the RFC 9309 split applies
    (a 403 on robots.txt is a refusal, not consent). A refused host is skipped, not
    worked around.
  - One worker per host at a time, `DELAY` between fetches to the same host.
  - `--limit-per-outlet` caps how much any one publisher is asked for.
  - Google News redirect URLs are skipped outright: they no longer resolve, which is
    the defect that created this whole situation.

    python3 scripts/roster/harvest_phrase_counts.py <state.db> --dry-run
    python3 scripts/roster/harvest_phrase_counts.py <state.db> --apply
"""
from __future__ import annotations

import collections
import pathlib
import re
import sqlite3
import sys
import threading
import time
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT))

import requests  # noqa: E402

from analyzers import phrase_counts as pc  # noqa: E402

MARKETS = ("US", "GB", "AU", "CA", "IN", "IE", "ZA", "PK")
PLACED = ("far-left", "left", "center-left", "center",
          "center-right", "right", "far-right")

MIN_ARTICLES_PER_OUTLET = 30   # below this the outlet cannot reach a usable n anyway
LIMIT_PER_OUTLET = 150         # do not ask any one publisher for more than this
WORKERS = 8                    # across DIFFERENT hosts only
DELAY = 0.5                    # seconds between fetches to the same host
TIMEOUT = 15
MIN_BODY_WORDS = 150           # the scorer's own full-confidence threshold

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

_TAG = re.compile(r"<(script|style|nav|header|footer|aside)[^>]*>.*?</\1>",
                  re.S | re.I)
_STRIP = re.compile(r"<[^>]+>")


def body_text(html: str) -> str:
    """Rough visible text. Good enough to COUNT phrases in, which is all it is for.

    Deliberately not a parser: nothing downstream reads this string except the phrase
    counter, and it is discarded in the same call. A precise extraction would be worth
    it if the text were kept, and it is not.
    """
    cleaned = _TAG.sub(" ", html or "")
    return re.sub(r"\s+", " ", _STRIP.sub(" ", cleaned)).strip()


def targets(db_path: str) -> dict[str, list[tuple[str, str]]]:
    """{source_id: [(article_url, slug)]} for placed English-market outlets."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    q = f"""select s.id sid, s.slug, s.name, a.url
            from articles a join sources s on s.id = a.source_id
            where a.url is not null
              and a.url not like '%news.google.com%'
              and s.country in ({','.join('?' * len(MARKETS))})
              and s.political_lean_baseline in ({','.join('?' * len(PLACED))})"""
    by: dict[str, list] = collections.defaultdict(list)
    names: dict[str, str] = {}
    for r in conn.execute(q, MARKETS + PLACED):
        by[r["sid"]].append(r["url"])
        names[r["sid"]] = r["name"]
    out = {sid: urls[:LIMIT_PER_OUTLET]
           for sid, urls in by.items() if len(urls) >= MIN_ARTICLES_PER_OUTLET}
    print(f"outlets in scope: {len(out)} "
          f"(placed, {'/'.join(MARKETS)}, {MIN_ARTICLES_PER_OUTLET}+ real URLs)")
    print(f"articles to fetch: {sum(len(v) for v in out.values()):,} "
          f"(capped at {LIMIT_PER_OUTLET} per outlet)")
    return out, names


def host_of(url: str) -> str:
    return urllib.parse.urlparse(url).netloc.lower()


class Harvester:
    """Counts phrases from fetched bodies. Keeps no text, by construction."""

    def __init__(self):
        self.tally: dict[str, collections.Counter] = collections.defaultdict(
            collections.Counter)
        self.stats = collections.Counter()
        self.lock = threading.Lock()
        self.host_last: dict[str, float] = {}
        self.host_lock = threading.Lock()
        self.session = requests.Session()
        self.session.headers["User-Agent"] = UA

    def _wait_for_host(self, host: str) -> None:
        """One request at a time per host, DELAY apart. Workers fan out across
        DIFFERENT hosts, so a publisher never sees us in parallel."""
        while True:
            with self.host_lock:
                now = time.monotonic()
                last = self.host_last.get(host, 0.0)
                if now - last >= DELAY:
                    self.host_last[host] = now
                    return
                wait = DELAY - (now - last)
            time.sleep(wait)

    def fetch_one(self, sid: str, url: str) -> None:
        from fetchers.web_scraper import _check_robots_txt
        try:
            if not _check_robots_txt(url):
                self.stats["robots_denied"] += 1
                return
        except Exception:
            self.stats["robots_error"] += 1
            return
        self._wait_for_host(host_of(url))
        try:
            resp = self.session.get(url, timeout=TIMEOUT, allow_redirects=True)
        except Exception as exc:
            self.stats[f"error_{type(exc).__name__}"] += 1
            return
        if resp.status_code != 200:
            self.stats[f"http_{resp.status_code}"] += 1
            return
        text = body_text(resp.text)
        words = len(text.split())
        if words < MIN_BODY_WORDS:
            self.stats["too_short"] += 1
            return
        # THE ONLY THING THAT LEAVES THIS FUNCTION IS A COUNT. `text` is local and
        # goes out of scope here; nothing writes it, returns it or logs it.
        counted = set(pc.phrases_of(text))
        with self.lock:
            self.tally[sid].update(counted)
            self.stats["ok"] += 1
            self.stats["words"] += words
        del text


def run(db_path: str, apply: bool, sample: int = 0) -> int:
    scope, names = targets(db_path)
    if not scope:
        print("nothing in scope")
        return 0

    # A DRY RUN FETCHES NOTHING. It prints the scope and stops.
    #
    # The first version fetched all 13,981 articles and only THEN checked the flag,
    # which is precisely the defect fixed in apply_feeds.py hours earlier: the flag
    # was read at the point of the dangerous write rather than at every side effect,
    # and a "dry run" that hits fourteen thousand publisher URLs is a side effect
    # whatever it does with the result. Use --sample N to exercise the fetch path.
    if not apply and not sample:
        print("\n--dry-run: nothing fetched, nothing written. "
              "Use --sample N to test the fetch path, --apply to harvest.")
        return 0

    # Interleave by outlet so the worker pool is always spread across different
    # hosts. A naive flat list would have eight workers hammering one publisher.
    queues = [list(v) for v in scope.values()]
    sids = list(scope.keys())
    work: list[tuple[str, str]] = []
    for i in range(max(len(q) for q in queues)):
        for sid, q in zip(sids, queues):
            if i < len(q):
                work.append((sid, q[i]))

    if sample:
        work = work[:sample]
        print(f"--sample {sample}: fetching {len(work)} article(s) only")

    h = Harvester()
    started = time.time()
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = [pool.submit(h.fetch_one, sid, url) for sid, url in work]
        done = 0
        for _ in cf.as_completed(futures):
            done += 1
            if done % 500 == 0:
                el = time.time() - started
                print(f"  {done:,}/{len(work):,} in {el/60:.1f} min, "
                      f"{h.stats['ok']:,} bodies counted", flush=True)

    el = time.time() - started
    print(f"\nfetched {len(work):,} in {el/60:.1f} min")
    print(f"  bodies counted: {h.stats['ok']:,}")
    print(f"  words counted:  {h.stats['words']:,}")
    print(f"  outlets with counts: {len(h.tally)}")
    for k, v in sorted(h.stats.items(), key=lambda kv: -kv[1]):
        if k not in ("ok", "words"):
            print(f"  {k}: {v:,}")

    if not apply:
        print("\n--sample run: counts NOT persisted. Pass --apply to write them.")
        return 0

    conn = sqlite3.connect(db_path)
    written = pc.persist(conn, h.tally, now=time.strftime("%Y-%m-%dT%H:%M:%SZ"))
    print(f"\nwrote {written:,} count rows to outlet_phrase_counts in {db_path}")
    widest = conn.execute("select max(words) from outlet_phrase_counts").fetchone()[0]
    print(f"widest stored phrase: {widest} words (bound is {pc.MAX_PHRASE_WORDS})")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    n = 0
    if "--sample" in sys.argv:
        n = int(sys.argv[sys.argv.index("--sample") + 1])
    raise SystemExit(run(sys.argv[1], "--apply" in sys.argv, n))
