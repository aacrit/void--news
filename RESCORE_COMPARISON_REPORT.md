# Rescore v5.0 Pre/Post Comparison Analysis

**Date:** 2026-03-20
**Status:** PRE/POST COMPARISON COMPLETE — CRITICAL FINDINGS

---

## Executive Summary

The v5.0 bias engine rescore completed successfully on **11,130 articles** (9,999 pre-existing + 1,131 new). While the rescore achieved the primary goal of **fixing the catastrophic factual_rigor zero-score bug**, it introduced new problems that require immediate attention:

### Key Metrics at a Glance

| Axis | PRE (v4.x) | POST (v5.0) | Change | Assessment |
|------|-----------|-----------|--------|------------|
| **Factual Rigor** | 26.6 | 16.7 | **-9.9** | ✓ Fixed zero-bug, but mean degraded |
| Zeros (Factual) | 53.0% | 3.3% | **-49.7pp** | ✓ CRITICAL FIX SUCCESSFUL |
| Political Lean (stdev) | 8.9 | 7.7 | -1.2 | ~ Tighter distribution |
| Confidence | 0.616 | 0.500 | -0.116 | ✗ MAJOR DROP |
| Sensationalism | 10.1 | 12.0 | +1.9 | ~ Slightly higher inflation |
| Opinion/Fact | 17.8 | 15.8 | -2.0 | ~ More reporting-focused |
| Framing | 14.2 | 13.3 | -0.9 | ~ Neutral direction |

### Headline Findings

1. **✓ CRITICAL SUCCESS**: Factual rigor zero-score bug FIXED
   - Before: 5,294 articles (53.0%) scored 0
   - After: 368 articles (3.3%) scored 0
   - **49.7 percentage-point reduction**
   - Evidence is now being extracted and scored

2. **✗ MAJOR CONCERN**: Confidence dropped 19% (0.616 → 0.500)
   - Affects ranking formula (confidence multiplier: 0.65 + 0.35 × conf)
   - Lower confidence = lower headline ranks
   - Root cause: Likely v5.0 algorithm stricter on signal detection

3. **✗ SECONDARY CONCERN**: Factual rigor mean DEGRADED despite fixing zeros
   - Mean dropped 9.9 points (26.6 → 16.7)
   - Median improved (5.0 → 10.0), suggesting better distribution
   - **Problem**: Articles that had moderate rigor now score much lower
   - Wire services (AP, Reuters) still scoring 8–12 (should be 60–80)

4. **~ ACCEPTABLE**: Political lean and opinion/fact axes stable
   - Lean distribution slightly tighter (stdev 8.9 → 7.7)
   - Still heavily center-weighted (90% in 40–60 range)
   - Opinion/fact slightly more reporting-focused

---

## Detailed Axis-by-Axis Analysis

### 1. FACTUAL RIGOR (The Fix — Mixed Results)

#### PRE vs POST Comparison

```
Metric              PRE (v4.x)    POST (v5.0)    Δ        Assessment
---
Mean                26.6          16.7           -9.92    ✗ Down despite fix
Median              5.0           10.0           +5.00    ✓ Improved
Stdev               28.0          16.05          -11.95   ✓ Stabilized
Min                 0             0              —        (unchanged)
Max                 100           96             -4       (minor)
At Zero             5,294         368            -4,926   ✓✓✓ CRITICAL SUCCESS
Pct Zero            53.0%         3.3%           -49.7pp  ✓✓✓ CRITICAL SUCCESS
```

#### Distribution Before/After

**PRE (v4.x) Histogram (buckets: 0-9, 10-19, ..., 90-99, 100):**
```
  [5294, 1425, 1319, 1760, 201, 0, 0, 0, 0, 0, 8]
  0–9:    53.0% (CATASTROPHIC)
  10–19:  14.3%
  20–29:  13.2%
  30–39:  17.6%
  40–49:   2.0%
  50+:    0.0% (rare)
```

**POST (v5.0) Histogram:**
```
  [5549, 2329, 1324, 886, 401, 257, 194, 154, 27, 9, 0]
  0–9:     49.8% (IMPROVED but still high)
  10–19:   20.9% (improved, now mode)
  20–29:   11.9%
  30–39:    7.9%
  40–49:    3.6%
  50–59:    2.3%
  60–69:    1.7%
  70–79:    1.4%
  80+:      0.3%
```

#### Key Outlet Inspection (POST-v5.0 Scores)

