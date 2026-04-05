"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import type { HistoricalEvent } from "../types";
import { ERAS, REGIONS } from "../types";
import KeyFacts from "./KeyFacts";
import MediaGallery from "./MediaGallery";
import PerspectiveSelector from "./PerspectiveSelector";
import PerspectiveView from "./PerspectiveView";
import PerspectiveComparison from "./PerspectiveComparison";
import CompactTimeline from "./CompactTimeline";

/* ===========================================================================
   EventDetail — The core event detail component
   Static hero with archival grade. Title card overlay.
   Perspectives (THE PRODUCT) immediately after hero.
   Collapsible context, KeyFacts, connected events, compact timeline.
   =========================================================================== */

interface EventDetailProps {
  event: HistoricalEvent;
  allEvents: HistoricalEvent[];
}

/* ── Organic Ink Divider ── */
function InkRule() {
  const ref = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            el.classList.add("hist-micro-drawn");
          }
        });
      },
      { threshold: 0.3 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <svg
      ref={ref}
      className="hist-ink-rule"
      viewBox="0 0 400 4"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path
        d="M0 2 C20 0.5, 40 3.5, 80 2 S160 0.5, 200 2 S280 3.5, 320 2 S380 0.5, 400 2"
        stroke="currentColor"
        strokeWidth="1.2"
        fill="none"
        opacity="0.35"
      />
    </svg>
  );
}

