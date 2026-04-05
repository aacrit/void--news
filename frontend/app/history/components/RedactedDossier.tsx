"use client";

import type { RedactedEvent } from "../types";

/* ===========================================================================
   RedactedDossier — "Coming" card for unpopulated events
   Foxing texture, redaction bars, two contradictory perspective quotes,
   "[DECLASSIFIED: COMING]" stamp. Hover reveals event title behind
   lifting redaction.
   =========================================================================== */

interface RedactedDossierProps {
  event: RedactedEvent;
}

export default function RedactedDossier({ event }: RedactedDossierProps) {
  return (
    <div className="hist-redacted" aria-label={`Coming: ${event.title}`}>
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

      {/* Hover reveal */}
      <div className="hist-redacted__reveal" aria-hidden="true">
        <span className="hist-redacted__reveal-title">{event.title}</span>
      </div>
    </div>
  );
}
