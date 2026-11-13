#!/usr/bin/env python3
"""Gates for "The Argument", the Weekly's audio edition (rev 2: three voices).

Pure: no DB, no LLM key, no network, no audio rendering.

The fixture is not hand-written prose. It is BUILT from the newest real
published issue that carries a left/right pair, so W-01, the rule that makes
the show's content unfabricatable, is exercised against the actual columns, and
the correspondents' passages, the week in brief and the editorial are the
issue's own sentences, so W-13 and the grounding pass are exercised against
real text. Every assertion after the clean run plants exactly one defect.
"""

import json
import re
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from briefing.weekly_script import (  # noqa: E402
    CLOSE_PREFIX, CLOSE_TAG, CONTENTS_OPEN, CORRESPONDENT_VOICES, FLOOR_MINUTES, HOST_VOICE,
    OPINION_OPEN, OVERLAP_FLOOR, SPEED, TARGET_MINUTES, WEEK_OPEN, WPM,
    cast_for_week, estimated_minutes, ground_script, overlap, parse_script, sign_on_line,
    target_minutes, validate_script, _bench_columns,
)

ISSUES = ROOT / "frontend" / "build-data" / "weekly-issues.json"
_failures = []


def check(name, ok, detail=""):
    print(f"  [{'ok' if ok else 'FAIL'}] {name}" + (f": {detail}" if detail else ""))
    if not ok:
        _failures.append(name)


def _issue():
    """The newest published issue that carries a left/right pair and an editorial."""
    rows = [r for r in json.loads(ISSUES.read_text(encoding="utf-8")) if isinstance(r, dict)]
    paired = [r for r in rows
              if {"L", "R"} <= set(_bench_columns(r.get("opinions") or []))
              and (r.get("opinion_text") or "").strip() and (r.get("cover_text") or [])]
    if not paired:
        raise SystemExit("FAIL  no published issue carries a left/right pair to build WA-01 from")
    return max(paired, key=lambda r: r.get("issue_number") or 0)


def _sentences(text, n, budget, min_words=6):
    """Real sentences off a published text, to a word budget."""
    out, words = [], 0
    for s in re.split(r"(?<=[.!?])\s+", (text or "").strip()):
        s = s.strip()
        if len(s.split()) < min_words:
            continue
        out.append(s)
        words += len(s.split())
        if len(out) >= n or words >= budget:
            break
    return out


def _filler(voice, words):
    """Host copy at a known length that names no number and no name, so the
    validators that read the host see only what is planted."""
    body = ("The week ran long and the record is public. "
            "Void scored every article it could reach and published the count. ")
    text, n = "", 0
    while n < words:
        text += body
        n = len(text.split())
    return [f"{voice}: {text.strip()}"]


def _passages(text, voices, n, lo=22, hi=60):
    """Correspondent passages cut from a published feature: whole sentences,
    grouped to about `hi` words, the leader first and the other voice last."""
    sents = _sentences(text, 40, 10 ** 6)
    out, cur = [], []
    for s in sents:
        if cur and len(" ".join(cur + [s]).split()) > hi:
            out.append(" ".join(cur))
            cur = []
        cur.append(s)
    if cur:
        out.append(" ".join(cur))
    out = [p for p in out if len(p.split()) >= lo][:n]
    return [f"{voices[1] if (i == len(out) - 1 or i % 3 == 2) else voices[0]}: {p}" for i, p in enumerate(out)]


DATELINE = "H: This week, in the north."


def _printed_name(issue):
    from briefing.weekly_parse import unsourced_terms
    from briefing.weekly_script import issue_text
    text = issue_text(issue)
    for m in re.finditer(r"\b([A-Z][a-z]{2,} [A-Z][a-z]{2,})\b", text):
        line = f"{m.group(1)} spoke for the kingdom."
        if not unsourced_terms(line, text, set()):
            return m.group(1)
    return None


