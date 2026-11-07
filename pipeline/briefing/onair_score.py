"""On Air: the score. One motif, composed fresh for every episode, held to the
house score standard (the `document` studio's A29 block, applied to radio).

Nothing here is a sample or a loop. Every cue is synthesised in numpy from
note data at render time, so it is Void's own, and the day's date seeds the
voicing so no two episodes carry the same bed while every episode carries the
same motif. The standard the cues are measured against, in one block:

    dialogue                 -20 LUFS integrated, per line (the producer)
    bed under speech         -32 LUFS in the voice's gaps (12 dB under)
    duck under voice         -12 dB, 1.0 s eased pre-roll, held across gaps < 1.2 s
    featured (title, outro)  -26 LUFS short-term, never louder
    transition / sting       never louder than the bed it leads into (+0.5 dB)
    band shape (beds)        sub-bass under 100 Hz kept, low-mids 150-400 Hz cut
                             (24 dB/oct high-pass at 400 Hz), treble shelf -3 dB
                             at 5 kHz; at most 2 % of a cue's energy above 5 kHz
    breathing (beds)         100 ms level spread p90-p10 >= 6 dB
    fades                    an entry from silence >= 1.5 s, an exit >= 1.5 s
    repetition               no 4 s stretch tiled three times inside a cue

Why these numbers: the founder's notes on the film studio's score, in order:
"not loud; dramatic when needed, silent when it deserves; transitions
consistent", then "a lot more bass heavy, a lot less treble, bass beats
soothingly guiding the audience", then "patterns are repeating and it's
jarring". `check_cue` and `check_duck` measure a rendered cue against the block
and return findings; `tests/test_onair_show.py` plants a defect for each.

Everything renders at SR = 48000 mono float32 in [-1, 1]. The producer mixes
it to stereo. No pydub here: this module imports only numpy and scipy.
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
BED_LUFS = -32.0                 # bed under speech, in the gaps
FEATURED_LUFS = -26.0            # title, entrance, outro: heard for themselves
TRANSITION_OVER_BED_MAX_DB = 0.5
DUCK_DB = -12.0
DUCK_PREROLL_S = 1.0             # eased attack, full depth ON the onset (A37)
DUCK_HOLD_S = 1.2                # a gap shorter than this keeps the duck
DUCK_RELEASE_S = 0.6             # the ramp back up after the hold
BED_LOWMID_HZ = 400.0            # 24 dB/oct high-pass: the low-mids go
SUB_BASS_HZ = 100.0              # 24 dB/oct low-pass: the sub-bass stays
TREBLE_HZ = 5000.0
TREBLE_SHELF_DB = -3.0
MUSIC_TREBLE_MAX_SHARE = 0.02
BED_LOWMID_MAX_SHARE = 0.10
BED_BREATH_DB = 6.0
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
    y = signal.lfilter(_K_STAGE1[0], _K_STAGE1[1], x)
    return signal.lfilter(_K_STAGE2[0], _K_STAGE2[1], y)


def _block_power(x: np.ndarray, block_s: float, hop_s: float) -> np.ndarray:
    n = int(block_s * SR)
    hop = max(1, int(hop_s * SR))
    if len(x) < n:
        return np.array([float(np.mean(x * x))]) if len(x) else np.array([])
    k = k_weight(x.astype(np.float64))
    sq = k * k
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
    up = signal.resample_poly(x.astype(np.float64), 4, 1)
    return 20 * math.log10(max(float(np.max(np.abs(up))), 1e-9))


def band_share(x: np.ndarray, lo_hz: float, hi_hz: float | None, floor_hz: float = 0.0) -> float:
    """Share of the energy above `floor_hz` that lies in [lo, hi)."""
    if len(x) < 2048:
        return 0.0
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
    """A29 refined: the sub-bass kept, the low-mids cut, the treble shelved."""
    if len(x) < 64:
        return x
    sub = signal.sosfiltfilt(_sos_butter(4, SUB_BASS_HZ, "low"), x)
    top = signal.sosfiltfilt(_sos_butter(4, BED_LOWMID_HZ, "high"), x)
    y = sub + top
    b, a = high_shelf_coeffs(TREBLE_HZ, TREBLE_SHELF_DB)
    return signal.filtfilt(b, a, y)


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
# Synthesis primitives
# ---------------------------------------------------------------------------

_NOTES = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6,
          "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def note_hz(name: str) -> float:
    i = len(name) - 1
    while i > 0 and not name[i].isdigit():
        i -= 1
    octave = int(name[i:]) if name[i:].lstrip("-").isdigit() else 4
    letter = name[:i] if name[i:].lstrip("-").isdigit() else name
    midi = 12 * (octave + 1) + _NOTES[letter]
    return 440.0 * 2 ** ((midi - 69) / 12)


def _t(n: int) -> np.ndarray:
    return np.arange(n, dtype=np.float64) / SR


def felt_pluck(hz: float, dur_s: float, *, amp: float = 1.0, bright: float = 1.0,
               rng: np.random.Generator | None = None) -> np.ndarray:
    """A soft struck string left to ring: six partials, the upper ones dying
    first, a 9 ms onset, a hair of detune so two notes never phase-lock."""
    n = int(dur_s * SR)
    t = _t(n)
    out = np.zeros(n)
    rng = rng or np.random.default_rng(0)
    for h in range(1, 7):
        decay = 0.9 / (h ** 0.9) * (1.0 + 0.3 * bright)
        a = (1.0 / h ** 1.7) * (0.6 + 0.4 * bright) if h > 1 else 1.0
        det = 1.0 + rng.normal(0, 0.0006)
        out += a * np.sin(2 * math.pi * hz * h * det * t) * np.exp(-t / decay)
    onset = np.minimum(1.0, t / 0.009)
    out *= onset
    return amp * out / (np.max(np.abs(out)) + 1e-9)


def pad_tone(hz: float, dur_s: float, *, amp: float = 1.0, attack_s: float = 2.2,
             release_s: float = 2.6, breath_hz: float = 0.09, breath_depth: float = 0.25,
             phase: float = 0.0, rng: np.random.Generator | None = None) -> np.ndarray:
    """Three detuned voices, four soft partials, a slow breath in level."""
    n = int(dur_s * SR)
    t = _t(n)
    rng = rng or np.random.default_rng(1)
    out = np.zeros(n)
    for det in (0.9985, 1.0, 1.0017):
        for h, a in ((1, 1.0), (2, 0.28), (3, 0.10), (4, 0.04)):
            out += a * np.sin(2 * math.pi * hz * h * det * t + rng.uniform(0, 2 * math.pi))
    env = np.minimum(1.0, t / max(attack_s, 1e-3))
    tail = np.minimum(1.0, (dur_s - t) / max(release_s, 1e-3))
    env = np.clip(env, 0, 1) * np.clip(tail, 0, 1)
    breath = 1.0 - breath_depth * 0.5 * (1 + np.sin(2 * math.pi * breath_hz * t + phase))
    out = out * env * breath
    sos = _sos_butter(2, 1100.0, "low")
    out = signal.sosfilt(sos, out)
    return amp * out / (np.max(np.abs(out)) + 1e-9)


def sub_pulse(hz: float, dur_s: float, *, amp: float = 1.0) -> np.ndarray:
    """One soft heartbeat on the sub: 40 ms rise, a slow fall, a small pitch
    drop over the first 80 ms so it has a front without a click."""
    n = int(dur_s * SR)
    t = _t(n)
    f = hz * (1.0 + 0.08 * np.exp(-t / 0.08))
    ph = 2 * math.pi * np.cumsum(f) / SR
    env = np.minimum(1.0, t / 0.04) * np.exp(-t / 0.42)
    x = np.sin(ph) * env
    return amp * x / (np.max(np.abs(x)) + 1e-9)


def room_ir(decay_s: float = 1.4, lp_hz: float = 2600.0, seed: int = 7) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(decay_s * 3 * SR)
    t = _t(n)
    ir = rng.normal(0, 1, n) * np.exp(-t / (decay_s / 3))
    ir = signal.sosfilt(_sos_butter(2, lp_hz, "low"), ir)
    ir[0] = 1.0
    return ir / (np.max(np.abs(ir)) + 1e-9)


def reverberate(x: np.ndarray, wet: float, ir: np.ndarray) -> np.ndarray:
    if wet <= 0 or len(x) == 0:
        return x
    w = signal.fftconvolve(x, ir)[: len(x)]
    w = w / (np.max(np.abs(w)) + 1e-9) * (np.max(np.abs(x)) + 1e-9)
    return (1 - wet) * x + wet * w


def fade(x: np.ndarray, in_s: float, out_s: float) -> np.ndarray:
    y = x.copy()
    n = len(y)
    ni = min(n, int(in_s * SR))
    no = min(n, int(out_s * SR))
    if ni > 0:
        y[:ni] *= np.sin(np.linspace(0, math.pi / 2, ni)) ** 2
    if no > 0:
        y[n - no:] *= np.cos(np.linspace(0, math.pi / 2, no)) ** 2
    return y


def place(canvas: np.ndarray, x: np.ndarray, at_s: float) -> None:
    i = int(at_s * SR)
    if i >= len(canvas) or i + len(x) <= 0:
        return
    if i < 0:
        x = x[-i:]
        i = 0
    n = min(len(x), len(canvas) - i)
    canvas[i:i + n] += x[:n]


# ---------------------------------------------------------------------------
# The motif and the day's voicing
# ---------------------------------------------------------------------------

# The house motif (generate_assets._theme_figure, unchanged in pitch): the
# cell D A D F# over a D pedal. Every cue below is a call to it.
MOTIF_CELL = ("D3", "A3", "D3", "F#3")
MOTIF_BASS = "D2"
MOTIF_SUB = "D1"

# Chord cycles, each a different colour of the same key. The day's seed
# picks one per segment and a tempo, so the bed is new every day and the
# motif is the same every day.
CYCLES = {
    # Voiced from G4 up (392 Hz and above), so a sustained chord tone never
    # sits in the voice's low-mids (150-400 Hz); the weight is the sub pulse.
    "lead": [
        [("A4", "D5", "F#5"), ("B4", "D5", "G5"), ("B4", "D5", "F#5"), ("A4", "C#5", "E5")],
        [("D5", "F#5", "A5"), ("B4", "D5", "F#5"), ("G4", "B4", "D5"), ("A4", "E5", "C#5")],
        [("A4", "D5", "F#5"), ("A4", "C#5", "F#5"), ("B4", "D5", "G5"), ("A4", "D5", "E5")],
    ],
    "second": [
        [("B4", "D5", "F#5"), ("G4", "B4", "D5"), ("A4", "D5", "F#5"), ("A4", "C#5", "E5")],
        [("G4", "B4", "E5"), ("A4", "D5", "F#5"), ("G4", "B4", "D5"), ("A4", "C#5", "E5")],
        [("G4", "B4", "D5"), ("A4", "D5", "F#5"), ("B4", "E5", "G5"), ("A4", "D5", "E5")],
    ],
    "desk": [
        [("A4", "D5", "A5"), ("G4", "D5", "E5"), ("A4", "D5", "A5"), ("G4", "B4", "D5")],
        [("A4", "D5", "F#5"), ("G4", "D5", "A5"), ("A4", "D5", "F#5"), ("A4", "D5", "E5")],
    ],
    "opinion": [
        [("A4", "D5", "F5"), ("Bb4", "D5", "F5"), ("G4", "Bb4", "D5"), ("A4", "C#5", "E5")],
        [("A4", "D5", "F5"), ("G4", "Bb4", "D5"), ("Bb4", "D5", "F5"), ("A4", "E5", "F5")],
    ],
    "close": [
        [("A4", "D5", "F#5"), ("B4", "D5", "G5"), ("A4", "C#5", "E5"), ("A4", "D5", "F#5")],
    ],
}
TEMPOS_BPM = (58, 62, 66, 72)


@dataclass
class Voicing:
    seed: int
    tempo_bpm: int
    cycle: dict[str, list[tuple[str, ...]]]
    rng: np.random.Generator = field(repr=False)

    @property
    def beat_s(self) -> float:
        return 60.0 / self.tempo_bpm


def voicing_for(key: str) -> Voicing:
    """The day's voicing, from a key such as 'onair:world:2026-11-07'."""
    seed = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    cycle = {seg: cycles[int(rng.integers(len(cycles)))] for seg, cycles in CYCLES.items()}
    tempo = TEMPOS_BPM[int(rng.integers(len(TEMPOS_BPM)))]
    return Voicing(seed=seed, tempo_bpm=tempo, cycle=cycle, rng=rng)


