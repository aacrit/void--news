"""On Air, the newsroom: the script's grammar, its validators, the
template edition, the score standard and the timeline. No LLM, no TTS.

    python tests/test_onair_show.py

Pattern (tests/test_radio_script.py): the clean fixture passes every check
and loses nothing to the grounding pass; then one planted defect per
validator fires exactly that id. The score checks render each cue type and
measure it against the standard in onair_score, then plant a tiled loop, a
loud featured cue, a steep duck, a loud and a silent interlude, a rev 5 tick
train and a pair of bright hats on a calm bed, and see each caught.
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
    COVERAGE_FORMULA_RE, content_words, is_repeat, remove_repeats, repeats_in, material_divergence, _sentences,
    Show, Segment, Turn, Context, parse_show, validate_show, bind_ranks, ground_show, template_show, build_prompt,
    generate_show, coverage_line, SIGN_ON, CLOSE_PREFIX, CLOSE_TAG, DESK_LEAD, OPINION_OPEN, WORD_BUDGETS, TOTAL_BUDGET,
)
from briefing.spoken_text import spoken_date  # noqa: E402
from briefing import onair_score as S  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "onair_show_2026-11-07.txt"
STORIES = ROOT / "tests" / "fixtures" / "onair_stories_2026-11-07.json"
OPINION = ROOT / "tests" / "fixtures" / "onair_opinion_2026-11-07.txt"
OP_HEAD, OP_LEAN = "The Door Stephen Miller Will Hold", "left"
DATE = datetime.datetime(2026, 11, 7, 19, tzinfo=datetime.timezone.utc)

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"  [{'ok' if cond else 'FAIL'}] {msg}")
    if not cond:
        failures.append(msg)


def stories() -> list[dict]:
    return json.loads(STORIES.read_text(encoding="utf-8"))


def ctx() -> Context:
    """The edition as published: eight stories and the day's Opinion."""
    return Context(top=stories(), date_spoken=spoken_date(DATE), opinion_text=OPINION.read_text(encoding="utf-8"),
                   opinion_headline=OP_HEAD, opinion_lean=OP_LEAN)


def ctx_no_op() -> Context:
    return Context(top=stories(), date_spoken=spoken_date(DATE))