def build_clean(issue, filler_words=0):
    """A rundown that passes every validator, built from the real issue."""
    cols = _bench_columns(issue.get("opinions") or [])
    stats = ((issue.get("bias_report_data") or {}).get("stats") or {})
    covers = [c for c in (issue.get("cover_text") or []) if isinstance(c, dict)]
    briefs = [r for r in (issue.get("recap_stories") or []) if isinstance(r, dict)]
    left = _sentences(cols["L"], 8, 170)
    right = _sentences(cols["R"], 8, 170)
    lw, rw = sum(len(l.split()) for l in left), sum(len(r.split()) for r in right)
    while rw / max(lw, 1) > 1.15 and len(right) > 2:
        rw -= len(right.pop().split())
    while lw / max(rw, 1) > 1.15 and len(left) > 2:
        lw -= len(left.pop().split())
    turn = _sentences(cols["L"], 3, 60) + _sentences(cols["R"], 3, 60)

    lines = ["## COLD", "H: The week opened on a count and closed on another."]
    lines += ["## OPEN", f"H: {sign_on_line(issue)}", "H: The week in one image."] + _filler("H", 40 + filler_words)
    lines += ["## CONTENTS", f"H: {CONTENTS_OPEN}", "H: The cover, and the borders it crossed.",
              "H: Two columnists, one story.", "H: The second feature, and the week in brief."]
    cover = _passages(covers[0].get("text"), ("A", "B"), 4)
    lines += ["## COVER | The cover"] + cover[:2]
    lines += ["## DATELINE", DATELINE]
    lines += ["## COVER"] + cover[2:]
    lines += ["## TOPIC", "H: The two columns below argue about the same story. The left column first."]
    lines += ["## LEFT"] + [f"A: {s}" for s in left]
    lines += ["## RIGHT"] + [f"B: {s}" for s in right]
    lines += ["## REST"]
    lines += ["## TURN"] + [f"H: {s}" for s in turn]
    second_text = covers[1].get("text") if len(covers) > 1 else covers[0].get("text")
    lines += ["## SECOND | The second feature"] + _passages(second_text, ("B", "A"), 3)
    if briefs:
        lines += ["## WEEK", f"H: {WEEK_OPEN}"]
        for i, b in enumerate(briefs[:6]):
            s = _sentences(b.get("summary"), 2, 40)
            if s:
                lines.append(f"{'AB'[i % 2]}: {' '.join(s)}")
    if stats:
        lines += ["## NUMBERS",
                  f"H: Coverage sat at {stats.get('avg_lean', 50.0)} on a hundred point scale.",
                  f"H: The spread was {stats.get('lean_std', 0.0)}."]
    paras = [p.strip() for p in re.split(r"\n\s*\n", (issue.get("opinion_text") or "").strip()) if p.strip()]
    lines += ["## EDITORIAL | The editorial", f"H: {OPINION_OPEN} {issue.get('opinion_headline') or 'The week.'}"]
    lines += [f"H: {p}" for p in paras]
    lines += ["## CLOSE", "H: Who decides what a week was about?", f"H: {CLOSE_PREFIX} {CLOSE_TAG}"]
    lines += ["## SAY", "Nuuk = NOOK"]
    return "\n".join(lines)


def clean_for_band(issue, band=None):
    """`build_clean`, with the host's open sized so the whole lands mid-band."""
    lo, hi = band or target_minutes(issue)
    first = build_clean(issue)
    minutes, _ = estimated_minutes(parse_script(first), cast_for_week(issue.get("week_start")))
    words = max(0, int(((lo + hi) / 2 - minutes) * WPM))
    return build_clean(issue, filler_words=words)


def _fails(issue, text, rule):
    findings = validate_script(parse_script(text), issue)
    return [f for f in findings if f.level == "fail" and f.id == rule]


def _detail(issue, text, rule):
    return str([f.detail for f in validate_script(parse_script(text), issue) if f.id == rule])


