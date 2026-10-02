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
  # A Debian-installed PyYAML (6.0.1, distutils) cannot be uninstalled by pip,
  # so `pip install -r` died on "Cannot uninstall PyYAML" and installed
  # nothing after it (audit 3 item 6). Install the pinned PyYAML over it
  # first, without uninstalling, then the rest.
  pyyaml_pin=$(grep -iE '^pyyaml' pipeline/requirements.txt | head -1 | sed 's/[[:space:]]*#.*//')
  pip install --quiet --ignore-installed "${pyyaml_pin:-pyyaml~=6.0.2}" >/dev/null 2>&1 \
    || say "[void] WARNING: could not install ${pyyaml_pin:-pyyaml}"
  if ! out=$(pip install --quiet -r pipeline/requirements.txt 2>&1); then
    say "[void] WARNING: pip install -r pipeline/requirements.txt failed; gates that import it will not run:"
    printf '%s\n' "$out" | tail -3 | sed 's/^/[void]     /'
  fi
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
# One call PER WORKFLOW (audit 3 item 6). A single repo-wide per_page=8 call
# was mostly Pair Test and Anchor Pairs and usually missed the pipeline. The
# responses go to ci_status.py on STDIN as one JSON object, never as argv, and
# it judges each workflow by its newest COMPLETED run that was not skipped or
# cancelled, so a newer skipped run cannot mask an older failure.
# auto-merge-claude runs on claude/* branches, so it is read without the
# branch filter.
if [ -n "$slug" ] && [[ "$slug" != *"/"*"/"* ]]; then
  tmp=$(mktemp -d 2>/dev/null || echo "/tmp/void-ci-$$")
  mkdir -p "$tmp"
  for wf in pipeline.yml verify-production.yml freshness-check.yml deploy-cloudflare.yml auto-merge-claude.yml; do
    q="branch=main&per_page=20"
    [ "$wf" = "auto-merge-claude.yml" ] && q="per_page=20"
    curl -sS --max-time 10 -H 'Accept: application/vnd.github+json' \
      "https://api.github.com/repos/$slug/actions/workflows/$wf/runs?$q" \
      -o "$tmp/$wf.json" 2>/dev/null || rm -f "$tmp/$wf.json"
  done
  {
    printf '{'
    for wf in pipeline.yml verify-production.yml freshness-check.yml deploy-cloudflare.yml auto-merge-claude.yml; do
      printf '"%s":' "$wf"
      if [ -s "$tmp/$wf.json" ] && python3 -c 'import json,sys; json.load(open(sys.argv[1]))' "$tmp/$wf.json" 2>/dev/null; then
        cat "$tmp/$wf.json"
      else
        printf 'null'
      fi
      printf ','
    done
    printf '"_end":null}'
  } | python3 "$ROOT/.claude/hooks/ci_status.py" \
    || say "[void] could not judge main's CI state"
  rm -rf "$tmp"
else
  say "[void] no GitHub remote; main's CI state unknown"
fi
say ""
exit 0
