#!/usr/bin/env python3
"""The image license gate, and every image already published.

WHY THIS FILE EXISTS. `_normalize_wiki_license` mapped a Commons
LicenseShortName onto one of four permissive keys, and anything it did not
recognise fell through as the raw string for the caller's allowlist to reject.
That fail-closed default was the design, and it was sound. Two strings were
getting through it in the ACCEPTING direction anyway:

    "CC BY-NC 4.0"  ->  "cc-by"  ->  accepted
    "CC BY-ND 4.0"  ->  "cc-by"  ->  accepted

because `"cc by" in "cc by-nc 4.0"` is true. NonCommercial forbids precisely
what Void does with the image. The public-domain branch was worse: `"pd" in
ls`, two letters, returning the most permissive key we have.

Nothing published had slipped through (all 163 History media objects are
PD/CC0/CC BY/CC BY-SA, all attributed, all Wikimedia-hosted), which is luck
plus the fact that Commons skews public-domain for historical subjects. A
weekly news magazine searches different ground.

Group 2 is the part that matters over time: it re-runs the gate against what
is actually on the site, so an image added later under a license this rule
would reject fails the build rather than a takedown notice.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

try:
    from media.image_search import (  # noqa: E402
        _normalize_wiki_license, _extract_wiki_text,
    )
except ImportError as e:
    # `image_search` imports `requests` at module scope and the light CI job
    # installs only nltk. A missing third-party wheel SKIPS; a missing module
    # of our own would raise a different name and fail loudly, which is the
    # distinction that matters.
    if "requests" not in str(e):
        raise
    print(f"SKIP tests/test_image_license.py — {e}")
    sys.exit(0)

ALLOWED = ("cc0", "public-domain", "cc-by", "cc-by-sa")
ok = True


def check(label, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print(f"  [{'ok' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))


def accepted(s):
    return _normalize_wiki_license(s) in ALLOWED


def test_gate():
    """IMG-01  free licenses pass, non-free ones do not."""
    print("\nIMG-01  the license gate")
    for s in ("Public domain", "PD-US", "PD-old-70", "CC0",
              "CC BY 2.0", "CC BY-SA 3.0", "CC BY-SA 4.0"):
        check(f"accepts {s!r}", accepted(s))

    # The two that were being accepted. NonCommercial forbids what Void does;
    # NoDerivatives is at best arguable once the image is re-rendered at
    # WIKI_RENDER_WIDTH.
    for s in ("CC BY-NC 4.0", "CC BY-NC-SA 3.0", "CC BY-ND 4.0", "CC BY-NC-ND 4.0"):
        check(f"REJECTS {s!r}", not accepted(s), "was accepted as cc-by")

    for s in ("Fair use", "Non-free media", "All rights reserved",
              "GFDL", "Attribution", "GPLv3"):
        check(f"rejects {s!r}", not accepted(s))

    # `"pd" in ls` matched any string carrying those two letters and returned
    # the most permissive key in the table.
    check("a stray 'pd' is not public domain", not accepted("Updated license"))
    check("an empty license is not free", not accepted(""))


def test_attribution_shape():
    """IMG-03  a credit has to be usable in a one-line caption slot.

    Commons `Artist` is free-form HTML, and on a composite file it is several
    stacked credits. Stripping tags alone left the newlines, so the credit for
    the North Korean missile-tests illustration came back as four lines. A CC
    BY / CC BY-SA image must carry a usable credit; a multi-line blob in a
    caption slot is not one.
    """
    print("\nIMG-03  attribution shape")
    messy = ('<a href="x">Flag of North Korea</a>\n<a>User:Zscout370</a>\n\n'
             '  Radiation warning symbol  ')
    got = _extract_wiki_text(messy)
    check("newlines are collapsed", "\n" not in got, repr(got[:60]))
    check("no double spaces", "  " not in got)
    check("the credit survives", "Zscout370" in got)
    check("tags are gone", "<" not in got and ">" not in got)
    check("a clean credit is unchanged",
          _extract_wiki_text("<span>Carol M. Highsmith</span>") == "Carol M. Highsmith")
    check("empty stays empty", _extract_wiki_text("") == "")
    check("adjacent tags do not fuse words",
          _extract_wiki_text("<b>Ansel</b><i>Adams</i>") == "Ansel Adams",
          "stripping to '' would have produced 'AnselAdams'")


def test_published():
    """IMG-02  every image already on the site passes the gate it shipped under."""
    print("\nIMG-02  published images")
    p = ROOT / "frontend/public/data/history.json"
    if not p.exists():
        check("history.json present", False, "not found")
        return
    rows = json.loads(p.read_text())
    rows = rows if isinstance(rows, list) else rows.get("events") or []

    media = []

    def walk(o):
        if isinstance(o, dict):
            if o.get("license") or o.get("attribution"):
                media.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(rows)
    check("the archive carries media", len(media) > 100, f"{len(media)} objects")

    bad = [m for m in media if not accepted(m.get("license") or "")]
    check("every published license is free", not bad,
          "; ".join(f"{m.get('license')}" for m in bad[:4]) or f"{len(media)} checked")

    # cc-by and cc-by-sa REQUIRE attribution. An unattributed one is a licence
    # breach even though the licence itself is free.
    noattr = [m for m in media if not (m.get("attribution") or "").strip()]
    check("every published image is attributed", not noattr, f"{len(noattr)} missing")

    # Rev 60 retired the re-hosting cacher on copyright grounds and rev 69
    # settled on hotlinked Commons originals. Anything served from elsewhere
    # is a scraped publisher image and does not belong here.
    off = [m for m in media
           if m.get("url") and "wikimedia.org" not in m["url"]
           and "wikipedia.org" not in m["url"]]
    check("nothing is hosted off Wikimedia", not off,
          "; ".join((m.get("url") or "")[:48] for m in off[:3]) or "all Commons")


if __name__ == "__main__":
    test_gate()
    test_attribution_shape()
    test_published()
    print("\n" + ("All image license gates passed." if ok else "FAILURES above."))
    sys.exit(0 if ok else 1)