def test_clean():
    print("\nWA-01  a rundown built from the real issue passes every validator")
    issue = _issue()
    script = parse_script(clean_for_band(issue))
    findings = validate_script(script, issue)
    fails = [f for f in findings if f.level == "fail"]
    for f in findings:
        print(f"         {f.id} {f.level:4} [{f.segment}] {f.detail[:100]}")
    check("no failures on a clean rundown", not fails, "; ".join(f"{f.id}:{f.segment}" for f in fails))
    minutes, wpm = estimated_minutes(script, cast_for_week(issue.get("week_start")))
    lo, hi = target_minutes(issue)
    check(f"inside this issue's {lo:.0f}-{hi:.0f} minute band", lo <= minutes <= hi,
          f"{minutes:.1f} min, {script.words} words")
    return issue


def test_planted(issue):
    print("\nWA-02  one planted defect per validator")
    clean = clean_for_band(issue)
    cols = _bench_columns(issue.get("opinions") or [])

    # W-01: THE MOAT. A column line the column does not contain.
    bad = clean.replace("## LEFT\n", "## LEFT\nA: The agreement hands the entire northern shelf to a foreign "
                                     "navy and every serious analyst has said so repeatedly this week.\n", 1)
    check("W-01 catches a column line that is not in the column", _fails(issue, bad, "W-01"))
    check("W-01 leaves a genuinely selected line alone", not _fails(issue, clean, "W-01"))
    src = _sentences(cols["L"], 1, 40)[0]
    trimmed = " ".join(src.split()[:-3])
    check("W-01 allows a line trimmed for the ear", overlap(trimmed, cols["L"]) >= OVERLAP_FLOOR,
          f"{overlap(trimmed, cols['L']):.0%}")

    # W-02: the firewall.
    check("W-02 catches a correspondent speaking for Void (the close)",
          _fails(issue, clean.replace("## CLOSE\nH:", "## CLOSE\nA:", 1), "W-02"))
    check("W-02 catches the host inside a column",
          _fails(issue, clean.replace("## RIGHT\nB:", "## RIGHT\nH:", 1), "W-02"))
    check("W-02 catches the wrong correspondent inside a column",
          _fails(issue, clean.replace("## RIGHT\nB:", "## RIGHT\nA:", 1), "W-02"))
    check("W-02 catches the host reading a feature",
          _fails(issue, clean.replace("## COVER | The cover\nA:", "## COVER | The cover\nH:", 1), "W-02"))
    check("W-02 catches a correspondent reading the editorial",
          _fails(issue, re.sub(r"(## EDITORIAL \| The editorial\nH: [^\n]*\n)H:", r"\1A:", clean, count=1), "W-02"))

    # W-03: one side given materially more airtime than the other.
    lop = clean.replace("## RIGHT\n", "## RIGHT\n" + "\n".join(f"B: {s}" for s in _sentences(cols["R"], 12, 400)) + "\n", 1)
    check("W-03 catches a lopsided bench", _fails(issue, lop, "W-03"))

    # W-04: a turn that reckons with one side only, or with neither.
    one = re.sub(r"## TURN\n(?:H: .*\n)+", "## TURN\n" + "\n".join(f"H: {s}" for s in _sentences(cols["L"], 6, 140)) + "\n",
                 clean, count=1)
    check("W-04 catches a turn that engages one column", _fails(issue, one, "W-04"))
    check("W-04 catches a turn too short to reckon with two positions",
          _fails(issue, re.sub(r"## TURN\n(?:H: .*\n)+", "## TURN\nH: Both sides miss it.\n", clean, count=1), "W-04"))

    # W-05: the programme's shape.
    check("W-05 catches a missing movement", _fails(issue, clean.replace("## TOPIC", "## NOTES", 1), "W-05"))
    swapped = clean.replace("## CONTENTS", "## XX1").replace("## OPEN", "## CONTENTS").replace("## XX1", "## OPEN")
    check("W-05 catches movements out of order", _fails(issue, swapped, "W-05"))
    with_stats = dict(issue, bias_report_data={"stats": {"avg_lean": 51.2, "lean_std": 12.1}})
    no_numbers = re.sub(r"## NUMBERS\n(?:H: .*\n)+", "", clean)
    check("W-05 catches a bias report the programme does not read",
          [f for f in validate_script(parse_script(no_numbers), with_stats) if f.id == "W-05" and f.segment == "NUMBERS"])

    # W-06: the dateline beat, inside the cover.
    check("W-06 catches a missing dateline", _fails(issue, clean.replace(f"## DATELINE\n{DATELINE}\n", "", 1), "W-06"))
    moved = clean.replace(f"## DATELINE\n{DATELINE}\n", "", 1).replace("## TOPIC\n", f"## DATELINE\n{DATELINE}\n## TOPIC\n", 1)
    check("W-06 catches a dateline outside the cover", _fails(issue, moved, "W-06"))
    check("W-06 catches a dateline that is a paragraph",
          _fails(issue, clean.replace(DATELINE, "H: This week in the north the record ran long and every count was public and Void published it."), "W-06"))

    # W-07: length.
    short = "\n".join(l for l in clean.splitlines() if not l.startswith("H: The week ran long"))
    short = re.sub(r"## WEEK\n(?:[HAB]: .*\n)+", "", short)
    check("W-07 catches a programme far under the band", _fails(issue, short, "W-07"))
    full = {"opinion_text": "word " * 6000}
    thin = {"opinion_text": "word " * 300}
    check("a full issue keeps the 18-22 band", target_minutes(full) == TARGET_MINUTES, str(target_minutes(full)))
    check("a thin issue floats down to the floor, never under it",
          target_minutes(thin) == (FLOOR_MINUTES, FLOOR_MINUTES + 4.0), str(target_minutes(thin)))
    check("the floor is a Sunday magazine, not a bulletin", 12.0 <= FLOOR_MINUTES <= 14.0, str(FLOOR_MINUTES))
    check("an issue with no sourced words gets the full band", target_minutes({}) == TARGET_MINUTES)
    if target_minutes(issue)[1] < TARGET_MINUTES[0] + 1:
        check("W-07 catches a full-length rundown on a thin issue (padding)",
              _fails(issue, clean_for_band(issue, TARGET_MINUTES), "W-07"))

    # W-08: borrowed radio furniture.
    check("W-08 catches a borrowed catchphrase",
          _fails(issue, clean.replace("## CONTENTS\n", "## CONTENTS\nH: Up first, the Arctic.\n", 1), "W-08"))

    # W-09: a Week in Bias the issue cannot back.
    if "## NUMBERS" in clean:
        check("W-09 catches an invented figure",
              _fails(issue, clean.replace("H: The spread was", "H: Void scored 8412 articles and the spread was", 1), "W-09"))
    no_stats = dict(issue, bias_report_data={})
    with_numbers = clean.replace("## EDITORIAL", "## NUMBERS\nH: Coverage sat at 51.2 on a hundred point scale.\n## EDITORIAL", 1) \
        if "## NUMBERS" not in clean else clean
    check("W-09 catches a Week in Bias read on an issue with no bias report",
          [f for f in validate_script(parse_script(with_numbers), no_stats) if f.id == "W-09"])

    # W-10: the close asks.
    stated = re.sub(r"H: Who decides what a week was about\?", "H: The week is over.", clean)
    check("W-10 warns when the close states rather than asks",
          any(f.id == "W-10" for f in validate_script(parse_script(stated), issue)))


