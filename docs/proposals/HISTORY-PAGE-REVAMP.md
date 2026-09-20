# History event page: from five tabs to one hearing

Proposal, 2026-09-20. Nothing here is implemented. It answers one question the
CEO put after hearing the audio documentaries:

> "now with this documentary style audio, evaluate if our history page can also
> be given a similar journey vs just 5 perspectives. Is building custom
> timeline style viewing experience incorporating all the perspectives
> possible?"

Everything below was checked against the repo as it stands today: the 78 event
records, the 78 committed scripts, the 63 published episodes, the components
that actually mount, and the CSS that actually styles them.

---

## 1. Verdict

**Yes, the page can carry the documentary journey, and it is cheaper than it
looks, because the journey already exists as data.** Every one of the 78
events has a committed script in `data/history/scripts/<slug>.txt` that passes
the H-01 to H-11 gates: a cold open, three to seven scenes, one to six primary
documents, four to nine rests, five accounts each given its own case, a turn
that names what every account leaves out, and a close. The page has no spine
because nothing ever exported that file to it. The current page renders none
of `summary`, `significance`, `legacy_points` or the event-level primary
sources either; it renders a hero, four numbers, and five frames. The revamp is
chiefly an export plus a layout. No new writing for 78 events.

**No, a timeline cannot carry all five accounts simultaneously, and it should
not try.** Three reasons, in order of weight. First, the accounts carry no
dated moments: a perspective in the YAML is a narrative, a list of arguments, a
list of what it stresses and what it omits, and its witnesses. A five-lane
timeline would need per-account events on a time axis, and that data does not
exist; inventing it would put things in the record nobody checked. Second, and
worse, five lanes side by side is a comparison chart. The format's whole value
is sequence: each account is heard whole before anything is said against it.
Simultaneity is exactly the "bias meter" failure in a different costume.
Third, at 390px five lanes are five strips 70px tall, which nobody can read.

What a timeline CAN do, and what this proposal builds, is show the reader
where they are along ONE spine whose middle third is the five accounts as five
coloured stations, with the audio playhead moving on the same spine. The five
accounts appear together exactly once on the page: in the turn, after all five
have spoken, as a ledger rather than a chart. That is the honest version of
"a timeline incorporating all the perspectives", and it is the version that
keeps the thing the section exists for.

---

## 2. What exists, and what the current page does with it

Measured today across all 78 events and scripts.

| Data | Exists | On the page today |
|---|---|---|
| Script: OPEN, TITLE, SCENE 3-7, DOCUMENT 1-6, ASIDE 0-5, REST 4-9, PERSPECTIVE 5 of 5, TURN 2 of 2, CLOSE, SAY | 78 of 78, in the repo, validated | **Not exported. Nothing.** |
| `summary` (310-832 words), `significance`, `legacy_points` (4-8) | 78 | Not rendered (summary is used only as a fallback hook for linked events) |
| `primary_source_excerpts` (3-6 per event) | 78 | Not rendered |
| `key_figures` | 78 | Names only, joined with dots |
| Five perspectives: `narrative` (242-818 words), `key_arguments`, `emphasized`, `omitted` (3-5 each, none empty), `notable_quotes`, `sources` | 78 x 5 | One `emphasized` line, one quote, two `omitted` lines per frame; the rest behind a modal |
| `media` (0-12, median 5.5) | 76 (Kingdom of Kongo and Rise of Islam have none; 11 events have no hero image) | Frame backgrounds and a gallery |
| Audio: episode + chapters (12-16 per episode, titles only) | 63 of 78 | Listen button into the shared player |
| `connections` | 78 | Threads exit frame |

Two things about the current page matter for the design.

**The reel puts "what this side leaves out" inside each account's frame.** That
is the exact failure `docs/HISTORY-SCRIPT-BRIEF.md` describes: every account
introduced alongside its hole. The audio format fixed this by moving all
omissions into a closing turn. The page never did. The single most important
change in this proposal is moving them.

