#!/usr/bin/env python3
"""Subject resolution: the guard, the licence, the floor. No network.

Vol. I, No. 1 shipped with ZERO photographs. The cause was not licensing and
not Commons coverage. It was the query: the pipeline searched Commons with the
full editorial headline, and Commons indexes subjects.

    "Greenland's Arctic Calculus"                        ->  0 Commons results
    "Greenland"                                          ->  5
    "Trump Closes Kennedy Center, Cites Safety Concerns" ->  0
    "John F. Kennedy Center for the Performing Arts"     ->  5

Wikipedia's search resolves a headline to an article well. What it does not do
is say when it has failed: "Greenland's Arctic Calculus" resolves confidently
to a 2026 Icelandic EU referendum, whose lead image is a map of Iceland. An
Iceland map on a Greenland story is worse than no photograph, because it looks
authoritative.

So resolution is guarded by word overlap against the headline we published,
the same way the weekly audio's bench lines are (W-01) and History's document
reads are (H-01). The machine may SELECT a subject the headline names. It may
not invent one.

These are the real cases, measured live and recorded here, so the rules stay
testable without depending on Wikimedia (which rate-limits sandboxes hard
enough that a live test proves nothing either way).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

try:
    from media.image_search import (  # noqa: E402
        _subject_words, _normalize_wiki_license, SUBJECT_MIN_WIDTH, WIKI_MIN_WIDTH,
    )
except ImportError as e:
    if "requests" not in str(e):
        raise
    print(f"SKIP tests/test_subject_image.py — {e}")
    sys.exit(0)

ok = True


def check(label, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print(f"  [{'ok' if cond else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))


def overlaps(headline, article):
    """The guard, exactly as resolve_subject applies it."""
    return bool(_subject_words(headline) & _subject_words(article))


def test_guard():
    """SUB-01  a resolved article must share a content word with the headline."""
    print("\nSUB-01  the overlap guard")

    # Live resolutions that are RIGHT.
    for head, art in [
        ("Trump Closes Kennedy Center, Cites Safety Concerns", "Kennedy Center"),
        ("Erdogan Attends UNGA, Focuses on Gaza", "Gaza peace summit"),
        ("A New Front in the AI Race", "Artificial intelligence arms race"),
        ("Arctic Sovereignty, Contested Control", "Territorial claims in the Arctic"),
        ("North Korea Conducts Missile Tests", "North Korea and weapons of mass destruction"),
    ]:
        check(f"keeps {art!r}", overlaps(head, art))

    # The live resolution that is WRONG, and the reason this guard exists.
    check("REFUSES the Iceland referendum for a Greenland story",
          not overlaps("Greenland's Arctic Calculus",
                       "2026 Icelandic European Union membership negotiations referendum"),
          "would have put a map of Iceland on the cover")
    check("REFUSES a polar research centre for the same story",
          not overlaps("Greenland's Arctic Calculus",
                       "Byrd Polar and Climate Research Center"))

    # Possessives. "Greenland's" must reduce to "Greenland" or the one word
    # carrying the whole subject is discarded. Same defect as rev 57's brief
    # matcher and rev 65's shared tokenizer; cheap to reintroduce.
    check("a possessive matches its root", overlaps("Greenland's Arctic Calculus", "Greenland"))
    check("Jehovah's Witnesses matches its article",
          overlaps("Jehovah's Witnesses Update Blood Transfusion Stance",
                   "Criticism of Jehovah's Witnesses"))

    # Stopwords cannot carry a match on their own.
    check("a shared stopword is not a match",
          not overlaps("The New Front on the Border", "The New Deal"),
          "'the'/'new' are stopwords; nothing real is shared")
    check("an empty headline resolves to nothing", not overlaps("", "Kennedy Center"))


def test_licence_and_floor():
    """SUB-02  a resolved subject still has to clear licence and resolution."""
    print("\nSUB-02  licence and resolution gates")
    ALLOWED = ("cc0", "public-domain", "cc-by", "cc-by-sa")

    # Live: the Greenland alt-title path resolved to "Canadian sovereignty",
    # whose lead image is Canada_(orthographic_projection).svg under GFDL.
    # Resolution succeeding is not permission to publish.
    check("GFDL is refused even on a correctly resolved subject",
          _normalize_wiki_license("GFDL") not in ALLOWED)
    check("a public-domain lead image is allowed",
          _normalize_wiki_license("Public domain") in ALLOWED)

    # Live: "Criticism of Jehovah's Witnesses" resolved correctly and its lead
    # image is 208px wide.
    check("208px is below the subject floor", 208 < SUBJECT_MIN_WIDTH)
    # The subject path feeds weekly plates and thumbnails, not History's
    # full-bleed Lightbox, so it must NOT inherit that floor: 800 was throwing
    # away correctly resolved subjects over pixel count.
    check("the subject floor is looser than the Lightbox floor",
          SUBJECT_MIN_WIDTH < WIKI_MIN_WIDTH,
          f"subject {SUBJECT_MIN_WIDTH} vs search {WIKI_MIN_WIDTH}")
    check("but still above any weekly render slot", SUBJECT_MIN_WIDTH >= 400)


if __name__ == "__main__":
    test_guard()
    test_licence_and_floor()
    print("\n" + ("All subject-image gates passed." if ok else "FAILURES above."))
    sys.exit(0 if ok else 1)
