"use client";

import Link from "next/link";
import { useReveal } from "./useReveal";
import { SIX_AXES } from "../../film/data";

/* ---------------------------------------------------------------------------
   About — "What void is, and is not." A compact, honest FAQ. Covers the fixed
   principles (no personalization, no account, free forever, every score traces
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
    a: "Free, forever. No paywall, no premium tier, no ads. There never will be.",
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
            Yes. Every score on all {SIX_AXES.length} axes traces back to specific words in the article. Nothing is a
            black box.{" "}
            <Link href="/sources#methodology" className="faq__link">Read the methodology</Link>.
          </dd>
        </div>

        <div className="faq__item" ref={register(3 + QA.length)} style={{ opacity: 0 }}>
          <dt className="faq__q">Is a person deciding what I see?</dt>
          <dd className="faq__a">
            No. Void is not a human editorial board, and it is not an AI judging the news. It is an experimental,
            rule-based engine reading language by fixed rules. The rules are open, imperfect, and improving.
          </dd>
        </div>
      </dl>
    </section>
  );
}