def without_opinion(raw: str) -> str:
    a, b = raw.index("## OPINION"), raw.index("## CLOSE")
    return raw[:a] + raw[b:]


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
    check([s.kind for s in show.segments] == ["COLD", "TITLE", "LEAD", "SECOND", "DESK", "OPINION", "CLOSE"],
          "fixture carries the seven segments in order")
    lead = show.seg("LEAD")
    check(lead is not None and lead.cluster_id == stories()[0]["id"], "LEAD is bound to rank 1 by position, not copied")
    desk = show.seg("DESK")
    check(desk is not None and desk.desk_ranks == [3, 4, 5, 6, 7, 8, 9, 10], f"desk items bind to ranks 3-10 ({desk.desk_ranks if desk else None})")
    words_before = show.words
    cuts = ground_show(show, ctx())
    check(not cuts, f"the grounding pass cuts nothing from the fixture ({[c.sentence[:60] for c in cuts]})")
    check(show.words == words_before, "grounding left the word count unchanged")
    check(TOTAL_BUDGET[0] <= show.words <= TOTAL_BUDGET[1], f"{show.words} words inside the total budget")
    check(lead is not None and lead.exchanges() >= 5, "the lead has at least five passages")
    check(lead is not None and not any(t.is_question for t in lead.turns), "nobody interviews anybody in the lead")
    check(lead is not None and lead.turns[0].speaker == "A" and lead.turns[-1].speaker == "B", "A leads the lead, B takes the last passage")
    second = show.seg("SECOND")
    check(second is not None and second.turns[0].speaker == "B" and second.turns[-1].speaker == "A", "B leads the second, A takes the last passage")
    op = show.seg("OPINION")
    check(op is not None and {t.speaker for t in op.turns} == {"A"} and len(op.turns) >= 3, "A introduces Void Opinion and reads it (rev 5: two voices)")
    check(op is not None and op.turns[0].text.startswith("This is Void Opinion. Through a progressive lens today."),
          "the Opinion is introduced by name: Void Opinion, then its lens")
    check({t.speaker for s in show.segments for t in s.turns} == {"A", "B"}, "two voices in the whole script, A and B")
    # rev 6: the spoken Opinion is its own sentences, in order; the only ones
    # missing are the ones the listener heard in the news segments
    written = [x.strip() for x in _sentences(" ".join(OPINION.read_text(encoding="utf-8").split())
               .replace("3,000", "three thousand").replace("170 billion", "one hundred seventy billion")
               .replace("58 percent", "fifty-eight percent")) if x.strip()]
    spoken = [x.strip() for t in (op.turns[1:] if op else []) for x in _sentences(t.text) if x.strip()]
    it = iter(written)
    in_order = all(any(w == x for w in it) for x in spoken)
    heard = [content_words(x) for s_ in show.segments if s_.kind in ("COLD", "TITLE", "LEAD", "SECOND", "DESK")
             for t in s_.turns for x in _sentences(t.text)]
    missing = [w for w in written if w not in spoken]
    check(in_order and spoken and all(is_repeat(w, heard) for w in missing),
          f"the Opinion's passages are its own sentences, in order; only what was already heard is left out ({missing})")
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
    check("C-05" in planted(raw, "A: On Friday, President Donald Trump announced", "A: Welcome back. On Friday, President Donald Trump announced"),
          "C-05 fires on a borrowed phrase")
    check("C-05" in planted(raw, "publicly backed the move.", "publicly backed the move, a significant shift."),
          "C-05 fires on a significance word in Void's voice")
    check("C-05" in planted(raw, "B: That record runs across both terms.", "B: Thanks. That record runs across both terms."),
          "C-05 fires on thanking a host")
    # C-06: empty the lead to one passage
    lead_start = raw.index("## LEAD")
    second_start = raw.index("## SECOND")
    short = raw[:lead_start] + ("## LEAD | Miller Takes the West Wing\n"
                                "A: President Donald Trump announced on Friday that Stephen Miller will replace Susie Wiles "
                                "as White House chief of staff. The change takes effect on Monday. Miller is the deputy chief of staff now.\n\n") + raw[second_start:]
    show = parse_show(short)
    bind_ranks(show, ctx())
    ids = fail_ids(validate_show(show, ctx()))
    check("C-06" in ids and "C-07" in ids, f"C-06 and C-07 fire on a one-passage lead ({ids})")
    check("C-07" in planted(raw, "A: On Friday, President Donald Trump announced", "B: On Friday, President Donald Trump announced"),
          "C-07 fires when the other anchor leads the lead")
    check("C-07" in planted(raw, "B: That record runs across both terms.", "A: That record runs across both terms."),
          "C-07 fires when one voice reads four passages in a row")
    check("C-07" in planted(raw, "B: That record runs across both terms. Miller's forty-one,",
                            "B: What's his record? Where did it start? Miller's forty-one,"),
          "C-07 fires when the anchors interview each other")
    check("C-07" in planted(raw, "A: Wiles had held the post since the start of this term, and she was the first woman to hold it. She submitted her resignation on Thursday night. According to the president's announcement, she's moving to his political operation.",
                            "A: Wiles had held the post since the start of this term."),
          "C-07 fires on a passage under the floor")
    check("C-07" in planted(raw, "B: Today: Stephen Miller takes", "A: Today: Stephen Miller takes"),
          "C-07 fires when B does not read the lineup")
    check("C-08" in planted(raw, "Police shot and arrested him.",
                            "Police shot and arrested him after a chase through the square that witnesses described at length, "
                            "past the cloth hall and the church, while the market traders ran for cover and the city's ambulances "
                            "and a medical helicopter arrived over the old town."),
          "C-08 fires on a desk item over the word cap")
    check("C-08" in planted(raw, f"A: {DESK_LEAD}", "A: Also on the desk."), "C-08 fires when the desk opens on another line")
    check("C-11" in planted(raw, "Schumer states he has sufficient votes within his caucus to retain his leadership position.",
                            "Schumer states he will resign before the new Congress meets."),
          "C-11 fires on an attributed claim the story does not carry")
    check("C-12" in planted(raw, "Police shot and arrested him.", "The Constitution protects the square."),
          "C-12 fires on a court or a law in Void's own voice")
    check("C-14" in planted(raw, "A: This is Void Opinion. Through a progressive lens today.", "A: This is Void Opinion."),
          "C-14 fires when the Opinion's introduction drops its lens")
    check("C-14" in planted(raw, "A: This is Void Opinion. Through a progressive lens today.", "A: Now, the Opinion. Through a progressive lens today."),
          "C-14 fires when the Opinion's introduction does not name Void Opinion")
    check("C-14" in planted(raw, "A: We think the question is not", "B: We think the question is not"),
          "C-14 fires when B reads a passage of the Opinion")
    check("C-00" in planted(raw, "A: We think the question is not", "B: We think the question is not"),
          "C-00 fires when B speaks in the Opinion")
    check("C-14" in planted(raw, "A: A chief of staff decides who reaches the president. On Monday, the person most identified with the policy a majority of voters rejected will hold that door. The Congress that meets him in January is one his party no longer controls. That is the check the structure left standing.",
                            "A: A chief of staff decides who reaches the president."),
          "C-14 fires on an Opinion passage under the floor")
    check("C-00" in planted(raw, "\nB: That record runs", "\nC: That record runs"), "a C line in the news fails (two voices)")
    check("C-00" in planted(raw, "A: We think the question is not", "C: We think the question is not"), "a C line in the Opinion fails (two voices)")
    check("C-00" in planted(raw, "A: The rest of the desk.\nA: In Krakow", "A: The rest of the desk.\nC: In Krakow"), "a C line on the desk fails (two voices)")
    # C-09 counts the news only: the Opinion is all A's and must not push A over the share
    bulk = parse_show(raw)
    bind_ranks(bulk, ctx())
    news, every = bulk.words_by_speaker(), bulk.words_by_speaker(news_only=False)
    check("C-09" not in fail_ids(validate_show(bulk, ctx())) and
          every["A"] / sum(every.values()) > news["A"] / sum(news.values()),
          "C-09 measures the news segments only, so the Opinion read by A does not count against the share")
    # C-09: hand every B line to A
    show = parse_show(raw.replace("\nB: ", "\nA: "))
    bind_ranks(show, ctx())
    check("C-09" in fail_ids(validate_show(show, ctx())), "C-09 fires when one voice carries the show")
    # a passage the story does not carry is cut, and the handover survives
    wiles = ("A: Wiles had held the post since the start of this term, and she was the first woman to hold it. "
             "She submitted her resignation on Thursday night. According to the president's announcement, she's moving to his political operation.")
    assert wiles in raw
    show = parse_show(raw.replace(wiles, "A: Wiles has taken a post at the United Nations in Geneva, a city of two million."))
    bind_ranks(show, ctx())
    cuts = ground_show(show, ctx())
    lead = show.seg("LEAD")
    texts = " ".join(t.text for t in lead.turns)
    check(bool(cuts) and "Geneva" not in texts, "grounding cuts a passage the story does not carry")
    check(lead.turns[0].speaker == "A" and lead.turns[-1].speaker == "B", "A still leads and B still closes after a cut")
    # the Opinion is read against the Opinion, not the stories
    show = parse_show(raw.replace("The voters answered on Tuesday.", "The voters answered on Tuesday. Nine in ten of them live in Ohio."))
    bind_ranks(show, ctx())
    cuts = ground_show(show, ctx())
    check(any("Ohio" in c.sentence for c in cuts), "a sentence the Opinion does not carry is cut from the anchor's reading")