# ---------------------------------------------------------------------------
# Cues
# ---------------------------------------------------------------------------

def _motif_phrase(v: Voicing, *, start_s: float, canvas: np.ndarray, octave_shift: int = 0,
                  amp: float = 0.5, step_beats: float = 1.0, bright: float = 0.6) -> None:
    for k, name in enumerate(MOTIF_CELL):
        hz = note_hz(name) * (2 ** octave_shift)
        place(canvas, felt_pluck(hz, 3.2, amp=amp * (0.85 + 0.15 * (k % 2)), bright=bright, rng=v.rng),
              start_s + k * step_beats * v.beat_s)


def _bed_core(v: Voicing, segment: str, dur_s: float, *, pulse: bool, pulse_every_beats: float,
              motif_every_s: float, motif_octave: int, pad_amp: float, pluck_amp: float,
              chord_s: float, ir: np.ndarray) -> np.ndarray:
    """A bed: slow pad chords, a sub heartbeat, sparse motif fragments at
    irregular bars, no two bars alike. Composed to length; never looped."""
    n = int(dur_s * SR)
    pad = np.zeros(n)
    plucks = np.zeros(n)
    subs = np.zeros(n)
    chords = v.cycle[segment]
    t = 0.0
    i = 0
    while t < dur_s:
        chord = chords[i % len(chords)]
        length = min(chord_s, dur_s - t) + 2.4   # overlap into the next chord
        for j, name in enumerate(chord):
            amp = pad_amp * (1.0 if j == 0 else 0.7)
            place(pad, pad_tone(note_hz(name), length, amp=amp, attack_s=2.4, release_s=2.6,
                                breath_hz=0.07 + 0.02 * j, breath_depth=0.3,
                                phase=float(v.rng.uniform(0, 6.28)), rng=v.rng), t)
        # a regional pluck at most once a chord: the chord's root, low
        if v.rng.random() < 0.55:
            root_hz = note_hz(chord[0])
            if root_hz < BED_LOWMID_HZ:
                root_hz *= 2.0     # a sustained root in the low-mids is taken out of the score
            place(plucks, felt_pluck(root_hz, 3.0, amp=pluck_amp * 0.7, bright=0.3, rng=v.rng),
                  t + v.beat_s * float(v.rng.integers(1, 4)))
        t += chord_s
        i += 1
    if pulse:
        root_hz = note_hz(MOTIF_SUB)
        beat = 0.0
        while beat < dur_s:
            # a rest in two beats of eight, drawn, so the pulse breathes
            if v.rng.random() > 0.25:
                place(subs, sub_pulse(root_hz, 1.4, amp=1.0), beat)
            beat += pulse_every_beats * v.beat_s
    # motif fragments at irregular distances, never twice in the same bar
    at = motif_every_s * (0.6 + 0.6 * v.rng.random())
    while at < dur_s - 6.0:
        _motif_phrase(v, start_s=at, canvas=plucks, octave_shift=motif_octave, amp=pluck_amp,
                      step_beats=1.0 if v.rng.random() < 0.6 else 0.5)
        at += motif_every_s * (0.7 + 0.8 * v.rng.random())
    mix = reverberate(pad, 0.35, ir) + reverberate(plucks, 0.45, ir) + subs * 0.9
    return mix


