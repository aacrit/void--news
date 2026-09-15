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
    print("Done.")
