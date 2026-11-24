"""The mood map: what a segment's `# MOOD:` directive does to the production.

docs/proposals/HISTORY-AUDIO-ARCHIVAL.md §5a, §5b, §5d, §5e. Six moods, each
derived from what the segment CARRIES (a count that is short, a document being
made, the moment the thing happens, the dead, one person's words, the
accounts), so two drafters tag the same scene the same way. A mood is
advisory data about the production, never a fact about the event, so it needs
no gate beyond "a name in the set".

A mood sets four things and nothing else:
  pace     Kokoro `speed` for the narrator and for the document voice. Never
           below 0.88: a voice slowed further sounds ill, not grave.
  silence  the gaps between lines, into and out of a document read, and the
           length of a REST that follows the segment
  score    which bed runs under it (or none), how deep it ducks, and which
           transition plays into it
  dryness  testimony and rupture carry no bed: nothing under a person's own
           words, and nothing under the moment until its last word

A segment with no mood inherits the previous one. A script with no moods at
all renders exactly as it did before this module existed.
"""

from __future__ import annotations

from dataclasses import dataclass

SPEED_FLOOR = 0.88


@dataclass(frozen=True)
class Mood:
    name: str
    narrator_speed: float
    document_speed: float
    line_ms: int             # between narrator lines in one segment
    to_document_ms: int      # narrator -> the document voice
    from_document_ms: int    # the document voice -> narrator
    rest_ms: int             # a `## REST` after a segment in this mood
    rest_short_ms: int       # a `## REST | short`
    duck_db: float | None    # bed floor under speech; None = no bed at all (cut)
    stings: bool             # the to_document sting plays in this mood
    lufs_short_term: float   # the master's short-term target, reported per chapter

    @property
    def dry(self) -> bool:
        return self.duck_db is None


MOODS: dict[str, Mood] = {m.name: m for m in (
    #     name         N     D     line  to_d  fr_d  rest  short duck   sting LUFS-S
    Mood("dread",     0.92, 0.95,  520, 1000, 1500, 4000, 2600, -10.0, True,  -18.0),
    Mood("procedure", 1.00, 0.95,  380,  900, 1200, 3000, 2000, -14.0, True,  -16.0),
    Mood("rupture",   0.95, 0.95,  700, 1100, 1600, 3500, 2400, None,  False, -16.0),
    Mood("grief",     0.90, 0.93,  560, 1200, 1800, 4500, 3000, -10.0, True,  -18.0),
    Mood("testimony", 0.95, 0.93,  480, 1400, 1800, 4000, 2600, None,  False, -17.0),
    Mood("reckoning", 1.00, 0.95,  340,  800, 1100, 2000, 1400, -18.0, True,  -15.0),
)}

for _m in MOODS.values():   # the floor is a rule, so it is asserted, not hoped
    assert _m.narrator_speed >= SPEED_FLOOR and _m.document_speed >= SPEED_FLOOR, _m.name


def segment_moods(script) -> list[str | None]:
    """The mood in force for each segment: its own `# MOOD:`, else the last
    one set. Unknown names are ignored (and reported by `unknown_moods`)."""
    out: list[str | None] = []
    cur: str | None = None
    for seg in script.segments:
        d = seg.directive("MOOD")
        if d is not None and d.head in MOODS:
            cur = d.head
        out.append(cur)
    return out


def dry_segments(script) -> list[bool]:
    """A segment is dry when its mood is, or when it says `# DRY`."""
    moods = segment_moods(script)
    return [bool(seg.directive("DRY")) or (m is not None and MOODS[m].dry)
            for seg, m in zip(script.segments, moods)]


def has_moods(script) -> bool:
    return any(m is not None for m in segment_moods(script))


def unknown_moods(script) -> list[str]:
    return [d.head for seg in script.segments for d in seg.directives_of("MOOD") if d.head not in MOODS]
