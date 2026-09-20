"""Where Void's binaries live: Cloudflare R2, behind one configured hostname.

The repo carries the site's data, which works for JSON and does not work for
media. `.git` is already 379 MB, the audio directory alone is 71 MB, and
archive.json is 20 MB rewritten EVERY pipeline run. Git binaries cannot be
un-committed cleanly, so each day of delay makes the move more expensive;
docs/HISTORY-AUDIO.md picked R2 for the 78-episode catalogue for exactly this
reason and asked for the move before the catalogue was staged.

One hostname, one place. `VOID_MEDIA_BASE` is the public custom domain bound to
the bucket, and every url on the site is `MEDIA_BASE + "/" + key`. Nothing else
knows where media lives: moving buckets, or moving off R2 entirely, is a change
to that one string and a re-upload.

CONFIGURED OR NOT, NEVER HALF. When the R2 variables are absent, `enabled()` is
False and every caller keeps its existing local-file behaviour unchanged. That
is what makes this safe to land before the bucket exists: the switch is turning
the variables on, not merging the code.

    VOID_MEDIA_BASE        https://media.voidvision.org   (no trailing slash)
    R2_ACCOUNT_ID          Cloudflare account id
    R2_BUCKET              bucket name
    R2_ACCESS_KEY_ID       R2 API token key
    R2_SECRET_ACCESS_KEY   R2 API token secret

Keys are structured so the CDN can cache correctly:

    audio/<edition>/<stem>.mp3        episodes; immutable once written
    audio/history/<slug>.mp3          History editions
    img/history/<sha1>.<ext>          content-addressed, cacheable forever
    data/archive/latest.json          rewritten daily, short cache

A content-addressed image key is not a detail: it means re-running the uploader
never re-uploads a byte that has not changed, and a url can be cached for a year
without a purge story.
"""

from __future__ import annotations

import hashlib
import os
import threading

# Cache policy per prefix. An image keyed by its own hash can never change
# behind its url, so it gets the maximum; the archive is rewritten every run.
IMMUTABLE = "public, max-age=31536000, immutable"
DAILY = "public, max-age=300, s-maxage=3600"

_client = None
_client_lock = threading.Lock()


def media_base() -> str:
    return (os.environ.get("VOID_MEDIA_BASE") or "").rstrip("/")


def _creds() -> tuple[str, str, str, str] | None:
    account = os.environ.get("R2_ACCOUNT_ID") or ""
    bucket = os.environ.get("R2_BUCKET") or ""
    key = os.environ.get("R2_ACCESS_KEY_ID") or ""
    secret = os.environ.get("R2_SECRET_ACCESS_KEY") or ""
    if account and bucket and key and secret:
        return account, bucket, key, secret
    return None


def enabled() -> bool:
    """True only when media can be BOTH uploaded and linked.

    Both halves are required. A base with no credentials would write urls to
    objects that were never uploaded, which is worse than not moving at all:
    the pages would look correct and serve nothing.
    """
    return bool(media_base() and _creds())


def url(key: str) -> str:
    """The public url for a key. Raises when unconfigured, rather than guessing."""
    base = media_base()
    if not base:
        raise RuntimeError("VOID_MEDIA_BASE is not set; no public url exists for media")
    return f"{base}/{key.lstrip('/')}"


def _get_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                creds = _creds()
                if not creds:
                    raise RuntimeError("R2 credentials are not configured")
                account, _bucket, key, secret = creds
                import boto3
                from botocore.config import Config
                _client = boto3.client(
                    "s3",
                    endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
                    aws_access_key_id=key,
                    aws_secret_access_key=secret,
                    # R2 is S3-compatible but region-less; boto3 requires one and
                    # "auto" is what Cloudflare documents.
                    region_name="auto",
                    config=Config(
                        signature_version="s3v4",
                        retries={"max_attempts": 4, "mode": "standard"},
                    ),
                )
    return _client


def bucket() -> str:
    creds = _creds()
    return creds[1] if creds else ""


def image_key(data: bytes, ext: str, prefix: str = "img/history") -> str:
    """A content-addressed key: the same bytes always produce the same key.

    This is what makes re-running the uploader cheap and the url cacheable for a
    year. `ext` carries the leading dot or not; both are accepted.
    """
    digest = hashlib.sha1(data).hexdigest()
    suffix = ext if ext.startswith(".") else f".{ext}"
    return f"{prefix.strip('/')}/{digest}{suffix.lower()}"


def exists(key: str) -> bool:
    try:
        _get_client().head_object(Bucket=bucket(), Key=key.lstrip("/"))
        return True
    except Exception:
        return False


def put(key: str, data: bytes, content_type: str,
        cache_control: str = DAILY, skip_if_present: bool = False) -> str:
    """Upload and return the public url. Raises on failure.

    Raising is deliberate. A silent upload failure would leave a url in a
    manifest pointing at nothing, and the whole point of routing every url
    through this module is that a url in a manifest means an object exists.
    """
    k = key.lstrip("/")
    if skip_if_present and exists(k):
        return url(k)
    _get_client().put_object(
        Bucket=bucket(),
        Key=k,
        Body=data,
        ContentType=content_type,
        CacheControl=cache_control,
    )
    return url(k)


def put_file(key: str, path, content_type: str, **kw) -> str:
    from pathlib import Path
    return put(key, Path(path).read_bytes(), content_type, **kw)


def describe() -> str:
    """One line for a run log: what media is configured to do right now."""
    if enabled():
        return f"media: R2 bucket {bucket()!r} served from {media_base()}"
    if media_base():
        return (f"media: VOID_MEDIA_BASE is {media_base()} but R2 credentials are "
                f"missing; falling back to committed files")
    return "media: R2 not configured; using committed files"
