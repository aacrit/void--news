"""The Argument, rev 2 (2026-11-08): the weekly audio edition's script format,
parser, validators and grounding pass.

On Air is what happened today. History is what it meant then. THE WEEKLY IS
WHAT WE ARGUED ABOUT, AND WHAT THE ARGUMENT LOOKED LIKE FROM OUTSIDE.

Rev 2 is the CEO's ask of 2026-11-08: a show that feels like On Air's family
and is completely a weekly, with more drama and one more anchor. Three voices:

    H  the host, Void's voice (af_aoede, the voice that anchors On Air and
       reads Void Opinion there): the cold open, the sign-on, the week in one
       image, the contents, the datelines, the topic, the turn, the numbers,
       the editorial and the close.
    A  B  two correspondents (am_puck and bf_emma). They carry the two
       features in passages the way On Air's anchors trade a story (A leads
       the cover, B leads the second feature; no interviewing), read the week
       in brief in turns, AND read the two columns of the argument: A the
       left column, B the right. Which VOICE is A and which is B is drawn per
       issue from the week (`cast_for_week`), so no voice owns a side.

    ## COLD | OPEN | CONTENTS | COVER | DATELINE | TOPIC | LEFT | RIGHT | REST | TURN
    ## SECOND | DEPARTMENT | <label> | WEEK | NUMBERS | EDITORIAL | CLOSE
    ## SAY
    Kaseya = ka-SAY-ah

THE FIREWALL. The host never reads a column; the correspondents never voice
Void's framing or its editorial (W-02). THE MOAT is W-01: every `A:` line in
LEFT and every `B:` line in RIGHT exists in that column's published text by
word overlap; the script SELECTS from the columns, it never paraphrases them.
Everything any voice says outside the columns is held to the published issue
twice: W-13 (every number and multi-word name is the issue's) and the
grounding pass (`ground_script`, the same `derived_grounding` On Air uses),
which cuts a sentence the issue does not carry.

Validator IDs are stable. W-01..W-17 here; W-01..W-10 in `verify_sections.py`
are a different namespace (the served page), as R-nn and H-nn already are.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field

HOST = "H"
CORRESPONDENTS = ("A", "B")
SPEAKERS = (HOST,) + CORRESPONDENTS
#: Kept under the old name for callers that think in benches: A reads LEFT, B RIGHT.
BENCH = CORRESPONDENTS

KINDS = ("COLD", "OPEN", "CONTENTS", "COVER", "DATELINE", "TOPIC", "LEFT", "RIGHT",
         "REST", "TURN", "SECOND", "DEPARTMENT", "WEEK", "NUMBERS", "EDITORIAL", "CLOSE")

#: Which correspondent reads which column. Fixed in the grammar so W-01 and
#: W-02 have something to hold; the VOICE behind each letter rotates (below).
COLUMN_READER = {"LEFT": "A", "RIGHT": "B"}
#: Movements the correspondents carry in passages (features) or in turns (the week).
CORRESPONDENT_SEGMENTS = ("COVER", "SECOND", "WEEK", "LEFT", "RIGHT")
#: Void's own movements: the host alone speaks here.
HOST_SEGMENTS = ("COLD", "OPEN", "CONTENTS", "DATELINE", "TOPIC", "TURN", "DEPARTMENT",
                 "NUMBERS", "EDITORIAL", "CLOSE")

#: Every issue must carry these, in this order, or it is not the programme.
#: NUMBERS is required only when the issue carries a bias report (W-05/W-09).
REQUIRED = ("COLD", "OPEN", "COVER", "TOPIC", "LEFT", "RIGHT", "TURN", "SECOND",
            "EDITORIAL", "CLOSE")

# Void's lines. The sign-on opens OPEN (the cold open carried the image), the
# sign-off closes CLOSE, and the editorial is introduced as Void Opinion, the
# spoken segment title On Air uses (CEO 2026-11-07; CLAUDE.md, Brand).
SIGN_ON = "From Void News, this is The Argument."
CONTENTS_OPEN = "Inside this week."
WEEK_OPEN = "The week in brief."
OPINION_OPEN = "This is Void Opinion."
CLOSE_PREFIX = "That's The Argument, from Void News."
CLOSE_TAG = "Every source, every story, scored for bias."
FORMULAS = (SIGN_ON, CONTENTS_OPEN, WEEK_OPEN, OPINION_OPEN, CLOSE_PREFIX, CLOSE_TAG,
            "The left column first.", "The right column.", "The week in one image.")

# ---------------------------------------------------------------------------
# The cast and the pace
# ---------------------------------------------------------------------------
#: One house pace for all three voices, On Air's (CEO 2026-11-08, rev 5b).
#: No voice is stretched on its own.
SPEED = 0.88
HOST_VOICE = "af_aoede"
CORRESPONDENT_VOICES = ("am_puck", "bf_emma")
#: Measured 2026-11-08 at 0.88 through the real worker over the WHOLE Issue 32
#: script (876, 514 and 518 words), after the voice chain's trim: the pace of
#: a programme, pauses inside the lines included, not of one brisk passage
#: (the same voices read a 118-word passage at 168, 184 and 173). W-07 is only
#: as honest as these numbers: the first render ran 15.2 minutes against an
#: estimate of 13.3 made on the passage figures.
VOICE_WPM = {"af_aoede": 147.0, "am_puck": 154.0, "bf_emma": 144.0,
             # rev 1's cast, kept so an old script can still be estimated
             "bm_lewis": 172.0, "am_michael": 160.0, "af_heart": 162.0}
WPM = 148.0                  # the blend, used when the cast is unknown


def cast_for_week(week_start: str | None, edition: str = "world") -> dict[str, str]:
    """The three voices for THIS issue: {"H": host, "A": left reader, "B": right reader}.

    The host is fixed. Which correspondent reads the left column (A) and
    which the right (B) is drawn from the sha256 of the week, so over the
    volume neither voice owns a political side, and the draw is stated: the
    same week always casts the same way, so a re-render is the same show.
    """
    h = hashlib.sha256(f"argument:{edition}:{week_start or ''}".encode("utf-8")).digest()
    one, two = CORRESPONDENT_VOICES
    if h[0] % 2:
        one, two = two, one
    return {"H": HOST_VOICE, "A": one, "B": two}


# ---------------------------------------------------------------------------
# The band
# ---------------------------------------------------------------------------
# 18-22 minutes, curated (CEO decision): the band of a FULL issue and the
# ceiling of every issue. Since decision 6 (2026-10-02) the band W-07 applies
# is `target_minutes(issue)`, which floats down with the sourced words to a
# floor. Narrower than an hour because a magazine read is not a podcast.
TARGET_MINUTES = (18.0, 22.0)
#: Theme, two interludes, the sting and its silences, the spine, the rest, the
#: stop, the entrance, the outro and the gaps between the lines: about two
#: minutes and a quarter that nobody speaks over (rev 2; rev 1's four WAVs
#: made 1.4). Measured on the first rev 2 render: 914 s of programme over 773
#: s of speech is 2.35.
MUSIC_MINUTES = 2.3

#: A rundown is asked for the middle of the band, not its edges, so ordinary
#: variance in how much the host carries does not tip a good script out.
BAND_MARGIN_MINUTES = 0.5

# THE BAND FLOATS WITH THE SOURCED WORDS (decision 6, CEO 2026-10-02).
#
#   spoken = sourced_words(issue) / WPM * SOURCED_SHARE + MUSIC_MINUTES
#   hi     = clamp(spoken + BAND_WIDTH / 2, FLOOR + BAND_WIDTH, CEILING)
#   lo     = max(FLOOR, hi - BAND_WIDTH)
#
# SOURCED_SHARE is how much of the printed issue the programme reads: it
# SELECTS from the columns, reads the editorial whole and tells the covers in
# passages. A full issue (two covers, five columns, the editorial and ten
# briefs, about 5,700 words) keeps the 18-22 band exactly; a thin one floats
# down to the floor. Padding to reach a band is where unsourced sentences came
# from, so the floor is the honest minimum and never a target. Issue 32 (1,864
# sourced words) read almost whole, the editorial entire and the columns
# selected, ran 15.2 minutes under rev 2's score: inside 14-18 with nothing
# said that the issue did not print.
FLOOR_MINUTES = 14.0
CEILING_MINUTES = TARGET_MINUTES[1]
BAND_WIDTH_MINUTES = TARGET_MINUTES[1] - TARGET_MINUTES[0]
SOURCED_SHARE = 0.55


def sourced_words(issue: dict | None) -> int:
    """Words the published issue carries that the programme may read from."""
    issue = issue or {}
    texts = [c.get("text") for c in (issue.get("cover_text") or []) if isinstance(c, dict)]
    texts += [o.get("text") for o in (issue.get("opinions") or []) if isinstance(o, dict)]
    texts += [d.get("text") for d in (issue.get("departments") or []) if isinstance(d, dict)]
    texts += [r.get("summary") for r in (issue.get("recap_stories") or []) if isinstance(r, dict)]
    texts.append(issue.get("opinion_text"))
    return sum(len(str(t).split()) for t in texts if t)


def target_minutes(issue: dict | None = None) -> tuple[float, float]:
    """The W-07 band for THIS issue. With no issue, the full band."""
    words = sourced_words(issue)
    if not words:
        return TARGET_MINUTES
    spoken = words / WPM * SOURCED_SHARE + MUSIC_MINUTES
    hi = min(CEILING_MINUTES, max(FLOOR_MINUTES + BAND_WIDTH_MINUTES,
                                  spoken + BAND_WIDTH_MINUTES / 2))
    lo = max(FLOOR_MINUTES, hi - BAND_WIDTH_MINUTES)
    return round(lo, 1), round(hi, 1)


def word_budget(voices: dict | None = None,
                band: tuple[float, float] | None = None) -> tuple[int, int]:
    """The word range that actually lands inside the band.

    One function owns the conversion from minutes to words, beside the
    constants W-07 measures with, so the prompt and the validator cannot
    drift (2026-09-20: a prompt at a flat 163 wpm ignored MUSIC_MINUTES and
    a rundown obeyed it and was rejected). The two edges take OPPOSITE rates:
    runtime is words over rate, so the ceiling assumes the SLOWEST voice and
    the floor the FASTEST.
    """
    lo, hi = band or TARGET_MINUTES
    rates = [VOICE_WPM[v] for v in (voices or {}).values() if v in VOICE_WPM]
    fastest = max(rates) if rates else WPM
    slowest = min(rates) if rates else WPM
    speech_lo = (lo + BAND_MARGIN_MINUTES) - MUSIC_MINUTES
    speech_hi = (hi - BAND_MARGIN_MINUTES) - MUSIC_MINUTES
    return int(speech_lo * fastest), int(speech_hi * slowest)


#: A line shorter than this is furniture ("Inside this week.") and is exempt
#: from W-01: it carries no claim to verify.
MIN_CHECKED_WORDS = 8
#: Fraction of a column line's words that must appear in its own column.
OVERLAP_FLOOR = 0.70
#: Fraction of an editorial line's words that must appear in the published
#: editorial: it is read as written, so this is far stricter than the columns.
EDITORIAL_OVERLAP_FLOOR = 0.90

# Void's own lines. Borrowed radio catchphrases and AI-podcast tells fail the
# script, the same list On Air enforces.
BORROWED = (
    "up first", "first the headlines", "and finally", "stay with us",
    "welcome back", "thanks for listening", "thanks for having me",
    "that's all for", "before we go", "let's dive", "let's break",
    "great question", "absolutely", "i'm your host", "joining me now",
)

# The features: the correspondents' passages, On Air's shape (C-07) applied
# to a magazine. A passage is a paragraph for the ear.
PASSAGE_WORDS = (18, 130)
FEATURE_PASSAGES = {"COVER": (3, 9), "SECOND": (2, 7)}
FEATURE_LEADER = {"COVER": "A", "SECOND": "B"}
MAX_RUN = 3
#: The week in brief: items in turns, a fact each, at most this many words.
WEEK_ITEM_MAX_WORDS = 75
WEEK_ITEMS = (3, 10)
#: The turn must reckon with two positions; under this it cannot.
TURN_MIN_WORDS = 60
#: Distinctive words from each column that a turn must engage with.
MIN_DISTINCTIVE = 3


@dataclass
class Line:
    speaker: str
    text: str

    @property
    def words(self) -> int:
        return len(self.text.split())


@dataclass
class Segment:
    kind: str
    title: str | None = None
    lines: list[Line] = field(default_factory=list)

    @property
    def words(self) -> int:
        return sum(l.words for l in self.lines)

    def runs(self) -> int:
        best = cur = 0
        for i, l in enumerate(self.lines):
            cur = cur + 1 if i and l.speaker == self.lines[i - 1].speaker else 1
            best = max(best, cur)
        return best


@dataclass
class Script:
    edition: str = "world"
    segments: list[Segment] = field(default_factory=list)
    say: dict[str, str] = field(default_factory=dict)

    @property
    def words(self) -> int:
        return sum(s.words for s in self.segments)

    def minutes(self, wpm: float = WPM) -> float:
        return self.words / wpm + MUSIC_MINUTES

    def of_kind(self, kind: str) -> list[Segment]:
        return [s for s in self.segments if s.kind == kind]

    def to_text(self) -> str:
        out: list[str] = []
        for s in self.segments:
            out.append(f"## {s.kind}" + (f" | {s.title}" if s.title else ""))
            out.extend(f"{l.speaker}: {l.text}" for l in s.lines)
            out.append("")
        if self.say:
            out.append("## SAY")
            out.extend(f"{k} = {v}" for k, v in self.say.items())
        return "\n".join(out).strip() + "\n"


@dataclass
class Finding:
    id: str
    level: str          # "fail" | "warn"
    segment: str
    detail: str


# ---------------------------------------------------------------------------
# Parsing. Never raises: a malformed script becomes findings, not a traceback.
# ---------------------------------------------------------------------------
#: Rev 1 spoke in E/L/R (the Editor, the left and right bench). An old script
#: parses as H/A/B so its record stays readable; it will not pass rev 2's shape.
_LEGACY_SPEAKERS = {"E": "H", "L": "A", "R": "B"}


def parse_script(raw: str, edition: str = "world") -> Script:
    script = Script(edition=edition)
    cur: Segment | None = None
    in_say = False
    for line in (raw or "").splitlines():
        line = line.rstrip()
        if line.startswith("## "):
            head = [p.strip() for p in line[3:].split("|")]
            kind = head[0].split()[0].upper() if head[0] else ""
            if kind == "SAY":
                in_say, cur = True, None
                continue
            in_say = False
            cur = Segment(kind=kind, title=(head[1] if len(head) > 1 else None))
            script.segments.append(cur)
            continue
        if in_say and "=" in line:
            k, v = line.split("=", 1)
            script.say[k.strip()] = v.strip()
            continue
        if not line or ":" not in line:
            continue
        sp, text = line.split(":", 1)
        sp = _LEGACY_SPEAKERS.get(sp.strip(), sp.strip())
        if sp in SPEAKERS and cur is not None and text.strip():
            cur.lines.append(Line(sp, re.sub(r"\s+", " ", text.strip())))
    return script


def _fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn")


def _words(s: str) -> list[str]:
    return re.sub(r"[^a-z0-9 ]+", " ", _fold(s).lower()).split()


def overlap(line: str, source: str) -> float:
    """Fraction of the line's words that appear in the source.

    A multiset comparison, not a set one: a line that repeats "the" eight times
    must not score for eight matches against one "the" in the column. Trimming
    for the ear is what this tolerates; inventing a sentence is what it catches.
    """
    lw = _words(line)
    if not lw:
        return 1.0
    pool: dict[str, int] = {}
    for w in _words(source):
        pool[w] = pool.get(w, 0) + 1
    hit = 0
    for w in lw:
        if pool.get(w, 0) > 0:
            pool[w] -= 1
            hit += 1
    return hit / len(lw)


def distinctive_hits(turn: str, left: str, right: str) -> dict[str, int]:
    """How many words UNIQUE to each column the turn actually uses.

    Plain overlap does not work here: the two columns argue the SAME story
    and share most of their vocabulary (a one-sided turn still scores 76%
    against the other column). Words present in one column and absent from
    the other separate cleanly (36/0 against 21/24 on the same data).
    """
    lw, rw = set(_words(left)), set(_words(right))
    tw = set(_words(turn))
    return {"L": len(tw & (lw - rw)), "R": len(tw & (rw - lw))}


def estimated_minutes(script: Script, voices: dict | None = None) -> tuple[float, float]:
    """Runtime for THIS script read by THIS cast: weighted by who speaks."""
    voices = voices or {}
    rates = {sp: VOICE_WPM.get(voices.get(sp, ""), WPM) for sp in SPEAKERS}
    secs, words = 0.0, 0
    for seg in script.segments:
        for line in seg.lines:
            secs += line.words / rates.get(line.speaker, WPM) * 60.0
            words += line.words
    minutes = secs / 60.0 + MUSIC_MINUTES
    return minutes, (words / (secs / 60.0) if secs else WPM)


# ---------------------------------------------------------------------------
# The week, spoken
# ---------------------------------------------------------------------------
_MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December")
_ORDINALS = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth", 7: "seventh",
             8: "eighth", 9: "ninth", 10: "tenth", 11: "eleventh", 12: "twelfth", 13: "thirteenth",
             14: "fourteenth", 15: "fifteenth", 16: "sixteenth", 17: "seventeenth", 18: "eighteenth",
             19: "nineteenth", 20: "twentieth", 21: "twenty-first", 22: "twenty-second", 23: "twenty-third",
             24: "twenty-fourth", 25: "twenty-fifth", 26: "twenty-sixth", 27: "twenty-seventh",
             28: "twenty-eighth", 29: "twenty-ninth", 30: "thirtieth", 31: "thirty-first"}


def _spoken_year(y: int) -> str:
    try:
        from briefing.spoken_text import number_words
    except ImportError:  # pragma: no cover
        from pipeline.briefing.spoken_text import number_words  # type: ignore
    if 2000 <= y < 2100:
        return "two thousand" + (f" and {number_words(y - 2000)}" if y > 2000 else "")
    return number_words(y)


def spoken_week(issue: dict) -> str | None:
    """"October twenty-sixth to November first, two thousand and twenty six",
    from the issue's own week_start and week_end; None when they are missing."""
    try:
        a = [int(x) for x in str(issue.get("week_start") or "").split("-")]
        b = [int(x) for x in str(issue.get("week_end") or "").split("-")]
        ya, ma, da = a
        yb, mb, db = b
    except (ValueError, TypeError):
        return None
    start = f"{_MONTHS[ma - 1]} {_ORDINALS[da]}"
    end = _ORDINALS[db] if (ma, ya) == (mb, yb) else f"{_MONTHS[mb - 1]} {_ORDINALS[db]}"
    if (ma, ya) == (mb, yb):
        end = "the " + end
    return f"{start} to {end}, {_spoken_year(yb)}"


