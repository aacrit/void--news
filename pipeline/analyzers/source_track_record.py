"""
Source track record for void --verify Phase 2.

Longitudinal tracking of source accuracy: how often does a source's unique
(single-source) claims get confirmed or contradicted by other sources in
subsequent pipeline runs?

Runs as Step 9d after topic tracking. Non-critical — failures don't kill
the pipeline.
"""

import re
from datetime import datetime, timedelta, timezone

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


_CORROBORATION_THRESHOLD = 0.65

# Negation detection (subset of claim_verifier patterns)
_NEGATION_MAP = {
    "confirmed": "denied", "denied": "confirmed",
    "approved": "rejected", "rejected": "approved",
    "increased": "decreased", "decreased": "increased",
    "rose": "fell", "fell": "rose",
    "gained": "lost", "lost": "gained",
    "allowed": "banned", "banned": "allowed",
}
_NEGATION_TOKENS = frozenset({"not", "no", "never", "neither", "nor", "without"})


def _has_negation_conflict(text_a: str, text_b: str) -> bool:
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    neg_a = words_a & _NEGATION_TOKENS
    neg_b = words_b & _NEGATION_TOKENS
    if neg_a != neg_b and (neg_a or neg_b):
        return True
    for word in words_a:
        antonym = _NEGATION_MAP.get(word)
        if antonym and antonym in words_b:
            return True
    return False


