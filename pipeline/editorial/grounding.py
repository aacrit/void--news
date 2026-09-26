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
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import pathlib
import re
from typing import Any

# How much of each article is INDEXED. No text is stored, so this is now a
# bound on work and on index size rather than on retained content.
PER_ARTICLE_CHARS = 24_000

DIRNAME = "grounding"

# Record format version, so an audit reading an old file knows it holds prose
# and a new one knows it holds an index.
FORMAT = 2

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

_NUM_RE = re.compile(r"\b\d[\d,]*\b")


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


def numbers_in(text: str) -> list[str]:
    """Multi-digit integers, normalised. Mirrors `standard._numbers`."""
    out = set()
    for m in _NUM_RE.finditer(text or ""):
        raw = m.group(0).replace(",", "")
        if raw.isdigit() and len(raw) >= 2:
            out.add(raw.lstrip("0") or "0")
    return sorted(out, key=lambda s: (len(s), s))


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

def build_record(cluster_id: str, articles: list[dict[str, Any]]) -> dict[str, Any]:
    """One cluster's sources as a verification index. Stores no article text."""
    rows: list[dict[str, Any]] = []
    all_numbers: set[str] = set()
    shingle_list: list[str] = []
    for a in articles or []:
        text = " ".join(
            str(a.get(k)) for k in ("title", "summary", "full_text") if a.get(k)
        ).strip()
        cut = len(text) > PER_ARTICLE_CHARS
        indexed = text[:PER_ARTICLE_CHARS]
        nums = numbers_in(indexed)
        all_numbers.update(nums)
        shingle_list.extend(shingles_of(indexed))
        rows.append({
            "id": a.get("id"),
            "url": a.get("url"),
            "chars": len(text),
            "words": len(words_of(indexed)),
            "truncated": cut,
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
        "articles": rows,
    }


def write_record(build_dir: pathlib.Path, record: dict[str, Any]) -> pathlib.Path:
    out = pathlib.Path(build_dir) / DIRNAME
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{record['cluster']}.json"
    path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return path


class Verifier:
    """Answers the two questions E-13 and E-14 ask, and nothing else.

    `truncated` means the index does not cover the whole of every source, so a
    negative answer is "cannot confirm" rather than "absent". A caller must not
    turn that into an accusation.
    """

    __slots__ = ("numbers", "_bloom", "_size", "truncated", "present")

    def __init__(self, record: dict[str, Any] | None):
        self.present = bool(record)
        rec = record or {}
        self.numbers = set(rec.get("numbers") or ())
        self.truncated = bool(rec.get("truncated"))
        q = rec.get("quotes") or {}
        self._size = int(q.get("shingleWords") or SHINGLE_WORDS)
        blob = q.get("bloom")
        self._bloom = (Bloom.decode(int(q["bits"]), int(q["hashes"]), blob)
                       if blob else None)

    def has_number(self, n: str) -> bool:
        return str(n) in self.numbers

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


def load_verifier(build_dir: pathlib.Path, cluster_id: str) -> Verifier:
    """The verification index for a cluster.

    A Verifier with `present` False means no record exists, and a caller
    running E-13 or E-14 must skip rather than accuse.
    """
    path = pathlib.Path(build_dir) / DIRNAME / f"{cluster_id}.json"
    if not path.exists():
        return Verifier(None)
    return Verifier(json.loads(path.read_text(encoding="utf-8")))
