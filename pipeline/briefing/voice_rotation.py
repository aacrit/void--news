"""Voice rotation for daily audio briefs. 3 voices per edition, cycling daily."""

from datetime import datetime, timezone

VOICES: dict[str, list[dict]] = {
    "world": [
        {"id": "en-GB-Neural2-B", "label": "British Male", "gender": "M", "language_code": "en-GB"},
        {"id": "en-GB-Neural2-A", "label": "British Female", "gender": "F", "language_code": "en-GB"},
        {"id": "en-GB-Neural2-D", "label": "British Male II", "gender": "M", "language_code": "en-GB"},
    ],
    "us": [
        {"id": "en-US-Neural2-D", "label": "American Male", "gender": "M", "language_code": "en-US"},
        {"id": "en-US-Neural2-F", "label": "American Female", "gender": "F", "language_code": "en-US"},
        {"id": "en-US-Neural2-J", "label": "American Male II", "gender": "M", "language_code": "en-US"},
    ],
    "india": [
        {"id": "en-IN-Neural2-B", "label": "Indian Male", "gender": "M", "language_code": "en-IN"},
        {"id": "en-IN-Neural2-A", "label": "Indian Female", "gender": "F", "language_code": "en-IN"},
        {"id": "en-IN-Neural2-D", "label": "Indian Male II", "gender": "M", "language_code": "en-IN"},
    ],
}


def get_voice_for_today(edition: str) -> dict:
    """Return the voice dict for today's broadcast of the given edition."""
    day = datetime.now(timezone.utc).timetuple().tm_yday
    voices = VOICES.get(edition, VOICES["world"])
    return voices[day % len(voices)]
