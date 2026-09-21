#!/usr/bin/env python3
"""Four gates on the History catalogue's reader-facing prose.

Each exists because an audit found the defect and nothing structural could have.
`pipeline/editorial/standard.py` gates the daily feed; until now nothing gated
the History YAML at all, so every class regrew freely.

**The dash gate.** The house rule bans the em dash and the en dash in all
written editorial output, History copy included. 1,668 fields carried one.

Three exemptions, and they are the rule working rather than holes in it:
  - inside a quotation, because the words are as the source printed them and
    editing them would make the quote non-verbatim, which Rule 1 forbids;
  - inside a published title, because "Poor Numbers - How We Are Misled by
    African Development Statistics" is not the title of that book;
  - inside a script, which is excluded here because scripts keep dashes as TTS
    breath marks and H-08 already governs them.

**The speaker-shape gate.** A quotation's `speaker` or `author` must name
somebody: a person, or an institution that can hold a position. It must not
hold a sentence, and it must not hold a bare description of an unnamed person
with nothing checkable behind it.

The line this draws is the one the 2026-09-20 audit settled on, and it matters
that it is drawn here rather than looser. "Anonymous Luddite letter to a
Huddersfield manufacturer" is FINE: it discloses the anonymity out loud and
names a document. Roughly 45 entries of that shape carry nearly every
Congolese, Nahua, Tibetan, Laotian, Rwandan, Kurdish and Chinese voice in the
catalogue. A gate that failed those would strip them while leaving every named
Western statesman standing, which is the failure this section exists to
prevent. So the test is not "is the speaker a bare name". It is: **if the
speaker is not a name, does anything in the entry point at something a reader
could go and check?**

**What this gate does not catch, said plainly rather than papered over.**
Whether a described position was ever actually uttered is a judgement, not a
shape. "Iraqi state framing of the September 1980 casus belli" was deleted on
2026-09-20 as a rendering of a position rather than a quotation, and this gate
would pass it, because it names a date. What the gate catches is the mechanical
shape: an empty speaker, a speaker holding prose, a description with nothing
behind it at all. The rest needs a reader, and claiming otherwise would itself
be a false claim in a file about false claims.

**The time-relative gate.** CLAUDE.md Rule 1: "A number that goes stale is a
future error. Do not publish a count that changes with time ('ten presidents',
'sixty-five years on') when a durable formulation exists." The 2026-09-21 brand
audit found the rule's own example in the catalogue, along with 80 more: "the
exclusion zone persists in 2026", "still open in 2026", "leads French elections
in the 2020s", "remains the world's most unequal country". None of these is
false today. Every one of them becomes false without anybody touching the file,
which is the point: the error is scheduled, not present, so no proofread finds
it.

The gate fails `summary`, `subtitle`, `significance`, `legacy_points[]` and
`perspectives[].narrative` on any phrase that measures from the reading moment.

**The allowed rewrite**, which is what the 149 fixes on 2026-09-21 did:
  - anchor the claim to a dated observation, phrased so the date belongs to the
    measurement rather than to the reader: "the exclusion zone, 2,600 square
    kilometres in 2016 surveys"; "a 2024 Gini coefficient of 0.63 made South
    Africa the most unequal country on earth"; "by 2024, 34 countries had
    recognized the genocide". "By <year>" and a year used adjectivally
    ("the 2003 study", "2024 unemployment") are spared deliberately: they read
    as a fixed observation. "in / as of / since <the year of writing>" is not,
    because it reads as now;
  - or replace the relative offset with the absolute date the record already
    carries: "Four years later he launched the Cultural Revolution" became
    "In 1966 he launched the Cultural Revolution", which the same file states
    twice;
  - or, where the durable fact is in neither the YAML nor the event's own
    sources, drop the clause. Rule 1 again: silence beats a plausible
    reconstruction. "As of 2026, eastern Congo has over 120 active armed
    groups" was cut rather than dated, because nothing in the record says when
    anyone counted.

Two carve-outs, both false positives found by running the rule:
  - "in 2025 dollars", "in 2025 values": an inflation conversion is pinned to
    its base year forever and does not decay. Three entries carry one.
  - "served alongside him for 25 years on the island" (apartheid): there "on"
    is a preposition, not the idiom "thirty years on". The idiom always closes
    a clause, so the rule requires punctuation after it.

**The prose-attribution gate.** The speaker-shape gate above governs quotation
blocks. Nothing governed the same move made in running prose: "pro-nuclear
analysts argue", "many analysts argue", "Some argue that Eisenhower's financial
coercion", "Some sources say he was forced to watch his sons killed first".
VOICE-BRAND II is "Attribute or Abstain", and a hedge noun attributes to
nobody. So the hedge is allowed only when the same sentence names somebody: a
person, a work or an institution.

Where the source existed it was named ("the war museums studied by Narges
Bajoghli"). Where it did not, the claim went: the carpet-execution detail in
`mongol-conquest-baghdad` names no chronicle in a file that cites four, and
Rule 1 says a claim that cannot be sourced is cut, not softened. Presenting a
position as a position ("One reading holds that...") is not the defect this
catches; counting unnamed people who hold it is.

Run: python3 tests/test_history_copy.py
"""
import glob
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVENTS = sorted(glob.glob(str(ROOT / "data/history/events/*.yaml")))

