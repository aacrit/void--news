"""The house promo pool is publishing, so it is tested like copy.

Every promo: exactly two sentences, no digits, only number words that are
tied to a constant in the code, nothing borrowed, the address in the second
sentence, five to nine seconds at the house voice, never inside the section
it advertises. Selection is deterministic and spreads across the pool. The
house voice is cast nowhere else. A rendered manifest, when present, matches
the text it was made from.

Pure: no audio libraries needed. `python3 tests/test_house_promos.py`
"""

from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from briefing import house_promos as hp  # noqa: E402

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        failures.append(msg)
        print(f"  FAIL {msg}")


def main() -> int:
    promos = hp.load_pool()
    check(len(promos) >= 18, f"pool has {len(promos)} promos, expected at least 18")

    # 1. The pool validates clean.
    findings = hp.validate(promos)
    for f in findings:
        check(False, f)

    # 2. Each rule fires on a synthetic bad promo.
    good = promos[0]

    def findings_for(**kw) -> str:
        bad = replace(good, **kw)
        others = [p for p in promos if p.id != good.id]
        return " | ".join(hp.validate(others + [bad]))

    check("P-01" in findings_for(plays_in=(good.promotes,)), "self-promotion is caught")
    check("P-02" in findings_for(text="One sentence only at news.voidvision.org."), "one sentence is caught")
    check("P-02" in findings_for(text="One. Two. Three at news.voidvision.org."), "three sentences are caught")
    check("P-03" in findings_for(text="We read 1,016 sources. Find them at news.voidvision.org."), "digits are caught")
    check("P-04" in findings_for(text="Seventy eight episodes and counting. Hear them at news.voidvision.org."),
          "an untied number word is caught")
    check("P-05" in findings_for(text="Twenty stories a day. Read them at news.voidvision.org.", claims=()),
          "twenty without the feed_size claim is caught")
    check("P-06" in findings_for(text="Stay with us for the news. More at news.voidvision.org."),
          "a borrowed radio phrase is caught")
    check("P-06" in findings_for(text="A significant week for the benches. More at news.voidvision.org."),
          "a kill-list word is caught")
    check("P-07" in findings_for(text="Two benches — one story. More at news.voidvision.org."), "an em dash is caught")
    check("P-07" in findings_for(text="Two benches, one story! More at news.voidvision.org."), "an exclamation mark is caught")
    check("P-08" in findings_for(text="Two benches argue one story. The Argument, every Sunday, on the wireless.",
                                 names_url=True), "a promo without the address is caught")
    check("P-09" in findings_for(text="Two. At news.voidvision.org."), "a promo under five seconds is caught")
    check("P-09" in findings_for(
        text="Every single line that either of the two benches says on the programme is printed in the "
             "column in full. The Argument, from Void Weekly, every Sunday, at news.voidvision.org."),
        "a promo over nine seconds is caught")
    check("P-10" in findings_for(claims=("made_up_claim",)), "an unknown claim is caught")

    # 3. Sentence splitting survives the address and dotted abbreviations.
    check(len(hp.sentences("The U.S. desk too. More at news.voidvision.org.")) == 2,
          "U.S. and the address do not split a sentence")
    check(len(hp.sentences("Nothing plays under the news but room tone. On Air, at news.voidvision.org.")) == 2,
          "a plain two-sentence promo counts as two")

    # 4. Spoken form: the address is spelled, and no digits survive.
    spoken = hp.spoken_form(good)
    check(hp.SPOKEN_HOST in spoken, f"spoken form spells the address: {spoken}")
    check(not any(ch.isdigit() for ch in spoken), "spoken form has no digits")
    check(hp.SITE_HOST not in spoken, "spoken form does not carry the bare address")

    # 5. Selection: deterministic, never self-promoting, spread across the pool.
    for section in hp.SECTIONS:
        pool = hp.eligible(promos, section)
        check(len(pool) >= 3, f"{section}: {len(pool)} eligible, need at least three")
        check(all(p.promotes != section for p in pool), f"{section}: nothing in its pool promotes itself")
        first = hp.select(section, f"{section}:key-a", promos)
        for _ in range(50):
            check(hp.select(section, f"{section}:key-a", promos) == first, f"{section}: selection is stable")
        seen = {hp.select(section, f"{section}:k{i}", promos).id for i in range(200)}
        check(len(seen) >= min(3, len(pool)), f"{section}: 200 keys reach only {len(seen)} promo(s)")
    # The real keys the producers use.
    hist = hp.select("history", "history:partition-of-india", promos)
    check(hist is not None and hist.promotes != "history", "history key selects a non-history promo")

    # 6. The house voice anchors nothing.
    from briefing.tts_engines import KOKORO_VOICES
    from briefing.weekly_producer import VOICES as WEEKLY_VOICES
    from history import casting

    cast = set(KOKORO_VOICES.values()) | set(WEEKLY_VOICES.values())
    for narrator, docs in casting.DOCUMENT_VOICE.items() if hasattr(casting, "DOCUMENT_VOICE") else []:
        cast.add(narrator)
        cast.update(docs.values())
    src = (ROOT / "pipeline" / "history" / "casting.py").read_text(encoding="utf-8")
    check(f'"{hp.HOUSE_VOICE}"' not in src, f"house voice {hp.HOUSE_VOICE} is not in casting.py")
    check(hp.HOUSE_VOICE not in cast, f"house voice {hp.HOUSE_VOICE} is cast nowhere else")

    # 7. The number words the pool uses are all tied to a code constant.
    from briefing.radio_script_generator import DEEP_STORIES
    check(DEEP_STORIES == 4, f"'four stories' is tied to DEEP_STORIES={DEEP_STORIES}")
    va = (ROOT / "scripts" / "verify_audio.py").read_text(encoding="utf-8")
    check("<= 840" in va, "'under fifteen minutes' is tied to A-04's 840 s ceiling")
    partition = ROOT / "data" / "history" / "scripts" / "partition-of-india.txt"
    check(partition.exists() and "five weeks" in partition.read_text(encoding="utf-8")
          and "never been to India" in partition.read_text(encoding="utf-8"),
          "'five weeks' and 'never been to India' are in the Partition script")
    size = hp.feed_size()
    check(size == 20, f"feed.json displayed is {size}; if this changed, the 'twenty' promos must change")

    # 8. Chapter bookkeeping keeps contiguity and the total.
    chs = [{"startTime": 0.0, "endTime": 30.0, "title": "Opening", "kind": "segment"},
           {"startTime": 30.0, "endTime": 100.0, "title": "Close", "kind": "segment"}]
    out = hp.append_promo_chapter(chs, good, 86_000, 100_000, kind="segment",
                                  title=hp.HISTORY_PROMO_CHAPTER_TITLE)
    check(len(out) == 3 and out[-2]["endTime"] == 86.0 and out[-1]["startTime"] == 86.0
          and out[-1]["endTime"] == 100.0 and out[-1]["title"] == hp.HISTORY_PROMO_CHAPTER_TITLE,
          f"promo chapter appended contiguously: {out[-2:]}")
    check(chs[-1]["endTime"] == 100.0, "append_promo_chapter does not mutate its input")

    # 9. A rendered manifest, when present, matches the pool.
    manifest = hp.load_manifest()
    rendered = manifest.get("promos") or {}
    by_id = {p.id: p for p in promos}
    for pid, entry in rendered.items():
        check(pid in by_id, f"rendered {pid} is still in the pool")
        if pid in by_id:
            check(entry.get("sha") == by_id[pid].sha, f"rendered {pid} was made from the current text")
            check((hp.RENDER_DIR / f"{pid}.wav").exists(), f"rendered {pid}.wav is committed")
            secs = entry.get("seconds")
            check(isinstance(secs, (int, float))
                  and hp.MIN_SECONDS - hp.RENDER_TOLERANCE <= secs <= hp.MAX_SECONDS + hp.RENDER_TOLERANCE,
                  f"rendered {pid} runs {secs}s")

    # 10. The timing window is self-consistent.
    check(hp.LEAD_MS + int(hp.MAX_SECONDS * 1000) + 500 <= hp.OUTRO_SILENT_MS - hp.END_MARGIN_MS,
          "a nine second promo fits under the outro with the end margin")

    if failures:
        print(f"\n{len(failures)} FAILED")
        return 1
    print(f"test_house_promos: {len(promos)} promos, all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
