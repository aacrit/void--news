"use client";

import { useState, useCallback, useMemo, useEffect, useRef } from "react";
import Link from "next/link";
import { DAILY_UNDERTOW, getAxisImage } from "./data";
import type { Artifact } from "./data";
import ArtifactCard from "./components/ArtifactCard";
import AxisBar from "./components/AxisBar";
import ShareButton from "./components/ShareButton";

/* ==========================================================================
   UndertowGame — void --undertow: Daily Cultural Subtext Puzzle

   Four cultural artifacts. One conceptual axis (e.g. CULT <-> YOGA CLASS).
   Player orders the artifacts along the axis. Three attempts.
   Cinematic reveal: sequential card-by-card highlighted words + Orwellian
   commentary.

   Confidence mechanic: player can optionally tap a card to mark it as their
   "call" — if it lands in the correct position, they get a CALLED IT badge.

   Cinematic layer system (back to front):
     1. Background image — full-viewport, heavily blurred, dark overlay
     2. Parallax layer — shifts +/-15px on mouse move
     3. Grain layer — animated film grain (SVG feTurbulence)
     4. Vignette layer — radial edge darkening
     5. Content layer — cards, axis, UI chrome

   States: playing -> feedback -> reveal
   Desktop: drag cards onto axis bar drop zones.
   Mobile: tap slot buttons (1st 2nd 3rd 4th) on each card.
   ========================================================================== */

const MAX_ATTEMPTS = 3;
const ROMAN = ["I", "II", "III", "IV"];

type Phase = "playing" | "feedback" | "reveal";

/* ---- Personality-driven feedback messages ---- */
const FEEDBACK_MESSAGES = [
  // attempt 1 wrong (attemptsRemaining goes from 3 to 2)
  [
    "Close. {n} of 4 landed.",
    "Interesting read. {n} of 4.",
    "Not quite. {n} placed correctly.",
  ],
  // attempt 2 wrong (1 remaining)
  [
    "Last chance. {n} of 4 right.",
    "One more look. {n} correct.",
    "Trust your instincts. {n} of 4.",
  ],
];

/** Pick a random message from the right attempt bucket, inject correctCount */
function getFeedbackMessage(attemptNumber: number, correctCount: number): string {
  const bucket =
    FEEDBACK_MESSAGES[
      Math.min(attemptNumber - 1, FEEDBACK_MESSAGES.length - 1)
    ];
  const template = bucket[Math.floor(Math.random() * bucket.length)];
  return template.replace("{n}", String(correctCount));
}

