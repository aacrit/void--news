# History scripts under Orpheus and the Ken Burns register: does the algorithm need to change?

Status: PROPOSAL, 2026-10-03. Review and one variant script only. No code, no live
script and no ledger row changed. The variant is
`data/history/scripts/variants/partition-of-india.cinematic.txt`; nothing globs
that directory (every consumer reads `data/history/scripts/*.txt` flat:
`pipeline/history/export_scripts.py:149`, `pipeline/history/publish_audio.py:202`,
`pipeline/history/quote_ledger.py:179`, `tests/test_history_script.py:390`,
`tests/test_history_clips.py:449`, `tests/test_history_export_parity.py:104`), so
it is reviewable without being live.

The question the CEO asked: today's TTS audition chose Orpheus 3B, voice `tara`,
for the narrator, with male Orpheus voices as the reader of record and a female
reader for `F:` lines, and named the style target as a Ken Burns documentary.
Does the way a History script is produced need to change for that?

**Short answer: the structure does not; the pace model, four gates and one dormant
hazard do.** The format is already Ken Burns shaped (a second voice reads the
documents, attribution before every read, a late TURN, a close on a particular).
What is Kokoro shaped is everything that turns words into minutes: the rate
table, the mood speeds, the overhead fit, the respellings. And the gates have
three gaps a Ken Burns cut walks straight into: nothing checks sentence length,
nothing ties a read to the extract its own segment cites, and the per-segment
runtime charge makes documents and rests, the two things this register has more
of, the most expensive thing on the page.

---

## 1. What the "algorithm" actually is

There are two things in the tree that could be called the script algorithm, and
only one of them produced the live script.

**The live path is hand authoring under a brief and gates.** `docs/HISTORY-AUDIO.md`
219-230 ("Why the scripts are not generated") and `docs/HISTORY-SCRIPT-BRIEF.md`
are the method; `pipeline/history/script_format.py` is the contract (`parse_script`
209-247; `validate_script` 314-561; H-18 at 597-655); `pipeline/history/clips.py`
is the clip contract (H-12..H-17); `pipeline/history/check_script.py` is the
runner. The Partition script's history is six commits: the format and gate
(`578600bd`), a case per side and H-09 (`60954e12`), sex-matched readers
(`4263ed68`), REST as a segment (`72111e88`), the ledger re-cut and the archival
proposal (`128a6640`), and the CEO signing the Nehru clip (`52eef066`). Every
step was a writer reading sources and a gate catching a class of error after it
had happened once.

**The dormant path is `pipeline/history/audio_script_generator.py`.** It is the
old Gemini two-host generator: `A:`/`B:` turns, 500 to 950 words
(`calculate_word_target`, 464-500), 35 words a turn, JSON out. The parser cannot
read a line of it (`parse_script` keeps `N:`/`M:`/`F:` only, 244-246), and its
cache writes to the SAME path as the live scripts:
`_SCRIPTS_DIR = .../data/history/scripts` and `_save_cached_script` writes
`<slug>.txt` (604-619). One call to `generate_history_audio_script(...)` for a
slug that has a hand-authored script would overwrite it with dialogue the
renderer cannot parse. Nothing calls it today. It should not be able to do that
tomorrow either (change 5.1 below).

So "does the algorithm need to change" is really "does the brief and do the
gates need to change", and the rest of this review is about them.

---

## 2. Findings, by the questions asked

### 2a. Structure: OPEN / TITLE / SCENE / DOCUMENT / ASIDE / REST / PERSPECTIVE / TURN / CLOSE

Keep it. The format already does the three things a Ken Burns film does
mechanically: a different voice reads the record (`script_format.py` 30-38,
`docs/HISTORY-AUDIO.md` 76-78), the narrator names the source before the read
(H-04, 390-420), and the argument is withheld to a late TURN (H-06, 379-380).
`QUOTING = ("DOCUMENT", "PERSPECTIVE", "ASIDE")` (49) already permits a document
read anywhere a documentary wants one, including as a coda after the final TURN.

Two findings about how the shape is USED, not about the shape:

- **The budget punishes the register.** H-07 prices every segment at 5.3 s of
  silence (`SEGMENT_MINUTES = 0.0883`, 107) on top of its words, anchored at the
  catalogue mean of 24.5 segments (108). A Ken Burns cut has more documents and
  more rests than the catalogue mean; the variant has 11 reads and 7 rests in 41
  segments, so it pays 2.56 min of overhead and its word ceiling at the cast
  rate falls to about 1,800. That was the binding constraint on this cut: I
  wrote the Viceroy's "astounded" line as a twelfth DOCUMENT closing the TURN,
  and the budget made me narrate it instead (variant line 208). The fit is
  correct for what it measured (49 Kokoro renders with the current GAPS); it is
  the wrong price for a register that spends on silence by design. See 3.1.
