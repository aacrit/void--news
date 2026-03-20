# void --news — Project Charter

**Date:** 2026-03-19 (rev 2)
**Project Owner:** Aacrit (CEO)
**Status:** Planning

---

## 1. Vision

A free, transparent news aggregation platform that delivers World News and US News with sophisticated, per-article bias analysis. Bias insights are central and free — never paywalled. Every source is vetted for credibility, and analysis goes far beyond simple left/right labels.

**One sentence:** The news, dissected — see what every outlet is saying, how they're saying it, and what they're leaving out.

## 2. Problem Statement

| Problem | Industry Status Quo | void --news Solution |
|---------|---------------------|---------------------|
| Bias is per-outlet, not per-article | Most tools label an entire outlet as "left" or "right" regardless of the specific article | Multi-axis NLP analysis on every individual article |
| Bias features are paywalled or limited | Free tiers show limited bias info, full insights require subscriptions | All bias data is free and central to the experience |
| Aggregators include untrusted sources | Low-credibility outlets mixed in with reputable ones | 200 curated, vetted sources only — quality over quantity |
| Left/right is too simplistic | Single-axis political spectrum (left/center/right buckets) | 6-axis analysis: political lean, sensationalism, opinion/fact, factual rigor, framing, per-topic tracking; 7-point lean spectrum (far-left → far-right) |

## 3. Scope

### In Scope (MVP)

- World News and US News coverage
- 200 curated sources across 3 tiers (US major, international, independent); 7-point political lean spectrum
- 2x daily automated pipeline (GitHub Actions)
- Rule-based NLP bias engine (6 axes, zero API cost)
- Gemini Flash summarization for high-value clusters (3+ sources), free-tier only (25 calls/run cap, 150-250 word briefings)
- Story clustering with unified summaries
- Importance ranking with editorial weighting
- Responsive web app (desktop + mobile optimized layouts)
- Static site on GitHub Pages, data in Supabase
- Modern newspaper aesthetic with adaptive dark mode

### Out of Scope (MVP)

- User accounts, authentication, personalization
- Mobile native apps (iOS/Android)
- Real-time/streaming news updates
- Social features (comments, sharing, bookmarks)
- Paid features or subscriptions
- Push notifications
- Paid AI/LLM inference (Gemini Flash used via free tier only, capped at 25 calls/run; all bias analysis remains rule-based)

## 4. Success Criteria

| Metric | Target |
|--------|--------|
| Sources at launch | 200 (49 us_major + 67 international + 84 independent) |
| Pipeline reliability | 95%+ successful runs |
| Pipeline completion time | < 6 minutes (GitHub Actions limit) |
| Bias scoring coverage | 100% of ingested articles scored on all 6 axes |
| Story clustering accuracy | 85%+ correct groupings |
| Frontend Lighthouse score | 90+ (performance, accessibility, SEO) |
| WCAG compliance | 2.1 AA |
| Operational cost | $0/month |

## 5. Architecture Summary

```
GitHub Actions (2x daily) → Python Pipeline → Supabase (PostgreSQL) ← Next.js Static (GitHub Pages)
```

- **Zero backend server** — fully serverless
- **Zero API cost** — all bias NLP is local, rule-based; Gemini Flash cluster summarization uses the free tier (capped at 25 calls/run, 50 RPD)
- **Zero hosting cost** — GitHub Pages + Supabase free tier + GitHub Actions free tier

