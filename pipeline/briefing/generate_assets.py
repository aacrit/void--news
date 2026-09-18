"""Generate void --news sonic identity assets.

Run: python3 -m pipeline.briefing.generate_assets

Sound design concept — "Glass & Gravity"
-----------------------------------------
The sonic identity of void --news is built from layered sine harmonics
shaped into chord voicings that bloom and resolve. No beeps, no drones.
Every element is a musical gesture with intention.

The harmonic palette is rooted in D major / B minor — warm, authoritative,
slightly nostalgic. Intervals are chosen for their natural beating patterns
when detuned by 1-2 Hz, creating organic shimmer without effects processing.

Assets:
  - ident.wav:           ~2.0s — harmonic bloom, D major 9th chord building
                          from a single root. Feels like tuning in.
  - transition.wav:       1.5s — rhythmic pulse phrase (legacy, kept for compat).
  - section_break.wav:    0.9s — glass-bell chime between stories. Light,
                          unobtrusive. Overlaid at silence gaps in speech.
  - news_to_opinion.wav:  1.3s — editorial page-turn. Weighted, deliberate.
                          Replaces transition.wav at the news→opinion boundary.
  - headline_sting.wav:   0.4s — full chord stab. Punctuation after headlines.
  - outro.wav:           ~1.8s — the bloom chord returns and resolves downward
                          to a low D with decaying harmonics. The lens closing.

Radio set (2026-09)
-------------------
A second, independent family of assets for the redesigned On Air radio show,
synthesized with numpy (additive partials, spectrally shaped noise, raised-
cosine envelopes, convolution reverb) and written as 24 kHz / mono / 16-bit
PCM via the stdlib `wave` module, so rendering never needs ffmpeg. The D major
/ B minor palette above is kept; the character is not. These are new files and
nothing above is touched.

  - radio_ident.wav:          2.4s — opening ident. A low D root swells, a
                              bright upper voicing blooms all at once, the
                              ninth falls away into the chord, and the root
                              rings on as a tail the sign-on speaks over.
                              Peak -14 dBFS.
  - radio_menu_bed.wav:      20.0s — seamlessly loopable pad under the spoken
                              headline menu. Eleven partials, each on its own
                              7-20s breath cycle. No melody, no pulse.
                              RMS -40 dBFS.
  - radio_close_bed.wav:     12.0s — the menu bed's warmer, lower sibling for
                              the sign-off. Does not loop; falls to silence
                              across the last 3s. RMS -40 dBFS.
  - radio_editorial_stab.wav: 0.7s — weighted low-mid page-turn marking the
                              move from news to the editorial. Darkens as it
                              settles; deliberately not a chime.
                              Peak -12 dBFS.
  - radio_outro.wav:          2.0s — the ident inverted: the voicing falls
                              from D5 back down to D2 and decays.
                              Peak -12 dBFS.
  - radio_room_tone.wav:     10.0s — loopable synthesized studio room tone,
                              pink-tilted, high-passed at 60 Hz, low-passed at
                              4 kHz. Mixed under the whole programme so TTS's
                              digital silence never sounds synthetic.
                              RMS -57 dBFS, inaudible as hiss.

ORIGINALITY RULE: every asset in this file is synthesized in-repo from first
principles. Nothing is sampled, transcribed, or modelled after a broadcaster's
or a library's signature. No time pips, no ascending-fifth fanfare, no
rhythmic underscore.

Loops are exact, not crossfaded: `_lock()` snaps every partial frequency and
every LFO rate to an integer multiple of 1/duration, and noise layers are
shaped over the full-buffer FFT, so the buffers are periodic and the wrap
point is click-free. The render prints measured peak dBFS, RMS dBFS, duration
and (for loopable assets) a seam ratio per file.
"""

from pathlib import Path
from pydub import AudioSegment
from pydub.generators import Sine

ASSETS_DIR = Path(__file__).parent / "assets"

# Match Gemini TTS native output rate (24kHz 16-bit mono).
# Assets at the same sample rate avoid implicit resampling during assembly.
SAMPLE_RATE = 24000


# ---------------------------------------------------------------------------
# Tone-shaping primitives
# ---------------------------------------------------------------------------

def _bell(freq_hz: float, duration_ms: int, gain_db: float = -6) -> AudioSegment:
    """Bell-like tone: fast attack, long exponential decay.

    The rapid fade-in (5ms) and slow fade-out (80% of duration) gives
    each tone the quality of a struck glass or chime rather than an
    electronic beep.
    """
    seg = (
        Sine(freq_hz, sample_rate=SAMPLE_RATE)
        .to_audio_segment(duration=duration_ms)
        .apply_gain(gain_db)
        .fade_in(5)
        .fade_out(int(duration_ms * 0.8))
    )
    return seg


def _pad(freq_hz: float, duration_ms: int, gain_db: float = -10) -> AudioSegment:
    """Pad tone: slow swell in, slow swell out.

    Used for harmonic beds that breathe in and out. The slow attack
    (40% of duration) means the tone emerges gradually — felt before
    it's consciously heard.
    """
    attack = int(duration_ms * 0.4)
    release = int(duration_ms * 0.5)
    seg = (
        Sine(freq_hz, sample_rate=SAMPLE_RATE)
        .to_audio_segment(duration=duration_ms)
        .apply_gain(gain_db)
        .fade_in(attack)
        .fade_out(release)
    )
    return seg


def _shimmer_pair(
    freq_hz: float,
    detune_hz: float,
    duration_ms: int,
    gain_db: float = -10,
) -> AudioSegment:
    """Two slightly detuned tones layered for natural chorus/beating.

    When two sines differ by 1-3 Hz, the interference pattern creates
    a slow amplitude modulation (beating) at the difference frequency.
    At 1.5 Hz detune, you get a gentle ~1.5 Hz pulse — organic shimmer
    that sounds alive, not electronic.
    """
    a = _pad(freq_hz, duration_ms, gain_db)
    b = _pad(freq_hz + detune_hz, duration_ms, gain_db - 2)
    return a.overlay(b)


# ---------------------------------------------------------------------------
# D major 9th voicing — the void --news chord
# ---------------------------------------------------------------------------
# D3 (147 Hz) — root, gravity
# A3 (220 Hz) — fifth, openness
# D4 (294 Hz) — octave, reinforcement
# F#4 (370 Hz) — major third, warmth
# E4 (330 Hz) — ninth, sophistication (the "news" note)
# A4 (440 Hz) — high fifth, shimmer
#
# This voicing has the weight of a piano chord in the left hand
# with color tones in the right. The ninth (E) prevents it from
# sounding like a simple triad — it adds the questioning quality
# appropriate for journalism.

_CHORD = {
    "root":     147.0,   # D3
    "fifth":    220.0,   # A3
    "octave":   294.0,   # D4
    "ninth":    330.0,   # E4
    "third":    370.0,   # F#4
    "hi_fifth": 440.0,   # A4
}


# ---------------------------------------------------------------------------
# Intro: "The Bloom"
# ---------------------------------------------------------------------------

