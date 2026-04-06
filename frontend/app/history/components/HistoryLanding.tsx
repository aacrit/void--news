"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import type { HistoricalEvent, RedactedEvent } from "../types";
import HistoryOverlay from "./HistoryOverlay";

/* ===========================================================================
   HistoryLanding — The Corridor
   Museum corridor. Events are spotlit exhibits in dim surroundings.
   Continuous vertical scroll with atmospheric fog between events.
   Cardinal rules: Show Not Tell. Arrive Late, Leave Early.
   =========================================================================== */

/* ── Hooks — story-specific, "Arrive Late, Leave Early" ── */
const HOOKS: Record<string, string> = {
  "partition-of-india":
    "A lawyer who\u2019d never been to India drew the border in five weeks. 15 million crossed it.",
  "hiroshima-nagasaki":
    "66,000 dead in 8.5 seconds. Seven of eight five-star American generals said it wasn\u2019t necessary.",
  "rwandan-genocide":
    "The UN had a fax warning them. They reduced their force from 2,500 to 270. 800,000 died in 100 days.",
  "scramble-for-africa":
    "Fourteen nations met in a Berlin conference room in 1884. Not one African was invited. By 1914, Europeans controlled 90% of the continent.",
  "opium-wars":
    "Britain went to war because China burned 20,000 chests of opium. The peace treaty ceded Hong Kong for 156 years.",
  "french-revolution":
    "A Parisian laborer spent 88% of his wages on bread. On July 14, the crowd took 30,000 muskets. The Bastille fell by dinner.",
  "creation-of-israel-nakba":
    "On May 14, 1948, one people declared independence. On May 15, 750,000 of another people became refugees. Same land.",
  "trail-of-tears":
    "The Supreme Court ruled in their favor. The president ignored the ruling. 60,000 walked. 4,000 never arrived.",
  "fall-of-berlin-wall":
    "At 6:53 p.m. on November 9, 1989, a spokesman misread a memo on live television. The Wall fell by midnight.",
  "transatlantic-slave-trade":
    "12.5 million embarked. 10.7 million survived the crossing. The database lists 36,000 individual voyages.",
  "armenian-genocide":
    "The American ambassador cabled Washington: \u2018Race extermination.\u2019 Raphael Lemkin later coined a word for it \u2014 \u2018genocide.\u2019",
  "holodomor":
    "Gareth Jones walked through Ukrainian villages counting bodies. Walter Duranty won a Pulitzer for saying there was no famine.",
  "congo-free-state":
    "Leopold II never visited the Congo. His agents collected severed hands as proof of productivity. The population fell by 10 million.",
  "cambodian-genocide":
    "Tuol Sleng processed 17,000 prisoners. Seven survived. The guards photographed every face before killing them.",
  "tiananmen-square":
    "On June 5, 1989, a man with two shopping bags stopped a column of tanks. No one knows his name. China erased the photograph.",
  "peloponnesian-war":
    "Athens told the island of Melos: submit or die. Melos chose neutrality. Athens killed every man and enslaved the women and children.",
  "mongol-conquest-baghdad":
    "The Tigris ran black with ink from a million manuscripts. Then Hulagu built the world\u2019s finest observatory with the looted books.",
  "haitian-revolution":
    "Dessalines tore the white from the French tricolor. The flag that remained was the first made by formerly enslaved people who\u2019d defeated a European army.",
  "meiji-restoration":
    "Japan watched China lose two wars to Britain. In 30 years, a feudal archipelago built railways, a constitution, and a navy that sank the Russian fleet.",
  "treaty-of-waitangi":
    "The English text said \u2018sovereignty.\u2019 The Maori text said \u2018governance.\u2019 Hone Heke cut down the British flagpole four times to make the point.",
  "bolivarian-revolutions":
    "Bol\u00edvar sailed to Haiti after his defeat. P\u00e9tion gave him ships and soldiers in exchange for one promise: free the enslaved. Bol\u00edvar partially broke it.",
};

