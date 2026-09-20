"use client";

/* ---------------------------------------------------------------------------
   Perspectives — the argument, and the lenses.

   WHAT WAS BROKEN. The generator writes five opinion essays with a deliberate
   editorial structure: essays 1 and 2 argue the SAME cover story from left and
   right, each told in its prompt that the other columnist exists and will be
   read beside it. Essay 3 is a centre voice on the second cover story, and 4
   and 5 are centre-left and centre-right on other threads.

   That structure was destroyed on the way to the page. The backend bucketed by
   lean, so centre-left, centre and centre-right all landed in one
   `opinion_center`; the page then took `[0]` of each of three buckets and
   rendered three essays on three unrelated topics — while silently dropping
   two. The deliberate dialectic never appeared anywhere.

   THE ARGUMENT sets the paired two facing each other across a centre rule,
   with the story they are arguing about named once, above both. THREE MORE
   LENSES carries the rest. Between them, all five essays are now printed.
   --------------------------------------------------------------------------- */

import type React from "react";
import type { WeeklyOpinion } from "../types";
import { leanBadgeLabel, leanToBiasVar } from "../format";
import { DepartmentPlate } from "./furniture";
import { useScrollReveal } from "../hooks";

function paragraphs(text: string): string[] {
  return (text || "").split("\n\n").map((p) => p.trim()).filter(Boolean);
}

function Column({ op, side }: { op: WeeklyOpinion; side?: "left" | "right" }) {
  return (
    <article
      className={`wk-opinion wk-reveal-child${side ? ` wk-opinion--${side}` : ""}`}
      style={{ ["--lean-color" as string]: leanToBiasVar(op.lean) }}
    >
      <div className="wk-opinion__header">
        <span className="wk-opinion__badge">{leanBadgeLabel(op.lean)}</span>
      </div>
      {op.headline?.trim() && <h3 className="wk-opinion__headline">{op.headline}</h3>}
      <div className="wk-opinion__text">
        {paragraphs(op.text).map((p, i) => <p key={i}>{p}</p>)}
      </div>
    </article>
  );
}

/**
 * Pick the head-to-head. Two essays that share a `pair_id` are the pair the
 * generator wrote as one argument. Snapshots published before `pair_id`
 * existed fall back to the `paired` flag, and before that to a left/right
 * match on one topic — so every vintage of the data still finds its argument.
 */
function findPair(opinions: WeeklyOpinion[]): [WeeklyOpinion, WeeklyOpinion] | null {
  const byPairId = new Map<string, WeeklyOpinion[]>();
  for (const o of opinions) {
    if (!o.pair_id) continue;
    byPairId.set(o.pair_id, [...(byPairId.get(o.pair_id) || []), o]);
  }
  for (const group of byPairId.values()) {
    if (group.length === 2) return orient(group[0], group[1]);
  }
  const flagged = opinions.filter((o) => o.paired);
  if (flagged.length === 2) return orient(flagged[0], flagged[1]);
  const left = opinions.find((o) => (o.lean || "").toLowerCase() === "left");
  const right = opinions.find((o) => (o.lean || "").toLowerCase() === "right");
  if (left && right && left.topic && left.topic === right.topic) return [left, right];
  return null;
}

function orient(a: WeeklyOpinion, b: WeeklyOpinion): [WeeklyOpinion, WeeklyOpinion] {
  return (a.lean || "").toLowerCase().startsWith("left") ? [a, b] : [b, a];
}

export function TheArgument({
  opinions,
  issueNumber,
  page,
}: {
  opinions: WeeklyOpinion[];
  issueNumber: number;
  page: number;
}) {
  const [ref, visible] = useScrollReveal(0.08);
  const pair = findPair(opinions);
  if (!pair) return null;
  const [left, right] = pair;

  return (
    <section
      id="wk-argument"
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-cover-anchor wk-argument wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-labelledby="wk-argument-heading"
    >
      <DepartmentPlate
        label="The Argument"
        issueNumber={issueNumber}
        page={page}
        id="wk-argument-heading"
      />
      {left.topic && <p className="wk-argument__topic">{left.topic}</p>}
      <div className="wk-argument__grid">
        <Column op={left} side="left" />
        <span className="wk-argument__spine" aria-hidden="true" />
        <Column op={right} side="right" />
      </div>
    </section>
  );
}

export function MoreLenses({
  opinions,
  issueNumber,
  page,
}: {
  opinions: WeeklyOpinion[];
  issueNumber: number;
  page: number;
}) {
  const [ref, visible] = useScrollReveal(0.08);
  const pair = findPair(opinions);
  const paired = new Set(pair ? [pair[0], pair[1]] : []);
  const rest = opinions.filter((o) => !paired.has(o));
  if (rest.length === 0) return null;

  return (
    <section
      id="wk-perspectives"
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-cover-anchor wk-opinions-section wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-labelledby="wk-opinions-heading"
    >
      <DepartmentPlate
        label="Other Lenses"
        issueNumber={issueNumber}
        page={page}
        id="wk-opinions-heading"
      />
      <div className="wk-opinions__grid" data-count={rest.length}>
        {rest.map((op, i) => (
          <div key={i} className="wk-opinions__cell">
            {op.topic && <p className="wk-opinion__topic">{op.topic}</p>}
            <Column op={op} />
          </div>
        ))}
      </div>
    </section>
  );
}
