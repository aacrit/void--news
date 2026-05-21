"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
import Link from "next/link";
import { DAILY_FRAME } from "./data";
import type { FrameHeadline } from "./data";
import HeadlineCard from "./components/HeadlineCard";
import SpectrumBar from "./components/SpectrumBar";
import RevealPanel from "./components/RevealPanel";

/* ==========================================================================
   FrameGame — THE FRAME: Daily Media Literacy Puzzle

   Four headlines about the same event. Player ranks them LEFT to RIGHT on
   the political spectrum. Pure language pattern recognition — no news
   knowledge required. Three attempts. Cinematic reveal shows outlets,
   lean scores, and bias-trigger words.

   Desktop: drag cards onto spectrum bar drop zones.
   Mobile: tap slot buttons (L / C-L / C-R / R) on each card.
   ========================================================================== */

const MAX_ATTEMPTS = 3;

type Phase = "play" | "feedback" | "reveal";

export default function FrameGame() {
  const challenge = DAILY_FRAME;
  const [phase, setPhase] = useState<Phase>("play");
  const [attempt, setAttempt] = useState(1);
  const [wrongIds, setWrongIds] = useState<Set<string>>(new Set());
  const [feedbackMsg, setFeedbackMsg] = useState("");

  // Slots: 4 positions (left to right), each holds a headline id or null
  const [slots, setSlots] = useState<(string | null)[]>([null, null, null, null]);

  // Shuffled headline order for display (randomized on mount)
  const [displayOrder, setDisplayOrder] = useState<FrameHeadline[]>([]);
  useEffect(() => {
    const shuffled = [...challenge.headlines].sort(() => Math.random() - 0.5);
    setDisplayOrder(shuffled);
  }, [challenge.headlines]);

  // Map headline id -> text for spectrum bar preview
  const headlineMap = useMemo(() => {
    const m = new Map<string, string>();
    challenge.headlines.forEach((h) => m.set(h.id, h.text));
    return m;
  }, [challenge.headlines]);

  // Map headline id -> assigned slot
  const assignmentMap = useMemo(() => {
    const m = new Map<string, number>();
    slots.forEach((id, i) => {
      if (id) m.set(id, i);
    });
    return m;
  }, [slots]);

  // Correct slot for each headline
  const correctSlotMap = useMemo(() => {
    const m = new Map<string, number>();
    challenge.correct_order.forEach((id, i) => m.set(id, i));
    return m;
  }, [challenge.correct_order]);

  /** Assign a headline to a spectrum slot */
  const assignToSlot = useCallback(
    (headlineId: string, slotIndex: number) => {
      if (phase === "reveal") return;

      setSlots((prev) => {
        const next = [...prev];

        // If this headline was already in another slot, remove it
        const oldSlot = next.indexOf(headlineId);
        if (oldSlot !== -1) {
          next[oldSlot] = null;
        }

        // If this slot already has a headline, swap
        const displaced = next[slotIndex];
        if (displaced && oldSlot !== -1) {
          next[oldSlot] = displaced;
        }

        next[slotIndex] = headlineId;
        return next;
      });

      // Clear feedback state when making new assignments
      if (phase === "feedback") {
        setPhase("play");
        setWrongIds(new Set());
        setFeedbackMsg("");
      }
    },
    [phase]
  );

  /** Handle spectrum bar drop */
  const handleSpectrumDrop = useCallback(
    (headlineId: string, slotIndex: number) => {
      assignToSlot(headlineId, slotIndex);
    },
    [assignToSlot]
  );

  /** Handle mobile slot button click on a card */
  const handleSlotAssign = useCallback(
    (headlineId: string, slot: number) => {
      assignToSlot(headlineId, slot);
    },
    [assignToSlot]
  );

  /** Submit current ordering */
  const handleSubmit = useCallback(() => {
    // Must fill all slots
    if (slots.some((s) => s === null)) return;

    const isCorrect = slots.every(
      (id, i) => id === challenge.correct_order[i]
    );

    if (isCorrect) {
      setPhase("reveal");
      return;
    }

    // Wrong answer
    if (attempt >= MAX_ATTEMPTS) {
      // Last attempt used, reveal
      setPhase("reveal");
      return;
    }

    // Count how many are in the correct position
    const correctInPosition = slots.filter(
      (id, i) => id === challenge.correct_order[i]
    ).length;

    // Mark wrong positions
    const wrong = new Set<string>();
    slots.forEach((id, i) => {
      if (id && id !== challenge.correct_order[i]) {
        wrong.add(id);
      }
    });
    setWrongIds(wrong);

    setFeedbackMsg(`Not quite. ${correctInPosition} of 4 in position.`);
    setPhase("feedback");
    setAttempt((a) => a + 1);

    // Clear feedback shake after animation
    setTimeout(() => setWrongIds(new Set()), 600);
  }, [slots, challenge.correct_order, attempt]);

  // Count correct in current submission
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

  // Remaining attempts indicator
  const attemptsRemaining = MAX_ATTEMPTS - attempt + 1;

  return (
    <div className="frame-page">
      {/* Film grain overlay */}
      <div className="frame-page__grain" aria-hidden="true" />

      {/* Navigation back */}
      <nav className="frame-page__nav" aria-label="Breadcrumb">
        <Link href="/games" className="frame-page__back">
          <span aria-hidden="true">&larr;</span> void --games
        </Link>
      </nav>

      {/* Header */}
      <header className="frame-page__header">
        <h1 className="frame-page__title">THE FRAME</h1>
        <p className="frame-page__date">
          #{challenge.id} &middot; {dateStr}
        </p>
        <p className="frame-page__tagline">
          everyone reads the story. almost nobody reads the frame.
        </p>
      </header>

      {/* Event context */}
      <div className="frame-page__event" role="note">
        <p className="frame-page__event-text">{challenge.topic}</p>
      </div>

      {/* Attempt counter with dots */}
      {phase !== "reveal" && (
        <div className="frame-page__attempt" aria-live="polite" aria-label={`${attemptsRemaining} attempts remaining`}>
          <span className="frame-page__attempt-label">ATTEMPTS: </span>
          {Array.from({ length: MAX_ATTEMPTS }).map((_, i) => (
            <span
              key={i}
              className={`frame-page__attempt-dot${i < attemptsRemaining ? " frame-page__attempt-dot--active" : ""}`}
              aria-hidden="true"
            />
          ))}
        </div>
      )}

      {/* Feedback message */}
      {feedbackMsg && phase === "feedback" && (
        <div className="frame-page__feedback" role="alert" aria-live="assertive">
          {feedbackMsg}
        </div>
      )}

      {/* Spectrum bar (desktop drag-drop) — above cards for visual flow */}
      {phase !== "reveal" && (
        <SpectrumBar
          slots={slots}
          headlineMap={headlineMap}
          onDrop={handleSpectrumDrop}
          revealed={false}
        />
      )}

      {/* Headline cards */}
      <div
        className={`frame-page__cards${phase === "reveal" ? " frame-page__cards--revealed" : ""}`}
        role="list"
        aria-label="Headlines to order"
      >
        {(phase === "reveal"
          ? challenge.correct_order.map(
              (id) => challenge.headlines.find((h) => h.id === id)!
            )
          : displayOrder
        ).map((headline, i) => (
          <HeadlineCard
            key={headline.id}
            headline={headline}
            index={i}
            assignedSlot={assignmentMap.get(headline.id) ?? null}
            revealed={phase === "reveal"}
            correctSlot={correctSlotMap.get(headline.id)}
            wasWrong={wrongIds.has(headline.id)}
            onSlotAssign={handleSlotAssign}
            revealDelay={phase === "reveal" ? i * 300 : 0}
          />
        ))}
      </div>

      {/* Submit button */}
      {phase !== "reveal" && (
        <div className="frame-page__submit-row">
          <button
            type="button"
            className={`frame-page__submit${allFilled ? " frame-page__submit--ready" : ""}`}
            onClick={handleSubmit}
            disabled={!allFilled}
            aria-label="Submit your ordering"
          >
            TRANSMIT RANKING
          </button>
        </div>
      )}

      {/* Reveal panel */}
      {phase === "reveal" && (
        <RevealPanel
          challenge={challenge}
          playerOrder={slots}
          attemptsUsed={attempt}
          isCorrect={isPlayerCorrect}
          correctCount={correctCount}
        />
      )}
    </div>
  );
}
