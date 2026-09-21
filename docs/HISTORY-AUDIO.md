# History: the audio edition


## Catalogue state

**62 of 78 scripts written. 49 of 78 episodes rendered and live.**
(Snapshot taken 2026-09-20. It goes stale; the register below regenerates.)

The one-stop record of every episode is `docs/data/history-episodes.csv`
(33 columns, one row per event) plus a narrower `history-episodes-sheet.csv`
for sharing. Both regenerate from the event YAML, the committed scripts, the
audio manifest and git history:

```
python3 pipeline/history/episode_report.py
```

It answers, per event: what to review and why, the cast anchor and the rule
that chose it, the cold open's misconception, the shape (scenes, rests,
documents, accounts), estimated against rendered runtime, and **which rules a
script predates** — derived by comparing the script's first commit against the
commits that introduced each rule, so a script written before H-11 is flagged
without anyone remembering to flag it.

Two things that register currently surfaces:

- **Four rendered episodes exceed the 15.0 minute format ceiling** (Congo Free
  State 15.46, Rise of Islam 15.43, Russian Revolution 15.37, Indian
  Independence 15.36). All sit under the audio gate's 15.5, so they shipped.
  They are a re-cut or an accepted exception, not a defect.
- **39 of the written scripts predate H-11.** They are not known to be wrong;
  they were never checked against that rule.

To ask what is left to make, ask the manifest rather than a list:

```
python3 pipeline/history/publish_audio.py --pending 99
```

The catalogue is complete when that returns `[]` and the live manifest carries
78 episodes.

---
Status: BUILT, 2026-09-20. Stages 1 and 2 are shipped and live; stage 3 is
in flight. What follows describes what exists, not what is intended.

Every one of the 78 History events becomes an 8-12 minute produced audio piece:
written for the ear, cast by the event's own mood, scored per scene, and
mastered to the same standard as On Air.

This is a ONE-TIME build. It does not run on a cron and it is not a pipeline
stage. The scripts are authored in-session and committed as data; the renderer
reads them. That is not a shortcut, it is the only workable design (see
"Why the scripts are not generated").

## The reference

The CEO named seven: NPR, NYT, Conflicted, Ken Burns, MKBHD, Veritasium,
Vsauce, plus "Screenplay". Averaged together these produce mush, because they
disagree: Vsauce digresses, MKBHD does not; Ken Burns is solemn, MKBHD is
breezy. So each one is assigned a STRUCTURAL ROLE and is allowed to own that
role and nothing else.

| reference | contribution | where it is allowed |
|---|---|---|
| Veritasium | the misconception hook: you think you know this; you do not | COLD OPEN only |
| Screenplay | arrive late, leave early. Scene, not summary | every SCENE |
| Ken Burns | present tense, accumulative particulars, and PRIMARY SOURCES READ ALOUD | the spine |
| MKBHD | crisp direct address: "here is what that actually meant" | the ASIDE after a scene |
| Conflicted | moral seriousness without solemnity; the wry, human aside | register, throughout |
| Vsauce | the zoom-out that reframes the whole thing | THE TURN, once, late |
| NPR / NYT | restraint, attribution before claim, scoring | sound design + CLOSE |

The one that matters mechanically is Ken Burns: **a different voice reads the
documents.** That is a dramatic device, not a style coat, and it is the reason
the format is two voices rather than one.

## The format

Derived from the data that actually exists in every `data/history/events/*.yaml`
(verified across all 78: 5 perspectives each, 3-6 primary source excerpts each,
none missing, median 3,181 words of source prose against the ~1,450 a ten-minute
episode needs — so every script is SELECTION, never padding).

```
theme (era motif)
COLD OPEN    N   the misconception, from `subtitle` + `summary`. 2-4 sentences, no names yet
TITLE        N   "<title>. <date_display>."                                  [ident]
SCENE 1      N   arrive late: one moment, one place, one person. From key_figures + summary
DOCUMENT     D   a primary_source_excerpt, attribution spoken by N BEFORE the read
ASIDE        N   what that meant. Direct, short, MKBHD register
SCENE 2-4    N   the event proceeds. Each scene ends on a fact, not a conclusion
DOCUMENT     D   (2-4 per episode, always attributed first)
THE TURN     N   the perspectives: same event, five accounts, and what each OMITS
CLOSE        N   from legacy_points. Ends on a particular, never on a moral
outro (fading to silence)
```

