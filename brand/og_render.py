#!/usr/bin/env python3
"""
Void News social share card (OpenGraph / Twitter) - 1200x630 PNG.

Deep-ink (walnut) ground, terracotta footed Sigil hero + "VOID NEWS" serif
lockup (NEWS in terracotta), the bias spectrum, the tagline "See through the
void." and the canonical domain news.voidvision.org.

Drawn with Pillow at 3x supersample then LANCZOS-downsampled to 1200x630 for
crisp edges. Sigil geometry is lifted verbatim from brand/generate.py
(_icon_paths, the ScaleIcon footed geometry).

    python brand/og_render.py
"""

import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.path.join(HERE, "..", "frontend", "public", "og-image.png"))

W, H = 1200, 630
SS = 3  # supersample
CW, CH = W * SS, H * SS

# --- Palette (Evening Edition / walnut, from brand/color/palette.md) ---
WALNUT = (28, 26, 23)        # #1C1A17 page canvas
WALNUT_CARD = (37, 35, 32)   # #252320
CREAM = (237, 232, 224)      # #EDE8E0 ink primary (dark mode)
CREAM_MUTED = (184, 176, 165)  # #B8B0A5 ink secondary
META = (122, 116, 108)       # muted meta
RULE = (74, 69, 64)          # #4A4540
TERRA = (216, 154, 124)      # #D89A7C News terracotta (dark)

# Bias spectrum (dark-mode retuned, palette.md section 2)
SPECTRUM = [
    (80, 136, 208),   # far/left blue  #5088D0
    (100, 152, 216),  # left           #6498D8
    (72, 184, 112),   # center green   #48B870
    (208, 92, 72),    # right          #D05C48
    (176, 46, 38),    # far right      #B02E26
]

WIN = r"C:\Windows\Fonts"


def font(name, size):
    return ImageFont.truetype(os.path.join(WIN, name), size * SS)


serif_bold = lambda s: font("georgiab.ttf", s)
sans = lambda s: font("arial.ttf", s)
mono = lambda s: font("consola.ttf", s)


def rcap_line(d, x1, y1, x2, y2, width, fill):
    """Line with round caps (PIL line has no caps; add end dots)."""
    w = int(round(width * SS))
    d.line([(x1 * SS, y1 * SS), (x2 * SS, y2 * SS)], fill=fill, width=w)
    r = w / 2
    for (x, y) in ((x1, y1), (x2, y2)):
        cx, cy = x * SS, y * SS
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)


def ring(d, cx, cy, r, width, fill):
    """Stroked circle of given stroke width."""
    w = width * SS
    cx, cy, r = cx * SS, cy * SS, r * SS
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=fill, width=int(round(w)))


def cubic(p0, p1, p2, p3, steps=48):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1 - t
        x = (mt**3) * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t**3 * p3[0]
        y = (mt**3) * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t**3 * p3[1]
        pts.append((x, y))
    return pts


def sigil(d, ox, oy, scale, stroke):
    """Footed Sigil (ScaleIcon geometry, 100x100 box) at (ox,oy) * scale.
    Maps local box coords to canvas via L() then draws at SS resolution."""
    def L(x, y):
        return (ox + x * scale, oy + y * scale)

    def line(x1, y1, x2, y2, sw):
        rcap_line(d, *L(x1, y1), *L(x2, y2), sw * scale, stroke)

    # ring: circle cx50 cy40 r30 sw8
    ring(d, ox / SS + 0, 0, 0, 0, stroke) if False else None
    cx, cy = L(50, 40)
    rr = 30 * scale
    d.ellipse([(cx - rr) * SS, (cy - rr) * SS, (cx + rr) * SS, (cy + rr) * SS],
              outline=stroke, width=int(round(8 * scale * SS)))
    # beam + ticks + post
    line(12, 40, 88, 40, 6)
    line(12, 32, 12, 48, 5)
    line(88, 32, 88, 48, 5)
    line(50, 70, 50, 86, 6)
    # base curve M36 93 C44 88 56 88 64 93
    pts = cubic(L(36, 93), L(44, 88), L(56, 88), L(64, 93))
    w = int(round(6 * scale * SS))
    d.line([(x * SS, y * SS) for (x, y) in pts], fill=stroke, width=w, joint="curve")
    r = w / 2
    for (x, y) in (pts[0], pts[-1]):
        d.ellipse([x * SS - r, y * SS - r, x * SS + r, y * SS + r], fill=stroke)


