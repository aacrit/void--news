"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import LogoIcon from "../components/LogoIcon";
import LogoWordmark from "../components/LogoWordmark";

/* ---------------------------------------------------------------------------
   /about — "See through the void." Mission Manifesto
   7-section cinematic page. Always dark mode. Film grain elevated.
   Progressive disclosure. ~350 words total. Every sentence earns its place.
   --------------------------------------------------------------------------- */

export default function AboutPage() {
  const sectionsRef = useRef<HTMLDivElement>(null);

  /* Scroll-triggered fade-in for each section */
  useEffect(() => {
    const root = sectionsRef.current;
    if (!root) return;
    const els = root.querySelectorAll<HTMLElement>(".about-reveal");
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            (e.target as HTMLElement).style.opacity = "1";
            (e.target as HTMLElement).style.transform = "translateY(0)";
          }
        });
      },
      { threshold: 0.15, rootMargin: "0px 0px -60px 0px" }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  /* Force dark mode on this page */
  useEffect(() => {
    const html = document.documentElement;
    const prev = html.getAttribute("data-mode");
    html.setAttribute("data-mode", "dark");
    return () => {
      if (prev) html.setAttribute("data-mode", prev);
    };
  }, []);

  return (
    <div className="about-page" ref={sectionsRef}>
      {/* ── SECTION 1: THE VOID (Hero) ── */}
      <section className="about-hero">
        <div className="about-hero__mark">
          <LogoIcon size={96} animation="idle" />
        </div>
        <h1 className="about-hero__tagline">See through the void.</h1>
        <div className="about-hero__scroll" aria-hidden="true">
          <span className="about-hero__chevron" />
        </div>
      </section>

      {/* ── SECTION 2: THE PROBLEM ── */}
      <section className="about-section">
        <div className="about-section__inner">
          <div className="about-reveal" style={{ opacity: 0, transform: "translateY(24px)", transition: "opacity 0.8s var(--ease-cinematic), transform 0.8s var(--ease-cinematic)" }}>
            <p className="about-body about-body--lead">
              The same event. Five outlets. Five different realities.
            </p>
            <p className="about-body">
              One calls it a &ldquo;crackdown.&rdquo; Another calls it &ldquo;restoring order.&rdquo;
              A third doesn&rsquo;t cover it at all. The headline says one thing; the article
              says another. The source is &ldquo;officials say&rdquo;&thinsp;&mdash;&thinsp;no name, no title, no
              accountability.
            </p>
            <blockquote className="about-pullquote">This is the void.</blockquote>
            <p className="about-body">
              Not the absence of information&thinsp;&mdash;&thinsp;the opposite. A flood of it, shaped
              by incentive, refracted through ideology, optimized for the click that
              keeps you inside the bubble you didn&rsquo;t choose.
            </p>
            <p className="about-body">
              You already know it&rsquo;s there. You feel it every time you read a headline
              and wonder: who decided this was the story? What am I not seeing?
            </p>
          </div>
        </div>
      </section>

      {/* ── SECTION 3: THE INSTRUMENT ── */}
      <section className="about-section">
        <div className="about-section__inner">
          <div className="about-reveal" style={{ opacity: 0, transform: "translateY(24px)", transition: "opacity 0.8s var(--ease-cinematic) 0.1s, transform 0.8s var(--ease-cinematic) 0.1s" }}>
            <p className="about-body about-body--lead">
              void --news is a newspaper.
            </p>
            <p className="about-body">
              Not a feed. Not an algorithm. Not a recommendation engine trained on
              what you clicked last Tuesday. A newspaper&thinsp;&mdash;&thinsp;the same stories, in the
              same order, for every reader.
            </p>
            <p className="about-data">
              <Link href="/sources" className="about-data__link">1,013 sources</Link>&ensp;·&ensp;158 countries&ensp;·&ensp;4 editions&ensp;·&ensp;Updated 4&times; daily
            </p>
            <p className="about-body">
              Every article scored on six axes&thinsp;&mdash;&thinsp;not by outlet reputation, but by
              what the article itself contains. Word by word. Sentence by sentence.
              Every score has a rationale you can read.
            </p>
          </div>
        </div>
      </section>

      {/* ── SECTION 4: THE SIX AXES ── */}
      <section className="about-section">
        <div className="about-section__inner">
          <div className="about-reveal" style={{ opacity: 0, transform: "translateY(24px)", transition: "opacity 0.8s var(--ease-cinematic) 0.15s, transform 0.8s var(--ease-cinematic) 0.15s" }}>
            <dl className="about-axes">
              {[
                ["Political Lean", "Where the article falls \u2014 not where the outlet is labeled."],
                ["Sensationalism", "How much the article inflates urgency beyond what the facts warrant."],
                ["Opinion vs. Reporting", "Whether it reports facts or argues a position."],
                ["Factual Rigor", "How thoroughly it cites named sources, data, and direct quotes."],
                ["Framing", "Whether word choices or omissions nudge the reader toward a conclusion."],
                ["Outlet Tracking", "How each outlet covers each topic over time."],
              ].map(([name, desc]) => (
                <div key={name} className="about-axis">
                  <dt className="about-axis__name">{name}</dt>
                  <dd className="about-axis__desc">{desc}</dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </section>

      {/* ── SECTION 5: THE DIFFERENCE ── */}
      <section className="about-section">
        <div className="about-section__inner">
          <div className="about-reveal" style={{ opacity: 0, transform: "translateY(24px)", transition: "opacity 0.8s var(--ease-cinematic) 0.1s, transform 0.8s var(--ease-cinematic) 0.1s" }}>
            <p className="about-body about-body--lead">
              Other tools label the outlet.<br />
              We read the article.
            </p>
            <div className="about-comparison">
              <div className="about-comparison__them">
                <span className="about-comparison__label">Outlet label</span>
                <span className="about-comparison__value about-comparison__value--them">&ldquo;Left&rdquo;</span>
              </div>
              <div className="about-comparison__vs">vs</div>
              <div className="about-comparison__us">
                <span className="about-comparison__label">Per-article score</span>
                <div className="about-comparison__scores">
                  <span>Lean <strong>42</strong></span>
                  <span>Rigor <strong>78</strong></span>
                  <span>Tone <strong>18</strong></span>
                  <span>Framing <strong>31</strong></span>
                </div>
              </div>
            </div>
            <p className="about-body about-body--small">
              An outlet rated &ldquo;Left&rdquo; published this article with a center-right
              lean, high factual rigor, and minimal framing. The outlet label
              would have told you to distrust it. The article itself earned that
              trust back.
            </p>
            <p className="about-body about-body--emphasis">
              Per article. Not per outlet. That is the difference.
            </p>
          </div>
        </div>
      </section>

      {/* ── SECTION 6: THE PRINCIPLES ── */}
      <section className="about-section">
        <div className="about-section__inner">
          <div className="about-reveal" style={{ opacity: 0, transform: "translateY(24px)", transition: "opacity 0.8s var(--ease-cinematic) 0.1s, transform 0.8s var(--ease-cinematic) 0.1s" }}>
            <div className="about-principles">
              <div className="about-principle">
                <h3 className="about-principle__head">No paywall.</h3>
                <p className="about-principle__body">
                  Every score, every rationale, every source&thinsp;&mdash;&thinsp;free. Bias transparency
                  is not a premium feature.
                </p>
              </div>
              <div className="about-principle">
                <h3 className="about-principle__head">No algorithm.</h3>
                <p className="about-principle__body">
                  Every reader sees the same stories in the same order. Importance is
                  determined by editorial weight, not by what you clicked yesterday.
                </p>
              </div>
              <div className="about-principle">
                <h3 className="about-principle__head">No black box.</h3>
                <p className="about-principle__body">
                  Every score has a rationale. Every rationale traces to specific signals
                  in the text. You can read the reasoning and disagree.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── SECTION 7: THE INVITATION ── */}
      <section className="about-section about-cta">
        <div className="about-section__inner" style={{ textAlign: "center" }}>
          <div className="about-reveal" style={{ opacity: 0, transform: "translateY(24px)", transition: "opacity 0.8s var(--ease-cinematic), transform 0.8s var(--ease-cinematic)" }}>
            <div className="si-hoverable" style={{ display: "inline-block" }}>
              <LogoIcon size={56} animation="idle" />
            </div>
            <div style={{ marginTop: "var(--space-4)" }}>
              <LogoWordmark height={24} />
            </div>
            <p className="about-cta__tagline">See through the void.</p>
            <Link href="/" className="about-cta__button">
              Read the news
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
