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
# Quoted speech is read by a voice of the SPEAKER'S SEX, so every episode
# carries two readers. The male reader must not be confusable with a male
# narrator, so it is chosen far from the narrator in pitch: bm_lewis at 93 Hz
# narrates against am_michael at 112, bm_george at 137 against bm_lewis. The
# attribution spoken before every read does the rest of the work.
_DOCUMENTS_FOR = {
    "bm_lewis":   {"M": "bm_george",  "F": "af_aoede"},
    "am_michael": {"M": "bm_daniel",  "F": "af_aoede"},
    "bm_daniel":  {"M": "am_michael", "F": "af_aoede"},
    "bm_george":  {"M": "bm_lewis",   "F": "af_aoede"},
    "af_aoede":   {"M": "bm_daniel",  "F": "af_nicole"},
    "af_nicole":  {"M": "bm_george",  "F": "af_aoede"},
}


def cast(event: dict) -> dict:
    """Return {narrator, document_m, document_f, why} for an event."""
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

    docs = _DOCUMENTS_FOR[narrator]
    return {"narrator": narrator, "document_m": docs["M"], "document_f": docs["F"], "why": why}
