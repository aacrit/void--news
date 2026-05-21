/* ---------------------------------------------------------------------------
   LogoMark — small wordmark used in every IG render template.
   Reuses the existing LogoIcon SVG via inline rendering (no client import).
   --------------------------------------------------------------------------- */

interface Props {
  position?: "tl" | "br";
  tone?: "ink" | "warm";
}

export function LogoMark({ position = "tl", tone = "ink" }: Props) {
  const color = tone === "warm" ? "var(--cin-amber-bright, #AD7E1E)" : "currentColor";
  return (
    <div className={`ig-mark ig-mark--${position}`} style={{ color }}>
      <svg
        className="ig-mark__sigil"
        viewBox="0 0 100 100"
        aria-hidden="true"
        focusable="false"
      >
        <circle cx="50" cy="50" r="44" fill="none" stroke="currentColor" strokeWidth="3" />
        <line x1="14" y1="50" x2="86" y2="50" stroke="currentColor" strokeWidth="3" />
        <line x1="50" y1="14" x2="50" y2="32" stroke="currentColor" strokeWidth="3" />
      </svg>
      <span>void --news</span>
    </div>
  );
}