EM, EN = "—", "–"

# Keys holding someone's actual words, or a published title. Exempt from the
# dash gate; see the module docstring.
# `work` holds a published work's title exactly as `title` does: Li Peng's
# diary is called "The Critical Moment - Li Peng June Fourth Diary" and the
# dash is the publisher's, not ours.
VERBATIM_KEYS = {"quote", "text", "excerpt", "title", "work", "caption_original"}

# A quoted span ANYWHERE is also exempt, not only a field named "quote". The
# reason quotations are spared is that the words are as the source printed
# them, and that reason does not care which field holds them.
#
# ashoka-maurya-empire quotes Rock Edict XIII inside a perspective narrative:
# "those who are well cared for in the conquered country - the friends,
# acquaintances, companions, and relatives". Keyed on the field name alone this
# gate would have demanded someone repunctuate a 3rd-century BCE edict to
# satisfy a house style rule, which is precisely the inversion Rule 1 forbids.
_QUOTED_SPAN = re.compile(r"[\u201c\"]([^\u201c\u201d\"]{2,600})[\u201d\"]")


def outside_quotations(text: str) -> str:
    """The text with every quoted span blanked, so only our own prose is judged."""
    return _QUOTED_SPAN.sub(lambda m: " " * len(m.group(0)), text or "")

# A speaker that is not a bare name is acceptable when the entry points
# somewhere a reader could go, OR discloses its own mediation out loud. Both
# satisfy Rule 1's "say so out loud or do not use it"; only a bare description
# with neither fails.
CHECKABLE = re.compile(
    r"archive|museum|memorial|collection|report|commission|tribunal|inquiry|"
    r"codex|chronicle|testimon|oral histor|letter|handbill|petition|diary|"
    r"transcript|proceedings|hansard|gazette|edict|decree|treaty|communiqu|"
    r"broadcast|dispatch|despatch|census|record|papers|archives|trial|"
    r"textbook|interview|memoir|published|press|journal|review|sermon|"
    r"history|histories|dialogue|book\s+\d|"
    # A field that describes what the DOCUMENT is, which script_format.py:290
    # records as legitimate in terms: "a record that calls its source a
    # 'reactor-safety summary' is describing what the document IS, not hedging
    # whose words it carries."
    r"summary|description|formulation|designation|position|framing|"
    # Disclosure of mediation is the rule being satisfied, not broken.
    r"attribut|paraphras|apocryph|rendered by|recorded by|compiled|"
    r"reconstructed|tradition|as told to|quoted in|"
    r"\b1[0-9]{3}\b|\b20[0-9]{2}\b|\bBCE\b|\bCE\b|\bc\.\s*\d",
    re.IGNORECASE)

