# History audio: archival recordings as artifacts, and a mood-aware production

Status: PROPOSAL, 2026-09-25. Design and one script only. Nothing here is
implemented in the producer, nothing is downloaded, and no clip is licensed.
The Partition of India script (`data/history/scripts/partition-of-india.txt`)
is the pilot: it is re-cut against its evidence ledger, it carries inert
`# MOOD:` and `# CLIP:` directives, and it renders today exactly as any other
script does.

The CEO's direction, verbatim: "While we redo audio, make it more interesting,
at least for the events after the 20th century began: real audio footage of
real people as artifacts. Make this $0 but premium." And: "Can the audio be
mood aware? Cinematic? Original but realistic like a true audio production?"

Two rules stand over everything below. Rule 1: nothing Void publishes may
contain a factual error, and a clip is a factual claim about who spoke, when,
where and on what occasion. $0: no licence fee, no paid API, no paid voice,
nothing that costs money to render or to serve.

---

## 1. The concept: a recording is an exhibit

The thesis page (`docs/proposals/HISTORY-THESIS-PAGE.md`) already holds
exhibits: an image or a map with provenance first, what it shows, what it does
not show, its licence, its URL. An archival recording is the same object with
a waveform instead of pixels. It lives in the ledger, it carries the same
provenance block, it is rendered on the page with a player and its transcript,
and the episode plays it in the place a DOCUMENT read would otherwise go.

What it is not: colour. A recording is admitted for the same reason a document
is, because it is the record. It is never admitted because it sounds good.

**How it sits against the Kokoro voices.** The format has two voices: a
narrator, and a document voice that reads the record. A real recording is a
third thing, and the listener must never mistake it for either. So:

- **Attribution before the clip**, exactly as before a DOCUMENT read, and
  one word more: the narrator says it is a recording. "Nehru, to the
  assembly, in the All India Radio recording." The credit is spoken, not
  only printed, because a podcast listener cannot see the page.
- **A silence before and after.** 900 ms of nothing before, 1,200 ms after.
  No music runs under a real voice, and no music runs into or out of it. The
  bed leaves before the clip and returns after the silence, on a fade that
  lands under the narrator's next sentence, never under the clip's last word.
- **No bed under a real voice.** House rule, absolute, and mechanised in §6.
- **One treatment, always the same, so the ear learns it.** A clip is
  presented in its own room: mono, band-limited as the source is, with its
  own noise floor left alone. It is not "cleaned" to sound like Kokoro. The
  1947 shellac hiss is part of the provenance; a listener who hears a clean
  studio voice saying "Long years ago" has been handed a re-enactment.
- **A short in, a short out.** 60 ms fade in, 180 ms fade out. No reverb, no
  EQ beyond a high-pass at 60 Hz to remove rumble the source never had.
- **Bounded.** A clip is at most 45 s, at most two per episode, and never
  the cold open. The episode is a Void production that holds artifacts, not a
  compilation of other people's audio.

What makes it premium is restraint: the credit, the silence, the untouched
floor, and that it happens once or twice, in the place where the document
would have been read, so the listener understands that they are now hearing
the thing itself.

---

## 2. Rights policy (the CEO's decision)

Every option is stated with its real exposure. The recommendation follows.

### Option A: strict

Admit a recording only if it is **public domain in the United States AND in
its country of origin**, or carries **CC0 / CC-BY / Public Domain Mark applied
by the rights holder or a repository that states the basis**, with the licence
visible at the source URL the ledger records.

Exposure, honestly:

- **URAA restoration.** A foreign work that was public domain in the US
  for want of formalities was restored on 1 January 1996 if it was still
  protected at home. So "old and foreign" is not "public domain in the US".
  A 1947 Indian broadcast is safe only if it was out of copyright in India on
  the URAA date or is a government work under a term that has run.
- **Indian government works** run 60 years from publication (Copyright Act
  1957, s. 28). All India Radio's 1947 recordings, as Government of India
  works, are out of term in India. That does not by itself settle the US
  position, but a work whose home term had expired before 1996 was not
  restored, and 1947 + 60 = 2007 is after 1996, so the strict reading is that
  the AIR recordings WERE restored in the US and run there for 95 years from
  publication (to 2043). This is the single biggest exposure in the whole
  programme, and it applies to the best material.
- **Public Domain Mark is not a licence.** It is a repository's assertion.
  Public.Resource.Org's CC0 on the Nehru upload is the uploader's dedication
  of whatever rights the uploader holds, which for a Government of India
  recording is none. The ledger records what the source says; the policy
  decides what that is worth.
- **BBC, All India Radio (Prasar Bharati), British Pathé, Radio Pakistan**
  own their catalogues and license them commercially. Nothing on their own
  sites is open. A clip that only exists on one of them fails strict.
