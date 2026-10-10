"""The History documentary score, per episode, on sampled real instruments.

`load_score(slug, era)` returns the SAME dict the producer has always consumed
(`generate_assets.history_cues`: theme, outro, rupture_entry, sting:to_document,
sting:from_clip, bed:<mood>, transition:<mood>) as pydub segments at the
producer's rate, so `mood_plan`, `mood_music_bus`, the duck, the clip mute and
H-17 are untouched. What changes is where the sound comes from:

  data/history/scores/<slug>.yaml   the episode's manifest: key, tempo, the
                                     theme and every cue as NOTE DATA, and the
                                     instruments as sampled recordings with their
                                     licence as stated, its URL, a rights basis on
                                     the allowlist and the sha256 of every file
  ~/.cache/void-score-samples/       the samples (never in the repository), fetched
                                     from the URL the manifest names and refused
                                     unless their sha256 is the pinned one
  ~/.cache/void-score-samples/render the rendered cues, keyed by a content hash of
                                     the note data, the sample hashes, the era and
                                     the renderer version, so a render is cheap
                                     the second time and bit-identical every time

An episode with no manifest, a manifest cue that cannot be rendered (a sample
not obtainable, a decoder missing), or a key the manifest does not define falls
back KEY BY KEY to the synthesised cue of `history_cues(era)`, so the other
episodes render exactly as before.

The renderer is pure numpy: a minimal RIFF reader, FFT resampling to the
target pitch and rate, a raised-cosine attack and release around each sample's
own decay, a steady-region loop for a sustain held longer than its sample, the
repo's own reverb (`generate_assets._history_room`, the era as the room) and
loop-clean beds by the repo's fold (render twice the length, fold the second
half onto the first). No ffmpeg is needed to render; ffmpeg (VOID_FFMPEG or on
PATH) is needed ONCE to decode a sample that was only lawfully downloadable as
an MP3 preview, and the decoded WAV is kept beside it.

Rules this module enforces (tests/test_history_score.py has a planted defect
for each):
  - rights_basis on RIGHTS_ALLOWLIST (CC0 as stated, or CC-BY as stated WITH a
    credit line); no NC, SA or ND anywhere in a licence string or URL
  - `claims: []` on every cue: the music claims nothing about the event
  - `textures: []`: AI textures are a documented hook (TEXTURES_HOOK), not a
    thing this module renders
  - every sample has a 64-hex sha256 and a source URL; a cached file whose hash
    is not the pinned one is deleted and the cue falls back

    python pipeline/history/score.py --preview <slug> [--era contemporary] [--out out/score]
    python pipeline/history/score.py --validate <slug>
    python pipeline/history/score.py --levels <slug>      # bed levels against the narrator
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import urllib.request
import wave
from pathlib import Path

import numpy as np
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from briefing import generate_assets as ga                                   # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SCORES_DIR = ROOT / "data" / "history" / "scores"
SAMPLE_RATE = 24000                     # the producer's rate (briefing.tts_engines.SAMPLE_RATE)
RENDER_VERSION = 5                      # bump when the renderer's arithmetic changes

RIGHTS_ALLOWLIST = ("cc0-as-stated", "cc-by-as-stated")
LICENCE_URL_OK = (
    re.compile(r"^https?://creativecommons\.org/publicdomain/zero/1\.0/?$"),
    re.compile(r"^https?://creativecommons\.org/licenses/by/\d\.\d/?$"),
)
LICENCE_FORBIDDEN = re.compile(r"(?i)(?:^|[^a-z])(nc|sa|nd)(?:$|[^a-z])|non-?commercial|share-?alike|no-?deriv")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
# The keys the producer consumes; a manifest may define no other.
MANDATORY_KEYS = ("theme", "outro", "rupture_entry", "sting:to_document", "sting:from_clip")
WET_MOODS = ("dread", "procedure", "grief", "reckoning")
DRY_MOODS = ("rupture", "testimony")
ALLOWED_KEYS = MANDATORY_KEYS + tuple(f"bed:{m}" for m in WET_MOODS) + tuple(f"transition:{m}" for m in WET_MOODS)
# What house_promos.stitch_post_roll assumes of the outro: silent from here.
OUTRO_MAX_S = 13.75
RUPTURE_ENTRY_MAX_S = 6.0               # mood_plan's span for the entry

# AI-generated TEXTURES (never the theme) are a CEO decision pending an
# audition on the GPU; this module renders none. The hook: a manifest's
# `textures:` list stays empty; when the CEO admits one, a texture is a row
# with the same rights fields as a sample, rendered by a separate module into
# a `texture:<mood>` array that `load_score` would add UNDER the bed of that
# mood at a level the manifest sets. Nothing in this file reads it today.
TEXTURES_HOOK = "textures"

_NOTE_INDEX = {"C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3, "E": 4, "F": 5, "F#": 6, "GB": 6,
               "G": 7, "G#": 8, "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11}


class ScoreError(RuntimeError):
    """A cue that cannot be rendered from the manifest; the caller falls back."""


# --------------------------------------------------------------------- notes

def note_to_midi(name: str) -> int:
    m = re.fullmatch(r"([A-Ga-g][#b]?)(-?\d)", str(name).strip())
    if not m:
        raise ScoreError(f"not a note name: {name!r}")
    return 12 * (int(m.group(2)) + 1) + _NOTE_INDEX[m.group(1).upper()]


def midi_to_hz(m: float) -> float:
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


# --------------------------------------------------------------------- cache

def cache_root() -> Path:
    root = Path(os.environ.get("VOID_SCORE_CACHE") or (Path.home() / ".cache" / "void-score-samples"))
    try:
        root.resolve().relative_to(ROOT.resolve())
    except ValueError:
        return root
    raise ScoreError(f"refusing a sample cache inside the repository: {root}")


def _offline() -> bool:
    return os.environ.get("VOID_SCORE_OFFLINE", "0") == "1"


def _ffmpeg() -> str | None:
    return os.environ.get("VOID_FFMPEG") or shutil.which("ffmpeg")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_sample(sample: dict) -> Path:
    """The sample's file in the cache, with the pinned sha256, fetched if
    needed. For a `decode:` sample the return value is the decoded WAV beside
    the download (the download is what the hash pins)."""
    root = cache_root()
    rel = str(sample.get("file") or "")
    if not rel or ".." in rel.split("/"):
        raise ScoreError(f"bad sample path {rel!r}")
    dest = root / rel
    pinned = str(sample.get("sha256") or "")
    if dest.exists():
        got = _sha256(dest)
        if got != pinned:
            dest.unlink()
            raise ScoreError(f"{rel}: sha256 {got[:12]} is not the pinned {pinned[:12]}; deleted")
    else:
        if _offline():
            raise ScoreError(f"{rel}: not in the cache and VOID_SCORE_OFFLINE=1")
        url = str(sample.get("url") or "")
        if not url.startswith("https://"):
            raise ScoreError(f"{rel}: no https source URL")
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        req = urllib.request.Request(url, headers={"User-Agent": "VoidNews-history-score/1.0"})
        with urllib.request.urlopen(req, timeout=120) as r, open(tmp, "wb") as out:
            shutil.copyfileobj(r, out)
        got = _sha256(tmp)
        if got != pinned:
            tmp.unlink()
            raise ScoreError(f"{rel}: downloaded sha256 {got[:12]} is not the pinned {pinned[:12]}")
        tmp.replace(dest)
    decode = sample.get("decode")
    if not decode:
        return dest
    wav = dest.with_suffix(".wav")
    if wav.exists():
        return wav
    ff = _ffmpeg()
    if not ff:
        raise ScoreError(f"{rel}: needs ffmpeg once to decode the {decode} preview (VOID_FFMPEG or PATH)")
    p = subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(dest), "-ac", "1",
                        "-ar", "44100", "-c:a", "pcm_s16le", "-bitexact", str(wav)],
                       capture_output=True, text=True)
    if p.returncode != 0 or not wav.exists():
        raise ScoreError(f"{rel}: decode failed: {p.stderr.strip()[-160:]}")
    return wav


# --------------------------------------------------------------------- WAV in / out

def read_wav(path: Path) -> tuple[np.ndarray, int]:
    """Mono float64 and the rate. PCM 16/24/32 and float32, plain or
    WAVE_FORMAT_EXTENSIBLE; stdlib `wave` refuses some of these."""
    data = path.read_bytes()
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ScoreError(f"{path.name}: not a RIFF/WAVE file")
    pos, fmt, pcm = 12, None, None
    while pos + 8 <= len(data):
        cid, size = data[pos:pos + 4], struct.unpack("<I", data[pos + 4:pos + 8])[0]
        body = data[pos + 8:pos + 8 + size]
        if cid == b"fmt ":
            tag, ch, sr, _, _, bits = struct.unpack("<HHIIHH", body[:16])
            if tag == 0xFFFE and len(body) >= 26:
                tag = struct.unpack("<H", body[24:26])[0]
            fmt = (tag, ch, sr, bits)
        elif cid == b"data":
            pcm = body
        pos += 8 + size + (size & 1)
    if fmt is None or pcm is None:
        raise ScoreError(f"{path.name}: no fmt or data chunk")
    tag, ch, sr, bits = fmt
    if tag == 3 and bits == 32:
        x = np.frombuffer(pcm[:len(pcm) // 4 * 4], dtype="<f4").astype(np.float64)
    elif tag == 1 and bits == 16:
        x = np.frombuffer(pcm[:len(pcm) // 2 * 2], dtype="<i2").astype(np.float64) / 32768.0
    elif tag == 1 and bits == 24:
        b = np.frombuffer(pcm[:len(pcm) // 3 * 3], dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        v = b[:, 0] | (b[:, 1] << 8) | (b[:, 2] << 16)
        x = np.where(v >= 1 << 23, v - (1 << 24), v).astype(np.float64) / float(1 << 23)
    elif tag == 1 and bits == 32:
        x = np.frombuffer(pcm[:len(pcm) // 4 * 4], dtype="<i4").astype(np.float64) / float(1 << 31)
    else:
        raise ScoreError(f"{path.name}: unsupported WAV format tag={tag} bits={bits}")
    if ch > 1:
        x = x[:len(x) // ch * ch].reshape(-1, ch).mean(axis=1)
    return x, sr


def write_wav(path: Path, x: np.ndarray, rate: int = SAMPLE_RATE) -> None:
    pcm = to_pcm16(x)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(rate)
        fh.writeframes(pcm.tobytes())


def to_pcm16(x: np.ndarray) -> np.ndarray:
    return np.round(np.clip(x, -1.0, 1.0) * 32767.0).astype(np.int16)


def to_segment(x: np.ndarray, rate: int = SAMPLE_RATE):
    from pydub import AudioSegment
    return AudioSegment(to_pcm16(x).tobytes(), frame_rate=rate, sample_width=2, channels=1)


# --------------------------------------------------------------------- DSP

def resample(x: np.ndarray, n_out: int) -> np.ndarray:
    """FFT resampling (what scipy.signal.resample does), so a pitch shift and
    a rate change are one band-limited operation with no new dependency."""
    n = len(x)
    if n_out <= 0:
        return np.zeros(0)
    if n_out == n:
        return x.copy()
    X = np.fft.rfft(x)
    k = n_out // 2 + 1
    Y = np.zeros(k, dtype=complex)
    m = min(k, len(X))
    Y[:m] = X[:m]
    if n_out < n and n_out % 2 == 0 and m == k:
        Y[-1] = Y[-1].real          # the new Nyquist bin must be real
    return np.fft.irfft(Y, n_out) * (n_out / n)


def _rms_dbfs(x: np.ndarray) -> float:
    r = float(np.sqrt(np.mean(np.square(x)))) if x.size else 0.0
    return -200.0 if r <= 0 else 20.0 * math.log10(r)


def _peak_dbfs(x: np.ndarray) -> float:
    p = float(np.max(np.abs(x))) if x.size else 0.0
    return -200.0 if p <= 0 else 20.0 * math.log10(p)


def _cos_in(n: int) -> np.ndarray:
    return 0.5 - 0.5 * np.cos(np.pi * np.arange(max(n, 0)) / max(n, 1))


def _cos_out(n: int) -> np.ndarray:
    return 0.5 + 0.5 * np.cos(np.pi * np.arange(max(n, 0)) / max(n, 1))


def detect_onset(x: np.ndarray, sr: int, floor_db: float = -38.0) -> int:
    """First sample where a 5 ms RMS clears `floor_db` under the peak, backed
    off 5 ms so the attack's own rise is kept."""
    peak = float(np.max(np.abs(x))) or 1.0
    w = max(1, int(sr * 0.005))
    n = len(x) // w
    if n == 0:
        return 0
    frames = np.sqrt(np.mean(np.square(x[:n * w].reshape(n, w)), axis=1)) / peak
    hit = np.argmax(frames > 10 ** (floor_db / 20.0))
    return max(0, (int(hit) - 1) * w)