**Every side gets its own case. This is the moat, and it is enforced.**

The first draft of the Partition script got this wrong in a way worth
recording, because it is the failure this format will keep drifting toward.
It summarised all five perspectives in about 280 words and characterised each
one BY WHAT IT OMITS. That is a debunking format wearing a balance costume:
every account is introduced only to be undercut, and the strongest fact in the
Pakistani case (the Muslim League winning 446 of 495 Muslim seats in 1946) was
left out entirely while the account was still called incomplete.

So a `PERSPECTIVE` segment now gives each account its own hearing: its argument
in its own terms, its strongest fact, and its own witness quoted by the
document voice. Only after all five have spoken does a closing TURN name what
each leaves out, and it names one for every side including the most recent and
most sympathetic.

`H-09` makes this structural rather than editorial: the event data names the
sides, so an episode that quietly drops one does not render. The gate is
verified against a script with the Pakistani account cut out.

An episode that ends "here are five accounts, each true, each with a hole, and
the holes are not random" is a history programme nobody else is making. An
episode that ends "here is what everyone gets wrong" is one that many people
make badly.

**Attribution before the claim**, exactly as On Air does it: the narrator says
who wrote it, where and when, and THEN the document voice reads. The listener
always knows whose words they are hearing before they hear them.

## Casting: 5-6 voices, chosen by the data

Every casting input already exists as a structured field, so the choice is
DETERMINISTIC and testable rather than a per-episode judgement: `severity`
(catastrophic 49 / critical 15 / major 14), `category` (9 values), `era`
(6 values), `region`.

The shortlist and the mapping are finalised after the ear test (a 10-voice
audition on a Ken Burns-register passage is rendered; grades from hexgrad's
table are a training-data measure, not a naturalness score, so they inform but
do not decide). The shape:

| role | used for | selection |
|---|---|---|
| Narrator | the whole episode | cast per event from `severity` + `category` |
| Document | primary sources and perspective witnesses ONLY | fixed per narrator, chosen to contrast (sex, register, accent) |

The document voice is a READER OF RECORD, not an impersonator. It does not
change per speaker and it is not accent-matched to the event's region: casting
an Indian voice for Partition and a Russian one for Chernobyl is a short road
to caricature, and one voice would still be reading Nehru, Gandhi and Jinnah
regardless. Attribution before every read is what removes the ambiguity, so
the voice never has to act.

Constraints the mapping must satisfy:
- A narrator and its document voice must never be confusable. The voice change
  is load-bearing: it is what tells the listener "these are real words".
- No voice is stretched. Pace is a casting decision (the On Air rule): a voice
  whose natural rate is wrong for a grave episode is not slowed, it is not cast.
- Every voice must hold 10 minutes. Auditions are judged on a full paragraph,
  not a line, because thinner-trained voices fall apart over distance.

## Sound

The same principles as On Air, which are now proven: one motif family, music
with an ARC per scene (enter, hold, leave), every fade-out landing UNDER a
sentence, beds darker as well as quieter under speech.

What differs: History gets **era motifs**. One family, six variations selected
by the `era` field, so a classical episode and a contemporary one are audibly
the same programme in different light. All synthesised in-repo by
`generate_assets`, no licensed material, per the originality rule.

## Why the scripts are not generated

`gemini-2.5-flash` is capped at **20 requests per day** on the free tier. 78
premium scripts is four days of budget, and flash-lite is not good enough for
this writing. More importantly, a generated script would need the same
validator-and-retry apparatus On Air needs, to police a model that cannot see
the whole catalogue and cannot keep 78 episodes from converging on one shape.

So the scripts are authored in-session and committed as
`data/history/scripts/<slug>.txt` in a marked-up format the renderer parses
(the same discipline as the radio rundown: segment markers, speaker prefixes,
`## SAY` respellings). This costs zero Gemini budget, produces better prose,
and makes every script reviewable and re-renderable forever.

## Pipeline

| piece | reuse or build |
|---|---|
| Synthesis, voice buses, ffmpeg chain, loudnorm, encode, ID3 chapters, sidecars | REUSE from `radio_producer` (format-agnostic) |
| `apply_duck`, `_loop_to`, `weave_end`, the arc logic | REUSE |
| `build_timeline` / `render_music_bus` | PARALLEL implementation: they hard-code the radio segment kinds |
| Script parser + validators | NEW, modelled on `radio_script_generator` |
| Era motifs | NEW in `generate_assets` |
| Storage | **Cloudflare R2** (CEO decision) |

