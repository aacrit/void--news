"use client";

import { useRef, useCallback, useState, useEffect } from "react";
import type { Artifact } from "../data";
import { CATEGORY_COLORS } from "../data";
import type { ArtifactCategory } from "../data";
import RevealCommentary from "./RevealCommentary";

/* ==========================================================================
   ArtifactCard — Physical paper document on a dark surface

   The artifact text is the hero. Playfair Display, large, generous
   white space. Each card has a deterministic tilt, paper texture
   overlay, and corner fold effect.

   States:
     Default:   dark card, Playfair text, category label, slight tilt
     Assigned:  amber border glow (slot selected)
     Dragging:  lifted, rotated, dramatic shadow
     Wrong:     shake animation (400ms)
     Correct:   subtle warm glow at base
     Revealed:  highlighted words stagger in, commentary fades in below
     Confidence: amber dot top-right; CALLED IT / MISJUDGED on reveal

   Desktop: draggable onto AxisBar drop zones.
   Mobile: slot assignment buttons (1st 2nd 3rd 4th) below text.
   ========================================================================== */

interface ArtifactCardProps {
  artifact: Artifact;
  roman: string;
  /** Position in the display list (for deterministic tilt) */
  index: number;
  /** Current assigned slot (0-3, or null if unassigned) */
  position: number | null;
  /** Whether the game has been revealed */
  revealed: boolean;
  /** Index in the reveal sequence (for stagger timing) */
  revealIndex: number;
  /** Callback to assign this card to a slot */
  onSlotAssign: (artifactId: string, slot: number) => void;
  /** Whether this card was in the wrong slot on last attempt */
  wasWrong?: boolean;
  /** Whether this card is in the correct position (subtle hint) */
  isCorrectPosition?: boolean;
  /** Axis pole labels for slot buttons */
  leftPole: string;
  rightPole: string;
  /** Whether this card is the confidence pick */
  isConfidencePick?: boolean;
  /** Callback to toggle confidence pick on this card */
  onConfidencePick?: () => void;
  /** Confidence result for reveal: 'correct', 'wrong', or null */
  confidenceResult?: "correct" | "wrong" | null;
}

const SLOT_LABELS = ["1st", "2nd", "3rd", "4th"];

/** Deterministic tilts per card — physical document scatter */
const TILTS = [-1.2, 0.8, -0.5, 1.1];

export default function ArtifactCard({
  artifact,
  roman,
  index,
  position,
  revealed,
  revealIndex,
  onSlotAssign,
  wasWrong = false,
  isCorrectPosition = false,
  leftPole,
  rightPole,
  isConfidencePick = false,
  onConfidencePick,
  confidenceResult = null,
}: ArtifactCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const revealDelay = revealIndex * 500; // sequential: 500ms between each card
  const commentaryDelay = revealDelay + 800;
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
        cardRef.current.classList.add("undertow-card--dragging");
      }
    },
    [artifact.id, revealed]
  );

  const handleDragEnd = useCallback(() => {
    if (cardRef.current) {
      cardRef.current.classList.remove("undertow-card--dragging");
    }
  }, []);

  const handleSlotClick = useCallback(
    (slot: number) => {
      if (revealed) return;
      onSlotAssign(artifact.id, slot);
    },
    [artifact.id, revealed, onSlotAssign]
  );

  /** Handle card body click for confidence pick (not slot buttons).
   *  Triggers the ut-confidence-tap spring animation via CSS class toggle. */
  const handleCardClick = useCallback(() => {
    if (revealed) return;
    // Trigger spring tap animation
    if (cardRef.current) {
      cardRef.current.classList.remove("undertow-card--confidence-tap");
      // Force reflow so re-adding the class restarts the animation
      void cardRef.current.offsetWidth;
      cardRef.current.classList.add("undertow-card--confidence-tap");
    }
    onConfidencePick?.();
  }, [revealed, onConfidencePick]);

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

    const highlightSet = new Set(highlights.map((h) => h.toLowerCase()));
    let highlightIndex = 0;

    return (
      <>
        {parts.map((part, i) => {
          if (highlightSet.has(part.toLowerCase())) {
            const delay = highlightIndex * 80;
            highlightIndex++;
            return (
              <mark
                key={i}
                className="undertow-highlight undertow-highlight--active"
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
  const categoryColor = CATEGORY_COLORS[artifact.category as ArtifactCategory];

  return (
    <div
      ref={cardRef}
      className={[
        "undertow-card",
        isAssigned ? "undertow-card--assigned" : "",
        revealed ? "undertow-card--revealed" : "",
        wasWrong && !revealed ? "undertow-card--wrong" : "",
        isCorrectPosition && !revealed ? "undertow-card--correct-hint" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      style={
        {
          "--card-tilt": TILTS[index % TILTS.length],
          "--reveal-delay": `${revealDelay}ms`,
          "--commentary-delay": `${commentaryDelay}ms`,
          "--cat-color": categoryColor,
        } as React.CSSProperties
      }
      draggable={!revealed}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onClick={handleCardClick}
      role="listitem"
      aria-label={`Artifact ${roman}: ${artifact.text}${isConfidencePick ? " (your confidence pick)" : ""}`}
      tabIndex={0}
    >
      {/* Confidence indicator — top-right corner */}
      {isConfidencePick && !revealed && (
        <div className="undertow-card__confidence" aria-label="Your confidence pick">&middot;</div>
      )}
      {revealed && confidenceResult === "correct" && (
        <div className="undertow-card__confidence undertow-card__confidence--correct">CALLED IT</div>
      )}
      {revealed && confidenceResult === "wrong" && (
        <div className="undertow-card__confidence undertow-card__confidence--wrong">MISJUDGED</div>
      )}

      {/* Card header: category + roman numeral */}
      <div className="undertow-card__header">
        <span
          className="undertow-card__category"
          style={{ color: categoryColor }}
        >
          [{artifact.category}]
        </span>
        <span className="undertow-card__roman">
          &middot; ARTIFACT {roman}
        </span>
      </div>

      {/* Artifact text — the hero */}
      <blockquote className="undertow-card__text">
        <p>
          &ldquo;{renderText(artifact.text, artifact.highlighted_words)}&rdquo;
        </p>
      </blockquote>

      {/* Reveal: commentary appears below */}
      {revealed && (
        <RevealCommentary
          text={artifact.reveal}
          delay={commentaryDelay}
        />
      )}

      {/* Mobile: slot assignment buttons */}
      {!revealed && (
        <div
          className="undertow-card__slots"
          role="group"
          aria-label="Assign position on axis"
        >
          <span className="undertow-card__slots-pole" aria-hidden="true">
            {leftPole}
          </span>
          {SLOT_LABELS.map((label, i) => (
            <button
              key={label}
              type="button"
              className={`undertow-card__slot-btn${position === i ? " undertow-card__slot-btn--active" : ""}`}
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
          <span className="undertow-card__slots-pole" aria-hidden="true">
            {rightPole}
          </span>
        </div>
      )}
    </div>
  );
}
