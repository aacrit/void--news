#!/usr/bin/env python3
"""A refusal on robots.txt is not permission.

`web_scraper._check_robots_txt` used to return True for EVERY non-200 response
and for every network error. So a 403 on robots.txt, a 503, and a 429 all read
as consent, on the one file whose entire job is to say no. The error ran one
way: it never refused a site that had allowed us, it only scraped sites whose
answer we had failed to obtain.

RFC 9309 section 2.3.1 splits the statuses, and the split is not "200 or not":

    404, 410   allow. "Unavailable" means no restrictions exist. This is the
               common case for a small publisher and the reason the permissive
               version looked reasonable.
    401, 403   deny. The RFC calls these "unauthorized" and says access is
               completely disallowed.
    429, 5xx   deny for this run. A site rate-limiting us or under load is
               where restraint costs least.

The status mapping is a pure function so it can be asserted with no network,
which is the point: the old behaviour was untestable except by fetching real
sites, so it was never tested.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipeline"))

from fetchers import web_scraper as ws  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"PASS  {name}")
    else:
        failures.append(f"{name}: {detail}" if detail else name)
        print(f"FAIL  {name} {detail}")


ALLOW = [200, 204, 299, 404, 410]
# 3xx is unreachable in practice (safe_get follows redirects) and denies
# anyway, which is the safe direction for a status we never expect to see.
DENY = [302, 401, 403, 418, 429, 451, 500, 502, 503, 504, None]

for status in ALLOW:
    check(f"robots.txt {status} allows crawling",
          ws.robots_verdict_for_status(status) == ws._ALLOW_ALL,
          ws.robots_verdict_for_status(status))
for status in DENY:
    check(f"robots.txt {status} does NOT allow crawling",
          ws.robots_verdict_for_status(status) == ws._DENY_ALL,
          ws.robots_verdict_for_status(status))

# The two that were wrong before, named so a regression is legible.
check("a 403 on robots.txt is a refusal, not consent (was: consent)",
      ws.robots_verdict_for_status(403) == ws._DENY_ALL)
check("a 503 on robots.txt is not consent (was: consent)",
      ws.robots_verdict_for_status(503) == ws._DENY_ALL)
check("a network error is not consent (was: consent)",
      ws.robots_verdict_for_status(None) == ws._DENY_ALL)

# The verdict must actually reach the caller, not just the mapping. The cache
# is the seam: seeding it is exactly what a fetch does.
URL = "https://example.test/story/1"
DOMAIN = "https://example.test"
for verdict, expect in ((ws._ALLOW_ALL, True), (ws._DENY_ALL, False)):
    ws._robots_cache.clear()
    ws._robots_cache[DOMAIN] = verdict
    check(f"a cached {verdict} verdict reaches the caller",
          ws._check_robots_txt(URL) is expect)

# A real parsed robots.txt still decides per path.
import urllib.robotparser  # noqa: E402

rp = urllib.robotparser.RobotFileParser()
rp.parse(["User-agent: *", "Disallow: /premium/"])
ws._robots_cache.clear()
ws._robots_cache[DOMAIN] = rp
check("a parsed robots.txt still allows an open path",
      ws._check_robots_txt("https://example.test/story/1") is True)
check("a parsed robots.txt still refuses a disallowed path",
      ws._check_robots_txt("https://example.test/premium/1") is False)
ws._robots_cache.clear()

# --- the retry, because the split denies on transient failures --------------
# Measured on 70 roster domains (2026-09-22): 60 served robots.txt, 5 returned
# 403, 1 returned 429, 4 failed at the transport. A refusal is a decision and
# must not be retried; a timeout is noise and must be, or a whole domain's
# coverage is paid for one dropped packet.


class _Resp:
    def __init__(self, status: int, text: str = ""):
        self.status_code = status
        self.text = text


def with_fake_get(responses):
    """Run one _check_robots_txt against a scripted sequence of responses."""
    calls = {"n": 0}

    def fake(url, timeout=None, headers=None):
        i = calls["n"]
        calls["n"] += 1
        item = responses[min(i, len(responses) - 1)]
        if isinstance(item, Exception):
            raise item
        return item

    real_get, real_sleep = ws.safe_get, ws.time.sleep
    ws.safe_get = fake
    ws.time.sleep = lambda *_: None  # no real pause in a test
    try:
        ws._robots_cache.clear()
        allowed = ws._check_robots_txt(URL)
    finally:
        ws.safe_get, ws.time.sleep = real_get, real_sleep
        ws._robots_cache.clear()
    return allowed, calls["n"]


allowed, n = with_fake_get([_Resp(403)])
check("a 403 is not retried", n == 1 and allowed is False, f"{n} call(s), allowed={allowed}")

allowed, n = with_fake_get([_Resp(404)])
check("a 404 is not retried", n == 1 and allowed is True, f"{n} call(s), allowed={allowed}")

allowed, n = with_fake_get([TimeoutError("slow"), _Resp(200, "User-agent: *\nAllow: /")])
check("a timeout is retried, and a second-attempt 200 is honoured",
      n == 2 and allowed is True, f"{n} call(s), allowed={allowed}")

allowed, n = with_fake_get([_Resp(503), _Resp(200, "User-agent: *\nDisallow: /")])
check("a 503 is retried, and the retry's robots.txt still decides",
      n == 2 and allowed is False, f"{n} call(s), allowed={allowed}")

allowed, n = with_fake_get([TimeoutError("slow"), TimeoutError("slow again")])
check("two transport failures deny, and do not retry forever",
      n == 2 and allowed is False, f"{n} call(s), allowed={allowed}")

if failures:
    print(f"\nFAIL  {len(failures)} robots-compliance check(s)")
    sys.exit(1)
print("\nPASS  a refusal on robots.txt is read as a refusal")
