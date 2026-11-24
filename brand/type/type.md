# Void - Typography

Four faces, four jobs. The tension between a high-contrast Didone serif and a
monospace terminal face is the whole brand: **editorial authority meets data
terminal.** Nothing else is needed, and nothing else is allowed.

Fonts are locked. You may tune tracking, weight, and line-height. You may not
add a fifth family.

---

## The Four Faces

| Face | Role | Where it lives | Why |
|------|------|----------------|-----|
| **Playfair Display** | Editorial | Masthead, headlines, the VOID wordmark, pull-quotes | A Didone with dramatic thick/thin contrast. It is the broadsheet voice: authority, age, print. |
| **Inter** | Structural | Body copy, UI labels, buttons, navigation | Neutral, humanist, invisible. It gets out of the way so the reporting reads. |
| **Barlow Condensed** | Meta | Kickers, datelines, section headers, tags | Narrow grotesque. The newspaper "meta" register: compressed, all-caps, tracked. |
| **IBM Plex Mono** | Data | Bias scores, source counts, timestamps, the `--flag` heritage | Monospace. Every number aligns; the terminal lineage of the `void --news` command name. |

Fallback stacks (portable, no network):

```css
--font-editorial:  'Playfair Display', Georgia, 'Times New Roman', serif;
--font-structural: 'Inter', 'Helvetica Neue', Arial, sans-serif;
--font-meta:       'Barlow Condensed', 'Franklin Gothic Medium', 'Arial Narrow', sans-serif;
--font-data:       'IBM Plex Mono', Menlo, Consolas, monospace;
```

---

## Type Scale

Fluid, `clamp()`-driven so it breathes between mobile and wide desktop. Values
below are the min -> max endpoints.

| Token | Size (min -> max) | Face | Use |
|-------|-------------------|------|-----|
| `--text-hero` | 24 -> 48 px | Playfair 700 | Section heroes |
| `--type-lead-headline` | 29 -> 58 px | Playfair 700 | The single lead story |
| `--type-twin-headline` | 22 -> 35 px | Playfair 700 | Twin lead split |
| `--text-xl` | 20 -> 28 px | Playfair 600/700 | Sub-heads |
| `--text-lg` | 17 -> 21 px | Playfair / Inter | Deck, standfirst |
| `--type-card-headline` | 14 -> 18 px | Playfair 700 | Feed card headlines |
| `--text-base` | 14 -> 16 px | Inter 400 | Body |
| `--text-sm` | 12 -> 14 px | Inter 400 | Secondary body |
| `--text-xs` | 9 -> 10 px | Barlow / Mono | Meta, tags, data |
| `--text-xxs` | 10 -> 12 px | Barlow 600 | Kickers, datelines |

---

## Weights

- **Playfair Display**: 700 for hero + lead; 600 for sub-headlines and decks. Never below 600 for display; the thins collapse at small sizes.
- **Inter**: 400 body, 500 emphasis, 600 UI labels. Avoid 700 in body - it muddies the newsprint.
- **Barlow Condensed**: 500 / 600 for kickers and section headers, tracked +0.06 to +0.10em, uppercase.
- **IBM Plex Mono**: 400 for data, 500 for emphasized figures (a bias score under focus).

---

## Tracking & Line-height (cinematic tuning)

| Context | Tracking | Line-height |
|---------|----------|-------------|
| Hero / lead headline (Playfair) | -0.035em to -0.02em | 1.12 - 1.18 |
| Card headline (Playfair) | -0.01em | 1.25 |
| Body (Inter) | 0 | 1.65 (editorial) |
| Kicker / dateline (Barlow, caps) | +0.06em to +0.10em | 1.0 |
| Data (Mono) | 0 | 1.4 |

Large Playfair wants **negative** tracking (the counters are open; tighten to
hold the word together). Barlow caps want **positive** tracking (compression
needs air between letters to stay legible).

---

## Pairing - Do / Don't

**Do**
- Let Playfair carry meaning; let Inter carry information.
- Set kickers in Barlow caps directly above a Playfair headline - the register
  jump (condensed meta -> display serif) is the newspaper rhythm.
- Use Mono for anything that is a measurement. If it is a number the engine
  produced, it is Mono.
- Keep the VOID wordmark in Playfair 700; the Sigil-O is the only ornament.

**Don't**
- Do not set body copy in Playfair. It is a display face; it fatigues at
  paragraph length.
- Do not set headlines in Inter. The page loses its authority instantly.
- Do not use Barlow for running text - it is a signage/label face.
- Do not mix a fifth typeface, a script, or a geometric sans "for personality."
  The personality is the serif-vs-mono tension. Adding more dilutes it.
- Do not use em dashes or en dashes in any copy (see guidelines - voice).
