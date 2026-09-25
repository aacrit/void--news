"""Archival clips: the ledger's audio artifacts, and whether one may play.

docs/proposals/HISTORY-AUDIO-ARCHIVAL.md is the spec; the CEO decided policy B
on rights (§2) on 2026-09-25. A recording is a factual claim four times over
(this speaker, this occasion, this date, these words), and it is a rights
claim besides, so a `# CLIP:` directive plays ONLY when every one of these
holds, and otherwise the DOCUMENT read under it renders exactly as before:

  H-12 rights       the row's `rights_basis` is on policy B's allowlist, the
                    licence is recorded as stated with its URL, the rights
                    reading is written down, AND the CEO has signed the row
                    (`signed_by` and `signed_at`). Nothing else signs.
  H-13 provenance   speaker, occasion, date, repository, accession, url, file,
                    origin as stated, fetched_at, and a checksum to fetch
                    against: an item that cannot say who, when and where from
                    is not evidence, whatever it sounds like
  H-14 transcript   the transcript is verbatim from its ledger extract; the
                    verification record exists, passed, was run on THIS window
                    of THIS file against THIS transcript, and clears the
                    coverage floor
  H-15 credit       the narrator line spoken immediately before the clip names
                    the speaker and says "recording" or "broadcast"
  H-16 caps         at most 45 s, at most two per episode, never in the OPEN
  H-17 dry          no bed, sting or designed sound under a real voice; the
                    timeline half is `timeline_findings`, the rendered half is
                    `bus_findings` (both run by the producer before it writes)

Levels. H-12..H-15 BLOCK admission: the clip does not play and the document
read does. Their findings are "warn" while the row is unsigned, because a
candidate is the expected state and the fallback is honest; they become
"fail" once the CEO has signed, because then someone expects to hear the clip
and a signed clip must never vanish silently. H-16 and H-17 are structural and
always "fail": the render stops.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

try:
    from history.script_format import Finding, Script, _fold
except ImportError:  # imported as pipeline.history.clips
    from pipeline.history.script_format import Finding, Script, _fold  # type: ignore

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "data" / "history" / "evidence"

# Policy B (CEO, 2026-09-25). A basis names what the SOURCE states, never what
# Void infers: "cc0-as-stated" means the repository's own item page carries a
# CC0 licence URL. UN, tribunal and parliamentary material enters under the
# publisher's written terms, which the row must quote in `licence_as_stated`.
POLICY = "B"
RIGHTS_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "A": ("cc0-as-stated", "pdm-as-stated", "cc-by-as-stated", "public-domain-as-stated"),
    "B": ("cc0-as-stated", "pdm-as-stated", "cc-by-as-stated", "public-domain-as-stated",
          "un-published-terms", "tribunal-public-record", "parliament-published-terms"),
}
PROVENANCE_FIELDS = ("speaker", "occasion", "date", "repository", "accession", "url", "file",
                     "origin_as_stated", "fetched_at")
RIGHTS_FIELDS = ("licence_as_stated", "licence_url", "rights_reading")

MAX_CLIP_S = 45.0
MAX_CLIPS = 2
# Calibrated on the pilot (docs/proposals/HISTORY-AUDIO-ARCHIVAL.md §3): the
# stored words must recur, in order, at this share of the transcript. A 1947
# disc transfer through a base-size model comes in far under a clean-speech
# WER, so the gate asks for ALIGNMENT, not a match, and the planted wrong
# passage (the same speaker, a different part of the speech) must fail it.
COVERAGE_MIN = 0.70
CREDIT_WORDS = ("recording", "recorded", "broadcast")
# H-17: nothing designed within this distance of a real voice.
DESIGNED_CLEARANCE_MS = 3000
BED_CLEARANCE_MS = 400
BUS_RMS_CEILING_DBFS = -60.0


# --------------------------------------------------------------------- times

def parse_time(v) -> float | None:
    """"00:00:28.050" | "28.05" | 28.05 -> seconds."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    parts = s.split(":")
    try:
        secs = 0.0
        for p in parts:
            secs = secs * 60.0 + float(p)
        return secs
    except ValueError:
        return None


def window(rec: dict) -> tuple[float, float] | None:
    ex = rec.get("excerpt") or {}
    t0, t1 = parse_time(ex.get("in")), parse_time(ex.get("out"))
    if t0 is None or t1 is None or t1 <= t0:
        return None
    return t0, t1


# --------------------------------------------------------------------- records

