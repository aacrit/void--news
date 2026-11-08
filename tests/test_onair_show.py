"""On Air, the conversation: the script's grammar, its validators, the
template edition, the score standard and the timeline. No LLM, no TTS.

    python tests/test_onair_show.py

Pattern (tests/test_radio_script.py): the clean fixture passes every check
and loses nothing to the grounding pass; then one planted defect per
validator fires exactly that id. The score checks render each cue type and
measure it against the standard in onair_score, then plant a tiled loop, a
loud featured cue and a steep duck and see each caught.
"""

from __future__ import annotations

import datetime
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
os.environ.setdefault("VOID_SQLITE_PATH", str(ROOT / "tests" / ".onair-show-test.db"))

import numpy as np  # noqa: E402

from briefing.onair_show import (  # noqa: E402
    Context, parse_show, validate_show, bind_ranks, ground_show, template_show, build_prompt,
    generate_show, coverage_line, SIGN_ON, CLOSE_PREFIX, CLOSE_TAG, DESK_LEAD, OPINION_OPEN, WORD_BUDGETS, TOTAL_BUDGET,
)
from briefing.spoken_text import spoken_date  # noqa: E402
from briefing import onair_score as S  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "onair_show_2026-11-07.txt"
STORIES = ROOT / "tests" / "fixtures" / "onair_stories_2026-11-07.json"
DATE = datetime.datetime(2026, 11, 7, 19, tzinfo=datetime.timezone.utc)

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"  [{'ok' if cond else 'FAIL'}] {msg}")
    if not cond:
        failures.append(msg)


def stories() -> list[dict]:
    return json.loads(STORIES.read_text(encoding="utf-8"))


def ctx() -> Context:
    return Context(top=stories(), date_spoken=spoken_date(DATE))


def fail_ids(report) -> set[str]:
    return {f.id for f in report.findings if f.level == "fail"}


def planted(raw: str, old: str, new: str) -> set[str]:
    assert old in raw, old
    show = parse_show(raw.replace(old, new, 1))
    bind_ranks(show, ctx())
    return fail_ids(validate_show(show, ctx()))


# ---------------------------------------------------------------- the clean fixture
def clean_fixture() -> str:
    raw = FIXTURE.read_text(encoding="utf-8")
    show = parse_show(raw)
    bind_ranks(show, ctx())
    rep = validate_show(show, ctx())
    check(rep.passed, f"fixture passes every validator ({[f'{f.id} {f.detail[:50]}' for f in rep.failures]})")
    check([s.kind for s in show.segments] == ["COLD", "TITLE", "LEAD", "SECOND", "DESK", "CLOSE"],
          "fixture carries the six segments in order")
    lead = show.seg("LEAD")
    check(lead is not None and lead.cluster_id == stories()[0]["id"], "LEAD is bound to rank 1 by position, not copied")
    desk = show.seg("DESK")
    check(desk is not None and desk.desk_ranks == [3, 4, 5, 6, 7, 8], f"desk items bind to ranks 3-8 ({desk.desk_ranks if desk else None})")
    words_before = show.words
    cuts = ground_show(show, ctx())
    check(not cuts, f"the grounding pass cuts nothing from the fixture ({[c.sentence[:60] for c in cuts]})")
    check(show.words == words_before, "grounding left the word count unchanged")
    check(TOTAL_BUDGET[0] <= show.words <= TOTAL_BUDGET[1], f"{show.words} words inside the total budget")
    check(lead is not None and lead.exchanges() >= 5, "the lead has at least five exchanges")
    check(any(not t.is_question for t in lead.turns if t.speaker == "A"), "the asker may make a statement the desk picks up")
    check(show.say.get("Eisenkot") == "eye-zen-kot", "SAY respellings parse and lowercase")
    check(show.to_text().startswith("## COLD"), "to_text round-trips the markers")
    return raw