def sign_on_line(issue: dict) -> str:
    week = spoken_week(issue)
    return f"{SIGN_ON} The week of {week}." if week else SIGN_ON


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------
def validate_script(script: Script, issue: dict,
                    voices: dict | None = None) -> list[Finding]:
    """Check a rundown against THE PUBLISHED ISSUE it was written from."""
    out: list[Finding] = []
    voices = voices or cast_for_week(issue.get("week_start"), issue.get("edition") or "world")
    stats = ((issue.get("bias_report_data") or {}).get("stats") or {})

    # --- W-05: the programme's shape ---------------------------------------
    kinds = [s.kind for s in script.segments]
    present = set(kinds)
    for kind in REQUIRED:
        if kind not in present:
            out.append(Finding("W-05", "fail", kind,
                               f"no {kind} segment: this is not the programme"))
    if stats and "NUMBERS" not in present:
        out.append(Finding("W-05", "fail", "NUMBERS",
                           "the issue carries a bias report and the programme does not read it"))
    bad = sorted(present - set(KINDS))
    if bad:
        out.append(Finding("W-05", "fail", ",".join(bad),
                           f"unknown segment marker(s): {', '.join(bad)}"))
    order = [k for k in kinds if k in KINDS and k not in ("COVER", "DATELINE", "REST", "DEPARTMENT")]
    if order and order != sorted(order, key=KINDS.index):
        out.append(Finding("W-05", "fail", "ORDER", f"movements out of order: {kinds}"))

    # --- W-01: the bench cannot say anything Void did not print -------------
    opinions = [o for o in (issue.get("opinions") or []) if isinstance(o, dict)]
    columns = _bench_columns(opinions)
    for side, kind in (("L", "LEFT"), ("R", "RIGHT")):
        source = columns.get(side)
        if source is None:
            out.append(Finding("W-01", "fail", kind,
                               f"the issue publishes no {kind.lower()} column for the bench to read"))
            continue
        for seg in script.of_kind(kind):
            for line in seg.lines:
                if line.words < MIN_CHECKED_WORDS:
                    continue
                score = overlap(line.text, source)
                if score < OVERLAP_FLOOR:
                    out.append(Finding(
                        "W-01", "fail", kind,
                        f"{score:.0%} of this line is in the published column "
                        f"(floor {OVERLAP_FLOOR:.0%}): {line.text[:90]!r}"))

    # --- W-02: the firewall ------------------------------------------------
    #   The host never reads a column; one correspondent reads one column; the
    #   correspondents never voice Void's own movements.
    for seg in script.segments:
        for line in seg.lines:
            if line.speaker not in SPEAKERS:
                out.append(Finding("W-02", "fail", seg.kind, f"unknown speaker {line.speaker!r}"))
            elif seg.kind in COLUMN_READER and line.speaker != COLUMN_READER[seg.kind]:
                who = "the host" if line.speaker == HOST else f"correspondent {line.speaker}"
                out.append(Finding("W-02", "fail", seg.kind,
                                   f"{who} speaks inside the {seg.kind.lower()} column; "
                                   f"only {COLUMN_READER[seg.kind]} reads it"))
            elif seg.kind in HOST_SEGMENTS and line.speaker != HOST:
                out.append(Finding("W-02", "fail", seg.kind,
                                   f"a correspondent ({line.speaker}) speaks for Void in {seg.kind}"))
            elif seg.kind in ("COVER", "SECOND") and line.speaker == HOST:
                out.append(Finding("W-02", "fail", seg.kind,
                                   "the host reads a feature; the features are the correspondents'"))

    # --- W-03: both sides, and comparable AIRTIME --------------------------
    #   Rev 2 measures seconds, not words: the two correspondents read at
    #   their own natural rates (154 and 144 wpm) at one house pace, so the
    #   fairness rule has to know the rates rather than demand a matched pair.
    left_w = sum(s.words for s in script.of_kind("LEFT"))
    right_w = sum(s.words for s in script.of_kind("RIGHT"))
    if left_w and right_w:
        l_s = left_w / VOICE_WPM.get(voices.get("A", ""), WPM)
        r_s = right_w / VOICE_WPM.get(voices.get("B", ""), WPM)
        ratio = max(l_s, r_s) / min(l_s, r_s)
        if ratio > 1.35:
            out.append(Finding("W-03", "fail", "LEFT/RIGHT",
                               f"one side gets {ratio:.2f}x the airtime of the other "
                               f"({left_w} vs {right_w} words); the bench is not a platform for one column"))
        elif ratio > 1.20:
            out.append(Finding("W-03", "warn", "LEFT/RIGHT",
                               f"airtime ratio {ratio:.2f}x ({left_w} vs {right_w} words)"))

    # --- W-04: the TURN names BOTH sides -----------------------------------
    turn = " ".join(l.text for s in script.of_kind("TURN") for l in s.lines)
    if turn:
        if len(turn.split()) < TURN_MIN_WORDS:
            out.append(Finding("W-04", "fail", "TURN",
                               f"the turn runs {len(turn.split())} words; it cannot name what "
                               f"BOTH sides leave out in less than about {TURN_MIN_WORDS}"))
        else:
            hits = distinctive_hits(turn, columns.get("L", ""), columns.get("R", ""))
            lo, hi = min(hits.values()), max(hits.values())
            if hi >= MIN_DISTINCTIVE and (lo < MIN_DISTINCTIVE or lo < hi * 0.15):
                out.append(Finding(
                    "W-04", "fail", "TURN",
                    f"the turn engages one column and not the other "
                    f"(L {hits['L']}, R {hits['R']} distinctive words); "
                    "it reckons with both or with neither"))

    # --- W-06: the signature devices ---------------------------------------
    cover_idx = [i for i, s in enumerate(script.segments) if s.kind == "COVER"]
    date_idx = [i for i, s in enumerate(script.segments) if s.kind == "DATELINE"]
    if not date_idx:
        out.append(Finding("W-06", "fail", "DATELINE",
                           "no dateline beat inside the cover feature"))
    elif not (cover_idx and min(cover_idx) < date_idx[0] < max(cover_idx)):
        out.append(Finding("W-06", "fail", "DATELINE",
                           "the dateline beat sits INSIDE the cover, between two of its passages"))
    for seg in script.of_kind("DATELINE"):
        if len(seg.lines) != 1 or seg.lines[0].words > 8:
            out.append(Finding("W-06", "fail", "DATELINE",
                               "a dateline is one short beat: a day and a count, nothing else"))
    if not script.of_kind("REST"):
        out.append(Finding("W-06", "warn", "REST",
                           "no held pause between the argument and the turn"))

    # --- W-07: length ------------------------------------------------------
    minutes, wpm = estimated_minutes(script, voices)
    lo, hi = target_minutes(issue)
    if not (lo <= minutes <= hi):
        out.append(Finding("W-07", "fail", "TOTAL",
                           f"{script.words} words is about {minutes:.1f} min at {wpm:.0f} wpm; "
                           f"the band is {lo:.0f}-{hi:.0f}"))

    # --- W-08: Void's own lines only ---------------------------------------
    for seg in script.segments:
        for line in seg.lines:
            low = line.text.lower()
            for phrase in BORROWED:
                if phrase in low:
                    out.append(Finding("W-08", "fail", seg.kind,
                                       f"borrowed radio furniture: {phrase!r}"))

    # --- W-09: the numbers read are the issue's own ------------------------
    numbers_text = " ".join(l.text for s in script.of_kind("NUMBERS") for l in s.lines)
    if numbers_text and not stats:
        out.append(Finding("W-09", "fail", "NUMBERS",
                           "a Week in Bias read on an issue that carries no bias report; "
                           "the movement is dropped, never invented"))
    if numbers_text and stats:
        spoken = set(re.findall(r"\d+(?:\.\d+)?", numbers_text))
        known = {str(int(v)) for v in _stat_values(stats)}
        known |= {f"{v:.1f}" for v in _stat_values(stats)}
        invented = sorted(n for n in spoken if n not in known and len(n) > 2)
        if invented:
            out.append(Finding("W-09", "fail", "NUMBERS",
                               "figures read aloud that the issue does not carry: "
                               + ", ".join(invented)))

    # --- W-10: the close leaves it open ------------------------------------
    close = " ".join(l.text for s in script.of_kind("CLOSE") for l in s.lines)
    if close and "?" not in close:
        out.append(Finding("W-10", "warn", "CLOSE",
                           "the close states rather than asks; the week's unresolved "
                           "question is a signature device"))

    # --- W-11: no headline is read as a list -------------------------------
    for seg in script.of_kind("CONTENTS"):
        if len(seg.lines) > 6:
            out.append(Finding("W-11", "warn", "CONTENTS",
                               f"{len(seg.lines)} lines; a contents is four, not a rundown"))

    # --- W-12: a SPOKEN script carries no quotation marks ------------------
    for seg in script.segments:
        for line in seg.lines:
            if '"' in line.text or "“" in line.text:
                out.append(Finding("W-12", "warn", seg.kind,
                                   "quotation marks in spoken copy; attribute in words instead"))

    out.extend(w13_findings(script, issue))
    out.extend(_w14_editorial(script, issue))
    out.extend(_w15_features(script))
    out.extend(_w16_week(script, issue))
    out.extend(_w17_formulas(script, issue))
    return out


