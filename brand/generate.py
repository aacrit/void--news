#!/usr/bin/env python3
"""
Void brand pack - SVG master generator.

Emits the full logo suite (horizontal lockup / icon / wordmark, each in
color / one-color-black / reversed-white) for the four Void brands, plus the
flagship animated Sigil SVG. Run from anywhere:

    python brand/generate.py

Every path is resolution-independent SVG with explicit fills/strokes (no CSS
vars, no currentColor) so the files are portable into any tool. Geometry is
lifted verbatim from the app source of truth:
  - frontend/app/components/ScaleIcon.tsx      (footed Sigil, square icon)
  - frontend/app/components/SigilWordmark.tsx  (inline Sigil-O, foot descends)

The Sigil = coverage ring (breadth of sources) + level balance beam with |-|
end ticks (the bias measurement) + post & base foot (the lens/stand).
"""

import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOGOS = os.path.join(HERE, "logos")
ANIM = os.path.join(HERE, "animated")

SERIF = "'Playfair Display', Georgia, 'Times New Roman', serif"
INK = "#1A1A1A"     # editorial ink (VOID letters, light-ground)
BLACK = "#111111"   # one-color treatment
WHITE = "#FFFFFF"   # reversed treatment

# label = swappable product word; accent = per-brand color (light-mode master)
BRANDS = {
    "void-news":    {"label": "NEWS",    "accent": "#B26F52", "name": "Void News"},
    "void-history": {"label": "HISTORY", "accent": "#5C4033", "name": "Void History"},
    "void-weekly":  {"label": "WEEKLY",  "accent": "#B91C1C", "name": "Void Weekly"},
    "void-vision":  {"label": "VISION",  "accent": "#946B15", "name": "Void Vision"},
}

# Sigil sweep colors (light) - drive the animated beam spectrum.
LEAN_LEFT = "#3F72B0"
LEAN_CENTER = "#3E7C57"
LEAN_RIGHT = "#B0433B"

# Serif cap advances (em fractions), sized to the WIDE fallback face
# (Times/Georgia bold, +4% safety) so the viewBox never clips when Playfair
# is absent. Overestimating width only adds harmless right whitespace; native
# text kerning still handles the real letter spacing.
ADV = {
    "V": .78, "O": .82, "I": .42, "D": .77, "N": .77, "E": .70, "W": .99,
    "S": .60, "H": .77, "T": .65, "R": .72, "Y": .77, "K": .77, "L": .65,
    " ": .27,
}
RIGHT_PAD = 46


def text_width(s, fs, tracking=0.0):
    w = sum(ADV.get(ch, .75) for ch in s) * fs
    w += tracking * max(0, len(s) - 1)
    return w


# --- Sigil geometry as reusable path bodies ------------------------------

def _icon_paths(sw_scale=1.0):
    """Footed Sigil (ScaleIcon geometry) centered in a 100x100 box."""
    return (
        '  <circle cx="50" cy="40" r="30" stroke-width="8"/>\n'
        '  <line x1="12" y1="40" x2="88" y2="40" stroke-width="6"/>\n'
        '  <line x1="12" y1="32" x2="12" y2="48" stroke-width="5"/>\n'
        '  <line x1="88" y1="32" x2="88" y2="48" stroke-width="5"/>\n'
        '  <line x1="50" y1="70" x2="50" y2="86" stroke-width="6"/>\n'
        '  <path d="M36 93 C44 88 56 88 64 93" stroke-width="6"/>\n'
    )


def _sigil_o_group(stroke):
    """Inline Sigil-O (SigilWordmark geometry): foot hangs below the baseline.
    Placed as the O in the lockup at x-slot 68..132, scaled 0.64, baseline 88."""
    return (
        f'  <g transform="translate(68,30.4) scale(0.64)" fill="none" '
        f'stroke="{stroke}" stroke-linecap="round">\n'
        '    <circle cx="50" cy="50" r="41" stroke-width="8"/>\n'
        '    <line x1="4" y1="50" x2="96" y2="50" stroke-width="6"/>\n'
        '    <line x1="4" y1="42" x2="4" y2="58" stroke-width="5"/>\n'
        '    <line x1="96" y1="42" x2="96" y2="58" stroke-width="5"/>\n'
        '    <line x1="50" y1="91" x2="50" y2="112" stroke-width="6"/>\n'
        '    <path d="M35 118 C43 113 57 113 65 118" stroke-width="6"/>\n'
        '  </g>\n'
    )


# --- Asset builders -------------------------------------------------------

def icon_svg(stroke, brand_name):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" '
        f'fill="none" stroke="{stroke}" stroke-linecap="round" '
        f'role="img" aria-label="{brand_name} Sigil">\n'
        + _icon_paths()
        + '</svg>\n'
    )


def wordmark_svg(void_fill, prod_fill, label, brand_name):
    fs = 78
    tracking = 1.0
    full = f"VOID {label}"
    width = round(12 + text_width(full, fs, tracking) + RIGHT_PAD)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 112" '
        f'role="img" aria-label="VOID {label} wordmark">\n'
        f'  <text x="12" y="84" font-family="{SERIF}" font-weight="700" '
        f'font-size="{fs}" letter-spacing="{tracking}">'
        f'<tspan fill="{void_fill}">VOID </tspan>'
        f'<tspan fill="{prod_fill}">{label}</tspan></text>\n'
        '</svg>\n'
    )


