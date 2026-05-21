"use client";

import type { Perspective } from "../types";
import PrimarySourceBlock from "./PrimarySourceBlock";
import OmissionsPanel from "./OmissionsPanel";

/* ===========================================================================
   PerspectiveView — Single perspective narrative panel
   Narrative text (Inter 400, justified, 1.7 line-height), primary sources,
   key narratives & omissions.
   =========================================================================== */

interface PerspectiveViewProps {
  perspective: Perspective;
}

export default function PerspectiveView({ perspective }: PerspectiveViewProps) {
  return (
    <div
      className="hist-persp-view"
      id={`perspective-panel-${perspective.id}`}
      role="tabpanel"
      aria-labelledby={`perspective-tab-${perspective.id}`}
    >
      {/* Narrative */}
      <div className="hist-persp-narrative">
        {perspective.narrative.split("\n").map((para, i) => (
          <p key={i}>{para}</p>
        ))}
      </div>

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
