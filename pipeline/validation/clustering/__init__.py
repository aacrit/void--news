"""Clustering validation suite for void --news.

Mirrors the bias engine validation pattern (pipeline/validation/runner.py)
but exercises pipeline/clustering/story_cluster.py instead of analyzers.

Fixtures live under fixtures/*.yaml. Each encodes a known clustering
behavior: must-merge, must-split, must-be-present, must-dampen,
must-tag, or must-have-signal. Run via:

    python pipeline/validation/clustering/runner.py
"""
