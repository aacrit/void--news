"""On Air: the score. One motif, composed fresh for every episode, held to the
house score standard (the `document` studio's A29 block, applied to radio).

Nothing here is a sample or a loop. Every cue is synthesised in numpy from
note data at render time, so it is Void's own, and the day's date seeds the
voicing so no two episodes carry the same bed while every episode carries the
same motif. The standard the cues are measured against, in one block:

    dialogue                 -20 LUFS integrated, per line (the producer)
    bed under speech         -31 LUFS in the voice's gaps (11 dB under), rising +6 dB over
                             the last 10 s into a page-turn, the entrance or the outro
    duck under voice         -10 dB, 1.0 s eased pre-roll, held across gaps < 1.2 s
    featured (title, outro)  -26 LUFS short-term, never louder
    transition / sting       never louder than the bed it leads into (+0.5 dB)
    band shape (beds)        bass under 130 Hz kept (rev 5; 100 before), low-mids
                             150-400 Hz cut (24 dB/oct high-pass at 400 Hz), treble
                             shelf -3 dB at 5 kHz; at most 2 % of a cue's energy
                             above 5 kHz, at most 10 % of it in 150-400 Hz
    breathing (beds)         100 ms level spread p90-p10 >= 6 dB
    fades                    an entry from silence >= 1.5 s, an exit >= 1.5 s
    repetition               no 4 s stretch tiled three times inside a cue

Why these numbers: the founder's notes on the film studio's score, in order:
"not loud; dramatic when needed, silent when it deserves; transitions
consistent", then "a lot more bass heavy, a lot less treble, bass beats
soothingly guiding the audience", then "patterns are repeating and it's
jarring". `check_cue` and `check_duck` measure a rendered cue against the block
and return findings; `tests/test_onair_show.py` plants a defect for each.

Rev 3 (2026-11-07): the SOUND lives in `onair_music.py` (patches, harmony,
the hook, the arrangement of every cue, stereo); this module keeps the
standard and its measurements, levels and shapes what the music renders,
and places the duck. Cues are stereo float64 of shape (n, 2) at SR = 48000;
every measurement reads the stereo as BS.1770 does (channel powers summed).
No pydub here: numpy and scipy only.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field

import numpy as np
from scipy import signal

SR = 48000

# ---------------------------------------------------------------------------
# The standard
# ---------------------------------------------------------------------------

DIALOGUE_LUFS = -20.0
BED_LUFS = -31.0                 # bed under speech, in the gaps (CEO 2026-11-07 ear test 2: -28 overpowered; it rises into transitions instead)
FEATURED_LUFS = -26.0            # title, entrance, outro: heard for themselves
TRANSITION_OVER_BED_MAX_DB = 0.5
DUCK_DB = -10.0
DUCK_PREROLL_S = 1.0             # eased attack, full depth ON the onset (A37)
DUCK_HOLD_S = 1.2                # a gap shorter than this keeps the duck
DUCK_RELEASE_S = 0.6             # the ramp back up after the hold
BED_LOWMID_HZ = 400.0            # 24 dB/oct high-pass: the low-mids go
# 24 dB/oct low-pass: the bass stays. Rev 5 (2026-11-08, CEO: "a little more
# bass") moved it from 100 to 130 Hz so a bass note keeps its OCTAVE (the
# roots sit at 49-87 Hz; their octaves at 98-175 Hz are what a small speaker
# reproduces of the note). 130 passes the octave of every root up to C2
# whole and shades D2's and F2's; the 150-400 Hz limit below and the phone
# margin (150 Hz-4 kHz) are untouched because the pass-band ends under them.
SUB_BASS_HZ = 130.0
TREBLE_HZ = 5000.0
TREBLE_SHELF_DB = -3.0
MUSIC_TREBLE_MAX_SHARE = 0.02
BED_LOWMID_MAX_SHARE = 0.10
BED_BREATH_DB = 6.0
RISE_DB = 6.0                    # a bed rises this much into the transition it leads to
RISE_S = 10.0                    # over this long, eased
ENTRY_FADE_MIN_S = 1.5
EXIT_FADE_MIN_S = 1.5
TOL_DB = 1.0

# ---------------------------------------------------------------------------
# Loudness (ITU-R BS.1770-4), 48 kHz coefficients
# ---------------------------------------------------------------------------

_K_STAGE1 = (np.array([1.53512485958697, -2.69169618940638, 1.19839281085285]),
             np.array([1.0, -1.69065929318241, 0.73248077421585]))
_K_STAGE2 = (np.array([1.0, -2.0, 1.0]),
             np.array([1.0, -1.99004745483398, 0.99007225036621]))


def k_weight(x: np.ndarray) -> np.ndarray:
    y = signal.lfilter(_K_STAGE1[0], _K_STAGE1[1], x, axis=0)
    return signal.lfilter(_K_STAGE2[0], _K_STAGE2[1], y, axis=0)


def _t(n: int) -> np.ndarray:
    return np.arange(n, dtype=np.float64) / SR


def mono(x: np.ndarray) -> np.ndarray:
    """A mono view for the spectral measurements: the channels' mean."""
    return x if x.ndim == 1 else np.mean(x, axis=1)


