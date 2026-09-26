"""On Air radio rundown: the script for the daily radio show.

A separate artifact from the written TL;DR. The written brief is read; this is
SPOKEN, so it follows radio-news writing rules (one idea per sentence, present
tense, attribution before the claim, numbers as words, no quotation marks read
aloud) and a fixed running order the assembler turns into chapters:

    ## OPEN                      sign-on (voice A)
    ## MENU                      five headlines, alternating voices
    ## STORY 1 | <title>         ranks 1-4 in depth, lead voice alternates
    ## BRIEFS                    ranks 5-12 as one-liners
    ## FINALLY | <rank> | <title> a lighter last item (absent on a disaster day)
    ## CLOSE                     sign-off (voice A)
    ## SAY                       Name = lowercase respelling (applied before synthesis)

The throw into the editorial ("Next, the editorial.") is a code constant, and
the editorial itself is the existing opinion_audio_script, so the model never
writes a segment the assembler may have to drop.

One Gemini flash call, one retry with the validator findings named, then the
caller falls back to the legacy single-call audio script so a show always
ships. Plain text with markers, never JSON: rev 54 (CLAUDE.md) records that
long prose inside JSON breaks on the first unescaped quote.

Everything expressible is Void's own. Bulletin STRUCTURE (menu, lead, round-up,
kicker, sign-off) is a convention nobody owns; the lines are not borrowed from
any broadcaster and the validators reject the well-known catchphrases.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from briefing.spoken_text import (
        has_numerals, has_quotation_marks, spoken_date, strip_quotation_marks,
    )
except ImportError:  # pragma: no cover - package-relative import
    from pipeline.briefing.spoken_text import (  # type: ignore
        has_numerals, has_quotation_marks, spoken_date, strip_quotation_marks,
    )

# ---------------------------------------------------------------------------
# Void's own lines (original; never borrowed)
# ---------------------------------------------------------------------------

SIGN_ON_PREFIX = "From Void News, this is On Air."
MENU_LEAD = "On the desk today."
BRIEFS_LEAD = "Also on the desk."
KICKER_LEADS = ("One more before Void Opinion.", "Last item.", "One more.")
CLOSE_PREFIX = "That's On Air from Void News."
CLOSE_TAG = "Every source, every story, at Void News."

# A lead story this severe (deaths, mass casualties: importance_ranker's
# disaster_severity, 0..1) suppresses the lighter last item.
KICKER_SUPPRESS_SEVERITY = 0.6

SegmentKind = Literal["OPEN", "MENU", "STORY", "BRIEFS", "FINALLY", "CLOSE"]
_KINDS: tuple[str, ...] = ("OPEN", "MENU", "STORY", "BRIEFS", "FINALLY", "CLOSE")

# The pace the show is actually read at. Each voice now reads at its own
# natural rate rather than being stretched to a common one (see
# tts_engines.KOKORO_SPEED), so this is the blend across the desk: am_puck 164,
# af_bella 177, af_heart 162, weighted by how much each carries. Used for the
# length estimates the validators report, so a rundown that reads long says so
# before it is synthesised.
SPEECH_WPM = 158

# Word budgets at SPEECH_WPM. (lo, hi); the validator fails outside ±25 % of
# the band and warns inside it. Total news budget 850-1150 words ≈ 5-7
# minutes, plus a 500-700 word editorial ≈ 8.5-10 minutes with music.
WORD_BUDGETS: dict[str, tuple[int, int]] = {
    "OPEN": (12, 35),
    "MENU": (35, 80),
    "STORY1": (190, 280),
    "STORY": (150, 230),
    "BRIEFS": (100, 180),
    "FINALLY": (60, 120),
    "CLOSE": (25, 55),
}
TOTAL_BUDGET = (950, 1250)
MENU_HEADLINE_MAX_WORDS = 12
BRIEF_ITEM_MAX_WORDS = 22
BRIEF_ITEMS = (6, 8)
DEEP_STORIES = 4
BRIEF_RANKS = (5, 12)

# Phrases that either belong to someone else's show, or are the tells of an
# AI "podcast" (host-name addressing, thanks, reacting). Case-insensitive,
# matched on word boundaries.
BANNED_PHRASES: tuple[str, ...] = (
    "up first", "here's what we're covering", "here is what we're covering",
    "first the headlines", "first, the headlines", "and that's the headlines",
    "that's the headlines", "these are our main stories", "our main stories",
    "stay with us", "and finally", "welcome back", "welcome to", "let's dive in",
    "let's get into it", "let's get started", "buckle up", "stay tuned",
    "that's fascinating", "great question", "absolutely", "wow", "incredible",
    "thanks,", "thank you,", "over to you", "back to you", "good morning",
    "good evening", "good afternoon", "you're listening to", "i'm your host",
    "in today's episode", "in this episode", "join us tomorrow", "see you tomorrow",
    "perhaps most significantly", "in a troubling development", "this next one matters",
    "which brings us to", "in a sign of things to come", "it should be noted",
    "interestingly", "crucially", "notably",
    # The significance family, a hard fail since 2026-09-21: "This attack
    # marks a significant escalation" reached the air because the sanitizer
    # that deletes these words is skipped for audio (brand audit F-13).
    "significant", "significantly", "notable", "importantly", "marks a",
)


# ---------------------------------------------------------------------------
# R-14 grounded attribution and R-15 no unattributed statement of law
# (2026-09-21, brand audit F-02). R-01..R-13 are shape rules; nothing compared
# a rundown line's CLAIM to the summary it was cut from, and the served script
# had turned "Waltz argues the Supreme Court has protected the right to
# publish, but not access to any government facility" into "Waltz argues the
# Supreme Court has protected such actions", then went on in Void's own voice:
# "The Supreme Court has previously protected the government's right to limit
# access to facilities."
# ---------------------------------------------------------------------------
R14_MIN_OVERLAP = 0.6

_STOP_WORDS = frozenset("""
a an the and or but of to in on at for by with from as is are was were be been being has have had
that this these those it its he she they them his her their not no any such all some more most than
then there here which who whom what when where would could should will can may might do does did so
if into over under up out about after before also only just very own other says say said argues argued
states stated describes described calls called according told tells claims claimed contends
""".split())
_PRONOUN_SUBJECTS = frozenset({"he", "she", "it", "they", "we", "i", "you", "this", "that", "there"})
_SPEECH_VERBS = r"says|argues|states|describes|calls"
_ATTRIBUTED_CLAIM_RE = re.compile(
    r"^(?P<who>(?:[A-Z][\w'\u2019.-]*\s+){0,5}[A-Z][\w'\u2019.-]*)\s+(?P<verb>" + _SPEECH_VERBS + r")\s+"
    r"(?:that\s+)?(?P<clause>.+)$"
)
_SOURCE_CLAIM_VERBS = (r"says?|said|argues?|argued|states?|stated|describes?|described|calls?|called|"
                       r"contends?|claims?|claimed|told|tells|maintains?|insists?")
_ATTRIBUTION_ANY_RE = re.compile(
    r"\b(?:" + _SOURCE_CLAIM_VERBS + r"|according to|in (?:his|her|their|its) words|warns?|warned|"
    r"adds?|added|accuses?|accused|denies|denied|announces?|announced)\b", re.I,
)
_LEGAL_SUBJECT_RE = re.compile(
    r"^(?:(?:The|A|An|This|That)\s+)?(?:[\w'\u2019-]+\s+){0,4}?"
    r"(?P<noun>Supreme Court|court|courts|Constitution|law|laws|act|statute|amendment)\s+"
    r"(?:(?:also|previously|now|long|already|still|never)\s+)*"
    r"(?:(?:has|have|had)\s+)?"
    r"(?:(?:also|previously|now|long|already|still|never)\s+)*"
    r"(?:protect(?:s|ed)?|prohibit(?:s|ed)?|allow(?:s|ed)?|permit(?:s|ted)?|forbid(?:s|den)?|forbade|"
    r"bar(?:s|red)?|require(?:s|d)?|guarantee(?:s|d)?|held|holds|upheld|upholds)\b", re.I,
)


def _stem(word: str) -> str:
    w = word.lower().strip("'\u2019.,;:!?\"()")
    for poss in ("\u2019s", "'s"):
        if w.endswith(poss):
            w = w[:-2]
    for suf in ("ations", "ation", "ing", "ies", "edly", "ed", "es", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            w = w[:-len(suf)]
            break
    if len(w) > 4 and w.endswith("y"):
        w = w[:-1]
    return w


def _content_stems(text: str) -> set[str]:
    out = set()
    for tok in re.findall(r"[A-Za-z][\w'\u2019-]*", text or ""):
        low = tok.lower()
        if low in _STOP_WORDS or len(low) < 3:
            continue
        out.add(_stem(low))
    return out


def _cluster_text(row: dict) -> str:
    parts = [str(row.get("title") or ""), str(row.get("summary") or "")]
    for key in ("consensus_points", "divergence_points"):
        val = row.get(key) or []
        if isinstance(val, str):
            parts.append(val)
        else:
            parts.extend(str(x) for x in val)
    return " ".join(parts)


def _rows_for_segment(s: RadioSegment, ctx: RundownContext) -> list[dict]:
    if s.cluster_id:
        own = [row for row in ctx.top20
               if str(row.get("id") or row.get("_db_id") or "").lower() == s.cluster_id.lower()]
        if own:
            return own
    return list(ctx.top20)


def attribution_grounding(who: str, clause: str, rows: list[dict]) -> tuple[float, str] | None:
    """How much of an attributed clause the story it was cut from supports.

    Returns None when the rows carry no summary (nothing to judge against, so
    the rule abstains rather than accuses), else (score, reason). The score is
    the share of the clause's content words found in the rows that name the
    speaker. When the story carries the same speaker's claim, a cut that keeps
    under R14_MIN_OVERLAP of that claim's words while adding a word the story
    never used scores its recall instead: cutting is the job, substitution is
    the defect.
    """
    with_summary = [row for row in rows if (row.get("summary") or "").strip()]
    if not with_summary:
        return None
    tokens = who.split()
    if not tokens or tokens[0].lower() in _PRONOUN_SUBJECTS:
        return None
    surname = tokens[-1].strip("'\u2019.,")
    for poss in ("\u2019s", "'s"):
        if surname.endswith(poss):
            surname = surname[:-2]
    name_re = re.compile(r"\b" + re.escape(surname) + r"\b", re.I)
    named = [t for t in (_cluster_text(row) for row in rows) if name_re.search(t)]
    if not named:
        if len(with_summary) < len(rows):
            return None  # a row with no summary could have named them: abstain
        return 0.0, f"{surname} is not named in the story"
    clause_stems = _content_stems(clause)
    if not clause_stems:
        return None
    pool = " ".join(named)
    pool_stems = _content_stems(pool)
    precision = len(clause_stems & pool_stems) / len(clause_stems)
    if precision < R14_MIN_OVERLAP:
        return precision, f"only {precision:.0%} of the clause is in the story"
    if precision < 1.0:
        source_re = re.compile(
            name_re.pattern + r"[^.!?]*?\b(?:" + _SOURCE_CLAIM_VERBS + r")\b\s+(?:that\s+)?(?P<c>[^.!?]+)", re.I)
        recalls = []
        for m in source_re.finditer(pool):
            stems = _content_stems(m.group("c"))
            if stems:
                recalls.append(len(clause_stems & stems) / len(stems))
        if recalls and max(recalls) < R14_MIN_OVERLAP:
            added = sorted(clause_stems - pool_stems)
            return max(recalls), (f"keeps {max(recalls):.0%} of what {surname} is reported to have said "
                                  f"and adds {added}, which the story never says")
    return precision, "grounded"

_HOST_NAME_ADDRESS_RE = re.compile(r"\bthanks?\b(?!\s+to\b)|\bthank you\b", re.IGNORECASE)
_AMPM_RE = re.compile(r"\b\d{1,2}(?::\d{2})?\s?(?:a\.m\.|p\.m\.|am|pm)(?![\w])", re.IGNORECASE)
_DATELINE_RE = re.compile(r"^[A-Z][A-Z .]{2,}\s*[—–-]\s")
_TRAILING_ATTR_RE = re.compile(
    r",\s*(?:[A-Z][\w.'-]*\s){0,5}(?:said|says|told|added|noted|announced|stated|according to)[^.]{0,40}\.?\s*$")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"“])")
_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)

# ``## STORY 2 | <uuid> | Fed raises rates``  (tolerant: #, ###, **, colons)
_MARKER_RE = re.compile(
    r"^\s*[#*]*\s*(OPEN|MENU|STORY|BRIEFS|FINALLY|CLOSE|SAY)\b\s*(\d+)?\s*[:*]*\s*(?:\|\s*([^|]*?)\s*)?(?:\|\s*(.*?)\s*)?[*]*\s*$",
    re.IGNORECASE,
)
_TURN_RE = re.compile(r"^\s*\**\s*([AB])\s*[:\-–—]\s*\**\s*(.+?)\s*$")
_SAY_RE = re.compile(r"^\s*(.+?)\s*=\s*(.+?)\s*$")


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------

@dataclass
class RadioTurn:
    speaker: Literal["A", "B"]
    text: str

    @property
    def words(self) -> int:
        return len(self.text.split())


@dataclass
class RadioSegment:
    kind: str
    rank: int | None = None          # STORY n (running-order position)
    cluster_id: str | None = None    # resolved from the feed by rank (see resolve_cluster_ids)
    title: str | None = None
    source_rank: int | None = None   # feed rank named in the marker (FINALLY | 15 | title)
    turns: list[RadioTurn] = field(default_factory=list)

    @property
    def words(self) -> int:
        return sum(t.words for t in self.turns)

    @property
    def text(self) -> str:
        return "\n".join(f"{t.speaker}: {t.text}" for t in self.turns)

    @property
    def budget_key(self) -> str:
        if self.kind == "STORY" and self.rank == 1:
            return "STORY1"
        return self.kind


@dataclass
class RadioRundown:
    segments: list[RadioSegment]
    say: dict[str, str]
    raw: str
    warnings: list[str] = field(default_factory=list)

    def story_segments(self) -> list[RadioSegment]:
        return [s for s in self.segments if s.kind == "STORY"]

    def get(self, kind: str) -> RadioSegment | None:
        for s in self.segments:
            if s.kind == kind:
                return s
        return None

    @property
    def words(self) -> int:
        return sum(s.words for s in self.segments)

    def to_text(self) -> str:
        """Canonical serialisation (what gets stored in daily_briefs.audio_script)."""
        out: list[str] = []
        for s in self.segments:
            head = f"## {s.kind}"
            if s.kind == "STORY" and s.rank:
                head += f" {s.rank}"
            if s.kind == "FINALLY" and s.source_rank:
                head += f" | {s.source_rank} | {s.title or ''}"
            elif s.kind == "FINALLY" and s.cluster_id:
                head += f" | {s.cluster_id} | {s.title or ''}"
            elif s.title:
                head += f" | {s.title}"
            out.append(head)
            out.extend(f"{t.speaker}: {t.text}" for t in s.turns)
            out.append("")
        if self.say:
            out.append("## SAY")
            out.extend(f"{k} = {v}" for k, v in self.say.items())
        return "\n".join(out).strip() + "\n"


@dataclass
class RundownContext:
    """What the validators need to know about the day."""
    top20: list[dict]            # rank-ordered rows: id, title, disaster_severity
    has_editorial: bool = True
    date_spoken: str = ""
    editorial_cluster_id: str | None = None   # the opinion's story: never the kicker

    def rank_of(self, cluster_id: str | None) -> int | None:
        if not cluster_id:
            return None
        for i, row in enumerate(self.top20, 1):
            if str(row.get("id") or row.get("_db_id") or "").lower() == cluster_id.lower():
                return i
        return None

    @property
    def lead_severity(self) -> float:
        if not self.top20:
            return 0.0
        try:
            return float(self.top20[0].get("disaster_severity") or 0.0)
        except (TypeError, ValueError):
            return 0.0

    @property
    def kicker_allowed(self) -> bool:
        return self.lead_severity < KICKER_SUPPRESS_SEVERITY


@dataclass
class Finding:
    id: str
    level: Literal["fail", "warn"]
    segment: str
    detail: str

    def as_dict(self) -> dict:
        return {"id": self.id, "level": self.level, "segment": self.segment, "detail": self.detail}


@dataclass
class ValidationReport:
    findings: list[Finding] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not any(f.level == "fail" for f in self.findings)

    @property
    def failures(self) -> list[Finding]:
        return [f for f in self.findings if f.level == "fail"]

    def as_dict(self) -> dict:
        return {"passed": self.passed, "findings": [f.as_dict() for f in self.findings],
                "metrics": self.metrics}

    def named(self) -> str:
        return "\n".join(f"- {f.id} [{f.segment}] {f.detail}" for f in self.findings)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _clean_turn_text(text: str) -> str:
    text = re.sub(r"[*_`#]+", "", text)
    text = re.sub(r"\[[^\]]*\]", "", text)          # stage directions
    return re.sub(r"\s{2,}", " ", text).strip()


def parse_rundown(raw: str) -> RadioRundown:
    """Parse the model's plain text into segments. Never raises.

    Text before the first marker is ignored; unknown lines inside a segment
    that carry no ``A:``/``B:`` tag continue the previous turn (models wrap
    long sentences), except inside ``## SAY`` where they are ``Name = value``.
    """
    segments: list[RadioSegment] = []
    say: dict[str, str] = {}
    warnings: list[str] = []
    current: RadioSegment | None = None
    in_say = False

    for line in (raw or "").splitlines():
        if not line.strip():
            continue
        m = _MARKER_RE.match(line)
        if m and (line.lstrip().startswith("#") or line.strip().upper().startswith(m.group(1).upper())):
            kind = m.group(1).upper()
            if kind == "SAY":
                in_say = True
                current = None
                continue
            in_say = False
            rank = int(m.group(2)) if m.group(2) else None
            # Fields after "|" in any order: a uuid (legacy), an integer feed
            # rank, or the chapter title. Models mis-copy 36-character ids by
            # a hex digit, so ids are RESOLVED from the rank, never trusted.
            cid: str | None = None
            source_rank: int | None = None
            title_parts: list[str] = []
            for fld in (m.group(3), m.group(4)):
                f = (fld or "").strip().strip("*").strip()
                if not f:
                    continue
                if _UUID_RE.fullmatch(f):
                    cid = f.lower()
                elif re.fullmatch(r"(?:rank\s*)?#?(\d{1,2})", f, re.IGNORECASE):
                    source_rank = int(re.sub(r"\D", "", f))
                else:
                    title_parts.append(f)
            title = " ".join(title_parts).strip() or None
            if cid is None:
                found = _UUID_RE.search(line)
                if found:
                    cid = found.group(0).lower()
                    if title and cid in title.lower():
                        title = title.replace(found.group(0), "").strip(" |") or None
            if kind == "STORY" and rank is None:
                rank = len([s for s in segments if s.kind == "STORY"]) + 1
            current = RadioSegment(kind=kind, rank=rank, cluster_id=cid, title=title,
                                   source_rank=source_rank)
            segments.append(current)
            continue
        if in_say:
            sm = _SAY_RE.match(line)
            if sm:
                say[sm.group(1).strip()] = sm.group(2).strip()
            else:
                warnings.append(f"SAY: ignored line {line.strip()[:40]!r}")
            continue
        if current is None:
            continue
        tm = _TURN_RE.match(line)
        if tm:
            text = _clean_turn_text(tm.group(2))
            if text:
                current.turns.append(RadioTurn(speaker=tm.group(1).upper(), text=text))
        elif current.turns:
            current.turns[-1].text = _clean_turn_text(current.turns[-1].text + " " + line.strip())
        else:
            # Untagged first line of a segment: assume the lead voice.
            text = _clean_turn_text(line)
            if text:
                lead = "A" if current.kind in ("OPEN", "MENU", "BRIEFS", "CLOSE") else "A"
                current.turns.append(RadioTurn(speaker=lead, text=text))
                warnings.append(f"{current.kind}: untagged line assigned to {lead}")

    return RadioRundown(segments=segments, say=say, raw=raw or "", warnings=warnings)


# ---------------------------------------------------------------------------
# Validators (stable ids; fail -> one retry, warn -> logged)
# ---------------------------------------------------------------------------

def _seg_label(s: RadioSegment) -> str:
    return f"{s.kind} {s.rank}" if s.kind == "STORY" else s.kind


def _sentences(text: str) -> list[str]:
    return [x for x in _SENTENCE_SPLIT_RE.split(text.strip()) if x.strip()]


def _hamming_close(a: str, b: str, max_diff: int = 3) -> bool:
    if len(a) != len(b):
        return False
    return sum(1 for x, y in zip(a, b) if x != y) <= max_diff


def resolve_cluster_ids(r: RadioRundown, ctx: RundownContext) -> list[str]:
    """Bind every STORY/FINALLY segment to a feed cluster id.

    STORY n is rank n by definition, so its id comes from the feed. FINALLY
    names a feed rank (preferred), or an id that may be a near-miss copy of a
    real one (models drop or flip a hex digit), or nothing usable. Returns
    notes for the validator; never raises.
    """
    notes: list[str] = []
    ids = [str(row.get("id") or row.get("_db_id") or "").lower() for row in ctx.top20]
    for seg in r.segments:
        if seg.kind == "STORY" and seg.rank and 1 <= seg.rank <= len(ids):
            want = ids[seg.rank - 1]
            if seg.cluster_id and seg.cluster_id != want:
                notes.append(f"STORY {seg.rank}: marker id ignored, bound to rank {seg.rank}")
            seg.cluster_id = want
            seg.source_rank = seg.rank
        elif seg.kind == "FINALLY":
            if seg.source_rank and 1 <= seg.source_rank <= len(ids):
                seg.cluster_id = ids[seg.source_rank - 1]
            elif seg.cluster_id:
                if seg.cluster_id not in ids:
                    near = [i for i, x in enumerate(ids) if _hamming_close(x, seg.cluster_id)]
                    if near:
                        notes.append(f"FINALLY: id {seg.cluster_id[:8]} matched rank {near[0] + 1} by near-miss")
                        seg.cluster_id = ids[near[0]]
                if seg.cluster_id in ids:
                    seg.source_rank = ids.index(seg.cluster_id) + 1
            if seg.cluster_id not in ids and seg.title:
                # Last resort: the marker title shares words with one feed title.
                tw = {w.lower().strip(".,'") for w in seg.title.split() if len(w) > 3}
                best, best_n = None, 0
                for i, row in enumerate(ctx.top20):
                    rw = {w.lower().strip(".,'") for w in str(row.get("title") or "").split() if len(w) > 3}
                    n = len(tw & rw)
                    if n > best_n:
                        best, best_n = i, n
                if best is not None and best_n >= 2:
                    notes.append(f"FINALLY: bound to rank {best + 1} by title words")
                    seg.cluster_id = ids[best]
                    seg.source_rank = best + 1
    return notes


def validate_rundown(r: RadioRundown, ctx: RundownContext) -> ValidationReport:
    rep = ValidationReport()
    for note in resolve_cluster_ids(r, ctx):
        r.warnings.append(note)
    F = rep.findings

    def fail(id_: str, seg: str, detail: str) -> None:
        F.append(Finding(id_, "fail", seg, detail))

    def warn(id_: str, seg: str, detail: str) -> None:
        F.append(Finding(id_, "warn", seg, detail))

    # R-01 sign-on
    open_seg = r.get("OPEN")
    if not open_seg or not open_seg.turns:
        fail("R-01", "OPEN", "missing OPEN segment")
    else:
        first = open_seg.turns[0]
        if first.speaker != "A" or not first.text.startswith(SIGN_ON_PREFIX):
            fail("R-01", "OPEN", f"first line must be A: {SIGN_ON_PREFIX!r} ... got {first.speaker}: {first.text[:60]!r}")
        if ctx.date_spoken and ctx.date_spoken.split(",")[0] not in " ".join(t.text for t in open_seg.turns):
            warn("R-01", "OPEN", f"sign-on should name the day ({ctx.date_spoken})")

    close_seg = r.get("CLOSE")
    if not close_seg or not close_seg.turns:
        fail("R-01", "CLOSE", "missing CLOSE segment")
    else:
        text = " ".join(t.text for t in close_seg.turns)
        if not text.startswith(CLOSE_PREFIX):
            fail("R-01", "CLOSE", f"sign-off must start {CLOSE_PREFIX!r}")
        if CLOSE_TAG.rstrip(".") not in text:
            warn("R-01", "CLOSE", f"sign-off should end with {CLOSE_TAG!r}")

    menu = r.get("MENU")
    if menu and menu.turns and not menu.turns[0].text.startswith(MENU_LEAD):
        warn("R-01", "MENU", f"menu should open with {MENU_LEAD!r}")
    briefs = r.get("BRIEFS")
    if briefs and briefs.turns and not briefs.turns[0].text.startswith(BRIEFS_LEAD):
        warn("R-01", "BRIEFS", f"round-up should open with {BRIEFS_LEAD!r}")

    # Per-turn line rules
    all_text_words = 0
    speaker_words = {"A": 0, "B": 0}
    long_sentences = 0
    total_sentences = 0
    for s in r.segments:
        label = _seg_label(s)
        for t in s.turns:
            all_text_words += t.words
            if s.kind != "MENU" or True:
                speaker_words[t.speaker] += t.words
            # R-02 quotation marks. Was advisory (the engine strips the marks
            # anyway) and so changed nothing: the served script of 2026-09-21
            # carried four. A hard fail spends the retry on reported speech;
            # if the retry still carries marks, generate_radio_rundown strips
            # them and re-validates, so punctuation alone never costs the show.
            if has_quotation_marks(t.text):
                fail("R-02", label, f"quotation marks are never read aloud; use reported speech: {t.text[:70]!r}")
            # R-03 numerals (code normalises anyway; warn so the prompt learns)
            if has_numerals(t.text):
                warn("R-03", label, f"numerals present (will be spoken by the normaliser): {t.text[:70]!r}")
            # R-04 clock forms and datelines
            if _AMPM_RE.search(t.text):
                fail("R-04", label, f"no a.m./p.m. clock forms; say 'this morning'/'overnight': {t.text[:70]!r}")
            if _DATELINE_RE.match(t.text):
                fail("R-04", label, f"print dateline has no spoken form: {t.text[:40]!r}")
            # R-05 banned phrases and host addressing
            low = t.text.lower()
            for phrase in BANNED_PHRASES:
                if re.search(r"(?<![\w'])" + re.escape(phrase) + r"(?![\w])", low):
                    fail("R-05", label, f"banned phrase {phrase!r}: {t.text[:70]!r}")
                    break
            if _HOST_NAME_ADDRESS_RE.search(t.text):
                fail("R-05", label, f"hosts are never addressed by name or thanked: {t.text[:70]!r}")
            # R-07 attribution after the claim, R-11 sentence length (per sentence)
            for sent in _sentences(t.text):
                if _TRAILING_ATTR_RE.search(sent):
                    warn("R-07", label, f"put attribution before the claim ('X says ...'): {sent[-70:]!r}")
                total_sentences += 1
                n = len(sent.split())
                if n > 28:
                    warn("R-11", label, f"{n}-word sentence; one idea per sentence, under twenty words: {sent[:60]!r}")
                if n > 20:
                    long_sentences += 1
    if total_sentences and long_sentences / total_sentences > 0.10:
        warn("R-11", "ALL", f"{long_sentences}/{total_sentences} sentences over twenty words")

    # R-06 budgets
    for s in r.segments:
        lo, hi = WORD_BUDGETS.get(s.budget_key, (0, 10 ** 6))
        w = s.words
        label = _seg_label(s)
        if w < lo * 0.75 or w > hi * 1.25:
            fail("R-06", label, f"{w} words; budget {lo}-{hi}")
        elif w < lo or w > hi:
            warn("R-06", label, f"{w} words; budget {lo}-{hi}")
    if menu:
        heads = [t for t in menu.turns if not t.text.startswith(MENU_LEAD)]
        if len(heads) != 5:
            fail("R-06", "MENU", f"{len(heads)} headline lines; exactly five, one per line")
        for t in heads:
            if t.words > MENU_HEADLINE_MAX_WORDS:
                warn("R-06", "MENU", f"{t.words}-word headline; keep to {MENU_HEADLINE_MAX_WORDS}: {t.text!r}")
    if briefs:
        items = [t for t in briefs.turns if not t.text.startswith(BRIEFS_LEAD)]
        if not (BRIEF_ITEMS[0] <= len(items) <= BRIEF_ITEMS[1]):
            fail("R-06", "BRIEFS", f"{len(items)} items; {BRIEF_ITEMS[0]}-{BRIEF_ITEMS[1]} one-line items")
        for t in items:
            if t.words > BRIEF_ITEM_MAX_WORDS + 6:
                warn("R-06", "BRIEFS", f"{t.words}-word item; one sentence, under {BRIEF_ITEM_MAX_WORDS}: {t.text[:60]!r}")
    total = r.words
    if total < TOTAL_BUDGET[0] * 0.85 or total > TOTAL_BUDGET[1] * 1.15:
        fail("R-06", "ALL", f"{total} words total; budget {TOTAL_BUDGET[0]}-{TOTAL_BUDGET[1]}")

    # R-08 story identity and order
    stories = r.story_segments()
    if len(stories) != DEEP_STORIES:
        fail("R-08", "STORY", f"{len(stories)} STORY segments; exactly {DEEP_STORIES} (ranks 1-{DEEP_STORIES})")
    for i, s in enumerate(stories, 1):
        label = _seg_label(s)
        if s.rank != i:
            fail("R-08", label, f"stories must run 1..{DEEP_STORIES} in rank order")
        if not s.cluster_id:
            fail("R-08", label, f"no feed story at rank {i}")
        if not s.title:
            warn("R-08", label, "missing chapter title in the marker")
        elif len(s.title.split()) > 8:
            warn("R-08", label, f"chapter title over six words: {s.title!r}")
    fin = r.get("FINALLY")
    if fin:
        rk = ctx.rank_of(fin.cluster_id) if fin.cluster_id else None
        if rk is None:
            fail("R-08", "FINALLY", "the kicker marker must name the story's feed rank (## FINALLY | <rank> | <title>)")
        elif rk <= DEEP_STORIES:
            fail("R-08", "FINALLY", f"kicker is rank {rk}, already told in depth; pick from ranks {DEEP_STORIES + 1}-{len(ctx.top20)}")
        if fin.cluster_id and ctx.editorial_cluster_id and fin.cluster_id.lower() == ctx.editorial_cluster_id.lower():
            fail("R-08", "FINALLY", "the kicker is the opinion's own story; the opinion follows it, pick another")

    # R-09 kicker suppression
    if fin and not ctx.kicker_allowed:
        fail("R-09", "FINALLY", f"lead story disaster severity {ctx.lead_severity:.1f}; no lighter last item today")
    if not fin and ctx.kicker_allowed and len(ctx.top20) > DEEP_STORIES:
        warn("R-09", "FINALLY", "no FINALLY segment on a day that allows one")

    # R-10 speaker balance
    news_words = speaker_words["A"] + speaker_words["B"]
    if news_words:
        share_a = speaker_words["A"] / news_words
        rep.metrics["speaker_share_a"] = round(share_a, 2)
        if share_a < 0.35 or share_a > 0.65:
            fail("R-10", "ALL", f"voice A carries {share_a:.0%} of the words; keep both voices between 35 and 65 percent")

    # R-12 alternation
    prev_lead = None
    for s in stories:
        if not s.turns:
            continue
        lead = s.turns[0].speaker
        label = _seg_label(s)
        if prev_lead is not None and lead == prev_lead:
            fail("R-12", label, "lead voice must alternate story by story")
        others = [t for t in s.turns if t.speaker != lead]
        if len(others) > 1:
            fail("R-12", label, f"the second voice adds at most one line inside a story ({len(others)} found)")
        prev_lead = lead

    # R-13 SAY hygiene
    body = " ".join(t.text for s in r.segments for t in s.turns)
    for k in list(r.say):
        if k not in body:
            warn("R-13", "SAY", f"respelling for {k!r} but the word never appears; dropped")
            r.say.pop(k)
    if len(r.say) > 12:
        warn("R-13", "SAY", f"{len(r.say)} respellings; keep to the hard names")

    # R-14 grounded attribution, R-15 no unattributed statement of law
    for s in r.segments:
        if s.kind not in ("STORY", "BRIEFS", "FINALLY"):
            continue
        label = _seg_label(s)
        rows = _rows_for_segment(s, ctx)
        for t in s.turns:
            attributed_earlier = False
            for sent in _sentences(t.text):
                m = _ATTRIBUTED_CLAIM_RE.match(sent)
                if m:
                    verdict = attribution_grounding(m.group("who"), m.group("clause"), rows)
                    if verdict is not None and verdict[0] < R14_MIN_OVERLAP:
                        fail("R-14", label, f"attributed claim not what the story says ({verdict[1]}): {sent[:90]!r}")
                attributed_here = bool(_ATTRIBUTION_ANY_RE.search(sent))
                if _LEGAL_SUBJECT_RE.match(sent) and not attributed_here and not attributed_earlier:
                    fail("R-15", label, f"a court or a law stated in Void's own voice; say who says so: {sent[:90]!r}")
                attributed_earlier = attributed_earlier or attributed_here

    for w in r.warnings:
        warn("R-00", "PARSE", w)

    rep.metrics.update({
        "words": total,
        "est_minutes": round(total / SPEECH_WPM, 1),
        "segments": [{"kind": _seg_label(s), "words": s.words, "est_seconds": round(s.words / SPEECH_WPM * 60)}
                     for s in r.segments],
        "stories": len(stories),
        "kicker": bool(fin),
    })
    return rep


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM = """You write the daily radio rundown for On Air, the audio edition of Void News: an independent, source-transparent news product. Two voices read it: voice A anchors; voice B takes alternate stories and adds single facts. The voices are never named and never address each other.

