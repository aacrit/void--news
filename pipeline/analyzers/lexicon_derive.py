#!/usr/bin/env python3
"""Derive lean lexicon candidates from our own labelled corpus, and prove it.

WHY. Measured 2026-09-22 (`docs/audits/LEAN-SIGNAL-2026-09-22.md`): the hand-written
lexicon of 318 phrases fires on **26.4%** of the articles the scorer can fully read, so
the median outlet has 8 signal-bearing articles and only 20 outlets reach n>=25. The
signal that does fire is real (Spearman rho +0.479 against the labels, at the published
ceiling), so the constraint is coverage, not precision. More articles move rho by
roughly nothing; more phrases move every outlet at once.

The method is Gentzkow and Shapiro's in shape: take text from speakers of known
ideology, and rank phrases by how unevenly they are used across the sides. Their
speakers were members of Congress; ours are outlets the roster has placed.

THE CIRCULARITY, AND THE ONLY DEFENCE AGAINST IT. Deriving phrases from outlet labels
and then reporting how well those phrases predict outlet labels is not a measurement,
it is a mirror. It would produce a high number that means nothing, and it is the same
mistake as the `source_topic_lean` loop cut on 2026-09-22, where the score fed the table
and the table fed the score.

So the split is by OUTLET, never by article. Phrases are derived from the fit outlets
only, and every number that claims improvement is computed on HOLDOUT outlets whose
text never entered the derivation. Splitting by article would leak: two articles from
the same outlet share its vocabulary, so a phrase fitted on one would "predict" the
other and the score would measure memorisation. `tests/test_lexicon_derive.py` asserts
the two outlet sets are disjoint rather than trusting that they are.

WHAT THE CORPUS IS, and its one real limitation. `articles.full_text` is truncated to
300 characters after analysis (`main.py` step 10, the top control in
`docs/IP-COMPLIANCE.md`), so 98.9% of the history is a lead rather than an article.
What survives is titles, summaries and those leads: 5.3M words, every row labelled.
That is enough to derive from, and it SKEWS TOWARD HEADLINE LANGUAGE, which is denser
in framing than body text. The output says so. `phrase_counts.py` accumulates counts
from full bodies going forward, before truncation, so the next derivation does not
carry this skew.

    python3 pipeline/analyzers/lexicon_derive.py <pipeline_state.db>
    python3 pipeline/analyzers/lexicon_derive.py <db> --out data/lexicon/candidates.json
"""
from __future__ import annotations

import collections
import json
import hashlib
import math
import pathlib
import re
import sqlite3
import sys

# The seven rungs, as `political_lean.BASELINE_MAP` defines them. Imported there
# rather than restated; duplicated here only as a fallback so this script can run
# without the analyzer's spaCy import chain.
BASELINE = {"far-left": 10, "left": 20, "center-left": 35, "center": 50,
            "center-right": 65, "right": 80, "far-right": 90}

# English-speaking markets, per the CEO's scope decision. Nearly all the volume, and
# no translation needed. Non-English markets need their own lexicons and are a
# separate, larger piece of linguistic work.
MARKETS = ("US", "GB", "AU", "CA", "IN", "IE", "ZA", "PK")

# A phrase must be used by several DIFFERENT outlets before it means anything about a
# side. MIN_OUTLETS = 5 was not remotely enough: the first run's top "left" phrases
# were `herald`, `sacramento`, `scotland`, `portland`, `beast`, `toronto`, `baltimore`,
# `monitor`, `telegram`, `photograph` and `this article`. Those are MASTHEADS, CITIES
# and BOILERPLATE. They separate the sides perfectly in the fit set and carry no
# ideology at all, because a paper based in Portland is the only paper that writes
# "Portland" and it happens to be labelled left.
#
# That is leakage, not signal, and it generalises to holdout outlets only where they
# share a city or a template with a fit outlet. The chi-squared did its job; the floors
# let furniture through.
MIN_OUTLETS = 20
MIN_ARTICLES = 50