## 6. Key Design Decisions (Locked)

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Bias model | Per-article, 6-axis, rule-based NLP | Granular per-article analysis instead of static per-outlet labels |
| 2 | Source strategy | 200 curated, vetted; 7-point lean spectrum | Quality over quantity, balanced political representation |
| 3 | Pipeline frequency | 2x daily + frontend refresh from Supabase | Balances freshness with quality analysis time |
| 4 | Frontend framework | Next.js (static export) + React + TypeScript | Modern, dynamic, static-exportable |
| 5 | Responsive strategy | One project, two layouts (desktop/mobile) | Shared logic, optimized presentation |
| 6 | Animation library | Motion One v11 (spring physics) | Proven in DondeAI, ~6.5KB, zero cost |
| 7 | Design philosophy | "Press & Precision" — newspaper aesthetic, modern data density | Clean on arrival, rich on interaction |
| 8 | Typography | Playfair Display (editorial) + Inter (structural) + JetBrains Mono (data) | Three-voice system from DondeAI |
| 9 | Data visualization | Color-coded dot matrix, minimal and intuitive | Information-dense without visual clutter |
| 10 | Story clustering | Unified summary with divergence highlights, link to source outlets | Compresses many sources into one scannable view |
| 11 | Color scheme | Light mode (newspaper warmth) + adaptive dark mode | Both retain newspaper aesthetic, never harsh |
| 12 | Importance ranking | Data-driven + editorial weighting from top outlets per bias category | Cross-spectrum coverage = higher importance |
| 13 | Hosting | GitHub Pages (frontend) + Supabase (data) + GitHub Actions (pipeline) | Zero cost, already set up |
| 14 | Logo | Designed by dedicated logo-designer agent | Professional branding with design expertise |

## 7. Stakeholders

| Role | Person/System | Responsibility |
|------|--------------|----------------|
| CEO | Aacrit | Vision, design decisions, final approval |
| COO | void-coo (agent) | Orchestrates all agents, quality gates |
| Frontend Division | frontend-builder, frontend-fixer, responsive-specialist | UI implementation |
| R&I Division | motion-physics-designer, data-storytelling-designer, micro-interaction-designer, accessibility-inclusivity-lead | Design advisory |
| Infrastructure | perf-optimizer, db-reviewer | Performance, data quality |
| Pipeline | nlp-engineer, source-curator, bias-auditor | NLP engine, source management |
| Branding | logo-designer | Visual identity, logo |

## 8. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| GitHub Actions timeout (>6 min for 200 sources) | Medium | High | Parallelize fetching, batch processing, incremental updates |
| NLP bias scoring inaccuracy | Medium | High | Benchmark against known examples, iterative tuning, bias-auditor agent |
| RSS feed changes/breakage | High | Medium | Health monitoring, fallback scraping, source-curator maintenance |
| Supabase free tier limits | Low | Medium | Efficient queries, prune old articles, monitor usage |
| Story clustering false positives/negatives | Medium | Medium | TF-IDF + headline similarity tuning, human spot-checks |
| Web scraping blocked by outlets | Medium | Low | Respect robots.txt, rotate user agents, prioritize RSS |

## 9. Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1 — Foundation | Week 1-2 | Pipeline scaffolding, source list, Supabase schema, basic fetcher, GitHub Actions |
| Phase 2 — Analysis Engine | Week 3-5 | Full 6-axis bias engine, clustering, categorization, importance ranking |
| Phase 3 — Frontend MVP | Week 6-8 | Desktop + mobile layouts, news feed, bias indicators, deploy to GitHub Pages |
| Phase 4 — Deep Dive | Week 9-11 | Dashboard, story comparison, bias visualizations, framing analysis |
| Phase 5 — Polish & Launch | Week 12 | Accessibility, performance, animation polish, cross-browser testing |

## 10. Budget

**$0/month operational cost.**

| Item | Cost |
|------|------|
| GitHub Actions | Free (public repo) or 2000 min/month (private) |
| GitHub Pages | Free |
| Supabase | Free tier (500MB database, 50K monthly active users) |
| Motion One | Free (CDN) |
| Python NLP libraries | Free (open source) |
| Gemini Flash API | Free tier (1500 RPD limit; capped at 50 RPD = 3.3% of limit) |
| Claude CLI (development) | Existing subscription |
| **Total** | **$0/month** |

## 11. Definition of Done

The MVP is complete when:

- [ ] 200 sources actively ingested 2x daily with 95%+ reliability
- [ ] All 6 bias axes scored on every article
- [ ] Story clustering groups related articles with 85%+ accuracy
- [ ] Desktop layout renders newspaper-style multi-column grid
- [ ] Mobile layout renders single-column feed with bottom navigation
- [ ] Deep Dive shows unified summary with divergence highlights and source links
- [ ] Bias dot matrix displays inline on every story card
- [ ] Importance ranking factors editorial weight across bias categories
- [ ] Light and dark modes both retain newspaper aesthetic
- [ ] Lighthouse score 90+ on all categories
- [ ] WCAG 2.1 AA compliant
- [ ] Deployed to GitHub Pages with $0 operational cost