def _block_power(x: np.ndarray, block_s: float, hop_s: float) -> np.ndarray:
    """Mean K-weighted power per block; a stereo cue sums its channels' powers (BS.1770)."""
    n = int(block_s * SR)
    hop = max(1, int(hop_s * SR))
    if len(x) < n:
        return np.array([float(np.sum(np.mean(np.atleast_2d(x.T) ** 2, axis=1)))]) if len(x) else np.array([])
    k = k_weight(x.astype(np.float64))
    sq = k * k if k.ndim == 1 else np.sum(k * k, axis=1)
    cs = np.concatenate([[0.0], np.cumsum(sq)])
    starts = np.arange(0, len(x) - n + 1, hop)
    return (cs[starts + n] - cs[starts]) / n


def lufs_integrated(x: np.ndarray) -> float:
    """Gated integrated loudness (absolute -70, relative -10)."""
    p = _block_power(x, 0.4, 0.1)
    if p.size == 0:
        return -math.inf
    l = -0.691 + 10 * np.log10(np.maximum(p, 1e-20))
    keep = l > -70.0
    if not keep.any():
        return -math.inf
    rel = -0.691 + 10 * math.log10(float(np.mean(p[keep]))) - 10.0
    keep &= l > rel
    if not keep.any():
        return -math.inf
    return -0.691 + 10 * math.log10(float(np.mean(p[keep])))


def lufs_shortterm(x: np.ndarray, hop_s: float = 0.1) -> np.ndarray:
    """Short-term (3 s) loudness series."""
    p = _block_power(x, 3.0, hop_s)
    return -0.691 + 10 * np.log10(np.maximum(p, 1e-20))


def lufs_momentary(x: np.ndarray, hop_s: float = 0.1) -> np.ndarray:
    p = _block_power(x, 0.4, hop_s)
    return -0.691 + 10 * np.log10(np.maximum(p, 1e-20))


def level_to(x: np.ndarray, target_lufs: float) -> tuple[np.ndarray, float]:
    """One static gain so the integrated loudness is `target_lufs`."""
    cur = lufs_integrated(x)
    if not math.isfinite(cur):
        return x, 0.0
    g = target_lufs - cur
    return x * (10 ** (g / 20)), g


def true_peak_dbtp(x: np.ndarray) -> float:
    if len(x) == 0:
        return -math.inf
    up = signal.resample_poly(x.astype(np.float64), 4, 1, axis=0)
    return 20 * math.log10(max(float(np.max(np.abs(up))), 1e-9))


def band_share(x: np.ndarray, lo_hz: float, hi_hz: float | None, floor_hz: float = 0.0) -> float:
    """Share of the energy above `floor_hz` that lies in [lo, hi)."""
    if len(x) < 2048:
        return 0.0
    x = mono(x)
    spec = np.abs(np.fft.rfft(x.astype(np.float64) * np.hanning(len(x)))) ** 2
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    tot = float(spec[f >= floor_hz].sum()) or 1e-20
    sel = (f >= lo_hz) & ((f < hi_hz) if hi_hz else True)
    return float(spec[sel].sum()) / tot


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

def _sos_butter(order: int, hz: float, kind: str):
    return signal.butter(order, hz, btype=kind, fs=SR, output="sos")