def is_signed(rec: dict) -> bool:
    return bool(rec.get("signed_by")) and bool(rec.get("signed_at"))


def verification_path(slug: str, rec: dict, evidence: Path | None = None) -> Path | None:
    rel = rec.get("verification")
    if not rel:
        return None
    return (evidence or EVIDENCE) / slug / str(rel)


def load_verification(slug: str, rec: dict, evidence: Path | None = None) -> dict | None:
    p = verification_path(slug, rec, evidence)
    if p is None or not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", _fold(s or "")).strip()


# --------------------------------------------------------------------- H-12..H-14

def rights_findings(rec: dict, level: str, where: str) -> list[Finding]:
    out: list[Finding] = []
    basis = str(rec.get("rights_basis") or "")
    if basis not in RIGHTS_ALLOWLIST[POLICY]:
        out.append(Finding("H-12", level, where,
                           f"rights basis {basis or 'none'!r} is not on policy {POLICY}'s allowlist"))
    for k in RIGHTS_FIELDS:
        if not rec.get(k):
            out.append(Finding("H-12", level, where, f"the row does not record {k}"))
    if not is_signed(rec):
        out.append(Finding("H-12", level, where,
                           "not signed: signed_by and signed_at are the CEO's, per clip"))
    return out


def provenance_findings(rec: dict, level: str, where: str) -> list[Finding]:
    out: list[Finding] = []
    for k in PROVENANCE_FIELDS:
        if not rec.get(k):
            out.append(Finding("H-13", level, where, f"provenance lacks {k}"))
    if rec.get("kind") != "audio":
        out.append(Finding("H-13", level, where, f"kind {rec.get('kind')!r} is not audio"))
    if not rec.get("file_md5"):
        out.append(Finding("H-13", level, where,
                           "no repository checksum: the file cannot be fetched against its source"))
    return out


def transcript_findings(slug: str, rec: dict, ledger, level: str, where: str,
                        evidence: Path | None = None) -> list[Finding]:
    """H-14: the words are the extract's, and the audio was checked against them."""
    out: list[Finding] = []
    transcript = rec.get("transcript") or ""
    ref = str(rec.get("transcript_extract") or "")
    src, _, loc = ref.partition(".")
    ex = ledger.extract(src, loc) if (ledger is not None and src and loc) else None
    if not transcript:
        out.append(Finding("H-14", level, where, "no transcript"))
    elif ex is None:
        out.append(Finding("H-14", level, where, f"transcript extract {ref or 'none'!r} is not stored"))
    elif _norm_text(transcript) not in _norm_text(ex.text):
        out.append(Finding("H-14", level, where,
                           f"the transcript is not verbatim from {ref}"))
    w = window(rec)
    if w is None:
        out.append(Finding("H-14", level, where, "no excerpt window"))
    ver = load_verification(slug, rec, evidence)
    if ver is None:
        out.append(Finding("H-14", level, where,
                           "no verification record: run pipeline/history/verify_clip.py"))
        return out
    if not ver.get("pass"):
        out.append(Finding("H-14", level, where,
                           f"verification failed (coverage {ver.get('coverage')}, WER {ver.get('wer')})"))
    cov = ver.get("coverage")
    if cov is None or float(cov) < COVERAGE_MIN:
        out.append(Finding("H-14", level, where, f"coverage {cov} under {COVERAGE_MIN}"))
    if not ver.get("verified_at") or not ver.get("excerpt_sha256"):
        out.append(Finding("H-14", level, where, "record lacks verified_at or excerpt_sha256"))
    if _norm_text(ver.get("reference") or "") != _norm_text(transcript):
        out.append(Finding("H-14", level, where, "the record checked a different transcript"))
    vw = ver.get("window") or {}
    if w is None or abs(float(vw.get("in", -1)) - w[0]) > 0.0005 or abs(float(vw.get("out", -1)) - w[1]) > 0.0005:
        out.append(Finding("H-14", level, where, "the record checked a different window"))
    if (ver.get("source") or {}).get("md5") != rec.get("file_md5"):
        out.append(Finding("H-14", level, where, "the record checked a different file"))
    return out


# --------------------------------------------------------------------- the script side

@dataclass
class ClipSlot:
    seg_idx: int
    clip_id: str
    replaces: str                  # "document" | "none"
    rec: dict | None
    admitted: bool = False
    findings: list[Finding] = field(default_factory=list)
    verification: dict | None = None

    @property
    def seconds(self) -> float | None:
        w = window(self.rec or {})
        return None if w is None else w[1] - w[0]


