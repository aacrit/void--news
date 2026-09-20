#!/usr/bin/env python3
"""The R2 media layer: does a url in a manifest mean an object exists?

Everything about moving binaries off git rests on that one promise. If an
upload can fail quietly, a manifest ends up pointing at nothing and the page
looks correct while serving 404s, which is strictly worse than the committed
files it replaced.

Runs against a mocked S3 (moto), so it exercises the real boto3 calls without a
bucket. Skips cleanly when moto is absent, because this must not be the reason
CI cannot run.

Run: python tests/test_media_r2.py
"""
import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "pipeline"))

FAIL = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global FAIL
    if not ok:
        FAIL += 1
    print(f"[{'ok  ' if ok else 'FAIL'}] {name}{(' — ' + detail) if detail else ''}")


def test_config_gate() -> None:
    """Configured or not, never half: a base with no credentials must read OFF."""
    from utils import media
    saved = {k: os.environ.get(k) for k in (
        "VOID_MEDIA_BASE", "R2_ACCOUNT_ID", "R2_BUCKET",
        "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY")}
    try:
        for k in saved:
            os.environ.pop(k, None)
        check("unconfigured is off", media.enabled() is False)

        os.environ["VOID_MEDIA_BASE"] = "https://media.example.org/"
        check("base without credentials stays off", media.enabled() is False,
              "otherwise urls are written for objects nobody uploaded")

        os.environ.update({"R2_ACCOUNT_ID": "a", "R2_BUCKET": "b",
                           "R2_ACCESS_KEY_ID": "k", "R2_SECRET_ACCESS_KEY": "s"})
        check("fully configured is on", media.enabled() is True)
        check("url joins exactly once",
              media.url("/audio/x.mp3") == "https://media.example.org/audio/x.mp3",
              media.url("/audio/x.mp3"))
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_content_addressing() -> None:
    from utils import media
    a = media.image_key(b"same", "JPG")
    b = media.image_key(b"same", ".jpg")
    c = media.image_key(b"other", "jpg")
    check("same bytes give the same key", a == b, f"{a} vs {b}")
    check("different bytes give a different key", a != c)
    check("key is prefixed and lowercased", a.startswith("img/history/") and a.endswith(".jpg"), a)


def test_round_trip() -> None:
    try:
        from moto import mock_aws
        import boto3
    except Exception as e:
        print(f"[skip] round trip — moto unavailable ({type(e).__name__})")
        return

    from utils import media
    os.environ.update({
        "VOID_MEDIA_BASE": "https://media.example.org",
        "R2_ACCOUNT_ID": "acct", "R2_BUCKET": "void-media",
        "R2_ACCESS_KEY_ID": "k", "R2_SECRET_ACCESS_KEY": "s",
    })
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1",
                          aws_access_key_id="k", aws_secret_access_key="s")
        s3.create_bucket(Bucket="void-media")
        media._client = s3
        try:
            u = media.put("audio/history/a.mp3", b"ID3fake", "audio/mpeg",
                          cache_control=media.IMMUTABLE)
            obj = s3.get_object(Bucket="void-media", Key="audio/history/a.mp3")
            check("upload returns the public url",
                  u == "https://media.example.org/audio/history/a.mp3", u)
            check("bytes stored verbatim", obj["Body"].read() == b"ID3fake")
            check("content type stored", obj["ContentType"] == "audio/mpeg")
            check("cache control stored", obj["CacheControl"] == media.IMMUTABLE)
            check("exists is true for a stored key", media.exists("audio/history/a.mp3"))
            check("exists is false for a missing key", not media.exists("audio/history/no.mp3"))

            media.put("audio/history/a.mp3", b"CHANGED", "audio/mpeg", skip_if_present=True)
            kept = s3.get_object(Bucket="void-media", Key="audio/history/a.mp3")["Body"].read()
            check("skip_if_present does not re-upload", kept == b"ID3fake")

            p = Path(tempfile.mkdtemp()) / "x.jpg"
            p.write_bytes(b"\xff\xd8bytes")
            key = media.image_key(p.read_bytes(), ".jpg")
            media.put_file(key, p, "image/jpeg", cache_control=media.IMMUTABLE)
            check("put_file uploads a file by its content key", media.exists(key), key)

            # The promise: a failed upload RAISES instead of handing back a url.
            media._client = boto3.client(
                "s3", region_name="us-east-1", aws_access_key_id="k",
                aws_secret_access_key="s", endpoint_url="http://127.0.0.1:1")
            raised = False
            try:
                media.put("y.bin", b"z", "application/octet-stream")
            except Exception:
                raised = True
            check("a failed upload raises, never returns a url", raised,
                  "a url to a missing object is worse than no move at all")
        finally:
            media._client = None


def main() -> int:
    test_config_gate()
    test_content_addressing()
    test_round_trip()
    print()
    if FAIL:
        print(f"FAIL: {FAIL} media check(s) failed")
        return 1
    print("PASS: the R2 media layer keeps its promise")
    return 0


if __name__ == "__main__":
    sys.exit(main())
