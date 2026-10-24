#!/usr/bin/env python3
"""The derivation must not be allowed to measure itself, or to store an article.

Two modules, one question each.

`lexicon_derive.py` derives lean phrases from outlets the roster has placed. Deriving
from labels and then reporting how well the result predicts labels is a mirror, not a
measurement, and it is the same mistake as the `source_topic_lean` loop cut on
2026-09-22. The defence is a split by OUTLET, never by article: two articles from one
outlet share its vocabulary, so an article split would let a phrase fitted on one
"predict" the other and the number would measure memorisation.

It also needs a sanity test with no judgement in it, because the first run looked
successful and was not. It reached rho +0.226 on held-out outlets while rediscovering
ZERO of the 318 hand-written political phrases, and its top entries were `getty
images`, `continue`, `follow`, `photo` and `sep`. Outlets on a side often share a
publishing platform, so the ranking was fingerprinting CMS templates. A real-looking
number measuring the wrong thing is worse than a low one.

`phrase_counts.py` is what unblocks that, by counting phrases in full article bodies
before the IP truncation and storing counts rather than text. Its one invariant is that
a stored row is a phrase and not a sentence, and a promise in a comment is not an
invariant.
"""
import collections
import json
import importlib.util
import pathlib
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipeline"))


def load(name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "pipeline" / "analyzers" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ld = load("lexicon_derive")
pc = load("phrase_counts")

# The hand-written lexicon the derivation is measured against. `political_lean`
# imports the Supabase switch, which raises without VOID_SQLITE_PATH, so the two
# tuples are read straight out of the file rather than imported: this gate has to run
# in CI, where no state database exists.
def _known_phrases() -> set:
    import ast
    src = (ROOT / "pipeline" / "analyzers" / "political_lean.py").read_text("utf-8")
    tree = ast.parse(src)
    out: set = set()
    for node in tree.body:
        # They are annotated dict literals (`LEFT_KEYWORDS: dict[str, int] = {...}`),
        # so the node is an AnnAssign and the phrases are the dict's KEYS.
        if isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        else:
            continue
        if not (isinstance(target, ast.Name)
                and target.id in ("LEFT_KEYWORDS", "RIGHT_KEYWORDS")):
            continue
        if isinstance(value, ast.Dict):
            items = value.keys
        else:
            items = getattr(value, "elts", [])
        for k in items:
            if isinstance(k, ast.Constant) and isinstance(k.value, str):
                out.add(k.value.lower())
    if not out:
        raise SystemExit(
            "could not read LEFT_KEYWORDS/RIGHT_KEYWORDS out of political_lean.py; "
            "this gate measures against them and must not silently pass on an "
            "empty set")
    return out


KNOWN_PHRASES = _known_phrases()

failures: list[str] = []


def check(name, cond, detail=""):
    if cond:
        print(f"PASS  {name}")
    else:
        failures.append(f"{name}: {detail}" if detail else name)
        print(f"FAIL  {name} {detail}")


# --- the split is by outlet, and it is stable -------------------------------
slugs = [f"outlet-{i}" for i in range(400)]
held = {s for s in slugs if ld.hash_split(s)}
fit = {s for s in slugs if not ld.hash_split(s)}
check("fit and holdout outlets are disjoint", not (held & fit))
check("every outlet lands on exactly one side", len(held) + len(fit) == len(slugs))
check("the holdout is a usable share, not empty or everything",
      0.1 < len(held) / len(slugs) < 0.45, f"{len(held) / len(slugs):.0%}")
check("the split is deterministic across calls",
      all(ld.hash_split(s) == (s in held) for s in slugs))
check("the split does not depend on insertion order",
      {s for s in reversed(slugs) if ld.hash_split(s)} == held)

# --- a planted signal is found, and noise is not ----------------------------
LEFT_MARK, RIGHT_MARK = "wealth tax now", "border security now"


def corpus(mark_left, mark_right, n_outlets=30, n_articles=60):
    """A corpus where each mark is used by BOTH sides, at different rates.

    The first version of this fixture gave each mark exclusively to one side, and the
    derivation correctly refused to return it: a phrase only ever used by one side is
    what a masthead, a city name or a CMS template looks like, and refusing those is
    the entire point of MIN_OUTLETS_PER_SIDE. Ideology does not look like that.
    "illegal alien" appears in left coverage too, criticising it; what differs is the
    RATE. So the left mark appears in 80% of left articles and 20% of right ones, and
    the test is whether a rate difference is recovered.
    """
    rows = []
    for i in range(n_outlets):
        side_left = i % 2 == 0
        base = 20 if side_left else 80
        for j in range(n_articles):
            filler = f"ordinary council coverage number {j % 7} about a meeting"
            marks = []
            # 3 of every 10 on the owning side, 1 of every 20 on the other. Kept well
            # under MAX_DOC_FREQ: a first attempt used 80%/20%, which put the phrase in
            # half of all documents and the derivation dropped it for being too common,
            # correctly. A phrase in half the corpus is "said", not "wealth tax".
            if (j % 10) < (3 if side_left else 0) or (side_left is False and j % 20 == 0):
                marks.append(mark_left)
            if (j % 10) < (3 if not side_left else 0) or (side_left and j % 20 == 0):
                marks.append(mark_right)
            rows.append({"slug": f"o{i}", "name": f"Outlet {i}", "lab": "x",
                         "base": base, "text": f"{filler} {' '.join(marks)}"})
    return rows


found = ld.derive(corpus(LEFT_MARK, RIGHT_MARK))
phrases = {d["phrase"]: d for d in found}
check("a planted left phrase is recovered on the left",
      LEFT_MARK in phrases and phrases[LEFT_MARK]["side"] == "left",
      str(phrases.get(LEFT_MARK)))
check("a planted right phrase is recovered on the right",
      RIGHT_MARK in phrases and phrases[RIGHT_MARK]["side"] == "right",
      str(phrases.get(RIGHT_MARK)))
# The top entry is `border`, the unigram inside the planted trigram, and that is
# right: it carries the same signal and occurs more often, so it ranks higher. The
# assertion is that the top phrase comes FROM a planted mark, not that it is the whole
# mark. Demanding the exact trigram would have been a test of my fixture rather than
# of the derivation.
planted_words = set(LEFT_MARK.split()) | set(RIGHT_MARK.split())
check("the top phrase comes from a planted mark, not the filler",
      found and set(found[0]["phrase"].split()) <= planted_words,
      found[0]["phrase"] if found else "nothing derived")

# --- the ranking is REPRODUCIBLE, not merely sorted -----------------------------
# This gate passed locally four times and failed in CI, which is the signature of
# hash-order dependence rather than flakiness. `sort(key=-chi2)` is not a total
# order: nine phrases tie at 87.820 on the fixture above, Python's sort is stable,
# and the surviving order came from iterating SETS of strings, which Python
# randomises per process. Seed 0 gave `wealth`, seed 1 `border`, seed 5
# `about meeting wealth`, and that last one is filler straddling the plant.
#
# A same-process re-run cannot catch this, because PYTHONHASHSEED is fixed once
# the interpreter starts. So this runs the derivation in two subprocesses with
# different seeds and requires the same answer from both.
import subprocess  # noqa: E402

_PROBE = r"""
import importlib.util, pathlib, sys, json
R = pathlib.Path(%r)
sys.path.insert(0, str(R)); sys.path.insert(0, str(R / "pipeline"))
sp = importlib.util.spec_from_file_location("ld", R / "pipeline/analyzers/lexicon_derive.py")
ld = importlib.util.module_from_spec(sp); sys.modules["ld"] = ld; sp.loader.exec_module(ld)
L, RM = "wealth tax", "border security"
rows = []
for i in range(40):
    sl = i %% 2 == 0; base = 20 if sl else 80
    for j in range(30):
        f = f"ordinary council coverage number {j %% 7} about a meeting"; m = []
        if (j %% 10) < (3 if sl else 0) or (sl is False and j %% 20 == 0): m.append(L)
        if (j %% 10) < (3 if not sl else 0) or (sl and j %% 20 == 0): m.append(RM)
        rows.append({"slug": f"o{i}", "name": f"Outlet {i}", "lab": "x",
                     "base": base, "text": f"{f} {' '.join(m)}"})
print(json.dumps([d["phrase"] for d in ld.derive(rows)[:10]]))
""" % str(ROOT)


def _top_ten(seed: str):
    import os
    env = dict(os.environ, PYTHONHASHSEED=seed)
    r = subprocess.run([sys.executable, "-c", _PROBE], capture_output=True,
                       text=True, env=env, timeout=300)
    if r.returncode != 0:
        return None, r.stderr.strip()[-200:]
    return json.loads(r.stdout.strip().splitlines()[-1]), ""


_a, _ea = _top_ten("0")
_b, _eb = _top_ten("5")
check("the derivation runs under a fixed hash seed", _a is not None, _ea)
check("and under a different one", _b is not None, _eb)
if _a is not None and _b is not None:
    check("the ranking does not depend on PYTHONHASHSEED",
          _a == _b, f"seed 0 {_a[:3]} vs seed 5 {_b[:3]}")
    check("ties are broken toward the SHORTER phrase, which is the general finding",
          _a and len(_a[0].split()) == 1, str(_a[:3]))

# The other direction, which is the one that matters: identical text on both sides
# must yield no high-confidence phrase at all.
# Both marks identical means both sides use both at the same rate: no signal.
flat = ld.derive(corpus("same phrase here", "same phrase here"))
top = flat[0]["chi2"] if flat else 0.0
check("a corpus with no side signal yields no strong phrase", top < 10.0,
      f"top chi2 {top}")

# --- a masthead may not become a political phrase ---------------------------
mast = corpus("", "")
for r in mast:
    if r["base"] == 20:
        r["name"] = "The Sentinel"
        r["text"] += " sentinel"
check("an outlet's own name is excluded from its phrases",
      "sentinel" not in {d["phrase"] for d in ld.derive(mast)})

# --- a candidate carries the evidence behind it -----------------------------
check("every candidate records its counts and its outlets per side",
      all({"left", "right", "left_outlets", "right_outlets", "chi2"} <= set(d)
          for d in found), str(found[0]) if found else "")

# --- phrase_counts stores a phrase, never a sentence ------------------------
SENTENCE = ("The minister said the policy would proceed despite objections from "
            "three separate committees and a lengthy public consultation process")
tally = pc.accumulate([{"source_id": "s1", "title": SENTENCE,
                        "summary": "", "full_text": SENTENCE}])
widest = max((len(p.split()) for p in tally["s1"]), default=0)
check(f"no accumulated phrase exceeds {pc.MAX_PHRASE_WORDS} words",
      widest <= pc.MAX_PHRASE_WORDS, f"widest {widest}")

conn = sqlite3.connect(":memory:")
# A caller handing it a sentence must be refused at the write, not trusted upstream.
forced = {"s1": collections.Counter({SENTENCE: 3, "wealth tax": 5, "": 2})}
pc.persist(conn, forced, now="2026-09-22")
stored = list(conn.execute("select phrase, words, count from outlet_phrase_counts"))
check("a sentence handed straight to persist() is refused",
      all(w <= pc.MAX_PHRASE_WORDS for _, w, _ in stored),
      str([p for p, w, _ in stored if w > pc.MAX_PHRASE_WORDS])[:120])
check("an empty phrase is refused", all(p.strip() for p, _, _ in stored))
check("the phrase that belongs is kept",
      any(p == "wealth tax" for p, _, _ in stored), str(stored))

pc.persist(conn, {"s1": collections.Counter({"wealth tax": 4})}, now="2026-09-23")
merged = conn.execute("select count from outlet_phrase_counts where phrase='wealth tax'"
                      ).fetchone()[0]
check("a second run adds to the count rather than replacing it", merged == 9, merged)

# --- the band keeps the rare middle, not the commonest N --------------------
# `persist` used to keep `most_common(4000)` per outlet. Measured 2026-09-23 on the
# first real harvest, all 98 outlets hit that ceiling EXACTLY out of 112,891 distinct
# phrases, 259 of the 318 known political phrases never entered the table, and the 59
# that did sat at a median frequency rank of 37,906. The derivation was handed each
# outlet's page furniture and asked to find politics in it.
BAND_CASES = collections.Counter({
    "subscribe now": 90,    # furniture: in 90 of the outlet's 100 articles
    "wealth tax": 14,       # the middle, where argument lives
    "border security": 8,
    "a one off": 1,         # too rare to carry a rate difference
})
kept = dict(pc.band(BAND_CASES, 100))
check("the band drops an outlet's own furniture",
      "subscribe now" not in kept, str(sorted(kept)))
check("the band keeps the rare middle",
      {"wealth tax", "border security"} <= set(kept), str(sorted(kept)))
check("the band drops the long tail", "a one off" not in kept, str(sorted(kept)))

# A share is meaningless without a denominator, and inferring one from the counts is
# exactly the mistake that hid the ceiling. No article count means no band.
check("no article count means nothing is cut",
      len(pc.band(BAND_CASES, None)) == len(BAND_CASES))
check(f"under {pc.BAND_MIN_ARTICLES} articles nothing is cut",
      len(pc.band(BAND_CASES, pc.BAND_MIN_ARTICLES - 1)) == len(BAND_CASES))
check("the ceiling applies to what the band already kept, so it cannot decide "
      "which KIND of phrase survives",
      pc.MAX_ROWS_PER_OUTLET > 10000, pc.MAX_ROWS_PER_OUTLET)

# The band must reach the table, not just the helper.
conn2 = sqlite3.connect(":memory:")
pc.persist(conn2, {"s9": BAND_CASES}, now="2026-09-23", articles={"s9": 100})
banded = {r[0] for r in conn2.execute("select phrase from outlet_phrase_counts")}
check("persist() applies the band when given a real article count",
      banded == {"wealth tax", "border security"}, str(sorted(banded)))

# --- the thresholds are set where they bound STORAGE, not signal --------------
# Measured against the pre-band table (98 outlets, ~81 bodies each) over the 175 rows
# matching hand-written political phrases: a floor of 3 cut 17% of them, 4 cut 36%,
# 5 cut 44%; a floor of 2 cuts 5%. A storage rule that removes a sixth of the
# vocabulary the derivation is looking for is not a storage rule.
check(f"the floor does not cut a sixth of the political vocabulary "
      f"(is {pc.MIN_ARTICLES_PER_PHRASE})", pc.MIN_ARTICLES_PER_PHRASE <= 2,
      pc.MIN_ARTICLES_PER_PHRASE)
check("the floor still removes the count-1 tail",
      pc.MIN_ARTICLES_PER_PHRASE >= 2, pc.MIN_ARTICLES_PER_PHRASE)
check("the per-outlet ceiling is looser than the derivation's own signal filter, "
      "which is where that decision belongs",
      pc.MAX_DOC_SHARE > ld.MAX_DOC_FREQ,
      f"band {pc.MAX_DOC_SHARE} vs MAX_DOC_FREQ {ld.MAX_DOC_FREQ}")

# --- the denominator the band would otherwise break ---------------------------
# `derive_from_counts` took max(count) as the article count. The band deletes every
# phrase above MAX_DOC_SHARE of an outlet's articles, so that maximum is bounded by
# MAX_DOC_SHARE and the proxy understates by ~1/MAX_DOC_SHARE. Rates inflate, and
# MAX_DOC_FREQ then cuts the middle band this change exists to keep.
conn3 = sqlite3.connect(":memory:")
pc.persist(conn3, {"s1": collections.Counter(
    {"wealth tax": 14, "border security": 8, "subscribe now": 90})},
    now="2026-09-23", articles={"s1": 100})
stored_n = conn3.execute(
    "select articles from outlet_phrase_articles where source_id='s1'").fetchone()
check("persist records how many articles the counts came from",
      stored_n and stored_n[0] == 100, str(stored_n))
top = conn3.execute("select max(count) from outlet_phrase_counts").fetchone()[0]
check("and the old proxy would have been wrong by more than a third here",
      top < 100 * 0.7, f"max(count)={top} against 100 articles")

pc.persist(conn3, {"s1": collections.Counter({"wealth tax": 6})},
           now="2026-09-24", articles={"s1": 40})
again = conn3.execute(
    "select articles from outlet_phrase_articles where source_id='s1'").fetchone()[0]
check("a second run accumulates the denominator with the counts", again == 140, again)

check("the article table holds a COUNT and no identifier",
      {r[1] for r in conn3.execute("pragma table_info(outlet_phrase_articles)")}
      == {"source_id", "articles", "updated_at"},
      str(sorted(r[1] for r in conn3.execute(
          "pragma table_info(outlet_phrase_articles)"))))

# --- the gate's own denominator ----------------------------------------------
# Every report so far said "zero of the 318". 318 is not reachable: nine phrases are
# four or five words and cannot be stored under MAX_PHRASE_WORDS, and two carry digits
# the tokeniser strips. A gate read three times as evidence about the method has to
# divide by what the method can actually reach.
reach, unreach = ld.reachable_known(KNOWN_PHRASES)
check("the unreachable phrases are excluded from the gate's denominator",
      len(reach) == len(KNOWN_PHRASES) - len(unreach) and len(unreach) > 0,
      f"{len(reach)} reachable, {len(unreach)} not")
check("nothing reachable exceeds the stored width bound",
      all(len(p.split()) <= pc.MAX_PHRASE_WORDS for p in reach))
check("a phrase the tokeniser cannot emit is called unreachable, not missed",
      all(" ".join(pc._WORD.findall(p)) == p for p in reach))
check("the four and five word phrases are the ones excluded",
      any(len(p.split()) > pc.MAX_PHRASE_WORDS for p in unreach), str(sorted(unreach)[:3]))

cols = {r[1] for r in conn.execute("pragma table_info(outlet_phrase_counts)")}
check("the table stores no article identifier, so rows cannot be re-associated",
      not (cols & {"article_id", "url", "text", "body", "full_text"}), str(sorted(cols)))

if failures:
    print(f"\nFAIL  {len(failures)} lexicon check(s)")
    sys.exit(1)
print("\nPASS  the derivation cannot measure itself, and the counts cannot hold prose")
