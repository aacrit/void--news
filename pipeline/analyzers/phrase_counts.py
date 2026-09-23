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
#:
#: BOTH OF THESE WERE GUESSED FIRST AND THEN MEASURED, and the guess was wrong in the
#: direction that matters. Taken against the 175 rows in the pre-band table that match
#: the hand-written political phrases (98 outlets, ~81 bodies each): a floor of 3 cut
#: 17% of them, 4 cut 36%, 5 cut 44%, while a floor of 2 cuts 5% and still removes the
#: count-1 noise that is 15% of all rows. A ceiling of 0.50 cut a further 6%.
#:
#: So the band is set where it bounds STORAGE and nothing else. The signal filter is
#: `lexicon_derive.MAX_DOC_FREQ` (0.25, corpus-wide), which is the right place for it:
#: a storage rule should not be quietly deciding which political phrases exist. That
#: is exactly what the 4,000-row ceiling was doing.
MAX_DOC_SHARE = 0.65

#: Below this many articles, a phrase cannot carry a rate difference. Set to 2 rather
#: than 3 on the measurement above, and deliberately not to 1: a phrase seen once at an
#: outlet is the long tail that made an unbounded table look like a corpus.
MIN_ARTICLES_PER_PHRASE = 2

#: A ceiling still, because an unbounded table drifts back toward being a corpus.
#:
#: IT IS THE 4,000-ROW DEFECT IN WAITING, and at 60,000 it was close enough to the
#: real figure to be a live risk: a single outlet at 239 bodies of ~929 words plausibly
#: carries tens of thousands of phrases at document frequency 2 or more. When a cap
#: binds on a list sorted by descending count it keeps the entries nearest the ceiling,
#: which are the most furniture-like, and drops the rare middle. That is exactly how
#: the top-4,000 ceiling emptied this table of political language, and it would have
#: done it again silently, on the largest outlets only, manufacturing an outlet-level
#: signal out of a storage policy.
#:
#: So: raised, cut from the COMMON end rather than the rare one when it does bind, and
#: never silent. `persist` reports every outlet that hits it. The IP argument does not
#: depend on the row count (the table holds counts and no article id at any size), so
#: there is no reason to keep this tight.
MAX_ROWS_PER_OUTLET = 200000

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

-- HOW MANY ARTICLES EACH OUTLET'S COUNTS WERE BUILT FROM. It is a COUNT, not an
-- identifier, so the invariant above is untouched: nothing here can be re-associated
-- with an article, and this table on its own says only "we read 81 pieces from this
-- outlet".
--
-- It exists because the band broke the denominator downstream.
-- `lexicon_derive.derive_from_counts` used to take `max(counter.values())` as a proxy
-- for the article count, which was roughly right while the commonest phrase was
-- stored: "the" appears in nearly every article. The band DELETES every phrase above
-- MAX_DOC_SHARE of an outlet's articles, so that maximum is now bounded by
-- MAX_DOC_SHARE itself and the proxy understates the truth by about 1.5x. Every rate
-- computed from it is inflated by that factor, and MAX_DOC_FREQ would then cut phrases
-- really sitting at 12-16%, which is precisely the middle band this whole change
-- exists to preserve.
create table if not exists outlet_phrase_articles (
    source_id  text not null primary key,
    articles   integer not null default 0,
    updated_at text
);
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
    if len(kept) > MAX_ROWS_PER_OUTLET:
        # Drop from the COMMON end. `kept` is descending, so slicing off the head
        # sheds what is nearest the furniture ceiling and keeps the rare middle,
        # which is the only part the derivation is looking for.
        kept = kept[len(kept) - MAX_ROWS_PER_OUTLET:]
    return kept


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
    capped: list[tuple[str, int, int]] = []
    for sid, counter in (tally or {}).items():
        n_for_band = (articles or {}).get(sid)
        rows = band(counter, n_for_band)
        # A cap that binds invisibly is the whole defect this module was rewritten
        # for, so it is counted and reported rather than trusted not to happen.
        if n_for_band and n_for_band >= BAND_MIN_ARTICLES:
            in_band = sum(1 for _, c in counter.most_common()
                          if MIN_ARTICLES_PER_PHRASE <= c <= MAX_DOC_SHARE * n_for_band)
            if in_band > len(rows):
                capped.append((sid, in_band, in_band - len(rows)))
        for phrase, count in rows:
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
        # The denominator, recorded beside the counts and accumulated the same way,
        # so a second run over more articles keeps the share meaningful.
        n_articles = (articles or {}).get(sid)
        if n_articles:
            conn.execute(
                """insert into outlet_phrase_articles(source_id, articles, updated_at)
                   values(?,?,?)
                   on conflict(source_id) do update set
                     articles = articles + excluded.articles,
                     updated_at = excluded.updated_at""",
                (sid, int(n_articles), now))
    if capped:
        worst = max(c for _, _, c in capped)
        print(f"  MAX_ROWS_PER_OUTLET ({MAX_ROWS_PER_OUTLET:,}) BOUND on "
              f"{len(capped)} outlet(s), discarding up to {worst:,} in-band phrases "
              f"from the commonest end. Raise it: a storage cap deciding which "
              f"phrases exist is the defect this band replaced.")
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
