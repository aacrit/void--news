"use client";

import { useReveal } from "./useReveal";
import { SOURCE_TIERS, RANKING_SIGNALS, RANKING_SIGNAL_COUNT, SIX_AXES } from "../../film/data";

/* ---------------------------------------------------------------------------
   About — "How the front page is built". A transparent five-step pipeline
   explainer (Read, Cluster, Measure, Rank, Publish), stepped cards that stagger
   in on scroll. This is the "why 50 stories, and how they are chosen" section.
   All figures pull from film/data.ts so they cannot drift.
   --------------------------------------------------------------------------- */

// Top ranking signals, named in the copy (kept short; the full list lives in the
// beat above). Pulled from RANKING_SIGNALS so weights/names cannot drift.
const TOP_SIGNALS = RANKING_SIGNALS.slice(0, 4).map((s) => s.name.toLowerCase()).join(", ");

const STEPS = [
  {
    n: "01",
    verb: "Read",
    detail: `Every day Void reads ${SOURCE_TIERS.total.toLocaleString()} sources across ${SOURCE_TIERS.countries} countries: ${SOURCE_TIERS.usMajor} US majors, ${SOURCE_TIERS.international} international outlets, ${SOURCE_TIERS.independent} independents. Left, right, and everywhere between.`,
  },
  {
    n: "02",
    verb: "Cluster",
    detail: "Every outlet telling the same story is grouped into one cluster. You see the whole spread of coverage on an event, not one publisher's version of it.",
  },
  {
    n: "03",
    verb: "Measure",
    detail: `Each article is scored on ${SIX_AXES.length} bias axes from two things: the outlet's track record and the article's own words. Rule-based language analysis, no AI opinion. A short item leans on the record; a full article leans on its words.`,
  },
  {
    n: "04",
    verb: "Rank",
    detail: `Clusters are ordered by importance: ${TOP_SIGNALS}, and more. ${RANKING_SIGNAL_COUNT} signals in all, weighted and bias-blind. Never by clicks, never tuned to you.`,
  },
  {
    n: "05",
    verb: "Publish",
    detail: "The top 50 stories go out once a day, in one order, the same front page for every reader. When the news settles, so does the page.",
  },
];

export default function AboutPipeline() {
  const { rootRef, register } = useReveal<HTMLElement>();

  return (
    <section className="about-sec about-sec--pipeline" ref={rootRef} aria-labelledby="about-pipeline-h">
      <p className="about-sec__eyebrow" ref={register(0)} style={{ opacity: 0 }}>How the front page is built</p>
      <h2 id="about-pipeline-h" className="about-sec__h" ref={register(1)} style={{ opacity: 0 }}>
        From a thousand sources to fifty stories.
      </h2>
      <p className="about-sec__lede" ref={register(2)} style={{ opacity: 0 }}>
        No editors picking favorites, no feed learning your habits. The same five steps run once a day, and
        the result is one front page.
      </p>

      <ol className="pipe" aria-label="How the front page is built, five steps">
        {STEPS.map((s, i) => (
          <li className="pipe__step" key={s.n} ref={register(3 + i)} style={{ opacity: 0 }}>
            <span className="pipe__n" aria-hidden="true">{s.n}</span>
            <div className="pipe__body">
              <h3 className="pipe__verb">{s.verb}</h3>
              <p className="pipe__detail">{s.detail}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
