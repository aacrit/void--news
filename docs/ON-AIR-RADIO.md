# On Air: the radio edition

Last updated: 2026-09-18 (rev 1, the first radio-format build)

On Air is the daily radio edition of Void News: eight to ten minutes, two voices,
the day's top stories read for the ear, then the editorial. It is generated once a
day by the pipeline (step 7d) and served as one MP3 with chapters.

This document is the positive definition of the show. The code that enforces it:

| What | Where |
|---|---|
| The rundown (prompt, parser, validators R-01..R-13) | `pipeline/briefing/radio_script_generator.py` |
| Spoken-text normalisation (numbers, currency, initialisms, respellings) | `pipeline/briefing/spoken_text.py` |
| Voices (Kokoro primary, edge-tts fallback) | `pipeline/briefing/tts_engines.py`, `tts_kokoro_worker.py`, `kokoro_assets.py`, `kokoro.lock.json`, `pipeline/requirements-tts.txt` |
| Assembly, music placement, mastering, chapters | `pipeline/briefing/radio_producer.py` |
| Original sound (ident, beds, stab, outro, room tone) | `pipeline/briefing/generate_assets.py` (radio set) -> `assets/radio_*.wav` |
| Pipeline wiring, fallback, storage | `pipeline/main.py` (`_produce_radio_edition`), `pipeline/refresh_brief.py` (`--radio-only`, `--rundown-file`, `--render-dir`) |
| Chapters in the player | `frontend/app/lib/chapters.ts`, `AudioProvider.tsx`, `OnAirPage.tsx`, `FloatingPlayer.tsx`, `MobileMiniPlayer.tsx` |
| Podcast feed (`<podcast:chapters>`) | `pipeline/briefing/podcast_feed_generator.py` |
| Tests | `tests/test_radio_script.py`, `tests/test_radio_assembly.py`, `frontend/test/chapters.test.mjs`, `pipeline/briefing/tts_bench.py` |
| Served-output gate | `scripts/verify_audio.py` (A-01..A-05), run by `verify-production.yml` |

## Running order

```
ident (2.4 s)
OPEN      voice A   "From Void News, this is On Air. It's Friday, September eighteenth." + one sentence
MENU      A/B       "On the desk today." then five headlines, one line each        [menu bed underneath]
STORY 1   A leads   rank 1 in depth, 170-260 words; B adds at most one new fact   (marker: ## STORY 1 | <title>; the id is bound from the feed by rank)
STORY 2   B leads   rank 2, 130-210 words, opens with a one-clause bridge
STORY 3   A leads   rank 3
STORY 4   B leads   rank 4
BRIEFS    A/B       "Also on the desk." then ranks 5-12, one sentence each
FINALLY   B         "One more before the editorial." a lighter item from ranks 5-20   (marker: ## FINALLY | <feed rank> | <title>; absent when the lead is a mass-casualty story)
throw     A         "Next, the editorial."                                              (code constant)
stab (0.7 s)
EDITORIAL B         the existing opinion_audio_script, paragraph by paragraph
CLOSE     A         "That's On Air from Void News." + one concrete fact + "Every source, every story, at Void News."   [close bed]
outro (2.0 s)
```

Ranks 13-20 are context for the model and are not read. Nothing sits under the
stories, the briefs or the editorial except synthesised room tone at -57 dBFS.

## Writing for the ear

The rules the prompt states and the validators enforce (fail = one regeneration
with the findings named, then the legacy audio path; warn = logged):

