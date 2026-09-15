"use client";

// Shared styles live in verify.css, which all three Deep Dive shells already
// import. Re-importing here keeps the component self-contained (the bundler
// dedupes the import).
import "../styles/verify.css";

/* ---------------------------------------------------------------------------
   SpreadDisagreement — the promoted "what sources agree on vs where they split"
   panel.

   Previously this content lived buried inside ComparativeView behind a
   "Key agreements & disagreements" disclosure at the very bottom of the Deep
   Dive. It is now pulled UP to sit right after the spectrum, before Six Lenses,
   as the centerpiece: the reader sees the shared facts and the contested ones
   without a click.

   Two editorial tracks separated by a hairline ink rule:
     - WHAT THEY AGREE ON   (deepDive.consensus)  with a converging mark
     - WHERE THEY SPLIT     (deepDive.divergence)  with a diverging mark

   An empty track is omitted entirely (never fabricated). If BOTH are empty the
   component renders nothing, so callers can mount it unconditionally.

   Shared by the mobile DeepDive, the desktop InlineDeepDive, and the standalone
   /story archive page so the vocabulary lives in exactly one place.
   Styles: `.spread-disagree*` in verify.css.
   --------------------------------------------------------------------------- */

/* Converging mark — two strokes meeting at a point: sources arriving at the
   same account. Calm (sense-low) tone. */
function ConvergeMark() {
  return (
    <svg
      className="spread-disagree__mark"
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      aria-hidden="true"
    >
      <path d="M2 4 L11 9" stroke="var(--sense-low)" strokeWidth="1.5" strokeLinecap="round" opacity="0.85" />
      <path d="M2 14 L11 9" stroke="var(--sense-low)" strokeWidth="1.5" strokeLinecap="round" opacity="0.85" />
      <circle cx="13" cy="9" r="2" fill="var(--sense-low)" />
    </svg>
  );
}

/* Diverging mark — one origin splitting into two: sources parting ways. Alert
   (sense-high) tone. */
function DivergeMark() {
  return (
    <svg
      className="spread-disagree__mark"
      width="18"
      height="18"
      viewBox="0 0 18 18"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="5" cy="9" r="2" fill="var(--sense-high)" />
      <path d="M7 9 L16 4" stroke="var(--sense-high)" strokeWidth="1.5" strokeLinecap="round" opacity="0.85" />
      <path d="M7 9 L16 14" stroke="var(--sense-high)" strokeWidth="1.5" strokeLinecap="round" opacity="0.85" />
    </svg>
  );
}

interface SpreadDisagreementProps {
  consensus?: string[];
  divergence?: string[];
}

export default function SpreadDisagreement({ consensus, divergence }: SpreadDisagreementProps) {
  const agree = (consensus ?? []).filter((p) => typeof p === "string" && p.trim().length > 0);
  const split = (divergence ?? []).filter((p) => typeof p === "string" && p.trim().length > 0);

  // Both empty -> render nothing. Never assert agreement or fabricate a split.
  if (agree.length === 0 && split.length === 0) return null;

  return (
    <div
      className="spread-disagree"
      role="group"
      aria-label="What sources agree on and where they split"
    >
      {agree.length > 0 && (
        <section
          className="spread-disagree__track spread-disagree__track--agree"
          aria-label="What sources agree on"
        >
          <div className="spread-disagree__head">
            <ConvergeMark />
            <h3 className="spread-disagree__label text-meta">What they agree on</h3>
          </div>
          <ul className="spread-disagree__list" role="list">
            {agree.map((pt, i) => (
              <li key={`agree-${i}`} className="spread-disagree__point">{pt}</li>
            ))}
          </ul>
        </section>
      )}

      {agree.length > 0 && split.length > 0 && (
        <hr className="spread-disagree__rule ink-rule" aria-hidden="true" />
      )}

      {split.length > 0 && (
        <section
          className="spread-disagree__track spread-disagree__track--split"
          aria-label="Where sources split"
        >
          <div className="spread-disagree__head">
            <DivergeMark />
            <h3 className="spread-disagree__label text-meta">Where they split</h3>
          </div>
          <ul className="spread-disagree__list" role="list">
            {split.map((pt, i) => (
              <li key={`split-${i}`} className="spread-disagree__point">{pt}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