You write for the EAR, in the manner of a trained radio newsreader, not for the page:
- One idea per sentence. Under twenty words. Subject, verb, object. Never open a sentence with a subordinate clause.
- Present tense or present perfect for what is happening: "The central bank has raised rates." Never "raised rates yesterday".
- Attribution BEFORE the claim: "The Fed chair says inflation has run too high for too long." Never a trailing ", she said."
- No quotation marks, ever, not even around a nickname or a slogan. Report speech: "the staff call her Yoko Ono", "he called the idea a hostile act". If one phrase matters, say "in his words" and then the phrase, without marks.
- Numbers are words, rounded: "almost four billion dollars", "three and three-quarter percent", "about thirty-one tonnes". Never digits, never symbols.
- No a.m. or p.m., no clock times unless they carry the story; say "this morning", "overnight", "on Wednesday".
- No print datelines. "In Washington," not "WASHINGTON —".
- Initialisms read as letters are hyphenated: "the F-B-I", "the E-U", "the U-S". Words stay words: NATO, OPEC.
- Every fact MUST appear in the provided articles. Do not supplement with prior knowledge. Never invent a number, a name or a quote.
- When you attribute a claim ("X says", "X argues"), the clause after the verb is what the story reports X said: cut it, never reword it. A court, a law or the Constitution never does anything in your own voice; say who says so.
- Show, don't tell. Never "significant", "notable", "interestingly", "crucially", "it should be noted". Concrete facts, then stop.
- No editorialising in the news segments. No reactions between the voices ("Wow.", "That's fascinating."). No thanks, no names, no "over to you".
- Em dashes are allowed only as a spoken pause mark, sparingly.