def _normalise(x: np.ndarray, peak: float = 0.8) -> np.ndarray:
    m = float(np.max(np.abs(x))) if len(x) else 0.0
    return x * (peak / m) if m > 0 else x


def render_theme(v: Voicing, dur_s: float = 7.0, *, ir: np.ndarray | None = None) -> np.ndarray:
    """The title: the sub, a D pad opening, the motif twice (low, then up an
    octave, brighter), landing on the fifth. Featured: it is heard for itself."""
    ir = ir if ir is not None else room_ir(1.8, 2400.0, v.seed)
    n = int(dur_s * SR)
    c = np.zeros(n)
    place(c, pad_tone(note_hz("D2"), dur_s, amp=0.5, attack_s=1.2, release_s=2.0, breath_depth=0.15, rng=v.rng), 0.0)
    place(c, pad_tone(note_hz("A4"), dur_s - 0.8, amp=0.22, attack_s=2.0, release_s=2.0, breath_depth=0.2, rng=v.rng), 0.8)
    beats = [0.0, 1.0, 2.0, 3.0]
    for b in beats:
        place(c, sub_pulse(note_hz(MOTIF_SUB), 1.4, amp=0.9), b * v.beat_s)
    _motif_phrase(v, start_s=0.25 * v.beat_s, canvas=c, octave_shift=0, amp=0.55, step_beats=0.5, bright=0.45)
    _motif_phrase(v, start_s=2.4 * v.beat_s, canvas=c, octave_shift=1, amp=0.45, step_beats=0.5, bright=0.7)
    place(c, felt_pluck(note_hz("A4"), 3.5, amp=0.35, bright=0.6, rng=v.rng), 4.5 * v.beat_s)
    out = reverberate(c, 0.4, ir)
    out = shape_bed(out)
    return _normalise(fade(out, 0.02, 1.8))