- **Estates.** A speech is a literary work with its own copyright, separate
  from the recording. Nehru died 1964, Jinnah 1948, Gandhi 1948, Mountbatten
  1979: in India (life + 60) Nehru's speeches entered the public domain in
  2025, Jinnah's and Gandhi's in 2009; in the UK (life + 70) Mountbatten's
  run to 2050. A Crown-copyright broadcast by a Viceroy is Crown copyright
  (50 years from publication), so the speech is clear, but the BBC's or
  AIR's recording of it is not.

Yield under strict: low. Of the candidates in §7, one (Nehru, Tryst with
Destiny, archive.org, CC0 as stated, "Audio Source: All India Radio") passes
on the letter of the licence at source and fails on the URAA reading above.
None passes both cleanly.

### Option B: strict, plus UN and tribunal records under their published terms

Everything in A, plus recordings the **UN Audiovisual Library**, the **ICTY /
IRMCT court records**, the **ICJ** and national **parliamentary broadcasters**
publish under written reuse terms (the UN's terms allow non-commercial
educational use with attribution; IRMCT court audio is public record). This
opens the post-1990 catalogue: Srebrenica (ICTY testimony and the 1995 UN
briefings), Rwanda (ICTR), the UN Security Council on Iraq 2003, and a
Security Council meeting for most post-1946 events.

Exposure: the UN's terms are non-commercial; Void carries no advertising and
sells nothing, but "non-commercial" is the publisher's reading, not ours, and
the ledger must record the exact terms text and date. Tribunal audio of a
witness carries a privacy interest the court has already weighed; Void adds
nothing to that and quotes only what the public transcript carries.

Yield under B: real for events after 1990, nil for 1900 to 1990 beyond A.

### Option C: short-excerpt fair use

Admit any recording of the historical event itself, up to 30 seconds, with
the provenance block, a spoken credit and a transcript, on a fair-use reading
(US, 17 U.S.C. §107: criticism, comment, news reporting, teaching; a short
excerpt; a factual work; a use that substitutes for no market).

Exposure: the site is served from Cloudflare (US law for the host), but a
podcast feed reaches every jurisdiction and the UK's fair dealing is narrower.
A rights holder can send a DMCA notice; Cloudflare will act on it, and the
release that holds the MP3 is one takedown from silence for the whole
catalogue. Fair use is a defence, not a permission, and Void has no counsel
budget. The doctrine also does not cover the recording's separate literary
copyright in the words when the words themselves are still in term
(Mountbatten in the UK to 2050).

Yield under C: nearly every twentieth-century event has something.

### Recommendation: B, with the URAA reading stated on the page

Adopt **Option B**. Under it, admit a recording when (i) the source states an
open licence or PD mark, (ii) the ledger records the licence text, the
rights-holder's identity as best the record gives it, and the URAA reading,
and (iii) a human has signed the entry. Where the URAA reading is adverse but
the home-country term has run and the repository is one that removes on
request (archive.org, Commons), the entry says so in the open and is admitted
only after the CEO signs it; the page's provenance block prints the basis, so
a reader sees exactly what Void is relying on. Do not adopt C: one takedown
against the History release is a worse outcome than a catalogue with fewer
clips, and a programme built on Rule 1 should not rest its artifacts on a
defence.

The practical consequence for Partition: **one clip qualifies under B with a
CEO signature (Nehru), none without it.** That is the honest yield, and it is
still a premium episode, because the design in §1 makes one clip land.

---

## 3. Authenticity under Rule 1

A clip is a factual claim four times over: this person, this occasion, this
date, these words. Each is checked, and each check is a gate, not a note.

**Identity and occasion.** The ledger entry names the archive, its item id,
the item's own metadata (title, creator, date, description) as fetched, and
what the archive does NOT say. The Nehru item on archive.org says "Audio
Source: All India Radio" and "1947-08-14"; the Commons copy of the same
speech says "Source: YouTube". The first is admissible provenance; the second
is not, and the entry says why. An item with no date, no creator and no
description (the anonymous Jinnah tapes on archive.org, §7) is not admitted
whatever it sounds like.

**Transcript.** The clip's transcript must be the ledger extract it is
cited against, and the audio must match it. The check is mechanical and $0:

- `faster-whisper` (CTranslate2, CPU, int8; the `base.en` model is about
  75 MB and is cached on the runner like the Kokoro venv) transcribes the
  clip. On a 1947 AM broadcast the word error rate will be high; the check
  therefore does not demand a match, it demands **alignment**: after
  normalising both to lower-case alphanumerics, the stored transcript's
  words must recur in order in the ASR output at a coverage of at least 0.70
  over a window, and the in/out points must fall inside the aligned span.
  The threshold is calibrated on the pilot and stated in the gate, and a
  planted wrong clip (the same speaker, a different speech) must fail it.
