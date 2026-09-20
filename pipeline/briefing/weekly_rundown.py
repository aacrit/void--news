"""Write the Sunday rundown for "The Argument" from a PUBLISHED weekly issue.

One Gemini call over the issue that already exists. It is not a second
editorial pass: every fact, every column and every number is already written
and already on the page, and this turns that page into a running order for
three voices.

THE ONE INSTRUCTION THAT MATTERS is that the bench SELECTS rather than
paraphrases. `weekly_script.W-01` checks every `L:` and `R:` line against that
column's published text by word overlap, so a script that summarises the
argument in its own words does not render. That is H-01 (History's quotation
rule) applied to argument instead of archive, and it is what makes the show's
core content unfabricatable.

The old weekly audio path is the counter-example this replaces: one call
writing free `A:`/`B:` dialogue, a prompt that FORBADE segment markers ("NO
[SEGMENT] headers. Raw dialogue only."), and therefore no timeline, no
chapters and no per-segment music, ever.
"""

from __future__ import annotations

import re

from briefing.weekly_script import (
    KINDS, TARGET_MINUTES, parse_script, validate_script, estimated_minutes,
)

SYSTEM = """You are the editor of Void Weekly, writing the running order for
The Argument: the magazine's Sunday audio edition, read by three voices.

    E  the Editor. Speaks for Void. Carries the spine of the programme, the
       datelines, the numbers, the editorial and the close.
    L  the left bench.   R  the right bench.
       They ONLY argue, and they ONLY speak inside their own column.

THE ONE RULE YOU CANNOT BREAK. Every L: and R: line must be SELECTED from the
columnist's published essay, which is given to you below in full. Cut it for
the ear: drop a clause, end a sentence early, take three sentences that sit
apart and set them together. Do not rewrite, do not paraphrase, do not add a
word the column does not contain. A line that is not in the column is rejected
automatically and the episode does not render.

WRITE FOR THE EAR. One idea a sentence. Present tense. Attribution before the
claim. Numbers as words. No quotation marks: attribute in words instead, because
a synthesiser reads a quotation mark as nothing and the listener hears an
unattributed claim.

VOID'S OWN LINES ONLY. Never "up first", "and finally", "stay with us",
"welcome back", "thanks for listening", "let's dive in". No host names, no
reactions, no banter. Two voices agreeing that something is interesting is the
sound of a podcast, and this is not one.

OUTPUT FORMAT — plain text, no JSON, no Markdown. Segment markers exactly:

## OPEN
E: the week in one image. Not a list of headlines. Three or four sentences.
## CONTENTS
E: four lines, one per movement. Open with: Inside this week.
## COVER
E: the lead feature, told as reporting. Five or six paragraphs' worth.
## DATELINE
E: one beat naming a day and a count. "Tuesday. Thirteen sources." Nothing else.
## COVER
E: the rest of the feature.
## TOPIC
E: name the story the two columns argue about, once, then get out of the way.
## LEFT
L: the left column, selected, unbroken.
## RIGHT
R: the right column, selected, unbroken.
## REST
## TURN
E: what EACH side leaves out. Both, never one. At least eighty words. Engage
   both columns by name of argument, not by calling them left and right.
## SECOND
E: the second feature, shorter.
## DEPARTMENT | <label>
E: one department, sixty to ninety seconds.
## NUMBERS
E: The Week in Bias, read as measurement. Use only figures given below.
## EDITORIAL
E: Void's own argued column, about four minutes.
## CLOSE
E: the question the week leaves open. End on the question mark.
## SAY
Nuuk = NOOK

A REST marker carries no lines: it is a held pause the listener needs.
Target {LO:.0f} to {HI:.0f} minutes, which is about {WORDS_LO} to {WORDS_HI} words."""


def _block(label: str, text: str, limit: int = 6000) -> str:
    return f"\n\n=== {label} ===\n{(text or '').strip()[:limit]}"


