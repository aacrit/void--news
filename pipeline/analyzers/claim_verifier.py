"""
Cross-source claim verification for void --verify (Claim Consensus engine).

Takes NLP-extracted claims from multiple articles in a cluster and determines
which claims are corroborated, disputed, or single-source. Uses TF-IDF
cosine similarity for matching and negation/numeric detection for
contradictions. Rule-based, $0 cost.
"""

import re
from dataclasses import dataclass, field

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


# ---------------------------------------------------------------------------
# Negation pairs for contradiction detection
# ---------------------------------------------------------------------------
NEGATION_PAIRS = [
    ("confirmed", "denied"), ("approved", "rejected"), ("agreed", "disagreed"),
    ("accepted", "refused"), ("supported", "opposed"), ("advanced", "retreated"),
    ("increased", "decreased"), ("rose", "fell"), ("gained", "lost"),
    ("allowed", "banned"), ("released", "detained"), ("survived", "died"),
]

NEGATION_TOKENS = frozenset({"not", "no", "never", "neither", "nor", "without"})

# Build lookup for fast pair detection
_NEGATION_MAP: dict[str, str] = {}
for a, b in NEGATION_PAIRS:
    _NEGATION_MAP[a] = b
    _NEGATION_MAP[b] = a

# Number extraction pattern
_NUMBER_PATTERN = re.compile(r'[\d,]+\.?\d*')

# Cosine thresholds
_CORROBORATION_THRESHOLD = 0.65
_ENTITY_RELAXED_THRESHOLD = 0.30
_CONTRADICTION_THRESHOLD = 0.50
_NUMERIC_DIVERGENCE = 0.20  # 20% difference


@dataclass
class VerifiedClaim:
    claim_text: str
    status: str = "unverified"  # corroborated | single_source | disputed
    source_count: int = 1
    sources: list[str] = field(default_factory=list)
    source_names: list[str] = field(default_factory=list)
    highlight: bool = False


@dataclass
class DisputedClaim:
    topic: str = ""
    version_a: str = ""
    version_a_sources: list[str] = field(default_factory=list)
    version_b: str = ""
    version_b_sources: list[str] = field(default_factory=list)
    contradiction_type: str = "negation"  # negation | numeric | entity_swap


@dataclass
class ClusterConsensus:
    cluster_id: str = ""
    total_claims: int = 0
    corroborated: int = 0
    single_source: int = 0
    disputed: int = 0
    consensus_ratio: float = 0.0
    claims: list[VerifiedClaim] = field(default_factory=list)
    disputed_details: list[DisputedClaim] = field(default_factory=list)


def _extract_numbers(text: str) -> list[float]:
    """Extract numeric values from text."""
    matches = _NUMBER_PATTERN.findall(text)
    nums = []
    for m in matches:
        try:
            nums.append(float(m.replace(",", "")))
        except ValueError:
            pass
    return nums


def _has_negation_conflict(text_a: str, text_b: str) -> bool:
    """Check if two texts have a negation-based contradiction."""
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())

    # Check negation token asymmetry
    neg_a = words_a & NEGATION_TOKENS
    neg_b = words_b & NEGATION_TOKENS
    if neg_a != neg_b and (neg_a or neg_b):
        return True

    # Check antonym verb pairs
    for word in words_a:
        antonym = _NEGATION_MAP.get(word)
        if antonym and antonym in words_b:
            return True

    return False


def _has_numeric_conflict(text_a: str, text_b: str) -> bool:
    """Check if two texts have conflicting numbers (>20% divergence)."""
    nums_a = _extract_numbers(text_a)
    nums_b = _extract_numbers(text_b)

    if not nums_a or not nums_b:
        return False

    for na in nums_a:
        for nb in nums_b:
            if na == 0 and nb == 0:
                continue
            # Magnitude gating: only compare numbers in similar ranges
            if na > 0 and nb > 0:
                ratio = max(na, nb) / min(na, nb)
                if ratio > 100:
                    continue  # Different scales (e.g., "5.25%" vs "1000 people")
            denom = max(abs(na), abs(nb))
            if denom > 0 and abs(na - nb) / denom > _NUMERIC_DIVERGENCE:
                return True

    return False


def _get_entity(claim) -> str:
    """Get lowercase subject entity from a claim object."""
    entity = getattr(claim, "subject_entity", "") or ""
    return entity.lower().strip()


class _UnionFind:
    """Simple union-find for grouping corroborated claims."""

    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x: int, y: int) -> None:
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1


