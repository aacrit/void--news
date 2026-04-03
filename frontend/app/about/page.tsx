"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import LogoIcon from "../components/LogoIcon";
import LogoWordmark from "../components/LogoWordmark";

/* ===========================================================================
   /about — "See through the void." Cinematic Mission Manifesto
   12-section, 4-act page. Always dark mode. Film grain elevated.
   Scroll-driven cinematic reveals. Organic ink elements. Interactive demos.
   =========================================================================== */

/* ── Hardcoded Data ── */

const DIVERGENCE_HEADLINES = [
  {
    outlet: "Reuters",
    lean: "Center",
    leanScore: 48,
    headline:
      "\u201CUS and China resume trade talks amid tariff tensions\u201D",
  },
  {
    outlet: "Fox News",
    lean: "Right",
    leanScore: 72,
    headline:
      "\u201CTrump administration takes hard line as China trade talks restart\u201D",
  },
  {
    outlet: "The Guardian",
    lean: "Center-Left",
    leanScore: 38,
    headline:
      "\u201CTrade war uncertainty looms as US-China negotiations resume\u201D",
  },
  {
    outlet: "Al Jazeera",
    lean: "Center-Left",
    leanScore: 35,
    headline:
      "\u201CGlobal markets brace as superpowers return to negotiating table\u201D",
  },
  {
    outlet: "New York Post",
    lean: "Right",
    leanScore: 74,
    headline:
      "\u201CBiden caves to China pressure, agrees to new round of trade talks\u201D",
  },
];

const SIX_AXES: {
  name: string;
  brief: string;
  score: number;
  signals: string;
  sample: string;
}[] = [
  {
    name: "Political Lean",
    brief: "Where the article falls on the spectrum.",
    score: 42,
    signals:
      "Keyword lexicons, entity sentiment (NER + TextBlob), framing phrases, length-adaptive + sparsity-weighted source baseline blending.",
    sample:
      "The <mark>administration</mark> defended the <mark>crackdown</mark> as necessary to <mark>restore order</mark>.",
  },
  {
    name: "Sensationalism",
    brief: "How much urgency is inflated beyond the facts.",
    score: 28,
    signals:
      "Clickbait patterns, superlative density, TextBlob extremity, partisan attack density (capped 30 pts).",
    sample:
      "The <mark>unprecedented</mark> move sent <mark>shockwaves</mark> through the <mark>entire</mark> industry.",
  },
  {
    name: "Opinion vs. Reporting",
    brief: "Whether it reports facts or argues a position.",
    score: 15,
    signals:
      "First-person pronouns, subjectivity score, attribution density (24 investigative patterns), value judgments, rhetorical questions.",
    sample:
      "<mark>I believe</mark> the decision <mark>should have been</mark> made earlier. <mark>Don\u2019t you agree?</mark>",
  },
  {
    name: "Factual Rigor",
    brief: "How thoroughly it cites named sources and data.",
    score: 78,
    signals:
      "Named sources via NER + attribution verbs, org citations, data patterns, direct quotes, vague-source penalty.",
    sample:
      "<mark>Treasury Secretary Janet Yellen</mark> told reporters at the <mark>G7 summit</mark> that <mark>2.3% GDP growth</mark> was expected.",
  },
  {
    name: "Framing",
    brief: "Whether word choices nudge the reader.",
    score: 31,
    signals:
      "50+ charged synonym pairs, cluster-aware omission detection, headline-body divergence, passive voice (capped 30).",
    sample:
      "Protestors <mark>clashed with</mark> police vs. Police <mark>dispersed</mark> the crowd.",
  },
  {
    name: "Outlet Tracking",
    brief: "How each outlet covers each topic over time.",
    score: 55,
    signals:
      "Per-topic per-outlet EMA with adaptive alpha (0.3 new / 0.15 established). Stored across pipeline runs.",
    sample:
      "Fox News on immigration: <mark>lean 68 avg</mark> over 30 days (12 articles). CNN: <mark>lean 35 avg</mark>.",
  },
];

