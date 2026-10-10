"""Newspaper of Record — permanent print archive of each day's top-50.

Phase 1 is backend-only (nothing reader-facing). ``print_archive`` snapshots
the displayed top-50 clusters, metadata-only (no article bodies), into the
permanent ``printed_days`` / ``printed_stories`` tables (migration 075).
"""
