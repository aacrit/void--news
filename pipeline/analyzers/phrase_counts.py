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

# THE KEEP CRITERION, and the defect it replaces.
#
# This was `most_common(4000)`: the 4,000 commonest phrases per outlet. Measured
# 2026-09-23 against the first real harvest (7,901 bodies, 7.34M words, 98 outlets),
# every single outlet hit that ceiling EXACTLY, 392,000 rows over 98 outlets being
# 4,000 each to the row, out of 112,891 distinct phrases seen. Of the 318 hand-written
# political phrases, 59 reached the table and 259 never entered it, and those 59 sat at
# a median frequency rank of 37,906 of 112,891.
#
# So the derivation was handed each outlet's commonest 4,000 phrases, which is by
# construction its page furniture, and asked to find politics in it. It rediscovered
# zero political phrases twice, and neither zero was evidence about the method. Raw
# frequency is the wrong keep criterion because the thing being looked for is RARE.
#
# The band is Gentzkow and Shapiro's own move, in both directions:
#
#   upper   a phrase present in most of an outlet's articles is that outlet's
#           template, not its politics. "subscribe", "follow", "continue reading".
#   lower   a phrase seen once or twice cannot carry a rate difference and is the
#           long tail that made an unbounded table look like a corpus.
#
# WHEN THE BAND APPLIES. Only where the caller supplies a real article count and that
# count clears BAND_MIN_ARTICLES. A document SHARE is meaningless over six articles,
# and a caller that cannot say how many articles it read gets the width bound and
# nothing else, because guessing the denominator is how the 4,000 ceiling hid for a
# day: `max(counter.values())` looks like an article count and is not one.
BAND_MIN_ARTICLES = 20

#: Above this share of an outlet's own articles, a phrase is that outlet's furniture.
MAX_DOC_SHARE = 0.50

#: Below this many articles, a phrase cannot carry a rate difference.
MIN_ARTICLES_PER_PHRASE = 3

#: A ceiling still, because an unbounded table drifts back toward being a corpus.
#: It applies to what the band already kept, so it no longer decides WHICH KIND of
#: phrase survives, only how much of the middle is stored.
MAX_ROWS_PER_OUTLET = 60000

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


def band(counter: collections.Counter, articles: int | None):
    """The phrases worth storing, commonest first.

    `articles` is how many articles this outlet's counter was built from. Without it,
    or below BAND_MIN_ARTICLES, there is no denominator a share could be taken against
    and everything is kept: the width bound is then the only invariant, which is what
    it has always been for a caller that hands `persist()` a hand-built Counter.
    """
    items = counter.most_common()
    if not articles or articles < BAND_MIN_ARTICLES:
        return items
    ceiling = MAX_DOC_SHARE * articles
    kept = [(p, c) for p, c in items
            if MIN_ARTICLES_PER_PHRASE <= c <= ceiling]
    return kept[:MAX_ROWS_PER_OUTLET]


def persist(conn: sqlite3.Connection, tally: dict[str, collections.Counter],
            now: str | None = None,
            articles: dict[str, int] | None = None) -> int:
    """Merge a run's tally into the table. Returns rows written.

    Refuses any phrase wider than MAX_PHRASE_WORDS. That is the one invariant this
    module exists to hold, so it is enforced at the write rather than upstream where a
    later caller could bypass it.

    `articles` maps source_id to the number of articles that outlet's counter was built
    from. It is what turns a count into a document share, and without it no band is
    applied. See the note on the band above for why it is not inferred.
    """
    conn.executescript(SCHEMA)
    written = 0
    for sid, counter in (tally or {}).items():
        for phrase, count in band(counter, (articles or {}).get(sid)):
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


def record(conn: sqlite3.Connection, rows, now: str | None = None) -> int:
    """The one entry point for the pipeline: tally these articles and merge them.

    Counts the articles per outlet on the way past, so the band has a real
    denominator rather than one inferred from the counts themselves.
    """
    tally = accumulate(rows)
    per_outlet: collections.Counter = collections.Counter()
    for row in rows or []:
        if row.get("source_id"):
            per_outlet[row["source_id"]] += 1
    return persist(conn, tally, now, dict(per_outlet))
