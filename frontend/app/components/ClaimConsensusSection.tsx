"use client";

import { useState, useRef, useEffect } from "react";
import type { ClaimConsensus, VerifiedClaim, DisputedClaim } from "../lib/types";

/* ===========================================================================
   ClaimConsensusSection — void --verify
   Full claim breakdown for the Deep Dive panel. Renders after Source
   Perspectives. Shows consensus ratio bar, corroborated/disputed/single-source
   claims with progressive disclosure.

   Cinematic: consensus bar fills left-to-right on mount (800ms ease-cinematic).
   Disputed claims pulse on first reveal. Single-source claims collapsed by
   default with ease-rack expand/collapse.
   =========================================================================== */

interface ClaimConsensusSectionProps {
  consensus: ClaimConsensus;
}

/* ── Consensus Ratio Bar ──────────────────────────────────────────────────── */

function ConsensusBar({
  corroborated,
  disputed,
  singleSource,
  total,
  mounted,
}: {
  corroborated: number;
  disputed: number;
  singleSource: number;
  total: number;
  mounted: boolean;
}) {
  if (total <= 0) return null;

  const corrobPct = (corroborated / total) * 100;
  const disputedPct = (disputed / total) * 100;
  const singlePct = (singleSource / total) * 100;

  return (
    <div
      className="cc-bar"
      role="img"
      aria-label={`${corroborated} corroborated, ${disputed} disputed, ${singleSource} single-source out of ${total} claims`}
    >
      <div className="cc-bar__track">
        <div
          className="cc-bar__segment cc-bar__segment--corroborated"
          style={{
            width: mounted ? `${corrobPct}%` : "0%",
          }}
        />
        <div
          className="cc-bar__segment cc-bar__segment--disputed"
          style={{
            width: mounted ? `${disputedPct}%` : "0%",
          }}
        />
        <div
          className="cc-bar__segment cc-bar__segment--single"
          style={{
            width: mounted ? `${singlePct}%` : "0%",
          }}
        />
      </div>
      <div className="cc-bar__legend">
        <span className="cc-bar__legend-item cc-bar__legend-item--corroborated">
          {corroborated} corroborated
        </span>
        <span className="cc-bar__legend-item cc-bar__legend-item--disputed">
          {disputed} disputed
        </span>
        <span className="cc-bar__legend-item cc-bar__legend-item--single">
          {singleSource} unverified
        </span>
      </div>
    </div>
  );
}

/* ── Claim Row ────────────────────────────────────────────────────────────── */

function ClaimRow({
  claim,
  index,
}: {
  claim: VerifiedClaim;
  index: number;
}) {
  const statusClass =
    claim.status === "corroborated"
      ? "cc-claim--corroborated"
      : claim.status === "disputed"
        ? "cc-claim--disputed"
        : "cc-claim--single";

  return (
    <li
      className={`cc-claim ${statusClass}`}
      style={{
        animationDelay: `${index * 60}ms`,
      }}
    >
      <p className="cc-claim__text">{claim.text}</p>
      <span className="cc-claim__meta">
        {claim.source_count} source{claim.source_count !== 1 ? "s" : ""}
        {claim.sources.length > 0 && (
          <>
            {" "}
            <span className="cc-claim__source-list">
              {claim.sources.join(", ")}
            </span>
          </>
        )}
      </span>
    </li>
  );
}

/* ── Dispute Row ──────────────────────────────────────────────────────────── */

function DisputeRow({
  dispute,
  index,
}: {
  dispute: DisputedClaim;
  index: number;
}) {
  return (
    <li
      className="cc-dispute"
      style={{ animationDelay: `${index * 80}ms` }}
    >
      <span className="cc-dispute__topic">{dispute.topic}</span>
      <div className="cc-dispute__versions">
        <div className="cc-dispute__version">
          <p className="cc-dispute__text">{dispute.version_a}</p>
          <span className="cc-dispute__sources">
            {dispute.version_a_sources.join(", ")}
          </span>
        </div>
        <span className="cc-dispute__vs" aria-hidden="true">
          vs
        </span>
        <div className="cc-dispute__version">
          <p className="cc-dispute__text">{dispute.version_b}</p>
          <span className="cc-dispute__sources">
            {dispute.version_b_sources.join(", ")}
          </span>
        </div>
      </div>
    </li>
  );
}

/* ── Main Section ─────────────────────────────────────────────────────────── */

export default function ClaimConsensusSection({
  consensus,
}: ClaimConsensusSectionProps) {
  const [mounted, setMounted] = useState(false);
  const [singleExpanded, setSingleExpanded] = useState(false);
  const sectionRef = useRef<HTMLElement>(null);

  // Trigger bar animation after mount
  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 80);
    return () => clearTimeout(t);
  }, []);

  const corroboratedClaims = consensus.highlighted_claims.filter(
    (c) => c.status === "corroborated",
  );
  const singleSourceClaims = consensus.highlighted_claims.filter(
    (c) => c.status === "single_source",
  );
  const disputedClaims = consensus.disputed_details;

  return (
    <section
      ref={sectionRef}
      className="cc-section"
      aria-label="Claim Consensus"
    >
      {/* Header */}
      <div className="cc-header">
        <h3 className="cc-header__title dd-section-label">Claim Consensus</h3>
        <span className="cc-header__ratio">
          {Math.round(consensus.consensus_ratio * 100)}% corroborated
        </span>
      </div>

      {/* Consensus ratio bar */}
      <ConsensusBar
        corroborated={consensus.corroborated}
        disputed={consensus.disputed}
        singleSource={consensus.single_source}
        total={consensus.total_claims}
        mounted={mounted}
      />

      {/* Summary */}
      {consensus.consensus_summary && (
        <p className="cc-summary">{consensus.consensus_summary}</p>
      )}

      {/* Corroborated claims */}
      {corroboratedClaims.length > 0 && (
        <div className="cc-claims">
          <h4 className="cc-claims__heading">Corroborated</h4>
          <ul className="cc-claims__list">
            {corroboratedClaims.map((claim, i) => (
              <ClaimRow key={`corr-${claim.text.slice(0, 50)}`} claim={claim} index={i} />
            ))}
          </ul>
        </div>
      )}

      {/* Disputed claims */}
      {disputedClaims.length > 0 && (
        <div className="cc-claims">
          <h4 className="cc-claims__heading cc-claims__heading--disputed">
            Disputed
          </h4>
          <ul className="cc-claims__list">
            {disputedClaims.map((dispute, i) => (
              <DisputeRow key={`disp-${dispute.topic.slice(0, 50)}`} dispute={dispute} index={i} />
            ))}
          </ul>
        </div>
      )}

      {/* Single-source claims — collapsed by default */}
      {singleSourceClaims.length > 0 && (
        <div className="cc-claims">
          <button
            className="cc-expand"
            onClick={() => setSingleExpanded((v) => !v)}
            aria-expanded={singleExpanded}
            aria-controls="cc-single-source-list"
          >
            <span className="cc-expand__label">
              {singleSourceClaims.length} single-source claim
              {singleSourceClaims.length !== 1 ? "s" : ""}
            </span>
            <span
              className={`cc-expand__caret${singleExpanded ? " cc-expand__caret--open" : ""}`}
              aria-hidden="true"
            >
              &#x25B8;
            </span>
          </button>
          <ul
            id="cc-single-source-list"
            className={`cc-claims__list cc-claims__list--collapsible${singleExpanded ? " cc-claims__list--expanded" : ""}`}
          >
            {singleSourceClaims.map((claim, i) => (
              <ClaimRow key={`single-${claim.text.slice(0, 50)}`} claim={claim} index={i} />
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
