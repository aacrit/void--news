# Void - Brand Pack

The foundation of the Void brand identity: logo masters, color system, type,
guidelines, and a one-stop showcase page. One parent brand (**Void**) with four
product editions - **News**, **History**, **Weekly**, **Vision** - that share
the Sigil-O mark and swap only the accent color and the product word.

Open **[`index.html`](index.html)** in any browser (works offline from the
filesystem) for the full visual pack with live marks, copyable swatches, type
specimens, and a download link to every asset.

---

## Folder structure

```
brand/
  index.html            One-stop showcase (self-contained, theme-aware, offline)
  README.md             This file
  generate.py           Regenerates all logo SVG masters + the animated SVG
  _sigil_draw.py        Pillow Sigil geometry (shared: icons, social, animation)
  build_png_icons.py    Phase 2 - icon PNG matrix (Pillow, all sizes)
  build_png_lockups.py  Phase 2 - lockup PNGs (chromium render of SVG masters)
  build_social.py       Phase 2 - platform avatars + banners
  build_video.py        Phase 2 - animation frames + GIF (+ MP4/WebM if capable ffmpeg)
  render-video.sh       CI: MP4 + WebM from frames with a full ffmpeg
  logos/                36 SVG masters (4 brands x 3 assets x 3 treatments)
    png/                64 raster exports (40 icons + 24 lockups)
  social/               7 platform assets (YouTube, Instagram, X, Bluesky)
  video/                2 GIFs + 88 frame PNGs (MP4/WebM via render-video.sh)
  animated/             Living Sigil - animated SVG + Lottie JSON
  color/                colors.css, colors.json, palette.md
  type/                 type.md (specimen + scale + pairing rules)
  guidelines/           guidelines.md + guidelines-print.html + void-brand-book.pdf
  ci/                   render_svg.mjs, render_pdf.mjs (chromium renderers)
```

### logos/ naming

`{brand}-{asset}-{treatment}.svg`

- **brand**: `void-news` `void-history` `void-weekly` `void-vision`
- **asset**:
  - `horizontal` - full lockup, `V[Sigil-O]ID PRODUCT` (Sigil replaces the O). Primary.
  - `wordmark` - `VOID PRODUCT` in Playfair, no Sigil.
  - `icon` - the footed Sigil alone, square 100x100.
- **treatment**: `color` (brand accent) / `black` (`#111`) / `reversed` (white)

Example: `logos/void-news-horizontal-color.svg`

That is **9 SVGs per brand x 4 brands = 36 logo files**, plus the animated
Sigil (SVG + Lottie).

---

## The Sigil (what the mark means)

- **Coverage ring** - breadth of sources. The hollow lens, the "void," the O in VOID.
- **Level balance beam + `|-|` ticks** - the bias measurement. Level = balanced.
- **Foot (post + base)** - the lens/stand, the method. It never tilts.

Geometry is lifted verbatim from the running product so the pack never drifts:
- `frontend/app/components/ScaleIcon.tsx` - footed Sigil (the icon).
- `frontend/app/components/SigilWordmark.tsx` - inline Sigil-O (foot descends below the baseline).

All SVGs use **explicit fills/strokes** - no CSS variables, no `currentColor` -
so they are portable into any tool. The wordmark and lockup use live `<text>`
with the Playfair Display / Georgia / serif fallback stack (see Phase 2 for
outlining to paths).

---

## Regenerate

The 36 logo masters and the animated SVG are emitted by a script:

```bash
python brand/generate.py
```

Edit brand accents, labels, or geometry in `generate.py` and re-run. The color
tokens (`color/`), Lottie JSON, docs, and `index.html` are authored by hand and
not touched by the generator.

Color conversions in `palette.md` (RGB / HSL / OKLCH) were computed from the
canonical HEX values; regenerate them if HEX changes.

---

## Fonts

Playfair Display (editorial) / Inter (structural) / Barlow Condensed (meta) /
IBM Plex Mono (data). Locked. See `type/type.md`.

---

## Phase 2 - raster, social, animation, print

Regenerate everything at once:

