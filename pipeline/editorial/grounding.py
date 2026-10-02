"""A verification index for the sources a card was written from. NOT their text.

E-13 and E-14 read a card against its sources. Both can only run where those
sources still exist, and `articles.full_text` lives in `pipeline_state.db`,
which is gitignored and dies with the Actions cache, while
`deepdive/<id>.json` keeps only each source's RSS snippet. That gap is why the
2026-09-20 feed audit could not resolve two of its findings either way: no
audit can confirm or refute a claim against evidence nobody kept.

WHY THIS MODULE NO LONGER STORES PROSE (2026-09-22). It used to write up to
24,000 characters of each source article into `frontend/build-data/grounding/`,
which the repo commits, and the repo keeps every commit forever. Measured on
the committed tree: 35 files, 975 records, **519,041 characters of publisher
article text**, longest single record 10,003 characters, in a public
repository's permanent history.

`docs/IP-COMPLIANCE.md` names as its single highest-priority control: do not
store `full_text` permanently, truncate it or delete it, store the derived
scores and not the source text. The daily pipeline obeys that at
`main.py` step 10, truncating `full_text` to 300 characters after analysis. So
the throwaway database was protected and the permanent public repo leaked. The
protection was pointing the wrong way.

Deleting the module was not an option: E-13 and E-14 are how Rule 1 is
enforced against fabricated numbers and invented quotations, and an audit with
no evidence is not an audit.

WHAT IS STORED INSTEAD, and why each part is sufficient:

  numbers   E-13 asks "does this multi-digit number appear in any source?".
            That needs the SET of numbers, nothing more. A list of integers is
            not expressive content and cannot be read as journalism.

  shingles  E-14 asks "does this span of four or more words appear verbatim?".
            That needs a membership test over word sequences, not the
            sequences themselves. So the record carries a Bloom filter of the
            source's overlapping 4-word shingles, folded the same way E-14
            folds a quotation. A Bloom filter answers membership and **cannot
            be inverted to recover text**: it is a bit array, the words are
            gone.

The trade is a false-positive rate, and its direction matters. A Bloom filter
never reports absent-when-present, so E-14 can never gain a false accusation
from this. It can report present-when-absent, which would let a fabricated
quotation through. That is the dangerous direction, so the rate is set low
(BLOOM_FP) and a quotation is only cleared when EVERY one of its consecutive
shingles is present: for a quote of k shingles the error compounds to
BLOOM_FP ** k, so a ten-word quote is cleared in error at about 1e-12. A
four-word quote, the shortest E-14 inspects, has one shingle and carries the
bare BLOOM_FP.

The cap stays, and stays recorded. A cap that went unrecorded would be worse
than no cap: an auditor would read a number's absence as fabrication when it
was merely cut off. Every record carries `truncated`, and a reader that sees it
set must not conclude "ungrounded" from this file alone. That is the same
defect the Weekly shipped by publishing `.limit(500)` as an exact count.

FORMAT 3 (2026-10-02, rev 85), three additions, each an index and never prose:

  decimals  "8.3%" used to read as the single digits 8 and 3, both ignored,
            so a decimal figure was never checked at all (audit 3 item 3).
            Numbers now keep their decimal part: 8.3, 47.6, 1.79.

  contexts  E-13 asked only whether a number exists somewhere. The Iraq card of
            2026-10-01 attached 4,419 U.S. deaths to Operation Inherent Resolve;
            the sources attach it to the 23 years since 2003, and E-13 passed
            because 4,419 is in them. A second Bloom filter holds (number, word)
            pairs from each SOURCE SENTENCE that carries a number, so a check
            can ask "does any source sentence put this number beside this word
            or this name?". Pairs, hashed into bits: no sentence can be read
            back.

  junctions E-14's shingles strip punctuation, so a quotation whose ellipsis
            was turned into a full stop read as verbatim (the Hegseth card,
            2026-10-01). A third Bloom filter holds every PUNCTUATED word
            junction ("department...no"), so a quotation that changes the
            punctuation between two words fails. An ellipsis in the card is the
            one legitimate cut mark and is honoured.

WHEN THE INDEX IS BUILT (rev 85). Step 10 of `main.py` truncates every body to
300 characters, and `export_static.py` used to build this record afterwards,
so the median indexed article was 496 characters and a post-run audit
false-flagged 48 numbers and 6 quotations across one top 20. Stage 2 now
writes the record at 8f from the bodies it reviewed (`stage2.write_bench_index`),
before step 10, and the export keeps that record rather than rebuilding it
from the stubs. Each article row says whether its body was already a
300-character stub when indexed (`stub`), because an article carried in from
an earlier run by the 36-hour lookback was truncated by THAT run's step 10,
and coverage has to be judged honestly.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import pathlib
import re
from typing import Any

# How much of each article is INDEXED. No text is stored, so this is a bound
# on work and on index size rather than on retained content.
#
# 24,000 until rev 85, when it was never reached: the index was built after
# step 10 had cut every body to 300 characters. Built from whole bodies, 24,000
# would commit roughly 300 KB per cluster, 10 MB a day, into a repository that
# keeps every commit. The summarizer reads at most 2,200 characters of a body
# (`cluster_summarizer._ARTICLE_BODY_MAX_CHARS`), so 3,000 covers everything a
# card can have been written from with room to spare, and each article row
# still records `truncated` for anything longer.
PER_ARTICLE_CHARS = 3_000

DIRNAME = "grounding"

# Record format version, so an audit reading an old file knows it holds prose
# and a new one knows it holds an index. 2 is the first index; 3 adds decimals,
# number contexts and punctuated junctions. A format-2 record is still an index
# (no prose) and is still read, with the format-3 questions answered "unknown".
FORMAT = 3
MIN_INDEX_FORMAT = 2

# The step-10 stub: `main.py` cuts a body to 297 characters plus "...".
STUB_CHARS = 300

# Where an index was built. "pre-truncation" is Stage 2 at 8f, from the bodies
# the card was reviewed against; "export" is the fallback in export_static.py,
# from whatever the database still holds after step 10.
STAGE_PRE = "pre-truncation"
STAGE_EXPORT = "export"

# Context pairs are a SECONDARY check whose error direction is lenient (a false
# positive clears an attachment), so they take a looser rate than quotations.
CONTEXT_FP = 0.02

# Words either side of a number that count as its context. The whole sentence
# was measured first and made the context filter the largest part of the
# record; the words that say what a number counts sit beside it.
CONTEXT_WINDOW = 6

# Words per shingle. Four, because that is E-14's own floor for what counts as
# a quotation, so the shortest inspectable quote maps to exactly one shingle.
SHINGLE_WORDS = 4

# Target false-positive rate per shingle lookup. See the note above on why the
# direction of this error matters and why it compounds away on longer quotes.
BLOOM_FP = 0.001


# --------------------------------------------------------------------------
# A minimal Bloom filter. Pure stdlib, deterministic, and small enough that the
# index is smaller than the prose it replaces.
# --------------------------------------------------------------------------

def _bloom_params(n_items: int, fp: float = BLOOM_FP) -> tuple[int, int]:
    """(bits, hashes) for n items at the target false-positive rate."""
    n = max(1, n_items)
    bits = max(64, int(math.ceil(-(n * math.log(fp)) / (math.log(2) ** 2))))
    bits += (-bits) % 8  # whole bytes
    hashes = max(1, int(round((bits / n) * math.log(2))))
    return bits, min(hashes, 16)


def _bloom_positions(token: str, bits: int, hashes: int):
    """Deterministic hash positions for a token, derived from one digest."""
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    for i in range(hashes):
        # 4 bytes per hash, cycling the digest for more than 8 hashes.
        off = (i * 4) % (len(digest) - 4)
        yield int.from_bytes(digest[off:off + 4], "big") % bits


class Bloom:
    """Membership only. There is no way back to the inserted tokens."""

    __slots__ = ("bits", "hashes", "array")

    def __init__(self, bits: int, hashes: int, array: bytearray | None = None):
        self.bits = bits
        self.hashes = hashes
        self.array = array if array is not None else bytearray(bits // 8)

    def add(self, token: str) -> None:
        for p in _bloom_positions(token, self.bits, self.hashes):
            self.array[p >> 3] |= 1 << (p & 7)

    def __contains__(self, token: str) -> bool:
        return all(self.array[p >> 3] & (1 << (p & 7))
                   for p in _bloom_positions(token, self.bits, self.hashes))

    def encode(self) -> str:
        return base64.b64encode(bytes(self.array)).decode("ascii")

    @classmethod
    def decode(cls, bits: int, hashes: int, blob: str) -> "Bloom":
        return cls(bits, hashes, bytearray(base64.b64decode(blob)))


# --------------------------------------------------------------------------
# Folding and extraction. These must stay in lock-step with standard.py's
# _fold_quote and _numbers, or the index answers a different question from the
# one E-13 and E-14 ask. tests/test_grounding.py asserts that they agree.
# --------------------------------------------------------------------------

# A number, with its thousands separators and its decimal part. "8.3%" is 8.3,
# "1,200" is 1200, "47.6 percent" is 47.6.
_NUM_RE = re.compile(r"\b\d[\d,]*(?:\.\d+)?\b")


def fold(text: str) -> str:
    """Lowercase, straighten the punctuation a summarizer rewrites, collapse.

    Mirrors `standard._fold_quote`. Kept here rather than imported because this
    module is loaded by the export and must not pull in the validator graph.
    """
    t = (text or "").lower()
    for curly, plain in (("‘", "'"), ("’", "'"), ("“", '"'),
                         ("”", '"'), ("–", "-"), ("—", "-")):
        t = t.replace(curly, plain)
    return re.sub(r"\s+", " ", t).strip()


def norm_number(raw: str) -> str | None:
    """One number token normalised, or None when it is out of scope.

    Integers need two digits or more, so "five officers" and a lone digit are
    out. A decimal is always in scope: "8.3%" is a precise claim however short.
    Trailing zeros after the point are dropped, so 8.30 and 8.3 agree.
    """
    raw = (raw or "").replace(",", "")
    if "." in raw:
        whole, _, frac = raw.partition(".")
        frac = frac.rstrip("0")
        whole = whole.lstrip("0") or "0"
        if not whole.isdigit() or (frac and not frac.isdigit()):
            return None
        if frac:
            return f"{whole}.{frac}"
        raw = whole
    if raw.isdigit() and len(raw) >= 2:
        return raw.lstrip("0") or "0"
    return None


def numbers_in(text: str) -> list[str]:
    """Numbers in scope, normalised. `standard._numbers` is this function."""
    out = set()
    for m in _NUM_RE.finditer(text or ""):
        n = norm_number(m.group(0))
        if n is not None:
            out.add(n)
    return sorted(out, key=lambda s: (len(s), s))


# --------------------------------------------------------------------------
# Sentences, context words and proper names. Used at index time over the
# sources and at check time over the card, so both sides tokenise alike.
# --------------------------------------------------------------------------
_SENT_RE = re.compile(
    r"(?<=[.!?])[\"'”’)\]]*\s+(?=[\"'“‘(\[]?[A-Z0-9])")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'’&.-]*")
_CAP = r"[A-Z][\w'’&.-]*"
_LINK = r"(?:of|the|de|al|bin|von|van|la|du)"
_NAME_RE = re.compile(_CAP + r"(?:\s+" + _LINK + r"\s+" + _CAP + r"|\s+" + _CAP + r")+")
CONTEXT_STOP = frozenset("""
a an the and or but if of in on at to for from by with as into onto over under
about after before during since until than then that this these those there
their them they he she his her its it we our you your i me my is are was were
be been being has have had do does did will would could should may might can
not no nor so such per via also just only more most less least very said says
say told tell according while when where which who whom whose what why how
all any each both some other another many much few one two three four five six
seven eight nine ten percent per cent mr mrs ms dr last first new up out down
off against between among around
""".split())
NAME_OPENERS = frozenset("""
The A An In On But And This That These Those For As At By With When While If
Its His Her Their It He She They We After Before Since Until Over Under From
Into Across Such Both Each Many Most Some Every Yet Still So Then Now Here There
What Why How Where Who Which Meanwhile However Although Though Despite During
Against Within Without Among Between Following Last Next Separately Earlier
Later Also
""".split())


_ABBREV_END = re.compile(
    r"(?:\b(?:Mr|Mrs|Ms|Dr|St|Gen|Sen|Rep|Gov|Lt|Col|Sgt|Capt|Cmdr|Adm|Jr|Sr|"
    r"Prof|Rev|Hon|No|Nos|vs|Inc|Corp|Co|Ltd|Jan|Feb|Mar|Apr|Aug|Sept?|Oct|Nov|"
    r"Dec)\.|\b(?:[A-Z]\.){1,3})$")


def sentences_of(text: str) -> list[str]:
    """Sentences, not split after "Mr." or an initial such as "U.S." or "J."."""
    out: list[str] = []
    for piece in _SENT_RE.split(text or ""):
        piece = piece.strip()
        if not piece:
            continue
        if out and _ABBREV_END.search(out[-1]):
            out[-1] = f"{out[-1]} {piece}"
        else:
            out.append(piece)
    return out


def context_word(token: str) -> str | None:
    """A token as a context word: folded, possessive and plural light-stripped."""
    w = (token or "").replace("’", "'").lower().strip(".'-&")
    w = re.sub(r"'s$", "", w)
    if len(w) < 3 or w in CONTEXT_STOP or not w[0].isalpha():
        return None
    if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
        w = w[:-1]
    return w


def context_words(sentence: str) -> set[str]:
    return {w for w in (context_word(t) for t in _WORD_RE.findall(sentence or ""))
            if w}


def name_key(name: str) -> str:
    t = (name or "").replace("’", "'").lower()
    t = re.sub(r"'s\b", "", t)
    return re.sub(r"\s+", " ", t.replace(".", "")).strip()


def proper_names(sentence: str) -> list[str]:
    """Multi-word capitalised names in a sentence, folded, openers removed."""
    out = []
    for m in _NAME_RE.finditer(sentence or ""):
        toks = m.group(0).split()
        while toks and (toks[0] in NAME_OPENERS or toks[0][:1].islower()):
            toks = toks[1:]
        while toks and toks[-1][:1].islower():
            toks = toks[:-1]
        if sum(1 for t in toks if t[:1].isupper()) < 2:
            continue
        out.append(name_key(" ".join(toks)))
    return out


def context_pairs(text: str):
    """(number, key) pairs from every sentence of `text` that carries a number.

    key is a context word within CONTEXT_WINDOW words of the number,
    "P:<name>" for a multi-word proper name anywhere in the same sentence, or "F:<first word>" for that name's first word, which is what lets
    a check see that the source puts the number beside a DIFFERENT
    "Operation ..." from the one the card names.
    """
    for sent in sentences_of(text):
        if not _NUM_RE.search(sent):
            continue
        names = set()
        for nm in proper_names(sent):
            names.add("P:" + nm)
            names.add("F:" + nm.split(" ")[0])
        toks = sent.split()
        for i, tok in enumerate(toks):
            for m in _NUM_RE.finditer(tok):
                n = norm_number(m.group(0))
                if n is None:
                    continue
                lo, hi = max(0, i - CONTEXT_WINDOW), i + CONTEXT_WINDOW + 1
                for w in context_words(" ".join(toks[lo:hi])):
                    yield n, w
                for k in names:
                    yield n, k


# --------------------------------------------------------------------------
# Punctuated junctions (E-14 keeps punctuation).
# --------------------------------------------------------------------------
_JUNCTION_PUNCT = re.compile(r"(?:\.\.\.|[.,;:!?])+$")


def _punct_tokens(text: str) -> list[tuple[str, str]]:
    """(word, mark) for each token, quotation marks removed.

    An apostrophe inside a word ("don't") is kept; one that opens or closes a
    quotation is dropped with the other quotation marks. "…" and "..." are
    the same mark.
    """
    t = fold(text).replace("…", "...")
    t = t.replace('"', " ")
    out = []
    for tok in t.split():
        tok = tok.lstrip("'([")
        tok = re.sub(r"'(?=[.,;:!?)\]]*$)", "", tok)
        tok = tok.rstrip(")]")
        m = _JUNCTION_PUNCT.search(tok)
        mark = m.group(0) if m else ""
        word = tok[:len(tok) - len(mark)].strip(_EDGE)
        if not word:
            continue
        mark = "..." if "..." in mark else mark[-1:]
        out.append((word, mark))
    return out


def junctions_of(text: str):
    """Every punctuated junction, "word<mark>next", for a mark in .,;:!? or ...

    Only junctions that CARRY a mark are indexed. An unpunctuated pair is
    already covered by the word shingles.
    """
    toks = _punct_tokens(text)
    for (w, mark), (nxt, _) in zip(toks, toks[1:]):
        if mark:
            yield f"{w}{mark}{nxt}"


def quote_junctions(segment: str):
    """(junction, mark, word, next) for each adjacent pair inside one segment.

    The segment's own last mark is never examined: a quotation's closing
    punctuation is the writer's typography ("here," for "here."), not the
    speaker's.
    """
    toks = _punct_tokens(segment)
    for (w, mark), (nxt, _) in zip(toks, toks[1:]):
        yield f"{w}{mark}{nxt}", mark, w, nxt


# Punctuation that clings to a word and must not decide whether a shingle
# matches. The source carries `"we` and `responsible,"` where a quotation
# carries `we` and `responsible`, and E-14's own test tolerates that because it
# is a SUBSTRING test. A word-shingle index has to strip the same characters at
# both ends, at index time and at query time, or a verbatim quotation reads as
# fabricated. Internal apostrophes are kept, because "don't" is one word.
_EDGE = "\"'\u201c\u201d\u2018\u2019,.;:!?()[]{}-\u2013\u2014"


def words_of(text: str) -> list:
    """Folded words with edge punctuation removed. Empty tokens dropped."""
    return [w for w in (t.strip(_EDGE) for t in fold(text).split()) if w]


def shingles_of(text: str, size: int = SHINGLE_WORDS):
    """Overlapping word shingles of folded, edge-stripped text.

    One widening is accepted here and stated rather than hidden: stripping
    punctuation lets a shingle straddle a sentence boundary, so a span that
    appears only as "... he said. The minister ..." would be cleared as though
    contiguous. E-14's substring test would not clear it. The realistic failure
    E-14 exists to catch is a quotation that appears NOWHERE in the sources,
    and that case is unaffected; the alternative, keeping punctuation in the
    shingles, fails every genuine quotation instead, which is the far worse
    error.
    """
    words = words_of(text)
    if len(words) < size:
        if words:
            yield " ".join(words)
        return
    for i in range(len(words) - size + 1):
        yield " ".join(words[i:i + size])


# --------------------------------------------------------------------------
# Record build / read
# --------------------------------------------------------------------------

def is_stub(full_text: str | None) -> bool:
    """True when a body is already the step-10 stub (297 chars plus "...")."""
    ft = full_text or ""
    return 0 < len(ft) <= STUB_CHARS and ft.endswith("...")


def _bloom_spec(items: set[str], fp: float) -> dict[str, Any]:
    bits, hashes = _bloom_params(len(items), fp)
    bloom = Bloom(bits, hashes)
    for s in sorted(items):
        bloom.add(s)
    return {"bits": bits, "hashes": hashes, "count": len(items), "fp": fp,
            "bloom": bloom.encode()}


def build_record(cluster_id: str, articles: list[dict[str, Any]],
                 stage: str = STAGE_EXPORT) -> dict[str, Any]:
    """One cluster's sources as a verification index. Stores no article text."""
    rows: list[dict[str, Any]] = []
    all_numbers: set[str] = set()
    shingle_list: list[str] = []
    pairs: set[str] = set()
    junctions: set[str] = set()
    for a in articles or []:
        text = " ".join(
            str(a.get(k)) for k in ("title", "summary", "full_text") if a.get(k)
        ).strip()
        cut = len(text) > PER_ARTICLE_CHARS
        indexed = text[:PER_ARTICLE_CHARS]
        nums = numbers_in(indexed)
        all_numbers.update(nums)
        shingle_list.extend(shingles_of(indexed))
        # Title, summary and body are separate passages: a sentence or a
        # punctuated junction must not run from the end of one into the next.
        budget = PER_ARTICLE_CHARS
        for k in ("title", "summary", "full_text"):
            part = str(a.get(k) or "")[:max(0, budget)]
            budget -= len(part) + 1
            if not part:
                continue
            pairs.update(f"{n}|{key}" for n, key in context_pairs(part))
            junctions.update(junctions_of(part))
        rows.append({
            "id": a.get("id"),
            "url": a.get("url"),
            "chars": len(text),
            "bodyChars": len(str(a.get("full_text") or "")),
            "words": len(words_of(indexed)),
            "truncated": cut,
            "stub": is_stub(a.get("full_text")),
            "numbers": nums,
        })
    uniq = sorted(set(shingle_list))
    bits, hashes = _bloom_params(len(uniq))
    bloom = Bloom(bits, hashes)
    for s in uniq:
        bloom.add(s)
    return {
        "cluster": cluster_id,
        "format": FORMAT,
        "stage": stage,
        "perArticleChars": PER_ARTICLE_CHARS,
        "truncated": any(r["truncated"] for r in rows),
        "numbers": sorted(all_numbers, key=lambda s: (len(s), s)),
        "quotes": {
            "shingleWords": SHINGLE_WORDS,
            "bits": bits,
            "hashes": hashes,
            "count": len(uniq),
            "fp": BLOOM_FP,
            "bloom": bloom.encode(),
        },
        "contexts": _bloom_spec(pairs, CONTEXT_FP),
        "junctions": _bloom_spec(junctions, BLOOM_FP),
        "articles": rows,
    }