def test_w13(issue):
    """W-13: no voice says a number or a name the issue did not print."""
    print("\nWA-07  W-13: every voice's numbers and names are the issue's")
    clean = clean_for_band(issue)
    check("W-13 is silent on a clean rundown", not _fails(issue, clean, "W-13"), _detail(issue, clean, "W-13"))
    num = clean.replace("## CLOSE\n", "## CLOSE\nH: Nine hundred and seventy three thousand bases were promised.\n", 1)
    check("W-13 catches a spoken number the issue does not carry", _fails(issue, num, "W-13"))
    year = clean.replace("## CLOSE\n", "## CLOSE\nH: The deal dates to nineteen fifty one.\n", 1)
    check("W-13 catches a year the issue does not carry", _fails(issue, year, "W-13"))
    name = clean.replace("## CLOSE\n", "## CLOSE\nH: The Hudson Institute called it a bargain.\n", 1)
    check("W-13 catches a multi-word name the issue does not print", _fails(issue, name, "W-13"))
    for seg in ("OPEN", "TOPIC", "TURN", "EDITORIAL", "CLOSE"):
        planted = clean.replace(f"## {seg}\n" if seg != "EDITORIAL" else "## EDITORIAL | The editorial\n",
                                (f"## {seg}\n" if seg != "EDITORIAL" else "## EDITORIAL | The editorial\n")
                                + "H: Nine hundred and seventy three thousand bases were promised.\n", 1)
        check(f"W-13 reads the host in {seg}", _fails(issue, planted, "W-13"))
    # rev 2: the correspondents are read too, in the features and the week
    planted = clean.replace("## COVER | The cover\n", "## COVER | The cover\nA: Nine hundred and seventy three thousand bases were promised to the Hudson Institute in nineteen fifty one.\n", 1)
    check("W-13 reads a correspondent in the cover", _fails(issue, planted, "W-13"))
    if "## WEEK" in clean:
        planted = clean.replace(f"## WEEK\nH: {WEEK_OPEN}\n", f"## WEEK\nH: {WEEK_OPEN}\nB: The Hudson Institute counted nine hundred and seventy three thousand.\n", 1)
        check("W-13 reads a correspondent in the week", _fails(issue, planted, "W-13"))
    printed = _printed_name(issue)
    check("the issue prints a two-word name to test with", printed is not None)
    named = clean.replace("## CLOSE\n", f"## CLOSE\nH: {printed} spoke for the kingdom.\n", 1)
    check(f"W-13 passes a name the issue prints ({printed})", not _fails(issue, named, "W-13"), _detail(issue, named, "W-13"))
    sourced = clean.replace("## CLOSE\n", "## CLOSE\nH: The European Union was among the sources, as the record shows.\n", 1)
    check("W-13 passes a long form the issue prints short (EU)" if "EU" in json.dumps(issue) else "W-13 passes a line with no number",
          not _fails(issue, sourced, "W-13") if "EU" in json.dumps(issue) else True, _detail(issue, sourced, "W-13"))
    check("W-13 does not read the sign-on, which W-17 pins to the week", not _fails(issue, clean, "W-13"))


