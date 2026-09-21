#!/usr/bin/env python3
"""Gates for "The Argument", the void --weekly audio edition.

Pure: no DB, no LLM key, no network, no audio rendering.

The fixture is not hand-written prose. It is BUILT from the real published
Issue #26 — the same columns the live page renders — so W-01, the rule that
makes the show's content unfabricatable, is exercised against the actual data
rather than against a sentence invented to satisfy it. Every assertion after
the clean run plants exactly one defect, which is how History's validators
caught H-04 shipping weak: the rule matched "king" inside "striking", and only
a planted case found it.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from briefing.weekly_script import (  # noqa: E402
    OVERLAP_FLOOR, TARGET_MINUTES, estimated_minutes, overlap,
    parse_script, validate_script, _bench_columns,
)

ISSUES = ROOT / "frontend" / "build-data" / "weekly-issues.json"
_failures = []


def check(name, ok, detail=""):
    print(f"  [{'ok' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        _failures.append(name)


def _issue():
    rows = json.loads(ISSUES.read_text(encoding="utf-8"))
    return max((r for r in rows if isinstance(r, dict)),
               key=lambda r: r.get("issue_number") or 0)


def _sentences(text, n, budget):
    """Real sentences off a published column, to a word budget."""
    out, words = [], 0
    for s in re.split(r"(?<=[.!?])\s+", (text or "").strip()):
        s = s.strip()
        if len(s.split()) < 6:
            continue
        out.append(s)
        words += len(s.split())
        if len(out) >= n or words >= budget:
            break
    return out


def _filler(voice, words):
    """Editor copy at a known length. The Editor invents nothing a validator
    checks, so this can be generated; the BENCH never can."""
    body = ("The week ran long and the record is public. "
            "Void scored every article it could reach and published the count. ")
    text, n = "", 0
    while n < words:
        text += body
        n = len(text.split())
    return [f"{voice}: {text.strip()}"]


def build_clean(issue):
    """A rundown that passes every validator, built from the real issue."""
    cols = _bench_columns(issue.get("opinions") or [])
    stats = ((issue.get("bias_report_data") or {}).get("stats") or {})
    # The bench SELECTS: these lines exist verbatim in the published columns.
    left = _sentences(cols["L"], 8, 230)
    right = _sentences(cols["R"], 8, 230)
    # Within W-03's 1.35x airtime band, which is the point of trimming both.
    lw, rw = sum(len(l.split()) for l in left), sum(len(r.split()) for r in right)
    while rw / max(lw, 1) > 1.20 and len(right) > 2:
        rw -= len(right.pop().split())
    while lw / max(rw, 1) > 1.20 and len(left) > 2:
        lw -= len(left.pop().split())

    # The turn engages BOTH columns, so it is built from both.
    turn = _sentences(cols["L"], 3, 60) + _sentences(cols["R"], 3, 60)

    lines = ["## OPEN"] + _filler("E", 90)
    lines += ["## CONTENTS", "E: Inside this week.", "E: The Arctic, contested.",
              "E: Two columnists, one story.", "E: The week, measured."]
    lines += ["## COVER"] + _filler("E", 700)
    lines += ["## DATELINE", "E: Tuesday. Thirteen sources."]
    lines += ["## COVER"] + _filler("E", 250)
    lines += ["## TOPIC", "E: The two columns below argue about the same agreement."]
    lines += ["## LEFT"] + [f"L: {s}" for s in left]
    lines += ["## RIGHT"] + [f"R: {s}" for s in right]
    lines += ["## REST"]
    lines += ["## TURN"] + [f"E: {s}" for s in turn]
    lines += ["## SECOND"] + _filler("E", 420)
    lines += ["## DEPARTMENT | Technology"] + _filler("E", 200)
    lines += ["## NUMBERS",
              f"E: Void scored more than three thousand articles this week.",
              f"E: Coverage sat at {stats.get('avg_lean', 51.2)} on a hundred point scale.",
              f"E: The spread was {stats.get('lean_std', 14.9)}."]
    lines += ["## EDITORIAL"] + _filler("E", 620)
    lines += ["## CLOSE", "E: Who decides what a territory is worth?"]
    lines += ["## SAY", "Nuuk = NOOK"]
    return "\n".join(lines)


def test_clean():
    print("\nWA-01  a rundown built from the real issue passes every validator")
    issue = _issue()
    script = parse_script(build_clean(issue))
    findings = validate_script(script, issue)
    fails = [f for f in findings if f.level == "fail"]
    for f in findings:
        print(f"         {f.id} {f.level:4} [{f.segment}] {f.detail[:100]}")
    check("no failures on a clean rundown", not fails,
          "; ".join(f"{f.id}:{f.segment}" for f in fails))
    minutes, wpm = estimated_minutes(script)
    lo, hi = TARGET_MINUTES
    check("inside the 18-22 minute band", lo <= minutes <= hi,
          f"{minutes:.1f} min, {script.words} words")
    return issue


def _fails(issue, text, rule):
    findings = validate_script(parse_script(text), issue)
    return [f for f in findings if f.level == "fail" and f.id == rule]


def test_planted(issue):
    print("\nWA-02  one planted defect per validator")
    clean = build_clean(issue)

    # W-01 — THE MOAT. A bench line the column does not contain.
    bad = clean.replace(
        "## LEFT\n",
        "## LEFT\nL: The agreement hands the entire northern shelf to a foreign "
        "navy and every serious analyst has said so repeatedly this week.\n", 1)
    check("W-01 catches a bench line that is not in the column",
          _fails(issue, bad, "W-01"))
    check("W-01 leaves a genuinely selected line alone",
          not _fails(issue, clean, "W-01"))

    # A real column sentence with three words trimmed must still pass: cutting
    # for the ear is the whole allowance.
    cols = _bench_columns(issue.get("opinions") or [])
    src = _sentences(cols["L"], 1, 40)[0]
    trimmed = " ".join(src.split()[:-3])
    check("W-01 allows a line trimmed for the ear",
          overlap(trimmed, cols["L"]) >= OVERLAP_FLOOR,
          f"{overlap(trimmed, cols['L']):.0%}")

    # W-02 — a bench voice outside the argument.
    check("W-02 catches the bench speaking outside its column",
          _fails(issue, clean.replace("## CLOSE\nE:", "## CLOSE\nL:", 1), "W-02"))
    check("W-02 catches the Editor inside a bench column",
          _fails(issue, clean.replace("## RIGHT\nR:", "## RIGHT\nE:", 1), "W-02"))

    # W-03 — one side given materially more airtime than the other.
    lop = clean.replace("## RIGHT\n", "## RIGHT\n" + "\n".join(
        f"R: {s}" for s in _sentences(cols["R"], 12, 400)) + "\n", 1)
    check("W-03 catches a lopsided bench", _fails(issue, lop, "W-03"))

    # W-04 — a turn that reckons with one side only.
    one = re.sub(r"## TURN\n(?:E: .*\n)+",
                 "## TURN\n" + "\n".join(f"E: {s}" for s in _sentences(cols["L"], 6, 140))
                 + "\n", clean, count=1)
    check("W-04 catches a turn that engages one column",
          _fails(issue, one, "W-04"))
    check("W-04 catches a turn too short to reckon with two positions",
          _fails(issue, re.sub(r"## TURN\n(?:E: .*\n)+", "## TURN\nE: Both sides miss it.\n",
                               clean, count=1), "W-04"))

    # W-05 — the programme's shape.
    check("W-05 catches a missing movement",
          _fails(issue, clean.replace("## NUMBERS", "## NOTES", 1), "W-05"))

    # W-06 — the dateline beat.
    check("W-06 catches a missing dateline",
          _fails(issue, clean.replace("## DATELINE\nE: Tuesday. Thirteen sources.\n", "", 1),
                 "W-06"))

    # W-07 — length.
    short = "\n".join(l for l in clean.splitlines()
                      if not l.startswith("E: The week ran long"))
    check("W-07 catches a programme far under the band",
          _fails(issue, short, "W-07"))

    # W-08 — borrowed radio furniture.
    check("W-08 catches a borrowed catchphrase",
          _fails(issue, clean.replace("## OPEN\n", "## OPEN\nE: Up first, the Arctic.\n", 1),
                 "W-08"))

    # W-09 — a figure read aloud that the issue does not carry.
    check("W-09 catches an invented figure",
          _fails(issue, clean.replace("E: The spread was",
                                      "E: Void scored 8412 articles and the spread was", 1),
                 "W-09"))


def test_columns_match_the_page(issue):
    """The programme and the page must agree on WHICH two essays are the argument.

    `_bench_columns` mirrors `findPair` in Perspectives.tsx. If they diverged,
    the show would stage a debate the reader cannot find on the page it is
    supposedly reading from.
    """
    print("\nWA-03  the bench is the page's pair")
    cols = _bench_columns(issue.get("opinions") or [])
    check("a pair was found", set(cols) == {"L", "R"}, str(sorted(cols)))
    paired = [o for o in issue["opinions"] if o.get("paired")]
    check("the pair is the flagged pair", len(paired) == 2, str(len(paired)))
    check("left is left", (paired[0].get("lean") or "").startswith("left")
          or cols["L"] == (paired[0].get("text") or ""))
    check("both columns carry text", all(len(v.split()) > 50 for v in cols.values()))

    # The same source used by the frontend reader, so a refactor that drops
    # `pair_id` on one side is caught here rather than on Sunday.
    tsx = (ROOT / "frontend" / "app" / "weekly" / "components" / "Perspectives.tsx").read_text()
    for token in ("pair_id", "paired", "lean"):
        check(f"findPair still keys on {token}", token in tsx)


def test_committed_scripts():
    """Every AUTHORED rundown, against the issue it was written from.

    History's scripts are committed and validated the same way, for the same
    reason: flash is capped at 20 requests a DAY shared with the daily
    pipeline, so generating a 3,000 word script is a cost that buys worse
    prose than a person writes. The trade is that a committed script can drift
    from its issue silently, which is exactly what this catches.

    W-01 is the one that matters here. A bench line must exist in that
    columnist's PUBLISHED column, so if an issue is ever repaired or
    regenerated and a column changes, the script that quotes it stops being
    true and stops rendering.
    """
    print("\nWA-04  committed rundowns")
    scripts = sorted((ROOT / "data" / "weekly" / "scripts").glob("*.txt"))
    if not scripts:
        print("  (none committed yet)")
        return

    rows = json.loads(ISSUES.read_text(encoding="utf-8"))
    by_week = {r["week_start"]: r for r in rows if isinstance(r, dict) and r.get("week_start")}

    for path in scripts:
        week = path.stem
        issue = by_week.get(week)
        check(f"{week}: its issue is published", issue is not None)
        if not issue:
            continue
        script = parse_script(path.read_text(encoding="utf-8"))
        findings = validate_script(script, issue)
        fails = [f for f in findings if f.level == "fail"]
        for f in fails:
            print(f"         {f.id} [{f.segment}] {f.detail[:100]}")
        check(f"{week}: renders clean", not fails,
              "; ".join(f"{f.id}" for f in fails))
        minutes, wpm = estimated_minutes(script)
        lo, hi = TARGET_MINUTES
        check(f"{week}: inside the band", lo <= minutes <= hi,
              f"{minutes:.1f} min, {script.words} words")


def main():
    print("void --weekly audio gates (The Argument)")
    issue = test_clean()
    test_planted(issue)
    test_columns_match_the_page(issue)
    test_committed_scripts()
    print()
    if not test_wa05_word_budget_lands_inside_the_band():
        _failures.append("WA-05")
    print()
    if not test_wa06_the_prompt_names_the_banned_phrases():
        _failures.append("WA-06")
    print()
    if _failures:
        print(f"FAILED ({len(_failures)}): " + ", ".join(_failures))
        return 1
    print("All weekly-audio script gates passed.")
    return 0





# ---------------------------------------------------------------------------
# WA-05: the word budget the generator is given must land inside W-07's band.
#
# The scheduled run of 2026-09-20 fell back to the legacy two-voice read
# because W-07 rejected a 3,463-word rundown at 22.6 minutes. The rundown was
# not disobedient: its prompt asked for "about 2934 to 3586 words", computed as
# the minute band times a flat 163 wpm. `estimated_minutes` adds MUSIC_MINUTES
# on top, 1.4 minutes of theme, beds and outro that nobody speaks over, so the
# prompt's ceiling was roughly 228 words past what the band allows. A rundown
# could obey the prompt exactly and still fail the validator.
#
# The two edges take opposite rates, which a synthetic script at each edge
# caught in review: runtime is words over rate, so the ceiling must assume the
# slowest voice and the floor the fastest. One blended rate put the floor below
# the band whenever the Editor carries most of the programme, which he always
# does.
# ---------------------------------------------------------------------------
def _synthetic(total_words: int, editor_share: float) -> str:
    editor = int(total_words * editor_share)
    half = (total_words - editor) // 2

    def block(speaker: str, words: int) -> str:
        return "\n".join(f"{speaker}: " + " word" * 40
                         for _ in range(max(1, words // 40)))

    return ("## OPEN\n" + block("E", editor)
            + "\n## LEFT\n" + block("L", half)
            + "\n## RIGHT\n" + block("R", half)
            + "\n## CLOSE\nE: and what now?\n")


def test_wa05_word_budget_lands_inside_the_band() -> bool:
    from briefing.weekly_script import (
        MUSIC_MINUTES, TARGET_MINUTES, VOICE_WPM, estimated_minutes,
        parse_script, word_budget,
    )
    voices = {"editor": "bm_lewis", "left": "am_michael", "right": "af_heart"}
    lo_band, hi_band = TARGET_MINUTES
    lo_w, hi_w = word_budget(voices)
    ok = True

    print("WA-05  the generator's word budget lands inside W-07's band")

    # Both edges, across every plausible split of airtime.
    for share, label in ((0.85, "editor-heavy"), (0.75, "typical"),
                         (0.55, "bench-heavy")):
        for words, edge in ((lo_w, "floor"), (hi_w, "ceiling")):
            script = parse_script(_synthetic(words, share), "world")
            minutes, _ = estimated_minutes(script, voices)
            inside = lo_band <= minutes <= hi_band
            print(f"  [{'ok' if inside else 'FAIL'}] {label} {edge}: "
                  f"{script.words} words is {minutes:.2f} min")
            ok = ok and inside

    # The budget must account for music, or it is the old bug again.
    speech_only_ceiling = int(hi_band * VOICE_WPM["am_michael"])
    if hi_w >= speech_only_ceiling:
        print(f"  [FAIL] ceiling {hi_w} ignores MUSIC_MINUTES "
              f"({speech_only_ceiling} would)")
        ok = False
    else:
        print(f"  [ok] the ceiling accounts for {MUSIC_MINUTES} min of music — "
              f"{hi_w} not {speech_only_ceiling}")

    # And the exact rundown that caused the fallback must now be out of budget.
    if lo_w <= 3463 <= hi_w:
        print("  [FAIL] 3,463 words, the rundown that failed W-07, is still "
              "inside the budget the prompt hands out")
        ok = False
    else:
        print("  [ok] 3,463 words, the rundown that sent 2026-09-20 to the "
              "legacy read, is outside the budget")
    return ok


def test_wa06_the_prompt_names_the_banned_phrases() -> bool:
    """W-08 rejected 'absolutely'. The prompt had never mentioned it."""
    from briefing import weekly_rundown
    from briefing.weekly_script import BORROWED
    ok = True
    print("WA-06  the rundown prompt names the phrases W-08 rejects")
    rendered = weekly_rundown.SYSTEM.format(
        LO=18, HI=22, MUSIC=1.4, WORDS_LO=1, WORDS_HI=2,
        BORROWED=", ".join(f'"{b}"' for b in BORROWED))
    for phrase in ("absolutely", "great question", "let's dive"):
        if phrase not in rendered:
            print(f"  [FAIL] the prompt never tells the model to avoid {phrase!r}")
            ok = False
    if ok:
        print(f"  [ok] all {len(BORROWED)} borrowed phrases are named in the prompt")
    return ok


if __name__ == "__main__":
    sys.exit(main())
