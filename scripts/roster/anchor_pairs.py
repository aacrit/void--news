#!/usr/bin/env python3
"""Collect same-story cross-language article pairs from multilingual newsrooms.

WHY THIS EXISTS. If outlet baselines are ever derived per market with a
per-language lexicon, the resulting numbers are NOT automatically on one scale:
a French lexicon's "one standard deviation right" is not an English lexicon's.
Something has to bridge the two spaces.

The bridge is a newsroom that publishes the SAME journalism in two languages.
Deutsche Welle, France 24, Euronews and RFI all do. Score DW's German with the
German lexicon and DW's English with the English one, and the systematic gap
between the two IS the transform between the spaces. Fit that across several
anchors and you have a per-language offset and scale, derived from data rather
than assumed.

It also carries a falsification test worth more than the calibration: if the
two halves of an anchor pair do NOT converge after calibration, then a single
global lean scale is not defensible and Void should publish lean as a
within-market quantity and say so. Note that the current English-only product
already makes the cross-market claim implicitly, so this test is overdue
regardless of whether the multilingual work ever happens.

WHAT IT DOES NOT DO. It does not score anything. There is no French lexicon
yet, and `pipeline/utils/nlp_shared.py` loads `en_core_web_sm` unconditionally,
so scoring is English-only today. This collects the corpus the calibration will
need, which is the part that takes calendar time rather than cleverness.

MEASURED, 2026-09-22, against live feeds: at a loose threshold pairs are
recoverable for roughly 62 to 80 percent of the smaller feed (Euronews 80%,
DW 78%, RFI 67%, France 24 62%). DW gives each language its own /a-NNNNNNN
article id, so matching is semantic, not by id.

PRECISION IS THE RISK, NOT RECALL, because the calibration needs only a few
hundred clean pairs and a strict threshold is therefore free. Precision was
measured by hand over every pair of one run, 2026-09-22:

    score >= 4    ~137 pairs   62-80% of the smaller feed, precision not measured
    score >= 14      21 pairs   17 clearly correct, about 81% precision
    score >= 18      11 pairs   11 of 11 correct, 100% on this sample

Every failure between 14 and 17 had the same shape: shared topic, different
subject. RFI paired "Macron to meet Trump ahead of UN General Assembly" with a
Zelensky story because both mention the Assembly; DW paired "US-China rivalry
is reshaping global trade" with a piece about the Xi-Trump summit. Related, not
the same article. Topic overlap is not subject identity.

So MIN_SCORE defaults to 18. At roughly 11 pairs per run against four
newsrooms, and feeds that refresh through the day, a few hundred verified pairs
is weeks of ordinary collection rather than a project. Every pair is written
with its score, so the bar can be raised further or the file spot-checked from
the top.

    python3 scripts/roster/anchor_pairs.py            collect and print a summary
    python3 scripts/roster/anchor_pairs.py --out FILE write pairs as JSON
"""
from __future__ import annotations
import json, re, sys, unicodedata
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

# newsroom -> {language: feed}. Same newsroom, same stories, different language.
ANCHORS = {
    "Deutsche Welle": {"en": "https://rss.dw.com/rdf/rss-en-all",
                       "de": "https://rss.dw.com/rdf/rss-de-all"},
    "France 24":      {"en": "https://www.france24.com/en/rss",
                       "fr": "https://www.france24.com/fr/rss",
                       "es": "https://www.france24.com/es/rss"},
    "Euronews":       {"en": "https://www.euronews.com/rss?level=theme&name=news",
                       "fr": "https://fr.euronews.com/rss?level=theme&name=news"},
    "RFI":            {"en": "https://www.rfi.fr/en/rss",
                       "fr": "https://www.rfi.fr/fr/rss"},
}

# Deliberately strict: see PRECISION IS THE RISK above.
MIN_SCORE = 18

_S = requests.Session()
_S.headers["User-Agent"] = UA


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def fetch(url: str) -> list[dict]:
    r = _S.get(url, timeout=20)
    r.raise_for_status()
    out = []
    for m in re.finditer(r"<item[ >](.*?)</item>", r.text, re.S):
        block = m.group(1)

        def grab(tag):
            mm = re.search(rf"<{tag}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{tag}>",
                           block, re.S)
            return re.sub(r"<[^>]+>", "", mm.group(1)).strip() if mm else ""
        title = grab("title")
        if title:
            out.append({"title": title, "summary": grab("description")[:400],
                        "link": grab("link"), "published": grab("pubDate")})
    return out


def _features(text: str):
    plain = _strip_accents(text.lower())
    words = set(re.findall(r"[a-z]{5,}", plain))
    numbers = set(re.findall(r"\d+", text))
    # Capitalised tokens are a weak proper-noun proxy in German, where every
    # noun is capitalised, so they are scored lower than numbers.
    proper = {_strip_accents(w.lower())
              for w in re.findall(r"\b[A-ZÀ-Ý][\wÀ-ÿ]{3,}", text)}
    return words, numbers, proper


def similarity(a: str, b: str) -> int:
    wa, na, pa = _features(a)
    wb, nb, pb = _features(b)
    # 5-char prefixes catch transliteration drift (Zelensky / Selenskyj).
    pre_a = {p[:5] for p in pa}
    pre_b = {p[:5] for p in pb}
    return (len(pa & pb) * 2 + len(pre_a & pre_b)
            + len(na & nb) * 2 + len(wa & wb))


def pair_up(a_items, b_items, min_score=MIN_SCORE):
    pairs = []
    used = set()
    scored = []
    for i, x in enumerate(a_items):
        xt = f"{x['title']} {x['summary'][:200]}"
        for j, y in enumerate(b_items):
            s = similarity(xt, f"{y['title']} {y['summary'][:200]}")
            if s >= min_score:
                scored.append((s, i, j))
    # greedy best-first so one article is not paired twice
    for s, i, j in sorted(scored, reverse=True):
        if i in used or ("b", j) in used:
            continue
        used.add(i); used.add(("b", j))
        pairs.append({"score": s, "a": a_items[i], "b": b_items[j]})
    return pairs


def main() -> int:
    out_path = None
    if "--out" in sys.argv:
        out_path = sys.argv[sys.argv.index("--out") + 1]
    everything = []
    for newsroom, feeds in ANCHORS.items():
        langs = sorted(feeds)
        cache = {}
        for lang in langs:
            try:
                cache[lang] = fetch(feeds[lang])
            except Exception as exc:
                print(f"{newsroom} [{lang}]: fetch failed, {type(exc).__name__}")
        base = "en"
        if base not in cache:
            continue
        for lang in langs:
            if lang == base or lang not in cache:
                continue
            pairs = pair_up(cache[base], cache[lang])
            smaller = min(len(cache[base]), len(cache[lang])) or 1
            print(f"{newsroom:16s} en<->{lang}  items {len(cache[base]):>3}/{len(cache[lang]):<3} "
                  f"pairs {len(pairs):>3}  ({len(pairs)/smaller:.0%} of the smaller feed)")
            for p in pairs:
                everything.append({"newsroom": newsroom, "lang_a": base,
                                   "lang_b": lang, **p})
    print(f"\ntotal pairs at score >= {MIN_SCORE}: {len(everything)}")
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(everything, fh, indent=1, ensure_ascii=False)
        print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