def render_bed(v: Voicing, segment: str, dur_s: float, *, ir: np.ndarray | None = None) -> np.ndarray:
    ir = ir if ir is not None else room_ir(1.6, 2200.0, v.seed + 1)
    dur_s = max(dur_s, 4.5)
    if segment == "lead":
        x = _bed_core(v, "lead", dur_s, pulse=True, pulse_every_beats=2.0, motif_every_s=16.0,
                      motif_octave=1, pad_amp=0.42, pluck_amp=0.4, chord_s=4 * v.beat_s * 2, ir=ir)
    elif segment == "second":
        x = _bed_core(v, "second", dur_s, pulse=True, pulse_every_beats=2.0, motif_every_s=18.0,
                      motif_octave=2, pad_amp=0.36, pluck_amp=0.36, chord_s=4 * v.beat_s * 2, ir=ir)
    elif segment == "desk":
        x = _bed_core(v, "desk", dur_s, pulse=True, pulse_every_beats=1.0, motif_every_s=12.0,
                      motif_octave=2, pad_amp=0.30, pluck_amp=0.42, chord_s=4 * v.beat_s, ir=ir)
    elif segment == "opinion":
        x = _bed_core(v, "opinion", dur_s, pulse=True, pulse_every_beats=3.0, motif_every_s=22.0,
                      motif_octave=2, pad_amp=0.44, pluck_amp=0.3, chord_s=4 * v.beat_s * 2, ir=ir)
    else:
        x = _bed_core(v, "close", dur_s, pulse=True, pulse_every_beats=2.0, motif_every_s=10.0,
                      motif_octave=1, pad_amp=0.42, pluck_amp=0.4, chord_s=4 * v.beat_s, ir=ir)
    x = shape_bed(x)
    return _normalise(fade(x, ENTRY_FADE_MIN_S + 0.5, EXIT_FADE_MIN_S + 1.0))