def generate_ident():
    """Intro ident: D major 9th chord that blooms from a single root. ~2.0s.

    The root D arrives first, alone — a single clear tone.
    Then harmonics layer in one by one over 800ms, each slightly
    staggered, building the full chord. The effect is a sound that
    opens like a lens adjusting to light.

    Detuned pairs on the upper harmonics create organic shimmer.
    The whole thing breathes — it's alive, not static.

    Total: ~2000ms. What the listener hears: a warm chord that swells
    into focus, holds briefly at full resonance, then gently releases.
    """
    canvas = AudioSegment.silent(duration=2000)

    # Layer 1: Root arrives first — the anchor (t=0)
    # Bell-like attack, sustained presence
    root = _bell(_CHORD["root"], 1800, -8)
    canvas = canvas.overlay(root, position=0)

    # Subtle octave reinforcement, slightly detuned for warmth (t=80ms)
    root_color = _pad(_CHORD["root"] + 0.8, 1600, -16)
    canvas = canvas.overlay(root_color, position=80)

    # Layer 2: Fifth opens the chord (t=200ms)
    fifth = _bell(_CHORD["fifth"], 1500, -10)
    canvas = canvas.overlay(fifth, position=200)

    # Layer 3: Octave D reinforces (t=350ms)
    octave = _pad(_CHORD["octave"], 1300, -12)
    canvas = canvas.overlay(octave, position=350)
    # Shimmer pair on the octave
    octave_shimmer = _pad(_CHORD["octave"] + 1.5, 1200, -18)
    canvas = canvas.overlay(octave_shimmer, position=400)

    # Layer 4: The ninth — the questioning tone (t=500ms)
    ninth = _pad(_CHORD["ninth"], 1100, -13)
    canvas = canvas.overlay(ninth, position=500)

    # Layer 5: Major third — warmth arrives (t=600ms)
    third = _bell(_CHORD["third"], 1000, -12)
    canvas = canvas.overlay(third, position=600)

    # Layer 6: High fifth — crystalline top (t=700ms)
    # Shimmer pair creates the "alive" quality
    hi = _shimmer_pair(_CHORD["hi_fifth"], 1.5, 900, -14)
    canvas = canvas.overlay(hi, position=700)

    # Master gain: pull back to leave -3dB headroom (prevents clipping
    # from overlaid sine layers accumulating amplitude)
    canvas = canvas.apply_gain(-6)

    # Final master fade-out for smooth release
    canvas = canvas.fade_out(500)

    canvas.export(ASSETS_DIR / "ident.wav", format="wav")
    print(f"  ident.wav ({len(canvas)}ms) — D major 9th bloom")


# ---------------------------------------------------------------------------
# Transition: "The Pulse" — musical interstitial between stories
# ---------------------------------------------------------------------------

def generate_transition():
    """Story transition: a 1.5s musical phrase that breathes. Not a chime — a moment.

    Built from the same D major palette as the ident, but rhythmic:
    - A soft rhythmic pulse (bass notes with space between them)
    - Harmonic shimmer that swells and fades
    - The feel of a page turning in a magazine — unhurried, active, alive

    This plays between stories. It gives the listener a breath, signals
    "next topic," and keeps the energy moving without rushing.

    LEGACY: kept for backward compatibility. New assemblies use
    section_break.wav (intra-story) and news_to_opinion.wav (editorial shift).
    """
    canvas = AudioSegment.silent(duration=1500)

    # Rhythmic bass pulse: two soft D3 hits with space — heartbeat feel
    pulse1 = _bell(_CHORD["root"], 200, -14)
    pulse2 = _bell(_CHORD["root"], 250, -12)
    canvas = canvas.overlay(pulse1, position=100)
    canvas = canvas.overlay(pulse2, position=500)

    # Harmonic swell between the pulses — the "active" quality
    # A3 + E4 (fifth + ninth) shimmer pair, breathes in and out
    swell = _shimmer_pair(_CHORD["fifth"], 1.2, 900, -16)
    canvas = canvas.overlay(swell, position=200)

    # High color: a brief F#4 bell at the midpoint — the "turn"
    turn = _bell(_CHORD["third"], 300, -18)
    canvas = canvas.overlay(turn, position=700)

    # Ghost A4 shimmer trailing off — movement, not static
    trail = _pad(_CHORD["hi_fifth"], 600, -22)
    canvas = canvas.overlay(trail, position=800)

    # Shape: fade in gently, fade out naturally
    canvas = canvas.fade_in(80).fade_out(400)

    # Pull back gain for layered content
    canvas = canvas.apply_gain(-4)

    canvas.export(ASSETS_DIR / "transition.wav", format="wav")
    print(f"  transition.wav ({len(canvas)}ms) — rhythmic pulse phrase [legacy]")


# ---------------------------------------------------------------------------
# Section Break: "The Bell" — between stories within the news dialogue
# ---------------------------------------------------------------------------

def generate_section_break():
    """Section break: a crisp two-note stinger. ~1.2s.

    Inspired by The Economist's Intelligence podcast: their section
    breaks are short, bright, unmistakable. They ANNOUNCE "next story"
    rather than whispering it. The listener should think "oh, new topic"
    without effort.

    Design: a rising two-note motif (fifth → octave) with a shimmer tail.
    The rising interval creates forward momentum — "we're moving on."
    Louder than background, quieter than ident. This is a proper stinger,
    not ambient texture.

    Comparable to: Economist section break (~1-2s synth phrase),
    NPR Up First story divider (~1s bright sting).
    """
    canvas = AudioSegment.silent(duration=1200)

    # Beat 1: Fifth (A3) — the launch note, crisp bell
    note1 = _bell(_CHORD["fifth"], 350, -8)
    canvas = canvas.overlay(note1, position=50)

    # Beat 2: Octave (D4) — arrives 300ms later, rising interval
    note2 = _bell(_CHORD["octave"], 400, -8)
    canvas = canvas.overlay(note2, position=350)

    # Shimmer tail: A4 + detuned pair — sparkle after the notes land
    tail = _shimmer_pair(_CHORD["hi_fifth"], 1.5, 500, -16)
    canvas = canvas.overlay(tail, position=500)

    # Root anchor: D3 pad underneath — connects to the chord palette
    anchor = _pad(_CHORD["root"], 600, -18)
    canvas = canvas.overlay(anchor, position=100)

    # Ninth color: E4 ghost at the end — the "news" interval
    color = _pad(_CHORD["ninth"], 300, -20)
    canvas = canvas.overlay(color, position=600)

    # Shape: instant attack, natural ring-out
    canvas = canvas.fade_in(5).fade_out(400)

    # Master gain: audible and crisp — a proper stinger, not ambient
    canvas = canvas.apply_gain(-4)

    canvas.export(ASSETS_DIR / "section_break.wav", format="wav")
    print(f"  section_break.wav ({len(canvas)}ms) — glass bell between stories")


# ---------------------------------------------------------------------------
# News-to-Opinion: "The Page Turn" — editorial shift marker
# ---------------------------------------------------------------------------