- **One motif line, used three times, costs nothing and the brief does not ask
  for it.** The variant's "One census, any map, and five weeks." closes the OPEN
  (22), the first scene (51) and the CLOSE (217). Nothing in the brief names the
  device, and nothing should gate it; it belongs in the brief as a sentence of
  craft (3.6).

### 2b. Word budget against Orpheus's measured rate

Every rate in the system is a Kokoro voice. `NARRATOR_WPM` is keyed by Kokoro
ids (`script_format.py` 78-83); `estimated_minutes` looks the voice up through
`history.casting.cast` (269-275), whose tables are Kokoro ids too
(`pipeline/history/casting.py` 42-49, 52-69); the brief's table (`HISTORY-SCRIPT-BRIEF.md`
183-188) prints `bm_lewis 148`, which the code has since corrected to 146
(`NARRATOR_WPM["bm_lewis"] = 146.0`), so the brief is already a word out of date.

The audition's one measurement of Orpheus (`out/audition/README.md`, the
`orpheus` and `orpheus-seed100` runs) is 335 words in 125.0 and 125.4 s of
speech across three voices (`leo`/`dan`/`tara`), which is **160.8 wpm**, against
Kokoro's 125.0 s for the same passage at the mood speeds. For Partition that
means the same script is 14.89 min at the cast rate and 13.81 at 160: Orpheus
has a minute of headroom the gate does not see. The risk runs the other way
too: a script written to Orpheus's ceiling (about 1,990 words at 41 segments)
would render over the 15.5 publish gate if Kokoro ever reads it, and Kokoro is
still first in the engine list (`history_producer.py:776`,
`engines = [KokoroEngine(voices=vmap), EdgeTtsEngine()]`).

Two cautions on the number. It is one passage, three voices mixed, and `tara`
was not the narrator in that run (the `voice-tara` run is 71 words). And the
`voice-*` runs show `tara` synthesising at **RTF 4.42** against `leo` at about
2.0 on an RTX 4090 (README, voice-tara vs voice-leo): a 14 minute episode is
roughly an hour of GPU synthesis in `tara`, and the render workflow runs on CPU
GitHub runners sized for Kokoro (`docs/HISTORY-AUDIO.md` 332-349). The rate
belongs in the code only once it has been measured on a full `tara` narration,
and the render path has to be decided before the catalogue is re-cut.

### 2c. Sentence length

There is no rule. The brief says "One idea per line. The line is the unit of
synthesis" (`HISTORY-SCRIPT-BRIEF.md` 176), which was true for Kokoro and is
not true for Orpheus: the audition synthesises by SENTENCE (`scripts/audition_tts.py`
163, `split_sentences`) and silently rides any sentence under four words onto its
neighbour (`MIN_UNIT_WORDS = 4`, line 64), because "short generation is where
autoregressive TTS hallucinates" (166). The live script has "Gurdaspur." (1
word), "Over years." (2), "Five weeks." (2) and a 70 word TURN line. Under Orpheus
the one-word beat the writer placed is either joined to the next sentence by the
renderer, which changes the prosody the writer wrote, or synthesised alone and
degraded. Neither is what the page says. The variant has no sentence under 4
words and one over 45 (Jinnah's 46 word sentence, which is verbatim and cannot
be split). The rule should exist and the writer should obey it on the page (3.2).

### 2d. How documents are framed and attributed

Working as designed, with two edges.

- The attribution line is the one line a signed clip changes (`HISTORY-AUDIO-ARCHIVAL.md`
  §4b 275-278; `52eef066` did exactly that), and H-15 (`clips.py` 73, 225-232)
  enforces its two words. Fine. But **H-10 reads only the event YAML** (`haystack
  = _norm(_event_text(event))`, `script_format.py` 508), while the credit's
  provenance lives in the ledger (`recordings:` row `origin_as_stated: "Audio
  Source: All India Radio ..."`, `ledger.yaml` 1756). So the honest credit warns
  on `'Radio'` forever, on the live script and on the variant, and the brief's
  own words apply: "a recurring false positive is worse than a missing rule,
  because it teaches the writer to wave H-10 through" (836-838). H-18 already
  widened its record to the thesis and the extracts (`_thesis_record_text`,
  626-638); H-10 should read the same record plus the recordings rows (3.3).
