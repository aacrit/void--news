#!/usr/bin/env python3
"""Animated Sigil beam-sweep -> frame PNGs + GIF (+ MP4/WebM if ffmpeg present).

The beam group sweeps: accent (level) -> blue (left) -> green (centre) ->
red (right) -> accent, a 4.4s seamless loop, matching the animated SVG master
keyframes. Static ring/post/foot stay the brand accent; only the beam tilts and
crosses the lean spectrum. Angle eased per segment; colour linearly blended.

Outputs (Void News accent), 512x512:
  video/frames/frame_###.png     transparent RGBA source frames
  video/void-news-sigil-ink.gif      seamless loop on Evening ink
  video/void-news-sigil-transparent.gif  seamless loop, 1-bit transparency
  video/void-news-sigil-ink.mp4      H.264 (if ffmpeg)
  video/void-news-sigil-alpha.webm   VP9 + alpha (if ffmpeg)
"""
import os, math, shutil, subprocess
from PIL import Image
from _sigil_draw import render_sigil

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "video")
FRAMES = os.path.join(OUT, "frames")
os.makedirs(FRAMES, exist_ok=True)

ACCENT = "#B26F52"
LEFT = "#3F72B0"
CENTER = "#3E7C57"
RIGHT = "#B0433B"
INK = (20, 18, 15, 255)  # #14120F

PX = 512
N = 88                    # frames
DUR_S = 4.4
FPS = N / DUR_S           # ~20 fps
GIF_MS = round(1000 * DUR_S / N)

# keyframes: (phase, angle_deg, color)
KF = [(0.00, 0, ACCENT), (0.20, -15, LEFT), (0.45, 0, CENTER),
      (0.70, 15, RIGHT), (0.88, 0, ACCENT), (1.00, 0, ACCENT)]


def _hex(c):
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def ease(t):  # ~cubic-bezier(0.22,1,0.36,1), easeOutQuint-ish
    return 1 - (1 - t) ** 4


def sample(p):
    for i in range(len(KF) - 1):
        p0, a0, c0 = KF[i]
        p1, a1, c1 = KF[i + 1]
        if p0 <= p <= p1:
            t = 0 if p1 == p0 else (p - p0) / (p1 - p0)
            e = ease(t)
            ang = a0 + (a1 - a0) * e
            r0, g0, b0 = _hex(c0)
            r1, g1, b1 = _hex(c1)
            col = (round(r0 + (r1 - r0) * e),
                   round(g0 + (g1 - g0) * e),
                   round(b0 + (b1 - b0) * e), 255)
            return ang, col
    return 0, (_hex(ACCENT) + (255,))


print(f"rendering {N} frames @ {PX}px...")
for i in range(N):
    p = i / N
    ang, col = sample(p)
    img = render_sigil(PX, ACCENT, beam_stroke=col, beam_angle_deg=ang, pad=24)
    img.save(os.path.join(FRAMES, f"frame_{i:03d}.png"))

# --- GIF: ink ground (clean) + transparent (1-bit) --------------------------
ink_frames, tpt_frames = [], []
for i in range(N):
    rgba = Image.open(os.path.join(FRAMES, f"frame_{i:03d}.png")).convert("RGBA")
    ink = Image.new("RGBA", rgba.size, INK)
    ink.alpha_composite(rgba)
    ink_frames.append(ink.convert("P", palette=Image.ADAPTIVE, colors=128))
    # transparent: paste on a magenta key, quantize, set transparency
    key = (255, 0, 255)
    flat = Image.new("RGB", rgba.size, key)
    flat.paste(rgba, (0, 0), rgba)
    q = flat.convert("P", palette=Image.ADAPTIVE, colors=255)
    tpt_frames.append(q)

ink_frames[0].save(os.path.join(OUT, "void-news-sigil-ink.gif"), save_all=True,
                   append_images=ink_frames[1:], duration=GIF_MS, loop=0,
                   optimize=True, disposal=2)
