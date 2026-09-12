#!/usr/bin/env python3
"""PNG horizontal lockups at ~800 and ~1600 wide (transparent + light + dark).

Renders the SVG horizontal masters via Playwright chromium (one hi-res render
per treatment per brand) then derives every size + ground composite in Pillow.
  transparent : color lockup, no ground
  light       : color lockup on Morning paper (#F0EBDD)
  dark        : reversed (white) lockup on Evening ink (#14120F)

Font: the SVG font stack resolves to Georgia on this box (Playfair Display not
installed). See README -- run this in CI with Playfair present for pixel-perfect
lockups; the geometry (Sigil-O) is already exact.
"""
import os, json, subprocess, tempfile
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
LOGOS = os.path.join(HERE, "logos")
OUT = os.path.join(LOGOS, "png")
RENDER = os.path.join(HERE, "ci", "render_svg.mjs")
os.makedirs(OUT, exist_ok=True)

LIGHT_GROUND = (240, 235, 221, 255)  # #F0EBDD
DARK_GROUND = (20, 18, 15, 255)      # #14120F
BRANDS = ["void-news", "void-history", "void-weekly", "void-vision"]
WIDTHS = [800, 1600]
HIRES = 3200  # single hi-res render, downscaled per target

hires_dir = os.path.join(tempfile.gettempdir(), "void_lockup_hires")
os.makedirs(hires_dir, exist_ok=True)

# 1) render color + reversed horizontal masters hi-res via chromium
jobs = []
for slug in BRANDS:
    for treat in ("color", "reversed"):
        jobs.append({
            "svg": os.path.join(LOGOS, f"{slug}-horizontal-{treat}.svg"),
            "out": os.path.join(hires_dir, f"{slug}-{treat}.png"),
            "width": HIRES,
        })
jobs_path = os.path.join(hires_dir, "jobs.json")
with open(jobs_path, "w") as f:
    json.dump(jobs, f)
print("rendering hi-res lockups via chromium...")
subprocess.run(["node", RENDER, jobs_path], cwd=HERE, check=True)


def fit_width(src, w):
    im = Image.open(src).convert("RGBA")
    h = round(w * im.height / im.width)
    return im.resize((w, h), Image.LANCZOS)


def on_ground(lockup, canvas_w, ground):
    inset = round(canvas_w * 0.09)          # side clear space
    content_w = canvas_w - 2 * inset
    lk = lockup.resize((content_w, round(content_w * lockup.height / lockup.width)),
                       Image.LANCZOS)
    vpad = round(lk.height * 0.6)           # top/bottom clear space
    canvas_h = lk.height + 2 * vpad
    canvas = Image.new("RGBA", (canvas_w, canvas_h), ground)
    canvas.alpha_composite(lk, (inset, vpad))
    return canvas


count = 0
for slug in BRANDS:
    color_hi = os.path.join(hires_dir, f"{slug}-color.png")
    rev_hi = os.path.join(hires_dir, f"{slug}-reversed.png")
    for w in WIDTHS:
        # transparent (color)
        t = fit_width(color_hi, w)
        t.save(os.path.join(OUT, f"{slug}-horizontal-{w}.png")); count += 1
        # light ground (color)
        on_ground(Image.open(color_hi).convert("RGBA"), w, LIGHT_GROUND).save(
            os.path.join(OUT, f"{slug}-horizontal-{w}-light.png")); count += 1
        # dark ground (reversed)
        on_ground(Image.open(rev_hi).convert("RGBA"), w, DARK_GROUND).save(
            os.path.join(OUT, f"{slug}-horizontal-{w}-dark.png")); count += 1

print(f"wrote {count} lockup PNGs -> {os.path.relpath(OUT, HERE)}")
