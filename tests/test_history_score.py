"""The sampled History score: every rule against a planted defect.

pipeline/history/score.py renders an episode's score from note data on
sampled real instruments, and the manifest is where the rights live. So:

  rights      every instrument's rights_basis is on the allowlist (CC0 as
              stated, or CC-BY as stated WITH a credit line); no NC, SA or ND
              term anywhere in a licence string or URL
  claims      every cue carries `claims: []`: the music says nothing about
              the event
  textures    the AI-texture hook stays empty
  pins        every sample has a source URL and a 64-hex sha256; a cached file
              that does not match is refused
  keys        a manifest defines only keys the producer consumes, the five
              mandatory ones among them, no bed or transition for a dry mood
  lengths     the theme is a statement (16..32 s), the outro fits under the
              promo window (13.75 s) and ends in silence, the rupture entry
              fits mood_plan's 6 s
  fallback    an episode with no manifest gets exactly history_cues(era)
  hook        produce() calls load_score(slug, era) where history_score(era)
              was; history_score itself still exists for the clip tests
  render      with the samples in the cache: the same bytes twice, beds that
              loop without a seam, nothing clipping, the outro under -80 dBFS

The render checks need the samples (~/.cache/void-score-samples); without
them they print SKIPPED and the manifest checks still run. Nothing here
touches the network (VOID_SCORE_OFFLINE=1).

Run: python tests/test_history_score.py
"""

from __future__ import annotations

import copy
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT))
os.environ["VOID_SCORE_OFFLINE"] = "1"

import numpy as np  # noqa: E402
import yaml  # noqa: E402

from history import score as sc  # noqa: E402

failures: list[str] = []
skipped: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{': ' + detail if detail else ''}")


MANIFESTS = sorted(sc.SCORES_DIR.glob("*.yaml"))
ERA = "contemporary"


def _load(p: Path) -> dict:
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def _samples_cached(m: dict) -> bool:
    try:
        root = sc.cache_root()
    except sc.ScoreError:
        return False
    return all((root / s["file"]).exists() for inst in m["instruments"].values() for s in inst["samples"])


# ---------------------------------------------------------------------------
# 1. Every committed manifest validates, and the planted defects fail
# ---------------------------------------------------------------------------

def test_manifests_valid() -> None:
    check("score: at least one manifest is committed", bool(MANIFESTS))
    for p in MANIFESTS:
        m = _load(p)
        bad = sc.validate_manifest(m)
        check(f"score: {p.name} validates", not bad, "; ".join(bad[:5]))
        check(f"score: {p.name} slug matches its file", m.get("slug") == p.stem)
        text = p.read_text(encoding="utf-8")
        check(f"score: {p.name} carries no em or en dash", "—" not in text and "–" not in text)
        check(f"score: {p.name} names no raga, maqam or named mode", not re.search(r"(?i)\braga\b|\bmaqam\b|\braag\b", text))
        for name, inst in m["instruments"].items():
            check(f"score: {p.name} {name} names what it is presented as",
                  bool(inst.get("role_as_presented")) and "sarangi" not in inst["role_as_presented"].lower()
                  and "duduk" not in inst["role_as_presented"].lower())