- Non-English audio (the Gandhi prayer speeches on archive.org are in
  Hindustani, and the ledger's extract is a third-person English report) is
  **not verifiable by this check**, and a clip of it is not admitted until a
  Hindi model has been evaluated on the pilot and the extract is a transcript
  in the language spoken. A voice is not evidence of words.
- `whisper.cpp` is the fallback if the Python package's wheel fails on the
  runner; same model family, same check.

**The page shows the transcript** beside the player, as the exhibit's
caption, and the words are the extract. So a reader can check the clip by
ear against the same text the gate checked it against.

**What a clip may not do.** It may not be trimmed inside a sentence, may not
be joined from two places in the source, may not be sped up or pitch-shifted,
and may not be denoised into a different room. The producer refuses any
in/out pair the alignment does not cover.

---

## 4. Data model, directive, producer, page, checks

### 4a. Ledger: the audio artifact

A new `kind: audio` exhibit in `data/history/evidence/<slug>/ledger.yaml`,
beside `image` and `map`:

```yaml
  - id: ex-nehru-tryst-19470814
    kind: audio
    title: "Jawaharlal Nehru, Tryst with Destiny, Constituent Assembly, 14 August 1947"
    speaker: Jawaharlal Nehru
    occasion: "Moving the pledge in the Constituent Assembly of India, Parliament House, New Delhi"
    date: "1947-08-14"
    repository: Internet Archive
    accession: "HindSwaraj-Speech-03-1"
    url: "https://archive.org/details/HindSwaraj-Speech-03-1"
    file: "https://archive.org/download/HindSwaraj-Speech-03-1/tryst.mp3"
    origin_as_stated: "Audio Source: All India Radio (the item's description)"
    licence_as_stated: "CC0 1.0 (licenseurl on the item; uploader Public.Resource.Org)"
    rights_reading: "Government of India work, 60-year term run in India (2007); URAA-restored in the US on the strict reading, to 2043; admitted under policy B with CEO signature"
    signed_by: null
    signed_at: null
    duration_s: 280.9
    excerpt: {in: "00:00:00.000", out: "00:00:38.400"}
    transcript_extract: src-cad-19470814.sec53612
    transcript_check: {tool: faster-whisper, model: base.en, coverage: null, verified_at: null}
    sha256: null
    shows: "Nehru's voice, in English, from the opening of the pledge to 'life and freedom'"
    does_not_show: "the Hindustani speech that preceded it, and the hall's response, which the recording does not carry"
```

`sha256`, `coverage` and `verified_at` are written by the check, never by
hand; an entry with any of them null renders on the page as a candidate and
in the episode not at all.

### 4b. The script directive

Comment-prefixed, so today's parser skips it (`parse_script` keeps only
`## ` headers and `N:`/`M:`/`F:` lines) and the producer that learns it
reads it. It sits inside the DOCUMENT segment it stands in for:

```
## DOCUMENT | Jawaharlal Nehru | Tryst with Destiny, to the Constituent Assembly | August 14, 1947
# extract: src-cad-19470814.sec53612
# CLIP: id=ex-nehru-tryst-19470814 replaces=document status=verified max=45s
N: Then, in English. Nehru, to the assembly, in the All India Radio recording.
M: Long years ago we made a tryst with destiny ...
```

`replaces=document` means the M/F read is the fallback: rendered when the
clip is absent, unsigned or unverified, dropped when the clip plays.
`replaces=none` means the clip is added before the segment as a separate
artifact (the Mountbatten broadcast, if ever cleared, opens SCENE 1 that way).
`status` is advisory in the script; the ledger's `signed_by` and
`transcript_check` decide. The narrator line carries the spoken credit in
both cases, so the fallback is honest too: "in the All India Radio recording"
is only written once the clip is signed, and the pilot script therefore says
"Nehru, to the assembly" until then.

### 4c. Producer changes

In `pipeline/history/history_producer.py`, all reuse, no new synthesis:

1. `parse_script` gains a `directives` list per segment (`MOOD`, `CLIP`,
   `extract`), read from `# KEY:` lines; the validator gains H-12..H-15
   (§4e).
2. `build_turns` emits a `TurnSpec(role=CLIP, path=...)` where a signed,
   verified clip replaces a document read; the synthesiser skips it and the
   assembler loads the excerpt from the ledger's cached file.
3. `_gap` learns two new transitions: `to_clip` (900 ms) and `from_clip`
   (1,200 ms), and `wants_transition` is always False around a clip.
4. `music_bus`: the duck envelope treats a clip cue as speech at full duck
   AND the bed is cut, not ducked, from 400 ms before the clip to the end of
   its trailing silence (`apply_duck(..., mute=[(start, end)])`). Room tone
   is also muted there, so the clip's own floor is the only floor.
5. **Loudness match.** The master is `loudnorm` two-pass to -16 LUFS
   integrated (`radio_producer.loudnorm_two_pass`), which would pump a
   noisy 1947 clip up with its hiss. So the clip is normalised on its own
   first, to **-19 LUFS short-term with a -3 dBTP ceiling**, measured over
   the excerpt only, then laid in; the programme's integrated target is
   unchanged and the clip sits 3 LU under the narrator, where a record
   played into a room would. The gate checks the clip's short-term loudness
   in the master lands within 1 LU of that.
