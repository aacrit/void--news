"""
Audio producer for the void --news daily brief.

Uses edge-tts (Microsoft Neural TTS, free, no API key) for two-host
dialogue synthesis. Parses A:/B: speaker tags, synthesizes each turn
with the appropriate voice, stitches with pydub.

Returns None gracefully if edge-tts or pydub are not installed.
"""

import asyncio
import io
import re
import sys
import tempfile
from pathlib import Path
from typing import Optional

# edge-tts + pydub are optional
EDGE_TTS_AVAILABLE = False
PYDUB_AVAILABLE = False

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    pass

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).parent.parent))

ASSETS_DIR = Path(__file__).parent / "assets"

# Segment markers in order
_SEGMENT_ORDER = [
    "GREETING", "HEADLINES",
    "STORY_1", "STORY_2", "STORY_3",
    "EDITORIAL_NOTE", "SIGNOFF",
]

# Silence gaps (ms) after each section marker
_SILENCE_AFTER: dict[str, int] = {
    "GREETING": 900,
    "HEADLINES": 1000,
    "STORY_1": 800,
    "STORY_2": 800,
    "STORY_3": 900,
    "EDITORIAL_NOTE": 700,
    "SIGNOFF": 0,
}

# Gap between speaker turns within a section
_TURN_GAP_MS = 180


def _parse_script(script: str) -> list[tuple[str, str, str]]:
    """
    Parse a two-host script into (marker, speaker, text) tuples.
    Lines with A:/B: prefixes get their own turn. Lines without default to "A".
    """
    turns: list[tuple[str, str, str]] = []
    current_marker: str = "GREETING"
    current_speaker: str = "A"
    current_lines: list[str] = []

    def _flush():
        text = " ".join(current_lines).strip()
        if text:
            turns.append((current_marker, current_speaker, text))
        current_lines.clear()

    for line in script.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        marker_match = re.match(r"^\[([A-Z_]+)\](.*)$", stripped)
        if marker_match:
            _flush()
            current_marker = marker_match.group(1)
            inline = marker_match.group(2).strip()
            if inline:
                sp = re.match(r"^([AB]):\s*(.+)$", inline)
                if sp:
                    current_speaker = sp.group(1)
                    current_lines.append(sp.group(2))
                else:
                    current_speaker = "A"
                    current_lines.append(inline)
            continue

        sp = re.match(r"^([AB]):\s*(.+)$", stripped)
        if sp:
            _flush()
            current_speaker = sp.group(1)
            current_lines.append(sp.group(2))
        else:
            current_lines.append(stripped)

    _flush()
    return turns


def _clean_text(text: str) -> str:
    """Strip leaked markers and speaker tags from TTS text."""
    text = re.sub(r"\[/?[A-Z_]+\]", "", text)
    text = re.sub(r"^[AB]:\s*", "", text)
    text = re.sub(
        r"\b(?:STORY|HEADLINE|GREETING|SIGNOFF|EDITORIAL)[_ ]?\d*:?\s*",
        "", text, flags=re.IGNORECASE,
    )
    return re.sub(r"  +", " ", text).strip()


async def _synthesize_edge(text: str, voice: str, rate: str = "-5%") -> Optional[bytes]:
    """Synthesize text via edge-tts. Returns MP3 bytes or None."""
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
        if chunks:
            return b"".join(chunks)
        return None
    except Exception as e:
        print(f"  [warn][audio] edge-tts failed: {e}")
        return None


def _synthesize_sync(text: str, voice: str, rate: str = "-5%") -> Optional[bytes]:
    """Sync wrapper for async edge-tts."""
    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(_synthesize_edge(text, voice, rate))
        loop.close()
        return result
    except Exception as e:
        print(f"  [warn][audio] sync wrapper failed: {e}")
        return None


def _mp3_to_segment(mp3_bytes: bytes) -> Optional["AudioSegment"]:
    """Convert MP3 bytes to pydub AudioSegment."""
    if not PYDUB_AVAILABLE:
        return None
    try:
        return AudioSegment.from_mp3(io.BytesIO(mp3_bytes))
    except Exception as e:
        print(f"  [warn][audio] MP3 decode failed: {e}")
        return None