# ---------------------------------------------------------------- rev 6: memory and the coverage formula
def memory_and_coverage(raw: str) -> None:
    check("C-16" in planted(raw, "A: Kyiv and Moscow describe different targets.",
                            "A: The coverage splits here. Kyiv and Moscow describe different targets."),
          "C-16 fires on 'The coverage splits here'")
    check("C-16" in planted(raw, "B: That record runs across both terms.",
                            "B: The outlets agree on this much. That record runs across both terms."),
          "C-16 fires on 'The outlets agree on this much'")
    check("C-16" in planted(raw, "A: Kyiv and Moscow describe different targets.",
                            "A: Of the twenty-one outlets Void placed on this story, six sit left of centre. Kyiv and Moscow describe different targets."),
          "C-16 fires on the roster line")
    check("C-16" not in planted(raw, "A: Kyiv and Moscow describe different targets.",
                                "A: Kyiv and Moscow describe different targets, and the accounts of the injured differ."),
          "C-16 does not fire on a disagreement said in the story's own words")
    # C-17: the headline read again as the story's first line; the cold open's fact again
    check("C-17" in planted(raw, "A: On Friday, President Donald Trump announced",
                            "A: Stephen Miller takes the chief of staff's office on Monday. On Friday, President Donald Trump announced"),
          "C-17 fires when the story re-reads the TITLE's line")
    check("C-17" in planted(raw, "B: That record runs across both terms.",
                            "B: Three days after the Republican Party lost both chambers of Congress, the White House has a new chief of staff. That record runs across both terms."),
          "C-17 fires on the cold open's sentence said again")
    check("C-17" not in planted(raw, "B: That record runs across both terms.", "B: That record runs across both terms."),
          "the clean fixture says nothing twice")

    # the pass itself
    show = parse_show(raw.replace("B: That record runs across both terms.",
                                  "B: Three days after the Republican Party lost both chambers of Congress, the White House has a new chief of staff. That record runs across both terms."))
    cuts = remove_repeats(show)
    check(len(cuts) == 1 and cuts[0].startswith("Three days after"), f"remove_repeats cuts the repeated sentence and nothing else ({cuts})")
    check(not repeats_in(show), "after the pass nothing is said twice")
    check(any(t.text.startswith("That record runs") for t in show.seg("LEAD").turns), "the passage keeps its new sentences")
    # a paraphrase that adds facts stays
    heard = [content_words("Seven people died in the train collision that occurred Sunday in Giza province south of Cairo.")]
    check(not is_repeat("Seven people died and at least one hundred twenty-five others were injured when two passenger trains "
                        "collided in the al Ayyat district of Giza province.", heard),
          "a sentence that adds to an earlier one is not a repeat")
    check(is_repeat("Seven people died in the train collision on Sunday in Giza province, south of Cairo.", heard),
          "a sentence that adds nothing is a repeat")
    # an Opinion that opens on a recap of the second story: the recap goes, the argument stays
    second_line = "President Donald Trump elevated Stephen Miller to White House chief of staff, replacing Susie Wiles."
    op = Show(segments=[
        Segment("SECOND", turns=[Turn("B", second_line + " Richard Walters resigned as deputy the same day.")]),
        Segment("OPINION", turns=[Turn("A", "This is Void Opinion. Through a pragmatic lens today. Continuity matters."),
                                  Turn("A", second_line + " Richard Walters resigned as deputy the same day."),
                                  Turn("A", "Institutional memory resets when a chief of staff and a decade-long deputy leave "
                                            "together, and the machinery of government slows while it is rebuilt.")]),
        Segment("CLOSE", turns=[Turn("A", f"{CLOSE_PREFIX} {second_line} {CLOSE_TAG}")])])
    remove_repeats(op)
    o = op.seg("OPINION")
    check(o is not None and len(o.turns) == 2 and o.turns[1].text.startswith("Institutional memory"),
          f"the Opinion's recap of the news is left out of the spoken Opinion, its argument kept ({[t.text[:30] for t in (o.turns if o else [])]})")
    check(op.seg("CLOSE").turns[0].text == f"{CLOSE_PREFIX} {CLOSE_TAG}", "the close keeps Void's lines when its middle was already said")
    # the template reads a disagreement only when it is over a fact
    row = {"divergence_points": ["Sources differ on the total number of injured, citing figures from 64 up to at least 125.",
                                 "Some outlets focus on the personnel shifts, while others emphasise the political reaction."]}
    div = material_divergence(row, 2)
    check(div.startswith("Sources differ on the total number") and "personnel shifts" not in div,
          f"material_divergence keeps the disputed count and drops the difference of emphasis ({div!r})")

