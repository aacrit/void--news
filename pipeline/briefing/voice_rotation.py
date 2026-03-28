"""Voice rotation for the void --news audio broadcast.

Uses Gemini 2.5 Flash TTS prebuilt voices. Newsroom model: 5 male hosts
and 5 female hosts rotate across runs so each broadcast sounds fresh.
Opinion voice is a separate fixed pool per edition.

Rotation: pipeline_run_count (4x daily) cycles through host pairs.
Day 1 run 1 gets pair 0, run 2 gets pair 1, etc. 5 pairs = 20 runs
(5 days) before repeating.

Official voice data from Google Cloud TTS docs:

Male (16): Achird (friendly), Algenib (gravelly), Algieba (smooth),
  Alnilam (firm), Charon (informative), Enceladus (breathy),
  Fenrir (excitable), Iapetus (clear), Orus (firm), Puck (upbeat),
  Rasalgethi (informative), Sadachbia (lively), Sadaltager (knowledgeable),
  Schedar (even), Umbriel (easy-going), Zubenelgenubi (casual).

Female (14): Achernar (soft), Aoede (breezy), Autonoe (bright),
  Callirrhoe (easy-going), Despina (smooth), Erinome (clear),
  Gacrux (mature), Kore (firm), Laomedeia (upbeat), Leda (youthful),
  Pulcherrima (forward), Sulafat (warm), Vindemiatrix (gentle),
  Zephyr (bright).
"""

from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Host pools — 5 male, 5 female. Chosen for maximum tonal contrast so
# each broadcast pair sounds distinct. Official style labels from Google.
# ---------------------------------------------------------------------------
MALE_HOSTS: list[str] = [
    "Charon",       # informative — authoritative anchor
    "Orus",         # firm — decisive, commanding
    "Sadaltager",   # knowledgeable — expert analyst
    "Achird",       # friendly — approachable co-host
    "Algenib",      # gravelly — distinctive texture
]

FEMALE_HOSTS: list[str] = [
    "Kore",         # firm — strong anchor presence
    "Aoede",        # breezy — natural conversational flow
    "Gacrux",       # mature — seasoned correspondent
    "Zephyr",       # bright — energetic reporter
    "Achernar",     # soft — thoughtful, measured
]

# 5 host pairs — each broadcast gets a unique male+female combination.
# Pairs maximize vocal contrast: authoritative+breezy, firm+bright, etc.
HOST_PAIRS: list[tuple[str, str]] = [
    ("Charon", "Aoede"),       # pair 0: informative anchor + breezy analyst
    ("Orus", "Zephyr"),        # pair 1: firm decisive + bright energetic
    ("Sadaltager", "Kore"),    # pair 2: knowledgeable expert + firm anchor
    ("Achird", "Gacrux"),      # pair 3: friendly co-host + mature correspondent
    ("Algenib", "Achernar"),   # pair 4: gravelly texture + soft thoughtful
]

# Opinion voices — one per edition, never used as news hosts.
# Fixed for brand consistency: opinion always sounds the same per edition.
# Chosen for editorial gravitas — voices that suit monologue delivery.
OPINION_VOICES: dict[str, str] = {
    "world": "Sulafat",       # female, warm — ideal for editorial
    "us": "Schedar",          # male, even — measured editorial tone
    "india": "Despina",       # female, smooth — composed editorial
    "uk": "Rasalgethi",       # male, informative — authoritative editorial
    "canada": "Vindemiatrix", # female, gentle — thoughtful editorial
}


def _get_rotation_index() -> int:
    """Get the current rotation index based on UTC time.

    4 runs per day x 5 pairs = cycles every 5 days (20 runs).
    Uses UTC hour buckets: 0-5=run0, 6-11=run1, 12-17=run2, 18-23=run3.
    """
    now = datetime.now(timezone.utc)
    day_of_year = now.timetuple().tm_yday
    run_of_day = now.hour // 6  # 0, 1, 2, or 3
    total_runs = (day_of_year * 4) + run_of_day
    return total_runs % len(HOST_PAIRS)


def get_voices_for_today(edition: str) -> dict:
    """Return voice config for the current broadcast.

    News hosts rotate across runs — 5 distinct male+female pairs cycle
    every 20 runs (5 days at 4x/day). Each broadcast sounds different.
    Opinion voice stays fixed per edition for brand consistency.
    """
    idx = _get_rotation_index()
    male, female = HOST_PAIRS[idx]

    # Alternate who leads (host_a) vs. who responds (host_b) each run
    if idx % 2 == 0:
        host_a, host_b = male, female
    else:
        host_a, host_b = female, male

    opinion_voice = OPINION_VOICES.get(edition, OPINION_VOICES["world"])

    return {
        "host_a": {"id": host_a},
        "host_b": {"id": host_b},
        "opinion": {"id": opinion_voice},
    }


def get_voice_for_today(edition: str) -> dict:
    """Return a single voice for backward compatibility."""
    return get_voices_for_today(edition)["host_a"]
