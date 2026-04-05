"use client";

import type { Perspective } from "../types";

/* ===========================================================================
   PerspectiveSelector — Tab cards for choosing a perspective
   Colored left border, viewpoint name, type badge, temporal/geographic anchor.
   =========================================================================== */

interface PerspectiveSelectorProps {
  perspectives: Perspective[];
  activeId: string;
  onSelect: (id: string) => void;
}

export default function PerspectiveSelector({
  perspectives,
  activeId,
  onSelect,
}: PerspectiveSelectorProps) {
  return (
    <div
      className="hist-persp-tabs"
      role="tablist"
      aria-label="Perspective viewpoints"
    >
      {perspectives.map((p) => {
        const isActive = p.id === activeId;
        return (
          <button
            key={p.id}
            role="tab"
            aria-selected={isActive}
            aria-controls={`perspective-panel-${p.id}`}
            id={`perspective-tab-${p.id}`}
            className={[
              "hist-persp-tab",
              `hist-persp-tab--color-${p.color}`,
              isActive ? "hist-persp-tab--active" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() => onSelect(p.id)}
            tabIndex={isActive ? 0 : -1}
          >
            <span className="hist-persp-tab__name">{p.viewpointName}</span>
            <span className="hist-persp-tab__type">{p.viewpointType}</span>
            <span className="hist-persp-tab__anchor">
              {p.temporalAnchor} &middot; {p.geographicAnchor}
            </span>
          </button>
        );
      })}
    </div>
  );
}
