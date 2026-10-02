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

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPE = ROOT / "pipeline"
sys.path.insert(0, str(PIPE))
from utils.prohibited_terms import find_prohibited  # noqa: E402

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


# ---------------------------------------------------------------------------
# Kill-list words in copy the CODE writes (P1-6, audit 1 item 13).
#
# The rule-based fallbacks in pipeline/main.py wrote "Sources show significant
# differences in political framing", "notably more sensational" and
# "Single-source coverage \u2014 no cross-source comparison" into
# divergence_points, and those strings were served on archived Deep Dives. No
# model wrote them, so no output sanitizer ever read them. This scans every
# string literal a reader could be served from pipeline/main.py and
# pipeline/briefing/*.py.
#
# Not copy, and skipped: docstrings and bare string statements, arguments to
# print/log/regex/argparse/exception calls, constants whose NAME says they are
# instructions to a model or a term list (prompts quote the banned words in
# order to ban them), set literals, comparison operands, and tuples or lists
# made wholly of short terms (a ban list). Everything else is held to the kill
# list. Dashes are held in pipeline/main.py and in the named published
# fallbacks only, because the audio-script literals in briefing/ keep their
# dashes as TTS breath marks (CLAUDE.md, "No em dashes", exception).
# ---------------------------------------------------------------------------
_NOT_COPY_NAME = re.compile(
    r"(SYSTEM|PROMPT|INSTRUCTION|TERMS|WORDS|BANNED|BORROWED|_RE$|PATTERN|SLOP|"
    r"KILL|RULES|GUIDE|TEMPLATE|EXAMPLE|PROFILE|PERSONA|VOICE|FOCUS|SCENE|"
    r"STYLE|DIRECTION|SUFFIX)", re.I)
_NOT_COPY_CALL = frozenset({
    "print", "write", "warn", "warning", "info", "debug", "error", "exception",
    "add_argument", "ArgumentParser", "compile", "search", "sub", "match",
    "findall", "finditer", "fullmatch", "split", "replace", "_log", "log",
    "exit", "RuntimeError", "ValueError", "Exception", "SystemExit",
    "KeyError", "TypeError", "join", "startswith", "endswith", "strip",
    "rstrip", "lstrip", "count", "find", "rfind", "index",
})


def _is_term_list(node) -> bool:
    elts = getattr(node, "elts", None) or []
    return bool(elts) and all(
        isinstance(e, ast.Constant) and isinstance(e.value, str)
        and len(e.value.split()) <= 5 for e in elts)


def copy_literals(src: str):
    """(lineno, text) for every string literal that can reach a reader."""
    out: list[tuple[int, str]] = []

    def visit(node, assigned: str = "") -> None:
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            body = list(node.body)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                body = body[1:]
            for child in ast.iter_child_nodes(node):
                if child in node.body and child not in body:
                    continue
                visit(child)
            return
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            return
        if isinstance(node, ast.Call):
            f = node.func
            name = (f.id if isinstance(f, ast.Name)
                    else f.attr if isinstance(f, ast.Attribute) else "")
            if name in _NOT_COPY_CALL:
                return
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            names = [t.id if isinstance(t, ast.Name)
                     else t.attr if isinstance(t, ast.Attribute) else ""
                     for t in targets]
            if any(_NOT_COPY_NAME.search(n or "") for n in names):
                return
        if isinstance(node, (ast.Set, ast.Compare)):
            return
        if isinstance(node, (ast.Tuple, ast.List)) and _is_term_list(node):
            return
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append((node.lineno, node.value))
            return
        for child in ast.iter_child_nodes(node):
            visit(child)

    visit(ast.parse(src))
    return out


COPY_FILES = [PIPE / "main.py"] + sorted((PIPE / "briefing").glob("*.py"))
DASH_FILES = {PIPE / "main.py"}
# Published fallbacks outside main.py that must carry no dash either.
DASH_NAMED = [("briefing/daily_brief_generator.py", "Daily brief unavailable")]
_DASH = re.compile("[\u2014\u2013]")

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

    print("\nkill list in code-written copy (main.py, briefing/*.py)")
    for path in COPY_FILES:
        rel = path.relative_to(PIPE)
        lits = copy_literals(path.read_text(encoding="utf-8"))
        hits = [(n, t) for n, t in lits if find_prohibited(t)]
        check(not hits, f"{rel}: no kill-list word in a copy literal"
              + (f" (line {hits[0][0]}: {find_prohibited(hits[0][1])} in "
                 f"{hits[0][1][:60]!r})" if hits else ""))
        if path in DASH_FILES:
            dashes = [(n, t) for n, t in lits if _DASH.search(t)]
            check(not dashes, f"{rel}: no dash in a copy literal"
                  + (f" (line {dashes[0][0]}: {dashes[0][1][:60]!r})" if dashes else ""))
    for rel, needle in DASH_NAMED:
        lits = copy_literals((PIPE / rel).read_text(encoding="utf-8"))
        bad = [t for _, t in lits if needle in t and _DASH.search(t)]
        check(not bad, f"{rel}: the published fallback {needle!r} carries no dash")

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
    planted_copy = (
        '"""Docstring: significant is allowed here."""\n'
        'X_PROMPT = "Never write significant."\n'
        'def f():\n'
        '    print("significant in a log line")\n'
        '    return ["Sources show significant differences in framing",\n'
        '            "Single-source coverage \u2014 nothing to compare"]\n')
    lits = copy_literals(planted_copy)
    check(any(find_prohibited(t) for _, t in lits),
          "a kill-list word in a returned fallback string is caught")
    check(any(_DASH.search(t) for _, t in lits),
          "a dash in a returned fallback string is caught")
    check(not any("Docstring" in t or "Never write" in t or "log line" in t
                  for _, t in lits),
          "docstrings, prompts and log lines are not copy")

    if failures:
        print(f"\n{len(failures)} FAILED")
        return 1
    print("\ntest_prompt_grounding: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
