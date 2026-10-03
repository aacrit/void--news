# Void - Palette Reference

Every brand color in four color spaces plus usage and contrast notes. HEX is
canonical. RGB / HSL / OKLCH are computed conversions (sRGB, D65) for tooling
and perceptual work. Source of truth: `frontend/app/styles/tokens.css`.

Two editions:
- **Morning Edition (light)** - warm newsprint, aged broadsheet under morning light.
- **Evening Edition (dark)** - walnut broadsheet, not terminal black.

---

## 1. Brand Accents

One accent per product. Accents are **decorative marks** (large logo use) and
are not bound by the WCAG AA 4.5:1 small-text rule. For small bold labels on
paper, use the `-ink` shade.

| Name | HEX | RGB | HSL | OKLCH | Usage |
|------|-----|-----|-----|-------|-------|
| News terracotta (light) | `#B26F52` | rgb(178, 111, 82) | hsl(18, 38%, 51%) | oklch(0.607 0.095 44.0) | Flagship accent: Sigil-O, NEWS word, links. Decorative (~3.3:1 on cream). |
| News ink (light labels) | `#9A5638` | rgb(154, 86, 56) | hsl(18, 47%, 41%) | oklch(0.526 0.100 43.9) | Small bold labels (Top Story, News Brief). Clears AA on cream. |
| News terracotta (dark) | `#D89A7C` | rgb(216, 154, 124) | hsl(20, 54%, 67%) | oklch(0.739 0.086 46.8) | News accent on walnut. Clears AA on `#1C1A17`. |
| History umber (light) | `#5C4033` | rgb(92, 64, 51) | hsl(19, 29%, 28%) | oklch(0.399 0.045 45.9) | Archive accent. Deep, near-ink; pair with paper. |
| History umber alt | `#8B7355` | rgb(139, 115, 85) | hsl(33, 24%, 44%) | oklch(0.571 0.053 72.7) | History secondary/meta; the dark-mode History accent. |
| Weekly red (light) | `#B91C1C` | rgb(185, 28, 28) | hsl(0, 74%, 42%) | oklch(0.505 0.190 27.5) | Magazine accent: hero headline, rules. ~4.9:1 on cream (AA). |
| Weekly red alt | `#EF5350` | rgb(239, 83, 80) | hsl(1, 83%, 63%) | oklch(0.654 0.193 25.1) | Weekly accent on dark; bright pull-quote red. |
| Vision brass (light) | `#946B15` | rgb(148, 107, 21) | hsl(41, 75%, 33%) | oklch(0.556 0.108 80.1) | Umbrella + YouTube; the bare Sigil default. ~4.9:1 on cream (AA). |
| Vision brass alt | `#B8872A` | rgb(184, 135, 42) | hsl(39, 63%, 44%) | oklch(0.655 0.121 79.1) | Hover / snap / active brass. |
| Vision brass (dark) | `#D4A574` | rgb(212, 165, 116) | hsl(31, 53%, 64%) | oklch(0.754 0.085 67.1) | Aged brass reads as pale gold on walnut. 7.8:1 on `#1C1A17`. |

---

## 2. Bias Spectrum

The earned colors. Blue (left) -> **Green (center ONLY)** -> Red (right). Depth
encodes distance from center: the far extremes are deepest. Never recolor these
for decoration. Light values are AA on paper; dark values are AA-retuned for
walnut.

| Lean | HEX (light) | RGB | HSL | OKLCH | Contrast note |
|------|-------------|-----|-----|-------|---------------|
| Far left | `#0E2E70` | rgb(14, 46, 112) | hsl(220, 78%, 25%) | oklch(0.324 0.120 262.4) | 8.2:1 - deepest blue |
| Left | `#1B5298` | rgb(27, 82, 152) | hsl(214, 70%, 35%) | oklch(0.443 0.128 256.4) | 5.8:1 |
| Center-left | `#2E78B4` | rgb(46, 120, 180) | hsl(207, 59%, 44%) | oklch(0.556 0.118 246.7) | 4.5:1 |
| Center | `#2B784A` | rgb(43, 120, 74) | hsl(144, 47%, 32%) | oklch(0.513 0.105 153.9) | 5.4:1 - green only |
| Center-right | `#C4503E` | rgb(196, 80, 62) | hsl(8, 53%, 51%) | oklch(0.580 0.152 31.1) | 4.6:1 |
| Right | `#9C2C22` | rgb(156, 44, 34) | hsl(5, 64%, 37%) | oklch(0.465 0.150 29.1) | 5.9:1 |
| Far right | `#6E1610` | rgb(110, 22, 16) | hsl(4, 75%, 25%) | oklch(0.354 0.123 28.9) | 8.1:1 - deepest red |

