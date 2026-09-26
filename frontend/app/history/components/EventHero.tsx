import type { HistoricalEvent } from "../types";
import HeroListen from "./HeroListen";

/* ===========================================================================
   EventHero — the hero both page kinds share.

   Image (an exhibit, never stock), date, title, subtitle, Listen. The
   Hearing rendered this inline; the Thesis needs the same hero, so it lives
   here once and the two pages sit in one catalogue without a seam. Server
   markup except the Listen island, exactly as before.
   =========================================================================== */

export const HERO_ID = "hearing-hero";

export default function EventHero({ event }: { event: HistoricalEvent }) {
  return (
    <section className="hist-stage hist-stage--scene" id={HERO_ID}>
      <div
        className="hist-stage__hero"
        style={event.heroImage ? { backgroundImage: `url(${event.heroImage})` } : undefined}
      >
        {!event.heroImage && <div className="hist-stage__hero-fallback" />}
        <div className="hist-stage__hero-overlay" />
        <div className="hist-stage__hero-content">
          <span className="hist-stage__date">{event.datePrimary}</span>
          <h1 className="hist-stage__title">{event.title}</h1>
          {event.subtitle && <p className="hist-stage__subtitle">{event.subtitle}</p>}
          {event.audioUrl ? (
            <HeroListen
              id={event.id}
              title={event.title}
              subtitle={event.subtitle}
              audioUrl={event.audioUrl}
              durationSeconds={event.audioDuration ?? 0}
              chapters={event.audioChapters ?? null}
              accountCount={event.perspectives.length}
            />
          ) : (
            <p className="hist-hero-pending">
              <svg
                width="14"
                height="10"
                viewBox="0 0 14 10"
                aria-hidden="true"
                focusable="false"
                className="hist-hero-pending__icon"
              >
                <g fill="currentColor">
                  <rect x="0" y="4" width="1.5" height="2" rx="0.75" />
                  <rect x="3" y="3" width="1.5" height="4" rx="0.75" />
                  <rect x="6" y="4" width="1.5" height="2" rx="0.75" />
                  <rect x="9" y="3" width="1.5" height="4" rx="0.75" />
                  <rect x="12" y="4" width="1.5" height="2" rx="0.75" />
                </g>
              </svg>
              <span>Audio edition in production</span>
            </p>
          )}
        </div>
        {event.heroAttribution && (
          <span className="hist-stage__attribution">{event.heroAttribution}</span>
        )}
      </div>
    </section>
  );
}
