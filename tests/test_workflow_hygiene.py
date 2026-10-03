#!/usr/bin/env python3
"""The workflows that decide what reaches production hold their own rules.

Rev 85 (WS-A, 2026-10-02). Every check here is a defect that shipped:

W-01  No cron on minute 0 or 30. GitHub's scheduler starts those shared
      minutes hours late: the 11:00 pipeline began 14:55 to 18:32 on runs
      #380 to #385, and the 15:00 and 17:00 deploy backstops ran at 20:10 and
      21:30 on 2026-10-01.
W-02  auto-merge-claude.yml refuses a branch that changes .github/. A claude/*
      push ran the workflow from its own commit with contents: write, so it
      could delete a gate and still merge (audit 5 H3). The refusal job runs
      first and is a `needs:` of the merge, the merge job re-checks before the
      merge step, and the refusal script is EXECUTED here against a throwaway
      repository both ways.
W-03  No attacker-chosen context (a branch name, a commit message, a PR or
      issue title or body) is pasted into a `run:` script. It goes through
      `env:` and is quoted. `${{ github.ref_name }}` sat in the merge script.
W-04  Every workflow declares `permissions:` (audit 5 L4: four did not, and
      inherited the repository default).
W-05  Every `tests/test_*.py` is run by some workflow, or is on ALLOWLIST with
      its reason. test_insecure_origins and test_lean_suite_discriminates were
      run by nothing.
W-06  The workflows that push data straight to main run the four gates
      pipeline.yml runs, before their push (weekly-digest and refresh-brief
      did not).
W-07  pipeline.yml dispatches the deploy after its data commit (P0-1), its
      checkout persists no token into the scrape step (audit 5 M1), and
      freshness-check.yml reads the LIVE page.
W-08  Retired schedules stay retired: db-cleanup has none; Pair Test and
      Anchor Pairs run once a day.
W-09  Every action is pinned to a 40-hex commit with its tag in a comment.

    python3 tests/test_workflow_hygiene.py
"""
from __future__ import annotations

import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
WF = ROOT / ".github" / "workflows"

# W-05: test files no workflow runs ON PURPOSE, each with its reason.
ALLOWLIST: dict[str, str] = {
    "test_corrections.py":
        "run from inside tests/test_grounding.py, which auto-merge-claude.yml "
        "and pipeline.yml (before the data commit) both run, so it guards the "
        "path that writes. Name it in a run: block when .github/ is next edited.",
}

FOUR_GATES = ("tests/test_grounding.py", "tests/test_bias_defaults_gate.py",
              "tests/test_feed_buildable.py", "tests/test_onair_sidecar.py")

# Contexts whose value is chosen by whoever pushes or opens something.
TAINTED = re.compile(
    r"\$\{\{\s*github\.(ref_name|head_ref|event\.head_commit\.[\w.]+|"
    r"event\.commits|event\.pull_request\.(title|body|head\.ref|head\.label)|"
    r"event\.issue\.(title|body)|event\.comment\.body|event\.review\.body)")

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'ok' if cond else 'FAIL'}] {name}" + (f": {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def load(path: pathlib.Path) -> dict:
    d = yaml.safe_load(path.read_text())
    # PyYAML reads the bare key `on` as boolean True.
    if True in d:
        d["on"] = d.pop(True)
    return d


workflows = {p.name: load(p) for p in sorted(WF.glob("*.yml"))}


def steps(d: dict):
    for jname, job in (d.get("jobs") or {}).items():
        for i, st in enumerate(job.get("steps") or []):
            yield jname, i, st


def run_text(st: dict) -> str:
    return st.get("run") or ""


def code_lines(text: str) -> str:
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))


def crons(d: dict) -> list[str]:
    on = d.get("on") or {}
    if not isinstance(on, dict):
        return []
    return [c["cron"] for c in (on.get("schedule") or []) if isinstance(c, dict) and "cron" in c]


def minutes(field: str) -> set[int]:
    out: set[int] = set()
    for part in field.split(","):
        step = 1
        if "/" in part:
            part, s = part.split("/")
            step = int(s)
        if part == "*":
            lo, hi = 0, 59
        elif "-" in part:
            lo, hi = (int(x) for x in part.split("-"))
        else:
            lo = hi = int(part)
            if step != 1:
                hi = 59
        out.update(range(lo, hi + 1, step))
    return out


# ---------------------------------------------------------------- W-01
all_crons = [(n, c) for n, d in workflows.items() for c in crons(d)]
check("W-01 workflows have crons to check", len(all_crons) > 0)
for name, c in all_crons:
    fields = c.replace("CRON_TZ=", "").split()
    m = minutes(fields[-5])
    check(f"W-01 {name} cron '{c}' avoids minute 0 and 30", not (m & {0, 30}),
          f"minutes {sorted(m & {0, 30})} are the shared, late-starting ones")

# ---------------------------------------------------------------- W-02
am = workflows["auto-merge-claude.yml"]
jobs = am["jobs"]
REFUSE_NAME = "Refuse to auto-merge a change to .github"