# --- W-13: nobody says a number or a name the issue did not print ----------
#   W-01 holds the columns to their text. Every OTHER line, whoever reads it
#   (the host's framing, the correspondents' passages and briefs), is held to
#   the published issue: every number read as a value ("twenty percent" is 20)
#   and every multi-word proper name. The name rule is the Weekly print rule
#   (`weekly_parse.unsourced_terms`). The sign-on is pinned to week_start and
#   week_end by W-17 instead. Failure means no render.
HOUSE_NAMES = ("From Void News", "Void News", "Void Opinion", "The Argument")
NAME_ALIASES = (("european union", "eu"), ("united states", "us"), ("united kingdom", "uk"),
                ("united nations", "un"), ("federal reserve", "fed"))
_NOT_ISSUE_TEXT = ("audio_", "gemini_calls_used", "generation_duration_seconds",
                   "generator", "id", "created_at", "updated_at", "opinion_start_seconds")


def issue_text(issue: dict) -> str:
    """Every string and number the published issue carries, flattened."""
    parts: list[str] = []

    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, bool) or v is None:
            return
        else:
            parts.append(str(v))

    for k, v in (issue or {}).items():
        if any(k == p or (p.endswith("_") and k.startswith(p)) for p in _NOT_ISSUE_TEXT):
            continue
        walk(v)
    return "\n".join(parts)