6. Chapters: a clip gets its own chapter, kind `segment`, titled with the
   exhibit's title, so the rail names it and the page's episode marks can
   point at it.
7. The manifest entry records `clips: [{id, startTime, endTime, sha256}]`
   so `tests/test_history_audio.py` can assert the served file carries what
   its row claims.

### 4d. The page

The exhibit card that already renders `image` and `map` gains an `audio`
form: provenance first (repository, accession, origin as stated, licence as
stated, rights reading, signed by), then a native `<audio controls preload="none">`
on the excerpt, then the transcript as the caption, then `does_not_show`.
The player is the site's own element under `AudioProvider`, so it obeys the
one-transport rule and pauses the episode if one is playing.

### 4e. Checks

| Gate | Fails on |
|---|---|
| H-12 rights allowlist | a `CLIP` whose exhibit has `licence_as_stated` outside the allowlist for the policy in force, or `signed_by: null` |
| H-13 provenance | an exhibit missing any of repository, accession, url, date, speaker, occasion, origin_as_stated |
| H-14 transcript match | `transcript_check.coverage` below the threshold, or `verified_at` null, or the in/out outside the aligned span; the fixture is the same speaker in a different speech |
| H-15 spoken credit | a `CLIP` whose preceding narrator line does not name the speaker AND say "recording" (or "broadcast") |
| H-16 caps | a clip over 45 s, more than two per episode, or one in the OPEN |
| H-17 no bed under a real voice | in the rendered master, RMS of the music bus within the clip's span plus 400 ms either side above -60 dBFS; and no ambience or foley cue whose span begins or ends within 3 s of a clip (§6) |
| `test_history_audio` | a manifest `clips` entry whose sha256 is not the served excerpt |

Every gate ships with a planted defect, as H-01..H-11 do.

---

## 5. Mood-aware, cinematic, original: the production design

The CEO's second question. This section is the whole answer; §4 is what it
needs from the code.

### 5a. The mood map

Six moods. Each is derived from what the segment carries, not from how the
writer feels about it, so two drafters would tag the same scene the same way:

| mood | the segment carries | score | ambience | pace | voice |
|---|---|---|---|---|---|
| **dread** | a count that is short, a date that is close, a force that is small | motif in the low register, held, no pulse | one sustained designed element (wind, a distant line) | slow, longer rests | narrator at 0.92 speed |
| **procedure** | a document being made: a statement, an award, a telegram | the motif as a slow figure, sparse, dry | paper, a room, a pen; or nothing | even, no rests inside | narrator at 1.0; document voice at 0.95 |
| **rupture** | the moment the thing happens: midnight, the line published | the motif withheld, then one entry on the last word | none, or a single real recording | line, silence, line | narrator at 0.95 with 700 ms line pauses |
| **grief** | the dead, the counts that do not agree, a lament | the motif inverted, high register, thin | none | slow; the longest rests | narrator at 0.9; F voice for testimony |
| **testimony** | one person's own words | NO SCORE under the words | none | the record's own | the document voice at 0.93, never faster |
| **reckoning** | the accounts, the turn, the adjudication | the motif as a pulse under the narrator, thinnest of all | none | brisk, clipped, MKBHD register | narrator at 1.0 |

The `# MOOD:` line is per segment, and the producer reads it to pick the cue
set, the gap lengths and the speed. A segment with no mood inherits the
previous one. The tags are advisory data, never a fact about the event, so
they need no gate beyond "a mood name in the set".

**The Partition script, segment by segment** (as committed):

| segment | mood | why |
|---|---|---|
| OPEN | dread | four wars, five weeks, one census: the numbers are the threat |
| TITLE | (theme) | |
| SCENE 1 The count · DOCUMENT Attlee · ASIDE · DOCUMENT Radcliffe · ASIDE | procedure | a sentence read to the Commons becomes the ground; the only document in Radcliffe's voice; "he hesitated long" is dry |
| SCENE 2 Midnight · DOCUMENT Nehru (CLIP slot) · ASIDE | rupture | the score is withheld until "life and freedom"; the clip, if signed, plays dry |
| SCENE 3 Gurdaspur · DOCUMENT Bhopal record · ASIDE | reckoning | counts against counts; ends where the record stops |
| SCENE 4 How many · DOCUMENT Khosla · ASIDE | grief | the counts that do not agree |
| SCENE 5 The force that was supposed to hold · DOCUMENT Jenkins · ASIDE | dread | a step back in time, said aloud; 7,500 rifles, 12 million people. Chapter 5 keeps the served manifest's title so the thesis's episode mark (T-10) still resolves until the re-render |
| REST | | the longest rest in the episode |
| SCENE 6 The drum · DOCUMENT Sarla Dutta · ASIDE | testimony | one person, her own words; nothing under them |
| TURN Five accounts | reckoning | |
| PERSPECTIVE British | procedure | an administrative account gets an administrative sound |
| PERSPECTIVE Indian | reckoning | |
| PERSPECTIVE Pakistani · DOCUMENT Jinnah | reckoning | |
| PERSPECTIVE Subaltern · DOCUMENT the elders | testimony | |
| PERSPECTIVE Women's · DOCUMENT Pritam | grief | a lament, in translation, said so |
| TURN The shape of the disagreement | reckoning | |
| CLOSE | grief | ends on a particular: one census, any map, five weeks |

