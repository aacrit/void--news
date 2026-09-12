"use client";

/* ==========================================================================
   RevealPanel — Post-game summary panel
   Shows score, insight, share CTA, and countdown to next puzzle.
   ========================================================================== */

import { useState, useEffect } from "react";
import ShareButton from "./ShareButton";
import type { FrameChallenge } from "../data";

interface RevealPanelProps {
  challenge: FrameChallenge;
  /** Player's final ordering (headline ids, left to right) */
  playerOrder: (string | null)[];
  /** Number of attempts used */
  attemptsUsed: number;
  /** Whether the player got it correct */
  isCorrect: boolean;
  /** How many slots matched the correct order */
  correctCount: number;
}

/** Calculate time until next midnight UTC */
function getCountdownToMidnightUTC(): string {
  const now = new Date();
  const nextMidnight = new Date(now);
  nextMidnight.setUTCDate(nextMidnight.getUTCDate() + 1);
  nextMidnight.setUTCHours(0, 0, 0, 0);
  const diff = nextMidnight.getTime() - now.getTime();
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  return `${hours}h ${minutes}m`;
}

export default function RevealPanel({
  challenge,
  playerOrder,
  attemptsUsed,
  isCorrect,
  correctCount,
}: RevealPanelProps) {
  const total = challenge.correct_order.length;
  const [countdown, setCountdown] = useState(getCountdownToMidnightUTC());

  // Update countdown every minute
  useEffect(() => {
    const interval = setInterval(() => {
      setCountdown(getCountdownToMidnightUTC());
    }, 60_000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="frame-reveal" role="region" aria-label="Game results">
      {/* Result header */}
      <div className="frame-reveal__header">
        <h2 className="frame-reveal__title">
          {isCorrect ? "Perfect frame detection." : "Frame exposed."}
        </h2>
        <p className="frame-reveal__score">
          You placed {correctCount} of {total} correctly.
          {attemptsUsed > 1 && (
            <span className="frame-reveal__attempts">
              {" "}&middot; {attemptsUsed} attempt{attemptsUsed !== 1 ? "s" : ""}
            </span>
          )}
        </p>
      </div>

      {/* Organic divider */}
      <svg
        className="frame-reveal__divider"
        viewBox="0 0 400 4"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <path d="M0,2 C40,0.5 80,3.5 120,2 C160,0.5 200,3 240,2 C280,1 320,3.5 360,2 C380,0.5 400,2 400,2" />
      </svg>

      {/* Insight */}
      <p className="frame-reveal__insight">
        {isCorrect
          ? "Same event, four frames. The ordering reveals editorial distance \u2014 how far language travels from the facts."
          : "The language of a headline shapes the story before you read a single paragraph. Framing is the first edit."}
      </p>

      {/* Share + countdown */}
      <div className="frame-reveal__actions">
        <ShareButton
          challengeId={challenge.id}
          playerOrder={playerOrder}
          correctOrder={challenge.correct_order}
          attemptsUsed={attemptsUsed}
          headlines={challenge.headlines}
        />
        <p className="frame-reveal__next">
          Next frame in {countdown}
        </p>
      </div>
    </div>
  );
}