const RANKING_SIGNALS = [
  { name: "Source Breadth", weight: 20 },
  { name: "Maturity", weight: 16 },
  { name: "Tier Diversity", weight: 13 },
  { name: "Consequentiality", weight: 10 },
  { name: "Institutional Authority", weight: 8 },
];

const PRODUCT_FAMILY = [
  { cli: "void --news", desc: "The Feed", href: "/" },
  { cli: "void --tl;dr", desc: "Daily Brief", href: "/" },
  { cli: "void --onair", desc: "Audio Broadcast", href: "/" },
  { cli: "void --paper", desc: "E-Paper Edition", href: "/paper" },
  { cli: "void --sources", desc: "Source Spectrum", href: "/sources" },
  { cli: "void --deep-dive", desc: "Deep Dive Analysis", href: "/" },
];

const NUMBERS = [
  { value: "1,013", label: "sources" },
  { value: "6", label: "axes" },
  { value: "4", label: "editions" },
  { value: "$0", label: "cost" },
  { value: "4\u00D7", label: "daily" },
  { value: "0", label: "accounts required" },
];

const LANDSCAPE = [
  {
    them: "AllSides rates the outlet.",
    us: "void --news reads the article.",
  },
  {
    them: "Ground News tracks metadata.",
    us: "void --news analyzes the text.",
  },
  {
    them: "NewsGuard scores once.",
    us: "void --news scores every article, every day.",
  },
];

/* ── Organic Divider SVG (hand-drawn wobble path) ── */
function OrganicDivider() {
  return (
    <svg
      className="about-divider"
      viewBox="0 0 600 4"
      preserveAspectRatio="none"
      aria-hidden="true"
      style={{ "--divider-len": 600 } as React.CSSProperties}
    >
      <path d="M0,2 C50,0.5 100,3.5 150,2 C200,0.5 250,3 300,2 C350,1 400,3.5 450,2 C500,0.5 550,3 600,2" />
    </svg>
  );
}

/* ── Ink Droplet ── */
function InkDroplet() {
  return (
    <div className="about-ink-droplet">
      <div className="about-ink-droplet__dot" />
    </div>
  );
}

/* ── Source Density SVG (subtle height-map above spectrum bar) ── */
function SourceDensitySVG() {
  return (
    <svg
      className="about-spectrum__density"
      viewBox="0 0 400 32"
      preserveAspectRatio="none"
      aria-hidden="true"
      style={{ width: "100%" }}
    >
      <path
        d="M0,32 L0,28 C30,26 60,22 80,18 C100,14 120,16 140,12 C160,8 180,4 200,2 C220,4 240,8 260,12 C280,16 300,14 320,18 C340,22 360,26 380,28 L400,30 L400,32 Z"
        fill="currentColor"
        opacity="0.08"
      />
    </svg>
  );
}

/* ===========================================================================
   PAGE COMPONENT
   =========================================================================== */