export default function UndertowGame() {
  const challenge = DAILY_UNDERTOW;
  const [phase, setPhase] = useState<Phase>("playing");
  const [attempt, setAttempt] = useState(1);
  const [feedbackMsg, setFeedbackMsg] = useState("");
  const [mounted, setMounted] = useState(false);
  const bgRef = useRef<HTMLDivElement>(null);

  // Confidence pick: player marks one card as their call
  const [confidencePick, setConfidencePick] = useState<string | null>(null);

  // Track every submitted ordering (for share text)
  const [attemptHistory, setAttemptHistory] = useState<(string | null)[][]>([]);

  // Axis intro animation: staged entrance
  useEffect(() => {
    // Small delay to ensure DOM is painted before triggering CSS transitions
    const timer = setTimeout(() => setMounted(true), 50);
    return () => clearTimeout(timer);
  }, []);

  // Parallax on mouse move — shifts background layer
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) return;

    const handleMouseMove = (e: MouseEvent) => {
      const x = (e.clientX / window.innerWidth - 0.5) * 30;
      const y = (e.clientY / window.innerHeight - 0.5) * 20;
      bgRef.current?.style.setProperty("--px", `${x}px`);
      bgRef.current?.style.setProperty("--py", `${y}px`);
    };
    window.addEventListener("mousemove", handleMouseMove, { passive: true });
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  // Slots: 4 positions (left pole -> right pole), each holds an artifact id or null
  const [slots, setSlots] = useState<(string | null)[]>([
    null,
    null,
    null,
    null,
  ]);

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

  /** Handle mobile slot button click on a card */
  const handleSlotAssign = useCallback(
    (artifactId: string, slot: number) => {
      assignToSlot(artifactId, slot);
    },
    [assignToSlot]
  );

  /** Submit current ordering */
  const handleSubmit = useCallback(() => {
    if (slots.some((s) => s === null)) return;

    // Record this attempt's ordering
    setAttemptHistory((prev) => [...prev, [...slots]]);

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

    const correctInPosition = slots.filter(
      (id, i) => id === challenge.correct_order[i]
    ).length;

    setCorrectPositionIds(correctIds);
    setWrongIds(wrong);
    setFeedbackMsg(getFeedbackMessage(attempt, correctInPosition));
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

  // Determine confidence pick result for reveal phase
  const confidenceResult = useMemo((): "correct" | "wrong" | null => {
    if (phase !== "reveal" || !confidencePick) return null;
    const assignedSlot = assignmentMap.get(confidencePick);
    const correctSlot = challenge.correct_order.indexOf(confidencePick);
    if (assignedSlot === undefined) return null;
    return assignedSlot === correctSlot ? "correct" : "wrong";
  }, [phase, confidencePick, assignmentMap, challenge.correct_order]);

  // Format date
  const dateStr = new Date(challenge.date + "T00:00:00").toLocaleDateString(
    "en-US",
    { month: "long", day: "numeric", year: "numeric" }
  );

  const attemptsRemaining = MAX_ATTEMPTS - attempt + 1;

  // Resolve background image for this axis
  const axisImage = getAxisImage(challenge.axis.left_pole);

  return (
    <div className={`undertow-page${mounted ? " undertow-page--mounted" : ""}${phase === "reveal" ? " undertow-page--revealed" : ""}`}>
      {/* Layer 1: Background image — heavily blurred, dark overlay */}
      <div className="undertow-page__bg" ref={bgRef} aria-hidden="true">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={axisImage.url}
          alt=""
          className="undertow-page__bg-img"
          loading="eager"
        />
        <div className="undertow-page__bg-overlay" />
      </div>

      {/* Layer 2: Animated film grain */}
      <div className="undertow-page__grain" aria-hidden="true">
        <svg width="0" height="0" aria-hidden="true">
          <filter id="undertow-grain">
            <feTurbulence
              type="fractalNoise"
              baseFrequency="0.65"
              numOctaves="3"
              stitchTiles="stitch"
              result="noise"
            />
            <feColorMatrix
              type="saturate"
              values="0"
              in="noise"
              result="mono"
            />
          </filter>
        </svg>
        <div className="undertow-page__grain-layer" />
      </div>

      {/* Layer 3: Vignette */}
      <div className="undertow-page__vignette" aria-hidden="true" />

      {/* Layer 3.5: Warm tint — Paper Archive signature */}
      <div className="undertow-page__warm-tint" aria-hidden="true" />

      {/* Layer 4: Content */}
      <div className="undertow-page__content">
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

        {/* Axis announcement — dramatic intro */}
        <div
          className={`undertow-axis${mounted ? " undertow-axis--visible" : ""}`}
          role="note"
          aria-label={`Today's axis: ${challenge.axis.left_pole} to ${challenge.axis.right_pole}`}
        >
          <span className="undertow-axis__pole undertow-axis__pole--left">
            {challenge.axis.left_pole}
          </span>
          <span className="undertow-axis__line" aria-hidden="true" />
          <span className="undertow-axis__pole undertow-axis__pole--right">
            {challenge.axis.right_pole}
          </span>
        </div>
        <p className={`undertow-axis__desc${mounted ? " undertow-axis__desc--visible" : ""}`}>
          {challenge.axis.description}
        </p>

        {/* Attempt counter */}
        {phase !== "reveal" && (
          <div
            className="undertow-page__attempt"
            aria-live="polite"
            aria-label={`${attemptsRemaining} attempts remaining`}
          >
            <span className="undertow-page__attempt-label">ATTEMPTS</span>
            <div className="undertow-page__attempt-dots">
              {Array.from({ length: MAX_ATTEMPTS }).map((_, i) => (
                <span
                  key={i}
                  className={`undertow-page__attempt-dot${i < attemptsRemaining ? " undertow-page__attempt-dot--active" : ""}`}
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
          className={`undertow-page__cards${phase === "reveal" ? " undertow-page__cards--revealed" : ""}${mounted ? " undertow-page__cards--entered" : ""}`}
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
              index={i}
              position={assignmentMap.get(artifact.id) ?? null}
              revealed={phase === "reveal"}
              revealIndex={i}
              onSlotAssign={handleSlotAssign}
              wasWrong={wrongIds.has(artifact.id)}
              isCorrectPosition={correctPositionIds.has(artifact.id)}
              leftPole={challenge.axis.left_pole}
              rightPole={challenge.axis.right_pole}
              isConfidencePick={confidencePick === artifact.id}
              onConfidencePick={() =>
                setConfidencePick((prev) =>
                  prev === artifact.id ? null : artifact.id
                )
              }
              confidenceResult={
                phase === "reveal"
                  ? confidencePick === artifact.id
                    ? confidenceResult
                    : null
                  : null
              }
            />
          ))}
        </div>

        {/* Submit button */}
        {phase !== "reveal" && (
          <div className="undertow-page__submit-row">
            <button
              type="button"
              className={`undertow-submit${allFilled ? " undertow-submit--ready" : ""}`}
              onClick={handleSubmit}
              disabled={!allFilled}
              aria-label="Submit your ordering"
            >
              DECODE
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
              axisLabel={`${challenge.axis.left_pole} \u2194 ${challenge.axis.right_pole}`}
              correctOrder={challenge.correct_order}
              attemptHistory={attemptHistory}
              attemptsUsed={attempt}
              confidencePick={confidencePick}
              confidenceResult={confidenceResult}
            />

            <p className="undertow-page__credit" aria-hidden="true">
              {axisImage.credit}
            </p>
          </div>
        )}

        {/* Photo credit (playing phase only — reveal has its own) */}
        {phase !== "reveal" && (
          <p className="undertow-page__credit" aria-hidden="true">
            {axisImage.credit}
          </p>
        )}
      </div>
    </div>
  );
}
