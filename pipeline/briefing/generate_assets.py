"""Generate static audio assets for the daily brief broadcast.
Run once: python -m pipeline.briefing.generate_assets
"""

from pathlib import Path
from pydub import AudioSegment
from pydub.generators import Sine

ASSETS_DIR = Path(__file__).parent / "assets"


def generate_pips():
    """Greenwich time pips: 5 short beeps (100ms, 1kHz) + 1 long beep (500ms)."""
    short = Sine(1000).to_audio_segment(duration=100).fade_out(20) - 6  # reduce volume
    silence = AudioSegment.silent(duration=900)
    long_pip = Sine(1000).to_audio_segment(duration=500).fade_out(50) - 6

    audio = AudioSegment.empty()
    for _ in range(5):
        audio += short + silence
    audio += long_pip

    audio.export(ASSETS_DIR / "pips.mp3", format="mp3", bitrate="128k")
    print(f"Generated pips.mp3 ({len(audio)}ms)")


def generate_ident():
    """Warm sine sweep 200-800Hz over 1.5s — analog broadcast ident."""
    # Build sweep by concatenating short sine segments at increasing frequencies
    duration_ms = 1500
    steps = 30
    step_ms = duration_ms // steps
    audio = AudioSegment.empty()
    for i in range(steps):
        freq = 200 + (600 * i / steps)  # 200 to 800 Hz
        segment = Sine(freq).to_audio_segment(duration=step_ms) - 8
        audio += segment
    audio = audio.fade_in(100).fade_out(200)
    audio.export(ASSETS_DIR / "ident.mp3", format="mp3", bitrate="128k")
    print(f"Generated ident.mp3 ({len(audio)}ms)")


def generate_outro():
    """Descending tone 800-200Hz over 2s, fade out."""
    duration_ms = 2000
    steps = 40
    step_ms = duration_ms // steps
    audio = AudioSegment.empty()
    for i in range(steps):
        freq = 800 - (600 * i / steps)  # 800 to 200 Hz
        segment = Sine(freq).to_audio_segment(duration=step_ms) - 8
        audio += segment
    audio = audio.fade_in(50).fade_out(500)
    audio.export(ASSETS_DIR / "outro.mp3", format="mp3", bitrate="128k")
    print(f"Generated outro.mp3 ({len(audio)}ms)")


if __name__ == "__main__":
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    generate_pips()
    generate_ident()
    generate_outro()
    print("All assets generated.")
