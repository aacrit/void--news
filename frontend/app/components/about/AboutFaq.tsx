"use client";

import Link from "next/link";
import { useReveal } from "./useReveal";
import { SIX_AXES } from "../../film/data";

/* ---------------------------------------------------------------------------
   About — "What void is, and is not." A compact, honest FAQ. Covers the fixed
   principles (no personalization, no account, free to read, every score traces
   to words) plus the honest limits (experimental, rule-based, not a human board
   and not an AI judge). Replaces the old footer principles list so the same
   promise is never printed twice on the page.
   --------------------------------------------------------------------------- */

const QA = [
  {
    q: "Does Void learn what I like?",
    a: "No. There is no personalization. The same 50 stories, in the same order, for every reader. A front page, not a feed.",
  },
  {
    q: "Do I need an account?",
    a: "No account, no login, no cookies that follow you. Nothing about you is collected, profiled, or sold.",
  },
  {
    q: "What does it cost?",
    a: "The daily edition is free to read. No paywall, no tracking, no feed tuned to you.",
  },
];

export default function AboutFaq() {
  const { rootRef, register } = useReveal<HTMLElement>();

  return (
    <section className="about-sec about-sec--faq" ref={rootRef} aria-labelledby="about-faq-h">
      <p className="about-sec__eyebrow" ref={register(0)} style={{ opacity: 0 }}>What Void is, and is not</p>
      <h2 id="about-faq-h" className="about-sec__h" ref={register(1)} style={{ opacity: 0 }}>
        A few things, said plainly.
      </h2>

      <dl className="faq">
        {QA.map((item, i) => (
          <div className="faq__item" key={item.q} ref={register(2 + i)} style={{ opacity: 0 }}>
            <dt className="faq__q">{item.q}</dt>
            <dd className="faq__a">{item.a}</dd>
          </div>
        ))}

        <div className="faq__item" ref={register(2 + QA.length)} style={{ opacity: 0 }}>
          <dt className="faq__q">Can I check a bias score?</dt>
          <dd className="faq__a">
            Yes. Every score on all {SIX_AXES.length} axes traces back to two things: the article&rsquo;s own words and the
            outlet&rsquo;s track record. Nothing is a black box.{" "}
            <Link href="/sources#methodology" className="faq__link">Read the methodology</Link>.
          </dd>
        </div>

        <div className="faq__item" ref={register(3 + QA.length)} style={{ opacity: 0 }}>
          <dt className="faq__q">Is a person deciding what I see?</dt>
          <dd className="faq__a">
            No human editorial board picks the stories, and the bias analysis is rule-based with no AI: fixed rules
            read each article's words, and every score shows its work. The feed's ordering does use one small AI
            signal, a story-type tag from Gemini, alongside source breadth and other measures, but it is bounded by
            published guardrails and cannot down-weight a story that is under 12 hours old, has 20 or more sources, or
            is still gaining coverage.
          </dd>
        </div>
      </dl>
    </section>
  );
}