def center_text(d, cx, y, text, fnt, fill, tracking=0.0):
    """Draw text centered on cx at baseline-ish top y, with optional px tracking."""
    if tracking == 0:
        bbox = d.textbbox((0, 0), text, font=fnt)
        tw = bbox[2] - bbox[0]
        d.text((cx * SS - tw / 2 - bbox[0], y * SS), text, font=fnt, fill=fill)
        return tw / SS
    # letter-spaced
    tr = tracking * SS
    widths = []
    for ch in text:
        b = d.textbbox((0, 0), ch, font=fnt)
        widths.append(b[2] - b[0])
    total = sum(widths) + tr * (len(text) - 1)
    x = cx * SS - total / 2
    for ch, wch in zip(text, widths):
        b = d.textbbox((0, 0), ch, font=fnt)
        d.text((x - b[0], y * SS), ch, font=fnt, fill=fill)
        x += wch + tr
    return total / SS


def draw_wordmark(d, cx, y):
    """VOID NEWS - Georgia bold caps, VOID cream + NEWS terracotta, tracked."""
    fnt = serif_bold(84)
    tr = 3 * SS
    gap = 26 * SS  # space between VOID and NEWS
    parts = [("VOID", CREAM), ("NEWS", TERRA)]
    # measure
    seg = []
    for word, col in parts:
        chs = []
        for ch in word:
            b = d.textbbox((0, 0), ch, font=fnt)
            chs.append((ch, b[2] - b[0], b[0]))
        wsum = sum(c[1] for c in chs) + tr * (len(word) - 1)
        seg.append((chs, col, wsum))
    total = seg[0][2] + gap + seg[1][2]
    x = cx * SS - total / 2
    for chs, col, wsum in seg:
        for ch, wch, bx in chs:
            d.text((x - bx, y * SS), ch, font=fnt, fill=col)
            x += wch + tr
        x += gap - tr
    return total / SS


def main():
    img = Image.new("RGB", (CW, CH), WALNUT)
    d = ImageDraw.Draw(img)

    # top masthead rules
    d.line([(120 * SS, 78 * SS), (1080 * SS, 78 * SS)], fill=RULE, width=1 * SS)
    d.line([(120 * SS, 83 * SS), (1080 * SS, 83 * SS)], fill=RULE, width=3 * SS)

    # eyebrow (small mono, top-left inside rule)
    d.text((120 * SS, 44 * SS), "AN  EXPERIMENTAL  NEWSROOM", font=mono(15),
           fill=META)

    # hero Sigil - terracotta, centered. Box 100 units, scale ~2.15.
    hs = 2.15
    box = 100 * hs
    sigil(d, 600 - box / 2, 118, hs, TERRA)

    # wordmark
    draw_wordmark(d, 600, 360)

    # bias spectrum dots (5), centered, connecting hairline
    n = len(SPECTRUM)
    step = 118
    span = step * (n - 1)
    x0 = 600 - span / 2
    yb = 470
    # connectors first
    for i in range(n - 1):
        ax = x0 + step * i
        d.line([((ax + 16) * SS, yb * SS), ((ax + step - 16) * SS, yb * SS)],
               fill=(58, 53, 48), width=2 * SS)
    for i, col in enumerate(SPECTRUM):
        cx = (x0 + step * i) * SS
        cy = yb * SS
        r = 10 * SS
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col)
    # spectrum labels
    center_text(d, x0, yb + 26, "LEFT", mono(12), META)
    center_text(d, 600, yb + 26, "CENTER", mono(12), META)
    center_text(d, x0 + span, yb + 26, "RIGHT", mono(12), META)

    # tagline
    center_text(d, 600, 512, "See through the void.", serif_bold(30), CREAM_MUTED)

    # bottom rule
    d.line([(120 * SS, 556 * SS), (1080 * SS, 556 * SS)], fill=RULE, width=1 * SS)

    # footer: domain + stats
    center_text(d, 600, 578, "news.voidvision.org", mono(15), TERRA, tracking=2)
    center_text(d, 600, 600, "1,016 SOURCES   6-AXIS BIAS ANALYSIS   FREE & OPEN",
                mono(12), META, tracking=1)

    out = img.resize((W, H), Image.LANCZOS)
    out.save(OUT, "PNG")
    print("wrote", OUT, out.size)


if __name__ == "__main__":
    main()
