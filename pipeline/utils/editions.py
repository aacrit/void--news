"""Single-feed constants.

2026-06-02 — void --news collapsed to a single daily feed. The legacy
multi-edition data plane (us, europe, south-asia) is gone. The two
constants below are kept as singletons so any worker still importing
ACTIVE_EDITIONS / ALL_EDITIONS continues to work; they both resolve to
["world"]. Callers should treat the values as opaque — equality is the
only meaningful operation.
"""

ACTIVE_EDITIONS: list[str] = ["world"]
ALL_EDITIONS: list[str] = ["world"]