def high_shelf_coeffs(f0: float, gain_db: float, slope: float = 0.9):
    """RBJ high shelf, returned as (b, a)."""
    A = 10 ** (gain_db / 40)
    w0 = 2 * math.pi * f0 / SR
    alpha = math.sin(w0) / 2 * math.sqrt((A + 1 / A) * (1 / slope - 1) + 2)
    cw = math.cos(w0)
    b0 = A * ((A + 1) + (A - 1) * cw + 2 * math.sqrt(A) * alpha)
    b1 = -2 * A * ((A - 1) + (A + 1) * cw)
    b2 = A * ((A + 1) + (A - 1) * cw - 2 * math.sqrt(A) * alpha)
    a0 = (A + 1) - (A - 1) * cw + 2 * math.sqrt(A) * alpha
    a1 = 2 * ((A - 1) - (A + 1) * cw)
    a2 = (A + 1) - (A - 1) * cw - 2 * math.sqrt(A) * alpha
    return np.array([b0, b1, b2]) / a0, np.array([1.0, a1 / a0, a2 / a0])


def peaking_coeffs(f0: float, gain_db: float, q: float):
    """RBJ peaking bell, returned as (b, a)."""
    A = 10 ** (gain_db / 40)
    w0 = 2 * math.pi * f0 / SR
    alpha = math.sin(w0) / (2 * q)
    cw = math.cos(w0)
    b0 = 1 + alpha * A
    b1 = -2 * cw
    b2 = 1 - alpha * A
    a0 = 1 + alpha / A
    a1 = -2 * cw
    a2 = 1 - alpha / A
    return np.array([b0, b1, b2]) / a0, np.array([1.0, a1 / a0, a2 / a0])


def shape_bed(x: np.ndarray) -> np.ndarray:
    """A29 refined: the bass kept (under SUB_BASS_HZ, 130 Hz since rev 5 so a
    bass note's octave survives), the low-mids cut (130 to 400 Hz is a hole by
    design: the voice's fundamentals live there), the treble shelved."""
    if len(x) < 64:
        return x
    sub = signal.sosfiltfilt(_sos_butter(4, SUB_BASS_HZ, "low"), x, axis=0)
    top = signal.sosfiltfilt(_sos_butter(4, BED_LOWMID_HZ, "high"), x, axis=0)
    y = sub + top
    b, a = high_shelf_coeffs(TREBLE_HZ, TREBLE_SHELF_DB)
    return signal.filtfilt(b, a, y, axis=0)


def voice_house_eq(x: np.ndarray) -> np.ndarray:
    """A38, the house warmth for a synthetic voice: +2.5 dB bell at 200 Hz
    (Q 1.2) and a -2.5 dB high shelf with its half-gain point at 6 kHz,
    zero-phase; the caller re-levels the line afterwards."""
    if len(x) < 64:
        return x
    b, a = peaking_coeffs(200.0, 2.5, 1.2)
    y = signal.filtfilt(b, a, x)
    b, a = high_shelf_coeffs(6000.0, -2.5)
    return signal.filtfilt(b, a, y)


# ---------------------------------------------------------------------------
# The music (onair_music) and the day's voicing
# ---------------------------------------------------------------------------

try:
    from briefing import onair_music as M
except ImportError:  # pragma: no cover
    from pipeline.briefing import onair_music as M  # type: ignore

TEMPOS_BPM = (M.BPM,)


@dataclass
class Voicing:
    """The day's seed and the music's voicing drawn from it (the chord cycle
    per segment); the tempo is the house tempo."""
    seed: int
    tempo_bpm: int
    music: "M.Voicing" = field(repr=False)

    @property
    def beat_s(self) -> float:
        return 60.0 / self.tempo_bpm

    @property
    def rng(self) -> np.random.Generator:
        return self.music.rng


def voicing_for(key: str) -> Voicing:
    """The day's voicing, from a key such as 'onair:world:2026-11-07'."""
    seed = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)
    return Voicing(seed=seed, tempo_bpm=M.BPM, music=M.voicing_for(seed))


def fade(x: np.ndarray, in_s: float, out_s: float) -> np.ndarray:
    y = x.copy()
    n = len(y)
    ni = min(n, int(in_s * SR))
    no = min(n, int(out_s * SR))
    shape = (lambda w: w[:, None]) if y.ndim == 2 else (lambda w: w)
    if ni > 0:
        y[:ni] *= shape(np.sin(np.linspace(0, math.pi / 2, ni)) ** 2)
    if no > 0:
        y[n - no:] *= shape(np.cos(np.linspace(0, math.pi / 2, no)) ** 2)
    return y


