"""Generate static audio assets for the daily brief broadcast.
Run once: python3 -m pipeline.briefing.generate_assets

Exports as WAV (no ffmpeg required). Assets:
  - pips.wav: BBC-style time pips (5 short + 1 long at 1kHz)
  - countdown.wav: "3... 2... 1..." tonal countdown (descending frequencies)
  - outro.wav: Soft chime + warm bass resolution (broadcast ends)
"""

from pathlib import Path
from pydub import AudioSegment
from pydub.generators import Sine

ASSETS_DIR = Path(__file__).parent / "assets"


def generate_pips():
    """BBC Greenwich time pips: 5 short beeps (100ms, 1kHz) + 1 long beep (500ms).
    Each pip separated by 900ms silence. Classic analog broadcast opener."""
    short = Sine(1000).to_audio_segment(duration=100).fade_in(5).fade_out(20) - 8
    silence = AudioSegment.silent(duration=900)
    long_pip = Sine(1000).to_audio_segment(duration=500).fade_in(5).fade_out(80) - 6

    audio = AudioSegment.empty()
    for _ in range(5):
        audio += short + silence
    audio += long_pip

    audio.export(ASSETS_DIR / "pips.wav", format="wav")
    print(f"  pips.wav ({len(audio)}ms)")


def generate_countdown():
    """Tonal countdown: three descending tones representing 3...2...1.
    Each tone is a clean sine at descending pitch with a gap.
    Evokes analog broadcast count-in without spoken words."""
    # Three descending tones: E5 (659Hz), C5 (523Hz), A4 (440Hz)
    freqs = [659, 523, 440]
    audio = AudioSegment.empty()

    for i, freq in enumerate(freqs):
        tone = Sine(freq).to_audio_segment(duration=250).fade_in(10).fade_out(60) - 6
        gap = AudioSegment.silent(duration=600)
        audio += tone + gap

    # Final long tone at A4 — the "zero" moment
    final = Sine(440).to_audio_segment(duration=600).fade_in(10).fade_out(150) - 4
    audio += final

    audio.export(ASSETS_DIR / "countdown.wav", format="wav")
    print(f"  countdown.wav ({len(audio)}ms)")


def generate_outro():
    """Soft chime + warm bass resolution. Two layers:
    1. High chime: C6 (1047Hz) bell-like tone, short, bright
    2. Warm bass: C3 (131Hz) sustained underneath, slow fade
    Mixed together for a "broadcast ends" feeling."""

    # Chime: bright, short, bell-like
    chime = Sine(1047).to_audio_segment(duration=400).fade_in(5).fade_out(200) - 8
    chime_pad = chime + AudioSegment.silent(duration=200)

    # Second softer chime a fifth below: G5 (784Hz)
    chime2 = Sine(784).to_audio_segment(duration=500).fade_in(5).fade_out(250) - 10
    chime2_pad = AudioSegment.silent(duration=300) + chime2

    # Warm bass: C3, long sustain, slow fade
    bass = Sine(131).to_audio_segment(duration=2500).fade_in(100).fade_out(1200) - 6

    # Layer: bass is the bed, chimes sit on top
    # Make all same length
    total_ms = 2500
    chime_full = chime_pad + AudioSegment.silent(duration=total_ms - len(chime_pad))
    chime2_full = chime2_pad + AudioSegment.silent(duration=total_ms - len(chime2_pad))

    # Overlay
    mixed = bass.overlay(chime_full).overlay(chime2_full)

    # Final fade
    mixed = mixed.fade_out(800)

    mixed.export(ASSETS_DIR / "outro.wav", format="wav")
    print(f"  outro.wav ({len(mixed)}ms)")


if __name__ == "__main__":
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating broadcast assets:")
    generate_pips()
    generate_countdown()
    generate_outro()
    print("Done.")
