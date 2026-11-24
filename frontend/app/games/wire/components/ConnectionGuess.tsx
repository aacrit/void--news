"use client";

import { useState, useRef, useEffect, useCallback } from "react";

/* ==========================================================================
   ConnectionGuess — Input for guessing the secret connection.
   Appears after all 4 words are found. Player types their guess,
   then sees the real connection regardless. Honor-system scoring.
   ========================================================================== */

interface ConnectionGuessProps {
  onSubmit: (guess: string, claimedCorrect: boolean) => void;
  hint: string;
}

export default function ConnectionGuess({ onSubmit, hint }: ConnectionGuessProps) {
  const [value, setValue] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [showHint, setShowHint] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => inputRef.current?.focus(), 300);
    return () => clearTimeout(timer);
  }, []);

  const handleSubmit = useCallback(() => {
    const guess = value.trim();
    if (!guess) return;
    setSubmitted(true);
    // Will trigger reveal in parent — the honor checkbox comes in RevealPanel
    onSubmit(guess, false);
  }, [value, onSubmit]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const handleSkip = useCallback(() => {
    onSubmit("", false);
  }, [onSubmit]);

  return (
    <div className="wire-connection" role="group" aria-label="Guess the connection">
      <div className="wire-connection__header">
        <p className="wire-connection__prompt">WHAT CONNECTS THESE FOUR WORDS?</p>
      </div>

      <div className="wire-connection__field-row">
        <input
          ref={inputRef}
          type="text"
          className="wire-connection__field"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="the connection is..."
          autoComplete="off"
          spellCheck={false}
          disabled={submitted}
          aria-label="Your connection guess"
        />
        <button
          type="button"
          className="wire-connection__submit"
          onClick={handleSubmit}
          disabled={!value.trim() || submitted}
        >
          TRANSMIT
        </button>
      </div>

      <div className="wire-connection__actions">
        {!showHint && (
          <button
            type="button"
            className="wire-connection__hint-btn"
            onClick={() => setShowHint(true)}
          >
            need a hint?
          </button>
        )}
        {showHint && (
          <p className="wire-connection__hint" role="note" aria-live="polite">
            {hint}
          </p>
        )}
        <button
          type="button"
          className="wire-connection__skip"
          onClick={handleSkip}
        >
          reveal connection
        </button>
      </div>
    </div>
  );
}