**The page is a client shell.** `history/[slug]/page.tsx` renders
`EventPageClient`, which fetches `/data/history.json` in a `useEffect`. With
JavaScript off, the served HTML says "Retrieving archival record..." and
nothing else. The weekly section was prerendered in rev 71 for this reason
(W-04 gate); the history event page needs the same treatment and this
proposal assumes it.

Of the nine components named in the brief, four are not mounted anywhere:
`KeyFacts`, `PerspectiveComparison`, `CompactTimeline`, `HistoryTimeline`
(marked DEFERRED in its own header). `OmissionsPanel` mounts only through
`PerspectiveReader` (the modal) and `PerspectiveView` (the tab-era panel,
not imported by `EventDetail`). `history.css` is 9,844 lines and still carries
the six-stage documentary CSS (lines 3124-4258) that the reel replaced, plus
the reel's own ~900 lines. Nothing asserts class parity for history the way
`tests/test_weekly.py` does for the weekly.

One more fact that shapes the audio half: `history_producer.chapters()`
emits a `kind` per chapter (`open`, `scene`, `perspective`, `turn`, `close`),
and `publish_audio.py` overwrites every one with `"segment"` because that is
the player's contract, and `tests/test_history_audio.py` asserts it. So the
published manifest knows chapter order and titles, not what a chapter is.

---

## 3. The design: "The Hearing"

The name comes from `docs/HISTORY-AUDIO.md`: "a PERSPECTIVE segment now gives
each account its own hearing". The page is one vertical column, read top to
bottom, in the order the script is spoken. No horizontal reel. No wheel
hijack. No tabs. No modal.

### 3a. The four voices, mapped

The design system has four typographic voices. The script has four kinds of
speech. They map one to one, and that mapping is the whole typographic idea:

| Script | Who is speaking | Page voice | Set as |
|---|---|---|---|
| OPEN, ASIDE, the TURN framing lines, CLOSE | the narrator addressing the reader | Editorial: Playfair Display 400 | `--text-lg` to `--text-xl`, one line per paragraph, measure 40ch |
| SCENE lines, PERSPECTIVE case lines | the narrator telling | Structural: Inter 400 | `--text-base`, 1.6, left-aligned, measure 65ch, one script line = one paragraph |
| DOCUMENT quote, a PERSPECTIVE's witness | someone else's words | Data: IBM Plex Mono 400 | the existing "typewritten citation" style of `PrimarySourceBlock` |
| Scene titles, attributions, station labels | the record's labels | Meta: Barlow Condensed 600 uppercase | `--text-xxs` / `--text-xs`, 0.06-0.16em tracking |

In the audio, a different voice reads the documents. On the page, a different
typeface does, and the attribution comes before the words in both. That is the
single rule that keeps "these are real words" legible without a label saying
so.

### 3b. Running order

```
HERO            kept as is: image, date, title, subtitle, Listen
OPEN            the misconception, Playfair, 3-4 lines, paper only, no image
SCENE 1..n      eyebrow "Scene 1 · The bungalow in Delhi", Inter lines
  DOCUMENT      inset band: attribution eyebrow, narrator's intro line, Plex Mono quote, brass left rule
  ASIDE         Playfair, indented to the document's rule
  REST          full-bleed archival image, caption and credit only, no words
FIVE ACCOUNTS   the framing lines (Playfair) + a contents list of five coloured stations
  ACCOUNT 1..5  eyebrow (type · name), h2 = the script's title, the case in Inter,
                its witness in Plex Mono with the account's colour on the rule,
                then <details> "Read the full account" (YAML narrative, arguments, sources)
  REST | short  thin paper band between accounts
THE TURN        paper-deep band: framing line, five-row ledger, closing lines
CLOSE           Playfair, ends on a particular, nothing after it but end matter
THE RECORD      By the Numbers (moved here), key figures plate, the event's
                primary sources in full, remaining gallery, Threads, next event
```

Decisions inside that order, with reasons:

**The OPEN is the first thing under the hero, and By the Numbers moves to the
end.** A stat strip before the cold open is the summary-before-the-scene the
brief bans. The numbers are reference matter. They are still on the page; they
are no longer the first thing read.

**The TITLE segment is not rendered.** It is an audio ident; the hero already
carries the title and date.

**The SAY block is not rendered.** It is for the synthesiser.

**A REST is an image.** The script's held silence becomes a full-bleed band
(60vh desktop, 45vh at 390px) holding one item from `media`, with only its
caption and credit, under `--img-grade-history`. The reader looks instead of
reads, which is what a rest is for. Media is assigned to rests in order; what
is left over goes to the gallery in the end matter. Rests beyond the media
count, and the two events with no media, render as a bare `--hist-paper-deep`
band, 30vh, hairline above and below. That is a quieter rest, not a broken one.

**Documents in the spine take the brass rule; a witness inside an account
takes that account's colour.** A Radcliffe letter in Scene 1 belongs to no
side. Attlee's "I gave them their freedom" inside the British account belongs
to the British account. The rule colour says which without a label.

**Each account is a full section, and nothing is said against it inside its
own section.** Eyebrow in the account's colour: `victor · British Imperial`
(the YAML `viewpoint_type` and `viewpoint`). The h2 is the script's own title
for the account ("The British account is administrative" is a line; the title
is "British Imperial"). Then the four to six case lines. Then its witness,
if the script gives it one. Then a native `<details>` whose summary reads
"Read the full account": the YAML `narrative`, `key_arguments`, and `sources`,
inline, in the reading column. Not a modal: a modal fails without JavaScript
and traps the reader outside the spine. The `omitted` list does not appear
here. Ever.