def _credit_ok(text: str, speaker: str) -> bool:
    words = re.findall(r"[a-z0-9']+", _fold(text).lower())
    honorifics = ("lord", "lady", "pandit", "mahatma", "president", "minister")
    names = [w for w in re.findall(r"[a-z0-9']+", _fold(speaker).lower())
             if len(w) > 3 and w not in honorifics]
    said_name = any(n in words or any(x.startswith(n) for x in words) for n in names)
    said_kind = any(any(x.startswith(k) for x in words) for k in CREDIT_WORDS)
    return said_name and said_kind


def credit_line(script: Script, slot: ClipSlot) -> str | None:
    """The narrator line the listener hears immediately before the clip."""
    seg = script.segments[slot.seg_idx]
    if slot.replaces == "document":
        before = []
        for l in seg.lines:
            if l.speaker in ("M", "F"):
                break
            before.append(l)
        n = [l for l in before if l.speaker == "N"]
        if n:
            return n[-1].text
    # replaces=none plays before the segment: the credit is the last narrator
    # line of whatever segment was spoken before it.
    for s in reversed(script.segments[:slot.seg_idx]):
        n = [l for l in s.lines if l.speaker == "N"]
        if n:
            return n[-1].text
    return None


def slots(script: Script, ledger) -> list[ClipSlot]:
    out: list[ClipSlot] = []
    recs = getattr(ledger, "recordings", {}) or {}
    for i, seg in enumerate(script.segments):
        for d in seg.directives_of("CLIP"):
            cid = d.args.get("id", "")
            out.append(ClipSlot(seg_idx=i, clip_id=cid, replaces=d.args.get("replaces", "document"),
                                rec=recs.get(cid)))
    return out


def evaluate(script: Script, ledger, slug: str, evidence: Path | None = None) -> tuple[list[ClipSlot], list[Finding]]:
    """Decide, per `# CLIP:` slot, whether it plays. Returns (slots, findings)."""
    all_findings: list[Finding] = []
    got = slots(script, ledger)
    for s in got:
        seg = script.segments[s.seg_idx]
        where = f"{seg.kind}{' ' + (seg.title or seg.author or '') if (seg.title or seg.author) else ''} [{s.clip_id}]"
        f: list[Finding] = []
        if s.rec is None:
            f.append(Finding("H-13", "warn", where, "no ledger row for this clip"))
            s.findings = f
            all_findings += f
            continue
        level = "fail" if is_signed(s.rec) else "warn"
        f += rights_findings(s.rec, level, where)
        f += provenance_findings(s.rec, level, where)
        f += transcript_findings(slug, s.rec, ledger, level, where, evidence)
        s.verification = load_verification(slug, s.rec, evidence)
        # H-15: the spoken credit.
        line = credit_line(script, s)
        if not line or not _credit_ok(line, str(s.rec.get("speaker") or "")):
            f.append(Finding("H-15", level, where,
                             f"the narrator line before the clip must name {s.rec.get('speaker')} and say "
                             f"recording or broadcast: {(line or 'none')[:80]!r}"))
        if s.replaces == "document":
            q = [l for l in seg.lines if l.speaker in ("M", "F")]
            first = next((k for k, l in enumerate(seg.lines) if l.speaker in ("M", "F")), None)
            contiguous = first is not None and all(l.speaker in ("M", "F") for l in seg.lines[first:first + len(q)])
            if seg.kind != "DOCUMENT" or not q or not contiguous:
                f.append(Finding("H-16", "fail", where,
                                 "replaces=document needs a DOCUMENT with one contiguous read to replace"))
        elif s.replaces != "none":
            f.append(Finding("H-16", "fail", where, f"replaces={s.replaces!r} is not document or none"))
        s.findings = f
        s.admitted = not any(x.id in ("H-12", "H-13", "H-14", "H-15") for x in f) and \
            not any(x.level == "fail" for x in f)
        all_findings += f
    all_findings += cap_findings(script, got)
    # A structural failure anywhere stops every clip.
    if any(x.level == "fail" and x.id in ("H-16",) for x in all_findings):
        for s in got:
            s.admitted = False
    return got, all_findings