def _is_sign_on(seg: Segment, i: int, line: Line) -> bool:
    return seg.kind == "OPEN" and i == 0 and line.text.startswith(SIGN_ON)


def w13_findings(script: Script, issue: dict) -> list[Finding]:
    try:
        from history.spoken_numbers import (
            Num, digit_numbers, record_values, spoken_numbers, supported)
    except ImportError:  # pragma: no cover - imported from the repo root
        from pipeline.history.spoken_numbers import (
            Num, digit_numbers, record_values, spoken_numbers, supported)
    try:
        from briefing.weekly_parse import _G_SENT_RE, unsourced_terms
    except ImportError:  # pragma: no cover
        from pipeline.briefing.weekly_parse import _G_SENT_RE, unsourced_terms

    text = issue_text(issue)
    low_text = re.sub(r"\s+", " ", text.lower().replace(".", ""))
    values = record_values(text)
    out: list[Finding] = []
    for seg in script.segments:
        if seg.kind in COLUMN_READER:
            continue
        for i, line in enumerate(seg.lines):
            if _is_sign_on(seg, i, line):
                continue
            who = "the host" if line.speaker == HOST else f"correspondent {line.speaker}"
            said = line.text
            for house in HOUSE_NAMES:
                said = said.replace(house, " ")
            nums = spoken_numbers(said) + [Num(v, f"{v:g}", False) for v in digit_numbers(said)]
            for x in nums:
                if x.value and not supported(x, values):
                    out.append(Finding("W-13", "fail", seg.kind,
                                       f"{who} says {x.text!r} ({x.value:g}); the issue "
                                       f"carries no such number: {line.text[:80]!r}"))
            for sent in _G_SENT_RE.split(said):
                for name in unsourced_terms(sent, text, set()):
                    if re.fullmatch(r"[\d,.]+", name):
                        continue          # digits are judged as values above
                    if _aliased(name, low_text):
                        continue
                    out.append(Finding("W-13", "fail", seg.kind,
                                       f"{who} names {name!r}; the issue does not: "
                                       f"{line.text[:80]!r}"))
    return out