# transparency index = palette entry nearest magenta
pal = tpt_frames[0].getpalette() or []
key_idx = 0
best = 1e9
for idx in range(len(pal) // 3):
    r, g, b = pal[idx*3:idx*3+3]
    d = (r-255)**2 + g**2 + (b-255)**2
    if d < best:
        best, key_idx = d, idx
tpt_frames[0].save(os.path.join(OUT, "void-news-sigil-transparent.gif"),
                   save_all=True, append_images=tpt_frames[1:], duration=GIF_MS,
                   loop=0, transparency=key_idx, disposal=2)
print("wrote 2 GIFs")

# --- MP4 + WebM via ffmpeg (playwright build or PATH) -----------------------
def find_ffmpeg():
    p = shutil.which("ffmpeg")
    if p:
        return p
    import glob
    cands = glob.glob(os.path.expanduser(
        "~/AppData/Local/ms-playwright/ffmpeg-*/ffmpeg-win64.exe"))
    return cands[0] if cands else None


def ffmpeg_can_encode(ff):
    """A usable build must decode PNG, demux an image sequence, and encode
    at least one video codec. Playwright's bundled ffmpeg is a capture-only
    VP8 build (no PNG decoder, no image2 demuxer) -- it fails this probe."""
    dec = subprocess.run([ff, "-hide_banner", "-decoders"],
                         capture_output=True, text=True).stdout
    dem = subprocess.run([ff, "-hide_banner", "-demuxers"],
                         capture_output=True, text=True).stdout
    enc = subprocess.run([ff, "-hide_banner", "-encoders"],
                         capture_output=True, text=True).stdout
    png_dec = " png " in dec or "\tpng" in dec
    img2 = "image2" in dem and "image2pipe" not in dem.replace("image2 ", "")
    has_x264 = "libx264" in enc
    has_vp9 = "libvpx-vp9" in enc
    can = png_dec and ("image2" in dem) and (has_x264 or has_vp9)
    return can, has_x264, has_vp9


ff = find_ffmpeg()
did_video = False
if ff:
    ok, has_x264, has_vp9 = ffmpeg_can_encode(ff)
    if ok:
        print(f"ffmpeg (encode-capable): {ff}")
        pattern = os.path.join(FRAMES, "frame_%03d.png")
        fps = f"{FPS:.4f}"
        if has_vp9:
            subprocess.run([ff, "-y", "-framerate", fps, "-i", pattern,
                            "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
                            "-crf", "24", "-b:v", "0", "-auto-alt-ref", "0",
                            os.path.join(OUT, "void-news-sigil-alpha.webm")],
                           check=True, capture_output=True)
            print("wrote WebM (VP9 alpha)"); did_video = True
        if has_x264:
            ink_dir = os.path.join(OUT, "_inkframes")
            os.makedirs(ink_dir, exist_ok=True)
            for i in range(N):
                rgba = Image.open(os.path.join(FRAMES, f"frame_{i:03d}.png")).convert("RGBA")
                c = Image.new("RGBA", rgba.size, INK); c.alpha_composite(rgba)
                c.convert("RGB").save(os.path.join(ink_dir, f"f_{i:03d}.png"))
            subprocess.run([ff, "-y", "-framerate", fps, "-i",
                            os.path.join(ink_dir, "f_%03d.png"),
                            "-c:v", "libx264", "-pix_fmt", "yuv420p",
                            "-crf", "18", "-movflags", "+faststart",
                            os.path.join(OUT, "void-news-sigil-ink.mp4")],
                           check=True, capture_output=True)
            shutil.rmtree(ink_dir, ignore_errors=True)
            print("wrote MP4 (H.264 ink)"); did_video = True

if not did_video:
    print("MP4/WebM DEFERRED: no encode-capable ffmpeg on this box. The only "
          "ffmpeg present is Playwright's capture-only VP8 build (no PNG "
          "decoder / no image2 demuxer / no x264|vp9). GIF + frame PNGs are "
          "delivered; run brand/render-video.sh with a full ffmpeg (CI) to "
          "produce MP4 + WebM from the frames.")

# report sizes
for f in sorted(os.listdir(OUT)):
    fp = os.path.join(OUT, f)
    if os.path.isfile(fp):
        print(f"  {f}  {os.path.getsize(fp)//1024} KB")
print(f"frames: {len(os.listdir(FRAMES))} PNGs")
