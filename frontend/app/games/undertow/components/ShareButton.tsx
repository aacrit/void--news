"use client";

import { useState, useCallback } from "react";

/* ==========================================================================
   ShareButton — Copies punchy game result grid to clipboard

   Share format:
   void --undertow #1
   CULT <-> YOGA CLASS

   ◆ ○ ● ◈   attempt 1
   ◆ ◈ ○ ●   attempt 2
   ◆ ◈ ● ○   ✓

   called: ✓
   void.news/games
   ========================================================================== */

interface ShareButtonProps {
  challengeId: number;
  axisLabel: string;
  correctOrder: string[];
  attemptHistory: (string | null)[][];
  attemptsUsed: number;
  confidencePick: string | null;
  confidenceResult: "correct" | "wrong" | null;
}

/** Map artifact position (in correct order) to geometric symbol */
const SYMBOLS = ["\u25C6", "\u25C8", "\u25CB", "\u25CF"];

export default function ShareButton({
  challengeId,
  axisLabel,
  correctOrder,
  attemptHistory,
  attemptsUsed,
  confidencePick,
  confidenceResult,
}: ShareButtonProps) {
  const [copied, setCopied] = useState(false);

  const buildShareText = useCallback(() => {
    // Map each artifact id to its symbol (based on correct order position)
    const symbolMap = new Map<string, string>();
    correctOrder.forEach((id, i) => symbolMap.set(id, SYMBOLS[i]));

    const totalAttempts = attemptHistory.length;
    const lastAttempt = attemptHistory[totalAttempts - 1];
    const wasCorrect =
      lastAttempt &&
      lastAttempt.every((id, i) => id === correctOrder[i]);

    // Build attempt lines
    const attemptLines = attemptHistory.map((order, idx) => {
      const symbols = order
        .map((id) => (id ? symbolMap.get(id) ?? "\u25A1" : "\u25A1"))
        .join(" ");

      const isLast = idx === totalAttempts - 1;
      if (isLast && wasCorrect) {
        return `${symbols}   \u2713`;
      }
      return `${symbols}   attempt ${idx + 1}`;
    });

    const lines = [
      `void --undertow #${challengeId}`,
      axisLabel,
      "",
      ...attemptLines,
    ];

    // Confidence line
    if (confidencePick) {
      lines.push("");
      lines.push(
        confidenceResult === "correct"
          ? "called: \u2713"
          : "called: \u2717"
      );
    }

    lines.push("void.news/games");

    return lines.join("\n");
  }, [
    challengeId,
    axisLabel,
    correctOrder,
    attemptHistory,
    confidencePick,
    confidenceResult,
  ]);

  const handleCopy = useCallback(async () => {
    const text = buildShareText();
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
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
