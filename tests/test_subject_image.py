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
    # A length filter of >2 discarded AI, US, EU and UN: the highest-signal
    # tokens a news headline carries. "A New Front in the AI Race" reduced to
    # {front, race} and matched its article only by coincidence on "race".
    check("an acronym survives tokenizing",
          "ai" in _subject_words("A New Front in the AI Race"))
    check("so does a country acronym", "us" in _subject_words("US Military Strikes"))
    check("but the pronoun 'us' does not",
          "us" not in _subject_words("Give it back to us"),
          "case is read before lowercasing, which is the only place it can be")

    # `[A-Za-z']+` split on the accent: "Erdogan" with its breve tokenized to
    # "erdo". It still matched because the Wikipedia title breaks the same way,
    # but a prefix matching a prefix is a coincidence, not a rule.
    check("an accented name survives whole",
          "erdo\u011fan" in _subject_words("Erdo\u011fan Attends UNGA"),
          str(sorted(_subject_words("Erdo\u011fan Attends UNGA"))))
    check("and still matches its article",
          overlaps("Erdo\u011fan Attends UNGA, Focuses on Gaza", "Recep Tayyip Erdo\u011fan"))

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


def test_not_a_diagram():
    """SUB-03  a map, flag or chart is not an illustration.

    Every technical gate passed and the result was still wrong. The Ed Sheeran
    feature (a musician apologising over a Macklemore controversy, calling
    Gaza "unjustifiable") resolved to the Gaza war territorial-control map:
    front lines, destroyed buildings, evacuation zones. Correctly licensed,
    correctly captioned, genuine word overlap on "Gaza", and a war map printed
    under a celebrity apology.

    Commons SVGs are overwhelmingly maps, flags, logos and charts. They are
    reference artefacts; a news magazine illustrates with photographs. A map
    also carries framing that printing it endorses, which is the one thing
    this section exists not to do silently.
    """
    print("\nSUB-03  diagrams are not illustrations")
    from briefing.backfill_weekly_images import _is_diagram  # noqa: E402

    for u, why in [
        ("https://thumb.wikimedia.org/x/October_2023_Gaza-Israel_conflict.svg/1280px-a.svg.png",
         "the Gaza war control map, under an Ed Sheeran feature"),
        ("https://thumb.wikimedia.org/x/Map_with_Greenland_and_the_United_States_highlighted.svg/1280px-b.svg.png",
         "a schematic world map as a full-screen cover"),
        ("https://thumb.wikimedia.org/x/North_Korea_nuclear.svg/1280px-c.svg.png",
         "a flag composite on a missile-test brief"),
    ]:
        check(f"rejects {why}", _is_diagram(u))

    for u in ("https://thumb.wikimedia.org/x/Kennedy_Center.jpg/1280px-d.jpg",
              "https://thumb.wikimedia.org/x/Imran_Khan_2019.png/1280px-e.png"):
        check(f"keeps the photograph {u.rsplit('/', 1)[-1]}", not _is_diagram(u))
    check("an absent image is not a diagram", not _is_diagram(""))


def test_no_repeats():
    """SUB-04  nothing appears twice in one issue."""
    print("\nSUB-04  no image repeats")
    from briefing.backfill_weekly_images import _claimed  # noqa: E402

    # The cover is resolved FROM the lead feature, so they collide by
    # construction. Vol. I, No. 1 came out of a backfill with the same
    # Greenland map as its full-screen cover AND its lead feature one screen
    # below.
    row = {
        "cover_image_url": "https://x/a.jpg?v=1",
        "cover_text": [{"image_url": "https://x/a.jpg?v=2"},
                       {"image_url": "https://x/b.jpg"}],
        "departments": [], "recap_stories": [],
    }
    used = _claimed(row)
    check("the cover's image is claimed up front", "https://x/a.jpg" in used)
    # ONLY the cover. Seeding this with every slot's url made each slot a
    # repeat of ITSELF, and the first item examined dropped its own perfectly
    # good distinct photograph.
    check("no other slot is pre-claimed", used == {"https://x/a.jpg"}, sorted(used))

    # A pre-existing duplicate is removed; a distinct image beside it is not.
    import briefing.backfill_weekly_images as B
    real = B.find_cover_image_for_cluster
    B.find_cover_image_for_cluster = lambda *a, **k: None   # nothing better
    try:
        r = {"cover_image_url": "https://x/a.jpg?v=1", "cover_image_caption": "S",
             "cover_text": [
                 {"headline": "One", "image_url": "https://x/a.jpg?v=2",
                  "image_caption": "S", "image_attribution": "A"},
                 {"headline": "Two", "image_url": "https://x/b.jpg",
                  "image_caption": "O", "image_attribution": "B"}],
             "departments": [], "recap_stories": []}
        B.illustrate(r)
        check("a slot repeating the cover is cleared",
              r["cover_text"][0].get("image_url") is None)
        check("a distinct image beside it survives",
              bool(r["cover_text"][1].get("image_url")))
    finally:
        B.find_cover_image_for_cluster = real


def test_skip_means_not_written():
    """SUB-05  a slot reported as skipped must not carry the image.

    The dedup check sat AFTER the assignment, so a duplicate was attached,
    then detected, then reported as "skipped" while staying on the page. The
    issue shipped the same Greenland protest photograph as its full-screen
    cover AND its lead feature, under a log line saying it had not.

    That is the worst shape a bug can take: the log is not merely wrong, it
    reports the opposite of what happened, so reading it is worse than not
    looking. Asserted against a fake lookup, so it needs no network.
    """
    print("\nSUB-05  a skipped duplicate is not written")
    import briefing.backfill_weekly_images as B

    real = B.find_cover_image_for_cluster
    B.find_cover_image_for_cluster = lambda *a, **k: {
        "url": "https://x/same.jpg?v=9", "attribution": "A", "caption": "Same Subject"}
    try:
        row = {
            "cover_image_url": "https://x/same.jpg?v=1",
            "cover_image_caption": "Same Subject",
            "cover_text": [{"headline": "One"}, {"headline": "Two"}],
            "departments": [], "recap_stories": [],
        }
        lines = B.illustrate(row)
        urls = [c.get("image_url") for c in row["cover_text"]]
        check("both features report skipped",
              sum("skipped" in l for l in lines) == 2, "; ".join(lines))
        check("and NEITHER carries the image", urls == [None, None], str(urls))
        check("no caption is left behind either",
              all(not c.get("image_caption") for c in row["cover_text"]))

        # A query string is not a different image: the cover's ?v= differs
        # from the lookup's by construction.
        check("the cover kept its own image", row["cover_image_url"].endswith("v=1"))
    finally:
        B.find_cover_image_for_cluster = real


if __name__ == "__main__":
    test_guard()
    test_licence_and_floor()
    test_not_a_diagram()
    test_no_repeats()
    test_skip_means_not_written()
    print("\n" + ("All subject-image gates passed." if ok else "FAILURES above."))
    sys.exit(0 if ok else 1)
