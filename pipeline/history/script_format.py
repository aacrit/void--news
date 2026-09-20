"""The History audio script format: parser and validators.

A History script is authored by hand and committed as data (see
docs/HISTORY-AUDIO.md for why it is not generated). This module is the
contract between that prose and the renderer.

    ## OPEN | TITLE | SCENE n | <title> | ASIDE | TURN | CLOSE
    ## DOCUMENT | <author> | <work> | <date>
    N: narrator line
    D: document line (only inside a DOCUMENT segment)
    ## SAY
    Radcliffe = RAD-kliff

The validators exist because one failure in a history programme is
unrecoverable: a quotation the source never said. H-01 makes that
structurally impossible by checking every D: line against the event's own
`primary_source_excerpts`. A script that invents a quote does not render.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

# N narrates. M and F read quoted speech, matched to the SPEAKER'S SEX: a
# woman reading Nehru is jarring, and sex-matched readers are the documentary
# convention the format is modelled on (Ken Burns narrates in one voice and
# casts actors per source). The script declares it rather than the renderer
# guessing from a name, because guessing sex from names fails on exactly the
# cases that matter: Azad, Jucunda, anonymous testimony.
SPEAKERS = ("N", "M", "F")
QUOTE_SPEAKERS = ("M", "F")
KINDS = ("OPEN", "TITLE", "SCENE", "DOCUMENT", "PERSPECTIVE", "ASIDE", "TURN",
         "REST", "CLOSE")
# A REST carries no words. It is a held musical pause, placed by the writer
# where the listener needs somewhere to put what they have just heard: after a
# document that lands hard, before the accounts begin, before the close. A
# documentary that never stops talking gives the audience no room to feel
# anything, and the silence is part of the writing, not a gap in it.
# Segments in which the document voice may speak: a primary source, or a
# perspective quoting its own witness.
QUOTING = ("DOCUMENT", "PERSPECTIVE", "ASIDE")
WPM = 145.0                      # the catalogue average, used when the cast is unknown
# Narrators do NOT read at one rate, and casting is deterministic from the
# event, so the difference is predictable rather than noise. Measured over all
# 39 rendered episodes as words / (rendered minutes - MUSIC_MINUTES):
#
#   am_michael  n=15  139.4 wpm (sd 4.2)      bm_lewis   n=12  146.1 (sd 4.0)
#   bm_george   n= 9  145.0 wpm (sd 4.4)      bm_daniel  n= 3  168.4 (sd 4.6)
#
# bm_lewis was 148.0 at n=9 and settled to 146.1 as three more of its episodes
# landed, which is what a small sample does. The others moved by less than a
# word.
#
# bm_daniel reads a fifth faster than am_michael. Against one constant that is
# a two minute error at episode length, in opposite directions, so an
# am_michael script written to the top of the band renders OVER the ceiling
# while a bm_daniel script written the same way comes in two minutes short.
# Using the cast rate took the worst error, measured on the 33 episodes that
# existed when the rule was written, from 2.1 minutes to 0.8, and it caught a
# written but unrendered script that would
# have come out at 15.1 minutes, before the nine minutes of rendering that
# would have been the only other way to find out.
#
# bm_daniel rests on three episodes and always will: it is cast only for
# `category: cultural`, all three of those events are already rendered, and
# none of the events still to be written casts it. So this is not a number
# waiting for more evidence. It is the number, on three samples, and a
# cultural event added to the catalogue later is the only thing that would
# change that.
NARRATOR_WPM = {
    "am_michael": 140.0,
    "bm_george": 145.0,
    "bm_lewis": 146.0,
    "bm_daniel": 168.0,
}
# An event with five substantial perspectives cannot state all five fairly
# inside ten minutes, and stating them fairly is the whole point of the
# catalogue, so the band is wide enough to pay for the moat.
TARGET_MINUTES = (8.0, 15.0)
AUDIO_GATE_MINUTES = 15.5        # what tests/test_history_audio.py rejects
MUSIC_MINUTES = 1.1              # theme, scene stings, outro

# Non-speech time is NOT a constant. The silence grammar in history_producer
# spends its gaps PER SEGMENT (scene 1600 ms, to_perspective 2200, to_turn
# 2400, a REST longer still), so a 35-segment episode carries far more silence
# than a 20-segment one carrying the same words. Treating it as a constant is
# why four episodes shipped over the 15 minute format ceiling while estimating
# comfortably under it, and why september-11-attacks estimated 14.5 and
# rendered 15.9, failing the audio gate after nine minutes of rendering.
#
# Measured across 49 rendered episodes: corr(error, segment count) = +0.63,
# slope 5.3 s per segment. Anchoring the correction at the catalogue's mean
# segment count keeps the constant physical; the equivalent y-intercept is
# negative, which is an artefact of fitting inside a 20-35 segment range and
# is never used directly.
#
# Mean absolute error 0.35 -> 0.26 min, worst 1.07 -> 0.89, and episodes
# landing within half a minute of their real runtime 39/49 -> 43/49.
SEGMENT_MINUTES = 0.0883         # 5.3 s of silence per segment
SEGMENT_REFERENCE = 24.5         # catalogue mean; correction is zero here
MIN_OVERHEAD_MINUTES = 0.6       # the theme and the outro play at any length


def _overhead_minutes(n_segments: int) -> float:
    """Non-speech minutes for a script with this many segments.

    Linear in segment count, anchored at the catalogue mean so the constant
    stays physical. Floored, because the fit is only observed between 20 and 35
    segments and extrapolating below that goes negative, which would let a
    short script claim a runtime shorter than its own theme music.
    """
    return max(MIN_OVERHEAD_MINUTES,
               MUSIC_MINUTES + SEGMENT_MINUTES * (n_segments - SEGMENT_REFERENCE))


@dataclass
class Line:
    speaker: str          # N | M | F
    text: str


@dataclass
class Segment:
    kind: str
    title: str | None = None
    author: str | None = None
    work: str | None = None
    date: str | None = None
    lines: list[Line] = field(default_factory=list)

    @property
    def words(self) -> int:
        return sum(len(l.text.split()) for l in self.lines)


@dataclass
class Script:
    slug: str
    segments: list[Segment] = field(default_factory=list)
    say: dict[str, str] = field(default_factory=dict)

    @property
    def words(self) -> int:
        return sum(s.words for s in self.segments)

    @property
    def minutes(self) -> float:
        return self.words / WPM + _overhead_minutes(len(self.segments))


@dataclass
class Finding:
    id: str
    level: str          # "fail" | "warn"
    segment: str
    detail: str


def parse_script(raw: str, slug: str = "") -> Script:
    """Never raises: a malformed script becomes findings, not a traceback."""
    script = Script(slug=slug)
    cur: Segment | None = None
    in_say = False
    for line in raw.splitlines():
        line = line.rstrip()
        if line.startswith("## "):
            head = [p.strip() for p in line[3:].split("|")]
            kind = head[0].split()[0].upper() if head[0] else ""
            if kind == "SAY":
                in_say = True
                cur = None
                continue
            in_say = False
            cur = Segment(kind=kind)
            if kind == "DOCUMENT":
                cur.author = head[1] if len(head) > 1 else None
                cur.work = head[2] if len(head) > 2 else None
                cur.date = head[3] if len(head) > 3 else None
            elif len(head) > 1:
                cur.title = head[1]
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
    """Strip accents. The event records spell names as the sources do
    (Hernan Cortes is Hernán Cortés there); the scripts spell them for a
    speech synthesiser. They are the same name and must compare equal."""
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", _fold(s).lower())


def estimated_minutes(script: Script, event: dict | None) -> tuple[float, float, str]:
    """Runtime for THIS script read by the narrator this event casts.

    Returns (minutes, wpm, who). Falls back to the catalogue average when the
    event is missing or its narrator has no measured rate yet, so a new voice
    degrades to the old behaviour instead of raising.
    """
    who, rate = "the cast", WPM
    if event:
        try:
            from history.casting import cast
            who = cast(event).get("narrator") or who
            rate = NARRATOR_WPM.get(who, WPM)
        except Exception:
            pass
    return script.words / rate + _overhead_minutes(len(script.segments)), rate, who


def _best_source(said: str, sourced) -> tuple[str, str] | None:
    """The source this quote matches BEST, not the first one over the line.

    Taking the first match above threshold misattributes a quote whenever a
    weaker match happens to sit earlier in the event file, and H-04 then checks
    the narration against the wrong speaker. Two drafters hit this
    independently on real data:

      "Both sides declared victory over a war that returned them to the
       border where it began"
          1.000 against its true source
          0.667 against Khomeini's "War, war until victory", which is earlier
                and shares only "war" and "victory"

      "To the strongest"
          1.000 against its true source
          0.667 against an unrelated Plutarch paraphrase, which is earlier

    Both were silently resolved to the wrong speaker. Scoring every candidate
    and keeping the highest costs one pass over a handful of quotes.
    """
    best, best_score = None, 0.0
    for src, who in sourced:
        if not src:
            continue
        if said in src or src in said:
            score = 1.0
        else:
            score = _overlap(said, src)
        if score > 0.6 and score > best_score:
            best, best_score = (src, who), score
    return best


def validate_script(script: Script, event: dict) -> list[Finding]:
    """Check a script against the EVENT DATA it was written from."""
    out: list[Finding] = []
    excerpts = event.get("primary_source_excerpts") or []
    quotes = [q for p in (event.get("perspectives") or [])
              for q in (p.get("notable_quotes") or [])]
    # The hedge is not always in the speaker field. Four drafters, on four
    # unrelated events, found a record whose speaker reads as a clean name
    # while its CONTEXT or WORK field carries the disclaimer: "Reported by
    # Anthony Nutting in No End of a Lesson", "as recorded by Capuchin
    # missionaries", "Paraphrased from scholarship", "Attributed". H-11 read
    # only the speaker, so each of those would have passed the gate as direct
    # speech. Every one was caught by a writer reading the data instead, which
    # is not a control. Carry all three fields and hedge on any of them.
    # H-04 needs the speaker's NAME and nothing else, so it stays clean here.
    # H-11 needs everything the record says ABOUT the attribution, so it gets a
    # parallel lookup. Folding both into one string broke H-04, which then
    # demanded the narration say "Anonymous Gesta Francorum (Deeds of the
    # Franks)" out loud.
    sourced = [(_norm(e.get("text", "")), e.get("author", "")) for e in excerpts]
    sourced += [(_norm(q.get("text", "")), q.get("speaker", "")) for q in quotes]

    def _attrib(d: dict, name_key: str) -> str:
        return " ".join(str(d.get(k) or "") for k in (name_key, "context", "work"))

    ATTRIBUTION = {_norm(e.get("text", "")): _attrib(e, "author") for e in excerpts}
    ATTRIBUTION.update({_norm(q.get("text", "")): _attrib(q, "speaker") for q in quotes})

    # A source whose own speaker field says the words are not verbatim. The
    # record marks these; nothing read them before H-11. "summary" is NOT here:
    # a record that calls its source a "reactor-safety summary" is describing
    # what the document IS, not hedging whose words it carries.
    HEDGED = ("paraphras", "attributed", "reconstruct", "apocryph", "legend",
              # Secondhand: the record names a person who wrote the words down,
              # not the person who said them. A listener told "Alexander said"
              # deserves to know Plutarch wrote it four centuries later. Six
              # such records exist across the 78 events.
              "recount", "as reported by", "as told to", "quoted in",
              "quoted by", "via",
              # Rendered or imagined in someone else's voice. Thucydides
              # reconstructed the speeches he reports, and five of the eight
              # such records in the catalogue are his; Mark Twain wrote a
              # satire in Leopold's voice. Read in the document voice with no
              # word said, both become a real person's quotation.
              "(as ", "in the voice of", "imagin", "satir")
    # The same hedge, said out loud. A script that tells the listener the words
    # are attributed has done the honest thing, whether it says so in the
    # DOCUMENT marker or in the narration that introduces the quote.
    # Said out loud. Every term that marks a record as hedged counts here too:
    # a script that uses the record's own word for the thing has disclosed it.
    # Keeping the two lists separate meant three separate occasions where an
    # honest script failed because the gate did not know the word it chose
    # ("wrote down what Mellon told him", "a satire imagining what Leopold
    # would say", "Sima Qian wrote his report down two generations later"), so
    # the spoken list is now the marked list plus the ways people say it.
    SPOKEN_HEDGE = tuple(h.strip(" (") for h in HEDGED) + (
        "said to", "reputed", "tradition holds", "by tradition",
        "is remembered", "remembered for", "later recorded",
        "recorded generations", "as reported", "as told", "as recorded",
        "recorded by", "rendered by", "wrote down", "set down", "records that")

    kinds = [s.kind for s in script.segments]
    for required in ("OPEN", "CLOSE"):
        if required not in kinds:
            out.append(Finding("H-05", "fail", required, f"no {required} segment"))
    if "TURN" not in kinds:
        out.append(Finding("H-06", "fail", "TURN", "no TURN: the episode never shows the disagreement"))

    for seg in script.segments:
        label = f"{seg.kind}{' ' + seg.title if seg.title else ''}"
        d_lines = [l for l in seg.lines if l.speaker in QUOTE_SPEAKERS]
        if seg.kind not in QUOTING and d_lines:
            out.append(Finding("H-02", "fail", label, "document voice speaks outside a DOCUMENT segment"))
        if seg.kind in ("DOCUMENT", "PERSPECTIVE", "ASIDE") and d_lines:
            if seg.kind == "DOCUMENT" and not seg.author:
                out.append(Finding("H-03", "fail", label, "DOCUMENT has no author in its marker"))
            # H-04: the narrator must NAME THE SPEAKER before the voice reads.
            # Checking merely that some narration came first is not enough: a
            # perspective states its argument before it quotes, so that test
            # passes even when nobody is named. The speaker's name is looked up
            # from the data by matching the quote, so the rule holds wherever a
            # quote appears and does not depend on the marker being filled in.
            for i, l in enumerate(seg.lines):
                if l.speaker not in QUOTE_SPEAKERS:
                    continue
                said = _norm(l.text)
                _m = _best_source(said, sourced)
                speaker = _m[1] if _m else None
                before = " ".join(_norm(x.text) for x in seg.lines[:i] if x.speaker == "N")
                if not before:
                    out.append(Finding("H-04", "fail", label,
                                       "a quote is read with no narration before it: the listener "
                                       "hears words without knowing whose they are"))
                elif speaker:
                    named = [w for w in _norm(speaker).split() if len(w) > 3 and w != "anonymous"]
                    # Match on WORDS, not on raw substrings. "king" is inside
                    # "striking", and a segment that happens to use the word
                    # striking is not a segment that named Martin Luther King.
                    # A leading-edge match is still allowed in both directions
                    # so a possessive ("Khomeini's") names Khomeini.
                    words = before.split()
                    def _names(w: str) -> bool:
                        return any(x == w or x.startswith(w) or w.startswith(x)
                                   for x in words if len(x) > 3)
                    if named and not any(_names(w) for w in named):
                        out.append(Finding("H-04", "fail", label,
                                           f"the narration before this quote never names {speaker}"))
            # H-01: the quote must exist in the event's own sources.
            for l in d_lines:
                said = _norm(l.text)
                match = _best_source(said, sourced)
                if match is None:
                    out.append(Finding("H-01", "fail", label,
                                       f"quotation not found in this event's primary sources: "
                                       f"{l.text[:70]!r}"))
                    continue
                # H-11: the record sometimes carries a line whose own speaker
                # field says it is NOT that person's words: "Patricia Crone
                # (paraphrased)", an attributed saying, a reconstructed
                # address. H-01 is satisfied by such a line, because the text
                # really is in the data. But the document voice is the one
                # thing in this format that means "these are the words they
                # said", so reading a paraphrase in it puts sentences in a
                # real person's mouth, introduced by narration that names
                # them. That is the worst failure available to this format
                # and no rule caught it until an episode did it.
                # The fact itself is never lost: it belongs in narration,
                # which states a position rather than quoting one.
                # Matched at the START of a word, so "paraphras" still finds
                # "paraphrased" and "recount" finds "recounting", but "via"
                # does not fire inside "Silvia": the historian Silvia Rivera
                # Cusicanqui is a witness, not a secondhand source. This is the
                # defect class H-04 shipped with, where "king" inside
                # "striking" passed for Martin Luther King. Short whole words
                # need the trailing guard too, or they match half the roster.
                who = (ATTRIBUTION.get(match[0]) or match[1] or "").lower()

                def _marked(h: str) -> bool:
                    # Only a short BARE word needs the trailing guard ("via"
                    # inside "Silvia"). A term carrying its own punctuation or
                    # space is already bounded, and guarding it would stop
                    # "(as " ever matching "(as leopold".
                    tail = "(?![a-z])" if len(h) <= 4 and h.isalpha() else ""
                    return re.search(rf"(?<![a-z]){re.escape(h)}{tail}", who) is not None

                if any(_marked(h) for h in HEDGED):
                    # Said out loud, anywhere the listener will hear it before
                    # the voice reads: the DOCUMENT marker, or the narration.
                    aloud = " ".join([_norm(seg.author or ""), _norm(seg.title or ""),
                                      _norm(seg.work or "")]
                                     + [_norm(x.text) for x in seg.lines
                                        if x.speaker == "N"])
                    if not any(h in aloud for h in SPOKEN_HEDGE):
                        marked = (ATTRIBUTION.get(match[0]) or match[1] or "").strip()
                        out.append(Finding("H-11", "fail", label,
                                           f"the record marks this line {marked!r}, and nothing "
                                           f"says so aloud: either say it is attributed, or narrate "
                                           f"the position instead of reading it as their words"))

    # H-09 is the reason this catalogue is worth making. Void's claim is that
    # it shows every side; an episode that quietly drops one is the single
    # failure that would make the claim false. The data names the sides, so the
    # script cannot silently omit one.
    have = " ".join(_norm(s.title or "") for s in script.segments if s.kind == "PERSPECTIVE")
    for persp in (event.get("perspectives") or []):
        name = persp.get("viewpoint") or ""
        # Compare on word PREFIXES, not whole words: a script may reasonably
        # title the account "the engineers" where the data says "Scientific and
        # Engineering Legacy", and those are plainly the same account. Six
        # characters is enough to keep "engineer" from matching "engine".
        stems = [w[:6] for w in _norm(name).split() if len(w) > 3]
        if stems and not any(st in have for st in stems):
            out.append(Finding("H-09", "fail", "PERSPECTIVE",
                               f"the {name} account is in the data but never heard in the episode"))
    heard = len([s for s in script.segments if s.kind == "PERSPECTIVE"])
    if heard and heard < len(event.get("perspectives") or []):
        out.append(Finding("H-09", "fail", "PERSPECTIVE",
                           f"{heard} of {len(event['perspectives'])} accounts given their own case"))

    # H-10: every proper name the script speaks aloud must come from the
    # event's own record. This is the rule that makes DELEGATED drafting
    # safe. H-01 already makes a fabricated quotation impossible, but the
    # likelier failure by far is a confident, checkable, unsourced FACT: a
    # name, a place, an institution that the writer knows from somewhere
    # else and the event data does not contain. I introduced exactly that
    # twice by hand (an East India Company official who deciphered the
    # Ashokan script, and a leaning cathedral in Mexico City), caught both
    # only by grepping the YAML afterwards, and a drafting fleet will make
    # the same move far more often than one writer does.
    #
    # Matching is deliberately loose in the writer's favour: six-character
    # prefixes, case-insensitive, against the whole event document, so
    # "Ottomans" matches "Ottoman" and "Mande" matches "Mande". What it
    # catches is a name with no root anywhere in the record at all.
    haystack = _norm(_event_text(event))
    hay_words = set(haystack.split())
    hay_roots = {w[:6] for w in hay_words if len(w) > 3}
    for seg in script.segments:
        if seg.kind == "SAY":
            continue
        for l in seg.lines:
            for tok in _proper_names(l.text):
                low = _fold(tok).lower()
                if low in _NAME_ALLOWED or low in hay_words:
                    continue
                # A possessive or a hyphenated name is several words to the
                # record: Ben-Gurion is "ben gurion" there, Musa's is "musa".
                # Match on the PARTS, and treat the name as sourced when any
                # part of it is, which is the writer-favouring direction.
                parts = [x for x in re.split(r"[^a-z0-9]+", low) if len(x) > 2]
                if not parts or all(x in _NAME_ALLOWED for x in parts):
                    continue
                if any(x in hay_words or (x[:6] in hay_roots) or
                       any(x[:6] in w for w in hay_words) for x in parts):
                    continue
                out.append(Finding("H-10", "warn", f"{seg.kind}{' ' + seg.title if seg.title else ''}",
                                   f"{tok!r} is spoken in the script and appears nowhere in this "
                                   f"event's data: source it or cut it"))

    # H-07 used to FAIL at the format target of 15.0 while the audio gate in
    # tests/test_history_audio.py fails at 15.5. Two gates measuring the same
    # thing at different thresholds means a script can pass the cheap one and
    # fail the expensive one, which is exactly what happened to
    # september-11-attacks: it passed here, rendered for nine minutes, and was
    # rejected at publish, taking nine good episodes down with it.
    #
    # The hard failure now matches the gate that actually blocks publishing.
    # Overrunning the 15.0 format target is a WARNING, because an episode a few
    # seconds over is an editorial call and an episode over 15.5 is not
    # shippable at all.
    lo, hi = TARGET_MINUTES
    mins, rate, who = estimated_minutes(script, event)
    if mins < lo or mins > AUDIO_GATE_MINUTES:
        out.append(Finding("H-07", "fail", "TOTAL",
                           f"{script.words} words is {mins:.1f} min at {who}'s {rate:.0f} wpm, "
                           f"outside {lo:.0f}-{AUDIO_GATE_MINUTES:.1f}"))
    elif mins > hi:
        out.append(Finding("H-07", "warn", "TOTAL",
                           f"{script.words} words is {mins:.1f} min at {who}'s {rate:.0f} wpm, "
                           f"over the {hi:.0f} min format target (renders below the "
                           f"{AUDIO_GATE_MINUTES:.1f} gate, so it ships)"))
    for seg in script.segments:
        for l in seg.lines:
            if "—" in l.text or "–" in l.text:
                out.append(Finding("H-08", "warn", seg.kind, "dash in spoken copy"))
                break
    return out


def _event_text(event: dict) -> str:
    """Every word of the event record, flattened, as the sourcing haystack."""
    parts: list[str] = []
    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, str):
            parts.append(v)
        elif v is not None:
            parts.append(str(v))
    walk(event)
    return " ".join(parts)


# Words that are capitalised in ordinary prose and are not claims about the
# world: sentence openers, months and weekdays, the house name, and the
# spoken-number vocabulary the format requires (numbers are written as words,
# and a sentence can legitimately open "Twenty thousand men were lost").
_NAME_ALLOWED = {
    "the", "a", "an", "and", "but", "or", "so", "then", "now", "here", "there",
    "this", "that", "these", "those", "it", "its", "he", "she", "they", "them",
    "his", "her", "their", "we", "you", "i", "in", "on", "at", "by", "for",
    "from", "of", "to", "with", "within", "without", "after", "before", "when",
    "what", "which", "who", "whom", "whose", "why", "how", "if", "not", "no",
    "nobody", "none", "nothing", "every", "everything", "all", "both", "each",
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty",
    "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "million",
    "billion", "first", "second", "third", "fourth", "fifth", "sixth",
    # Ordinals run past "tenth" because REGNAL NUMBERS are spelled out: a
    # synthesiser reads "Constantine XI" as "Constantine ex eye". The list
    # stopped at tenth, so every monarch past the tenth of their name drew a
    # warning on a name the record does carry, in two scripts already. A
    # recurring false positive is worse than a missing rule, because it
    # teaches the writer to wave H-10 through.
    "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth",
    "thirteenth", "fourteenth", "fifteenth", "sixteenth", "seventeenth",
    "eighteenth", "nineteenth", "twentieth", "half", "january", "february",
    "march", "april", "may", "june", "july", "august", "september", "october",
    "november", "december", "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday", "void", "news", "on", "air", "history",
    "read", "listen", "look", "take", "put", "let", "say", "said", "there's",
    "god", "europe", "european", "west", "western", "east", "eastern",
    "north", "northern", "south", "southern",
    # Capitalised only because they open a sentence. Found by running the
    # rule over twenty one hand-written scripts and reading every flag.
    "about", "above", "across", "against", "almost", "along", "already",
    "also", "although", "among", "another", "any", "around", "as", "because",
    "behind", "being", "below", "beside", "besides", "between", "beyond",
    "can", "council", "did", "do", "does", "during", "either", "enough",
    "even", "ever", "everybody", "everyone", "everything", "except", "far",
    "few", "finally", "getting", "given", "going", "had", "has", "have",
    "health", "hold", "instead", "into", "inside", "is", "it's", "just",
    "keep", "kept", "know", "known", "later", "left", "legally", "less",
    "like", "long", "made", "make", "making", "many", "meanwhile", "might",
    "modelled", "more", "most", "much", "must", "near", "nearly", "neither",
    "never", "next", "nine", "nobody's", "once", "only", "other", "others",
    "out", "outside", "over", "own", "people", "perhaps", "property", "put",
    "rather", "read", "reading", "remember", "roughly", "same", "saying",
    "several", "shall", "should", "since", "small", "some", "somebody",
    "someone", "something", "somewhere", "still", "such", "tear", "tell",
    "than", "that's", "their", "think", "those", "though", "through",
    "throughout", "thus", "together", "toward", "towards", "under", "until",
    "up", "upon", "used", "very", "was", "were", "whatever", "whenever",
    "wherever", "whether", "while", "whole", "will", "with", "within",
    "worth", "would", "writers", "yet", "you're",
}

_NAME_RE = re.compile(r"\b([A-Z][a-zA-Z'\u2019-]{2,})")


def _proper_names(text: str) -> list[str]:
    """Capitalised words in a spoken line, as candidate factual claims."""
    return [m.group(1).strip("'\u2019-") for m in _NAME_RE.finditer(text or "")]


def _overlap(a: str, b: str) -> float:
    """Word overlap, so trimming a quote for the ear is allowed but inventing is not."""
    wa, wb = set(a.split()), set(b.split())
    return len(wa & wb) / max(1, min(len(wa), len(wb)))
