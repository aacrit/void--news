#!/usr/bin/env python3
"""Second pass over a discovered feed: is it really this outlet's feed?

Discovery answers "is this a valid feed whose links are on its own domain".
That is not enough, and both ways it fails were measured on 2026-09-22 rather
than imagined:

  the channel link            The first pass read `<link>` anywhere in the XML,
                              which in RSS 2.0 is the CHANNEL's link, the site
                              homepage. It declared 139 of 143 healthy feeds
                              suspicious. Links are read from inside `<item>`
                              here, and nowhere else.

  a hijacked domain           Botswana Guardian's feed resolved to
                              bettingbotswana.com, and because the first pass
                              compared item links against the FEED's own
                              domain, every link matched and it passed. Links
                              are compared against the EXPECTED domain here,
                              which is the caller's, not the feed's. That
                              rejected 8 of 143.

  a plausible wrong domain    New to this version. For an outlet not yet on the
                              roster the expected domain is a human's guess, so
                              a guess that happens to be a live news site would
                              pass the domain test by construction. So the
                              feed's own channel title has to carry a word of
                              the outlet's name. It is reported as `named`
                              rather than enforced here: the caller decides.

Input is a JSON list of objects with `name`, `url` (the outlet's expected
homepage) and `feed`. Output is one JSON object per line on stdout.

    python3 scripts/roster/verify_feeds.py <candidates.json>
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
import urllib.parse

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
S = requests.Session()
S.headers["User-Agent"] = UA

# A word shorter than this carries no identifying power ("the", "de", "news"
# is common to half the roster and is excluded outright).
NAME_TOKEN_MIN = 4
NAME_STOPWORDS = {"news", "daily", "times", "post", "the", "online", "world",
                  "today", "weekly", "journal", "press", "media", "report"}


# `requests` falls back to ISO-8859-1 when a response declares no charset in
# its Content-Type, which is most RSS. Hankyoreh's Korean title therefore came
# back as "ì ì²´ê¸°ì¬ : ë´ì¤", its real UTF-8 bytes read as latin-1, and the
# check asking whether the title names the outlet was asking it of garbage.
# An XML document declares its own encoding; that declaration wins.
_XML_ENC_RE = re.compile(rb"""<\?xml[^>]*encoding=["']([\w.-]+)["']""", re.I)


def decoded(resp) -> str:
    """The feed as text, using the encoding the XML itself declares."""
    raw = resp.content
    hit = _XML_ENC_RE.search(raw[:200])
    for enc in ([hit.group(1).decode("ascii", "ignore")] if hit else []) + \
               ([resp.encoding] if resp.encoding
                and resp.encoding.lower() not in ("iso-8859-1", "latin-1")
                else []) + ["utf-8"]:
        try:
            return raw.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return raw.decode("utf-8", "replace")


# Multi-label public suffixes. `reg()` used to take the last two labels of a
# host, which returns the SUFFIX rather than the registrable domain for these:
# `english.hani.co.kr` became `co.kr`, and the expected-domain test then asked
# "is this link on any .co.kr site". That is the same vacuity as comparing
# links against the feed's own domain, which is what let a hijacked
# bettingbotswana.com pass the first version of this pass. Six of the outlets
# added on 2026-09-22 sit on one of these.
#
# This is NOT the Public Suffix List. It is the multi-label suffixes the roster
# actually uses, which is checkable against data/sources.json and says so. An
# unlisted suffix falls back to two labels, which is the old behaviour and no
# worse than it was.
MULTI_LABEL_SUFFIXES = frozenset({
    "co.uk", "org.uk", "gov.uk", "ac.uk", "me.uk", "net.uk", "sch.uk",
    "co.jp", "or.jp", "ne.jp", "go.jp", "ac.jp",
    "co.kr", "or.kr", "go.kr", "re.kr",
    "co.in", "net.in", "org.in", "gov.in", "ac.in",
    "com.au", "net.au", "org.au", "gov.au", "edu.au",
    "co.nz", "net.nz", "org.nz", "govt.nz", "ac.nz",
    "co.za", "org.za", "net.za", "gov.za", "ac.za",
    "com.br", "net.br", "org.br", "gov.br",
    "com.ar", "gob.ar", "org.ar", "net.ar",
    "com.mx", "gob.mx", "org.mx",
    "com.co", "gov.co", "com.pe", "gob.pe", "com.ve", "com.ec", "com.uy",
    "com.bo", "com.py", "com.do", "com.gt", "com.pa", "com.sv", "com.ni",
    "com.cn", "net.cn", "org.cn", "gov.cn", "com.hk", "org.hk", "com.tw",
    "com.sg", "com.my", "com.ph", "com.vn", "co.th", "or.th", "com.pk",
    "com.bd", "com.np", "com.lk", "com.kh", "com.mm",
    "com.tr", "gov.tr", "com.eg", "com.sa", "com.qa", "com.kw", "com.bh",
    "com.om", "com.jo", "com.lb", "com.ly", "com.ng", "com.gh", "co.ke",
    "or.ke", "go.ke", "co.tz", "co.ug", "co.zm", "co.zw", "com.na",
    "com.mt", "com.cy", "com.ua", "com.ru", "org.ru", "net.ru",
    "com.pl", "com.hr", "co.rs", "com.ge", "com.pt", "com.es", "com.fr",
    "com.de", "co.il", "org.il", "net.il", "ac.il", "gov.il",
})


def reg(host: str) -> str:
    """The registrable domain: one label above the public suffix.

    `news.bbc.co.uk` -> `bbc.co.uk`, not `co.uk`.
    """
    parts = [p for p in (host or "").lower().split(".") if p]
    if len(parts) < 2:
        return host or ""
    if ".".join(parts[-2:]) in MULTI_LABEL_SUFFIXES and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


# A CDATA wrapper hides the link from a naive regex: the content starts with
# "<", and every `[^<]` class stops dead on it. Measured 2026-09-22 on
# eldiario.es and Rzeczpospolita, which both write
# `<link><![CDATA[https://...]]></link>`. Both were reported as having ZERO
# links on their own domain, which is the same verdict this pass gives a
# Google News proxy, so two national majors (one Spanish left, one Polish
# right) were about to be dropped over a choice of XML escaping. A
# publisher's escaping is not evidence about their feed, so it is unwrapped
# before anything is read. `guid` is accepted as a last resort for the same
# reason: rp.pl puts the canonical URL there as well.
_CDATA_RE = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.S)


