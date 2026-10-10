"""Cut what the gate would confirm as wrong, so the rest of the edition ships.

Rule 1 says silence beats a plausible reconstruction. Until 2026-10-04 the
pipeline enforced that by holding back the WHOLE day: `audit_grounding.py`
(F-1) ran before the data commit and one confirmed finding on one shipped
card failed the run. Run #389 did exactly that. Two of thirty-five cards
carried a real error ("On October 4, 2026" for an attempt the card's own
points put on Saturday, October 3; a point giving a plunge of "18,000 feet"
that none of the 34 fetchable sources carries, six of which say 16,625), and
readers got yesterday's paper instead of today's.

CEO decision 2026-10-04: cut and publish. The export now does what a copy
desk does with a line it cannot stand behind: it cuts that line and prints
the rest. The verdict is the gate's own, `rigor.audit_text` against the
committed index, and only a CONFIRMED finding cuts, never "cannot confirm"
or "advisory": the index has to cover everything the writer could have read
before its silence counts as absence, so a cut never removes a sentence
merely because the evidence for it was not kept.

  a summary sentence with a confirmed finding   the sentence is cut
  a point with a confirmed finding              the point is cut
  anything still failing after the cuts (a      nothing more: the gate holds
    head, a finding that needs the whole        the edition, as before
    summary, a summary the cuts would empty)
  nothing confirmed                             nothing changes

A card is never pulled from the feed. Removing one moves an unprinted story
up into the twenty, and that story has no /story/ page (measured on the
editorial-stage harness: two displayed cards with no permalink). A wrong
head is rare and is not a line a copy desk can cut, so it stays a stop.

Every copy is cut: feed.json, the latest archive rows, and the state
database (story_clusters, printed_stories), so the next export cannot put
the line back. Each cut is recorded in build-data/cuts.json (Void's own card
text, never publisher prose). Nothing is ever written in a cut line's place.

The gate still runs afterwards and still fails on anything left, so a defect
in this module cannot ship an error; it can only fail to save the edition.
tests/test_cut_confirmed.py plants each case.
"""
from __future__ import annotations

import json
import pathlib
import re
import sqlite3

CUTS_NAME = "cuts.json"


def _mods():
    from pipeline.editorial import grounding as G
    from pipeline.validation import rigor
    return G, rigor


def _confirmed(findings: list[dict]) -> list[dict]:
    return [f for f in findings if f.get("status") == "confirmed"]


def _sentences(text: str) -> list[str]:
    """The editorial standard's own splitter, the one E-13 and E-16 read."""
    from pipeline.editorial import standard as std
    return [s for s in std.sentences(text or "") if s.strip()]


def remove_sentence(text: str, sent: str) -> str:
    """`text` without `sent` and the spaces after it; paragraph breaks kept."""
    i = (text or "").find(sent)
    if i < 0:
        return text
    j = i + len(sent)
    while j < len(text) and text[j] == " ":
        j += 1
    out = text[:i] + text[j:]
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def plan_card(c: dict, build: pathlib.Path, fresh: bool | None) -> dict | None:
    """What to cut from one card, or None when the gate confirms nothing."""
    G, rigor = _mods()
    report = rigor.audit_cluster(c, build, fresh)
    found = _confirmed(report["findings"])
    if not found:
        return None
    rec = rigor.load_record(build, str(c.get("id") or ""))
    v = G.Verifier(rec) if rec else None
    state = report["state"]
    summary = c.get("summary") or ""

    cut_points: list[dict] = []
    points = rigor.points_of(c)
    for f in found:
        m = re.match(r"point (\d+)$", f["where"])
        if m and int(m.group(1)) < len(points):
            cut_points.append({"text": points[int(m.group(1))], "rule": f["rule"],
                               "message": f["message"]})

    cut_sents: list[dict] = []
    if any(f["where"] == "card" for f in found):
        for s in _sentences(summary):
            hits = _confirmed(rigor.audit_text("", s, v, where="card", state=state))
            if hits:
                cut_sents.append({"text": s, "rule": hits[0]["rule"],
                                  "message": hits[0]["message"]})

    new_summary = summary
    for s in cut_sents:
        new_summary = remove_sentence(new_summary, s["text"])
    gone = {p["text"] for p in cut_points}
    after = dict(c, summary=new_summary)
    for k in ("consensus_points", "divergence_points"):
        val = c.get(k) or []
        if isinstance(val, list):
            after[k] = [p for p in val if str(p) not in gone]
    left = _confirmed(rigor.audit_cluster(after, build, fresh)["findings"])
    if not new_summary.strip():
        # Every sentence failed: there is no card left to print, and printing
        # an empty one is not a cut. Leave it for the gate to hold.
        new_summary, cut_sents = summary, []
    return {
        "id": c.get("id"),
        "title": c.get("title") or "",
        "summary": new_summary,
        "consensus_points": after.get("consensus_points"),
        "divergence_points": after.get("divergence_points"),
        "sentences": cut_sents,
        "points": cut_points,
        "left": [f["message"] for f in left],
    }


def plan(feed: dict, build: pathlib.Path, fresh_ids: set[str] | None) -> list[dict]:
    out = []
    for c in feed.get("clusters") or []:
        f = None if fresh_ids is None else (c.get("id") in fresh_ids)
        p = plan_card(c, build, f)
        if p:
            out.append(p)
    return out