# The filter that actually separates ideology from geography: a real political phrase
# is used MORE by one side, but BOTH sides use it. "illegal alien" appears in left
# coverage too, criticising it. "sacramento" appears only in Sacramento's paper. So a
# candidate must be used by at least this many distinct outlets ON EACH SIDE, which no
# masthead or city name can satisfy.
MIN_OUTLETS_PER_SIDE = 8

# Phrases of one to three words, as Gentzkow and Shapiro used.
NGRAM_SIZES = (1, 2, 3)

# Roughly a quarter of outlets held out. Enough to measure on, few enough to keep the
# derivation's own sample large.
HOLDOUT_SHARE = 0.25

# A phrase this common carries no side information (it is "the" or "said"), and one
# this rare is noise however lopsided it looks.
MAX_DOC_FREQ = 0.25

_WORD = re.compile(r"[a-z][a-z'-]+")


def _rank(d: dict) -> tuple:
    """The order candidates are reported in. A TOTAL order, deliberately.

    `sort(key=lambda d: -d["chi2"])` looked complete and was not. Chi-squared
    ties constantly, because a planted phrase, its unigrams, and every n-gram
    that straddles it all carry identical counts: on the gate's own fixture
    NINE phrases tie at 87.820. Python's sort is stable, so the winner was
    whatever insertion order the dicts happened to have, and that order comes
    from iterating SETS of strings, which is PYTHONHASHSEED-dependent. So
    `derive()` returned a different top phrase in every process.

    Measured on that fixture: seed 0 gave `wealth`, seed 1 `border`, seed 2
    `wealth tax`, seed 5 `about meeting wealth`. The last one is filler
    straddling the plant, which is what finally failed the gate in CI after
    passing locally four times. A derivation nobody can reproduce is one
    nobody can act on, and the ranked lists this function produced were being
    read and quoted.

    The tie-break is shortest-then-alphabetical, and the first half of that is
    a real editorial preference rather than an arbitrary stabiliser: among
    phrases of identical discriminating power, the shortest is the general
    finding. A trigram that ties with its own unigram is that unigram plus
    context contributing nothing. Alphabetical last, purely so the order is
    total and no tie can fall through to hash order again.
    """
    return (-d["chi2"], len(d["phrase"].split()), d["phrase"])


def reachable_known(known: set[str]) -> tuple[set[str], set[str]]:
    """Split the hand-written phrases into the ones a harvest could ever store
    and the ones it could not.

    EVERY REPORT SO FAR HAS SAID "zero of the 318", AND 318 IS NOT REACHABLE.
    `phrase_counts.MAX_PHRASE_WORDS` is 3, so nine of them are four or five words
    (`right to bear arms`, `shall not be infringed`, `tax cuts for the wealthy`) and
    can never be stored, by the same invariant that keeps a stored row a phrase and
    not a sentence. Two more carry digits (`project 2025`, `top 1%`) which the
    tokeniser strips. The achievable ceiling is 307.

    A failure reported against the wrong denominator is partly just arithmetic, and
    this is a gate that has already been read three times as evidence about the
    method. It divides by what the method could actually reach.
    """
    # Loaded by path, not by package: this module is run as a script
    # (`python3 pipeline/analyzers/lexicon_derive.py`), where `analyzers` is not an
    # importable package, and a gate that raises here is a gate that does not run.
    try:
        from analyzers import phrase_counts as _pc          # inside the pipeline
    except ImportError:
        import importlib.util
        _spec = importlib.util.spec_from_file_location(
            "phrase_counts", pathlib.Path(__file__).with_name("phrase_counts.py"))
        _pc = importlib.util.module_from_spec(_spec)
        _spec.loader.exec_module(_pc)
    reach, out = set(), set()
    for p in known:
        if len(p.split()) > _pc.MAX_PHRASE_WORDS:
            out.add(p)
        elif " ".join(_pc._WORD.findall(p)) != p:
            out.add(p)      # digits or punctuation the tokeniser will not emit
        else:
            reach.add(p)
    return reach, out

