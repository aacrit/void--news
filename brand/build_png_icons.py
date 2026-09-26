#!/usr/bin/env python3
"""PNG matrix: the footed Sigil ICON for all four brands, drawn in Pillow.

Per brand: transparent at 16/32/48/64/128/256/512/1024, plus 512 on the
Morning paper ground (#F0EBDD) and 512 on the Evening ink ground (#14120F).
On the dark ground the brand's dark-mode accent is used for contrast.
"""
import os
from _sigil_draw import render_sigil

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "logos", "png")
os.makedirs(OUT, exist_ok=True)

LIGHT_GROUND = "#F0EBDD"
DARK_GROUND = "#14120F"

BRANDS = {
    "void-news":    {"light": "#B26F52", "dark": "#D89A7C"},
    "void-history": {"light": "#5C4033", "dark": "#8B7355"},
    "void-weekly":  {"light": "#B91C1C", "dark": "#EF5350"},
    "void-vision":  {"light": "#946B15", "dark": "#D4A574"},
}

SIZES = [16, 32, 48, 64, 128, 256, 512, 1024]
count = 0
for slug, c in BRANDS.items():
    for s in SIZES:
        # tiny sizes need a hair of padding so round caps do not clip
        pad = 1 if s <= 32 else 0
        img = render_sigil(s, c["light"], pad=pad)
        img.save(os.path.join(OUT, f"{slug}-icon-{s}.png"))
        count += 1
    # 512 on grounds
    render_sigil(512, c["light"], bg=LIGHT_GROUND, pad=52).save(
        os.path.join(OUT, f"{slug}-icon-512-light.png")); count += 1
    render_sigil(512, c["dark"], bg=DARK_GROUND, pad=52).save(
        os.path.join(OUT, f"{slug}-icon-512-dark.png")); count += 1

print(f"wrote {count} icon PNGs -> {os.path.relpath(OUT, HERE)}")
