# void --news — Project Charter

**Date:** 2026-04-03 (rev 7)
**Project Owner:** Aacrit (CEO)
**Status:** Phase 4 In Progress

---

## 1. Vision

A free, transparent news aggregation platform delivering World, US, Europe, and South Asia news with per-article, multi-axis bias analysis. Bias insights are central and free — never paywalled. Every source is vetted for credibility.

**One sentence:** The news, dissected — see what every outlet is saying, how they're saying it, and what they're leaving out.

## 2. Problem Statement

| Problem | Industry Status Quo | void --news Solution |
|---------|---------------------|---------------------|
| Bias is per-outlet, not per-article | Tools label an entire outlet "left" or "right" | Multi-axis NLP on every individual article |
| Bias features are paywalled | Full insights require subscriptions | All bias data free and central |
| Aggregators include untrusted sources | Low-credibility outlets mixed in | 1,013 curated, vetted sources only |
| Left/right is too simplistic | Single-axis spectrum | 6-axis analysis + 7-point lean spectrum (far-left → far-right) |

## 3. Scope

### In Scope (MVP)
- World, US, Europe, and South Asia editions (4 editions)
- 1,013 curated sources across 3 tiers (43 us_major, 373 international, 597 independent); 7-point political lean spectrum; 158 countries
- 4x daily automated pipeline (GitHub Actions)
- Rule-based NLP bias engine (6 axes, $0 cost)
- Gemini Flash: cluster summarization + editorial importance + reasoning (~116 RPD, free tier)
- Story clustering with v6.0 importance ranking (10 signals + Gemini editorial intelligence + edition-unique ranking)
- Responsive web app (desktop + mobile)
- Static site on GitHub Pages, data in Supabase

### Out of Scope (MVP)
- User accounts, authentication, personalization
- Mobile native apps (iOS/Android)
- Real-time/streaming updates
- Social features (comments, sharing, bookmarks)
- Paid features or subscriptions
- Paid AI/LLM inference

## 4. Success Criteria

| Metric | Target |
|--------|--------|
| Sources at launch | 1,013 (43 us_major + 373 international + 597 independent) |
| Pipeline reliability | 95%+ successful runs |
| Pipeline completion time | < 6 minutes per run |
| Bias scoring coverage | 100% of articles scored on all 6 axes |
| Story clustering accuracy | 85%+ correct groupings |
| Frontend Lighthouse score | 90+ |
| WCAG compliance | 2.1 AA |
| Operational cost | $0/month |

## 5. Architecture Summary

```
GitHub Actions (4x daily) → Python Pipeline → Supabase (PostgreSQL) ← Next.js Static (GitHub Pages)
```

- **Zero backend server** — fully serverless
- **Zero API cost** — NLP is local/rule-based; Gemini Flash on free tier (~116 RPD)
- **Zero hosting cost** — GitHub Pages + Supabase + GitHub Actions free tiers

## 6. Key Design Decisions (Locked)

| # | Decision | Choice |
|---|----------|--------|
| 1 | Bias model | Per-article, 6-axis, rule-based NLP |
| 2 | Source strategy | 1,013 curated (158 countries); 7-point lean spectrum |
| 3 | Pipeline frequency | 4x daily (every 6h, all editions each run) |
| 4 | Frontend | Next.js 16 (static export) + React 19 + TypeScript |
| 5 | Responsive | One project, two layouts (desktop/mobile) |
| 6 | Animation | Motion One v11 (spring physics, ~6.5KB CDN) |
| 7 | Design | "Press & Precision" — newspaper aesthetic, modern data density |
| 8 | Typography | Playfair Display + Inter + Barlow Condensed + IBM Plex Mono |
| 9 | Bias viz | BiasLens Three Lenses (Beam, Ring, Prism) |
| 10 | Ranking | v6.0: 10 deterministic signals + Gemini editorial intelligence + edition-unique ranking |
| 11 | Color | Light mode (warm paper) + adaptive dark mode |
| 12 | Hosting | GitHub Pages + Supabase + GitHub Actions |

## 7. Stakeholders

| Role | Person/System |
|------|--------------|
| CEO | Aacrit |
| Frontend | frontend-builder, frontend-fixer, responsive-specialist |
| Infrastructure | perf-optimizer, db-reviewer |
| Pipeline | nlp-engineer, source-curator, bias-auditor |
| Branding | logo-designer |

## 8. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| GitHub Actions timeout | Medium | High | Parallel fetching, batch processing |
| NLP bias scoring inaccuracy | Medium | High | Benchmark against known examples, bias-auditor agent |
| RSS feed changes/breakage | High | Medium | Health monitoring, fallback scraping |
| Supabase free tier limits | Low | Medium | Efficient queries, prune old articles |
| Story clustering false positives | Medium | Medium | Two-phase algorithm, human spot-checks |

## 9. Timeline

| Phase | Status | Deliverable |
|-------|--------|-------------|
| Phase 1 — Foundation | COMPLETE | Pipeline, source list, Supabase schema, fetchers, GitHub Actions |
| Phase 2 — Analysis Engine | COMPLETE | 6-axis bias engine, clustering, ranking v6.0, Gemini integration |
| Phase 3 — Frontend MVP | COMPLETE | Desktop + mobile layouts, news feed, BiasLens, deploy pending |
| Phase 4 — Deep Dive | IN PROGRESS | Dashboard, source comparison, bias viz, framing analysis |
| Phase 5 — Polish & Launch | PENDING | Accessibility, performance, animation polish, cross-browser |

## 10. Budget

**$0/month operational cost.**

| Item | Cost |
|------|------|
| GitHub Actions | Free (public repo) |
| GitHub Pages | Free |
| Supabase | Free tier |
| Motion One | Free (CDN) |
| Python NLP libraries | Free (open source) |
| Gemini Flash API | Free tier (~116 RPD / 10.4% of 1500 RPD limit) |
| Claude CLI (development) | Existing Max subscription |
| **Total** | **$0/month** |

## 11. Definition of Done

The MVP is complete when:

- [ ] 1,013 sources actively ingested 4x daily with 95%+ reliability
- [ ] All 6 bias axes scored on every article
- [ ] Story clustering groups related articles with 85%+ accuracy
- [ ] Desktop layout renders newspaper-style multi-column grid
- [ ] Mobile layout renders single-column feed with bottom navigation
- [ ] Deep Dive shows unified summary with divergence highlights and source links
- [ ] BiasLens Three Lenses displays inline on every story card
- [ ] v6.0 importance ranking active with edition-unique ranking
- [ ] Light and dark modes retain newspaper aesthetic
- [ ] Lighthouse score 90+ on all categories
- [ ] WCAG 2.1 AA compliant
- [ ] Deployed to GitHub Pages with $0 operational cost
