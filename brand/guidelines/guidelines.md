# Void - Brand Guidelines

The promise of the brand is legible in the mark itself: **show the bias, do not
hide it.** Every rule below protects that promise.

---

## 1. What the Sigil Means

The Void Sigil is not decoration. It is a diagram of what the product does.

```
        ______              <- coverage ring: the breadth of sources.
       /      \                A hollow circle, the analytical lens, the "void"
      |        |               you look through. The O in VOID.
   |--+--------+--|         <- level balance beam with |-| end ticks:
      |        |               the bias measurement. Level = balanced coverage.
       \______/                It tilts left (blue) or right (red) as the
          |                    measured lean moves. Green = true center.
        __|__               <- the foot (post + base): the lens/stand.
       (_____)                 The ground the scale stands on. It never tilts.
```

- **Coverage ring** = breadth of sources. The wider the reporting, the more the
  ring means.
- **Balance beam** = the multi-axis bias reading. At rest it is level. In
  motion it sweeps the lean spectrum. The `|-|` ticks are the weighing pans.
- **Foot** = the instrument's stand. It is fixed. Measurement moves; the method
  does not.

When the beam sweeps in the animated mark, it crosses blue -> green -> red -
the same spectrum the product paints across every story. The logo performs the
methodology.

---

## 2. Logo Usage

### The three assets

- **Horizontal lockup** - `V[Sigil-O]ID PRODUCT`. The Sigil replaces the O in
  VOID. The primary signature. Use wherever there is horizontal room.
- **Wordmark** - `VOID PRODUCT` in Playfair, no Sigil. Use when a second Sigil
  would be redundant (e.g. sitting beside the animated icon) or when the mark
  must stay purely typographic.
- **Icon** - the footed Sigil alone, square. Favicon, app tile, avatar, and the
  Void Vision umbrella mark.

### Clear space

Minimum clear space on all sides = **the height of the Sigil ring** (its
diameter). Nothing - type, image edge, another logo - enters that zone.

```
   +---------------------------+
   |         ^ 1 ring          |
   |     +---------------+      |
   |<1 r | VOID  NEWS    | 1r >|
   |     +---------------+      |
   |         v 1 ring          |
   +---------------------------+
```

### Minimum sizes

| Asset | Digital min | Print min |
|-------|-------------|-----------|
| Icon (Sigil) | 16 px | 8 mm |
| Horizontal lockup | 120 px wide | 24 mm wide |
| Wordmark | 100 px wide | 20 mm wide |

At 16 px the icon must render the ring + level beam clearly. Do not animate
below 24 px (the tilt is illegible and reads as jitter).

### Treatments

- **Full color** - the brand accent (see color rules). Default.
- **One-color black** (`#111`) - single-color print, embossing, fax, stamps.
- **Reversed white** (`#FFF`) - on dark or photographic grounds. Use reversed
  paper (`#FBF6EC`) where pure white is too stark on warm dark.

### Never

- Never recolor the Sigil into a bias-spectrum color as a static state (a fixed
  blue or red Sigil implies the brand itself leans). The sweep is motion only;
  at rest the mark is the brand accent.
- Never fill the ring. It is a lens; it is hollow.
- Never tilt the foot. The beam tilts; the stand is fixed.
- Never rebuild the wordmark in another typeface.
- Never stretch, skew, add a drop shadow, gradient, or outline.
- Never place the color mark on a ground that drops it below 3:1 - switch to
  black or reversed.

---

## 3. Color Usage

- **One accent per surface.** A Void News page is terracotta; a Weekly page is
  red; a History page is umber; Vision is brass. Do not mix product accents on
  one page.
- **Bias colors are earned, never decorative.** The 7-point blue -> green ->
  red spectrum belongs to the measurement only. Do not use `--bias-right` red
  for an error state or `--bias-center` green for success - it corrupts the one
  place color carries data.
- **Green means center only.** Never use the center green to signal "good."
- **Accents are for large marks.** For small bold labels on paper, use the
  `-ink` shade (e.g. News `#9A5638`) so text clears WCAG AA 4.5:1.
- **Paper and ink carry the page.** Accent is a spice, not a base. If a screen
  looks colorful, it is wrong.

Full values: `../color/palette.md`.

---

## 4. Typography

Playfair (editorial) / Inter (structural) / Barlow Condensed (meta) / IBM Plex
Mono (data). Full spec: `../type/type.md`. The one-line rule: **serif carries
meaning, mono carries measurements, and the two never trade jobs.**

---

## 5. Voice

The writing is as disciplined as the design. Three rules, non-negotiable,
enforced in generated copy and human copy alike.

### Show, don't tell
Never assert significance. Juxtapose concrete facts and let the reader
conclude. Kill "notable," "significant," "it should be noted,"
"interestingly," "crucially."

> **Bad:** "Tensions are rising significantly between the two nations."
> **Good:** "Both countries recalled their ambassadors within 48 hours. Neither
> has done that since 1979."

### Arrive late, leave early
Enter at the last possible moment; exit before the point is spelled out. Drop
the reader into the action. The gap is where understanding happens.

> **Bad:** "The Partition of India was a complex process that began with
> British colonial rule and led to two nations in 1947."
> **Good:** "A lawyer who'd never been to India drew the border in five weeks.
> 15 million crossed it."

### No em dashes
Em dashes (`-` U+2014) and en dashes (U+2013) are banned in all written copy:
headlines, body, taglines, captions, UI microcopy, social. They are an AI tell.
Rewrite as two short sentences, or use a comma, semicolon, colon, or
parentheses. Hyphens in compound words ("fact-check") are fine.

> **Bad:** "The bank cut rates Tuesday - the third move this quarter."
> **Good:** "The bank cut rates Tuesday. Third move this quarter."

The single exception is spoken audio scripts, where an em dash is a breath mark
for text-to-speech. Never in anything read on screen.

### Tone
Editorial authority without pomposity. Precise, restrained, evidence-first.
Institutional "we" for editorial voice. Never breathless, never cute, never a
tech-startup exclamation point.

---

## 6. The Brands

| Brand | Accent | Voice register |
|-------|--------|----------------|
| **Void News** | Terracotta `#B26F52` | The flagship. Daily, measured, the record. |
| **Void History** | Umber `#5C4033` | Archival, long-view, multi-perspective. |
| **Void Weekly** | Red `#B91C1C` | Magazine. Argued, essayistic, the week's through-line. |
| **Void Vision** | Brass `#946B15` | The umbrella + YouTube. The bare Sigil is the master mark. |

Void is the parent. Products are the swappable second word after VOID. The
Sigil-O scales across all of them; only the accent and the product word change.