def _normalise(x: np.ndarray, peak: float = 0.8) -> np.ndarray:
    m = float(np.max(np.abs(x))) if len(x) else 0.0
    return x * (peak / m) if m > 0 else x


def place(canvas: np.ndarray, x: np.ndarray, at_s: float) -> None:
    i = int(at_s * SR)
    if i >= len(canvas) or i + len(x) <= 0:
        return
    if i < 0:
        x = x[-i:]
        i = 0
    n = min(len(x), len(canvas) - i)
    if canvas.ndim == 2 and x.ndim == 1:
        canvas[i:i + n] += x[:n, None]
    elif canvas.ndim == 1 and x.ndim == 2:
        canvas[i:i + n] += np.mean(x[:n], axis=1)
    else:
        canvas[i:i + n] += x[:n]


THEME_S, PAGETURN_S, OUTRO_S = 14.0, 3.6, 15.0
ENTRANCE_S = M.ENTRANCE_S             # 11.4 s, four bars (rev 5); the music owns the number
ENTRANCE_VOICE_S = M.ENTRANCE_VOICE_S  # 9.8 s in: the anchor speaks once the hook's last note has landed
STOP_RING_S = M.STOP_RING_S           # a stopped bed: its hit is this long before its end
THEME_DOWNBEAT_S = 4 * M.BAR          # where the sign-on lands inside the theme


def render_theme(v: Voicing, dur_s: float = THEME_S, *, ir=None) -> np.ndarray:
    """The title, featured: four bars into the downbeat the sign-on lands on,
    then the pad holds under the voice."""
    x = M.render_theme(v.music, dur_s)
    return _normalise(fade(shape_bed(x), 0.01, 1.0))


def render_bed(v: Voicing, segment: str, dur_s: float, *, ir=None, ending: str = "out") -> np.ndarray:
    """`ending` is "out" (the bed thins and leaves), "rise" (it gathers into
    the transition it hands over to) or "stop" (it ends on a hit STOP_RING_S
    before its end and rings out: the desk before the Opinion's entrance). A
    stopped bed's exit fade is the ring itself, so the fade only cleans the
    last second."""
    dur_s = max(dur_s, 4.5)
    x = M.render_bed(v.music, segment, dur_s, ending=ending)
    out_s = EXIT_FADE_MIN_S + 1.0 if ending != "stop" else min(1.0, STOP_RING_S - 1.5)
    return _normalise(fade(shape_bed(x), ENTRY_FADE_MIN_S + 0.5, out_s))


def render_transition(v: Voicing, *, ir=None, dur_s: float = PAGETURN_S) -> np.ndarray:
    """The page-turn: a riser, one downbeat, the hook's first three notes."""
    x = M.render_pageturn(v.music, dur_s)
    return _normalise(fade(shape_bed(x), 0.01, 1.0))


def render_entrance(v: Voicing, *, ir=None, dur_s: float = ENTRANCE_S) -> np.ndarray:
    """"Void Opinion": the music composes its own 1.5 s swell from silence, so
    the fade only guards the edges; the held last note goes out over 1.4 s."""
    x = M.render_entrance(v.music, dur_s)
    return _normalise(fade(shape_bed(x), 0.02, 1.4))


def render_outro(v: Voicing, *, ir=None, dur_s: float = OUTRO_S) -> np.ndarray:
    x = M.render_outro(v.music, dur_s)
    return _normalise(fade(shape_bed(x), 0.02, 3.0))


def room_ir(decay_s: float = 1.4, lp_hz: float = 2600.0, seed: int = 7) -> np.ndarray:
    """Kept for callers; the music's own rooms live in onair_music.reverb."""
    rng = np.random.default_rng(seed)
    n = int(decay_s * 3 * SR)
    t = np.arange(n) / SR
    ir = rng.normal(0, 1, n) * np.exp(-t / (decay_s / 3))
    ir = signal.sosfilt(_sos_butter(2, lp_hz, "low"), ir)
    ir[0] = 1.0
    return ir / (np.max(np.abs(ir)) + 1e-9)


def room_tone(dur_s: float, seed: int = 11, level_dbfs: float = -57.0) -> np.ndarray:
    """Synthesised room tone, pink-ish, so a silence is never digital zero."""
    rng = np.random.default_rng(seed)
    n = int(dur_s * SR)
    white = rng.normal(0, 1, n)
    x = signal.sosfilt(_sos_butter(1, 900.0, "low"), white)
    x = signal.sosfilt(_sos_butter(2, 60.0, "high"), x)
    rms = math.sqrt(float(np.mean(x * x))) or 1e-9
    return x * (10 ** (level_dbfs / 20) / rms)


