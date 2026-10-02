# Handoff: Partition cinematic voice audition (local RTX 4090)

Paste everything below the line into a Claude Code CLI session opened at the
root of a fresh `git pull` of `aacrit/void--news` on the laptop.

---

You are on the CEO's laptop (RTX 4090, CUDA). Task: a **local audition** of two
open, $0 TTS models for the History episode "The Partition of India", to decide
whether either is clearly more cinematic and human than our production voice
(Kokoro-82M). This is a pilot. **Nothing is published, committed or pushed**
unless the CEO says so after listening.

## Read first

- `CLAUDE.md` (Rule 1: zero factual error outranks everything).
- `docs/HISTORY-AUDIO.md` and `docs/proposals/HISTORY-AUDIO-ARCHIVAL.md` §5
  (moods, voice direction, mixing; §5d already names Orpheus as the GPU option).
- `pipeline/history/script_format.py` (`parse_script`): the only parser of the
  script format. Use it; do not write a second parser.
- `pipeline/history/history_producer.py` and `casting.py`: how Kokoro renders
  today (voices, speeds, rests, stings, ducking, `loudnorm_two_pass`, defined in `pipeline/briefing/radio_producer.py`, to -16 LUFS).

## Input

`data/history/scripts/partition-of-india.txt` from **origin/main** (re-cut
2026-09-25 against the evidence ledger, later edits since). `N:` lines are the
narrator, `M:` lines the document voice (verbatim ledger extracts: never edit
them). `#` lines are inert comments; `# MOOD:` gives the delivery for the
segment; `## REST` is a pause. Em dashes stay: they are TTS breath marks.

**Audition passage: `## OPEN` through the end of `## SCENE 2`** (about 3
minutes: the dread opening, the procedural Attlee/Radcliffe scene, and the
Nehru midnight scene). Do not change one word of the text.

## The two models

1. **Chatterbox** (Resemble AI, MIT). `pip install chatterbox-tts`. Use its
   `exaggeration` and `cfg_weight` controls for delivery (start: narrator
   exaggeration 0.35, cfg 0.4 for grave and slow; documents 0.25, cfg 0.5).
   Use the model's built-in default voice, or a reference clip that is clearly
   licensed for this use. **Never clone a real person's voice** (no
   Nehru, no Attlee, no broadcaster).
2. **Orpheus 3B** (`canopylabs/orpheus-3b-0.1-ft`, Apache-2.0, built on
   Llama 3.2 so Meta's Llama licence also applies; the HF repo may require
   accepting the licence first). Built-in voices only (e.g. `leo` or `dan`
   narrator, `tara` or `leah` for the document voice). Emotion tags such as
   `<sigh>` are allowed **only** where the script's MOOD supports it and never
   inside an `M:` line: a document is read, not performed.

Set each model up in its own venv (`.venv-audition-chatterbox`,
`.venv-audition-orpheus`) with CUDA PyTorch matching the installed driver. If
on Windows, prefer WSL2. Pin the exact package versions you used in the output
README. If a model produces noise or garbage, suspect a torch / transformers
version mismatch before judging the model (Parler Large did exactly this on a
mismatched CPU install in the cloud session).

## Build

One script, `scripts/audition_tts.py --model {chatterbox,orpheus,kokoro}
--from OPEN --to "SCENE 2"`, that:

- parses with `parse_script`, renders sentence by sentence (long single
  generations drift), keeps the producer's rests and the narrator/document
  voice split, fixes a seed per voice so the narrator stays one person;
- **at the Nehru `# CLIP:` slot (`status=signed`): renders the DOCUMENT read
  below it as today**, or uses the real clip if the producer already fetches
  it; either way no music under a real voice and no synthetic imitation of him;
- masters every output identically: dry voice only (no bed, no stings) so the
  comparison is the voice, then `loudnorm` two-pass to -16 LUFS, -1 dBTP;
- writes `out/audition/partition-<model>.mp3` plus `out/audition/README.md`
  with model, version, voice, settings, render time and real-time factor.
  `out/` must be gitignored; add it to `.gitignore` if it is not.

Render **kokoro** too through the same script so all three are mastered alike.

## Check before handing to the CEO

- Transcribe each MP3 locally (faster-whisper on the GPU) and diff against the
  script text: any dropped, added or garbled word, wrong number ("nineteen
  forty seven") or wrong name (Radcliffe, Attlee, Abell, Sutlej, Beas) is a
  defect. Report the diff per model; a model that changes a word fails Rule 1
  regardless of how it sounds.
- Listen-check list for the CEO: does the narrator stay one person across
  lines, does the document voice sound distinct, are pauses natural, do any
  lines rush.

## Deliver

Tell the CEO where the three MP3s are, the transcript diff per model, render
speed, and your recommendation. Then STOP and wait. If the CEO picks a model,
the follow-up (separate, on a `claude/*` branch) is: the full episode with the
production mix, `tests/test_history_audio.py` and H-12..H-17 passing, staged
beside the live episode, never replacing it without sign-off.
