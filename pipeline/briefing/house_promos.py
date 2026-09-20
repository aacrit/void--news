"""House promos: two-sentence cross-promos stitched under the outro of every
Void audio programme.

A promo is publishing. It is rendered once and plays for years, so the rules
here are the editorial rules, not marketing rules:

* exactly two sentences, a pitch and a pointer; the second sentence names
  the site;
* no number that can go stale (no source, country or episode counts); the
  few number words allowed are each tied to a constant in the code and the
  test asserts the tie;
* nothing borrowed from radio ("stay with us", "and finally"), nothing from
  the kill list in `docs/VOICE-BRAND.md`;
* never inside the section it advertises.

Placement is a producer decision, not a script marker. Every programme has a
closed set of segment kinds and a validator that fails the rundown on an
unknown one, and every programme ends on a designed beat (On Air's tag,
Weekly's open question, History's particular). The promo goes AFTER that
beat, under the outro's held bars, and the outro's own fall to silence still
closes the file. Because it sits under music that is already there, the
programme's length does not change and no duration gate moves.

Selection is deterministic: the episode key (a date and slot, a week, a slug)
is hashed into the eligible pool, so a re-render never silently changes the
audio and a test can name the promo an episode carries.

    python3 pipeline/briefing/house_promos.py validate
    python3 pipeline/briefing/house_promos.py fill-seconds
    python3 pipeline/briefing/house_promos.py select history history:partition-of-india
    python3 pipeline/briefing/house_promos.py render      # needs .venv-tts
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POOL = ROOT / "data" / "promos" / "house.yaml"
RENDER_DIR = ROOT / "data" / "promos" / "rendered"
FEED_CONFIG = ROOT / "frontend" / "config" / "feed.json"

SITE_HOST = "news.voidvision.org"
# Kokoro's G2P reads a bare dot as a full stop and "voidvision" as one word.
# Spelling the dots is the one form that comes out as an address.
SPOKEN_HOST = "news dot void vision dot org"

SECTIONS = ("onair", "weekly", "history")
PROMOTABLE = SECTIONS + ("site",)
SECTION_NAMES = {"onair": "On Air", "weekly": "Weekly", "history": "History",
                 "site": "Void News"}

# The house voice anchors nothing: On Air is am_puck / af_bella / af_heart,
# Weekly is bm_lewis / am_michael / af_heart, History casts from six narrators
# in casting.py. A voice the listener has not heard for the last quarter of an
# hour is what makes the promo read as the station rather than the presenter
# coming back. af_kore is on the ear-tested alternates list in
# docs/ON-AIR-RADIO.md; bf_emma is the alternate for the CEO ear test.
HOUSE_VOICE = os.environ.get("VOID_PROMO_VOICE", "af_kore")
HOUSE_SPEED = float(os.environ.get("VOID_PROMO_SPEED", "0.95") or 0.95)
HOUSE_WPM = 181.0 * HOUSE_SPEED   # af_kore's measured natural rate, house pace

MIN_SECONDS = 5.0
MAX_SECONDS = 9.0
RENDER_TOLERANCE = 0.5            # a real render may land this far outside

# Every number word a promo may say, and the fact in the code it is tied to.
# Digits are banned outright; anything not listed here fails P-05.
ALLOWED_NUMBER_WORDS = {
    "one": "a count of programmes or events, never of sources",
    "two": "two benches (weekly_script), a second voice (H-02)",
    "four": "DEEP_STORIES in radio_script_generator (R-08)",
    "five": "the Partition script: five weeks (data/history/scripts)",
    "fifteen": "verify_audio A-04: the served show is under 840 s",
    "twenty": "frontend/config/feed.json displayed, asserted at validation",
}

ALLOWED_CLAIMS = {
    "feed_size", "same_order", "no_accounts", "free", "no_tracking",
    "both_outlet_and_words", "rules_public", "outlets_shown", "sources_spectrum",
    "onair_four_stories", "onair_under_fifteen", "onair_cold_open",
    "onair_no_thanks", "onair_room_tone", "onair_opinion_firewall",
    "onair_ranking", "onair_daily",
    "weekly_two_benches", "weekly_verbatim_column", "weekly_open_question",
    "weekly_sunday", "weekly_week_in_bias", "weekly_no_host_side",
    "history_perspectives", "history_leaves_out", "history_document_voice",
    "history_particular", "history_quarter_hour", "history_cold_open",
    "history_partition_five_weeks", "history_one_event",
}

# Timing under the outro. The outro asset holds its bars for about 8.25 s,
# then falls over 5.5 s and is silent from 13.75 s. The promo starts a beat
# after the last spoken word and must be finished well before the silence,
# so the outro's own fall still closes the programme.
OUTRO_MS = 14000
OUTRO_SILENT_MS = 13750
END_MARGIN_MS = 1500
LEAD_MS = 1200
DUCK_DB = -8.0
RAMP_MS = 250

PROMO_CHAPTER_TITLE = "Also from Void"
HISTORY_PROMO_CHAPTER_TITLE = "Also from Void News"


class PromoDoesNotFit(ValueError):
    """The promo would run into the outro's fall to silence."""


