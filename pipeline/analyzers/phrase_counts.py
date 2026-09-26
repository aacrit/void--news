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

CALLED FROM `main.py` step 9e through `record_daily`, BEFORE the step-10 truncation,
which is the only moment the body exists and the last moment it is allowed to. The
daily path writes to its OWN database file (`VOID_PHRASE_DB`), never the pipeline
state, for the reason set out above `record_daily`.
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
-- By phrase, for the retention sweep, which asks how many outlets hold a phrase.
-- (There is deliberately no source_id index: the primary key already leads with it.)
create index if not exists idx_opc_phrase on outlet_phrase_counts(phrase);

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
            articles: dict[str, int] | None = None,
            apply_band: bool = True) -> int:
    """Merge a run's tally into the table. Returns rows written.

    Refuses any phrase wider than MAX_PHRASE_WORDS. That is the one invariant this
    module exists to hold, so it is enforced at the write rather than upstream where a
    later caller could bypass it.

    `articles` maps source_id to the number of articles that outlet's counter was built
    from. It is what turns a count into a document share, and without it no band is
    applied. See the note on the band above for why it is not inferred.

    `apply_band=False` is the daily path: a day's counts are one slice of a running
    total, so a phrase seen once today is not noise yet (it may be seen again
    tomorrow), and `prune` does the bounding over time instead.
    """
    conn.executescript(SCHEMA)
    written = 0
    capped: list[tuple[str, int, int]] = []
    for sid, counter in (tally or {}).items():
        n_for_band = (articles or {}).get(sid) if apply_band else None
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


# ---------------------------------------------------------------------------
# THE DAILY PATH, and why it is not just `record()` called once a day.
#
# `record()` was written for the one-off harvest, which hands it hundreds of articles
# per outlet at once, so the band has a real denominator and applies. A daily run
# hands it a handful per outlet, under BAND_MIN_ARTICLES, so the band never applies
# and EVERY phrase would be kept. And the real volume is not small: 4,816 full bodies
# from 410 direct-feed outlets on 2026-09-25 (state snapshot of run #379), up from
# ~2,600 a day before the 2026-09-23 feed migration.
#
# Measured 2026-09-26 by replaying real news (CC-News, 141,649 articles, real
# domains as outlets) through this module into a real SQLite file:
#
#   one row per (outlet, phrase) as text      ~107 bytes a row; 88% of a day's rows
#                                             are phrases seen once
#   + admission gate                          4,900 bodies a day still wrote ~1.8M
#                                             rows a day: 7.3M rows by day seven
#   + compact storage                         26 bytes a row instead of 107
#   + 3-per-outlet cap                        ~750 bodies, ~200-300k rows a day:
#                                             1.8M rows and 105 MB at day ten, prunes
#                                             firing from day nine
#
# The corpus ran out at sixteen days, so the steady state past that is NOT measured.
# Growth was still close to linear, which is what RETAIN_LATE_DAYS and the ceiling
# are for. The run log prints the table size every day; read it before trusting any
# projection here.
#
# FIVE RULES, each taken from what the derivation can actually use, so none of them
# decides which political phrases exist:
#
#   1. Only a FULL body counts (DAILY_MIN_BODY_WORDS, the scorer's own full-confidence
#      threshold). A headline is not an article, and counting it as one would inflate
#      the per-outlet denominator with documents that could never contain the phrase.
#   2. Only a phrase the derivation can SCORE is stored: `lexicon_derive.phrases()`
#      drops stop unigrams, words under three letters and stop-bracketed n-grams, and
#      `score_outlets` iterates `phrases()`, so anything else is dead weight.
#   3. A phrase must RECUR before it gets a row (the admission gate). CEO decision,
#      2026-09-26. A phrase is counted per outlet only from its GATE_SIGHTINGS-th
#      sighting in any article, corpus-wide, within the last one to two generations
#      of GATE_GEN_DAYS. The first sightings live in two Bloom filters (seen once,
#      seen twice), not in rows, so a phrase that never recurs costs a few bits.
#      THE COST, stated because it is a real bias and not a rounding: the derivation's
#      floor is MIN_ARTICLES (50) per phrase, so the gate drops the first two of at
#      least fifty uses, about 4%, and they fall on whichever outlets used the phrase
#      FIRST. An outlet that coins a phrase loses up to two of its uses of it.
#      A Bloom false positive moves a phrase up a level early, so an error ADMITS a
#      phrase sooner; it can never keep a recurring phrase out.
#   4. A phrase must SPREAD or be dropped. The derivation needs MIN_OUTLETS (20)
#      outlets and MIN_OUTLETS_PER_SIDE (8) on each side. A phrase that has reached
#      fewer than RETAIN_MIN_OUTLETS_EARLY outlets and not been seen for
#      RETAIN_EARLY_DAYS, or fewer than RETAIN_MIN_OUTLETS_LATE and not seen for
#      RETAIN_LATE_DAYS, is a masthead, a place name or noise.
#   5. A CAP PER OUTLET PER DAY (CEO decision, 2026-09-26). At most
#      DAILY_PER_OUTLET_CAP full bodies per outlet per run, chosen by the hash of the
#      article URL, so which ones are kept is fixed by the URL and not by feed order,
#      length or topic. The derivation needs n per OUTLET (25 to place one at SE ~3,
#      per the 2026-09-22 programme), not every article from the busiest feeds, and
#      the cap stops a 30-a-day outlet outweighing a 3-a-day one on its side. Measured
#      on run #379: 3,635 full bodies from 313 rated outlets (median 9 each) become
#      849, and the median outlet still reaches n=25 in about nine days.
#      The pipeline passes rated outlets only: an unrated outlet has no baseline and
#      the derivation's roster excludes it.
#   6. COMPACT STORAGE. Each phrase and each outlet is stored ONCE and the counts are
#      three integers, in a table without rowids. The derivation reads the same
#      `outlet_phrase_counts` / `outlet_phrase_articles` shape through views, so no
#      reader changes.
#
# And one alarm: past DAILY_MAX_ROWS the run records nothing and says so loudly. It
# does NOT prune to fit, because pruning to a size is the storage-policy-decides-
# the-lexicon defect the band replaced.
#
# THIS FILE IS NOT THE STATE DB. The daily path writes to `VOID_PHRASE_DB` only, and
# its schema (views where the harvest path has tables) is deliberately incompatible
# with `persist()`, so the two paths cannot be pointed at one file by accident.
DAILY_MIN_BODY_WORDS = 150
DAILY_PER_OUTLET_CAP = 3
RETAIN_EARLY_DAYS = 7
RETAIN_MIN_OUTLETS_EARLY = 3
RETAIN_LATE_DAYS = 28
RETAIN_MIN_OUTLETS_LATE = 8
# At 26 bytes a row, ~210 MB of counts: the most this file may cost the Actions cache,
# beside a state DB of 433 MB (105 MB gzipped) on 2026-09-25.
DAILY_MAX_ROWS = 8_000_000