def test_rev2_rules(issue):
    """W-14..W-17: the editorial as written, the features in passages, the week
    in brief, Void's fixed lines."""
    print("\nWA-08  rev 2: W-14 the editorial, W-15 the features, W-16 the week, W-17 the formulas")
    clean = clean_for_band(issue)
    head = "## EDITORIAL | The editorial\n"
    i = clean.index(head) + len(head)
    j = clean.index("\n", i)
    intro = clean[i:j]
    check("W-14 catches an editorial that does not open on Void Opinion",
          _fails(issue, clean.replace(intro, "H: Now, the editorial.", 1), "W-14"))
    k = clean.index("\n", j + 1)
    first_para = clean[j + 1:k]
    reworded = "H: " + " ".join(first_para[3:].split()[:8]) + ", and the rest of it was rewritten freely in Void's own words for the ear tonight."
    check("W-14 catches an editorial line that is not the published column",
          _fails(issue, clean.replace(first_para, reworded, 1), "W-14"))
    check("W-14 passes the editorial read as written", not _fails(issue, clean, "W-14"), _detail(issue, clean, "W-14"))

    check("W-15 catches the wrong correspondent leading the cover",
          _fails(issue, clean.replace("## COVER | The cover\nA:", "## COVER | The cover\nB:", 1), "W-15"))
    check("W-15 catches a question between the correspondents",
          _fails(issue, clean.replace("## COVER | The cover\nA:", "## COVER | The cover\nA: And what did the desks make of it, do you think, this week of all weeks, with twenty desks on it?\nA:", 1), "W-15"))
    check("W-15 catches a passage too short for the ear",
          _fails(issue, clean.replace("## COVER | The cover\nA:", "## COVER | The cover\nA: The week turned on it.\nA:", 1), "W-15"))
    run = clean.replace("## COVER | The cover\nA:", "## COVER | The cover\n" + "\n".join(
        ["A: " + " ".join(["the record ran long and every count was published whole"] * 3)] * 4) + "\nA:", 1)
    check("W-15 catches one voice reading four passages in a row", _fails(issue, run, "W-15"))

    if "## WEEK" in clean:
        check("W-16 catches a week that does not open on the host's line",
              _fails(issue, clean.replace(f"H: {WEEK_OPEN}", "H: And now, briefly.", 1), "W-16"))
        check("W-16 catches a week item that is a question",
              _fails(issue, clean.replace(f"H: {WEEK_OPEN}\n", f"H: {WEEK_OPEN}\nA: Did the week end?\n", 1), "W-16"))
        many = clean.replace(f"H: {WEEK_OPEN}\n", f"H: {WEEK_OPEN}\n" + "".join(
            f"{'AB'[n % 2]}: The record ran long and the count was published whole.\n" for n in range(12)), 1)
        check("W-16 catches more items than the issue prints briefs", _fails(issue, many, "W-16"))

    check("W-17 catches a sign-on that mis-dates the week",
          _fails(issue, clean.replace(sign_on_line(issue), sign_on_line({"week_start": "2026-01-05", "week_end": "2026-01-11"}), 1), "W-17"))
    check("W-17 catches a cold open that names the programme",
          _fails(issue, clean.replace("H: The week opened on a count and closed on another.", "H: This is The Argument.", 1), "W-17"))
    check("W-17 catches a wrong sign-off",
          _fails(issue, clean.replace(f"{CLOSE_PREFIX} {CLOSE_TAG}", "Thanks, and goodnight.", 1), "W-17"))
    check("W-17 catches a contents that does not open on its line",
          _fails(issue, clean.replace(f"H: {CONTENTS_OPEN}", "H: Coming up.", 1), "W-17"))


