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
theme (8.0 s)                                                    [one motif: every cue below is this figure]
OPEN      voice A   sign-on, starting 1.2 s before the theme ends, over its release
MENU      A/B       "On the desk today." then five headlines                    [menu bed]
STORY 1   A leads   rank 1 in depth
transition (2.9 s)  the theme's cell, in the clear
STORY 2   B leads   rank 2
BREAK (9.0 s)       four bars, instrumental, the programme breathes
STORY 3   A leads   rank 3
transition
STORY 4   B leads   rank 4
transition
BRIEFS    A/B       "Also on the desk." then ranks 5-12, one sentence each
FINALLY   B         "One more before Void Opinion."                              (absent on a mass-casualty day)
opinion entrance (6.5 s)  minor shading, dotted pulse, ends on an open fifth
OPINION   C         the opinion script, starting over the entrance's tail        [opinion bed]
CLOSE     A         "That's On Air from Void News." + a fact + the tag           [close bed]
outro (14.0 s)      four bars resolving to low D, then a 5.5 s fall to TRUE silence
```

There is no spoken throw. The entrance music announces the segment and the
opinion script's own first line ("Now, void opinion.") does the naming; a voice
saying "Next, the editorial." immediately before that was two names for one
thing, back to back. The segment is **Opinion** everywhere: chapter kind
`opinion`, chapter title `Opinion`, `opinion_start_seconds`. Episodes rendered
before 2026-09-19 carry kind `editorial` and the player still resolves them.

**One motif.** `generate_assets._theme_figure` holds the theme's musical
content (120 bpm, cell D3-A3-D3-F#3 over a half-time D2 bass, breathing pad),
and the transition, the break, the opinion entrance and the outro are all calls
to it. The refactor is verified lossless by sha256: the theme is byte-identical
to the one it replaced.


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
| R-06 | Word budgets at ~165 wpm per segment, five menu lines, six to eight brief items, 850-1150 news words | fail outside +-25 % |
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
| A, the anchor | `am_puck` | 1.00 | -7 % | light American, 112 Hz, 164 wpm. The one voice that hits the worker's -1 dBFS clamp |
| B, alternate stories | `af_bella` | 1.00 | +7 % | A-grade, 177 wpm. Replaced `af_nova`, which was C-grade and the roster's fastest at 205 wpm |
| C, the editorial only | `af_heart` | 1.00 | centre | the roster's other A-grade voice, 162 wpm; centred, because it speaks alone |

**Every voice reads at its own natural rate, and pace is a casting decision.**
Kokoro's voices are trained at the pace of their training audio. The `speed`
knob scales predicted phoneme durations away from that distribution, and the
further it is pushed the more the read acquires the flat, stretched quality
that gets heard as synthetic. So a voice whose natural rate is wrong for the
show is REPLACED, never stretched, and two readers a few wpm apart is what a
real desk sounds like.

This reverses the one-pace calibration of earlier the same day, which had put
all three at about 156 wpm. The correction it required of `af_nova` (0.82) was
the largest on the desk, and `af_nova` was also the voice the CEO picked out
as artificial: cause and effect, not coincidence.

Natural rates, measured on the four long turns of
`tests/fixtures/radio_bench_turns.json` (real rundown copy: a short line
over-counts because its leading silence does not scale, and absolute wpm
swings about 30 % with the passage, so only same-passage numbers compare):
`af_nicole` 114, `af_heart` 162, `am_puck` 164, `af_bella` 177, `af_kore` 181,
`af_aoede` 183, `af_sarah` 188, `bf_emma` 196, `af_nova` 205. Grades from
hexgrad's own table: `af_heart` A, `af_bella` A-, `af_nicole`/`bf_emma` B-,
`af_sarah`/`af_aoede`/`af_kore` C+, `af_nova` C. `af_aoede` is the warmest
timbre on the roster (1943 Hz centroid) if brightness is what reads as
synthetic. `VOID_KOKORO_VOICE_A/B/C` and `VOID_KOKORO_SPEED_A/B/C` override
any of it.

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
Podcasting 2.0 app (sidecar). Each voice at its own natural rate; no voice is stretched (wpm printed in the log).
