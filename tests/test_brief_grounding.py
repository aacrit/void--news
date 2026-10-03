#!/usr/bin/env python3
"""The derived products are grounded against the stories they were written from.

    python tests/test_brief_grounding.py

The TL;DR, the Opinion and the On Air script are written after every card
check has run, and until rev 85 nothing read them against the cards. The
edition of 2026-10-01 shipped, in those three products alone: a stacked
twenty percent a listener heard as thirty, a £1,000 figure no source carries,
"two days later" for "a day earlier", "would be purged" for "no longer work
here", and a TL;DR paragraph that ended on another card's story.

Every case below is one of those defects, planted in a minimal story, and each
must be CUT by `pipeline/editorial/derived_grounding.py`. The controls are the
half that keeps a cut from silencing a true sentence: the correct version of
each sentence must survive. stdlib only, no key, no network.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from editorial import derived_grounding as dg  # noqa: E402

failures: list[str] = []


def check(ok: bool, msg: str) -> None:
    print(f"  [{'ok' if ok else 'FAIL'}] {msg}")
    if not ok:
        failures.append(msg)


HEGSETH = {
    "id": "hegseth",
    "title": "Hegseth Announces Cuts to General and Admiral Positions",
    "summary": (
        "On Wednesday, September 30, 2026, Hegseth announced additional 10 percent "
        "cuts to positions for generals and admirals, following 10 percent cuts last "
        "year, totaling a 20 percent reduction across the board. He told troops that "
        "those who “clung to the 'woke department' ... no longer work here,” "
        "adding, “The ideological clowns are out.” Retired Army General Randy "
        "Manner said Hegseth has fired 80 generals and admirals."),
    "consensus_points": [
        "Secretary of Defense Pete Hegseth announced a 20 percent reduction in general "
        "and admiral positions across the U.S. military."],
    "divergence_points": [],
}
PENSIONS = {
    "id": "pensions",
    "title": "Burnham Proposes Pension Triple Lock Changes",
    "summary": (
        "Prime Minister Andy Burnham announced plans to alter the state pension triple "
        "lock. John Swinney, First Minister of Scotland, stated that official analysis "
        "shows the changes would cost Scottish pensioners £4 billion annually by "
        "2049/50, reducing individual incomes by nearly £2,000 in real terms. The "
        "UK Government estimates the changes could save £15 billion annually."),
    "consensus_points": [], "divergence_points": [],
}
FAIRFORD = {
    "id": "fairford",
    "title": "Police Arrest Sixth Suspect Over RAF Fairford Plot",
    "summary": (
        "British counterterrorism police arrested a 27-year-old dual UK-Iranian "
        "national in London on Thursday. Five British men were arrested on Sunday near "
        "the air base and released on police bail on Monday, a day earlier than "
        "initially expected. Officers found petrol in vans near the base."),
    "consensus_points": [], "divergence_points": [],
}
GOOD = {
    "id": "good",
    "title": "Renee Good's Family Files Federal Lawsuits",
    "summary": (
        "Renee Good's family filed two federal lawsuits on Thursday against the US "
        "government. Renee Good, 37, was fatally shot on January 7 by ICE agent "
        "Jonathan Ross in Minneapolis."),
    "consensus_points": [], "divergence_points": [],
}
JUDGES = {
    "id": "judges",
    "title": "DOJ Files Misconduct Complaint Against Seven Minnesota Judges",
    "summary": (
        "The Department of Justice filed a judicial misconduct complaint against seven "
        "federal judges in the District of Minnesota. Attorney General Todd Blanche "
        "said the judges spoke to The New York Times about immigration cases."),
    "consensus_points": [], "divergence_points": [],
}
STORIES = [HEGSETH, PENSIONS, FAIRFORD, GOOD, JUDGES]


def cut_one(text: str, story: dict, needle: str, label: str, why: str) -> None:
    """The sentence carrying `needle` is cut, and for the planted reason."""
    kept, cuts = dg.ground_text(text, story, product="test")
    hit = [c for c in cuts if needle in c.sentence]
    check(bool(hit) and needle not in kept and why in hit[0].reason,
          f"cut: {label} ({[c.reason for c in cuts]})")


def keeps(text: str, story: dict, label: str) -> None:
    kept, cuts = dg.ground_text(text, story, product="test")
    check(not cuts, f"kept: {label}" + (f" (wrongly cut: {[c.reason for c in cuts]})"
                                        if cuts else ""))


def points_are_evidence_only_once_checked() -> None:
    """A brief sentence whose only anchor is a dropped point is cut.

    Before rev 86 a consensus point was read by no rule and then handed to
    this pass as evidence, so an unsourced number in a point cleared the same
    number in the TL;DR. Stage 2 now drops the point at 8d.3 (E-13 against the
    card's sources) and stores only the survivors, which is what this cluster
    dict is once the brief reads it back.
    """
    from editorial import standard as std
    sources = ("Flooding forced evacuations along the river on Sunday. Officials "
               "said 12 villages were cut off by the water.")
    story = {
        "id": "flood",
        "title": "Floods Cut Off Villages Along the River",
        "summary": ("Flooding forced evacuations along the river on Sunday. "
                    "Officials said 12 villages were cut off by the water."),
        "consensus_points": ["Officials said 4,800 residents were evacuated.",
                             "Officials said 12 villages were cut off."],
        "divergence_points": ["Separately, a dam inspection found 4,800 cracks."],
    }
    brief = "Officials said 4,800 residents were evacuated as the river rose."
    # The control: with the unchecked point, the number has an anchor.
    keeps(brief, story, "the sentence while the unchecked point stood (control)")
    kept_c, gone_c = std.check_points(story["consensus_points"], sources)
    kept_d, gone_d = std.check_points(story["divergence_points"], sources)
    check([t for t, _ in gone_c] == ["Officials said 4,800 residents were evacuated."],
          "the point with the unsourced number is dropped at 8d.3")
    check(kept_c == ["Officials said 12 villages were cut off."],
          "the sourced point is kept")
    checked = dict(story, consensus_points=kept_c, divergence_points=kept_d)
    cut_one(brief, checked, "4,800", "the brief sentence anchored only in the dropped point",
            "number")
    # E-16 needs no evidence, so cluster_text re-applies it: a point that
    # opens on another story is never evidence, even if nothing dropped it.
    text = dg.cluster_text(story)
    check("dam inspection" not in text, "cluster_text skips a point that opens on another story")
    check("12 villages were cut off." in text, "cluster_text keeps a passing point")


def main() -> int:
    print("planted defects, each cut")
    # 1. The unsourced figure (audit 1 item 2).
    cut_one("John Swinney stated the changes would cost Scottish pensioners £1,000 "
            "per year.", PENSIONS, "£1,000", "an unsourced £1,000", "number")
    # 2. A cross-story number: true of another card, not of this one.
    cut_one("Hegseth said the changes would save £15 billion annually.", HEGSETH,
            "15 billion", "a number from another story", "number")
    # 3. The stacked total (audit 1 item 1).
    cut_one("Hegseth announced a 20 percent reduction in general and admiral positions. "
            "This follows 10 percent cuts last year, totaling a 20 percent reduction.",
            HEGSETH, "totaling a 20 percent", "a total that is not the sum of its parts",
            "total")
    # 4. An altered quotation: the ellipsis became a full stop.
    cut_one("He told troops that those who “clung to the 'woke department'. No "
            "longer work here.”", HEGSETH, "clung", "a quotation with its ellipsis removed",
            "quotation")
    # 5. The reworded kicker (audit 1 item 5).
    cut_one("Secretary Hegseth told troops that those who clung to the woke department "
            "would be purged.", HEGSETH, "purged", "reported speech that ends on words never said",
            "lifts a quotation")
    # 6. An interval the source contradicts (audit 1 item 4).
    cut_one("Five British men were released on police bail just two days later.",
            FAIRFORD, "two days later", "\"two days later\" against \"a day earlier\"",
            "interval")
    # 7. A weekday the story never states.
    cut_one("Police arrested a sixth suspect on Tuesday.", FAIRFORD, "Tuesday",
            "a weekday the story does not carry", "weekday")
    # 8. A name the story never mentions.
    cut_one("Home Secretary Shabana Mahmood praised the arrests.", FAIRFORD,
            "Shabana Mahmood", "a name the story does not carry", "name")
    # 9. A hedge standing in for attribution: BLOCKING here (audit 1 item 7).
    cut_one("Manner was reportedly charged with fraud.", HEGSETH,
            "reportedly", "a hedge as attribution (E-15)", "E-15")
    # 10. Radio: a spoken figure the story does not carry.
    cut_one("He has fired ninety generals and admirals.", HEGSETH, "ninety",
            "a spoken number not in the story", "number")

    print("\ncontrols, each kept")
    keeps("John Swinney stated the changes would cost Scottish pensioners £4 billion "
          "a year by 2049/50.", PENSIONS, "the sourced figure")
    keeps("Hegseth announced additional 10 percent cuts, following 10 percent cuts last "
          "year, totaling a 20 percent reduction.", HEGSETH, "a total that adds up")
    keeps("He told troops that those who “clung to the 'woke department' ... no "
          "longer work here.”", HEGSETH, "the quotation with its ellipsis")
    keeps("Five British men were released on police bail on Monday, a day earlier than "
          "expected.", FAIRFORD, "the interval as the source gives it")
    keeps("Retired Army General Randy Manner says Hegseth has fired eighty generals and "
          "admirals.", HEGSETH, "a spoken number the story carries")
    keeps("Hegseth told troops that a twenty percent reduction is coming.", HEGSETH,
          "\"twenty percent\" read as 20")
    keeps("Mr. Hegseth announced the cuts on Wednesday.", HEGSETH,
          "an honorific and a weekday the story states")
    keeps("British counterterrorism police arrested a twenty-seven-year-old dual U-K-Iranian "
          "national in London on Thursday.", FAIRFORD, "radio's spoken forms")

    print("\none story per paragraph (audit 1 item 9)")
    tldr = ("Renee Good's family filed two federal lawsuits on Thursday against the US "
            "government. Renee Good, 37, was fatally shot on January 7 by ICE agent "
            "Jonathan Ross in Minneapolis. The Department of Justice also filed a judicial "
            "misconduct complaint against seven federal judges in the District of "
            "Minnesota.\n\n"
            "Prime Minister Andy Burnham announced plans to alter the state pension triple "
            "lock.")
    out, cuts = dg.ground_brief(tldr, STORIES)
    paras = out.split("\n\n")
    check(len(paras) == 3 and "Department of Justice" in paras[1]
          and "Department of Justice" not in paras[0],
          f"a second story in a paragraph is moved to its own paragraph ({len(paras)} paragraphs)")
    tldr2 = tldr + ("\n\nThe Department of Justice filed a judicial misconduct complaint "
                    "against seven federal judges in the District of Minnesota.")
    out2, cuts2 = dg.ground_brief(tldr2, STORIES)
    check(out2.count("Department of Justice") == 1
          and any("own paragraph" in c.reason for c in cuts2),
          "and cut when that story already has its own paragraph")
    out3, cuts3 = dg.ground_brief(
        "Hegseth announced a 20 percent reduction in general and admiral positions. "
        "John Swinney stated the changes would cost Scottish pensioners £1,000 per "
        "year.\n\nJohn Swinney, First Minister of Scotland, said the changes would cost "
        "Scottish pensioners £1,000 per year.", STORIES)
    check("1,000" not in out3, "a paragraph is grounded against its own story only")

    print("\nradio rundown")
    try:
        from briefing.radio_script_generator import (
            RundownContext, ground_rundown, parse_rundown, resolve_cluster_ids)
        script = (
            "## OPEN\nA: From Void News, this is On Air. It's Thursday, October first.\n\n"
            "## STORY 1 | Pentagon Cuts\n"
            "A: Hegseth has announced a twenty percent reduction in general and admiral "
            "positions. It follows ten percent cuts last year.\n"
            "B: Secretary Hegseth told troops that those who clung to the woke department "
            "would be purged.\n\n"
            "## CLOSE\nA: That's On Air from Void News. Every source, every story, at Void News.\n")
        r = parse_rundown(script)
        ctx = RundownContext(top20=[HEGSETH, PENSIONS, FAIRFORD, GOOD, JUDGES],
                             date_spoken="Thursday, October first")
        resolve_cluster_ids(r, ctx)
        cuts = ground_rundown(r, ctx)
        body = "\n".join(t.text for s in r.segments for t in s.turns)
        check("purged" not in body and "twenty percent reduction" in body
              and any("lifts a quotation" in c.reason for c in cuts),
              f"the kicker is cut and the sourced line kept ({[c.reason for c in cuts]})")
        check("It's Thursday, October first" in body, "the sign-on formula is not read")
    except ImportError as e:  # pragma: no cover
        check(False, f"radio generator importable ({e})")

    print("\nthe pronoun scrubber is retired (CEO Decision 8, Block 5a)")
    # It turned Ted Cruz's "a traumatic experience for all of us" into "for
    # all of them" on the live 09-09 feed. A sentence in the first person
    # outside quotation marks is now cut whole (E-03), never rewritten.
    src = (ROOT / "pipeline" / "summarizer" / "cluster_summarizer.py").read_text(
        encoding="utf-8")
    check("_convert_first_person_outside_quotes" not in src
          and "_FIRST_PERSON_SUBS" not in src,
          "no pronoun-rewriting table or converter is left in the summarizer")
    check("s = _cut_first_person_sentences(s)" in src,
          "the post-check chain cuts first-person sentences instead")
    try:
        from summarizer import cluster_summarizer as cs
        cruz = ("Senator Ted Cruz said the hearing was a traumatic experience for "
                "all of us. The committee adjourned on Tuesday.")
        out = cs._cut_first_person_sentences(cruz)
        check("all of them" not in out and "all of us" not in out
              and out == "The committee adjourned on Tuesday.",
              f"the Cruz sentence is cut, not rewritten ({out!r})")
        quoted = ("Cruz called it “a traumatic experience for all of us.” "
                  "The committee adjourned.")
        check(cs._cut_first_person_sentences(quoted) == quoted,
              "a first-person pronoun inside a quotation is left alone")
    except ImportError as e:  # the summarizer needs google-genai
        print(f"  [skip] summarizer not importable here ({e}); source checks above hold")

    print("points that failed their check are not evidence (rev 86, gap 1)")
    points_are_evidence_only_once_checked()

    if failures:
        print(f"\n{len(failures)} FAILED")
        return 1
    print("\ntest_brief_grounding: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())


def test_brief_grounding() -> None:
    assert main() == 0