# ---------------------------------------------------------------- template and prompt
def template_and_prompt() -> None:
    show = template_show(stories(), DATE)
    bind_ranks(show, ctx_no_op())
    rep = validate_show(show, ctx_no_op())
    check([s.kind for s in show.segments] == ["COLD", "TITLE", "LEAD", "SECOND", "DESK", "CLOSE"],
          "the template edition carries every segment")
    check(not any(f.id in ("C-01", "C-02", "C-04", "C-05", "C-08", "C-09", "C-11", "C-12") for f in rep.failures),
          f"the template edition breaks no line rule ({[f.id for f in rep.failures]})")
    cuts = ground_show(show, ctx_no_op())
    check(not cuts, f"the template edition is grounded by construction ({[c.sentence[:50] for c in cuts]})")
    lead = show.seg("LEAD")
    check(lead is not None and not any("Of the" in t.text or COVERAGE_FORMULA_RE.search(t.text) for t in lead.turns),
          "rev 6: the template reads no coverage line and no coverage formula")
    check(lead is not None and lead.turns[0].speaker == "A" and lead.turns[-1].speaker == "B" and not any(t.is_question for t in lead.turns),
          "the template lead is A's passages, B takes the last, no questions")
    title = show.seg("TITLE")
    check(lead is not None and title is not None and not lead.turns[0].text.startswith(stories()[0]["title"].rstrip(".")),
          "rev 6: the template's story starts past its headline, which the TITLE has just read")
    check(not repeats_in(show), f"rev 6: the template edition says nothing twice ({repeats_in(show)[:2]})")
    cov = coverage_line(stories()[0])
    check(cov == "Of the sixty outlets Void placed on this story, twenty-four sit left of centre, twenty at the centre and sixteen right of it.",
          f"coverage line is one vote per outlet, in words ({cov!r})")
    check(coverage_line({"bias_diversity": {"lean_buckets": {"center": 2}}}) is None, "a thin roster gives no coverage line")

    system, user = build_prompt(stories(), spoken_date(DATE))
    check(f"{SIGN_ON} It's {spoken_date(DATE)}." in user, "the prompt carries the sign-on and the day")
    check(CLOSE_PREFIX in user and CLOSE_TAG in user and DESK_LEAD in user, "the prompt carries Void's lines")
    check(f"{WORD_BUDGETS['LEAD'][0]}-{WORD_BUDGETS['LEAD'][1]} words" in user, "the prompt's budgets are the validator's")
    check("No questions between the anchors" in user and "asks" not in system.split("Nobody interviews anybody")[0], "the prompt asks for a newsroom, not an interview")
    check("<source id=" in user, "every story is wrapped as data")
    check("Coverage:" not in user and "Divergence:" not in user, "rev 6: the prompt no longer hands the model a coverage line to read")
    check("Never narrate where the outlets agree" in system and "hears the episode once" in system,
          "rev 6: the prompt tells the model the listener remembers, and to skip the coverage formula")

    # the Opinion read whole: template, prompt, validators
    op_text = ("The argument has two parts. The first part says the Senate changed hands in January. "
               "The second part says any vacancy on the court will meet a Democratic majority. "
               "The conclusion is that the two justices face a different calendar than they did a week ago. "
               "A calendar is not a verdict. It is the set of days on which a decision can still be made by the people who hold it now.\n\n"
               "Consider what the Senate does with a vacancy. It holds hearings, it takes a vote, and it does both on its own schedule. "
               "For two years that schedule is written by the party that won on Tuesday. The justices who might have retired this spring "
               "know that as well as anyone in the building. We think the quiet in their chambers is the sound of that arithmetic being done.\n\n"
               "None of this is a prediction. The court decides its own cases and the justices decide their own retirements. "
               "What changed is only who waits on the other side of the decision, and for how long they are willing to wait.")
    show = template_show(stories(), DATE, opinion_text=op_text, opinion_headline="Two Justices and a Senate", opinion_lean="center")
    octx = Context(top=stories(), date_spoken=spoken_date(DATE), opinion_text=op_text,
                   opinion_headline="Two Justices and a Senate", opinion_lean="center")
    bind_ranks(show, octx)
    rep = validate_show(show, octx)
    op = show.seg("OPINION")
    check(op is not None and len(op.turns) >= 3 and all(t.speaker == "A" for t in op.turns),
          "the template Opinion is A introducing and A reading")
    check(op is not None and op.turns[0].text.startswith(f"{OPINION_OPEN} Through a pragmatic lens today."),
          "the template Opinion opens on Void's line and names its lens")
    check(not rep.failures, f"the template Opinion passes ({[f.id + ' ' + f.detail[:40] for f in rep.failures]})")
    cuts = ground_show(show, octx)
    check(not cuts, "the Opinion's lines are grounded in the Opinion text by construction")
    system, user = build_prompt(stories(), spoken_date(DATE), opinion_text=op_text, opinion_headline="Two Justices and a Senate",
                                opinion_lean="left")
    check("C:" not in user and "two voices" in user, "the prompt asks for two voices and never offers a C line")
    check(f"A: {OPINION_OPEN} Through a progressive lens today." in user, "the prompt's Opinion opens on Void Opinion")
    check("## OPINION" in user and "Through a progressive lens today." in user and "<source id=\"opinion\"" in user,
          "the prompt carries the Opinion block, its lens and the text as data")
    no_op = validate_show(parse_show(without_opinion(FIXTURE.read_text(encoding="utf-8"))), ctx())
    check(any(f.id == "C-00" and f.segment == "OPINION" for f in no_op.failures),
          "an edition with an Opinion whose script carries none fails")
    with_op = parse_show(FIXTURE.read_text(encoding="utf-8"))
    bind_ranks(with_op, ctx_no_op())
    check(any(f.id == "C-00" and f.segment == "OPINION" for f in validate_show(with_op, ctx_no_op()).failures),
          "an Opinion segment on a day with no written opinion fails")

    # generation: a model that answers garbage, then the template
    op_kw = dict(opinion_text=OPINION.read_text(encoding="utf-8"), opinion_headline=OP_HEAD, opinion_lean=OP_LEAN)
    show, rep, label = generate_show(stories(), date=DATE, generate_fn=lambda s, u: "nonsense", **op_kw)
    check(show is not None and label == "template-after-gemini", f"a failed model falls to the template ({label})")
    show, rep, label = generate_show(stories(), date=DATE, generate_fn=lambda s, u: FIXTURE.read_text(encoding="utf-8"), **op_kw)
    check(show is not None and label == "gemini" and show.grounded is True, f"the fixture is accepted as the model's ({label})")
    # a script with one repairable defect is repaired, not lost
    raw = FIXTURE.read_text(encoding="utf-8").replace("pledged loyalty to the president.", 'pledged "loyalty" to the president.')
    show, rep, label = generate_show(stories(), date=DATE, generate_fn=lambda s, u: raw, max_attempts=1, **op_kw)
    check(show is not None and label == "gemini", "quotation marks alone are stripped rather than costing the show")


