#!/usr/bin/env python3
"""Verify an archival clip against its stored transcript, with a free local ASR.

HISTORY-AUDIO-ARCHIVAL.md §3. A clip is admitted for its words, so the words
are checked mechanically, at $0, on CPU:

  1. fetch   the ledger row's `file` into a cache OUTSIDE the repository
             (~/.cache/void-history-clips, or VOID_CLIP_CACHE), and refuse it
             unless its md5 is the one the repository itself publishes
  2. cut     the declared window, nothing else, to 16 kHz mono for the ASR,
             and hash the excerpt's PCM at the source rate (the sha256 the
             producer checks again before it splices)
  3. listen  faster-whisper (CTranslate2, int8, `base.en` by default), or
             whisper.cpp when WHISPER_CPP_BIN and WHISPER_CPP_MODEL are set
  4. align   the recognised words against the stored transcript, both folded
             to lower-case alphanumerics: word error rate, the share of the
             transcript's words recovered IN ORDER (coverage), and whether the
             window's edges sit on the transcript's edges

A 1947 disc transfer through a base-size model will not match word for word,
so the gate is alignment, not identity: coverage >= clips.COVERAGE_MIN, the
first and last transcript words recovered within one word of each edge, and
no more than EDGE_INSERT_MAX recognised words outside the aligned span (an
out point that runs into the next sentence fails here). WER is recorded and
reported, never used to pass a clip.

The record is written beside the ledger, at the path the row's `verification`
names. It holds numbers, the recognised text, the diff and the hashes, never
audio. Nothing here signs anything: `signed_by` is the CEO's.

    python -m pipeline.history.verify_clip partition-of-india clip-nehru-tryst-19470814 --write
    python -m pipeline.history.verify_clip partition-of-india clip-nehru-tryst-19470814 --check
    python -m pipeline.history.verify_clip <slug> <id> --in 60 --out 93   # calibration: a wrong window
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline.history import clips  # noqa: E402
from pipeline.history.ledger import load_ledger, EVIDENCE  # noqa: E402

DEFAULT_MODEL = os.environ.get("VOID_ASR_MODEL", "base.en")
EDGE_INSERT_MAX = 2
EDGE_SLACK_WORDS = 1
_UA = "void-history-verify-clip/0.1 (+https://news.voidvision.org)"


# --------------------------------------------------------------------- cache

def cache_root() -> Path:
    root = Path(os.environ.get("VOID_CLIP_CACHE") or (Path.home() / ".cache" / "void-history-clips"))
    root = root.expanduser().resolve()
    try:
        root.relative_to(ROOT)
        inside = True
    except ValueError:
        inside = False
    if inside:
        # The repository never holds a recording: not committed, not staged,
        # not sitting in the tree waiting for a careless `git add -A`.
        raise SystemExit(f"refusing a clip cache inside the repository: {root}")
    return root


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(slug: str, rec: dict) -> Path:
    """The row's file, in the cache, checked against the repository's md5."""
    url = str(rec.get("file") or "")
    if not url:
        raise SystemExit(f"{rec.get('id')}: no file url")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", url.rsplit("/", 1)[-1]) or "clip"
    dest = cache_root() / slug / str(rec["id"]) / name
    want = str(rec.get("file_md5") or "")
    if dest.exists() and (not want or md5_of(dest) == want):
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as fh:
        shutil.copyfileobj(r, fh)
    got = md5_of(tmp)
    if want and got != want:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"{rec['id']}: md5 {got} is not the repository's {want}; refusing the file")
    tmp.replace(dest)
    return dest


# --------------------------------------------------------------------- cut + hash

def _ffmpeg() -> str:
    ff = shutil.which("ffmpeg")
    if not ff:
        raise SystemExit("ffmpeg is required")
    return ff


def source_rate(src: Path) -> int:
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        p = subprocess.run([ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries",
                            "stream=sample_rate", "-of", "csv=p=0", str(src)],
                           capture_output=True, text=True)
        try:
            return int(p.stdout.strip().splitlines()[0])
        except (ValueError, IndexError):
            pass
    return 44100


def excerpt_pcm(src: Path, t0: float, t1: float, rate: int | None = None) -> tuple[bytes, int]:
    """The window as raw s16le mono at the source's own rate (or `rate`).

    The hash is over samples, not a container, so it does not move when an
    ffmpeg build writes a different WAV header. Sample-accurate: `atrim` on
    the decoded stream, not a keyframe seek."""
    rate = rate or source_rate(src)
    p = subprocess.run([_ffmpeg(), "-hide_banner", "-loglevel", "error", "-i", str(src),
                        "-af", f"atrim=start={t0:.3f}:end={t1:.3f},asetpts=PTS-STARTPTS",
                        "-ac", "1", "-ar", str(rate), "-f", "s16le", "-acodec", "pcm_s16le",
                        "-bitexact", "-"], capture_output=True)
    if p.returncode != 0 or not p.stdout:
        raise SystemExit(f"cut failed: {p.stderr.decode(errors='replace')[-300:]}")
    return p.stdout, rate


def excerpt_sha256(src: Path, t0: float, t1: float) -> str:
    pcm, _ = excerpt_pcm(src, t0, t1)
    return hashlib.sha256(pcm).hexdigest()


def cut_wav(src: Path, t0: float, t1: float, dst: Path, rate: int = 16000) -> Path:
    p = subprocess.run([_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-i", str(src),
                        "-af", f"atrim=start={t0:.3f}:end={t1:.3f},asetpts=PTS-STARTPTS",
                        "-ac", "1", "-ar", str(rate), "-c:a", "pcm_s16le", str(dst)],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"cut failed: {p.stderr[-300:]}")
    return dst


# --------------------------------------------------------------------- ASR

_FW_SNIPPET = r"""
import json, sys
from faster_whisper import WhisperModel
import faster_whisper
wav, model = sys.argv[1], sys.argv[2]
m = WhisperModel(model, device="cpu", compute_type="int8")
segs, info = m.transcribe(wav, beam_size=5, language="en", vad_filter=False,
                          condition_on_previous_text=False, temperature=0.0)
