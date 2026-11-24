#!/usr/bin/env python3
"""Mechanical checks on the 78 History event files.

These exist because an audit found four event pages crediting the wrong person
entirely: a Cherokee chief linked to an Arctic explorer, a missionary to a
Massachusetts politician, a murdered journalist to a film director, and an earl
to his own father. None was a quote, so none of the H-01..H-11 script
validators could see it. Half were found by one grep.

A finding is worth one afternoon. A check is worth every afternoon after it.
"""
import glob
import pathlib
import re
import sys
import unicodedata

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVENTS = sorted(glob.glob(str(ROOT / "data/history/events/*.yaml")))

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}: {detail}" if detail else name)


# Words that appear inside a Wikipedia disambiguator and say what the person
# DID. If the role text contradicts every one of them, the link is suspect.
ROLE_WORDS = {
    "journalist": ("journalist", "reporter", "correspondent", "press"),
    "politician": ("politician", "senator", "congress", "governor", "mp"),
    "director": ("director", "filmmaker", "film"),
    "archaeologist": ("archaeolog",),
    "astronaut": ("astronaut", "pilot", "apollo"),
    "missionary": ("missionar", "church", "cms"),
    "activist": ("activist", "leader", "campaign"),
    "monk": ("monk", "buddhis"),
}

# --------------------------------------------------------------------------
# A quotation dated outside its speaker's life.
#
# cambodian-genocide served "They told us to leave the city for three
# days..." as Dith Pran's "Testimony to the ECCC, 2009", in the same file that
# records him dying in 2008. Nothing compared the two fields, so the page and
# the episode both carried a testimony its speaker could not have given. The
# check reads the date the record gives a quotation (an excerpt's `date`, the
# year in a notable quote's `context`) against the `born`/`died` of the key
# figure the speaker field names.
#
# A record that SAYS its date is not the utterance date is not a
# contradiction: a journal published posthumously, a remark "as recounted in"
# a memoir thirty years later, a line "recorded by" a chronicler. Those dates
# belong to the publication, and whether the line may be read as the
# speaker's own words is H-11's question, not this one. BCE dates are skipped
# for the same reason the lifespan check skips them: the catalogue stores them
# both ways.
_NOT_THE_UTTERANCE = re.compile(
    r"posthum|published|recorded by|recounted|reported (?:in|by)|cited in|quoted (?:in|by)|"
    r"as told|attributed|compiled|tradition|memoir|translated", re.I)


def _toks(s: str) -> list[str]:
    s = "".join(c for c in unicodedata.normalize("NFD", s or "")
                if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9]+", s.lower())


def _figure_for(speaker: str, figures: list[dict]) -> dict | None:
    """The ONE key figure a speaker field names, or None when it names none or
    several. A guess here would fail a true quotation, so ambiguity is silence."""
    said = _toks(re.sub(r"\([^)]*\)", "", speaker or ""))
    if not said:
        return None
    hits = []
    for fig in figures:
        raw = str(fig.get("name") or "")
        forms = [_toks(re.sub(r"\([^)]*\)", "", raw))] + [_toks(a) for a in re.findall(r"\(([^)]+)\)", raw)]
        for form in forms:
            if form and (form == said
                         or (len(form) >= 2 and all(t in said for t in form))
                         or (len(said) >= 2 and all(t in form for t in said))):
                hits.append(fig)
                break
    return hits[0] if len(hits) == 1 else None


def _years(text: str) -> list[int]:
    """Three- and four-digit years in a date string, in order. A thousands
    figure ("60,000 people") is not a year."""
    s = re.sub(r"\d{1,3}(?:,\d{3})+", " ", str(text or ""))
    return [int(y) for y in re.findall(r"(?<!\d)(\d{3,4})(?!\d)", s)]


