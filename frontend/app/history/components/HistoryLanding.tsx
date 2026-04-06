"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import type { HistoricalEvent, RedactedEvent } from "../types";
import HistoryOverlay from "./HistoryOverlay";

/* ===========================================================================
   HistoryLanding — The Timeline
   Horizontal scroll through time. Cards snap to center. A single CSS custom
   property `--tl-focus` (0-1) drives rack focus, content reveal, and scale.
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
  "ashoka-maurya-empire":
    "He carved the body count into rock for everyone to read: 100,000 killed, 150,000 deported. Then, on the same stone, he said he regretted it.",
  "fall-of-rome":
    "The last emperor was sixteen. The general who deposed him didn\u2019t kill him \u2014 he gave him a pension and mailed the crown to Constantinople.",
  "mali-empire-mansa-musa":
    "Mansa Musa carried 18 tons of gold to Mecca. His charity crashed Egypt\u2019s gold market for twelve years.",
  "the-crusades":
    "The Fourth Crusade never reached Jerusalem. It sacked Constantinople \u2014 the largest Christian city on earth \u2014 instead.",
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
  "ashoka-maurya-empire":
    "The conqueror\u2019s own confession vs. the modern nation that put his symbol on its flag",
  "fall-of-rome":
    "Did it fall or transform? The debate that shaped how the West thinks about collapse",
  "mali-empire-mansa-musa":
    "European maps vs. oral tradition \u2014 two records of Africa\u2019s wealthiest empire",
  "the-crusades":
    "Jerusalem 1099 vs. Jerusalem 1187 \u2014 the massacre and the mercy, side by side",
};

/* ── Perspective color map ── */
const PERSP_COLORS: Record<string, string> = {
  a: "var(--hist-persp-a)",
  b: "var(--hist-persp-b)",
  c: "var(--hist-persp-c)",
  d: "var(--hist-persp-d)",
  e: "var(--hist-persp-e)",
};

/* ── Severity → CSS modifier ── */
const SEVERITY_CLASS: Record<string, string> = {
  catastrophic: "hist-tl-card--catastrophic",
  critical: "hist-tl-card--critical",
  major: "hist-tl-card--major",
};

/* ── Extract year from YYYYMMDD dateSort ── */
function extractYear(dateSort: number, datePrimary: string): string {
  const s = String(dateSort);
  if (s.length >= 4) return s.slice(0, 4);
  const match = datePrimary.match(/\d{4}/);
  return match ? match[0] : "";
}

/* ===========================================================================
   PosterImage — Robust fallback chain
   heroImage -> media[0].url -> media[1].url -> ... -> cinematic gradient
   =========================================================================== */