def estimate_f0(x: np.ndarray, sr: int, fmin: float = 40.0, fmax: float = 1500.0) -> float:
    """Harmonic product spectrum on one window; used to check a slice is the
    note the manifest says it is (an octave error is tolerated by the check)."""
    seg = x - np.mean(x)
    n = len(seg)
    if n < sr // 10:
        return 0.0
    S = np.abs(np.fft.rfft(seg * np.hanning(n), 4 * n))
    fr = np.fft.rfftfreq(4 * n, 1.0 / sr)
    hps = S.copy()
    for h in (2, 3, 4, 5):
        hps[:len(S) // h] *= S[::h][:len(S) // h]
    lo, hi = np.searchsorted(fr, fmin), np.searchsorted(fr, fmax)
    return float(fr[lo + int(np.argmax(hps[lo:hi]))])


# --------------------------------------------------------------------- instruments

class Sample:
    """One prepared recording: mono, trimmed to its onset, peak-normalised, at
    its native rate, with its sounding MIDI note."""

    def __init__(self, x: np.ndarray, sr: int, midi: int, kind: str, loop: tuple[int, int] | None):
        self.x, self.sr, self.midi, self.kind, self.loop = x, sr, midi, kind, loop

    @property
    def seconds(self) -> float:
        return len(self.x) / self.sr


_SAMPLES: dict[str, Sample] = {}


def _prepare(inst_name: str, inst: dict, sample: dict, slice_: dict | None) -> Sample:
    key = json.dumps([inst_name, sample.get("file"), slice_], sort_keys=True)
    if key in _SAMPLES:
        return _SAMPLES[key]
    path = ensure_sample(sample)
    x, sr = read_wav(path)
    kind = str(inst.get("kind") or "sustain")
    if slice_ is not None:
        a, b = float(slice_["start_s"]), float(slice_["end_s"])
        if not (0 <= a < b <= len(x) / sr + 0.01):
            raise ScoreError(f"{sample['file']}: slice {a}-{b}s outside the file")
        x = x[int(a * sr):int(b * sr)]
        note = slice_["note"]
        # The slice is the note the manifest says, or the cue falls back.
        f0 = estimate_f0(x[int(0.3 * sr):int(min(len(x) / sr, 2.3) * sr)], sr)
        if f0 > 0:
            cents = 1200.0 * math.log2(f0 / midi_to_hz(note_to_midi(note)))
            off = ((cents + 600.0) % 1200.0) - 600.0            # octave-tolerant
            if abs(off) > 60.0:
                raise ScoreError(f"{sample['file']} slice {a}-{b}s sounds {f0:.1f} Hz, not {note} ({off:+.0f} cents)")
        fade = int(0.04 * sr)
        x = x.copy()
        x[:fade] *= _cos_in(fade)
        x[-fade:] *= _cos_out(fade)
        onset = 0
    else:
        note = sample["note"]
        onset = int(sample["onset_s"] * sr) if sample.get("onset_s") is not None else detect_onset(x, sr)
        x = x[onset:]
    peak = float(np.max(np.abs(x))) or 1.0
    x = x * (10 ** (-6.0 / 20.0) / peak)
    loop = None
    if kind == "sustain":
        # The steady region to loop when a note is held longer than the sample:
        # from after the attack to before the sample's own decay.
        ls = float(sample.get("loop_start_s", inst.get("loop_start_s", 0.8)))
        le = float(sample.get("loop_end_s", inst.get("loop_end_s", 0.0))) or (len(x) / sr - 1.2)
        le = min(le, len(x) / sr - 0.2)
        if le - ls < 0.5:
            ls, le = 0.05, max(0.6, len(x) / sr - 0.1)
        loop = (int(ls * sr), int(le * sr))
    s = Sample(x, sr, note_to_midi(note), kind, loop)
    _SAMPLES[key] = s
    return s


def instrument_samples(inst_name: str, inst: dict) -> list[Sample]:
    out: list[Sample] = []
    for sample in inst.get("samples") or []:
        if sample.get("slices"):
            for sl in sample["slices"]:
                out.append(_prepare(inst_name, inst, sample, sl))
        else:
            out.append(_prepare(inst_name, inst, sample, None))
    if not out:
        raise ScoreError(f"{inst_name}: no samples")
    return out


def _nearest(samples: list[Sample], midi: int) -> Sample:
    return min(samples, key=lambda s: (abs(s.midi - midi), s.midi))


def render_note(samples: list[Sample], inst: dict, midi: int, dur_s: float | None, vel: float,
                rate: int = SAMPLE_RATE) -> np.ndarray:
    """One note at `rate`: the nearest sample pitched to `midi`, held for
    `dur_s` then released over the instrument's release, or (dur None, a
    pluck) left to its own decay."""
    s = _nearest(samples, midi)
    ratio = 2.0 ** ((midi - s.midi) / 12.0)
    attack = float(inst.get("attack_s", 0.0))
    release = float(inst.get("release_s", 0.3))
    scale = rate / (s.sr * ratio)                 # output samples per source sample
    if dur_s is None or s.kind != "sustain":
        src = s.x
        y = resample(src, int(round(len(src) * scale)))
        if dur_s is not None:
            n_hold = int(dur_s * rate)
            n_rel = int(release * rate)
            if n_hold + n_rel < len(y):
                y = y[:n_hold + n_rel].copy()
                y[n_hold:] *= _cos_out(n_rel)
    else:
        need_src = int((dur_s + release) * s.sr * ratio)     # source samples that cover hold + release
        if need_src <= len(s.x) or s.loop is None:
            src = s.x[:min(len(s.x), need_src)]
        else:
            # Loop the steady region with an equal-power crossfade.
            a, b = s.loop
            seg = s.x[a:b]
            xf = min(int(0.6 * s.sr), len(seg) // 3)
            parts = [s.x[:b]]
            total = b
            while total < need_src:
                prev = parts[-1]
                # Equal POWER, not equal gain: the two sides of a loop seam
                # are not phase-aligned for a pitched tone, so raised-cosine
                # gains that sum to 1 partly cancel and dip several dB once
                # per cycle (found by the 1918 influenza composer, 2026-10-04).
                ramp = np.arange(xf) / max(xf, 1)
                head = seg[:xf] * np.sin(0.5 * np.pi * ramp) + prev[-xf:] * np.cos(0.5 * np.pi * ramp)
                parts[-1] = prev[:-xf]
                parts.append(np.concatenate([head, seg[xf:]]))
                total += len(seg) - xf
            src = np.concatenate(parts)[:need_src]
        y = resample(src, int(round(len(src) * scale)))
        n_hold = int(dur_s * rate)
        n_rel = int(release * rate)
        y = y[:n_hold + n_rel].copy()
        if len(y) > n_hold:
            y[n_hold:] *= _cos_out(len(y) - n_hold)
    if attack > 0:
        n_a = min(int(attack * rate), len(y))
        y[:n_a] *= _cos_in(n_a)
    return y * float(vel)


# --------------------------------------------------------------------- cues

def _events(cue: dict, beat_s: float) -> list[tuple[str, int, float, float | None, float]]:
    """(instrument, midi, at_s, dur_s or None, velocity) per note row:
    [inst, note, at_beats, dur_beats or null, vel]."""
    out = []
    for row in cue.get("notes") or []:
        inst, note, at, dur = row[0], row[1], float(row[2]), row[3]
        vel = float(row[4]) if len(row) > 4 else 0.8
        out.append((str(inst), note_to_midi(note), at * beat_s, None if dur is None else float(dur) * beat_s, vel))
    return out


def render_cue(manifest: dict, key: str, era: str, rate: int = SAMPLE_RATE) -> np.ndarray:
    cue = manifest["cues"][key]
    beat_s = 60.0 / float(manifest["tempo_bpm"])
    length = float(cue["length_s"])
    fold = bool(cue.get("fold", False))
    n = int(round(length * rate))
    buf = np.zeros(2 * n if fold else n)
    insts = manifest["instruments"]
    cache: dict[str, list[Sample]] = {}
    for inst_name, midi, at_s, dur_s, vel in _events(cue, beat_s):
        if inst_name not in insts:
            raise ScoreError(f"{key}: unknown instrument {inst_name!r}")
        inst = insts[inst_name]
        if inst_name not in cache:
            cache[inst_name] = instrument_samples(inst_name, inst)
        y = render_note(cache[inst_name], inst, midi, dur_s, vel, rate) * 10 ** (float(inst.get("gain_db", 0.0)) / 20.0)
        i0 = int(round(at_s * rate))
        i1 = min(len(buf), i0 + len(y))
        if i1 > i0:
            buf[i0:i1] += y[:i1 - i0]
    if fold:
        buf = buf[:n] + buf[n:2 * n]
    sw = cue.get("swell")
    if sw:
        a, h, r = (float(v) for v in sw)
        t = np.arange(len(buf)) / rate
        buf = buf * ga._swell(t, 0.0, a, h, r)
    wet = float(cue.get("room_wet", 1.0))
    if wet > 0:
        buf = ga._history_room(buf, era, circular=fold, wet_scale=wet)
    fi, fo = int(cue.get("fade_in_ms", 0)) * rate // 1000, int(cue.get("fade_out_ms", 0)) * rate // 1000
    if fi > 1:
        buf[:fi] *= _cos_in(fi)
    if fo > 1:
        buf[-fo:] *= _cos_out(fo)
    if "rms_dbfs" in cue:
        buf = ga._norm_rms(buf, float(cue["rms_dbfs"]), peak_ceiling_dbfs=-1.0)
    elif "peak_dbfs" in cue:
        buf = ga._norm_peak(buf, float(cue["peak_dbfs"]))
    if cue.get("tail_silence") and _rms_dbfs(buf[-int(0.2 * rate):]) > -80.0:
        raise ScoreError(f"{key}: does not end in silence ({_rms_dbfs(buf[-int(0.2 * rate):]):.1f} dBFS)")
    if float(np.max(np.abs(buf))) >= 1.0:
        raise ScoreError(f"{key}: clips")
    return buf


def _cue_hash(manifest: dict, key: str, era: str) -> str:
    cue = manifest["cues"][key]
    used = sorted({row[0] for row in cue.get("notes") or []})
    body = {"cue": cue, "tempo": manifest["tempo_bpm"], "era": era, "v": RENDER_VERSION,
            "instruments": {k: manifest["instruments"][k] for k in used if k in manifest["instruments"]},
            "room": ga.HISTORY_ERA_ROOM.get(era, ga.HISTORY_ERA_ROOM["modern"])}
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()[:16]


def render_cue_cached(manifest: dict, key: str, era: str) -> np.ndarray:
    h = _cue_hash(manifest, key, era)
    p = cache_root() / "render" / str(manifest["slug"]) / f"{key.replace(':', '_')}-{h}.wav"
    if p.exists():
        x, sr = read_wav(p)
        if sr == SAMPLE_RATE:
            return x
    x = render_cue(manifest, key, era)
    write_wav(p, x)
    return x


# --------------------------------------------------------------------- manifest

def manifest_path(slug: str) -> Path:
    return SCORES_DIR / f"{slug}.yaml"


def load_manifest(slug: str) -> dict | None:
    p = manifest_path(slug)
    if not p.exists():
        return None
    m = yaml.safe_load(p.read_text(encoding="utf-8"))
    if not isinstance(m, dict):
        raise ScoreError(f"{p.name}: not a mapping")
    return m


def validate_manifest(m: dict) -> list[str]:
    """Every rule, as a list of what is wrong. Empty means the manifest may
    render."""
    bad: list[str] = []
    for k in ("slug", "tempo_bpm", "instruments", "cues"):
        if k not in m:
            bad.append(f"missing {k}")
    if bad:
        return bad
    if not (20 <= float(m["tempo_bpm"]) <= 120):
        bad.append(f"tempo {m['tempo_bpm']} outside 20..120")
    if m.get(TEXTURES_HOOK):
        bad.append("textures must be empty: AI textures are a hook, not a rendered layer")
    for name, inst in (m["instruments"] or {}).items():
        basis = str(inst.get("rights_basis") or "")
        if basis not in RIGHTS_ALLOWLIST:
            bad.append(f"{name}: rights_basis {basis!r} not on {RIGHTS_ALLOWLIST}")
        if basis == "cc-by-as-stated" and not str(inst.get("credit_line") or "").strip():
            bad.append(f"{name}: CC-BY needs a credit_line")
        for field in ("licence_as_stated", "licence_url", "licence_source", "library", "role_as_presented"):
            if not str(inst.get(field) or "").strip():
                bad.append(f"{name}: lacks {field}")
        url = str(inst.get("licence_url") or "")
        if url and not any(r.match(url) for r in LICENCE_URL_OK):
            bad.append(f"{name}: licence_url {url!r} is not a CC0 or CC-BY deed")
        for field in ("licence_as_stated", "licence_url"):
            if LICENCE_FORBIDDEN.search(str(inst.get(field) or "")):
                bad.append(f"{name}: {field} carries an NC, SA or ND term")
        if inst.get("kind") not in ("sustain", "pluck"):
            bad.append(f"{name}: kind must be sustain or pluck")
        if not inst.get("samples"):
            bad.append(f"{name}: no samples")
        for s in inst.get("samples") or []:
            if not SHA_RE.match(str(s.get("sha256") or "")):
                bad.append(f"{name}: {s.get('file')}: sha256 missing or not 64 hex")
            if not str(s.get("url") or "").startswith("https://"):
                bad.append(f"{name}: {s.get('file')}: no https url")
            if not s.get("file"):
                bad.append(f"{name}: a sample without a file")
            if s.get("slices"):
                for sl in s["slices"]:
                    for f in ("note", "start_s", "end_s"):
                        if f not in sl:
                            bad.append(f"{name}: slice lacks {f}")
            elif not s.get("note"):
                bad.append(f"{name}: {s.get('file')}: no note")
    cues = m["cues"] or {}
    for k in MANDATORY_KEYS:
        if k not in cues:
            bad.append(f"cue {k} missing")
    for k, cue in cues.items():
        if k not in ALLOWED_KEYS:
            bad.append(f"cue {k!r} is not a key the producer consumes")
        if not isinstance(cue, dict):
            bad.append(f"cue {k}: not a mapping")
            continue
        if "claims" not in cue or cue["claims"] != []:
            bad.append(f"cue {k}: claims must be present and empty")
        if cue.get("silent"):
            continue
        try:
            length = float(cue["length_s"])
        except (KeyError, TypeError, ValueError):
            bad.append(f"cue {k}: no length_s")
            continue
        if length <= 0:
            bad.append(f"cue {k}: length_s must be positive")
        if k == "outro" and (length > OUTRO_MAX_S or not cue.get("tail_silence")):
            bad.append(f"cue outro: must be at most {OUTRO_MAX_S}s and tail_silence: true (the promo rides it)")
        if k == "rupture_entry" and length > RUPTURE_ENTRY_MAX_S:
            bad.append(f"cue rupture_entry: longer than mood_plan's {RUPTURE_ENTRY_MAX_S}s span")
        if k == "theme" and not (16.0 <= length <= 32.0):
            bad.append(f"cue theme: {length}s is not a statement of 16..32 s")
        if k.startswith("bed:") and not cue.get("fold"):
            bad.append(f"cue {k}: a bed must fold so it loops")
        if not cue.get("notes"):
            bad.append(f"cue {k}: no notes")
        for row in cue.get("notes") or []:
            if not (isinstance(row, list) and 4 <= len(row) <= 5):
                bad.append(f"cue {k}: note row {row!r} is not [inst, note, at, dur, vel]")
                continue
            if row[0] not in (m["instruments"] or {}):
                bad.append(f"cue {k}: instrument {row[0]!r} undefined")
            try:
                note_to_midi(row[1])
            except ScoreError as e:
                bad.append(f"cue {k}: {e}")
            if float(row[2]) < 0 or (row[3] is not None and float(row[3]) <= 0):
                bad.append(f"cue {k}: note {row!r} has a negative start or non-positive length")
            if len(row) > 4 and not (0.0 < float(row[4]) <= 1.0):
                bad.append(f"cue {k}: velocity {row[4]} outside (0, 1]")
    return bad


# --------------------------------------------------------------------- the producer's entry

def synthesised_cues(era: str) -> dict:
    """`history_cues(era)` as pydub segments at the producer's rate: the set
    every episode without a manifest gets, and the fallback for any key."""
    out = {}
    for k, x in ga.history_cues(era).items():
        out[k] = to_segment(np.asarray(x), ga.SAMPLE_RATE).set_frame_rate(SAMPLE_RATE)
    return out


def load_score(slug: str, era: str, *, log=print) -> dict:
    """The cue dict the producer consumes. Same keys and shape as
    `history_producer.history_score(era)`; sampled where the episode's
    manifest renders, synthesised everywhere else."""
    base = synthesised_cues(era)
    try:
        m = load_manifest(slug)
    except (ScoreError, yaml.YAMLError) as e:
        log(f"  [score] {slug}: manifest unreadable ({e}); synthesised cues")
        return base
    if m is None:
        return base
    bad = validate_manifest(m)
    if bad:
        log(f"  [score] {slug}: manifest fails validation; synthesised cues: " + "; ".join(bad[:4]))
        return base
    out = dict(base)
    rendered, fell = [], []
    for key, cue in m["cues"].items():
        if cue.get("silent"):
            out.pop(key, None)
            continue
        try:
            out[key] = to_segment(render_cue_cached(m, key, era))
            rendered.append(key)
        except (ScoreError, OSError, ValueError) as e:
            fell.append(key)
            log(f"  [score] {slug}: {key} falls back to the synthesised cue: {e}")
    log(f"  [score] {slug}: {len(rendered)} sampled cue(s)" + (f", {len(fell)} synthesised" if fell else ""))
    return out


# --------------------------------------------------------------------- preview and measurement

def _bed_levels(slug: str, era: str) -> list[str]:
    """Where each bed sits against the narrator, before (synthesised) and
    after (this manifest), through the producer's gains and duck floors."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from briefing import radio_producer as rp
    from history import mood as moodmod
    ref_path = ROOT / "out" / "audition" / "kokoro" / "meas_narrator.wav"
    narrator = -22.5
    note = "the Kokoro narrator bus of the local audition (no voice chain; the production chain adds 2 dB makeup)"
    if ref_path.exists():
        x, _ = read_wav(ref_path)
        narrator = _rms_dbfs(x[np.abs(x) > 0.003]) if np.any(np.abs(x) > 0.003) else _rms_dbfs(x)
    lines = [f"narrator reference {narrator:.1f} dBFS RMS ({note})",
             f"producer gains: bed +{rp.BED_STORY_GAIN_DB:.0f} dB, duck floor per mood (mood.py)"]
    synth = ga.history_cues(era)
    m = load_manifest(slug)
    for mood in WET_MOODS:
        floor = moodmod.MOODS[mood].duck_db
        key = f"bed:{mood}"
        row = [f"{key:16}"]
        for label, arr in (("before", synth.get(key)), ("after", render_cue_cached(m, key, era) if m and key in m["cues"] else None)):
            if arr is None:
                row.append(f"{label}: none")
                continue
            r = _rms_dbfs(np.asarray(arr))
            full = r + rp.BED_STORY_GAIN_DB
            ducked = full + floor
            row.append(f"{label}: cue {r:6.1f} dBFS -> in a rest {full:6.1f} ({narrator - full:4.1f} under speech), "
                       f"ducked {ducked:6.1f} ({narrator - ducked:4.1f} under)")
        lines.append(" | ".join(row))
    return lines


DEMO_PLAN = (
    # (key, seconds or None for the whole cue, gap after in seconds)
    ("theme", None, 1.5), ("bed:dread", 12.0, 1.0), ("transition:procedure", None, 0.4),
    ("bed:procedure", 12.0, 0.0), ("sting:to_document", None, 1.2), ("bed:procedure", 5.0, 2.0),
    ("__silence__", 4.0, 0.0), ("rupture_entry", None, 1.5), ("transition:reckoning", None, 0.4),
    ("bed:reckoning", 8.0, 1.0), ("transition:grief", None, 0.4), ("bed:grief", 16.0, 1.0),
    ("transition:dread", None, 0.4), ("bed:dread", 6.0, 1.5), ("outro", None, 0.0),
)


def preview(slug: str, era: str, out_dir: Path) -> list[Path]:
    """Every cue as a WAV, and a score-only demo in episode order with gaps,
    at the producer's gains (beds +BED_STORY_GAIN_DB, the rest +CUE_GAIN_DB)
    and the beds UN-ducked, which is how they sound in a REST."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from briefing import radio_producer as rp
    m = load_manifest(slug)
    if m is None:
        raise SystemExit(f"no manifest for {slug}")
    bad = validate_manifest(m)
    if bad:
        raise SystemExit("manifest invalid:\n  " + "\n  ".join(bad))
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    cues: dict[str, np.ndarray] = {}
    for key in m["cues"]:
        if m["cues"][key].get("silent"):
            continue
        x = render_cue_cached(m, key, era)
        cues[key] = x
        p = out_dir / f"{key.replace(':', '_')}.wav"
        write_wav(p, x)
        written.append(p)
        print(f"  {key:22} {len(x) / SAMPLE_RATE:6.2f}s  peak {_peak_dbfs(x):6.1f}  rms {_rms_dbfs(x):6.1f} dBFS")
    parts: list[np.ndarray] = []
    for key, secs, gap in DEMO_PLAN:
        if key == "__silence__":
            parts.append(np.zeros(int(secs * SAMPLE_RATE)))
            continue
        x = cues.get(key)
        if x is None:
            continue
        gain = rp.BED_STORY_GAIN_DB if key.startswith("bed:") else rp.CUE_GAIN_DB
        y = x * 10 ** (gain / 20.0)
        if secs is not None:
            n = int(secs * SAMPLE_RATE)
            reps = int(math.ceil(n / len(y))) if len(y) else 1
            y = np.tile(y, reps)[:n].copy()
            fi, fo = int(1.5 * SAMPLE_RATE), int(2.0 * SAMPLE_RATE)
            y[:fi] *= _cos_in(fi)
            y[-fo:] *= _cos_out(fo)
        parts.append(y)
        parts.append(np.zeros(int(gap * SAMPLE_RATE)))
    demo = np.concatenate(parts)
    demo = demo / max(1.0, float(np.max(np.abs(demo))) / 10 ** (-1.0 / 20.0))
    p = out_dir / f"{slug}.score-demo.wav"
    write_wav(p, demo)
    written.append(p)
    print(f"  demo {len(demo) / SAMPLE_RATE:.0f}s -> {p}")
    ff = _ffmpeg()
    if ff:
        mp3 = p.with_suffix(".mp3")
        r = subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(p), "-b:a", "128k", str(mp3)],
                           capture_output=True, text=True)
        if r.returncode == 0:
            written.append(mp3)
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--preview", metavar="SLUG")
    ap.add_argument("--validate", metavar="SLUG")
    ap.add_argument("--levels", metavar="SLUG")
    ap.add_argument("--fetch", metavar="SLUG", help="fetch and verify every sample, render nothing")
    ap.add_argument("--era", default=None, help="default: the event's era")
    ap.add_argument("--out", default=str(ROOT / "out" / "score"))
    a = ap.parse_args(argv)
    slug = a.preview or a.validate or a.levels or a.fetch
    if not slug:
        ap.print_help()
        return 2
    era = a.era
    if era is None:
        ev = ROOT / "data" / "history" / "events" / f"{slug}.yaml"
        era = str((yaml.safe_load(ev.read_text(encoding="utf-8")) or {}).get("era") or "modern") if ev.exists() else "modern"
    if a.validate:
        m = load_manifest(slug)
        if m is None:
            print(f"no manifest at {manifest_path(slug)}")
            return 1
        bad = validate_manifest(m)
        print("\n".join(bad) if bad else f"{slug}: manifest valid")
        return 1 if bad else 0
    if a.fetch:
        m = load_manifest(slug)
        for name, inst in m["instruments"].items():
            for s in inst["samples"]:
                print(f"  {name:10} {s['file']} -> {ensure_sample(s)}")
        return 0
    if a.levels:
        print("\n".join(_bed_levels(slug, era)))
        return 0
    for p in preview(slug, era, Path(a.out) / slug):
        print(f"  wrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
