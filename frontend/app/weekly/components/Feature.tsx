"use client";

/* ---------------------------------------------------------------------------
   A cover feature: the long form of the issue.

   TYPE SETTING — the single biggest change in this rebuild.

   The essay used to set as JUSTIFIED Inter across the full canvas, which is
   min(92vw, 1600px). At desktop width that is roughly 200 characters a line,
   against the design system's own 65ch rule, with `hyphens: auto` doing what
   automatic hyphenation does at that measure: rivers.

   The instinct is `column-count: 2`, and it is wrong here. Print columns work
   because a page is finite. On a scrolling page, a 1,200-word two-column block
   makes the reader read to the bottom of column one and then scroll back UP,
   with no reflow control. So the rule in this issue is: MEASURE the long
   things, COLUMN the short ones. Features get one 68ch column; the 400-700
   word departments (see DepartmentEssay) get two, because at that length a
   two-column block is about one screen tall and genuinely reads as a page.

   The width that used to be spent on more text is now the MARGIN SYSTEM. The
   grid is named-line (full / rail / text), so art breaks full-bleed, the
   pull-quote breaks into the outer column, and the numbers rail sits beside
   the prose instead of interrupting it.

   That answers the objection that killed the last attempt at this. weekly.css
   recorded that a 2-col cover zone was reverted because it "left a blank
   column beside the editorial" — a property of FLOAT, which depends on content
   length. A grid cannot reproduce it: the outer tracks are 1fr and have no
   height when nothing is placed in them.
   --------------------------------------------------------------------------- */

import { useState } from "react";
import type React from "react";
import type { WeeklyCoverStory } from "../types";
import { essayParagraphs, pickPullQuote } from "../format";
import { ImgCaption } from "./furniture";
import { useScrollReveal } from "../hooks";

function FeatureImage({
  imageUrl,
  attribution,
  caption,
  eager = false,
}: {
  imageUrl: string;
  attribution?: string | null;
  caption?: string | null;
  eager?: boolean;
}) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  if (error) return null;
  return (
    <figure className="wk-feature__figure">
      <div className="wk-feature__image-wrap">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={imageUrl}
          alt=""
          className={`wk-feature__image${loaded ? " wk-feature__image--loaded" : ""}`}
          loading={eager ? "eager" : "lazy"}
          fetchPriority={eager ? "high" : undefined}
          decoding="async"
          onLoad={() => setLoaded(true)}
          onError={() => setError(true)}
        />
      </div>
      <ImgCaption caption={caption} credit={attribution} />
    </figure>
  );
}

/** The figures rail: numbers that already appear in the essay, set beside it. */
function NumbersRail({ story }: { story: WeeklyCoverStory }) {
  const numbers = (story.numbers || [])
    .map((n) => ({
      stat: (n.value ?? n.stat ?? "").trim(),
      context: (n.label ?? n.context ?? "").trim(),
    }))
    .filter((n) => n.stat);
  if (numbers.length === 0) return null;
  return (
    <aside className="wk-feature__numbers" aria-label="By the numbers">
      {numbers.slice(0, 5).map((n, i) => (
        <div key={i} className="wk-feature__number-item">
          <span className="wk-feature__number-stat">{n.stat}</span>
          <span className="wk-feature__number-context">{n.context}</span>
        </div>
      ))}
    </aside>
  );
}

/** The week as it happened, from the cluster data. Never LLM-written. */
function TimelineRail({ story }: { story: WeeklyCoverStory }) {
  const entries = (story.timeline || []).filter((e) => e.date && e.title);
  if (entries.length < 2) return null;
  return (
    <aside className="wk-feature__timeline" aria-label="How the week ran">
      <span className="wk-feature__timeline-label">How the week ran</span>
      <ol className="wk-feature__timeline-list">
        {entries.map((e, i) => (
          <li key={i} className="wk-feature__timeline-item">
            <span className="wk-feature__timeline-date">{e.date}</span>
            <span className="wk-feature__timeline-title">{e.title}</span>
            {!!e.source_count && (
              <span className="wk-feature__timeline-count">
                {e.source_count} sources
              </span>
            )}
          </li>
        ))}
      </ol>
    </aside>
  );
}

export default function Feature({
  story,
  id,
  /** The lead feature sets its lede larger and loads its art eagerly. */
  lead = false,
}: {
  story: WeeklyCoverStory;
  id?: string;
  lead?: boolean;
}) {
  const [ref, visible] = useScrollReveal(0.08);
  const paras = essayParagraphs(story.text || "");
  const pullQuote = pickPullQuote(story.text || "");
  if (paras.length === 0) return null;

  return (
    <article
      id={id}
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-feature wk-cover-anchor wk-reveal${visible ? " wk-reveal--visible" : ""}`}
    >
      {story.image_url && (
        <FeatureImage
          imageUrl={story.image_url}
          attribution={story.image_attribution}
          caption={story.image_caption}
          eager={lead}
        />
      )}

      <div className="wk-feature__body">
        {paras.map((para, j) => (
          <p
            key={j}
            className={j === 0 ? "wk-feature__lede" : undefined}
          >
            {para}
          </p>
        ))}
      </div>

      {pullQuote && paras.length > 2 && (
        <blockquote className="wk-pullquote">{pullQuote}</blockquote>
      )}
      <NumbersRail story={story} />
      <TimelineRail story={story} />
    </article>
  );
}
