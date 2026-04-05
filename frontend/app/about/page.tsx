"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import LogoIcon from "../components/LogoIcon";
import LogoWordmark from "../components/LogoWordmark";
import {
  CHAPTERS, SIX_AXES, FIRST_PRINCIPLES,
} from "../film/data";
import DivergentHeadlines from "../film/scenes/DivergentHeadlines";
import SigilBreakdown from "../film/scenes/SigilBreakdown";
import SourceEngine from "../film/scenes/SourceEngine";
import ArticleDifference from "../film/scenes/ArticleDifference";
import ProductWorlds from "../film/scenes/ProductWorlds";
import TheVerdict from "../film/scenes/TheVerdict";

/* ===========================================================================
   /about — "The Film: Director's Cut"

   Unified manifesto page. Same 6 chapters as the prologue (onboarding),
   rendered in manifesto mode with extended content, interactive demos,
   and scroll-driven IO reveals.

   Content data: film/data.ts (single source of truth).
   Scene visuals: film/scenes/*.tsx (shared with prologue).
   =========================================================================== */

const MODE = "manifesto" as const;

/* ── Organic Divider ── */
function OrganicDivider() {
  return (
    <svg className="about-divider" viewBox="0 0 600 4" preserveAspectRatio="none" aria-hidden="true"
      style={{ "--divider-len": 600 } as React.CSSProperties}>
      <path d="M0,2 C50,0.5 100,3.5 150,2 C200,0.5 250,3 300,2 C350,1 400,3.5 450,2 C500,0.5 550,3 600,2" />
    </svg>
  );
}