# A speaker field holding a sentence rather than a name. Initials are NOT
# sentence boundaries: the first draft of this rule flagged "John F. Kennedy",
# "B.R. Ambedkar" and "E.D. Morel" among 62 others, every one a false positive,
# because it read the period after an initial as the end of a sentence.
_INITIALS = re.compile(r"\b[A-Z]\.(\s*[A-Z]\.)*")
_ABBREV = re.compile(r"\b(Mr|Mrs|Ms|Dr|Prof|Rev|Sr|Jr|St|Gen|Col|Capt|Lt|Sgt"
                     r"|Hon|Amb|Sen|Rep|Gov|Pres|vs|etc|al)\.", re.IGNORECASE)


def holds_a_sentence(speaker: str) -> bool:
    """True when the field is prose rather than a name or a title."""
    stripped = _ABBREV.sub("", _INITIALS.sub("", speaker))
    # A full stop followed by a capitalised word is a real sentence boundary.
    if re.search(r"[.!?]\s+[A-Z]", stripped):
        return True
    # Or a finite reporting verb, which a name never contains.
    return bool(re.search(r"\b(said|told|wrote|argued|claimed|noted|explained|"
                          r"insisted|replied)\b", stripped, re.IGNORECASE))


# ------------------------------------------------------ time-relative gate
# Every entry measures from the moment somebody reads the page. The module
# docstring carries the rewrite each one asks for, and why the two look-ahead
# carve-outs are there.
TIME_RELATIVE = [
    # "as of 2026", "in 2026", "since 2025": the writing year used as the
    # present. An inflation conversion is exempt; its base year never moves.
    ("a near year used as now",
     re.compile(r"\b(?:in|as of|since) 20(?:2[4-9]|3\d)\b"
                r"(?!\s+(?:dollars|values|prices|terms|money))", re.I)),
    ("to this day", re.compile(r"\bto this day\b", re.I)),
    ("a state asserted as continuing",
     re.compile(r"\bstill (?:open|governs|leads|stands|in force|the)\b", re.I)),
    # "remains in force", "persists today", "remains the world's most unequal".
    ("a state asserted as still holding",
     re.compile(r"\b(?:remains?|persists?)\b[^.!?]*?"
                r"\b(?:in force|today|the (?:most|largest|only|world's))\b",
                re.I)),
    # "sixty-five years on", "9,000 years ago", "80 years later". Spared:
    # "forty years later in 1988", and "years on" used as a preposition.
    ("an interval measured from now",
     re.compile(r"\b\w+(?:-\w+)? years "
                r"(?:ago\b|later\b|on\b(?=\s*[,.;:]|$))"
                r"(?!\s+in\s+\d{4})", re.I)),
    ("the present decade", re.compile(r"\bin the 2020s\b", re.I)),
    ("currently", re.compile(r"\bcurrently\b", re.I)),
    ("today", re.compile(r"\btoday\b", re.I)),
]

# ------------------------------------------------- prose-attribution gate
# A hedge noun standing where a name belongs.
HEDGED_ATTRIBUTION = re.compile(
    r"\b(?:analysts|experts|critics|observers|some|many|sources) "
    r"(?:say|says|said|argue|argues|argued|believe|believes|believed"
    r"|note|notes|noted)\b", re.I)

# What rescues it: a full name, or an institution that can hold a position.
# One capitalised word is not enough, because the subject of the claim is
# usually capitalised ("Some argue that Eisenhower's coercion...") and naming
# whom the claim is ABOUT is not naming who makes it.
NAMED = re.compile(
    r"\b[A-Z][a-z]+(?:\s+(?:de|van|von|al|ibn|bin|da|di|of|the))?"
    r"\s+[A-Z][\w'’-]+|\b[A-Z]{2,}\b")

_SENTENCE = re.compile(r"[^.!?]*[.!?]|[^.!?]+$")


def sentence_around(text: str, index: int) -> str:
    """The sentence containing `index`, or the whole text if it has none."""
    for m in _SENTENCE.finditer(text):
        if m.start() <= index < m.end():
            return m.group(0)
    return text


