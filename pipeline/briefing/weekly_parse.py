"""The pure core of void --weekly: parsing, week math, row assembly.

No DB, no LLM, no network, and no third-party import.

WHY THIS MODULE EXISTS
----------------------
`weekly_digest_generator` imports `utils.supabase_client`, which raises
`EnvironmentError` at import time unless `VOID_SQLITE_PATH` or `SUPABASE_*` is
set. So the generator module cannot be imported in CI *at all*, and every pure
function inside it was untestable. That import wall, not neglect, is why the
weekly had zero tests while the `week_offset` sign bug served Issue #23 for
three weeks.

Everything here imports `re`, `datetime` and the stdlib-only shared kill list
in `utils.prohibited_terms`, and nothing else, so `tests/test_weekly.py` can
exercise it with no key, no database and no network.

THE HEADLINE GUARD
------------------
`_parse_essay` took the first non-empty LINE as the headline with no sanity
check. `COVER_SYSTEM` does explicitly demand "Line 1: the headline only", but a
model is free to ignore an instruction, and on Issue #26 it did: the second
cover feature opened straight into prose, so its entire 698-character lede
became `cover_text[1].headline` and the essay LOST that paragraph. The page
then set it as a display-size red <h2> and as coverline #1 on the cover.

`looks_like_headline` is the fix. A line that could be a paragraph is not
accepted as a title, and the parser falls back to the single-block branch that
already existed: `headline = ""`, the prose stays whole in the body. Every
consumer already guards `headline?.trim()`, so no new failure mode.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

from utils.prohibited_terms import find_prohibited, find_slop

# A headline is short and is one utterance. These are deliberately loose: the
# job is to reject a PARAGRAPH, not to police house style. The live defect was
# 698 characters and 110 words, an order of magnitude past either bound.
MAX_HEADLINE_CHARS = 120
MAX_HEADLINE_WORDS = 18

# A sentence boundary with more text after it. A trailing period is fine (a
# headline may end in one); an INTERIOR boundary means the line is prose.
_INTERIOR_SENTENCE_END = re.compile(r"[.!?][\"')\]]?\s+\S")


def looks_like_headline(line: str) -> bool:
    """True when a line could be a title rather than a paragraph."""
    s = (line or "").strip()
    if not s:
        return False
    if len(s) > MAX_HEADLINE_CHARS:
        return False
    if len(s.split()) > MAX_HEADLINE_WORDS:
        return False
    if _INTERIOR_SENTENCE_END.search(s):
        return False
    return True


def clean_headline(line):
    """Strip an optional 'HEADLINE:'/'TITLE:' label and Markdown chars off a line.

    The label is only stripped when followed by a colon, so a real headline that
    happens to start with the word "Headline" (e.g. "Headline inflation") is kept.
    """
    line = re.sub(r"^\s*#{0,3}\s*(?:HEADLINE|TITLE)\s*:\s*", "", line, flags=re.IGNORECASE)
    return line.strip().strip("*_#").strip()


def parse_essay(raw, want_numbers=False):
    """Parse a plain-text essay into {headline, text[, numbers]} or None.

    Layout: first non-empty line is the headline, the rest is the body. If
    want_numbers, a trailing line "NUMBERS" splits off a block of
    "value | context" lines parsed into [{"stat", "context"}].

    A first line that does not pass `looks_like_headline` is treated as body:
    the essay keeps its lede and the caller supplies a headline from the
    cluster title instead of printing a paragraph at display size.
    """
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    numbers = []
    if want_numbers:
        parts = re.split(r"\n\s*#{0,3}\s*NUMBERS\s*:?\s*\n", text, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            text, num_block = parts[0].strip(), parts[1]
            for ln in num_block.splitlines():
                ln = ln.strip().lstrip("-*•").strip()
                if "|" not in ln:
                    continue
                value, _, context = ln.partition("|")
                value = value.strip()
                if value:
                    numbers.append({"stat": value, "context": context.strip()})

    lines = text.splitlines()
    idx = next((k for k, ln in enumerate(lines) if ln.strip()), None)
    if idx is None:
        return None
    headline = clean_headline(lines[idx])
    body = "\n".join(lines[idx + 1:]).strip()
    if not body:
        # Single-block output: no separable headline; keep it all as text.
        body, headline = headline, ""
    elif not looks_like_headline(headline):
        # Line 1 is prose. Keep the essay whole rather than eating its lede.
        body = (headline + "\n" + body).strip()
        headline = ""
    result = {"headline": headline, "text": body}
    if want_numbers:
        result["numbers"] = numbers
    return result


def parse_recap(raw):
    """Parse a plain-text recap batch into {stories: [{headline, summary}]}.

    Stories are separated by a line that is just "###" (optionally "### STORY").
    Within each block, the first non-empty line is the headline, the rest is the
    summary. Returns None if nothing parseable.
    """
    if not raw or not raw.strip():
        return None
    blocks = re.split(r"\n\s*#{2,}(?:\s*STORY\s*\d*)?\s*\n", "\n" + raw.strip())
    stories = []
    for block in blocks:
        lines = block.strip().splitlines()
        idx = next((k for k, ln in enumerate(lines) if ln.strip()), None)
        if idx is None:
            continue
        headline = clean_headline(lines[idx])
        summary = " ".join(ln.strip() for ln in lines[idx + 1:] if ln.strip()).strip()
        if not summary:
            summary, headline = headline, ""
        elif not looks_like_headline(headline):
            summary = (headline + " " + summary).strip()
            headline = ""
        if headline or summary:
            stories.append({"headline": headline, "summary": summary})
    return {"stories": stories} if stories else None


# ---------------------------------------------------------------------------
# Week window
# ---------------------------------------------------------------------------

# Issue #1 is the week beginning Sunday 2026-03-22.
# ---------------------------------------------------------------------------
# The editorial spec, enforced
#
# The prompts have always CLAIMED enforcement. COVER_SYSTEM asks for 800-1200
# words; OPINION_SYSTEM says an output containing "notable" or "crucially" is
# REJECTED. Nothing rejected. The check existed at exactly one site in the
# whole file, inside `_generate_weekly_opinion`, so five of six sections were
# written against a spec nobody measured, and the published issue carries nine
# banned terms and three em dashes in the opinion columns alone.
#
# A model is free to ignore an instruction. That makes the CHECK the fix, the
# same argument that moved the headline guard out of COVER_SYSTEM and into
# `looks_like_headline`. This lives here, with the other pure functions, so it
# is testable without a key: the generator cannot be imported without one.
# ---------------------------------------------------------------------------

# The kill list itself lives in `utils.prohibited_terms` (SIGNIFICANCE_WORDS
# and SLOP_PATTERN) since 2026-09-21. This module used to carry its own tuple
# of 24 terms: the significance family and the Vox scaffolding, and none of
# the VOICE-BRAND VII AI-slop set, so 27 of the 34 kill-list hits on the two
# published issues were words the weekly's check had never heard of (brand
# audit F-03). One list, three consumers: feed, weekly, served-output gate.


def word_count(text) -> int:
    t = (text or "").strip()
    return len(t.split()) if t else 0


def banned_terms(text):
    """Every kill-list term present, word-bounded, from the shared list.

    Bounded deliberately: a raw substring test flags "signify" for
    "significant" and, more to the point, cannot tell a quoted source saying
    "crucial" from our own prose. The bound is the cheap half of that; the
    quote case is left alone rather than guessed at.
    """
    return find_prohibited(text or "")


def drop_terms(text):
    """The kill-list hits that DROP a section rather than ship it.

    `enforce` regenerates once and ships the better attempt, and that is the
    right call for a word count: a department forty words long reads better
    than no department. It is the wrong call for "underscores the
    vulnerability", which cannot be deleted by code (the sentence loses its
    verb) and was shipped seven times over on Vol. I, No. 1 by exactly that
    once-then-ship path. Verbs, nouns and scaffolding from the shared slop set
    are returned here; the significance adjectives are not, because
    `strip_significance` removes those deterministically before this runs.
    """
    return find_slop(text or "")


def strip_dashes(text):
    """Em and en dashes out of editorial prose, deterministically.

    CLAUDE.md bans both as an AI tell. This runs whether or not the model
    complied, because a rewrite the reader never sees is worth more than a
    finding in a log. Audio scripts are exempt and never passed here: there the
    dash is a breath mark for the synthesiser.
    """
    if not text:
        return text
    out = text.replace(" — ", ", ").replace(" – ", ", ")
    out = out.replace("—", ", ").replace("–", "-")
    # ", ," is what two adjacent dashes leave behind.
    return re.sub(r",\s*,", ",", out)


def enforce(text, *, min_words=0, max_words=0):
    """Findings against the spec, in the words the retry prompt will use.

    Returns [] when the piece is clean. The caller regenerates once naming
    these, then ships the better attempt: a second failure means the model will
    not comply, and a missing department reads worse than a long one.
    """
    findings = []
    n = word_count(text)
    if min_words and n < min_words:
        findings.append(f"it runs {n} words against a {min_words}-{max_words or min_words} word brief; it is too short")
    elif max_words and n > max_words:
        findings.append(f"it runs {n} words against a {min_words}-{max_words} word brief; it is too long")
    found = banned_terms(text)
    if found:
        findings.append("it uses " + ", ".join(f'"{t}"' for t in sorted(found))
                        + ", which announces that a fact matters instead of showing it; "
                          "give the fact and let it land")
    if "—" in (text or "") or "–" in (text or ""):
        findings.append("it uses a dash where a full stop or a comma belongs")
    return findings


def enforce_recap(items, *, min_words, max_words):
    """Findings for a Week in Brief COLUMN, which is measured per item.

    Separate from `enforce` because the column is one generation covering ten
    briefs: a caller that concatenated them and measured once would compare a
    460-word blob against a 55-word spec and be wrong in both directions at
    the same time.

    It reports a BAND. The first version of this check tested only
    `n > max_words * 1.3`, which could catch a column running long and nothing
    else, because running long was the failure in front of it: RECAP_SYSTEM
    asked for 150-200 words and every published brief ran ~140. Tightening the
    spec to 55-75 fixed that and uncovered the opposite failure, invisible to a
    one-sided test. Vol. I, No. 1 shipped nine of ten briefs BELOW the floor,
    at 40 to 49 words, and the column passed clean on length.

    The ceiling keeps its 1.3 tolerance and the floor does not. Running a
    little long costs column inches; running short means the brief is missing a
    fact, and there is no such thing as being usefully under-informed.
    """
    counts = [word_count(i.get("summary")) for i in (items or [])]
    if not counts:
        return []
    over = [n for n in counts if n > max_words * 1.3]
    under = [n for n in counts if n < min_words]
    banned = sorted({t for i in items for t in banned_terms(i.get("summary"))})

    findings = []
    if over:
        findings.append(
            f"{len(over)} of {len(counts)} briefs run past {max_words} words "
            f"(the longest is {max(over)}); two or three sentences each, no more"
        )
    if under:
        findings.append(
            f"{len(under)} of {len(counts)} briefs run under {min_words} words "
            f"(the shortest is {min(under)}); each one needs {min_words} to "
            f"{max_words}, so give every story a second fact rather than a "
            f"second clause"
        )
    if banned:
        findings.append(
            "the column uses " + ", ".join(f'"{t}"' for t in banned)
            + ". Give the fact, not a label announcing that it matters"
        )
    return findings


# ---------------------------------------------------------------------------
# Grounding: a sentence that names what the week never printed is cut.
#
# CLAUDE.md Rule 1: every fact traces to a source in the data; a claim that
# cannot be sourced is cut, not softened. The writer is handed only the week's
# printed stories, and still reached past them: Issue #26's cover carried "the
# High North", "Cold War-era military bases" and China as "a near-Arctic
# state", and Issue #27's carried "the U.S. withdrawal from the Joint
# Comprehensive Plan of Action". None of it was in that week's record.
#
# The check is deliberately narrow, because a false cut costs a sentence and
# a false pass costs a fact: a sentence goes when it carries a NUMBER or a
# MULTI-WORD PROPER NAME the sources do not. A name passes when the sources
# hold its last two capitalised words as a phrase and every capitalised word
# on its own ("United States President Donald Trump" against a record that
# says "President Donald Trump" and "United States"). Unnamed background
# ("melting ice caps") is not caught here; the prompt's grounding line is the
# control for that.
# ---------------------------------------------------------------------------
_G_SENT_RE = re.compile(r"(?:(?<=[.!?])|(?<=[.!?][\"\u201d']))\s+(?=[\"\u201c']?[A-Z0-9])")
_G_NUM_RE = re.compile(r"\d[\d,.]*\d|\d")
_G_CAP = r"[A-Z][\w'\u2019.-]*"
_G_NAME_RE = re.compile(_G_CAP + r"(?:\s+(?:of|the|de|al|bin)\s+" + _G_CAP + r"|\s+" + _G_CAP + r")+")
_G_OPENERS = frozenset("""The A An In On But And This That These Those For As At By With When While If Its His
Her Their It He She They We After Before Since Until Over Under From Into Across Such Both Each Many Most Some
Every Yet Still So Then Now Here There What Why How Where Who Which Meanwhile However Although Though Outside
Inside Despite During Against Within Without Under Among Between Following Last Next""".split())


def _g_norm(text):
    return re.sub(r"\s+", " ", (text or "").replace("\u2019", "'")).lower()


def _g_num(n):
    return n.replace(",", "").rstrip(".")


def unsourced_terms(sentence, source_text, source_nums=None):
    """The numbers and multi-word names in `sentence` the sources do not hold."""
    src = _g_norm(source_text)
    nums = source_nums if source_nums is not None else {_g_num(n) for n in _G_NUM_RE.findall(source_text or "")}
    missing = []
    for n in _G_NUM_RE.findall(sentence):
        if _g_num(n) not in nums:
            missing.append(n)
    for m in _G_NAME_RE.finditer(sentence):
        name = re.sub(r"['\u2019]s$", "", m.group(0).rstrip("."))
        caps = [re.sub(r"['\u2019]s$", "", c) for c in re.findall(_G_CAP, name)]
        while caps and caps[0] in _G_OPENERS:
            caps = caps[1:]
        if len(caps) < 2:
            continue
        if _g_norm(name) in src:
            continue
        tail = name[name.rfind(caps[-2]):]
        if _g_norm(tail) in src and all(re.search(r"\b" + re.escape(c.lower().rstrip(".")) + r"\b", src) for c in caps):
            continue
        missing.append(name)
    return missing


def ground_text(text, source_text):
    """`text` with every sentence carrying an unsourced number or name cut.

    Returns (kept_text, cut) where `cut` lists (sentence, missing_terms).
    Paragraph breaks are kept; a paragraph emptied by the cut is dropped.
    """
    if not text:
        return text, []
    nums = {_g_num(n) for n in _G_NUM_RE.findall(source_text or "")}
    cut, paras = [], []
    for para in text.split("\n\n"):
        kept = []
        for sent in _G_SENT_RE.split(para.strip()):
            if not sent:
                continue
            miss = unsourced_terms(sent, source_text, nums)
            if miss:
                cut.append((sent, miss))
            else:
                kept.append(sent)
        if kept:
            paras.append(" ".join(kept))
    return "\n\n".join(paras), cut


def _cut_sentences(text, test):
    """`text` with every sentence for which `test(sentence)` is truthy cut.

    Returns (kept_text, cut) where `cut` lists (sentence, test_result). Same
    sentence splitter and paragraph handling as `ground_text`, so a piece cut
    by one rule and then another is split the same way both times.
    """
    if not text:
        return text, []
    cut, paras = [], []
    for para in text.split("\n\n"):
        kept = []
        for sent in _G_SENT_RE.split(para.strip()):
            if not sent:
                continue
            why = test(sent)
            if why:
                cut.append((sent, why))
            else:
                kept.append(sent)
        if kept:
            paras.append(" ".join(kept))
    return "\n\n".join(paras), cut


# ---------------------------------------------------------------------------
# Quotations: verbatim from the week, or not in quotation marks at all.
#
# Issue #26 set three passages in quotation marks that the week's printed
# stories did not carry as quoted: Rasmussen's "binding agreement" (reported
# as paraphrase), a Trump quote that ran a clause past the printed one, and
# "EVER have a base", which no story carried at all. `ground_text` could not
# see any of it, because every name and number in those sentences WAS
# sourced. Quotation marks are a claim that these are the speaker's words,
# so the check is literal: the quoted span, punctuation at its ends aside,
# must appear in the sources. Case and curly quotes are normalised; nothing
# else is.
# ---------------------------------------------------------------------------
_Q_RE = re.compile(r'"([^"\n]+?)"|“([^“”\n]+?)”')
_Q_EDGE = " \t.,;:!?'’‘"


def _q_norm(text):
    t = (text or "").replace("’", "'").replace("‘", "'")
    t = t.replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", t).strip().lower()


def quotations(text):
    """Every double-quoted span in `text`, straight or curly, as written."""
    return [a or b for a, b in _Q_RE.findall(text or "")]


def unsourced_quotes(text, source_text, allow=()):
    """The quoted spans in `text` that `source_text` does not hold verbatim.

    `allow` is a set of spans that may be quoted without a source: Void's own
    section titles, which the page quotes as names, not as anybody's words.
    """
    src = _q_norm(source_text)
    allowed = {_q_norm(a).strip(_Q_EDGE) for a in allow}
    out = []
    for q in quotations(text):
        core = _q_norm(q).strip(_Q_EDGE)
        if not core or core in allowed:
            continue
        if core not in src:
            out.append(q)
    return out


def ground_quotes(text, source_text, allow=()):
    """`text` with every sentence carrying an unsourced quotation cut.

    Cut, not unquoted: removing the marks would leave the same words standing
    as Void's own assertion of what someone said, which is the error in a
    quieter form. Returns (kept_text, cut).
    """
    return _cut_sentences(text, lambda s: unsourced_quotes(s, source_text, allow))


# ---------------------------------------------------------------------------
# The kill list cuts the SENTENCE, not the piece.
#
# `drop_terms` used to discard a whole cover, column or department over one
# word that survived the regeneration: 3 of 5 columns were dropped on
# 2026-09-27. A kill-list verb ("underscores") cannot be deleted from its
# sentence by code, because the sentence loses its verb; it CAN be deleted
# with its sentence, which costs one sentence and keeps every sourced fact
# around it.
# ---------------------------------------------------------------------------
def cut_slop_sentences(text):
    """`text` with every sentence carrying a kill-list hit cut. (kept, cut)."""
    return _cut_sentences(text, drop_terms)


# ---------------------------------------------------------------------------
# Length is sized to what the sources can carry, and checked AFTER the cut.
#
# The cover brief was 800-1200 words whatever the week held. A thread printed
# once, about 450 words of summary and points, cannot fill 800 words without
# reaching past its sources, and the reaching is what `ground_text` and the
# source check then cut: Issue #26's Greenland cover lost seventeen claims
# that way. The length was enforced before those cuts and never after, so the
# brief demanded the padding and the checks removed it, and nothing measured
# what was left. A short sourced piece is acceptable. A padded one is not.
# ---------------------------------------------------------------------------
#: A piece runs no longer than the words it was written from.
SOURCE_SIZE_SHARE = 1.0
#: Under this many source words there is nothing to write a piece from.
MIN_SOURCE_WORDS = 120
#: The floor of a sized brief, as a share of its ceiling.
SIZED_FLOOR_SHARE = 0.6
#: After the cuts, a piece under this share of its sized floor is a fragment.
AFTER_CUT_FLOOR_SHARE = 0.5


def sized_spec(spec, source_words):
    """The word brief sized to the sources, or None when they cannot carry one.

    The ceiling is the smaller of the section's own ceiling and the source
    word count; the floor follows the ceiling down. Never raised: a week with
    more material than the section's brief still gets the section's brief.
    """
    spec = spec or {}
    if source_words < MIN_SOURCE_WORDS:
        return None
    hi = min(int(spec.get("max_words") or source_words), int(source_words * SOURCE_SIZE_SHARE))
    lo = min(int(spec.get("min_words") or 0), int(hi * SIZED_FLOOR_SHARE))
    return {"min_words": lo, "max_words": hi}


def length_after_cut(text, spec):
    """None when what is left after the cuts can ship; else the reason it cannot.

    Run on the text that survived `ground_text`, `ground_quotes`, the kill-list
    cut and the source check. It never asks for more words: a piece under its
    floor but over the fragment line ships short, because the only way to
    lengthen it is to write what the sources do not hold.
    """
    n = word_count(text)
    floor = int((spec or {}).get("min_words") or 0)
    if floor and n < floor * AFTER_CUT_FLOOR_SHARE:
        return f"{n} words left after the cuts, under half its {floor}-word floor"
    return None


def source_words(rows):
    """Words a writer is handed from these printed rows (see `row_corpus`)."""
    return word_count(row_corpus(rows))


def row_corpus(rows):
    """The printed rows in full, as a writer reads them: every field Stage 2 wrote.

    A writer handed a title and a summary was asked for 500 words and had
    about 60 to write them from (audit 4, the tech and sports pages). The
    consensus and divergence points are part of what Void printed, and they
    are where the attributed quotations usually live.
    """
    blocks = []
    for r in rows or []:
        when = str(r.get("printed_on") or r.get("first_published") or "")[:10]
        parts = [f"[{when}] {r.get('title') or ''}".strip()]
        if r.get("source_count"):
            parts.append(f"Sources: {r['source_count']}")
        if r.get("summary"):
            parts.append(f"Summary: {r['summary']}")
        for key, label in (("consensus_points", "Agreed across sources"),
                           ("divergence_points", "Where sources differ")):
            v = r.get(key)
            if v:
                if isinstance(v, str):
                    parts.append(f"{label}: {v}")
                else:
                    parts.append(f"{label}: " + json.dumps(v, ensure_ascii=False))
        blocks.append("\n".join(parts))
    return "\n\n".join(blocks)


def retry_suffix(findings):
    """The findings, named, appended to the original prompt for one retry.

    Naming them is the whole point. Stage 2's validator pass established the
    pattern: a bare "try again" gets a reworded version of the same defect.
    """
    return (
        "\n\nYour previous attempt was rejected. "
        + " ".join(f"({i + 1}) {f}." for i, f in enumerate(findings))
        + " Rewrite it in full, fixing every point. Do not acknowledge this note."
    )


ISSUE_EPOCH = datetime(2026, 3, 22, tzinfo=timezone.utc)

# ---------------------------------------------------------------------------
# Volume and number: the ONE issue label
#
# `issue_number` counts weeks from ISSUE_EPOCH and is the sort key; a reader
# never sees it. The page sets "Vol. I, No. 1" from frontend/app/weekly/
# format.ts, and until 2026-09-21 the podcast feed set "Issue #26" for the
# same issue from the raw number: one issue, two labels. This is the Python
# twin of format.ts (issueRef / romanNumeral / issueLabel), and
# tests/test_podcast_feed.py asserts the two constants agree.
# ---------------------------------------------------------------------------

# Epoch issue number of Vol. I, No. 1: the week of 2026-09-14.
WEEKLY_LAUNCH_ISSUE = 26
WEEKS_PER_VOLUME = 52

_ROMAN = (
    (1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"),
    (50, "L"), (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"),
)


def roman_numeral(n) -> str:
    try:
        left = int(n)
    except (TypeError, ValueError):
        return ""
    if left < 1:
        return ""
    out = ""
    for value, sym in _ROMAN:
        while left >= value:
            out += sym
            left -= value
    return out


def issue_ref(raw) -> dict:
    """{pilot, volume, number, serial}: the same arithmetic as format.ts."""
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return {"pilot": True, "volume": 0, "number": 0, "serial": 0}
    serial = n - WEEKLY_LAUNCH_ISSUE + 1
    if serial < 1:
        return {"pilot": True, "volume": 0, "number": 0, "serial": 0}
    return {
        "pilot": False,
        "volume": (serial - 1) // WEEKS_PER_VOLUME + 1,
        "number": (serial - 1) % WEEKS_PER_VOLUME + 1,
        "serial": serial,
    }


def issue_label(raw) -> str:
    """"Vol. I, No. 1", or "Pilot issue" for an issue before the launch."""
    r = issue_ref(raw)
    if r["pilot"]:
        return "Pilot issue"
    return f"Vol. {roman_numeral(r['volume'])}, No. {r['number']}"


def weekly_window(now, week_offset=0):
    """-> (week_start, week_end, issue_number) for a Monday-to-Sunday week.

    `week_offset` counts weeks BACK from the week that most recently closed: 0
    is that week, 1 the week before it, and -1 the week still in progress
    (partial data, for a mid-week refresh).

    THE WEEK CLOSES ON SUNDAY NIGHT, AND SUNDAY IS INSIDE IT. Void Weekly
    publishes on Sunday evening, so the issue covers the week the reader has
    just lived through, Monday to that same Sunday. The modulo is what makes
    that true: `weekday() + 1` walks back to the PREVIOUS Sunday from every
    day including Sunday itself, which on a Sunday means skipping the week
    that is closing as the issue goes out. `% 7` sends Sunday to zero and
    leaves every other weekday exactly where it was, so a run on any other day
    still resolves to the last completed week and the 52-Monday test is
    unchanged by this.

    `now` is injected rather than read from the clock precisely because this
    arithmetic was WRONG IN THE OTHER DIRECTION until 2026-09-19 and could
    only be caught in production: offset 0 resolved to the week CONTAINING
    today on every weekday, so the Monday cron generated the week that had
    just STARTED. Issue #23 (week of 2026-08-24, generated 2026-08-24 12:48)
    is the last one that shipped that way.
    """
    week_end = now - timedelta(days=((now.weekday() + 1) % 7) + (week_offset * 7))
    week_start = week_end - timedelta(days=6)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_end.replace(hour=23, minute=59, second=59, microsecond=0)
    issue_number = max(1, int((week_start - ISSUE_EPOCH).days / 7) + 1)
    return week_start, week_end, issue_number


# ---------------------------------------------------------------------------
# Row assembly — pure, so the persistence contract is testable without a key
#
# This was 60 lines of dict literal inline in generate_weekly_digest, which is
# why nothing ever noticed that `tech` and `sports` were generated every week
# and then dropped: the row had a comment where the write should have been.
# ---------------------------------------------------------------------------

# Front-of-book order. A magazine's running order is editorial data, so it
# lives in a list rather than being implied by the order of column
# declarations in whatever renders it.
DEPARTMENTS = (
    ("tech", "Technology"),
    ("sports", "Sports & Culture"),
)


def _department_item(slug, label, essay):
    """One front-of-book department, or None when the week had no such story."""
    if not essay or not isinstance(essay, dict):
        return None
    text = (essay.get("text") or "").strip()
    if not text:
        return None
    return {
        "slug": slug,
        "label": label,
        "headline": (essay.get("headline") or "").strip(),
        "text": text,
        "cluster_id": essay.get("cluster_id"),
        "image_url": essay.get("image_url"),
        "image_attribution": essay.get("image_attribution"),
        "image_caption": essay.get("image_caption"),
    }


def _opinion_items(opinions, issue_number):
    """The flat opinion array, with the dialectic made explicit.

    `_generate_opinions` writes a deliberate structure: the first two essays
    argue the SAME cover story from left and right, each told the other exists.
    That structure survived only as an array index, and the three lean buckets
    destroyed it outright — center-left, center and center-right all land in
    `opinion_center`, and the page then read `[0]` of each bucket and dropped
    two essays on the floor. `pair_id` states it instead of implying it: two
    entries sharing one are a head-to-head on a single story.
    """
    items = []
    for i, o in enumerate(opinions or []):
        item = {
            "headline": (o.get("headline") or "").strip(),
            "text": (o.get("text") or "").strip(),
            "lean": o.get("lean", ""),
            "topic": o.get("topic", ""),
            "cluster_id": o.get("cluster_id"),
            "paired": bool(o.get("paired")),
            "position": i,
        }
        if item["paired"]:
            item["pair_id"] = f"w{issue_number}-{o.get('cluster_id') or 'lead'}"
        items.append(item)
    return items


def build_weekly_row(*, edition, week_start, week_end, issue_number, cover_items,
                     opinions, tech, sports, recap_stories, bias_text, bias_data,
                     weekly_opinion, audio, cover_image, total_articles,
                     week_days=None,
                     total_clusters, gemini_calls, elapsed, voice_pair=None):
    """Assemble the weekly_digests row. Pure: dict in, dict out.

    `cover_items` arrives with its images already resolved, so this function
    makes no network call and `tests/test_weekly.py` can assert the whole
    persistence contract against a fixture with no Gemini key.
    """
    audio = audio or {}
    weekly_opinion = weekly_opinion or {}
    audio_url = audio.get("audio_url")
    opinion_list = _opinion_items(opinions, issue_number)

    return {
        "edition": edition,
        "week_start": week_start,
        "week_end": week_end,
        "issue_number": issue_number,
        # Cover
        "cover_headline": cover_items[0].get("headline", "") if cover_items else "",
        "cover_text": json.dumps(cover_items),
        "cover_numbers": json.dumps(cover_items[0].get("numbers", []) if cover_items else []),
        "cover_timelines": json.dumps([
            {"story_index": i, "entries": c.get("timeline", [])}
            for i, c in enumerate(cover_items)
        ]),
        # Front-of-book departments. Generated since the section was written and
        # persisted by nothing until 2026-09-20.
        "departments": json.dumps([
            d for d in (
                _department_item("tech", "Technology", tech),
                _department_item("sports", "Sports & Culture", sports),
            ) if d
        ]),
        # Recap
        "recap_stories": json.dumps(recap_stories or []),
        # Opinions. The flat array is the real shape; the three lean buckets are
        # a lossy partition of it, kept so an already-deployed client and every
        # archived row still render.
        "opinions": json.dumps(opinion_list),
        "opinion_left": json.dumps([o for o in opinion_list if o["lean"] == "left"]),
        "opinion_center": json.dumps([o for o in opinion_list
                                      if o["lean"] in ("center", "center-left", "center-right")]),
        "opinion_right": json.dumps([o for o in opinion_list if o["lean"] == "right"]),
        "opinion_topic": ", ".join(o["topic"] for o in opinion_list[:3]),
        # Bias report
        "bias_report_text": bias_text,
        "bias_report_data": json.dumps(bias_data),
        # Audio (fixed weekly pair: Editor + Correspondent)
        "audio_script": audio.get("script"),
        "audio_url": audio_url,
        "audio_duration_seconds": audio.get("duration_seconds"),
        "audio_file_size": audio.get("file_size"),
        # Weekly editorial (one argued week-in-review column + monologue)
        "opinion_text": weekly_opinion.get("opinion_text"),
        "opinion_headline": weekly_opinion.get("opinion_headline"),
        "opinion_lean": weekly_opinion.get("opinion_lean"),
        "opinion_audio_script": weekly_opinion.get("opinion_audio_script"),
        "opinion_start_seconds": audio.get("opinion_start_seconds"),
        # Broadcast desk voices (news pair drives player host chips + label)
        # The chapter rail. `chapters.ts` renders any `kind` and already
        # guards an empty label, which is what lets a new format's rail work
        # with no frontend change — the same reason History's episodes got one.
        # json.dumps, not the list: these are TEXT columns, and the SQLite
        # shim binds what it is given. A list reaches sqlite3 as an
        # unsupported type and takes the whole upsert down with it, which is
        # exactly what would have happened on the first run that rendered an
        # audio edition. W-T05 catches it because it loads every column the
        # exporter parses.
        "audio_chapters": json.dumps(audio["chapters"]) if audio.get("chapters") else None,
        # An engine string, as On Air writes it, not a pair of display names.
        # "The Editor" and "The Correspondent" were a label over an identical
        # signal chain: both mapped to the same two edge voices.
        # No `voice_pair` fallback. It used to fill these in whenever an
        # audio_url existed and the renderer had not named a voice, which is
        # how a row came to advertise "Sadaltager+Achernar" and "The Editor &
        # The Correspondent" over a file those voices never read. The legacy
        # path that needed it is gone; the only renderer left always names its
        # own cast, so a missing voice here means something is wrong and must
        # read as missing rather than be guessed at.
        "audio_voice": audio.get("voice"),
        "audio_voice_label": audio.get("voice_label"),
        # Cover image
        "cover_image_url": cover_image["url"] if cover_image else None,
        "cover_image_attribution": cover_image["attribution"] if cover_image else None,
        "cover_image_source": cover_image["source"] if cover_image else None,
        # Names what the picture is. The weekly illustrates with FILE
        # photography, a picture of the subject rather than the event, and
        # that is honest only while the page says which it is.
        "cover_image_caption": cover_image.get("caption") if cover_image else None,
        # Stats
        "total_articles": total_articles,
        # The week, day by day. Computed from rows the generator already had
        # and threw away; the shape of the week is the one thing only a weekly
        # can show.
        "week_days": json.dumps(week_days or []),
        "total_clusters": total_clusters,
        "generator": "gemini-flash",
        "gemini_calls_used": gemini_calls,
        "generation_duration_seconds": round(elapsed, 1),
    }
