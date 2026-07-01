"use client";

import { useState, useCallback } from "react";

/* ==========================================================================
   RevealPanel — Post-solve: connection established, commentary, share.
   Shows the real connection, the reveal text, honor-system checkbox,
   and a share button.
   ========================================================================== */

interface RevealPanelProps {
  challengeId: number;
  connection: string;
  reveal: string;
  wordsCorrect: number;
  totalWords: number;
  playerGuess: string;
}

export default function RevealPanel({
  challengeId,
  connection,
  reveal,
  wordsCorrect,
  totalWords,
  playerGuess,
}: RevealPanelProps) {
  const [honorClaimed, setHonorClaimed] = useState(false);
  const [copied, setCopied] = useState(false);

  const score = wordsCorrect * 25 + (honorClaimed ? 25 : 0);

  const shareText = [
    `void --wire #${challengeId}`,
    `${"████ ".repeat(totalWords).trim()}`,
    `solved: ${wordsCorrect}/${totalWords} words${honorClaimed ? " + connection" : ""}`,
    `connection: ${connection}`,
    `void.news/games`,
  ].join("\n");

  const handleShare = useCallback(async () => {
    if (navigator.share) {
      try {
        await navigator.share({ text: shareText });
        return;
      } catch {
        // fallthrough to clipboard
      }
    }
    try {
      await navigator.clipboard.writeText(shareText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // silent fail
    }
  }, [shareText]);

  return (
    <div className="wire-reveal" role="region" aria-label="Game results">
      {/* CONNECTION ESTABLISHED header */}
      <p className="wire-reveal__established">CONNECTION ESTABLISHED</p>

      {/* The connection */}
      <h2 className="wire-reveal__connection">{connection}</h2>

      {/* Organic ink divider */}
      <svg
        className="wire-reveal__divider"
        viewBox="0 0 400 4"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        <path d="M0,2 C40,0.5 80,3.5 120,2 C160,0.5 200,3 240,2 C280,1 320,3.5 360,2 C380,0.5 400,2 400,2" />
      </svg>

      {/* Reveal commentary */}
      <p className="wire-reveal__commentary">{reveal}</p>

      {/* Score line */}
      <p className="wire-reveal__score">
        {wordsCorrect}/{totalWords} words decoded
        {playerGuess && (
          <span className="wire-reveal__player-guess">
            {" "}
            &middot; your guess: &ldquo;{playerGuess}&rdquo;
          </span>
        )}
      </p>

      {/* Honor system checkbox */}
      <label className="wire-reveal__honor">
        <input
          type="checkbox"
          checked={honorClaimed}
          onChange={(e) => setHonorClaimed(e.target.checked)}
          className="wire-reveal__honor-check"
        />
        <span className="wire-reveal__honor-label">I got the connection</span>
      </label>

      {/* Share button */}
      <button
        type="button"
        className="wire-reveal__share"
        onClick={handleShare}
        aria-label="Share your result"
      >
        <svg
          className="wire-reveal__share-icon"
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          aria-hidden="true"
        >
          <path
            d="M4 8V13H12V8M8 2V10M8 2L5 5M8 2L11 5"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        {copied ? "COPIED" : "SHARE"}
      </button>
    </div>
  );
}