def generate_news_to_opinion():
    """News-to-opinion transition: a 2.5s three-phase editorial page turn.

    The most important structural moment in the broadcast — the shift from
    two-voice reporting to single-voice editorial.

    Phase 1 — The Resolve (0-800ms):
      The news section closes. Low D3 pad swells, the fifth (A3) arrives
      as a bell. The feeling is "settling."

    Phase 2 — The Breath (800-1600ms):
      Literal silence. 800ms of nothing. The ear resets. The contrast
      between Phase 1's harmonics and Phase 2's silence creates the
      "page turn" — the brain registers a structural shift.

    Phase 3 — The Arrival (1600-2500ms):
      The opinion voice's territory. F#4 bell rings alone, then E4 ghosts
      in underneath with A4 shimmer. A compressed intro bloom starting
      from the chord's middle, not the root.
    """
    canvas = AudioSegment.silent(duration=2500)

    # --- Phase 1: The Resolve (0-800ms) ---
    # Root D3 pad — gravity, authority
    root_open = _pad(_CHORD["root"], 800, -8)
    canvas = canvas.overlay(root_open, position=0)

    # Root detune — warmth, beating
    root_detune = _pad(_CHORD["root"] + 0.8, 700, -16)
    canvas = canvas.overlay(root_detune, position=50)

    # Fifth A3 bell — short, settling
    fifth = _bell(_CHORD["fifth"], 400, -14)
    canvas = canvas.overlay(fifth, position=200)

    # Sub-bass D2 — felt in the chest
    sub = _pad(73.4, 600, -20)
    canvas = canvas.overlay(sub, position=100)

    # --- Phase 2: The Breath (800-1600ms) ---
    # Silence. The canvas is already silent here. Nothing to add.

    # --- Phase 3: The Arrival (1600-2500ms) ---
    # F#4 bell — the warmth note, alone first
    third_bell = _bell(_CHORD["third"], 500, -12)
    canvas = canvas.overlay(third_bell, position=1600)

    # E4 pad — the ninth ghosts in underneath
    ninth_pad = _pad(_CHORD["ninth"], 400, -18)
    canvas = canvas.overlay(ninth_pad, position=1700)

    # A4 + 441.5 Hz shimmer pair — high crystalline shimmer
    hi_shimmer = _shimmer_pair(_CHORD["hi_fifth"], 1.5, 350, -22)
    canvas = canvas.overlay(hi_shimmer, position=1750)

    # Shape: Phase 1 attack, Phase 3 decay
    canvas = canvas.fade_in(60).fade_out(400)

    # Master gain: more present than section break, less than ident
    canvas = canvas.apply_gain(-4)

    canvas.export(ASSETS_DIR / "news_to_opinion.wav", format="wav")
    print(f"  news_to_opinion.wav ({len(canvas)}ms) — three-phase editorial page turn")


# ---------------------------------------------------------------------------
# Headline Underscore: "The Arrival" — rhythmic bed under opening headlines
# ---------------------------------------------------------------------------