GATE_SIGHTINGS = 3
GATE_GEN_DAYS = 7
# Sized from the capped replay: ~750 bodies a day raise level one's fill ~0.8% a
# day at 25M, i.e. ~2.8M first sightings a week against 8M capacity, at 3%.
# Level one sees every first sighting; level two only second ones. Each
# generation costs ~11 MB of bits, two generations ~22 MB.
GATE_L1_CAPACITY = 8_000_000
GATE_L2_CAPACITY = 4_000_000
GATE_FP = 0.03

DAILY_SCHEMA = """
create table if not exists pc_phrase (
    id        integer primary key,
    phrase    text not null unique,
    words     integer not null,
    last_seen text not null
);
create table if not exists pc_outlet (
    id         integer primary key,
    source_id  text not null unique,
    articles   integer not null default 0,
    updated_at text
);
create table if not exists pc_count (
    phrase_id integer not null,
    outlet_id integer not null,
    count     integer not null,
    primary key (phrase_id, outlet_id)
) without rowid;
create view if not exists outlet_phrase_counts as
    select o.source_id, p.phrase, p.words, c.count, p.last_seen as updated_at
      from pc_count c
      join pc_phrase p on p.id = c.phrase_id
      join pc_outlet o on o.id = c.outlet_id;
create view if not exists outlet_phrase_articles as
    select source_id, articles, updated_at from pc_outlet;
create table if not exists phrase_gate (
    name       text not null primary key,   -- cur1, cur2, prev1, prev2
    started_at text not null,
    bits       integer not null,
    hashes     integer not null,
    array      blob not null
);
"""


def _scoreable_phrases(text: str):
    """Exactly the phrases `lexicon_derive.phrases` emits. Imported lazily because
    `lexicon_derive` imports this module."""
    try:
        from analyzers import lexicon_derive as _ld          # inside the pipeline
    except ImportError:
        import importlib.util
        import pathlib
        spec = importlib.util.spec_from_file_location(
            "lexicon_derive", pathlib.Path(__file__).with_name("lexicon_derive.py"))
        _ld = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_ld)
    return _ld.phrases(text)


def _bloom_mod():
    try:
        from editorial import grounding as _g                # inside the pipeline
    except ImportError:
        import importlib.util
        import pathlib
        spec = importlib.util.spec_from_file_location(
            "grounding",
            pathlib.Path(__file__).resolve().parents[1] / "editorial" / "grounding.py")
        _g = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_g)
    return _g


