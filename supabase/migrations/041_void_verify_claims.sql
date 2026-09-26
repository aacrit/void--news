-- ============================================================
-- void --verify: Claim Consensus Engine
-- Migration 041
-- ============================================================

-- Per-article extracted claims (normalized, queryable)
CREATE TABLE article_claims (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
    cluster_id UUID REFERENCES story_clusters(id) ON DELETE SET NULL,

    -- Claim content
    claim_text TEXT NOT NULL,
    source_sentence TEXT,
    subject_entity TEXT,
    subject_entity_type TEXT,
    claim_type TEXT DEFAULT 'statement'
        CHECK (claim_type IN ('quantitative', 'attribution', 'event', 'statement')),
    has_quantitative BOOLEAN DEFAULT FALSE,

    -- Verification
    status TEXT DEFAULT 'unverified'
        CHECK (status IN (
            'unverified',
            'corroborated',
            'single_source',
            'disputed',
            'later_corroborated',
            'later_contradicted'
        )),
    corroboration_count INTEGER DEFAULT 0,
    corroborating_sources TEXT[] DEFAULT '{}',

    -- Contradiction details
    contradiction_type TEXT
        CHECK (contradiction_type IN ('negation', 'numeric', 'entity_swap')
               OR contradiction_type IS NULL),
    contradicting_claim_id UUID REFERENCES article_claims(id),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_claims_cluster ON article_claims(cluster_id);
CREATE INDEX idx_claims_article ON article_claims(article_id);
CREATE INDEX idx_claims_status ON article_claims(status);
CREATE INDEX idx_claims_entity ON article_claims(subject_entity) WHERE subject_entity IS NOT NULL;

-- Pre-aggregated consensus JSONB on story_clusters
ALTER TABLE story_clusters ADD COLUMN IF NOT EXISTS claim_consensus JSONB;

-- Phase 2: Source track record (longitudinal accuracy)
CREATE TABLE source_claim_accuracy (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    source_slug TEXT NOT NULL UNIQUE,
    source_name TEXT,

    total_unique_claims INTEGER DEFAULT 0,
    later_corroborated INTEGER DEFAULT 0,
    later_contradicted INTEGER DEFAULT 0,
    still_unverified INTEGER DEFAULT 0,

    accuracy_rate REAL DEFAULT 0.0,
    trend TEXT DEFAULT 'stable'
        CHECK (trend IN ('improving', 'stable', 'declining')),

    accuracy_30d REAL,
    accuracy_90d REAL,

    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_accuracy_slug ON source_claim_accuracy(source_slug);
CREATE INDEX idx_accuracy_rate ON source_claim_accuracy(accuracy_rate);

-- View: cluster claim summary for frontend
CREATE OR REPLACE VIEW cluster_claim_summary AS
SELECT
    sc.id AS cluster_id,
    sc.title,
    (sc.claim_consensus->>'consensus_ratio')::REAL AS consensus_ratio,
    (sc.claim_consensus->>'total_claims')::INTEGER AS total_claims,
    (sc.claim_consensus->>'disputed')::INTEGER AS disputed_count,
    sc.claim_consensus->>'consensus_summary' AS consensus_summary
FROM story_clusters sc
WHERE sc.claim_consensus IS NOT NULL;