/* ── CTAs — story-specific ── */
const CTAS: Record<string, string> = {
  "partition-of-india": "See how 4 nations remember August 15, 1947",
  "hiroshima-nagasaki":
    "Compare what Washington said vs. what survivors remember",
  "rwandan-genocide":
    "Read what the world chose not to see for 100 days",
  "scramble-for-africa":
    "See what the colonizers wrote vs. what the kingdoms remember",
  "opium-wars":
    "Compare the British free-trade argument with the Qing court\u2019s response",
  "french-revolution":
    "Read the revolution from Paris, Versailles, and Haiti",
  "creation-of-israel-nakba":
    "Same day, same land \u2014 read both declarations side by side",
  "trail-of-tears":
    "The court said no. The president said yes. Read both arguments",
  "fall-of-berlin-wall":
    "Compare what East and West saw on the same night",
  "transatlantic-slave-trade":
    "Ledger entries vs. survivor testimony \u2014 two records of the same voyage",
  "armenian-genocide":
    "The ambassador\u2019s cables vs. the government\u2019s denials",
  "holodomor":
    "One journalist told the truth. Another won a Pulitzer for lying. Read both",
  "congo-free-state":
    "Leopold\u2019s civilizing mission vs. the photographs of severed hands",
  "cambodian-genocide":
    "The regime\u2019s ideology vs. the faces in the S-21 photographs",
  "tiananmen-square":
    "The party\u2019s version vs. what the cameras recorded before the signal cut",
  "peloponnesian-war":
    "Thucydides put words in both mouths. Read what Athens said to Melos",
  "mongol-conquest-baghdad":
    "Destroyer or globalizer? Two accounts of what happened to the library",
  "haitian-revolution":
    "The enslaved who defeated Napoleon \u2014 told by 4 sides",
  "meiji-restoration":
    "How Japan avoided China\u2019s fate \u2014 reformers vs. the last samurai",
  "treaty-of-waitangi":
    "Two texts, two languages, two meanings. Read both treaties",
  "bolivarian-revolutions":
    "The liberator\u2019s promise to Haiti vs. what he actually delivered",
};

/* ── Perspective color map ── */
const PERSP_COLORS: Record<string, string> = {
  a: "var(--hist-persp-a)",
  b: "var(--hist-persp-b)",
  c: "var(--hist-persp-c)",
  d: "var(--hist-persp-d)",
  e: "var(--hist-persp-e)",
};

/* ── Severity → CSS class + color ── */
const SEVERITY_CLASS: Record<string, string> = {
  catastrophic: "hist-poster--catastrophic",
  critical: "hist-poster--critical",
  major: "hist-poster--major",
};

/* ===========================================================================
   PosterImage — Robust fallback chain
   heroImage → media[0].url → media[1].url → … → cinematic gradient
   =========================================================================== */
function PosterImage({ event, eager }: { event: HistoricalEvent; eager?: boolean }) {
  const fallbackUrls = useMemo(() => {
    const urls: string[] = [];
    if (event.heroImage) urls.push(event.heroImage);
    event.media.forEach((m) => {
      if (m.url && m.type === "image") urls.push(m.url);
    });
    // Also include maps/documents as last resort before gradient
    event.media.forEach((m) => {
      if (m.url && m.type !== "image" && !urls.includes(m.url)) urls.push(m.url);
    });
    return urls;
  }, [event.heroImage, event.media]);

  const [currentIndex, setCurrentIndex] = useState(0);
  const [allFailed, setAllFailed] = useState(fallbackUrls.length === 0);

  const handleError = useCallback(() => {
    const nextIdx = currentIndex + 1;
    if (nextIdx < fallbackUrls.length) {
      setCurrentIndex(nextIdx);
    } else {
      setAllFailed(true);
    }
  }, [currentIndex, fallbackUrls.length]);

  if (allFailed) {
    return <div className="hist-poster__photo-fallback" aria-hidden="true" />;
  }

  return (
    <img
      src={fallbackUrls[currentIndex]}
      alt={event.heroCaption || event.title}
      loading={eager ? "eager" : "lazy"}
      className="hist-poster__photo-img"
      onError={handleError}
    />
  );
}

/* ── Props ── */
interface HistoryLandingProps {
  events: HistoricalEvent[];
  redacted: RedactedEvent[];
}