# Function words, which dominate any n-gram count and say nothing about a side. Kept
# short deliberately: a stopword list that grows to include political words would
# quietly decide the answer.
STOP = frozenset("""
a an the and or but if then than that this these those of in on at to for from by with
about into over after before under above is are was were be been being has have had do
does did will would can could should may might must not no nor so such as it its it's
he she they them his her their we us our you your i me my who whom which what when
where why how all any both each few more most other some only own same too very s t
just now also said says say told tells according reported reports report new news
year years day days time times week month first last one two three
""".split())


def hash_split(slug: str) -> bool:
    """True when this outlet is HELD OUT. Deterministic, so a rerun is comparable.

    Hashed rather than sampled so the split does not move between runs and cannot be
    quietly reshuffled until the numbers improve.
    """
    digest = hashlib.sha256(slug.encode("utf-8")).digest()
    return (int.from_bytes(digest[:4], "big") % 1000) < int(HOLDOUT_SHARE * 1000)


def phrases(text: str):
    """Lowercased 1-, 2- and 3-grams, function words dropped from the unigrams.

    Bigrams and trigrams keep their stopwords, because "the wall" and "wall" mean
    different things and the phrase is the point.
    """
    words = _WORD.findall((text or "").lower())
    for n in NGRAM_SIZES:
        if n == 1:
            for w in words:
                if w not in STOP and len(w) > 2:
                    yield w
            continue
        for i in range(len(words) - n + 1):
            gram = words[i:i + n]
            if gram[0] in STOP and gram[-1] in STOP:
                continue          # "of the", "in a": furniture either way
            yield " ".join(gram)


