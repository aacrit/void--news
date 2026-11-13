/* DEFERRED: Not rendered in current version. Preserved for Phase 2. */
"use client";

import { useState } from "react";
import type { RedactedEvent } from "../types";

/* ===========================================================================
   RedactedDossier — "Coming" card for unpopulated events
   Foxing texture, redaction bars, two contradictory perspective quotes,
   "[DECLASSIFIED: COMING]" stamp. Hover reveals event title behind
   lifting redaction. Click toggles reveal on touch devices.
   =========================================================================== */

interface RedactedDossierProps {
  event: RedactedEvent;
}

export default function RedactedDossier({ event }: RedactedDossierProps) {
  const [touchRevealed, setTouchRevealed] = useState(false);

  return (
    <div
      className={`hist-redacted ${touchRevealed ? "hist-redacted--revealed" : ""}`}
      aria-label={`Coming: ${event.title}`}
      role="button"
      tabIndex={0}
      onClick={() => setTouchRevealed((prev) => !prev)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          setTouchRevealed((prev) => !prev);
        }
      }}
    >
      {/* Title */}
      <h3 className="hist-redacted__title">
        {/* Partially redacted title — show first word, redact rest */}
        {event.title.split(" ")[0]}{" "}
        <span style={{ opacity: 0.15 }}>
          {event.title
            .split(" ")
            .slice(1)
            .map((w) => "\u2588".repeat(w.length))
            .join(" ")}
        </span>
      </h3>

      {/* Date hint */}
      <span className="hist-redacted__date">{event.dateHint}</span>

      {/* Redaction bars */}
      <span className="hist-redacted__bar hist-redacted__bar--long" aria-hidden="true" />
      <span className="hist-redacted__bar hist-redacted__bar--medium" aria-hidden="true" />
      <span className="hist-redacted__bar hist-redacted__bar--short" aria-hidden="true" />

      {/* Contradictory quotes */}
      <div className="hist-redacted__quotes">
        {event.quoteA && (
          <p className="hist-redacted__quote">{event.quoteA}</p>
        )}
        {event.quoteB && (
          <p className="hist-redacted__quote">{event.quoteB}</p>
        )}
      </div>

      {/* Stamp */}
      <span className="hist-redacted__stamp">[Declassified: Coming]</span>

      {/* Hover reveal (desktop) + click reveal (touch) */}
      <div className="hist-redacted__reveal" aria-hidden="true">
        <span className="hist-redacted__reveal-title">{event.title}</span>
      </div>
    </div>
  );
}
