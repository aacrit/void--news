"use client";

import { useState } from "react";
import type { Perspective } from "../types";
import PrimarySourceBlock from "./PrimarySourceBlock";
import OmissionsPanel from "./OmissionsPanel";

/* ===========================================================================
   PerspectiveView — Single perspective narrative panel
   Lead argument up top, then the full account behind a toggle (keeps the
   panel tight), primary sources, and the emphasized / omitted / disputed
   ledger. Inter 400, justified, 1.7 line-height for the body.
   =========================================================================== */

interface PerspectiveViewProps {
  perspective: Perspective;
}

export default function PerspectiveView({ perspective }: PerspectiveViewProps) {
  const [showFull, setShowFull] = useState(false);

  const paragraphs = perspective.narrative.split("\n").filter(Boolean);
  const lead = paragraphs.slice(0, 1);
  const rest = paragraphs.slice(1);
  const leadArgument = perspective.keyNarratives[0];

  return (
    <div
      className="hist-persp-view"
      id={`perspective-panel-${perspective.id}`}
      role="tabpanel"
      aria-labelledby={`perspective-tab-${perspective.id}`}
    >
      {/* Lead argument — the one-line stance, always visible */}
      {leadArgument && (
        <p
          className="hist-persp-lead"
          style={{ borderColor: `var(--hist-persp-${perspective.color})` }}
        >
          {leadArgument}
        </p>
      )}

      {/* Narrative — first paragraph visible, full account behind toggle */}
      <div className="hist-persp-narrative">
        {lead.map((para, i) => (
          <p key={i}>{para}</p>
        ))}
        {rest.length > 0 && showFull && rest.map((para, i) => (
          <p key={i + 1}>{para}</p>
        ))}
      </div>

      {rest.length > 0 && (
        <button
          type="button"
          className="hist-persp-more"
          onClick={() => setShowFull((v) => !v)}
          aria-expanded={showFull}
        >
          <span className="hist-persp-more__arrow" aria-hidden="true">
            {showFull ? "▴" : "▾"}
          </span>
          {showFull ? "Close the account" : "Read the full account"}
        </button>
      )}

      {/* Primary Sources */}
      {perspective.primarySources.length > 0 && (
        <section aria-label="Primary sources">
          <h4 className="hist-persp-section-heading">Primary Sources</h4>
          {perspective.primarySources.map((source, i) => (
            <PrimarySourceBlock key={i} source={source} />
          ))}
        </section>
      )}

      {/* Key Narratives, Omissions, Disputed */}
      <OmissionsPanel
        keyNarratives={perspective.keyNarratives}
        omissions={perspective.omissions}
        disputed={perspective.disputed}
        color={perspective.color}
      />
    </div>
  );
}