def cap_findings(script: Script, got: list[ClipSlot]) -> list[Finding]:
    """H-16: bounded. Applies to every slot, admitted or not: a script that
    asks for three clips or a clip in the cold open is wrong as written."""
    out: list[Finding] = []
    if len(got) > MAX_CLIPS:
        out.append(Finding("H-16", "fail", "TOTAL", f"{len(got)} clips; at most {MAX_CLIPS} per episode"))
    for s in got:
        seg = script.segments[s.seg_idx]
        if seg.kind == "OPEN" or (s.replaces == "none" and s.seg_idx == 0):
            out.append(Finding("H-16", "fail", seg.kind, f"{s.clip_id}: never in the OPEN"))
        d = next((d for d in seg.directives_of("CLIP") if d.args.get("id") == s.clip_id), None)
        declared = parse_time((d.args.get("max") or "").rstrip("s")) if d else None
        secs = s.seconds
        if declared is not None and declared > MAX_CLIP_S:
            out.append(Finding("H-16", "fail", seg.kind, f"{s.clip_id}: max={declared:.0f}s over {MAX_CLIP_S:.0f}s"))
        if secs is not None and secs > MAX_CLIP_S:
            out.append(Finding("H-16", "fail", seg.kind, f"{s.clip_id}: excerpt {secs:.1f}s over {MAX_CLIP_S:.0f}s"))
        if secs is not None and declared is not None and secs > declared + 0.001:
            out.append(Finding("H-16", "fail", seg.kind,
                               f"{s.clip_id}: excerpt {secs:.1f}s over its own max={declared:.0f}s"))
    return out


# --------------------------------------------------------------------- H-17

@dataclass
class Span:
    kind: str          # "clip" | "bed" | "sting" | "transition" | "ambience" | "foley" | "room"
    start_ms: int
    end_ms: int
    label: str = ""


def timeline_findings(clips: list[Span], music: list[Span]) -> list[Finding]:
    """H-17, first half, before anything renders.

    No designed sound (ambience, foley) begins, ends or sits within 3 s of a
    real voice, and nothing musical (bed, sting, transition, room tone) is
    scheduled inside the clip's span plus 400 ms either side.
    """
    out: list[Finding] = []
    for c in clips:
        for m in music:
            if m.end_ms <= m.start_ms:
                continue
            if m.kind in ("ambience", "foley"):
                lo, hi = c.start_ms - DESIGNED_CLEARANCE_MS, c.end_ms + DESIGNED_CLEARANCE_MS
                if m.start_ms < hi and m.end_ms > lo:
                    out.append(Finding("H-17", "fail", c.label or "clip",
                                       f"designed {m.kind} {m.label!r} at {m.start_ms}-{m.end_ms} ms within "
                                       f"{DESIGNED_CLEARANCE_MS} ms of a real recording at {c.start_ms}-{c.end_ms}"))
            else:
                lo, hi = c.start_ms - BED_CLEARANCE_MS, c.end_ms + BED_CLEARANCE_MS
                if m.start_ms < hi and m.end_ms > lo:
                    out.append(Finding("H-17", "fail", c.label or "clip",
                                       f"{m.kind} {m.label!r} at {m.start_ms}-{m.end_ms} ms runs under a real "
                                       f"recording at {c.start_ms}-{c.end_ms}"))
    return out


def rms_dbfs(seg, start_ms: int, end_ms: int) -> float:
    """RMS of a pydub segment over a span, in dBFS (-inf reads as -200)."""
    import math
    part = seg[max(0, start_ms):max(0, end_ms)]
    if len(part) == 0:
        return -200.0
    try:
        import numpy as np
        x = np.array(part.get_array_of_samples()).astype(np.float64) / float(1 << (8 * part.sample_width - 1))
        r = float(np.sqrt(np.mean(x * x))) if x.size else 0.0
    except Exception:
        r = part.rms / float(1 << (8 * part.sample_width - 1))
    return -200.0 if r <= 0 else 20.0 * math.log10(r)


def bus_findings(clips: list[Span], buses: dict) -> list[Finding]:
    """H-17, second half, on the rendered buses: the music bus (beds, stings,
    room tone) and the ambience bus must each read under -60 dBFS RMS across
    every clip's span plus 400 ms either side."""
    out: list[Finding] = []
    for c in clips:
        for name, bus in buses.items():
            if bus is None:
                continue
            r = rms_dbfs(bus, c.start_ms - BED_CLEARANCE_MS, c.end_ms + BED_CLEARANCE_MS)
            if r > BUS_RMS_CEILING_DBFS:
                out.append(Finding("H-17", "fail", c.label or "clip",
                                   f"{name} bus at {r:.1f} dBFS RMS under a real recording "
                                   f"({c.start_ms}-{c.end_ms} ms); ceiling {BUS_RMS_CEILING_DBFS:.0f}"))
    return out
