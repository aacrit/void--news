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

   Two editorial tracks, set as the story's sidebar (beside it on a wide
   screen, after it on a narrow one):
     - What they agree on   (deepDive.consensus)
     - Where they split     (deepDive.divergence)
   In the Deep Dive's own voice (2026-09-26): the same small mono label as
   The Story and The Spread, hanging numerals in the margin, secondary ink
   at the sidebar size, space between points rather than a rule under each.
   It used to wear bold sans capitals, arrow glyphs and bright green and red
   dash bullets, a design language nothing else on the page spoke. The only
   colour left is a short hairline under each label: green for agree, red for
   split.

   An empty track is omitted entirely (never fabricated). If BOTH are empty the
   component renders nothing, so callers can mount it unconditionally.

   Shared by the mobile DeepDive, the desktop InlineDeepDive, and the standalone
   /story archive page so the vocabulary lives in exactly one place.
   Styles: `.spread-disagree*` in verify.css.
   --------------------------------------------------------------------------- */

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
    <aside className="spread-disagree" aria-label="What sources agree on and where they split">
      {agree.length > 0 && (
        <section
          className="spread-disagree__track spread-disagree__track--agree"
          aria-labelledby="spread-disagree-agree"
        >
          <h3 id="spread-disagree-agree" className="dd-section-label spread-disagree__label">What they agree on</h3>
          <ol className="spread-disagree__list">
            {agree.map((pt, i) => (
              <li key={`agree-${i}`} className="spread-disagree__point">{pt}</li>
            ))}
          </ol>
        </section>
      )}
      {split.length > 0 && (
        <section
          className="spread-disagree__track spread-disagree__track--split"
          aria-labelledby="spread-disagree-split"
        >
          <h3 id="spread-disagree-split" className="dd-section-label spread-disagree__label">Where they split</h3>
          <ol className="spread-disagree__list">
            {split.map((pt, i) => (
              <li key={`split-${i}`} className="spread-disagree__point">{pt}</li>
            ))}
          </ol>
        </section>
      )}
    </aside>
  );
}