| Id | Rule | Level |
|---|---|---|
| R-01 | Sign-on and sign-off are Void's exact lines; the sign-on names the day | fail |
| R-02 | No quotation marks. Reported speech only; a quote is never read aloud | fail |
| R-03 | Numbers are words. Code normalises anyway (`spoken_text`), so this warns | warn |
| R-04 | No a.m./p.m. clock forms, no print datelines | fail |
| R-05 | No borrowed or AI-podcast phrases: "Up first", "Here's what we're covering", "First the headlines", "And that's the headlines", "these are our main stories", "Stay with us", "And finally", "Welcome", "Thanks", "Absolutely", "Wow", "Over to you" and the show never names or thanks a host | fail |
| R-06 | Word budgets at 156 wpm per segment, five menu lines, six to eight brief items, 850-1150 news words | fail outside +-25 % |
| R-07 | Attribution before the claim ("The Fed chair says ..."), never trailing | warn |
| R-08 | Exactly four STORY segments, ranks 1-4 in order; ids are bound from the feed by rank (the model never copies UUIDs: the first real run mis-copied two by one hex digit); the kicker must name a feed rank from 5 up, and never the editorial's story | fail |
| R-09 | FINALLY absent when the lead's `disaster_severity` >= 0.6; present otherwise | fail / warn |
| R-10 | Each voice carries 35-65 % of the words | fail |
| R-11 | Sentences under twenty words; one idea per sentence | warn |
| R-12 | Lead voice alternates story by story; the second voice adds at most one line per story | fail |
| R-13 | `## SAY` respellings are well formed and used; they are lowercased before synthesis because the phonemizer reads a run of capitals as initials ("KAR-nee" came out as K, A, arnee on 2026-09-19) | warn |

Before synthesis every line passes through `normalize_for_speech`: `## SAY`
respellings, then numerals to words ("$4 billion" -> "four billion dollars",
"3.75%" -> "three point seven five percent", "2018" -> "twenty eighteen"), then
initialisms hyphenated so they are read as letters ("US" -> "U-S", "FBI" ->
"F-B-I"; NATO and OPEC stay words), then em dashes to commas.

## Originality

Bulletin structure (menu, lead, round-up, kicker, sign-off) is a broadcasting
convention nobody owns. Everything expressible is Void's own: the sign-on, the
menu and round-up lead-ins, the throw, the sign-off, and every sound. The assets
are synthesised in-repo from a documented palette (no samples, no libraries, no
time pips, no ascending-fifth fanfare) and the validators reject the well-known
catchphrases. Only in-repo synthesis or CC0 material is ever acceptable here;
BBC sound effects are non-commercial and most "free" music libraries are not
cleared for a distributed MP3.

## Voices

Kokoro-82M (Apache-2.0, trained on permissive audio, explicit commercial
blessing) is the production engine. It runs on the CI runner's CPU inside its
own virtualenv (`.venv-tts`, numpy 2) as a worker subprocess; model files are
pinned by sha256 in `kokoro.lock.json` and cached between runs.

Three roles since 2026-09-19 (CEO). The editorial has a voice that reads
nothing else, so the opinion firewall is audible the moment it starts.

| Role | Voice | Speed | Pan | Why |
|---|---|---|---|---|
| A, the anchor | `am_puck` | 0.92 | -7 % | light American, 112 Hz. The one voice that hits the worker's -1 dBFS clamp |
| B, alternate stories | `af_nova` | 0.82 | +7 % | low female (159 Hz), a register contrast to A without the brightness of `af_heart` |
| C, the editorial only | `af_heart` | 0.93 | centre | the roster's one A-grade voice; centred, because it speaks alone |

**One pace, about 156 wpm.** The show is one programme, so the three voices do
not read at three speeds, and 156 is a calm read rather than the brisk wire
pace the first build shipped (CEO, 2026-09-19). Each speed above is the
smallest correction that voice needs to reach it: at speed 1.0 the roster
reads `am_puck` 164, `af_heart` 162 and `af_nova` 181. Kokoro's speed knob
scales predicted phoneme durations before the decoder, so it re-synthesises at
the new rate rather than time-stretching, and the response is near linear at
about 100 wpm per unit of speed. `af_nova` needs by far the largest correction
because it is the fastest voice on the roster; if it ever reads as dragged the
answer is a naturally calmer B voice, not a smaller correction, which would
leave B a fifth faster than the anchor.

`VOID_KOKORO_VOICE_A/B/C` and `VOID_KOKORO_SPEED_A/B/C` override any of them.

Measured pitch and brightness across the English roster (same line, 2026-09-19)
live in this session's voice samplers; the useful facts: `af_sky` (147 Hz,
1954 Hz centroid) is the darkest well-behaved female voice, `am_onyx` (85 Hz)
and `bm_lewis` (86 Hz) are the two documentary-deep males, `am_michael` (the
anchor until 2026-09-19) is darker than `am_puck` and reads 157 wpm at 1.08.
Speed must be calibrated per voice, and against REAL rundown copy: absolute
wpm swings about 30 % with the passage, so the four long turns of
`tests/fixtures/radio_bench_turns.json` are the reference (a single short line
over-counts, because its leading silence does not scale with speed).
A voice can also be a BLEND of roster voices (weights summed over
`get_voice_style`), which keeps a dark timbre while borrowing stability from a
better-trained voice.

