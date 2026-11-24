"""Wikimedia Commons upload paths, derived rather than typed.

A Commons original lives at

    https://upload.wikimedia.org/wikipedia/commons/<h>/<hh>/<File_name>

where `hh` is the first two hex digits of md5(<File_name>) with spaces as
underscores, and `h` the first of them. Four thesis exhibits shipped broken
on 2026-10-02 because their hash directories were typed by hand
(scramble-for-africa's Afrikakonferenz, Colonial_Africa_1913_map and
MutilatedChildrenFromCongo; cambodian-genocide's Choeungek2): each file name
was right and each path was another file's, so the browser drew nothing.

`upload_url()` is what `export_thesis.py` serves, and `hash_problem()` is
T-22 in `thesis_checks.py` and the served-JSON scan in
`tests/test_history_thesis.py`.
"""
from __future__ import annotations

import hashlib
import re
import urllib.parse

UPLOAD_RE = re.compile(
    r"https://upload\.wikimedia\.org/wikipedia/commons/(thumb/)?([0-9a-f])/([0-9a-f]{2})/([^/?#\s\"']+)")


def file_name(value: str | None) -> str | None:
    """The Commons file name in an accession ("File:X"), a file page URL or an
    upload URL, with spaces as underscores; None if the value names none."""
    v = str(value or "").strip()
    if not v:
        return None
    m = UPLOAD_RE.search(v)
    if m:
        name = m.group(4)
    elif "commons.wikimedia.org/wiki/File:" in v:
        name = v.split("commons.wikimedia.org/wiki/File:", 1)[1].split("?")[0].split("#")[0]
    elif v.startswith("File:"):
        name = v[len("File:"):]
    else:
        return None
    return urllib.parse.unquote(name).replace(" ", "_")


def hash_dirs(name: str) -> tuple[str, str]:
    h = hashlib.md5(name.replace(" ", "_").encode("utf-8")).hexdigest()
    return h[0], h[:2]


def upload_url(name: str) -> str:
    """The original's URL for a Commons file name, its hash path computed."""
    name = name.replace(" ", "_")
    a, ab = hash_dirs(name)
    return (f"https://upload.wikimedia.org/wikipedia/commons/{a}/{ab}/"
            + urllib.parse.quote(name, safe="!$&'*+;=@_.~-"))


def hash_problem(url: str) -> str | None:
    """None if every Commons upload path in `url` sits under md5(its own file
    name); otherwise what the path should have been."""
    for m in UPLOAD_RE.finditer(url or ""):
        name = urllib.parse.unquote(m.group(4)).replace(" ", "_")
        want = hash_dirs(name)
        if (m.group(2), m.group(3)) != want:
            return (f"{name} is filed under {m.group(2)}/{m.group(3)}; md5 puts it under "
                    f"{want[0]}/{want[1]}")
    return None