export default function HistoryLanding({
  events,
  redacted,
}: HistoryLandingProps) {
  const corridorRef = useRef<HTMLDivElement>(null);
  const [activeOverlay, setActiveOverlay] = useState<{
    event: HistoricalEvent;
    sourceRect: DOMRect | null;
  } | null>(null);

  /* ── Scroll cinematography: poster reveal via IntersectionObserver ── */
  useEffect(() => {
    const posters = corridorRef.current?.querySelectorAll(".hist-poster");
    if (!posters || posters.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("hist-poster--visible");
          }
        });
      },
      { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
    );

    posters.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [events]);

  /* ── Classified tile reveal observer ── */
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("hist-reveal--visible");
          }
        });
      },
      { threshold: 0.05, rootMargin: "0px 0px -30px 0px" }
    );
    const tiles = corridorRef.current?.querySelectorAll(".hist-classified-tile");
    tiles?.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [redacted]);

  /* ── Open story overlay ── */
  const openStory = useCallback(
    (event: HistoricalEvent, photoEl: HTMLElement | null) => {
      const rect = photoEl?.getBoundingClientRect() ?? null;
      setActiveOverlay({ event, sourceRect: rect });
    },
    []
  );

  /* ── Close overlay ── */
  const closeOverlay = useCallback(() => {
    setActiveOverlay(null);
  }, []);

  return (
    <div>
      <div ref={corridorRef} className="hist-corridor hist-grade">
        {/* ── Mission Brief — one line, cold open ── */}
        <header className="hist-brief" aria-label="Archive mission brief">
          <p className="hist-brief__line">
            One event. Every side. Decide for yourself.
          </p>
        </header>

        {/* ── Fog zone after brief ── */}
        <div className="hist-fog" aria-hidden="true" />

        {/* ── Event Posters ── */}
        {events.map((event, i) => (
          <div key={event.slug}>
            <EventPoster
              event={event}
              index={i}
              onOpen={openStory}
            />
            {/* Fog zone between events (not after the last) */}
            {i < events.length - 1 && (
              <div className="hist-fog" aria-hidden="true" />
            )}
          </div>
        ))}

        {/* ── Classified Section ── */}
        {redacted.length > 0 && (
          <>
            <div className="hist-fog" aria-hidden="true" />
            <div className="hist-classified-divider">
              <span className="hist-classified-divider__line" aria-hidden="true" />
              <span className="hist-classified-divider__label">
                CLASSIFIED — PENDING DECLASSIFICATION
              </span>
              <span className="hist-classified-divider__line" aria-hidden="true" />
            </div>

            <section
              className="hist-classified-feed"
              aria-label="Classified upcoming event dossiers"
            >
              {redacted.map((event, i) => (
                <ClassifiedTile key={event.slug} event={event} index={i} />
              ))}
            </section>
          </>
        )}
      </div>

      {/* ── Story Overlay ── */}
      {activeOverlay && (
        <HistoryOverlay
          event={activeOverlay.event}
          allEvents={events}
          sourceRect={activeOverlay.sourceRect}
          onClose={closeOverlay}
        />
      )}
    </div>
  );
}

/* ===========================================================================
   EventPoster — Full-width spotlit exhibit (cinematic v2)
   Archival photo (Ken Burns drift + accelerated hover), date + title,
   THE HOOK, perspective names (hover-reveal desktop, always-visible mobile),
   stark data line (death toll + displaced), story-specific CTA with arrow.
   =========================================================================== */