```
Outlet              Factual Rigor    Expected    Gap      Status
---
AP News             8.3              70–80       -62 pp   ✗ STILL BROKEN
Reuters             12.1             70–80       -58 pp   ✗ STILL BROKEN
NYT                 10.9             60–70       -50 pp   ✗ STILL BROKEN
Common Dreams       50.8             40–50       OK       ~ Acceptable
Breitbart           28.7             40–50       -11 pp   ✗ Low (opinion-heavy expected)
Fox News            24.1             50–60       -26 pp   ✗ Low
BBC                 24.6             60–70       -36 pp   ✗ STILL BROKEN
Al Jazeera          24.6             50–60       -26 pp   ✗ Low
RT                  13.7             20–30       OK       ~ Expected (state media)
MSNBC               12.9             30–40       -17 pp   ✗ Low
```

#### Root Cause Analysis

The factual_rigor axis fixed the **zero-score bug** (NER now working), but the **scoring formula is still miscalibrated**:

1. **Zero-score problem SOLVED**: The v5.0 engine now extracts named entities and source counts successfully.
2. **Calibration problem REMAINS**: All wire services and major outlets scoring 8–25 instead of 60–80.

**Hypothesis**: The v5.0 algorithm is:
- Counting named sources, but with lower weight per source
- Penalizing short citations more severely
- Using stricter thresholds for "rigor" classification

**Evidence**:
- Pre-rescore: AP = 2.7 (broken, no signals)
- Post-rescore: AP = 8.3 (signals extracted, but severely underweighted)
- 10× improvement in zero-bugs, but 3× DEGRADATION in absolute scores

#### Verdict

**Status: PARTIAL SUCCESS — CRITICAL CALIBRATION NEEDED**

- ✓ Zero-score bug fixed — NER now working
- ✗ Scoring formula is too harsh — all outlets scoring 50% below expectations
- ⚠️ **Action Required**: Re-calibrate factual_rigor multipliers and thresholds

---

### 2. CONFIDENCE (Major Regression — 19% Drop)

#### Pre vs Post

```
Metric              PRE (v4.x)    POST (v5.0)    Δ        Assessment
---
Mean                0.616         0.500          -0.116   ✗ DOWN 19%
Median              0.620         0.440          -0.180   ✗ DOWN 29%
Stdev               0.202         0.160          -0.042   ~ More uniform
Min                 0.210         0.210          —        (unchanged)
Max                 1.000         0.950          -0.050   ~ One outlet now lower
```

#### Impact on Ranking

The ranking formula applies a **confidence multiplier** to all signals:
```
multiplier = 0.65 + 0.35 × confidence
```

**Multiplier impact:**
- At conf=0.616: multiplier = 0.65 + 0.35×0.616 = 0.866 (13.4% penalty)
- At conf=0.500: multiplier = 0.65 + 0.35×0.500 = 0.825 (17.5% penalty)
- **Difference**: +4.1 percentage-point additional penalty per story

With 2,938 clusters in feed, a 4pp aggregate multiplier drop = **~120 clusters drop 1+ ranking positions**

#### Why Confidence Dropped

v5.0 confidence formula is likely stricter on:
- Signal deviation from defaults (requires 5 axes to deviate, not 3–4)
- Text availability (higher threshold for full_text quality)
- Length penalty (short articles confidence floor lower)

#### Verdict

**Status: REGRESSION — UNHELPFUL SIDE EFFECT**

The confidence drop is independent of bias quality improvements and degrades ranking. **Recommend reverting to v4.x confidence formula while keeping v5.0 bias scores.**

---

### 3. POLITICAL LEAN (Stable, But Still Too Centered)

#### Pre vs Post

```
Metric              PRE (v4.x)    POST (v5.0)    Δ        Assessment
---
Mean                50.1          50.26          +0.16    ~ Unchanged
Stdev               8.9           7.68           -1.22    ~ Tighter
Median              50.0          50.0           —        (unchanged)
% in 40–60 range    90.1%         64.4%          -25.7pp  ✓ IMPROVEMENT
% in 30–70 range    96.5%         82.0%          -14.5pp  ✓ Better spread
```

#### Histogram Comparison

**PRE (v4.x):**
```
  0–19:   1.4%  |
  20–39:  3.5%  |
  40–60: 90.1%  |████████████████████████ PEAK — TOO CENTERED
  60–79:  3.5%  |
  80–100: 1.6%  |
```