def test_grounding(issue):
    """The grounding pass: a sentence the issue does not carry is cut; the
    columns and the formulas are not touched; a clean rundown loses nothing."""
    print("\nWA-09  the grounding pass")
    clean = clean_for_band(issue)
    script = parse_script(clean)
    before = script.words
    cuts = ground_script(script, issue)
    check("a clean rundown loses nothing to grounding", not cuts and script.words == before,
          str([(c.sentence[:60], c.reason) for c in cuts]))
    planted = clean.replace("## TURN\n", "## TURN\nH: The Hudson Institute put the cost at nine hundred and seventy three thousand dollars.\n", 1)
    script = parse_script(planted)
    cuts = ground_script(script, issue)
    turn = " ".join(l.text for s in script.of_kind("TURN") for l in s.lines)
    check("a sentence the issue does not carry is cut", len(cuts) == 1 and "Hudson" not in turn,
          str([(c.sentence[:60], c.reason) for c in cuts]))
    check("the cut is logged with its reason", cuts and cuts[0].reason and cuts[0].product == "weekly:TURN",
          str(cuts[:1]))
    cols = _bench_columns(issue.get("opinions") or [])
    bogus = clean.replace("## LEFT\n", "## LEFT\nA: " + " ".join(_sentences(cols["L"], 1, 40)) + "\n", 1)
    script = parse_script(bogus)
    n_left = sum(len(s.lines) for s in script.of_kind("LEFT"))
    ground_script(script, issue)
    check("the columns are W-01's and the pass does not touch them",
          sum(len(s.lines) for s in script.of_kind("LEFT")) == n_left)
    script = parse_script(clean)
    ground_script(script, issue)
    check("the sign-on survives the pass", script.of_kind("OPEN")[0].lines[0].text == sign_on_line(issue))
    check("the sign-off survives the pass", script.of_kind("CLOSE")[0].lines[-1].text.endswith(CLOSE_TAG))


