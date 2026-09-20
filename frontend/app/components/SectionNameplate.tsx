"use client";

import Link from "next/link";
import type { CSSProperties } from "react";
import SigilWordmark from "./SigilWordmark";

/* ---------------------------------------------------------------------------
   SectionNameplate — how a SECTION of Void News names itself.

   The brand hierarchy is Void (the parent) -> Void News (a product) -> its
   sections: History, Weekly, On Air, Opinion, Games, Revolt. The
   `VOID [Sigil-O] <WORD>` lockup names a PRODUCT of Void, which is why it fits
   VOID NEWS and would fit VOID VISION. A section that borrows that same lockup
   promotes itself to a sibling of the thing it belongs to, and that is exactly
   what "VOID HISTORY" and "VOID WEEKLY" were doing on their own pages and in
   the news masthead.

   So a section never gets its own lockup. It gets the masterbrand, a hairline,
   and its plain name set in editorial italic in the section's accent:

       VOID [O] NEWS │ History

   Roman small caps for the brand that does not change, italic accent for the
   part that does. The two are the same cap height, so this reads as one
   nameplate rather than two marks competing, and the reader is told where they
   are without being told they have left.

   Two targets, two links: the lockup goes home, the section word goes to the
   section's own front page. Sizing is one `height`, inherited by both halves,
   so a caller scales the whole nameplate with one number and a breakpoint can
   override it in CSS (`.void-nameplate { font-size }`) without a second copy
   of the markup in the DOM.
   --------------------------------------------------------------------------- */

interface SectionNameplateProps {
  /** The section's own name, in plain words: "History", "Weekly". */
  section: string;
  /** Where the section word points. */
  href: string;
  /** Rendered cap height in px, shared by the lockup and the section word. */
  height: number;
  /** The section's accent colour, e.g. var(--palette-history). */
  accent: string;
  className?: string;
}

export default function SectionNameplate({
  section,
  href,
  height,
  accent,
  className,
}: SectionNameplateProps) {
  const style = {
    fontSize: `${height}px`,
    ["--nameplate-accent" as string]: accent,
  } as CSSProperties;

  return (
    <span className={className ? `void-nameplate ${className}` : "void-nameplate"} style={style}>
      <Link href="/" className="void-nameplate__parent" aria-label="Void News home">
        {/* `responsive` so the lockup takes the wrapper's font-size instead of
            baking its own, which is what lets one instance serve every
            breakpoint. */}
        <SigilWordmark product="NEWS" responsive height={height} />
      </Link>
      <span className="void-nameplate__rule" aria-hidden="true" />
      <Link
        href={href}
        className="void-nameplate__section"
        aria-label={`${section}, from Void News`}
      >
        {section}
      </Link>
    </span>
  );
}
