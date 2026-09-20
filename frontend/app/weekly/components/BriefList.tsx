"use client";

/* ---------------------------------------------------------------------------
   Week in Brief.

   Ten short items — which is what columns are actually for. A magazine sets
   briefs in columns because each one is a few lines and the eye takes a whole
   item in at once; the reader never has to track back up a column, which is
   why features get a measure and briefs get columns (see Feature.tsx).

   Two things had to change upstream before this could read as a brief column.
   The items were ~1000 characters each, because RECAP_SYSTEM asked for 150-200
   words and the model obeyed exactly; the spec was the bug, and it is 55-75
   words now. And each item carries its cluster's category as a kicker —
   `section` has been declared in the types all along and nothing ever copied it
   across, so every item rendered unlabelled.
   --------------------------------------------------------------------------- */

import { useState } from "react";
import type React from "react";
import type { WeeklyRecapStory } from "../types";
import { DepartmentPlate } from "./furniture";
import { useScrollReveal } from "../hooks";

function Thumb({ story }: { story: WeeklyRecapStory }) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  if (!story.image_url || error) return null;
  return (
    <div className="wk-brief__thumb">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={story.image_url}
        alt=""
        className={`wk-brief__thumb-img${loaded ? " wk-brief__thumb-img--loaded" : ""}`}
        loading="lazy"
        decoding="async"
        onLoad={() => setLoaded(true)}
        onError={() => setError(true)}
      />
    </div>
  );
}

export default function BriefList({
  stories,
  issueNumber,
  page,
}: {
  stories: WeeklyRecapStory[];
  issueNumber: number;
  page: number;
}) {
  const [ref, visible] = useScrollReveal(0.08);
  if (!stories || stories.length === 0) return null;

  return (
    <section
      id="wk-brief"
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-cover-anchor wk-brief-section wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-labelledby="wk-brief-heading"
    >
      <DepartmentPlate
        label="Week in Brief"
        issueNumber={issueNumber}
        page={page}
        id="wk-brief-heading"
      />
      <div className="wk-brief__list">
        {stories.map((story, i) => (
          <article
            key={i}
            className={`wk-brief__item${story.image_url ? " wk-brief__item--has-thumb" : ""}`}
          >
            <div className="wk-brief__body">
              {story.section && (
                <span className="wk-brief__kicker">{story.section}</span>
              )}
              {story.headline?.trim() && (
                <h3 className="wk-brief__headline">{story.headline}</h3>
              )}
              <p className="wk-brief__summary">{story.summary}</p>
            </div>
            <Thumb story={story} />
          </article>
        ))}
      </div>
    </section>
  );
}
