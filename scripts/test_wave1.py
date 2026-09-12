"""Offline ($0) verification of Wave 1 hygiene fixes against the live export.

Asserts headline normalization and summary sanitization remove the exact
defects the multi-perspective review flagged, with no LLM.
"""
import sys, os, json, re
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "pipeline"))
from utils.text_sanitizer import normalize_headline, sanitize_summary  # noqa

d = json.load(open("scripts/top50_export.json", encoding="utf-8"))
by = {c["_display_rank"]: c for c in d}

fails = []

# --- Headlines: source suffix + editorial/tabloid prefix leaks -------------
SUFFIX_LEAK = [11, 19, 21, 22, 24, 41, 48, 49]          # CQ-2
PREFIX_LEAK = [19, 20, 47]                               # INSIGHT:/Exclusive,/South Africa:
CLICKBAIT   = [26, 34, 50]                               # Devastating:/Buckeye Lore:/Unbothered King:
BAD_SUFFIX_RE = re.compile(r"\s[-–—|]\s*\S")            # any " - X" trailing delimiter segment

print("=== HEADLINES ===")
for r in sorted(set(SUFFIX_LEAK + PREFIX_LEAK + CLICKBAIT)):
    c = by.get(r)
    if not c:
        continue
    orig = c.get("title", "")
    fixed = normalize_headline(orig)
    ok = True
    # suffix must be gone
    if r in SUFFIX_LEAK and BAD_SUFFIX_RE.search(fixed) and BAD_SUFFIX_RE.search(orig):
        # allow legitimate internal hyphenation; only fail if a trailing outlet remains
        tail = fixed.rsplit(" - ", 1)[-1] if " - " in fixed else ""
        if tail and tail[0].isupper() and len(tail.split()) <= 4:
            ok = False
    for pre in ("INSIGHT:", "Exclusive,", "ANALYSIS:", "OPINION:"):
        if fixed.startswith(pre):
            ok = False
    for lead in ("Devastating:", "Unbothered King:", "Buckeye Lore:", "Shocking:"):
        if fixed.startswith(lead):
            ok = False
    status = "ok " if ok else "FAIL"
    if not ok:
        fails.append(f"headline #{r}")
    print(f"[{status}] #{r}: {orig!r}\n        -> {fixed!r}")

# --- Summaries: CMS/RSS boilerplate + mid-word truncation ------------------
BOILERPLATE = re.compile(
    r"appeared first on|Continue reading|Read more at|Submitted by|"
    r"pic\.twitter\.com|onLinkedIn|The post[A-Z]", re.IGNORECASE)
NULL_TIER = [c["_display_rank"] for c in d if c.get("summary_tier") is None]

print("\n=== SUMMARIES (null-tier) ===")
n_clean = 0
for r in NULL_TIER:
    c = by[r]
    orig = c.get("summary", "") or ""
    fixed = sanitize_summary(orig)
    had = bool(BOILERPLATE.search(orig))
    still = bool(BOILERPLATE.search(fixed))
    trunc = fixed.endswith("...") or fixed.endswith("…")
    # over-strip guard: if original had real body (>200 chars) fixed shouldn't collapse <60
    collapsed = len(orig) > 200 and len(fixed) < 60
    ok = (not still) and (not trunc) and (not collapsed)
    if had or not ok:
        tag = "ok " if ok else "FAIL"
        if not ok:
            fails.append(f"summary #{r}")
        print(f"[{tag}] #{r} len {len(orig)}->{len(fixed)} boiler {had}->{still} trunc={trunc} collapse={collapsed}")
        if not ok:
            print(f"       ORIG…{orig[-140:]!r}")
            print(f"       FIX …{fixed[-140:]!r}")
    if ok and had:
        n_clean += 1

print(f"\nnull-tier summaries with boilerplate cleaned OK: {n_clean}")
print(f"\n{'ALL PASS' if not fails else 'FAILURES: ' + ', '.join(fails)}")
sys.exit(1 if fails else 0)