export default function AboutPage() {
  const pageRef = useRef<HTMLDivElement>(null);
  const heroRef = useRef<HTMLElement>(null);
  const [activeAxis, setActiveAxis] = useState<number | null>(null);
  const [morphed, setMorphed] = useState(false);
  const comparisonMorphedRef = useRef(false);
  const morphTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* ── Force dark mode ── */
  useEffect(() => {
    const html = document.documentElement;
    const prev = html.getAttribute("data-mode");
    html.setAttribute("data-mode", "dark");
    return () => {
      if (prev) html.setAttribute("data-mode", prev);
    };
  }, []);

  /* ── Reduced motion check ── */
  const prefersReducedMotion = useCallback(() => {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }, []);

  /* ── Intersection Observer Architecture ── */
  useEffect(() => {
    const page = pageRef.current;
    if (!page) return;

    const cleanups: (() => void)[] = [];

    /* If reduced motion, set everything visible immediately */
    if (prefersReducedMotion()) {
      page
        .querySelectorAll<HTMLElement>(
          ".about-reveal, .about-pullquote, .about-data, .about-divergence, .about-principles, .about-axes, .about-spectrum, .about-deepdive-preview, .about-family-grid, .about-ranking__bars, .about-landscape, .about-numbers, .about-divider, .about-ink-droplet"
        )
        .forEach((el) => el.setAttribute("data-visible", "true"));
      setMorphed(true);
      return;
    }

    /* Observer 1: Hero scroll parallax (desktop only, multi-threshold) */
    const heroEl = heroRef.current;
    if (heroEl) {
      const heroIO = new IntersectionObserver(
        (entries) => {
          entries.forEach((e) => {
            if (window.innerWidth <= 768) return;
            const ratio = e.intersectionRatio;
            const scale = 0.92 + 0.08 * ratio;
            const opacity = 0.3 + 0.7 * ratio;
            heroEl.style.transform = `scale(${scale})`;
            heroEl.style.opacity = String(opacity);
            heroEl.setAttribute("data-parallax", "");
          });
        },
        { threshold: [0, 0.25, 0.5, 0.75, 1] }
      );
      heroIO.observe(heroEl);
      cleanups.push(() => heroIO.disconnect());
    }

    /* Observer 2: Section reveals — one-shot data-visible="true" */
    const revealEls = page.querySelectorAll<HTMLElement>(
      ".about-reveal, .about-divergence, .about-principles, .about-spectrum, .about-deepdive-preview, .about-family-grid, .about-ranking__bars, .about-landscape, .about-numbers"
    );
    const revealIO = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            (e.target as HTMLElement).setAttribute("data-visible", "true");
            obs.unobserve(e.target);
          }
        });
      },
      { threshold: 0.2 }
    );
    revealEls.forEach((el) => revealIO.observe(el));
    cleanups.push(() => revealIO.disconnect());

    /* Observer 3: Axes cascade */
    const axesEl = page.querySelector<HTMLElement>(".about-axes");
    if (axesEl) {
      const axesIO = new IntersectionObserver(
        (entries, obs) => {
          entries.forEach((e) => {
            if (e.isIntersecting) {
              axesEl.setAttribute("data-visible", "true");
              obs.unobserve(e.target);
            }
          });
        },
        { threshold: 0.2 }
      );
      axesIO.observe(axesEl);
      cleanups.push(() => axesIO.disconnect());
    }

    /* Observer 4: Comparison morph — threshold 0.5, 1.5s delay */
    const compEl = page.querySelector<HTMLElement>(".about-comparison");
    if (compEl) {
      const compIO = new IntersectionObserver(
        (entries, obs) => {
          entries.forEach((e) => {
            if (e.isIntersecting && !comparisonMorphedRef.current) {
              comparisonMorphedRef.current = true;
              morphTimerRef.current = setTimeout(() => {
                setMorphed(true);
              }, 1500);
              obs.unobserve(e.target);
            }
          });
        },
        { threshold: 0.5 }
      );
      compIO.observe(compEl);
      cleanups.push(() => compIO.disconnect());
    }

    /* Observer 5: Pullquote smash cut */
    const pullquotes = page.querySelectorAll<HTMLElement>(".about-pullquote");
    if (pullquotes.length) {
      const pullIO = new IntersectionObserver(
        (entries, obs) => {
          entries.forEach((e) => {
            if (e.isIntersecting) {
              (e.target as HTMLElement).setAttribute("data-visible", "true");
              obs.unobserve(e.target);
            }
          });
        },
        { threshold: 0.4 }
      );
      pullquotes.forEach((el) => pullIO.observe(el));
      cleanups.push(() => pullIO.disconnect());
    }

    /* Observer 6: Data lines wipe */
    const dataLines = page.querySelectorAll<HTMLElement>(".about-data");
    if (dataLines.length) {
      const dataIO = new IntersectionObserver(
        (entries, obs) => {
          entries.forEach((e) => {
            if (e.isIntersecting) {
              (e.target as HTMLElement).setAttribute("data-visible", "true");
              obs.unobserve(e.target);
            }
          });
        },
        { threshold: 0.5 }
      );
      dataLines.forEach((el) => dataIO.observe(el));
      cleanups.push(() => dataIO.disconnect());
    }

    /* Observer 7: Organic dividers + ink droplets */
    const organicEls = page.querySelectorAll<HTMLElement>(
      ".about-divider, .about-ink-droplet"
    );
    if (organicEls.length) {
      const organicIO = new IntersectionObserver(
        (entries, obs) => {
          entries.forEach((e) => {
            if (e.isIntersecting) {
              (e.target as HTMLElement).setAttribute("data-visible", "true");
              obs.unobserve(e.target);
            }
          });
        },
        { threshold: 0.5 }
      );
      organicEls.forEach((el) => organicIO.observe(el));
      cleanups.push(() => organicIO.disconnect());
    }

    /* Observer 8: Deep Dive preview */
    const ddPreview = page.querySelector<HTMLElement>(
      ".about-deepdive-preview"
    );
    if (ddPreview) {
      const ddIO = new IntersectionObserver(
        (entries, obs) => {
          entries.forEach((e) => {
            if (e.isIntersecting) {
              (e.target as HTMLElement).setAttribute("data-visible", "true");
              obs.unobserve(e.target);
            }
          });
        },
        { threshold: 0.3 }
      );
      ddIO.observe(ddPreview);
      cleanups.push(() => ddIO.disconnect());
    }

    return () => {
      cleanups.forEach((fn) => fn());
      if (morphTimerRef.current) clearTimeout(morphTimerRef.current);
    };
  }, [prefersReducedMotion]);

  return (
    <div className="about-page" ref={pageRef}>
      {/* ══════════════════════════════════════════════════════════════════
          ACT I: THE VOID — EMOTIONAL SETUP
          ══════════════════════════════════════════════════════════════════ */}

      {/* ── Section 1: Cold Open (Hero) ── */}
      <section className="about-hero" ref={heroRef} aria-label="Hero">
        <div className="about-hero__halo" aria-hidden="true" />
        <div className="about-hero__glow" aria-hidden="true" />
        <div className="about-hero__mark">
          <LogoIcon size={120} animation="idle" />
        </div>
        <h1 className="about-hero__tagline">See through the void.</h1>
        <div className="about-hero__scroll" aria-hidden="true">
          <span className="about-hero__chevron" />
        </div>
      </section>

      {/* ── Section 2: The Problem ── */}
      <section className="about-section" aria-label="The Problem">
        <div className="about-section__inner">
          <div className="about-reveal">
            <p className="about-body about-body--lead about-body--stagger">
              The same event. Five outlets. Five different realities.
            </p>
            <p className="about-body about-body--stagger">
              One calls it a &ldquo;crackdown.&rdquo; Another calls it
              &ldquo;restoring order.&rdquo; A third doesn&rsquo;t cover it at
              all. The headline says one thing; the article says another. The
              source is &ldquo;officials
              say&rdquo;&thinsp;&mdash;&thinsp;no name, no title, no
              accountability.
            </p>
          </div>

          <blockquote className="about-pullquote">This is the void.</blockquote>

          <InkDroplet />

          <div className="about-reveal">
            <p className="about-body about-body--stagger">
              Not the absence of information&thinsp;&mdash;&thinsp;the opposite.
              A flood of it, shaped by incentive, refracted through ideology,
              optimized for the click that keeps you inside the bubble you
              didn&rsquo;t choose.
            </p>
            <p className="about-body about-body--stagger">
              You already know it&rsquo;s there. You feel it every time you read
              a headline and wonder: who decided this was the story? What am I
              not seeing?
            </p>
          </div>

          {/* Live Divergence Demo */}
          <div
            className="about-divergence"
            aria-label="Divergence demo: same event, different headlines"
          >
            <p className="about-divergence__event">
              Same event &mdash; US-China trade negotiations resume
            </p>
            <div className="about-divergence__list" role="list">
              {DIVERGENCE_HEADLINES.map((h) => (
                <div
                  key={h.outlet}
                  className="about-divergence__card"
                  role="listitem"
                >
                  <div className="about-divergence__source">
                    <span className="about-divergence__outlet">
                      {h.outlet}
                    </span>
                    <span className="about-divergence__lean-badge">
                      {h.lean} &middot; {h.leanScore}
                    </span>
                  </div>
                  <p className="about-divergence__headline">{h.headline}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <OrganicDivider />

      {/* ── Section 3: First Principles ── */}
      <section className="about-section" aria-label="First Principles">
        <div className="about-section__inner">
          <div className="about-principles" role="list">
            <div className="about-principle" role="listitem">
              <p className="about-principle__text">
                Every reader sees the same stories in the same order.
              </p>
            </div>
            <div className="about-principle" role="listitem">
              <p className="about-principle__text">
                Every score traces to specific words in the text.
              </p>
            </div>
            <div className="about-principle" role="listitem">
              <p className="about-principle__text">
                Every feature is free. There is no premium tier. There never
                will be.
              </p>
            </div>
          </div>
        </div>
      </section>

      <OrganicDivider />

      {/* ══════════════════════════════════════════════════════════════════
          ACT II: THE INSTRUMENT — PRODUCT SHOWCASE
          ══════════════════════════════════════════════════════════════════ */}

      {/* ── Section 4: The Six Axes — Interactive ── */}
      <section
        className="about-section about-section--act2"
        aria-label="The Six Axes"
      >
        <div className="about-section__inner">
          <p className="about-section-label">The Instrument</p>
          <div className="about-reveal">
            <p className="about-body about-body--lead">
              Six dimensions. Zero black boxes.
            </p>
          </div>

          <div className="about-axes" role="list">
            {SIX_AXES.map((axis, i) => {
              const isActive = activeAxis === i;
              return (
                <div
                  key={axis.name}
                  className={`about-axis${isActive ? " about-axis--active" : ""}`}
                  role="listitem"
                  tabIndex={0}
                  aria-expanded={isActive}
                  onClick={() => setActiveAxis(isActive ? null : i)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      setActiveAxis(isActive ? null : i);
                    }
                  }}
                >
                  <div className="about-axis__header">
                    <span className="about-axis__name">{axis.name}</span>
                  </div>
                  {!isActive && (
                    <p className="about-axis__brief">{axis.brief}</p>
                  )}
                  {isActive && (
                    <div className="about-axis__detail">
                      <div className="about-axis__score-label">
                        <span>0</span>
                        <span className="about-axis__score-value">
                          {axis.score}/100
                        </span>
                        <span>100</span>
                      </div>
                      <div className="about-axis__score-bar">
                        <div
                          className="about-axis__score-fill"
                          style={
                            {
                              "--bar-fill": axis.score / 100,
                            } as React.CSSProperties
                          }
                        />
                      </div>
                      <p className="about-axis__signals">{axis.signals}</p>
                      <p
                        className="about-axis__sample"
                        dangerouslySetInnerHTML={{ __html: axis.sample }}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ── Section 5: The Source Spectrum ── */}
      <section
        className="about-section about-section--act2"
        aria-label="The Source Spectrum"
      >
        <div className="about-section__inner">
          <div className="about-reveal">
            <p className="about-body about-body--lead">
              1,013 sources. 158 countries. One spectrum.
            </p>
          </div>

          <div className="about-spectrum">
            <SourceDensitySVG />
            <div
              className="about-spectrum__bar"
              role="img"
              aria-label="Political lean spectrum from far-left to far-right"
            />
            <p className="about-spectrum__stats">
              1,013 sources &middot; 158 countries &middot; 43 US major &middot;
              373 international &middot; 597 independent
            </p>
            <p className="about-spectrum__stats-secondary">
              Left:Right ratio 1.23:1 &middot; 38 wire services &middot; 10
              fact-checkers
            </p>
          </div>
        </div>
      </section>

      <InkDroplet />

      {/* ── Section 6: The Difference — Interactive Morph ── */}
      <section
        className="about-section about-section--act2"
        aria-label="The Difference"
      >
        <div className="about-section__inner">
          <div className="about-reveal">
            <p className="about-body about-body--lead">
              Other tools label the outlet.
              <br />
              We read the article.
            </p>
          </div>

          <div
            className={`about-comparison${morphed ? " about-comparison--morphed" : ""}`}
            aria-label="Comparison: outlet label versus per-article scoring"
          >
            <div className="about-comparison__them">
              <span className="about-comparison__label">Outlet label</span>
              <span className="about-comparison__value--them">
                &ldquo;Left&rdquo;
              </span>
            </div>
            <div className="about-comparison__vs" aria-hidden="true">
              vs
            </div>
            <div className="about-comparison__us">
              <span className="about-comparison__label">Per-article score</span>
              <div className="about-comparison__scores">
                {[
                  { name: "Lean", value: 42 },
                  { name: "Rigor", value: 78 },
                  { name: "Tone", value: 18 },
                  { name: "Framing", value: 31 },
                ].map((s) => (
                  <div key={s.name} className="about-comparison__score-row">
                    <span className="about-comparison__score-name">
                      {s.name}
                    </span>
                    <div className="about-comparison__score-bar-track">
                      <div
                        className="about-comparison__score-bar-fill"
                        style={
                          {
                            "--bar-fill": s.value / 100,
                          } as React.CSSProperties
                        }
                      />
                    </div>
                    <span className="about-comparison__score-num">
                      {s.value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="about-reveal">
            <p className="about-body about-body--small">
              An outlet rated &ldquo;Left&rdquo; published this article with a
              center-right lean, high factual rigor, and minimal framing. The
              outlet label would have told you to distrust it. The article itself
              earned that trust back.
            </p>
            <p className="about-body about-body--emphasis">
              Per article. Not per outlet. That is the difference.
            </p>
          </div>
        </div>
      </section>

      <OrganicDivider />

      {/* ══════════════════════════════════════════════════════════════════
          ACT III: THE EXPERIENCE — FEATURE TOUR
          ══════════════════════════════════════════════════════════════════ */}

      {/* ── Section 7: Deep Dive Preview ── */}
      <section
        className="about-section about-section--act3"
        aria-label="The Deep Dive"
      >
        <div className="about-section__inner">
          <p className="about-section-label">The Deep Dive</p>
          <div className="about-reveal">
            <p className="about-body about-body--lead">
              Click any story. See every angle.
            </p>
          </div>

          <div
            className="about-deepdive-preview"
            aria-label="Deep Dive preview mockup"
          >
            <p className="about-deepdive-preview__headline">
              US-China trade negotiations resume after six-month pause
            </p>
            <div className="about-deepdive-preview__spectrum">
              <div
                className="about-deepdive-preview__dot"
                style={{ left: "35%" }}
                aria-label="Source at center-left position"
              />
              <div
                className="about-deepdive-preview__dot"
                style={{ left: "48%" }}
                aria-label="Source at center position"
              />
              <div
                className="about-deepdive-preview__dot"
                style={{ left: "62%" }}
                aria-label="Source at center-right position"
              />
              <div
                className="about-deepdive-preview__dot"
                style={{ left: "72%" }}
                aria-label="Source at right position"
              />
              <div
                className="about-deepdive-preview__dot"
                style={{ left: "38%" }}
                aria-label="Source at center-left position"
              />
            </div>
            <div className="about-deepdive-preview__scores">
              {[
                { label: "Lean", value: "42" },
                { label: "Rigor", value: "78" },
                { label: "Tone", value: "18" },
                { label: "Framing", value: "31" },
              ].map((s) => (
                <div key={s.label} className="about-deepdive-preview__score">
                  <span className="about-deepdive-preview__score-label">
                    {s.label}
                  </span>
                  <span className="about-deepdive-preview__score-value">
                    {s.value}
                  </span>
                </div>
              ))}
            </div>
            <p className="about-deepdive-preview__caption">
              How five outlets frame the same event. Where they agree. Where they
              diverge.
            </p>
          </div>
        </div>
      </section>

      {/* ── Section 8: Product Family Grid ── */}
      <section
        className="about-section about-section--act3"
        aria-label="Product Family"
      >
        <div className="about-section__inner" style={{ maxWidth: "72ch" }}>
          <div className="about-reveal">
            <p className="about-body about-body--lead">The void suite.</p>
          </div>

          <div className="about-family-grid" role="list">
            {PRODUCT_FAMILY.map((p) => (
              <Link
                key={p.cli}
                href={p.href}
                className="about-family-card"
                role="listitem"
              >
                <p className="about-family-card__name">{p.cli}</p>
                <p className="about-family-card__desc">{p.desc}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <InkDroplet />

      {/* ── Section 9: The Ranking ── */}
      <section
        className="about-section about-section--act3"
        aria-label="The Ranking"
      >
        <div className="about-section__inner">
          <div className="about-reveal">
            <p className="about-body about-body--lead">
              Importance, not popularity.
            </p>
          </div>

          <div className="about-ranking">
            <div className="about-ranking__bars" role="list">
              {RANKING_SIGNALS.map((s) => (
                <div
                  key={s.name}
                  className="about-ranking__row"
                  role="listitem"
                >
                  <span className="about-ranking__signal">{s.name}</span>
                  <div className="about-ranking__bar-track">
                    <div
                      className="about-ranking__bar-fill"
                      style={
                        {
                          "--bar-fill": s.weight / 20,
                        } as React.CSSProperties
                      }
                    />
                  </div>
                  <span className="about-ranking__weight">{s.weight}%</span>
                </div>
              ))}
            </div>
            <p className="about-ranking__caption">
              11 signals. Zero engagement metrics. The algorithm decides what
              matters&thinsp;&mdash;&thinsp;not what gets clicked.
            </p>
          </div>
        </div>
      </section>

      <OrganicDivider />

      {/* ══════════════════════════════════════════════════════════════════
          ACT IV: THE INVITATION
          ══════════════════════════════════════════════════════════════════ */}

      {/* ── Section 10: The Landscape (Competitive) ── */}
      <section
        className="about-section about-section--act4"
        aria-label="The Landscape"
      >
        <div className="about-section__inner">
          <div className="about-landscape" role="list">
            {LANDSCAPE.map((l) => (
              <div
                key={l.them}
                className="about-landscape__pair"
                role="listitem"
              >
                <p className="about-landscape__them">{l.them}</p>
                <p className="about-landscape__us">{l.us}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Section 11: The Numbers ── */}
      <section
        className="about-section about-section--act4"
        aria-label="The Numbers"
      >
        <div className="about-section__inner" style={{ maxWidth: "72ch" }}>
          <div className="about-numbers" role="list">
            {NUMBERS.map((n, i) => (
              <span
                key={n.label}
                className="about-numbers__item"
                role="listitem"
              >
                <span className="about-numbers__value">{n.value}</span>{" "}
                {n.label}
                {i < NUMBERS.length - 1 && (
                  <span className="about-numbers__sep" aria-hidden="true">
                    &middot;
                  </span>
                )}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Section 12: CTA ── */}
      <section
        className="about-section about-section--act4 about-cta"
        aria-label="Call to action"
      >
        <div className="about-section__inner">
          <div className="about-reveal" style={{ textAlign: "center" }}>
            <div className="about-cta__mark">
              <LogoIcon size={56} animation="idle" />
            </div>
            <div className="about-cta__wordmark">
              <LogoWordmark height={24} />
            </div>
            <p className="about-cta__tagline">See through the void.</p>
            <Link href="/" className="about-cta__button">
              Read today&rsquo;s edition
            </Link>
            <p className="about-cta__sub">
              No signup. No paywall. No tracking.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
