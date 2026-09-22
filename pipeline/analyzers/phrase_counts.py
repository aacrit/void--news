#!/usr/bin/env python3
"""Per-outlet phrase COUNTS from full article bodies. Never the bodies.

WHY THIS IS THE CRITICAL PATH, not an enhancement. `lexicon_derive.py` tried to derive
a lean lexicon from the corpus we still have, and the attempt produced a clean negative
result on 2026-09-22: the derived list rediscovered **zero of the 318** hand-written
political phrases, while its top entries were `getty images`, `continue`, `follow`,
`photo`, `this article` and `sep`.

The reason is the corpus, not the method. `articles.full_text` is truncated to 300
characters after analysis (`main.py` step 10, the top control in
`docs/IP-COMPLIANCE.md`), so what survives is titles, RSS summaries and leads, and
those are largely CMS boilerplate. Outlets on the same side often share a publishing
platform, so a chi-squared ranking separates the sides by FINGERPRINTING THEIR
TEMPLATES. It reaches rho +0.23 on held-out outlets doing so, which is worse than
useless: a real-looking number measuring the wrong thing.

Deriving a real lexicon needs article bodies. Keeping article bodies is the thing
`docs/IP-COMPLIANCE.md` forbids, and rightly: this project already found 519,041
characters of publisher prose committed to a public repo and spent a day removing it.

So this module keeps what a derivation needs and nothing a reader could consume: the
COUNT of each phrase, per outlet. A count is derived data. It cannot be read as
journalism, it cannot be reassembled into an article, and it answers the only question
the derivation asks, which is how often each side uses each phrase. This is the same
argument the grounding index won, and `pipeline/editorial/grounding.py`'s header makes
it in full.

WHAT IS STORED, and what is structurally impossible to store:

  phrase        at most MAX_PHRASE_WORDS words. Enforced when writing, not promised,
                so a bug cannot widen it into a sentence.
  outlet        the source id.
  count         an integer.

There is no article id and no ordering, so two phrases from the same article cannot be
associated, which is what would make reassembly conceivable. `tests/test_phrase_counts.py`
asserts the width bound against the data rather than trusting the comment.

CALLED FROM the analysis step in `main.py`, BEFORE the step-10 truncation, which is the
only moment the body exists and the last moment it is allowed to.
"""
from __future__ import annotations

import collections
import re
import sqlite3

# The widest phrase the derivation uses (`lexicon_derive.NGRAM_SIZES`). A row wider
# than this is refused rather than stored: the whole defence of this table is that a
# row is a phrase and not a sentence, and a defence that depends on nobody making a
# mistake is not one.
MAX_PHRASE_WORDS = 3

# Rows per outlet per run. A cap, because an unbounded table of every 3-gram every
# outlet ever printed drifts back toward being a corpus. The tail is noise for a
# chi-squared anyway: `lexicon_derive` discards anything under 50 articles.
TOP_PER_OUTLET = 4000

_WORD = re.compile(r"[a-z][a-z'-]+")

SCHEMA = """
create table if not exists outlet_phrase_counts (
    source_id text not null,
    phrase    text not null,
    words     integer not null,
    count     integer not null default 0,
    updated_at text,
    primary key (source_id, phrase)
);
create index if not exists idx_opc_source on outlet_phrase_counts(source_id);
"""


def phrases_of(text: str, max_words: int = MAX_PHRASE_WORDS):
    """1..max_words grams, lowercased. Deliberately the same shape as
    `lexicon_derive.phrases` so a count here answers the question asked there."""
    words = _WORD.findall((text or "").lower())
    for n in range(1, max_words + 1):
        for i in range(len(words) - n + 1):
            yield " ".join(words[i:i + n])


def accumulate(rows) -> dict[str, collections.Counter]:
    """{source_id: Counter(phrase -> articles containing it)}.

    Counted by PRESENCE per article, not by frequency, which is what a chi-squared over
    documents needs and which also means a repeated phrase cannot be used to infer how
    long an article was.
    """
    out: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for row in rows or []:
        sid = row.get("source_id")
        if not sid:
            continue
        text = " ".join(str(row.get(k) or "") for k in ("title", "summary", "full_text"))
        out[sid].update(set(phrases_of(text)))
    return out


def persist(conn: sqlite3.Connection, tally: dict[str, collections.Counter],
            now: str | None = None) -> int:
    """Merge a run's tally into the table. Returns rows written.

    Refuses any phrase wider than MAX_PHRASE_WORDS. That is the one invariant this
    module exists to hold, so it is enforced at the write rather than upstream where a
    later caller could bypass it.
    """
    conn.executescript(SCHEMA)
    written = 0
    for sid, counter in (tally or {}).items():
        for phrase, count in counter.most_common(TOP_PER_OUTLET):
            n = len(phrase.split())
            if n > MAX_PHRASE_WORDS or not phrase.strip():
                continue
            conn.execute(
                """insert into outlet_phrase_counts(source_id, phrase, words, count,
                                                    updated_at)
                   values(?,?,?,?,?)
                   on conflict(source_id, phrase) do update set
                     count = count + excluded.count,
                     updated_at = excluded.updated_at""",
                (sid, phrase, n, int(count), now))
            written += 1
    conn.commit()
    return written


def record(conn: sqlite3.Connection, articles, now: str | None = None) -> int:
    """The one entry point for the pipeline: tally these articles and merge them."""
    return persist(conn, accumulate(articles), now)