- **A candidate clip is ten warnings a run.** The live script carries
  `clip-mountbatten-broadcast-19470603 status=candidate` and `clips.evaluate`
  emits two H-12, four H-13, three H-14 and one H-15 finding for it on every
  check (confirmed on the live script this session). The design intended
  candidates to render honestly as the document read (`clips.py` 28-31), which
  they do, but the noise is the same false-positive hazard. The variant does not
  carry the slot (3.4).

Two things I would NOT change: `_credit_ok`'s requirement of the speaker's name
plus "recording"/"broadcast" is right, and the proposal's spoken-credit rule (§1,
43-46) is the Ken Burns convention exactly.

### 2e. Rests and pauses as directives

`## REST` and `## REST | short` exist (`script_format.py` 42-46; lengths from
`GAPS["rest"]`/`["rest_short"]` 7500/4500 ms, `history_producer.py` 74-75, or
from the mood, `mood.py` 50-58, read at `history_producer.py` 813-828). The
proposal's own mood table asked for "the longest rest in the episode" after the
force scene (`HISTORY-AUDIO-ARCHIVAL.md` 371) and there is no way to write that:
the writer has two lengths and the mood picks between 2.0 and 4.5 s. Under
Orpheus, which has no speed control, silence is the only pace instrument left,
and the writer should have a third stop (3.5). The variant uses 7 rests, as the
live does; the brief's "four to seven" (204-206) stands.

### 2f. Pronunciation

`## SAY` respellings were tuned for Kokoro (`HISTORY-SCRIPT-BRIEF.md` 202-203).
The audition ran with respellings on for every model and whisper still heard
`abel`, `biyaz`/`beyes`/`biars` and `sutledge`, so the audition cannot say
whether the respellings helped Orpheus, hurt it or did nothing; names were
counted as "confirm by ear", not defects. What the audition DID establish as
systematic (two seeds, same word) is a misread of a common word, "to the Commons"
as "to the comments", and a dropped possessive in "the Punjab commission's
secretaries". Those are writing problems, not respelling problems, and the
variant rephrases both ("reading the statement to Parliament", "the secretaries
of the Punjab commission") and the one-seed "contesting" -> "contested" ("The
dispute is not finished"). The remaining rare names in a verbatim read (Sutlej,
Beas) cannot be rewritten; the variant keeps their `SAY` entries and adds
`Attlee` and `Abell`. The catalogue needs an engine-keyed lexicon and a lint fed
from the audition's own `check.json` defects, which already exist on disk (3.7).

### 2g. Rule 1 traceability

What exists: H-01 (every quote in the YAML's excerpts or notable quotes, 0.6 word
overlap, 422-428), H-04 (the speaker named, 390-420), H-09 (every side heard,
473-491), H-10 (names, advisory, 493-531), H-11 (hedged records said aloud,
429-471), H-18 (every spoken number in YAML + thesis + extracts, blocking,
597-655), and the quote ledger (`quote_ledger.py:65-70`, words in order in SOME
extract). That is a serious apparatus and it caught real things this session:
my first draft said "It does not mention Kashmir" of the award, and the thesis
(`data/history/theses/partition-of-india.md` 203) is more careful, because the
schedule names Kashmir as where the Ujh enters; the variant now says "Its reasons
do not mention Kashmir" (90).

Three gaps:

- **No gate ties a read to its own `# extract:`.** The quote ledger asks whether
  the words appear in ANY extract of the event; the directive above the read is a
  comment nobody checks. A read could cite the wrong extract id, or an extract id
  that does not exist, and pass. I checked the variant by hand (every `M:`/`F:`
  line is a verbatim substring of the extract its segment names; the Pritam line
  matches its `.en` rendering once the rendering's verse line break is folded to
  a space). That check should be a gate (3.3).