export default function AboutPage() {
  const pageRef = useRef<HTMLDivElement>(null);
  const [activeAxis, setActiveAxis] = useState<number | null>(null);
  const [sectionsVisible, setSectionsVisible] = useState<Set<string>>(new Set());

  /* ── Mark section visible (IO triggers) ── */
  const markVisible = (id: string) => {
    setSectionsVisible((prev) => {
      if (prev.has(id)) return prev;
      const next = new Set(prev);
      next.add(id);
      return next;
    });
  };

  /* ── Intersection Observer — one-shot reveals ── */
  useEffect(() => {
    const page = pageRef.current;
    if (!page) return;

    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) {
      // Show everything immediately
      page.querySelectorAll<HTMLElement>("[data-film-section]").forEach((el) => {
        markVisible(el.dataset.filmSection!);
      });
      return;
    }

    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            const id = (e.target as HTMLElement).dataset.filmSection;
            if (id) markVisible(id);
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.2 }
    );

    page.querySelectorAll<HTMLElement>("[data-film-section]").forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  const isVisible = (id: string) => sectionsVisible.has(id);

  return (
    <div className="about-page" ref={pageRef}>
      {/* Back nav */}
      <Link href="/" className="pwa-back" aria-label="Back to news feed">
        <span aria-hidden="true">&larr;</span> News Feed
      </Link>

      {/* ══════════════════════════════════════════════════════════════════
          COLD OPEN — Hero
          ══════════════════════════════════════════════════════════════════ */}
      <section className="about-hero" aria-label="Hero">
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

      {/* ══════════════════════════════════════════════════════════════════
          CHAPTER I — The Void
          ══════════════════════════════════════════════════════════════════ */}
      <section id="the-void" className="about-section" aria-label="The Void" data-film-section="void">
        <div className="about-section__inner">
          <p className="about-section-label">{CHAPTERS[0].roman}</p>
          <div className="about-reveal" data-visible={isVisible("void") || undefined}>
            <p className="about-body about-body--lead">{CHAPTERS[0].prologueBody}</p>
            {CHAPTERS[0].manifestoLead && (
              <p className="about-body about-body--stagger">{CHAPTERS[0].manifestoLead}</p>
            )}
          </div>

          <blockquote className="about-pullquote" data-visible={isVisible("void") || undefined}>
            This is the void.
          </blockquote>

          {/* Shared scene: divergent headlines */}
          <DivergentHeadlines mode={MODE} active={isVisible("void")} />
        </div>
      </section>

      {/* First Principles */}
      <section className="about-section" aria-label="First Principles" data-film-section="principles">
        <div className="about-section__inner">
          <div className="about-principles" role="list" data-visible={isVisible("principles") || undefined}>
            {FIRST_PRINCIPLES.map((p) => (
              <div key={p} className="about-principle" role="listitem">
                <p className="about-principle__text">{p}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <OrganicDivider />

      {/* ══════════════════════════════════════════════════════════════════
          CHAPTER II — The Instrument
          ══════════════════════════════════════════════════════════════════ */}
      <section id="the-instrument" className="about-section about-section--act2" aria-label="The Instrument" data-film-section="instrument">
        <div className="about-section__inner">
          <p className="about-section-label">{CHAPTERS[1].roman}</p>
          <div className="about-reveal" data-visible={isVisible("instrument") || undefined}>
            <p className="about-body about-body--lead">{CHAPTERS[1].prologueBody}</p>
          </div>

          {/* Shared scene: Sigil exploded-view breakdown */}
          <SigilBreakdown mode={MODE} active={isVisible("instrument")} />

          {/* Manifesto extension: Six Axes interactive accordion */}
          <div className="about-axes" role="list" data-film-section="axes" data-visible={isVisible("axes") || undefined}>
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
                  {!isActive && <p className="about-axis__brief">{axis.brief}</p>}
                  {isActive && (
                    <div className="about-axis__detail">
                      <div className="about-axis__score-label">
                        <span>0</span>
                        <span className="about-axis__score-value">{axis.score}/100</span>
                        <span>100</span>
                      </div>
                      <div className="about-axis__score-bar">
                        <div className="about-axis__score-fill" style={{ "--bar-fill": axis.score / 100 } as React.CSSProperties} />
                      </div>
                      <p className="about-axis__signals">{axis.signals}</p>
                      <p className="about-axis__sample" dangerouslySetInnerHTML={{ __html: axis.sample }} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <OrganicDivider />

      {/* ══════════════════════════════════════════════════════════════════
          CHAPTER III — The Engine
          ══════════════════════════════════════════════════════════════════ */}
      <section id="the-engine" className="about-section about-section--act2" aria-label="The Engine" data-film-section="engine">
        <div className="about-section__inner">
          <p className="about-section-label">{CHAPTERS[2].roman}</p>
          <div className="about-reveal" data-visible={isVisible("engine") || undefined}>
            <p className="about-body about-body--lead">{CHAPTERS[2].subtitle}</p>
          </div>

          {/* Shared scene: ranking + source spectrum */}
          <SourceEngine mode={MODE} active={isVisible("engine")} />
        </div>
      </section>

      <OrganicDivider />

      {/* ══════════════════════════════════════════════════════════════════
          CHAPTER IV — The Difference
          ══════════════════════════════════════════════════════════════════ */}
      <section id="the-difference" className="about-section about-section--act2" aria-label="The Difference" data-film-section="difference">
        <div className="about-section__inner">
          <p className="about-section-label">{CHAPTERS[3].roman}</p>
          <div className="about-reveal" data-visible={isVisible("difference") || undefined}>
            <p className="about-body about-body--lead">
              They rate the outlet.<br />We read the article.
            </p>
          </div>

          {/* Shared scene: comparison morph + competitive landscape */}
          <ArticleDifference mode={MODE} active={isVisible("difference")} />

          <div className="about-reveal" data-visible={isVisible("difference") || undefined}>
            <p className="about-body about-body--emphasis">
              Per article. Not per outlet. That is the difference.
            </p>
          </div>
        </div>
      </section>

      <OrganicDivider />

      {/* ══════════════════════════════════════════════════════════════════
          CHAPTER V — The Worlds
          ══════════════════════════════════════════════════════════════════ */}
      <section id="the-worlds" className="about-section about-section--act3" aria-label="The Worlds" data-film-section="worlds">
        <div className="about-section__inner" style={{ maxWidth: "72ch" }}>
          <p className="about-section-label">{CHAPTERS[4].roman}</p>
          <div className="about-reveal" data-visible={isVisible("worlds") || undefined}>
            <p className="about-body about-body--lead">The void suite.</p>
            <p className="about-body about-body--stagger">{CHAPTERS[4].prologueBody}</p>
          </div>

          {/* Shared scene: product family grid */}
          <ProductWorlds mode={MODE} active={isVisible("worlds")} />
        </div>
      </section>

      <OrganicDivider />

      {/* ══════════════════════════════════════════════════════════════════
          CHAPTER VI — The Verdict
          ══════════════════════════════════════════════════════════════════ */}
      <section id="the-verdict" className="about-section about-section--act4 about-cta" aria-label="The Verdict" data-film-section="verdict">
        <div className="about-section__inner">
          <div className="about-reveal" data-visible={isVisible("verdict") || undefined} style={{ textAlign: "center" }}>
            <p className="about-section-label">{CHAPTERS[5].roman}</p>
            <p className="about-body about-body--lead">{CHAPTERS[5].headline}</p>
            <p className="about-body">{CHAPTERS[5].prologueBody}</p>
          </div>

          {/* Shared scene: 3 Sigils + numbers */}
          <TheVerdict mode={MODE} active={isVisible("verdict")} />

          {/* CTA */}
          <div className="about-reveal" data-visible={isVisible("verdict") || undefined} style={{ textAlign: "center", marginTop: "var(--space-6)" }}>
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