def _ts(iso: str):
    import datetime as _dt
    return _dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))


class Gate:
    """Two-level, two-generation Bloom gate. Holds no phrase text: membership only."""

    def __init__(self, conn: sqlite3.Connection, now_iso: str):
        import datetime as _dt
        self.conn = conn
        self.g = _bloom_mod()
        rows = {r[0]: r for r in conn.execute(
            "select name, started_at, bits, hashes, array from phrase_gate")}
        cur = rows.get("cur1")
        rotate = cur is None or (
            _ts(now_iso) - _ts(cur[1]) >= _dt.timedelta(days=GATE_GEN_DAYS))
        self.rotated = rotate and cur is not None
        if rotate:
            self.prev = [self._load(rows.get("cur1")), self._load(rows.get("cur2"))]
            self.prev_started = cur[1] if cur else now_iso
            self.cur = [self._new(GATE_L1_CAPACITY), self._new(GATE_L2_CAPACITY)]
            self.started = now_iso
        else:
            self.prev = [self._load(rows.get("prev1")), self._load(rows.get("prev2"))]
            self.prev_started = rows["prev1"][1] if rows.get("prev1") else cur[1]
            self.cur = [self._load(cur), self._load(rows.get("cur2"))]
            self.started = cur[1]

    def _new(self, capacity):
        bits, hashes = self.g._bloom_params(capacity, GATE_FP)
        return self.g.Bloom(bits, hashes)

    def _load(self, row):
        if row is None:
            return None
        return self.g.Bloom(int(row[2]), int(row[3]), bytearray(row[4]))

    def _seen(self, level: int, phrase: str) -> bool:
        return any(b is not None and phrase in b
                   for b in (self.cur[level], self.prev[level]))

    def sight(self, phrase: str) -> bool:
        """Record one sighting. True when this sighting is admitted."""
        if self._seen(1, phrase):
            return True                         # third (or later) sighting
        if self._seen(0, phrase):
            self.cur[1].add(phrase)             # second
            return GATE_SIGHTINGS <= 2
        self.cur[0].add(phrase)                 # first
        return GATE_SIGHTINGS <= 1

    def fill(self) -> float:
        """Share of level-one bits set in the current generation. Past ~0.5 the
        false-positive rate is climbing well above GATE_FP: resize."""
        a = self.cur[0].array
        return sum(bin(x).count("1") for x in a) / (len(a) * 8)

    def save(self) -> None:
        items = [("cur1", self.started, self.cur[0]), ("cur2", self.started, self.cur[1]),
                 ("prev1", self.prev_started, self.prev[0]),
                 ("prev2", self.prev_started, self.prev[1])]
        for name, started, b in items:
            if b is None:
                self.conn.execute("delete from phrase_gate where name=?", (name,))
                continue
            self.conn.execute(
                """insert into phrase_gate(name, started_at, bits, hashes, array)
                   values(?,?,?,?,?) on conflict(name) do update set
                   started_at=excluded.started_at, bits=excluded.bits,
                   hashes=excluded.hashes, array=excluded.array""",
                (name, started, b.bits, b.hashes, bytes(b.array)))


