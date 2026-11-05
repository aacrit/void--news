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
import io
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
        cap = html.escape((r.get("caption") or "(no caption yet)").strip())
        cards.append(f"""
        <section class="page {ring}">
          <div class="page__head">
            <span class="idx">Post {i + 1} / {len(rows)}</span>
            <span class="pill pill--{html.escape(r.get('pillar') or '')}">{html.escape((r.get('pillar') or '').upper())}</span>
            <span class="state">{html.escape(r.get('state') or '')}</span>
            {badges}
          </div>
          <div class="page__slides">{slides}</div>
          <div class="page__cap">
            <p class="cap">{cap}</p>
            <p class="tags">{html.escape(tags)}</p>
          </div>
        </section>""")
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>Void News social drafts, {html.escape(track)}</title>
<style>
:root{{color-scheme:dark}}*{{box-sizing:border-box}}
html,body{{margin:0;height:100%}}
body{{background:#14120f;color:#ece7dd;font-family:-apple-system,Segoe UI,Inter,system-ui,sans-serif}}
/* One post per full-viewport page; scroll snaps to the next post. */
.deck{{height:100vh;overflow-y:scroll;scroll-snap-type:y mandatory;scroll-behavior:smooth}}
.page{{height:100vh;scroll-snap-align:start;display:flex;flex-direction:column;gap:12px;padding:18px 30px 16px}}
.page--warn{{box-shadow:inset 0 0 0 2px #8a6d1f}}
.page--err{{box-shadow:inset 0 0 0 2px #a23b2f}}
.page__head{{flex:0 0 auto;display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.idx{{font-family:Georgia,serif;font-size:15px;color:#a89f8f}}
.pill{{font-size:12px;letter-spacing:.06em;padding:3px 11px;border-radius:20px;background:#322d25;color:#cbb98f;text-transform:uppercase}}
.pill--vision,.pill--method,.pill--example{{color:#d9a184}}
.pill--history{{color:#c6a678}}.pill--weekly{{color:#e08a7c}}
.state{{font-size:12px;color:#8a8175}}
.flag{{font-size:12px;padding:3px 9px;border-radius:5px}}
.flag.err{{background:#3a1512;color:#f0a89c;border:1px solid #a23b2f}}
.flag.warn{{background:#332812;color:#e6c878;border:1px solid #8a6d1f}}
/* The three slides, side by side, filling the middle. */
.page__slides{{flex:1 1 auto;min-height:0;display:flex;gap:18px;justify-content:center;align-items:center}}
.page__slides img{{max-height:100%;max-width:31vw;width:auto;height:auto;border-radius:4px;box-shadow:0 6px 30px rgba(0,0,0,.45);cursor:zoom-in}}
.noimg{{color:#6b6459;font-size:14px}}
.page__cap{{flex:0 0 auto;max-height:20vh;overflow-y:auto;display:flex;gap:26px;align-items:flex-start}}
.cap{{font-size:14px;line-height:1.5;margin:0;white-space:pre-wrap;flex:1 1 auto}}
.tags{{font-size:12.5px;color:#7fa8c8;margin:0;flex:0 0 28%}}
.lb{{position:fixed;inset:0;background:rgba(8,7,6,.94);display:none;align-items:center;justify-content:center;z-index:999;cursor:zoom-out;padding:24px}}
.lb.on{{display:flex}}
.lb img{{max-width:96vw;max-height:96vh;width:auto;height:auto;box-shadow:0 10px 60px rgba(0,0,0,.6);border-radius:4px}}
.hint{{position:fixed;bottom:12px;left:50%;transform:translateX(-50%);font-size:12px;color:#a89f8f;background:rgba(20,18,15,.85);border:1px solid #322d25;padding:5px 14px;border-radius:20px;pointer-events:none;z-index:50}}
</style></head><body>
<div class="deck">{''.join(cards)}</div>
<div class="hint">{len(rows)} drafts, nothing posted &middot; scroll for next &darr; &middot; click a slide to zoom</div>
<div class="lb" id="lb"><img id="lbimg" alt="expanded slide"></div>
<script>
(function(){{
  var lb=document.getElementById('lb'), im=document.getElementById('lbimg');
  document.querySelectorAll('.page__slides img').forEach(function(t){{
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


def _pdf_font(size, bold=False):
    from PIL import ImageFont
    names = (["georgiab.ttf", "arialbd.ttf"] if bold else ["georgia.ttf", "arial.ttf"]) + ["DejaVuSans.ttf"]
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for w in (text or "").split():
        t = (cur + " " + w).strip()
        if not cur or draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def build_pdf(track, limit):
    """One LANDSCAPE page per post (3 slides side by side + caption + tags),
    combined into a shareable multi-page PDF. Pillow only, no browser."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        sys.exit("ig_review --pdf needs Pillow (pip install pillow)")
    inlist = ",".join(TRACK_PILLARS[track])
    rows = _rest(f"ig_posts?select=id,pillar,caption,hashtags,image_urls"
                 f"&pillar=in.({inlist})&state=neq.rejected"
                 f"&order=created_at.desc&limit={limit}")
    W, H, M, GAP = 2200, 1400, 70, 44
    SW = (W - 2 * M - 2 * GAP) // 3
    SH = int(SW * 1350 / 1080)   # keep the 1080x1350 slide aspect
    SY = 150
    BG, INK, TAG = (250, 247, 240), (28, 24, 20), (90, 120, 150)
    hfont, cfont, tfont = _pdf_font(34, bold=True), _pdf_font(30), _pdf_font(24)
    pages = []
    for i, r in enumerate(rows):
        pg = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(pg)
        d.text((M, 52), f"POST {i + 1} / {len(rows)}    {(r.get('pillar') or '').upper()}", font=hfont, fill=INK)
        d.line([(M, 120), (W - M, 120)], fill=(210, 200, 188), width=2)
        imgs = r.get("image_urls") or []
        x = M
        for u in (imgs[:3] if isinstance(imgs, list) else []):
            try:
                raw = urllib.request.urlopen(u, timeout=25).read()
                pg.paste(Image.open(io.BytesIO(raw)).convert("RGB").resize((SW, SH)), (x, SY))
            except Exception:
                d.rectangle([x, SY, x + SW, SY + SH], outline=(200, 190, 178), width=2)
            x += SW + GAP
        cy = SY + SH + 34
        for ln in _wrap(d, (r.get("caption") or "").strip(), cfont, W - 2 * M)[:6]:
            d.text((M, cy), ln, font=cfont, fill=INK)
            cy += 40
        tags = r.get("hashtags")
        tags = " ".join(tags) if isinstance(tags, list) else (tags or "")
        for ln in _wrap(d, tags, tfont, W - 2 * M)[:2]:
            d.text((M, cy + 8), ln, font=tfont, fill=TAG)
            cy += 32
        pages.append(pg)
    out = os.path.join(tempfile.gettempdir(), f"ig_strategy_{track}.pdf")
    if pages:
        pages[0].save(out, save_all=True, append_images=pages[1:], resolution=150.0)
    return out, len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", choices=list(TRACK_PILLARS), default="void")
    ap.add_argument("--limit", type=int, default=12)
    ap.add_argument("--open", action="store_true", help="open the output in a browser/viewer")
    ap.add_argument("--pdf", action="store_true", help="also render a landscape PDF (1 post per page)")
    args = ap.parse_args()
    _load_env()
    path, n = build(args.track, args.limit)
    print(f"WROTE {path} ({n} drafts)")
    if args.pdf:
        pdf, _ = build_pdf(args.track, args.limit)
        print(f"WROTE {pdf}")
        if args.open:
            webbrowser.open("file:///" + pdf.replace("\\", "/"))
    if args.open:
        webbrowser.open("file:///" + path.replace("\\", "/"))


if __name__ == "__main__":
    main()