- **Narrator claims trace to nothing but names and numbers.** The thesis cites
  every sentence (`[^src-x locator]`); the script cites none. The writer's
  discipline is the only control, and the brief says so honestly ("That part is
  on you", 164-165). A parser-inert `# claims:` directive per segment, checked
  only for resolving to stored extracts, would let a reviewer trace the ASIDE
  that says "eight days before the award was signed" to `src-top-xii.item335` and
  the thesis line that computes it, without putting footnotes in the ear (3.3).
- **Two sources that disagree have no home.** The YAML says the award was
  published on 17 August (`partition-of-india.yaml` 23) and the Mahbub and Saba
  extract agrees; the ledger's own gap note records that the Transfer of Power
  introduction says "not published till 16 August" (`ledger.yaml` 1297-1299).
  The task's rule ("say so aloud rather than pick one") is the right one and the
  variant does neither, saying only "until after independence" (68), which both
  support. But the disagreement is not in `contested:`, so the thesis page does
  not print it and the next writer will not know it is there.

### 2h. Which gates conflict with a Ken Burns rhythm

In order of how hard they bit this cut:

1. **H-07's segment charge** (2a): documents and rests are the register, and
   each costs 5.3 s before a word is spoken. It forced one document back into
   narration.
2. **The silent sentence join** in the renderer (2c): the writer's one-word beat
   is not what renders.
3. **H-10's YAML-only haystack** (2d): the signed clip's honest credit warns on
   every run.
4. **Candidate clip noise** (2d): ten warnings for a slot that is behaving
   correctly.
5. **No emotion-tag check.** Policy is zero tags; the audition records
   `emotion_tags: "none (verbatim audition)"` as a SETTING (`audition_tts.py`
   285). Nothing fails a `<sigh>` in an `N:` line. A tag in a script would be a
   policy breach no gate can see.

Gates that do NOT conflict and should not move: H-01, H-02, H-04, H-05, H-06,
H-09, H-11, H-18, H-12..H-17. The "numbers as words" rule (brief 174) is fine:
document lines keep their digits ("7500", "0.8", "200,000") and the renderer
normalises them (`briefing.spoken_text.normalize_for_speech`, imported at
`audition_tts.py` 41).

---

## 3. Proposed changes

Ordered by the five I would make first; the rest follow.

### 3.1 Make the pace model engine-aware (brief + `script_format.py` + `mood.py`)

- `NARRATOR_WPM` becomes keyed by `engine:voice` (`"kokoro:bm_lewis": 146.0`,
  `"orpheus:tara": <measured>`), and `estimated_minutes` takes the engine the
  episode will render with. The episode's engine is pinned (a field in the
  render manifest, or a `# ENGINE:` directive added to `DIRECTIVE_KEYS`,
  `script_format.py` 137-138) so H-07 measures the voice that will read it.
  Until a full `tara` narration has been timed, `orpheus:tara` is absent and the
  gate falls back to the catalogue average, which is what `estimated_minutes`
  already does for an unknown voice (269-277).
- H-07 measures against the SLOWEST engine in the fallback chain when the
  chain is live (`history_producer.py:776`), or the chain is removed and the
  engine is the pinned one. A script must not pass at 160 and fail at 146.
- Re-fit `SEGMENT_MINUTES`/`SEGMENT_REFERENCE` (107-108) after the first
  Orpheus render, as the comment at 99-106 says was done for Kokoro. The
  comment should record the engine the fit belongs to.
- `mood.py`: `narrator_speed`/`document_speed` are Kokoro `speed` (docstring
  10-12, floor 28). Under an engine with no speed control they are no-ops, so a
  mood's slowness has to live in its silences. Add two fields per mood for such
  engines: `max_sentence_words` (dread 18, grief 18, testimony 22, procedure 28,
  reckoning 24, rupture 16) read by the advisory in 3.2, and a `pause_scale`
  applied to `line_ms`/`to_document_ms`/`from_document_ms` so dread and grief
  breathe longer where Kokoro would have slowed the voice.
- Fix the brief's rate table (183-188: `bm_lewis 148` vs code 146) and add the
  Orpheus row once measured.

### 3.2 Two new gates on the sentence: H-19 length, H-21 no tags

- **H-19** (advisory for Kokoro, blocking when the pinned engine is Orpheus):
  every sentence in a spoken line is 4 to 45 words. A 1 to 3 word sentence fails
  with "join it or lengthen it: the synthesiser cannot hold a fragment"; over 45
  warns, except inside an `M:`/`F:` line, where the sentence is verbatim and the
  finding names the extract instead. Sentence splitting must treat initials and
  abbreviations as non-terminal ("G. D. Khosla"); my own audit split that name
  into three sentences before I fixed the splitter, and the audition's
  `split_sentences` should be checked for the same.
- Retire the renderer's silent join (`MIN_UNIT_WORDS` ride, `audition_tts.py`
  64, 163-166) once H-19 is blocking: the page should say what renders.