def quote_lifespan_findings(ev: dict) -> list[str]:
    out: list[str] = []
    if "BCE" in str(ev.get("date_display") or ""):
        return out
    figures = ev.get("key_figures") or []
    quotes = [(q.get("author"), q.get("date"), " ".join(str(q.get(k) or "") for k in ("date", "work")),
               q.get("text", ""), "primary_source_excerpts")
              for q in ev.get("primary_source_excerpts") or []]
    quotes += [(q.get("speaker"), q.get("context"), str(q.get("context") or ""),
                q.get("text", ""), "notable_quotes")
               for p in ev.get("perspectives") or [] for q in p.get("notable_quotes") or []]
    for speaker, date, said_about, text, where in quotes:
        if re.search(r"\bB\.?C", str(date or "")) or _NOT_THE_UTTERANCE.search(said_about):
            continue
        fig = _figure_for(str(speaker or ""), figures)
        years = _years(date)
        if fig is None or not years:
            continue
        born, died = fig.get("born"), fig.get("died")
        label = f"{ev.get('slug')}/{where}: {speaker}: {str(text)[:50]!r}"
        if isinstance(died, int) and died > 0 and min(years) > died:
            out.append(f"{label} is dated {date!r}, after its speaker died ({died})")
        if isinstance(born, int) and born > 0 and max(years) < born:
            out.append(f"{label} is dated {date!r}, before its speaker was born ({born})")
    return out


# The rule must be able to fail: the Dith Pran shape, and its mirror.
_PLANTED = {
    "slug": "planted", "date_display": "1975-1979",
    "key_figures": [{"name": "Ana Writer", "born": 1942, "died": 2008},
                    {"name": "Ben Elder (The Elder)", "born": 1900, "died": 1960}],
    "primary_source_excerpts": [
        {"text": "after death", "author": "Ana Writer", "work": "Testimony to a court", "date": "2009"},
        {"text": "in life", "author": "Ana Writer", "work": "Testimony to a court", "date": "1999"},
        {"text": "posthumous", "author": "Ana Writer", "work": "Diary, published posthumously", "date": "2010"},
    ],
    "perspectives": [{"notable_quotes": [
        {"text": "before birth", "speaker": "The Elder", "context": "Letter, 1888"},
        {"text": "secondhand", "speaker": "Ben Elder", "context": "Remark, as recounted in a memoir, 1990"},
        {"text": "thousands", "speaker": "Ben Elder", "context": "Speech moving 60,000 people, 1930"},
    ]}],
}
_got = quote_lifespan_findings(_PLANTED)
check("planted: a quotation dated after its speaker's death fails",
      any("'after death'" in g for g in _got), str(_got))
check("planted: a quotation dated before its speaker's birth fails",
      any("'before birth'" in g for g in _got), str(_got))
check("planted: a date the record marks as posthumous or secondhand, a dated-in-life quote "
      "and a thousands figure are not failures", len(_got) == 2, str(_got))