# ---------------------------------------------------------------------------
# The duck
# ---------------------------------------------------------------------------

def duck_envelope(total_s: float, speech: list[tuple[float, float]], *, depth_db: float = DUCK_DB,
                  preroll_s: float = DUCK_PREROLL_S, hold_s: float = DUCK_HOLD_S,
                  release_s: float = DUCK_RELEASE_S, step_s: float = 0.01) -> np.ndarray:
    """Gain in dB on a `step_s` grid: 0 in the clear, `depth_db` under voice.

    The attack eases in over `preroll_s` BEFORE the onset (a sine in-out in
    dB) and is at full depth on the onset; the duck holds through any gap
    shorter than `hold_s`; the release ramps back up over `release_s`.
    """
    n = int(math.ceil(total_s / step_s)) + 1
    env = np.zeros(n)
    if not speech:
        return env
    spans = sorted(speech)
    merged: list[list[float]] = [list(spans[0])]
    for s, e in spans[1:]:
        if s - merged[-1][1] < hold_s:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    for s, e in merged:
        a0 = max(0.0, s - preroll_s)
        i0, i1 = int(a0 / step_s), int(s / step_s)
        if s < preroll_s:
            # no room for the eased attack before the first word: the music
            # is simply down from the start (there is none there anyway)
            env[:i1] = depth_db
        elif i1 > i0:
            x = np.linspace(0, 1, i1 - i0, endpoint=False)
            ease = 0.5 - 0.5 * np.cos(math.pi * x)
            env[i0:i1] = np.minimum(env[i0:i1], depth_db * ease)
        j0, j1 = int(s / step_s), min(n, int(e / step_s))
        env[j0:j1] = depth_db
        r0, r1 = j1, min(n, j1 + int(release_s / step_s))
        if r1 > r0:
            x = np.linspace(0, 1, r1 - r0, endpoint=False)
            ease = 0.5 - 0.5 * np.cos(math.pi * x)
            env[r0:r1] = np.minimum(env[r0:r1], depth_db * (1 - ease))
    return env


def rise_into(x: np.ndarray, *, rise_db: float = RISE_DB, rise_s: float = RISE_S, hold_s: float = 0.0) -> np.ndarray:
    """The bed grows toward its end: a raised-cosine ramp of `rise_db` over the
    last `rise_s` seconds (before a final `hold_s` that stays at the top), so
    the music arrives at the transition rather than being cut off under it."""
    n = len(x)
    k = min(n, int(rise_s * SR))
    h = min(n - k, int(hold_s * SR))
    if k <= 0:
        return x
    g = np.zeros(n)
    ramp = 0.5 - 0.5 * np.cos(np.linspace(0, math.pi, k))
    g[n - k - h:n - h] = rise_db * ramp
    if h:
        g[n - h:] = rise_db
    lin = 10 ** (g / 20)
    return x * (lin[:, None] if x.ndim == 2 else lin)


def apply_envelope(x: np.ndarray, env_db: np.ndarray, step_s: float = 0.01) -> np.ndarray:
    grid = np.arange(len(env_db)) * step_s
    t = np.arange(len(x)) / SR
    g = 10 ** (np.interp(t, grid, env_db) / 20)
    return x * (g[:, None] if x.ndim == 2 else g)


# ---------------------------------------------------------------------------
# Measurement against the standard
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    id: str
    detail: str


def breath_db(x: np.ndarray) -> float:
    """100 ms level spread, p90 minus p10, over windows that are not silence."""
    x = mono(x)
    n = int(0.1 * SR)
    if len(x) < 2 * n:
        return 0.0
    m = len(x) // n
    w = x[: m * n].reshape(m, n)
    rms = np.sqrt(np.mean(w * w, axis=1))
    rms = rms[rms > 1e-6]
    if rms.size < 4:
        return 0.0
    db = 20 * np.log10(rms)
    return float(np.percentile(db, 90) - np.percentile(db, 10))


