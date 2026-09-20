"use client";

/* ---------------------------------------------------------------------------
   Contents.

   The clearest single signal that a thing is a magazine and not a long page:
   an issue that tells you what is in it before you start. Every string here
   already exists in weekly.json — this section costs nothing to generate and
   nothing to run, and it is the piece the weekly has never had.

   It also does real navigational work. The issue now runs to nine departments;
   without a contents, the only way to learn that The Week in Bias exists is to
   scroll past four essays.
   --------------------------------------------------------------------------- */

import { DepartmentPlate } from "./furniture";
import { useScrollReveal } from "../hooks";
import type React from "react";

export interface ContentsEntry {
  /** The department, as its plate names it. */
  label: string;
  /** The piece's own headline, or a one-line description of the department. */
  title: string;
  /** In-page anchor. */
  href: string;
  /** Running folio, matching the plate. */
  page: number;
}

export default function Contents({
  entries,
  issueNumber,
}: {
  entries: ContentsEntry[];
  issueNumber: number;
}) {
  const [ref, visible] = useScrollReveal(0.1);
  if (entries.length === 0) return null;

  return (
    <section
      id="wk-contents"
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-cover-anchor wk-contents-section wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-labelledby="wk-contents-heading"
    >
      <DepartmentPlate
        label="Contents"
        issueNumber={issueNumber}
        id="wk-contents-heading"
      />
      <ol className="wk-contents__list">
        {entries.map((e) => (
          <li key={e.href} className="wk-contents__item">
            <a className="wk-contents__link" href={e.href}>
              <span className="wk-contents__folio" aria-hidden="true">
                {String(e.page).padStart(2, "0")}
              </span>
              <span className="wk-contents__body">
                <span className="wk-contents__label">{e.label}</span>
                <span className="wk-contents__title">{e.title}</span>
              </span>
            </a>
          </li>
        ))}
      </ol>
    </section>
  );
}