def is_refusal(st: dict) -> bool:
    t = run_text(st)
    return st.get("name") == REFUSE_NAME and "-- .github/" in t and "exit 1" in t


check("W-02 auto-merge has a merge-scope job", "merge-scope" in jobs)
scope_steps = jobs.get("merge-scope", {}).get("steps", [])
check("W-02 merge-scope runs the refusal step", any(is_refusal(s) for s in scope_steps))
check("W-02 merge-scope is listed FIRST", list(jobs)[0] == "merge-scope", str(list(jobs)))
merge_job = jobs.get("auto-merge", {})
needs = merge_job.get("needs") or []
needs = [needs] if isinstance(needs, str) else needs
check("W-02 the merge job needs merge-scope", "merge-scope" in needs, str(needs))
ms = merge_job.get("steps") or []
ref_i = next((i for i, s in enumerate(ms) if is_refusal(s)), None)
merge_i = next((i for i, s in enumerate(ms) if "git push origin main" in run_text(s)), None)
check("W-02 the merge job has a merge step", merge_i is not None)
check("W-02 the refusal step runs before the merge step",
      ref_i is not None and merge_i is not None and ref_i < merge_i, f"refusal {ref_i}, merge {merge_i}")
check("W-02 the merge merges the judged commit (GITHUB_SHA), not the moving branch tip",
      merge_i is not None and 'git merge "$GITHUB_SHA"' in run_text(ms[merge_i]))

