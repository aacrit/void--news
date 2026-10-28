#!/usr/bin/env python3
"""The Python and TypeScript summary hygiene must agree.

utils/summary_hygiene.py and app/lib/summaryHygiene.ts are hand-kept in
lock-step and there was nothing checking that they still are. They decide the
same question on two sides of the same pipeline: the Python decides whether a
stored summary is a raw excerpt (the display window, the print archive, the
summary floor), the TypeScript decides whether to render it. A divergence
means a card the pipeline believes is fine renders blank, which is the exact
defect the floor pass was written to stop.

The fixture strings here are asserted IDENTICALLY by frontend/test/labels.test.mjs.
Adding a case to one file means adding it to the other.

The second half is Python only: the rule-based summary the floor writes when
Gemini is unavailable (every card from 2026-10-21, a 402 on the key). Run #412
served "i Phone" and "Mac Book Pro", "CAIRO:" and "SPECIAL REPORT |" openers,
"BREAKING NEWS:" and "LIVE NOW:" heads, and two cards whose summary was their
own headline again. Each is a fixture below.

Run: python tests/test_summary_hygiene_parity.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from utils.summary_hygiene import is_raw_excerpt  # noqa: E402

RAW_EXCERPT = [
    "Sign up for our newsletter to get the day's top stories.",
    "Why it matters: the vote splits the caucus three ways.",
    "The minister resigned on Tuesday. Photo: Getty Images",
    "Troops entered the city at dawn - reuters.com",
    "The council met on Tuesday (Ahmed Gomaa/Anadolu)",
    "The governmentSaid the investigationContinues into the collapse.",
]

CLEAN = [
    "The Senate voted 61 to 38 on Tuesday to confirm the nominee. "
    "Two Republicans crossed over.",
    "Pfizer said the mRNA candidate cut hospitalisations by 42 percent "
    "in the mRNA arm of the trial.",
    "Apple shipped 4.2 million iPhone units in the quarter, up from "
    "3.8 million a year earlier.",
]


def rule_based_cases() -> list[tuple[str, bool]]:
    from utils.text_sanitizer import normalize_headline, sanitize_summary
    from clustering.story_cluster import _generate_cluster_summary

    head = "Israelis are voting on whether to oust Netanyahu in first election"
    body = ("Israelis voted on Tuesday in a parliamentary election. Polls opened "
            "at 7 a.m. and close at 10 p.m. The opposition is led by a former "
            "prime minister. Turnout at midday was 32 percent, the elections "
            "committee said, slightly higher than at the last vote. Results are "
            "expected overnight.")
    echo = _generate_cluster_summary(
        [{"title": head, "summary": head, "full_text": body}], head)
    product = sanitize_summary("Apple unveiled a new MacBook Pro and iMac, and "
                               "said the iPhone line would follow in the spring.")
    return [
        ("a brand's own capital is not a glued word",
         "MacBook Pro and iMac" in product and "iPhone" in product),
        ("a glued word is still split",
         "lost Submitted" in sanitize_summary("The bill was lostSubmitted to the "
                                              "committee on Tuesday for review.")),
        ("a colon dateline is stripped",
         sanitize_summary("KARACHI/CAIRO: Officials from three nations met in "
                          "Tehran on Monday to discuss the war.").startswith("Officials")),
        ("a kicker before a pipe is stripped",
         sanitize_summary("SPECIAL REPORT | Uganda says it has contained the "
                          "outbreak, but cases in Kenya remain.").startswith("Uganda")),
        ("BREAKING NEWS: leaves the head",
         normalize_headline("BREAKING NEWS: Xi sends condolences over the death "
                            "of Fukuda").startswith("Xi")),
        ("LIVE NOW: leaves the head",
         normalize_headline("LIVE NOW: Senate candidate holds a press "
                            "conference in Detroit").startswith("Senate")),
        ("a blurb that is its own headline gives way to the article's opening",
         echo.startswith("Israelis voted") and echo.endswith(".")),
    ]


def main() -> int:
    rb_failed = 0
    for name, ok in rule_based_cases():
        print(f"{'PASS' if ok else 'FAIL'}  rule-based summary: {name}")
        rb_failed += 0 if ok else 1
    failed = 0
    for s in RAW_EXCERPT:
        if not is_raw_excerpt(s):
            failed += 1
            print(f"FAIL  python kept what the TypeScript blanks: {s[:60]!r}")
    for s in CLEAN:
        if is_raw_excerpt(s):
            failed += 1
            print(f"FAIL  python blanks what the TypeScript keeps: {s[:60]!r}")
    total = len(RAW_EXCERPT) + len(CLEAN)
    print(f"{total - failed}/{total} hygiene fixtures agree with the TypeScript")
    return 1 if failed or rb_failed else 0


if __name__ == "__main__":
    sys.exit(main())