def build_prompt(issue: dict) -> str:
    """Everything the rundown is allowed to draw on, and nothing else."""
    from briefing.weekly_script import _bench_columns

    covers = [c for c in (issue.get("cover_text") or []) if isinstance(c, dict)]
    opinions = [o for o in (issue.get("opinions") or []) if isinstance(o, dict)]
    cols = _bench_columns(opinions)
    depts = [d for d in (issue.get("departments") or []) if isinstance(d, dict)]
    stats = ((issue.get("bias_report_data") or {}).get("stats") or {})

    parts = [f"Issue #{issue.get('issue_number')}, week of {issue.get('week_start')}."]
    for i, c in enumerate(covers[:2]):
        parts.append(_block(f"COVER FEATURE {i + 1}: {c.get('headline', '')}", c.get("text")))
        for e in (c.get("timeline") or [])[:8]:
            parts.append(f"\n  {e.get('date')}: {e.get('title')} "
                         f"({e.get('source_count')} sources)")
        if c.get("days_active"):
            parts.append(f"\n  ran {c['days_active']} days across "
                         f"{c.get('week_sources')} sources")
    # The columns go in VERBATIM and in full: the bench selects from these, so
    # a truncated column is a column the bench cannot legally quote from.
    parts.append(_block("THE LEFT COLUMN, verbatim", cols.get("L", ""), 12000))
    parts.append(_block("THE RIGHT COLUMN, verbatim", cols.get("R", ""), 12000))
    for d in depts[:2]:
        parts.append(_block(f"DEPARTMENT {d.get('label', '')}: {d.get('headline', '')}",
                            d.get("text"), 4000))
    if stats:
        parts.append("\n\n=== THE NUMBERS (use no figure that is not here) ===\n"
                     + "\n".join(f"  {k}: {v}" for k, v in stats.items()))
    parts.append(_block("VOID'S OWN EDITORIAL, verbatim", issue.get("opinion_text"), 8000))
    return "".join(parts)


def generate(issue: dict, generate_text) -> tuple[str | None, list, int]:
    """Write and validate the rundown. Returns (script_text, findings, calls).

    One regeneration NAMING the findings, mirroring the editorial pass and
    Stage 2 before it. `generate_text(prompt, system_instruction=...)` is
    injected so this module stays importable and testable without a key.
    """
    lo, hi = TARGET_MINUTES
    system = SYSTEM.format(LO=lo, HI=hi,
                           WORDS_LO=int(lo * 163), WORDS_HI=int(hi * 163))
    prompt = build_prompt(issue)
    best, best_fails, calls = None, None, 0

    for attempt in range(2):
        raw = generate_text(
            prompt if attempt == 0 else prompt + _retry(best_fails),
            system_instruction=system,
        )
        calls += 1
        if not raw:
            if attempt:
                break
            best_fails = [_F("the model returned nothing")]
            continue
        script = parse_script(raw, issue.get("edition") or "world")
        findings = validate_script(script, issue)
        fails = [f for f in findings if f.level == "fail"]
        if not fails:
            return raw, findings, calls
        if best is None or len(fails) < len(best_fails or []):
            best, best_fails = raw, fails
        if attempt == 0:
            print(f"    [rundown] {len(fails)} failure(s) — regenerating")
    # A rundown with failures is NOT returned for rendering: unlike an essay
    # that merely runs long, a bench line the column does not contain is words
    # put in a columnist's mouth. The caller falls back to the legacy path.
    return None, (best_fails or []), calls


class _F:
    def __init__(self, detail):
        self.id, self.level, self.segment, self.detail = "W-00", "fail", "ALL", detail


def _retry(findings) -> str:
    named = " ".join(f"({i + 1}) [{f.id} {f.segment}] {f.detail}"
                     for i, f in enumerate(findings or []))
    return ("\n\nYour previous rundown was rejected by the validators. "
            + named
            + " Rewrite the whole rundown fixing every point. "
              "Remember that L: and R: lines must be taken FROM the columns above, "
              "word for word, cut but never reworded.")


def word_target() -> tuple[int, int]:
    lo, hi = TARGET_MINUTES
    return int(lo * 163), int(hi * 163)
