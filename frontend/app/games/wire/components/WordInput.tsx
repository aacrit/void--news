"use client";

import { useState, useRef, useEffect, useCallback } from "react";

/* ==========================================================================
   WordInput — Input field for guessing a hidden word.
   Appears below the transmission when a hidden-word block is clicked.
   3 attempts per word. Wrong = shake + decrement. Correct = snap + solve.
   ========================================================================== */

interface WordInputProps {
  wordIndex: number;
  maxAttempts: number;
  attemptsUsed: number;
  onGuess: (guess: string) => "correct" | "wrong";
  onClose: () => void;
}

export default function WordInput({
  wordIndex,
  maxAttempts,
  attemptsUsed,
  onGuess,
  onClose,
}: WordInputProps) {
  const [value, setValue] = useState("");
  const [shaking, setShaking] = useState(false);
  const [feedback, setFeedback] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-focus on mount
  useEffect(() => {
    const timer = setTimeout(() => inputRef.current?.focus(), 50);
    return () => clearTimeout(timer);
  }, []);

  const attemptsRemaining = maxAttempts - attemptsUsed;

  const handleSubmit = useCallback(() => {
    const guess = value.trim();
    if (!guess) return;

    const result = onGuess(guess);
    if (result === "correct") {
      // Parent handles the solve state; input will unmount
      return;
    }

    // Wrong guess
    setShaking(true);
    setFeedback("Not this one.");
    setValue("");
    setTimeout(() => setShaking(false), 500);
    setTimeout(() => setFeedback(""), 2000);
  }, [value, onGuess]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter") {
        e.preventDefault();
        handleSubmit();
      } else if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    },
    [handleSubmit, onClose]
  );

  return (
    <div
      className={`wire-input${shaking ? " wire-input--shake" : ""}`}
      role="group"
      aria-label={`Guess word ${wordIndex + 1}`}
    >
      <div className="wire-input__row">
        <label className="wire-input__label" htmlFor={`wire-guess-${wordIndex}`}>
          <span className="wire-input__label-text">WORD {wordIndex + 1}</span>
          <span className="wire-input__attempts" aria-live="polite">
            {attemptsRemaining} attempt{attemptsRemaining !== 1 ? "s" : ""} left
          </span>
        </label>
        <div className="wire-input__field-row">
          <input
            ref={inputRef}
            id={`wire-guess-${wordIndex}`}
            type="text"
            className="wire-input__field"
            value={value}
            onChange={(e) => setValue(e.target.value.toUpperCase())}
            onKeyDown={handleKeyDown}
            placeholder="TYPE YOUR GUESS"
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
            aria-describedby={feedback ? `wire-feedback-${wordIndex}` : undefined}
          />
          <button
            type="button"
            className="wire-input__submit"
            onClick={handleSubmit}
            disabled={!value.trim()}
            aria-label="Submit guess"
          >
            DECODE
          </button>
        </div>
      </div>

      {feedback && (
        <p
          id={`wire-feedback-${wordIndex}`}
          className="wire-input__feedback"
          role="alert"
          aria-live="assertive"
        >
          {feedback}
        </p>
      )}
    </div>
  );
}