**R2, not git.** 78 episodes at On Air quality is ~750 MB against a repo whose
entire history is 167 MB. Git binaries cannot be un-committed cleanly, so this
is the one decision in the build that is expensive to reverse. R2 was already
the flagged follow-up in CLAUDE.md for exactly this reason, and it lets the
catalogue keep full 128k stereo instead of being degraded to fit a repo.

## Delivery: how an episode reaches a reader

Rendering an episode is not shipping it. The path from a rendered file to a
playing Listen button is three things, and only the first is audio:

1. `pipeline/history/publish_audio.py <slug> --from <render dir>` copies the
   MP3 and its chapter sidecar into `frontend/public/audio/history/` and
   records the episode in `frontend/public/data/history-audio.json`.
2. `frontend/app/history/audio.ts` imports that manifest at BUILD time (it is
   committed with the audio it describes, so a fetch would only make the
   Listen button arrive late) and fills `audioUrl` / `audioDuration` /
   `audioChapters` onto every event, in the row mapper and the fallback alike.
   It is the only module that knows where the audio lives.
3. The player already handles it: `playHistory` passes the chapters through
   `coerceChapters`, so an episode gets the same chapter rail as On Air. A
   History chapter carries `kind: "segment"`, which draws the title alone with
   no "No. 3" or "Opinion" badge beside it.

**The catalogue lives in a GitHub Release, not in git and not on R2**
(changed 2026-09-20; this section previously said the Pages CDN, and that is no
longer true). Committing ~750 MB of MP3 could not be undone, and the R2 bucket
is still not provisioned, so the episodes are uploaded to a Release and the
Cloudflare deploy pulls them into `frontend/out/audio/history` at build time
via `pipeline/history/release_store.py fetch`. The deploy **fails loudly** if
the manifest names a file the Release does not have, so a page can never ship
pointing at audio that does not exist.

The manifest is what kept that change cheap, and still does: every consumer
reads its `url`, so moving to R2 later is a change to the strings
`publish_audio.py` writes and nothing else.

`tests/test_history_audio.py` is the gate (in `auto-merge-claude.yml`): every
manifest entry has its MP3 committed at the size and duration claimed, under
the 25 MiB Cloudflare Pages per-file limit, naming a real event, with ordered
chapters starting at zero; and every MP3 in the deploy tree is in the manifest,
so audio cannot sit in git unreferenced by any page.

Two things this does NOT do, deliberately: it does not lift the `/history/*`
301 in `_redirects`, and it does not change where History gets its events
(still Supabase-or-mock; the static-JSON rewrite is the separate piece of work
that un-hides the section). The audio is ready and reachable ahead of both.

## House promo (post-roll)