def keep_existing(existing: dict[str, Any] | None, article_ids) -> bool:
    """Whether the export should keep a record Stage 2 already wrote.

    Kept when it was built before truncation and covers every article the
    cluster now links. Rebuilding it from the database after step 10 would
    replace an index of whole bodies with an index of 300-character stubs,
    which is the defect this ordering exists to prevent.
    """
    if not existing or existing.get("stage") != STAGE_PRE:
        return False
    have = {a.get("id") for a in existing.get("articles") or []}
    return set(article_ids) <= have


def write_record(build_dir: pathlib.Path, record: dict[str, Any]) -> pathlib.Path:
    out = pathlib.Path(build_dir) / DIRNAME
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{record['cluster']}.json"
    path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return path


def _bloom_of(spec: dict | None) -> "Bloom | None":
    if not spec or not spec.get("bloom"):
        return None
    return Bloom.decode(int(spec["bits"]), int(spec["hashes"]), spec["bloom"])


class Verifier:
    """Answers the questions E-13 and E-14 ask, and nothing else.

    `truncated` means the index does not cover the whole of every source, so a
    negative answer is "cannot confirm" rather than "absent". A caller must not
    turn that into an accusation.

    A format-2 record predates decimals, contexts and junctions. Its capability
    flags say so, and the rules skip those questions rather than accuse.
    """

    __slots__ = ("numbers", "_bloom", "_size", "truncated", "present",
                 "_ctx", "_junc", "decimals")

    def __init__(self, record: dict[str, Any] | None):
        self.present = bool(record)
        rec = record or {}
        self.numbers = set(rec.get("numbers") or ())
        self.truncated = bool(rec.get("truncated"))
        q = rec.get("quotes") or {}
        self._size = int(q.get("shingleWords") or SHINGLE_WORDS)
        self._bloom = _bloom_of(q)
        self._ctx = _bloom_of(rec.get("contexts"))
        self._junc = _bloom_of(rec.get("junctions"))
        self.decimals = int(rec.get("format") or 0) >= 3

    @property
    def contexts(self) -> bool:
        return self._ctx is not None

    @property
    def punctuation(self) -> bool:
        return self._junc is not None

    def has_number(self, n: str) -> bool:
        return str(n) in self.numbers

    def has_pair(self, n: str, key: str) -> bool:
        return self._ctx is not None and f"{n}|{key}" in self._ctx

    def has_junction(self, junction: str) -> bool:
        return self._junc is not None and junction in self._junc

    def has_span(self, text: str) -> bool:
        """True when every consecutive shingle of `text` is in the index.

        Requiring all of them is what drives the false-positive rate down to
        BLOOM_FP ** k for a span of k shingles.
        """
        if self._bloom is None:
            return False
        shingles = list(shingles_of(text, self._size))
        if not shingles:
            return False
        return all(s in self._bloom for s in shingles)