@dataclass(frozen=True)
class Promo:
    id: str
    promotes: str
    plays_in: tuple[str, ...]
    text: str
    seconds: float
    angle: str
    claims: tuple[str, ...]
    names_url: bool
    spoken: str | None = None

    @property
    def sha(self) -> str:
        return hashlib.sha256(self.text.encode("utf-8")).hexdigest()[:12]

    @property
    def promoted_name(self) -> str:
        return SECTION_NAMES.get(self.promotes, self.promotes)


# ---------------------------------------------------------------------------
# Pool
# ---------------------------------------------------------------------------

def load_pool(path: Path = POOL) -> list[Promo]:
    import yaml  # pyyaml is in pipeline/requirements.txt

    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    rows = data.get("promos") or []
    out: list[Promo] = []
    for r in rows:
        plays = r.get("plays_in") or []
        if isinstance(plays, str):
            plays = [plays]
        claims = r.get("claims") or []
        if isinstance(claims, str):
            claims = [claims]
        out.append(Promo(
            id=str(r.get("id", "")).strip(),
            promotes=str(r.get("promotes", "")).strip(),
            plays_in=tuple(str(p).strip() for p in plays),
            text=str(r.get("text", "")).strip(),
            seconds=float(r.get("seconds") or 0.0),
            angle=str(r.get("angle", "")).strip(),
            claims=tuple(str(c).strip() for c in claims),
            names_url=bool(r.get("names_url", False)),
            spoken=(str(r["spoken"]).strip() if r.get("spoken") else None),
        ))
    return sorted(out, key=lambda p: p.id)


# ---------------------------------------------------------------------------
# Text
# ---------------------------------------------------------------------------

_URL_RE = re.compile(re.escape(SITE_HOST), re.IGNORECASE)
_DOTTED_ABBREV_RE = re.compile(r"\b(?:[A-Za-z]\.){2,}")
_SENTENCE_END_RE = re.compile(r"[.!?]+(?:\s+|$)")
_WORD_RE = re.compile(r"[A-Za-z']+")


def sentences(text: str) -> list[str]:
    """Split on sentence ends after masking the address and dotted
    abbreviations, so "news.voidvision.org" and "U.S." do not count."""
    masked = _URL_RE.sub("SITEHOST", text)
    masked = _DOTTED_ABBREV_RE.sub(lambda m: m.group(0).replace(".", ""), masked)
    parts = [p.strip() for p in _SENTENCE_END_RE.split(masked)]
    return [p for p in parts if p]


def spoken_form(promo: Promo) -> str:
    """What the TTS is handed. The written text keeps the real address."""
    from briefing.spoken_text import normalize_for_speech

    base = promo.spoken or _URL_RE.sub(SPOKEN_HOST, promo.text)
    return normalize_for_speech(base)


def spoken_words(promo: Promo) -> int:
    return len(_WORD_RE.findall(_URL_RE.sub(SPOKEN_HOST, promo.spoken or promo.text)))


def estimate_seconds(promo: Promo) -> float:
    """Words at the house rate, plus a beat at the sentence break and a tail."""
    words = spoken_words(promo)
    breaks = max(0, len(sentences(promo.text)) - 1)
    return round(words / (HOUSE_WPM / 60.0) + 0.35 * breaks + 0.30, 1)


