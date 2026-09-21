#!/usr/bin/env python3
"""Every production prompt carries the grounding sentence, and no prompt calls
the product by its terminal name.

    python tests/test_prompt_grounding.py

CLAUDE.md says: "Every LLM prompt carries: 'Every fact MUST appear in the
provided articles. Do not supplement with prior knowledge.'" On 2026-09-21
that was true of two prompts. Nine production prompts had no grounding
sentence of any kind, and the daily Opinion, one of the nine, told readers
about "autocrats in Beijing, Moscow, and Riyadh" that no article in its
112-article cluster mentioned (brand audit F-04). The line had been added to
the prompts that write news and never to the ones that write argument.

This test reads each module's SOURCE, because the generators cannot be
imported without a key or a database, and asserts the sentence is inside
every prompt block, so CLAUDE.md's claim is true by construction. The Opinion
prompts must also forbid the historical parallel, since a grounded model
still reaches for one.

stdlib only, no key, no network.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPE = ROOT / "pipeline"

GROUNDING = ("Every fact MUST appear in the provided articles. "
             "Do not supplement with prior knowledge.")
ARGUE = ("Historical parallels, other countries and 'patterns' are not permitted "
         "unless a provided article states them.")

# (module, prompt constant, must also carry the argue-only line)
PROMPTS = [
    ("briefing/daily_brief_generator.py", "_SYSTEM_INSTRUCTION", False),
    ("briefing/daily_brief_generator.py", "_OPINION_SYSTEM_INSTRUCTION", True),
    ("briefing/daily_brief_generator.py", "_OPINION_USER_PROMPT", False),
    ("briefing/weekly_digest_generator.py", "COVER_SYSTEM", False),
    ("briefing/weekly_digest_generator.py", "OPINION_SYSTEM", True),
    ("briefing/weekly_digest_generator.py", "TECH_SYSTEM", False),
    ("briefing/weekly_digest_generator.py", "SPORTS_SYSTEM", False),
    ("briefing/weekly_digest_generator.py", "RECAP_SYSTEM", False),
    ("briefing/weekly_digest_generator.py", "AUDIO_SYSTEM", False),
    ("briefing/weekly_digest_generator.py", "_WEEKLY_OPINION_SYSTEM", True),
    ("briefing/weekly_digest_generator.py", "_WEEKLY_OPINION_PROMPT", False),
    ("briefing/weekly_digest_generator.py", "_WEEKLY_OPINION_AUDIO_PROMPT", False),
    ("briefing/weekly_rundown.py", "SYSTEM", False),
    ("briefing/radio_script_generator.py", "_SYSTEM", False),
    ("summarizer/cluster_summarizer.py", "_SYSTEM_INSTRUCTION", False),
]

# Exempt from the exact sentence, each with its reason:
#   history/audio_script_generator.py _HISTORY_SYSTEM_INSTRUCTION: its inputs
#     are event data, not articles, so the sentence would be false about its
#     own inputs (Rule 1). It carries the equivalent with the right noun,
#     asserted below.
#   analyzers/gemini_reasoning.py: parked behind DISABLE_GEMINI_REASONING; no
#     production caller writes copy from it.
#   memory/live_poller.py: reads the decommissioned Supabase; its output
#     reaches nothing that is served.
#   social/ig_caption.py: a manual bundle that is never posted.
HISTORY = ("history/audio_script_generator.py", "_HISTORY_SYSTEM_INSTRUCTION",
           "Do not supplement with outside knowledge.")

# Prompt strings in these modules must not call the product "void --news",
# "void --weekly", "void --history", "void --onair" or "void --opinion": the
# masthead says "Void News" (brand audit F-11). Docstrings, comments, prints
# and argparse text are operator-facing and are not prompts.
NO_TERMINAL_NAME = [
    "briefing/daily_brief_generator.py",
    "briefing/weekly_digest_generator.py",
    "briefing/weekly_rundown.py",
    "briefing/radio_script_generator.py",
    "summarizer/cluster_summarizer.py",
    "history/audio_script_generator.py",
]

failures: list[str] = []


def check(ok: bool, msg: str) -> None:
    print(f"  [{'ok' if ok else 'FAIL'}] {msg}")
    if not ok:
        failures.append(msg)


def prompt_block(src: str, name: str) -> str | None:
    m = re.search(r'^' + re.escape(name) + r' = f?"""(.*?)"""', src, re.M | re.S)
    return m.group(1) if m else None


def flatten(block: str) -> str:
    """A backslash before a newline is a line continuation inside the literal."""
    return block.replace("\\\n", "")


def prompt_text_lines(src: str) -> list[str]:
    """Source lines that can hold prompt text: not the module docstring, not
    comments, not prints or argparse descriptions."""
    body = re.sub(r'\A(?:#[^\n]*\n|\s)*"""(.*?)"""', "", src, count=1, flags=re.S)
    out = []
    for line in body.split("\n"):
        s = line.strip()
        if s.startswith("#") or "print(" in s or "description=" in s:
            continue
        out.append(line)
    return out


def main() -> int:
    print("prompt grounding")
    for rel, name, argue in PROMPTS:
        src = (PIPE / rel).read_text(encoding="utf-8")
        block = prompt_block(src, name)
        check(block is not None, f"{rel}: {name} found")
        if block is None:
            continue
        flat = flatten(block)
        check(GROUNDING in flat, f"{rel}: {name} carries the grounding sentence")
        if argue:
            check(ARGUE in flat, f"{rel}: {name} forbids unsourced parallels and patterns")

    rel, name, equiv = HISTORY
    block = prompt_block((PIPE / rel).read_text(encoding="utf-8"), name)
    check(block is not None and equiv in flatten(block),
          f"{rel}: {name} carries the event-data equivalent")

    print("\nproduct name in prompts")
    for rel in NO_TERMINAL_NAME:
        src = (PIPE / rel).read_text(encoding="utf-8")
        hits = [line.strip()[:80] for line in prompt_text_lines(src) if "void --" in line]
        check(not hits, f"{rel}: no prompt string says 'void --'"
              + (f" (first: {hits[0]!r})" if hits else ""))

    print("\nthe check itself")
    # Planted defects: a prompt without the sentence, and one with the old name.
    planted = 'X = """You are the editorial voice of void --news.\nWrite well.\n"""\n'
    check(GROUNDING not in flatten(prompt_block(planted, "X") or ""),
          "a prompt without the sentence is caught")
    check(any("void --" in line for line in prompt_text_lines(planted)),
          "a prompt naming void --news is caught")
    check(not any("void --" in line for line in prompt_text_lines(
        '"""Module for void --news."""\n# void --news comment\nprint("void --news")\n')),
          "docstrings, comments and prints are not prompts")

    if failures:
        print(f"\n{len(failures)} FAILED")
        return 1
    print("\ntest_prompt_grounding: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
