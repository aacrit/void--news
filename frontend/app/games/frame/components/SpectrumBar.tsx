"use client";

import { useCallback, useRef, useState } from "react";

/* ==========================================================================
   SpectrumBar — Left-to-right ordering track
   Desktop: 4 drop zones along a gradient bar for drag-and-drop.
   Mobile: hidden (mobile uses slot buttons on cards instead).
   ========================================================================== */

interface SpectrumBarProps {
  /** Which slots have been filled, by headline id */
  slots: (string | null)[];
  /** Map headline id to its display text (for labels) */
  headlineMap: Map<string, string>;
  /** Called when a headline is dropped into a slot */
  onDrop: (headlineId: string, slotIndex: number) => void;
  /** Whether the game has been revealed */
  revealed: boolean;
}

const ZONE_LABELS = ["LEFT", "CENTER-LEFT", "CENTER-RIGHT", "RIGHT"];

export default function SpectrumBar({
  slots,
  headlineMap,
  onDrop,
  revealed,
}: SpectrumBarProps) {
  const [dragOverSlot, setDragOverSlot] = useState<number | null>(null);
  const barRef = useRef<HTMLDivElement>(null);

  const handleDragOver = useCallback(
    (e: React.DragEvent, slotIndex: number) => {
      if (revealed) return;
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      setDragOverSlot(slotIndex);
    },
    [revealed]
  );

  const handleDragLeave = useCallback(() => {
    setDragOverSlot(null);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent, slotIndex: number) => {
      if (revealed) return;
      e.preventDefault();
      const headlineId = e.dataTransfer.getData("text/plain");
      if (headlineId) {
        onDrop(headlineId, slotIndex);
      }
      setDragOverSlot(null);
    },
    [revealed, onDrop]
  );

  /** Truncate headline text for slot preview */
  function truncate(text: string, max: number) {
    if (text.length <= max) return text;
    return text.slice(0, max).trim() + "\u2026";
  }

  return (
    <div className="frame-spectrum" ref={barRef} role="list" aria-label="Political spectrum ordering bar">
      {/* Gradient bar background */}
      <div className="frame-spectrum__bar" aria-hidden="true">
        <div className="frame-spectrum__gradient" />
      </div>

      {/* Axis labels */}
      <div className="frame-spectrum__axis" aria-hidden="true">
        <span className="frame-spectrum__axis-label frame-spectrum__axis-label--left">LEFT</span>
        <span className="frame-spectrum__axis-arrow">&larr;</span>
        <span className="frame-spectrum__axis-center">&mdash;</span>
        <span className="frame-spectrum__axis-arrow">&rarr;</span>
        <span className="frame-spectrum__axis-label frame-spectrum__axis-label--right">RIGHT</span>
      </div>

      {/* Drop zones */}
      <div className="frame-spectrum__zones">
        {ZONE_LABELS.map((label, i) => {
          const filled = slots[i];
          const headline = filled ? headlineMap.get(filled) : null;
          const isOver = dragOverSlot === i;

          return (
            <div
              key={label}
              className={[
                "frame-spectrum__zone",
                filled ? "frame-spectrum__zone--filled" : "",
                isOver ? "frame-spectrum__zone--over" : "",
                revealed ? "frame-spectrum__zone--revealed" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              onDragOver={(e) => handleDragOver(e, i)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, i)}
              role="listitem"
              aria-label={`${label} position${headline ? `: ${headline}` : ""}`}
            >
              <span className="frame-spectrum__zone-label">{label}</span>
              {headline && (
                <span className="frame-spectrum__zone-preview">
                  {truncate(headline, 40)}
                </span>
              )}
              {!filled && !revealed && (
                <span className="frame-spectrum__zone-placeholder">
                  Drop here
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