def _aliased(name: str, low_text: str) -> bool:
    low = re.sub(r"\s+", " ", name.lower().replace(".", "")).strip()
    for long, short in NAME_ALIASES:
        if long in low:
            alt = low.replace(long, short)
            if re.search(r"\b" + re.escape(alt) + r"\b", low_text):
                return True
    return False


# --- W-14: the editorial is Void's column, read as written -----------------
def _w14_editorial(script: Script, issue: dict) -> list[Finding]:
    out: list[Finding] = []
    text = (issue.get("opinion_text") or "").strip()
    for seg in script.of_kind("EDITORIAL"):
        if not seg.lines:
            out.append(Finding("W-14", "fail", "EDITORIAL", "the editorial has no spoken line"))
            continue
        first = seg.lines[0]
        if not first.text.startswith(OPINION_OPEN):
            out.append(Finding("W-14", "fail", "EDITORIAL",
                               f"the editorial opens on {OPINION_OPEN!r} and its headline: {first.text[:70]!r}"))
        if not text:
            out.append(Finding("W-14", "fail", "EDITORIAL",
                               "the issue publishes no editorial for the host to read"))
            continue
        body = seg.lines[1:]
        if not body:
            out.append(Finding("W-14", "fail", "EDITORIAL", "the introduction alone is not an editorial"))
        for line in body:
            score = overlap(line.text, text)
            if score < EDITORIAL_OVERLAP_FLOOR:
                out.append(Finding("W-14", "fail", "EDITORIAL",
                                   f"{score:.0%} of this line is in the published editorial "
                                   f"(floor {EDITORIAL_OVERLAP_FLOOR:.0%}); it is read as written: "
                                   f"{line.text[:80]!r}"))
    return out


