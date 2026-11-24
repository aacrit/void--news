#!/usr/bin/env bash
# Assemble the Sigil animation into MP4 (H.264) + WebM (VP9, alpha) from the
# frame PNGs in video/frames/. Requires a FULL ffmpeg build (libx264 +
# libvpx-vp9 + png decoder + image2 demuxer).
#
# The Playwright-bundled ffmpeg on the dev box is a capture-only VP8 build that
# CANNOT decode PNGs, so build_video.py delivers the GIF + frames and defers the
# real encodes to this script. Run in CI (ubuntu-latest ships a full ffmpeg):
#
#   sudo apt-get install -y ffmpeg      # if not present
#   bash brand/render-video.sh
#
set -euo pipefail
cd "$(dirname "$0")/video"

FPS=20            # 88 frames / 4.4s
FRAMES="frames/frame_%03d.png"
INK="#14120F"

command -v ffmpeg >/dev/null || { echo "ffmpeg not found"; exit 1; }

# MP4 (H.264) on Evening-ink ground -- mp4 has no alpha
mkdir -p _ink
python3 - <<'PY'
from PIL import Image; import os
os.makedirs("_ink", exist_ok=True)
for i in range(len(os.listdir("frames"))):
    f=f"frames/frame_{i:03d}.png"
    if not os.path.exists(f): break
    r=Image.open(f).convert("RGBA"); c=Image.new("RGBA",r.size,(20,18,15,255))
    c.alpha_composite(r); c.convert("RGB").save(f"_ink/f_{i:03d}.png")
PY
ffmpeg -y -framerate $FPS -i "_ink/f_%03d.png" \
  -c:v libx264 -pix_fmt yuv420p -crf 18 -movflags +faststart \
  void-news-sigil-ink.mp4
rm -rf _ink

# WebM (VP9) with alpha -- transparent loop
ffmpeg -y -framerate $FPS -i "$FRAMES" \
  -c:v libvpx-vp9 -pix_fmt yuva420p -crf 24 -b:v 0 -auto-alt-ref 0 \
  void-news-sigil-alpha.webm

echo "wrote void-news-sigil-ink.mp4 + void-news-sigil-alpha.webm"
