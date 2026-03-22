"""Voice rotation for two-host daily audio briefs.

Each edition gets a male+female pair. Roles (anchor vs analyst) swap
on alternate days so listeners hear variety.
"""

from datetime import datetime, timezone

# Two voices per edition: male + female pair
VOICE_PAIRS: dict[str, dict[str, dict]] = {
    "world": {
        "male":   {"id": "en-GB-Neural2-B", "label": "British Male", "gender": "M", "language_code": "en-GB"},
        "female": {"id": "en-GB-Neural2-A", "label": "British Female", "gender": "F", "language_code": "en-GB"},
    },
    "us": {
        "male":   {"id": "en-US-Neural2-D", "label": "American Male", "gender": "M", "language_code": "en-US"},
        "female": {"id": "en-US-Neural2-F", "label": "American Female", "gender": "F", "language_code": "en-US"},
    },
    "india": {
        "male":   {"id": "en-IN-Neural2-B", "label": "Indian Male", "gender": "M", "language_code": "en-IN"},
        "female": {"id": "en-IN-Neural2-A", "label": "Indian Female", "gender": "F", "language_code": "en-IN"},
    },
}


def get_voices_for_today(edition: str) -> dict:
    """
    Return a two-host voice pair for today's broadcast.

    On even days: male = Host A (anchor), female = Host B (analyst).
    On odd days: roles swap for variety.

    Returns:
        {
            "host_a": {"id": "...", "language_code": "...", ...},
            "host_b": {"id": "...", "language_code": "...", ...},
        }
    """
    day = datetime.now(timezone.utc).timetuple().tm_yday
    pair = VOICE_PAIRS.get(edition, VOICE_PAIRS["world"])

    if day % 2 == 0:
        return {"host_a": pair["male"], "host_b": pair["female"]}
    else:
        return {"host_a": pair["female"], "host_b": pair["male"]}


# Backward compat — single voice (returns host_a)
def get_voice_for_today(edition: str) -> dict:
    """Return a single voice for backward compatibility."""
    return get_voices_for_today(edition)["host_a"]
