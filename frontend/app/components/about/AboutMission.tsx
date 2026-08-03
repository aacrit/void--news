"use client";

import { useReveal } from "./useReveal";

/* ---------------------------------------------------------------------------
   About — Mission. Why void exists. Two short editorial paragraphs, ending on
   the "See through the void" ethos. Page-only (not in the onboarding overlay).
   --------------------------------------------------------------------------- */

export default function AboutMission() {
  const { rootRef, register } = useReveal<HTMLElement>();

  return (
    <section className="about-sec about-sec--mission" ref={rootRef} aria-labelledby="about-mission-h">
      <p className="about-sec__eyebrow" ref={register(0)} style={{ opacity: 0 }}>Why Void exists</p>
      <h2 id="about-mission-h" className="about-sec__h" ref={register(1)} style={{ opacity: 0 }}>
        The spin is the story no one prints.
      </h2>
      <div className="about-mission__body">
        <p ref={register(2)} style={{ opacity: 0 }}>
          Every outlet covers the same events. Each one chooses the words, the order, the things left
          unsaid. That choosing is bias, and it is almost always invisible. Read one paper and you never
          see the tilt. Read a hundred and the tilt is all you see. Over time it quietly erodes the trust
          that a shared set of facts depends on.
        </p>
        <p ref={register(3)} style={{ opacity: 0 }}>
          Void measures that tilt from the words themselves, on six axes, rule by rule, with no opinion of
          its own. It ranks the day like a newspaper, by what matters, not by what you click. And it gives
          the whole thing away: no account, no tracking, no price. See the words, see the slant, and decide
          for yourself. See through the void.
        </p>
      </div>
    </section>
  );
}
