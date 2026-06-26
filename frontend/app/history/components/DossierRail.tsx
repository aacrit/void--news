"use client";

import Link from "next/link";
import type { HistoricalEvent, EventConnection } from "../types";

/* ===========================================================================
   DossierRail — At-a-glance record.
   Date, location, toll, key figures, and parallel/consequence threads.
   Sticky right rail on desktop (facts always in view while the account
   scrolls); a compact card near the top on mobile. Pulls the dense factual
   ledger off the vertical reading flow.
   =========================================================================== */

interface DossierRailProps {
  event: HistoricalEvent;
  sidebarConnections: EventConnection[];
  allEvents: HistoricalEvent[];
}

/* Format year for Key Figures: <=0 = BCE */
const fmtYear = (y: number) =>
  y <= 0 ? `${Math.abs(y) + (y === 0 ? 1 : 0)} BCE` : String(y);

export default function DossierRail({
  event,
  sidebarConnections,
  allEvents,
}: DossierRailProps) {
  const facts: { label: string; value: string }[] = [
    { label: "Date", value: event.dateRange || event.datePrimary },
    { label: "Location", value: event.location },
    ...(event.duration ? [{ label: "Duration", value: event.duration }] : []),
    ...(event.deathToll && event.deathToll !== "N/A"
      ? [{ label: "Killed", value: event.deathToll }]
      : []),
    ...(event.displaced && event.displaced !== "N/A"
      ? [{ label: "Displaced", value: event.displaced }]
      : []),
  ].filter((f) => f.value);

  const threads = sidebarConnections.map((conn) => {
    const linked = allEvents.find((e) => e.slug === conn.targetSlug);
    return {
      slug: conn.targetSlug,
      title: conn.targetTitle,
      year: linked?.datePrimary ?? "",
      description: conn.description.split(". ")[0] + ".",
    };
  });

  return (
    <aside className="hist-rail" aria-label="The record">
      {/* Facts ledger */}
      <section className="hist-rail__block">
        <span className="hist-rail__eyebrow">The Record</span>
        <dl className="hist-rail__ledger">
          {facts.map((f) => (
            <div key={f.label} className="hist-rail__row">
              <dt>{f.label}</dt>
              <dd>{f.value}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* Key figures */}
      {event.keyFigures.length > 0 && (
        <section className="hist-rail__block">
          <span className="hist-rail__eyebrow">Key Figures</span>
          <ul className="hist-rail__figures">
            {event.keyFigures.map((fig, i) => {
              const hasDates = fig.born != null || fig.died != null;
              const dates = hasDates
                ? `${fig.born != null ? fmtYear(fig.born) : "?"}–${
                    fig.died != null ? fmtYear(fig.died) : "?"
                  }`
                : null;
              return (
                <li key={i} className="hist-rail__figure">
                  <span className="hist-rail__figure-head">
                    {fig.wikipedia ? (
                      <a
                        href={fig.wikipedia}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hist-rail__figure-name"
                        aria-label={`${fig.name} on Wikipedia (opens in new tab)`}
                      >
                        {fig.name}
                      </a>
                    ) : (
                      <span className="hist-rail__figure-name">{fig.name}</span>
                    )}
                    {dates && (
                      <span className="hist-rail__figure-dates">{dates}</span>
                    )}
                  </span>
                  <span className="hist-rail__figure-role">{fig.role}</span>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      {/* Elsewhere, meanwhile */}
      {threads.length > 0 && (
        <section className="hist-rail__block">
          <span className="hist-rail__eyebrow">Elsewhere, Meanwhile</span>
          <ul className="hist-rail__threads">
            {threads.map((t) => (
              <li key={t.slug} className="hist-rail__thread">
                <span className="hist-rail__thread-year">{t.year}</span>
                <Link
                  href={`/history/${t.slug}`}
                  className="hist-rail__thread-title"
                >
                  {t.title}
                </Link>
                <p className="hist-rail__thread-desc">{t.description}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </aside>
  );
}