Output PLAIN TEXT in exactly the marker format the instructions specify. No JSON, no markdown fences, no commentary before or after."""

_USER_TEMPLATE = """Today is {DATE_SPOKEN}. Write the On Air rundown from these stories, which are ranked 1 to {N} by today's editorial ranking. Ranks 1-4 get full treatment, ranks 5-12 get one line each, ranks 13-{N} are context only and are not read.

STORIES
{STORIES}

FORMAT. Reproduce these markers exactly, in this order. Every spoken line starts with "A:" or "B:". Nothing else is spoken.

## OPEN
A: {SIGN_ON} It's {DATE_SPOKEN}. <one more sentence at most: the single fact of the day that sets the tone, present tense, no adjectives>

## MENU
A: {MENU_LEAD}
A: <headline for rank 1: one sentence, present tense, at most twelve words, no numbers as digits>
B: <headline for rank 2>
A: <headline for rank 3>
B: <headline for rank 4>
A: <headline for rank 5>

## STORY 1 | <chapter title, at most six words>
A: <the lead story in depth: {STORY1_LO}-{STORY1_HI} words over several A: lines, each line two to four sentences. Open on the newest fact. Then what happened, who says what, what is disputed, what happens next.>
B: <exactly ONE line: a new fact the lead did not give (a number, a date, a counter-claim from a named source). Not a reaction.>

