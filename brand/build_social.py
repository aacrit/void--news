#!/usr/bin/env python3
"""Social kit: on-brand avatars + banners, correctly sized, mark centred/safe.

  YouTube  (Void Vision, brass)  avatar 800x800 + banner 2560x1440 (safe 1546x423)
  Instagram(Void News, terracotta) avatar 320x320
  X/Twitter(Void News)           avatar 400x400 + header 1500x500
  Bluesky  (Void News)           avatar 512x512 + banner 3000x1000

Avatars: Sigil centred on a solid brand ground, kept inside the circular-crop
safe zone. Banners: the horizontal lockup centred inside each platform's safe
area. Grounds: Evening ink (#14120F) or Morning paper (#F0EBDD).
"""
import os, json, subprocess, tempfile
from PIL import Image
from _sigil_draw import render_sigil

HERE = os.path.dirname(os.path.abspath(__file__))
LOGOS = os.path.join(HERE, "logos")
OUT = os.path.join(HERE, "social")
RENDER = os.path.join(HERE, "ci", "render_svg.mjs")
os.makedirs(OUT, exist_ok=True)

INK = (20, 18, 15, 255)      # #14120F Evening ink
PAPER = (240, 235, 221, 255)  # #F0EBDD Morning paper
NEWS = "#B26F52"
NEWS_DARK = "#D89A7C"
VISION_DARK = "#D4A574"       # brass, dark-accent for contrast on ink

# --- render the transparent lockups the banners need (hi-res, chromium) -----
tmp = os.path.join(tempfile.gettempdir(), "void_social_hires")
os.makedirs(tmp, exist_ok=True)
jobs = [
    {"svg": os.path.join(LOGOS, "void-vision-horizontal-reversed.svg"),
     "out": os.path.join(tmp, "vision-reversed.png"), "width": 2600},
    {"svg": os.path.join(LOGOS, "void-news-horizontal-color.svg"),
     "out": os.path.join(tmp, "news-color.png"), "width": 2600},
]
jp = os.path.join(tmp, "jobs.json")
json.dump(jobs, open(jp, "w"))
print("rendering banner lockups via chromium...")
subprocess.run(["node", RENDER, jp], cwd=HERE, check=True)
VISION_LOCKUP = os.path.join(tmp, "vision-reversed.png")
NEWS_LOCKUP = os.path.join(tmp, "news-color.png")


def avatar(px, sigil_color, ground, name):
    pad = round(px * 0.19)  # Sigil ~62% of frame, safe inside circular crop
    canvas = Image.new("RGBA", (px, px), ground)
    canvas.alpha_composite(render_sigil(px, sigil_color, pad=pad), (0, 0))
    canvas.save(os.path.join(OUT, name))
    return canvas.size


def banner(cw, ch, lockup_png, ground, name, safe_w=None, safe_h=None,
           max_frac=0.78):
    canvas = Image.new("RGBA", (cw, ch), ground)
    lk = Image.open(lockup_png).convert("RGBA")
    box_w = round((safe_w or cw) * max_frac)
    box_h = round((safe_h or ch) * (0.62 if safe_h else 0.42))
    scale = min(box_w / lk.width, box_h / lk.height)
    lk = lk.resize((round(lk.width * scale), round(lk.height * scale)), Image.LANCZOS)
    canvas.alpha_composite(lk, ((cw - lk.width) // 2, (ch - lk.height) // 2))
    canvas.save(os.path.join(OUT, name))
    return canvas.size


results = []
# YouTube - Void Vision (brass)
results.append(("youtube-void-vision-avatar-800.png",
                avatar(800, VISION_DARK, INK, "youtube-void-vision-avatar-800.png")))
results.append(("youtube-void-vision-banner-2560x1440.png",
                banner(2560, 1440, VISION_LOCKUP, INK,
                       "youtube-void-vision-banner-2560x1440.png",
                       safe_w=1546, safe_h=423)))
# Instagram - Void News
results.append(("instagram-void-news-avatar-320.png",
                avatar(320, NEWS, PAPER, "instagram-void-news-avatar-320.png")))
# X/Twitter - Void News
results.append(("x-void-news-avatar-400.png",
                avatar(400, NEWS, PAPER, "x-void-news-avatar-400.png")))
results.append(("x-void-news-header-1500x500.png",
                banner(1500, 500, NEWS_LOCKUP, PAPER,
                       "x-void-news-header-1500x500.png", max_frac=0.72)))
# Bluesky - Void News
results.append(("bluesky-void-news-avatar-512.png",
                avatar(512, NEWS, PAPER, "bluesky-void-news-avatar-512.png")))
results.append(("bluesky-void-news-banner-3000x1000.png",
                banner(3000, 1000, NEWS_LOCKUP, PAPER,
                       "bluesky-void-news-banner-3000x1000.png", max_frac=0.66)))

print(f"wrote {len(results)} social assets -> {os.path.relpath(OUT, HERE)}")
for n, sz in results:
    print(f"  {n}  {sz[0]}x{sz[1]}")