def generate_headline_underscore(duration_ms: int) -> "AudioSegment":
    """Generate a rhythmic underscore bed for the headlines section.

    Dynamically generated at assembly time (not saved to disk) because its
    duration must match the estimated headlines length.

    Three layers from the D major 9th palette:
      - D3 bell pulses every 800ms (75 BPM) — forward momentum
      - A3 shimmer pair (1.5 Hz detune) — harmonic warmth that breathes
      - Single E4 bell accent at 60% mark — the ninth waking up

    Args:
        duration_ms: Target duration, typically 12-20 seconds.

    Returns:
        AudioSegment at SAMPLE_RATE (24000 Hz), with fade-in and fade-out applied.
    """
    canvas = AudioSegment.silent(duration=duration_ms)

    # Layer 1: Rhythmic root pulse — D3 bell every 800ms (75 BPM)
    # Louder than before: these pulses should be felt as momentum
    pulse_interval = 800
    pulse_pos = 0
    while pulse_pos + 200 <= duration_ms:
        pulse = _bell(_CHORD["root"], 200, -14)
        canvas = canvas.overlay(pulse, position=pulse_pos)
        pulse_pos += pulse_interval

    # Layer 2: Shimmer swell — A3 + A3+1.5 Hz pad pair
    shimmer = _shimmer_pair(_CHORD["fifth"], 1.5, duration_ms, -18)
    canvas = canvas.overlay(shimmer, position=0)

    # Layer 3: Color accents — E4 bell at 40% and 80% marks
    for pct in (0.4, 0.8):
        accent_pos = int(duration_ms * pct)
        if accent_pos + 300 <= duration_ms:
            accent = _bell(_CHORD["ninth"], 300, -20)
            canvas = canvas.overlay(accent, position=accent_pos)

    # Layer 4: F#4 bell at 60% — the warmth note, once
    warmth_pos = int(duration_ms * 0.6)
    if warmth_pos + 250 <= duration_ms:
        warmth = _bell(_CHORD["third"], 250, -22)
        canvas = canvas.overlay(warmth, position=warmth_pos)

    # Gain curve: 600ms fade-in, 2500ms fade-out (longer dissolve)
    fade_in_ms = min(600, duration_ms // 3)
    fade_out_ms = min(2500, duration_ms // 2)
    canvas = canvas.fade_in(fade_in_ms).fade_out(fade_out_ms)

    # Master gain: present — the headlines should feel energized
    canvas = canvas.apply_gain(-10)

    return canvas


# ---------------------------------------------------------------------------
# Headline Sting: "The Stamp" — quick punctuation after headlines
# ---------------------------------------------------------------------------

def generate_headline_sting():
    """Headline sting: a 0.4s chord stab. Punctuation, not melody.

    Used after the opening headlines rundown — a quick "full stop" that
    marks the end of the summary and the beginning of the deep coverage.

    The sound is a compressed version of the full D major 9th chord,
    all tones arriving simultaneously and decaying fast. Think: a gavel
    tap, but musical. Or a newspaper being snapped open to the front page.

    Design choices:
    - All chord tones at once (no staggered bloom — that is the intro's job)
    - Very fast decay (300ms bell envelopes)
    - The ninth (E4) and third (F#4) are slightly louder — they carry
      the "identity" of the chord in this compressed form
    - Root D3 provides just enough weight to feel authoritative
    """
    canvas = AudioSegment.silent(duration=400)

    # All tones arrive together — simultaneous, not layered
    root = _bell(_CHORD["root"], 300, -14)
    canvas = canvas.overlay(root, position=10)

    fifth = _bell(_CHORD["fifth"], 280, -16)
    canvas = canvas.overlay(fifth, position=10)

    octave = _bell(_CHORD["octave"], 260, -18)
    canvas = canvas.overlay(octave, position=10)

    # Identity tones — slightly more present
    ninth = _bell(_CHORD["ninth"], 300, -12)
    canvas = canvas.overlay(ninth, position=10)

    third = _bell(_CHORD["third"], 300, -12)
    canvas = canvas.overlay(third, position=10)

    # High fifth — crystalline top
    hi = _bell(_CHORD["hi_fifth"], 250, -16)
    canvas = canvas.overlay(hi, position=10)

    # Shape: instant attack, fast out
    canvas = canvas.fade_in(5).fade_out(200)

    # Master gain: crisp but not aggressive
    canvas = canvas.apply_gain(-6)

    canvas.export(ASSETS_DIR / "headline_sting.wav", format="wav")
    print(f"  headline_sting.wav ({len(canvas)}ms) — chord stab punctuation")


# ---------------------------------------------------------------------------
# Opinion Kicker: "The Landing" — chord stab after editorial
# ---------------------------------------------------------------------------

def generate_opinion_kicker():
    """Opinion kicker: a 0.6s chord stab. The period at the end of the editorial.

    A compressed version of the outro's resolving motion, but faster and
    heavier. Where the outro breathes over 1.8s, the kicker drops and lands
    in 0.6s. Think: the last chord of a piano piece, played forte then
    allowed to ring.

    All tones arrive nearly simultaneously (within 20ms) — a chord stab,
    not a bloom. The root is louder than in the headline sting (-6 vs. -14 dB),
    giving it more gravity. The sub-bass provides physical weight.
    """
    canvas = AudioSegment.silent(duration=600)

    # Root D3 bell — heavy, authoritative
    root = _bell(_CHORD["root"], 500, -6)
    canvas = canvas.overlay(root, position=0)

    # Fifth A3 bell — arrives 10ms later
    fifth = _bell(_CHORD["fifth"], 450, -10)
    canvas = canvas.overlay(fifth, position=10)

    # Third F#4 bell — warmth, same time as fifth
    third = _bell(_CHORD["third"], 400, -10)
    canvas = canvas.overlay(third, position=10)

    # Ninth E4 bell — arrives 20ms later
    ninth = _bell(_CHORD["ninth"], 350, -14)
    canvas = canvas.overlay(ninth, position=20)

    # Sub-bass D2 pad — physical weight, starts with root
    sub = _pad(73.4, 400, -18)
    canvas = canvas.overlay(sub, position=0)

    # Shape: instant attack (5ms), ring and decay (350ms)
    canvas = canvas.fade_in(5).fade_out(350)

    # Master gain: present, comparable to the ident
    canvas = canvas.apply_gain(-4)

    canvas.export(ASSETS_DIR / "opinion_kicker.wav", format="wav")
    print(f"  opinion_kicker.wav ({len(canvas)}ms) — chord stab after editorial")


# ---------------------------------------------------------------------------
# Outro: "The Resolve"
# ---------------------------------------------------------------------------

def generate_outro():
    """Outro: the bloom chord returns, then resolves down to the root. ~1.8s.

    Opens with the top of the chord (A4 + F#4 + E4) in bell tones,
    then the harmonics fall away, leaving only the root D3 with a
    long, warm decay. The effect is a musical sigh — resolution,
    completion, the broadcast signing off.

    The root D3 is held longest with a slow shimmer, giving the
    ending a sense of gravity — the sound settling to the ground.
    """
    canvas = AudioSegment.silent(duration=1800)

    # Upper chord tones arrive first — echo of the intro
    hi_fifth = _bell(_CHORD["hi_fifth"], 600, -12)
    canvas = canvas.overlay(hi_fifth, position=0)

    third = _bell(_CHORD["third"], 700, -13)
    canvas = canvas.overlay(third, position=50)

    ninth = _bell(_CHORD["ninth"], 800, -14)
    canvas = canvas.overlay(ninth, position=100)

    # Mid tones
    octave = _pad(_CHORD["octave"], 1000, -14)
    canvas = canvas.overlay(octave, position=200)

    fifth = _bell(_CHORD["fifth"], 1100, -12)
    canvas = canvas.overlay(fifth, position=250)

    # The root — arrives last, sustains longest
    # This is the "gravity" — the sound settling down
    root = _pad(_CHORD["root"], 1500, -8)
    canvas = canvas.overlay(root, position=300)

    # Warm shimmer on the root
    root_shimmer = _pad(_CHORD["root"] + 0.8, 1400, -16)
    canvas = canvas.overlay(root_shimmer, position=350)

    # Sub-bass presence: D2 (73.4 Hz) — felt more than heard
    sub = _pad(73.4, 1200, -20)
    canvas = canvas.overlay(sub, position=400)

    # Master gain: headroom for layered sines
    canvas = canvas.apply_gain(-4)

    # Long final decay
    canvas = canvas.fade_out(900)

    canvas.export(ASSETS_DIR / "outro.wav", format="wav")
    print(f"  outro.wav ({len(canvas)}ms) — resolving to root D")


# ---------------------------------------------------------------------------
# Background Bed: "The Presence Layer" — felt, not heard
# ---------------------------------------------------------------------------

def generate_background_bed():
    """Background bed: a 10s loopable subharmonic warmth layer.

    This sits BELOW the speech frequency band (200-4000 Hz) so it never
    competes with voices. No ducking needed. The listener won't consciously
    hear it, but removing it would make the broadcast feel thinner.

    Three layers, all subharmonic:
      - D2 (73.4 Hz) at -34 dB — root presence, felt in headphones
      - D3 (147 Hz) at -38 dB — harmonic warmth, octave reinforcement
      - A3 (220 Hz) shimmer pair at -42 dB — 1.2 Hz beating for life

    The bed is tileable: identical fade-in/fade-out shapes at start/end
    allow seamless looping when tiled in the assembly pipeline.

    Industry standard: background music 20-26 dB below speech (W3C, BBC).
    These levels (-34 to -42 dB individual, ~-30 dB combined) exceed that
    margin against TTS output at ~-6 to -12 dBFS.
    """
    duration = 10000  # 10 seconds, tileable

    canvas = AudioSegment.silent(duration=duration)

    # Layer 1: Root presence — D2, felt in the chest
    root = _pad(73.4, duration, -34)
    canvas = canvas.overlay(root)

    # Layer 2: Harmonic warmth — D3, octave above root
    warmth = _pad(_CHORD["root"], duration, -38)
    canvas = canvas.overlay(warmth)

    # Layer 3: Shimmer ghost — A3 detuned pair, 1.2 Hz beating
    # Creates imperceptible pulse that makes the bed feel alive
    shimmer = _shimmer_pair(_CHORD["fifth"], 1.2, duration, -42)
    canvas = canvas.overlay(shimmer)

    # Tileable crossfade: gentle ramps at both ends
    canvas = canvas.fade_in(500).fade_out(500)

    canvas.export(ASSETS_DIR / "background_bed.wav", format="wav")
    print(f"  background_bed.wav ({len(canvas)}ms) — subharmonic presence layer")


# ===========================================================================
# RADIO SET (2026-09) — numpy additive synthesis
# ===========================================================================
# Everything below is a separate, self-contained synthesis layer. It does not
# touch the pydub generators above; the weekly/history assemblies keep loading
# ident.wav / outro.wav / background_bed.wav / news_to_opinion.wav /
# opinion_kicker.wav unchanged.
#
# Why numpy here: the radio set needs sample-accurate control the pydub
# generator API cannot give — per-partial envelopes, spectrally shaped noise,
# convolution reverb, and (critically) beds that loop without a seam.
#
# ORIGINALITY RULE: every sample is computed from first principles in this
# file. Nothing is sampled, transcribed, or modelled after a broadcaster's
# signature. No pips, no ascending-fifth fanfare, no rhythmic underscore.
#
# LOOP MATHEMATICS: an asset loops seamlessly with no crossfade when every
# component is exactly periodic over the buffer. `_lock()` snaps each partial
# frequency and each LFO rate to an integer multiple of 1/duration, and the
# noise layers are built by shaping a full-buffer FFT (circular by
# construction). The last sample then flows into the first sample as if the
# buffer were infinite. `_seam_ratio()` measures this and it is printed per
# loopable file: a value near 1.0 means the wrap-around step is no larger
# than an ordinary sample-to-sample step, i.e. inaudible.

import wave

try:  # numpy is in pipeline/requirements.txt; guard so audio_producer's
    import numpy as np  # import of generate_headline_underscore never breaks.
except ImportError:  # pragma: no cover
    np = None

# The six radio assets, in programme order.
RADIO_ASSETS = [
    "radio_ident.wav",
    "radio_menu_bed.wav",
    "radio_close_bed.wav",
    "radio_editorial_stab.wav",
    "radio_outro.wav",
    "radio_room_tone.wav",
]

# Same D major / B minor palette as the pydub set above, extended down to D2
# for gravity and up to F#5 for the ident's bright voicing. B2/B3 are the
# B-minor shading: they let the beds read as harmonically rich without ever
# committing to a melody.
_NOTE = {
    "D2":  73.416,
    "A2": 110.000,
    "B2": 123.471,
    "D3": 146.832,
    "F#3": 184.997,
    "A3": 220.000,
    "B3": 246.942,
    "D4": 293.665,
    "E4": 329.628,
    "F#4": 369.994,
    "A4": 440.000,
    "B4": 493.883,
    "D5": 587.330,
    "E5": 659.255,
    "F#5": 739.989,
}


# ---------------------------------------------------------------------------
# numpy primitives
# ---------------------------------------------------------------------------

def _time(duration_s: float):
    """Sample-clock array for `duration_s` at SAMPLE_RATE."""
    return np.arange(int(round(duration_s * SAMPLE_RATE))) / float(SAMPLE_RATE)


def _lock(freq_hz: float, duration_s: float) -> float:
    """Snap a frequency to the nearest integer multiple of 1/duration.

    A partial at k/duration Hz completes exactly k cycles in the buffer, so
    its value and slope at the wrap point are identical to those at t=0.
    Snapping every partial and LFO makes the whole buffer periodic, which is
    what makes the beds loop with no crossfade and no click. The shift is at
    most 1/(2*duration) Hz (0.025 Hz over 20s) — far below any pitch JND.
    """
    return max(1.0, round(freq_hz * duration_s)) / float(duration_s)


def _tone(t, freq_hz: float, phase: float = 0.0):
    """One sine partial. No square/saw anywhere in this file, by design."""
    return np.sin(2.0 * np.pi * freq_hz * t + phase)


def _swell(t, onset: float, attack: float, hold: float, release: float):
    """Raised-cosine attack / flat hold / raised-cosine release.

    Cosine rather than linear ramps: the first derivative is zero at both
    ends, so a swell never announces itself with an edge. This is the
    "soft attack" the radio set is built on.
    """
    env = np.zeros_like(t)
    x = t - onset
    a = (x >= 0.0) & (x < attack)
    env[a] = 0.5 - 0.5 * np.cos(np.pi * x[a] / attack)
    h = (x >= attack) & (x < attack + hold)
    env[h] = 1.0
    r = (x >= attack + hold) & (x < attack + hold + release)
    env[r] = 0.5 + 0.5 * np.cos(np.pi * (x[r] - attack - hold) / release)
    return env


def _pluck(t, onset: float, attack_tau: float, decay_tau: float):
    """Soft-attack exponential decay: (1 - e^-x/a) * e^-x/d.

    Used for the stab and the outro cascade. `attack_tau` of 10-40ms keeps
    the onset weighted rather than clicky — there is no instantaneous edge,
    so nothing reads as a beep.
    """
    x = np.maximum(t - onset, 0.0)
    env = (1.0 - np.exp(-x / attack_tau)) * np.exp(-x / decay_tau)
    env[t < onset] = 0.0
    return env


def _breath(t, rate_hz: float, depth: float, phase: float):
    """Slow amplitude wander between (1-depth) and 1.0. Never a pulse.

    Rates used in the beds are 0.05-0.15 Hz, i.e. 7-20 second cycles. At
    that speed the ear reads "the room is alive", not "something is
    repeating".
    """
    return (1.0 - depth) + depth * (0.5 + 0.5 * np.sin(2.0 * np.pi * rate_hz * t + phase))


def _shaped_noise(n: int, shaper, seed: int):
    """Noise with an arbitrary magnitude response, periodic over n samples.

    White noise -> rFFT -> multiply by the shaper's magnitude curve -> irFFT.
    Because the shaping happens on the full-buffer spectrum, the result is a
    circular (periodic) signal: sample n-1 leads into sample 0 correctly.
    That is what lets the room tone loop forever with no seam.
    """
    rng = np.random.default_rng(seed)
    spec = np.fft.rfft(rng.standard_normal(n))
    freqs = np.fft.rfftfreq(n, 1.0 / SAMPLE_RATE)
    gain = shaper(freqs)
    gain[0] = 0.0  # kill DC; a DC offset would eat headroom and thump on loop
    out = np.fft.irfft(spec * gain, n)
    peak = np.max(np.abs(out))
    return out / peak if peak > 0 else out


def _pink_lp_hp(pink_exp: float, lp_hz: float, hp_hz: float, order: int = 2):
    """Magnitude-response shaper: 1/f^exp tilt, Butterworth-shaped LP and HP."""
    def shaper(f):
        f = np.maximum(f, 1e-6)
        tilt = 1.0 / np.power(f, pink_exp)
        lp = 1.0 / np.sqrt(1.0 + np.power(f / lp_hz, 2 * order))
        hp = np.power(f / hp_hz, order) / np.sqrt(1.0 + np.power(f / hp_hz, 2 * order))
        return tilt * lp * hp
    return shaper


def _reverb_ir(duration_s: float, decay_tau: float, lp_hz: float, seed: int):
    """Algorithmic reverb impulse: a dark, exponentially decaying noise burst.

    A decaying noise tail convolved with the dry signal is the cheapest
    honest reverb there is: dense from the first millisecond, no comb
    ringing, no metallic flutter. Low-passing the tail makes the room feel
    upholstered rather than tiled — a studio, not a stairwell.
    """
    n = int(round(duration_s * SAMPLE_RATE))
    tail = _shaped_noise(n, _pink_lp_hp(0.0, lp_hz, 80.0, order=2), seed)
    tail = tail * np.exp(-np.arange(n) / (decay_tau * SAMPLE_RATE))
    tail /= np.max(np.abs(tail))
    tail[:24] *= np.linspace(0.0, 1.0, 24)  # no pre-echo edge on the tail
    ir = np.zeros(n)
    ir[0] = 1.0                              # dry impulse
    ir += 0.55 * tail
    return ir


def _reverberate(x, wet: float, ir):
    """Mix a convolved tail in behind the dry signal, truncated to length."""
    tail = np.convolve(x, ir)[: len(x)]
    peak = np.max(np.abs(tail))
    if peak > 0:
        tail = tail * (np.max(np.abs(x)) / peak)
    return (1.0 - wet) * x + wet * tail


def _edge_fade(x, fade_in_ms: float, fade_out_ms: float):
    """Raised-cosine fades so a one-shot never starts or ends on an edge."""
    out = x.copy()
    n_in = int(SAMPLE_RATE * fade_in_ms / 1000.0)
    n_out = int(SAMPLE_RATE * fade_out_ms / 1000.0)
    if n_in > 1:
        out[:n_in] *= 0.5 - 0.5 * np.cos(np.pi * np.arange(n_in) / n_in)
    if n_out > 1:
        out[-n_out:] *= 0.5 + 0.5 * np.cos(np.pi * np.arange(n_out) / n_out)
    return out


# ---------------------------------------------------------------------------
# Measurement, gain staging, file writing
# ---------------------------------------------------------------------------

def _peak_dbfs(x) -> float:
    peak = float(np.max(np.abs(x)))
    return -999.0 if peak <= 0 else 20.0 * np.log10(peak)


def _rms_dbfs(x) -> float:
    rms = float(np.sqrt(np.mean(np.square(x))))
    return -999.0 if rms <= 0 else 20.0 * np.log10(rms)


def _norm_peak(x, target_dbfs: float):
    """Scale so the loudest sample sits exactly at target_dbfs."""
    peak = float(np.max(np.abs(x)))
    if peak <= 0:
        return x
    return x * (10.0 ** (target_dbfs / 20.0) / peak)


def _norm_rms(x, target_dbfs: float, peak_ceiling_dbfs: float = -1.0):
    """Scale to a target RMS, then pull back if that would risk the ceiling.

    Beds are specified by RMS because RMS is what determines whether they
    read under speech; peak is irrelevant at -40 dBFS. The ceiling check is
    the clip guard: it can only ever reduce gain, never raise it.
    """
    rms = float(np.sqrt(np.mean(np.square(x))))
    if rms <= 0:
        return x
    out = x * (10.0 ** (target_dbfs / 20.0) / rms)
    ceiling = 10.0 ** (peak_ceiling_dbfs / 20.0)
    peak = float(np.max(np.abs(out)))
    if peak > ceiling:
        out = out * (ceiling / peak)
    return out


def _seam_ratio(x) -> float:
    """How big the loop wrap-around step is vs an ordinary sample step.

    ~1.0 means the seam is indistinguishable from any other sample
    transition, i.e. the loop is click-free. Anything above ~10 would be
    audible as a tick once per cycle.
    """
    typical = float(np.mean(np.abs(np.diff(x))))
    if typical <= 0:
        return 0.0
    return float(abs(x[0] - x[-1])) / typical


def _write_radio_wav(filename: str, x, note: str, loopable: bool = False):
    """Hard-clip guard, 16-bit PCM write via stdlib `wave`, then report.

    stdlib `wave` rather than pydub export: the render must not depend on
    ffmpeg being present.
    """
    clipped = int(np.count_nonzero(np.abs(x) > 1.0))
    x = np.clip(x, -1.0, 1.0)
    pcm = np.round(x * 32767.0).astype(np.int16)

    path = ASSETS_DIR / filename
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(SAMPLE_RATE)
        fh.writeframes(pcm.tobytes())

    # Measure what actually landed on disk, post-quantisation.
    measured = pcm.astype(np.float64) / 32768.0
    seam = f"  seam x{_seam_ratio(measured):.2f}" if loopable else ""
    guard = f"  CLIPPED {clipped}" if clipped else ""
    print(
        f"  {filename:<26} {len(measured) / SAMPLE_RATE:5.2f}s  "
        f"peak {_peak_dbfs(measured):6.1f} dBFS  "
        f"rms {_rms_dbfs(measured):6.1f} dBFS{seam}{guard}  — {note}"
    )


# ---------------------------------------------------------------------------
# 1. radio_ident.wav — "Tuning In"
# ---------------------------------------------------------------------------

def generate_radio_ident():
    """2.4s opening ident. Peak -14 dBFS.

    The gesture is one continuous act of focusing, not a tune:

      0.00-0.85s  A low D2/D3 root swells up out of nothing. Slight detune
                  (0.7 / 1.1 Hz) gives a slow breathing beat, and two quiet
                  upper harmonics on D3 make it read as a struck body rather
                  than a test tone.
      0.45s       The upper voicing arrives ALL AT ONCE (D4, F#4, A4, D5,
                  F#5). Simultaneous, deliberately: a staggered entry would
                  be an ascending fanfare, which is exactly the broadcast
                  cliche this must avoid.
      0.45-1.45s  E5, the ninth, hangs above the voicing and then falls away
                  while D5 stays. That is the resolution — a suspension
                  releasing INTO the chord, heard as the sound settling into
                  focus rather than as two melody notes.
      1.6-2.4s    Everything above the root has gone. D2/D3 ring on alone at
                  a low level: the tail the sign-on speaks over.

    Deliberately NOT: no pips (no isolated 1 kHz tones, nothing on a grid),
    no ascending perfect fifth, no rhythmic element of any kind, no
    brass/orchestral fanfare shape, nothing with a repeating figure.
    """
    dur = 2.4
    t = _time(dur)
    sig = np.zeros_like(t)

    # --- Low root swell: gravity arrives first ---
    root_env = _swell(t, 0.00, 0.85, 0.55, 1.00)
    sig += 0.58 * root_env * _tone(t, _NOTE["D2"], 0.0)
    sig += 0.22 * root_env * _tone(t, _NOTE["D2"] + 0.7, 1.9)   # 0.7 Hz beat
    sig += 0.42 * root_env * _tone(t, _NOTE["D3"], 0.6)
    sig += 0.17 * root_env * _tone(t, _NOTE["D3"] + 1.1, 3.1)   # 1.1 Hz beat
    # Two quiet harmonics of D3: body, not brightness.
    sig += 0.07 * root_env * _tone(t, _NOTE["D3"] * 2.0, 2.2)
    sig += 0.035 * root_env * _tone(t, _NOTE["D3"] * 3.0, 0.4)

    # --- Upper voicing: simultaneous bloom, no arpeggio ---
    up_env = _swell(t, 0.45, 0.22, 0.50, 0.90)
    for note, amp, detune, phase in (
        ("D4",  0.17, 0.0, 0.3),
        ("F#4", 0.15, 0.0, 1.4),
        ("A4",  0.20, 0.0, 2.6),
        ("D5",  0.16, 0.0, 4.0),
        ("F#5", 0.085, 0.0, 5.2),
        ("A4",  0.075, 1.4, 0.9),   # shimmer twin
        ("D5",  0.060, 1.4, 2.1),   # shimmer twin
    ):
        sig += amp * up_env * _tone(t, _NOTE[note] + detune, phase)

    # --- The ninth: present, then released. This is the "resolve". ---
    ninth_env = _swell(t, 0.45, 0.20, 0.25, 0.55)
    sig += 0.135 * ninth_env * _tone(t, _NOTE["E5"], 1.1)
    sig += 0.050 * ninth_env * _tone(t, _NOTE["E5"] + 1.6, 3.4)

    # --- Room ---
    sig = _reverberate(sig, 0.18, _reverb_ir(0.80, 0.22, 3500.0, seed=101))

    sig = _edge_fade(sig, 8.0, 70.0)
    sig = _norm_peak(sig, -14.0)
    _write_radio_wav("radio_ident.wav", sig, "opening ident, low root into bright voicing")


# ---------------------------------------------------------------------------
# 2. radio_menu_bed.wav — "Under the Menu"
# ---------------------------------------------------------------------------

def generate_radio_menu_bed():
    """20s seamlessly loopable pad under the spoken headline menu. RMS -40 dBFS.

    Low-information by construction. Eleven sine partials of a D-major-with-
    B-minor-shading stack, each on its own 7-to-20-second breath cycle at a
    different phase, so the composite never repeats a recognisable shape and
    never pulses. Nothing here is a melody, because nothing here ever changes
    pitch.

    Nearly all the energy is below 250 Hz, i.e. under the speech
    intelligibility band. At -40 dBFS RMS against TTS at roughly -18 dBFS it
    sits ~22 dB down, inside the W3C/BBC 20-26 dB guidance for a bed under
    speech, so the headline menu needs no ducking.

    The loop is exact, not crossfaded: every partial frequency and every
    breath rate is snapped by `_lock()` to a multiple of 1/20 Hz, and the
    air layer is FFT-shaped over the whole buffer.
    """
    dur = 20.0
    t = _time(dur)
    sig = np.zeros_like(t)

    # (note, detune Hz, amplitude, breath rate Hz, breath depth, phase)
    voices = (
        ("D2",  0.00, 0.60, 0.05, 0.25, 0.0),
        ("D2",  0.35, 0.24, 0.07, 0.30, 2.1),
        ("A2",  0.00, 0.34, 0.06, 0.30, 4.2),
        ("D3",  0.00, 0.40, 0.09, 0.35, 1.3),
        ("D3",  0.55, 0.16, 0.11, 0.40, 3.7),
        ("F#3", 0.00, 0.22, 0.08, 0.45, 5.5),
        ("A3",  0.00, 0.20, 0.10, 0.45, 0.8),
        ("A3",  1.15, 0.09, 0.13, 0.50, 2.9),
        ("B3",  0.00, 0.10, 0.07, 0.55, 4.8),   # B minor shading
        ("D4",  0.00, 0.09, 0.12, 0.55, 1.7),
        ("F#4", 1.70, 0.05, 0.14, 0.60, 3.3),
    )
    for note, detune, amp, rate, depth, phase in voices:
        freq = _lock(_NOTE[note] + detune, dur)
        sig += amp * _breath(t, _lock(rate, dur), depth, phase) * _tone(t, freq, phase)

    # Two faint harmonics of the root: richness without adding information.
    for mult, amp, phase in ((2.0, 0.05, 2.4), (3.0, 0.025, 5.0)):
        sig += amp * _breath(t, _lock(0.06, dur), 0.3, phase) * _tone(
            t, _lock(_NOTE["D2"] * mult, dur), phase
        )

    # Air: a narrow, very quiet noise band so the pad has a top without
    # having a treble. FFT-shaped, therefore periodic, therefore loop-safe.
    air = _shaped_noise(len(t), _pink_lp_hp(0.5, 1100.0, 260.0, order=2), seed=202)
    sig += 0.030 * _breath(t, _lock(0.05, dur), 0.35, 2.0) * air

    sig = _norm_rms(sig, -40.0)
    _write_radio_wav(
        "radio_menu_bed.wav", sig, "loopable headline-menu pad", loopable=True
    )


# ---------------------------------------------------------------------------
# 3. radio_close_bed.wav — "Under the Sign-Off"
# ---------------------------------------------------------------------------

def generate_radio_close_bed():
    """12s bed under the sign-off, with a natural end. RMS -40 dBFS.

    The menu bed's family, moved down and warmed: the top is B3, there is no
    F#4 shimmer, and the B2 gives the stack a minor-key weight the opening
    bed does not have. Same breathing construction, so the two beds are
    audibly siblings.

    It does not loop and does not need to. A 1.2s swell in, then from 9.0s a
    3.0s raised-cosine fall to true digital silence, so the programme ends on
    a decay rather than a cut.
    """
    dur = 12.0
    t = _time(dur)
    sig = np.zeros_like(t)

    voices = (
        ("D2",  0.00, 0.62, 0.06, 0.25, 0.4),
        ("D2",  0.30, 0.26, 0.08, 0.30, 2.7),
        ("A2",  0.00, 0.36, 0.07, 0.30, 4.9),
        ("B2",  0.00, 0.14, 0.05, 0.40, 1.1),   # the warm minor shade
        ("D3",  0.00, 0.38, 0.09, 0.35, 3.5),
        ("D3",  0.45, 0.15, 0.11, 0.40, 5.8),
        ("F#3", 0.00, 0.20, 0.08, 0.45, 0.9),
        ("A3",  0.00, 0.16, 0.10, 0.50, 2.2),
        ("B3",  0.00, 0.07, 0.12, 0.55, 4.4),
    )
    for note, detune, amp, rate, depth, phase in voices:
        sig += amp * _breath(t, rate, depth, phase) * _tone(t, _NOTE[note] + detune, phase)

    for mult, amp, phase in ((2.0, 0.045, 1.8), (3.0, 0.020, 4.6)):
        sig += amp * _breath(t, 0.07, 0.3, phase) * _tone(t, _NOTE["D2"] * mult, phase)

    air = _shaped_noise(len(t), _pink_lp_hp(0.5, 850.0, 220.0, order=2), seed=303)
    sig += 0.026 * _breath(t, 0.06, 0.35, 3.0) * air

    # Swell in, hold, and fall to silence across the last 3 seconds.
    sig *= _swell(t, 0.0, 1.2, 7.8, 3.0)

    sig = _norm_rms(sig, -40.0)
    _write_radio_wav("radio_close_bed.wav", sig, "sign-off bed, fades to silence")


# ---------------------------------------------------------------------------
# 4. radio_editorial_stab.wav — "The Page Turn"
# ---------------------------------------------------------------------------

def generate_radio_editorial_stab():
    """0.7s stab marking news -> editorial. Peak -12 dBFS.

    Weighted and deliberate, and pointedly NOT a chime. Three things keep it
    out of chime territory:

      1. The whole stack lives between D2 and D4. There is no bell partial
         above 300 Hz, so there is nothing to ring.
      2. Spectral darkening: the higher partials are given short decay
         constants and the low ones long ones, so the sound loses its top
         within 150ms and settles. That downward spectral motion is what the
         ear reads as weight.
      3. A 40ms low-passed noise transient under the onset — the physical
         sound of something being moved, not struck.

    The attack is 12ms of raised exponential, not a step: deliberate, never
    percussive.
    """
    dur = 0.7
    t = _time(dur)
    sig = np.zeros_like(t)

    # (note, detune Hz, amp, attack_tau, decay_tau, phase)
    # Decay constants fall as pitch rises: the stack darkens as it settles.
    for note, detune, amp, atk, dec, phase in (
        ("D2",  0.0, 0.58, 0.014, 0.30, 0.0),
        ("D2",  0.6, 0.20, 0.016, 0.26, 2.3),   # detuned twin
        ("D3",  0.0, 0.52, 0.012, 0.24, 1.2),
        ("F#3", 0.0, 0.30, 0.013, 0.17, 3.4),
        ("A3",  0.0, 0.25, 0.013, 0.13, 5.1),
        ("D4",  0.0, 0.13, 0.011, 0.085, 0.7),
    ):
        sig += amp * _pluck(t, 0.0, atk, dec) * _tone(t, _NOTE[note] + detune, phase)

    # Sub weight, felt rather than heard on a phone speaker.
    sig += 0.16 * _pluck(t, 0.0, 0.020, 0.22) * _tone(t, _NOTE["D2"] / 2.0, 1.5)

    # The physical transient: dark, short, low in the mix.
    thud = _shaped_noise(len(t), _pink_lp_hp(0.6, 760.0, 70.0, order=2), seed=404)
    sig += 0.26 * _pluck(t, 0.0, 0.004, 0.055) * thud

    # Small, tight, upholstered room. A long tail would turn this into a bell.
    sig = _reverberate(sig, 0.13, _reverb_ir(0.35, 0.10, 2200.0, seed=505))

    sig = _edge_fade(sig, 2.0, 60.0)
    sig = _norm_peak(sig, -12.0)
    _write_radio_wav("radio_editorial_stab.wav", sig, "news -> editorial page turn")


# ---------------------------------------------------------------------------
# 5. radio_outro.wav — "The Descent"
# ---------------------------------------------------------------------------

def generate_radio_outro():
    """2.0s closing resolve: the ident inverted. Peak -12 dBFS.

    The ident begins at the root and opens upward into the bright voicing.
    This begins at the top of that same voicing and falls back down to the
    root, one note every 140ms, each with a longer decay than the one above
    it. Because the decays overlap heavily the ear hears a single settling
    gesture rather than a descending scale, which is the point: a scale would
    be a melodic tag, and a tag is a station signature.

    D5 -> A4 -> F#4 -> D4 -> A3 -> D3 -> D2. The last two arrive with slow
    attacks and hold while everything above them dies, then a 0.65s master
    release takes the whole thing to silence.
    """
    dur = 2.0
    t = _time(dur)
    sig = np.zeros_like(t)

    # (note, onset, amp, attack_tau, decay_tau, phase)
    cascade = (
        ("D5",  0.00, 0.19, 0.030, 0.45, 0.0),
        ("A4",  0.14, 0.23, 0.030, 0.55, 1.6),
        ("F#4", 0.28, 0.25, 0.035, 0.70, 3.0),
        ("D4",  0.42, 0.27, 0.040, 0.85, 4.5),
        ("A3",  0.56, 0.31, 0.050, 1.05, 5.9),
        ("D3",  0.70, 0.52, 0.100, 1.60, 1.1),
        ("D2",  0.78, 0.62, 0.160, 2.20, 2.4),
    )
    for note, onset, amp, atk, dec, phase in cascade:
        sig += amp * _pluck(t, onset, atk, dec) * _tone(t, _NOTE[note], phase)

    # Detuned twins on the two landing notes: the same 0.8 / 1.1 Hz breathing
    # the ident opens with, so the close answers the open.
    sig += 0.21 * _pluck(t, 0.70, 0.100, 1.60) * _tone(t, _NOTE["D3"] + 1.1, 4.0)
    sig += 0.24 * _pluck(t, 0.78, 0.160, 2.20) * _tone(t, _NOTE["D2"] + 0.8, 5.3)
    # Body harmonics on the root.
    sig += 0.07 * _pluck(t, 0.78, 0.140, 1.30) * _tone(t, _NOTE["D2"] * 2.0, 0.6)
    sig += 0.03 * _pluck(t, 0.78, 0.140, 0.90) * _tone(t, _NOTE["D2"] * 3.0, 2.8)

    sig = _reverberate(sig, 0.20, _reverb_ir(0.90, 0.26, 3000.0, seed=606))

    # Master release: the tail decays rather than being cut at 2.0s.
    sig *= _swell(t, 0.0, 0.02, 1.33, 0.65)

    sig = _edge_fade(sig, 3.0, 40.0)
    sig = _norm_peak(sig, -12.0)
    _write_radio_wav("radio_outro.wav", sig, "closing resolve, descending to low D")


# ---------------------------------------------------------------------------
# 6. radio_room_tone.wav — "The Room"
# ---------------------------------------------------------------------------

def generate_radio_room_tone():
    """10s loopable synthesized studio room tone. RMS -57 dBFS.

    Mixed under the entire programme. Its only job is that the gaps between
    TTS turns stop being mathematically perfect digital silence, which is the
    single loudest tell that a broadcast was machine-assembled. Real rooms
    are never silent; this gives the ear a floor to rest on.

    Spectrum: a 1/sqrt(f) pink tilt, 2nd-order high-pass at 60 Hz (below that
    is rumble that costs headroom and buys nothing), 2nd-order low-pass at
    4 kHz (above that it would read as hiss). At -57 dBFS RMS it is roughly
    39 dB under speech and around 20 dB under the beds, so it is inaudible as
    hiss at any normal level and only noticeable if it is removed.

    A 0.1 Hz, +/-0.4 dB level wander keeps it from sounding like a frozen
    noise buffer. Built by full-buffer FFT shaping and a period-locked
    wander, so the loop is exact.
    """
    dur = 10.0
    t = _time(dur)

    tone = _shaped_noise(
        len(t), _pink_lp_hp(0.5, 4000.0, 60.0, order=2), seed=707
    )
    # Barely-there level drift: one full cycle per buffer, so loop-safe.
    tone = tone * _breath(t, _lock(0.1, dur), 0.09, 0.0)

    tone = _norm_rms(tone, -57.0)
    _write_radio_wav(
        "radio_room_tone.wav", tone, "loopable studio room tone", loopable=True
    )


# ---------------------------------------------------------------------------
# Radio set entry point
# ---------------------------------------------------------------------------

def render_radio_assets():
    """Render the six radio-set assets into ASSETS_DIR.

    Independent of the pydub set: nothing here overwrites ident.wav,
    outro.wav, background_bed.wav, news_to_opinion.wav or opinion_kicker.wav.
    """
    if np is None:  # pragma: no cover
        raise RuntimeError(
            "numpy is required to render the radio set "
            "(pip install 'numpy~=1.26.4'); it is listed in pipeline/requirements.txt"
        )
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating void --onair radio set (2026-09):")
    generate_radio_ident()
    generate_radio_menu_bed()
    generate_radio_close_bed()
    generate_radio_editorial_stab()
    generate_radio_outro()
    generate_radio_room_tone()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating void --news sonic identity (Glass & Gravity):")
    generate_ident()
    generate_transition()
    generate_section_break()
    generate_news_to_opinion()
    generate_headline_sting()
    generate_opinion_kicker()
    generate_outro()
    generate_background_bed()
    print()
    render_radio_assets()
    print("Done.")
