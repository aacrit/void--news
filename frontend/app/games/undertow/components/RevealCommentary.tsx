"use client";

/* ==========================================================================
   RevealCommentary — The Orwellian 2-3 sentence reveal text

   The most important text in the game. It should feel like marginalia --
   a quiet voice that noticed something. Never bold, never exclamation.
   Italic Inter, muted, small. Subtle animation: fade-in with slight
   translateY, staggered per card during sequential reveal.
   ========================================================================== */

interface RevealCommentaryProps {
  text: string;
  /** Animation delay in ms */
  delay: number;
}

export default function RevealCommentary({ text, delay }: RevealCommentaryProps) {
  return (
    <div
      className="undertow-reveal__commentary"
      style={{ "--commentary-delay": `${delay}ms` } as React.CSSProperties}
      aria-label="Analysis"
    >
      <p className="undertow-reveal__text">{text}</p>
    </div>
  );
}
