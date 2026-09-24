#!/usr/bin/env python3
"""Find a direct RSS feed for an outlet whose current feed is broken or is a
Google News proxy.

WHY THIS EXISTS. Measured 2026-09-22 across 78,328 archived articles: the 540
sources fed by Google News search queries carry a MEDIAN OF 11 WORDS, and 0.0%
of them reach the 150-word threshold the lean analyser needs for full text
authority. Direct-fed sources carry a median of 407 words with 66% over 150.
The Google News redirect token (`news.google.com/rss/articles/CBMi...`) no
longer resolves to a publisher URL, so `web_scraper.py`'s canonical-URL
recovery fails and scoring falls back to the RSS summary, which is a headline.

WHAT COUNTS AS SUCCESS, and this is the part that is easy to get wrong: NOT
full article text in the feed. The pipeline's scraper fetches the article
itself, so the feed only has to supply a resolvable publisher URL. Success is
therefore a valid feed with items whose <link> points at the outlet's own
registered domain. A feed whose descriptions are 50 words is fine; a feed whose
links are google.com redirects is not.

WHAT IT CANNOT DO. Outlets behind a bot wall return 401/403 to any
non-browser client (measured: reuters.com 401, apnews.com a Cloudflare 403),
and some have genuinely discontinued public RSS. Those cannot be migrated by
this script and need a separate decision: either accept that they are scored on
headlines and say so on the page, or drop them.

    python3 scripts/roster/discover_feeds.py <records.json>

Input is a JSON list of roster records carrying at least `name` and `url`.
Output is one JSON object per line on stdout, with `found` holding the feed and
its evidence, or null plus a `why`. Politeness: one request at a time, 0.25s
between candidates. It touches no roster file; the diff is for human review.
"""
import json, re, sys, urllib.parse, time, random
import requests
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
S=requests.Session(); S.headers.update({'User-Agent':UA,'Accept':'application/rss+xml,application/xml,text/xml,*/*'})
COMMON=["/feed","/feed/","/rss","/rss/","/rss.xml","/feed.xml","/index.xml","/atom.xml",
        "/feeds/all.atom.xml","/en/rss","/rss/news","/news/rss","/?feed=rss2","/feeds/rss.xml",
        "/arc/outboundfeeds/rss/","/rssfeeds/latest.xml","/api/rss"]
# See scripts/roster/verify_feeds.py for why two labels is not the registrable
# domain: `english.hani.co.kr` became `co.kr`, so the own-domain test asked
# whether a link was on any .co.kr site at all.
from verify_feeds import reg  # noqa: E402  (same directory, same definition)
def probe(u):
    try: r=S.get(u,timeout=12,allow_redirects=True)
    except Exception as e: return None,f"{type(e).__name__}"
    if r.status_code!=200: return None,f"HTTP {r.status_code}"
    h=r.text[:1500].lower()
    if not ('<rss' in h or '<feed' in h or '<rdf' in h): return None,"not a feed"
    # CDATA first: a `<link><![CDATA[https://...]]></link>` is invisible to a
    # `[^<]` class, because the content opens with "<". Measured 2026-09-22:
    # eldiario.es and Rzeczpospolita were both reported as having zero
    # own-domain links and dropped, which is the verdict this script exists to
    # give a Google News proxy. A publisher's XML escaping is not evidence
    # about their feed.
    body=re.sub(r'<!\[CDATA\[(.*?)\]\]>', lambda m: m.group(1), r.text, flags=re.S)
    links=re.findall(r'<link[^>]*>\s*([^<\s]+)\s*</link>', body) \
        + re.findall(r'<link[^>]*href=["\']([^"\']+)["\']', body) \
        + re.findall(r'<guid[^>]*>\s*(https?://[^<\s]+)\s*</guid>', body)
    links=[l for l in links if l.startswith('http')]
    items=len(re.findall(r'<item[ >]|<entry[ >]', r.text))
    if items==0: return None,"0 items"
    gnews=sum(1 for l in links if 'news.google.com' in l)
    own=reg(urllib.parse.urlparse(r.url).netloc)
    onown=sum(1 for l in links if reg(urllib.parse.urlparse(l).netloc)==own)
    return {'feed':r.url,'items':items,'links':len(links),
            'own_domain_links':onown,'google_links':gnews,
            'sample_link':next((l for l in links if 'news.google' not in l and reg(urllib.parse.urlparse(l).netloc)==own), None)},"ok"
def autodiscover(home):
    out=[]
    for base in (home,):
        try: r=S.get(base,timeout=12,allow_redirects=True)
        except Exception: continue
        if r.status_code!=200: continue
        for m in re.finditer(r'<link[^>]+>', r.text[:500000], re.I):
            t=m.group(0)
            if not re.search(r'type=["\']application/(rss|atom)\+xml', t, re.I): continue
            hm=re.search(r'href=["\']([^"\']+)["\']', t, re.I)
            if hm: out.append(urllib.parse.urljoin(r.url,hm.group(1)))
    return out[:8]
def subdomains(home):
    h=urllib.parse.urlparse(home).netloc
    r=reg(h)
    return [f"https://rss.{r}/rss/",f"https://rss.{r}/",f"https://feeds.{r}/",f"https://feeds.{r}/rss"]
def run(rec):
    home=rec['url'] or ''
    if not home.startswith('http'): return {**rec,'found':None,'why':'no url'}
    cands=autodiscover(home)+[urllib.parse.urljoin(home,p) for p in COMMON]+subdomains(home)
    seen=set(); best=None; whys=[]
    for u in cands:
        if u in seen: continue
        seen.add(u)
        got,why=probe(u)
        whys.append(why)
        if got and got['own_domain_links']>0:
            if best is None or got['own_domain_links']>best['own_domain_links']: best=got
            if best['own_domain_links']>=5: break
        time.sleep(0.25)
    # `whys[0]` alone produced records reading found=null, why='ok', which is
    # a contradiction: 'ok' from probe() means a parseable feed with items,
    # and reaching here means none of them had a link on the outlet's own
    # domain. Say that instead.
    if best: why='ok'
    elif 'ok' in whys: why='feed found, no item link on the outlet own domain'
    elif whys: why=whys[0]
    else: why='no candidates'
    return {**rec,'found':best,'why':why}
if __name__=='__main__':
    recs=json.load(open(sys.argv[1]))
    for rec in recs:
        print(json.dumps(run(rec)), flush=True)