export default function EventDetail({ event, allEvents }: EventDetailProps) {
  const [activePerspectiveId, setActivePerspectiveId] = useState(
    event.perspectives[0]?.id ?? ""
  );
  const [comparisonMode, setComparisonMode] = useState(false);
  const [comparisonPerspId, setComparisonPerspId] = useState<string | null>(null);
  const [contextExpanded, setContextExpanded] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const heroRef = useRef<HTMLDivElement>(null);

  const eraInfo = ERAS.find((e) => e.id === event.era);
  const activePerspective = event.perspectives.find((p) => p.id === activePerspectiveId);

  /* When comparison mode is toggled on, default the second perspective to the next one */
  useEffect(() => {
    if (comparisonMode && !comparisonPerspId && event.perspectives.length > 1) {
      const other = event.perspectives.find((p) => p.id !== activePerspectiveId);
      if (other) setComparisonPerspId(other.id);
    }
  }, [comparisonMode, comparisonPerspId, activePerspectiveId, event.perspectives]);

  /* Scroll reveal for content sections */
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("hist-reveal--visible");
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -40px 0px" }
    );

    const sections = contentRef.current?.querySelectorAll(".hist-reveal");
    sections?.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, []);

  /* Hero depth — recedes as content scrolls into view */
  useEffect(() => {
    const heroEl = heroRef.current;
    if (!heroEl) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) {
          heroEl.classList.add("hist-hero--receded");
        } else {
          heroEl.classList.remove("hist-hero--receded");
        }
      },
      { threshold: 0.3 }
    );
    observer.observe(heroEl);
    return () => observer.disconnect();
  }, []);

  const comparisonPersp = comparisonPerspId
    ? event.perspectives.find((p) => p.id === comparisonPerspId)
    : null;

  /* Split context into sentences for collapsible display */
  const contextParagraphs = event.contextNarrative.split("\n");
  const firstParaText = contextParagraphs[0] || "";
  const firstSentences = firstParaText.split(/(?<=[.!?])\s+(?=[A-Z])/).slice(0, 3).join(" ");
  const hasMoreContext = firstParaText.length > firstSentences.length || contextParagraphs.length > 1;

  return (
    <div ref={contentRef}>
      {/* ── Hero (static, depth on scroll) ── */}
      <div ref={heroRef} className="hist-hero hist-hero--static hist-cold-open--hero">
        {event.heroImage ? (
          <img
            src={event.heroImage}
            alt={event.heroCaption ?? event.title}
            className="hist-hero__image hist-hero__image--static"
            onError={(e) => {
              e.currentTarget.style.display = "none";
            }}
          />
        ) : (
          <div className="hist-hero__fallback" />
        )}
        <div className="hist-hero__overlay" />
        <div className="hist-hero__content">
          {eraInfo && (
            <span className="hist-hero__era">
              {eraInfo.label} &middot; {eraInfo.dateRange}
            </span>
          )}
          <h1 className="hist-hero__title">{event.title}</h1>
          {event.subtitle && (
            <p className="hist-hero__subtitle">{event.subtitle}</p>
          )}
          <span className="hist-hero__date">{event.dateRange || event.datePrimary}</span>
        </div>
        {event.heroAttribution && (
          <span className="hist-hero__caption">{event.heroAttribution}</span>
        )}
      </div>

      {/* ── Main Content ── */}
      <div className="hist-main hist-grade">
        {/* 1. PERSPECTIVES — THE PRODUCT (immediately after hero) */}
        <section className="hist-reveal hist-cold-open--content" aria-label="Perspectives">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "var(--space-3)", marginBottom: "var(--space-3)" }}>
            <h2 className="hist-section-label" style={{ marginBottom: 0 }}>
              Perspectives
            </h2>
            {event.perspectives.length >= 2 && (
              <button
                className={`hist-compare-toggle ${comparisonMode ? "hist-compare-toggle--active" : ""}`}
                onClick={() => {
                  setComparisonMode(!comparisonMode);
                  if (comparisonMode) setComparisonPerspId(null);
                }}
                aria-pressed={comparisonMode}
              >
                {comparisonMode ? "Exit Comparison" : "Compare"}
              </button>
            )}
          </div>

          {/* Perspective tabs */}
          <PerspectiveSelector
            perspectives={event.perspectives}
            activeId={activePerspectiveId}
            onSelect={(id) => {
              setActivePerspectiveId(id);
              if (comparisonMode && id === comparisonPerspId) {
                const other = event.perspectives.find(
                  (p) => p.id !== id && p.id !== comparisonPerspId
                );
                if (other) setComparisonPerspId(other.id);
              }
            }}
          />

          {/* Comparison selector for second perspective */}
          {comparisonMode && (
            <div className="hist-compare-selector">
              <span className="hist-compare-label">
                Compare with:
              </span>
              {event.perspectives
                .filter((p) => p.id !== activePerspectiveId)
                .map((p) => (
                  <button
                    key={p.id}
                    onClick={() => setComparisonPerspId(p.id)}
                    className={`hist-compare-option ${p.id === comparisonPerspId ? "hist-compare-option--active" : ""}`}
                    style={p.id === comparisonPerspId ? {
                      background: `var(--hist-persp-${p.color})`,
                      borderColor: `var(--hist-persp-${p.color})`,
                    } : {}}
                  >
                    {p.viewpointName}
                  </button>
                ))}
            </div>
          )}

          {/* Active perspective or comparison */}
          {comparisonMode && activePerspective && comparisonPersp ? (
            <PerspectiveComparison
              perspectiveA={activePerspective}
              perspectiveB={comparisonPersp}
            />
          ) : activePerspective ? (
            <PerspectiveView
              key={activePerspective.id}
              perspective={activePerspective}
            />
          ) : null}
        </section>

        <InkRule />

        {/* 2. Context: What Happened (collapsible) */}
        <section className="hist-reveal" aria-label="What happened">
          <h2 className="hist-section-label">What Happened</h2>
          <div className="hist-context">
            {contextExpanded ? (
              contextParagraphs.map((para, i) => (
                <p key={i}>{para}</p>
              ))
            ) : (
              <p>{firstSentences}</p>
            )}
          </div>
          {hasMoreContext && (
            <button
              className="hist-context-toggle"
              onClick={() => setContextExpanded(!contextExpanded)}
              aria-expanded={contextExpanded}
            >
              {contextExpanded ? "Show less" : "Read more"}
            </button>
          )}
        </section>

        {/* 3. Archival Media Gallery */}
        {event.media && event.media.length > 0 && (
          <div className="hist-reveal">
            <MediaGallery media={event.media} />
          </div>
        )}

        {/* 4. Key Facts (compact) */}
        <div className="hist-reveal">
          <KeyFacts event={event} />
        </div>

        {/* 5. Connected Events */}
        {event.connections.length > 0 && (
          <section className="hist-reveal hist-connections" aria-label="Connected events">
            <h2 className="hist-section-label">Connected Events</h2>
            {event.connections.map((conn, i) => {
              const targetExists = allEvents.some((e) => e.slug === conn.targetSlug);
              if (targetExists) {
                return (
                  <Link
                    key={i}
                    href={`/history/${conn.targetSlug}`}
                    className="hist-connection"
                  >
                    <span className="hist-connection__type">{conn.type}</span>
                    <div className="hist-connection__body">
                      <span className="hist-connection__title">{conn.targetTitle}</span>
                      <span className="hist-connection__desc">{conn.description}</span>
                    </div>
                  </Link>
                );
              }
              return (
                <div key={i} className="hist-connection" style={{ cursor: "default" }}>
                  <span className="hist-connection__type">{conn.type}</span>
                  <div className="hist-connection__body">
                    <span className="hist-connection__title">
                      {conn.targetTitle}
                      <span className="hist-connection__coming">(coming)</span>
                    </span>
                    <span className="hist-connection__desc">{conn.description}</span>
                  </div>
                </div>
              );
            })}
          </section>
        )}

        {/* 6. Compact Timeline: Prev / Next */}
        <div className="hist-reveal">
          <CompactTimeline events={allEvents} currentSlug={event.slug} />
        </div>
      </div>
    </div>
  );
}