**The TURN is the payload, and it is built so it cannot be skipped.** A
full-width `--hist-paper-deep` band with a hairline top and bottom, the
eyebrow "The turn" in brass, the script's framing line in Playfair, then five
rows. Each row: the account's colour chip, its name, and the script's one line
for it in Inter. Under each row a `<details>` labelled "From the record" holds
the YAML `omitted` bullets (three to five, hollow bullets, the existing
`OmissionsPanel` visual language). Then the script's closing turn lines in
Playfair ("The holes are not random. Each account omits the thing that would
cost its own side the most."). This band is the only place the five names sit
together on the page, it comes after all five have spoken, its rail station is
drawn in brass rather than any account's colour, and it is never collapsed or
lazy-loaded.

**The CLOSE ends the reading.** Playfair, the last line given `--space-7`
above it. What follows is visually subordinate: smaller type, a section label
"The record", ruled rows.

**`significance` and `legacy_points` are not rendered.** They are the moral
the format refuses ("Established the India-Pakistan rivalry: four wars,
nuclear standoff"). The CLOSE was written from `legacy_points` and does the
same job as a particular instead of a claim. I would refuse to add them back.

### 3c. The rail

Replaces `ReelScrubber`. It is the timeline the CEO asked for, redirected: it
plots the reader's position, not the accounts.

**Desktop (1024px and up).** The page uses the named-line grid the weekly
introduced (`full` / `rail` / `text`). The rail track on the left holds a
`position: sticky` vertical index: a 1.5px ink line with stations. Open and
Close are ink ticks; scenes are small ticks with the scene number in Plex Mono;
the five accounts are five dots in `--hist-persp-a` to `--hist-persp-e`; the
turn is a brass diamond. A fill in ink rises with scroll progress. The station
nearest the viewport centre carries `aria-current="true"` and its label
(Barlow, `--text-xxs`) is shown; other labels show on hover or focus. Each
station is an `<a href="#…">`, so the rail is a working contents list with
JavaScript off; the fill and the current marker are the enhancement.

**Mobile (below 1024px).** The rail becomes a 3px strip fixed directly under
the sticky topbar (`--hist-topbar-height: 56px`), segmented in the same
colours in the same proportions as the page, plus a one-line readout of the
current station in Barlow at `--text-xxs`, 24px tall in total. Tapping the
readout opens a bottom sheet listing the stations (the design system's mobile
bottom-sheet pattern). With JavaScript off, the same `<nav>` renders inline
once, under the hero, as a plain list.

Progress comes from an `IntersectionObserver` on the sections, not a scroll
listener; the parallax code in `EventDetail` goes with the reel.

### 3d. The audio edition: companion on the same spine, never the driver

The episode's chapter list and the page's station list are the same sequence
by construction: `chapters()` emits one chapter per OPEN, SCENE, TURN,
PERSPECTIVE and CLOSE segment, in script order, and skips ASIDE, DOCUMENT and
TITLE. The Partition sidecar has 15 chapters; the page has 15 stations. So:

1. **Listen from here.** Every station with a matching chapter carries a small
   play glyph in its eyebrow row (44px target, `aria-label="Listen from
   Scene 3"`). It calls `playHistory()` if this event is not loaded, then
   `seekTo(chapter.startTime)`. Both exist on `useAudio()` today. The glyph is
   a client island; without JavaScript it does not render, and the hero's
   Listen button is already a button.
2. **The playhead on the rail.** When `contentType === "history"`,
   `brief.id === event.id` and `isPlaying`, a brass tick moves along the rail
   at `currentChapterIndex`. Two cursors on one spine: where you are reading
   and where the audio is. No "now playing" label; the moving tick is the
   label.
3. **Follow the audio.** An opt-in toggle in the rail. When on, the page
   scrolls to each station as its chapter begins (`scrollIntoView`, smooth, or
   instant under reduced motion). Off by default, and nothing else ever moves
   the page on the reader's behalf. The reel's desktop wheel hijack, with its
   engaged-region and upward-intent release logic, is deleted.

What this is not: a transcript viewer with a moving highlight. The manifest
carries segment times, not line times. The producer's `Timeline` has more than
one cue per segment (`chapters()` dedups on `seg_idx`), so line marks are
probably emittable later, but that is a different feature and this proposal
does not need it.

The 15 events without an episode get the whole page minus the three items
above, and the hero keeps its existing "Audio edition in production" line.

### 3e. Numbers

The scripts spell numbers for the synthesiser: "nineteen forty seven",
"fourteen to fifteen million". In print those read as a transcript. The export
converts them under two constraints: a strict grammar (four-digit years in the
"nineteen forty seven" and "two thousand and eight" forms, cardinals with
thousand / million / billion, "forty four BCE"), and a grounding gate in the
spirit of H-01: **an emitted numeral must appear as that digit string somewhere
in the event's own YAML**, or the words stay. Ordinals ("the fifteenth of
August") stay as words; they read fine. A wrong number on a history page is
worse than a spelled one, and the gate is what makes the converter safe.

### 3f. Motion

Within the design system's rules: transform and opacity only, tokens not
literals, everything to 0ms under reduced motion.

- Sections reveal with the existing `.hist-reveal` pattern (opacity 0 to 1,
  translateY 12px to 0, `--dur-normal`, `--ease-cinematic`). The `<noscript>`
  override in `history/layout.tsx` already forces them visible.
- Rest images get no Ken Burns. A rest is still.
- The rail fill and the playhead tick transition with `--dur-fast`.
- The turn band does not animate in. It is there when you reach it.

### 3g. Layout sketch

```
Desktop 1440                          Mobile 390
┌──────────────────────────────┐     ┌───────────────┐
│ HERO (full bleed, kept)      │     │ HERO          │
├───┬──────────────────┬───────┤     ├───────────────┤
│ r │  OPEN  Playfair  │       │     │ ▬▬▬▬▬▬▬▬▬▬▬▬▬ │ ← 3px strip + readout
│ a │                  │       │     │ OPEN          │
│ i │  Scene 1 · ...   │       │     │               │
│ l │  Inter lines     │       │     │ SCENE 1 · ... │
│ · │ ┃ Radcliffe ·1947│       │     │ ┃ Radcliffe   │
│ · │ ┃ mono quote     │       │     │ ┃ mono quote  │
│ ● │                  │       │     ├───────────────┤
│ ● │██ REST: image ███│██████ │     │███ REST ██████│ 45vh
│ ● │                  │       │     ├───────────────┤
│ ● │  Five accounts   │       │     │ FIVE ACCOUNTS │
│ ● │▌ victor · British│       │     │▌British       │
│ ◆ │▌ h2, case, witness       │     │▌case, witness │
│ · │▌ ▸ Read the full account │     │▌▸ Read the …  │
│   │  ...x5           │       │     │ …x5           │
│   │▒▒ THE TURN ▒▒▒▒▒▒▒▒▒▒▒▒▒│     │▒▒ THE TURN ▒▒▒│
│   │  CLOSE           │       │     │ CLOSE         │
│   │  the record ...  │       │     │ the record …  │
└───┴──────────────────┴───────┘     └───────────────┘
```

The text column is measure-bound (65ch, 576px as the weekly measured it).
Rests break to `full`. The rail sits in `rail`. At 390px the gutters are 16px
and nothing scrolls horizontally.

---

## 4. Alternatives considered and rejected

**A. Five parallel lanes on a time axis (the literal ask).** Rejected for the
three reasons in the verdict: no per-account dated data, simultaneity destroys
sequence, unreadable at phone width. Its honest descendant is the rail in 3c.

**B. Keep the reel, add the scenes as frames in front of it.** Rejected. A
frame is one viewport, so an account is capped at one `emphasized` line, one
quote and two omissions, with the rest behind a modal; a six-line case plus a
witness does not fit at 390px. The omissions-in-frame problem stays. And the
horizontal snap needed ~60 lines of wheel-hijack logic just to let the page
scroll normally, which is a sign the pattern was fighting the medium.

**C. Audio-driven page: the audio is primary, the page is its scrolling
transcript.** Rejected. Fifteen events have no episode; a page that needs
audio to make sense fails with JavaScript off, fails on a train, and fails the
reader who reads faster than 145 words a minute. Line timings are not in the
manifest. The companion model in 3d gets most of the value at none of the
cost.

**D. Pairwise split-screen with vocabulary diffing** (`PerspectiveComparison`
exists, unmounted). Rejected. Reducing two accounts to their ten most frequent
non-shared six-letter words is a bias meter with extra steps.

**E. Tabs, the original "Rotating Lectern".** Rejected; it is the CEO's
premise.

**F. Render the script verbatim, numbers as words.** Rejected in favour of
3e. Considered as the fallback if the converter's residue proves large.

---

## 5. What it costs

### Data and pipeline (new, all derivable, no authoring)

1. **Script export.** `pipeline/history/export_scripts.py` parses each script
   with the existing `script_format.parse_script` and writes
   `frontend/build-data/history-scripts/<slug>.json`. Build-data, not
   `public/data`: the server component reads it at build and the HTML carries
   it, so the browser never fetches it and `history.json` (which the landing
   loads whole) does not grow by 78 x ~12 KB. Shape:

   ```json
   { "slug": "partition-of-india",
     "segments": [
       { "kind": "OPEN", "lines": [{ "voice": "N", "text": "…" }] },
       { "kind": "SCENE", "title": "The bungalow in Delhi", "lines": [] },
       { "kind": "DOCUMENT", "author": "Sir Cyril Radcliffe", "work": "…", "date": "1947", "lines": [] },
       { "kind": "REST", "short": false, "mediaIndex": 0 },
       { "kind": "PERSPECTIVE", "title": "British Imperial", "perspectiveIndex": 0, "lines": [] },
       { "kind": "TURN", "title": "The shape of the disagreement", "rows": [{ "perspectiveIndex": 0, "text": "…" }] }
     ],
     "stations": [{ "segment": 0, "chapter": 0 }, …] }
   ```

2. **Account resolution.** Script account titles are script-authored
   ("Subaltern and displacement") and differ from YAML names ("Subaltern /
   Displacement"). Using H-09's own six-character stem rule, all 390 script
   accounts resolve to at least one YAML account, and 76 resolve to more than
   one (Apartheid's three "Movement" accounts, Caesar's two "The …" accounts,
   and so on). The exporter takes the best stem overlap and, on a tie, script
   order; a test asserts every event resolves to a permutation of 0..4 and the
   export fails otherwise. Expect a handful of title touch-ups on first run.

3. **Chapter resolution.** For a published episode, station i and chapter i
   correspond by position, verified by title equality against the manifest.
   On any mismatch (a script re-edited after render) the export drops the
   `chapter` field for that event, so the page never seeks to the wrong place;
   `episode_report.py` should list such events as needing a re-render.
   Cleaner long term: `publish_audio.py` keeps the producer's kind in a new
   `segment` field alongside `kind: "segment"` (so the player contract and
   the test at `tests/test_history_audio.py:126` are untouched). The 63
   published sidecars carry no kind today, so that field arrives on
   re-publish; position-plus-title does not wait for it.

4. **The turn's rows.** The closing TURN has one line per account (H-06
   guarantees the segment; the brief guarantees the shape). The exporter maps
   each line to an account by the same stem rule and falls back to rendering
   the lines unmapped, in order, when a line names none.

5. **Numbers converter and its grounding gate**, per 3e, with a test that
   runs it over all 78 scripts and prints the residue.

### Frontend

**Prerender.** `history/[slug]/page.tsx` becomes a server component. It reads
the event row from the emitted snapshot (extend `lib/historyCatalog.ts`, which
already reads `public/data/history.json` at build, to return the full row) and
the script JSON, and renders the hearing as server markup with three small
client islands: the rail, the listen-from-here glyphs, and the reveal
observer. `EventPageClient`'s fetch path is retired for event pages; the
landing keeps its own loader.

| Component | Fate |
|---|---|
| Hero block inside `EventDetail` | reused as is |
| "By the Numbers" derivation (~200 lines of stat parsing in `EventDetail`) | reused, moved to `history/stats.ts`, rendered in the end matter |
| `MediaGallery`, `Lightbox` | reused for the leftover media |
| `PrimarySourceBlock` | reused; becomes `DocumentBlock` with the attribution-first eyebrow and the rule colour prop |
| `OmissionsPanel` | reused, `omitted` list only, inside the turn's details |
| Threads exit block, `HOOKS`, `CTAS` | reused |
| `PerspectiveFrame` | replaced by `AccountSection` |
| `ReelScrubber` | replaced by `SpineRail` |
| `PerspectiveReader` (modal) | replaced by an inline `<details>` |
| New | `Hearing` (server: segments to sections), `RestBand`, `TurnLedger`, `SpineRail`, `ListenFromHere` |
| Delete | `KeyFacts`, `PerspectiveComparison`, `CompactTimeline`, `HistoryTimeline`, `PerspectiveSelector`, `PerspectiveView` (none mounted from the event page), the reel CSS (`history.css` ~8957-9843), the six-stage CSS (~3124-4258) |

**CSS.** Port the weekly's class-parity test (`tests/test_weekly.py`, both
directions) to `history.css` before deleting anything, then delete what it
reports orphaned. The file is 255 KB; a good fraction of it styles markup that
no longer exists, and the test is what makes that claim safe to act on.

**Gates.** `scripts/verify_production.py` has no History check today. Add:
the served `/history/<slug>` HTML carries the OPEN's first line, all five
YAML viewpoint names, and a heading for the turn (the proof it is not a client
shell); no em or en dash in the served text; and, for events with an episode,
one listen-from-here target per chapter. A build test asserts all 78 exports
parse with five accounts and two turns.

**Effort.** Export, resolvers and gates: one session. Page markup and CSS:
two to three sessions. Rail and audio islands: one. Deletion with the parity
test: one. QA at 390 and 1440, light and dark, JS off, reduced motion: one.
Roughly seven agent sessions.

### Data that does not exist

- The script export (derivable). The segment kind on published chapters
  (derivable at publish; optional). Nothing that needs a writer.
- Rest imagery for the two events with no media and hero imagery for the
  eleven without one: editorial sourcing already tracked elsewhere, and the
  design degrades to bare bands rather than waiting on it.

---

## 6. What could go wrong

**Accessibility.** Heading order is h1 (hero), h2 for Open, each scene, "Five
accounts", each account, "The turn", Close; h3 inside details. The rail is
`<nav aria-label="Where you are in the record">` with `aria-current` on the
nearest station. Documents are `<blockquote>` with `<cite>`, attribution
before the quote in DOM order as well as visually. Rest images take their
caption as alt; a bare rest band is `aria-hidden`. Colour is never the only
carrier: every chip sits beside a name. No live region for the playhead tick
(it would announce every chapter); the player already does that. Listen
glyphs are 44px targets with text labels for screen readers.

**Mobile.** 56px topbar plus a 24px rail strip is 80px of chrome; the strip
should hide until the hero has scrolled off. At 390px, document bands drop
their inset and keep the left rule; rests are 45vh; details summaries are
full-width rows. The page is long: roughly 1,800 words of spine plus five
collapsed accounts plus end matter, eight to ten screens. That length is the
point, and the rail exists because of it.

**JavaScript off.** Handled by prerendering: the spine, the accounts, the
turn, the details and the inline rail list are all server markup. Listen
affordances do not render. The layout's `<noscript>` rule already unhides
`.hist-reveal`. This must be a gate, not a hope: the verify check in §5 is
the assertion.

**Reduced motion.** Reveals are instant (the global rule sets every duration
to 0ms), the rail fill jumps, "Follow the audio" scrolls instantly, rests are
still images regardless.

**Long against short.** Scenes run 3 to 7, documents 1 to 6, rests 4 to 9,
words 1,472 (Chernobyl) to 1,997 (the Holocaust). Fall of Rome, Civil Rights
and Apartheid have one document each, so their typeface change happens once;
that is the script's shape and the page should not fake a second. Rests
beyond the media count go bare. Page length varies by about a third across
the catalogue, which is fine.

**The 78-event consistency problem.** The page's shape is dictated by the
script grammar that H-05, H-06 and H-09 already enforce, so every page has an
open, three or more scenes, a document, five accounts, a turn and a close
without anyone checking 78 pages by hand. What is not enforced by anything
today is the script-title to YAML-name mapping and the script-to-chapter
alignment; §5 puts both behind export gates so a mismatch fails the build
instead of shipping a mis-seek or a mislabelled account. Thirty-nine scripts
predate H-11 (per `docs/HISTORY-AUDIO.md`); the page prints their hedges
exactly as the audio speaks them, so nothing extra is needed there.

**The numbers converter.** The failure is a wrong numeral. The grounding gate
prevents it by construction; the cost is a residue of spelled numbers where
the YAML has no matching digits. If that residue is large on the first run,
fall back to option F and revisit.

**Two cursors on one rail.** A reading marker and a playhead could confuse.
The playhead tick renders only while this event is loaded and playing, in
brass, and the reading marker is ink; they are never the same glyph.

**Script edits after render.** The audio and the page would drift. The
title-equality check drops the listen-from-here affordances for that event
rather than seeking wrong, and the register should flag it for re-render.

---

## 7. What I would refuse to build

- Five accounts as lanes, columns, a slider, a wheel, or any layout that puts
  them on screen at once before each has been read whole.
- Any "how far apart are they" meter, overlap score, or word-diff between
  accounts.
- The omitted list inside an account's own section.
- A blended narrative that averages the five into one.
- `significance` and `legacy_points` as rendered bullets.
- Scroll that moves without the reader asking it to.
