"""Generate void --news sonic identity assets.
Run once: python3 -m pipeline.briefing.generate_assets

Assets:
  - ident.wav:      0.8s intro — ascending A-major triad (data terminal online)
  - transition.wav: 0.3s section break — descending two-note (same interval, inverted)
  - outro.wav:      1.2s close — intro motif reversed, resolving down
"""

from pathlib import Path
from pydub import AudioSegment
from pydub.generators import Sine

ASSETS_DIR = Path(__file__).parent / "assets"


def _tone(freq_hz: int, duration_ms: int, gain_db: float = -6) -> AudioSegment:
    """Clean sine tone with sharp attack, soft release."""
    return (
        Sine(freq_hz)
        .to_audio_segment(duration=duration_ms)
        .apply_gain(gain_db)
        .fade_in(15)
        .fade_out(30)
    )


def generate_ident():
    """Intro ident: three ascending tones, A-major triad. 0.8s.
    A4 (440) → C#5 (554) → E5 (660). Staccato, precise.
    Reads as 'system ready' — data terminal coming online."""
    canvas = AudioSegment.silent(duration=800)
    canvas = canvas.overlay(_tone(440, 120, -6), position=0)
    canvas = canvas.overlay(_tone(554, 120, -6), position=150)
    canvas = canvas.overlay(_tone(660, 280, -4), position=300)
    canvas.export(ASSETS_DIR / "ident.wav", format="wav")
    print(f"  ident.wav ({len(canvas)}ms)")


def generate_transition():
    """Section transition: descending two-note. 0.3s.
    C#5 (554) → A4 (440). Same interval as intro, inverted.
    Subtle — sits under speech level at -12dB."""
    canvas = AudioSegment.silent(duration=300)
    canvas = canvas.overlay(_tone(554, 140, -12), position=0)
    canvas = canvas.overlay(_tone(440, 140, -12), position=160)
    canvas.export(ASSETS_DIR / "transition.wav", format="wav")
    print(f"  transition.wav ({len(canvas)}ms)")


def generate_outro():
    """Outro ident: intro motif reversed, resolving down. 1.2s.
    E5 (660) → C#5 (554) → A4 (440, sustained with fade).
    The long A4 fade = system powering down."""
    canvas = AudioSegment.silent(duration=1200)
    canvas = canvas.overlay(_tone(660, 120, -6), position=0)
    canvas = canvas.overlay(_tone(554, 120, -6), position=150)
    # Final A4: longer, fades out slowly
    final_a = (
        Sine(440)
        .to_audio_segment(duration=600)
        .apply_gain(-4)
        .fade_in(15)
        .fade_out(400)
    )
    canvas = canvas.overlay(final_a, position=300)
    canvas.export(ASSETS_DIR / "outro.wav", format="wav")
    print(f"  outro.wav ({len(canvas)}ms)")


def build_background_bed(duration_ms: int) -> AudioSegment:
    """Broadcast-floor presence bed. Three stacked sine layers, felt more than heard.

    85 Hz  (E2)  — floor presence, -32dB
    170 Hz (E3)  — warmth, -36dB
    520 Hz (C5)  — faint room tone, -40dB

    Constant, not pulsing. 600ms fade-in, 1200ms fade-out.
    Call at runtime — duration matches dialogue length.
    """
    bed_85 = Sine(85).to_audio_segment(duration=duration_ms).apply_gain(-32)
    bed_170 = Sine(170).to_audio_segment(duration=duration_ms).apply_gain(-36)
    bed_520 = Sine(520).to_audio_segment(duration=duration_ms).apply_gain(-40)
    bed = bed_85.overlay(bed_170).overlay(bed_520)
    return bed.fade_in(600).fade_out(1200)


if __name__ == "__main__":
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating void --news sonic identity:")
    generate_ident()
    generate_transition()
    generate_outro()
    print("Done.")