function PosterImage({ event, eager }: { event: HistoricalEvent; eager?: boolean }) {
  const fallbackUrls = useMemo(() => {
    const urls: string[] = [];
    if (event.heroImage) urls.push(event.heroImage);
    event.media.forEach((m) => {
      if (m.url && m.type === "image") urls.push(m.url);
    });
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
    return <div className="hist-tl-card__photo-fallback" aria-hidden="true" />;
  }

  return (
    <img
      src={fallbackUrls[currentIndex]}
      alt={event.heroCaption || event.title}
      loading={eager ? "eager" : "lazy"}
      className="hist-tl-card__photo-img"
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
  const containerRef = useRef<HTMLDivElement>(null);
  const cardRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [focusedIndex, setFocusedIndex] = useState(0);
  const [hasScrolled, setHasScrolled] = useState(false);
  const [activeOverlay, setActiveOverlay] = useState<{
    event: HistoricalEvent;
    sourceRect: DOMRect | null;
  } | null>(null);

  /* Merge events + classified into one timeline (classified at end) */
  const allItems = useMemo(() => {
    const sorted = [...events].sort((a, b) => a.dateSort - b.dateSort);
    return { events: sorted, redacted };
  }, [events, redacted]);

  const totalCards = allItems.events.length + allItems.redacted.length;

  /* ── Scroll listener: update --tl-focus on every card ── */
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let rafId: number;
    const updateFocus = () => {
      const containerRect = container.getBoundingClientRect();
      const centerX = containerRect.left + containerRect.width / 2;
      let closestIndex = 0;
      let closestDist = Infinity;

      cardRefs.current.forEach((cardEl, i) => {
        if (!cardEl) return;
        const cardRect = cardEl.getBoundingClientRect();
        const cardCenterX = cardRect.left + cardRect.width / 2;
        const dist = Math.abs(cardCenterX - centerX);
        const maxDist = containerRect.width * 0.8;
        const t = Math.min(dist / maxDist, 1);
        cardEl.style.setProperty("--tl-focus", (1 - t).toFixed(3));

        if (dist < closestDist) {
          closestDist = dist;
          closestIndex = i;
        }
      });

      setFocusedIndex(closestIndex);
    };

    const onScroll = () => {
      if (!hasScrolled) setHasScrolled(true);
      cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(updateFocus);
    };

    container.addEventListener("scroll", onScroll, { passive: true });
    updateFocus(); // initial calculation
    return () => {
      container.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(rafId);
    };
  }, [allItems.events, allItems.redacted, hasScrolled]);

  /* ── Vertical wheel -> horizontal scroll ── */
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const handleWheel = (e: WheelEvent) => {
      if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
        e.preventDefault();
        container.scrollLeft += e.deltaY;
      }
    };

    container.addEventListener("wheel", handleWheel, { passive: false });
    return () => container.removeEventListener("wheel", handleWheel);
  }, []);

  /* ── Smooth scroll to card by index ── */
  const scrollToCard = useCallback(
    (index: number) => {
      const el = cardRefs.current[index];
      if (el) {
        el.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
          inline: "center",
        });
      }
    },
    []
  );

  /* ── Keyboard: arrow keys, Home, End ── */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowRight") {
        e.preventDefault();
        scrollToCard(Math.min(focusedIndex + 1, totalCards - 1));
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        scrollToCard(Math.max(focusedIndex - 1, 0));
      } else if (e.key === "Home") {
        e.preventDefault();
        scrollToCard(0);
      } else if (e.key === "End") {
        e.preventDefault();
        scrollToCard(totalCards - 1);
      }
    },
    [focusedIndex, totalCards, scrollToCard]
  );

  /* ── Open story overlay ── */
  const openStory = useCallback(
    (event: HistoricalEvent, cardIndex: number) => {
      const photoEl = cardRefs.current[cardIndex]?.querySelector<HTMLElement>(
        ".hist-tl-card__photo"
      );
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
    <div className="hist-tl-wrapper">
      {/* ── Mission Brief — fades on first scroll ── */}
      <div
        className={`hist-tl-brief ${hasScrolled ? "hist-tl-brief--hidden" : ""}`}
        aria-hidden={hasScrolled}
      >
        <p className="hist-tl-brief__text">
          One event. Every side. Decide for yourself.
        </p>
        <span className="hist-tl-brief__hint">&larr; scroll through time &rarr;</span>
      </div>

      {/* ── Horizontal timeline scroller ── */}
      {/* eslint-disable-next-line jsx-a11y/no-static-element-interactions */}
      <div
        ref={containerRef}
        className="hist-tl-landing hist-grade"
        role="region"
        aria-label="Historical events timeline"
        aria-roledescription="timeline"
        tabIndex={0}
        onKeyDown={handleKeyDown}
      >
        {/* ── Event cards ── */}
        {allItems.events.map((event, i) => (
          <TimelineCard
            key={event.slug}
            ref={(el) => { cardRefs.current[i] = el; }}
            event={event}
            index={i}
            onOpen={openStory}
          />
        ))}

        {/* ── Classified cards ── */}
        {allItems.redacted.map((event, i) => {
          const idx = allItems.events.length + i;
          return (
            <ClassifiedCard
              key={event.slug}
              ref={(el) => { cardRefs.current[idx] = el; }}
              event={event}
              index={idx}
            />
          );
        })}
      </div>

      {/* ── Timeline track (minimap) ── */}
      <nav className="hist-tl-track" aria-label="Timeline navigation">
        <div className="hist-tl-track__line" aria-hidden="true" />
        {allItems.events.map((event, i) => (
          <button
            key={event.slug}
            className={`hist-tl-track__dot ${
              i === focusedIndex ? "hist-tl-track__dot--active" : ""
            }`}
            style={{
              left: `${5 + (totalCards > 1 ? (i / (totalCards - 1)) * 90 : 45)}%`,
            }}
            onClick={() => scrollToCard(i)}
            aria-label={`${event.title} (${event.datePrimary})`}
            type="button"
          >
            <span className="hist-tl-track__year">
              {extractYear(event.dateSort, event.datePrimary)}
            </span>
          </button>
        ))}
        {allItems.redacted.map((event, i) => {
          const idx = allItems.events.length + i;
          return (
            <button
              key={event.slug}
              className={`hist-tl-track__dot hist-tl-track__dot--classified ${
                idx === focusedIndex ? "hist-tl-track__dot--active" : ""
              }`}
              style={{
                left: `${5 + (totalCards > 1 ? (idx / (totalCards - 1)) * 90 : 45)}%`,
              }}
              onClick={() => scrollToCard(idx)}
              aria-label={`Coming: ${event.title}`}
              type="button"
            >
              <span className="hist-tl-track__year">?</span>
            </button>
          );
        })}
      </nav>

      {/* ── Story Overlay ── */}
      {activeOverlay && (
        <HistoryOverlay
          event={activeOverlay.event}
          allEvents={allItems.events}
          sourceRect={activeOverlay.sourceRect}
          onClose={closeOverlay}
        />
      )}
    </div>
  );
}

