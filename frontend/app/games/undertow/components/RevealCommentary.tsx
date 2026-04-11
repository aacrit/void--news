"use client";

/* ==========================================================================
   RevealCommentary — The Orwellian 2-3 sentence reveal text

   The most important text in the game. It should feel like marginalia —
   a quiet voice that noticed something. Never bold, never exclamation.
   Italic Inter, gray, small. Subtle animation: fade-in with slight
   translateY.
   ========================================================================== */

interface RevealCommentaryProps {
  text: string;
  /** Animation delay in ms */
  delay: number;
}

export default function RevealCommentary({ text, delay }: RevealCommentaryProps) {
  return (
    <div
      className="ut-commentary"
      style={{ "--commentary-delay": `${delay}ms` } as React.CSSProperties}
      aria-label="Analysis"
    >
      <p className="ut-commentary__text">{text}</p>
    </div>
  );
}
