"""The Argument: the weekly audio edition's script format, parser and validators.

On Air is what happened today. History is what it meant then. THE WEEKLY IS
WHAT WE ARGUED ABOUT, AND WHAT THE ARGUMENT LOOKED LIKE FROM OUTSIDE.

The generator already writes two columns on the SAME cover story, each told in
its prompt that the other exists and will be read beside it. Nothing had ever
staged them. Weekly audio, until now, was one Gemini call writing free `A:`/`B:`
dialogue into the 2026-06 edge-tts path: two voices, unmastered mono, no
chapters, no validators, and a `_WEEKLY_TTS_PREAMBLE` full of pacing
instructions that the engine which actually ran never read.

    ## OPEN | CONTENTS | COVER | DATELINE | TOPIC | LEFT | RIGHT | TURN
    ## SECOND | DEPARTMENT | <label> | NUMBERS | EDITORIAL | REST | CLOSE
    E: the Editor
    L: the left bench      R: the right bench
    ## SAY
    Nuuk = NOOK

THE MOAT: W-01. The script does not PARAPHRASE the columns, it SELECTS from
them, the way History's document voice reads primary sources rather than
summarising them. Every `L:` and `R:` line must exist in that column's
published `opinions[].text` by word overlap. Trimming for the ear is allowed;
inventing is not. That makes the show's core content unfabricatable, and it
means a listener hears the same words a reader reads.

Validator IDs are stable. W-01..W-12 here; W-01..W-09 in `verify_sections.py`
are a different namespace (the served page), as R-nn and H-nn already are.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# THREE VOICES, and the firewall is cleaner than On Air's rather than weaker.
# The bench voices ONLY ever argue; the Editor ONLY ever speaks for Void. Giving
# the Editorial to a bench voice would muddy the one line that matters, so the
# Editor reads it.
SPEAKERS = ("E", "L", "R")
BENCH = ("L", "R")

KINDS = ("OPEN", "CONTENTS", "COVER", "DATELINE", "TOPIC", "LEFT", "RIGHT",
         "TURN", "SECOND", "DEPARTMENT", "NUMBERS", "EDITORIAL", "REST", "CLOSE")

#: Segments in which a bench voice may speak. Anywhere else is the Editor.
BENCH_SEGMENTS = ("LEFT", "RIGHT")

#: Every issue must carry these, in this order, or it is not the programme.
REQUIRED = ("OPEN", "COVER", "TOPIC", "LEFT", "RIGHT", "TURN", "NUMBERS",
            "EDITORIAL", "CLOSE")

# 18-22 minutes, curated (CEO decision). Wider than History's band because the
# issue has four departments to carry and narrower than an hour because a
# magazine read is not a podcast.
TARGET_MINUTES = (18.0, 22.0)
MUSIC_MINUTES = 1.4          # theme, contents bed, two transitions, break, outro

# House pace 0.92, and the bench is RATE-MATCHED. This is the non-obvious
# constraint in the whole format: two voices with different natural rates give
# one side materially more airtime for the same number of words, which is an
# editorial fairness problem rather than an aesthetic one. am_michael and
# af_heart measure 160 and 162 wpm, two apart. The Editor is deliberately the
# outlier: the spine should not sound like a bench.
VOICE_WPM = {"bm_lewis": 172.0, "am_michael": 160.0, "af_heart": 162.0}
WPM = 163.0                  # the blend, used when the cast is unknown

#: A rundown is asked for the middle of the band, not its edges, so ordinary
#: variance in how much the Editor carries does not tip a good script out.
BAND_MARGIN_MINUTES = 0.5


def word_budget(voices: dict | None = None) -> tuple[int, int]:
    """The word range that actually lands inside TARGET_MINUTES.

    This exists because the generator and W-07 used to model the same quantity
    differently, and the generator lost. Its prompt turned the minute band into
    words at a flat 163 wpm, while `estimated_minutes` adds MUSIC_MINUTES on
    top: 1.4 minutes of theme, beds, transitions and outro that nobody speaks
    over. So the prompt's ceiling was about 228 words too generous, and a
    rundown could sit inside the range it was given and still fail the band.

    That is not hypothetical. The scheduled run of 2026-09-20 wrote 3,463
    words, comfortably inside the 2,934-3,586 the prompt asked for, and W-07
    measured 22.6 minutes against a 22.0 ceiling. The model did as it was told
    and was rejected for it, and the Weekly fell back to the legacy read.

    One function owns the conversion now, so the two cannot drift again.

    The two edges take OPPOSITE rates, which is the part that is easy to get
    wrong and which a synthetic script at each edge caught in review. Runtime
    is words over rate, so to stay under the ceiling at any cast mix the
    ceiling must assume the SLOWEST voice, and to clear the floor it must
    assume the FASTEST. Using one blended rate for both puts the floor below
    the band whenever the Editor, at 172, carries most of the programme, which
    he always does.
    """
    lo, hi = TARGET_MINUTES
    rates = [VOICE_WPM[v] for v in (voices or {}).values() if v in VOICE_WPM]
    fastest = max(rates) if rates else WPM
    slowest = min(rates) if rates else WPM
    speech_lo = (lo + BAND_MARGIN_MINUTES) - MUSIC_MINUTES
    speech_hi = (hi - BAND_MARGIN_MINUTES) - MUSIC_MINUTES
    return int(speech_lo * fastest), int(speech_hi * slowest)


#: A line shorter than this is furniture ("Inside this week.") and is exempt
#: from W-01: it carries no claim to verify.
MIN_CHECKED_WORDS = 8

#: Fraction of a bench line's words that must appear in its own column.
OVERLAP_FLOOR = 0.70

# Void's own lines. Borrowed radio catchphrases and AI-podcast tells fail the
# script, the same list On Air enforces, because the one thing a distinctive
# programme cannot afford is to sound like the programmes it is not.
BORROWED = (
    "up first", "first the headlines", "and finally", "stay with us",
    "welcome back", "thanks for listening", "thanks for having me",
    "that's all for", "before we go", "let's dive", "let's break",
    "great question", "absolutely", "i'm your host", "joining me now",
)


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


@dataclass
class Finding:
    id: str
    level: str          # "fail" | "warn"
    segment: str
    detail: str


# ---------------------------------------------------------------------------
# Parsing. Never raises: a malformed script becomes findings, not a traceback.
# ---------------------------------------------------------------------------
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
        if sp.strip() in SPEAKERS and cur is not None:
            cur.lines.append(Line(sp.strip(), text.strip()))
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


#: Distinctive words from each column that a turn must engage with.
MIN_DISTINCTIVE = 3


def distinctive_hits(turn: str, left: str, right: str) -> dict[str, int]:
    """How many words UNIQUE to each column the turn actually uses.

    Plain overlap does not work here, and the measurement says so. The two
    columns argue the SAME cover story, so they share most of their
    vocabulary; a turn drawn entirely from the left column still scores 76%
    against the right one, against 84% for a genuinely balanced turn. An 8
    point gap is not a signal.

    Words present in one column and absent from the other separate cleanly:
    on the same data a one-sided turn scores 36 and 0, a balanced one 21 and
    24. This is the same move the ranker makes when it stops counting shared
    stems and starts counting SPECIFIC ones.
    """
    lw, rw = set(_words(left)), set(_words(right))
    tw = set(_words(turn))
    return {"L": len(tw & (lw - rw)), "R": len(tw & (rw - lw))}


def estimated_minutes(script: Script, voices: dict | None = None) -> tuple[float, float]:
    """Runtime for THIS script read by THIS cast.

    Weighted by who speaks: the Editor carries most of the programme at 172
    wpm and the bench reads at 160, so one blended constant misjudges an
    argument-heavy issue in the direction that matters.
    """
    voices = voices or {}
    rates = {"E": VOICE_WPM.get(voices.get("editor", ""), WPM),
             "L": VOICE_WPM.get(voices.get("left", ""), WPM),
             "R": VOICE_WPM.get(voices.get("right", ""), WPM)}
    secs, words = 0.0, 0
    for seg in script.segments:
        for line in seg.lines:
            secs += line.words / rates.get(line.speaker, WPM) * 60.0
            words += line.words
    minutes = secs / 60.0 + MUSIC_MINUTES
    return minutes, (words / (secs / 60.0) if secs else WPM)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------
def validate_script(script: Script, issue: dict,
                    voices: dict | None = None) -> list[Finding]:
    """Check a rundown against THE PUBLISHED ISSUE it was written from."""
    out: list[Finding] = []

    # --- W-05: the programme's shape ---------------------------------------
    present = {s.kind for s in script.segments}
    for kind in REQUIRED:
        if kind not in present:
            out.append(Finding("W-05", "fail", kind,
                               f"no {kind} segment: this is not the programme"))
    bad = sorted({s.kind for s in script.segments} - set(KINDS))
    if bad:
        out.append(Finding("W-05", "fail", ",".join(bad),
                           f"unknown segment marker(s): {', '.join(bad)}"))

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

    # --- W-02: the bench speaks only on the bench --------------------------
    for seg in script.segments:
        for line in seg.lines:
            if line.speaker in BENCH and seg.kind not in BENCH_SEGMENTS:
                out.append(Finding("W-02", "fail", seg.kind,
                                   f"a bench voice ({line.speaker}) speaks outside the argument"))
            if line.speaker == "E" and seg.kind in BENCH_SEGMENTS:
                out.append(Finding("W-02", "fail", seg.kind,
                                   "the Editor speaks inside a bench column"))

    # --- W-03: both sides, and comparable airtime --------------------------
    left_w = sum(s.words for s in script.of_kind("LEFT"))
    right_w = sum(s.words for s in script.of_kind("RIGHT"))
    if left_w and right_w:
        ratio = max(left_w, right_w) / min(left_w, right_w)
        if ratio > 1.35:
            out.append(Finding("W-03", "fail", "LEFT/RIGHT",
                               f"one side gets {ratio:.2f}x the words of the other "
                               f"({left_w} vs {right_w}); the bench is not a platform for one column"))
        elif ratio > 1.20:
            out.append(Finding("W-03", "warn", "LEFT/RIGHT",
                               f"airtime ratio {ratio:.2f}x ({left_w} vs {right_w})"))

    # --- W-04: the TURN names BOTH sides -----------------------------------
    #   Checked structurally, not by looking for the words "left" and "right",
    #   which a good turn avoids: it must be long enough to reckon with two
    #   positions, and it must engage BOTH columns rather than debunking one.
    #   The Partition draft that shaped History's H-09 characterised each
    #   account by what it OMITS while omitting the strongest fact in one of
    #   them; a one-sided turn is that failure wearing a balance costume.
    turn = " ".join(l.text for s in script.of_kind("TURN") for l in s.lines)
    if turn:
        if len(turn.split()) < 60:
            out.append(Finding("W-04", "fail", "TURN",
                               f"the turn runs {len(turn.split())} words; it cannot name what "
                               "BOTH sides leave out in less than about sixty"))
        else:
            cols = _bench_columns(opinions)
            hits = distinctive_hits(turn, cols.get("L", ""), cols.get("R", ""))
            lo, hi = min(hits.values()), max(hits.values())
            if hi >= MIN_DISTINCTIVE and (lo < MIN_DISTINCTIVE or lo < hi * 0.15):
                out.append(Finding(
                    "W-04", "fail", "TURN",
                    f"the turn engages one column and not the other "
                    f"(L {hits['L']}, R {hits['R']} distinctive words); "
                    "it reckons with both or with neither"))

    # --- W-06: the signature devices the CEO asked for ---------------------
    if not script.of_kind("DATELINE"):
        out.append(Finding("W-06", "fail", "DATELINE",
                           "no dateline beat inside the cover feature"))
    if not script.of_kind("REST"):
        out.append(Finding("W-06", "warn", "REST",
                           "no held pause anywhere in eighteen minutes"))

    # --- W-07: length ------------------------------------------------------
    minutes, wpm = estimated_minutes(script, voices)
    lo, hi = TARGET_MINUTES
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
    stats = ((issue.get("bias_report_data") or {}).get("stats") or {})
    numbers_text = " ".join(l.text for s in script.of_kind("NUMBERS") for l in s.lines)
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
                           "question is the fourth signature device"))

    # --- W-11: no headline is read as a list -------------------------------
    for seg in script.of_kind("CONTENTS"):
        if len(seg.lines) > 6:
            out.append(Finding("W-11", "warn", "CONTENTS",
                               f"{len(seg.lines)} lines; a contents is four, not a rundown"))

    # --- W-12: written prose is dash-free; a SPOKEN script is not ----------
    #   Deliberately inverted from the written rule. A dash is a breath mark
    #   for the synthesiser, which is why audio scripts are exempt in
    #   CLAUDE.md. What a spoken script must NOT carry is a quotation mark,
    #   because the synthesiser reads punctuation it cannot pronounce as
    #   nothing and the listener hears an unattributed claim.
    for seg in script.segments:
        for line in seg.lines:
            if '"' in line.text or "“" in line.text:
                out.append(Finding("W-12", "warn", seg.kind,
                                   "quotation marks in spoken copy; attribute in words instead"))
    return out


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