def reader_prose(ev):
    """Every field the two prose gates govern, with its path."""
    for key in ("summary", "subtitle", "significance"):
        value = ev.get(key)
        if isinstance(value, str):
            yield key, value
    for i, point in enumerate(ev.get("legacy_points") or []):
        if isinstance(point, str):
            yield f"legacy_points[{i}]", point
    for i, p in enumerate(ev.get("perspectives") or []):
        narrative = (p or {}).get("narrative")
        if isinstance(narrative, str):
            yield f"perspectives[{i}].narrative", narrative


failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}: {detail}" if detail else name)


def walk(node, path="", key=None):
    """Every leaf string, with its path and the key that holds it."""
    if isinstance(node, str):
        yield path, key, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from walk(v, f"{path}.{k}" if path else k, k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]", key)


def prose_lists(node, field, path=""):
    """Every entry of a named prose list, anywhere in the event."""
    if isinstance(node, dict):
        for k, v in node.items():
            here = f"{path}.{k}" if path else k
            if k == field and isinstance(v, list):
                for i, item in enumerate(v):
                    yield f"{here}[{i}]", item
            else:
                yield from prose_lists(v, field, here)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from prose_lists(v, field, f"{path}[{i}]")


def quotations(ev):
    """Every quotation entry in an event, with where it came from."""
    for i, q in enumerate(ev.get("primary_source_excerpts") or []):
        if isinstance(q, dict):
            yield f"primary_source_excerpts[{i}]", q
    for pi, p in enumerate(ev.get("perspectives") or []):
        for qi, q in enumerate((p or {}).get("notable_quotes") or []):
            if isinstance(q, dict):
                yield f"perspectives[{pi}].notable_quotes[{qi}]", q


dash_hits = 0
speaker_hits = 0
stale_hits = 0
hedge_hits = 0
quotes_seen = 0

for path in EVENTS:
    slug = pathlib.Path(path).stem
    try:
        ev = yaml.safe_load(open(path, encoding="utf-8"))
    except yaml.YAMLError as exc:
        # A malformed file is a finding, not a traceback. Two files were broken
        # in a past session by inserting 4-space indent into a 2-space file,
        # and a crash here would hide every other event's result behind it.
        check(f"{slug}", False, f"does not parse: {str(exc).splitlines()[0]}")
        continue
    if not isinstance(ev, dict):
        check(f"{slug}", False, "is not a mapping")
        continue
    slug = ev.get("slug") or slug

    # ------------------------------------------------------------ dash gate
    for field, key, text in walk(ev):
        if key in VERBATIM_KEYS:
            continue
        text = outside_quotations(text)
        if EM in text or EN in text:
            dash_hits += 1
            if dash_hits <= 25:
                snippet = text.strip()
                idx = max(snippet.find(EM), snippet.find(EN))
                check(f"{slug} {field}", False,
                      f"...{snippet[max(0, idx - 45):idx + 45]}...")

    # ------------------------------------------ prose that parsed as a map
    # A line of prose containing ": " must be quoted, or YAML reads it as a
    # one-key mapping and the sentence stops being a sentence. Twelve entries
    # carried this, among them "Four empires collapsed within four years: the
    # German, Austro-Hungarian, Russian, and Ottoman", which parsed as a key
    # "Four empires collapsed within four years" holding the rest as its value.
    #
    # The old page rendered these only inside a client modal, where React threw
    # "Objects are not valid as a React child" into a console nobody read. The
    # Hearing renders at build, where the same value killed the static export
    # of /history/assassination-of-caesar. It was invisible for as long as it
    # was only wrong.
    # `connections` is deliberately absent: it is a real list of mappings with
    # schema keys, and an early draft of this rule flagged every `target_slug`
    # in the catalogue. What marks an accident is a SINGLE key holding a phrase
    # rather than a field name, so that is what it looks for.
    for field in ("omitted", "emphasized", "key_arguments", "legacy_points"):
        for where, entry in prose_lists(ev, field):
            if isinstance(entry, dict) and len(entry) == 1:
                k = str(next(iter(entry), ""))
                if " " in k:
                    check(f"{slug} {where}", False,
                          f"prose parsed as a mapping; quote the scalar: "
                          f"{k[:60]!r}")

    # -------------------------------------------------- speaker-shape gate
    for where, q in quotations(ev):
        quotes_seen += 1
        speaker = str(q.get("speaker") or q.get("author") or "").strip()
        if not speaker:
            speaker_hits += 1
            check(f"{slug} {where}", False, "quotation with no speaker at all")
            continue
        if holds_a_sentence(speaker):
            speaker_hits += 1
            check(f"{slug} {where}", False,
                  f"speaker holds a sentence: {speaker[:70]!r}")
            continue
        # Not obviously a name. Acceptable only if something points at a source.
        looks_like_name = len(speaker.split()) <= 5
        if not looks_like_name:
            haystack = " ".join(str(q.get(k) or "")
                                for k in ("speaker", "author", "context", "work"))
            if not CHECKABLE.search(haystack):
                speaker_hits += 1
                check(f"{slug} {where}", False,
                      f"speaker is a description with nothing checkable behind "
                      f"it: {speaker[:70]!r}")

    # ---------------------------------------------- time-relative gate
    # Quotations are spared for the same reason the dash gate spares them:
    # the words are as the source printed them.
    for where, text in reader_prose(ev):
        prose = outside_quotations(text)
        for label, rx in TIME_RELATIVE:
            for m in rx.finditer(prose):
                stale_hits += 1
                if stale_hits <= 25:
                    snippet = " ".join(
                        prose[max(0, m.start() - 55):m.end() + 55].split())
                    check(f"{slug} {where}", False,
                          f"{label}: ...{snippet}...")

    # ------------------------------------------ prose-attribution gate
    for where, text in reader_prose(ev):
        prose = outside_quotations(text)
        for m in HEDGED_ATTRIBUTION.finditer(prose):
            if NAMED.search(sentence_around(prose, m.start())):
                continue
            hedge_hits += 1
            check(f"{slug} {where}", False,
                  f"hedge in place of attribution: {m.group(0)!r}, and the "
                  f"sentence names nobody")