def test_cast():
    print("\nWA-10  the cast and the side rule")
    casts = [cast_for_week(f"2026-{m:02d}-{d:02d}") for m in range(1, 13) for d in (5, 12, 19, 26)]
    check("the host is always the host", all(c["H"] == HOST_VOICE for c in casts))
    check("the host anchors On Air too: one family", HOST_VOICE == "af_aoede")
    check("the correspondents are two other voices",
          all({c["A"], c["B"]} == set(CORRESPONDENT_VOICES) and c["A"] != c["B"] for c in casts))
    lefts = [c["A"] for c in casts]
    check("over a year no voice owns the left column",
          0.3 <= lefts.count(CORRESPONDENT_VOICES[0]) / len(lefts) <= 0.7,
          f"{lefts.count(CORRESPONDENT_VOICES[0])} of {len(lefts)} weeks")
    check("the draw is deterministic", cast_for_week("2026-10-26") == cast_for_week("2026-10-26"))
    check("one house pace, On Air's", SPEED == 0.88)


def test_columns_match_the_page(issue):
    print("\nWA-03  the bench is the page's pair")
    cols = _bench_columns(issue.get("opinions") or [])
    check("a pair was found", set(cols) == {"L", "R"}, str(sorted(cols)))
    paired = [o for o in issue["opinions"] if o.get("paired")]
    check("the pair is the flagged pair", len(paired) == 2, str(len(paired)))
    check("left is left", (paired[0].get("lean") or "").startswith("left") or cols["L"] == (paired[0].get("text") or ""))
    check("both columns carry text", all(len(v.split()) > 50 for v in cols.values()))
    tsx = (ROOT / "frontend" / "app" / "weekly" / "components" / "Perspectives.tsx").read_text()
    for token in ("pair_id", "paired", "lean"):
        check(f"findPair still keys on {token}", token in tsx)


def test_committed_scripts():
    """Every AUTHORED rundown, against the issue it was written from: valid,
    inside its band, and nothing lost to grounding (Rule 1: a sentence the
    issue does not carry is cut at render time, so a committed script that
    would lose one is a script with an unsourced sentence in it)."""
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
        voices = cast_for_week(week, issue.get("edition") or "world")
        script = parse_script(path.read_text(encoding="utf-8"))
        findings = validate_script(script, issue, voices)
        fails = [f for f in findings if f.level == "fail"]
        for f in fails:
            print(f"         {f.id} [{f.segment}] {f.detail[:100]}")
        check(f"{week}: renders clean", not fails, "; ".join(f"{f.id}" for f in fails))
        minutes, wpm = estimated_minutes(script, voices)
        lo, hi = target_minutes(issue)
        check(f"{week}: inside its {lo:.0f}-{hi:.0f} band", lo <= minutes <= hi, f"{minutes:.1f} min, {script.words} words")
        cuts = ground_script(script, issue)
        check(f"{week}: loses nothing to grounding", not cuts, str([(c.sentence[:60], c.reason) for c in cuts]))