```bash
python brand/build_png_icons.py     # 40 icon PNGs
python brand/build_png_lockups.py   # 24 lockup PNGs (needs frontend/node_modules/playwright)
python brand/build_social.py        #  7 social assets
python brand/build_video.py         #  2 GIFs + 88 frames (+ MP4/WebM if ffmpeg is capable)
node   brand/ci/render_pdf.mjs brand/guidelines/guidelines-print.html brand/guidelines/void-brand-book.pdf
```

### Done in this phase

- [x] **PNG export matrix** -> `logos/png/` (64 files, dimensions verified).
      - Icons: each brand at 16/32/48/64/128/256/512/1024 transparent, plus 512
        on Morning paper (`#F0EBDD`) and Evening ink (`#14120F`). Drawn directly
        in **Pillow** from the exact Sigil geometry (supersample x4 + LANCZOS),
        so they are pixel-crisp at 16 px with no browser dependency.
      - Lockups: `horizontal` at 800 and 1600 px wide, transparent + light +
        dark. Rendered from the SVG masters via **Playwright chromium**.
- [x] **Social kit** -> `social/` (7 files, dimensions verified). YouTube (Void
      Vision, brass) avatar 800 + banner 2560x1440 (mark inside the 1546x423
      safe area); Instagram (News) avatar 320; X (News) avatar 400 + header
      1500x500; Bluesky (News) avatar 512 + banner 3000x1000. Deep-ink / paper
      grounds, mark centred inside the circular-crop / TV-safe zones.
- [x] **Animation renders** -> `video/`. Seamless 4.4s beam-sweep loop
      (accent -> blue -> green -> red -> accent), 512 px, 88 frames.
      **GIF** (ink ground + transparent) via Pillow, plus the 88 frame PNGs.
- [x] **Print brand book** -> `guidelines/guidelines-print.html` (A4 `@media
      print`, `print-color-adjust: exact`) + a **real** `void-brand-book.pdf`
      (6 pages) rendered with chromium `page.pdf()`.

### Deferred / approximated (honest notes)

- **MP4 + WebM: DEFERRED to CI.** The only ffmpeg on the dev box is Playwright's
      bundled build, which is capture-only (VP8, and it cannot even decode PNG /
      has no image2 demuxer). `build_video.py` probes for a capable ffmpeg and,
      finding none, delivers the GIF + frames and prints a deferral note. Run
      **`bash brand/render-video.sh`** in CI (ubuntu-latest ships a full ffmpeg)
      to encode `void-news-sigil-ink.mp4` (H.264) + `void-news-sigil-alpha.webm`
      (VP9 alpha) from the frames. Only the file encode is deferred; every frame
      is already rendered.
- **Lockup wordmark face: Georgia stand-in, not Playfair.** Playfair Display is
      not installed on this box and is not present as a decodable font binary
      (the Next cache holds only brotli-compressed subsets that lack basic-latin
      A-Z, and there is no fontTools/brotli to convert them), so chromium renders
      the SVG masters' declared fallback (Georgia). **The Sigil-O geometry is
      exact**; only the letterforms differ. `ci/render_svg.mjs` is the CI script:
      run it on a box with Playfair Display installed (or embed a Playfair WOFF2
      via `@font-face`) for pixel-perfect Playfair lockups, identical pipeline.
- **Icon PNGs are true Playfair-free** (pure geometry), so they are final, not
      approximated.

### Still not in scope (Phase 3)

- [ ] Outline the wordmark/lockup `<text>` to vector paths (or embed a subset
      WOFF2) so the SVG masters render identically without fonts installed.
- [ ] `favicon.ico` (16/32/48 multi-size) + Apple touch icon (180) + maskable
      512 with safe-area padding, packaged for the app.
- [ ] Recolour the animated Sigil for History / Weekly / Vision.
- [ ] Wire a public `/press` route with the download pack.

---

## Constraints honored

- No em or en dashes in any copy (an AI tell; brand voice rule).
- Source-of-truth is the live product (`tokens.css` + the two Sigil components).
- Nothing committed/pushed by the tooling - assets are generated locally.
