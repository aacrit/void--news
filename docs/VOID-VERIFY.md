# void --verify — Claim Consensus

Last updated: 2026-04-28 (rev 1)

> *We don't tell you what's true. We show you who agrees.*

Cross-source factual verification through NLP claim extraction, cluster-level corroboration scoring, and cinematic contradiction surfacing.

## Product Identity

- **Product name**: `void --verify`
- **UI section label**: "Claim Consensus"
- **Philosophy**: void --news is not a fact-checking organization. It counts sources per claim within a cluster and surfaces contradictions. Show evidence, let the reader decide.

## Architecture

```
Step 6a: spaCy SVO+NER → claim extraction (~50ms/article)
Step 6a-ii: TF-IDF cosine → cross-source verification
Step 7b: Gemini prompt extension → claim deduplication (0 extra calls)
Step 8: Store → article_claims table + claim_consensus JSONB
Step 9d: Source track record → longitudinal accuracy (Phase 2)
```

## Pipeline Files

| File | Purpose |
|------|---------|
| `pipeline/analyzers/claim_extractor.py` | spaCy dep parse → SVO triples with NER + data patterns |
| `pipeline/analyzers/claim_verifier.py` | TF-IDF cosine matching + negation/numeric contradiction detection |
| `pipeline/analyzers/source_track_record.py` | Phase 2: longitudinal source accuracy tracking |

## Database (Migration 041)

- `article_claims` — per-article extracted claims with verification status
- `story_clusters.claim_consensus` — JSONB pre-aggregated for frontend
- `source_claim_accuracy` — Phase 2 source track record
- `cluster_claim_summary` — view for frontend reads

## Frontend Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `ConsensusBadge` | Cards (near Sigil) | Consensus ratio badge (12/15) |
| `ClaimMark` | Deep Dive summary | Inline contradiction highlight with rack-focus popover |
| `ClaimConsensusSection` | Deep Dive | Full claim breakdown section |
| `CredibilityArc` | Sources page | Phase 2: source accuracy sparkline |

## Cinematic Design

- **Dormant**: wavy amber underline + haze filter (copy editor's mark)
- **Focused**: rack focus snap (filter: none) + amber background gradient
- **Popover**: blur-in entrance (350ms ease-cinematic) with competing claim + sources
- **Badge**: lightning mark pulse on first viewport entry
- **Consensus bar**: left-to-right fill (800ms ease-cinematic)

## Performance

- Pipeline: +2-4 minutes per run
- Gemini: 0 additional API calls
- DB: ~15K claim rows per run
- Frontend: 0 additional queries (data in cluster fetch)
- Cost: $0
