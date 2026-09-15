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
            No human editorial board picks the stories, and no AI decides what leads. The order of the feed, how
            stories are grouped, and every bias score all come from fixed rules that run the same way for every
            reader, and each score shows its work. The only place we use AI is to write the words: the short summary
            under each story and the daily brief, and it is told to use only what the source articles say. The rules
            are open, imperfect, and improving.
          </dd>
        </div>
      </dl>
    </section>
  );
}