def update_source_track_record(supabase) -> dict:
    """
    Update source accuracy records based on single-source claim outcomes.

    Looks at single-source claims from 6-24h ago and checks if newer claims
    from different sources corroborate or contradict them.

    Returns summary stats dict.
    """
    if not SKLEARN_AVAILABLE:
        print("  [warn] sklearn not available, skipping source track record")
        return {"skipped": True}

    now = datetime.now(timezone.utc)
    eval_start = (now - timedelta(hours=24)).isoformat()
    eval_end = (now - timedelta(hours=6)).isoformat()

    # Fetch single-source claims in the evaluation window
    try:
        res = supabase.table("article_claims").select(
            "id,claim_text,subject_entity,article_id,cluster_id,"
            "corroborating_sources,created_at"
        ).eq(
            "status", "single_source"
        ).gte(
            "created_at", eval_start
        ).lte(
            "created_at", eval_end
        ).limit(500).execute()

        single_claims = res.data or []
    except Exception as e:
        print(f"  [warn] Failed to fetch single-source claims: {e}")
        return {"error": str(e)}

    if not single_claims:
        print("  No single-source claims in evaluation window")
        return {"evaluated": 0}

    # Fetch newer claims (from after the evaluation window) for comparison
    try:
        newer_res = supabase.table("article_claims").select(
            "id,claim_text,subject_entity,article_id,"
            "corroborating_sources,status"
        ).gt(
            "created_at", eval_end
        ).in_(
            "status", ["corroborated", "single_source", "unverified"]
        ).limit(2000).execute()

        newer_claims = newer_res.data or []
    except Exception as e:
        print(f"  [warn] Failed to fetch newer claims: {e}")
        return {"error": str(e)}

    if not newer_claims:
        print("  No newer claims for comparison")
        return {"evaluated": len(single_claims), "matched": 0}

    # Build TF-IDF matrix for newer claims
    newer_texts = [c.get("claim_text", "") for c in newer_claims]
    single_texts = [c.get("claim_text", "") for c in single_claims]

    try:
        all_texts = single_texts + newer_texts
        vectorizer = TfidfVectorizer(max_df=1.0, min_df=1, stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(all_texts)

        n_single = len(single_texts)
        single_matrix = tfidf_matrix[:n_single]
        newer_matrix = tfidf_matrix[n_single:]
        sim_matrix = cosine_similarity(single_matrix, newer_matrix)
    except ValueError:
        return {"evaluated": len(single_claims), "matched": 0}

    # Check each single-source claim against newer claims
    corroborated_ids = []
    contradicted_ids = []
    source_stats: dict[str, dict] = {}  # source_slug -> {corr, contra}

    for i, claim in enumerate(single_claims):
        claim_id = claim.get("id")
        claim_sources = claim.get("corroborating_sources", []) or []
        claim_source = claim_sources[0] if claim_sources else ""

        best_sim = 0.0
        best_j = -1
        for j in range(len(newer_claims)):
            if sim_matrix[i, j] > best_sim:
                newer_sources = newer_claims[j].get("corroborating_sources", []) or []
                # Must be from a different source
                if claim_source and newer_sources and claim_source not in newer_sources:
                    best_sim = sim_matrix[i, j]
                    best_j = j

        if best_sim < _CORROBORATION_THRESHOLD or best_j < 0:
            continue

        # Check if corroboration or contradiction
        newer_text = newer_claims[best_j].get("claim_text", "")
        single_text = claim.get("claim_text", "")

        if _has_negation_conflict(single_text, newer_text):
            contradicted_ids.append(claim_id)
            source_stats.setdefault(claim_source, {"corr": 0, "contra": 0})
            source_stats[claim_source]["contra"] += 1
        else:
            corroborated_ids.append(claim_id)
            source_stats.setdefault(claim_source, {"corr": 0, "contra": 0})
            source_stats[claim_source]["corr"] += 1

    # Update claim statuses
    updated = 0
    for claim_id in corroborated_ids:
        try:
            supabase.table("article_claims").update(
                {"status": "later_corroborated", "updated_at": now.isoformat()}
            ).eq("id", claim_id).execute()
            updated += 1
        except Exception:
            pass

    for claim_id in contradicted_ids:
        try:
            supabase.table("article_claims").update(
                {"status": "later_contradicted", "updated_at": now.isoformat()}
            ).eq("id", claim_id).execute()
            updated += 1
        except Exception:
            pass

    # Update source accuracy table
    for slug, stats in source_stats.items():
        try:
            # Fetch current record
            existing = supabase.table("source_claim_accuracy").select(
                "*"
            ).eq("source_slug", slug).limit(1).execute()

            if existing.data:
                rec = existing.data[0]
                total = rec.get("total_unique_claims", 0)
                corr = rec.get("later_corroborated", 0) + stats["corr"]
                contra = rec.get("later_contradicted", 0) + stats["contra"]
                unverified = max(0, total - corr - contra)
                denom = corr + contra
                rate = corr / denom if denom > 0 else 0.0

                # Compute trend vs existing rate
                old_rate = rec.get("accuracy_rate", 0.0) or 0.0
                if rate > old_rate + 0.05:
                    trend = "improving"
                elif rate < old_rate - 0.05:
                    trend = "declining"
                else:
                    trend = "stable"

                supabase.table("source_claim_accuracy").update({
                    "later_corroborated": corr,
                    "later_contradicted": contra,
                    "still_unverified": unverified,
                    "accuracy_rate": round(rate, 4),
                    "trend": trend,
                    "updated_at": now.isoformat(),
                }).eq("source_slug", slug).execute()
            else:
                # Create new record
                corr = stats["corr"]
                contra = stats["contra"]
                total = corr + contra
                denom = corr + contra
                rate = corr / denom if denom > 0 else 0.0
                supabase.table("source_claim_accuracy").upsert({
                    "source_slug": slug,
                    "total_unique_claims": total,
                    "later_corroborated": corr,
                    "later_contradicted": contra,
                    "still_unverified": 0,
                    "accuracy_rate": round(rate, 4),
                    "trend": "stable",
                    "updated_at": now.isoformat(),
                }, on_conflict="source_slug").execute()
        except Exception as e:
            print(f"  [warn] Failed to update accuracy for {slug}: {e}")

    result = {
        "evaluated": len(single_claims),
        "corroborated": len(corroborated_ids),
        "contradicted": len(contradicted_ids),
        "sources_updated": len(source_stats),
        "claims_updated": updated,
    }
    print(f"  Source track record: {result}")
    return result
