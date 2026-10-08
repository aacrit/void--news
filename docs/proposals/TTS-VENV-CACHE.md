# The TTS venv cache can restore a venv with no interpreter

**Status:** proposal, needs a hand merge (it changes `.github/`, which no
`claude/*` branch may auto-merge).

## What happened

On 2026-10-07, `auto-merge-claude.yml` → `radio-audio` → "Kokoro timing bench"
failed twice on runs that changed nothing near audio (runs 37708287170 and
37713663687), each time with:

    [bench] kokoro: available=False (no .venv-tts interpreter (VOID_KOKORO_PYTHON))

Both times the cache step reported a hit, so "Build TTS venv (cache miss)" was
skipped, and both times a re-run of the failed job passed.

## Why (most likely; not reproduced)

Six workflows restore `.venv-tts` under one key:

    key: venv-tts-py3.11-${{ hashFiles('pipeline/requirements-tts.txt') }}

`auto-merge-claude.yml`, `pipeline.yml`, `refresh-brief.yml`,
`render-history-audio.yml`, `stitch-promos.yml`, `weekly-digest.yml`.

A venv's `bin/python` is a symlink into the interpreter that built it
(`/opt/hostedtoolcache/Python/3.11.<patch>/x64/bin/python3.11`). The key names
the minor version only, so a venv built under one 3.11 patch is restored on a
runner whose `setup-python` installed another, and the symlink dangles. The
cache step cannot see that; it only compares keys. Run 37708287170's runner had
3.11.17.

The same restore feeds `pipeline.yml`, whose On Air render reads the same
`VOID_KOKORO_PYTHON`. A dangling venv there would turn up as a Kokoro-unavailable
render on the daily path.

## Fix (same two edits in all six workflows)

1. Key on the exact interpreter. Give the `setup-python` step an `id` and use its
   output:

   ```yaml
   - uses: actions/setup-python@<pinned sha>
     id: py
     with:
       python-version: '3.11'
   ...
   - name: Cache TTS venv
     id: tts-venv
     uses: actions/cache@<pinned sha>
     with:
       path: .venv-tts
       key: venv-tts-py${{ steps.py.outputs.python-version }}-${{ hashFiles('pipeline/requirements-tts.txt') }}
   ```

2. Build when the restored venv cannot run, not only on a key miss:

   ```yaml
   - name: Build TTS venv (cache miss or broken restore)
     run: |
       if ! .venv-tts/bin/python -c 'import sys' 2>/dev/null; then
         rm -rf .venv-tts
         python -m venv .venv-tts
         .venv-tts/bin/pip install -q -r pipeline/requirements-tts.txt
       fi
   ```

Edit 1 stops the mismatch; edit 2 makes any other broken restore heal itself
instead of failing a gate. `tests/test_workflow_hygiene.py` still has to pass
(no new unpinned action, `permissions:` unchanged).