- **H-21** (blocking, every engine): no `<[a-z_]+>` token in any spoken line.
  Zero-tag policy becomes a gate rather than a setting.

### 3.3 Close the traceability gaps: H-20 extract binding, wider H-10, `# claims:`

- **H-20** (blocking): every DOCUMENT/PERSPECTIVE/ASIDE segment with an
  `M:`/`F:` line carries a `# extract:` directive; the ref resolves
  (`ledger.extract(src, loc)`, or `ledger.renderings[of]` when the ref ends in
  `.en`); and each read is a whitespace-folded substring of that text. This is
  the check I ran by hand and it is the one that makes "every read is verbatim
  from its named extract" true by construction rather than by review. It is
  stricter than the quote ledger (which accepts any extract) and should sit
  beside it, not replace it.
- **H-10** reads `_event_text(event) + _thesis_record_text(slug)` plus the
  `recordings:` rows' `repository`, `origin_as_stated` and `speaker` (loaded
  through `pipeline.history.ledger.load_ledger`, which `clips.py` already
  imports the types of). The permanent `'Radio'` warning on a signed, honest
  credit disappears without touching the YAML.
- **`# claims:`** joins `DIRECTIVE_KEYS` as a comment directive listing
  `<src>.<locator>` refs for the narration in its segment. One advisory gate:
  each ref resolves to a stored extract. No spoken effect. It gives the
  reviewer the thesis's citation discipline on the script without footnotes in
  the ear, and gives a future writer the trail I had to rebuild from the ledger
  this session.
- Add a `contested:` row for the award's publication date (16 vs 17 August,
  2g) so the disagreement is printed, not remembered.

### 3.4 Candidates out of the script

Either `clips.evaluate` collapses an unsigned row with `status=candidate` to ONE
advisory finding ("candidate; not admitted; the document read renders"), or a
candidate lives only in the ledger (`recordings:` row with a `wanted_at:
"SCENE 1"` field) and the `# CLIP:` directive is written into the script only
when the CEO signs, which is already the moment the credit line must change
(§4b). The variant takes the second path and carries no candidate.

### 3.5 A third rest, and rests priced as what they are

`## REST | long` at 1.5x the mood's `rest_ms`, so the writer can place "the
longest rest in the episode" the proposal asked for (`HISTORY-AUDIO-ARCHIVAL.md`
371) without inventing a mood. And H-07 should price a REST at its actual
mood-resolved length (the producer already resolves it, `history_producer.py`
818-828) instead of the fitted 5.3 s average, so a writer who adds silence pays
for the silence and not for a phantom segment.

### 3.6 Brief changes (no code)

Add to `docs/HISTORY-SCRIPT-BRIEF.md`:

- "Write sentences, not lines. Four to forty five words each, full stop on every
  one. Never a one, two or three word sentence: fold it into its neighbour."
- "One recurring line, two or three times, a full sentence of six words or more.
  Introduce it as an enigma in the OPEN, land it in the scene that explains it,
  close on it."
- "Possessives before a sibilant and 'to the Commons' misread on Orpheus. Say
  'of the commission', 'to Parliament' or 'to the House of Commons'."
- "A document read in another voice is worth more than a sentence of narration
  about it. If the budget forces a choice, cut narration first." (This cut did
  the opposite once, under H-07, and the review says so.)
- "Numbers you refuse to say are not said. 'The figure of seventy five thousand
  could not be read, so it is not repeated here' repeats it." The live script
  does this twice (lines 92 and 165); the variant says "Larger figures exist, in
  books this programme could not read, so they are not said here" (112) and
  "The books that carry a count could not be read here, so none is given" (189).
- Correct the rate table (3.1) and replace `bm_lewis 148` with 146.
- Replace "The line is the unit of synthesis" (176) with the sentence rule.

### 3.7 Pronunciation: an engine-keyed lexicon and a misread lint

- A catalogue lexicon `data/history/pronounce/<engine>.yaml` mapping a name to
  its respelling per engine, merged under a script's own `## SAY`, so seventy
  eight scripts stop carrying divergent respellings of "Nehru" and a Kokoro
  respelling is never fed to Orpheus untested.
- An A/B audition, `SAY` on against off, for Orpheus on the five names the
  audition flagged (Abell, Beas, Sutlej, Radcliffe, Jawaharlal), before any
  Orpheus respelling is written down as a rule.
- **H-22** (advisory): a per-engine list of strings the audition has shown to
  misread on two seeds, fed from `out/audition/*/check.json` `defects` (today:
  `"to the Commons"`, a possessive `'s` before `s`), warned on in any `N:` line.
  The data is already produced; it only needs a reader.

