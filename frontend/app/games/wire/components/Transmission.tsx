"use client";

import { useState, useEffect, useCallback, useMemo, Fragment } from "react";

/* ==========================================================================
   Transmission — The intercepted paragraph with pulsing hidden word blocks.
   Renders the transmission text, replacing [WORD_X] placeholders with
   interactive hidden-word elements. Handles the type-in scan animation
   on initial load.
   ========================================================================== */

const STATIC_FRAMES = ["▓▒░▓", "░▓▒░", "▒▓░▒", "▓░▒▓", "░▒▓░", "▒░▓▒"];
const WORD_KEYS = ["WORD_A", "WORD_B", "WORD_C", "WORD_D"] as const;
type WordKey = (typeof WORD_KEYS)[number];

interface TransmissionProps {
  transmission: string;
  hiddenWords: [string, string, string, string];
  solvedWords: Set<number>; // indices of solved words (0-3)
  revealedWords: Set<number>; // words revealed by penalty (not earned)
  activeWordIndex: number | null; // which word the player clicked to guess
  onWordClick: (index: number) => void;
  scanComplete: boolean;
  onScanComplete: () => void;
}

/** Parse transmission text into segments: text + placeholders */
function parseTransmission(
  text: string
): Array<{ type: "text"; value: string } | { type: "word"; index: number }> {
  const segments: Array<
    { type: "text"; value: string } | { type: "word"; index: number }
  > = [];
  const pattern = /\[WORD_([A-D])\]/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: "text", value: text.slice(lastIndex, match.index) });
    }
    const keyLetter = match[1];
    const index = WORD_KEYS.indexOf(`WORD_${keyLetter}` as WordKey);
    segments.push({ type: "word", index });
    lastIndex = pattern.lastIndex;
  }
  if (lastIndex < text.length) {
    segments.push({ type: "text", value: text.slice(lastIndex) });
  }
  return segments;
}

/** HiddenWordBlock — pulsing amber block with cycling static */
function HiddenWordBlock({
  word,
  index,
  solved,
  revealed,
  active,
  onClick,
  scanComplete,
}: {
  word: string;
  index: number;
  solved: boolean;
  revealed: boolean;
  active: boolean;
  onClick: () => void;
  scanComplete: boolean;
}) {
  const [staticFrame, setStaticFrame] = useState(0);
  const [flashActive, setFlashActive] = useState(false);
  const [justSolved, setJustSolved] = useState(false);

  // Cycle static characters when unsolved
  useEffect(() => {
    if (solved || revealed) return;
    const prefersReduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;
    if (prefersReduced) return;
    const interval = setInterval(
      () => setStaticFrame((f) => (f + 1) % STATIC_FRAMES.length),
      150
    );
    return () => clearInterval(interval);
  }, [solved, revealed]);

  // Flash on solve
  useEffect(() => {
    if (solved && !justSolved) {
      setJustSolved(true);
      setFlashActive(true);
      const timer = setTimeout(() => setFlashActive(false), 300);
      return () => clearTimeout(timer);
    }
  }, [solved, justSolved]);

  if (solved || revealed) {
    return (
      <span
        className={`wire-hidden wire-hidden--solved${flashActive ? " wire-hidden--flash" : ""}${revealed && !solved ? " wire-hidden--penalty" : ""}`}
        aria-label={`Revealed word: ${word}`}
      >
        {word}
      </span>
    );
  }

  return (
    <button
      type="button"
      className={`wire-hidden${active ? " wire-hidden--active" : ""}${!scanComplete ? " wire-hidden--dormant" : ""}`}
      onClick={scanComplete ? onClick : undefined}
      aria-label={`Hidden word ${index + 1} of 4. Click to guess.`}
      tabIndex={scanComplete ? 0 : -1}
    >
      <span className="wire-hidden__static" aria-hidden="true">
        {STATIC_FRAMES[staticFrame]}
      </span>
    </button>
  );
}

export default function Transmission({
  transmission,
  hiddenWords,
  solvedWords,
  revealedWords,
  activeWordIndex,
  onWordClick,
  scanComplete,
  onScanComplete,
}: TransmissionProps) {
  const segments = useMemo(
    () => parseTransmission(transmission),
    [transmission]
  );

  // Split into lines (sentences separated by \n)
  type Segment = { type: "text"; value: string } | { type: "word"; index: number };
  const lines = useMemo(() => {
    const result: Segment[][] = [[]];
    for (const seg of segments) {
      if (seg.type === "text" && seg.value.includes("\n")) {
        const parts = seg.value.split("\n");
        for (let i = 0; i < parts.length; i++) {
          if (parts[i]) {
            result[result.length - 1].push({ type: "text" as const, value: parts[i] });
          }
          if (i < parts.length - 1) {
            result.push([]);
          }
        }
      } else {
        result[result.length - 1].push(seg);
      }
    }
    return result;
  }, [segments]);

  // Scan-in animation: reveal lines one by one
  const [visibleLines, setVisibleLines] = useState(0);
  const [lineRevealed, setLineRevealed] = useState<boolean[]>(
    new Array(lines.length).fill(false)
  );

  useEffect(() => {
    const prefersReduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    if (prefersReduced) {
      setVisibleLines(lines.length);
      setLineRevealed(new Array(lines.length).fill(true));
      onScanComplete();
      return;
    }

    let i = 0;
    const interval = setInterval(() => {
      i++;
      setVisibleLines(i);
      setLineRevealed((prev) => {
        const next = [...prev];
        next[i - 1] = true;
        return next;
      });
      if (i >= lines.length) {
        clearInterval(interval);
        // small delay before enabling interaction
        setTimeout(() => onScanComplete(), 300);
      }
    }, 500);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lines.length]);

  return (
    <div
      className="wire-transmission"
      role="region"
      aria-label="Intercepted transmission"
    >
      {lines.map((lineSegments, lineIdx) => (
        <p
          key={lineIdx}
          className={`wire-transmission__line${lineIdx < visibleLines ? " wire-transmission__line--visible" : ""}`}
          style={{ animationDelay: `${lineIdx * 100}ms` }}
        >
          {lineSegments.map((seg, segIdx) => {
            if (seg.type === "text") {
              return (
                <Fragment key={`t-${lineIdx}-${segIdx}`}>{seg.value}</Fragment>
              );
            }
            return (
              <HiddenWordBlock
                key={`w-${seg.index}`}
                word={hiddenWords[seg.index]}
                index={seg.index}
                solved={solvedWords.has(seg.index)}
                revealed={revealedWords.has(seg.index)}
                active={activeWordIndex === seg.index}
                onClick={() => onWordClick(seg.index)}
                scanComplete={scanComplete}
              />
            );
          })}
        </p>
      ))}
    </div>
  );
}
