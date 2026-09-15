"""Same-event merge, in Stage 2, over the candidate bench.

Two disjoint clusters covering one real event ship as two cards with two source
counts, two summaries and two bias labels. On 2026-09-06 the feed carried the
Nepal flood rescue at 46 sources (rank 18) and 9 sources (rank 27), spelling the
survivor's name two ways, and the Pentagon polygraph story at 12 sources (rank
20) and 8 (rank 48).

Why the existing Phase 7 pass did not catch them
------------------------------------------------
Phase 7 (clustering/same_event_merge.py, disabled 2026-09-06 after it fused
unrelated events) is not too strict for these pairs. Measured against the
stored membership, BOTH pairs pass all three of its conjuncts: Nepal shares 3
salient entities and 2 title stems and the clusters are 23 minutes apart;
Pentagon shares 2 entities and 2 stems and is 7 hours apart. The gate never
rejected them because the gate never saw them. Phase 7's candidate set is the
top 50 clusters by source_count out of the whole 36-hour corpus, and the
partners have 9 and 8 sources. Inside the 100 clusters that even reached the
feed pool, 37 already carry more than 9 sources and 44 more than 8; the corpus
is roughly twenty times that size. The window was full long before it reached
them.

That is why this pass lives here. The bench is 35 clusters chosen by RANK, not
by raw source count, so the small half of a duplicate pair is in it precisely
because the ranker already thinks it belongs on the page.

The Pentagon pair also shows why entity overlap cannot carry the gate alone:
its two "shared salient entities" are `new york` and `york`, the New York Times
masthead leaking out of article titles. Mastheads are excluded here.

The gate
--------
Conjunctive, and every conjunct has to be earned:

    the two titles share at least MERGE_MIN_SHARED_STEMS SPECIFIC stems
    AND the clusters are within MERGE_TEMPORAL_HOURS
    AND at least one of those shared stems survives as an ANCHOR

"Specific" excludes the vocabulary any two same-day news stories share: day,
kill, strike, order, official, and the prepositions the tokenizer keeps ("into"
is why a Tesla autonomy probe and the US Open tennis draw shared two stems).
An anchor additionally excludes outlet mastheads (the Pentagon pair's only
shared entities were `new york` and `york`, the New York Times) and words that
are proper nouns in one headline and common verbs in another (Regulators OPEN
a probe; Alcaraz into the US OPEN). Demonyms are normalized, so "Nepal" and
"Nepali" are one anchor; without that the Nepal pair shares one stem, not two.

Deliberately NOT in the gate:

  * a numeric branch ("both mention a death toll"). It was the primary
    contamination path when Phase 7 shipped with it: it merged any two same-day
    casualty stories.
  * article cosine. Cross-cluster article cosine saturates near 1.0 on shared
    wire reprints, so it separates nothing.
  * topic_coherence. It scores any shared word as on topic and reported 1.00 on
    the Assam cluster at a true precision of 0.25.

Merging is pairwise into the higher-sourced survivor, with no transitive chains
and a ceiling of MERGE_CEILING absorbed clusters, so this can never manufacture
a mega-cluster. Bias is NEVER averaged: the merge writes the unioned membership
and then re-runs the pipeline's own aggregation over the merged article set, so
a 55 and a 42 become one number computed from all the articles.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from typing import Callable, Optional

from editorial.standard import title_stem_sequence, title_word_stems

MERGE_TEMPORAL_HOURS = 48
MERGE_MIN_SHARED_STEMS = 2
MERGE_CEILING = 3

# A stem carried by this many SEPARATE bench headlines is the day's ambient
# vocabulary, not an identifier (see ambient_stems).
AMBIENT_MIN_DF = 3

# A pair this alike in raw headline vocabulary is the same story told twice,
# and may merge on ONE independent signal instead of two (see should_merge).
MERGE_NEAR_IDENTICAL_JACCARD = 0.33

# Vocabulary any two same-day news stories share. A stem in here can never be
# one of the two specific stems, and can never be the anchor.
GENERIC_STEMS = frozenset({
    "day", "week", "month", "year", "time", "hour", "new", "old", "top",
    "kill", "dead", "death", "die", "injur", "wound", "toll", "victim",
    "strike", "attack", "hit", "blast", "fire", "crash", "explos",
    "order", "call", "say", "said", "tell", "warn", "urg", "vow", "plan",
    "leader", "presid", "minist", "offici", "author", "govern", "state",
    "polic", "court", "judg", "case", "probe", "investig", "arrest",
    "man", "woman", "peopl", "famili", "home", "citi", "town", "villag",
    "found", "face", "over", "sourc", "live", "updat", "latest",
    "recap", "roundup",
    # Prepositions and connectives the tokenizer keeps. "into" is why a Tesla
    # autonomy probe and the US Open tennis draw shared two stems.
    "into", "onto", "upon", "amid", "across", "within", "without",
    "toward", "after", "befor", "dure", "against", "among",
})

# Words that are proper nouns in one headline and common verbs or nouns in
# another. "Federal Regulators OPEN Probe Into Tesla" and "Alcaraz into US
# OPEN last 16" share the stem and share nothing else. This is the same class
# of bug as the ranker's "pla" matching "downplays": a lexical hit that carries
# no meaning. An ambiguous word can never be the anchor.
AMBIGUOUS_ANCHORS = frozenset({
    "open", "close", "post", "mail", "sun", "star", "march", "may",
    "will", "union", "standard", "record", "journal", "age", "hill",
    "point", "mark", "green", "brown", "young", "west", "east", "north",
    "south", "general", "nation", "capit", "counter", "bank",
})

# Demonym and adjectival forms that must resolve to one anchor. Keyed by the
# STEM the tokenizer produces.
# Keyed on the stems the TOKENIZER produces, not on the words. The lookup runs
# AFTER stemming, so a key written as an ordinary spelling never fires. Two
# were: "Israeli" arrives as `isra`, so "Nations Impose Sanctions on ISRAELI
# Settlements" and "ISRAEL Orders UK to Close East Jerusalem Consulate" shared
# no stem at all on 2026-09-10; and "US" is a title stopword, so `us` never
# reached the lookup and is simply gone. The -ese demonyms were already right
# (`chines`, `japanes`, `nepales` are what the stemmer emits).
#
# This is the third appearance of one defect. Rev 57 fixed possessives in the
# brief's continuing-story matcher, rev 65 found `germany'` failing to match
# `German` in this module, and this is the same shape one layer down. The test
# below asserts on WORD PAIRS rather than on key spellings, because a key that
# is already a stem can be stemmed again and a naive check misreads five of
# these as broken.
_DEMONYM = {
    "nepali": "nepal", "nepales": "nepal",
    "isra": "israel", "palestinian": "palestin",
    "russian": "russia", "ukrainian": "ukrain", "ukrain": "ukrain",
    "chines": "china", "japanes": "japan", "indian": "india",
    "iranian": "iran", "iraqi": "iraq", "syrian": "syria",
    "german": "germani", "french": "franc", "spanish": "spain",
    "britain": "british", "uk": "british", "american": "usa",
    "mexican": "mexico", "brazilian": "brazil", "turkish": "turkey",
    "pakistani": "pakistan", "afghan": "afghanistan", "egyptian": "egypt",
    "nigerian": "nigeria", "kenyan": "kenya", "sudanes": "sudan",
    "korean": "korea", "vietnames": "vietnam", "thai": "thailand",
    "greek": "greec", "polish": "poland", "swedish": "sweden",
    "danish": "denmark", "dutch": "netherland", "italian": "itali",
}


# Quantities. A number is the most portable word in a headline: every day
# carries a dozen unrelated stories that each count something. On 2026-09-10
# "US Destroys FIVE Iranian Tankers" absorbed "Cargo Ship Fire at Chinese Port
# Kills 25, Injures FIVE" on the pair (five, ship), putting an industrial fire
# in a Qingdao shipyard and a naval exchange in the Strait of Hormuz on one
# card at rank 1; on 2026-08-10 a Chinese typhoon and a British Columbia
# wildfire shared (000, evacu).
#
# The module docstring already refused a numeric BRANCH ("both mention a death
# toll") because it was Phase 7's primary contamination path. That refusal was
# incomplete: numbers still entered through the ordinary stem path, where a
# spelled-out cardinal is just a word. A quantity can never identify an event,
# so it is barred from the stem count and from the anchor alike.
_DIGIT = re.compile(r"\d")
_CARDINALS = frozenset("""
one two three four five six seven eight nine ten eleven twelv
thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenti
thirti forti fifti sixti seventi eighti nineti hundr thousand
million billion trillion dozen percent
""".split())


def _is_quantity(stem: str) -> bool:
    return bool(_DIGIT.search(stem)) or stem in _CARDINALS


# Process vocabulary: words that describe what happened to a story rather than
# which story it is. Kept SEPARATE from GENERIC_STEMS, which the coherence pass
# also reads. The two passes have opposite error preferences, and widening the
# shared list would silently make coherence delete more real coverage: a member
# whose headline says "Supreme Court" and nothing else in the vocabulary would
# stop matching its own cluster. This set is subtracted by should_merge only.
#
# Every entry here anchored a false merge in the 30-day replay:
#   mak      Typhoon Dolphin MAKES landfall / Delta flight MAKES emergency landing
#   includ   Zimbabwe ferry toll INCLUDING 18 / Kentucky shooting INCLUDING two
#   leave    China mudslides LEAVE hundreds missing / Bolivia blast LEAVES two dead
#   launch   North Korea LAUNCHES missiles / South Korean bank LAUNCHES Vietnam unit
#   off      Altalena shipwreck OFF the coast / tanker struck OFF Oman
#   plea     two unrelated Supreme Court PLEAS on one docket day
#   murder   Lindsay Clancy MURDER TRIAL / Charlie Kirk MURDER suspect
#   primari  Minnesota Senate PRIMARY / Minnesota GOP governor PRIMARY
#   evacu    Typhoon Dolphin prompts EVACUATIONS / Delta flight EVACUATED
#   report   Pentagon fires a Stars and Stripes editor / Pentagon REPORTS
#            increased sexual assault REPORTING
MERGE_GENERIC_STEMS = frozenset({
    # process verbs and the prepositions the tokenizer keeps
    "make", "includ", "leav", "launch", "miss", "still", "off",
    "evacu", "report",
    # judicial and electoral process: the docket, not the case. `supreme` and
    # `murder` are deliberately NOT here. Barring `supreme` also rejected the
    # real pair "Supreme Court Rules on Transgender Care Ban in 6-3 Decision"
    # / "Supreme Court Upholds Tennessee Law Restricting Care for Minors",
    # which rev 59 identified as one story printed twice. Barring the docket
    # word `plea` is enough to separate two unrelated cases heard the same day
    # while leaving a shared SUBJECT like `care` to carry a genuine pair.
    "plea", "trial", "juri", "verdict", "primari",
})


def independent_signals(shared: set, title_a: str, title_b: str) -> set:
    """Collapse shared stems that are adjacent words of one phrase.

    MERGE_MIN_SHARED_STEMS asks for two shared stems on the theory that two
    stems are two independent pieces of evidence. For a fixed multi-word name
    they are not. "White House" is one institution, and a gate counting `white`
    and `house` believes a ballroom lawsuit and a press secretary's resignation
    agree on two things when they agree on one. Measured over 30 printed days
    that single phrase carried SIX false merges, more than any other cause, and
    `prime minister`, `vice president`, `justice department` and `democratic
    senate` carried the rest of that class.

    Measured over the 30-day printed archive, the gate proposed 131 merges
    before these filters and 35 after, and the six real decisions of the
    2026-09-10 run all come out right.

    Adjacency is checked in BOTH headlines, which is what makes this safe
    without a lexicon of institutions. Two words that happen to sit side by side
    once are not a phrase; two that sit side by side in both headlines are the
    same name written twice. "Saudi Arabia, Turkey, Pakistan Sign Mecca Joint
    Defense Pact" against "...Sign NATO-Style Defense Pact" still merges,
    because collapsing `saudi arabia` leaves `defense` and `pact` behind.

    Returns one representative per phrase, so the caller keeps counting stems.
    """
    seq_a, seq_b = title_stem_sequence(title_a), title_stem_sequence(title_b)

    def pairs(seq):
        return {(x, y) for x, y in zip(seq, seq[1:])}

    both = pairs(seq_a) & pairs(seq_b)
    parent = {s: s for s in shared}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for x, y in both:
        if x in parent and y in parent and find(x) != find(y):
            parent[find(y)] = find(x)
    return {find(s) for s in shared}


def title_jaccard(title_a: str, title_b: str) -> float:
    """Raw content-stem overlap of two headlines, before any merge filter.

    Deliberately computed on unfiltered specific_stems: its job is to be
    independent evidence about whether two headlines describe one event, so
    subtracting the day's ambient vocabulary from it would couple it to the
    very filter it exists to backstop.
    """
    A, B = specific_stems(title_a), specific_stems(title_b)
    return len(A & B) / len(A | B) if (A | B) else 0.0


def ambient_stems(titles: list[str], min_df: int = AMBIENT_MIN_DF) -> frozenset:
    """Stems that appear in at least min_df of the bench's OWN headlines.

    GENERIC_STEMS is a hand-written list, so it can only exclude vocabulary
    somebody thought of in advance. It cannot know that on 2026-09-10 the word
    that joined four unrelated cards was `trump`, or that on an election week
    it is `midterm`, or that on the day oil passes $100 it is `oil`. That run
    made six merges and five were wrong, every one of them anchored on the
    day's ambient vocabulary:

        Trump Promises $5,000 Dividend  <- German Far-Right AfD Wins
                                           Saxony-Anhalt      (trump, win)
        Trump Promises $5,000 Dividend  <- Trump Predicts Iran War Ends
                                           After Midterms  (midterm, trump)
        Trump Predicts Oil Prices Fall  <- Trump Pledges $5,000 Payments
                                                          (midterm, trump)
        Trump Predicts Oil Prices Fall  <- Trump Touts US as Top Oil
                                           Producer            (oil, trump)

    The sixth merge, the only correct one, anchored on `assassin` and
    `anniversari`: words no other story that day had any use for. That is the
    whole signal, and it is measurable without a lexicon.

    min_df is 3 and not 2 on purpose. A genuine duplicate pair contributes a
    document frequency of exactly 2 to its own shared vocabulary, so a floor of
    2 would bar every true merge from its own evidence. A stem reaching 3 means
    a THIRD headline, on the bench because the ranker judged it a different
    story, also uses the word. At that point the word describes the news day
    rather than the event.

    The error preference is precision, and deliberately so. A false merge
    deletes a story: on 2026-09-10 the AfD win in Saxony-Anhalt was absorbed
    into a card about US dividend cheques and left the feed entirely. A missed
    merge leaves two cards on one thread, which is visible, recoverable and
    costs the reader one slot.
    """
    df: dict[str, int] = {}
    for t in titles or []:
        for stem in specific_stems(t):
            df[stem] = df.get(stem, 0) + 1
    return frozenset(s for s, k in df.items() if k >= min_df)


def _norm(stem: str) -> str:
    return _DEMONYM.get(stem, stem)


def specific_stems(title: str) -> set[str]:
    """Title stems that could identify a story, demonyms normalized.

    Hyphenated tokens are NOT split here. The merge gate's error preference is
    precision: splitting "Nepal-Tibet Flood" into nepal and flood is enough to
    merge a Singapore xenophobia story into the Nepal rescue. The coherence
    pass, whose error preference is the opposite, uses topic_stems instead.
    """
    return {_norm(x) for x in title_word_stems(title)
            if _norm(x) not in GENERIC_STEMS and len(x) > 2
            and not _is_quantity(_norm(x))}


def topic_stems(title: str) -> set[str]:
    """Like specific_stems, but a hyphenated token also contributes its parts.

    For the coherence pass, where a false flag deletes real coverage: without
    this a Bloomberg headline almost word for word the cluster's own title
    ("Germany's Far Right Heads for Historic State Win" against a cluster
    titled "Germany's Far-Right AfD Poised for Historic State Election
    Victory") reads as off topic on a hyphen.
    """
    raw = set(title_word_stems(title))
    for part in re.split(r"[-\u2010-\u2015]", (title or "").lower()):
        raw |= title_word_stems(part)
    return {_norm(x) for x in raw if _norm(x) not in GENERIC_STEMS and len(x) > 2}


_PROPER = re.compile(r"\b[A-Z][a-zA-Z'’-]{2,}")


def title_anchors(title: str) -> set[str]:
    """Capitalized content stems in a headline.

    Worth being honest about what this can and cannot do: news headlines are
    title case, so capitalization does NOT identify proper nouns here. In
    "Rescuers Pull Two People Alive From Nepal Debris" every content word is
    capitalized. What makes an anchor an anchor is therefore not the capital
    letter but the three exclusions applied to it in should_merge: outlet
    mastheads, the generic same-day vocabulary, and the ambiguous words. This
    function supplies the pool; those filters do the work.
    """
    words = _PROPER.findall(title or "")
    out: set[str] = set()
    for w in words:
        for s in specific_stems(w):
            out.add(s)
    return out


def masthead_tokens(source_names: list[str]) -> set[str]:
    """Stems of the outlet names covering a cluster.

    The Pentagon pair's only shared entities were `new york` and `york`. An
    outlet name is evidence about who reported a story, never about what the
    story is, so it cannot anchor a merge.
    """
    out: set[str] = set()
    for name in source_names or []:
        out |= title_word_stems(name)
    return {_norm(s) for s in out}


def _bias_reaggregator():
    """main._enrich_cluster_fallback, resolved without importing main.

    `from main import ...` is wrong here. Under `python pipeline/main.py` the
    orchestrator is the module `__main__`, so importing `main` would load
    main.py a SECOND time under a different name and re-run its top level. Look
    it up in whichever module object is already loaded instead.

    Returns None when neither is present (a unit test importing this module on
    its own), and the caller then leaves the pre-merge bias in place rather
    than writing an average of two clusters, which is the one thing this pass
    must never do.
    """
    for name in ("main", "__main__"):
        mod = sys.modules.get(name)
        fn = getattr(mod, "_enrich_cluster_fallback", None)
        if callable(fn):
            return fn
    return None


def _parse_ts(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        s = str(value).replace("Z", "+00:00").replace(" ", "T", 1)
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def should_merge(a: dict, b: dict,
                 ambient: frozenset = frozenset()) -> tuple[bool, str]:
    """The gate, as a pure function of two cluster dicts.

    Each dict needs: title, first_published, and optionally entities (a set of
    salient entity strings) and mastheads (a set of outlet-name stems). Returns
    (merge, reason); `reason` names the branch on a pass and the FAILING
    conjunct on a reject, which is what the run log records for every rejected
    pair that shared a stem.

    `ambient` is the day's own vocabulary from ambient_stems, excluded from
    both the stem count and the anchor. It defaults to empty so a caller
    reasoning about one pair in isolation gets the unconditioned answer, but
    merge_candidates always supplies it: without the bench there is no way to
    tell an identifier from a word every third headline happens to use.
    """
    title_a, title_b = a.get("title") or "", b.get("title") or ""
    drop = ambient | MERGE_GENERIC_STEMS
    stems_a = specific_stems(title_a) - drop
    stems_b = specific_stems(title_b) - drop
    shared_stems = stems_a & stems_b
    signals = independent_signals(shared_stems, title_a, title_b)
    # Two independent signals, OR one signal plus two headlines that are
    # near-copies of each other. The three filters above are deliberately
    # blunt, and on a story covered by several fragments they can take away
    # the story's own vocabulary: the Indonesia quake was split three ways on
    # 2026-08-16, which pushed `earthquake` and `indonesia` to a document
    # frequency of 3 and marked them ambient, so "Indonesia Earthquake Kills
    # 51, Displaces Thousands on Flores Island" stopped matching "Indonesia
    # Magnitude 7.7 Earthquake Kills 51, Displaces Thousands on Flores".
    #
    # Raw headline overlap is independent of every filter above and separates
    # those cleanly. Measured over the 30-day replay, genuine duplicates the
    # filters had started to miss score 0.30 to 0.67; every pair that must
    # stay apart scores 0.07 to 0.23, the highest being an unrelated pair of
    # White House stories. The threshold sits above that ceiling with margin
    # rather than midway, because the cost of the two errors is not equal. One
    # known duplicate stays missed at 0.30 ("Trump Warns Data Center
    # Opposition Leads to Poverty"); that is the price of the margin.
    #
    # A surviving signal is still REQUIRED: similarity relaxes how much
    # specific evidence is needed, never whether any is needed.
    near = title_jaccard(title_a, title_b)
    enough = (len(signals) >= MERGE_MIN_SHARED_STEMS
              or (signals and near >= MERGE_NEAR_IDENTICAL_JACCARD))
    if not enough:
        collapsed = len(shared_stems) - len(signals)
        note = f", {collapsed} collapsed into a phrase" if collapsed else ""
        return False, (f"stems({len(signals)}<{MERGE_MIN_SHARED_STEMS}{note}, "
                       f"jaccard {near:.2f}<{MERGE_NEAR_IDENTICAL_JACCARD})")

    ts_a, ts_b = _parse_ts(a.get("first_published")), _parse_ts(b.get("first_published"))
    if ts_a and ts_b:
        hours = abs((ts_a - ts_b).total_seconds()) / 3600.0
        if hours > MERGE_TEMPORAL_HOURS:
            return False, f"temporal({hours:.0f}h>{MERGE_TEMPORAL_HOURS}h)"

    mast = (a.get("mastheads") or set()) | (b.get("mastheads") or set())
    anchors = ((title_anchors(a.get("title") or "") & title_anchors(b.get("title") or ""))
               | ({_norm(e) for e in (a.get("entities") or set())}
                  & {_norm(e) for e in (b.get("entities") or set())}))
    anchors = {x for x in anchors
               if x not in mast
               and x not in GENERIC_STEMS
               and x not in AMBIGUOUS_ANCHORS
               and x not in ambient
               and x not in MERGE_GENERIC_STEMS
               and not _is_quantity(x)}
    if not anchors:
        return False, ("anchor(none outside mastheads, ambiguous words, "
                       "quantities and the day's ambient vocabulary)")
    # The two shared stems have to include the anchor. Two clusters that agree
    # on WHAT happened but not on WHO or WHERE are two stories.
    if not (anchors & shared_stems):
        return False, f"anchor({sorted(anchors)[:2]}) not among shared stems"

    return True, f"anchor({sorted(anchors)[:2]})+stems({sorted(shared_stems)[:3]})"


# ---------------------------------------------------------------------------
# The pass
# ---------------------------------------------------------------------------

def merge_candidates(supabase, candidate_ids: list[str],
                     log_fn: Optional[Callable[[str], None]] = None) -> dict:
    """Merge same-event fragments among the bench. Returns metrics.

    Writes: the survivor absorbs the other's cluster_articles links, the
    absorbed row is deleted, source_count is recomputed from the union of
    DISTINCT sources (never a sum, which double-counts a source present in
    both), and the survivor's bias is re-aggregated from the merged article set
    by the pipeline's own enrichment path. The survivor keeps its own title,
    which is the higher-sourced one.

    Never raises: on any unexpected failure it logs and leaves the bench alone.
    """
    log = log_fn or (lambda m: print(m))
    metrics = {"merged": 0, "absorbed": [], "examined": 0, "rejected": 0}
    if len(candidate_ids) < 2:
        return metrics
    try:
        rows: dict[str, dict] = {}
        for i in range(0, len(candidate_ids), 100):
            res = supabase.table("story_clusters").select(
                "id,title,source_count,first_published,bias_diversity"
            ).in_("id", candidate_ids[i:i + 100]).execute()
            for r in (res.data or []):
                rows[r["id"]] = r
        order = [cid for cid in candidate_ids if cid in rows]
        if len(order) < 2:
            return metrics

        # Membership and outlet names, for the source recount and the masthead
        # exclusion. One read each, not one per pair.
        links: dict[str, list[str]] = {}
        for i in range(0, len(order), 100):
            res = supabase.table("cluster_articles").select(
                "cluster_id,article_id").in_("cluster_id", order[i:i + 100]).execute()
            for r in (res.data or []):
                links.setdefault(r["cluster_id"], []).append(r["article_id"])
        all_arts = sorted({a for ids in links.values() for a in ids})
        art_src: dict[str, str] = {}
        for i in range(0, len(all_arts), 200):
            res = supabase.table("articles").select("id,source_id").in_(
                "id", all_arts[i:i + 200]).execute()
            for a in (res.data or []):
                art_src[a["id"]] = a.get("source_id") or ""
        src_ids = sorted({v for v in art_src.values() if v})
        src_name: dict[str, str] = {}
        for i in range(0, len(src_ids), 200):
            res = supabase.table("sources").select("id,name").in_(
                "id", src_ids[i:i + 200]).execute()
            for s in (res.data or []):
                src_name[s["id"]] = s.get("name") or ""

        info: dict[str, dict] = {}
        for cid in order:
            aids = links.get(cid, [])
            srcs = {art_src.get(a, "") for a in aids} - {""}
            info[cid] = {
                "title": rows[cid].get("title") or "",
                "first_published": rows[cid].get("first_published"),
                "source_count": rows[cid].get("source_count") or 0,
                "articles": set(aids),
                "sources": srcs,
                "mastheads": masthead_tokens([src_name.get(s, "") for s in srcs]),
                "entities": set(),
            }

        # The bench's own vocabulary, measured once over the same headlines
        # the gate is about to compare. Computed BEFORE any merge so a merge
        # cannot change the denominator half way through the pass.
        ambient = ambient_stems([info[cid]["title"] for cid in order])
        if ambient:
            log(f"  [merge] ambient vocabulary ({len(order)} headlines, "
                f"df>={AMBIENT_MIN_DF}): {sorted(ambient)}")

        absorbed: set[str] = set()
        load: dict[str, int] = {cid: 1 for cid in order}
        for i, a in enumerate(order):
            if a in absorbed:
                continue
            for b in order[i + 1:]:
                if b in absorbed:
                    continue
                # Pairwise into the survivor only: no transitive chains, so a
                # merged cluster can never become the bridge between two
                # clusters that would never have merged with each other.
                if load[a] + 1 > MERGE_CEILING:
                    break
                ok, reason = should_merge(info[a], info[b], ambient=ambient)
                metrics["examined"] += 1
                if not ok:
                    # Only log a near miss: a pair with nothing in common is
                    # noise, a pair that shared a stem is a judgement call
                    # someone may want to review.
                    if reason.startswith("stems(0") or reason.startswith("stems(1"):
                        continue
                    metrics["rejected"] += 1
                    log(f"  [merge-reject] \"{info[a]['title'][:44]}\" vs "
                        f"\"{info[b]['title'][:44]}\": {reason}")
                    continue

                keep, drop = (a, b) if info[a]["source_count"] >= info[b]["source_count"] else (b, a)
                lean_k = (rows[keep].get("bias_diversity") or {}).get("avg_political_lean")
                lean_d = (rows[drop].get("bias_diversity") or {}).get("avg_political_lean")
                new_links = info[drop]["articles"] - info[keep]["articles"]
                try:
                    if new_links:
                        supabase.table("cluster_articles").upsert(
                            [{"cluster_id": keep, "article_id": aid}
                             for aid in sorted(new_links)],
                            on_conflict="cluster_id,article_id").execute()
                    supabase.table("cluster_articles").delete().eq(
                        "cluster_id", drop).execute()
                    merged_sources = info[keep]["sources"] | info[drop]["sources"]
                    supabase.table("story_clusters").update(
                        {
                            "source_count": len(merged_sources),
                            # The stored summary was written from HALF this
                            # story. Invalidate it the same way the coherence
                            # pass does, so the 8d.6 floor rewrites the card
                            # from the merged article set in THIS run rather
                            # than shipping a summary of one half under a
                            # headline now covering both.
                            "summary_tier": None,
                            "summary_article_hash": None,
                        }).eq("id", keep).execute()
                    supabase.table("story_clusters").delete().eq("id", drop).execute()
                except Exception as e:
                    log(f"  [warn][merge] write failed, pair skipped: {e}")
                    continue

                info[keep]["articles"] |= info[drop]["articles"]
                info[keep]["sources"] = merged_sources
                info[keep]["source_count"] = len(merged_sources)
                info[keep]["mastheads"] |= info[drop]["mastheads"]
                load[keep] += load[drop]
                absorbed.add(drop)
                metrics["merged"] += 1
                metrics["absorbed"].append(drop)
                log(f"  [merge] survivor summary invalidated; the floor will "
                    f"rewrite it from {len(info[keep]['articles'] | info[drop]['articles'])} "
                    f"merged articles")
                log(f"  [merge] KEEP[{rows[keep].get('source_count')}src lean={lean_k}] "
                    f"\"{info[keep]['title'][:44]}\" <- "
                    f"ABSORB[{rows[drop].get('source_count')}src lean={lean_d}] "
                    f"\"{info[drop]['title'][:44]}\" -> {len(merged_sources)} sources, "
                    f"{reason}")

        if absorbed:
            # Bias from the MERGED set, computed by the pipeline's own
            # aggregation. Never (55 + 42) / 2.
            enrich = _bias_reaggregator()
            for cid in {c for c in order if c not in absorbed and load[c] > 1}:
                if enrich is None:
                    log("  [warn][merge] bias re-aggregation unavailable; the "
                        "survivor keeps the pre-merge numbers until the next run")
                    break
                try:
                    enrich(cid, skip_text=False)
                    log(f"  [merge] re-aggregated bias for {cid[:8]} "
                        f"from {len(info[cid]['articles'])} merged articles")
                except Exception as e:
                    log(f"  [warn][merge] bias re-aggregation failed for {cid[:8]}: {e}")

        # Canary, not a gate. A semicolon joining two subjects is a symptom of
        # exactly this pass going wrong, and the CEO asked whether it could be
        # flagged automatically. As a general rule it cannot: 94 of the 1,377
        # printed headlines carry a semicolon and splitting them on it flags 85,
        # because "development; consequence" is ordinary headline grammar
        # ("Russia Resumes Kyiv Strikes After US Envoys Visit; Talks Possible").
        # Rev 65 measured that and rejected it, and it still measures the same.
        #
        # Narrowed to survivors THIS pass just merged, the set is a handful a
        # day and every hit is worth a human glance, so it is logged and
        # nothing more. It costs one string scan and it is how the next
        # unforeseen contamination path announces itself.
        for cid in {c for c in order if c not in absorbed and load[c] > 1}:
            if ";" in (info[cid].get("title") or ""):
                log(f"  [merge][audit] survivor {cid[:8]} carries a semicolon "
                    f"headline after absorbing {load[cid] - 1}: "
                    f"\"{info[cid]['title'][:70]}\". Check that the two "
                    f"halves are one story")
        return metrics
    except Exception as e:
        log(f"  [warn][merge] pass skipped ({type(e).__name__}: {e})")
        return metrics


# ---------------------------------------------------------------------------
# Step 8c.7: candidate coherence
# ---------------------------------------------------------------------------
# Merging does not fix a contaminated cluster; it makes a bigger one. On
# 2026-09-06 the feed carried "Russia Loads First Crude Oil on Arctic Tanker"
# whose 6 members were 2 stories about the tanker and 4 about a NATO exercise,
# EU energy policy, an Arctic power struggle and sea-ice observation, joined by
# the single word "Arctic"; "Trump Threatens Iran's Pickaxe Mountain" carried a
# member titled "Morning recap"; and a local paper's whole Saturday output rode
# in on one BYU football card.
#
# The measure is the cluster's OWN modal vocabulary, not its title. Comparing
# each member to the title reads a differently-worded report of the same event
# as off topic: four members of the Putin ceasefire cluster say "Putin orders
# three-day halt to strikes on Kiev" where the title says "Suspends Kyiv
# Strikes for 72 Hours", and a title-based rule flags all four. Modal
# vocabulary (stems in at least MODAL_MIN of member headlines, minus the broad
# geographic terms that join anything) keeps them and still catches the tanker.
#
# topic_coherence is not used and never should be: it scores any shared word as
# on topic and reported 1.00 on the Assam cluster at a true precision of 0.25.

MODAL_MIN = 0.30          # a stem is modal at this share of member headlines
MODAL_MIN_STEMS = 3       # below this the cluster has no vocabulary to judge by.
                          # Three, not two: the 25-member Ukraine wire bag
                          # spanning Mykolaiv, Kherson, Dnipropetrovsk and
                          # Donetsk has a modal vocabulary of exactly {forces,
                          # region}, and trimming 8 of its members would pick an
                          # arbitrary half of a cluster that has no core at all.
                          # That is a clustering defect; this pass abstains.

# Regions and nationalities broad enough to join unrelated events. Kept small
# and geographic ON PURPOSE: an earlier draft also listed the topic words
# (strike, election, price, politics) and that flagged the Putin ceasefire
# reports, the AfD election coverage and two on-topic fuel-price stories.
BROAD_GEOGRAPHY = frozenset("""
arctic africa asia europ american usa uk british britain china chines
russia russian iran iranian israel israeli india indian pakistan japan japanes
korea german germani franc french spain spanish itali ukrain ukrainian
nato eu turkey turkish brazil mexico canada australia middl east west
""".split())


def modal_vocabulary(member_titles: list[str]) -> set[str]:
    """Stems carried by at least MODAL_MIN of the member headlines."""
    if not member_titles:
        return set()
    counts: dict[str, int] = {}
    for t in member_titles:
        for s in topic_stems(t):
            counts[s] = counts.get(s, 0) + 1
    n = len(member_titles)
    return {s for s, k in counts.items()
            if k / n >= MODAL_MIN and s not in BROAD_GEOGRAPHY}


def incoherent_members(member_titles: list[str],
                       cluster_title: str = "") -> tuple[list[int], set[str]]:
    """Indices of members foreign to the cluster, plus the modal vocabulary.

    TWO independent signals must agree before a member is removed: it shares no
    modal stem AND no stem with the cluster's own headline. Deleting an article
    destroys coverage, so one signal is not enough to justify it.

    That second signal exists because of what the first one does on a BIG
    cluster. modal_vocabulary keeps stems carried by MODAL_MIN of the headlines,
    and a large cluster covering one event from many angles has enormous
    phrasing diversity, so almost no stem clears the share. Measured on the
    2026-09-09 production feed:

        rank 1   62 members, 57 sources -> modal vocabulary of 3 stems
                 {destroy, oil, tanker}
        rank 7   75 members, 58 sources -> 3 stems {arabia, houthi, saudi}
        rank 2   73 members, 61 sources -> 6 stems

    The vocabulary SHRINKS as the cluster grows, so the biggest and most
    important stories are judged against the weakest possible test, and any
    legitimate report phrased differently is deleted. That run removed 55
    members across 17 clusters; 17 of the 55 were the same story in different
    words, including "War in the Middle East: Iran attacks US base in Jordan"
    dropped from the Iran strike cluster and "Trump hails 'really big night' for
    populists in German elections" dropped from a cluster titled "Trump hails
    AfD win in Germany's Saxony-Anhalt".

    The cluster headline does not shrink with size, so it catches exactly those.
    Re-running the same 55 removals with this guard keeps all 17 and still
    removes all 38 genuine ones, including "Makinde: Blockade of Obi's convoy"
    from the Iran cluster and a college football recap from a plane crash.

    The failure directions are not symmetric, which is why the guard is
    conjunctive rather than a tuned threshold: keeping a marginal member costs a
    slightly noisier Deep Dive roster, deleting a real one destroys journalism
    and understates source_count on the story that most deserves it.

    Returns ([], vocabulary) when the cluster has fewer than MODAL_MIN_STEMS
    modal stems: with no vocabulary of its own there is nothing to be off topic
    against, and guessing there would delete real coverage.
    """
    vocab = modal_vocabulary(member_titles)
    if len(vocab) < MODAL_MIN_STEMS:
        return [], vocab
    head = topic_stems(cluster_title) if cluster_title else set()
    return [i for i, t in enumerate(member_titles)
            if not (topic_stems(t) & vocab) and not (topic_stems(t) & head)], vocab


MIN_MEMBERS_TO_TRIM = 6   # below this one removal is a large share of a small
                          # cluster, and the borderline calls (a wire stub with
                          # a generic headline) cost more than they fix.


def split_incoherent_candidates(supabase, candidate_ids: list[str],
                                log_fn: Optional[Callable[[str], None]] = None) -> dict:
    """Step 8c.7: remove members that share no vocabulary with their cluster.

    A trimmed cluster has its source_count recomputed from the DISTINCT sources
    that remain, its bias re-aggregated over the cleaned membership, and its
    summary cache INVALIDATED, so step 8d rewrites the headline and summary from
    what the cluster actually contains rather than serving yesterday's text
    about a membership that no longer exists.

    A removed article is only unlinked, never deleted. It stays in the 36-hour
    window and is re-clustered on the next run.

    Reports, but does not trim, when the cluster is small or when more than half
    its members are off vocabulary: at that point there is no core to keep and
    trimming would choose an arbitrary half.
    """
    log = log_fn or (lambda m: print(m))
    metrics = {"trimmed": 0, "removed": 0, "reported": 0, "abstained": 0}
    if not candidate_ids:
        return metrics
    try:
        links: dict[str, list[str]] = {}
        for i in range(0, len(candidate_ids), 100):
            res = supabase.table("cluster_articles").select(
                "cluster_id,article_id").in_(
                "cluster_id", candidate_ids[i:i + 100]).execute()
            for r in (res.data or []):
                links.setdefault(r["cluster_id"], []).append(r["article_id"])
        all_ids = sorted({a for v in links.values() for a in v})
        arts: dict[str, dict] = {}
        for i in range(0, len(all_ids), 200):
            res = supabase.table("articles").select("id,title,source_id").in_(
                "id", all_ids[i:i + 200]).execute()
            for a in (res.data or []):
                arts[a["id"]] = a
        titles_by_cluster: dict[str, dict] = {}
        for i in range(0, len(candidate_ids), 100):
            res = supabase.table("story_clusters").select("id,title").in_(
                "id", candidate_ids[i:i + 100]).execute()
            for r in (res.data or []):
                titles_by_cluster[r["id"]] = r.get("title") or ""

        for cid in candidate_ids:
            aids = [a for a in links.get(cid, []) if a in arts]
            if len(aids) < 3:
                continue
            member_titles = [arts[a].get("title") or "" for a in aids]
            idx, vocab = incoherent_members(
                member_titles, titles_by_cluster.get(cid, ""))
            if len(vocab) < MODAL_MIN_STEMS:
                metrics["abstained"] += 1
                continue
            if not idx:
                continue
            head = titles_by_cluster.get(cid, "")[:44]
            if len(aids) < MIN_MEMBERS_TO_TRIM or len(idx) * 2 > len(aids):
                metrics["reported"] += 1
                log(f"  [coherence-report] \"{head}\": {len(idx)} of {len(aids)} "
                    f"members share none of {sorted(vocab)[:4]}, not trimmed "
                    f"({'too small' if len(aids) < MIN_MEMBERS_TO_TRIM else 'no core'})")
                continue

            drop = [aids[i] for i in idx]
            try:
                for aid in drop:
                    supabase.table("cluster_articles").delete().eq(
                        "cluster_id", cid).eq("article_id", aid).execute()
                keep = [a for a in aids if a not in set(drop)]
                srcs = {arts[a].get("source_id") for a in keep} - {None, ""}
                supabase.table("story_clusters").update({
                    "source_count": len(srcs),
                    # The stored summary was written from the contaminated
                    # membership. Clearing the cache key and the tier makes 8d
                    # treat this as a miss and rewrite the card.
                    "summary_tier": None,
                    "summary_article_hash": None,
                }).eq("id", cid).execute()
            except Exception as e:
                log(f"  [warn][coherence] write failed for {cid[:8]}: {e}")
                continue
            metrics["trimmed"] += 1
            metrics["removed"] += len(drop)
            for i in idx:
                log(f"  [coherence] \"{head}\" -> removed "
                    f"\"{member_titles[i][:58]}\"")
            log(f"  [coherence] \"{head}\": {len(keep)} members, "
                f"{len(srcs)} sources, summary invalidated")
            try:
                enrich = _bias_reaggregator()
                if enrich is not None:
                    enrich(cid, skip_text=False)
            except Exception as e:
                log(f"  [warn][coherence] bias re-aggregation failed for {cid[:8]}: {e}")
        return metrics
    except Exception as e:
        log(f"  [warn][coherence] pass skipped ({type(e).__name__}: {e})")
        return metrics
