"use client";

import { useState, useCallback } from "react";
import type { Perspective } from "../types";
import PerspectiveSelector from "./PerspectiveSelector";
import PerspectiveView from "./PerspectiveView";

/* ===========================================================================
   PerspectiveExhibit — Tabbed museum vitrine for multiple viewpoints.
   One voice visible at a time. Color-coded chips switch the active account;
   the panel re-mounts on change so the lectern-turn reveal replays.
   Replaces the old stacked-and-pre-expanded witness blocks: 5 essays become
   one panel, the single biggest cut to page scroll.
   =========================================================================== */

interface PerspectiveExhibitProps {
  perspectives: Perspective[];
}

export default function PerspectiveExhibit({ perspectives }: PerspectiveExhibitProps) {
  const [activeId, setActiveId] = useState(perspectives[0]?.id ?? "");
  const onSelect = useCallback((id: string) => setActiveId(id), []);

  if (perspectives.length === 0) return null;

  const active =
    perspectives.find((p) => p.id === activeId) ?? perspectives[0];

  return (
    <div className="hist-exhibit">
      <PerspectiveSelector
        perspectives={perspectives}
        activeId={active.id}
        onSelect={onSelect}
      />
      {/* key forces remount so the entrance animation replays per switch */}
      <PerspectiveView key={active.id} perspective={active} />
    </div>
  );
}