def load(db_path: str):
    """One row per article: outlet, side, and the text that survived truncation."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    marks = ",".join("?" * len(MARKETS))
    q = f"""select s.slug, s.name, s.country, s.political_lean_baseline lab,
                   a.title, a.summary, a.full_text
            from articles a
            join sources s on s.id = a.source_id
            where s.country in ({marks})"""
    out = []
    for r in conn.execute(q, MARKETS):
        lab = (r["lab"] or "").lower()
        if lab not in BASELINE:
            continue
        text = " ".join(x for x in (r["title"], r["summary"], r["full_text"]) if x)
        if not text.strip():
            continue
        out.append({"slug": r["slug"], "name": r["name"], "lab": lab,
                    "base": BASELINE[lab], "text": text})
    return out


def derive(rows: list[dict]) -> list[dict]:
    """Chi-squared association of each phrase with the left or the right.

    Centre outlets are excluded from the FIT. A phrase's side is defined by its use
    among outlets that have a side, and a centre outlet contributes no such evidence;
    including them would drag every phrase's expectation toward whichever side happens
    to be better represented at 50.
    """
    left_docs = right_docs = 0
    counts = collections.defaultdict(lambda: [0, 0])      # phrase -> [left, right]
    outlets = collections.defaultdict(lambda: (set(), set()))   # phrase -> per side
    # Every word of every outlet's own name, so a masthead cannot become a political
    # phrase. `herald`, `beast`, `monitor` and `telegram` all reached the first run's
    # top ten this way.
    banned = set()
    for r in rows:
        for w in _WORD.findall((r["name"] or "").lower()):
            banned.add(w)
    for r in rows:
        if r["base"] == 50:
            continue
        side = 0 if r["base"] < 50 else 1
        if side == 0:
            left_docs += 1
        else:
            right_docs += 1
        for p in set(phrases(r["text"])):                 # presence, not frequency
            if p in banned:
                continue
            counts[p][side] += 1
            outlets[p][side].add(r["slug"])
    total = left_docs + right_docs
    if not total:
        return []

    out = []
    for phrase, (l, r) in counts.items():
        n = l + r
        left_outlets, right_outlets = outlets[phrase]
        if n < MIN_ARTICLES or len(left_outlets) + len(right_outlets) < MIN_OUTLETS:
            continue
        # Used on BOTH sides, by enough outlets each. This is what a city name or a
        # template line cannot do, and what a contested political phrase always does.
        if (len(left_outlets) < MIN_OUTLETS_PER_SIDE
                or len(right_outlets) < MIN_OUTLETS_PER_SIDE):
            continue
        if n / total > MAX_DOC_FREQ:
            continue
        # 2x2: (phrase present/absent) x (left/right), chi-squared with Yates.
        el = n * left_docs / total
        er = n * right_docs / total
        if el < 1 or er < 1:
            continue
        chi = ((abs(l - el) - 0.5) ** 2) / el + ((abs(r - er) - 0.5) ** 2) / er
        # Which side, by rate rather than raw count, since the sides differ in size.
        rate_l = l / left_docs
        rate_r = r / right_docs
        side = "left" if rate_l > rate_r else "right"
        out.append({"phrase": phrase, "side": side, "chi2": round(chi, 2),
                    "left": l, "right": r,
                    "outlets": len(left_outlets) + len(right_outlets),
                    "left_outlets": len(left_outlets),
                    "right_outlets": len(right_outlets),
                    "rate_left": round(rate_l * 100, 3),
                    "rate_right": round(rate_r * 100, 3)})
    out.sort(key=_rank)
    return out


def score_outlets(rows: list[dict], lexicon: dict[str, int]) -> dict[str, float]:
    """Mean per-article lean score for each outlet, from a phrase list alone.

    Deliberately the same shape as `political_lean._keyword_score`: a 0-100 where 50 is
    "nothing fired", moved by the balance of left and right hits. It never sees the
    outlet, which is what makes it usable as a holdout measurement.
    """
    per = collections.defaultdict(list)
    for r in rows:
        left = right = 0
        for p in phrases(r["text"]):
            w = lexicon.get(p)
            if w:
                if w < 0:
                    left -= w
                else:
                    right += w
        if left or right:
            per[r["slug"]].append(50.0 + 50.0 * (right - left) / (right + left))
    return {k: sum(v) / len(v) for k, v in per.items() if v}


def spearman(xs, ys) -> float:
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        out = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                out[order[k]] = avg
            i = j + 1
        return out
    rx, ry = ranks(xs), ranks(ys)
    mx = sum(rx) / len(rx)
    my = sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    rows = load(sys.argv[1])
    print(f"corpus: {len(rows):,} articles, "
          f"{len({r['slug'] for r in rows})} placed outlets in {'/'.join(MARKETS)}")

    fit = [r for r in rows if not hash_split(r["slug"])]
    hold = [r for r in rows if hash_split(r["slug"])]
    fit_outlets = {r["slug"] for r in fit}
    hold_outlets = {r["slug"] for r in hold}
    assert not (fit_outlets & hold_outlets), "the split leaked"
    print(f"  fit: {len(fit):,} articles / {len(fit_outlets)} outlets")
    print(f"  holdout: {len(hold):,} articles / {len(hold_outlets)} outlets "
          f"(their text never enters the derivation)")

    cands = derive(fit)
    print(f"\ncandidates passing the floors "
          f"(>={MIN_ARTICLES} articles, >={MIN_OUTLETS} outlets, "
          f"<{MAX_DOC_FREQ:.0%} of documents): {len(cands):,}")
    for top in (100, 300, 1000):
        sub = cands[:top]
        l = sum(1 for d in sub if d["side"] == "left")
        print(f"  top {top:4d} by chi-squared: {l} left, {len(sub) - l} right")

    # Does it generalise? Score the HOLDOUT outlets with the derived list and compare
    # against the labels it has never seen.
    print("\nheld-out validation (outlets never used in the derivation)")
    labels = {r["slug"]: r["base"] for r in hold}

    # THE CONTROL, printed first and always. A derived rho on its own is unreadable:
    # the +0.479 this project measured elsewhere came from FULL article text at
    # analysis time with the framing and entity signals included, and this corpus is
    # truncated leads scored by keywords alone. Comparing across those would flatter or
    # damn the derivation for reasons that have nothing to do with it. So the
    # hand-written lexicon is scored here on the same corpus, the same holdout outlets
    # and the same function, and that is the only number the derived list is measured
    # against.
    try:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
        from analyzers.political_lean import LEFT_KEYWORDS, RIGHT_KEYWORDS
        hand = {p: -w for p, w in LEFT_KEYWORDS.items()}
        hand.update(dict(RIGHT_KEYWORDS))
        got = score_outlets(hold, hand)
        common = [s for s in got if s in labels]
        if len(common) >= 5:
            rho = spearman([labels[s] for s in common], [got[s] for s in common])
            print(f"  CONTROL, the hand-written lexicon on this same corpus: "
                  f"rho={rho:+.3f} on {len(common)} outlets, "
                  f"{len(got) / max(len(labels), 1):.0%} of them scored")
    except Exception as exc:                       # spaCy chain unavailable
        print(f"  CONTROL unavailable ({type(exc).__name__}): a derived rho below "
              f"has nothing to be compared against, so do not read it alone")

    for top in (100, 300, 1000, 3000):
        lex = {d["phrase"]: (-1 if d["side"] == "left" else 1) for d in cands[:top]}
        got = score_outlets(hold, lex)
        common = [s for s in got if s in labels]
        if len(common) < 5:
            continue
        rho = spearman([labels[s] for s in common], [got[s] for s in common])
        fired = len(got) / max(len(hold_outlets), 1)
        print(f"  top {top:4d}: rho={rho:+.3f} on {len(common)} holdout outlets, "
              f"{fired:.0%} of them scored")

    # THE TEST THAT DECIDES WHETHER ANY OF THIS IS POLITICAL LANGUAGE.
    # If the derivation were finding ideology it would rediscover some of the 318
    # phrases a human wrote for exactly this purpose. Run 2026-09-22 rediscovered
    # ZERO, at every depth and across all 1,789 candidates, while its top entries were
    # `getty images`, `continue`, `follow`, `photo`, `this article` and `sep`. Those
    # are CMS boilerplate: outlets on a side often share a publishing platform, so the
    # ranking separates the sides by fingerprinting their templates. A rho earned that
    # way generalises to holdout outlets sharing a CMS and means nothing about
    # politics, which is why it is printed here beside every rho above.
    try:
        from analyzers.political_lean import LEFT_KEYWORDS as _L, RIGHT_KEYWORDS as _R
        known = {p.lower() for p in _L} | {p.lower() for p in _R}
        reachable, unreachable = reachable_known(known)
        allp = {d["phrase"] for d in cands}
        hit = allp & reachable
        print(f"\nsanity: rediscovers {len(hit)} of the {len(reachable)} REACHABLE "
              f"hand-written political phrases"
              + (f" {sorted(hit)[:6]}" if hit else ""))
        print(f"  ({len(unreachable)} of the {len(known)} are unreachable by "
              f"construction and are not counted against the derivation: "
              f"{sorted(unreachable)[:4]} ...)")
        if not hit:
            print("  ZERO. The list is not political language. Do not promote any of "
                  "it into the lexicon: inspect the top entries and you will find "
                  "page furniture, not argument.")
    except Exception:
        pass

    out_path = None
    if "--out" in sys.argv:
        out_path = pathlib.Path(sys.argv[sys.argv.index("--out") + 1])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({
            "_why": ("Candidates derived from the fit outlets only. Nothing here is "
                     "in the live lexicon: these are for review, because the live "
                     "lists carry hand-set weights and a recorded removal, and that "
                     "curation is worth keeping."),
            "_corpus": ("titles, summaries and 300-char leads, because full_text is "
                        "truncated after analysis by the IP control. SKEWS TOWARD "
                        "HEADLINE LANGUAGE, which is denser in framing than body "
                        "text; phrase_counts.py removes that skew going forward."),
            "markets": list(MARKETS),
            "fit_outlets": sorted(fit_outlets),
            "holdout_outlets": sorted(hold_outlets),
            "candidates": cands[:2000],
        }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nwrote {out_path} ({min(len(cands), 2000)} candidates)")
    return 0


def main_counts(db_path: str, roster_db: str | None = None) -> int:
    """Run the derivation over harvested COUNTS and report the gate.

    `derive_from_counts` had no caller anywhere in the repo: the rediscovery check,
    `reachable_known` and the candidate writer all lived in `main()`, which reads the
    truncated-text corpus instead. So the counts path could be run only by hand, and
    the one number that decides whether any of this is political language was not
    printed by it.

        python3 pipeline/analyzers/lexicon_derive.py --counts <state.db>

    The daily pipeline writes counts to their own file (`phrase_counts.db`), which
    has no `sources` table, so the roster is read from the state DB:

        python3 pipeline/analyzers/lexicon_derive.py --counts phrase_counts.db \
            --roster pipeline_state.db
    """
    conn = sqlite3.connect(db_path)
    roster = {}
    rconn = sqlite3.connect(roster_db) if roster_db else conn
    for sid, name, lean in rconn.execute(
            "select id, name, political_lean_baseline from sources"):
        if lean in BASELINE:
            roster[sid] = {"base": BASELINE[lean], "name": name}
    n_rows = conn.execute("select count(*) from outlet_phrase_counts").fetchone()[0]
    n_out = conn.execute(
        "select count(distinct source_id) from outlet_phrase_counts").fetchone()[0]
    print(f"counts: {n_rows:,} rows over {n_out} outlets; "
          f"{len(roster)} roster outlets carry a baseline")

    cands = derive_from_counts(conn, roster)
    print(f"\ncandidates passing the floors: {len(cands):,}")
    for side in ("left", "right"):
        top = [d["phrase"] for d in cands if d["side"] == side][:14]
        print(f"  top {side}: {top}")

    known = _hand_written()
    if not known:
        # Refused, not skipped. This number is the whole point of the run.
        print("\nABORT: could not read LEFT_KEYWORDS/RIGHT_KEYWORDS out of "
              "political_lean.py, so the gate cannot be applied. Reporting "
              "candidates without it would be reporting nothing.")
        return 2
    reach, unreach = reachable_known(known)
    hit = {d["phrase"] for d in cands} & reach
    print(f"\nGATE: rediscovers {len(hit)} of the {len(reach)} REACHABLE "
          f"hand-written political phrases ({len(unreach)} of {len(known)} cannot be "
          f"stored at all and are not counted)")
    if hit:
        rank = {d["phrase"]: i for i, d in enumerate(cands, 1)}
        print(f"  {sorted(hit)[:25]}")
        print(f"  best rank among them: {min(rank[p] for p in hit)} of {len(cands)}")
    else:
        print("  ZERO. On a corpus that now contains the words, this is the first "
              "result that is evidence about the METHOD rather than the storage.")

    # The floors, printed, because they are the likeliest binding constraint now:
    # MIN_OUTLETS_PER_SIDE=8 means a phrase needs 16 distinct outlets, and on the
    # truncated table exactly one known phrase ever reached that.
    import collections as _c
    spread = _c.Counter(min(d.get("left_outlets", 0), d.get("right_outlets", 0))
                        for d in cands if d["phrase"] in reach)
    if spread:
        print(f"  reachable-known candidates by thinner-side outlet count: "
              f"{dict(sorted(spread.items()))}")
    return 0


def _hand_written() -> set:
    """The hand-written lexicon, read from source rather than imported.

    `political_lean` pulls in the Supabase switch and the spaCy chain, either of which
    can fail for reasons that have nothing to do with this gate, and a gate that
    silently does not apply is the same defect as one that passes vacuously. The
    tuples are annotated DICT literals, so the phrases are the dict's keys.
    """
    import ast
    src = (pathlib.Path(__file__).with_name("political_lean.py")
           .read_text(encoding="utf-8"))
    out: set = set()
    for node in ast.parse(src).body:
        if isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        else:
            continue
        if not (isinstance(target, ast.Name)
                and target.id in ("LEFT_KEYWORDS", "RIGHT_KEYWORDS")):
            continue
        items = value.keys if isinstance(value, ast.Dict) else getattr(value, "elts", [])
        for k in items:
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                out.add(k.value.lower())
    return out




# ---------------------------------------------------------------------------
# Deriving from harvested COUNTS instead of stored text
# ---------------------------------------------------------------------------
# `scripts/roster/harvest_phrase_counts.py` re-fetched 8,697 article bodies for
# URLs already in the corpus and kept only per-outlet phrase counts: 10.5M words,
# against 5.3M of truncated leads. That is the corpus the first derivation needed
# and did not have, and it exists without any article text being stored.
#
# A count here is "articles from this outlet containing this phrase", because the
# harvester counted `set(phrases_of(text))` per article. So it is a DOCUMENT
# count and the same chi-squared applies, with one substitution: the per-outlet
# article total is not stored, so the outlet's largest single phrase count stands
# in for it. Some near-universal word appears in essentially every article, which
# makes the proxy tight, and it is only ever used as a denominator for rates.

def derive_from_counts(conn, roster: dict) -> list[dict]:
    """Chi-squared over harvested counts. Same filters, same meaning, more text.

    `roster` maps source_id -> {"base": int, "name": str}, so this never reads a
    label out of the counts table and the split stays by outlet.
    """
    rows = conn.execute(
        "select source_id, phrase, count from outlet_phrase_counts").fetchall()
    per_outlet = collections.defaultdict(dict)
    for sid, phrase, count in rows:
        per_outlet[sid][phrase] = count

    # THE DENOMINATOR, and why it is no longer taken from the counts themselves.
    #
    # This was `max(counter.values())` and called a proxy. It was roughly right while
    # the commonest phrase was stored, because "the" appears in nearly every article.
    # `phrase_counts.band` now DELETES every phrase above MAX_DOC_SHARE of an outlet's
    # articles, so that maximum is bounded by MAX_DOC_SHARE and the proxy understates
    # the article count by exactly 1/MAX_DOC_SHARE.
    #
    # WHAT THAT DOES, stated correctly, because the first version of this note got it
    # wrong. The chi-squared is SCALE-INVARIANT: `el = n * left_docs / total` depends
    # only on the ratio left_docs/total, so scaling every outlet by the same factor
    # leaves el, er and chi untouched, and the side test `l/L > r/R` with it. Measured
    # over the pre-band table, the two rankings agree at Spearman 0.9999 with 7 side
    # flips in 2,448, and those come from the scale being slightly NON-uniform (0.479
    # to 0.500, plus unbanded small outlets at 1.0), not from the factor itself.
    #
    # The damage is in `MAX_DOC_FREQ`, and it is large. That test is `n / total`, where
    # n is unaffected and total is halved, so a filter meant to fire at 25% fires at a
    # true document frequency of 12.5%. Measured: 2,448 candidates against 2,794, so
    # 346 of them, 12%, silently deleted, and by construction the highest-n ones, which
    # is exactly the middle band this whole change exists to preserve.
    #
    # `outlet_phrase_articles` records the real count beside the phrases. The fallback
    # stays for tables written before it existed, and SAYS SO rather than guessing
    # quietly, because a silent proxy is how the 4,000-row ceiling hid for a day.
    articles: dict[str, int] = {}
    try:
        articles = {sid: n for sid, n in conn.execute(
            "select source_id, articles from outlet_phrase_articles") if n}
    except sqlite3.OperationalError:
        pass
    missing = [sid for sid in per_outlet if sid not in articles]
    if missing:
        # EXCLUDED, not estimated. A uniform error in the denominator is nearly free:
        # `el` and `er` below depend only on left_docs/total, so scaling every outlet
        # by the same factor leaves the chi-squared unchanged. A MIXED scale is not
        # free, and falling back for some outlets while others carry the real count is
        # exactly that. Dropping them loses their evidence; keeping them corrupts
        # everyone else's.
        for sid in missing:
            per_outlet.pop(sid, None)
        print(f"  WARNING: no stored article count for {len(missing)} of "
              f"{len(missing) + len(articles)} outlets, so they are EXCLUDED rather "
              f"than estimated: mixing a real denominator with a proxy one is worse "
              f"than either alone. Re-harvest to bring them back.")

    banned = set()
    for sid, meta in roster.items():
        for w in _WORD.findall((meta.get("name") or "").lower()):
            banned.add(w)

    left_docs = right_docs = 0
    counts = collections.defaultdict(lambda: [0, 0])
    outlets = collections.defaultdict(lambda: (set(), set()))
    # THE FILTER THIS PATH WAS MISSING. `phrases()` drops STOP unigrams, anything
    # under three letters, and any bigram or trigram bracketed by stopwords ("of the",
    # "at the"). `phrase_counts.phrases_of` deliberately stores raw, which is the right
    # layering, but this function never applied the rule at read time, so `at the`,
    # `to be`, `with the`, `were`, `than` and `had` could rank.
    #
    # That is not cosmetic. `score_outlets` is the only function that turns a candidate
    # into a number, and it iterates `phrases()`, which CAN NEVER EMIT those. A fifth
    # of anything promoted from here was structurally unscoreable, and the head of the
    # ranking was polluted with it.
    def _emittable(phrase: str) -> bool:
        parts = phrase.split()
        if len(parts) == 1:
            return parts[0] not in STOP and len(parts[0]) > 2
        return not (parts[0] in STOP and parts[-1] in STOP)

    for sid, phrases_map in per_outlet.items():
        meta = roster.get(sid)
        if not meta or meta["base"] == 50:
            continue
        side = 0 if meta["base"] < 50 else 1
        n_articles = articles.get(sid, 0)
        if side == 0:
            left_docs += n_articles
        else:
            right_docs += n_articles
        for phrase, count in phrases_map.items():
            if phrase in banned or not _emittable(phrase):
                continue
            counts[phrase][side] += count
            outlets[phrase][side].add(sid)

    total = left_docs + right_docs
    if not total:
        return []
    out = []
    for phrase, (l, r) in counts.items():
        n = l + r
        left_outlets, right_outlets = outlets[phrase]
        if n < MIN_ARTICLES or len(left_outlets) + len(right_outlets) < MIN_OUTLETS:
            continue
        if (len(left_outlets) < MIN_OUTLETS_PER_SIDE
                or len(right_outlets) < MIN_OUTLETS_PER_SIDE):
            continue
        if n / total > MAX_DOC_FREQ:
            continue
        el = n * left_docs / total
        er = n * right_docs / total
        if el < 1 or er < 1:
            continue
        chi = ((abs(l - el) - 0.5) ** 2) / el + ((abs(r - er) - 0.5) ** 2) / er
        rate_l = l / left_docs
        rate_r = r / right_docs
        out.append({"phrase": phrase, "side": "left" if rate_l > rate_r else "right",
                    "chi2": round(chi, 2), "left": l, "right": r,
                    "outlets": len(left_outlets) + len(right_outlets),
                    "left_outlets": len(left_outlets),
                    "right_outlets": len(right_outlets),
                    "rate_left": round(rate_l * 100, 3),
                    "rate_right": round(rate_r * 100, 3)})
    out.sort(key=_rank)
    return out


if __name__ == "__main__":
    if "--counts" in sys.argv:
        _roster = (sys.argv[sys.argv.index("--roster") + 1]
                   if "--roster" in sys.argv else None)
        raise SystemExit(main_counts(sys.argv[sys.argv.index("--counts") + 1], _roster))
    raise SystemExit(main())