def uncdata(xml: str) -> str:
    return _CDATA_RE.sub(lambda m: m.group(1), xml)


def item_links(xml: str) -> list[str]:
    """Links from INSIDE items only. See the channel-link note above."""
    out = []
    for m in re.finditer(r"<(item|entry)[ >](.*?)</\1>", uncdata(xml), re.S):
        body = m.group(2)
        hit = (re.search(r"<link[^>]*>\s*(https?://[^<\s]+)\s*</link>", body)
               or re.search(r"<link[^>]*href=[\"'](https?://[^\"']+)[\"']", body)
               or re.search(r"<guid[^>]*>\s*(https?://[^<\s]+)\s*</guid>", body))
        if hit:
            out.append(hit.group(1).strip())
    return out


def channel_title(xml: str) -> str:
    """The feed's own title: the first <title> before any item."""
    head = re.split(r"<(?:item|entry)[ >]", xml, maxsplit=1)[0]
    m = re.search(r"<title[^>]*>(.*?)</title>", head, re.S)
    if not m:
        return ""
    t = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", m.group(1), flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t)).strip()


# What a section front is called. A single-segment URL is an article unless it
# is one of these. Written out rather than inferred, so a wrong entry shows.
SECTION_WORDS = frozenset({
    "news", "latest", "home", "index", "sport", "sports", "business",
    "politics", "opinion", "world", "national", "local", "tech",
    "technology", "science", "health", "culture", "arts", "entertainment",
    "lifestyle", "life", "travel", "food", "money", "markets", "economy",
    "environment", "climate", "education", "media", "features", "analysis",
    "comment", "editorial", "letters", "obituaries", "weather", "video",
    "videos", "photos", "podcasts", "audio", "newsletters", "archive",
    "about", "contact", "subscribe", "advertise", "privacy", "terms",
    "search", "tag", "tags", "topic", "topics", "category", "categories",
    "author", "authors", "staff", "section", "sections", "feed", "rss",
    "blog", "blogs", "stories", "articles", "all", "more", "page",
})


