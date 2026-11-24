"use client";

/* ---------------------------------------------------------------------------
   The Editorial — Void's own argued column on the week.

   Distinct from Perspectives: those are three lenses on three stories, written
   as columnists. This is one argument about the week as a whole, written after
   the daily columns and explicitly forbidden from restating them, so it argues
   the through-line no single day could see. Its lens rotates by issue number.

   At 450-650 words it sets in two columns, like the departments.
   --------------------------------------------------------------------------- */

import type React from "react";
import { DepartmentPlate } from "./furniture";
import { leanBadgeLabel, leanToBiasVar } from "../format";
import { useScrollReveal } from "../hooks";

export default function Editorial({
  headline,
  text,
  lean,
  issueNumber,
  page,
}: {
  headline?: string | null;
  text: string;
  lean?: string | null;
  issueNumber: number;
  page: number;
}) {
  const [ref, visible] = useScrollReveal(0.08);
  const paras = (text || "").split("\n\n").map((p) => p.trim()).filter(Boolean);
  if (paras.length === 0) return null;

  return (
    <section
      id="wk-editorial"
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-cover-anchor wk-editorial wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      style={{ ["--lean-color" as string]: leanToBiasVar(lean || "center") }}
      aria-labelledby="wk-editorial-heading"
    >
      <DepartmentPlate
        label="The Editorial"
        issueNumber={issueNumber}
        page={page}
        id="wk-editorial-heading"
      />
      <span className="wk-editorial__lens">
        The week, through a {leanBadgeLabel(lean || "center").toLowerCase()} lens
      </span>
      {headline?.trim() && <h3 className="wk-editorial__headline">{headline}</h3>}
      <div className="wk-editorial__text">
        {paras.map((p, i) => <p key={i}>{p}</p>)}
      </div>
    </section>
  );
}