def _load_asset(filename: str) -> Optional["AudioSegment"]:
    """Load a pre-recorded WAV asset."""
    if not PYDUB_AVAILABLE:
        return None
    path = ASSETS_DIR / filename
    if not path.exists():
        return None
    try:
        return AudioSegment.from_file(str(path), format="wav")
    except Exception as e:
        print(f"  [warn][audio] Asset load failed {filename}: {e}")
        return None


def _upload_to_supabase(audio_bytes: bytes, edition: str) -> Optional[str]:
    """Upload MP3 to Supabase Storage. Returns public URL."""
    try:
        from utils.supabase_client import supabase
        path = f"{edition}/latest.mp3"
        supabase.storage.from_("audio-briefs").upload(
            path, audio_bytes,
            {"content-type": "audio/mpeg", "upsert": "true"},
        )
        return supabase.storage.from_("audio-briefs").get_public_url(path)
    except Exception as e:
        print(f"  [warn][audio] Upload failed for {edition}: {e}")
        return None


def produce_audio(
    audio_script: str,
    voices: dict,
    edition: str,
) -> Optional[dict]:
    """
    Synthesize a two-host broadcast using edge-tts and upload to Supabase.

    Args:
        audio_script: Script with [MARKER] + A:/B: speaker tags.
        voices: {"host_a": {"id": "en-GB-RyanNeural", ...},
                 "host_b": {"id": "en-GB-SoniaNeural", ...}}
        edition: Edition slug for storage path.
    """
    if not EDGE_TTS_AVAILABLE:
        print("  [audio] edge-tts not installed — skipping")
        return None
    if not PYDUB_AVAILABLE:
        print("  [audio] pydub not installed — skipping")
        return None

    turns = _parse_script(audio_script)
    if not turns:
        print("  [warn][audio] No turns parsed from script")
        return None

    voice_a = voices["host_a"]["id"]
    voice_b = voices["host_b"]["id"]
    print(f"  [audio] Synthesizing {len(turns)} turns (A: {voice_a}, B: {voice_b})")

    combined: AudioSegment = AudioSegment.empty()

    # 1. Four beeps intro
    pips = _load_asset("pips.wav")
    if pips:
        combined += pips + AudioSegment.silent(duration=500)

    # 2. Two-host narration
    prev_marker = None
    synth_count = 0
    for marker, speaker, text in turns:
        text = _clean_text(text)
        if not text:
            continue

        # Section pause when marker changes
        if prev_marker and marker != prev_marker:
            combined += AudioSegment.silent(duration=_SILENCE_AFTER.get(prev_marker, 400))

        voice = voice_a if speaker == "A" else voice_b
        mp3_bytes = _synthesize_sync(text, voice)
        if mp3_bytes:
            seg = _mp3_to_segment(mp3_bytes)
            if seg:
                combined += seg
                synth_count += 1

        # Short gap between turns
        combined += AudioSegment.silent(duration=_TURN_GAP_MS)
        prev_marker = marker

    # Final section pause
    if prev_marker:
        combined += AudioSegment.silent(duration=_SILENCE_AFTER.get(prev_marker, 0))

    # 3. Clean ending
    combined += AudioSegment.silent(duration=500)

    if synth_count == 0:
        print("  [warn][audio] No segments synthesized — aborting")
        return None

    duration_seconds = round(len(combined) / 1000.0, 1)
    print(f"  [audio] Assembled {duration_seconds}s ({synth_count} turns)")

    # Export MP3
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        combined.export(tmp_path, format="mp3", bitrate="128k", parameters=["-ac", "1"])
        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()
    except Exception as e:
        print(f"  [warn][audio] Export failed: {e}")
        return None
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    file_size = len(audio_bytes)
    print(f"  [audio] Exported {file_size / 1024:.1f} KB — uploading")

    public_url = _upload_to_supabase(audio_bytes, edition)
    if not public_url:
        return None

    print(f"  [audio] Uploaded: {public_url}")
    return {
        "audio_url": public_url,
        "duration_seconds": duration_seconds,
        "file_size": file_size,
    }
