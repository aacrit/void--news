"""Offline ($0) verification of the categorization ENGINE fixes (CAT-3/CAT-4)
against the live export, exercised through main's O10 headline-primary path.

The fixes under test (in auto_categorize.py):
  * word-boundary keyword matching — kills 'ev'/'epa'/'eu' substring hits that
    made `environment` a false-positive magnet;
  * consumer-tech + extreme-heat vocab — so WhatsApp resolves to technology and
    a heatwave to environment instead of falling through.
"""
import sys, os, json
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
from categorizer.auto_categorize import categorize_article, map_to_desk  # noqa
from utils.text_sanitizer import normalize_headline  # noqa

d = json.load(open("scripts/top50_export.json", encoding="utf-8"))
by = {c["_display_rank"]: c for c in d}


def o10_desk(cluster_title: str, articles: list) -> str:
    """Replicate main.py/rerank.py O10: headline-primary category, member vote
    only when there is no headline."""
    t = (cluster_title or "").strip()
    hc = categorize_article({"title": t, "summary": "", "full_text": ""}) if t else []
    if hc:
        return map_to_desk(hc[0])
    votes: dict = {}
    for a in articles[:8]:
        for c in categorize_article(a):
            votes[c] = votes.get(c, 0) + 1
    return map_to_desk(max(votes, key=votes.get) if votes else "politics")


dist = Counter()
for c in d:
    c["_desk"] = o10_desk(normalize_headline(c.get("title", "") or ""), c.get("_articles", []))
    dist[c["_desk"]] += 1

print("NEW desk distribution:", dict(dist))
print(f"environment (was 8): {dist.get('environment', 0)}")

checks = {
    1:  "!environment",   # SCOTUS admin state (was environment via 'ev')
    6:  "!environment",   # maternity review
    29: "science",        # WhatsApp -> technology desk (science)
    30: "environment",    # heatwave
    47: "!environment",   # Xi Van Fleet op-ed
    24: "economy",        # forex close
    17: "economy",        # China-Canada trade
}
passed = 0
for r, want in checks.items():
    desk = by[r]["_desk"]
    ok = (desk != want[1:]) if want.startswith("!") else (desk == want)
    passed += ok
    print(f"[{'ok ' if ok else 'FAIL'}] #{r} want {want}: got '{desk}' (old '{by[r].get('category')}')")

print(f"\n{passed}/{len(checks)} assertions passed")
sys.exit(0 if passed == len(checks) and dist.get("environment", 0) <= 5 else 1)