def test_planted_defects() -> None:
    base = _load(MANIFESTS[0]) if MANIFESTS else None
    if base is None:
        return
    check("planted: the clean manifest passes", not sc.validate_manifest(base))
    inst0 = next(iter(base["instruments"]))
    cue0 = next(iter(base["cues"]))

    def mutate(fn):
        m = copy.deepcopy(base)
        fn(m)
        return sc.validate_manifest(m)

    # Rights: a basis off the allowlist.
    bad = mutate(lambda m: m["instruments"][inst0].__setitem__("rights_basis", "cc-by-nc-as-stated"))
    check("planted: an NC rights basis FAILS", any("rights_basis" in b for b in bad), str(bad))
    bad = mutate(lambda m: m["instruments"][inst0].__setitem__("rights_basis", "fair-use"))
    check("planted: 'fair-use' FAILS", any("rights_basis" in b for b in bad))
    # Rights: a CC-BY without a credit line.
    bad = mutate(lambda m: (m["instruments"][inst0].__setitem__("rights_basis", "cc-by-as-stated"),
                            m["instruments"][inst0].__setitem__("credit_line", ""),
                            m["instruments"][inst0].__setitem__("licence_url", "https://creativecommons.org/licenses/by/4.0/")))
    check("planted: CC-BY without a credit line FAILS", any("credit_line" in b for b in bad), str(bad))
    # Rights: an NC or SA deed URL, and an SA term in the licence string.
    bad = mutate(lambda m: m["instruments"][inst0].__setitem__("licence_url", "https://creativecommons.org/licenses/by-nc/4.0/"))
    check("planted: a BY-NC deed URL FAILS", bool(bad))
    bad = mutate(lambda m: m["instruments"][inst0].__setitem__("licence_as_stated", "CC BY-SA 4.0"))
    check("planted: an SA licence string FAILS", any("NC, SA or ND" in b for b in bad), str(bad))
    # Claims: a cue that claims something.
    bad = mutate(lambda m: m["cues"][cue0].__setitem__("claims", ["recorded at the event"]))
    check("planted: a cue with a claim FAILS", any("claims" in b for b in bad))
    bad = mutate(lambda m: m["cues"][cue0].pop("claims"))
    check("planted: a cue without claims FAILS", any("claims" in b for b in bad))
    # Textures: the hook used.
    bad = mutate(lambda m: m.__setitem__("textures", [{"id": "wind"}]))
    check("planted: a texture row FAILS", any("textures" in b for b in bad))
    # Pins: a short hash, a non-https url.
    bad = mutate(lambda m: m["instruments"][inst0]["samples"][0].__setitem__("sha256", "abc123"))
    check("planted: a short sha256 FAILS", any("sha256" in b for b in bad))
    bad = mutate(lambda m: m["instruments"][inst0]["samples"][0].__setitem__("url", "http://example.com/x.wav"))
    check("planted: an http url FAILS", any("https" in b for b in bad))
    # Keys: a bed for a dry mood, a key the producer does not read.
    bad = mutate(lambda m: m["cues"].__setitem__("bed:testimony", copy.deepcopy(m["cues"]["bed:dread"])))
    check("planted: a bed under testimony FAILS", any("bed:testimony" in b for b in bad))
    bad = mutate(lambda m: m["cues"].__setitem__("bed:rupture", copy.deepcopy(m["cues"]["bed:dread"])))
    check("planted: a bed under rupture FAILS", any("bed:rupture" in b for b in bad))
    bad = mutate(lambda m: m["cues"].pop("theme"))
    check("planted: a missing theme FAILS", any("theme missing" in b for b in bad))
    # Lengths: an outro the promo cannot ride, a rupture entry past its span.
    bad = mutate(lambda m: m["cues"]["outro"].__setitem__("length_s", 20.0))
    check("planted: a 20 s outro FAILS", any("outro" in b for b in bad))
    bad = mutate(lambda m: m["cues"]["outro"].pop("tail_silence"))
    check("planted: an outro without tail_silence FAILS", any("outro" in b for b in bad))
    bad = mutate(lambda m: m["cues"]["rupture_entry"].__setitem__("length_s", 8.0))
    check("planted: an 8 s rupture entry FAILS", any("rupture_entry" in b for b in bad))
    bad = mutate(lambda m: m["cues"]["bed:dread"].pop("fold"))
    check("planted: a bed that does not fold FAILS", any("fold" in b for b in bad))
    bad = mutate(lambda m: m["cues"]["theme"]["notes"].append(["violin", "H4", 0, 1, 0.5]))
    check("planted: a note that is not a note FAILS", any("not a note" in b for b in bad))
    bad = mutate(lambda m: m["cues"]["theme"]["notes"].append(["theremin", "G4", 0, 1, 0.5]))
    check("planted: an undefined instrument FAILS", any("theremin" in b for b in bad))


# ---------------------------------------------------------------------------
# 2. Keys and the fallback
# ---------------------------------------------------------------------------

def test_keys_and_fallback() -> None:
    from briefing import generate_assets as ga
    synth = ga.history_cues(ERA)
    for p in MANIFESTS:
        m = _load(p)
        keys = set(m["cues"])
        check(f"keys: {p.name} covers every synthesised key", set(synth) <= keys | {k for k in keys if m["cues"][k].get("silent")},
              str(sorted(set(synth) - keys)))
        check(f"keys: {p.name} defines only producer keys", keys <= set(sc.ALLOWED_KEYS), str(sorted(keys - set(sc.ALLOWED_KEYS))))
    # No manifest: the dict is history_cues, key for key, length for length.
    base = sc.load_score("no-such-episode", ERA, log=lambda *_: None)
    check("fallback: an episode without a manifest gets every synthesised key", set(base) == set(synth))
    for k in synth:
        n = int(round(len(synth[k]) / ga.SAMPLE_RATE * 1000))
        check(f"fallback: {k} keeps its length", abs(len(base[k]) - n) <= 1, f"{len(base[k])} vs {n}")
        check(f"fallback: {k} is at the producer's rate", base[k].frame_rate == sc.SAMPLE_RATE)


# ---------------------------------------------------------------------------
# 3. The hook in the producer
# ---------------------------------------------------------------------------