# ---------------------------------------------------------------- the score
def score() -> None:
    v = S.voicing_for("onair:world:2026-11-07")
    v2 = S.voicing_for("onair:world:2026-11-08")
    check(v.seed != v2.seed, "two days get two voicings")
    theme, _ = S.level_featured(S.render_theme(v))
    check(not S.check_cue(theme, "featured"), f"the theme meets the featured standard ({[f.id for f in S.check_cue(theme, 'featured')]})")
    peak = None
    beds: dict[str, np.ndarray] = {}
    for seg, dur in (("lead", 40.0), ("desk", 30.0), ("opinion", 30.0)):
        bed, _ = S.level_bed(S.render_bed(v, seg, dur))
        beds[seg] = bed
        f = S.check_cue(bed, "bed")
        check(not f, f"the {seg} bed meets the bed standard ({[x.id for x in f]})")
        check(abs(S.lufs_integrated(bed) - S.BED_LUFS) < 0.6, f"the {seg} bed sits at {S.BED_LUFS} LUFS ({S.lufs_integrated(bed):.1f})")
        check(S.band_share(bed, 5000.0, None, 100.0) <= S.MUSIC_TREBLE_MAX_SHARE, f"the {seg} bed carries almost no treble")
        peak = S.bed_peak_lufs(bed)
    interludes = []
    for i in range(2):
        il, _ = S.level_interlude(S.render_interlude(v, i))
        f = S.check_cue(il, "interlude")
        check(not f, f"interlude {i} meets the interlude standard ({[x.id for x in f]})")
        interludes.append(il)
    outro, _ = S.level_featured(S.render_outro(v))
    check(not S.check_cue(outro, "featured"), f"the outro meets the featured standard ({[f.id for f in S.check_cue(outro, 'featured')]})")
    check(float(np.max(np.abs(outro[-S.SR // 2:]))) < 1e-3, "the outro falls to silence")
    stop = score_rev5(v, beds, theme, interludes)
    score_rev5c(v, beds, theme, outro, interludes, stop)
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


def score_rev5(v, beds: dict, theme: np.ndarray, interludes: list) -> np.ndarray:
    """Rev 5 (2026-11-08): the firewall between the news and the Opinion is the
    music, so each of its three parts is measured. (1) The Opinion's bed is
    the same show in another room: fewer clock onsets a second than any news
    bed (one soft kick a bar against a shaker on two off-beats) and a pitch-class
    profile further from the news beds' than they are from each other. (2) The
    desk bed STOPS: a hit STOP_RING_S before its end, the ring gone to the
    floor by the end, nothing after it. (3) The entrance is its own cue: it
    swells from silence rather than hitting, carries no clock, and its
    third-octave spectrum is apart from the theme's and the interludes'. Each
    also still meets the standard it is held to. Returns the stopped desk bed
    (rendered with two breaths) for the rev 5c checks."""
    op, news = beds["opinion"], {k: beds[k] for k in ("lead", "desk")}
    op_clock, news_clock = S.clock_density(op), {k: S.clock_density(x) for k, x in news.items()}
    check(min(news_clock.values()) >= 0.4 and op_clock <= 0.6 * min(news_clock.values()),
          f"the news beds carry a soft clock and the opinion bed under 60% of it ({op_clock:.2f}/s vs {min(news_clock.values()):.2f}/s)")
    centre = np.mean([S.chroma_profile(x) for x in news.values()], axis=0)
    centre /= np.linalg.norm(centre)
    op_cos = float(S.chroma_profile(op) @ centre)
    news_cos = min(float(S.chroma_profile(x) @ centre) for x in news.values())
    check(op_cos < news_cos - 0.03, f"the opinion bed's pitch profile sits apart from the news beds' ({op_cos:.3f} vs {news_cos:.3f})")
    check(S.M.PROGRESSIONS["opinion"] and all("Dm" not in p and "D" not in p for p in S.M.PROGRESSIONS["opinion"]),
          "the Opinion never lands on the tonic chord")
    # the stop (rendered with two desk breaths, rev 5c, which must not disturb it)
    stop, _ = S.level_bed(S.render_bed(v, "desk", 25.0, ending="stop", accents=(8.0, 14.0)))
    check(not S.check_cue(stop, "bed"), f"a stopped desk bed still meets the bed standard ({[f.id for f in S.check_cue(stop, 'bed')]})")
    mom = S.lufs_momentary(stop)
    hit = int((len(stop) / S.SR - S.STOP_RING_S - 0.1) / 0.1)
    check(float(mom[hit]) >= float(np.max(mom)) - 3.0, f"the stop is a hit, within 3 dB of the bed's loudest moment ({mom[hit]:.1f} vs {np.max(mom):.1f})")
    check(float(mom[min(len(mom) - 1, hit + 15)]) <= float(mom[hit]) - 5.0, "the ring is 5 dB down 1.5 s after the hit")
    check(float(mom[-1]) <= float(np.max(mom)) - 30.0, f"the stopped bed ends at the floor ({mom[-1]:.1f} LUFS momentary)")
    tail = stop[-int(0.4 * S.SR):]
    check(20 * np.log10(float(np.sqrt(np.mean(tail ** 2))) + 1e-12) < -55.0, "nothing plays after the ring")
    # the entrance
    en, _ = S.level_featured(S.render_entrance(v))
    check(not S.check_cue(en, "featured"), f"the entrance meets the featured standard ({[f.id for f in S.check_cue(en, 'featured')]})")
    check(abs(len(en) / S.SR - S.ENTRANCE_S) < 0.01 and 8.0 <= S.ENTRANCE_S <= 12.0, f"the entrance is {S.ENTRANCE_S} s, a section break")
    check(S.M.BAR + 9.0 * S.M.BEAT <= S.ENTRANCE_VOICE_S < S.ENTRANCE_S,
          f"the anchor speaks after the hook's last note has landed and before the cue ends ({S.ENTRANCE_VOICE_S} s)")
    emom = S.lufs_momentary(en)
    check(float(np.max(emom[:7])) <= float(np.max(emom)) - 6.0, "the entrance swells from silence; it does not hit")
    check(S.clock_density(theme) >= 0.3 and S.clock_density(en) <= 0.5 * S.clock_density(theme),
          f"the entrance carries no clock ({S.clock_density(en):.2f}/s vs the theme's {S.clock_density(theme):.2f}/s)")
    # Rev 5c widened the spectral bound from 0.85 to 0.9: the calm theme now
    # shares the entrance's warmth (both pad and bass, nothing bright), so the
    # cosine sits near 0.84; what keeps the entrance apart is measured above
    # and below (no clock against the theme's, the swell, the harmony).
    to_theme = float(S._third_octave(S.mono(en)) @ S._third_octave(S.mono(theme)))
    to_il = max(float(S._third_octave(S.mono(en)) @ S._third_octave(S.mono(x))) for x in interludes)
    check(to_theme <= 0.9 and to_il <= 0.92, f"the entrance's spectrum is its own (cos to theme {to_theme:.2f}, to the interludes {to_il:.2f})")
    for i, il in enumerate(interludes):
        mom = S.lufs_momentary(il)
        check(float(np.max(mom[:7])) >= float(np.max(mom)) - 3.0, f"interlude {i} arrives on its downbeat; it does not swell like the entrance")
    # the bass: the beds keep most of their energy under 120 Hz and the low-mids stay cut
    for seg, x in beds.items():
        check(S.band_share(x, 40.0, 120.0) >= 0.75 and S.band_share(x, 150.0, 400.0, 100.0) <= S.BED_LOWMID_MAX_SHARE,
              f"the {seg} bed's weight is in the bass ({S.band_share(x, 40.0, 120.0):.0%} in 40-120 Hz, {S.band_share(x, 150.0, 400.0, 100.0):.1%} in 150-400)")
    return stop


def _tick(amp: float, open_: bool = False) -> np.ndarray:
    """Rev 5's tick, kept here only to plant it: noise in 2.5 to 5 kHz with a
    2 ms rise and a 20 ms fall (60 open)."""
    from scipy import signal as sg
    n = int(0.14 * S.SR)
    t = np.arange(n) / S.SR
    x = np.random.default_rng(7).normal(0, 1, n) * np.minimum(1.0, t / 0.002) * np.exp(-t / (0.06 if open_ else 0.02))
    x = sg.sosfilt(sg.butter(4, [2500.0, 5000.0], btype="band", fs=S.SR, output="sos"), x)
    return x / np.max(np.abs(x)) * amp


def score_rev5c(v, beds: dict, theme: np.ndarray, outro: np.ndarray, interludes: list, stop: np.ndarray) -> None:
    """Rev 5c (2026-11-08, CEO: "cool calming beats and tunes between stories;
    ensure the score is also soothing"). (1) The interlude: three bars at its
    own level, never as loud as the title, never silent; two in one episode
    share no melody, chord pair or voice, and their pitch profiles differ.
    (2) Calm, in numbers, on every cue: clock onsets a second under the
    ceiling (rev 5's lead, second and desk beds carried 1.0 to 1.3 on this
    meter, its close 0.8, the theme 1.1) and the glare band over 3 kHz under
    its share (rev 5's beds 0.45 to 1.4 %); the interlude is calmer than any
    rev 5 bed on both. (3) The desk's
    breath: a bell tag lands where the producer says the desk pauses, the
    ostinato rests through it, and nothing else in the bed moves (the same
    seed with and without breaths differs only there). Planted: a loud and a
    silent interlude; rev 5's tick train on a calm bed (caught on the clock
    and the glare), bright open hats on two off-beats (the clock passes, the
    glare catches it)."""
    M = S.M
    check(S.BED_LUFS < S.INTERLUDE_LUFS < S.FEATURED_LUFS, f"the interlude level sits between a bed and a featured cue ({S.INTERLUDE_LUFS})")
    check(abs(S.INTERLUDE_S - 3 * M.BAR) < 0.06 and 6.0 <= S.INTERLUDE_S <= 11.5, f"the interlude is three bars ({S.INTERLUDE_S} s)")
    check(2 * M.BAR <= S.INTERLUDE_VOICE_S < S.INTERLUDE_S, f"the next anchor speaks over the release bar ({S.INTERLUDE_VOICE_S} s in)")
    for i, il in enumerate(interludes):
        st = S.lufs_shortterm(il)
        check(abs(len(il) / S.SR - S.INTERLUDE_S) < 0.01 and abs(float(np.max(st)) - S.INTERLUDE_LUFS) < 0.1,
              f"interlude {i} is {len(il) / S.SR:.1f} s with its loudest 3 s at {float(np.max(st)):.1f} LUFS")
        check(S.lufs_integrated(il) >= S.INTERLUDE_LUFS - S.INTERLUDE_FLOOR_DB, f"interlude {i} is heard ({S.lufs_integrated(il):.1f} LUFS integrated)")
    plans = [M.interlude_plan(v.music, i) for i in range(2)]
    check(plans[0][0] is not plans[1][0] and plans[0][1] != plans[1][1] and plans[0][2] != plans[1][2],
          f"two interludes in one episode share no melody, chord pair or voice ({plans[0][1:]} vs {plans[1][1:]})")
    cos = float(S.chroma_profile(interludes[0]) @ S.chroma_profile(interludes[1]))
    check(cos < 0.9, f"the two interludes differ in what they play (chroma cosine {cos:.2f})")
    check(any(f.id == "interlude-level" for f in S.check_cue(interludes[0] * 10 ** (4.0 / 20), "interlude")), "an interlude 4 dB over its ceiling is caught")
    check(any(f.id == "interlude-silent" for f in S.check_cue(interludes[0] * 10 ** (-10.0 / 20), "interlude")), "an interlude 10 dB under its level is caught")
    # calm
    for name, x, role in [("theme", theme, "featured"), ("outro", outro, "featured"), *((k, b, "bed") for k, b in beds.items()),
                          *((f"interlude {i}", il, "interlude") for i, il in enumerate(interludes))]:
        clock_max = S.CALM_CLOCK_MAX_FEATURED if role == "featured" else S.CALM_CLOCK_MAX
        check(S.clock_density(x) <= clock_max and S.glare_share(x) <= S.CALM_GLARE_MAX_SHARE[role],
              f"{name} is calm: {S.clock_density(x):.2f} clock onsets/s (at most {clock_max}), {S.glare_share(x):.2%} over 3 kHz "
              f"(at most {S.CALM_GLARE_MAX_SHARE[role]:.1%}; rev 5's lead, second and desk beds 1.0-1.3/s, its beds 0.45-1.4 %)")
    for i, il in enumerate(interludes):
        check(S.clock_density(il) < 0.83 and S.glare_share(il) < 0.0045,
              f"interlude {i} is calmer than any rev 5 bed ({S.clock_density(il):.2f}/s against rev 5's quietest 0.83; "
              f"{S.glare_share(il):.2%} against its lowest 0.45 %)")
    check(S.CALM_CLOCK_MAX < 1.04 and S.CALM_GLARE_MAX_SHARE["bed"] < 0.0067,
          "the calm ceilings sit under what rev 5's lead, second and desk beds measured, so rev 5 could not pass them")
    # planted: a rev 5 tick train on every off-beat, and bright open hats on two
    raw = S.render_bed(v, "lead", 20.0)
    ticks = raw.copy()
    for k in range(int(20.0 / M.BEAT)):
        S.place(ticks, _tick(0.12), (k + 0.5) * M.BEAT)
    ids = {f.id for f in S.check_cue(S.level_bed(ticks)[0], "bed")}
    check("calm-clock" in ids and "calm-glare" in ids, f"rev 5's tick train on a calm bed is caught on the clock and the glare ({sorted(ids)})")
    hats = raw.copy()
    for k in range(int(20.0 / M.BAR)):
        for b in (1.5, 3.5):
            S.place(hats, _tick(0.2, open_=True), k * M.BAR + b * M.BEAT)
    ids = {f.id for f in S.check_cue(S.level_bed(hats)[0], "bed")}
    check("calm-glare" in ids and "calm-clock" not in ids, f"bright hats on two off-beats pass the clock count and are caught on the glare ({sorted(ids)})")
    check(not {f.id for f in S.check_cue(S.level_bed(raw)[0], "bed")} & {"calm-clock", "calm-glare"}, "the same bed without them is calm")
    # the desk's breath: the same bed with and without its breaths (the breath
    # draws nothing from the day's generator, so every other note is the same)
    # differs only where the breaths are, and there by a bell's worth
    va, vb = S.voicing_for("onair:world:2026-11-07"), S.voicing_for("onair:world:2026-11-07")
    acc = (8.0, 14.0)
    with_, without = S.render_bed(va, "desk", 25.0, ending="stop", accents=acc), S.render_bed(vb, "desk", 25.0, ending="stop")
    diff = S.mono(with_ - without)
    n = int(1.5 * S.SR)
    k = len(diff) // n
    med = float(np.median(np.mean(diff[: k * n].reshape(k, n) ** 2, axis=1)))
    at_acc = [float(np.mean(diff[int(t * S.SR): int(t * S.SR) + n] ** 2)) for t in acc]
    check(all(e >= 8.0 * (med + 1e-18) for e in at_acc) and float(np.max(np.abs(diff))) > 0.02,
          f"the breaths are where the bed with them differs from the bed without ({[round(e / (med + 1e-18)) for e in at_acc]}x the median window)")
    quiet = [float(np.mean(diff[int(t * S.SR): int(t * S.SR) + n] ** 2)) for t in (2.0, 11.0, 19.0)]
    check(all(q <= 0.15 * min(at_acc) for q in quiet), "away from the breaths the two renders agree (the breath touches nothing else)")
    late = S.render_bed(v, "desk", 12.0, ending="stop", accents=(11.0,))
    tail = late[-int(S.STOP_RING_S * S.SR) + int(0.4 * S.SR):]
    check(20 * np.log10(float(np.sqrt(np.mean(tail ** 2))) + 1e-12) < -20.0, "a breath that would fall after the stop's hit is not played")


# ---------------------------------------------------------------- timeline and chapters
def timeline() -> None:
    from briefing.onair_producer import build_cues, build_timeline, chapters_from_timeline, ShowResult, bed_ending, GAPS
    raw = FIXTURE.read_text(encoding="utf-8")
    v = S.voicing_for("onair:world:2026-11-07")
    show = parse_show(raw)
    bind_ranks(show, ctx())
    cues = build_cues(show, None)
    check([c.role for c in cues if c.kind == "OPINION"] == ["A"] * 4 and {c.role for c in cues} == {"A", "B"},
          "the Opinion's cues are all A's; the show has two voices")
    lead_cues = [c for c in cues if c.kind == "LEAD"]
    check([c.exchange for c in lead_cues] == list(range(len(lead_cues))), "a cue's exchange is its passage index")
    lengths = {c.idx: 0.4 * len(c.text.split()) for c in cues}
    tl = build_timeline(cues, lengths, v)
    check(all(tl.cues[i].end <= tl.cues[i + 1].start for i in range(len(tl.cues) - 1)), "no two lines overlap")
    check(tl.news_start > 0 and tl.opinion_start is not None and tl.opinion_start > tl.news_start, "news and opinion marks")
    check(tl.outro_at < tl.last_word < tl.total, "the outro starts before the last word ends and the file outlives it")
    names = [m.name for m in tl.music]
    check(names.count("theme") == 1 and names.count("interlude") == 2 and names.count("entrance") == 1 and names.count("outro") == 1,
          f"one theme, two interludes, one entrance, one outro ({names})")
    check(names.count("lead") >= 2, "the lead bed leaves and comes back")
    beds = [m for m in tl.music if m.role == "bed"]
    check(all(m.end - m.start >= 4.5 for m in beds), "every bed is long enough to be judged")
    timeline_rev5(tl, bed_ending, GAPS)
    timeline_rev5c(tl, bed_ending, GAPS)
    ch = chapters_from_timeline(tl, opinion_headline="An argument", permalinks={stories()[0]["id"]: "/story/x/"})
    kinds = [c["kind"] for c in ch]
    check(kinds == ["headlines", "story", "story", "briefs", "opinion"], f"chapter kinds ({kinds})")
    check(ch[0]["startTime"] == 0.0 and all(ch[i]["startTime"] < ch[i + 1]["startTime"] for i in range(len(ch) - 1)),
          "chapters start at zero and rise")
    check(ch[1].get("rank") == 1 and ch[1].get("url") == "/story/x/" and ch[2].get("rank") == 2, "story chapters carry rank and link")
    ils = [m for m in tl.music if m.name == "interlude"]
    check(ch[2]["startTime"] == round(ils[0].start, 3) and ch[3]["startTime"] == round(ils[1].start, 3),
          "the second story's and the desk's chapters start at the interlude before them")
    check(ch[1]["startTime"] == round(tl.news_start, 3), "the lead's chapter starts at its first word (no interlude before it)")
    check(ch[4]["startTime"] == round(tl.opinion_start, 3) and ch[4].get("subtitle") == "An argument",
          "the Opinion chapter starts at its entrance music")
    check(all(ch[i]["endTime"] == ch[i + 1]["startTime"] for i in range(len(ch) - 1)) and ch[-1]["endTime"] == round(tl.total, 3),
          "chapters tile the file")
    r = ShowResult(audio_url="x", duration_seconds=1.0, file_size=1, news_start_seconds=1.0, opinion_start_seconds=None,
                   chapters=[], engine="kokoro", voices="kokoro:a+b")
    check(r.as_row_fields()["audio_voice_label"] == "Two voices", "no Opinion, two voices on the label")
    r.opinion_start_seconds = 5.0
    check(r.as_row_fields()["audio_voice_label"] == "Two voices", "an Opinion, still two voices on the label (rev 5)")
    # without an opinion, no entrance and no opinion chapter
    show = parse_show(without_opinion(raw))
    bind_ranks(show, ctx_no_op())
    cues = build_cues(show, None)
    tl = build_timeline(cues, {c.idx: 0.4 * len(c.text.split()) for c in cues}, v)
    check("entrance" not in [m.name for m in tl.music] and tl.opinion_start is None, "no opinion, no entrance")
    desk_bed = [m for m in tl.music if m.name == "desk"][-1]
    check(bed_ending(tl, desk_bed)[0] == "out", "no opinion, the desk bed goes out rather than stopping")


def timeline_rev5(tl, bed_ending, GAPS: dict) -> None:
    """The move into the Opinion, in the timeline (rev 5): the desk bed ends
    on its stop (the hit `desk_to_stop` after the desk's last word, the ring
    STOP_RING_S after that), the floor is held with no music for
    `stop_to_entrance`, the entrance starts there (and that is where the
    Opinion chapter starts), the anchor speaks at ENTRANCE_VOICE_S into it,
    and the Opinion's bed enters under the voice, never before it."""
    desk = [c for c in tl.cues if c.kind == "DESK"]
    op = [c for c in tl.cues if c.kind == "OPINION"]
    en = next(m for m in tl.music if m.name == "entrance")
    desk_bed = [m for m in tl.music if m.name == "desk"][-1]
    ending, into = bed_ending(tl, desk_bed)
    check(ending == "stop" and into is en, f"the desk bed stops before the entrance; it does not rise ({ending})")
    check(abs(desk_bed.end - (desk[-1].end + GAPS["desk_to_stop"] + S.STOP_RING_S)) < 0.01,
          "the desk bed ends once its stop has rung out after the desk's last word")
    check(abs(en.start - desk_bed.end - GAPS["stop_to_entrance"]) < 0.01 and GAPS["stop_to_entrance"] >= 1.5,
          f"the floor is held {GAPS['stop_to_entrance']} s between the stop and the entrance")
    check(not any(m is not en and m.start < en.start and m.end > desk_bed.end for m in tl.music),
          "no music plays in the held silence")
    check(not any(c.start < en.start and c.end > desk_bed.end for c in tl.cues), "nobody speaks in the held silence")
    check(tl.opinion_start == en.start, "the Opinion chapter starts where the entrance does")
    check(abs(op[0].start - (en.start + S.ENTRANCE_VOICE_S)) < 0.01 and op[0].start < en.end,
          "the anchor's introduction lands on the entrance's last bar")
    op_bed = [m for m in tl.music if m.name == "opinion"][0]
    check(op[0].start <= op_bed.start < en.end, "the Opinion's bed enters under the anchor's introduction, not before it")
    lead_tail = [m for m in tl.music if m.name == "lead"][-1]
    close_bed = [m for m in tl.music if m.name == "close"][-1]
    check(bed_ending(tl, lead_tail)[0] == "rise" and bed_ending(tl, close_bed)[0] == "rise",
          "the lead's coverage bed still rises into the interlude and the close into the outro")


def timeline_rev5c(tl, bed_ending, GAPS: dict) -> None:
    """Rev 5c in the timeline. The interludes: one after the lead's last word
    and one after the second's, each `story_to_interlude` after the word, the
    next anchor speaking INTERLUDE_VOICE_S in (over the release bar), nobody
    speaking before that, the next bed fading in under the release, the bed
    before each rising into it. The desk: after every second item (never the
    last) the gap is `desk_breath`, long enough for the duck to come fully up;
    the other gaps are `desk_items` and keep the duck down, so the desk moves;
    the desk bed carries an accent DESK_BREATH_TAG_S into each breath."""
    from briefing.onair_producer import DESK_BREATH_TAG_S, desk_breath_after
    lead = [c for c in tl.cues if c.kind == "LEAD"]
    second = [c for c in tl.cues if c.kind == "SECOND"]
    desk = [c for c in tl.cues if c.kind == "DESK"]
    ils = [m for m in tl.music if m.name == "interlude"]
    check(len(ils) == 2 and all(m.role == "interlude" for m in ils), "two interludes, each in the interlude role")
    for il, before, after in ((ils[0], lead[-1], second[0]), (ils[1], second[-1], desk[0])):
        check(abs(il.start - (before.end + GAPS["story_to_interlude"])) < 0.01 and abs(il.end - il.start - S.INTERLUDE_S) < 0.01,
              f"the interlude follows the story's last word by {GAPS['story_to_interlude']} s and runs {S.INTERLUDE_S} s")
        check(abs(after.start - (il.start + S.INTERLUDE_VOICE_S)) < 0.01 and abs(after.start - (il.end - GAPS["interlude_to_story"])) < 0.01,
              f"the next anchor starts {S.INTERLUDE_VOICE_S} s into the interlude, over its release")
        check(not any(c.start < il.start + S.INTERLUDE_VOICE_S - 0.01 and c.end > il.start for c in tl.cues),
              "nobody speaks over the interlude's first two bars")
        nxt = min((m for m in tl.music if m.role == "bed" and m.start > il.start), key=lambda m: m.start)
        check(il.start + 2 * S.M.BAR - 0.01 <= nxt.start < il.end, f"the next bed fades in under the interlude's release ({nxt.name})")
        prev = max((m for m in tl.music if m.role == "bed" and m.start < il.start), key=lambda m: m.end)
        ending, into = bed_ending(tl, prev)
        check(ending == "rise" and into is il, f"the {prev.name} bed rises into the interlude ({ending})")
    # the desk's breaths
    items = [c for c in desk if c.exchange > 0]
    gaps = [(a, b, round(b.start - a.end, 3)) for a, b in zip(items, items[1:])]
    breaths = [(a, b, g) for a, b, g in gaps if desk_breath_after(a)]
    moving = [(a, b, g) for a, b, g in gaps if not desk_breath_after(a)]
    check(len(items) == 8 and len(breaths) == (len(items) - 1) // 2 and [a.exchange for a, _, _ in breaths] == [2, 4, 6],
          f"an eight-item desk breathes after items 2, 4 and 6 ({[a.exchange for a, _, _ in breaths]})")
    check(all(abs(g - GAPS["desk_breath"]) < 0.01 for _, _, g in breaths) and all(abs(g - GAPS["desk_items"]) < 0.01 for _, _, g in moving),
          f"a breath is {GAPS['desk_breath']} s and every other desk gap {GAPS['desk_items']} s")
    check(GAPS["desk_breath"] >= S.DUCK_RELEASE_S + S.DUCK_PREROLL_S + 0.6, "a breath is long enough for the duck to come up and stay up a moment")
    env = S.duck_envelope(tl.total + 1.0, [(c.start, c.end) for c in tl.cues])
    up = [float(env[int((a.end + b.start) / 2 / 0.01)]) for a, b, _ in breaths]
    down = [float(env[int((a.end + b.start) / 2 / 0.01)]) for a, b, _ in moving]
    check(all(u >= -0.5 for u in up), f"the music comes fully up in every breath ({[round(u, 1) for u in up]} dB)")
    check(all(d <= S.DUCK_DB + 0.5 for d in down), f"the duck holds through the desk's other gaps, so the desk moves ({[round(d, 1) for d in down]} dB)")
    desk_bed = [m for m in tl.music if m.name == "desk"][-1]
    want = tuple(round(a.end + DESK_BREATH_TAG_S - desk_bed.start, 3) for a, _, _ in breaths)
    check(desk_bed.accents == want, f"the desk bed carries one accent per breath, {DESK_BREATH_TAG_S} s after the item's last word ({desk_bed.accents})")
    check(all(a.end < desk_bed.start + t < b.start for (a, b, _), t in zip(breaths, desk_bed.accents)), "every accent falls inside its breath")
    # what it costs: the interludes and the breaths against rev 5's page-turns and plain gaps
    added = 2 * (S.INTERLUDE_VOICE_S - 3.25) + len(breaths) * (GAPS["desk_breath"] - GAPS["desk_items"])
    check(0 < added < 20.0, f"rev 5c adds about {added:.1f} s to an eight-item episode (two interludes, three breaths)")


def main() -> int:
    print("--- the clean fixture ---")
    raw = clean_fixture()
    print("--- planted defects ---")
    planted_defects(raw)
    print("--- rev 6: the listener's memory, no coverage formula ---")
    memory_and_coverage(raw)
    print("--- the template edition and the prompt ---")
    template_and_prompt()
    print("--- the score ---")
    score()
    print("--- the timeline ---")
    timeline()
    # 2026-11-08: room_tone(n / SR) came back one sample short of n and the
    # mix's broadcast killed a render after synthesis. Every caller passes n / SR.
    for n in (33408283, 30000001, 48000 * 695 + 1, 7):
        check(len(S.room_tone(n / S.SR, seed=1)) == n, f"room_tone(n / SR) is n samples long (n={n})")
    if failures:
        print(f"\n{len(failures)} FAILED")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