text = " ".join(s.text.strip() for s in segs)
print(json.dumps({"text": text, "tool": "faster-whisper", "tool_version": faster_whisper.__version__,
                  "model": model, "compute_type": "int8", "beam_size": 5}))
"""


def transcribe(wav: Path, model: str = DEFAULT_MODEL) -> dict:
    """{text, tool, tool_version, model, ...}.

    faster-whisper in this interpreter, else in VOID_ASR_PYTHON (a separate
    venv, the way Kokoro runs in .venv-tts), else whisper.cpp."""
    py = os.environ.get("VOID_ASR_PYTHON", "").strip()
    candidates = [py] if py else [sys.executable]
    for interp in candidates:
        p = subprocess.run([interp, "-c", _FW_SNIPPET, str(wav), model], capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip():
            return json.loads(p.stdout.strip().splitlines()[-1])
        err = p.stderr.strip()[-300:]
    wbin, wmodel = os.environ.get("WHISPER_CPP_BIN"), os.environ.get("WHISPER_CPP_MODEL")
    if wbin and wmodel:
        p = subprocess.run([wbin, "-m", wmodel, "-f", str(wav), "-nt", "-np", "-l", "en"],
                           capture_output=True, text=True)
        if p.returncode == 0:
            return {"text": " ".join(p.stdout.split()), "tool": "whisper.cpp", "tool_version": None,
                    "model": Path(wmodel).name, "compute_type": None, "beam_size": None}
    raise SystemExit(f"no ASR available (faster-whisper: {err}); pip install faster-whisper, "
                     f"or set VOID_ASR_PYTHON / WHISPER_CPP_BIN")


# --------------------------------------------------------------------- alignment

def words_of(text: str) -> list[str]:
    s = "".join(c for c in unicodedata.normalize("NFD", text or "") if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9]+", s.lower())


def align(reference: str, hypothesis: str) -> dict:
    """Levenshtein alignment on words, with the backtrace.

    ops: ("=", ref, hyp) match, ("S", ref, hyp) substitution, ("D", ref, None)
    deletion (a transcript word not heard), ("I", None, hyp) insertion (a
    word heard that the transcript does not carry)."""
    r, h = words_of(reference), words_of(hypothesis)
    n, m = len(r), len(h)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1,
                          d[i - 1][j - 1] + (0 if r[i - 1] == h[j - 1] else 1))
    ops: list[tuple] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + (0 if r[i - 1] == h[j - 1] else 1):
            ops.append(("=" if r[i - 1] == h[j - 1] else "S", r[i - 1], h[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            ops.append(("D", r[i - 1], None))
            i -= 1
        else:
            ops.append(("I", None, h[j - 1]))
            j -= 1
    ops.reverse()
    S = sum(1 for o in ops if o[0] == "S")
    D = sum(1 for o in ops if o[0] == "D")
    I = sum(1 for o in ops if o[0] == "I")
    matched = [k for k, o in enumerate(ops) if o[0] == "="]
    # Reference index of each op, to place the matched span on the transcript.
    ref_idx, k_ref = [], 0
    for o in ops:
        ref_idx.append(k_ref if o[1] is not None else None)
        if o[1] is not None:
            k_ref += 1
    first_ref = ref_idx[matched[0]] if matched else None
    last_ref = ref_idx[matched[-1]] if matched else None
    lead_ins = sum(1 for o in ops[:matched[0]] if o[0] == "I") if matched else m
    trail_ins = sum(1 for o in ops[matched[-1] + 1:] if o[0] == "I") if matched else m
    return {
        "ref_words": n, "hyp_words": m,
        "substitutions": S, "deletions": D, "insertions": I,
        "wer": round((S + D + I) / n, 4) if n else None,
        "coverage": round(len(matched) / n, 4) if n else 0.0,
        "first_matched_ref": first_ref, "last_matched_ref": last_ref,
        "lead_insertions": lead_ins, "trail_insertions": trail_ins,
        "ops": ops,
    }


def verdict(al: dict) -> tuple[bool, list[str]]:
    why: list[str] = []
    n = al["ref_words"]
    if al["coverage"] < clips.COVERAGE_MIN:
        why.append(f"coverage {al['coverage']:.3f} under {clips.COVERAGE_MIN}")
    if al["first_matched_ref"] is None or al["first_matched_ref"] > EDGE_SLACK_WORDS:
        why.append("the window does not open on the transcript's first words")
    if al["last_matched_ref"] is None or al["last_matched_ref"] < n - 1 - EDGE_SLACK_WORDS:
        why.append("the window does not close on the transcript's last words")
    if al["lead_insertions"] > EDGE_INSERT_MAX:
        why.append(f"{al['lead_insertions']} recognised words before the transcript begins")
    if al["trail_insertions"] > EDGE_INSERT_MAX:
        why.append(f"{al['trail_insertions']} recognised words after the transcript ends")
    return (not why), why


def render_diff(ops: list[tuple]) -> list[str]:
    """Compact, reviewable: '=' runs collapsed, every disagreement spelled out."""
    out: list[str] = []
    run: list[str] = []
    for op, r, h in ops:
        if op == "=":
            run.append(r)
            continue
        if run:
            out.append(" ".join(run))
            run = []
        out.append({"S": f"[{r} -> {h}]", "D": f"[-{r}]", "I": f"[+{h}]"}[op])
    if run:
        out.append(" ".join(run))
    return out


# --------------------------------------------------------------------- main

def verify(slug: str, clip_id: str, *, t_in: float | None = None, t_out: float | None = None,
           model: str = DEFAULT_MODEL, reference: str | None = None,
           evidence: Path | None = None) -> dict:
    ledger = load_ledger(slug, evidence_dir=evidence)
    rec = ledger.recordings.get(clip_id)
    if rec is None:
        raise SystemExit(f"{slug}: no recording {clip_id!r} in the ledger")
    w = clips.window(rec)
    t0 = t_in if t_in is not None else (w[0] if w else None)
    t1 = t_out if t_out is not None else (w[1] if w else None)
    if t0 is None or t1 is None or t1 <= t0:
        raise SystemExit(f"{clip_id}: no excerpt window")
    ref = reference if reference is not None else str(rec.get("transcript") or "")
    src = fetch(slug, rec)
    with tempfile.TemporaryDirectory(prefix="void-clip-") as tmp:
        wav = cut_wav(src, t0, t1, Path(tmp) / "excerpt16k.wav")
        asr = transcribe(wav, model)
    al = align(ref, asr["text"])
    ok, why = verdict(al)
    return {
        "clip_id": clip_id, "slug": slug,
        "tool": asr.get("tool"), "tool_version": asr.get("tool_version"), "model": asr.get("model"),
        "compute_type": asr.get("compute_type"), "beam_size": asr.get("beam_size"),
        "source": {"file": rec.get("file"), "md5": md5_of(src), "md5_expected": rec.get("file_md5"),
                   "rate": source_rate(src)},
        "window": {"in": round(t0, 3), "out": round(t1, 3), "seconds": round(t1 - t0, 3)},
        "excerpt_sha256": excerpt_sha256(src, t0, t1),
        "excerpt_pcm": "s16le mono at the source rate, ffmpeg atrim, -bitexact",
        "reference": ref,
        "hypothesis": asr["text"].strip(),
        "wer": al["wer"], "coverage": al["coverage"],
        "counts": {k: al[k] for k in ("ref_words", "hyp_words", "substitutions", "deletions", "insertions",
                                       "first_matched_ref", "last_matched_ref", "lead_insertions",
                                       "trail_insertions")},
        "diff": render_diff(al["ops"]),
        "thresholds": {"coverage_min": clips.COVERAGE_MIN, "edge_slack_words": EDGE_SLACK_WORDS,
                       "edge_insert_max": EDGE_INSERT_MAX},
        "pass": ok, "why": why,
        "verified_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "signed": False,
        "note": "a pass verifies the words in this window against the stored transcript. It does not "
                "verify the occasion, the date or the rights, and it signs nothing.",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("slug")
    ap.add_argument("clip_id")
    ap.add_argument("--in", dest="t_in", type=float, default=None, help="override the window (calibration)")
    ap.add_argument("--out", dest="t_out", type=float, default=None)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--reference", default=None, help="check against this text instead (calibration)")
    ap.add_argument("--write", action="store_true", help="write the record the ledger row names")
    ap.add_argument("--check", action="store_true",
                    help="re-run and fail unless the committed record still holds (render job)")
    a = ap.parse_args(argv)
    calibrating = a.t_in is not None or a.t_out is not None or a.reference is not None
    rec = verify(a.slug, a.clip_id, t_in=a.t_in, t_out=a.t_out, model=a.model, reference=a.reference)
    print(f"{a.clip_id}: window {rec['window']['in']:.3f}-{rec['window']['out']:.3f} s "
          f"({rec['window']['seconds']:.2f} s), {rec['tool']} {rec['model']}")
    print(f"  heard: {rec['hypothesis']}")
    print(f"  WER {rec['wer']:.3f}  coverage {rec['coverage']:.3f}  "
          f"{'PASS' if rec['pass'] else 'FAIL'} {'; '.join(rec['why'])}")
    print(f"  diff: {' '.join(rec['diff'])}")
    print(f"  excerpt sha256 {rec['excerpt_sha256']}")
    ledger = load_ledger(a.slug)
    row = ledger.recordings[a.clip_id]
    target = clips.verification_path(a.slug, row)
    if a.write:
        if calibrating:
            raise SystemExit("--write records the ledger's own window and transcript only")
        if target is None:
            raise SystemExit("the ledger row names no `verification` path")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  wrote {target.relative_to(ROOT)}")
    if a.check:
        old = clips.load_verification(a.slug, row)
        if old is None:
            print("  CHECK FAIL: no committed record")
            return 1
        same = (old.get("excerpt_sha256") == rec["excerpt_sha256"] and bool(old.get("pass")) == rec["pass"]
                and old.get("reference") == rec["reference"])
        if not same:
            print("  CHECK FAIL: the committed record no longer holds for this file and window")
            return 1
        print("  CHECK OK: the committed record holds")
    return 0 if rec["pass"] else 2


if __name__ == "__main__":
    sys.exit(main())