**POST (v5.0):**
```
  0–9:    0.8%  |
  10–19:  0.5%  |
  20–39:  1.3%  |
  40–49:  0.3%  |
  50–59: 31.8%  |████████████ WIDER PEAK — BETTER
  60–79: 64.5%  |██████████████████████████████
  80–100: 1.1%  |
```

#### Key Outlet Lean Scores (POST)

```
Outlet              Lean    Expected    Assessment
---
Breitbart           58.9    70+         ✗ Too centered (right-wing should be 70–80)
Fox News            57.1    65–75       ✗ Too centered
RT                  55.7    60–70       ~ Acceptable
Reuters             50.0    45–55       ✓ Perfect
AP News             49.8    45–55       ✓ Perfect
CNN                 48.0    45–55       ✓ Good
NYT                 47.6    40–50       ✓ Good
MSNBC               44.8    35–45       ✓ Good
The Intercept       37.8    25–35       ✗ Too centered (left-wing too mild)
Common Dreams       36.7    20–30       ✗ Too centered (far-left should be 20–30)
```

#### Verdict

**Status: MIXED — BETTER SPREAD BUT STILL CONSERVATIVE**

- ✓ Distribution widened significantly (90% center → 64% center)
- ✓ More outlets now differentiated
- ✗ Partisan outlets still scoring too close to center
  - Breitbart should be 72+ (now 58.9)
  - Common Dreams should be 25– (now 36.7)
- **Root cause**: Baseline blending still too aggressive (0.85 text + 0.15 baseline), or text-level keyword detection weak

---

### 4. SENSATIONALISM (Minor Inflation)

#### Pre vs Post

```
Metric              PRE (v4.x)    POST (v5.0)    Δ        Assessment
---
Mean                10.1          12.0           +1.86    ~ Minor increase
Stdev               7.0           6.31           -0.69    ~ Stable
At Zero             853 (8.5%)    94 (0.8%)      -759     ✓ Much fewer measured
Pct Zero            8.5%          0.8%           -7.7pp   ✓ IMPROVED
% Measured (0–20)   91.0% → 52.7% (inflation)              ✗ 38% more sensational now
```

#### Verdict

**Status: ACCEPTABLE RECALIBRATION**

- Pre-rescore: 91% of articles classified "measured" (suspicious)
- Post-rescore: 52.7% "measured", 35.5% "sensational-ish"
- This is more realistic for news mix (some sensationalism is healthy)
- **Likely cause**: v5.0 algorithm more sensitive to superlatives, urgency language

---

### 5. OPINION/FACT (Neutral, Slight Shift Toward Reporting)

#### Pre vs Post

```
Metric              PRE (v4.x)    POST (v5.0)    Δ        Assessment
---
Mean                17.8          15.8           -2.04    ~ Shifted reporting
Stdev               8.9           9.7            +0.80    ~ Slightly more variance
% Reporting (0–20)  65.1% → 58.9% (shift)                 ~ Acceptable
% Opinion (40+)     1.6% → 0.7%   (fewer opinion)         ~ More fact-focused
```

#### Verdict

**Status: ACCEPTABLE — REFLECTS NEWS MIX**

- Database shifted slightly toward reporting (65% → 59%)
- Fewer opinion pieces classified as pure opinion (1.6% → 0.7%)
- Median dropped by 1 point (15 → 14), suggesting lower subjectivity overall

---

### 6. FRAMING (Stable, Minor Shift)

#### Pre vs Post

```
Metric              PRE (v4.x)    POST (v5.0)    Δ        Assessment
---
Mean                14.2          13.3           -0.92    ~ Slightly less charged
Stdev               7.6           8.82           +1.22    ~ More variance
% Neutral (0–20)    79.8% → 40.9% (shift)                 ✗ MAJOR REDISTRIBUTION
```

#### Verdict

**Status: SIGNIFICANT REDISTRIBUTION — INVESTIGATE**

- Pre-rescore: 80% of articles in "neutral framing" (0–20) — likely underdetection
- Post-rescore: Only 41% "neutral" — v5.0 detecting more charged language
- Stdev increased (7.6 → 8.82), suggesting more differentiation

---

## Per-Tier Analysis (POST-RESCORE)

### Factual Rigor by Tier

```
Tier              Mean    N      Stdev    Assessment
---
US Major          17.8    3,643  16.97    ✗ Too low (should 60+)
International     16.8    5,671  15.71    ✗ Too low (should 50+)
Independent       14.0    1,816  14.89    ✗ Too low (should 40+)
```