def render_transition(v: Voicing, *, ir: np.ndarray | None = None, dur_s: float = 3.4) -> np.ndarray:
    """The motif's cell alone, in the clear: a page turned, not a jingle."""
    ir = ir if ir is not None else room_ir(1.6, 2200.0, v.seed + 2)
    n = int(dur_s * SR)
    c = np.zeros(n)
    _motif_phrase(v, start_s=0.05, canvas=c, octave_shift=0, amp=0.5, step_beats=0.5, bright=0.5)
    place(c, sub_pulse(note_hz(MOTIF_SUB), 1.2, amp=0.7), 0.0)
    out = shape_bed(reverberate(c, 0.4, ir))
    return _normalise(fade(out, 0.01, 1.2))


def render_entrance(v: Voicing, *, ir: np.ndarray | None = None, dur_s: float = 6.0) -> np.ndarray:
    """The opinion entrance: minor shading, a dotted sub pulse, ends on an
    open fifth. Featured, so the segment is announced by the music alone."""
    ir = ir if ir is not None else room_ir(2.0, 2000.0, v.seed + 3)
    n = int(dur_s * SR)
    c = np.zeros(n)
    place(c, pad_tone(note_hz("D2"), dur_s, amp=0.45, attack_s=1.0, release_s=2.2, breath_depth=0.15, rng=v.rng), 0.0)
    place(c, pad_tone(note_hz("F3"), dur_s - 0.6, amp=0.22, attack_s=1.6, release_s=2.0, rng=v.rng), 0.6)
    for k, b in enumerate((0.0, 1.5, 2.0, 3.5, 4.0)):
        place(c, sub_pulse(note_hz(MOTIF_SUB), 1.3, amp=0.85 if k % 2 == 0 else 0.6), b * v.beat_s * 0.8)
    for k, name in enumerate(("D3", "F3", "A3", "D4")):
        place(c, felt_pluck(note_hz(name), 3.0, amp=0.42, bright=0.4, rng=v.rng), 0.3 + k * 0.6 * v.beat_s)
    place(c, felt_pluck(note_hz("A3"), 3.6, amp=0.4, bright=0.4, rng=v.rng), dur_s - 2.4)
    out = shape_bed(reverberate(c, 0.45, ir))
    return _normalise(fade(out, 0.02, 1.6))


