"""The Weekly's source check: a second model reads every sentence against the week.

WHY. CLAUDE.md Rule 1: every factual claim traces to a source in the data, and
a claim that cannot be sourced is cut, not softened. The Weekly's writers are
handed only the week's printed stories and every prompt carries the grounding
line, and they reached past them anyway. A sentence-level audit on 2026-10-01
found about eleven unsourced claims in the generated Issue #27 (the JCPOA
withdrawal as background to the Hormuz standoff, "a substantial portion of the
world's seaborne oil", an editorial line saying the Xi talks "avoided the
broader issues" when the printed stories list Taiwan, Iran and Ukraine among
them) and seventeen in the published Issue #26's Greenland cover (a paragraph
of Arctic geopolitics, a World War II history, Thule Air Base, "a treaty
established in the 1950s"). `weekly_parse.ground_text` catches only those that
carry an unsourced number or multi-word name: one of the eleven.

HOW. The daily feed already answers this with a critique pass on flash-lite
(`cluster_summarizer.critique_cards`). This is the Weekly's: each piece is split
into numbered sentences, handed to flash-lite with its evidence, and the model
names the sentences that state a fact the sources do not support or
contradict. Code cuts those sentences; the model never rewrites anything.

FAILS CLOSED. A piece the check could not read is not shipped. The daily
critique treats an unread card as clean because a missing card empties the
front page; the Weekly's floor (`generate_weekly_digest`) already handles a
missing section honestly, and an unchecked essay is exactly what shipped in
Issue #26.

EVIDENCE PER PIECE, NOT THE WHOLE WEEK (2026-10-03). The first version handed
every call the whole printed week: 134 stories, 407,306 characters, about
100,000 tokens, for a three-sentence brief whose evidence was one row of about
2,000 characters inside it. On the Issue #27 run (weekly-digest run
37105730672) the model marked 10 of 10 recap items wholly unsupported, both
covers (27 of 34 and 36 of 36 sentences) and two of five columns, while every
fact it named was in the prompt ("Noreen Niazi", "355 of the 450", "Jabalia",
"Trump TV" all present, 86%, 87%, 19% and 63% of the way in). It had not been
denied the evidence; it had been buried in it, and its "claims" were the
sentences restated in order rather than facts looked up. `select_evidence`
gives each piece its OWN printed rows (the story it was written from, and that
story's thread) plus the rows sharing its rarest words, under
`SOURCE_BUDGET_CHARS`.

NUMBERS ARE VERIFIED, NOT TRUSTED. The model echoes the first words of each
sentence it names (`starts`), and code places a verdict only where those words
open a numbered sentence. A verdict that opens none is cut nowhere: its text
counts as unread, and an unread text does not ship. On the same run the
claim "one shooting near Johannesburg, killing 17" cut the Cape Town sentence
and "arrested four farmers" cut the Qatari Prime Minister's: the model had
numbered claims, not sentences, and code cut by the number.

A CHECKER ERROR IS NOT A FINDING. A piece whose own printed story is absent
from its evidence, or a call with no evidence at all, is logged as a checker
error and does not ship, rather than being reported as unsupported claims.

Pure core (`number_sentences`, `rebuild`, `parse_verdict`, `place_verdict`,
`select_evidence`) needs no key and is tested in tests/test_weekly.py (W-T21,
W-T21b).
"""

from __future__ import annotations

import json
import math
import re

from briefing.weekly_parse import split_sentences

#: Characters of printed stories one check call may carry (about 15k tokens).
#: A piece's own rows always go in, even past this; related rows fill the rest.
SOURCE_BUDGET_CHARS = 60_000
#: Related rows (beyond its own) each text may pull in.
RELATED_ROWS_PER_TEXT = 6