for path in EVENTS:
    ev = yaml.safe_load(open(path))
    slug = ev["slug"]

    for finding in quote_lifespan_findings(ev):
        check(finding, False)

    for fig in ev.get("key_figures") or []:
        name = fig.get("name", "?")
        role = str(fig.get("role") or "").lower()
        wiki = str(fig.get("wikipedia") or "")
        born, died = fig.get("born"), fig.get("died")

        # A life that runs backwards is wrong, but BCE years count DOWN and
        # this catalogue stores them as positive numbers in key_figures while
        # using negative ones in date_sort. So the direction of the test
        # depends on the era, read from the event's own date_display.
        # BCE years are stored BOTH ways in this catalogue: alexanders uses
        # -356, peloponnesian uses 494 for the same era. So only judge a
        # lifespan where the answer does not depend on which convention the
        # file chose, and flag the mixed convention separately below.
        bce = "BCE" in str(ev.get("date_display") or "")
        if isinstance(born, int) and isinstance(died, int):
            if born < 0 and died < 0:
                ok = born < died                 # signed BCE sorts naturally
            elif born > 0 and died > 0 and not bce:
                ok = born < died                 # ordinary CE
            else:
                ok = True                        # ambiguous: do not guess
            check(f"{slug}/{name}: lifespan runs the right way",
                  ok, f"born {born}, died {died}")

        # The link's own disambiguator against the role beside it. This is the
        # grep that found half of them.
        m = re.search(r"\(([^)]+)\)\s*$", wiki)
        if m:
            tag = m.group(1).lower().replace("_", " ")
            for key, words in ROLE_WORDS.items():
                if key in tag:
                    check(f"{slug}/{name}: wikipedia disambiguator matches the role",
                          any(w in role for w in words),
                          f"link says {tag!r}, role says {role[:60]!r}")
                    break

        # A wrong identifier is worse than none, so a figure may carry no
        # wikidata id, but not one belonging to somebody else. We cannot check
        # that from here; we can check it is shaped like a QID.
        qid = fig.get("wikidata")
        if qid is not None:
            check(f"{slug}/{name}: wikidata looks like a QID",
                  bool(re.fullmatch(r"Q\d+", str(qid))), str(qid))

    # A figure credited with an act cannot have died before it. We only check
    # the cases the text states plainly as a four-digit year.
    for fig in ev.get("key_figures") or []:
        # And no figure acts before birth. black-death gave Ibn Khatima
        # `born: 1369` beside a role crediting him with a treatise of 1349;
        # the year was cut (the record holds no other), not moved to `died`.
        born = fig.get("born")
        if isinstance(born, int) and born > 0 and "BCE" not in str(ev.get("date_display") or ""):
            for year in re.findall(r"\b(1[0-9]\d\d|20[0-2]\d)\b", str(fig.get("role") or "")):
                check(f"{slug}/{fig.get('name')}: credited with an act before birth",
                      int(year) >= born, f"born {born}, role cites {year}")
    for fig in ev.get("key_figures") or []:
        died = fig.get("died")
        if not isinstance(died, int) or died < 0:
            continue
        role_txt = str(fig.get("role") or "")
        # Posthumous publication is not a contradiction: a journal can appear
        # after its author dies, and Henri Mouhot's did.
        if re.search(r"posthum|published|journal", role_txt, re.I):
            continue
        for year in re.findall(r"\b(1[5-9]\d\d|20[0-2]\d)\b", role_txt):
            check(f"{slug}/{fig.get('name')}: credited with an act after death",
                  int(year) <= died, f"died {died}, role cites {year}")

    # A stock photograph is not evidence of anything. 242 Unsplash and Pexels
    # items (48% of the catalogue's media) were removed on 2026-09-24, Phase 0
    # of docs/proposals/HISTORY-THESIS-PAGE.md; the exporter had been silently
    # dropping them from the served page, which is how nobody noticed a
    # photograph of the wrong century sitting in the record for months.
    STOCK_HOSTS = ("unsplash.com", "pexels.com", "pixabay.com")
    for i, m in enumerate(ev.get("media") or []):
        blob = " ".join(str(m.get(k) or "") for k in ("source_url", "supabase_url", "license", "attribution")).lower()
        check(f"{slug}/media[{i}]: not a stock photograph",
              not any(h in blob for h in STOCK_HOSTS) and "unsplash" not in blob and "pexels" not in blob,
              str(m.get("source_url"))[:80])
    hero = str(ev.get("hero_image_url") or "").lower()
    check(f"{slug}: hero is not a stock photograph",
          "unsplash" not in hero and "pexels" not in hero, hero[:80])

    # A wrong identifier is worse than none. On 2026-09-24, 188 bibliography
    # entries carried a DOI that 404s or names a different work (a review of
    # the book, mostly), or an archive.org link that is gone. Each lost the bad
    # identifier and kept its title, and an entry with no identifier left is
    # marked `verified: false` (docs/audits/HISTORY-IDENTIFIERS-2026-09-24.md).
    # The marker means exactly that: nothing on this entry has been resolved.
    # An identifier added back without clearing the marker is the lie the
    # marker exists to prevent, and it fails here.
    for pi, p in enumerate(ev.get("perspectives") or []):
        for si, s in enumerate(p.get("sources") or []):
            if s.get("verified") is False:
                check(f"{slug}/perspectives[{pi}].sources[{si}]: an unverified entry carries no identifier",
                      not any(s.get(k) for k in ("doi", "archive_url", "url")),
                      str(s.get("title"))[:60])

if failures:
    print("\n".join(f"FAIL  {f}" for f in failures))
    print(f"\n{len(failures)} History data failure(s)")
    sys.exit(1)

print(f"PASS  {len(EVENTS)} History events: figure identity, lifespans, identifiers")