# A gate nobody has watched fail is not a gate. Plant one of each shape and
# assert this file still rejects it, and plant the honest shapes it must spare.
PLANTED_BAD = [
    ("", "a quotation with no speaker at all"),
    ("A villager who survived the raid. She said the soldiers came at dawn.",
     "a speaker holding prose"),
    ("The minister told reporters the report was worthless",
     "a speaker holding a reporting clause"),
]
PLANTED_GOOD = [
    "John F. Kennedy",
    "B.R. Ambedkar",
    "W.E.B. Du Bois",
    "T.W. White, Australian delegate",
    "Anonymous Luddite letter to a Huddersfield manufacturer",
    "Ata-Malik Juvayni (paraphrasing a local poet's account)",
    "Athenian envoys to the Melians (as rendered by Thucydides)",
    "UN Office of the High Commissioner for Human Rights",
]

for speaker, why in PLANTED_BAD:
    caught = (not speaker) or holds_a_sentence(speaker) or (
        len(speaker.split()) > 5 and not CHECKABLE.search(speaker))
    check(f"planted: {why}", caught, f"{speaker[:50]!r} slipped through")

for speaker in PLANTED_GOOD:
    spared = bool(speaker) and not holds_a_sentence(speaker) and (
        len(speaker.split()) <= 5 or CHECKABLE.search(speaker))
    check(f"spared: {speaker[:44]}", spared, "an honest speaker was rejected")

