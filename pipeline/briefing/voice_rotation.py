"""Voice rotation for two-host daily audio briefs using edge-tts.

edge-tts voices are free, unlimited, no API key needed.
Each edition gets a male+female pair. Roles swap on alternate days.
"""

from datetime import datetime, timezone

# edge-tts neural voice pairs per edition
VOICE_PAIRS: dict[str, dict[str, dict]] = {
    "world": {
        "male":   {"id": "en-GB-RyanNeural", "label": "British Male"},
        "female": {"id": "en-GB-SoniaNeural", "label": "British Female"},
    },
    "us": {
        "male":   {"id": "en-US-GuyNeural", "label": "American Male"},
        "female": {"id": "en-US-JennyNeural", "label": "American Female"},
    },
    "india": {
        "male":   {"id": "en-IN-PrabhatNeural", "label": "Indian Male"},
        "female": {"id": "en-IN-NeerjaNeural", "label": "Indian Female"},
    },
}


def get_voices_for_today(edition: str) -> dict:
    """
    Return a two-host voice pair. Roles swap on alternate days.
    Returns: {"host_a": {"id": ..., ...}, "host_b": {"id": ..., ...}}
    """
    day = datetime.now(timezone.utc).timetuple().tm_yday
    pair = VOICE_PAIRS.get(edition, VOICE_PAIRS["world"])
    if day % 2 == 0:
        return {"host_a": pair["male"], "host_b": pair["female"]}
    else:
        return {"host_a": pair["female"], "host_b": pair["male"]}


def get_voice_for_today(edition: str) -> dict:
    """Single voice — backward compat."""
    return get_voices_for_today(edition)["host_a"]