# --- W-15: the features are the correspondents', in passages ---------------
def _w15_features(script: Script) -> list[Finding]:
    out: list[Finding] = []
    for kind, (lo, hi) in FEATURE_PASSAGES.items():
        segs = script.of_kind(kind)
        if not segs:
            continue
        lines = [l for s in segs for l in s.lines if l.speaker in CORRESPONDENTS]
        if not lines:
            out.append(Finding("W-15", "fail", kind, "no correspondent passage"))
            continue
        leader = FEATURE_LEADER[kind]
        other = "B" if leader == "A" else "A"
        if lines[0].speaker != leader:
            out.append(Finding("W-15", "fail", kind, f"correspondent {leader} leads the {kind.lower()}"))
        if not (lo <= len(lines) <= hi):
            out.append(Finding("W-15", "fail", kind, f"{len(lines)} passages; {lo} to {hi}"))
        for l in lines:
            if not (PASSAGE_WORDS[0] <= l.words <= PASSAGE_WORDS[1]):
                out.append(Finding("W-15", "fail", kind,
                                   f"a passage is {PASSAGE_WORDS[0]} to {PASSAGE_WORDS[1]} words; "
                                   f"got {l.words}: {l.text[:60]!r}"))
            if "?" in l.text:
                out.append(Finding("W-15", "fail", kind,
                                   f"the correspondents do not interview each other: {l.text[:60]!r}"))
        if not any(l.speaker == other for l in lines):
            out.append(Finding("W-15", "fail", kind, f"correspondent {other} takes no passage of the {kind.lower()}"))
        elif lines[-1].speaker != other:
            out.append(Finding("W-15", "warn", kind, f"{other} usually takes the last passage"))
        # the run is measured across the whole feature, dateline included
        whole = Segment(kind, lines=lines)
        if whole.runs() > MAX_RUN:
            out.append(Finding("W-15", "fail", kind,
                               f"one voice reads {whole.runs()} passages in a row; at most {MAX_RUN}"))
    return out


