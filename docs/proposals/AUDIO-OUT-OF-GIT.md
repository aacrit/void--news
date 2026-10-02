# On Air and Weekly audio out of git

Rev 85, WS-H, plan item P2-2. Status: the pipeline side is merged behind a flag
that defaults OFF. Turning it on needs the workflow change below, which WS-A owns.

## Why

688 MB of the repository's 743 MB pack is 67 MP3 blobs. Every On Air episode
(6 to 11 MB) and every Weekly episode (11 to 22 MB) adds to it, and git keeps
every byte of every render forever: 11 to 22 MB a day, 4 to 8 GB a year.
History audio already left git on 2026-09-21 for a GitHub Release that the
deploy pulls into the publish directory (`pipeline/history/release_store.py`).
This applies the same pattern to `frontend/public/audio/world/` (On Air) and
`frontend/public/audio/weekly-world/` (The Argument).

The release is a STORE, never a CDN. GitHub serves release assets as
`application/octet-stream` behind a signed redirect that expires in an hour,
which plays in Chrome and fails in iOS Safari. The deploy copies the bytes into
the site, so readers keep fetching `/audio/world/latest.mp3` from
news.voidvision.org: same origin, correct MIME, no redirect.

## What is merged

`pipeline/briefing/audio_store.py`, called from
`audio_producer._write_audio_static` (the one writer both programmes use) and
from `podcast_feed_generator.generate_podcast_feeds`.

| `VOID_AUDIO_STORE` | Behaviour |
|---|---|
| `git` (default) | Exactly as before. The module does nothing. |
| `release` | Before writing, the edition's stored back catalogue is pulled into the tree (so the two-file rotation and the podcast feed see yesterday's episode in a fresh checkout). After writing, the dated MP3 is uploaded to the release `<edition>-audio` (asset `<edition>--<file>.mp3`) and recorded in `frontend/public/data/audio-store.json` with its URL, size and SHA-256; `latest.mp3` is recorded as an alias of the dated file. Files the rotation removed leave the manifest and the release. If the upload fails, the writer returns no URL: an episode that is not in the store will not be deployed, so the brief must not point at it. |

Deploy side: `python -m pipeline.briefing.audio_store fetch --out DIR` writes
every manifest file and alias under `DIR/<edition>/`, checks each against its
SHA-256, and exits 1 on a miss or a mismatch. `verify --root DIR` checks a tree.

Gate: `tests/test_audio_store.py` (off by default, manifest hash equals the
bytes, a failed upload publishes no URL, the fetch refuses a tampered or
missing asset, rotation leaves the store, a committed manifest is well formed).
Add it to `auto-merge-claude.yml` with the switch-over.

## Why the flag is OFF

Turning it on alone would only add an upload. Three things must change at once:

1. The deploy must pull the stored files into `frontend/out/audio/` before the
   Pages upload, or every Listen button 404s.
2. The pipeline and weekly jobs need `GITHUB_TOKEN` in the step environment to
   write release assets (both already have `contents: write`).
3. The MP3 paths must leave the index, or `git add frontend/public/audio`
   keeps committing them. Removing them from the index is not removing them
   from history: the existing blobs stay, as the plan requires.

## The switch-over

Apply in one commit, after WS-A's workflow branch has merged.

### 1. `.gitignore`

```diff
 frontend/public/audio/history/*.mp3
+# On Air and Weekly MP3s live in the <edition>-audio releases (P2-2,
+# docs/proposals/AUDIO-OUT-OF-GIT.md); the manifest is
+# frontend/public/data/audio-store.json. Sidecars stay in git.
+frontend/public/audio/world/*.mp3
+frontend/public/audio/weekly-*/*.mp3
```

### 2. Seed the store, then untrack (run once, by hand, with a token)

```bash
export GITHUB_TOKEN=...            # contents: write on aacrit/void--news
python3 - <<'PY'
import sys; sys.path.insert(0, "pipeline")
from pathlib import Path
from briefing import audio_store as st
root = Path("frontend/public/audio")
for ed in ("world", "weekly-world"):
    dated = sorted((root / ed).glob("20??-??-??-??.mp3"))
    for i, f in enumerate(dated):
        st.record(ed, f.name, f.read_bytes(), alias="latest.mp3" if i == len(dated) - 1 else None)
PY
python3 -m pipeline.briefing.audio_store verify --root frontend/public/audio
git rm --cached frontend/public/audio/world/*.mp3 frontend/public/audio/weekly-world/*.mp3
git add .gitignore frontend/public/data/audio-store.json
```

