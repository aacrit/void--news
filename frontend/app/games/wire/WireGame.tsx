"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
import Link from "next/link";
import { DAILY_WIRE } from "./data";
import Transmission from "./components/Transmission";
import WordInput from "./components/WordInput";
import ConnectionGuess from "./components/ConnectionGuess";
import RevealPanel from "./components/RevealPanel";

/* ==========================================================================
   WireGame — void --wire: Daily "Intercept the Transmission" Word Puzzle

   State machine:
     loading    → transmission types in line by line
     playing    → player clicks hidden blocks, guesses words (3 attempts each)
     connecting → all 4 words found, now guess the connection
     reveal     → show connection + commentary + share

   CRT terminal aesthetic — dark, amber-tinted, signal-based.
   ========================================================================== */

type Phase = "loading" | "playing" | "connecting" | "reveal";

const MAX_WORD_ATTEMPTS = 3;

export default function WireGame() {
  const challenge = DAILY_WIRE;
  const [phase, setPhase] = useState<Phase>("loading");
  const [mounted, setMounted] = useState(false);

  // Per-word state
  const [solvedWords, setSolvedWords] = useState<Set<number>>(new Set());
  const [revealedWords, setRevealedWords] = useState<Set<number>>(new Set());
  const [wordAttempts, setWordAttempts] = useState<number[]>([0, 0, 0, 0]);
  const [activeWordIndex, setActiveWordIndex] = useState<number | null>(null);

  // Connection state
  const [playerConnectionGuess, setPlayerConnectionGuess] = useState("");

  // UTC time for header
  const [utcTime, setUtcTime] = useState("");

  useEffect(() => {
    setMounted(true);
    const now = new Date();
    const hh = String(now.getUTCHours()).padStart(2, "0");
    const mm = String(now.getUTCMinutes()).padStart(2, "0");
    setUtcTime(`${hh}:${mm}`);
  }, []);

  // Format date
  const dateStr = mounted
    ? new Date(challenge.date + "T00:00:00").toLocaleDateString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
      })
    : "\u00A0";

  // Check if all words are found (solved or revealed by penalty)
  const allWordsFound = useMemo(() => {
    for (let i = 0; i < 4; i++) {
      if (!solvedWords.has(i) && !revealedWords.has(i)) return false;
    }
    return true;
  }, [solvedWords, revealedWords]);

  // Transition to connecting phase when all words found
  useEffect(() => {
    if (allWordsFound && phase === "playing") {
      // Brief pause for the last word-snap animation
      const timer = setTimeout(() => setPhase("connecting"), 600);
      return () => clearTimeout(timer);
    }
  }, [allWordsFound, phase]);

  const handleScanComplete = useCallback(() => {
    if (phase === "loading") {
      setPhase("playing");
    }
  }, [phase]);

  /** Handle clicking a hidden word block */
  const handleWordClick = useCallback(
    (index: number) => {
      if (phase !== "playing") return;
      if (solvedWords.has(index) || revealedWords.has(index)) return;
      setActiveWordIndex((prev) => (prev === index ? null : index));
    },
    [phase, solvedWords, revealedWords]
  );

  /** Handle a word guess attempt */
  const handleWordGuess = useCallback(
    (guess: string): "correct" | "wrong" => {
      if (activeWordIndex === null) return "wrong";

      const correctWord = challenge.hidden_words[activeWordIndex];
      const isCorrect = guess.toUpperCase().trim() === correctWord;

      if (isCorrect) {
        setSolvedWords((prev) => new Set(prev).add(activeWordIndex));
        setActiveWordIndex(null);
        return "correct";
      }

      // Wrong guess
      const newAttempts = [...wordAttempts];
      newAttempts[activeWordIndex] = (newAttempts[activeWordIndex] || 0) + 1;
      setWordAttempts(newAttempts);

      // Exhausted attempts? Reveal the word as penalty
      if (newAttempts[activeWordIndex] >= MAX_WORD_ATTEMPTS) {
        setRevealedWords((prev) => new Set(prev).add(activeWordIndex));
        setActiveWordIndex(null);
      }

      return "wrong";
    },
    [activeWordIndex, challenge.hidden_words, wordAttempts]
  );

  /** Close the word input */
  const handleWordInputClose = useCallback(() => {
    setActiveWordIndex(null);
  }, []);

  /** Handle connection guess submission */
  const handleConnectionSubmit = useCallback(
    (guess: string) => {
      setPlayerConnectionGuess(guess);
      setPhase("reveal");
    },
    []
  );

  // Count words the player actually guessed (not penalty reveals)
  const wordsCorrect = solvedWords.size;

  return (
    <div
      className={`wire-page${mounted ? " wire-page--mounted" : ""}${phase === "reveal" ? " wire-page--revealed" : ""}`}
    >
      {/* Layer: CRT background gradient */}
      <div className="wire-page__crt-bg" aria-hidden="true" />

      {/* Layer: Scan lines */}
      <div className="wire-scanlines" aria-hidden="true" />

      {/* Layer: Film grain */}
      <div className="wire-page__grain" aria-hidden="true" />

      {/* Layer: Vignette */}
      <div className="wire-page__vignette" aria-hidden="true" />

      {/* Content */}
      <div className="wire-page__content">
        {/* Navigation */}
        <nav className="wire-page__nav" aria-label="Breadcrumb">
          <Link href="/games" className="wire-page__back">
            <span aria-hidden="true">&larr;</span> void --games
          </Link>
        </nav>

        {/* Header */}
        <header className="wire-page__header">
          <div className="wire-page__header-top">
            <h1 className="wire-page__title">VOID --WIRE</h1>
            <p className="wire-page__meta" suppressHydrationWarning>
              #{challenge.id} &middot; {dateStr}
            </p>
          </div>
          <div className="wire-page__rule" aria-hidden="true" />
          <p className="wire-page__tagline">
            four words. one frequency. what connects them?
          </p>
          <p className="wire-page__timestamp" suppressHydrationWarning>
            TRANSMISSION RECEIVED &middot;{" "}
            <span className="wire-page__utc">{utcTime || "00:00"}</span> UTC
          </p>
        </header>

        {/* Attempt counter — only during playing phase */}
        {phase === "playing" && activeWordIndex !== null && (
          <div
            className="wire-page__attempt"
            aria-live="polite"
            aria-label={`${MAX_WORD_ATTEMPTS - (wordAttempts[activeWordIndex] || 0)} attempts remaining for word ${activeWordIndex + 1}`}
          >
            <span className="wire-page__attempt-label">ATTEMPTS</span>
            <div className="wire-page__attempt-dots">
              {Array.from({ length: MAX_WORD_ATTEMPTS }).map((_, i) => (
                <span
                  key={i}
                  className={`wire-page__attempt-dot${i < MAX_WORD_ATTEMPTS - (wordAttempts[activeWordIndex] || 0) ? " wire-page__attempt-dot--active" : ""}`}
                  aria-hidden="true"
                />
              ))}
            </div>
          </div>
        )}

        {/* Progress bar — words found */}
        {phase !== "loading" && phase !== "reveal" && (
          <div className="wire-page__progress" aria-label="Words found">
            <div className="wire-page__progress-bar">
              {[0, 1, 2, 3].map((i) => (
                <span
                  key={i}
                  className={`wire-page__progress-pip${solvedWords.has(i) ? " wire-page__progress-pip--solved" : ""}${revealedWords.has(i) ? " wire-page__progress-pip--revealed" : ""}`}
                  aria-hidden="true"
                />
              ))}
            </div>
            <span className="wire-page__progress-text">
              {solvedWords.size + revealedWords.size}/4
            </span>
          </div>
        )}

        {/* Transmission */}
        <Transmission
          transmission={challenge.transmission}
          hiddenWords={challenge.hidden_words}
          solvedWords={solvedWords}
          revealedWords={revealedWords}
          activeWordIndex={activeWordIndex}
          onWordClick={handleWordClick}
          scanComplete={phase !== "loading"}
          onScanComplete={handleScanComplete}
        />

        {/* Word input — appears when a hidden block is clicked */}
        {phase === "playing" &&
          activeWordIndex !== null &&
          !solvedWords.has(activeWordIndex) &&
          !revealedWords.has(activeWordIndex) && (
            <WordInput
              wordIndex={activeWordIndex}
              maxAttempts={MAX_WORD_ATTEMPTS}
              attemptsUsed={wordAttempts[activeWordIndex] || 0}
              onGuess={handleWordGuess}
              onClose={handleWordInputClose}
            />
          )}

        {/* Connection guess — after all words found */}
        {phase === "connecting" && (
          <ConnectionGuess
            onSubmit={handleConnectionSubmit}
            hint={challenge.connection_hint}
          />
        )}

        {/* Reveal panel */}
        {phase === "reveal" && (
          <RevealPanel
            challengeId={challenge.id}
            connection={challenge.connection}
            reveal={challenge.reveal}
            wordsCorrect={wordsCorrect}
            totalWords={4}
            playerGuess={playerConnectionGuess}
          />
        )}
      </div>
    </div>
  );
}