# --- W-16: the week in brief -----------------------------------------------
def _w16_week(script: Script, issue: dict) -> list[Finding]:
    out: list[Finding] = []
    briefs = [r for r in (issue.get("recap_stories") or []) if isinstance(r, dict)]
    for seg in script.of_kind("WEEK"):
        if not seg.lines or seg.lines[0].speaker != HOST or seg.lines[0].text != WEEK_OPEN:
            out.append(Finding("W-16", "fail", "WEEK", f"the week opens with the host: {WEEK_OPEN!r}"))
        items = [l for l in seg.lines if l.speaker in CORRESPONDENTS]
        if any(l.speaker == HOST for l in seg.lines[1:]):
            out.append(Finding("W-16", "fail", "WEEK", "the correspondents read the week; the host only opens it"))
        if not (WEEK_ITEMS[0] <= len(items) <= WEEK_ITEMS[1]):
            out.append(Finding("W-16", "fail", "WEEK", f"{len(items)} items; {WEEK_ITEMS[0]} to {WEEK_ITEMS[1]}"))
        if len(items) > len(briefs):
            out.append(Finding("W-16", "fail", "WEEK",
                               f"{len(items)} items but the issue prints {len(briefs)} briefs"))
        for i, l in enumerate(items):
            if l.words > WEEK_ITEM_MAX_WORDS:
                out.append(Finding("W-16", "fail", "WEEK",
                                   f"{l.words}-word item; at most {WEEK_ITEM_MAX_WORDS}: {l.text[:60]!r}"))
            if "?" in l.text:
                out.append(Finding("W-16", "fail", "WEEK", f"an item is a fact, not a question: {l.text[:60]!r}"))
            if i and l.speaker == items[i - 1].speaker:
                out.append(Finding("W-16", "warn", "WEEK", "the items alternate voices"))
    return out