def _apply_text(row: dict, p: dict) -> bool:
    """Apply a plan's removals to another copy of the card. True if changed."""
    changed = False
    s = row.get("summary") or ""
    for cut in p["sentences"]:
        t = remove_sentence(s, cut["text"])
        if t != s:
            s, changed = t, True
    if "summary" in row:
        row["summary"] = s
    gone = {q["text"] for q in p["points"]}
    for k in ("consensus_points", "divergence_points"):
        v = row.get(k)
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except ValueError:
                continue
        if isinstance(v, list) and any(str(x) in gone for x in v):
            row[k] = [x for x in v if str(x) not in gone]
            changed = True
    return changed


def _write_json(path: pathlib.Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def apply(build: pathlib.Path, plans: list[dict], db: str | None = None,
          built_at: str | None = None) -> dict:
    """Write the plans into every copy. Returns what was done."""
    done = {"cards_cut": 0, "sentences": 0, "points": 0, "left": 0,
            "archive_rows": 0, "db_rows": 0}
    plans = [p for p in plans if p["sentences"] or p["points"] or p["left"]]
    if not plans:
        return done
    by_id = {p["id"]: p for p in plans}

    feed_path = build / "feed.json"
    feed = json.loads(feed_path.read_text(encoding="utf-8"))
    kept = []
    for c in feed.get("clusters") or []:
        p = by_id.get(c.get("id"))
        if not p:
            kept.append(c)
            continue
        done["left"] += bool(p["left"])
        if not (p["sentences"] or p["points"]):
            kept.append(c)
            continue
        c["summary"] = p["summary"]
        c["consensus_points"] = p["consensus_points"]
        c["divergence_points"] = p["divergence_points"]
        done["cards_cut"] += 1
        done["sentences"] += len(p["sentences"])
        done["points"] += len(p["points"])
        kept.append(c)
    feed["clusters"] = kept
    _write_json(feed_path, feed)

    arch_path = build / "archive.json"
    latest = ""
    if arch_path.exists():
        arch = json.loads(arch_path.read_text(encoding="utf-8"))
        latest = max((r.get("printed_on") or "" for r in arch), default="")
        rows = []
        for r in arch:
            p = by_id.get(r.get("source_cluster_id"))
            if p and r.get("printed_on") == latest:
                if _apply_text(r, p):
                    done["archive_rows"] += 1
            rows.append(r)
        _write_json(arch_path, rows)

    if db and pathlib.Path(db).exists():
        con = sqlite3.connect(db)
        con.row_factory = sqlite3.Row
        try:
            for p in plans:
                for table, key, by_day in (("story_clusters", "id", False),
                                           ("printed_stories", "source_cluster_id", True)):
                    sql = f"SELECT rowid AS _r, * FROM {table} WHERE {key} = ?"
                    args = [p["id"]]
                    if by_day and latest:
                        sql += " AND printed_on = ?"
                        args.append(latest)
                    try:
                        rows = con.execute(sql, args).fetchall()
                    except sqlite3.OperationalError:
                        continue
                    for row in rows:
                        d = {k: row[k] for k in row.keys()}
                        if not _apply_text(d, p):
                            continue
                        sets = {}
                        for k in ("summary", "consensus_points", "divergence_points"):
                            if k in row.keys():
                                val = d[k]
                                sets[k] = val if isinstance(val, (str, type(None))) \
                                    else json.dumps(val, ensure_ascii=False)
                        con.execute(
                            f"UPDATE {table} SET " + ", ".join(f"{k} = ?" for k in sets)
                            + " WHERE rowid = ?", [*sets.values(), row["_r"]])
                        done["db_rows"] += 1
            con.commit()
        finally:
            con.close()

    _write_json(build / CUTS_NAME, {
        "builtAt": built_at,
        "rule": "a sentence or point the grounding gate confirms as wrong is cut; "
                "nothing is written in its place",
        "cards": [{k: p[k] for k in ("id", "title", "sentences", "points", "left")}
                  for p in plans],
    })
    return done


def run(build: pathlib.Path, db: str | None = None) -> dict:
    """Plan and apply against the emitted feed. Prints one line per cut."""
    _, rigor = _mods()
    build = pathlib.Path(build)
    feed_path = build / "feed.json"
    if not feed_path.exists():
        return {}
    feed = json.loads(feed_path.read_text(encoding="utf-8"))
    fresh = rigor.fresh_ids(rigor.run_counters(build, feed.get("builtAt")))
    plans = plan(feed, build, fresh)
    for p in plans:
        for s in p["sentences"]:
            print(f"  [rule 1 cut] {str(p['id'])[:8]} sentence ({s['rule']}): \"{s['text'][:100]}\"")
        for q in p["points"]:
            print(f"  [rule 1 cut] {str(p['id'])[:8]} point ({q['rule']}): \"{q['text'][:100]}\"")
        for m in p["left"]:
            print(f"  [rule 1 NOT CUTTABLE] {str(p['id'])[:8]} the gate will hold the edition: {m[:120]}")
    done = apply(build, plans, db, feed.get("builtAt"))
    if plans:
        print(f"rule 1 cuts: {done['sentences']} sentence(s) and {done['points']} point(s) "
              f"cut from {done['cards_cut']} card(s); {done['left']} card(s) not cuttable; "
              f"{done['archive_rows']} archive row(s) and {done['db_rows']} database row(s) rewritten")
    else:
        print("rule 1 cuts: nothing the gate would confirm")
    return done
