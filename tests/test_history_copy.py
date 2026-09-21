#!/usr/bin/env python3
"""Two gates on the History catalogue's reader-facing prose.

Both exist because an audit found the defect and nothing structural could have.
`pipeline/editorial/standard.py` gates the daily feed; until now nothing gated
the History YAML at all, so both classes regrew freely.

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

if failures:
    print(f"FAIL  {dash_hits} dash field(s), {speaker_hits} speaker(s), "
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
    sys.exit(1)

print(f"PASS  {len(EVENTS)} events: no em or en dash outside quotations and "
      f"titles; {quotes_seen} quotations name an utterer or a source")
