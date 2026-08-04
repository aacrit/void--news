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
  logos/                36 SVG masters (4 brands x 3 assets x 3 treatments)
  animated/             Living Sigil - animated SVG + Lottie JSON
  color/                colors.css, colors.json, palette.md
  type/                 type.md (specimen + scale + pairing rules)
  guidelines/           guidelines.md (logo, color, type, voice, Sigil meaning)
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

## Phase 2 checklist (NOT in this phase)

The following are deliberately out of scope for the foundation. Run next:

- [ ] **Outline the wordmark/lockup text to vector paths** so the marks render
      identically without the fonts installed. Open each `*-wordmark-*.svg` and
      `*-horizontal-*.svg` in Illustrator/Inkscape/Fonttools, convert `<text>`
      to paths, and re-save. (Alternatively embed a subset WOFF2 as a data URI.)
- [ ] **Multi-resolution PNG export matrix.** Rasterize every SVG at 16 / 32 /
      48 / 64 / 128 / 256 / 512 / 1024 px. Recommended approach (same
      supersample method used for the app favicons): render the SVG to a canvas
      or via a headless renderer at **4x** the target, then downscale with a
      high-quality Lanczos filter for crisp edges.
      - Node: `sharp(svgBuffer, { density: 4*targetDPI }).resize(size).png()`
      - Python: `cairosvg.svg2png(url=..., output_width=size*4, ...)` then
        `Pillow` `Image.resize((size,size), Image.LANCZOS)`.
      - Keep transparent backgrounds; produce `@1x/@2x/@3x` sets for app tiles.
- [ ] **Favicon + PWA icon set.** `favicon.ico` (16/32/48 multi-size), Apple
      touch icon (180), maskable 512 with safe-area padding, from the icon SVGs.
- [ ] **Video renders of the animated Sigil.** MP4 (H.264) + WebM (VP9) +
      transparent GIF, ~4.4s loop at 1080x1080 and 512x512, from the Lottie
      (`lottie` -> `puppeteer`/`lottie-web` frames -> `ffmpeg`).
- [ ] **Per-platform social avatars/banners.** X/Twitter, YouTube (Vision),
      Instagram, LinkedIn, Open Graph 1200x630. Icon-on-accent avatar +
      lockup-on-paper banner per brand.
- [ ] **PDF brand book.** Compose the guidelines + specimens + logo grid into a
      print-ready PDF.
- [ ] **Wire the `/press` page.** Surface `index.html` (or a Next.js port) at a
      public press/brand route with the download pack.
- [ ] **Recolor the animated Sigil for History / Weekly / Vision** (currently
      only the News flagship exists). Swap the accent + ring/foot stroke in the
      SVG `<style>` and the Lottie stroke keyframes.

---

## Constraints honored

- No em or en dashes in any copy (an AI tell; brand voice rule).
- Source-of-truth is the live product (`tokens.css` + the two Sigil components).
- Nothing committed/pushed by the tooling - assets are generated locally.