# Execute the refusal script, both ways, against a throwaway origin.
script = next((run_text(s) for s in scope_steps if is_refusal(s)), "")
GIT = shutil.which("git")
if script and GIT:
    def g(cwd, *args):
        return subprocess.run([GIT, *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()

    def attempt(touch: str) -> subprocess.CompletedProcess:
        tmp = pathlib.Path(tempfile.mkdtemp(prefix="wsa-refuse-"))
        try:
            origin, work = tmp / "origin.git", tmp / "work"
            env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
            subprocess.run([GIT, "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
            g(origin, "config", "uploadpack.allowAnySHA1InWant", "true")
            subprocess.run([GIT, "clone", "-q", str(origin), str(work)], check=True, capture_output=True)
            (work / "README").write_text("x\n")
            subprocess.run([GIT, "add", "-A"], cwd=work, check=True, env=env)
            subprocess.run([GIT, "commit", "-qm", "base"], cwd=work, check=True, env=env)
            subprocess.run([GIT, "push", "-q", "origin", "HEAD:main"], cwd=work, check=True, env=env, capture_output=True)
            subprocess.run([GIT, "checkout", "-qb", "claude/t"], cwd=work, check=True, env=env)
            f = work / touch
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("changed\n")
            subprocess.run([GIT, "add", "-A"], cwd=work, check=True, env=env)
            subprocess.run([GIT, "commit", "-qm", "change"], cwd=work, check=True, env=env)
            subprocess.run([GIT, "push", "-q", "origin", "claude/t"], cwd=work, check=True, env=env, capture_output=True)
            sha = g(work, "rev-parse", "HEAD")
            return subprocess.run(["bash", "-c", script], cwd=work, capture_output=True, text=True,
                                  env={**env, "GITHUB_SHA": sha, "REF_NAME": "claude/t"}, timeout=60)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    p = attempt(".github/workflows/auto-merge-claude.yml")
    check("W-02 a branch changing .github/ is REFUSED", p.returncode != 0, p.stdout + p.stderr)
    check("W-02 the refusal tells a human to merge it by hand",
          "merge it by hand" in p.stdout and ".github/workflows/auto-merge-claude.yml" in p.stdout,
          p.stdout)
    p = attempt("frontend/app/page.tsx")
    check("W-02 a branch not touching .github/ passes the refusal step", p.returncode == 0,
          p.stdout + p.stderr)
else:
    check("W-02 refusal script found and git available to execute it", False)

# ---------------------------------------------------------------- W-03
tainted = [f"{name}:{jname}[{i}] {TAINTED.findall(run_text(st))}"
           for name, d in workflows.items() for jname, i, st in steps(d)
           if TAINTED.search(run_text(st))]
check("W-03 no ${{ github.ref_name }} / head_ref / event text inside any run: block",
      not tainted, "pass it through env: and quote it: " + "; ".join(tainted))

# ---------------------------------------------------------------- W-04
for name, d in workflows.items():
    check(f"W-04 {name} declares permissions", "permissions" in d)

# ---------------------------------------------------------------- W-05
ran = "\n".join(code_lines(run_text(st)) for d in workflows.values() for _, _, st in steps(d))
for t in sorted((ROOT / "tests").glob("test_*.py")):
    rel = f"tests/{t.name}"
    if t.name in ALLOWLIST:
        check(f"W-05 {rel} allowlisted with a reason", bool(ALLOWLIST[t.name].strip()))
        continue
    check(f"W-05 {rel} is run by a workflow", re.search(rf"{re.escape(rel)}\b", ran) is not None,
          "add it to a workflow's run: block, or to ALLOWLIST with the reason")
for stale in ALLOWLIST:
    check(f"W-05 allowlisted {stale} still exists", (ROOT / "tests" / stale).exists())

# ---------------------------------------------------------------- W-06
for name in ("pipeline.yml", "weekly-digest.yml", "refresh-brief.yml"):
    st = [s for _, _, s in steps(workflows[name])]
    push_i = next((i for i, s in enumerate(st) if re.search(r"\bpush origin\b", code_lines(run_text(s)))), None)
    gate_i = next((i for i, s in enumerate(st) if all(g_ in run_text(s) for g_ in FOUR_GATES)), None)
    check(f"W-06 {name} runs the four pre-commit gates before it pushes",
          push_i is not None and gate_i is not None and gate_i < push_i, f"gates {gate_i}, push {push_i}")

# ---------------------------------------------------------------- W-07
pl = workflows["pipeline.yml"]
pst = [s for _, _, s in steps(pl)]
commit_i = next((i for i, s in enumerate(pst) if s.get("id") == "commit"), None)
disp_i = next((i for i, s in enumerate(pst) if "gh workflow run deploy-cloudflare.yml" in run_text(s)), None)
check("W-07 pipeline.yml dispatches deploy-cloudflare.yml after its data commit",
      commit_i is not None and disp_i is not None and disp_i > commit_i, f"commit {commit_i}, dispatch {disp_i}")
check("W-07 the dispatch is the LAST step (after the engine floor)", disp_i == len(pst) - 1)
if disp_i is not None:
    cond = str(pst[disp_i].get("if", ""))
    check("W-07 the dispatch runs whenever the data reached main, floor or no floor",
          "always()" in cond and "steps.commit.outputs.pushed" in cond, cond)
check("W-07 pipeline.yml may dispatch (actions: write)",
      (pl.get("permissions") or {}).get("actions") == "write")
dep = workflows["deploy-cloudflare.yml"]
check("W-07 deploy-cloudflare.yml keeps its workflow_run on News Pipeline",
      "News Pipeline" in ((dep["on"].get("workflow_run") or {}).get("workflows") or []))
check("W-07 deploy-cloudflare.yml accepts the dispatch", "workflow_dispatch" in dep["on"])
co = next((s for s in pst if str(s.get("uses", "")).startswith("actions/checkout@")), {})
check("W-07 pipeline.yml checkout persists no token into the scrape step",
      (co.get("with") or {}).get("persist-credentials") is False)
fr = workflows["freshness-check.yml"]
ftext = "\n".join(run_text(s) for _, _, s in steps(fr))
check("W-07 freshness-check.yml reads the LIVE site", "news.voidvision.org" in str(fr))
check("W-07 freshness-check.yml holds the live page to 20 minutes after the data commit",
      'LIVE_DEADLINE_MIN: "20"' in (WF / "freshness-check.yml").read_text() and "git" in ftext)
check("W-07 freshness-check.yml runs after the pipeline",
      "News Pipeline" in ((fr["on"].get("workflow_run") or {}).get("workflows") or []))

# ---------------------------------------------------------------- W-08
check("W-08 db-cleanup.yml is unscheduled", not crons(workflows["db-cleanup.yml"]))
check("W-08 db-cleanup.yml keeps workflow_dispatch", "workflow_dispatch" in workflows["db-cleanup.yml"]["on"])
for n in ("pair-test.yml", "anchor-pairs.yml"):
    check(f"W-08 {n} runs once a day", len(crons(workflows[n])) == 1, str(crons(workflows[n])))

# ---------------------------------------------------------------- W-09
unpinned = [
    (p.name, m.group(1)) for p in sorted(WF.glob("*.yml")) for line in p.read_text().splitlines()
    if (m := re.match(r"\s*-?\s*uses:\s*(\S+)(.*)", line)) and not m.group(1).startswith("./")
    and not (re.fullmatch(r"[0-9a-f]{40}", m.group(1).split("@")[-1]) and re.search(r"#\s*v\d", m.group(2)))
]
check("W-09 every action is pinned to a commit SHA", not unpinned, str(unpinned[:5]))

# ---------------------------------------------------------------- repo files
check("CODEOWNERS covers .github/", re.search(r"^/\.github/\s+@aacrit", (ROOT / ".github/CODEOWNERS").read_text(), re.M) is not None)
dbot = yaml.safe_load((ROOT / ".github/dependabot.yml").read_text())
eco = {(u["package-ecosystem"], u["directory"]) for u in dbot.get("updates", [])}
for want in (("npm", "/frontend"), ("npm", "/worker"), ("pip", "/pipeline"), ("github-actions", "/")):
    check(f"dependabot covers {want[0]} in {want[1]}", want in eco)

if failures:
    print(f"\nFAIL: {len(failures)} check(s)")
    sys.exit(1)
print(f"\nPASS  workflow hygiene: {len(workflows)} workflows, {len(all_crons)} crons, "
      "merge refusal executed both ways, every test file run")
