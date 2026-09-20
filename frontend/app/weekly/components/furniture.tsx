"use client";

/* ---------------------------------------------------------------------------
   void --weekly — the issue's repeating furniture.

   A magazine teaches you its structure by repeating the same marks. Before
   this, every section in the weekly opened with the same generic
   `.wk-section-label` — an uppercase Barlow line with a wavy rule — so a
   reader had no way to feel where they were in the issue.

   The DEPARTMENT PLATE is that rhythm: the department's name, a hairline rule
   across the full grid, and a folio on the right in Plex Mono reading
   ISSUE 08 · WORLD · 06. It is the one piece of chrome that appears at every
   section boundary, and it is what makes the running order legible.
   --------------------------------------------------------------------------- */

import type React from "react";
import { useScrollReveal } from "../hooks";
import { issueFolio } from "../format";

/* An organic ink hairline. Hand-drawn path, not a border: a ruled line is a
   browser default, an inked one is a press. */
export function InkRule({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`wk-ink-rule ${className}`}
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

/* Line, lozenge, line — the mark between major movements of the issue. */
export function InkFlourish() {
  return (
    <div className="wk-flourish" aria-hidden="true">
      <svg className="wk-flourish__line" viewBox="0 0 80 2" preserveAspectRatio="none">
        <path d="M0 1 C10 0.3, 20 1.7, 40 1 S60 0.3, 80 1" stroke="currentColor" strokeWidth="1" fill="none" />
      </svg>
      <svg className="wk-flourish__ornament" viewBox="0 0 20 20">
        <path d="M10 2 L14 10 L10 18 L6 10 Z" fill="currentColor" opacity="0.6" />
      </svg>
      <svg className="wk-flourish__line" viewBox="0 0 80 2" preserveAspectRatio="none">
        <path d="M0 1 C10 0.3, 20 1.7, 40 1 S60 0.3, 80 1" stroke="currentColor" strokeWidth="1" fill="none" />
      </svg>
    </div>
  );
}

export function RevealFlourish() {
  const [ref, visible] = useScrollReveal(0.3);
  return (
    <div ref={ref as React.RefObject<HTMLDivElement>} className={visible ? "wk-reveal--visible" : ""}>
      <InkFlourish />
    </div>
  );
}

/**
 * The department plate. Every section in the issue opens with one.
 *
 * `page` is the running folio number — not a real page, but the department's
 * position in the running order, which is what a folio communicates: where you
 * are in the issue and how much is left.
 */
export function DepartmentPlate({
  label,
  issueNumber,
  edition = "World",
  page,
  id,
}: {
  label: string;
  issueNumber: number;
  edition?: string;
  page?: number;
  id?: string;
}) {
  return (
    <div className="wk-plate">
      <h2 className="wk-plate__label" id={id}>
        {label}
      </h2>
      <span className="wk-plate__rule" aria-hidden="true" />
      <span className="wk-plate__folio" aria-hidden="true">
        Issue {issueFolio(issueNumber)}
        <span className="wk-plate__dot"> · </span>
        {edition}
        {page !== undefined && (
          <>
            <span className="wk-plate__dot"> · </span>
            {String(page).padStart(2, "0")}
          </>
        )}
      </span>
    </div>
  );
}

/**
 * A caption line under a picture: what it shows, then who made it.
 *
 * Both halves are optional and the whole thing disappears when neither is
 * present, because an empty figcaption still takes a baseline.
 */
export function ImgCaption({
  caption,
  credit,
}: {
  caption?: string | null;
  credit?: string | null;
}) {
  const cap = (caption || "").trim();
  const cr = (credit || "").trim();
  if (!cap && !cr) return null;
  return (
    <figcaption className="wk-img-caption">
      {cap && <span className="wk-img-caption__text">{cap}</span>}
      {cap && cr && <span className="wk-img-caption__sep" aria-hidden="true"> · </span>}
      {cr && <span className="wk-img-caption__credit">{cr}</span>}
    </figcaption>
  );
}
