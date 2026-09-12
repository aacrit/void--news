"""Loader for clustering-suite YAML fixtures.

Each fixture file is a YAML document of the shape:

    id: streeting-resigns-2026-05
    name: "Streeting health-secretary resignation (must merge)"
    failure_date: "2026-05-15"
    failure_kind: fragmentation
    articles:
      - id: a1
        title: "..."
        summary: "..."
        full_text: "..."
        source: { slug: bbc, country: GB, tier: international, lean_baseline: -0.2 }
        published_at: "2026-05-12T14:00Z"
        bias_score: { political_lean: 45 }   # optional, for bias_diversity checks
    expectation:
      type: should_merge
      min_clusters: 1
      max_clusters: 1
      min_source_count: 3
      ...
    rationale: |
      ...

The loader flattens each article's `source: {slug, country, tier, ...}`
sub-dict into the flat fields cluster_stories() consumes:
`source_id`, `source_country`, `tier`, plus a kept `source` sub-dict for
downstream use.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def _flatten_article(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert a fixture-shape article into a cluster_stories()-shape article.

    Pulls `source.slug` -> `source_id`, `source.country` -> `source_country`,
    `source.tier` -> `tier`. Leaves the original `source` dict in place so
    fixtures can carry richer metadata (lean_baseline, name, etc.) for
    assertions that need it.
    """
    article = dict(raw)  # shallow copy
    src = article.get("source") or {}
    if isinstance(src, dict):
        article.setdefault("source_id", src.get("slug", ""))
        article.setdefault("source_country", src.get("country", ""))
        article.setdefault("tier", src.get("tier", ""))
    # Defensive defaults for fields cluster_stories() reads
    article.setdefault("title", "")
    article.setdefault("summary", "")
    article.setdefault("full_text", "")
    article.setdefault("published_at", "")
    article.setdefault("section", "")
    return article


def load_fixture(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Load a single YAML fixture file.

    Returns a dict with:
        id, name, failure_date, failure_kind, rationale,
        articles  (list of cluster_stories()-shape dicts)
        expectation (raw dict — passed to assertions.py)
    """
    p = Path(path)
    with open(p, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    articles_raw = raw.get("articles") or []
    if not isinstance(articles_raw, list):
        raise ValueError(f"{p.name}: 'articles' must be a list")

    articles = [_flatten_article(a) for a in articles_raw]

    expectation = raw.get("expectation") or {}
    if not isinstance(expectation, dict) or "type" not in expectation:
        raise ValueError(
            f"{p.name}: 'expectation' must be a dict with a 'type' key"
        )

    return {
        "id": raw.get("id") or p.stem,
        "name": raw.get("name", ""),
        "failure_date": raw.get("failure_date", ""),
        "failure_kind": raw.get("failure_kind", ""),
        "rationale": raw.get("rationale", ""),
        "articles": articles,
        "expectation": expectation,
        "_path": str(p),
    }


def load_fixtures(
    fixtures_dir: str | os.PathLike[str] | None = None,
) -> list[dict[str, Any]]:
    """Load every *.yaml under fixtures_dir, sorted by filename.

    Filename ordering keeps the report output stable and matches the
    numeric prefixes used in `001-*.yaml`, `002-*.yaml`, etc.
    """
    if fixtures_dir is None:
        fixtures_dir = Path(__file__).parent / "fixtures"
    p = Path(fixtures_dir)
    if not p.exists():
        return []

    out: list[dict[str, Any]] = []
    for fp in sorted(p.glob("*.yaml")):
        out.append(load_fixture(fp))
    return out
