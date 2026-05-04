"use client";

import { useState, useCallback } from "react";
import type { FrameHeadline } from "../data";

/* ==========================================================================
   ShareButton — Copies emoji grid of game result to clipboard

   Share format (spec):
   void --frame #1
   (player row emojis)
   correct: (correct row emojis)
   3 of 4 · 2 attempts
   void.news/games
   ========================================================================== */

interface ShareButtonProps {
  challengeId: number;
  playerOrder: (string | null)[];
  correctOrder: string[];
  attemptsUsed: number;
  headlines: FrameHeadline[];
}

/** Map lean label to emoji block */
function leanToEmoji(label: string): string {
  if (label.includes("LEFT")) return "\uD83D\uDFE6"; // blue square
  if (label === "CENTER") return "\u2B1C"; // white square
  if (label.includes("RIGHT")) return "\uD83D\uDFE5"; // red square
  return "\u2B1C";
}

export default function ShareButton({
  challengeId,
  playerOrder,
  correctOrder,
  attemptsUsed,
  headlines,
}: ShareButtonProps) {
  const [copied, setCopied] = useState(false);

  const buildShareText = useCallback(() => {
    const headlineMap = new Map(headlines.map((h) => [h.id, h]));

    // Build player emoji row
    const playerEmojis = playerOrder
      .map((id) => {
        if (!id) return "\u2B1B"; // black for empty
        const h = headlineMap.get(id);
        return h ? leanToEmoji(h.lean_label) : "\u2B1C";
      })
      .join("");

    // Build correct emoji row
    const correctEmojis = correctOrder
      .map((id) => {
        const h = headlineMap.get(id);
        return h ? leanToEmoji(h.lean_label) : "\u2B1C";
      })
      .join("");

    const correctCount = playerOrder.filter(
      (id, i) => id === correctOrder[i]
    ).length;

    const lines = [
      `void --frame #${challengeId}`,
      playerEmojis,
      `correct: ${correctEmojis}`,
      `${correctCount} of ${correctOrder.length} \u00B7 ${attemptsUsed} attempt${attemptsUsed !== 1 ? "s" : ""}`,
      "void.news/games",
    ];

    return lines.join("\n");
  }, [challengeId, playerOrder, correctOrder, attemptsUsed, headlines]);

  const handleCopy = useCallback(async () => {
    const text = buildShareText();
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: textarea copy
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [buildShareText]);

  return (
    <button
      type="button"
      className="frame-share"
      onClick={handleCopy}
      aria-label={copied ? "Copied to clipboard" : "Copy result to clipboard"}
    >
      <span className="frame-share__icon" aria-hidden="true">
        {copied ? (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="3 8 6.5 11.5 13 4.5" />
          </svg>
        ) : (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <rect x="5" y="5" width="9" height="9" rx="1.5" />
            <path d="M11 5V3.5A1.5 1.5 0 009.5 2h-7A1.5 1.5 0 001 3.5v7A1.5 1.5 0 002.5 12H5" />
          </svg>
        )}
      </span>
      <span className="frame-share__text">
        {copied ? "COPIED" : "COPY RESULT"}
      </span>
    </button>
  );
}