def test_hook() -> None:
    src = (ROOT / "pipeline/history/history_producer.py").read_text(encoding="utf-8")
    check("hook: produce() loads the episode's score", "load_score(slug, era)" in src)
    check("hook: the synthesised set is still there for the clip tests", "def history_score(era: str)" in src)
    body = src[src.index("def produce("):]
    check("hook: produce() no longer calls history_score directly except as the ImportError fallback",
          body.count("history_score(era)") == 1 and "except ImportError" in body)


# ---------------------------------------------------------------------------
# 4. Rendering, with the samples present
# ---------------------------------------------------------------------------

def test_render() -> None:
    from briefing import generate_assets as ga
    for p in MANIFESTS:
        m = _load(p)
        if not _samples_cached(m):
            skipped.append(f"render: {p.name} (samples not in the cache)")
            continue
        try:
            root = sc.cache_root()
            for inst in m["instruments"].values():
                for s in inst["samples"]:
                    got = sc._sha256(root / s["file"])
                    check(f"pins: {s['file']} matches its sha256", got == s["sha256"], got[:12])
            a = sc.render_cue(m, "theme", ERA)
            b = sc.render_cue(m, "theme", ERA)
            check(f"render: {p.name} theme is the same bytes twice", np.array_equal(sc.to_pcm16(a), sc.to_pcm16(b)))
            check(f"render: {p.name} theme length is a statement", 16.0 <= len(a) / sc.SAMPLE_RATE <= 32.0)
            check(f"render: {p.name} theme has sound", sc._rms_dbfs(a) > -40.0, f"{sc._rms_dbfs(a):.1f}")
            outro = sc.render_cue(m, "outro", ERA)
            check(f"render: {p.name} outro decays to silence", sc._rms_dbfs(outro[-int(0.2 * sc.SAMPLE_RATE):]) < -80.0)
            check(f"render: {p.name} outro fits the promo window", len(outro) / sc.SAMPLE_RATE <= sc.OUTRO_MAX_S)
            for key in m["cues"]:
                if m["cues"][key].get("silent"):
                    continue
                x = sc.render_cue_cached(m, key, ERA)
                check(f"render: {p.name} {key} does not clip", float(np.max(np.abs(x))) < 1.0)
                check(f"render: {p.name} {key} has sound", sc._rms_dbfs(x) > -60.0, f"{sc._rms_dbfs(x):.1f}")
                if key.startswith("bed:"):
                    check(f"render: {p.name} {key} loops without a seam", ga._seam_ratio(x) < 3.0, f"{ga._seam_ratio(x):.2f}")
            # Through the producer's entry: every key sampled, none fell back.
            logs: list[str] = []
            out = sc.load_score(m["slug"], ERA, log=logs.append)
            check(f"render: {p.name} load_score renders every cue", not any("falls back" in l for l in logs), " | ".join(logs))
            check(f"render: {p.name} load_score returns the producer's keys", set(out) >= set(sc.MANDATORY_KEYS))
        except sc.ScoreError as e:
            check(f"render: {p.name}", False, str(e))


def test_pin_refused() -> None:
    """A cached file whose hash is not the pin is deleted and the cue falls
    back. Planted in a throwaway cache so no real sample is touched."""
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="void-score-test-"))
    keep = os.environ.get("VOID_SCORE_CACHE")
    os.environ["VOID_SCORE_CACHE"] = str(tmp)
    try:
        fake = tmp / "x" / "fake.wav"
        fake.parent.mkdir(parents=True)
        fake.write_bytes(b"RIFF" + b"\0" * 64)
        row = {"file": "x/fake.wav", "sha256": "0" * 64, "url": "https://example.invalid/fake.wav", "note": "G3"}
        try:
            sc.ensure_sample(row)
            check("planted: a sample whose hash is not the pin is REFUSED", False)
        except sc.ScoreError:
            pass
        check("planted: the refused file is deleted", not fake.exists())
        # Offline, a missing sample is a ScoreError (the cue falls back), never a download.
        try:
            sc.ensure_sample(row)
            check("planted: a missing sample offline is REFUSED", False)
        except sc.ScoreError:
            pass
        # A cache inside the repository is refused outright.
        os.environ["VOID_SCORE_CACHE"] = str(ROOT / "data")
        try:
            sc.cache_root()
            check("planted: a cache inside the repository is REFUSED", False)
        except sc.ScoreError:
            pass
    finally:
        if keep is None:
            os.environ.pop("VOID_SCORE_CACHE", None)
        else:
            os.environ["VOID_SCORE_CACHE"] = keep


def main() -> int:
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    for s in skipped:
        print(f"SKIPPED {s}")
    if failures:
        for f in failures:
            print(f"FAIL {f}")
        print(f"{len(failures)} failure(s)")
        return 1
    print(f"test_history_score: all checks passed ({len(skipped)} skipped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