def render_outro(v: Voicing, *, ir: np.ndarray | None = None, dur_s: float = 14.0) -> np.ndarray:
    """Four bars resolving to the low D, then the fall to true silence."""
    ir = ir if ir is not None else room_ir(2.2, 2200.0, v.seed + 4)
    n = int(dur_s * SR)
    c = np.zeros(n)
    chords = CYCLES["close"][0]
    for i, chord in enumerate(chords):
        at = i * 2 * v.beat_s
        for j, name in enumerate(chord):
            place(c, pad_tone(note_hz(name), 4.5 * v.beat_s, amp=0.4 if j == 0 else 0.26, attack_s=0.9,
                              release_s=1.8, breath_depth=0.15, rng=v.rng), at)
        place(c, sub_pulse(note_hz(MOTIF_SUB), 1.4, amp=0.9), at)
    _motif_phrase(v, start_s=0.3, canvas=c, octave_shift=0, amp=0.5, step_beats=0.5, bright=0.5)
    _motif_phrase(v, start_s=4 * v.beat_s + 0.3, canvas=c, octave_shift=1, amp=0.4, step_beats=0.5, bright=0.6)
    land = 8 * v.beat_s
    place(c, felt_pluck(note_hz("D3"), 5.5, amp=0.55, bright=0.3, rng=v.rng), land)
    place(c, pad_tone(note_hz("D2"), dur_s - land, amp=0.5, attack_s=0.6, release_s=4.5, breath_depth=0.1, rng=v.rng), land)
    place(c, sub_pulse(note_hz(MOTIF_SUB), 2.0, amp=1.0), land)
    out = shape_bed(reverberate(c, 0.42, ir))
    return _normalise(fade(out, 0.02, 4.5))


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


def apply_envelope(x: np.ndarray, env_db: np.ndarray, step_s: float = 0.01) -> np.ndarray:
    grid = np.arange(len(env_db)) * step_s
    t = _t(len(x))
    g = np.interp(t, grid, env_db)
    return x * (10 ** (g / 20))


# ---------------------------------------------------------------------------
# Measurement against the standard
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    id: str
    detail: str


def breath_db(x: np.ndarray) -> float:
    """100 ms level spread, p90 minus p10, over windows that are not silence."""
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


def tiled_loop(x: np.ndarray, window_s: float = 4.0) -> bool:
    """True when a 4 s stretch is heard near-identically three times back to
    back (a tiled loop; twice is a restatement). Near-identical is all three
    at once: notes (12-bin chroma >= 0.97), register and orchestration
    (third-octave spectrum >= 0.95) and rhythm (envelope flux, Pearson's r
    >= 0.90), the score-repetition test of the house standard."""
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