The close ends on its particular, the outro starts, and a beat later the house
voice reads a two-sentence promo for On Air, Weekly or the site under the
outro's held bars. The episode's length does not change, so H-07 and the
15.5 minute gate are untouched, and the outro still falls to silence after
it. Selected by the sha256 of `history:<slug>`, so every re-render of an
episode carries the same promo; it appears as a final chapter, kind
`segment` (the only kind the rail draws without a badge), titled "Also from
Void News", and the manifest entry records `promo: {id, sha, voice,
startTime}`.

Episodes rendered before the promo existed are retrofitted without TTS:
`pipeline/history/stitch_promos.py` fetches the master from the release,
decodes it, lays the promo in, re-encodes once at 128k, rewrites the chapters
and the manifest (with a full-file `?v=` fingerprint and `renderedAt` kept
from the original render), and replaces the release asset. The un-stitched
master is parked under the release tag `history-audio-clean` so a later copy
change re-stitches from the original. Guards, measured on every episode:
integrated loudness within 1 LU of the original, true peak at or below
-0.8 dBTP, the promo within 3 dB of the last eight seconds of speech, the
last 300 ms below -50 dBFS, and the outro's fall byte-identical. Workflow:
`.github/workflows/stitch-promos.yml`.

## Staging

Each stage answers a different question and must be signed off before the next.

| stage | count | the question it answers |
|---|---|---|
| 1 | Partition of India | Does the format work at all, end to end? |
| 2 | 5 episodes | Does mood-casting hold across registers, and do five scripts sound like five stories or one formula? |
| 3 | 10 episodes | Does the pipeline hold: render throughput, R2 upload, player, chapters? |
| 4 | 62 remaining | Execution. |

Stage 2's question is the one most likely to fail, and it cannot be answered by
stage 1: a single good episode proves nothing about whether the format has
enough range. The five are deliberately chosen to span severity, era and
category (e.g. a genocide, a cultural moment, an ancient empire, a disaster, a
revolution).

**Throughput was the binding constraint, and it is solved.** 78 x 12 min is
~15 hours of audio, and rendering them one after another is about that long in
wall clock. `.github/workflows/render-history-audio.yml` fans them out instead:
one slug per matrix shard, ten at a time, each uploading its episode, then a
single publish job folds everything into the site in ONE commit (ten jobs each
committing to the same branch is a race, and the manifest is one file).

Measured on the first real runs: a 1,584-word episode took **8m40s end to end**
on a GitHub runner, including checkout, dependencies and mastering, with the
Kokoro venv and model files coming from cache. At ten wide that puts the whole
catalogue at roughly ninety minutes.

Dispatch it with an explicit list of slugs, or with `auto` to take the next N
scripts that have no published episode. "What is left to make" is answered by
the manifest (`publish_audio.py --pending N`) rather than by a list somebody
maintains by hand, so the workflow cannot drift from what has actually shipped.
The publish job runs on `always()`, so nine good episodes do not wait on a
tenth that failed, and it runs the manifest gate before it commits.

## Verification

- Script gates (`pipeline/history/script_format.py`), each verified against a
  planted defect in `tests/test_history_script.py` rather than merely written.
  That file exists because H-04 was silently weak: it matched the speaker's
  name as a RAW SUBSTRING of the preceding narration, and "king" is inside
  "striking", so a civil rights script that never named Martin Luther King
  passed the gate on the strength of the phrase "without striking back". The
  rule now matches on words, with a leading-edge match in both directions so a
  possessive still names its speaker. Re-running all fifteen committed scripts
  against the tightened rule found exactly one defect, the one that exposed it.
  The rules:
  - `H-01` every quote exists in the event's own `primary_source_excerpts` or
    `notable_quotes`, by word overlap so trimming for the ear is allowed and
    inventing is not. A fabricated quotation is the one unrecoverable failure
    in a history programme.
  - `H-04` the narration NAMES THE SPEAKER before the voice reads. Checking
    that some narration came first is not enough: a perspective argues before
    it quotes, so that weaker test passes even when nobody is named. The
    speaker is looked up from the data by matching the quote, which also
    catches crediting the wrong person.
  - `H-09` every perspective in the data is given its own case.
  - `H-02` the document voice speaks only where a quote belongs.
  - `H-06` the episode carries a TURN.
  - `H-07` length inside 8-15 minutes, measured **at the cast narrator's own
    speech rate**, not one average. The rates differ enough to matter
    (`bm_daniel` 168 wpm against `am_michael` 140), so a script legal at the
    average runs long when the slow voice reads it. `NARRATOR_WPM` carries the
    measured rates; `estimated_minutes()` looks up the anchor from the event.
  - `H-10` (advisory) spelled-out ordinals and numbers, since a digit read
    aloud is a defect an ear catches and a validator should catch first. A
    silent H-10 is not proof: it matches on a six-character root.
  - `H-11` a line the record itself disclaims — a paraphrase, a reconstruction,
    a secondhand account, a speech written in someone else's voice — may only
    be read in the DOCUMENT voice if the marker or the narration says so out
    loud. Without it, the programme puts words in a real person's mouth and
    presents them as that person's own. It fired on a Patricia Crone
    paraphrase about to be voiced as her words.
- Render gates: reuse the On Air assertions (gaps, arcs, fades landing under
  speech, loudness within tolerance, TP and LRA, chapters exact).
- `tests/test_history_audio.py` holds the published catalogue to its manifest.
  Since the MP3s moved to a Release they are no longer in a clean checkout, so
  the **sidecar is the in-repo proof** and the size and duration checks read
  the recorded values: every entry at the size and duration claimed, under the
  25 MiB Cloudflare Pages per-file limit, naming a real event, chapters ordered
  from zero, and no MP3 in the deploy tree that no page serves.
- Served: episodes reachable from the CDN, chapters render, player resumes.
- Ear test per stage, by the CEO, before the next stage starts.