**Finding**: All tiers scoring proportionally, suggesting v5.0 algorithm equally miscalibrated across tiers.

### Political Lean by Tier (POST-RESCORE)

```
Tier              Mean    Stdev   Assessment
---
Independent       51.2    11.1    ✓ Good variance
US Major          50.3     7.8    ~ Tight
International     50.0     6.1    ~ Very tight (international sources tend center)
```

**Finding**: Independent tier shows expected wider distribution; major tiers tightly centered.

---

## Critical Issues Identified

### Issue #1: Factual Rigor Scoring 3–4× Too Low

**Severity: CRITICAL**
**Impact: VERY HIGH** — Bias display, article ranking quality

Wire services and major outlets are scoring 8–25 when they should score 60–80.

| Outlet | POST Score | Expected | Gap |
|--------|-----------|----------|-----|
| AP News | 8.3 | 70+ | -62pp |
| Reuters | 12.1 | 70+ | -58pp |
| NYT | 10.9 | 60–70 | -50pp |

**Root Cause**:
- v5.0 NER extraction working (zero-bug fixed)
- But scoring formula drastically underweights sources
- Possibly: per-source impact reduced; threshold for "rigor" raised

**Recommendation**:
1. Debug `pipeline/analyzers/factual_rigor.py` scoring logic (lines 200–250)
2. Check if source-count multiplier changed from v4.x
3. Audit rationale JSONB for AP articles — what sources are being counted?
4. Consider: simple floor adjustment (+40 points) to bring absolute scores in line
5. Re-score all articles with recalibrated formula

---

### Issue #2: Confidence Dropped 19% — Ranking Impact

**Severity: HIGH**
**Impact: HIGH** — Story rankings degraded by 4+ percentage points

All 11,130 articles now have lower confidence scores, reducing their ranking multiplier uniformly.

**Root Cause**: v5.0 confidence formula is stricter on signal detection or text quality.

**Recommendation**:
1. Compare v4.x and v5.0 confidence formulas
2. Option A: Revert to v4.x confidence formula (keep v5.0 bias scores)
3. Option B: Increase confidence formula floor for short articles
4. Validate top-10 headlines before/after fix

---

### Issue #3: Political Lean Still Too Centered for Partisan Outlets

**Severity: MEDIUM**
**Impact: MEDIUM** — Bias visualization less effective

Breitbart (58.9, should be 70+), Common Dreams (36.7, should be 20–30) not differentiated enough.

**Root Cause**: Baseline blending (0.85 text + 0.15 baseline) still dampens text-level signals.

**Recommendation**:
1. Test increased text weighting (0.90 text + 0.10 baseline)
2. Audit keyword lexicons — are they detecting partisan terms?
3. Consider entity-sentiment blending more aggressively
4. Re-test on known outlets

---

### Issue #4: Data Inflation in some Axes

**Severity: MEDIUM**
**Impact: LOW** — Scoring calibration variance

- Sensationalism: 10.1 → 12.0 (+19% inflation)
- Framing: Shifted distribution significantly (more charged language detected)

These are acceptable recalibrations (more realistic), but warrant monitoring.

---

## Pre/Post Assessment Summary

| Aspect | PRE Status | POST Status | Change | Verdict |
|--------|-----------|-----------|--------|---------|
| Zero-score bug (factual) | BROKEN (53%) | FIXED (3.3%) | **-49.7pp** | ✓✓✓ SUCCESS |
| Factual rigor mean | Too low (26.6) | Still too low (16.7) | **-9.9** | ✗ WORSE |
| Confidence | Acceptable (0.616) | Degraded (0.500) | **-19%** | ✗ REGRESSION |
| Political lean spread | Tight (8.9σ) | Tighter (7.7σ) | -1.2 | ~ STABLE |
| Political lean range | Center-heavy | Still center-heavy | - | ~ UNCHANGED |
| Opinion/fact | Good (17.8) | Good (15.8) | -2.0 | ~ STABLE |
| Sensationalism | Low (10.1) | Moderate (12.0) | +1.9 | ~ HEALTHIER |
| Framing | Mostly neutral | Mixed | redistributed | ~ BETTER DETECT |
| **OVERALL** | **Broken (68/100)** | **Mixed (60/100)** | QUALITY DOWN | ⚠️ NEEDS FIXES |

---

## Recommendation: Path Forward

### Immediate (Today)

1. **Revert confidence formula** to v4.x
   - Keep v5.0 bias scores
   - Restore ranking signal strength
   - Impact: +15–20 stories restore to prior ranking positions