class TextIndex:
    """The same questions over source text still held in memory.

    Built with this module's own extraction, so the write-time answer and the
    after-the-fact answer from a persisted record cannot drift apart. Passages
    are separated by newlines, as `build_record` separates title, summary and
    body.
    """

    __slots__ = ("numbers", "_folded", "_pairs", "_junc", "truncated",
                 "present", "decimals", "contexts", "punctuation")

    def __init__(self, text: str):
        text = text or ""
        self.numbers = set(numbers_in(text))
        self._folded = fold(text)
        passages = [p for p in re.split(r"\n", text) if p.strip()]
        self._pairs = {f"{n}|{k}" for p in passages for n, k in context_pairs(p)}
        self._junc = {j for p in passages for j in junctions_of(p)}
        self.truncated = False
        self.present = bool(self._folded)
        self.decimals = True
        self.contexts = True
        self.punctuation = True

    def has_number(self, n: str) -> bool:
        return str(n) in self.numbers

    def has_pair(self, n: str, key: str) -> bool:
        return f"{n}|{key}" in self._pairs

    def has_junction(self, junction: str) -> bool:
        return junction in self._junc

    def has_span(self, text: str) -> bool:
        return fold(text).strip(" ,.;:!?-") in self._folded


def load_verifier(build_dir: pathlib.Path, cluster_id: str) -> Verifier:
    """The verification index for a cluster.

    A Verifier with `present` False means no record exists, and a caller
    running E-13 or E-14 must skip rather than accuse.
    """
    path = pathlib.Path(build_dir) / DIRNAME / f"{cluster_id}.json"
    if not path.exists():
        return Verifier(None)
    return Verifier(json.loads(path.read_text(encoding="utf-8")))
