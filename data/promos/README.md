# House promos

Two-sentence cross-promos, stitched under the outro of every Void audio
programme. `house.yaml` is the copy pool; `rendered/` holds one WAV per promo
plus a manifest naming the text each was rendered from.

## What a promo is

A pitch, not an announcement. The first sentence earns the second; the second
is always "Visit news.voidvision.org to check out <section>." Five to ten
seconds at the house voice, which reads slower than the programmes (Kokoro
speed 0.86). Dry, concrete, unimpressed by its own product.

> Every line the two benches say is printed in the column. Visit
> news.voidvision.org to check out The Argument.

## Rules, all asserted by `tests/test_house_promos.py`

1. Exactly two sentences, the second in the form "Visit news.voidvision.org
   to check out <section>." The address does not count as a sentence end.
2. No digits. Number words only from the allowed set in
   `pipeline/briefing/house_promos.py`, each tied to a constant in the code:
   "four" is the story count the radio validator enforces, "fifteen" is the
   served-show ceiling, "five weeks" is in the Partition script, "twenty" is
   the feed size in `frontend/config/feed.json` and fails the moment that
   changes.
3. Never a count of sources, countries or episodes. A promo is rendered once
   and plays for years.
4. Nothing borrowed from radio (the On Air and Weekly banned lists), nothing
   from the kill list in `docs/VOICE-BRAND.md`, no exclamation marks, no
   quotation marks, no em or en dashes in the written text.
5. `promotes` is never in `plays_in`. A promo never plays inside the section
   it advertises.
6. Promise only what exists: no app, no newsletter, no notifications, nothing
   personalized, nothing breaking.
7. The bias claim leads with "both": slant is scored on both the outlet and
   the words. "The words, not the outlet" is a banned framing.

## Fields

| field | meaning |
|---|---|
| `id` | stable slug; the rendered WAV is named after it |
| `promotes` | `onair`, `weekly`, `history` or `site` |
| `plays_in` | sections the promo may play in |
| `text` | the written copy, with the real address |
| `spoken` | optional TTS override; by default the address becomes "news dot void vision dot org" |
| `seconds` | estimate at the house rate; `fill-seconds` rewrites it |
| `angle` | one phrase on what the promo leans on |
| `claims` | tags for the facts it relies on, from the allowed set |
| `names_url` | true when the text carries the address |

## Where it plays

Post-roll, under the outro's held bars, starting a beat after the last
spoken word and finishing before the outro's fall to silence. A promo bed
(`pipeline/briefing/assets/radio_promo_bed.wav`, the house motif at the
Sunday tempo over a low D drone, with a riser and a landing) swells in 1.2 s
before the first word while the outro is pulled 12 dB down, and its own fall
hands the ending back to the outro. The programme's length does not change. Selection is the sha256 of the episode
key (`onair:world:2026-09-20:pm`, `weekly:world:2026-09-14`,
`history:partition-of-india`) into the eligible pool, so the same episode
always carries the same promo.

## Commands

```
python3 pipeline/briefing/house_promos.py validate
python3 pipeline/briefing/house_promos.py fill-seconds
python3 pipeline/briefing/house_promos.py select history history:partition-of-india
python3 pipeline/briefing/house_promos.py render        # needs .venv-tts (CI)
python3 pipeline/history/stitch_promos.py --all         # retrofit the catalogue
```
