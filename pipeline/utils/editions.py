"""
Edition configuration — single source of truth.

ACTIVE_EDITIONS used to live in pipeline/main.py. Worker contexts that
need to introspect which editions are live (e.g. cluster_summarizer's
Pool 2 round-robin) had to do `from main import ACTIVE_EDITIONS`, which
is fragile under multiprocessing/forking and creates an import cycle
risk. Now declared here so any module can import it without traversing
the orchestrator entry point.

Parking Lot: regional editions (us, europe, south-asia) disabled
pre-launch. To re-enable, change ACTIVE_EDITIONS and remove the parking
lot row in CLAUDE.md.
"""

ACTIVE_EDITIONS: list[str] = ["world"]
ALL_EDITIONS: list[str] = ["world", "us", "europe", "south-asia"]
