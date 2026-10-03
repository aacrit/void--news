#!/usr/bin/env python3
"""
Shared Pillow drawing of the Void Sigil (pure geometry).

The Sigil = coverage ring + level balance beam with |-| end ticks + footed
post/base. Geometry is lifted verbatim from the SVG masters (generate.py) and
frontend/app/components/ScaleIcon.tsx so the raster never drifts from vector.

Everything is drawn at SS x supersample and LANCZOS-downscaled for crisp,
anti-aliased edges with no browser dependency. The beam group (beam + two
ticks) can be rotated about the ring centre (50,40) to animate the sweep.
"""

from PIL import Image, ImageDraw
import math

SS = 4  # supersample factor

# --- Sigil geometry in the 100x100 viewBox (matches the SVG masters) --------
RING = dict(cx=50, cy=40, r=30, sw=8)
BEAM = dict(x1=12, y1=40, x2=88, y2=40, sw=6)
TICK_L = dict(x1=12, y1=32, x2=12, y2=48, sw=5)
TICK_R = dict(x1=88, y1=32, x2=88, y2=48, sw=5)
POST = dict(x1=50, y1=70, x2=50, y2=86, sw=6)
FOOT = dict(p0=(36, 93), c1=(44, 88), c2=(56, 88), p3=(64, 93), sw=6)
BEAM_PIVOT = (50, 40)


def _rgba(c):
    if isinstance(c, tuple):
        return c if len(c) == 4 else (c[0], c[1], c[2], 255)
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), 255)


def _rot(p, pivot, deg):
    if deg == 0:
        return p
    a = math.radians(deg)
    px, py = pivot
    dx, dy = p[0] - px, p[1] - py
    return (px + dx * math.cos(a) - dy * math.sin(a),
            py + dx * math.sin(a) + dy * math.cos(a))


class _Sigil:
    """Coordinate mapper + primitive drawer for one canvas."""

    def __init__(self, px, pad, ss=SS):
        self.px = px
        self.ss = ss
        drawable = px - 2 * pad
        self.scale = drawable * ss / 100.0
        self.off = pad * ss

    def M(self, p):
        return (self.off + p[0] * self.scale, self.off + p[1] * self.scale)

    def W(self, w):
        return w * self.scale

    def rline(self, d, p1, p2, sw, color):
        a, b = self.M(p1), self.M(p2)
        w = self.W(sw)
        d.line([a, b], fill=color, width=max(1, int(round(w))))
        r = w / 2.0
        for (x, y) in (a, b):  # round caps
            d.ellipse([x - r, y - r, x + r, y + r], fill=color)

    def ring(self, d, color):
        c = self.M((RING["cx"], RING["cy"]))
        # stroke centred on r: outer bbox = r + sw/2, Pillow grows width inward
        r_out = self.W(RING["r"] + RING["sw"] / 2.0)
        w = max(1, int(round(self.W(RING["sw"]))))
        d.ellipse([c[0] - r_out, c[1] - r_out, c[0] + r_out, c[1] + r_out],
                  outline=color, width=w)

    def foot(self, d, color):
        p0, c1, c2, p3 = FOOT["p0"], FOOT["c1"], FOOT["c2"], FOOT["p3"]
        w = self.W(FOOT["sw"])
        r = w / 2.0
        n = 28
        pts = []
        for i in range(n + 1):
            t = i / n
            mt = 1 - t
            x = mt**3 * p0[0] + 3 * mt**2 * t * c1[0] + 3 * mt * t**2 * c2[0] + t**3 * p3[0]
            y = mt**3 * p0[1] + 3 * mt**2 * t * c1[1] + 3 * mt * t**2 * c2[1] + t**3 * p3[1]
            pts.append(self.M((x, y)))
        d.line(pts, fill=color, width=max(1, int(round(w))), joint="curve")
        for (x, y) in (pts[0], pts[-1]):  # round caps
            d.ellipse([x - r, y - r, x + r, y + r], fill=color)


def render_sigil(px, stroke, *, beam_stroke=None, beam_angle_deg=0.0,
                 bg=None, pad=0, ss=SS):
    """Render the footed Sigil to an RGBA PIL Image of size px x px.

    stroke        colour of the static parts (ring, post, foot) + default beam
    beam_stroke   colour of the beam+ticks (defaults to stroke)
    beam_angle_deg tilt of the beam group about the ring centre
    bg            background fill (None = transparent)
    pad           padding in final px on every side around the 100-box
    """
    stroke = _rgba(stroke)
    beam_stroke = _rgba(beam_stroke) if beam_stroke is not None else stroke
    big = px * ss
    img = Image.new("RGBA", (big, big), _rgba(bg) if bg is not None else (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    S = _Sigil(px, pad, ss)

    # static: ring + post + foot
    S.ring(d, stroke)
    S.rline(d, (POST["x1"], POST["y1"]), (POST["x2"], POST["y2"]), POST["sw"], stroke)
    S.foot(d, stroke)

    # beam group (rotatable): beam + two ticks
    ang = beam_angle_deg
    b1 = _rot((BEAM["x1"], BEAM["y1"]), BEAM_PIVOT, ang)
    b2 = _rot((BEAM["x2"], BEAM["y2"]), BEAM_PIVOT, ang)
    S.rline(d, b1, b2, BEAM["sw"], beam_stroke)
    for tk in (TICK_L, TICK_R):
        t1 = _rot((tk["x1"], tk["y1"]), BEAM_PIVOT, ang)
        t2 = _rot((tk["x2"], tk["y2"]), BEAM_PIVOT, ang)
        S.rline(d, t1, t2, tk["sw"], beam_stroke)

    return img.resize((px, px), Image.LANCZOS)


if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(__file__), "_geom_check.png")
    render_sigil(512, "#B26F52", bg="#F0EBDD").save(out)
    print("wrote", out)