The verify must print nothing before the `git rm`. `latest.mp3` must be
byte-identical to the newest dated file for the alias to hold; the verify
catches it if not.

### 3. `.github/workflows/pipeline.yml`, step "Run pipeline"

```diff
       - name: Run pipeline
         env:
           PYTHONUNBUFFERED: "1"
           VOID_SQLITE_PATH: pipeline_state.db
           VOID_PHRASE_DB: phrase_counts.db
           GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
+          # On Air MP3s go to the world-audio release, not git (P2-2).
+          VOID_AUDIO_STORE: release
+          GITHUB_TOKEN: ${{ github.token }}
```

The commit step needs no change: `git add frontend/public/audio` now skips the
ignored MP3s and still adds the sidecars, and `audio-store.json` is under
`frontend/public/data`, which the allowed-paths check already admits.

### 4. `.github/workflows/weekly-digest.yml`, both rendering steps

```diff
       - name: Render The Argument from the committed script
         if: inputs.mode == 'audio-only'
         env:
           PYTHONUNBUFFERED: "1"
           VOID_SQLITE_PATH: pipeline_state.db
           VOID_TTS_ENGINE: kokoro
           VOID_KOKORO_PYTHON: .venv-tts/bin/python
+          VOID_AUDIO_STORE: release
+          GITHUB_TOKEN: ${{ github.token }}
         run: python -m pipeline.briefing.render_weekly_audio
```

```diff
       - name: Generate weekly digest
         env:
           PYTHONUNBUFFERED: "1"
           VOID_SQLITE_PATH: pipeline_state.db
           GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
+          VOID_AUDIO_STORE: release
+          GITHUB_TOKEN: ${{ github.token }}
```

and add the manifest to its commit list, which is an explicit glob:

```diff
           git add frontend/public/data/weekly.json \
                   frontend/public/data/weekly-archive.json \
+                  frontend/public/data/audio-store.json \
                   frontend/build-data/weekly-issues.json \
                   frontend/public/audio/weekly-* \
                   frontend/public/podcast-weekly.xml || true
```

and to its allowed-paths `case` (beside `frontend/public/audio/weekly-*`):

```diff
-                frontend/public/data/weekly*.json|frontend/build-data/weekly-issues.json|frontend/public/audio/weekly-*|frontend/public/podcast-weekly.xml) ;;
+                frontend/public/data/weekly*.json|frontend/public/data/audio-store.json|frontend/build-data/weekly-issues.json|frontend/public/audio/weekly-*|frontend/public/podcast-weekly.xml) ;;
```

### 5. `.github/workflows/deploy-cloudflare.yml`, after the History pull

```diff
       - name: Pull History audio into the publish directory
         if: steps.guard.outputs.skip != 'true'
         run: python3 pipeline/history/release_store.py fetch --out frontend/out/audio/history
+
+      # On Air and Weekly audio are not in git either (P2-2). Every file the
+      # manifest lists is pulled in and checked against its SHA-256; a miss or
+      # a mismatch FAILS the deploy, as the History pull does.
+      - name: Pull On Air and Weekly audio into the publish directory
+        if: steps.guard.outputs.skip != 'true'
+        run: python3 -m pipeline.briefing.audio_store fetch --out frontend/out/audio
```

### 6. `.github/workflows/auto-merge-claude.yml`

Add `python tests/test_audio_store.py` beside `tests/test_onair_sidecar.py`.

## Checks after the first live run

- `curl -sI https://news.voidvision.org/audio/world/latest.mp3` returns 200
  with `content-type: audio/mpeg`.
- `python3 -m pipeline.briefing.audio_store verify --root frontend/out/audio`
  in the deploy log printed nothing.
- `git count-objects -vH` on a fresh clone stops growing by the size of an
  episode a day.
- `tests/test_onair_sidecar.py` S-01 compares `latest.chapters.json` against
  the served MP3. After the switch the MP3 is not in the checkout, so S-01 and
  S-02 must read the manifest's alias instead of hashing a local file; that edit
  belongs with this switch-over, and WS-A or the owner of the sidecar test makes
  it.

## Rollback

Set `VOID_AUDIO_STORE: git` (or delete the line), delete the two `.gitignore`
lines, and the next run commits its MP3 as before. The manifest and the
release stay; the deploy step keeps working as long as the manifest is current,
so remove step 5 in the same commit.
