"""Voice casting for the History audio edition.

Every casting input already exists as a structured field on the event
(`severity`, `category`, `era`, `region`), so casting is a deterministic
table rather than 78 judgement calls. The same event always casts the same
way, and the mapping is testable.

Measured on a Ken Burns-register passage, 2026-09-19 (median pitch, spectral
centroid, natural words per minute at speed 1.0):

    bm_lewis    93 Hz  2207  172   the gravest voice on the roster
    am_michael 112 Hz  2861  160   dark American, unhurried
    bm_daniel  121 Hz  2176  155   British, warm, slow
    bm_george  137 Hz  2492  169   British, mid weight
    af_nicole  155 Hz  3270  113   intimate and very slow: testimony, not empire
    af_aoede   179 Hz  1915  181   the warmest voice measured

No voice is ever stretched. Pace is a casting decision, as on On Air: a voice
whose natural rate is wrong for an episode is not slowed down, it is not cast.
af_nicole at 113 wpm would run a 1,900 word script past twenty minutes, so it
is reserved for the shortest, most intimate pieces.
"""

from __future__ import annotations

# Categories whose events are defined by mass death. These take the gravest
# voice regardless of anything else.
_MASS_DEATH = ("genocide", "war", "disaster", "independence")
# Categories that are consequential without being funereal.
_STATECRAFT = ("political", "empire", "revolution", "economic")

# A narrator and its document voice must never be confusable: the change of
# voice is what tells the listener "these are real words". So the document
# reader always crosses the register, and is a READER OF RECORD, never an
# impersonator: it does not change per speaker and is never accent-matched to
# the region of the event.
_DOCUMENT_FOR = {
    "bm_lewis": "af_aoede",
    "am_michael": "af_aoede",
    "bm_daniel": "af_aoede",
    "bm_george": "af_aoede",
    "af_aoede": "bm_daniel",
    "af_nicole": "bm_george",
}


def cast(event: dict) -> dict:
    """Return {narrator, document, why} for an event."""
    sev = (event.get("severity") or "").lower()
    cat = (event.get("category") or "").lower()

    if sev == "catastrophic" and cat in _MASS_DEATH:
        narrator, why = "bm_lewis", f"catastrophic {cat}: the gravest voice"
    elif sev == "catastrophic":
        narrator, why = "am_michael", f"catastrophic {cat}: dark, but not funereal"
    elif sev == "critical" and cat in _MASS_DEATH:
        narrator, why = "am_michael", f"critical {cat}"
    elif cat == "cultural":
        narrator, why = "bm_daniel", "cultural: warm and unhurried"
    else:
        narrator, why = "bm_george", f"{sev or 'unrated'} {cat or 'event'}: mid weight"

    return {"narrator": narrator, "document": _DOCUMENT_FOR[narrator], "why": why}