### 5b. The original score, at $0

What the repo already does, and this builds on rather than beside:

- `pipeline/briefing/generate_assets.py` synthesises every cue in numpy:
  `_tone`, `_swell`, `_pluck`, `_breath`, `_shaped_noise`, `_reverb_ir`,
  `_reverberate`, and one **parameterised motif**, `_theme_figure(t,
  max_beats, bass_beats, ...)`, which is the On Air identity.
- Weekly's cue family (`docs/WEEKLY-AUDIO.md` §"The score") is **a
  parameter set** on the same motif: half tempo, a different register, the
  sonified spectrum under THE NUMBERS. One programme, one identity.
- History already has era motifs in the plan (`docs/HISTORY-AUDIO.md`
  §Sound): one family, six variations by `era`.

The History score family is therefore a **third parameter set on
`_theme_figure`**, and the moods are parameter sets inside it:

| element | how | parameters by mood |
|---|---|---|
| **Motif** | `_theme_figure` at History tempo (pulse 1.6 s, half of On Air's) transposed down a fifth, played on `_pad` partials rather than the radio bells | dread: bass_beats only, register −12 st; procedure: the figure once, dry, `_pluck` voicing; rupture: the figure's LAST two beats only, entering on cue; grief: the figure inverted (intervals mirrored about the tonic), +12 st, `_breath` depth 0.4; testimony: none; reckoning: the pulse alone, no melody, −20 dB |
| **Era variation** | as planned: six filters on the same figure by `era` (contemporary: the cleanest; classical: the widest reverb IR) | unchanged by mood |
| **Stings** | three, synthesised once: `to_document` (a single low partial, 400 ms, for the change of voice), `to_turn` (the existing transition), `from_clip` (a two-partial swell that begins ONLY after the clip's trailing silence) | one gain per mood |
| **The silence grammar** | REST lengths become mood-aware: `REST` in grief is 4.5 s, in reckoning 2.0 s; the gap before a DOCUMENT read in testimony is 1.4 s; every fade-out lands under a sentence (the On Air rule) and never under a clip | |
| **Dry moments** | testimony is dry by rule; rupture is dry until its last word; a `# DRY` directive can force any segment dry, and a script that goes more than four minutes without a dry segment gets a warning from the register report | |

All of it is generated in code from the existing primitives. No licensed
music, no samples, no soundfonts, no stems downloaded. The one new primitive
worth writing is an **inversion** of `_theme_figure`'s interval list; the
rest is parameters.

### 5c. The realistic soundscape, and the Rule 1 line

Ambience and foley are admitted from two places only: **Freesound, filtered
to CC0** (the site search is reachable without login and the licence filter
is visible on the results page; each sound page states the licence), and
**public-domain field recordings on archive.org** (licenseurl on the item).
Each sound is a ledger row of its own kind (`kind: sound`) with title,
uploader, id, URL, licence as stated, and a `designed: true` flag. Nothing
from a commercial library, nothing "royalty-free" under an unnamed licence.

The line that must not be crossed: **designed sound is never passed off as
archival.** A train ambience under SCENE 3 is scene-setting; the listener is
told nothing about it and it claims nothing. A crowd placed under the Nehru
clip, or a "hall" placed around it, is a fabrication: it says the recording
carried a room it did not. So:

- A designed sound is never placed **within 3 s** of a real recording, and
  never under one (H-17).
- A designed sound is never introduced by narration as if recorded at the
  event ("listen to the platform at Amritsar"). The narrator never refers to
  ambience at all.
- Ambience is mixed at −32 dBFS RMS or lower under narration, always in
  stereo, always with the motif's reverb IR applied so it sits in the same
  room as the music. A real recording is mono, dry, unreverberated and 3 LU
  louder. The two treatments are different on purpose and never swapped,
  so the ear can always tell which is which.
- The episode's page credits every designed sound in the colophon under
  "Designed sound (not recordings of the event)", with its Freesound or
  archive.org row.
- **What Partition gets**: under SCENE 3 (dread), a distant rail line at
  night from a CC0 field recording; under SCENE 1 and the British account
  (procedure), paper and a room; under the OPEN, wind. Nothing under
  midnight, Gurdaspur, the counts, the drum, or any document read. The
  Freesound search used to check the pipeline ("steam train station crowd",
  CC0) returned one result, so the sourcing will be a real search per sound,
  not a shelf.

### 5d. Voice direction inside Kokoro's limits

Kokoro-82M has no emotion control, no SSML, no prosody tags. What it has:
voice choice, `speed`, and whatever pause the text's punctuation and line
breaks produce. That is enough for a documentary register if it is used on
purpose:

- **Pace per mood** is `speed`: dread 0.92, procedure 1.0, rupture 0.95,
  grief 0.90, testimony 0.93 (the document voice), reckoning 1.0. Never below
  0.88: a voice slowed further sounds ill, not grave. The On Air rule
  stands: a voice whose natural rate is wrong is not slowed, it is not cast.
- **Pause lengths** are the producer's, not the model's: `GAPS` become
  mood-keyed (§5b), and a `## REST` is placed by the writer.
- **Breath marks**: the em dash is kept in scripts as the TTS breath mark
  (the one place the dash is allowed); the pilot uses full stops and short
  sentences instead, which Kokoro renders as a firmer stop.
- **Casting per account** stays fixed per episode (`casting.py` is
  deterministic from severity and category) and the document voice does NOT
  change per speaker, for the reason `docs/HISTORY-AUDIO.md` gives: an
  accent-matched reader is a short road to caricature. The F voice reads
  women's testimony and the lament; the M voice reads the state's documents.
- **What it cannot do**: no whisper, no rising fear, no held breath before
  "life and freedom", no cracked voice for the drum. Those are written into
  the silence around the line, not into the line.
- **A $0 open model that could do more**, evaluated, not added: **Orpheus
  3B (Apache-2.0)** carries inline emotion tags and a natural pause model
  but needs a GPU-class runtime for tolerable speed; **Parler-TTS (Apache-2.0)**
  takes a text description of the delivery ("a low, slow, grave male voice")
  and runs on CPU, at roughly 4x Kokoro's cost per minute on the GitHub
  runner. Parler is the candidate for a second audition if the CEO wants
  delivery control; neither is proposed now, because the ten-wide render
  fan-out is sized for Kokoro and a 4x cost puts the catalogue at six hours.

### 5e. Mixing and mastering

- **Ducking**: the proven `apply_duck` with `dark=` (a 2.4 kHz low-passed
  copy under speech). Mood sets the duck depth: reckoning −18 dB, procedure
  −14, dread and grief −10 (the bed is already thin), rupture and testimony
  cut, not ducked.
- **Stereo image**: narrator centre; document voice panned ±7 % (the On Air
  chain), alternating so consecutive reads do not sit on one side; a real
  recording dead centre, mono, no width, so it is the one thing in the mix
  with no room around it; ambience wide; the motif at the width the era
  IR gives it.
- **Target**: −16 LUFS integrated, −1 dBTP, LRA 11, unchanged (`loudnorm_two_pass`).
- **Dynamics per mood**: the programme is normalised once, integrated; the
  moods live in the short-term loudness. Reckoning runs at about −15 LUFS
  short-term, procedure −16, dread and grief −18, testimony −17 dry, and the
  gate reads them from the master with `ebur128` per chapter and warns on a
  chapter that lands 2 LU off its mood's target.
- **Headroom for clips**: a 1947 disc transfer has a noise floor near
  −45 dBFS and a crest factor far below Kokoro's; normalised on its own to
  −19 LUFS short-term with a −3 dBTP ceiling (§4c) it never hits the
  limiter, and the limiter's release is set long (600 ms) across the clip
  span so the hiss does not breathe.

### 5f. Producer changes and effort

| change | file | effort |
|---|---|---|
| directives in the parser; H-12..H-17 with fixtures | `script_format.py`, `tests/test_history_script.py` | 1 session |
| ledger `audio` and `sound` exhibit kinds; the transcript check as a CLI (`pipeline/history/verify_clip.py`) with `faster-whisper`; a planted-defect fixture | `pipeline/history/ledger.py`, new module, tests | 1 session, plus one CI run to calibrate the threshold on the Nehru clip |
| mood-keyed gaps, duck depths and speeds; the History parameter set on `_theme_figure`; the inversion; three stings; era filters | `history_producer.py`, `generate_assets.py` | 2 sessions |
| clip turn, bed mute, own-normalisation, chapters, manifest `clips` | `history_producer.py`, `publish_audio.py`, `test_history_audio.py` | 1 session |
| the page's audio exhibit and colophon credit | `Thesis.tsx`, `Hearing.tsx`, CSS | 1 session |
| render Partition, ear test, calibrate | workflow dispatch | 1 render (about 10 min on the runner) |

About six sessions and $0. Nothing is rendered until the CEO has signed the
rights policy (§2) and, per clip, the ledger row.

### 5g. Premium, concretely

Three productions whose techniques this borrows, techniques only:

- **Radiolab (WNYC)**: the *edit-as-music* discipline. Cuts on the beat of
  speech, silence as a written element, the score entering on a word rather
  than at a segment boundary. That is the rupture rule (the motif enters on
  "freedom") and the mood-keyed rests.
- **BBC Radio 4 documentary features** (the *Archive on 4* form): the
  archival clip presented dry with a spoken credit before it, a beat of
  silence after, and the presenter never talking over it. That is §1
  entire.
- **Ken Burns**: a different voice reads the documents, attribution before
  the read, the particular before the general. Already the format's spine
  (`docs/HISTORY-AUDIO.md`); the mood map only says what plays under it.

Nothing is borrowed from any of them as material.

---

## 6. The check for designed-versus-real sound

Mechanised as H-17 (§4e), in two halves:

1. **In the timeline**, before rendering: for every clip cue, no `ambience`
   or `foley` cue may begin or end within 3,000 ms of the clip's start or
   end, and no bed may be scheduled across it. A violating script fails the
   render.
2. **In the master**, after rendering: the music bus and the ambience bus
   are rendered to files as well as mixed (they already are, for the
   arcs check), and the RMS of each within the clip span plus 400 ms either
   side must be below −60 dBFS. A fixture places a 1 s of pink noise under a
   test clip and must fail.

A third rule is editorial and cannot be mechanised, so it is stated in the
script brief instead: the narrator never describes designed sound, and a
designed sound is never given a place or a time in the narration.

---

## 7. Candidate recordings for Partition, as found and fetched

Every row below was fetched on 2026-09-25 (archive.org metadata API, the
Commons file page, the UK National Archives CDN, the archive.org advanced
search). Nothing was downloaded into the repo. Only what was actually found
is listed.

| candidate | speaker · occasion · date | archive · id · URL | licence as stated at source | duration | rights under A / B / C | transcript verifiable |
|---|---|---|---|---|---|---|
| **Tryst with Destiny** | Jawaharlal Nehru, moving the pledge, Constituent Assembly, New Delhi, 1947-08-14 (the item's date) | Internet Archive, `HindSwaraj-Speech-03-1`, https://archive.org/details/HindSwaraj-Speech-03-1 ; description "Audio Source: All India Radio"; uploaded by Public.Resource.Org (2016) | `licenseurl` CC0 1.0 (the uploader's dedication) | tryst.mp3 4:40 (VBR), tryst.ogg 280.9 s | A: fails on the URAA reading (GoI work, term to 2007 in India, restored in the US); B: admissible with CEO signature, basis printed; C: yes | **Yes**: English; the ledger holds the verbatim text (`src-cad-19470814.sec53612`); faster-whisper alignment is the check |
| Tryst with Destiny (Commons copy) | same | Wikimedia Commons, `File:Tryst_with_Destiny-_Speech_by_Pt._Jawaharlal_Nehru.ogg` | Public Domain Mark 1.0; **Source: YouTube** | 5:29, 5.01 MB | provenance fails H-13 (source is YouTube; no archive of origin named); not admitted under any policy | same text, but the copy is not admitted |
| Gandhi, Calcutta prayer meeting | Mahatma Gandhi, post-prayer speech, Calcutta, 1947-08-24 | Internet Archive, `Swaraj-Gandhi-1947-08-24`, https://archive.org/details/Swaraj-Gandhi-1947-08-24 (Public Resource "Swaraj" series, "courtesy All India Radio"; annotated from CWMG vol. 89 No. 103 p. 84) | Public Domain Mark 1.0 | prayer_speech_25.mp3 1,790 s | A: fails (URAA, as above); B: signable; C: yes | **No**: the audio is the prayer speech in Hindustani; the ledger's extract (`src-gandhi-19470824.para6`) is Harijan's third-person English report. A Hindi ASR pass and a same-language transcript would be needed first (§3). Not admitted |
| Gandhi, other 1947 prayer speeches | 1947-05-13, 06-04, 06-06, 09-13 (New Delhi), 09-23, 10-19, 10-29, 12-23, 12-26 | Internet Archive `Swaraj-Gandhi-1947-*` | Public Domain Mark 1.0 | 1,700 to 1,800 s each | as above | as above: Hindustani, and none is in the ledger |
| Mountbatten, radio broadcast | Lord Mountbatten; the file is named "mountbatten-radio-broadcast"; occasion and date **not verified** (the education page that named it now 301s to a resource whose fetched part carries no broadcast) | UK National Archives CDN, https://cdn.nationalarchives.gov.uk/documents/education/mountbatten-radio-broadcast.mp3 (HTTP 200, audio/mpeg, 8,385,096 bytes, last-modified 2021-09-15) | site-wide "Open Government Licence v3.0, except where otherwise stated"; the copyright page excludes "any material on this website which is identified as being the copyright of a third party" and a broadcast recording is BBC or AIR material | about 8 min at 128 kb/s (inferred from size, not measured) | A: fails (the recording's owner is not the Crown); B: fails unless the page names OGL for this file; C: yes | Not attempted: the occasion is unverified and the 3 June broadcast text is not in the ledger. **Candidate only**; slot recorded in the script as `status=candidate` |
| Jinnah, 11 August 1947 address | | | | | | **No recording exists**: Dawn (2017) and the Express Tribune (2013) report that Radio Pakistan holds not a second of the address and that the Delhi team's recording was never found. Not a candidate |
| Jinnah, 3 June 1947 broadcast | Jinnah, All India Radio, 1947-06-03 | recordings were handed to Pakistan by India (Express Tribune, 2013) and published on Radio Pakistan's YouTube channel (2011); **no open-licence copy found** on archive.org or Commons | none stated anywhere open | | fails A and B; C only | the text is not in the ledger |
| Jinnah, undated tapes | untitled, undated, no creator | Internet Archive `MuhammadAliJinnah_79` (uploader mughal200@yahoo.co.uk, 2012): JINAH6b, Jinah10a/b, Jinah11a/b, Jinah2A, 33 to 49 min each | Public Domain Mark 1.0 (the uploader's) | | fails H-13 provenance under every policy | no |
| Baldev Singh, 3 June 1947 broadcast | | archive.org advanced search "Baldev Singh" AND mediatype:audio: 9 hits, none of them (Radio Ceylon shows, a namesake) | | | | not found |
| Nehru, 3 June 1947 broadcast | | not found on archive.org or Commons (the Commons category "Audio files of speeches by Jawaharlal Nehru" holds one 12 s file) | | | | not found |
| Survivor oral histories | The 1947 Partition Archive (Berkeley) with Stanford Libraries: a subset streams at https://exhibits.stanford.edu/1947-partition (e.g. `gb724cq8086`, `qj120mj7364`, `wj359dn5515`) | Stanford Digital Repository | **no licence or reuse terms published** on the Archive's access page or the Stanford guide; access "free of cost for educational purposes", streaming, remote access by paid platform fee, capacity booked to 2027-01-15; the Archive says to write to collections@1947partitionarchive.org | | fails A and B (no open licence); C is the wrong instrument for a living person's testimony without permission | the story pages the ledger holds (Sarla Dutta, Khushi Muhammad Jut) are text, not audio. **Ask the Archive**: a written permission for two excerpts with credit would be the proper route, and would be recorded as the licence |

The honest yield for Partition is one admissible clip (Nehru) under policy B,
and it is the right one: it is the sentence everyone knows, in the voice that
said it, at the point in the episode where the format withholds the score.

---

## 8. The sweep: which of the 78 events could carry a real recording

By `date_sort`, against what the open archives actually hold, at $0:

| band | events | what exists openly | realistic yield under B |
|---|---|---|---|
| before 1877 (no sound recording existed) | 44 of 78 | nothing; a later oral reading is a performance, not a record | 0 |
| 1877 to 1919 | Boxer, Russo-Japanese, Armenian genocide, the Great War, 1918 flu | cylinder and disc recordings of a handful of statesmen (Library of Congress National Jukebox, PD in the US); almost nothing of the events themselves | 1 to 2 (a contemporaneous voice, rarely the event) |
| 1920 to 1945 | Russian Revolution's aftermath, Nanjing, Holocaust, Hiroshima, Bengal famine, the Second World War events | US government recordings are PD (NARA, LoC); the BBC's are not; Hirohito's broadcast is Japanese government and NHK; German material is Bundesarchiv, licensed | 4 to 6 |
| 1946 to 1990 | Partition, Nakba, Korea, Suez, Hungary, Congo, Cuba, Vietnam, Six-Day War, Cambodia, Iran, Afghanistan, Tiananmen, Chernobyl | UN Audiovisual Library (Security Council meetings, General Assembly speeches; educational non-commercial terms), NASA and NARA (PD), archive.org PD-marked government material with URAA exposure | 8 to 12 |
| 1991 onward | Srebrenica, Rwanda, Iraq 2003, and the rest | ICTY/IRMCT court audio (public record), ICTR, UN webcasts and library, national parliaments' own recordings under open terms | 10 to 14 |

**A realistic yield: 20 to 30 of the 78 events**, nearly all after 1946, one
or two clips each. The rest keep the two-voice format unchanged, which
`docs/HISTORY-AUDIO.md` §14 already found to be the thing worth keeping.
Every clip goes through §3 before it is heard, so the sweep is a research
programme per event, folded into Stage 4 of the thesis workflow, not a
batch download.

---

## 9. What was NOT done here, deliberately

- No producer code changed. The pilot script's directives are comments.
- No clip downloaded, no licence relied on, no rights row signed.
- No transcript check run: `faster-whisper` 1.2.1 is on PyPI and installs on
  the runner, but the calibration needs the Nehru clip fetched, which waits
  on the policy.
- The Gandhi recording of the very speech the ledger already cites is the
  most tempting item in the table and is not admitted, because a voice in a
  language this check cannot read is not evidence of the words on the page.