def _chroma(seg: np.ndarray) -> np.ndarray:
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    f = np.fft.rfftfreq(len(seg), 1.0 / SR)
    sel = (f >= 100.0) & (f <= 2000.0)
    midi = 69 + 12 * np.log2(f[sel] / 440.0)
    pc = np.mod(np.round(midi).astype(int), 12)
    out = np.bincount(pc, weights=spec[sel], minlength=12)
    return out / (np.linalg.norm(out) + 1e-12)


def _third_octave(seg: np.ndarray) -> np.ndarray:
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)))) ** 2
    f = np.fft.rfftfreq(len(seg), 1.0 / SR)
    edges = 25.0 * 2 ** (np.arange(0, 28) / 3.0)
    bands = np.array([spec[(f >= lo) & (f < hi)].sum() for lo, hi in zip(edges[:-1], edges[1:])])
    bands = 10 * np.log10(bands + 1e-12)
    bands = bands - bands.mean()
    return bands / (np.linalg.norm(bands) + 1e-12)


def _rhythm(seg: np.ndarray) -> np.ndarray:
    n = int(0.05 * SR)
    m = len(seg) // n
    env = np.sqrt(np.mean(seg[: m * n].reshape(m, n) ** 2, axis=1))
    flux = np.diff(env, prepend=env[:1])
    return flux


def chroma_profile(x: np.ndarray) -> np.ndarray:
    """The 12-bin pitch-class profile of a whole cue (100 Hz to 2 kHz), unit
    norm: two cues' profiles dot to their cosine similarity."""
    return _chroma(mono(x))


def clock_density(x: np.ndarray) -> float:
    """Onsets a second in the clock's band (2 to 6 kHz: ticks, rims, the
    kick's click), on a 50 ms grid, a peak of the band's level flux over its
    median plus one sigma. The news beds carry a tick on every off-beat; the
    Opinion's room carries one whisper a bar; the entrance none."""
    m = mono(x)
    if len(m) < SR:
        return 0.0
    band = signal.sosfilt(signal.butter(4, [2000.0, 6000.0], btype="band", fs=SR, output="sos"), m)
    n = int(0.05 * SR)
    k = len(band) // n
    env = np.sqrt(np.mean(band[: k * n].reshape(k, n) ** 2, axis=1))
    flux = np.diff(env, prepend=env[:1])
    thr = float(np.median(flux) + np.std(flux))
    if thr <= 1e-7:
        return 0.0
    peaks = sum(1 for i in range(1, k - 1) if flux[i] > thr and flux[i] >= flux[i - 1] and flux[i] >= flux[i + 1])
    return peaks / (k * 0.05)


def tiled_loop(x: np.ndarray, window_s: float = 4.0) -> bool:
    """True when a 4 s stretch is heard near-identically three times back to
    back (a tiled loop; twice is a restatement). Near-identical is all three
    at once: notes (12-bin chroma >= 0.97), register and orchestration
    (third-octave spectrum >= 0.95) and rhythm (envelope flux, Pearson's r
    >= 0.90), the score-repetition test of the house standard."""
    x = mono(x)
    n = int(window_s * SR)
    if len(x) < 3 * n:
        return False
    hop = n // 2

    def near(a: np.ndarray, b: np.ndarray) -> bool:
        if float(_chroma(a) @ _chroma(b)) < 0.97:
            return False
        if float(_third_octave(a) @ _third_octave(b)) < 0.95:
            return False
        ra, rb = _rhythm(a), _rhythm(b)
        if np.var(ra) < 1e-12 or np.var(rb) < 1e-12:
            return True   # a held drone has no rhythm; chroma and spectrum decide
        r = float(np.corrcoef(ra, rb)[0, 1])
        return r >= 0.90

    for s in range(0, len(x) - 3 * n + 1, hop):
        a, b, c = x[s:s + n], x[s + n:s + 2 * n], x[s + 2 * n:s + 3 * n]
        if near(a, b) and near(b, c):
            return True
    return False


