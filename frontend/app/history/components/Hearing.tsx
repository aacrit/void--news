import Link from "next/link";
import PrintMast from "../../components/PrintMast";
import type { CSSProperties } from "react";
import type { HistoricalEvent, ConnectionType } from "../types";
import type { Hearing as HearingModel, HearingBlock, HearingSection } from "../hearing";
import { HOOKS, CTAS } from "../hooks";
import { deriveStats } from "../stats";
import HeroListen from "./HeroListen";
import SpineRail from "./SpineRail";
import MediaGallery from "./MediaGallery";

/* ===========================================================================
   The Hearing — the History event page, server-rendered.

   One vertical column, read top to bottom, in the order the episode is spoken:
   the cold open, the scenes and their documents, five accounts each arguing
   its own case uninterrupted, the turn, the close. Then, visually subordinate,
   the record.

   Four kinds of speech, four typographic voices, one to one:
     narrator to the reader (open, asides, turn framing, close) — Playfair
     narrator telling (scene lines, an account's case)          — Inter
     someone else's words (a document, an account's witness)    — Plex Mono
     the record's labels (scene titles, attributions, stations) — Barlow

   Three client islands and no more: the rail, the Listen button, and the
   gallery's lightbox. Everything a reader reads is server markup, so the page
   carries the open, the five accounts and the turn with JavaScript off.

   Not rendered, deliberately: TITLE (an audio ident; the hero has the title),
   SAY (for the synthesiser), `significance` and `legacy_points` (the moral the
   format refuses; the close does that job with a particular instead).
   =========================================================================== */

const CONNECTION_PRIORITY: Record<ConnectionType, number> = {
  caused: 4,
  consequence: 3,
  "response-to": 3,
  influenced: 2,
  parallel: 1,
};

const CONNECTION_GLYPH: Record<ConnectionType, string> = {
  caused: "↓",
  consequence: "↑",
  "response-to": "↑",
  influenced: "·",
  parallel: "·",
};

const HERO_ID = "hearing-hero";

/* --------------------------------------------------------------------------
   Blocks
   -------------------------------------------------------------------------- */

function Quote({ block, rule }: { block: Extract<HearingBlock, { t: "quote" }>; rule?: string }) {
  const a = block.attribution;
  return (
    <blockquote
      className="hist-source-block hist-doc__quote"
      cite={a?.work || undefined}
      style={rule ? ({ "--hist-doc-rule": rule } as CSSProperties) : undefined}
    >
      {a && (
        /* Attribution before the words, in DOM order as well as visually,
           exactly as the audio names the speaker before reading the document. */
        <p className="hist-source-block__citation hist-doc__attrib">
          {a.author && <span className="hist-source-block__citation-author">{a.author}</span>}
          {a.work && (
            <>
              {a.author ? " · " : ""}
              <cite>{a.work}</cite>
            </>
          )}
          {a.date && `${a.author || a.work ? " · " : ""}${a.date}`}
        </p>
      )}
      {block.lines.map((line, i) => (
        <p key={i} className="hist-source-block__text">
          &ldquo;{line}&rdquo;
        </p>
      ))}
    </blockquote>
  );
}

function Blocks({ blocks, rule }: { blocks: HearingBlock[]; rule?: string }) {
  return (
    <>
      {blocks.map((b, i) =>
        b.t === "prose" ? (
          <div key={i} className={`hist-prose hist-prose--${b.voice}`}>
            {b.lines.map((line, j) => (
              <p key={j} className="hist-prose__line">
                {line}
              </p>
            ))}
          </div>
        ) : (
          <Quote key={i} block={b} rule={rule} />
        ),
      )}
    </>
  );
}

/* --------------------------------------------------------------------------
   Sections
   -------------------------------------------------------------------------- */

