"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
import Link from "next/link";
import { DAILY_UNDERTOW } from "./data";
import type { Artifact } from "./data";
import ArtifactCard from "./components/ArtifactCard";
import AxisBar from "./components/AxisBar";
import ShareButton from "./components/ShareButton";

/* ==========================================================================
   UndertowGame — void --undertow: Daily Cultural Subtext Puzzle

   Four cultural artifacts. One axis (e.g. CONTROL <-> FREEDOM).
   Player orders the artifacts along the axis. Three attempts.
   Cinematic reveal: highlighted words + Orwellian commentary.

   States: playing -> feedback -> reveal
   Desktop: drag cards onto axis bar drop zones.
   Mobile: tap a card to select, then tap a position slot to assign.
   ========================================================================== */

const MAX_ATTEMPTS = 3;

/** Roman numeral labels */
const ROMAN = ["I", "II", "III", "IV"];

type Phase = "playing" | "feedback" | "reveal";

export default function UndertowGame() {
  const challenge = DAILY_UNDERTOW;
  const [phase, setPhase] = useState<Phase>("playing");
  const [attempt, setAttempt] = useState(1);
  const [feedbackMsg, setFeedbackMsg] = useState("");

  // Slots: 4 positions (left pole -> right pole), each holds an artifact id or null
  const [slots, setSlots] = useState<(string | null)[]>([
    null,
    null,
    null,
    null,
  ]);

  // Mobile: currently selected card for tap-to-assign
  const [selectedCard, setSelectedCard] = useState<string | null>(null);

  // Shuffled artifact order for display (randomized on mount)
  const [displayOrder, setDisplayOrder] = useState<Artifact[]>([]);
  useEffect(() => {
    const shuffled = [...challenge.artifacts].sort(() => Math.random() - 0.5);
    setDisplayOrder(shuffled);
  }, [challenge.artifacts]);

  // Which cards were in wrong positions on last attempt (for shake)
  const [wrongIds, setWrongIds] = useState<Set<string>>(new Set());

  // Which cards are in correct positions (subtle glow hint)
  const [correctPositionIds, setCorrectPositionIds] = useState<Set<string>>(
    new Set()
  );

  // Map artifact id -> assigned slot
  const assignmentMap = useMemo(() => {
    const m = new Map<string, number>();
    slots.forEach((id, i) => {
      if (id) m.set(id, i);
    });
    return m;
  }, [slots]);

  /** Assign an artifact to a spectrum slot */
  const assignToSlot = useCallback(
    (artifactId: string, slotIndex: number) => {
      if (phase === "reveal") return;

      setSlots((prev) => {
        const next = [...prev];

        // If this artifact was already in another slot, remove it
        const oldSlot = next.indexOf(artifactId);
        if (oldSlot !== -1) {
          next[oldSlot] = null;
        }

        // If this slot already has an artifact, swap
        const displaced = next[slotIndex];
        if (displaced && oldSlot !== -1) {
          next[oldSlot] = displaced;
        }

        next[slotIndex] = artifactId;
        return next;
      });

      // Clear selection after assignment (mobile flow)
      setSelectedCard(null);

      // Clear feedback state when making new assignments
      if (phase === "feedback") {
        setPhase("playing");
        setWrongIds(new Set());
        setCorrectPositionIds(new Set());
        setFeedbackMsg("");
      }
    },
    [phase]
  );

  /** Handle axis bar drop (desktop) */
  const handleAxisDrop = useCallback(
    (artifactId: string, slotIndex: number) => {
      assignToSlot(artifactId, slotIndex);
    },
    [assignToSlot]
  );

  /** Handle card selection (mobile: tap to select) */
  const handleCardSelect = useCallback(
    (artifactId: string) => {
      if (phase === "reveal") return;
      setSelectedCard((prev) => (prev === artifactId ? null : artifactId));
    },
    [phase]
  );

  /** Handle position slot tap on card (mobile: assign selected to slot) */
  const handleSlotAssign = useCallback(
    (artifactId: string, slot: number) => {
      assignToSlot(artifactId, slot);
    },
    [assignToSlot]
  );

  /** Submit current ordering */
  const handleSubmit = useCallback(() => {
    if (slots.some((s) => s === null)) return;

    const isCorrect = slots.every(
      (id, i) => id === challenge.correct_order[i]
    );

    if (isCorrect) {
      setPhase("reveal");
      return;
    }

    // Last attempt used -> reveal
    if (attempt >= MAX_ATTEMPTS) {
      setPhase("reveal");
      return;
    }

    // Count correct positions
    const correctIds = new Set<string>();
    const wrong = new Set<string>();
    slots.forEach((id, i) => {
      if (id && id === challenge.correct_order[i]) {
        correctIds.add(id);
      } else if (id) {
        wrong.add(id);
      }
    });

    setCorrectPositionIds(correctIds);
    setWrongIds(wrong);
    setFeedbackMsg("Not quite.");
    setPhase("feedback");
    setAttempt((a) => a + 1);

    // Clear shake after animation
    setTimeout(() => setWrongIds(new Set()), 600);
  }, [slots, challenge.correct_order, attempt]);

  // Score calculation
  const correctCount = useMemo(() => {
    return slots.filter((id, i) => id === challenge.correct_order[i]).length;
  }, [slots, challenge.correct_order]);

  const allFilled = slots.every((s) => s !== null);
  const isPlayerCorrect = phase === "reveal" && correctCount === 4;

  // Format date
  const dateStr = new Date(challenge.date + "T00:00:00").toLocaleDateString(
    "en-US",
    { month: "long", day: "numeric", year: "numeric" }
  );

  return (
    <div className="undertow-page">
      {/* Vignette overlay */}
      <div className="undertow-page__vignette" aria-hidden="true" />
      {/* Film grain overlay */}
      <div className="undertow-page__grain" aria-hidden="true" />

      {/* Navigation back */}
      <nav className="undertow-page__nav" aria-label="Breadcrumb">
        <Link href="/games" className="undertow-page__back">
          <span aria-hidden="true">&larr;</span> void --games
        </Link>
      </nav>

      {/* Header */}
      <header className="undertow-page__header">
        <h1 className="undertow-page__title">UNDERTOW</h1>
        <p className="undertow-page__meta">
          #{challenge.id} &middot; {dateStr}
        </p>
      </header>

      {/* Axis announcement */}
      <div className="undertow-page__axis" role="note">
        <p className="undertow-page__axis-label">TODAY&apos;S AXIS</p>
        <div className="undertow-page__axis-poles">
          <span className="undertow-page__pole undertow-page__pole--left">
            {challenge.axis.left_pole}
          </span>
          <span className="undertow-page__axis-line" aria-hidden="true">
            &larr; &mdash;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash;&mdash; &rarr;
          </span>
          <span className="undertow-page__pole undertow-page__pole--right">
            {challenge.axis.right_pole}
          </span>
        </div>
        <p className="undertow-page__axis-desc">
          {challenge.axis.description}
        </p>
      </div>

      {/* Attempt counter */}
      {phase !== "reveal" && (
        <div
          className="undertow-page__attempt"
          aria-live="polite"
          aria-label={`Attempt ${attempt} of ${MAX_ATTEMPTS}`}
        >
          <span className="undertow-page__attempt-label">
            ATTEMPT {attempt} OF {MAX_ATTEMPTS}
          </span>
          <div className="undertow-page__attempt-dots">
            {Array.from({ length: MAX_ATTEMPTS }).map((_, i) => (
              <span
                key={i}
                className={`undertow-page__attempt-dot${i < MAX_ATTEMPTS - attempt + 1 ? " undertow-page__attempt-dot--active" : ""}`}
                aria-hidden="true"
              />
            ))}
          </div>
        </div>
      )}

      {/* Feedback message */}
      {feedbackMsg && phase === "feedback" && (
        <div
          className="undertow-page__feedback"
          role="alert"
          aria-live="assertive"
        >
          {feedbackMsg}
        </div>
      )}

      {/* Axis bar (desktop drag-drop) — above cards */}
      {phase !== "reveal" && (
        <AxisBar
          slots={slots}
          artifactMap={
            new Map(challenge.artifacts.map((a) => [a.id, a.text]))
          }
          leftPole={challenge.axis.left_pole}
          rightPole={challenge.axis.right_pole}
          onDrop={handleAxisDrop}
        />
      )}

      {/* Artifact cards */}
      <div
        className={`undertow-page__cards${phase === "reveal" ? " undertow-page__cards--revealed" : ""}`}
        role="list"
        aria-label="Artifacts to order"
      >
        {(phase === "reveal"
          ? challenge.correct_order.map(
              (id) => challenge.artifacts.find((a) => a.id === id)!
            )
          : displayOrder
        ).map((artifact, i) => (
          <ArtifactCard
            key={artifact.id}
            artifact={artifact}
            roman={
              phase === "reveal"
                ? ROMAN[i]
                : ROMAN[displayOrder.indexOf(artifact)]
            }
            position={assignmentMap.get(artifact.id) ?? null}
            revealed={phase === "reveal"}
            revealIndex={i}
            onSelect={() => handleCardSelect(artifact.id)}
            onSlotAssign={handleSlotAssign}
            selected={selectedCard === artifact.id}
            wasWrong={wrongIds.has(artifact.id)}
            isCorrectPosition={correctPositionIds.has(artifact.id)}
            leftPole={challenge.axis.left_pole}
            rightPole={challenge.axis.right_pole}
          />
        ))}
      </div>

      {/* Submit button */}
      {phase !== "reveal" && (
        <div className="undertow-page__submit-row">
          <button
            type="button"
            className={`undertow-page__submit${allFilled ? " undertow-page__submit--ready" : ""}`}
            onClick={handleSubmit}
            disabled={!allFilled}
            aria-label="Submit your ordering"
          >
            TRANSMIT RANKING
          </button>
        </div>
      )}

      {/* Reveal summary */}
      {phase === "reveal" && (
        <div
          className="undertow-page__summary"
          role="region"
          aria-label="Game results"
        >
          {/* Organic divider */}
          <svg
            className="undertow-page__divider"
            viewBox="0 0 400 4"
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <path d="M0,2 C40,0.5 80,3.5 120,2 C160,0.5 200,3 240,2 C280,1 320,3.5 360,2 C380,0.5 400,2 400,2" />
          </svg>

          <p className="undertow-page__result">
            {isPlayerCorrect
              ? "Perfect read."
              : `You placed ${correctCount} of 4 correctly.`}
            {attempt > 1 && (
              <span className="undertow-page__result-attempts">
                {" "}
                &middot; {attempt} attempt{attempt !== 1 ? "s" : ""}
              </span>
            )}
          </p>

          <ShareButton
            challengeId={challenge.id}
            playerOrder={slots}
            correctOrder={challenge.correct_order}
            attemptsUsed={attempt}
          />

          {challenge.tomorrow_axis && (
            <p className="undertow-page__tomorrow">
              Tomorrow&apos;s axis: {challenge.tomorrow_axis}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