def check_cue(x: np.ndarray, role: str, *, bed_peak_lufs: float | None = None,
              gaps: list[tuple[float, float]] | None = None) -> list[Finding]:
    """Measure one rendered, levelled cue against the standard. A bed's level
    is read in the voice's `gaps` (seconds into the cue) when they are given
    and total at least 4 s; otherwise over its whole length."""
    out: list[Finding] = []
    if len(x) < SR:
        return [Finding("cue-length", f"{role}: {len(x) / SR:.2f} s is not a cue")]
    treble = band_share(x, TREBLE_HZ, None, floor_hz=100.0)
    if treble > MUSIC_TREBLE_MAX_SHARE:
        out.append(Finding("music-treble", f"{role}: {treble:.1%} of the energy over 100 Hz sits above 5 kHz"))
    if role in ("bed", "featured"):
        lowmid = band_share(x, 150.0, 400.0, floor_hz=100.0)
        if lowmid > BED_LOWMID_MAX_SHARE and role == "bed":
            out.append(Finding("bed-low-end", f"{role}: {lowmid:.1%} of the energy over 100 Hz sits in 150-400 Hz"))
    if role == "bed":
        ref = x
        if gaps:
            parts = [x[int(a * SR): int(b * SR)] for a, b in gaps if b > a]
            parts = [p for p in parts if len(p)]
            if parts and sum(len(p) for p in parts) >= 4 * SR:
                ref = np.concatenate(parts)
        lv = lufs_integrated(ref)
        if lv > BED_LUFS + TOL_DB:
            out.append(Finding("bed-level", f"bed at {lv:.1f} LUFS, target {BED_LUFS}"))
        br = breath_db(x)
        if br < BED_BREATH_DB:
            out.append(Finding("bed-breathing", f"bed level spread {br:.1f} dB, needs {BED_BREATH_DB}"))
        if tiled_loop(x):
            out.append(Finding("score-repetition", "a 4 s stretch is tiled three times"))
    if role == "featured":
        st = lufs_shortterm(x)
        if st.size and float(np.max(st)) > FEATURED_LUFS + TOL_DB:
            out.append(Finding("featured-level", f"short-term max {float(np.max(st)):.1f} LUFS over {FEATURED_LUFS}"))
    if role == "transition" and bed_peak_lufs is not None:
        mom = lufs_momentary(x)
        if mom.size and float(np.max(mom)) > bed_peak_lufs + TRANSITION_OVER_BED_MAX_DB:
            out.append(Finding("transition-ceiling",
                               f"transition peaks {float(np.max(mom)):.1f} LUFS over the bed's {bed_peak_lufs:.1f}"))
    return out


def check_duck(env_db: np.ndarray, step_s: float = 0.01) -> list[Finding]:
    """duck-slope: no attack steeper than 2.0 dB in any 100 ms."""
    k = max(1, int(0.1 / step_s))
    d = env_db[k:] - env_db[:-k]
    worst = float(np.min(d)) if d.size else 0.0
    if worst < -2.0:
        return [Finding("duck-slope", f"the duck falls {-worst:.2f} dB in 100 ms; 2.0 is the limit")]
    return []


def level_featured(x: np.ndarray) -> tuple[np.ndarray, float]:
    """Level a featured cue so its LOUDEST short-term (3 s) window sits at
    FEATURED_LUFS: heard for itself, never louder."""
    st = lufs_shortterm(x)
    if st.size == 0 or not math.isfinite(float(np.max(st))):
        return level_to(x, FEATURED_LUFS)
    g = FEATURED_LUFS - float(np.max(st))
    return x * (10 ** (g / 20)), g


def level_transition(x: np.ndarray, bed_peak_lufs: float) -> tuple[np.ndarray, float]:
    """A transition is never louder than the bed it leads into: its loudest
    400 ms lands on the bed's loudest 400 ms."""
    mom = lufs_momentary(x)
    if mom.size == 0 or not math.isfinite(float(np.max(mom))):
        return level_to(x, BED_LUFS)
    g = bed_peak_lufs - float(np.max(mom))
    return x * (10 ** (g / 20)), g


def bed_peak_lufs(x: np.ndarray) -> float:
    mom = lufs_momentary(x)
    return float(np.max(mom)) if mom.size else BED_LUFS


def level_bed(x: np.ndarray, gaps: list[tuple[float, float]] | None = None) -> tuple[np.ndarray, float]:
    """Level a bed so its loudness in the voice's gaps is BED_LUFS. When the
    gaps total under 4 s the whole span is measured instead."""
    if gaps:
        parts = [x[int(s * SR): int(e * SR)] for s, e in gaps if e > s]
        parts = [p for p in parts if len(p)]
        if parts and sum(len(p) for p in parts) >= 4 * SR:
            ref = np.concatenate(parts)
            cur = lufs_integrated(ref)
            if math.isfinite(cur):
                g = BED_LUFS - cur
                return x * (10 ** (g / 20)), g
    return level_to(x, BED_LUFS)