# ---------------------------------------------------------------- planted defects
def planted_defects(raw: str) -> None:
    check("C-01" in planted(raw, f"A: {SIGN_ON} It's Saturday, November seventh.",
                            "A: Good evening, this is On Air. It's Saturday, November seventh."),
          "C-01 fires on a sign-on that is not Void's line")
    check("C-01" in planted(raw, CLOSE_TAG, "Goodnight."), "C-01 fires on a sign-off without the tag")
    check("C-02" in planted(raw, "pledged loyalty to the president.", 'pledged "loyalty" to the president.'),
          "C-02 fires on quotation marks")
    check("C-04" in planted(raw, "On Friday evening he was at Mar-a-Lago", "At 7 p.m. he was at Mar-a-Lago"), "C-04 fires on a clock form")
    check("C-05" in planted(raw, "A: Let's start with what the president actually announced.", "A: Welcome back. What did the president announce?"),
          "C-05 fires on a borrowed phrase")
    check("C-05" in planted(raw, "Sharply, and along party lines.", "Sharply, and the split is significant."),
          "C-05 fires on a significance word in Void's voice")
    check("C-05" in planted(raw, "A: And Susie Wiles? She'd been there since the start of this term.", "A: Thanks. And Susie Wiles? She'd been there since the start of this term."),
          "C-05 fires on thanking a host")
    # C-06: empty the lead to one exchange
    lead_start = raw.index("## LEAD")
    second_start = raw.index("## SECOND")
    short = raw[:lead_start] + ("## LEAD | Miller Takes the West Wing\nA: What did the president announce?\n"
                                "B: President Donald Trump announced on Friday that Stephen Miller will replace Susie Wiles "
                                "as White House chief of staff. The change takes effect on Monday.\n\n") + raw[second_start:]
    show = parse_show(short)
    bind_ranks(show, ctx())
    ids = fail_ids(validate_show(show, ctx()))
    check("C-06" in ids and "C-07" in ids, f"C-06 and C-07 fire on a one-exchange lead ({ids})")
    check("C-07" in planted(raw, "A: Remind us what he's actually done on immigration.", "B: Remind us what he's actually done on immigration?"),
          "C-07 fires when the answering voice asks")
    check("C-07" in planted(raw, "A: Let's start with what the president actually announced.",
                            "A: Let's start with what the president actually announced, and how he announced it, and when, and who "
                            "was in the room, and what they said about it afterwards, and why he chose Friday for it, and to whom?"),
          "C-07 fires on a question over the word cap")
    check("C-08" in planted(raw, "Police shot and arrested him.",
                            "Police shot and arrested him after a chase through the square that witnesses described at length."),
          "C-08 fires on a desk item over the word cap")
    check("C-08" in planted(raw, f"A: {DESK_LEAD}", "A: Also on the desk."), "C-08 fires when the desk opens on another line")
    check("C-11" in planted(raw, "Schumer states he has sufficient votes within his caucus to retain his leadership position.",
                            "Schumer states he will resign before the new Congress meets."),
          "C-11 fires on an attributed claim the story does not carry")
    check("C-12" in planted(raw, "Police shot and arrested him.", "The Constitution protects the square."),
          "C-12 fires on a court or a law in Void's own voice")
    # C-09: hand every B line to A
    show = parse_show(raw.replace("\nB: ", "\nA: "))
    bind_ranks(show, ctx())
    check("C-09" in fail_ids(validate_show(show, ctx())), "C-09 fires when one voice carries the show")
    # a cut answer takes its question with it
    wiles = ("B: She had, and she was the first woman to hold the post. Wiles submitted her resignation on Thursday night. "
             "According to the president's announcement, she's moving to his political operation.")
    assert wiles in raw
    show = parse_show(raw.replace(wiles, "B: Wiles has taken a post at the United Nations in Geneva, a city of two million."))
    bind_ranks(show, ctx())
    cuts = ground_show(show, ctx())
    lead = show.seg("LEAD")
    texts = " ".join(t.text for t in lead.turns)
    check(bool(cuts) and "Geneva" not in texts, "grounding cuts an answer the story does not carry")
    check("And Susie Wiles?" not in texts, "a question whose answer was cut whole goes with it")
    check(all(lead.turns[i].speaker != lead.turns[i + 1].speaker for i in range(len(lead.turns) - 1)),
          "the voices still alternate after a cut")


