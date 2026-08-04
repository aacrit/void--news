"""ig_review — render Instagram DRAFTS to a local HTML review sheet and open it.

Used by the /void-social, /history-social, /weekly-social skills to give the
CEO a visual review of freshly generated drafts (nothing is posted). Queries
`ig_posts` for the requested track's pillars, renders every carousel slide plus
the caption / hashtags, flags obvious problems (unfilled placeholders, missing
captions, old-brand tokens, near-duplicates), writes an HTML file, and opens it
in the browser.

Usage:
    python -m pipeline.social.ig_review --track void [--open] [--limit 12]
    python -m pipeline.social.ig_review --track history --open
    python -m pipeline.social.ig_review --track all --open
"""
import argparse
import html
import json
import os
import re
import sys
import tempfile
import urllib.request
import webbrowser

TRACK_PILLARS = {
    "void": ["vision", "method", "example"],
    "history": ["history"],
    "weekly": ["weekly"],
    "all": ["vision", "method", "example", "history", "weekly"],
}


def _load_env():
    """Populate os.environ from a repo-root .env if the keys aren't already set."""
    if os.environ.get("SUPABASE_URL") or os.environ.get("NEXT_PUBLIC_SUPABASE_URL"):
        return
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    envp = os.path.join(root, ".env")
    if not os.path.exists(envp):
        return
    for line in open(envp, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _rest(path):
    url = os.environ.get("NEXT_PUBLIC_SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")
           or os.environ.get("NEXT_PUBLIC_SUPABASE_ANON_KEY"))
    if not url or not key:
        sys.exit("ig_review: SUPABASE_URL / key not found (set env or repo .env)")
    req = urllib.request.Request(url.rstrip("/") + "/rest/v1/" + path,
                                 headers={"apikey": key, "Authorization": "Bearer " + key})
    return json.load(urllib.request.urlopen(req))


def _words(cap):
    return set(w for w in re.findall(r"[a-z]{5,}", (cap or "").lower()))


def _flags(i, rows, sigs):
    out = []
    cap = rows[i].get("caption") or ""
    if not cap.strip():
        out.append(("err", "No caption generated"))
    if "[" in cap and "]" in cap:
        out.append(("err", "Unfilled template placeholder"))
    if "void --" in cap.lower():
        out.append(("warn", "Old brand token (void --...)"))
    for j, r2 in enumerate(rows):
        if j != i and sigs[i] and len(sigs[i] & sigs[j]) >= 8:
            out.append(("warn", f"Near-duplicate of a {r2.get('pillar')} post"))
            break
    return out


