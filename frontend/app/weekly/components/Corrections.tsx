"use client";

/* ---------------------------------------------------------------------------
   Corrections.

   For a publication whose whole thesis is measured honesty, admitting what it
   got wrong is the most on-brand thing it can print, and the box was the most
   conspicuous absence in the audit.

   It renders EVEN WHEN EMPTY, which is the decision that makes it worth
   having. A corrections box that appears only when there is bad news is a box
   a reader learns to dread and never looks for; one that is always in the same
   place, saying either what was fixed or that nothing was, is a standing
   claim. "Nothing corrected in this issue" is a sentence Void should have to
   write on purpose every week.

   The entries are hand-maintained in build-data/weekly-corrections.json. A
   correction is an editorial act: reader reports arrive through /feedback into
   D1, which the build cannot reach and should not, because publishing unvetted
   reader text under the masthead as a correction would be worse than printing
   nothing.
   --------------------------------------------------------------------------- */

import type React from "react";
import type { WeeklyCorrection } from "../../lib/weeklyIssues";
import { BASE_PATH } from "../../lib/utils";
import { useScrollReveal } from "../hooks";

function day(iso?: string): string {
  if (!iso) return "";
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  if (!y || !m || !d) return "";
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${MONTHS[m - 1]} ${d}`;
}

export default function Corrections({ entries }: { entries: WeeklyCorrection[] }) {
  const [ref, visible] = useScrollReveal(0.1);

  return (
    <aside
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-corrections wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-label="Corrections"
    >
      <span className="wk-corrections__label">Corrections</span>
      {entries.length === 0 ? (
        <p className="wk-corrections__none">
          Nothing corrected in this issue.{" "}
          <a className="wk-corrections__link" href={`${BASE_PATH}/feedback/`}>
            Tell us if we got something wrong.
          </a>
        </p>
      ) : (
        <ul className="wk-corrections__list">
          {entries.map((c, i) => (
            <li key={i} className="wk-corrections__item">
              <span className="wk-corrections__meta">
                {c.section}
                {day(c.corrected_on) && (
                  <>
                    <span aria-hidden="true"> · </span>
                    {day(c.corrected_on)}
                  </>
                )}
              </span>
              <p className="wk-corrections__text">{c.text}</p>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