Dark-mode spectrum: `#5088D0` `#6498D8` `#78AEDE` `#48B870` `#D05C48` `#CC3E34` `#B02E26` (all 4.5:1+ on walnut).

---

## 3. Sigil Sweep

The animated Sigil beam crosses these as it tilts left -> center -> right, then
settles back to the brand accent.

| Name | HEX (light) | RGB | HSL | OKLCH | Usage |
|------|-------------|-----|-----|-------|-------|
| Brass (rest) | `#946B15` | rgb(148, 107, 21) | hsl(41, 75%, 33%) | oklch(0.556 0.108 80.1) | Level beam at rest (Vision default). |
| Lean left | `#3F72B0` | rgb(63, 114, 176) | hsl(213, 47%, 47%) | oklch(0.546 0.112 254.4) | Beam tilted left. |
| Lean center | `#3E7C57` | rgb(62, 124, 87) | hsl(144, 33%, 36%) | oklch(0.534 0.087 155.7) | Beam balanced. |
| Lean right | `#B0433B` | rgb(176, 67, 59) | hsl(4, 50%, 46%) | oklch(0.531 0.144 27.2) | Beam tilted right. |

Dark sweep: brass `#D4A574`, left `#6098D8`, center `#6FB98C`, right `#D46A62`.

---

## 4. Ink & Paper

Editorial neutrals. Foregrounds all clear WCAG AA 4.5:1 on their own ground.

### Morning Edition (light)

| Name | HEX | RGB | HSL | OKLCH | Usage |
|------|-----|-----|-----|-------|-------|
| Paper primary | `#F0EBDD` | rgb(240, 235, 221) | hsl(44, 39%, 90%) | oklch(0.940 0.019 90.5) | Page canvas |
| Paper secondary | `#E8E2D4` | rgb(232, 226, 212) | hsl(42, 30%, 87%) | oklch(0.914 0.020 87.5) | Recessed surfaces |
| Paper card | `#F5F0E4` | rgb(245, 240, 228) | hsl(42, 46%, 93%) | oklch(0.956 0.017 88.0) | Cards, elevated |
| Ink primary | `#1A1A1A` | rgb(26, 26, 26) | hsl(0, 0%, 10%) | oklch(0.218 0.000 89.9) | Headlines, VOID letters |
| Ink secondary | `#4A4540` | rgb(74, 69, 64) | hsl(30, 7%, 27%) | oklch(0.394 0.011 67.5) | Body text |
| Ink muted | `#52504A` | rgb(82, 80, 74) | hsl(45, 5%, 31%) | oklch(0.431 0.010 91.6) | Meta, captions (AA) |

### Evening Edition (dark)

| Name | HEX | RGB | HSL | OKLCH | Usage |
|------|-----|-----|-----|-------|-------|
| Paper primary | `#1C1A17` | rgb(28, 26, 23) | hsl(36, 10%, 10%) | oklch(0.219 0.007 78.2) | Page canvas (walnut) |
| Paper secondary | `#252320` | rgb(37, 35, 32) | hsl(36, 7%, 14%) | oklch(0.257 0.006 78.2) | Recessed surfaces |
| Paper card | `#2A2725` | rgb(42, 39, 37) | hsl(24, 6%, 15%) | oklch(0.275 0.006 56.1) | Cards, elevated |
| Ink primary | `#EDE8E0` | rgb(237, 232, 224) | hsl(37, 27%, 90%) | oklch(0.933 0.012 79.8) | Headlines, cream text |
| Ink secondary | `#B8B0A5` | rgb(184, 176, 165) | hsl(35, 12%, 68%) | oklch(0.761 0.018 76.1) | Body text |
| Ink muted | `#9A938B` | rgb(154, 147, 139) | hsl(32, 7%, 57%) | oklch(0.667 0.014 71.3) | Meta, captions (AA) |

---

## 5. Treatments

| Name | HEX | RGB | Usage |
|------|-----|-----|-------|
| One-color black | `#111111` | rgb(17, 17, 17) | Single-color logo on light grounds; stamps, fax, embossing. |
| Reversed white | `#FFFFFF` | rgb(255, 255, 255) | Logo knocked out on dark/photographic grounds. |
| Reversed paper | `#FBF6EC` | rgb(251, 246, 236) | Softer knock-out where pure white is too stark on warm dark. |

> OKLCH values are for perceptual tooling (gradients, contrast mixing). When in
> doubt, HEX is authoritative and matches the running product exactly.
