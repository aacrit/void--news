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
# Do not ask any one publisher for more than this. Measured 2026-09-23: the corpus
# holds 13,981 eligible URLs across the 132 outlets that have 30 or more, so a cap of
# 150 was binding on only 32 of them and lifting it entirely costs about two minutes.
# The median eligible outlet has 84 and is nowhere near it.
LIMIT_PER_OUTLET = 400
WORKERS = 8                    # across DIFFERENT hosts only
DELAY = 0.5                    # seconds between fetches to the same host
TIMEOUT = 15
MIN_BODY_WORDS = 150           # the scorer's own full-confidence threshold

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# EXTRACTION IS THE WHOLE BALL GAME, and the first version of this file got it
# wrong. It stripped tags with a regex and called the result "good enough to COUNT
# phrases in". It was not. The 10.5M words that produced were mostly page chrome,
# and the derivation over them ranked `pic twitter com`, `sign`, `if you`,
# `instagram` and `page` at the top and rediscovered ZERO of the 318 hand-written
# political phrases, exactly as the truncated-lead corpus had.
#
# The pipeline already owns a real extractor. `web_scraper.scrape_article` does
# JSON-LD first, then article-body selectors, then Playwright, with paywall
# detection, image-credit stripping and title-echo detection on top. Writing a
# worse one beside it was the mistake; this now calls it.


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
        #: Articles actually COUNTED per outlet. `phrase_counts.band` takes a
        #: document share against this, and will not take one against a number
        #: inferred from the counts: that inference is what let a 4,000-row
        #: ceiling look like a filter for a day.
        self.articles: collections.Counter = collections.Counter()
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
            from fetchers.web_scraper import scrape_article
            got = scrape_article(url)
        except Exception as exc:
            self.stats[f"error_{type(exc).__name__}"] += 1
            return
        text = got.get("full_text") or ""
        words = got.get("word_count") or len(text.split())
        if not text:
            self.stats["no_text"] += 1
            return
        if words < MIN_BODY_WORDS:
            self.stats["too_short"] += 1
            return
        # THE ONLY THING THAT LEAVES THIS FUNCTION IS A COUNT. `text` is local and
        # goes out of scope here; nothing writes it, returns it or logs it.
        counted = set(pc.phrases_of(text))
        with self.lock:
            self.tally[sid].update(counted)
            self.articles[sid] += 1
            self.stats["ok"] += 1
            self.stats["words"] += words
        del text


def band_report(h: "Harvester") -> None:
    """Where the hand-written political phrases fall against the band, measured on
    the untruncated tally, before a single row is written.

    THIS IS THE ONLY MOMENT THE QUESTION IS CHEAP. After `persist` the cut phrases are
    gone and nobody can tell whether the thresholds were right; that is how a 4,000-row
    ceiling sat over this corpus for a day while two derivations reported zero and were
    read as evidence about the method. The band's two numbers were set from a sample of
    what a TRUNCATED table happened to contain, so they are an estimate until a full
    tally checks them, and this checks them on every run.

    A floor that cuts far more than the ~5% measured on that sample means the
    untruncated tail behaves differently and the thresholds need re-reading BEFORE the
    derivation that follows is believed.
    """
    try:
        from analyzers.political_lean import LEFT_KEYWORDS as L, RIGHT_KEYWORDS as R
        from analyzers.lexicon_derive import reachable_known
    except Exception as exc:
        print(f"\nband report unavailable: {exc}")
        return
    known, _ = reachable_known({p.lower() for p in L} | {p.lower() for p in R})

    inside = below = above = 0
    seen: set[str] = set()
    banded_outlets = 0
    for sid, counter in h.tally.items():
        n = h.articles.get(sid, 0)
        if n < pc.BAND_MIN_ARTICLES:
            continue                      # no band applied, nothing to report
        banded_outlets += 1
        ceiling = pc.MAX_DOC_SHARE * n
        for phrase in known:
            c = counter.get(phrase, 0)
            if not c:
                continue
            seen.add(phrase)
            if c < pc.MIN_ARTICLES_PER_PHRASE:
                below += 1
            elif c > ceiling:
                above += 1
            else:
                inside += 1
    total = inside + below + above
    print(f"\nband: floor {pc.MIN_ARTICLES_PER_PHRASE} article(s), ceiling "
          f"{pc.MAX_DOC_SHARE:.0%} of an outlet's own, applied to {banded_outlets} of "
          f"{len(h.tally)} outlets")
    if not banded_outlets:
        # Not the same thing as seeing no political language, and saying so would be a
        # diagnostic reporting a corpus failure that did not happen. A --sample run
        # gives every outlet one or two articles, so none clears BAND_MIN_ARTICLES and
        # the loop above never looked at a single phrase.
        print(f"  no outlet reached {pc.BAND_MIN_ARTICLES} bodies, so no band was "
              f"applied and nothing was measured against it. Nothing is being said "
              f"here about the corpus.")
        return
    if not total:
        print("  the harvest saw none of the hand-written political phrases at all, "
              "in outlets the band DID apply to. That is a corpus problem, not a "
              "threshold problem.")
        return
    print(f"  hand-written political phrases the harvest SAW: {len(seen)} of "
          f"{len(known)} reachable, in {total:,} outlet-phrase pairs")
    print(f"    inside the band (kept):    {inside:>6,}  ({inside/total:.0%})")
    print(f"    below the floor (cut):     {below:>6,}  ({below/total:.0%})"
          f"   <- ~5% expected; much more means re-read the floor")
    print(f"    above the ceiling (cut):   {above:>6,}  ({above/total:.0%})")


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

    # Before the early return, so `--sample N` exercises this path too. A diagnostic
    # that only runs on the 19-minute path is one nobody checks before spending 19
    # minutes.
    band_report(h)

    if not apply:
        print("\n--sample run: counts NOT persisted. Pass --apply to write them.")
        return 0

    conn = sqlite3.connect(db_path)
    written = pc.persist(conn, h.tally, now=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                         articles=dict(h.articles))
    banded = sum(1 for sid in h.tally if h.articles[sid] >= pc.BAND_MIN_ARTICLES)
    print(f"\nband: kept {pc.MIN_ARTICLES_PER_PHRASE}+ articles and at most "
          f"{pc.MAX_DOC_SHARE:.0%} of an outlet's own, applied to {banded} of "
          f"{len(h.tally)} outlets ({len(h.tally) - banded} had under "
          f"{pc.BAND_MIN_ARTICLES} bodies, so nothing was cut from them)")
    print(f"wrote {written:,} count rows to outlet_phrase_counts in {db_path}")
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
