"use client";

import { useCallback, useRef } from "react";
import type { Perspective } from "../types";

/* ===========================================================================
   PerspectiveSelector — Tab cards for choosing a perspective
   Colored left border, viewpoint name, type badge, temporal/geographic anchor.
   WAI-ARIA Tabs pattern: ArrowLeft/ArrowRight navigation with wrap-around.
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
  const tablistRef = useRef<HTMLDivElement>(null);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      e.preventDefault();
      const currentIdx = perspectives.findIndex((p) => p.id === activeId);
      if (currentIdx === -1) return;
      let nextIdx: number;
      if (e.key === "ArrowRight") {
        nextIdx = (currentIdx + 1) % perspectives.length;
      } else {
        nextIdx = (currentIdx - 1 + perspectives.length) % perspectives.length;
      }
      const nextPerspective = perspectives[nextIdx];
      onSelect(nextPerspective.id);
      /* Move focus to the newly activated tab */
      const nextButton = tablistRef.current?.querySelector<HTMLElement>(
        `#perspective-tab-${nextPerspective.id}`
      );
      nextButton?.focus();
    },
    [perspectives, activeId, onSelect]
  );

  return (
    <div
      ref={tablistRef}
      className="hist-persp-tabs"
      role="tablist"
      aria-label="Perspective viewpoints"
      onKeyDown={handleKeyDown}
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