function EventPoster({
  event,
  index,
  onOpen,
}: {
  event: HistoricalEvent;
  index: number;
  onOpen: (event: HistoricalEvent, photoEl: HTMLElement | null) => void;
}) {
  const photoRef = useRef<HTMLDivElement>(null);

  const hook =
    HOOKS[event.slug] ||
    event.contextNarrative.split(". ").slice(0, 2).join(". ") + ".";

  const cta =
    CTAS[event.slug] ||
    `Explore ${event.perspectives.length} accounts of ${event.title}`;

  const handleClick = useCallback(() => {
    onOpen(event, photoRef.current);
  }, [event, onOpen]);

  /* Build stark data line from deathToll + displaced */
  const starkParts: string[] = [];
  if (event.deathToll) starkParts.push(`${event.deathToll} killed`);
  if (event.displaced) starkParts.push(`${event.displaced} displaced`);
  const starkLine = starkParts.join(" \u00b7 ");

  const severityClass = SEVERITY_CLASS[event.severity] || "";

  return (
    <article
      className={`hist-poster ${severityClass}`}
      data-slug={event.slug}
      style={{ transitionDelay: index === 0 ? "300ms" : undefined }}
    >
      {/* 1. Full-width archival photo — PosterImage with fallback chain */}
      <div
        ref={photoRef}
        className="hist-poster__photo"
        data-slug={event.slug}
      >
        <PosterImage event={event} eager={index === 0} />
      </div>

      {/* 2. Date + Title */}
      <div className="hist-poster__body">
        <span className="hist-poster__date">{event.datePrimary}</span>
        <h3 className="hist-poster__title">{event.title}</h3>

        {/* 3. THE HOOK — the most important line */}
        <blockquote className="hist-poster__hook">{hook}</blockquote>

        {/* 4. Perspective dots — colored circles, no names at rest */}
        <div className="hist-poster__dots" aria-label={`${event.perspectives.length} perspectives`}>
          {event.perspectives.map((p) => (
            <span
              key={p.id}
              className="hist-poster__dot"
              style={{ background: PERSP_COLORS[p.color] || PERSP_COLORS.a }}
              aria-hidden="true"
            />
          ))}
        </div>

        {/* 5. Hover-reveal: perspective names + stark data */}
        <div className="hist-poster__hover-content" aria-hidden="false">
          {/* Perspective names — staggered reveal */}
          <div className="hist-poster__perspectives">
            {event.perspectives.map((p) => (
              <span
                key={p.id}
                className="hist-poster__persp-name"
                style={{ color: PERSP_COLORS[p.color] || PERSP_COLORS.a }}
              >
                <span className="hist-poster__persp-bullet" aria-hidden="true">&#9679;</span>
                {" "}{p.viewpointName}
              </span>
            ))}
          </div>

          {/* Stark data line — death toll + displaced */}
          {starkLine && (
            <p className="hist-poster__stark">{starkLine}</p>
          )}
        </div>

        {/* 6. CTA — story-specific, with arrow */}
        <button
          className="hist-poster__cta"
          onClick={handleClick}
          type="button"
        >
          <span className="hist-poster__cta-text">{cta}</span>
          <span className="hist-poster__cta-arrow" aria-hidden="true">&rarr;</span>
        </button>
      </div>
    </article>
  );
}

/* ===========================================================================
   ClassifiedTile — Desaturated, redacted text, click-to-flip
   =========================================================================== */
function ClassifiedTile({
  event,
  index,
}: {
  event: RedactedEvent;
  index: number;
}) {
  const [revealed, setRevealed] = useState(false);

  return (
    <div
      className={`hist-classified-tile hist-reveal ${revealed ? "hist-classified-tile--revealed" : ""}`}
      style={{ animationDelay: `${100 + index * 80}ms` }}
      role="button"
      tabIndex={0}
      onClick={() => setRevealed((p) => !p)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          setRevealed((p) => !p);
        }
      }}
      aria-label={`Coming: ${event.title}`}
      aria-pressed={revealed}
    >
      {/* Redacted title */}
      <h3 className="hist-classified-tile__title">
        {event.title.split(" ")[0]}{" "}
        <span className="hist-classified-tile__redacted">
          {event.title
            .split(" ")
            .slice(1)
            .map((w) => "\u2588".repeat(w.length))
            .join(" ")}
        </span>
      </h3>

      {/* Contradictory quotes */}
      {event.quoteA && (
        <p className="hist-classified-tile__quote">{event.quoteA}</p>
      )}
      {event.quoteB && (
        <p className="hist-classified-tile__quote hist-classified-tile__quote--b">
          {event.quoteB}
        </p>
      )}

      {/* Date hint + badge */}
      <div className="hist-classified-tile__meta">
        <span className="hist-classified-tile__date">{event.dateHint}</span>
        <span className="hist-classified-tile__badge">COMING</span>
      </div>

      {/* Reveal overlay */}
      <div className="hist-classified-tile__reveal" aria-hidden={!revealed}>
        <span className="hist-classified-tile__reveal-title">
          {event.title}
        </span>
        <span className="hist-classified-tile__reveal-hint">Coming soon</span>
      </div>
    </div>
  );
}