# ---------------------------------------------------------------------------
# WA-05: the word budget the generator is given must land inside W-07's band.
# ---------------------------------------------------------------------------
def _synthetic(total_words: int, host_share: float) -> str:
    host = int(total_words * host_share)
    half = (total_words - host) // 2

    def block(speaker: str, words: int) -> str:
        return "\n".join(f"{speaker}: " + " word" * 40 for _ in range(max(1, words // 40)))

    return ("## OPEN\n" + block("H", host) + "\n## LEFT\n" + block("A", half)
            + "\n## RIGHT\n" + block("B", half) + "\n## CLOSE\nH: and what now?\n")


def test_wa05_word_budget_lands_inside_the_band() -> bool:
    from briefing.weekly_script import MUSIC_MINUTES, VOICE_WPM, word_budget
    voices = cast_for_week("2026-10-26")
    lo_band, hi_band = TARGET_MINUTES
    lo_w, hi_w = word_budget(voices)
    ok = True
    print("WA-05  the generator's word budget lands inside W-07's band")
    for share, label in ((0.85, "host-heavy"), (0.6, "typical"), (0.4, "correspondent-heavy")):
        for words, edge in ((lo_w, "floor"), (hi_w, "ceiling")):
            script = parse_script(_synthetic(words, share), "world")
            minutes, _ = estimated_minutes(script, voices)
            inside = lo_band <= minutes <= hi_band
            print(f"  [{'ok' if inside else 'FAIL'}] {label} {edge}: {script.words} words is {minutes:.2f} min")
            ok = ok and inside
    speech_only_ceiling = int(hi_band * min(VOICE_WPM[v] for v in voices.values()))
    if hi_w >= speech_only_ceiling:
        print(f"  [FAIL] ceiling {hi_w} ignores MUSIC_MINUTES ({speech_only_ceiling} would)")
        ok = False
    else:
        print(f"  [ok] the ceiling accounts for {MUSIC_MINUTES} min of music — {hi_w} not {speech_only_ceiling}")
    return ok


def test_wa06_the_prompt_names_the_banned_phrases() -> bool:
    from briefing import weekly_rundown
    from briefing.weekly_script import BORROWED
    ok = True
    print("WA-06  the rundown prompt names the phrases W-08 rejects, and the format it writes")
    rendered = weekly_rundown.system_prompt({"week_start": "2026-10-26", "week_end": "2026-11-01",
                                             "bias_report_data": {"stats": {"avg_lean": 50.0}}})
    for phrase in ("absolutely", "great question", "let's dive"):
        if phrase not in rendered:
            print(f"  [FAIL] the prompt never tells the model to avoid {phrase!r}")
            ok = False
    for marker in ("## COLD", "## OPEN", "## WEEK", "## NUMBERS", "## EDITORIAL", OPINION_OPEN, WEEK_OPEN,
                   "October twenty-sixth to November first"):
        if marker not in rendered:
            print(f"  [FAIL] the prompt does not teach the model {marker!r}")
            ok = False
    if ok:
        print(f"  [ok] all {len(BORROWED)} borrowed phrases and the rev 2 markers are in the prompt")
    return ok


def main():
    print("void --weekly audio gates (The Argument)")
    issue = test_clean()
    test_planted(issue)
    test_w13(issue)
    test_rev2_rules(issue)
    test_grounding(issue)
    test_cast()
    test_columns_match_the_page(issue)
    test_committed_scripts()
    print()
    if not test_wa05_word_budget_lands_inside_the_band():
        _failures.append("WA-05")
    print()
    if not test_wa06_the_prompt_names_the_banned_phrases():
        _failures.append("WA-06")
    print()
    # The assembly and score gates (tests/test_weekly_assembly.py) need scipy,
    # which the radio-audio job does not install; they are run from here, in
    # the gates job, and must pass.
    import subprocess
    env = dict(os.environ, VOID_REQUIRE_SCIPY="1")
    asm = subprocess.run([sys.executable, str(Path(__file__).with_name("test_weekly_assembly.py"))],
                         env=env, capture_output=True, text=True)
    print(asm.stdout[-1500:])
    if asm.returncode != 0:
        print(asm.stderr[-1500:])
        _failures.append("assembly (tests/test_weekly_assembly.py)")
    print()
    if _failures:
        print(f"FAILED ({len(_failures)}): " + ", ".join(_failures))
        return 1
    print("All weekly-audio script gates passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