function Section({ section }: { section: HearingSection }) {
  switch (section.kind) {
    case "open":
      return (
        <section id={section.id} className="hist-hr-open" aria-labelledby="hist-hr-open-h">
          <h2 id="hist-hr-open-h" className="sr-only">
            Open
          </h2>
          <Blocks blocks={section.blocks} />
        </section>
      );

    case "scene":
      return (
        <section id={section.id} className="hist-hr-scene">
          <h2 className="hist-hr-scene__eyebrow">
            <span className="hist-hr-scene__num">Scene {section.number}</span>
            {section.title && <span className="hist-hr-scene__title">{section.title}</span>}
          </h2>
          <Blocks blocks={section.blocks} />
        </section>
      );

    case "passage":
      return (
        <div className="hist-hr-passage">
          <Blocks blocks={section.blocks} />
        </div>
      );

    case "rest":
      if (section.media) {
        return (
          <figure className="hist-hr-rest">
            <img
              className="hist-hr-rest__img"
              src={section.media.url}
              alt={section.media.caption}
              loading="lazy"
            />
            <figcaption className="hist-hr-rest__cap">
              <span className="hist-hr-rest__caption">{section.media.caption}</span>
              <span className="hist-hr-rest__credit">
                {section.media.attribution}
                {section.media.year ? ` (${section.media.year})` : ""}
              </span>
            </figcaption>
          </figure>
        );
      }
      /* A rest past the media count, or an event with no media at all: a
         quieter rest, not a broken one. */
      return (
        <div
          className={`hist-hr-rest hist-hr-rest--bare${section.short ? " hist-hr-rest--short" : ""}`}
          aria-hidden="true"
        />
      );

    case "accounts":
      return (
        <section id={section.id} className="hist-hr-accounts">
          <h2 className="hist-hr-accounts__title">{section.title}</h2>
          <Blocks blocks={section.blocks} />
          <ol className="hist-hr-accounts__index">
            {section.index.map((a) => (
              <li key={a.id} className="hist-hr-accounts__item">
                <a
                  href={`#${a.id}`}
                  className="hist-hr-accounts__link"
                  style={{ "--hist-account-color": a.color } as CSSProperties}
                >
                  <span className="hist-hr-accounts__chip" aria-hidden="true" />
                  <span className="hist-hr-accounts__name">{a.label}</span>
                </a>
              </li>
            ))}
          </ol>
        </section>
      );

    case "account": {
      const p = section.perspective;
      return (
        <section
          id={section.id}
          className="hist-hr-account"
          style={{ "--hist-account-color": section.color } as CSSProperties}
        >
          {p && (
            <p className="hist-hr-account__eyebrow">
              <span className="hist-hr-account__type">{section.viewpointType}</span>
              <span className="hist-hr-account__sep" aria-hidden="true">
                ·
              </span>
              <span className="hist-hr-account__viewpoint">{section.viewpoint}</span>
            </p>
          )}
          <h2 className="hist-hr-account__title">{section.title}</h2>
          <Blocks blocks={section.blocks} rule={section.color} />

          {/* Inline, in the reading column, and a real <details>. A modal fails
              without JavaScript and takes the reader out of the spine. Nothing
              in here is said against this account: the omitted list lives in
              the turn and nowhere else. */}
          {p && (p.narrative || (p.keyArguments?.length ?? 0) > 0 || (p.sources?.length ?? 0) > 0) && (
            <details className="hist-hr-account__details">
              <summary className="hist-hr-account__summary">Read the full account</summary>
              <div className="hist-hr-account__full">
                {p.narrative && (
                  <>
                    <h3 className="hist-hr-account__subhead">Narrative</h3>
                    {p.narrative
                      .split(/\n{2,}/)
                      .map((para) => para.trim())
                      .filter(Boolean)
                      .map((para, i) => (
                        <p key={i} className="hist-hr-account__narrative">
                          {para}
                        </p>
                      ))}
                  </>
                )}
                {(p.keyArguments?.length ?? 0) > 0 && (
                  <>
                    <h3 className="hist-hr-account__subhead">Arguments</h3>
                    <ul className="hist-hr-account__args">
                      {p.keyArguments!.map((arg, i) => (
                        <li key={i}>{arg}</li>
                      ))}
                    </ul>
                  </>
                )}
                {(p.sources?.length ?? 0) > 0 && (
                  <>
                    <h3 className="hist-hr-account__subhead">Sources</h3>
                    <ul className="hist-hr-account__sources">
                      {p.sources!.map((s, i) => (
                        <li key={i}>
                          <span className="hist-hr-account__source-title">
                            {s.archive_url ? (
                              <a href={s.archive_url} rel="noopener noreferrer" target="_blank">
                                {s.title}
                              </a>
                            ) : (
                              s.title
                            )}
                          </span>
                          {(s.author || s.year) && (
                            <span className="hist-hr-account__source-meta">
                              {[s.author, s.year].filter(Boolean).join(" · ")}
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            </details>
          )}
        </section>
      );
    }

    case "turn":
      /* The payload. After all five have spoken, the only place the five names
         sit together, never collapsed and never lazy-loaded. */
      return (
        <section id={section.id} className="hist-hr-turn">
          <div className="hist-hr-turn__inner">
            <h2 className="hist-hr-turn__eyebrow">The turn</h2>
            {section.framing.map((line, i) => (
              <p key={i} className="hist-hr-turn__framing">
                {line}
              </p>
            ))}
            <ol className="hist-hr-turn__ledger">
              {section.rows.map((row) => (
                <li
                  key={row.href}
                  className="hist-hr-turn__row"
                  style={{ "--hist-account-color": row.color } as CSSProperties}
                >
                  <p className="hist-hr-turn__name">
                    <span className="hist-hr-turn__chip" aria-hidden="true" />
                    <a href={row.href} className="hist-hr-turn__name-link">
                      {row.name}
                    </a>
                  </p>
                  {row.text && <p className="hist-hr-turn__line">{row.text}</p>}
                  {row.omitted.length > 0 && (
                    <details className="hist-hr-turn__record">
                      <summary className="hist-hr-turn__record-summary">From the record</summary>
                      <div className="hist-omissions">
                        <div className="hist-omissions__list" role="list">
                          {row.omitted.map((item, i) => (
                            <div key={i} className="hist-omission-item" role="listitem">
                              <span className="hist-omission-bullet--hollow" aria-hidden="true" />
                              <span className="hist-omission-text--omitted">{item}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </details>
                  )}
                </li>
              ))}
            </ol>
            {section.closing.map((line, i) => (
              <p key={i} className="hist-hr-turn__closing">
                {line}
              </p>
            ))}
          </div>
        </section>
      );

    case "close":
      return (
        <section id={section.id} className="hist-hr-close" aria-labelledby="hist-hr-close-h">
          <h2 id="hist-hr-close-h" className="sr-only">
            Close
          </h2>
          <Blocks blocks={section.blocks} />
        </section>
      );

    default:
      return null;
  }
}

/* --------------------------------------------------------------------------
   The page
   -------------------------------------------------------------------------- */

interface HearingProps {
  event: HistoricalEvent;
  hearing: HearingModel | null;
  nextEvent: { slug: string; title: string } | null;
}

export default function Hearing({ event, hearing, nextEvent }: HearingProps) {
  const stats = deriveStats(event);
  const galleryMedia = hearing ? hearing.galleryMedia : event.media;
  const threads = [...event.connections]
    .sort((a, b) => (CONNECTION_PRIORITY[b.type] ?? 0) - (CONNECTION_PRIORITY[a.type] ?? 0))
    .slice(0, 3);

  return (
    <div className="hist-event-detail hist-hearing-page">
      <PrintMast path={`/history/${event.slug}/`} />
      {/* ── HERO — kept as it was: image, date, title, subtitle, Listen ── */}
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

      {/* ── THE SPINE ── */}
      <div className="hist-hearing">
        {hearing && hearing.stations.length > 0 && (
          /* The rail spans every row of the spine so it can stay sticky the
             whole way down. `grid-row: 1 / -1` cannot do that here: the rows
             are implicit, so -1 resolves to line 1. The row count is known at
             build, so it rides in as a custom property and the desktop media
             query is the only thing that acts on it. */
          <div
            className="hist-rail-slot"
            style={{ "--hist-rail-span": hearing.sections.length + 2 } as CSSProperties}
          >
            <SpineRail stations={hearing.stations} heroId={HERO_ID} />
          </div>
        )}

        {hearing?.sections.map((section) => (
          <Section key={section.id} section={section} />
        ))}

        {/* ── THE RECORD — everything after the close is subordinate ── */}
        <section className="hist-record" aria-labelledby="hist-record-h">
          <h2 id="hist-record-h" className="hist-record__label">
            The record
          </h2>

          {stats.length > 0 && (
            <div className="hist-record__block">
              <h3 className="hist-record__subhead">By the numbers</h3>
              <dl className="hist-numbers__grid hist-numbers__grid--record" data-count={stats.length}>
                {stats.map((s) => (
                  <div key={s.key} className={`hist-stat hist-stat--${s.variant}`}>
                    <dt className="hist-stat__label">{s.label}</dt>
                    <dd className="hist-stat__body">
                      <span className="hist-stat__value">{s.value}</span>
                      {s.fine && <span className="hist-stat__fine">{s.fine}</span>}
                    </dd>
                  </div>
                ))}
              </dl>
            </div>
          )}

          {event.keyFigures.length > 0 && (
            <div className="hist-record__block">
              <h3 className="hist-record__subhead">Key figures</h3>
              <ul className="hist-record__figures">
                {event.keyFigures.map((f) => (
                  <li key={f.name} className="hist-record__figure">
                    <span className="hist-record__figure-name">{f.name}</span>
                    <span className="hist-record__figure-role">{f.role}</span>
                    {(f.born || f.died) && (
                      <span className="hist-record__figure-years">
                        {f.born ?? "?"} to {f.died ?? "?"}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {(event.primarySources?.length ?? 0) > 0 && (
            <div className="hist-record__block">
              <h3 className="hist-record__subhead">Primary sources</h3>
              {event.primarySources!.map((s, i) => (
                <blockquote key={i} className="hist-source-block hist-doc__quote" cite={s.work || undefined}>
                  <p className="hist-source-block__citation hist-doc__attrib">
                    {s.author && <span className="hist-source-block__citation-author">{s.author}</span>}
                    {s.work && (
                      <>
                        {s.author ? " · " : ""}
                        <cite>{s.work}</cite>
                      </>
                    )}
                    {s.date && `${s.author || s.work ? " · " : ""}${s.date}`}
                  </p>
                  <p className="hist-source-block__text">&ldquo;{s.text}&rdquo;</p>
                </blockquote>
              ))}
            </div>
          )}

          {galleryMedia.length > 0 && (
            <div className="hist-record__block" id="gallery">
              <h3 className="hist-record__subhead">Gallery</h3>
              <MediaGallery media={galleryMedia} />
            </div>
          )}

          {threads.length > 0 && (
            <div className="hist-record__block">
              <h3 className="hist-record__subhead">Threads</h3>
              <ul className="hist-record__threads">
                {threads.map((c) => (
                  <li key={c.targetSlug}>
                    <Link href={`/history/${c.targetSlug}`} className="hist-record__thread">
                      <span className="hist-record__thread-glyph" aria-hidden="true">
                        {CONNECTION_GLYPH[c.type] ?? "·"}
                      </span>
                      <span className="hist-record__thread-title">{c.targetTitle}</span>
                      <span className="hist-record__thread-hook">
                        {HOOKS[c.targetSlug] || c.description}
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="hist-record__exits">
            {nextEvent && (
              <Link href={`/history/${nextEvent.slug}`} className="hist-record__next">
                {CTAS[nextEvent.slug] || `Next: ${nextEvent.title}`} →
              </Link>
            )}
            <Link href="/history" className="hist-record__archive">
              Return to The Archive
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
