# Media on R2

Void's binaries do not belong in git. `.git` is 379 MB, `frontend/public/audio`
is 71 MB in the working tree, and `archive.json` is 20 MB rewritten by **every**
pipeline run. Git binaries cannot be un-committed cleanly, so the cost of
waiting only compounds: `docs/HISTORY-AUDIO.md` picked R2 for the 78-episode
History catalogue on exactly this reasoning and asked for the move *before* the
catalogue was staged.

This is the runbook for that move. The code is already merged and inert: with
the R2 variables unset, every path behaves exactly as it does today.

## The one rule

**One hostname, one place.** `VOID_MEDIA_BASE` is the public custom domain bound
to the bucket, and every media url on the site is `VOID_MEDIA_BASE + "/" + key`.
Nothing else knows where media lives. Moving buckets, or moving off R2 entirely,
is a change to that one string plus a re-upload.

`pipeline/utils/media.py` is the only module that talks to R2. Its `enabled()`
requires **both** a base and credentials, because a base without credentials
would write urls for objects nobody uploaded: the pages would look correct and
serve nothing. A failed upload **raises** rather than returning a url, for the
same reason.

## What moves

| Payload | Key | Cache | Was |
|---|---|---|---|
| Daily brief / Weekly episodes | `audio/<edition>/<date>-<slot>.mp3` | immutable | `frontend/public/audio/`, committed |
| History episodes | `audio/history/<slug>.mp3` | immutable | same |
| History images | `img/history/<sha1>.<ext>` | immutable | hotlinked from Wikimedia |
| Printed archive | `data/archive/latest.json` | 5 min | `frontend/build-data/archive.json`, committed |

Image keys are the **sha1 of the bytes**. That is not a detail: re-running the
mirror uploads only what actually changed, and a url whose name *is* its content
can be cached for a year with no purge story.

## Setting it up

1. **Create the bucket.** Cloudflare dashboard → R2 → Create bucket, e.g.
   `void-media`.
2. **Bind a custom domain.** R2 → the bucket → Settings → Public access → Custom
   domain, e.g. `media.voidvision.org`. This is the step that matters: a custom
   domain gets free egress and CDN caching, while the `r2.dev` url is rate
   limited and Cloudflare says not to use it in production.
3. **Create an R2 API token** (Object Read & Write, scoped to the bucket).
4. **Set them in the repository:**

   | Where | Name | Value |
   |---|---|---|
   | Variables | `VOID_MEDIA_BASE` | `https://media.voidvision.org` (no trailing slash) |
   | Secrets | `R2_ACCOUNT_ID` | Cloudflare account id |
   | Secrets | `R2_BUCKET` | `void-media` |
   | Secrets | `R2_ACCESS_KEY_ID` | token key |
   | Secrets | `R2_SECRET_ACCESS_KEY` | token secret |

   `VOID_MEDIA_BASE` is a **variable**, not a secret: it is a public hostname
   that appears in served HTML, and making it a secret would only mean it got
   scrubbed out of the logs where it is useful.

## Migrating, in the order that stays recoverable

Every step is additive and re-runnable. Nothing is deleted from git until the
urls are confirmed live.

1. **Dry run the images.** Actions → *Media → R2* → `images-dry-run`. It lists
   what it would upload and touches nothing. Expect ~245 files.
2. **Mirror the images.** Same workflow, `images`. It downloads each verified
   Commons thumbnail, uploads it under its content hash, records the url in
   `data/history/commons_media.json`, re-emits `history.json` and commits.
   An image that fails keeps its Wikimedia url and still works.
3. **Let one pipeline run write audio and the archive.** With the variables set,
   the daily run uploads the brief to R2 and writes `archive.pointer.json`
   instead of the 20 MB `archive.json`. Nothing else changes.
4. **Confirm the served site.** `python scripts/verify_sections.py
   https://news.voidvision.org/` checks that every image url is on an allowed
   host and that a sample really returns bytes.
5. **Only then, the cutover commit.** Remove the now-unreferenced binaries:

   ```
   git rm -r --cached frontend/public/audio
   git rm --cached frontend/build-data/archive.json
   ```

   This is the irreversible-feeling step, and it is deliberately last. It only
   removes files from the *tip*; the history keeps its copy either way, so the
   repo does not shrink until a history rewrite, which is a separate decision.

## How the build reads the archive

`frontend/app/lib/archive.ts` prefers a committed `build-data/archive.json` and
falls back to `build-data/archive.pointer.json`, which names the R2 url. It
fetches that once per build and caches it in the temp directory, because Next
runs `generateStaticParams`, `generateMetadata` and the page render in separate
worker processes, and without the cache a build fetched the 20 MB file four
times.

**A pointer that cannot be fetched fails the build.** That is deliberate. The
archive is the source of every `/story/<id>/` permalink, so returning an empty
list would publish a site that had silently dropped 1,557 pages while reporting
success. A failed build is recoverable; that deploy is not.

## Rolling back

Unset `VOID_MEDIA_BASE`. Every writer goes back to committed files on the next
run, and every reader still resolves the R2 urls already in the manifests, so
the site keeps working while the next run refills the repo. To go further,
delete the `cdn` field from `data/history/commons_media.json` and re-emit: the
images fall back to their Wikimedia urls, which never stopped being valid.

## Gates

- `tests/test_media_r2.py` — the media layer keeps its promise: configured or
  not but never half, content-addressed keys, and a failed upload raises instead
  of handing back a url to nothing. Runs against a mocked S3, skips if moto is
  absent.
- `tests/test_history_audio.py` — an episode lives either in the deploy or in
  R2, never both, and never in a third shape.
- `scripts/verify_sections.py` H-03 — against the live site: every image url is
  on Wikimedia or Void's own media host, carries a free licence, and a sample
  actually returns image bytes.
