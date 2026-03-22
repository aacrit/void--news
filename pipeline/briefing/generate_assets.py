"""Generate static audio assets for the daily brief broadcast.
Run once: python3 -m pipeline.briefing.generate_assets

Assets:
  - pips.wav: 4 short BBC-style beeps at 1kHz
"""

from pathlib import Path
from pydub import AudioSegment
from pydub.generators import Sine

ASSETS_DIR = Path(__file__).parent / "assets"


def generate_pips():
    """4 short beeps (100ms, 1kHz) with 900ms gaps. Classic broadcast opener."""
    beep = Sine(1000).to_audio_segment(duration=100).fade_in(5).fade_out(20) - 8
    gap = AudioSegment.silent(duration=900)

    audio = AudioSegment.empty()
    for i in range(4):
        audio += beep
        if i < 3:
            audio += gap

    audio.export(ASSETS_DIR / "pips.wav", format="wav")
    print(f"  pips.wav ({len(audio)}ms)")


if __name__ == "__main__":
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    print("Generating broadcast assets:")
    generate_pips()
    print("Done.")