def lockup_svg(v_fill, sigil_stroke, prod_fill, label, brand_name):
    fs = 80
    tail = f"ID {label}"
    width = round(138 + text_width(tail, fs) + RIGHT_PAD)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 120" '
        f'role="img" aria-label="VOID {label} horizontal lockup">\n'
        f'  <text x="12" y="88" font-family="{SERIF}" font-weight="700" '
        f'font-size="{fs}" fill="{v_fill}">V</text>\n'
        + _sigil_o_group(sigil_stroke)
        + f'  <text x="138" y="88" font-family="{SERIF}" font-weight="700" '
        f'font-size="{fs}">'
        f'<tspan fill="{v_fill}">ID </tspan>'
        f'<tspan fill="{prod_fill}">{label}</tspan></text>\n'
        '</svg>\n'
    )


def animated_sigil_svg(accent):
    """Flagship animated Sigil: beam sweeps level -> left(blue) -> center(green)
    -> right(red) -> back to accent. Self-contained inline CSS, loops, honors
    prefers-reduced-motion. Recolor `accent` + the ring/foot stroke for the
    other three brands."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"
     role="img" aria-label="Void News animated Sigil">
  <style>
    .void-static {{ fill: none; stroke: {accent}; stroke-linecap: round; }}
    .void-beam {{
      fill: none;
      stroke: {accent};
      stroke-linecap: round;
      transform-box: view-box;
      transform-origin: 50px 40px;
      animation: void-beam-sweep 4.4s cubic-bezier(0.22, 1, 0.36, 1) infinite;
    }}
    @keyframes void-beam-sweep {{
      0%, 100% {{ transform: rotate(0deg);   stroke: {accent}; }}
      20%      {{ transform: rotate(-15deg); stroke: {LEAN_LEFT}; }}
      45%      {{ transform: rotate(0deg);   stroke: {LEAN_CENTER}; }}
      70%      {{ transform: rotate(15deg);  stroke: {LEAN_RIGHT}; }}
      88%      {{ transform: rotate(0deg);   stroke: {accent}; }}
    }}
    @media (prefers-reduced-motion: reduce) {{
      .void-beam {{ animation: none; stroke: {accent}; transform: none; }}
    }}
  </style>

  <!-- Coverage ring + foot: the ground the scale stands on. Static. -->
  <circle class="void-static" cx="50" cy="40" r="30" stroke-width="8"/>
  <line class="void-static" x1="50" y1="70" x2="50" y2="86" stroke-width="6"/>
  <path class="void-static" d="M36 93 C44 88 56 88 64 93" stroke-width="6"/>

  <!-- Balance beam + |-| weight ticks: the bias measurement. Sweeps. -->
  <g class="void-beam">
    <line x1="12" y1="40" x2="88" y2="40" stroke-width="6"/>
    <line x1="12" y1="32" x2="12" y2="48" stroke-width="5"/>
    <line x1="88" y1="32" x2="88" y2="48" stroke-width="5"/>
  </g>
</svg>
'''


def write(path, content):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
    print("  wrote", os.path.relpath(path, HERE))


def main():
    os.makedirs(LOGOS, exist_ok=True)
    os.makedirs(ANIM, exist_ok=True)
    count = 0
    for slug, b in BRANDS.items():
        accent, label, name = b["accent"], b["label"], b["name"]

        # ICON (footed Sigil) - color / black / reversed
        write(os.path.join(LOGOS, f"{slug}-icon-color.svg"), icon_svg(accent, name)); count += 1
        write(os.path.join(LOGOS, f"{slug}-icon-black.svg"), icon_svg(BLACK, name)); count += 1
        write(os.path.join(LOGOS, f"{slug}-icon-reversed.svg"), icon_svg(WHITE, name)); count += 1

        # WORDMARK (pure type, no Sigil) - color / black / reversed
        write(os.path.join(LOGOS, f"{slug}-wordmark-color.svg"), wordmark_svg(INK, accent, label, name)); count += 1
        write(os.path.join(LOGOS, f"{slug}-wordmark-black.svg"), wordmark_svg(BLACK, BLACK, label, name)); count += 1
        write(os.path.join(LOGOS, f"{slug}-wordmark-reversed.svg"), wordmark_svg(WHITE, WHITE, label, name)); count += 1

        # HORIZONTAL LOCKUP (Sigil-O signature) - color / black / reversed
        write(os.path.join(LOGOS, f"{slug}-horizontal-color.svg"), lockup_svg(INK, accent, accent, label, name)); count += 1
        write(os.path.join(LOGOS, f"{slug}-horizontal-black.svg"), lockup_svg(BLACK, BLACK, BLACK, label, name)); count += 1
        write(os.path.join(LOGOS, f"{slug}-horizontal-reversed.svg"), lockup_svg(WHITE, WHITE, WHITE, label, name)); count += 1

    # Flagship animated Sigil (Void News accent).
    write(os.path.join(ANIM, "void-news-sigil-animated.svg"), animated_sigil_svg(BRANDS["void-news"]["accent"]))

    print(f"\nDone. {count} logo SVGs + 1 animated SVG.")


if __name__ == "__main__":
    main()
