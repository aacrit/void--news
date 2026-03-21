# void --news Data Quality Audit — Complete Index

**Audit Date:** 2026-03-21
**Database:** Supabase (PostgreSQL 15, us-west-2)
**Overall Health Score:** 72/100

---

## PRIMARY DOCUMENTS

### 1. **AUDIT_EXECUTIVE_SUMMARY.txt** (9.5 KB)
**For:** Busy decision-makers, product leads, sprint planning

**Contains:**
- Overall health score: 72/100
- One-paragraph status per domain
- Critical findings (3 issues)
- Top 10 improvements ranked by priority
- **THE ONE THING** — most important fix
- Next steps (immediate/short/medium term)

**Read this first if pressed for time.** 5-minute read.

---

### 2. **DATA_QUALITY_REPORT_FINAL.md** (24 KB)
**For:** Technical leads, database engineers, audit record

**Contains:**
- Complete 8-domain audit (10/10 breakdown per domain)
- Detailed statistics and findings
- Root cause analysis for each issue
- Migration SQL (014) with step-by-step instructions
- Performance recommendations and index analysis
- Data quality conclusions
- Appendix with audit methodology

**The authoritative audit record.** 30-minute deep read.

---

### 3. **AUDIT_SCHEMA_ANALYSIS.md** (13 KB)
**For:** Database architects, schema maintainers

**Contains:**
- Complete schema overview (8 tables, 1 view, 2 functions)
- Table-by-table field reference
- Index analysis (existing + recommended)
- Referential integrity status
- RLS configuration
- Storage estimates and performance analysis
- Migration path forward
- Schema health: 8/10

**Reference guide for database structure.** Lookup as needed.

---

### 4. **supabase/migrations/014_fix_orphaned_articles.sql** (6.3 KB)
**For:** Database migration execution

**Contains:**
- Fix 614 invalid article_id references
- Create single-article clusters for 2,972 orphaned articles
- Link articles to their clusters
- Verification queries
- Safety notes and performance considerations

**Run this immediately to fix critical issues.** 10 minutes to execute.

---

## KEY FINDINGS AT A GLANCE

### Health by Domain

| Domain | Score | Status |
|--------|-------|--------|
| Source Coverage | 10/10 | ✓ Perfect |
| Article Quality | 7/10 | ⚠ Minor issues |
| Bias Score Quality | 9/10 | ✓ Excellent |
| Cluster Quality | 6/10 | ⚠ CRITICAL |
| Enrichment Quality | 5/10 | ⚠ BROKEN |
| Temporal Freshness | 9/10 | ✓ Excellent |
| Referential Integrity | 5/10 | ⚠ CRITICAL |
| Cross-Field Consistency | 8/10 | ✓ Good |

---

### Critical Issues (Must Fix Today)

1. **45.5% Orphaned Articles (4,553/9,999)** — Invisible to frontend
2. **614 Invalid Article_id References** — Referential integrity violation
3. **coverage_velocity 99.9% Broken** — Ranking signal non-functional

---

## THE ONE THING

**If you can only make one fix:**

**CREATE SINGLE-ARTICLE CLUSTERS FOR THE 2,972 ORPHANED ARTICLES.**

Why: 45.5% of analyzed articles are currently invisible to users. Every article you fetch and analyze should be discoverable.

How: Run Migration 014, Steps 3-4 (10 minutes)

Impact: Immediate user value.

---

## NEXT STEPS

### TODAY (30 minutes)
1. Review AUDIT_EXECUTIVE_SUMMARY.txt
2. Apply Migration 014 (orphaned articles + invalid refs)
3. File bug on coverage_velocity

### THIS WEEK (5-6 hours)
1. Debug coverage_velocity
2. Investigate factual_rigor calibration
3. Fix headline_rank collisions
4. Add monitoring views

### THIS SPRINT (5-8 hours)
1. Investigate 53.3% short articles
2. Increase editorial_importance coverage
3. Tune clustering thresholds
4. Document assumptions

---

## FILE LOCATIONS

```
AUDIT_EXECUTIVE_SUMMARY.txt                    (This quarter's priorities)
DATA_QUALITY_REPORT_FINAL.md                   (Authoritative audit record)
AUDIT_SCHEMA_ANALYSIS.md                       (Database reference)
AUDIT_INDEX.md                                 (This file)
supabase/migrations/014_fix_orphaned_articles.sql  (Apply immediately)
```

---

**For details, see the corresponding report file listed above.**
