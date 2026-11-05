"use client";

import type { PerspectiveColor } from "../types";

/* ===========================================================================
   OmissionsPanel — Emphasized vs Omitted vs Disputed
   Filled circle (emphasized), hollow + strikethrough (omitted),
   half-filled (disputed). Perspective-colored bullets.
   =========================================================================== */

interface OmissionsPanelProps {
  keyNarratives: string[];
  omissions: string[];
  disputed: string[];
  color: PerspectiveColor;
}

export default function OmissionsPanel({
  keyNarratives,
  omissions,
  disputed,
  color,
}: OmissionsPanelProps) {
  const hasContent = keyNarratives.length > 0 || omissions.length > 0 || disputed.length > 0;
  if (!hasContent) return null;

  return (
    <div className="hist-omissions">
      {keyNarratives.length > 0 && (
        <>
          <h4 className="hist-persp-section-heading">Emphasized in this perspective</h4>
          <div className="hist-omissions__list" role="list">
            {keyNarratives.map((item, i) => (
              <div key={i} className="hist-omission-item" role="listitem">
                <span
                  className={`hist-omission-bullet--filled`}
                  style={{ background: `var(--hist-persp-${color})` }}
                  aria-hidden="true"
                />
                <span>{item}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {omissions.length > 0 && (
        <>
          <h4 className="hist-persp-section-heading">Omitted or minimized</h4>
          <div className="hist-omissions__list" role="list">
            {omissions.map((item, i) => (
              <div key={i} className="hist-omission-item" role="listitem">
                <span className="hist-omission-bullet--hollow" aria-hidden="true" />
                <span className="hist-omission-text--omitted">{item}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {disputed.length > 0 && (
        <>
          <h4 className="hist-persp-section-heading">Disputed</h4>
          <div className="hist-omissions__list" role="list">
            {disputed.map((item, i) => (
              <div key={i} className="hist-omission-item" role="listitem">
                <span
                  className="hist-omission-bullet--disputed"
                  style={{
                    background: `linear-gradient(90deg, var(--hist-persp-${color}) 50%, transparent 50%)`,
                    borderColor: `var(--hist-persp-${color})`,
                  }}
                  aria-hidden="true"
                />
                <span className="hist-omission-text--disputed">{item}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
