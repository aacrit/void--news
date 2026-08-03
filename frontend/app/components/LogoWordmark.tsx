"use client";

/* ---------------------------------------------------------------------------
   LogoWordmark — Text-only logo: "void --news" with hollow O
   No icon mark. Use where only the brand name is needed:
   edition lines, attribution, compact footers, print contexts.

   Direction 5 "Negative Space O" treatment:
   "void" — bold serif where the "O" is a hollow outline (the void).
   "--news" — lighter monospace letterforms.
   All vector — no font dependency.
   --------------------------------------------------------------------------- */

interface LogoWordmarkProps {
  /** Height in px. Width scales proportionally. Default 20. */
  height?: number;
  className?: string;
}

export default function LogoWordmark({ height = 20, className }: LogoWordmarkProps) {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 200 40"
      fill="currentColor"
      role="img"
      aria-hidden="true"
      className={className}
      style={{ height, width: "auto", display: "block", flexShrink: 0 }}
    >
      {/* Interim wordmark: plain "Void News" (final logo pending CEO). */}
      <text
        x="0"
        y="30"
        fontFamily="var(--font-editorial, 'Playfair Display', Georgia, serif)"
        fontSize="32"
        fontWeight={700}
        letterSpacing="-0.01em"
      >
        Void News
      </text>
    </svg>
  );
}
