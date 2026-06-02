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
      viewBox="0 0 340 40"
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
      <g transform="translate(36,2)">
        {/* "v" — bold serif letterform */}
        <polygon
          points="0,4 5.5,4 14,28 22.5,4 28,4 16.5,36 11.5,36"
        />

        {/* "o" — THE VOID: hollow outline only, no fill.
            An organic hand-drawn oval, empty interior.
            The void at the heart of the word. */}
        <path
          d="M48 3.5 C61 3 62 10 61.5 20 C61 30 58 37 48 36.5 C38 37 35 30 34.5 20 C34 10 35 3 48 3.5"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
        />

        {/* "i" — serif letterform */}
        <rect x="69" y="2" width="5" height="5" rx="0.8" />
        <rect x="69.5" y="11" width="4" height="25" rx="0.5" />

        {/* "d" — serif letterform */}
        <path d="M82,20C82,10.5 87,3 94,3C97,3 100,4.5 102,7.5L102,0L107,0L107,36L102,36L102,32.5C100,35.5 97,37 94,37C87,37 82,29.5 82,20ZM88,20C88,27.5 90.8,32 95,32C98,32 100.5,29.5 102,26L102,14C100.5,10.5 98,8 95,8C90.8,8 88,12.5 88,20Z" />

        {/* "--news" — lighter monospace letterforms */}
        <rect x="122" y="17.5" width="10" height="3" rx="0.5" />
        <rect x="134" y="17.5" width="10" height="3" rx="0.5" />
        <path d="M156,12L159.2,12L159.2,16C161,13 163.5,11 167,11C170,11 172,12.5 173.2,14.8C174,16.5 174,18.5 174,21L174,36L170.8,36L170.8,21.5C170.8,18.5 170.5,17 169.5,15.8C168.5,14.6 167,14 165,14C162.5,14 160.8,15.5 159.8,17.5C159.2,18.8 159.2,20 159.2,21.5L159.2,36L156,36Z" />
        <path d="M182,23.5C182,17.5 185.5,11 192,11C198.5,11 201.5,17 201.5,23L201.5,24.5L185.5,24.5C185.8,29 188.5,33 192.5,33C195.5,33 197.5,31 198.8,29L201,30.5C199,33.5 196,36 192,36C186,36 182,30 182,23.5ZM185.5,22L198,22C197.5,17.5 195.5,14 192,14C188.5,14 186.2,17.5 185.5,22Z" />
        <path d="M208,12L211.5,12L217,30L222.5,12L225.5,12L231,30L236.5,12L240,12L232.5,36L229,36L223.5,18L218,36L214.5,36Z" />
        <path d="M247,28C247,24.5 249,22.5 252,21.5L256.5,20C259,19 260,17.8 260,16C260,13.8 258,12 255,12C252,12 250,13.5 249,15.5L246.5,14C248,11.5 251,9.5 255,9.5C260,9.5 263.5,12.5 263.5,16.5C263.5,19.5 261.5,21.5 258.5,22.5L254,24C251.5,25 250.5,26.5 250.5,28.5C250.5,31 252.5,33 255.5,33C258,33 260,31.5 261,29.5L263.2,31C261.5,34 258.5,36 255,36C250.5,36 247,32.5 247,28Z" />
      </g>
    </svg>
  );
}
