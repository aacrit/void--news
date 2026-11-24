/* ---------------------------------------------------------------------------
   LogoMark — Void brand furniture for the IG render templates.

   Three exports:
     • IgSigil    — the Sigil-O mark on its own (coverage ring + level balance
                    beam with |-| end-ticks + scale foot). Geometry mirrors
                    components/SigilWordmark so the IG mark matches the masthead.
     • LogoMark   — the small STAMPED wordmark ( Sigil + "VOID <WORD>" ) that
                    sits in a corner of every slide.
     • HeroSigil  — the oversized centred mark used on hook / CTA slides.

   Every track uses the SAME Sigil-O; only the accent colour and the second
   wordmark word change (NEWS / HISTORY / WEEKLY). No "void --news" terminal
   text anywhere — this is the newspaper identity.
   --------------------------------------------------------------------------- */

type Ground = "onDark" | "onLight";
type Accent = "terracotta" | "umber" | "red";

const GROUND_COLOR: Record<Ground, string> = {
  onDark: "var(--ig-dark-fg)",   // light text for the dark ink slides
  onLight: "var(--ig-cream-fg)", // dark ink text for the cream slides
};

const ACCENT_COLOR: Record<Accent, string> = {
  terracotta: "var(--ig-terracotta)",
  umber: "var(--ig-umber)",
  red: "var(--ig-red)",
};

/* The Sigil mark only. viewBox runs to y=124 so the scale foot (which hangs
   below the ring like a descender in the wordmark) is fully contained. */
export function IgSigil({
  size,
  className,
  strokeColor = "currentColor",
}: {
  size: number;
  className?: string;
  strokeColor?: string;
}) {
  return (
    <svg
      className={className}
      width={size}
      height={size * 1.24}
      viewBox="0 0 100 124"
      fill="none"
      stroke={strokeColor}
      aria-hidden="true"
      focusable="false"
      style={{ display: "block", overflow: "visible" }}
    >
      {/* Coverage ring */}
      <circle cx="50" cy="50" r="41" strokeWidth="8" />
      {/* Level balance beam + |-| weight ticks */}
      <line x1="4" y1="50" x2="96" y2="50" strokeWidth="6" strokeLinecap="round" />
      <line x1="4" y1="42" x2="4" y2="58" strokeWidth="5" strokeLinecap="round" />
      <line x1="96" y1="42" x2="96" y2="58" strokeWidth="5" strokeLinecap="round" />
      {/* Scale foot — post + base */}
      <line x1="50" y1="91" x2="50" y2="112" strokeWidth="6" strokeLinecap="round" />
      <path d="M35 118 C43 113 57 113 65 118" strokeWidth="6" strokeLinecap="round" />
    </svg>
  );
}

/* Corner stamp: Sigil + "VOID <WORD>" wordmark. Present on every slide.
   `tone` = ground colour of the sigil + "VOID"; `accent` = second-word colour. */
export function LogoMark({
  position = "bl",
  tone = "onDark",
  accent = "terracotta",
  word = "NEWS",
}: {
  position?: "tl" | "tr" | "bl" | "br";
  tone?: Ground;
  accent?: Accent;
  word?: string;
}) {
  return (
    <div className={`ig-stamp ig-stamp--${position}`} style={{ color: GROUND_COLOR[tone] }}>
      <IgSigil size={26} className="ig-stamp__sigil" />
      <span className="ig-stamp__word">
        VOID <span className="ig-stamp__word-accent" style={{ color: ACCENT_COLOR[accent] }}>{word}</span>
      </span>
    </div>
  );
}

/* Hero mark for hook / CTA slides: big centred Sigil above an optional wordmark.
   The whole mark paints in the track accent. */
export function HeroSigil({
  size = 260,
  accent = "terracotta",
  word,
}: {
  size?: number;
  accent?: Accent;
  /** When set, renders "VOID <word>" under the mark (accent-coloured). */
  word?: string;
}) {
  return (
    <div className="ig-hero-mark" style={{ color: ACCENT_COLOR[accent] }}>
      <IgSigil size={size} className="ig-hero-mark__sigil" />
      {word && (
        <span className="ig-hero-mark__word">
          <span className="ig-hero-mark__word-void">VOID</span> {word}
        </span>
      )}
    </div>
  );
}
