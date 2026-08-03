"use client";

/* ---------------------------------------------------------------------------
   LogoFull — Full combination mark: Hybrid icon + "void --news" wordmark
   Single SVG entity. Use everywhere the full brand needs to appear:
   NavBar (desktop), Footer, error pages, about pages.

   The wordmark uses vector-drawn letterforms (not fonts) so it renders
   identically everywhere — no font-loading dependency.

   Direction 5 "Negative Space O" + hybrid scale beam:
   "void" — bold serif letterforms where the "O" is a hollow outline
   (stroke only, no fill), the defining visual tension.
   "--news" — lighter monospace letterforms (data/code precision).
   Icon — the void circle with scale beam in idle state, to the left.
   --------------------------------------------------------------------------- */

interface LogoFullProps {
  /** Height in px. Width scales proportionally. Default 28. */
  height?: number;
  className?: string;
}

export default function LogoFull({ height = 28, className }: LogoFullProps) {
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
      {/* ── Hybrid Icon (void circle + scale beam, scaled to wordmark) ─ */}
      <g
        transform="translate(2,4) scale(0.83)"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {/* Void circle — organic hand-drawn path */}
        <path d="M16 4 C24 3.5 25.5 7.5 25 13 C24.5 18.5 22.5 22 16 22 C9.5 22 7.5 18.5 7 13 C6.5 7.5 8 3.5 16 4" className="si-void" />
        {/* Beam group — idle tipping animation */}
        <g className="si-beam--idle">
          <path d="M3 13 C10 12.2 22 13.8 29 13" />
          <line x1="5" y1="11" x2="5" y2="15" />
          <line x1="27" y1="11" x2="27" y2="15" />
        </g>
        {/* Post */}
        <line x1="16" y1="22" x2="16" y2="29" />
        {/* Base — organic subtle curve */}
        <path d="M12 29 C14 28.7 18 29.3 20 29" />
      </g>

      {/* ── Wordmark ──────────────────────────────────────────────── */}
      {/* Interim wordmark: plain "Void News" (final logo pending CEO). */}
      <text
        x="40"
        y="30"
        fill="currentColor"
        fontFamily="var(--font-editorial, 'Playfair Display', Georgia, serif)"
        fontSize="30"
        fontWeight={700}
        letterSpacing="-0.01em"
      >
        Void News
      </text>
    </svg>
  );
}
