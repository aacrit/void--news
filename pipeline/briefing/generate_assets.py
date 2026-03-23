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
  - ident.wav:      ~2.0s — harmonic bloom, D major 9th chord building
                     from a single root. Feels like tuning in.
  - transition.wav:  0.6s — soft breath: a glass-bell dyad that swells
                     and vanishes. Marks a page turn.
  - outro.wav:      ~1.8s — the bloom chord returns and resolves downward
                     to a low D with decaying harmonics. The lens closing.
"""

from pathlib import Path
from pydub import AudioSegment
from pydub.generators import Sine

ASSETS_DIR = Path(__file__).parent / "assets"


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
        Sine(freq_hz)
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
        Sine(freq_hz)
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
# Transition: "The Breath"
# ---------------------------------------------------------------------------

def generate_transition():
    """Story transition: a soft glass-bell dyad. ~0.6s.

    Two notes — D5 and A4 — arrive almost together with bell attacks
    and fast decay. The effect is a gentle chime, like a crystal glass
    touched lightly. It says "next" without shouting.

    Sits well under speech level at -16/-18 dB. The listener registers
    the boundary subconsciously.
    """
    canvas = AudioSegment.silent(duration=600)

    # Primary bell: D5 (587 Hz) — bright but not harsh
    bell_hi = _bell(587.0, 500, -16)
    canvas = canvas.overlay(bell_hi, position=0)

    # Harmonic: A4 (440 Hz) — perfect fifth below, grounds the chime
    bell_lo = _bell(440.0, 450, -18)
    canvas = canvas.overlay(bell_lo, position=40)

    # Ghost harmonic: D4 (294 Hz) — barely there, adds depth
    ghost = _pad(294.0, 350, -24)
    canvas = canvas.overlay(ghost, position=60)

    canvas = canvas.fade_out(200)

    canvas.export(ASSETS_DIR / "transition.wav", format="wav")
    print(f"  transition.wav ({len(canvas)}ms) — glass bell dyad")


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
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating void --news sonic identity (Glass & Gravity):")
    generate_ident()
    generate_transition()
    generate_outro()
    print("Done.")
