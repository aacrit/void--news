#!/usr/bin/env python3
"""Served-audio gate for On Air: does production actually serve the show?

    python scripts/verify_audio.py [https://news.voidvision.org/]

Checks, against the LIVE site (stdlib only, like verify_production.py):
  A-01  brief.json has audio_url and it resolves (HTTP 200, audio/mpeg, > 1 MB)
  A-02  audio_chapters is a non-empty list with monotonic startTime, first at 0
  A-03  the chapters sidecar next to the MP3 exists and matches brief.json
  A-04  duration is a real show (5-14 minutes) and news_start/opinion_start sit inside it
  A-05  the rundown (audio_script) carries the Void sign-on, never a borrowed line

Exit 1 on any failure; prints one line per check. Run by verify-production.yml.
A legacy (unchaptered) episode fails A-02/A-03 on purpose: after the radio
format ships, an unchaptered show means the fallback path ran, and that
deserves a red gate rather than silence.
"""

from __future__ import annotations

import json
import sys
import urllib.request

BORROWED = ("up first", "here's what we're covering", "first the headlines",
            "and that's the headlines", "these are our main stories", "stay with us", "and finally")


def fetch(url: str, binary: bool = False, head: bool = False):
    req = urllib.request.Request(url, method="HEAD" if head else "GET",
                                 headers={"User-Agent": "void-verify-audio/1.0", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=60) as r:
        if head:
            return r.status, dict(r.headers), b""
        data = r.read()
        return r.status, dict(r.headers), data if binary else data.decode("utf-8", "replace")


def main(base: str) -> int:
    base = base.rstrip("/")
    ok = True

    def report(code: str, passed: bool, detail: str) -> None:
        nonlocal ok
        ok = ok and passed
        print(f"  [{'ok' if passed else 'FAIL'}] {code} {detail}")

    try:
        _, _, body = fetch(f"{base}/data/brief.json")
        brief = json.loads(body)
    except Exception as e:
        print(f"  [FAIL] A-01 brief.json unreachable: {e}")
        return 1

    audio_url = brief.get("audio_url") or ""
    clean = audio_url.split("?")[0]
    full = clean if clean.startswith("http") else f"{base}{clean}"
    try:
        status, headers, _ = fetch(full, head=True)
        ctype = headers.get("Content-Type", headers.get("content-type", ""))
        length = int(headers.get("Content-Length", headers.get("content-length", "0")) or 0)
        report("A-01", status == 200 and "audio" in ctype and (length == 0 or length > 1_000_000),
               f"{full} -> {status} {ctype} {length} bytes")
    except Exception as e:
        report("A-01", False, f"{full}: {e}")

    chapters = brief.get("audio_chapters")
    if isinstance(chapters, str):
        try:
            chapters = json.loads(chapters)
        except ValueError:
            chapters = None
    good = isinstance(chapters, list) and len(chapters) >= 5
    if good:
        starts = [c.get("startTime") for c in chapters]
        good = starts[0] == 0 and all(isinstance(s, (int, float)) for s in starts) and \
            all(starts[i] < starts[i + 1] for i in range(len(starts) - 1))
    report("A-02", good, f"{len(chapters) if isinstance(chapters, list) else 'no'} chapters"
           + (f", kinds {[c.get('kind') for c in chapters]}" if good else ""))

    side_ok = False
    if clean.endswith(".mp3"):
        side_url = (clean[:-4] + ".chapters.json")
        side_url = side_url if side_url.startswith("http") else f"{base}{side_url}"
        try:
            _, _, sbody = fetch(side_url)
            side = json.loads(sbody)
            side_ok = (side.get("version") == "1.2.0" and isinstance(chapters, list)
                       and [c["startTime"] for c in side["chapters"]] == [c["startTime"] for c in chapters])
            report("A-03", side_ok, f"{side_url}: {len(side.get('chapters', []))} chapters, matches brief.json={side_ok}")
        except Exception as e:
            report("A-03", False, f"{side_url}: {e}")
    else:
        report("A-03", False, "audio_url is not an mp3")

    dur = brief.get("audio_duration_seconds") or 0
    ns, os_ = brief.get("news_start_seconds"), brief.get("opinion_start_seconds")
    report("A-04", 300 <= float(dur) <= 840 and ns is not None and 0 < float(ns) < float(dur)
           and (os_ is None or float(ns) < float(os_) < float(dur)),
           f"duration {dur}s, news at {ns}s, editorial at {os_}s")

    script = (brief.get("audio_script") or "").lower()
    report("A-05", "from void news, this is on air" in script and not any(b in script for b in BORROWED),
           "sign-on present, no borrowed lines" if script else "no audio_script")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "https://news.voidvision.org/"))