Not available: `af_jadzia`. It appears in third-party sample repos but is in no
hexgrad release and no published embedding exists, so there are no weights to
load.

edge-tts (Andrew + Ava) remains only as the automatic fallback: it rides an
unofficial Microsoft endpoint with a documented commercial terms-of-service risk
and has broken without notice before. A show never depends on it, but a show
always ships. `VOID_TTS_ENGINE=edge` forces it; `VOID_RADIO_FORMAT=0` restores
the legacy single-script path entirely.

Measured 2026-09-18 on a 4-core sandbox: real-time factor 1.4 (a 9-minute show
is about 13 minutes of synthesis). The worker deadline is 1500 s; the CI bench
(`tts_bench.py`) fails above rtf 2.0.

## Sound and mastering

Music only under the menu and the sign-off. Per-voice chain (ffmpeg): high-pass
80 Hz, -1.5 dB at 250 Hz, +2.5 dB at 4 kHz, de-esser, 3:1 compression, +-7 %
pan (A left, B right). Mix -> limiter at -1 dBTP -> two-pass EBU R128 loudnorm
to -16 LUFS integrated, LRA 11 -> 128 kbps CBR stereo 44.1 kHz. Size ladder
under the 12 MB cap: 128k stereo -> 96k stereo -> 96k mono; the editorial is
never dropped.

Silence grammar (`RADIO_GAPS`, ms): sign-on starts 500 before the ident ends;
open -> menu 600; menu items 400; menu -> story 900; same speaker 250, speaker
change 320; story -> story 850; brief items 450; briefs -> kicker 1200; ->
throw 700; throw -> stab 300, stab -> editorial 450; editorial paragraphs 650
(900 around a one-sentence verdict); editorial -> close 900; outro starts 400
before the sign-off ends.

## Chapters

The timeline is built from the synthesised turn lengths and the gap table, so
chapter offsets are exact by construction: Headlines (0 s, covers ident,
sign-on and menu), one chapter per lead story (title from the marker, rank,
cluster id, permalink when archived), Also today, One more, The editorial
(starts at the throw line; `opinion_start_seconds` keeps that meaning).
`news_start_seconds` is where STORY 1 begins.

Stored as `daily_briefs.audio_chapters` (JSON) and `news_start_seconds`,
exported into `brief.json`, embedded as ID3v2 `CHAP`/`CTOC` frames in the MP3
(Apple Podcasts and most apps), and written as a Podcasting 2.0 sidecar
`<date>-<slot>.chapters.json` + `latest.chapters.json` next to the MP3,
referenced by `<podcast:chapters>` in `podcast-world.xml`.

## Operating it

- Daily: step 7d of `pipeline/main.py`. `[radio:world]` log lines carry the
  rundown word count, engine, rtf, wpm, loudness and chapter count.
- Regenerate today's show without the pipeline: `refresh-brief.yml` with mode
  `radio-dry-run` (rundown + validator report only, one flash call) then
  `radio` (rundown + audio + static export + commit).
- Offline: `python pipeline/refresh_brief.py --radio-only --rundown-file
  tests/fixtures/radio_rundown_2026-09-18.txt --render-dir /tmp/onair` renders a
  fixture rundown to a folder with no Gemini and no database.
- Gemini budget: one flash call per day, plus one on a validator retry.

## Ear-test checklist (CEO)

Sign-on lands in the ident tail, not under it. Menu bed is gone before story 1.
No bed under any story. Both voices within the first sixty seconds. No names,
no thanks. All numbers spoken as words. Kicker absent on a mass-casualty day.
The stab reads as a page-turn, not a jingle. Room tone never audible as hiss.
No clipping. Chapters show in the site player, in Apple Podcasts (ID3) and in a
Podcasting 2.0 app (sidecar). Speech rate about 156 wpm, the same in every voice (printed in the log).