def prune(conn: sqlite3.Connection, now_iso: str) -> int:
    """Drop phrases that have not spread. Returns count rows deleted.

    `last_seen` moves every time any outlet uses the phrase, so a phrase still in
    use is never old.
    """
    import datetime as _dt
    now = _ts(now_iso)
    deleted = 0
    for days, min_outlets in ((RETAIN_EARLY_DAYS, RETAIN_MIN_OUTLETS_EARLY),
                              (RETAIN_LATE_DAYS, RETAIN_MIN_OUTLETS_LATE)):
        cutoff = (now - _dt.timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn.execute("create temp table if not exists _pc_drop(id integer primary key)")
        conn.execute("delete from _pc_drop")
        conn.execute(
            """insert into _pc_drop(id)
               select p.id from pc_phrase p
                where p.last_seen < ?
                  and (select count(*) from pc_count c where c.phrase_id = p.id) < ?""",
            (cutoff, min_outlets))
        cur = conn.execute(
            "delete from pc_count where phrase_id in (select id from _pc_drop)")
        deleted += cur.rowcount or 0
        conn.execute("delete from pc_phrase where id in (select id from _pc_drop)")
        conn.execute("delete from _pc_drop")
    return deleted


def _ids(conn, table: str, key: str, values) -> dict:
    """{value: id} for `values`, inserting any that are new. One pass, no N+1."""
    conn.execute(f"create temp table if not exists _pc_keys(k text primary key)")
    conn.execute("delete from _pc_keys")
    conn.executemany("insert or ignore into _pc_keys(k) values(?)", ((v,) for v in values))
    out = {k: i for k, i in conn.execute(
        f"select t.{key}, t.id from {table} t join _pc_keys k on k.k = t.{key}")}
    conn.execute("delete from _pc_keys")
    return out


def _sample_key(row) -> str:
    import hashlib
    key = str(row.get("url") or row.get("full_text") or "")
    return hashlib.sha1(key.encode("utf-8")).hexdigest()


def record_daily(conn: sqlite3.Connection, rows, now: str) -> dict:
    """The pipeline's entry point. `rows` carry source_id, url and full_text (title
    and summary are ignored here: the body is the point, and a headline counted
    beside it would weight the lead twice).

    Returns a report dict; never raises on an empty day.
    """
    conn.executescript(DAILY_SCHEMA)
    total = conn.execute("select count(*) from pc_count").fetchone()[0]
    report = {"rows_before": total, "rows_after": total, "articles": 0, "outlets": 0,
              "written": 0, "pruned": 0, "skipped_short": 0, "capped": 0,
              "halted": False, "gated": 0, "gate_rotated": False, "gate_fill": 0.0}
    if total > DAILY_MAX_ROWS:
        report["halted"] = True
        print(f"  PHRASE COUNTS HALTED: {total:,} rows exceeds DAILY_MAX_ROWS "
              f"({DAILY_MAX_ROWS:,}). Nothing recorded this run. The retention rules "
              f"are not holding; measure before raising the ceiling.")
        return report

    full: dict[str, list] = collections.defaultdict(list)
    for row in rows or []:
        sid = row.get("source_id")
        if not sid:
            continue
        if len(str(row.get("full_text") or "").split()) < DAILY_MIN_BODY_WORDS:
            report["skipped_short"] += 1
            continue
        full[sid].append(row)
    sample = []
    for sid, rs in full.items():
        rs.sort(key=_sample_key)
        sample.extend(rs[:DAILY_PER_OUTLET_CAP])
        report["capped"] += max(0, len(rs) - DAILY_PER_OUTLET_CAP)

    docs: list[tuple[str, set]] = []
    per_outlet: collections.Counter = collections.Counter()
    for row in sample:
        sid = row["source_id"]
        body = str(row.get("full_text") or "")
        # The width bound, enforced here as well as by the tokeniser, because it is
        # the one invariant this module exists to hold.
        docs.append((sid, {p for p in _scoreable_phrases(body)
                           if 0 < len(p.split()) <= MAX_PHRASE_WORDS}))
        per_outlet[sid] += 1
    report["articles"] = sum(per_outlet.values())
    report["outlets"] = len(per_outlet)

    # A phrase that already holds a row is admitted whatever the filters say, which
    # matters after a cold gate.
    today = {p for _, ps in docs for p in ps}
    known = _ids(conn, "pc_phrase", "phrase", today) if today else {}

    gate = Gate(conn, now)
    tally: dict[tuple[str, str], int] = collections.Counter()
    admitted = set(known)
    for sid, ps in docs:
        for p in sorted(ps):                    # deterministic sighting order
            if p in admitted or gate.sight(p):
                admitted.add(p)
                tally[(sid, p)] += 1
            else:
                report["gated"] += 1
    gate.save()
    report["gate_rotated"] = gate.rotated
    report["gate_fill"] = round(gate.fill(), 3)

    if tally:
        seen = {p for _, p in tally}
        conn.executemany(
            """insert into pc_phrase(phrase, words, last_seen) values(?,?,?)
               on conflict(phrase) do update set last_seen = excluded.last_seen""",
            ((p, len(p.split()), now) for p in seen))
        conn.executemany(
            "insert or ignore into pc_outlet(source_id, updated_at) values(?,?)",
            ((s, now) for s in per_outlet))
        pid = _ids(conn, "pc_phrase", "phrase", seen)
        oid = _ids(conn, "pc_outlet", "source_id", per_outlet)
        conn.executemany(
            """insert into pc_count(phrase_id, outlet_id, count) values(?,?,?)
               on conflict(phrase_id, outlet_id) do update set count = count + excluded.count""",
            ((pid[p], oid[s], n) for (s, p), n in tally.items()))
        report["written"] = len(tally)
    # The denominator: every full body read, admitted phrases or not.
    conn.executemany(
        """insert into pc_outlet(source_id, articles, updated_at) values(?,?,?)
           on conflict(source_id) do update set articles = articles + excluded.articles,
           updated_at = excluded.updated_at""",
        ((s, n, now) for s, n in per_outlet.items()))
    report["pruned"] = prune(conn, now)
    conn.commit()
    report["rows_after"] = conn.execute("select count(*) from pc_count").fetchone()[0]
    return report