def build(track, limit):
    pillars = TRACK_PILLARS[track]
    inlist = ",".join(pillars)
    rows = _rest(f"ig_posts?select=id,pillar,state,caption,hashtags,image_urls,created_at"
                 f"&pillar=in.({inlist})&state=neq.rejected"
                 f"&order=created_at.desc&limit={limit}")
    sigs = [_words(r.get("caption")) for r in rows]
    cards = []
    for i, r in enumerate(rows):
        imgs = r.get("image_urls") or []
        if not isinstance(imgs, list):
            imgs = []
        slides = "".join(f'<img loading="lazy" src="{html.escape(u)}" alt="slide {n+1}">'
                         for n, u in enumerate(imgs)) or '<div class="noimg">not rendered yet</div>'
        tags = r.get("hashtags")
        tags = " ".join(tags) if isinstance(tags, list) else (tags or "")
        fl = _flags(i, rows, sigs)
        badges = "".join(f'<span class="flag {c}">{html.escape(t)}</span>' for c, t in fl)
        ring = "card--err" if any(c == "err" for c, _ in fl) else ("card--warn" if fl else "")
        cards.append(f"""
        <article class="card {ring}">
          <div class="slides">{slides}</div>
          <div class="meta">
            <div class="head"><span class="pill pill--{html.escape(r.get('pillar') or '')}">{html.escape((r.get('pillar') or '').upper())}</span><span class="state">{html.escape(r.get('state') or '')}</span></div>
            {f'<div class="flags">{badges}</div>' if badges else ''}
            <p class="cap">{html.escape((r.get('caption') or '(no caption yet)').strip())}</p>
            <p class="tags">{html.escape(tags)}</p>
          </div>
        </article>""")
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>Void News social drafts, {html.escape(track)}</title>
<style>
:root{{color-scheme:dark}}*{{box-sizing:border-box}}
body{{margin:0;background:#14120f;color:#ece7dd;font-family:-apple-system,Segoe UI,Inter,system-ui,sans-serif;padding:28px}}
h1{{font-family:Georgia,serif;margin:0 0 4px}}
.sub{{color:#a89f8f;margin:0 0 24px;font-size:14px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:22px}}
.card{{background:#1e1b16;border:1px solid #322d25;border-radius:10px;overflow:hidden}}
.card--warn{{border-color:#8a6d1f}}.card--err{{border-color:#a23b2f}}
.slides{{display:flex;gap:6px;overflow-x:auto;background:#0d0b09;padding:6px}}
.slides img{{height:300px;width:auto;border-radius:3px;flex:0 0 auto;cursor:zoom-in}}
.lb{{position:fixed;inset:0;background:rgba(8,7,6,.94);display:none;align-items:center;justify-content:center;z-index:999;cursor:zoom-out;padding:24px}}
.lb.on{{display:flex}}
.lb img{{max-width:96vw;max-height:96vh;width:auto;height:auto;box-shadow:0 10px 60px rgba(0,0,0,.6);border-radius:4px}}
.noimg{{color:#6b6459;font-size:13px;padding:24px}}
.meta{{padding:14px 15px 16px}}
.head{{display:flex;gap:8px;align-items:center;margin-bottom:8px}}
.pill{{font-size:11px;letter-spacing:.06em;padding:2px 9px;border-radius:20px;background:#322d25;color:#cbb98f}}
.pill--vision,.pill--method,.pill--example{{color:#d9a184}}
.pill--history{{color:#c6a678}}.pill--weekly{{color:#e08a7c}}
.state{{font-size:11px;color:#8a8175;margin-left:auto}}
.flags{{display:flex;flex-direction:column;gap:4px;margin-bottom:8px}}
.flag{{font-size:12px;padding:4px 8px;border-radius:5px}}
.flag.err{{background:#3a1512;color:#f0a89c;border:1px solid #a23b2f}}
.flag.warn{{background:#332812;color:#e6c878;border:1px solid #8a6d1f}}
.cap{{font-size:13.5px;line-height:1.5;margin:0 0 10px;white-space:pre-wrap}}
.tags{{font-size:12px;color:#7fa8c8;margin:0}}
</style></head><body>
<h1>Void News social drafts, {html.escape(track)} track</h1>
<p class="sub">{len(rows)} drafts, nothing posted. Red = broken (do not publish). Amber = needs a fix. Scroll a card's slides sideways; click to zoom.</p>
<div class="grid">{''.join(cards)}</div>
<div class="lb" id="lb"><img id="lbimg" alt="expanded slide"></div>
<script>
(function(){{
  var lb=document.getElementById('lb'), im=document.getElementById('lbimg');
  document.querySelectorAll('.slides img').forEach(function(t){{
    t.addEventListener('click',function(){{ im.src=t.src; lb.classList.add('on'); }});
  }});
  lb.addEventListener('click',function(){{ lb.classList.remove('on'); im.src=''; }});
  document.addEventListener('keydown',function(e){{ if(e.key==='Escape'){{ lb.classList.remove('on'); im.src=''; }} }});
}})();
</script>
</body></html>"""
    out = os.path.join(tempfile.gettempdir(), f"ig_review_{track}.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    return out, len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", choices=list(TRACK_PILLARS), default="void")
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--open", action="store_true", help="open the HTML in a browser")
    args = ap.parse_args()
    _load_env()
    path, n = build(args.track, args.limit)
    print(f"WROTE {path} ({n} drafts)")
    if args.open:
        webbrowser.open("file:///" + path.replace("\\", "/"))


if __name__ == "__main__":
    main()