## STORY 2 | <title>
B: <{STORY_LO}-{STORY_HI} words over several B: lines. Open with a one-clause bridge that orients in place or subject ("In Washington," / "To the markets," / "Staying with Europe,"), then the facts.>
A: <ONE new-fact line, optional>

## STORY 3 | <title>
A: <{STORY_LO}-{STORY_HI} words>
B: <ONE new-fact line, optional>

## STORY 4 | <title>
B: <{STORY_LO}-{STORY_HI} words>
A: <ONE new-fact line, optional>

## BRIEFS
A: {BRIEFS_LEAD}
A: <rank 5 in ONE sentence of at most twenty-two words>
A: <rank 6 in one sentence>
B: <rank 7>
B: <rank 8>
A: <rank 9>
A: <rank 10>
B: <rank 11, optional>
B: <rank 12, optional>

{FINALLY_BLOCK}
## CLOSE
A: {CLOSE_PREFIX} <one concrete detail from today's stories the listener will still be thinking about tomorrow: a number, a name, an unresolved outcome. Not a teaser, not a summary.> {CLOSE_TAG}

## SAY
<zero to six lines, only for names a reader would otherwise get wrong. Lowercase syllables joined by hyphens, no capitals (capitals are read as initials): "Hormuz = hor-mooz", "Nunez = noo-nyez". Never respell a common English name.>
Name = respelling
{PREVIOUS_MENU}
RULES THAT FAIL THE SCRIPT IF BROKEN
- The first spoken line is exactly "A: {SIGN_ON} It's {DATE_SPOKEN}." followed by at most one sentence.
- Exactly four STORY segments, ranks 1 to 4, in order: STORY 1 is story [1], STORY 2 is story [2], and so on. The FINALLY marker names the story's number from the list.
- Voice B leads STORY 2 and STORY 4; voice A leads STORY 1 and STORY 3. Inside a story the other voice speaks at most once.
- No quotation marks anywhere. No digits anywhere. No a.m./p.m.
- Never these phrases: "Up first", "Here's what we're covering", "First the headlines", "And that's the headlines", "these are our main stories", "Stay with us", "And finally", "Welcome", "Thanks", "Absolutely", "Wow".
- Total news length {TOTAL_LO} to {TOTAL_HI} words. The length comes from covering the four lead stories properly, not from padding.
{RETRY}"""

_FINALLY_TEMPLATE = """## FINALLY | <the NUMBER of a lighter story from [5] to [{N}]: culture, science, sport, an oddity; never a death, a war, a disaster, and never the opinion's story{EXCLUDE}> | <title>
B: <{KICKER_LEAD} then two to four sentences, {FINALLY_LO}-{FINALLY_HI} words, plainly told, ending on the fact rather than a joke>
"""


def build_stories_block(top20: list[dict]) -> str:
    lines: list[str] = []
    for i, c in enumerate(top20, 1):
        title = (c.get("title") or "").strip()
        summary = (c.get("summary") or "").strip()
        if len(summary) > 700:
            summary = summary[:697] + "..."
        consensus = c.get("consensus_points") or []
        divergence = c.get("divergence_points") or []
        cat = c.get("category") or ""
        sev = c.get("disaster_severity") or 0
        cid = c.get("id") or c.get("_db_id") or ""
        tier = "in depth" if i <= DEEP_STORIES else ("one line" if i <= BRIEF_RANKS[1] else "context only")
        lines.append(f"[{i}] ({c.get('source_count', 0)} sources, {cat}, severity {float(sev):.1f}) {tier}: {title}")
        if summary:
            lines.append(f"    Summary: {summary}")
        if consensus and isinstance(consensus, list) and i <= BRIEF_RANKS[1]:
            lines.append(f"    Consensus: {'; '.join(str(x) for x in consensus[:3])}")
        if divergence and isinstance(divergence, list) and i <= DEEP_STORIES:
            lines.append(f"    Divergence: {'; '.join(str(x) for x in divergence[:2])}")
        lines.append("")
    return "\n".join(lines)


def build_radio_prompt(
    top20: list[dict],
    date_spoken: str,
    *,
    has_editorial: bool = True,
    previous_menu: list[str] | None = None,
    retry_findings: str = "",
    editorial_cluster_id: str | None = None,
) -> tuple[str, str]:
    ctx = RundownContext(top20=top20, has_editorial=has_editorial, date_spoken=date_spoken,
                         editorial_cluster_id=editorial_cluster_id)
    n = len(top20)
    if ctx.kicker_allowed and n > DEEP_STORIES:
        exclude = ""
        if editorial_cluster_id:
            erank = ctx.rank_of(editorial_cluster_id)
            exclude = f" (story [{erank}])" if erank else ""
        finally_block = _FINALLY_TEMPLATE.format(N=n, KICKER_LEAD=KICKER_LEADS[0], EXCLUDE=exclude,
                                                FINALLY_LO=WORD_BUDGETS["FINALLY"][0],
                                                FINALLY_HI=WORD_BUDGETS["FINALLY"][1])
    else:
        finally_block = "(No FINALLY segment today: the lead story is a mass-casualty event.)\n"
    prev = ""
    if previous_menu:
        prev = ("\nYESTERDAY'S MENU (do not reuse these headline phrasings):\n" +
                "\n".join(f"- {h}" for h in previous_menu[:5]) + "\n")
    retry = ""
    if retry_findings:
        retry = ("\nYOUR PREVIOUS ATTEMPT FAILED THESE CHECKS. Fix every one of them and return the whole rundown again:\n"
                 + retry_findings + "\n")
    user = _USER_TEMPLATE.format(
        DATE_SPOKEN=date_spoken, N=n, STORIES=build_stories_block(top20),
        SIGN_ON=SIGN_ON_PREFIX, MENU_LEAD=MENU_LEAD, BRIEFS_LEAD=BRIEFS_LEAD,
        CLOSE_PREFIX=CLOSE_PREFIX, CLOSE_TAG=CLOSE_TAG,
        FINALLY_BLOCK=finally_block, PREVIOUS_MENU=prev, RETRY=retry,
        # The prompt's word budgets used to be typed into the template by hand
        # while the validator read WORD_BUDGETS, so the two drifted: the model
        # was being asked for one length and marked against another. They now
        # come from the same constants, and a test asserts the rendered prompt
        # carries these numbers.
        STORY1_LO=WORD_BUDGETS["STORY1"][0], STORY1_HI=WORD_BUDGETS["STORY1"][1],
        STORY_LO=WORD_BUDGETS["STORY"][0], STORY_HI=WORD_BUDGETS["STORY"][1],
        TOTAL_LO=f"{TOTAL_BUDGET[0]:,}", TOTAL_HI=f"{TOTAL_BUDGET[1]:,}",
    )
    return _SYSTEM, user


# ---------------------------------------------------------------------------
# Generation (one call, one retry)
# ---------------------------------------------------------------------------

def _gemini():
    try:
        from summarizer.gemini_client import (
            generate_text, is_available, _FLASH_MODEL,
        )
        return generate_text, is_available, _FLASH_MODEL
    except ImportError:  # pragma: no cover
        return None, (lambda: False), None


def generate_radio_rundown(
    top20: list[dict],
    *,
    has_editorial: bool = True,
    previous_menu: list[str] | None = None,
    date: datetime | None = None,
    max_attempts: int = 2,
    generate_fn=None,
    editorial_cluster_id: str | None = None,
) -> tuple[RadioRundown | None, ValidationReport | None, str]:
    """Return (rundown, report, generator_label); rundown is None on failure.

    ``generate_fn(system, user) -> str | None`` can be injected for tests and
    dry runs; by default this is one Gemini flash call per attempt.
    """
    generate_text, is_available, flash_model = _gemini()
    date = date or datetime.now(timezone.utc)
    date_spoken = spoken_date(date)
    ctx = RundownContext(top20=top20, has_editorial=has_editorial, date_spoken=date_spoken,
                         editorial_cluster_id=editorial_cluster_id)

    if generate_fn is None:
        if not generate_text or not is_available():
            print("  [radio] Gemini unavailable; no rundown")
            return None, None, "none"

        def generate_fn(system: str, user: str) -> str | None:  # noqa: E306
            return generate_text(user, system_instruction=system, count_call=False,
                                 max_output_tokens=8192, model=flash_model)

    findings = ""
    best: tuple[RadioRundown, ValidationReport] | None = None
    for attempt in range(max_attempts):
        system, user = build_radio_prompt(top20, date_spoken, has_editorial=has_editorial,
                                          previous_menu=previous_menu, retry_findings=findings,
                                          editorial_cluster_id=editorial_cluster_id)
        raw = generate_fn(system, user)
        if not raw or not raw.strip():
            print(f"  [radio] attempt {attempt + 1}: empty response")
            continue
        rundown = parse_rundown(raw)
        report = validate_rundown(rundown, ctx)
        n_fail = len(report.failures)
        print(f"  [radio] attempt {attempt + 1}: {rundown.words} words, {len(rundown.segments)} segments, "
              f"{n_fail} fail / {len(report.findings) - n_fail} warn")
        for f in report.findings:
            print(f"    [radio] {f.id} {f.level:4} [{f.segment}] {f.detail[:110]}")
        if report.passed:
            return rundown, report, "gemini-flash"
        if best is None or n_fail < len(best[1].failures):
            best = (rundown, report)
        findings = "\n".join(f"- {f.id} [{f.segment}] {f.detail}" for f in report.failures)

    if best is not None:
        rundown, report = best
        if report.failures and all(f.id == "R-02" for f in report.failures):
            # The retry was spent asking for reported speech. Once it is gone
            # the marks are punctuation the engine drops anyway, so strip and
            # re-validate rather than lose the show to them.
            for s in rundown.segments:
                for t in s.turns:
                    t.text = strip_quotation_marks(t.text)
            report = validate_rundown(rundown, ctx)
            if report.passed:
                print("  [radio] quotation marks stripped after the retry; script accepted")
                return rundown, report, "gemini-flash"
        print(f"  [radio] no attempt passed; best had {len(report.failures)} failures")
        return None, report, "gemini-flash-rejected"
    return None, None, "none"