def verify_claims_in_cluster(
    cluster_id: str,
    cluster_claims: dict[str, list],
    source_info: dict[str, str] | None = None,
) -> ClusterConsensus:
    """
    Verify claims across sources within a cluster.

    Args:
        cluster_id: The cluster identifier.
        cluster_claims: Dict of article_id -> list of Claim objects.
        source_info: Optional dict of source_slug -> source_name.

    Returns:
        ClusterConsensus with aggregated verification results.
    """
    if not SKLEARN_AVAILABLE:
        print("  [warn] sklearn not available, skipping claim verification")
        return ClusterConsensus(cluster_id=cluster_id)

    # Flatten all claims with source tracking
    all_claims = []
    claim_sources = []  # (source_slug, source_name) per claim
    for art_id, claims in cluster_claims.items():
        for claim in claims:
            all_claims.append(claim)
            slug = getattr(claim, "source_slug", "") or ""
            name = getattr(claim, "source_name", "") or ""
            if not name and source_info:
                name = source_info.get(slug, "")
            claim_sources.append((slug, name))

    if len(all_claims) < 2:
        # Single-article or empty — all claims are single-source
        verified = [
            VerifiedClaim(
                claim_text=c.claim_text,
                status="single_source",
                source_count=1,
                sources=[claim_sources[i][0]],
                source_names=[claim_sources[i][1]],
            )
            for i, c in enumerate(all_claims)
        ]
        return ClusterConsensus(
            cluster_id=cluster_id,
            total_claims=len(verified),
            single_source=len(verified),
            consensus_ratio=0.0,
            claims=verified,
        )

    # Build TF-IDF matrix
    texts = [c.claim_text for c in all_claims]
    try:
        vectorizer = TfidfVectorizer(max_df=1.0, min_df=1, stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(texts)
        sim_matrix = cosine_similarity(tfidf_matrix)
    except ValueError:
        # All claims are identical or vectorizer fails
        return ClusterConsensus(cluster_id=cluster_id, total_claims=len(all_claims))

    n = len(all_claims)
    uf = _UnionFind(n)

    # Primary matching: TF-IDF cosine > threshold, different sources
    for i in range(n):
        for j in range(i + 1, n):
            if claim_sources[i][0] == claim_sources[j][0]:
                continue  # Same source, skip
            if sim_matrix[i, j] >= _CORROBORATION_THRESHOLD:
                uf.union(i, j)
            # Entity-relaxed secondary matching
            elif sim_matrix[i, j] >= _ENTITY_RELAXED_THRESHOLD:
                ent_i = _get_entity(all_claims[i])
                ent_j = _get_entity(all_claims[j])
                if ent_i and ent_j and ent_i == ent_j:
                    uf.union(i, j)

    # Build groups
    groups: dict[int, list[int]] = {}
    for i in range(n):
        root = uf.find(i)
        groups.setdefault(root, []).append(i)

    # Classify each group
    verified_claims: list[VerifiedClaim] = []
    disputed_details: list[DisputedClaim] = []
    corroborated_count = 0
    single_source_count = 0
    disputed_count = 0

    for root, members in groups.items():
        unique_sources = set()
        source_names_set = set()
        for idx in members:
            slug = claim_sources[idx][0]
            name = claim_sources[idx][1]
            if slug:
                unique_sources.add(slug)
            if name:
                source_names_set.add(name)

        # Pick the most representative claim text (longest)
        best_idx = max(members, key=lambda i: len(all_claims[i].claim_text))
        canonical_text = all_claims[best_idx].claim_text

        if len(unique_sources) >= 2:
            # Check for contradictions within the group
            contradiction_found = False
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    idx_a, idx_b = members[i], members[j]
                    if claim_sources[idx_a][0] == claim_sources[idx_b][0]:
                        continue

                    text_a = all_claims[idx_a].claim_text
                    text_b = all_claims[idx_b].claim_text

                    if _has_negation_conflict(text_a, text_b):
                        contradiction_found = True
                        disputed_details.append(DisputedClaim(
                            topic=_get_entity(all_claims[best_idx]) or canonical_text[:50],
                            version_a=text_a,
                            version_a_sources=[claim_sources[idx_a][1] or claim_sources[idx_a][0]],
                            version_b=text_b,
                            version_b_sources=[claim_sources[idx_b][1] or claim_sources[idx_b][0]],
                            contradiction_type="negation",
                        ))
                        break
                    elif _has_numeric_conflict(text_a, text_b):
                        contradiction_found = True
                        disputed_details.append(DisputedClaim(
                            topic=_get_entity(all_claims[best_idx]) or canonical_text[:50],
                            version_a=text_a,
                            version_a_sources=[claim_sources[idx_a][1] or claim_sources[idx_a][0]],
                            version_b=text_b,
                            version_b_sources=[claim_sources[idx_b][1] or claim_sources[idx_b][0]],
                            contradiction_type="numeric",
                        ))
                        break
                if contradiction_found:
                    break

            if contradiction_found:
                status = "disputed"
                disputed_count += 1
            else:
                status = "corroborated"
                corroborated_count += 1

            verified_claims.append(VerifiedClaim(
                claim_text=canonical_text,
                status=status,
                source_count=len(unique_sources),
                sources=sorted(unique_sources),
                source_names=sorted(source_names_set),
                highlight=len(unique_sources) >= 3,
            ))
        else:
            # Single source
            single_source_count += 1
            verified_claims.append(VerifiedClaim(
                claim_text=canonical_text,
                status="single_source",
                source_count=1,
                sources=sorted(unique_sources),
                source_names=sorted(source_names_set),
            ))

    total = corroborated_count + single_source_count + disputed_count
    ratio = corroborated_count / total if total > 0 else 0.0

    return ClusterConsensus(
        cluster_id=cluster_id,
        total_claims=total,
        corroborated=corroborated_count,
        single_source=single_source_count,
        disputed=disputed_count,
        consensus_ratio=round(ratio, 3),
        claims=verified_claims,
        disputed_details=disputed_details,
    )


def verify_all_clusters(
    all_claims: dict[str, dict[str, list]],
    source_info: dict[str, str] | None = None,
) -> dict[str, ClusterConsensus]:
    """
    Verify claims across all clusters.

    Args:
        all_claims: Dict of cluster_id -> {article_id -> [Claims]}.
        source_info: Optional dict of source_slug -> source_name.

    Returns:
        Dict of cluster_id -> ClusterConsensus.
    """
    results: dict[str, ClusterConsensus] = {}
    total_corroborated = 0
    total_disputed = 0
    total_single = 0

    for cluster_id, cluster_claims in all_claims.items():
        consensus = verify_claims_in_cluster(cluster_id, cluster_claims, source_info)
        results[cluster_id] = consensus
        total_corroborated += consensus.corroborated
        total_disputed += consensus.disputed
        total_single += consensus.single_source

    print(f"  Verification: {len(results)} clusters — "
          f"{total_corroborated} corroborated, {total_disputed} disputed, "
          f"{total_single} single-source")
    return results