/* ===========================================================================
   TimelineCard — A single event in the horizontal timeline
   Rack focus driven by --tl-focus. Photo + date + title always visible.
   Hook, dots, CTA revealed when focused (--tl-focus > 0.65).
   =========================================================================== */
import { forwardRef } from "react";

const TimelineCard = forwardRef<
  HTMLDivElement,
  {
    event: HistoricalEvent;
    index: number;
    onOpen: (event: HistoricalEvent, cardIndex: number) => void;
  }
>(function TimelineCard({ event, index, onOpen }, ref) {
  const hook =
    HOOKS[event.slug] ||
    event.contextNarrative.split(". ").slice(0, 2).join(". ") + ".";

  const cta =
    CTAS[event.slug] ||
    `Explore ${event.perspectives.length} accounts of ${event.title}`;

  const handleClick = useCallback(() => {
    onOpen(event, index);
  }, [event, index, onOpen]);

  const severityClass = SEVERITY_CLASS[event.severity] || "";

  return (
    <article
      ref={ref}
      className={`hist-tl-card ${severityClass}`}
      style={{ "--tl-focus": "0.5" } as React.CSSProperties}
      data-slug={event.slug}
    >
      {/* Photo -- always visible, Ken Burns when focused */}
      <div className="hist-tl-card__photo">
        <PosterImage event={event} eager={index === 0} />
      </div>

      {/* Body content */}
      <div className="hist-tl-card__body">
        {/* Always visible: date + title */}
        <span className="hist-tl-card__date">{event.datePrimary}</span>
        <h3 className="hist-tl-card__title">{event.title}</h3>

        {/* Revealed when focused */}
        <blockquote className="hist-tl-card__hook">{hook}</blockquote>

        <div
          className="hist-tl-card__dots"
          aria-label={`${event.perspectives.length} perspectives`}
        >
          {event.perspectives.map((p) => (
            <span
              key={p.id}
              className="hist-tl-card__dot"
              style={{
                background: PERSP_COLORS[p.color] || PERSP_COLORS.a,
              }}
              title={p.viewpointName}
              aria-hidden="true"
            />
          ))}
        </div>

        <button
          className="hist-tl-card__cta"
          onClick={handleClick}
          type="button"
        >
          <span className="hist-tl-card__cta-text">{cta}</span>
          <span className="hist-tl-card__cta-arrow" aria-hidden="true">
            &rarr;
          </span>
        </button>
      </div>

      {/* Severity accent */}
      <div className="hist-tl-card__severity" aria-hidden="true" />
    </article>
  );
});

/* ===========================================================================
   ClassifiedCard — Desaturated, redacted text, click-to-flip
   Same --tl-focus system, plus dashed border + desaturation
   =========================================================================== */
const ClassifiedCard = forwardRef<
  HTMLDivElement,
  {
    event: RedactedEvent;
    index: number;
  }
>(function ClassifiedCard({ event, index }, ref) {
  const [revealed, setRevealed] = useState(false);

  return (
    <div
      ref={ref}
      className={`hist-tl-card hist-tl-card--classified ${
        revealed ? "hist-tl-card--classified-revealed" : ""
      }`}
      style={{ "--tl-focus": "0.5" } as React.CSSProperties}
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
      data-index={index}
    >
      <div className="hist-tl-card__body">
        {/* Redacted title */}
        <h3 className="hist-tl-card__title">
          {event.title.split(" ")[0]}{" "}
          <span className="hist-tl-card--classified__redacted">
            {event.title
              .split(" ")
              .slice(1)
              .map((w) => "\u2588".repeat(w.length))
              .join(" ")}
          </span>
        </h3>

        {/* Contradictory quotes */}
        {event.quoteA && (
          <p className="hist-tl-card--classified__quote">{event.quoteA}</p>
        )}
        {event.quoteB && (
          <p className="hist-tl-card--classified__quote hist-tl-card--classified__quote-b">
            {event.quoteB}
          </p>
        )}

        {/* Date hint + badge */}
        <div className="hist-tl-card--classified__meta">
          <span className="hist-tl-card--classified__date">
            {event.dateHint}
          </span>
          <span className="hist-tl-card--classified__badge">COMING</span>
        </div>
      </div>

      {/* Reveal overlay */}
      <div
        className="hist-tl-card--classified__reveal"
        aria-hidden={!revealed}
      >
        <span className="hist-tl-card--classified__reveal-title">
          {event.title}
        </span>
        <span className="hist-tl-card--classified__reveal-hint">
          Coming soon
        </span>
      </div>
    </div>
  );
});
