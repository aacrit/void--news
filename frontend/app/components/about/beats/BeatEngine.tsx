"use client";

import { useEffect, useRef } from "react";
import { BEATS, RANKING_SIGNALS, RANKING_GATE, RANKING_SIGNAL_COUNT, SOURCE_TIERS } from "../../../film/data";
import { useReducedMotion } from "../../../film/useReducedMotion";
import { useMotion } from "../useMotion";

/* ---------------------------------------------------------------------------
   Beat 3 — "Ranked by what matters."
   The real 10-signal importance ranker, visualized. Bars spring to their
   weights when the beat scrolls into view (Motion One inView + spring stagger).
   Bias-blind by design; zero engagement metrics.
   --------------------------------------------------------------------------- */

const BEAT = BEATS[2];
const MAX_W = Math.max(...RANKING_SIGNALS.map((s) => s.weight));

export default function BeatEngine() {
  const reduced = useReducedMotion();
  const motion = useMotion(!reduced.current);
  const rootRef = useRef<HTMLElement>(null);
  const barRefs = useRef<(HTMLSpanElement | null)[]>([]);
  const played = useRef(false);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;

    // Reduced motion / no Motion: show full bars immediately.
    if (reduced.current || !motion) {
      barRefs.current.forEach((el, i) => {
        if (el) el.style.transform = `scaleX(${RANKING_SIGNALS[i].weight / MAX_W})`;
      });
      return;
    }

    const stop = motion.inView(root, () => {
      if (played.current) return;
      played.current = true;
      barRefs.current.forEach((el, i) => {
        if (!el) return;
        motion.animate(
          el,
          { transform: `scaleX(${RANKING_SIGNALS[i].weight / MAX_W})` },
          { type: "spring", stiffness: 180, damping: 24, delay: i * 0.07 },
        );
      });
    }, { amount: 0.4 });

    return () => stop();
  }, [motion, reduced]);

  return (
    <section className="beat beat--engine" ref={rootRef} aria-labelledby="beat-engine-h">
      <div className="beat__head">
        <h2 id="beat-engine-h" className="beat__headline">{BEAT.headline}</h2>
        <p className="beat__body">{BEAT.body}</p>
      </div>

      <ul className="rsignals" aria-label={`${RANKING_SIGNAL_COUNT} ranking signals`}>
        {RANKING_SIGNALS.map((s, i) => (
          <li key={s.name} className="rsignals__row">
            <span className="rsignals__name">{s.name}</span>
            <span className="rsignals__bar" aria-hidden="true">
              <span
                className="rsignals__fill"
                ref={(el) => { barRefs.current[i] = el; }}
                style={{ transform: "scaleX(0)" }}
              />
            </span>
            <span className="rsignals__w">{s.weight}%</span>
          </li>
        ))}
      </ul>

      <p className="rsignals__gate">
        + {RANKING_GATE} = {RANKING_SIGNAL_COUNT} signals. Zero engagement metrics.
      </p>
      <p className="beat__note">
        {SOURCE_TIERS.total.toLocaleString()} sources · {SOURCE_TIERS.countries} countries ·{" "}
        {SOURCE_TIERS.usMajor} US major · {SOURCE_TIERS.international} international · {SOURCE_TIERS.independent} independent
      </p>
    </section>
  );
}
