"use client";

import { useCallback, useState } from "react";

/* ==========================================================================
   AxisBar — Horizontal spectrum ordering track

   Desktop: 4 drop zones between the two axis poles for drag-and-drop.
   Mobile: hidden (mobile uses slot buttons on each card instead).

   Minimal, typographic. Two words at each end, a long em-dash line
   between them. Not colorful. Just the poles.
   ========================================================================== */

interface AxisBarProps {
  /** Which slots have been filled, by artifact id */
  slots: (string | null)[];
  /** Map artifact id to its display text (for preview labels) */
  artifactMap: Map<string, string>;
  /** Left pole label */
  leftPole: string;
  /** Right pole label */
  rightPole: string;
  /** Called when an artifact is dropped into a slot */
  onDrop: (artifactId: string, slotIndex: number) => void;
}

export default function AxisBar({
  slots,
  artifactMap,
  leftPole,
  rightPole,
  onDrop,
}: AxisBarProps) {
  const [dragOverSlot, setDragOverSlot] = useState<number | null>(null);

  const handleDragOver = useCallback(
    (e: React.DragEvent, slotIndex: number) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      setDragOverSlot(slotIndex);
    },
    []
  );

  const handleDragLeave = useCallback(() => {
    setDragOverSlot(null);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent, slotIndex: number) => {
      e.preventDefault();
      const artifactId = e.dataTransfer.getData("text/plain");
      if (artifactId) {
        onDrop(artifactId, slotIndex);
      }
      setDragOverSlot(null);
    },
    [onDrop]
  );

  /** Truncate text for slot preview */
  function truncate(text: string, max: number) {
    if (text.length <= max) return text;
    return text.slice(0, max).trim() + "\u2026";
  }

  const POSITION_LABELS = ["1st", "2nd", "3rd", "4th"];

  return (
    <div
      className="ut-axis"
      role="list"
      aria-label="Axis ordering bar"
    >
      {/* Axis line with pole labels */}
      <div className="ut-axis__poles" aria-hidden="true">
        <span className="ut-axis__pole ut-axis__pole--left">
          &larr; {leftPole}
        </span>
        <span className="ut-axis__pole ut-axis__pole--right">
          {rightPole} &rarr;
        </span>
      </div>

      {/* Drop zones */}
      <div className="ut-axis__zones">
        {POSITION_LABELS.map((label, i) => {
          const filled = slots[i];
          const text = filled ? artifactMap.get(filled) : null;
          const isOver = dragOverSlot === i;

          return (
            <div
              key={label}
              className={[
                "ut-axis__zone",
                filled ? "ut-axis__zone--filled" : "",
                isOver ? "ut-axis__zone--over" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              onDragOver={(e) => handleDragOver(e, i)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, i)}
              role="listitem"
              aria-label={`Position ${label}${text ? `: ${text}` : ""}`}
            >
              <span className="ut-axis__zone-label">{label}</span>
              {text && (
                <span className="ut-axis__zone-preview">
                  {truncate(text, 35)}
                </span>
              )}
              {!filled && (
                <span className="ut-axis__zone-placeholder">Drop here</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