SOURCE_CHECK_SYSTEM = """You are the fact checker for a news magazine. You are given SOURCES (the only \
material the writer was allowed to use) and a TEXT split into numbered sentences, each written \
as [n] followed by the sentence.

For each sentence decide: does it state any fact that the SOURCES do not support, or that the \
SOURCES contradict? A fact is a name, number, date, day of the week, quotation, event, cause, \
historical or background claim, or a description of what happened or did not happen. \
Paraphrase of the SOURCES is supported. A sentence that only argues, frames, or asks a \
question, adding no new fact, is supported. A quotation must appear in the SOURCES as a \
quotation. General knowledge, however well known, is NOT a source. Before you list a sentence, \
search the SOURCES for its facts; list it only when the SOURCES do not hold one of them.

List each unsupported sentence ONCE, under the number in its brackets, never one entry per \
fact. "starts" is the first five words of that sentence, copied exactly as written after its [n].

Return JSON only: {"unsupported": [{"n": <sentence number>, "starts": "<first five words>", \
"claim": "<the unsupported fact, under 15 words>"}]}. Return {"unsupported": []} when every \
sentence is supported."""


def number_sentences(text: str) -> list[list[str]]:
    """The text as paragraphs of sentences, in order (`weekly_parse.split_sentences`)."""
    out = []
    for para in (text or "").split("\n\n"):
        sents = split_sentences(para)
        if sents:
            out.append(sents)
    return out


def numbered_text(paras: list[list[str]]) -> str:
    lines, n = [], 0
    for para in paras:
        for s in para:
            n += 1
            lines.append(f"[{n}] {s}")
    return "\n".join(lines)


def parse_verdict(result) -> list[dict] | None:
    """[{"n", "starts", "claim"}] from the model's JSON, or None if unreadable.

    `n` is whatever the model said (0 when it said nothing usable); it is
    never cut by on its own, see `place_verdict`.
    """
    if not isinstance(result, dict) or not isinstance(result.get("unsupported"), list):
        return None
    out = []
    for item in result["unsupported"]:
        if not isinstance(item, dict):
            continue
        try:
            n = int(item.get("n"))
        except (TypeError, ValueError):
            n = 0
        out.append({"n": n, "starts": str(item.get("starts") or "")[:200],
                    "claim": str(item.get("claim") or "")[:200]})
    return out


def _words(s):
    return re.findall(r"[a-z0-9]+", (s or "").lower().replace("’", "").replace("'", ""))


def opens(sentence: str, echo: str) -> bool:
    """True when the echoed words open `sentence`: at least three, or all it has."""
    e, w = _words(echo), _words(sentence)
    if not e or not w:
        return False
    k = min(len(e), 5)
    if k < min(3, len(w)):
        return False
    return w[:k] == e[:k]


def place_verdict(verdict: list[dict], flat: list[str], owner: list[int]):
    """({sentence number: verdict item}, [unplaced items]).

    An item is placed on its own number when its `starts` opens that
    sentence; otherwise on the ONE sentence its `starts` opens, looked for
    first in the same text, then in the batch. An item whose words open no
    sentence, or more than one, is unplaced: it is never cut by number alone.
    """
    cut, unplaced = {}, []
    total = len(flat)
    for item in verdict:
        n, echo = item["n"], item["starts"]
        if 1 <= n <= total and opens(flat[n - 1], echo):
            cut[n] = item
            continue
        hits = []
        if 1 <= n <= total:
            hits = [k for k in range(1, total + 1)
                    if owner[k - 1] == owner[n - 1] and opens(flat[k - 1], echo)]
        if not hits:
            hits = [k for k in range(1, total + 1) if opens(flat[k - 1], echo)]
        if len(hits) == 1:
            cut[hits[0]] = dict(item, realigned_from=n)
        else:
            unplaced.append(item)
    return cut, unplaced


def rebuild(paras: list[list[str]], cut: set[int]) -> str:
    """The text without the cut sentences; an emptied paragraph is dropped."""
    out, n = [], 0
    for para in paras:
        kept = []
        for s in para:
            n += 1
            if n not in cut:
                kept.append(s)
        if kept:
            out.append(" ".join(kept))
    return "\n\n".join(out)


def _checker_error(errors, where, why):
    print(f"    [source-check] CHECKER ERROR {where}: {why}; it does not ship")
    if errors is not None:
        errors.append((where, why))