### 3.8 Casting for Orpheus

`casting.py` has no Orpheus table. `_DOCUMENTS_FOR` (42-49) enforces one rule
worth keeping: narrator and document voice must not be confusable. With `tara`
narrating, the male reader contrasts by construction; the `F:` reader does not,
and `F:` lines are the most intimate reads in this episode (Sarla Dutta, the
lament). The audition tested `leo`/`dan`/`tara` as N/M/F and `jess`, `leah`,
`mia`, `dan`, `leo`, `tara` as narrators; it has not yet put a female reader
beside `tara` as narrator. That audition should run before the F voice is
chosen, and `casting.py` gains an engine-keyed table when it has.

### 3.9 The dormant generator

`audio_script_generator.py` should either be deleted or have `_SCRIPTS_DIR`
moved out from under the live scripts and its `_save_cached_script` refuse to
overwrite a file that parses as a History script. Its system prompt is also the
only place in the tree that still says "past tense throughout" and "never
present tense" (130-136), which contradicts the format's Ken Burns present
tense (`docs/HISTORY-AUDIO.md` 70) and would confuse anyone who reads it as the
house rule.

---

## 4. What the variant does differently, and what promotion would require

The variant is 1,800 words in 41 segments: 14.89 min at the cast rate (the live
script is 1,801 words, 41 segments, 14.89), 13.81 min at 160 wpm. Shape: 6
scenes, 11 documents (live 10), 7 asides, 7 rests, 2 turns, 5 perspectives. Gate
output on the final run is in the session report; it is zero fails, one warn
(H-10 `'Radio'`, the same finding the live script carries, explained in 2d), the
Nehru clip admitted at 28.05 s, and the clip gates otherwise clean.

Differences that matter:

- Every narrator sentence is 4 to 45 words; the three Orpheus misreads are
  phrased around; one motif line three times; `Attlee` and `Abell` added to
  `SAY`.
- Gurdaspur is told through two Mountbatten documents a month apart, the public
  press conference of 4 June (`src-mountbatten-press-19470604.p99-100`, a read
  the live script narrates) and the private Bhopal record of 4 August. The
  judges' two counts compress to one sentence.
- The Hindustani speech moves from the SCENE 2 scene-setter into the ASIDE after
  the recording, where it is the night's own evidence of the fires.
- "How many" gains the fact-finding body's own footnote: evidence from 2,094 of
  West Punjab's 19,914 villages (`src-khosla-1949.p298`, thesis 169).
- Four narrator claims the live script makes are tightened for Rule 1: "It does
  not mention Kashmir" becomes "Its reasons do not mention Kashmir" (the schedule
  names Kashmir); "by his own arithmetic" for the 1,600 ratio is dropped (the
  ratio is the thesis's analysis, `an-rifles-per-head`, not Jenkins's); "Sixteen
  recovered in a month" becomes "between the first and the twenty fifth"; the
  Indian account's reason for accepting partition follows the YAML
  (ungovernability, not delay).
- The Mountbatten candidate clip slot is not carried (2d, 3.4).
- The 75,000 and the "one to two million" are not spoken even in refusal, which
  removes the live script's known H-18 warning (`'2e+06'`).

Promotion to the live path is not a file move. It needs: the H18_KNOWN entry
`'partition-of-india': {'2e+06': ...}` removed (`script_format.py` 760-762),
because `tests/test_history_script.py` fails when a listed number stops firing
(588-589); the thesis's `episode_marks` re-pointed (`partition-of-india.md`
153-156 pins chapters 5 and 14, and the segment order has changed); a re-render,
because `publish_audio.py` records `script_sha256` and the audio test compares
it (`docs/HISTORY-AUDIO.md` 406-414); and the Nehru row's `signed_basis` reads
"credited as a recording, with no claim about where it was recorded", which the
variant's credit honours (63).

## 5. What I did not do

No code was changed, so nothing in sections 3.1 to 3.9 is implemented. The
Orpheus rate is one passage's measurement and is not written into any table.
The variant was not rendered; the audition harness is the way to hear it
(`scripts/audition_tts.py --model orpheus` reads the live path, so a `--script`
argument or a temporary copy would be needed). The 16 versus 17 August
disagreement is noted, not adjudicated, because the sources that carry it are
a volume introduction held under a Crown-copyright cap and a literary journal's
aside, and settling it is the thesis's job, not a script's.