def looks_article(u: str) -> bool:
    """Is this a link to one article rather than a section front?

    The query string counts. Novinite serves every article as
    `view_news.php?id=240715`, and dropping the query left `view_news.php`,
    which looks like a section front, so all 24 of its links were rejected and
    Bulgaria's news agency stayed on a Google News feed with an 11-word median.
    A CMS's URL style is not evidence about its journalism.
    """
    tail = u.split("://", 1)[-1]
    full = tail.split("/", 1)[1] if "/" in tail else ""
    path, _, query = full.partition("?")
    path = path.rstrip("/")
    if not path and not query:
        return False
    if re.search(r"(^|/)(index|home)\.html?$", path) and not query:
        return False
    # An id or a slug in the query is as much an article pointer as one in the
    # path: `?id=240715`, `?p=8812`, `?story=long-slug-here`.
    if re.search(r"\b(id|p|story|article|aid|nid)=[\w-]{3,}", query):
        return True
    segs = [seg for seg in path.split("/") if seg]
    if len(segs) >= 2 or any(len(seg) >= 25 or seg.count("-") >= 3
                             for seg in segs) or re.search(r"\d{4,}", path):
        return True
    # A SHORT SINGLE SEGMENT is the third false-negative class this heuristic
    # has had. `/dangers-of-ai/`, `/protectdemocracy` and
    # `/irooj-mike-farewelled/` are articles and were all rejected, which held
    # three healthy feeds at 9 of 10. The rule is not relaxed until they pass;
    # instead a section front is named for what it is, a navigational word.
    return bool(segs) and segs[-1].lower() not in SECTION_WORDS


def name_tokens(name: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", deaccent(name or "").lower())
    keep = [w for w in words
            if len(w) >= NAME_TOKEN_MIN and w not in NAME_STOPWORDS]
    # An outlet whose every word is a stopword ("The Daily Star") still has to
    # be checkable, so fall back to the raw words rather than passing vacuously.
    return keep or words


def deaccent(text: str) -> str:
    """Map an accented letter to its base, rather than deleting it.

    A `[^a-z0-9]` strip DELETES the accent's letter: "Página" became "pgina",
    so the token "pagina" did not match and Pagina 12's own feed was rejected
    for not naming Pagina 12. A publisher's orthography is not evidence about
    their feed.
    """
    stripped = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in stripped if not unicodedata.combining(c))


def squash(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", deaccent(text).lower())


def named(name: str, title: str, domain: str) -> bool:
    """Does the feed admit whose it is, in its title or its own domain?"""
    hay = squash(f"{title} {domain}")
    return any(squash(t) in hay for t in name_tokens(name))


def main() -> int:
    rows = json.load(open(sys.argv[1], encoding="utf-8"))
    for c in rows:
        expected = reg(urllib.parse.urlparse(c.get("url") or "").netloc)
        # The homepage is echoed through so the next stage writes the roster's
        # `url` from the same value this pass verified against, rather than
        # re-deriving it and possibly disagreeing with itself.
        # The roster `id` is echoed through when the caller supplies one, so
        # apply_feeds can key on it. A name can be renamed (and two rows shared
        # one until 2026-09-22); an id cannot, and a row matched by the wrong
        # key is a feed written onto the wrong outlet.
        rec = {"name": c["name"], "url": c.get("url"), "feed": c.get("feed"),
               "expected_domain": expected}
        if c.get("id"):
            rec["id"] = c["id"]
        try:
            r = S.get(c["feed"], timeout=15, allow_redirects=True)
            xml = decoded(r)
            links = item_links(xml)
            title = channel_title(xml)
            on_exp = [l for l in links
                      if reg(urllib.parse.urlparse(l).netloc) == expected]
            arts = [l for l in on_exp if looks_article(l)]
            rec.update(status=r.status_code, items=len(links),
                       on_expected=len(on_exp), articles=len(arts),
                       title=title[:120],
                       named=named(c["name"], title, expected),
                       sample=(arts[0] if arts else
                               (on_exp[0] if on_exp else
                                (links[0] if links else None))))
        except Exception as exc:
            rec.update(status=None, error=type(exc).__name__)
        print(json.dumps(rec, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