def check_texts(texts: list[str], sources: str, generate_json_fn, *, label: str = "piece",
                max_cut_share: float = 0.5, missing=None, errors=None):
    """Check several texts in ONE request; return ([checked_text or None], cuts).

    Sentences are numbered continuously across the texts, so a ten-item recap
    costs one call. A text comes back None when it does not ship:

      * the check could not run (every text is None then);
      * a CHECKER ERROR: the call had no sources, or `missing[i]` says text
        i's own printed story was absent from them. Logged as such and
        appended to `errors` (a list, if given), never reported as claims,
        and the text is not sent;
      * the model named a sentence in it that `place_verdict` could not
        place, after one retry: an unread text;
      * more than `max_cut_share` of its sentences were unsupported, which
        leaves fragments, not prose.
    """
    names = [label if len(texts) == 1 else f"{label} {i + 1}" for i in range(len(texts))]
    missing = list(missing) if missing is not None else [False] * len(texts)
    live = [bool((t or "").strip()) for t in texts]
    if not (sources or "").strip():
        for i in range(len(texts)):
            if live[i]:
                _checker_error(errors, names[i], "the check was given no sources")
        return [None if live[i] else t for i, t in enumerate(texts)], []
    out = list(texts)
    for i in range(len(texts)):
        if live[i] and missing[i]:
            _checker_error(errors, names[i], "its own printed story is not in the evidence")
            out[i] = None
    send = [i for i in range(len(texts)) if live[i] and not missing[i]]
    per = {i: number_sentences(texts[i]) for i in send}
    flat, owner = [], []
    for i in send:
        for para in per[i]:
            for sent in para:
                flat.append(sent)
                owner.append(i)
    if not flat:
        return out, []
    lines, cur = [], None
    for n, (sent, i) in enumerate(zip(flat, owner), 1):
        if len(send) > 1 and i != cur:
            lines.append(f"--- TEXT {send.index(i) + 1} ---")
            cur = i
        lines.append(f"[{n}] {sent}")
    prompt = f"SOURCES:\n{sources}\n\nTEXT:\n" + "\n".join(lines)
    total = len(flat)
    placed, unplaced = None, []
    for _ in range(2):
        verdict = parse_verdict(
            generate_json_fn(prompt, system_instruction=SOURCE_CHECK_SYSTEM,
                             max_output_tokens=4096))
        if verdict is None:
            continue
        placed, unplaced = place_verdict(verdict, flat, owner)
        if not unplaced:
            break
    if placed is None:
        print(f"    [source-check] {label}: check could not run; nothing here ships")
        return [None] * len(texts), []
    unread = set()
    for item in unplaced:
        n = item["n"]
        unread.update([owner[n - 1]] if 1 <= n <= total else send)
        print(f"    [source-check] {label}: verdict [{n}] starting {item['starts'][:40]!r} opens no "
              f"numbered sentence; read as unread ({item['claim'][:80]})")
    cuts, start = [], 0
    for i in send:
        count = sum(len(p) for p in per[i])
        mine = {k - start for k in placed if start < k <= start + count}
        sents = flat[start:start + count]
        for k in sorted(mine):
            item = placed[k + start]
            moved = f" [model said {item['realigned_from']}]" if "realigned_from" in item else ""
            cuts.append((names[i], sents[k - 1], item["claim"]))
            print(f"    [source-check] {names[i]}: cut ({item['claim']}){moved}: {sents[k - 1][:110]}")
        if i in unread:
            print(f"    [source-check] {names[i]}: a verdict could not be placed; it does not ship")
            out[i] = None
        elif count and len(mine) > count * max_cut_share:
            print(f"    [source-check] {names[i]}: {len(mine)} of {count} sentences "
                  f"unsupported; it does not ship")
            out[i] = None
        else:
            out[i] = rebuild(per[i], mine)
        start += count
    return out, cuts


def check_piece(text: str, sources: str, generate_json_fn, *, label: str = "piece",
                max_cut_share: float = 0.5, missing: bool = False, errors=None):
    """One text: (checked_text or None, cuts)."""
    out, cuts = check_texts([text], sources, generate_json_fn, label=label,
                            max_cut_share=max_cut_share, missing=[missing], errors=errors)
    return out[0], cuts


