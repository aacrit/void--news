# void --onair Musical Elements System

**Status:** SPECIFICATION -- awaiting CEO approval before implementation
**Date:** 2026-03-28
**Author:** audio-engineer
**Scope:** 5 new/modified musical elements + placement strategy + assembly pipeline changes

---

## 0. Executive Summary

The current broadcast sounds like speech with bookends. The ident opens, the outro closes, but the middle is a continuous stream of unbroken TTS dialogue. The listener has no sonic map of where they are in the broadcast.

This spec introduces five musical elements that create a broadcast architecture: a sense of arrival, orientation, progression through stories, a deliberate editorial shift, and a closing punctuation. Every element draws from the existing D major 9th palette. Every element is built from sine wave primitives. Total new audio: approximately 9.5 seconds of musical material distributed across a 5-6 minute broadcast.

### Current State

```
IDENT (2.0s) --crossfade--> NEWS DIALOGUE --350ms--> NEWS_TO_OPINION (1.3s)
  --200ms--> OPINION MONOLOGUE --350ms--> OUTRO (1.8s)

Background bed: tiled 10s loop, -34 to -42 dB, overlaid across full broadcast.
Section breaks: silence detection at -45 dB. Result: 0 breaks placed.
Headline sting: asset exists (0.4s). Result: never used in assembly pipeline.
```

### Proposed State

```
IDENT (2.0s) --crossfade--> HEADLINES with HEADLINE_BED underneath
  --> HEADLINE_STING (0.4s) --150ms--> STORY 1
  --> SECTION_BREAK (0.9s) --> STORY 2
  --> SECTION_BREAK (0.9s) --> STORY 3
  --> CLOSE --350ms--> NEWS_TO_OPINION (2.5s)
  --200ms--> OPINION MONOLOGUE --> OPINION_KICKER (0.6s)
  --150ms--> OUTRO (1.8s)

Background bed: same as current (subharmonic, tiled).
Headline bed: separate, higher-energy bed. Headlines only.
```

---

## 1. Opening Musical Element: The Underscore

### Purpose
A soft, forward-moving musical phrase that plays UNDER the opening headlines. The headlines are the first ~8% of the news script (3 sentences, ~50-80 words). The underscore gives the opening energy and momentum -- "the stories are arriving" -- then fades away as deep coverage begins.

This is NOT a separate asset that plays before or after speech. It is a bed that runs simultaneously with the first portion of the TTS audio, then dissolves.

### Harmonic Content
Three layers built from the D major 9th palette, but with rhythmic character the background bed lacks:

| Layer | Frequency | Gain | Character |
|-------|-----------|------|-----------|
| Rhythmic root pulse | D3 (147 Hz), bell envelope, 200ms duration, repeating every 800ms | -20 dB per hit | Heartbeat. Forward momentum. 75 BPM equivalent. |
| Shimmer swell | A3 (220 Hz) + A3+1.5 Hz shimmer pair, pad envelope | -22 dB | Harmonic warmth that breathes. Slow swell in, sustain, slow swell out. |
| Color accent | E4 (330 Hz), bell envelope, single hit at 60% mark | -26 dB | The ninth -- the "news" interval. One chime near the end of the underscore, as if the chord is waking up. |

### Duration
Variable. Computed at assembly time based on word count estimation of the headlines section (see Section 6: Placement Strategy). Expected range: 12-20 seconds.

