#!/bin/bash
# Void News session start.
#
# TWO JOBS, both learned from 2026-09-23.
#
# 1. INSTALL THE ENVIRONMENT THE GATES NEED. Nine CI gates had never once
#    executed because the job installed `nltk pyyaml` and they import requests,
#    bs4, numpy, scikit-learn, textblob and the spaCy model. The same gap makes
#    a session unable to run the checks it is about to rely on.
#
# 2. SAY WHETHER main IS GREEN, BEFORE ANY WORK STARTS. On 2026-09-23 the site
#    served two-day-old data and 37 finished commits sat behind a red main, and
#    it took hours to notice, because nothing said so. `main` is production
#    (deploy-cloudflare.yml serves from it and nothing else), so a red main is
#    everyone's problem the moment it happens, not the next time someone looks.
#
# Never fails the session. Every network call is guarded: a hook that blocks
# startup because GitHub was slow is worse than no hook.
set -uo pipefail

ROOT="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$ROOT" || exit 0

say() { printf '%s\n' "$*"; }

# ---- 1. the environment ----------------------------------------------------
# Idempotent by checking first: pip install over a satisfied requirements file
# still takes ~20s of resolution, and this runs on every session start.
missing=$(python3 - <<'PY' 2>/dev/null
import importlib.util as u
need = {"requests": "requests", "bs4": "beautifulsoup4", "numpy": "numpy",
        "sklearn": "scikit-learn", "textblob": "textblob", "spacy": "spacy",
        "nltk": "nltk", "yaml": "pyyaml", "feedparser": "feedparser"}
print(" ".join(p for m, p in need.items() if u.find_spec(m) is None))
PY
)
if [ -n "${missing// /}" ]; then
  say "[void] installing the pipeline environment (missing: $missing)"
  pip install --quiet -r pipeline/requirements.txt 2>&1 | tail -3
else
  say "[void] python environment already satisfied"
fi

if ! python3 -c "import spacy; spacy.load('en_core_web_sm')" >/dev/null 2>&1; then
  say "[void] downloading spaCy model en_core_web_sm"
  python3 -m spacy download en_core_web_sm >/dev/null 2>&1 \
    || say "[void] WARNING: spaCy model download failed; bias gates will not run"
fi

# ---- 2. is main green, and is this branch behind it? -----------------------
say ""
git fetch --quiet origin main 2>/dev/null

behind=$(git rev-list --count HEAD..origin/main 2>/dev/null || echo "?")
ahead=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo "?")
say "[void] main: $(git log --oneline -1 origin/main 2>/dev/null || echo unknown)"
say "[void] this branch: $ahead ahead, $behind behind origin/main"

slug=$(git remote get-url origin 2>/dev/null \
       | sed -E 's#.*github\.com[:/]([^/]+/[^/.]+)(\.git)?$#\1#')
if [ -n "$slug" ]; then
  api="https://api.github.com/repos/$slug/actions/runs?branch=main&per_page=8"
  runs=$(curl -sS --max-time 12 -H 'Accept: application/vnd.github+json' "$api" 2>/dev/null)
  if [ -n "$runs" ]; then
    python3 - "$runs" <<'PY' 2>/dev/null || true
import json, sys
try:
    d = json.loads(sys.argv[1])
except Exception:
    sys.exit(0)
runs = d.get("workflow_runs") or []
if not runs:
    sys.exit(0)
seen, bad = {}, []
for r in runs:                      # newest first; keep one per workflow
    n = r.get("name")
    if n in seen:
        continue
    seen[n] = r.get("conclusion") or r.get("status")
    # `skipped` is a conditional workflow declining to run (Alert on Failure
    # only fires when something failed), and `cancelled` is usually a superseded
    # run. Neither is a red main, and reporting them as one trains people to
    # ignore the warning, which is how a real failure gets missed.
    if seen[n] not in ("success", "skipped", "cancelled", "in_progress",
                       "queued", "neutral", None):
        bad.append(f'{n}: {seen[n]}')
if bad:
    print("[void] *** main IS NOT GREEN ***")
    for b in bad:
        print(f"[void]     {b}")
    print("[void] main is production. Per CLAUDE.md, a red main is fixed")
    print("[void] BEFORE any new work: a commit not on main is not live, and")
    print("[void] every branch inherits main's data, so this blocks everyone.")
else:
    print(f"[void] main is green ({len(seen)} workflow(s) checked)")
PY
  else
    say "[void] could not reach the GitHub API; main's CI state unknown"
  fi
fi
say ""
exit 0