def _row_block(r: dict) -> str:
    parts = [f"TITLE: {r.get('title') or ''}"]
    if r.get("printed_on"):
        parts.append(f"PRINTED: {r['printed_on']}")
    if r.get("source_count"):
        parts.append(f"SOURCES COUNTED: {r['source_count']}")
    parts.append(f"SUMMARY: {r.get('summary') or ''}")
    for k in ("consensus_points", "divergence_points"):
        v = r.get(k)
        if v:
            parts.append(f"{k.split('_')[0].upper()}: "
                         + (v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)))
    return "\n".join(parts)


def source_text(rows: list[dict]) -> str:
    """Printed stories, as the checker reads them."""
    return "\n\n".join(_row_block(r) for r in rows)


_STOP = frozenset("""about after again against also among around because been before being between
both could during each from have having into more most other over same since some such than that
their them then there these they this those through under until very were what when where which
while will with would said says week""".split())


def _terms(text):
    t = (text or "").replace("’", "'")
    words = {w for w in re.findall(r"[a-z][a-z'-]{3,}", t.lower()) if w not in _STOP}
    nums = {n.replace(",", "") for n in re.findall(r"\d[\d,.]*\d|\d{2,}", t)}
    return words | nums


def _has_text(r):
    return isinstance(r.get("summary"), str) and bool(r["summary"].strip())


def select_evidence(texts: list[str], pool: list[dict], anchors=None, *,
                    budget: int = SOURCE_BUDGET_CHARS, per_text: int = RELATED_ROWS_PER_TEXT):
    """(rows, missing): the printed rows the check of `texts` reads.

    `anchors[i]` holds the ids of the story (or stories) text i was written
    from. Every pool row with one of those ids, and every row of the same
    story thread, goes in first and in full, whatever the budget. Then, per
    text, the rows sharing its rarest words (idf-weighted overlap), taken
    round robin across the texts so a ten-item recap does not spend the
    budget on its first item, until `budget` characters.

    `missing[i]` is True when text i named anchors and not one is in the pool
    with a summary: its own story is absent, so a verdict on it would be a
    verdict against the wrong evidence.
    """
    anchors = list(anchors) if anchors is not None else [()] * len(texts)
    rows = [r for r in pool if _has_text(r)]
    by_id, by_thread = {}, {}
    for r in rows:
        by_id.setdefault(r.get("id"), []).append(r)
        if r.get("story_thread_id"):
            by_thread.setdefault(r["story_thread_id"], []).append(r)
    picked, seen = [], set()
    size = 0

    def take(r):
        nonlocal size
        if id(r) not in seen:
            seen.add(id(r))
            picked.append(r)
            size += len(_row_block(r)) + 2

    missing = []
    for ids in anchors:
        ids = [x for x in (ids or ()) if x]
        own = [r for x in ids for r in by_id.get(x, [])]
        threads = {r.get("story_thread_id") for r in own if r.get("story_thread_id")}
        own += [r for t in sorted(threads, key=str) for r in by_thread.get(t, [])]
        missing.append(bool(ids) and not own)
        for r in own:
            take(r)
    docs = [_terms(f"{r.get('title') or ''} {r.get('summary') or ''}") for r in rows]
    df: dict[str, int] = {}
    for d in docs:
        for w in d:
            df[w] = df.get(w, 0) + 1
    big_n = max(len(rows), 1)
    ranked = []
    for t in texts:
        tt = _terms(t)
        scored = []
        for j, (r, d) in enumerate(zip(rows, docs)):
            shared = tt & d
            if len(shared) < 2:
                continue
            scored.append((sum(math.log((big_n + 1) / (df[w] + 0.5)) for w in shared), j))
        scored.sort(key=lambda x: (-x[0], x[1]))
        ranked.append([rows[j] for _, j in scored[:per_text]])
    for k in range(per_text):
        for lst in ranked:
            if k < len(lst) and size + len(_row_block(lst[k])) <= budget:
                take(lst[k])
    return picked, missing