# ---------------------------------------------------------------- template and prompt
def template_and_prompt() -> None:
    show = template_show(stories(), DATE)
    bind_ranks(show, ctx())
    rep = validate_show(show, ctx())
    check([s.kind for s in show.segments] == ["COLD", "TITLE", "LEAD", "SECOND", "DESK", "CLOSE"],
          "the template edition carries every segment")
    check(not any(f.id in ("C-01", "C-02", "C-04", "C-05", "C-08", "C-09", "C-11", "C-12") for f in rep.failures),
          f"the template edition breaks no line rule ({[f.id for f in rep.failures]})")
    cuts = ground_show(show, ctx())
    check(not cuts, f"the template edition is grounded by construction ({[c.sentence[:50] for c in cuts]})")
    lead = show.seg("LEAD")
    check(lead is not None and any(t.text.startswith("Of the") for t in lead.turns), "the template reads the coverage line")
    cov = coverage_line(stories()[0])
    check(cov == "Of the sixty outlets Void placed on this story, twenty-four sit left of centre, twenty at the centre and sixteen right of it.",
          f"coverage line is one vote per outlet, in words ({cov!r})")
    check(coverage_line({"bias_diversity": {"lean_buckets": {"center": 2}}}) is None, "a thin roster gives no coverage line")

    system, user = build_prompt(stories(), spoken_date(DATE))
    check(f"{SIGN_ON} It's {spoken_date(DATE)}." in user, "the prompt carries the sign-on and the day")
    check(CLOSE_PREFIX in user and CLOSE_TAG in user and DESK_LEAD in user, "the prompt carries Void's lines")
    check(f"{WORD_BUDGETS['LEAD'][0]}-{WORD_BUDGETS['LEAD'][1]} words" in user, "the prompt's budgets are the validator's")
    check("<source id=" in user, "every story is wrapped as data")
    check("Coverage:" in user, "the prompt hands the model the coverage line")

    # the Opinion as a conversation: template, prompt, validators
    op_text = ("The argument has two parts. The first part says the Senate changed hands in January. "
               "The second part says any vacancy on the court will meet a Democratic majority. "
               "The conclusion is that the two justices face a different calendar than they did a week ago.")
    show = template_show(stories(), DATE, opinion_text=op_text, opinion_headline="Two Justices and a Senate", opinion_lean="center")
    octx = Context(top=stories(), date_spoken=spoken_date(DATE), opinion_text=op_text,
                   opinion_headline="Two Justices and a Senate", opinion_lean="center")
    bind_ranks(show, octx)
    rep = validate_show(show, octx)
    op = show.seg("OPINION")
    check(op is not None and [t.speaker for t in op.turns][:2] == ["A", "C"], "the template Opinion is A asking, C arguing")
    check(op is not None and op.turns[0].text.startswith(f"{OPINION_OPEN} Through a pragmatic lens today."),
          "the template Opinion opens on Void's line and names its lens")
    check(not rep.failures, f"the template Opinion passes ({[f.id + ' ' + f.detail[:40] for f in rep.failures]})")
    cuts = ground_show(show, octx)
    check(not cuts, "C's lines are grounded in the Opinion text by construction")
    system, user = build_prompt(stories(), spoken_date(DATE), opinion_text=op_text, opinion_headline="Two Justices and a Senate",
                                opinion_lean="left")
    check("## OPINION" in user and "Through a progressive lens today." in user and "<source id=\"opinion\"" in user,
          "the prompt carries the Opinion block, its lens and the text as data")
    no_op = validate_show(parse_show(FIXTURE.read_text(encoding="utf-8")), octx)
    check(any(f.id == "C-00" and f.segment == "OPINION" for f in no_op.failures),
          "an edition with an Opinion whose script carries none fails")
    with_op = parse_show(FIXTURE.read_text(encoding="utf-8").replace("## CLOSE",
              "## OPINION | Two Justices\nA: Now, the Opinion. Through a pragmatic lens today. What's the argument?\n"
              "C: The argument has two parts. The first part says the Senate changed hands in January.\n"
              "A: And where does it land?\n"
              "C: The second part says any vacancy on the court will meet a Democratic majority.\n\n## CLOSE"))
    bind_ranks(with_op, ctx())
    check(any(f.id == "C-00" and f.segment == "OPINION" for f in validate_show(with_op, ctx()).failures),
          "an Opinion segment on a day with no written opinion fails")
    bind_ranks(with_op, octx)
    check(not [f for f in validate_show(with_op, octx).failures if f.segment == "OPINION"],
          "a two-exchange Opinion with the lens line passes")
    c_in_lead = parse_show(FIXTURE.read_text(encoding="utf-8").replace("\nB: She had, and she was", "\nC: She had, and she was"))
    bind_ranks(c_in_lead, ctx())
    check(any(f.id == "C-00" for f in validate_show(c_in_lead, ctx()).failures), "C outside the Opinion fails")

    # generation: a model that answers garbage, then the template
    show, rep, label = generate_show(stories(), date=DATE, generate_fn=lambda s, u: "nonsense")
    check(show is not None and label == "template-after-gemini", f"a failed model falls to the template ({label})")
    show, rep, label = generate_show(stories(), date=DATE, generate_fn=lambda s, u: FIXTURE.read_text(encoding="utf-8"))
    check(show is not None and label == "gemini" and show.grounded is True, f"the fixture is accepted as the model's ({label})")
    # a script with one repairable defect is repaired, not lost
    raw = FIXTURE.read_text(encoding="utf-8").replace("pledged loyalty to the president.", 'pledged "loyalty" to the president.')
    show, rep, label = generate_show(stories(), date=DATE, generate_fn=lambda s, u: raw, max_attempts=1)
    check(show is not None and label == "gemini", "quotation marks alone are stripped rather than costing the show")


