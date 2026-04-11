"use client";

import { useState, useCallback } from "react";

/* ==========================================================================
   ShareButton — Copies geometric symbol grid of game result to clipboard

   Share format (spec):
   void --undertow #1
   axis: CONTROL <-> FREEDOM
   (player symbols)
   correct: (correct symbols)
   3 of 4 . 2 attempts
   void.news/games

   Uses solid/hollow geometric symbols — not emoji flags or political
   colors — to avoid spoiling the content.
   ========================================================================== */

interface ShareButtonProps {
  challengeId: number;
  playerOrder: (string | null)[];
  correctOrder: string[];
  attemptsUsed: number;
}

/** Map artifact position to geometric symbol */
const SYMBOLS = ["\u25C6", "\u25C8", "\u25CF", "\u25CB"]; // diamond, boxdot, circle, open circle

export default function ShareButton({
  challengeId,
  playerOrder,
  correctOrder,
  attemptsUsed,
}: ShareButtonProps) {
  const [copied, setCopied] = useState(false);

  const buildShareText = useCallback(() => {
    // Build a map: artifact id -> symbol index in correct order
    const symbolMap = new Map<string, string>();
    correctOrder.forEach((id, i) => symbolMap.set(id, SYMBOLS[i]));

    // Build player row
    const playerSymbols = playerOrder
      .map((id) => (id ? symbolMap.get(id) ?? "\u25A1" : "\u25A1"))
      .join(" ");

    // Build correct row
    const correctSymbols = correctOrder
      .map((id) => symbolMap.get(id) ?? "\u25A1")
      .join(" ");

    const correctCount = playerOrder.filter(
      (id, i) => id === correctOrder[i]
    ).length;

    const lines = [
      `void --undertow #${challengeId}`,
      `axis: CONTROL \u2194 FREEDOM`,
      playerSymbols,
      `correct: ${correctSymbols}`,
      `${correctCount} of ${correctOrder.length} \u00B7 ${attemptsUsed} attempt${attemptsUsed !== 1 ? "s" : ""}`,
      "void.news/games",
    ];

    return lines.join("\n");
  }, [challengeId, playerOrder, correctOrder, attemptsUsed]);

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
      className="ut-share"
      onClick={handleCopy}
      aria-label={copied ? "Copied to clipboard" : "Copy result to clipboard"}
    >
      <span className="ut-share__icon" aria-hidden="true">
        {copied ? (
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="3 8 6.5 11.5 13 4.5" />
          </svg>
        ) : (
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="5" y="5" width="9" height="9" rx="1.5" />
            <path d="M11 5V3.5A1.5 1.5 0 009.5 2h-7A1.5 1.5 0 001 3.5v7A1.5 1.5 0 002.5 12H5" />
          </svg>
        )}
      </span>
      <span className="ut-share__text">
        {copied ? "COPIED" : "COPY RESULT"}
      </span>
    </button>
  );
}