### Gain Curve
- Fade in: 800ms (begins with the first word of speech)
- Sustain: full duration minus fade-in and fade-out
- Fade out: 2000ms (dissolves gradually so the listener doesn't notice it leaving)
- Master gain: -16 dB (louder than the background bed at -30 dB combined, but still well under speech at -6 to -12 dBFS). The W3C/BBC standard is 20-26 dB below speech. At -16 dB against speech at -8 dB average, the underscore sits 8 dB below speech -- tighter than the background bed but appropriate because it is rhythmic (the ear separates rhythmic content from speech more easily than sustained tones).

### Asset Strategy
This is NOT a pre-generated .wav file. It is assembled programmatically at broadcast assembly time because its duration must match the estimated headlines length. The generation function (`_generate_headline_underscore(duration_ms)`) lives in `generate_assets.py` but is called from `audio_producer.py` during assembly.

### Design Rationale
The Daily's piano figure works because it creates anticipation -- something is about to be explained. The underscore serves the same function: rhythmic momentum says "pay attention, the stories are coming." The fade-out says "now we're going deep." The root pulse at 147 Hz sits below the speech band (200-4000 Hz), so it adds energy without masking words.

---

## 2. Section Breaks Between Stories

### Purpose
Short musical moments inserted between Story 1 and Story 2, and between Story 2 and Story 3. They create breathing room and signal "next topic" to the listener.

### Asset
The existing `section_break.wav` (0.9s glass-bell chime) is sonically correct. No changes needed to the asset itself.

### The Problem: Placement
The current silence detection approach (`_detect_silence_gaps` at -45 dB threshold, minimum 800ms) finds zero gaps in Gemini TTS output. This is because Gemini 2.5 Flash TTS produces continuous speech with no long pauses between topics -- it models natural dialogue rhythm, which means speaker turns overlap or follow with minimal gaps (~100-300ms).

Lowering the threshold is not the solution. At -35 dB, you detect breath pauses within stories, not boundaries between them. At -25 dB, you detect everything. The problem is that story boundaries in natural dialogue have no acoustic signature.

### Solution: Word-Count Proportional Placement

The script structure is deterministic. The system prompt specifies:

```
Headlines: ~5-8% of script (3 sentences)
Story 1:   ~30% of script (deepest coverage)
Story 2:   ~25% of script
Story 3:   ~20% of script
Close:     ~5% of script
```

Since we know the total word count of the news dialogue and the TTS output duration, we can estimate millisecond positions for story boundaries:

```
total_words = len(dialogue.split())
total_ms = len(news_audio_segment)

# Cumulative percentage at each boundary:
headlines_end = 0.08          # End of headlines / start of Story 1
story1_end    = 0.08 + 0.30 = 0.38   # End of Story 1
story2_end    = 0.38 + 0.25 = 0.63   # End of Story 2
story3_end    = 0.63 + 0.20 = 0.83   # End of Story 3 / start of Close

# Millisecond positions for section breaks:
break_1_ms = int(total_ms * 0.38)    # Between Story 1 and Story 2
break_2_ms = int(total_ms * 0.63)    # Between Story 2 and Story 3
```

### Snap-to-Quiet Refinement
The raw proportional position is an estimate. The actual story boundary will be near that position but may not align exactly. To avoid placing the chime on top of speech:

1. Define a search window: +/- 3 seconds around the estimated position.
2. Within that window, find the quietest 200ms segment (lowest RMS energy).
3. Place the section break centered on that quiet point.

This is not silence detection (which failed). This is targeted quiet-point detection within a known region. The search window is narrow enough that the quietest point will reliably be a speaker transition or sentence boundary.

### Implementation

```python
def _snap_to_quiet(audio, target_ms, window_ms=3000, grain_ms=200):
    """Find the quietest grain_ms chunk within +/- window_ms of target_ms."""
    start = max(0, target_ms - window_ms)
    end = min(len(audio), target_ms + window_ms)

    best_pos = target_ms
    best_rms = float('inf')

    pos = start
    while pos + grain_ms <= end:
        chunk = audio[pos : pos + grain_ms]
        if chunk.rms < best_rms:
            best_rms = chunk.rms
            best_pos = pos + grain_ms // 2
        pos += grain_ms // 2  # 50% overlap for precision

    return best_pos
```

### Overlay Behavior
The section break is overlaid (not spliced) at the snap point. The asset is already very quiet (-16 to -28 dB individual tones, -10 dB master). It sits under any residual speech. The 0.9s duration means even if speech continues through the break, the chime reads as a sonic comma -- present but not competing.

### Minimum Spacing Guard
Enforce at least 30 seconds between section breaks. If break_2 is within 30s of break_1, skip break_2. This prevents double-chiming on short scripts.

---

## 3. News-to-Opinion Transition: The Full Page Turn

### Current State
`news_to_opinion.wav` is 1.3 seconds. It works but feels rushed -- like a paragraph break when the broadcast needs a chapter break. The shift from two-voice reporting to single-voice editorial is the most important structural moment in the broadcast.

### Proposed Redesign: 2.5 seconds

The new asset has three phases:

**Phase 1 -- The Resolve (0-800ms)**
The news section closes. A low D3 pad swells and holds -- the same root gravity that anchors the intro bloom. The fifth (A3) arrives as a bell, short decay. The feeling is "settling."

| Tone | Frequency | Type | Duration | Gain | Entry |
|------|-----------|------|----------|------|-------|
| Root | D3 (147 Hz) | pad | 800ms | -8 dB | t=0 |
| Root detune | D3+0.8 Hz | pad | 700ms | -16 dB | t=50ms |
| Fifth | A3 (220 Hz) | bell | 400ms | -14 dB | t=200ms |
| Sub-bass | D2 (73.4 Hz) | pad | 600ms | -20 dB | t=100ms |

**Phase 2 -- The Breath (800-1600ms)**
Silence. Actual silence. 800ms of nothing. This is the most important part. The listener's ear resets. The contrast between the dense harmonic content of Phase 1 and the silence of Phase 2 creates the "page turn" -- the brain registers that something structural changed.

| Content | Duration |
|---------|----------|
| Silence | 800ms |

**Phase 3 -- The Arrival (1600-2500ms)**
The opinion voice's territory. A single F#4 bell (the warmth note, the major third) rings out alone -- one clear tone. Then the ninth (E4) ghosts in underneath. This is a compressed, stripped-down version of the intro bloom, but starting from the middle of the chord rather than the root. It signals "new voice incoming" without repeating the intro.

| Tone | Frequency | Type | Duration | Gain | Entry |
|------|-----------|------|----------|------|-------|
| Third | F#4 (370 Hz) | bell | 500ms | -12 dB | t=1600ms |
| Ninth | E4 (330 Hz) | pad | 400ms | -18 dB | t=1700ms |
| High shimmer | A4 (440 Hz) + 441.5 Hz | shimmer_pair | 350ms | -22 dB | t=1750ms |

**Master shaping:**
- Fade in: 60ms (Phase 1 attack)
- No fade between phases (silence IS the transition)
- Fade out: 400ms (Phase 3 decay)
- Master gain: -4 dB

### Assembly Change
In `audio_producer.py`, replace:
```python
combined += AudioSegment.silent(duration=350)
# ... transition ...
combined += AudioSegment.silent(duration=200)
```
with:
```python
combined += AudioSegment.silent(duration=200)  # brief breath before transition
combined += transition  # 2.5s page turn (includes its own internal silence)
combined += AudioSegment.silent(duration=100)  # minimal gap, Phase 3 handles the arrival
```

Total gap: was 350+1300+200 = 1850ms. Proposed: 200+2500+100 = 2800ms. Net increase: ~1 second. Worth it for the structural clarity.

---

## 4. Headlines Background Score (The Underscore -- Assembly Details)

This section specifies how the underscore from Section 1 integrates with the assembly pipeline in `audio_producer.py`.

### Triggering
The underscore is generated and overlaid only when the news TTS audio exists. It plays from the start of the news dialogue (after the ident crossfade) through the estimated end of the headlines section.

### Duration Calculation

```python
# In audio_producer.py, after TTS synthesis:
total_words = len(dialogue.split())
total_ms = len(news_seg)

# Headlines are ~8% of the script
headlines_end_ms = int(total_ms * 0.08)

# Minimum 10s, maximum 25s -- guard against extreme scripts
headlines_end_ms = max(10000, min(25000, headlines_end_ms))
```

### Overlay Position
The underscore starts at the same position as the news dialogue in the final assembly. If the ident crossfade places the news start at, say, 1800ms into the final audio, the underscore starts at 1800ms.

### Interaction with Background Bed
Both the background bed and the headline underscore play during the headlines section. The background bed is at -30 dB combined; the underscore is at -16 dB. They occupy different frequency ranges:
- Background bed: 73.4 Hz, 147 Hz, 220 Hz (all subharmonic, felt not heard)
- Underscore pulse: 147 Hz (shared with bed, but bell envelope vs. pad -- perceptually distinct)
- Underscore shimmer: 220 Hz (shared frequency, but the underscore is 20 dB louder)
- Underscore accent: 330 Hz (above the bed entirely)

The bed provides the floor; the underscore provides the energy. No conflict at these levels.

### Generation Function Signature

```python
def generate_headline_underscore(duration_ms: int) -> AudioSegment:
    """Generate a rhythmic underscore bed for the headlines section.

    Args:
        duration_ms: Target duration, typically 12-20 seconds.

    Returns:
        AudioSegment at SAMPLE_RATE (24000 Hz), with fade-in and fade-out applied.
    """
```

This function lives in `generate_assets.py` but is NOT called during the static asset generation pass. It is imported and called from `audio_producer.py` during assembly, because its duration is dynamic.

---

## 5. Opinion Kicker: The Landing

### Purpose
A short musical punctuation that plays at the very end of the opinion monologue, after the editorial voice delivers its final unresolved question and says "void opinion." The kicker is the period at the end of the editorial -- a chord that lands with weight.

### Design
A compressed version of the outro's resolving motion, but faster and heavier. Where the outro breathes and settles over 1.8s, the kicker drops and lands in 0.6s. Think: the last chord of a piano piece, played forte then allowed to ring.

### Harmonic Content

| Tone | Frequency | Type | Duration | Gain | Entry |
|------|-----------|------|----------|------|-------|
| Root | D3 (147 Hz) | bell, fast attack | 500ms | -6 dB | t=0 |
| Fifth | A3 (220 Hz) | bell | 450ms | -10 dB | t=10ms |
| Third | F#4 (370 Hz) | bell | 400ms | -10 dB | t=10ms |
| Ninth | E4 (330 Hz) | bell | 350ms | -14 dB | t=20ms |
| Sub-bass | D2 (73.4 Hz) | pad | 400ms | -18 dB | t=0 |

All tones arrive nearly simultaneously (within 20ms) -- a chord stab, not a bloom. The root is louder than in the headline sting (-6 vs. -14 dB), giving it more gravity. The sub-bass provides physical weight.

### Shaping
- Fade in: 5ms (instant attack -- this is a strike)
- Fade out: 350ms (ring and decay, not abrupt)
- Master gain: -4 dB (more present than section breaks, comparable to the ident)

### Duration: 0.6 seconds

### Asset: `opinion_kicker.wav`

### Assembly Position
After the opinion monologue audio, with a 100ms gap:

```python
# Current:
combined += opinion_seg
combined += AudioSegment.silent(duration=350)
# Proposed:
combined += opinion_seg
combined += AudioSegment.silent(duration=100)
combined += opinion_kicker   # 0.6s
combined += AudioSegment.silent(duration=200)
```

Total gap before outro: was 350ms silence. Proposed: 100ms + 600ms kicker + 200ms = 900ms. The kicker replaces silence with intentional sound, so perceived pace is similar.

---

## 6. Placement Strategy: Word-Count Proportional Positioning

### The Core Problem
Gemini 2.5 Flash TTS produces continuous natural dialogue. There are no reliable acoustic markers at story boundaries -- no long pauses, no tonal shifts, no silence gaps exceeding 800ms. The current `_detect_silence_gaps` function at -45 dB threshold found 0 gaps in the latest broadcast.

### The Solution
Use the known script structure (deterministic percentages from the system prompt) to estimate boundary positions in the TTS audio, then snap each estimate to the nearest quiet point for clean placement.

### Script Structure (from system prompt)

| Section | Word % | Cumulative % |
|---------|--------|-------------|
| Headlines | 8% | 8% |
| Story 1 | 30% | 38% |
| Story 2 | 25% | 63% |
| Story 3 | 20% | 83% |
| Close | 5% | 88% |
| (padding/transitions) | 12% | 100% |

These percentages are approximate. The system prompt specifies them as targets, and Gemini adheres closely (within +/- 5 percentage points based on listening tests).

### Assumption: Linear Word-to-Time Mapping
TTS output is approximately linear: if a script is 900 words and the TTS output is 270 seconds (4.5 minutes), then each word takes ~300ms on average. This is not perfectly linear -- dialogue exchanges are faster than monologue exposition -- but over 30% of a script (a full story segment), the error averages out to within +/- 3 seconds. The snap-to-quiet refinement absorbs this error.

### Placement Algorithm

```
Input:
  news_audio: AudioSegment (TTS output for news dialogue)
  dialogue: str (the full dialogue text sent to TTS)

Step 1: Compute proportional positions
  total_words = word_count(dialogue)
  total_ms = duration_ms(news_audio)

  headlines_end_ms   = total_ms * 0.08
  story1_end_ms      = total_ms * 0.38
  story2_end_ms      = total_ms * 0.63

Step 2: Snap to quiet points
  For each boundary position:
    Search +/- 3000ms window
    Find quietest 200ms chunk (lowest RMS)
    Use that chunk's midpoint as the actual placement position

Step 3: Enforce minimum spacing
  If any two adjacent placements are < 30000ms apart, drop the later one.

Step 4: Place elements
  - At headlines_end: overlay headline_sting.wav (0.4s)
  - At story1_end: overlay section_break.wav (0.9s)
  - At story2_end: overlay section_break.wav (0.9s)
```

### Why This Works Better Than Silence Detection
Silence detection is a bottom-up approach: scan the audio and hope the structure reveals itself. Word-count placement is top-down: use known structure to place elements approximately, then refine acoustically. The top-down approach works because:

1. We control the script structure via the system prompt.
2. Word-to-time mapping is approximately linear for TTS.
3. The snap-to-quiet step handles the "approximately" part.
4. Even if placement is off by 2-3 seconds, overlaying a -26 dB chime during speech is barely perceptible -- it reads as texture, not interruption.

### Fallback
If the dialogue word count is suspiciously low (<200 words) or the audio is suspiciously short (<60s), skip proportional placement entirely and fall back to silence detection with relaxed thresholds (-35 dB, 500ms gaps). Better to place nothing than to place incorrectly.

---

## 7. Headline Sting: Activation

### Current State
`headline_sting.wav` exists (0.4s chord stab) but is never loaded or used in `audio_producer.py`. It was generated but never wired into the assembly pipeline.

### Proposed Use
Place the headline sting at the estimated end of the headlines section, marking the transition from "here's what's coming" to "let's go deep on Story 1." It acts as a sonic full stop after the opening rundown.

### Overlay Behavior
Overlaid on the news audio at the snap-to-quiet position near `total_ms * 0.08`. The sting is already quiet (-6 dB master, individual tones -12 to -18 dB). At 0.4s, it is shorter than a single word -- it slips into a breath pause.

### No Asset Changes Needed
The existing `headline_sting.wav` is correctly designed for this purpose. The documentation in `generate_assets.py` already describes it as "punctuation after headlines." It simply needs to be wired into the assembly pipeline.

---

## 8. Summary of File Changes Required

### `generate_assets.py` -- 3 changes

1. **New function: `generate_headline_underscore(duration_ms)`**
   - Dynamically generates the rhythmic headlines bed
   - Uses D3 bell pulses at 800ms intervals + A3 shimmer + E4 accent
   - Returns AudioSegment (not written to disk -- called at assembly time)
   - Exposed as a module-level function for import by audio_producer.py

2. **Modified function: `generate_news_to_opinion()`**
   - Duration: 1300ms --> 2500ms
   - Three-phase structure: Resolve (800ms) + Silence (800ms) + Arrival (900ms)
   - New harmonic content for Phase 3 (F#4 bell + E4 pad + A4 shimmer)
   - Canvas size change, new overlay positions, same master gain

3. **New function: `generate_opinion_kicker()`**
   - New 0.6s asset: `opinion_kicker.wav`
   - D major 9th chord stab with heavy root emphasis
   - Bell envelopes, simultaneous attack, fast decay
   - Added to `if __name__ == "__main__"` block

### `audio_producer.py` -- 5 changes

1. **New import: `generate_headline_underscore` from generate_assets**

2. **New function: `_place_proportional_elements(news_audio, dialogue)`**
   - Computes proportional positions for headlines_end, story1_end, story2_end
   - Calls `_snap_to_quiet()` for each position
   - Overlays headline_sting + 2x section_break at computed positions
   - Replaces `_overlay_section_breaks()` call in the assembly pipeline

3. **New function: `_snap_to_quiet(audio, target_ms, window_ms, grain_ms)`**
   - Finds quietest chunk near a target position
   - Returns refined millisecond position

4. **Modified assembly section (Step 4)**
   - After news TTS: call `_place_proportional_elements()` instead of `_overlay_section_breaks()`
   - After ident crossfade: generate and overlay headline underscore
   - Load and place `opinion_kicker.wav` after opinion monologue
   - Use new gap timings for news-to-opinion transition

5. **Headline underscore overlay logic**
   - Compute headlines duration from word count
   - Call `generate_headline_underscore(headlines_duration_ms)`
   - Overlay at the start of the news dialogue in the final assembly

### `daily_brief_generator.py` -- 0 changes

No prompt changes needed. The current script structure (Headlines > Story 1 > Story 2 > Story 3 > Close) already produces the proportional distribution this spec relies on. The system prompt already specifies "3 stories in depth" and "crisp rundown of the 3 stories coming up" -- the structure is deterministic enough for proportional placement.

One optional enhancement (deferred, not in this spec): add a `[STORY_BREAK]` token to the system prompt that Gemini would insert between stories. This would give a text-level marker that could be matched against the TTS output for more precise placement. However, the current approach (proportional + snap-to-quiet) should work well enough without this, and adding markers risks changing the dialogue's natural flow.

---

## 9. New Asset Inventory

| Asset | Duration | Status | Generated |
|-------|----------|--------|-----------|
| `ident.wav` | 2.0s | Unchanged | Static |
| `transition.wav` | 1.5s | Unchanged (legacy) | Static |
| `section_break.wav` | 0.9s | Unchanged | Static |
| `news_to_opinion.wav` | 2.5s | **Redesigned** (was 1.3s) | Static |
| `headline_sting.wav` | 0.4s | Unchanged (now wired) | Static |
| `outro.wav` | 1.8s | Unchanged | Static |
| `background_bed.wav` | 10.0s | Unchanged | Static |
| `opinion_kicker.wav` | 0.6s | **New** | Static |
| (headline underscore) | 12-25s | **New** | Dynamic (per-broadcast) |

---

## 10. Full Assembly Timeline (Typical 5-minute broadcast)

```
TIME    ELEMENT                     NOTES
─────── ─────────────────────────── ──────────────────────────────
0.0s    IDENT (bloom)               2.0s, D major 9th ascending
1.8s    ├─ crossfade zone ──┐       200ms ident tail + news start
2.0s    NEWS BEGINS                 Headlines (A: rundown)
2.0s    ├─ headline underscore      ~15s rhythmic bed, fading out
2.0s    ├─ background bed           Full broadcast, subharmonic
~17s    HEADLINE STING              0.4s chord stab (snapped to quiet)
~17s    STORY 1 BEGINS              Deepest coverage (~75s)
~92s    SECTION BREAK               0.9s glass bell (snapped to quiet)
~92s    STORY 2 BEGINS              Second story (~60s)
~152s   SECTION BREAK               0.9s glass bell (snapped to quiet)
~152s   STORY 3 BEGINS              Third story (~50s)
~202s   CLOSE                       Final observation + "This was Void news."
~215s   ──200ms silence──
~215s   NEWS-TO-OPINION             2.5s (resolve + breath + arrival)
~218s   ──100ms silence──
~218s   OPINION BEGINS              Monologue: "Now... void opinion."
~338s   OPINION ENDS                "void opinion."
~338s   ──100ms silence──
~339s   OPINION KICKER              0.6s chord landing
~339s   ──200ms silence──
~340s   OUTRO (resolve)             1.8s, chord descending to root D
~342s   END
```

Total broadcast: approximately 5 minutes 42 seconds (342s), compared to current ~5 minutes 30 seconds. Net increase: ~12 seconds, entirely from the expanded news-to-opinion transition (+1.2s) and the opinion kicker (+0.6s offset by reduced silence gaps).

---

## 11. Gain Structure Reference

All levels relative to 0 dBFS. Speech from Gemini TTS arrives at approximately -6 to -12 dBFS.

| Element | Individual Tone Range | Master Gain | Combined Level (est.) | Below Speech |
|---------|-----------------------|-------------|----------------------|-------------|
| Ident | -8 to -18 dB | -6 dB | ~-14 dBFS | 2-8 dB |
| Headline underscore | -20 to -26 dB | -16 dB* | ~-22 dBFS | 10-16 dB |
| Headline sting | -12 to -18 dB | -6 dB | ~-16 dBFS | 4-10 dB |
| Section break | -16 to -28 dB | -10 dB | ~-26 dBFS | 14-20 dB |
| News-to-opinion | -8 to -22 dB | -4 dB | ~-12 dBFS | Between speech |
| Opinion kicker | -6 to -18 dB | -4 dB | ~-10 dBFS | Between speech |
| Background bed | -34 to -42 dB | 0 dB | ~-30 dBFS | 18-24 dB |
| Outro | -8 to -20 dB | -4 dB | ~-10 dBFS | After speech |

*The headline underscore uses a per-function gain structure rather than a separate master gain, because it is generated dynamically.

Note: Elements marked "Between speech" play in gaps, not over speech. Their gain can be higher because they are not competing with voice content.

---

## 12. Risk Assessment

### Low Risk
- **Headline sting activation**: Asset exists, just needs wiring. No sonic risk.
- **Opinion kicker**: New asset, plays after speech ends. Cannot interfere with content.
- **News-to-opinion redesign**: Plays between speech sections. The 800ms silence phase is self-evidently safe.

### Medium Risk
- **Headline underscore**: Plays OVER speech. If too loud, it masks words. Mitigation: -16 dB master gain is conservative (16 dB below average speech). Can be tuned down to -20 dB if listening tests reveal competition.
- **Proportional placement**: If Gemini produces a script with non-standard proportions (e.g., 50% on Story 1), the section breaks may land mid-story. Mitigation: snap-to-quiet refinement absorbs +/- 3 seconds of error. Even if a break lands 5 seconds off, a -26 dB chime during speech is barely noticeable.

### Regression Risks
- The `_overlay_section_breaks()` function and `_detect_silence_gaps()` function should be preserved (not deleted) for fallback use. The new proportional placement replaces them in the primary path but the old functions serve as a safety net if the dialogue word count is too low to estimate positions reliably.
- The `news_to_opinion.wav` file changes from 1.3s to 2.5s. Any code that hardcodes the transition duration should be checked (none found in current codebase -- the transition is loaded and appended without duration assumptions).

---

## 13. Testing Protocol

### Listening Test Checklist
After implementation, generate a test broadcast and evaluate:

- [ ] Headlines underscore: audible but not distracting during opening rundown?
- [ ] Headlines underscore: fade-out smooth? No abrupt cut?
- [ ] Headline sting: lands near the transition from rundown to Story 1?
- [ ] Section break 1: lands near the transition from Story 1 to Story 2?
- [ ] Section break 2: lands near the transition from Story 2 to Story 3?
- [ ] No section break lands in the middle of a sentence?
- [ ] News-to-opinion: the 800ms silence phase creates a clear "reset"?
- [ ] News-to-opinion: Phase 3 (F#4 bell) arrives before the opinion voice?
- [ ] Opinion kicker: lands after "void opinion." with appropriate weight?
- [ ] Background bed: still present throughout? Not masked by underscore?
- [ ] Overall: broadcast feels structured, not cluttered?
- [ ] Overall: total duration increase is reasonable (~12s)?

### Automated Validation
- Assert `news_to_opinion.wav` duration is between 2400ms and 2600ms.
- Assert `opinion_kicker.wav` duration is between 500ms and 700ms.
- Assert `generate_headline_underscore()` returns an AudioSegment with duration within 10% of requested.
- Assert proportional placement positions are within 0-100% of audio duration.
- Assert snap-to-quiet returns a position within the search window.

---

## 14. Deferred Ideas (Not in This Spec)

These are ideas considered and deliberately deferred:

1. **`[STORY_BREAK]` token in TTS prompt**: Would give text-level markers for precise story boundary detection. Deferred because it risks changing dialogue naturalness, and proportional placement should be sufficient.

2. **Per-story key changes**: Each story could have its own harmonic color (e.g., Story 1 in D major, Story 2 modulating to G). Deferred because the current D major 9th palette is the brand identity -- modulation would dilute it.

3. **Dynamic section break variants**: Generate 3 slightly different section breaks and use a different one at each boundary. Deferred as unnecessary complexity -- the listener hears each break once and will not notice repetition.

4. **Ducking the background bed during the underscore**: Side-chain-style ducking would lower the bed when the underscore plays. Deferred because they occupy overlapping but perceptually distinct registers, and the bed is already so quiet (-30 dB) that ducking is inaudible.

5. **Breaking news stinger**: A distinct, more urgent ident for breaking news editions. Deferred as a future feature -- requires editorial classification of "breaking" status.

---

## 15. Implementation Order

Recommended sequence for the developer:

1. `generate_assets.py`: Write `generate_opinion_kicker()`. Run, verify `opinion_kicker.wav` sounds correct.
2. `generate_assets.py`: Rewrite `generate_news_to_opinion()` with 3-phase structure. Run, verify the silence gap and Phase 3 bell.
3. `generate_assets.py`: Write `generate_headline_underscore(duration_ms)`. Test with 15000ms. Listen.
4. `audio_producer.py`: Write `_snap_to_quiet()`. Unit test against a known AudioSegment.
5. `audio_producer.py`: Write `_place_proportional_elements()`. Wire headline sting + section breaks.
6. `audio_producer.py`: Wire headline underscore overlay in assembly Step 4.
7. `audio_producer.py`: Wire opinion kicker in assembly Step 4.
8. `audio_producer.py`: Update gap timings for news-to-opinion transition.
9. Full integration test: `python pipeline/refresh_audio.py --editions world`
10. Listening test against checklist (Section 13).

---

*End of specification.*
