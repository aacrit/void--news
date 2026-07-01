"""Offline ($0) verification of categorization fixes (CAT-1/2/3/4/6)."""
import sys, os, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
from categorizer.auto_categorize import categorize_cluster, categorize_article, map_to_desk  # noqa
from utils.text_sanitizer import normalize_headline, sanitize_summary  # noqa

d = json.load(open("scripts/top50_export.json", encoding="utf-8"))
by = {c["_display_rank"]: c for c in d}

from collections import Counter
old_desks, new_desks = Counter(), Counter()
changes = []
for c in d:
    r = c["_display_rank"]
    title = normalize_headline(c.get("title", "") or "")
    summary = sanitize_summary(c.get("summary", "") or "")
    arts = c.get("_articles", [])
    new_fine = categorize_cluster(title, summary, arts)
    new_desk = map_to_desk(new_fine)
    old = c.get("category", "")
    old_desks[old] += 1
    new_desks[new_desk] += 1
    if new_desk != old:
        changes.append((r, old, new_desk, title[:60]))

print("OLD desk distribution:", dict(old_desks))
print("NEW desk distribution:", dict(new_desks))
print(f"\ngeneral: {old_desks.get('general',0)} -> {new_desks.get('general',0)}")
print(f"environment: {old_desks.get('environment',0)} -> {new_desks.get('environment',0)}")

print("\n=== KEY ASSERTIONS ===")
checks = {
    1:  ("politics", "not environment"),   # SCOTUS admin state
    6:  ("!environment", "maternity review"),
    29: ("science", "WhatsApp -> tech desk (science)"),  # tech folds to science
    30: ("environment", "heatwave"),
    47: ("!environment", "Xi Van Fleet op-ed"),
}
passed = 0
for r, (want, desc) in checks.items():
    c = by[r]
    title = normalize_headline(c.get("title", "") or "")
    summary = sanitize_summary(c.get("summary", "") or "")
    desk = map_to_desk(categorize_cluster(title, summary, c.get("_articles", [])))
    if want.startswith("!"):
        ok = desk != want[1:]
    else:
        ok = desk == want
    passed += ok
    print(f"[{'ok ' if ok else 'FAIL'}] #{r} {desc}: got '{desk}' (old '{c.get('category')}')")

print(f"\n=== CHANGES ({len(changes)}) ===")
for r, old, new, t in sorted(changes):
    print(f"  #{r}: {old} -> {new}   {t}")
print(f"\n{passed}/{len(checks)} key assertions passed")
