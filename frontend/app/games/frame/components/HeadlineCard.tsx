"use client";

import { useRef, useCallback } from "react";
import type { FrameHeadline, BiasTrigger } from "../data";
import { leanToColor } from "../data";

/* ==========================================================================
   HeadlineCard — Draggable / click-assignable headline card
   Newspaper clipping aesthetic: warm paper on dark background.

   States:
     Default:  dark card, Playfair headline, SOURCE redacted mask
     Assigned: amber border glow (slot selected)
     Dragging: lifted 8px, slight rotation (CSS .frame-card--dragging)
     Wrong:    desaturation shake (CSS .frame-card--wrong, 400ms)
     Revealed: outlet types in (teletype), score bar animates,
               bias-trigger words get colored underlines
   ========================================================================== */

interface HeadlineCardProps {
  headline: FrameHeadline;
  index: number;
  /** Current assigned slot (0-3, or null if unassigned) */
  assignedSlot: number | null;
  /** Whether the game has been revealed */
  revealed: boolean;
  /** Correct slot index for this headline (used during reveal) */
  correctSlot?: number;
  /** Whether this card was in the wrong slot on last attempt */
  wasWrong?: boolean;
  /** Callback when user starts dragging (desktop) */
  onDragStart?: (headlineId: string) => void;
  /** Callback when user taps a slot label (mobile) */
  onSlotAssign?: (headlineId: string, slot: number) => void;
  /** Animation delay stagger for reveal */
  revealDelay?: number;
}

/** Slot labels for mobile click-to-assign */
const SLOT_LABELS = ["L", "C-L", "C-R", "R"];
const SLOT_ARIA = ["Left", "Center-Left", "Center-Right", "Right"];

export default function HeadlineCard({
  headline,
  index,
  assignedSlot,
  revealed,
  correctSlot,
  wasWrong,
  onDragStart,
  onSlotAssign,
  revealDelay = 0,
}: HeadlineCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);

  const handleDragStart = useCallback(
    (e: React.DragEvent) => {
      if (revealed) return;
      e.dataTransfer.setData("text/plain", headline.id);
      e.dataTransfer.effectAllowed = "move";
      if (cardRef.current) {
        cardRef.current.classList.add("frame-card--dragging");
      }
      onDragStart?.(headline.id);
    },
    [headline.id, revealed, onDragStart]
  );

  const handleDragEnd = useCallback(() => {
    if (cardRef.current) {
      cardRef.current.classList.remove("frame-card--dragging");
    }
  }, []);

  const handleSlotClick = useCallback(
    (slot: number) => {
      if (revealed) return;
      onSlotAssign?.(headline.id, slot);
    },
    [headline.id, revealed, onSlotAssign]
  );

  /** Highlight bias-trigger words in headline text during reveal.
      Each trigger has its own direction (left/right), so underline
      color is per-word, not per-headline. */
  function renderHeadline(text: string, triggers: BiasTrigger[]) {
    if (!revealed || triggers.length === 0) {
      return <span>{text}</span>;
    }

    // Build regex from trigger words (sorted longest first for greedy match)
    const sorted = [...triggers].sort((a, b) => b.word.length - a.word.length);
    const escaped = sorted.map((t) => t.word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    const regex = new RegExp(`(${escaped.join("|")})`, "gi");
    const parts = text.split(regex);

    // Build a lookup: lowercase word -> direction
    const directionMap = new Map<string, "left" | "right">();
    triggers.forEach((t) => directionMap.set(t.word.toLowerCase(), t.direction));

    return (
      <>
        {parts.map((part, i) => {
          const direction = directionMap.get(part.toLowerCase());
          if (direction) {
            const cls = direction === "left"
              ? "frame-card__bias-word frame-card__bias-word--left"
              : "frame-card__bias-word frame-card__bias-word--right";
            return (
              <mark key={i} className={cls}>
                {part}
              </mark>
            );
          }
          return <span key={i}>{part}</span>;
        })}
      </>
    );
  }

  const isAssigned = assignedSlot !== null;
  const isCorrect = revealed && correctSlot !== undefined && assignedSlot === correctSlot;
  const leanColor = leanToColor(headline.lean_label);

  return (
    <div
      ref={cardRef}
      className={[
        "frame-card",
        isAssigned ? "frame-card--assigned" : "",
        revealed ? "frame-card--revealed" : "",
        wasWrong && !revealed ? "frame-card--wrong" : "",
        isCorrect ? "frame-card--correct" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      style={
        {
          "--reveal-delay": `${revealDelay}ms`,
          "--lean-color": revealed ? leanColor : undefined,
        } as React.CSSProperties
      }
      draggable={!revealed}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      role="listitem"
      aria-label={`Headline ${index + 1}: ${headline.text}`}
      tabIndex={0}
    >
      {/* Source redaction bar */}
      <div className="frame-card__source" aria-label={revealed ? headline.outlet : "Source hidden"}>
        {revealed ? (
          <span
            className="frame-card__outlet-reveal"
            style={{ "--reveal-delay": `${revealDelay + 200}ms` } as React.CSSProperties}
          >
            {headline.outlet}
          </span>
        ) : (
          <span className="frame-card__redacted">
            SOURCE <span className="frame-card__block" aria-hidden="true" />
          </span>
        )}
      </div>

      {/* Headline text */}
      <h3 className="frame-card__headline">
        {renderHeadline(headline.text, headline.bias_triggers)}
      </h3>

      {/* Reveal: bias score + lean bar */}
      {revealed && (
        <div
          className="frame-card__score"
          style={{
            color: leanColor,
            "--reveal-delay": `${revealDelay}ms`,
          } as React.CSSProperties}
        >
          <span className="frame-card__score-label">LEAN:</span>{" "}
          <span className="frame-card__score-value">
            {headline.lean_score > 0 ? "+" : ""}
            {headline.lean_score.toFixed(1)}
          </span>{" "}
          <span className="frame-card__score-tag">({headline.lean_label})</span>
          {/* Mini lean bar */}
          <div className="frame-card__lean-bar" aria-hidden="true">
            <div
              className="frame-card__lean-pip"
              style={{
                left: `${((headline.lean_score + 3.5) / 7) * 100}%`,
                backgroundColor: leanColor,
              }}
            />
          </div>
        </div>
      )}

      {/* Mobile: slot assignment buttons */}
      {!revealed && (
        <div className="frame-card__slots" role="group" aria-label="Assign position on spectrum">
          {SLOT_LABELS.map((label, i) => (
            <button
              key={label}
              type="button"
              className={`frame-card__slot-btn${assignedSlot === i ? " frame-card__slot-btn--active" : ""}`}
              onClick={() => handleSlotClick(i)}
              aria-label={`Assign to ${SLOT_ARIA[i]}`}
              aria-pressed={assignedSlot === i}
            >
              {label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