# --- W-17: Void's fixed lines are exact ------------------------------------
def _w17_formulas(script: Script, issue: dict) -> list[Finding]:
    out: list[Finding] = []
    cold = script.of_kind("COLD")
    if cold:
        lines = [l for s in cold for l in s.lines]
        if not (1 <= len(lines) <= 2) or any(l.speaker != HOST for l in lines):
            out.append(Finding("W-17", "fail", "COLD", "the cold open is one or two lines from the host"))
        if any("Argument" in l.text or "Void" in l.text for l in lines):
            out.append(Finding("W-17", "fail", "COLD", "the cold open names no programme; the sign-on does"))
        if any("?" in l.text for l in lines):
            out.append(Finding("W-17", "fail", "COLD", "the cold open is an image, not a question"))
    want = sign_on_line(issue)
    for seg in script.of_kind("OPEN"):
        if not seg.lines or seg.lines[0].text != want:
            out.append(Finding("W-17", "fail", "OPEN",
                               f"the sign-on is exactly {want!r}: {(seg.lines[0].text if seg.lines else '')[:90]!r}"))
    for seg in script.of_kind("CONTENTS"):
        if not seg.lines or seg.lines[0].text != CONTENTS_OPEN:
            out.append(Finding("W-17", "fail", "CONTENTS", f"the contents opens on {CONTENTS_OPEN!r}"))
    for seg in script.of_kind("CLOSE"):
        if not seg.lines:
            out.append(Finding("W-17", "fail", "CLOSE", "the close has no spoken line"))
            continue
        last = seg.lines[-1].text
        if not (last.startswith(CLOSE_PREFIX) and last.rstrip().endswith(CLOSE_TAG)):
            out.append(Finding("W-17", "fail", "CLOSE",
                               f"the sign-off is {CLOSE_PREFIX!r} ... {CLOSE_TAG!r}: {last[:80]!r}"))
    return out


# ---------------------------------------------------------------------------
# Grounding: every sentence outside the columns, read against the issue
# ---------------------------------------------------------------------------
def ground_script(script: Script, issue: dict) -> list:
    """Cut every sentence the published issue does not carry (On Air's
    `ground_show`, with the issue as the one story). The columns are W-01's
    and are not touched; the sign-on, the contents opener, the Void Opinion
    introduction and the sign-off are Void's formulas and are kept. A line
    cut whole goes; a segment emptied by the cut goes. Returns the cuts."""
    try:
        from editorial import derived_grounding as dg
    except ImportError:  # pragma: no cover
        from pipeline.editorial import derived_grounding as dg  # type: ignore
    text = issue_text(issue)
    if not text.strip():
        return []
    # The programme's own names are not in the issue's text and are not claims.
    ev = dg.Evidence(text + "\n" + " ".join(HOUSE_NAMES) + "\n" + sign_on_line(issue))
    editorial = dg.Evidence(issue.get("opinion_text") or "") if issue.get("opinion_text") else None
    cuts: list = []
    for seg in script.segments:
        if seg.kind in COLUMN_READER:
            continue
        kept: list[Line] = []
        for i, line in enumerate(seg.lines):
            if _is_sign_on(seg, i, line) or line.text in (CONTENTS_OPEN, WEEK_OPEN):
                kept.append(line)
                continue
            if seg.kind == "EDITORIAL" and i == 0 and line.text.startswith(OPINION_OPEN):
                kept.append(line)
                continue
            use = editorial if (seg.kind == "EDITORIAL" and editorial is not None) else ev
            new, more = dg.ground_text(line.text, use, product=f"weekly:{seg.kind}", formulas=FORMULAS)
            cuts.extend(more)
            if seg.kind == "CLOSE" and i == len(seg.lines) - 1:
                # the sign-off survives whatever the sentences before it do
                if not new.strip().startswith(CLOSE_PREFIX):
                    new = f"{CLOSE_PREFIX} {CLOSE_TAG}"
                if not new.rstrip().endswith(CLOSE_TAG):
                    new = new.rstrip() + " " + CLOSE_TAG
            if new.strip():
                line.text = re.sub(r"\s+", " ", new.replace("\n\n", " ")).strip()
                kept.append(line)
        seg.lines = kept
    script.segments = [s for s in script.segments if s.lines or s.kind == "REST"]
    return cuts


def _bench_columns(opinions: list[dict]) -> dict[str, str]:
    """The two paired columns, as the page finds them.

    Mirrors `findPair` in Perspectives.tsx: `pair_id` first, then the `paired`
    flag, then a left/right match on one topic. If the page and the programme
    disagreed about which two essays are the argument, the show would stage a
    debate the reader cannot find.
    """
    by_pair: dict[str, list[dict]] = {}
    for o in opinions:
        pid = o.get("pair_id")
        if pid:
            by_pair.setdefault(pid, []).append(o)
    group = next((g for g in by_pair.values() if len(g) == 2), None)
    if group is None:
        flagged = [o for o in opinions if o.get("paired")]
        group = flagged if len(flagged) == 2 else None
    if group is None:
        left = next((o for o in opinions if (o.get("lean") or "").lower() == "left"), None)
        right = next((o for o in opinions if (o.get("lean") or "").lower() == "right"), None)
        group = [left, right] if left and right and left.get("topic") == right.get("topic") else None
    if not group:
        return {}
    a, b = group
    if not (a.get("lean") or "").lower().startswith("left"):
        a, b = b, a
    return {"L": a.get("text") or "", "R": b.get("text") or ""}


def _stat_values(stats: dict) -> list[float]:
    out = []
    for v in stats.values():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            out.append(float(v))
    return out