# The same discipline for the two new gates. Every PLANTED_STALE line is a
# sentence that stood in the catalogue on the morning of 2026-09-21; every
# DURABLE line is the sentence that replaced it, or a shape the pass had to
# leave alone. A gate that failed the second column would have forced 149
# rewrites into worse prose than it found.
PLANTED_STALE = [
    "Sixty-five years on, the question has never been settled.",
    "a trade embargo that remains in force in 2026",
    "the 2,600 sq km exclusion zone persists in 2026",
    "One question left open in 1949 is still open in 2026.",
    "his party leads French elections in the 2020s",
    "Post-apartheid South Africa remains the world's most unequal country.",
    "the Republic of China survives to this day",
    "Ten million people still speak Quechua today.",
    "It sold out immediately and remains in print 80 years later.",
    "Maize, domesticated in central Mexico 9,000 years ago, reached Africa.",
    "As of 2024, 34 countries have formally recognized the genocide.",
    "The editorial triage is currently disabled.",
]
DURABLE = [
    "The question of whether it was a liberation has never been settled.",
    "imposed a trade embargo that was never lifted",
    "the 2,600 sq km exclusion zone was never lifted",
    "The question left open in 1949 was never settled.",
    "built the National Front on pied-noir grievance",
    "A 2024 Gini coefficient of 0.63 made South Africa the most unequal.",
    "where the Republic of China moved its capital to Taipei that December",
    "Ten million people speak Quechua.",
    "It sold out immediately and stayed in print.",
    "Maize, domesticated in central Mexico around 7000 BCE, reached Africa.",
    "By 2024, 34 countries had formally recognized the genocide.",
    "The bomb had cost $2 billion (approximately $30 billion in 2024 dollars).",
    "Walter Sisulu served alongside him for 25 years on the island.",
    "The United States did not ratify it until 1988, forty years after.",
    "The Convention was ratified forty years later in 1988.",
    "2024 unemployment among black South Africans exceeded 40%.",
]

for line in PLANTED_STALE:
    caught = any(rx.search(line) for _, rx in TIME_RELATIVE)
    check(f"planted stale: {line[:44]}", caught, "a scheduled error slipped through")

for line in DURABLE:
    spared = not any(rx.search(line) for _, rx in TIME_RELATIVE)
    check(f"durable: {line[:44]}", spared, "a dated, durable sentence was rejected")

PLANTED_HEDGE = [
    "Many analysts argue the treaty was doomed from the first draft.",
    "Some sources say he was forced to watch his sons killed first.",
    "Critics noted the industry had strong incentives to draw that line.",
    "Some argue that Eisenhower's coercion needlessly humiliated allies.",
]
ATTRIBUTED = [
    "The war museums studied by Narges Bajoghli teach that Iran stands alone.",
    "Many analysts argue the treaty was doomed, among them Margaret MacMillan.",
    "Some experts said so, the UNSCEAR panel among them.",
    "One reading holds that the coercion needlessly humiliated allies.",
    "Economic historians have shown the sterling crisis ran deeper.",
]

for line in PLANTED_HEDGE:
    m = HEDGED_ATTRIBUTION.search(line)
    caught = bool(m) and not NAMED.search(sentence_around(line, m.start()))
    check(f"planted hedge: {line[:44]}", caught, "an unattributed hedge slipped through")

for line in ATTRIBUTED:
    m = HEDGED_ATTRIBUTION.search(line)
    spared = (not m) or bool(NAMED.search(sentence_around(line, m.start())))
    check(f"attributed: {line[:44]}", spared, "an attributed sentence was rejected")

if failures:
    print(f"FAIL  {dash_hits} dash field(s), {speaker_hits} speaker(s), "
          f"{stale_hits} time-relative claim(s), {hedge_hits} hedge(s), "
          f"across {len(EVENTS)} events")
    for f in failures[:30]:
        print(f"  - {f}")
    if len(failures) > 30:
        print(f"  ... and {len(failures) - 30} more")
    print("\n  Dashes: rewrite the sentence. Two sentences, or a comma, "
          "semicolon, colon or parentheses. Never a mechanical replacement, "
          "and never inside a quotation or a published title.")
    print("  Speakers: name the utterer, or name the document the words are "
          "in. If neither exists, the line does not ship.")
    print("  Time-relative claims: anchor to a dated observation (\"in 2016 "
          "surveys\", \"by 2024\", \"a 2003 study\") or to the absolute date "
          "the record already carries. Where neither exists, drop the clause; "
          "do not invent a date to satisfy this gate.")
    print("  Hedged attribution: name the person, work or institution in the "
          "same sentence, or cut the claim.")
    sys.exit(1)

print(f"PASS  {len(EVENTS)} events: no em or en dash outside quotations and "
      f"titles; {quotes_seen} quotations name an utterer or a source; no "
      f"reader-facing claim measured from the reading moment; no hedge "
      f"standing in for a name")