def _number_words() -> set[str]:
    from briefing.spoken_text import _ONES, _SCALES, _TENS  # type: ignore

    words = set(w for w in _ONES if w) | set(w for w in _TENS if w)
    words |= {name for _, name in _SCALES}
    words |= {"hundred", "thousand", "million", "billion", "dozen", "half"}
    return words


def _banned_phrases() -> list[str]:
    from briefing.radio_script_generator import BANNED_PHRASES
    from briefing.weekly_script import BORROWED

    seen: list[str] = []
    for p in tuple(BANNED_PHRASES) + tuple(BORROWED):
        if p not in seen:
            seen.append(p)
    return seen


def feed_size() -> int | None:
    try:
        return int(json.loads(FEED_CONFIG.read_text()).get("displayed"))
    except (OSError, ValueError, TypeError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(promos: list[Promo]) -> list[str]:
    """Every finding is a reason the pool must not render. Rules:

    P-01 unique id, known promotes, known plays_in, never self-promoting
    P-02 exactly two sentences
    P-03 no digits
    P-04 number words only from ALLOWED_NUMBER_WORDS
    P-05 "twenty" only while feed.json says twenty, and only with feed_size
    P-06 nothing borrowed, nothing from the kill list
    P-07 no em or en dash, no quotation marks, no exclamation mark
    P-08 names_url agrees with the text
    P-09 5-9 s estimated, and the recorded seconds are within a second of it
    P-10 claims are known; every section has at least three eligible promos
    """
    from utils.prohibited_terms import check_prohibited_terms

    findings: list[str] = []
    ids: set[str] = set()
    numbers = _number_words()
    banned = _banned_phrases()
    size = feed_size()
    size_word = None
    if size is not None:
        from briefing.spoken_text import number_words
        size_word = number_words(size)

    for p in promos:
        tag = p.id or "<no id>"
        if not p.id or p.id in ids:
            findings.append(f"P-01 {tag}: id missing or duplicated")
        ids.add(p.id)
        if p.promotes not in PROMOTABLE:
            findings.append(f"P-01 {tag}: promotes {p.promotes!r} is not one of {PROMOTABLE}")
        if not p.plays_in or any(s not in SECTIONS for s in p.plays_in):
            findings.append(f"P-01 {tag}: plays_in {p.plays_in!r} must be a subset of {SECTIONS}")
        if p.promotes in p.plays_in:
            findings.append(f"P-01 {tag}: a promo never plays inside the section it advertises")

        n = len(sentences(p.text))
        if n != 2:
            findings.append(f"P-02 {tag}: {n} sentence(s), must be exactly two")

        if re.search(r"\d", p.text):
            findings.append(f"P-03 {tag}: digits are not spoken and go stale; write the word or drop the number")

        toks = [t.lower() for t in _WORD_RE.findall(p.text)]
        bad = sorted({t for t in toks if t in numbers and t not in ALLOWED_NUMBER_WORDS})
        if bad:
            findings.append(f"P-04 {tag}: number word(s) {bad} are not tied to anything in the code")

        if "twenty" in toks:
            if "feed_size" not in p.claims:
                findings.append(f"P-05 {tag}: says twenty without the feed_size claim")
            if size_word != "twenty":
                findings.append(f"P-05 {tag}: says twenty but frontend/config/feed.json displayed is {size}")
        if "feed_size" in p.claims and size_word and size_word not in toks:
            findings.append(f"P-05 {tag}: carries feed_size but never says {size_word!r}")

        low = p.text.lower()
        hits = [b for b in banned if b in low]
        hits += check_prohibited_terms(p.text, context=tag)
        if hits:
            findings.append(f"P-06 {tag}: borrowed or prohibited: {hits[:4]}")

        if "—" in p.text or "–" in p.text:
            findings.append(f"P-07 {tag}: em or en dash in written copy")
        if any(q in p.text for q in ('"', "“", "”")):
            findings.append(f"P-07 {tag}: quotation marks")
        if "!" in p.text:
            findings.append(f"P-07 {tag}: exclamation mark")

        if p.names_url != (SITE_HOST in p.text):
            findings.append(f"P-08 {tag}: names_url={p.names_url} but the address "
                            f"{'is' if SITE_HOST in p.text else 'is not'} in the text")
        if SITE_HOST not in p.text:
            findings.append(f"P-08 {tag}: the second sentence must send the listener to {SITE_HOST}")

        est = estimate_seconds(p)
        if not (MIN_SECONDS <= est <= MAX_SECONDS):
            findings.append(f"P-09 {tag}: estimated {est}s, must be {MIN_SECONDS}-{MAX_SECONDS}s "
                            f"({spoken_words(p)} spoken words)")
        if abs(est - p.seconds) > 1.0:
            findings.append(f"P-09 {tag}: recorded seconds {p.seconds} vs estimate {est}; run fill-seconds")

        unknown = [c for c in p.claims if c not in ALLOWED_CLAIMS]
        if unknown:
            findings.append(f"P-10 {tag}: unknown claim(s) {unknown}")

    for s in SECTIONS:
        n = len(eligible(promos, s))
        if n < 3:
            findings.append(f"P-10 {s}: only {n} eligible promo(s), need at least three")
    return findings


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

def eligible(promos: list[Promo], plays_in: str) -> list[Promo]:
    return sorted((p for p in promos if plays_in in p.plays_in and p.promotes != plays_in),
                  key=lambda p: p.id)


def select(plays_in: str, key: str, promos: list[Promo] | None = None) -> Promo | None:
    pool = eligible(promos if promos is not None else load_pool(), plays_in)
    if not pool:
        return None
    n = int(hashlib.sha256(key.encode("utf-8")).hexdigest(), 16) % len(pool)
    return pool[n]


def enabled() -> bool:
    return os.environ.get("VOID_HOUSE_PROMOS", "1").strip() != "0"


# ---------------------------------------------------------------------------
# Rendering (needs the TTS venv; runs in CI)
# ---------------------------------------------------------------------------

def _manifest_path(render_dir: Path) -> Path:
    return render_dir / "manifest.json"


def load_manifest(render_dir: Path = RENDER_DIR) -> dict:
    p = _manifest_path(render_dir)
    if not p.exists():
        return {"promos": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"promos": {}}
    except json.JSONDecodeError:
        return {"promos": {}}


def render_all(out_dir: Path = RENDER_DIR, engine=None, deadline_s: float = 900.0) -> dict:
    """Render every promo once, raw 24 kHz mono, and write the manifest.

    The WAVs are committed: 24 files of a few hundred KB each, re-rendered
    only when the text changes (the manifest records the sha of the text each
    file was made from, and `load_render` refuses a stale one).
    """
    from briefing.tts_engines import KokoroEngine, TurnSpec

    promos = load_pool()
    findings = validate(promos)
    if findings:
        raise ValueError("pool does not validate:\n  " + "\n  ".join(findings))
    out_dir.mkdir(parents=True, exist_ok=True)
    eng = engine or KokoroEngine(voices={"A": HOUSE_VOICE}, speed={"A": HOUSE_SPEED})
    turns = [TurnSpec(idx=i, role="A", text=spoken_form(p), speed=None)
             for i, p in enumerate(promos)]
    res = eng.synthesize_batch(turns, deadline_s=deadline_s)
    manifest = {"generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "voice": HOUSE_VOICE, "speed": HOUSE_SPEED,
                "engine": getattr(eng, "name", "kokoro"), "promos": {}}
    problems: list[str] = []
    for i, p in enumerate(promos):
        seg = res.audio.get(i)
        if seg is None:
            problems.append(f"{p.id}: no audio returned")
            continue
        seconds = round(len(seg) / 1000.0, 2)
        if not (MIN_SECONDS - RENDER_TOLERANCE <= seconds <= MAX_SECONDS + RENDER_TOLERANCE):
            problems.append(f"{p.id}: rendered {seconds}s, outside "
                            f"{MIN_SECONDS - RENDER_TOLERANCE}-{MAX_SECONDS + RENDER_TOLERANCE}s")
        path = out_dir / f"{p.id}.wav"
        seg.export(str(path), format="wav")
        manifest["promos"][p.id] = {"sha": p.sha, "seconds": seconds,
                                    "bytes": path.stat().st_size}
    _manifest_path(out_dir).write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    if problems:
        raise RuntimeError("promo render problems:\n  " + "\n  ".join(problems))
    return manifest


def load_render(promo: Promo, render_dir: Path = RENDER_DIR):
    """The raw render for a promo, or None when it is missing or was made from
    different text. A producer that gets None ships without a promo."""
    entry = (load_manifest(render_dir).get("promos") or {}).get(promo.id)
    path = render_dir / f"{promo.id}.wav"
    if not entry or entry.get("sha") != promo.sha or not path.exists():
        return None
    from pydub import AudioSegment

    return AudioSegment.from_file(str(path), format="wav")


# ---------------------------------------------------------------------------
# Audio
# ---------------------------------------------------------------------------

def voiced(seg, work: Path, label: str = "P"):
    """The promo through the same per-voice chain as the programme's voices,
    centred, so it sits at the level of the speech around it."""
    from briefing import radio_producer as rp

    return rp.process_voice_bus(seg, 0.0, work, label)


def mastered(seg, work: Path, label: str = "P"):
    """For the retrofit: voiced, then normalised to the programme target
    (-16 LUFS, -1 dBTP), 44.1 kHz stereo, like the episode it joins."""
    from pydub import AudioSegment

    from briefing import radio_producer as rp

    v = voiced(seg, work, label)
    src = work / f"promo_{label}.wav"
    dst = work / f"promo_{label}_master.wav"
    v.export(str(src), format="wav")
    rp.loudnorm_two_pass(src, dst)
    if dst.exists():
        return AudioSegment.from_file(str(dst), format="wav")
    return v.set_frame_rate(44100).set_channels(2)


def _duck_window(mix, start_ms: int, end_ms: int, duck_db: float, ramp_ms: int):
    """Raised-cosine gain dip over [start, end], ramps outside it."""
    try:
        import numpy as np
    except Exception:
        # pydub fallback: three slices, gain on the middle, short fades.
        a = max(0, start_ms - ramp_ms)
        b = min(len(mix), end_ms + ramp_ms)
        mid = (mix[a:b] + duck_db).fade_in(min(ramp_ms, b - a)).fade_out(min(ramp_ms, b - a))
        return mix[:a] + mid + mix[b:]
    floor = 10 ** (duck_db / 20.0)
    a = max(0, start_ms - ramp_ms)
    b = min(len(mix), end_ms + ramp_ms)
    window = mix[a:b]
    ch = window.channels
    samples = np.array(window.get_array_of_samples()).astype(np.float32)
    frames = len(samples) // ch
    t = np.arange(frames) * (1000.0 / window.frame_rate) + a
    gain = np.ones(frames, dtype=np.float32)
    # fade down over [start - ramp, start], hold at floor, fade up over [end, end + ramp]
    down = (t >= start_ms - ramp_ms) & (t < start_ms)
    hold = (t >= start_ms) & (t <= end_ms)
    up = (t > end_ms) & (t <= end_ms + ramp_ms)
    x = (t[down] - (start_ms - ramp_ms)) / max(1, ramp_ms)
    gain[down] = 1.0 - (1.0 - floor) * (0.5 - 0.5 * np.cos(math.pi * x))
    gain[hold] = floor
    x = (t[up] - end_ms) / max(1, ramp_ms)
    gain[up] = floor + (1.0 - floor) * (0.5 - 0.5 * np.cos(math.pi * x))
    if ch > 1:
        gain = np.repeat(gain, ch)
    out = np.clip(samples[: len(gain)] * gain, -32768, 32767).astype(np.int16)
    return mix[:a] + window._spawn(out.tobytes()) + mix[b:]


def stitch_post_roll(mix, outro_at_ms: int, promo, *, last_word_ms: int | None = None,
                     lead_ms: int = LEAD_MS, duck_db: float = DUCK_DB, ramp_ms: int = RAMP_MS,
                     promo_gain_db: float = 0.0):
    """Lay the promo under the outro's held bars. Returns (mix, promo_at_ms).

    The mix's length never changes: the promo is overlaid, the music under it
    is dipped, and the outro's fall and the room tone after it are untouched.
    """
    anchor = last_word_ms if last_word_ms is not None else outro_at_ms
    promo_at = int(anchor + lead_ms)
    promo_end = promo_at + len(promo)
    latest = outro_at_ms + OUTRO_SILENT_MS - END_MARGIN_MS
    if promo_end > latest:
        raise PromoDoesNotFit(f"promo ends at {promo_end} ms, latest allowed {latest} ms "
                              f"({(promo_end - latest) / 1000:.1f}s too long)")
    if promo_end > len(mix):
        raise PromoDoesNotFit(f"promo ends at {promo_end} ms past the mix ({len(mix)} ms)")
    p = promo.set_frame_rate(mix.frame_rate).set_channels(mix.channels)
    if promo_gain_db:
        p = p + promo_gain_db
    ducked = _duck_window(mix, promo_at, promo_end, duck_db, ramp_ms)
    return ducked.overlay(p, position=promo_at), promo_at


def append_promo_chapter(chapters: list[dict], promo: Promo, at_ms: int, total_ms: int, *,
                         kind: str = "promo", title: str = PROMO_CHAPTER_TITLE) -> list[dict]:
    """A chapter for the promo, so the player and the sidecar tell the truth
    about what plays where. The previous chapter closes where the promo
    starts; the promo runs to the end of the file."""
    at_s = round(at_ms / 1000.0, 3)
    total_s = round(total_ms / 1000.0, 3)
    out = [dict(c) for c in chapters]
    if out and isinstance(out[-1].get("endTime"), (int, float)) and out[-1]["endTime"] > at_s:
        out[-1]["endTime"] = at_s
    out.append({"startTime": at_s, "endTime": total_s, "title": title, "kind": kind,
                "subtitle": promo.promoted_name, "promo": promo.id})
    return out


def post_roll(mix, *, outro_at_ms: int, last_word_ms: int | None, plays_in: str, key: str,
              work: Path, render_dir: Path = RENDER_DIR, label: str = "P"):
    """What a producer calls: pick, load, voice, stitch. Returns (mix, info).
    `info` is None when promos are off or no render exists; the programme
    then ships exactly as it did before."""
    if not enabled():
        return mix, None
    try:
        promo = select(plays_in, key)
    except Exception as e:  # a broken pool must not take the programme down
        print(f"  [promo] pool unreadable ({e}); shipping without a promo")
        return mix, None
    if promo is None:
        return mix, None
    raw = load_render(promo, render_dir)
    if raw is None:
        print(f"  [promo] no render for {promo.id}; shipping without a promo")
        return mix, None
    try:
        stitched, at = stitch_post_roll(mix, outro_at_ms, voiced(raw, work, label),
                                        last_word_ms=last_word_ms)
    except PromoDoesNotFit as e:
        print(f"  [promo] {promo.id} does not fit ({e}); shipping without a promo")
        return mix, None
    info = {"id": promo.id, "sha": promo.sha, "voice": HOUSE_VOICE, "at_ms": at,
            "seconds": round(len(raw) / 1000.0, 2), "promotes": promo.promotes}
    print(f"  [promo] {promo.id} ({promo.promoted_name}) at {at / 1000:.1f}s in {plays_in}")
    return stitched, info


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _fill_seconds(path: Path = POOL) -> int:
    """Rewrite the `seconds` field of every promo from the estimate."""
    text = path.read_text(encoding="utf-8")
    promos = load_pool(path)
    for p in promos:
        est = estimate_seconds(p)
        pat = re.compile(rf"(- id: {re.escape(p.id)}\n(?:(?!- id:).*\n)*?\s+seconds:) *[0-9.]+")
        text, n = pat.subn(rf"\g<1> {est}", text, count=1)
        if n == 0:
            print(f"  [promo] no seconds line for {p.id}", file=sys.stderr)
    path.write_text(text, encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else "validate"
    if cmd == "validate":
        promos = load_pool()
        findings = validate(promos)
        for p in promos:
            print(f"  {p.id:<26} {p.promotes:<7} in {','.join(p.plays_in):<21} "
                  f"{estimate_seconds(p):>4}s  {spoken_words(p):>2}w")
        if findings:
            print("\n".join(f"FAIL  {f}" for f in findings))
            return 1
        print(f"OK    {len(promos)} promos; eligible per section: "
              + ", ".join(f"{s} {len(eligible(promos, s))}" for s in SECTIONS))
        return 0
    if cmd == "fill-seconds":
        return _fill_seconds()
    if cmd == "select":
        p = select(argv[1], argv[2])
        print(p.id if p else "")
        return 0
    if cmd == "render":
        out = Path(argv[argv.index("--out") + 1]) if "--out" in argv else RENDER_DIR
        m = render_all(out)
        print(f"rendered {len(m['promos'])} promos with {m['voice']} into {out}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "pipeline"))
    raise SystemExit(main())
