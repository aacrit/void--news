"""The text a card was written from, kept so it can be checked later.

E-13 and E-14 read a card against its sources. Both can only run where those
sources still exist, and until now they did not: `articles.full_text` lives in
`pipeline_state.db`, which is gitignored and dies with the Actions cache, while
`deepdive/<id>.json` keeps only each source's RSS snippet, often under a
hundred characters.

That gap is why the 2026-09-20 feed audit could not resolve two of its findings
either way. No audit can confirm or refute a claim against evidence nobody
kept. This module writes the evidence down at export time, into
`frontend/build-data/grounding/`, which the repo commits and the site does not
serve.

Each article's text is capped, because a handful of scraped pages run to
hundreds of kilobytes and the repo carries every run forever. A cap that went
unrecorded would be worse than no cap at all: an auditor would read a number's
absence as fabrication when it was merely cut off. So every record carries
`truncated`, and a reader that sees it set must not conclude "ungrounded" from
this file alone. That is the same defect the Weekly shipped by publishing
`.limit(500)` as an exact count.
"""
from __future__ import annotations

import json
import pathlib
from typing import Any

# Long enough for the body of essentially every news article; short enough that
# a scraped page carrying a site's whole archive cannot bloat the run.
PER_ARTICLE_CHARS = 24_000

DIRNAME = "grounding"


def build_record(cluster_id: str, articles: list[dict[str, Any]]) -> dict[str, Any]:
    """One cluster's sources, as much of each as the cap allows."""
    rows: list[dict[str, Any]] = []
    for a in articles or []:
        text = " ".join(
            str(a.get(k)) for k in ("title", "summary", "full_text") if a.get(k)
        ).strip()
        cut = len(text) > PER_ARTICLE_CHARS
        rows.append({
            "id": a.get("id"),
            "url": a.get("url"),
            "chars": len(text),
            "truncated": cut,
            "text": text[:PER_ARTICLE_CHARS],
        })
    return {
        "cluster": cluster_id,
        "perArticleChars": PER_ARTICLE_CHARS,
        "truncated": any(r["truncated"] for r in rows),
        "articles": rows,
    }


def write_record(build_dir: pathlib.Path, record: dict[str, Any]) -> pathlib.Path:
    out = pathlib.Path(build_dir) / DIRNAME
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{record['cluster']}.json"
    path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return path


def load_source_text(build_dir: pathlib.Path, cluster_id: str) -> tuple[str, bool]:
    """The concatenated source text for a cluster, and whether any was cut.

    Returns ("", False) when no record exists. A caller running E-13 or E-14
    must skip rather than accuse on an empty result, and must treat a True
    second value as "cannot conclude absence" rather than as evidence.
    """
    path = pathlib.Path(build_dir) / DIRNAME / f"{cluster_id}.json"
    if not path.exists():
        return "", False
    rec = json.loads(path.read_text(encoding="utf-8"))
    blob = " ".join(r.get("text") or "" for r in rec.get("articles") or [])
    return blob, bool(rec.get("truncated"))
