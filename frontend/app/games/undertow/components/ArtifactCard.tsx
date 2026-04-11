"use client";

import { useRef, useCallback, useState, useEffect } from "react";
import type { Artifact } from "../data";
import RevealCommentary from "./RevealCommentary";

/* ==========================================================================
   ArtifactCard — Cultural artifact display card

   The artifact text is the hero. Playfair Display, large, generous
   white space. The card should feel like holding a document — not a
   game tile.

   States:
     Default:   dark card, Playfair text, category provenance label
     Selected:  amber border (mobile tap-to-select)
     Assigned:  amber top accent bar (slot selected)
     Wrong:     shake animation (300ms horizontal keyframe)
     Correct:   subtle warm glow at base (not too revealing)
     Revealed:  highlighted words stagger in, commentary fades in below

   Desktop: draggable onto AxisBar drop zones.
   Mobile: slot assignment buttons (1st 2nd 3rd 4th) below text.
   ========================================================================== */

interface ArtifactCardProps {
  artifact: Artifact;
  roman: string;
  /** Current assigned slot (0-3, or null if unassigned) */
  position: number | null;
  /** Whether the game has been revealed */
  revealed: boolean;
  /** Index in the reveal sequence (for stagger timing) */
  revealIndex: number;
  /** Callback when card is tapped (mobile: select for assignment) */
  onSelect: () => void;
  /** Callback to assign this card to a slot */
  onSlotAssign: (artifactId: string, slot: number) => void;
  /** Whether this card is currently selected (mobile flow) */
  selected: boolean;
  /** Whether this card was in the wrong slot on last attempt */
  wasWrong?: boolean;
  /** Whether this card is in the correct position (subtle hint) */
  isCorrectPosition?: boolean;
  /** Axis pole labels for slot buttons */
  leftPole: string;
  rightPole: string;
}

const SLOT_LABELS = ["1st", "2nd", "3rd", "4th"];

export default function ArtifactCard({
  artifact,
  roman,
  position,
  revealed,
  revealIndex,
  onSelect,
  onSlotAssign,
  selected,
  wasWrong = false,
  isCorrectPosition = false,
  leftPole,
  rightPole,
}: ArtifactCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const revealDelay = revealIndex * 120;
  const commentaryDelay = revealIndex * 800 + 400;
  const [highlightsVisible, setHighlightsVisible] = useState(false);

  // Trigger word highlights after reveal animation settles
  useEffect(() => {
    if (!revealed) return;
    const timer = setTimeout(
      () => setHighlightsVisible(true),
      revealDelay + 500
    );
    return () => clearTimeout(timer);
  }, [revealed, revealDelay]);

  const handleDragStart = useCallback(
    (e: React.DragEvent) => {
      if (revealed) return;
      e.dataTransfer.setData("text/plain", artifact.id);
      e.dataTransfer.effectAllowed = "move";
      if (cardRef.current) {
        cardRef.current.classList.add("ut-card--dragging");
      }
    },
    [artifact.id, revealed]
  );

  const handleDragEnd = useCallback(() => {
    if (cardRef.current) {
      cardRef.current.classList.remove("ut-card--dragging");
    }
  }, []);

  const handleSlotClick = useCallback(
    (slot: number) => {
      if (revealed) return;
      onSlotAssign(artifact.id, slot);
    },
    [artifact.id, revealed, onSlotAssign]
  );

  /** Render artifact text with highlighted words during reveal */
  function renderText(text: string, highlights: string[]) {
    if (!revealed || !highlightsVisible || highlights.length === 0) {
      return <span>{text}</span>;
    }

    // Build regex from highlight words (sorted longest first for greedy match)
    const sorted = [...highlights].sort((a, b) => b.length - a.length);
    const escaped = sorted.map((w) =>
      w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    );
    const regex = new RegExp(`(${escaped.join("|")})`, "gi");
    const parts = text.split(regex);

    // Track which highlight we've seen for stagger
    const highlightSet = new Set(highlights.map((h) => h.toLowerCase()));
    let highlightIndex = 0;

    return (
      <>
        {parts.map((part, i) => {
          if (highlightSet.has(part.toLowerCase())) {
            const delay = highlightIndex * 50;
            highlightIndex++;
            return (
              <mark
                key={i}
                className="ut-card__highlight"
                style={
                  {
                    "--hl-delay": `${delay}ms`,
                  } as React.CSSProperties
                }
              >
                {part}
              </mark>
            );
          }
          return <span key={i}>{part}</span>;
        })}
      </>
    );
  }

  const isAssigned = position !== null;

  return (
    <div
      ref={cardRef}
      className={[
        "ut-card",
        selected ? "ut-card--selected" : "",
        isAssigned ? "ut-card--assigned" : "",
        revealed ? "ut-card--revealed" : "",
        wasWrong && !revealed ? "ut-card--wrong" : "",
        isCorrectPosition && !revealed ? "ut-card--correct-hint" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      style={
        {
          "--reveal-delay": `${revealDelay}ms`,
          "--commentary-delay": `${commentaryDelay}ms`,
        } as React.CSSProperties
      }
      draggable={!revealed}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onClick={!revealed ? onSelect : undefined}
      role="listitem"
      aria-label={`Artifact ${roman}: ${artifact.text}`}
      tabIndex={0}
    >
      {/* Card header: roman numeral + category */}
      <div className="ut-card__header">
        <span className="ut-card__roman">ARTIFACT &middot; {roman}</span>
        <span className="ut-card__category">[{artifact.category}]</span>
      </div>

      {/* Artifact text — the hero */}
      <blockquote className="ut-card__text">
        <p>
          &ldquo;{renderText(artifact.text, artifact.highlighted_words)}&rdquo;
        </p>
      </blockquote>

      {/* Reveal: commentary appears below */}
      {revealed && (
        <RevealCommentary
          text={artifact.reveal.text}
          delay={commentaryDelay}
        />
      )}

      {/* Mobile: slot assignment buttons */}
      {!revealed && (
        <div
          className="ut-card__slots"
          role="group"
          aria-label="Assign position on axis"
        >
          <span className="ut-card__slots-pole" aria-hidden="true">
            {leftPole}
          </span>
          {SLOT_LABELS.map((label, i) => (
            <button
              key={label}
              type="button"
              className={`ut-card__slot-btn${position === i ? " ut-card__slot-btn--active" : ""}`}
              onClick={(e) => {
                e.stopPropagation();
                handleSlotClick(i);
              }}
              aria-label={`Assign to position ${label}`}
              aria-pressed={position === i}
            >
              {label}
            </button>
          ))}
          <span className="ut-card__slots-pole" aria-hidden="true">
            {rightPole}
          </span>
        </div>
      )}
    </div>
  );
}
