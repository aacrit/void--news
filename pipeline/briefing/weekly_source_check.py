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
into numbered sentences, handed to flash-lite with the week's source text, and
the model names the sentences that state a fact the sources do not support or
contradict. Code cuts those sentences; the model never rewrites anything.

FAILS CLOSED. A piece the check could not read is not shipped. The daily
critique treats an unread card as clean because a missing card empties the
front page; the Weekly's floor (`generate_weekly_digest`) already handles a
missing section honestly, and an unchecked essay is exactly what shipped in
Issue #26.

Pure core (`number_sentences`, `rebuild`, `parse_verdict`) needs no key and is
tested in tests/test_weekly.py (W-T21).
"""

from __future__ import annotations

from briefing.weekly_parse import _G_SENT_RE

SOURCE_CHECK_SYSTEM = """You are the fact checker for a news magazine. You are given SOURCES (the only \
material the writer was allowed to use) and a TEXT split into numbered sentences.

For each sentence decide: does it state any fact that the SOURCES do not support, or that the \
SOURCES contradict? A fact is a name, number, date, day of the week, quotation, event, cause, \
historical or background claim, or a description of what happened or did not happen. \
Paraphrase of the SOURCES is supported. A sentence that only argues, frames, or asks a \
question, adding no new fact, is supported. A quotation must appear in the SOURCES as a \
quotation. General knowledge, however well known, is NOT a source.

Return JSON only: {"unsupported": [{"n": <sentence number>, "claim": "<the unsupported fact, \
under 15 words>"}]}. Return {"unsupported": []} when every sentence is supported."""


def number_sentences(text: str) -> list[list[str]]:
    """The text as paragraphs of sentences, in order."""
    out = []
    for para in (text or "").split("\n\n"):
        sents = [s for s in _G_SENT_RE.split(para.strip()) if s.strip()]
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


def parse_verdict(result, total: int) -> dict[int, str] | None:
    """{sentence_number: claim} from the model's JSON, or None if unreadable."""
    if not isinstance(result, dict) or not isinstance(result.get("unsupported"), list):
        return None
    out = {}
    for item in result["unsupported"]:
        if not isinstance(item, dict):
            continue
        try:
            n = int(item.get("n"))
        except (TypeError, ValueError):
            continue
        if 1 <= n <= total:
            out[n] = str(item.get("claim") or "")[:200]
    return out


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


def check_texts(texts: list[str], sources: str, generate_json_fn, *, label: str = "piece",
                max_cut_share: float = 0.5):
    """Check several texts in ONE request; return ([checked_text or None], cuts).

    Sentences are numbered continuously across the texts, so a ten-item recap
    costs one call. A text comes back None when it does not ship: the check
    could not run (every text is None then), or more than `max_cut_share` of
    its sentences were unsupported, which leaves fragments, not prose.
    """
    per = [number_sentences(t) for t in texts]
    total = sum(len(p) for paras in per for p in paras)
    if not total:
        return list(texts), []
    lines, n = [], 0
    for i, paras in enumerate(per):
        if len(texts) > 1:
            lines.append(f"--- TEXT {i + 1} ---")
        for para in paras:
            for sent in para:
                n += 1
                lines.append(f"[{n}] {sent}")
    prompt = f"SOURCES:\n{sources}\n\nTEXT:\n" + "\n".join(lines)
    verdict = None
    for _ in range(2):
        verdict = parse_verdict(
            generate_json_fn(prompt, system_instruction=SOURCE_CHECK_SYSTEM,
                             max_output_tokens=4096),
            total,
        )
        if verdict is not None:
            break
    if verdict is None:
        print(f"    [source-check] {label}: check could not run; nothing here ships")
        return [None] * len(texts), []
    out, cuts, start = [], [], 0
    for i, paras in enumerate(per):
        count = sum(len(p) for p in paras)
        flat = [x for p in paras for x in p]
        mine = {k - start for k in verdict if start < k <= start + count}
        for k in sorted(mine):
            cuts.append((label if len(texts) == 1 else f"{label} {i + 1}", flat[k - 1], verdict[k + start]))
            print(f"    [source-check] {cuts[-1][0]}: cut ({verdict[k + start]}): {flat[k - 1][:110]}")
        if count and len(mine) > count * max_cut_share:
            print(f"    [source-check] {label} {i + 1}: {len(mine)} of {count} sentences "
                  f"unsupported; it does not ship")
            out.append(None)
        else:
            out.append(rebuild(paras, mine))
        start += count
    return out, cuts


def check_piece(text: str, sources: str, generate_json_fn, *, label: str = "piece",
                max_cut_share: float = 0.5):
    """One text: (checked_text or None, cuts)."""
    out, cuts = check_texts([text], sources, generate_json_fn, label=label,
                            max_cut_share=max_cut_share)
    return out[0], cuts


def source_text(rows: list[dict]) -> str:
    """The week's printed stories, as the checker reads them."""
    import json
    blocks = []
    for r in rows:
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
        blocks.append("\n".join(parts))
    return "\n\n".join(blocks)
