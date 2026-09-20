"""Render "The Argument" from a COMMITTED script and the PUBLISHED issue.

No Gemini. No database. No regenerated prose.

WHY THIS EXISTS. `gemini-2.5-flash` is capped at 20 requests a DAY, shared with
the daily pipeline, which spends about thirteen of them. A weekly run costs
three or four more. That is fine once. It is not fine when the audio needs a
second attempt, because re-running the generator to fix the SHOW would rewrite
every essay that was already correct, at full flash cost, to change nothing a
reader sees.

It is also how History works, and for the same reason. Rev 70 decided that 78
documentary scripts would be AUTHORED and committed rather than generated,
because four days of budget is not a sensible price for prose a person can
write better. The weekly rundown is the same object: one script, one issue,
re-renderable forever at zero cost.

So the audio has its own entry point. It reads the issue that is already
published, reads a script from `data/weekly/scripts/<week_start>.txt`,
validates the one against the other, renders, and writes the result back into
the deploy tree — which is the archive of record, exactly as
`repair_weekly_snapshot` treats it.

    python -m pipeline.briefing.render_weekly_audio            # latest issue
    python -m pipeline.briefing.render_weekly_audio --week 2026-09-14
    python -m pipeline.briefing.render_weekly_audio --dry-run  # validate only
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "pipeline") not in sys.path:
    sys.path.insert(0, str(REPO / "pipeline"))

SCRIPTS = REPO / "data" / "weekly" / "scripts"
WEEKLY = REPO / "frontend" / "public" / "data" / "weekly.json"
ISSUES = REPO / "frontend" / "build-data" / "weekly-issues.json"


def _load_issue(week: str | None):
    """The published issue, from the deploy tree rather than the database.

    The weekly job restores the Actions cache and never saves it back, so the
    row it writes dies with the container. `build-data/weekly-issues.json` is
    the only durable copy, which makes it the right input here.
    """
    if not WEEKLY.exists():
        raise SystemExit(f"no published issue at {WEEKLY}")
    latest = json.loads(WEEKLY.read_text(encoding="utf-8"))
    if week is None or latest.get("week_start") == week:
        return latest, WEEKLY
    rows = json.loads(ISSUES.read_text(encoding="utf-8")) if ISSUES.exists() else []
    for row in rows:
        if isinstance(row, dict) and row.get("week_start") == week:
            return row, ISSUES
    raise SystemExit(f"no published issue for week {week}")


def _write_back(issue: dict, rendered: dict, url: str) -> list[str]:
    """Put the audio fields on every copy of the issue that a page reads.

    Three files carry an issue and they must agree: weekly.json is the latest
    snapshot, weekly-issues.json is the archive the pages prerender from, and
    weekly-archive.json is the summary index. A renderer that updated one of
    them would leave the page playing an older episode than the one it just
    made.
    """
    fields = {
        "audio_url": url,
        "audio_duration_seconds": round(rendered["seconds"], 1),
        "audio_file_size": rendered["bytes"],
        "audio_chapters": rendered["chapters"],
        "audio_voice": "kokoro:" + "+".join(
            rendered["voices"][k] for k in ("editor", "left", "right")
        ),
        "audio_voice_label": "Three voices",
        # The Editor reads the editorial, so the opinion is a CHAPTER rather
        # than a seek offset. The rail supersedes the two-tab split.
        "opinion_start_seconds": next(
            (c["startTime"] for c in rendered["chapters"] if c["kind"] == "editorial"),
            None,
        ),
    }
    week = issue.get("week_start")
    touched = []

    for path in (WEEKLY, ISSUES,
                 REPO / "frontend" / "public" / "data" / "weekly-archive.json"):
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else [data]
        hit = False
        for row in rows:
            if isinstance(row, dict) and row.get("week_start") == week:
                # The summary index carries only a few of these keys; writing
                # the rest into it would invent columns it does not have.
                for k, v in fields.items():
                    if isinstance(data, list) and path.name == "weekly-archive.json" \
                            and k not in ("audio_url", "audio_duration_seconds"):
                        continue
                    row[k] = v
                hit = True
        if hit:
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            touched.append(path.name)
    return touched


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--week", help="week_start; defaults to the published latest")
    ap.add_argument("--script", help="path to the rundown; defaults to data/weekly/scripts/<week>.txt")
    ap.add_argument("--dry-run", action="store_true", help="validate and stop")
    a = ap.parse_args()

    issue, src = _load_issue(a.week)
    week = issue.get("week_start")
    print(f"issue #{issue.get('issue_number')} ({week}) from {src.name}")

    path = Path(a.script) if a.script else SCRIPTS / f"{week}.txt"
    if not path.exists():
        raise SystemExit(f"no script at {path}")
    text = path.read_text(encoding="utf-8")
    print(f"script {path.relative_to(REPO)}")

    from briefing.weekly_script import parse_script, validate_script, estimated_minutes
    from briefing.weekly_producer import VOICES

    script = parse_script(text, issue.get("edition") or "world")
    findings = validate_script(script, issue, VOICES)
    minutes, wpm = estimated_minutes(script, VOICES)
    print(f"{script.words} words, about {minutes:.1f} min at {wpm:.0f} wpm")
    for f in findings:
        print(f"  {f.id} {f.level:4} [{f.segment}] {f.detail[:110]}")
    fails = [f for f in findings if f.level == "fail"]
    if fails:
        print(f"{len(fails)} failure(s); not rendering")
        return 1
    if a.dry_run:
        print("dry run: the script is valid against the published issue")
        return 0

    from briefing.weekly_producer import produce
    from briefing.audio_producer import _write_audio_static

    out = Path(tempfile.mkdtemp(prefix="void-weekly-audio-"))
    rendered = produce(text, issue, out, stem="weekly")
    if not rendered:
        print("render failed")
        return 1

    mp3 = Path(rendered["path"])
    sidecar = Path(rendered["sidecar"])
    url = _write_audio_static(
        mp3.read_bytes(), f"weekly-{issue.get('edition') or 'world'}",
        # The key is a SUFFIX, not a filename: `_write_audio_static`
        # writes f"{stem}{suffix}", so passing `sidecar.name` here
        # produced `2026-09-20-pmweekly.chapters.json` and a
        # `latestweekly.chapters.json` beside it. Every other caller
        # passes the suffix (radio_producer.py:1195).
        sidecars={".chapters.json": sidecar.read_bytes()},
    )
    if not url:
        print("could not write the audio into the deploy tree")
        return 1

    touched = _write_back(issue, rendered, url)
    print(f"{url}  ({rendered['bytes']/1e6:.1f} MB, {rendered['seconds']:.0f}s, "
          f"{len(rendered['chapters'])} chapters)")
    print("updated: " + ", ".join(touched))
    return 0


if __name__ == "__main__":
    sys.exit(main())