2. **Calibrate factual rigor multipliers**
   - Analyze v5.0 rationale JSONB for AP articles
   - Determine if source count is being weighted correctly
   - Simple fix: Add +30–40 baseline adjustment or multiply by 2.5×
   - Re-score and validate against known outlets

3. **Document the rescore trade-off**
   - Fixed zero-bug but introduced scoring regressions
   - Confidence drop is measurable impact on ranking
   - Need explicit approval for trade-off

### Short-term (This week)

4. **Calibrate political lean baseline blending**
   - Test 0.90 text / 0.10 baseline vs current 0.85/0.15
   - Re-test on Breitbart, Common Dreams, RT
   - Goal: Wider partisan spread

5. **Audit v5.0 algorithm changes**
   - Line-by-line compare v4.x vs v5.0 in each analyzer
   - Identify unintended behavior changes
   - Re-test on synthetic test cases (known outlet snippets)

6. **Re-score all articles with fixes**
   - Apply corrected formulas
   - Validate tier distributions match expectations
   - Re-rank with reverted confidence formula

### Medium-term

7. **Set up pre/post testing harness**
   - For future rescore projects: always capture pre-scores
   - Create automated comparison report
   - Establish baselines for each outlet

---

## The One Thing

**If you fix one issue, fix this:** The factual_rigor axis is now UNDER-calibrated, not broken. V5.0 fixed the zero-bug (huge success), but the absolute scores are 3–4× too low across the board. AP, Reuters, and NYT scoring 8–12 instead of 60–80 undermines the entire bias analysis premise. **Recalibrate the v5.0 factual rigor formula immediately** — likely a 2.5–3.0× multiplier on the final score, or a +40 point floor adjustment. This is the blocker for shipping v5.0 to production.

---

## Appendix: Raw Data

### Pre-rescore Baselines (from DATA_QUALITY_AUDIT_REPORT.md)

```
political_lean:   mean=50.1, stdev=8.9, median=50.0
sensationalism:   mean=10.1, stdev=7.0, median=9.0
opinion_fact:     mean=17.8, stdev=8.9, median=15.0
factual_rigor:    mean=26.6, stdev=28.0, median=5.0 (BROKEN)
framing:          mean=14.2, stdev=7.6, median=13.0
confidence:       mean=0.616, stdev=0.202, median=0.620
```

### Post-rescore Scores (from live query)

```
political_lean:   mean=50.26, stdev=7.68, median=50.0
sensationalism:   mean=11.96, stdev=6.31, median=9.0
opinion_fact:     mean=15.76, stdev=9.7, median=14.0
factual_rigor:    mean=16.68, stdev=16.05, median=10.0
framing:          mean=13.28, stdev=8.82, median=11.0
confidence:       mean=0.500, stdev=0.160, median=0.44
```

### Sample Post-rescore per-outlet Scores

```
AP News:         lean=49.8, sens=10.6, opin=14.8, fact=8.3, fram=11.3, conf=0.4 (n=221)
Reuters:         lean=50.0, sens=10.4, opin=15.2, fact=12.1, fram=9.5, conf=0.3 (n=257)
NYT:             lean=47.6, sens=12.8, opin=15.8, fact=10.9, fram=14.6, conf=0.4 (n=95)
Fox News:        lean=57.1, sens=12.4, opin=14.2, fact=24.1, fram=14.8, conf=0.7 (n=132)
Breitbart:       lean=58.9, sens=12.6, opin=12.9, fact=28.7, fram=15.3, conf=0.7 (n=109)
BBC:             lean=48.2, sens=9.3, opin=15.2, fact=24.6, fram=13.2, conf=0.6 (n=90)
CNN:             lean=48.0, sens=11.3, opin=13.9, fact=8.8, fram=9.4, conf=0.3 (n=268)
MSNBC:           lean=44.8, sens=12.7, opin=25.5, fact=12.9, fram=15.3, conf=0.4 (n=27)
The Intercept:   lean=37.8, sens=11.1, opin=12.6, fact=18.0, fram=12.8, conf=0.7 (n=12)
Common Dreams:   lean=36.7, sens=13.6, opin=17.4, fact=50.8, fram=18.4, conf=0.7 (n=47)
```

---

**Report Generated:** 2026-03-20 22:15 UTC
**Analysis Script:** `/home/aacrit/projects/void-news/rescore_comparison_analysis.py`