# ---------------------------------------------------------------- the score
def score() -> None:
    v = S.voicing_for("onair:world:2026-11-07")
    v2 = S.voicing_for("onair:world:2026-11-08")
    check(v.seed != v2.seed, "two days get two voicings")
    theme, _ = S.level_featured(S.render_theme(v))
    check(not S.check_cue(theme, "featured"), f"the theme meets the featured standard ({[f.id for f in S.check_cue(theme, 'featured')]})")
    peak = None
    for seg, dur in (("lead", 40.0), ("desk", 30.0), ("opinion", 30.0)):
        bed, _ = S.level_bed(S.render_bed(v, seg, dur))
        f = S.check_cue(bed, "bed")
        check(not f, f"the {seg} bed meets the bed standard ({[x.id for x in f]})")
        check(abs(S.lufs_integrated(bed) - S.BED_LUFS) < 0.6, f"the {seg} bed sits at {S.BED_LUFS} LUFS ({S.lufs_integrated(bed):.1f})")
        check(S.band_share(bed, 5000.0, None, 100.0) <= S.MUSIC_TREBLE_MAX_SHARE, f"the {seg} bed carries almost no treble")
        peak = S.bed_peak_lufs(bed)
    tr, _ = S.level_transition(S.render_transition(v), peak)
    check(not S.check_cue(tr, "transition", bed_peak_lufs=peak), "the page-turn is never louder than the bed it leads into")
    outro, _ = S.level_featured(S.render_outro(v))
    check(not S.check_cue(outro, "featured"), "the outro meets the featured standard")
    check(float(np.max(np.abs(outro[-S.SR // 2:]))) < 1e-3, "the outro falls to silence")
    # planted defects
    loud = theme * 10 ** (4.0 / 20)
    check(any(f.id == "featured-level" for f in S.check_cue(loud, "featured")), "a featured cue 4 dB over the ceiling is caught")
    seg4 = S.render_bed(v, "lead", 4.5)[: 4 * S.SR]
    looped, _ = S.level_bed(np.concatenate([seg4, seg4, seg4, seg4]))
    check(any(f.id == "score-repetition" for f in S.check_cue(looped, "bed")), "a tiled loop is caught")
    steady = np.sin(2 * np.pi * 440.0 * np.arange(10 * S.SR) / S.SR) * 0.01
    check(any(f.id == "bed-breathing" for f in S.check_cue(steady, "bed")), "a bed that does not breathe is caught")
    bright = S.render_bed(v, "lead", 12.0) + 0.02 * np.random.default_rng(1).normal(0, 1, (int(12.0 * S.SR), 2))
    check(any(f.id == "music-treble" for f in S.check_cue(bright, "bed")), "treble over the shelf is caught")
    env = S.duck_envelope(30.0, [(5.0, 9.0), (9.6, 14.0), (17.0, 20.0)])
    check(not S.check_duck(env), "the eased pre-roll never falls over 2 dB in 100 ms")
    g = np.arange(len(env)) * 0.01
    check(float(env[int(5.0 / 0.01)]) <= S.DUCK_DB + 0.01, "the duck is at full depth on the onset")
    check(float(env[int(4.0 / 0.01) - 1]) > -0.1, "the duck is up 1 s before the onset")
    check(float(env[int(9.3 / 0.01)]) <= S.DUCK_DB + 0.01, "the duck holds through a gap shorter than the hold")
    check(float(env[int(16.0 / 0.01)]) > -0.1, "the duck releases across a longer gap")
    check(g.size == env.size, "envelope grid")
    steep = S.duck_envelope(30.0, [(5.0, 9.0)], preroll_s=0.3)
    check(any(f.id == "duck-slope" for f in S.check_duck(steep)), "a steep attack is caught")


# ---------------------------------------------------------------- timeline and chapters
def timeline() -> None:
    from briefing.onair_producer import build_cues, build_timeline, chapters_from_timeline, ShowResult
    raw = FIXTURE.read_text(encoding="utf-8")
    show = parse_show(raw)
    bind_ranks(show, ctx())
    v = S.voicing_for("onair:world:2026-11-07")
    op_raw = raw.replace("## CLOSE", "## OPINION | Two Justices\nA: Now, the Opinion. Through a pragmatic lens today. What's the argument?\n"
                         "C: The argument has two parts, and the first part says the Senate changed hands in January, which matters.\n"
                         "A: And where does it land?\nC: It lands on the two justices, who face a different calendar than a week ago.\n\n## CLOSE")
    show = parse_show(op_raw)
    bind_ranks(show, ctx())
    cues = build_cues(show, None)
    check(any(c.kind == "OPINION" and c.role == "C" for c in cues) and any(c.kind == "OPINION" and c.role == "A" for c in cues),
          "the Opinion's cues carry A and C")
    lengths = {c.idx: 0.4 * len(c.text.split()) for c in cues}
    tl = build_timeline(cues, lengths, v)
    check(all(tl.cues[i].end <= tl.cues[i + 1].start for i in range(len(tl.cues) - 1)), "no two lines overlap")
    check(tl.news_start > 0 and tl.opinion_start is not None and tl.opinion_start > tl.news_start, "news and opinion marks")
    check(tl.outro_at < tl.last_word < tl.total, "the outro starts before the last word ends and the file outlives it")
    names = [m.name for m in tl.music]
    check(names.count("theme") == 1 and names.count("pageturn") == 2 and names.count("entrance") == 1 and names.count("outro") == 1,
          f"one theme, two page-turns, one entrance, one outro ({names})")
    check(names.count("lead") >= 2, "the lead bed leaves and comes back")
    beds = [m for m in tl.music if m.role == "bed"]
    check(all(m.end - m.start >= 4.5 for m in beds), "every bed is long enough to be judged")
    ch = chapters_from_timeline(tl, opinion_headline="An argument", permalinks={stories()[0]["id"]: "/story/x/"})
    kinds = [c["kind"] for c in ch]
    check(kinds == ["headlines", "story", "story", "briefs", "opinion"], f"chapter kinds ({kinds})")
    check(ch[0]["startTime"] == 0.0 and all(ch[i]["startTime"] < ch[i + 1]["startTime"] for i in range(len(ch) - 1)),
          "chapters start at zero and rise")
    check(ch[1].get("rank") == 1 and ch[1].get("url") == "/story/x/" and ch[2].get("rank") == 2, "story chapters carry rank and link")
    check(ch[4]["startTime"] == round(tl.opinion_start, 3) and ch[4].get("subtitle") == "An argument",
          "the Opinion chapter starts at its entrance music")
    check(all(ch[i]["endTime"] == ch[i + 1]["startTime"] for i in range(len(ch) - 1)) and ch[-1]["endTime"] == round(tl.total, 3),
          "chapters tile the file")
    r = ShowResult(audio_url="x", duration_seconds=1.0, file_size=1, news_start_seconds=1.0, opinion_start_seconds=None,
                   chapters=[], engine="kokoro", voices="kokoro:a+b")
    check(r.as_row_fields()["audio_voice_label"] == "Two voices", "no Opinion, two voices on the label")
    r.opinion_start_seconds = 5.0
    check(r.as_row_fields()["audio_voice_label"] == "Three voices", "an Opinion, three voices on the label")
    # without an opinion, no entrance and no opinion chapter
    show = parse_show(raw)
    bind_ranks(show, ctx())
    cues = build_cues(show, None)
    tl = build_timeline(cues, {c.idx: 0.4 * len(c.text.split()) for c in cues}, v)
    check("entrance" not in [m.name for m in tl.music] and tl.opinion_start is None, "no opinion, no entrance")


def main() -> int:
    print("--- the clean fixture ---")
    raw = clean_fixture()
    print("--- planted defects ---")
    planted_defects(raw)
    print("--- the template edition and the prompt ---")
    template_and_prompt()
    print("--- the score ---")
    score()
    print("--- the timeline ---")
    timeline()
    if failures:
        print(f"\n{len(failures)} FAILED")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
