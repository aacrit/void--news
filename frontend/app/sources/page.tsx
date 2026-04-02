"use client";

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import Link from "next/link";
import type { Edition } from "../lib/types";
import { supabase, supabaseError } from "../lib/supabase";
import SpectrumChart, { type SpectrumSource, normalizeLean } from "../components/SpectrumChart";
import ThemeToggle from "../components/ThemeToggle";
import PageToggle from "../components/PageToggle";
import EditionIcon from "../components/EditionIcon";
import LogoFull from "../components/LogoFull";
import LogoIcon from "../components/LogoIcon";
import Footer from "../components/Footer";
import { getEditionTimeOfDay, getEditionTimestamp } from "../lib/utils";
import ErrorBoundary from "../components/ErrorBoundary";
import { useInView } from "../lib/sharedObserver";

/* ---------------------------------------------------------------------------
   Sources Page — /sources
   Visualizes all curated news sources on a political lean spectrum.
   Desktop: horizontal spectrum bar with logos above/below.
   Mobile: horizontal swipeable card strip with scroll-snap.
   --------------------------------------------------------------------------- */

type LeanCategory =
  | "far-left" | "left" | "center-left" | "center"
  | "center-right" | "right" | "far-right";

type LeanFilter = "All" | "Left" | "Center" | "Right";

const EDITIONS: { slug: Edition; label: string }[] = [
  { slug: "world", label: "World" },
  { slug: "us", label: "US" },
  { slug: "india", label: "India" },
];

const EDITION_COUNTRIES: Record<Edition, string[] | null> = {
  world: null,
  us: ["US"],
  india: ["IN"],
};

const LEAN_FILTERS: LeanFilter[] = ["Left", "Center", "Right"];

const LEAN_ALLOWED: Record<LeanFilter, LeanCategory[] | null> = {
  All: null,
  Left: ["far-left", "left", "center-left"],
  Center: ["center"],
  Right: ["center-right", "right", "far-right"],
};

const LEAN_DOT_COLOR: Record<string, string> = {
  Left: "var(--bias-left)",
  Center: "var(--bias-center)",
  Right: "var(--bias-right)",
};

/* ---------------------------------------------------------------------------
   Methodology Section — comprehensive trust anchor
   Six sections: Per-Article, Six Axes, Worked Example, Validation,
   Curated Sources, Open Source.
   --------------------------------------------------------------------------- */

const AXES_DATA: {
  id: string;
  name: string;
  range: string;
  low: string;
  high: string;
  what: string;
  signals: string[];
  file: string;
}[] = [
  {
    id: "lean",
    name: "Political Lean",
    range: "0\u2013100",
    low: "Far Left",
    high: "Far Right",
    what: "Where an article lands on the left\u2013right spectrum, independent of its outlet\u2019s reputation.",
    signals: [
      "Keyword lexicons scored against curated left/right phrase lists",
      "Named-entity sentiment via spaCy NER + TextBlob polarity",
      "Framing phrases that signal ideological perspective",
      "Length-adaptive + sparsity-weighted source baseline blending",
    ],
    file: "pipeline/analyzers/political_lean.py",
  },
  {
    id: "sensationalism",
    name: "Sensationalism",
    range: "0\u2013100",
    low: "Measured",
    high: "Inflammatory",
    what: "How much the article inflates urgency, emotion, or outrage beyond what the facts warrant.",
    signals: [
      "Clickbait headline patterns (questions, listicles, superlatives)",
      "Superlative density via word-boundary regex",
      "TextBlob emotional extremity score",
      "Partisan attack density (capped at 30 points)",
    ],
    file: "pipeline/analyzers/sensationalism.py",
  },
  {
    id: "opinion",
    name: "Opinion vs Reporting",
    range: "0\u2013100",
    low: "Hard Reporting",
    high: "Editorial",
    what: "Whether the article reports facts or argues a position. 50 marks the analysis midpoint.",
    signals: [
      "First- and second-person pronoun frequency",
      "TextBlob subjectivity score",
      "Attribution density (24 investigative verb patterns)",
      "Value judgments and rhetorical questions",
    ],
    file: "pipeline/analyzers/opinion_detector.py",
  },
  {
    id: "rigor",
    name: "Factual Rigor",
    range: "0\u2013100",
    low: "Unsourced",
    high: "Well-sourced",
    what: "How thoroughly an article cites named sources, data, and direct quotes.",
    signals: [
      "Named sources detected via spaCy NER + attribution verbs",
      "Organizational citations (agencies, institutions)",
      "Data patterns (percentages, dollar figures, dates)",
      "Direct quotes count; vague-source penalty (\u201cofficials say\u201d)",
    ],
    file: "pipeline/analyzers/factual_rigor.py",
  },
  {
    id: "framing",
    name: "Framing",
    range: "0\u2013100",
    low: "Neutral",
    high: "Heavy Framing",
    what: "Whether word choices, omissions, or structural decisions nudge the reader toward a conclusion.",
    signals: [
      "Charged synonym detection (50+ curated word pairs)",
      "Cluster-aware omission analysis (what peers cover that this article skips)",
      "Headline\u2013body divergence score",
      "Passive voice frequency (capped at 30 points)",
    ],
    file: "pipeline/analyzers/framing.py",
  },
  {
    id: "tracking",
    name: "Outlet Tracking",
    range: "Adaptive",
    low: "New outlet",
    high: "Established",
    what: "A per-topic, per-outlet exponential moving average (EMA) that tracks how each outlet covers each topic over time.",
    signals: [
      "Adaptive alpha: 0.3 for new outlets, 0.15 for established",
      "Topic-specific tracking (an outlet\u2019s economy coverage vs. its foreign policy coverage)",
      "Stored in source_topic_lean table",
      "Smooths single-article noise into a reliable baseline",
    ],
    file: "pipeline/analyzers/topic_outlet_tracker.py",
  },
];

const WORKED_EXAMPLE = {
  headline: "Senate Passes Emergency Spending Bill After Marathon Session",
  source: "Associated Press",
  scores: [
    { axis: "Political Lean", score: 48, color: "var(--fg-secondary)", label: "Center", detail: "Neutral framing, balanced quote selection (3 Democratic, 3 Republican sources), no loaded modifiers." },
    { axis: "Sensationalism", score: 18, color: "var(--fg-secondary)", label: "Measured", detail: "\u201cMarathon session\u201d is the only heightened phrase. No superlatives, no clickbait patterns, no partisan attacks." },
    { axis: "Opinion vs Reporting", score: 12, color: "var(--fg-secondary)", label: "Hard reporting", detail: "Zero first-person pronouns. 8 direct attributions. No value judgments or rhetorical questions." },
    { axis: "Factual Rigor", score: 82, color: "var(--accent-warm)", label: "Well-sourced", detail: "6 named sources, 2 org citations (CBO, OMB), 4 direct quotes, specific dollar figures and vote counts." },
    { axis: "Framing", score: 15, color: "var(--fg-secondary)", label: "Neutral", detail: "No charged synonyms detected. Headline matches body content. Active voice throughout." },
    { axis: "Outlet Tracking", score: null, color: "var(--fg-muted)", label: "EMA: 47.2", detail: "AP\u2019s economy coverage averages 47.2 (center) across 342 tracked articles on this topic." },
  ],
};

function AxisAccordion({ axis }: { axis: typeof AXES_DATA[number] }) {
  const [open, setOpen] = useState(false);
  const panelId = `meth-axis-${axis.id}`;

  return (
    <div className={`meth-axis${open ? " meth-axis--open" : ""}`}>
      <button
        className="meth-axis__trigger"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        aria-controls={panelId}
      >
        <span className="meth-axis__name">{axis.name}</span>
        <span className="meth-axis__range">{axis.range}</span>
        <span className="meth-axis__scale">
          <span className="meth-axis__scale-low">{axis.low}</span>
          <span className="meth-axis__scale-arrow" aria-hidden="true">&rarr;</span>
          <span className="meth-axis__scale-high">{axis.high}</span>
        </span>
        <span className="meth-axis__chevron" aria-hidden="true">{"\u25B8"}</span>
      </button>
      <div
        className={`meth-axis__panel${open ? " meth-axis__panel--open" : ""}`}
        id={panelId}
        role="region"
        aria-label={`${axis.name} details`}
        aria-hidden={!open}
      >
        <div className="meth-axis__panel-inner">
          <p className="meth-axis__what">{axis.what}</p>
          <ul className="meth-axis__signals">
            {axis.signals.map((s, i) => (
              <li key={i} className="meth-axis__signal">{s}</li>
            ))}
          </ul>
          <p className="meth-axis__file">
            <code>{axis.file}</code>
          </p>
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------------
   MethSection — scroll-revealed section wrapper.
   Uses useInView to trigger the dolly entrance animation when the section
   scrolls into the viewport. Stagger delay is set via CSS custom property.
   --------------------------------------------------------------------------- */

function MethSection({
  index,
  className = "",
  children,
}: {
  index: number;
  className?: string;
  children: React.ReactNode;
}) {
  const [ref, visible] = useInView<HTMLDivElement>();
  const staggerDelay = `${index * 80}ms`;
  return (
    <div
      ref={ref}
      className={`meth__section${visible ? " meth__section--visible" : ""}${className ? ` ${className}` : ""}`}
      style={{ "--meth-stagger-delay": staggerDelay } as React.CSSProperties}
    >
      {children}
    </div>
  );
}

/* ---------------------------------------------------------------------------
   ValidationGrid — stat numbers with staggered fade-settle entrance.
   Each stat gets its own IO-driven visibility and a stagger delay.
   --------------------------------------------------------------------------- */

const VALIDATION_STATS = [
  { number: "42", label: "Ground-truth articles" },
  { number: "9", label: "Categories tested" },
  { number: "100%", label: "Accuracy" },
  { number: "r\u2009<\u20090.70", label: "Cross-axis correlation gate" },
];

function ValidationStat({ stat, index }: { stat: typeof VALIDATION_STATS[number]; index: number }) {
  const [ref, visible] = useInView<HTMLDivElement>();
  return (
    <div
      ref={ref}
      className={`meth__validation-stat${visible ? " meth__validation-stat--visible" : ""}`}
      style={{ "--meth-stat-delay": `${index * 100}ms` } as React.CSSProperties}
    >
      <span className="meth__validation-number">{stat.number}</span>
      <span className="meth__validation-label">{stat.label}</span>
    </div>
  );
}

function Methodology() {
  /* Rule curtain-pull entrance */
  const [ruleRef, ruleVisible] = useInView<HTMLDivElement>();

  return (
    <section id="methodology" className="meth" aria-label="Methodology">
      <div
        ref={ruleRef}
        className={`meth__rule${ruleVisible ? " meth__rule--visible" : ""}`}
        aria-hidden="true"
      />

      <header className="meth__header">
        <h2 className="meth__title">Methodology</h2>
        <p className="meth__subtitle">How void --news scores every article</p>
      </header>

      {/* ---- Section 1: Per-Article ---- */}
      <MethSection index={0}>
        <h3 className="meth__section-title">Per-Article, Not Per-Outlet</h3>
        <p className="meth__body">
          Most bias tools rate outlets. The New York Times is &ldquo;Lean Left&rdquo;
          regardless of the article. A wire piece and an editorial column receive the
          same label. void --news rejects that premise. Every article is scored
          individually by six rule-based NLP analyzers. An AP wire piece published on
          Fox News scores near-center. A Fox opinion segment scores right with a high
          opinion-to-fact ratio. The outlet name is metadata, not a verdict.
        </p>
        <p className="meth__body">
          No large language model makes scoring decisions. All analysis uses spaCy NER,
          TextBlob sentiment, curated keyword lexicons, and statistical patterns. The
          algorithms are deterministic: the same text produces the same scores every time.
        </p>
      </MethSection>

      {/* ---- Section 2: Six Axes ---- */}
      <MethSection index={1}>
        <h3 className="meth__section-title">Six Axes of Analysis</h3>
        <p className="meth__body">
          Each article passes through six independent analyzers. They run in parallel,
          share no state, and cannot influence each other&rsquo;s output. Cross-axis
          correlation is gated below r&nbsp;=&nbsp;0.70 to ensure the axes measure
          genuinely different properties.
        </p>
        <div className="meth__axes">
          {AXES_DATA.map((axis) => (
            <AxisAccordion key={axis.id} axis={axis} />
          ))}
        </div>
      </MethSection>

      {/* ---- Section 3: Worked Example ---- */}
      <MethSection index={2}>
        <h3 className="meth__section-title">Worked Example</h3>
        <p className="meth__body">
          A real-world decomposition of how the six axes score a single article.
        </p>
        <div className="meth__example">
          <div className="meth__example-header">
            <p className="meth__example-source">{WORKED_EXAMPLE.source}</p>
            <h4 className="meth__example-headline">{WORKED_EXAMPLE.headline}</h4>
          </div>
          <div className="meth__example-scores">
            {WORKED_EXAMPLE.scores.map((s) => (
              <div className="meth__score-row" key={s.axis}>
                <div className="meth__score-left">
                  <span className="meth__score-axis">{s.axis}</span>
                  <span className="meth__score-value" style={{ color: s.color }}>
                    {s.score !== null ? s.score : "\u2014"}
                  </span>
                  <span className="meth__score-label">{s.label}</span>
                </div>
                <p className="meth__score-detail">{s.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </MethSection>

      {/* ---- Section 4: Validation ---- */}
      <MethSection index={3}>
        <h3 className="meth__section-title">Validation</h3>
        <p className="meth__body">
          The bias engine is tested against a ground-truth corpus of 42 articles spanning
          9 categories&mdash;from hard-news wire copy to partisan opinion columns to
          tabloid sensationalism. Every article has hand-verified expected scores.
        </p>
        <div className="meth__validation-grid">
          {VALIDATION_STATS.map((stat, i) => (
            <ValidationStat key={stat.label} stat={stat} index={i} />
          ))}
        </div>
        <p className="meth__body">
          A CI gate runs the full validation suite on every commit via GitHub Actions.
          If any axis drifts outside its expected range, the pipeline build fails.
        </p>
        <p className="meth__body meth__body--code">
          Run it yourself: <code className="meth__inline-code">python pipeline/validation/runner.py</code>
        </p>
      </MethSection>

      {/* ---- Section 5: 419 Curated Sources ---- */}
      <MethSection index={4}>
        <h3 className="meth__section-title">419 Curated Sources</h3>
        <p className="meth__body">
          Every source in the spectrum above was added by hand. Each has a tier
          classification, a baseline political lean, a country of origin, and
          credibility notes written by a human editor.
        </p>
        <div className="meth__source-grid">
          <div className="meth__source-stat">
            <span className="meth__source-tier">us_major</span>
            <span className="meth__source-count">42</span>
            <span className="meth__source-desc">Top-tier U.S. outlets: NYT, WaPo, AP, Reuters, WSJ, etc.</span>
          </div>
          <div className="meth__source-stat">
            <span className="meth__source-tier">international</span>
            <span className="meth__source-count">181</span>
            <span className="meth__source-desc">Global outlets across 40+ countries: BBC, Al Jazeera, The Hindu, DW, etc.</span>
          </div>
          <div className="meth__source-stat">
            <span className="meth__source-tier">independent</span>
            <span className="meth__source-count">196</span>
            <span className="meth__source-desc">Nonprofit, investigative, and niche: ProPublica, The Intercept, Jacobin, etc.</span>
          </div>
        </div>
        <div className="meth__source-meta">
          <p className="meth__body">
            The lean spectrum uses 7 zones from Far Left to Far Right. The current
            left-to-right ratio across all 419 sources is <strong>1.54:1</strong>&mdash;a
            deliberate tilt toward the center with representation from both wings.
          </p>
        </div>
      </MethSection>

      {/* ---- Section 6: Open Source ---- */}
      <MethSection index={5} className="meth__section--last">
        <h3 className="meth__section-title">Open Source</h3>
        <p className="meth__body">
          Every analyzer is a standalone Python module in <code className="meth__inline-code">pipeline/analyzers/</code>.
          The validation framework, ground-truth fixtures, and signal decomposition tools are
          all public. No black-box models. No proprietary scoring. Read the code, run the
          tests, file an issue.
        </p>
        <div className="meth__open-links">
          <a href="https://github.com/aacrit/void--news/tree/main/pipeline/analyzers" target="_blank" rel="noopener noreferrer" className="meth__open-link-item">
            <code className="meth__inline-code">pipeline/analyzers/</code>
            <span className="meth__open-link-desc">All 6 scoring modules</span>
          </a>
          <a href="https://github.com/aacrit/void--news/tree/main/pipeline/validation" target="_blank" rel="noopener noreferrer" className="meth__open-link-item">
            <code className="meth__inline-code">pipeline/validation/</code>
            <span className="meth__open-link-desc">Test suite + fixtures</span>
          </a>
          <a href="https://github.com/aacrit/void--news/blob/main/data/sources.json" target="_blank" rel="noopener noreferrer" className="meth__open-link-item">
            <code className="meth__inline-code">data/sources.json</code>
            <span className="meth__open-link-desc">All 419 source definitions</span>
          </a>
        </div>
      </MethSection>
    </section>
  );
}

function formatDateCompact(): string {
  return new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function SourcesPageInner() {
  const [sources, setSources] = useState<SpectrumSource[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeEdition, setActiveEdition] = useState<Edition>("world");
  const [activeLean, setActiveLean] = useState<LeanFilter>("All");
  const editionGroupRef = useRef<HTMLDivElement>(null);
  const leanGroupRef = useRef<HTMLDivElement>(null);

  // Defer date rendering to client to avoid SSG hydration mismatch (#310)
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  /** Arrow-key navigation within a radiogroup container */
  const handleRadioGroupKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      e.preventDefault();
      const container = e.currentTarget;
      const radios = Array.from(
        container.querySelectorAll<HTMLButtonElement>('[role="radio"]')
      );
      const idx = radios.indexOf(e.target as HTMLButtonElement);
      if (idx < 0) return;
      const next =
        e.key === "ArrowRight"
          ? radios[(idx + 1) % radios.length]
          : radios[(idx - 1 + radios.length) % radios.length];
      next.focus();
      next.click();
    },
    []
  );

  useEffect(() => {
    const controller = new AbortController();

    async function loadSources() {
      if (!supabase) {
        setError(supabaseError ?? "Unable to connect to data source.");
        setIsLoading(false);
        return;
      }
      try {
        const { data, error: fetchError } = await supabase
          .from("sources")
          .select(
            "name, slug, url, tier, country, political_lean_baseline, credibility_notes"
          )
          .order("name");

        if (controller.signal.aborted) return;

        if (fetchError) {
          setError(fetchError.message);
          setIsLoading(false);
          return;
        }

        setSources((data as SpectrumSource[]) || []);
        setIsLoading(false);

        // Deep link: after data loads and Methodology mounts, scroll to hash target.
        // Browser already attempted the scroll before React rendered — retry now.
        requestAnimationFrame(() => {
          const hash = window.location.hash.slice(1);
          if (hash) {
            document.getElementById(hash)?.scrollIntoView({ behavior: "smooth" });
          }
        });
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error ? err.message : "Failed to load sources"
          );
          setIsLoading(false);
        }
      }
    }

    loadSources();
    return () => controller.abort();
  }, []);

  const filteredSources = useMemo(() => {
    let result = sources;
    const countries = EDITION_COUNTRIES[activeEdition];
    if (countries) result = result.filter((s) => countries.includes(s.country));
    const allowed = LEAN_ALLOWED[activeLean];
    if (allowed) result = result.filter((s) => allowed.includes(normalizeLean(s.political_lean_baseline)));
    return result;
  }, [sources, activeEdition, activeLean]);

  const totalCount = filteredSources.length;

  const handleLeanTap = (lean: LeanFilter) => {
    if (typeof navigator !== "undefined" && navigator.vibrate) navigator.vibrate(10);
    setActiveLean(lean === activeLean ? "All" : lean);
  };

  return (
    <div className="page-container">
      {/* ---- Nav header — matches NavBar layout ---- */}
      <header className="nav-header">
        <nav className="nav-inner" aria-label="Main navigation">
          <div className="nav-left">
            <Link
              href="/"
              aria-label="void --news — home"
              className="nav-logo si-hoverable"
            >
              <span className="nav-logo-desktop">
                <LogoFull height={32} />
              </span>
              <span className="nav-logo-mobile">
                <LogoFull height={22} />
              </span>
            </Link>
          </div>

          {/* Edition filter — radiogroup (filters content, not panel switch) */}
          <div
            className="nav-tabs"
            role="radiogroup"
            aria-label="Edition"
            ref={editionGroupRef}
            onKeyDown={handleRadioGroupKeyDown}
          >
            {EDITIONS.map((edition) => {
              const checked = activeEdition === edition.slug;
              return (
                <button
                  key={edition.slug}
                  role="radio"
                  aria-checked={checked}
                  tabIndex={checked ? 0 : -1}
                  className={`nav-tab${checked ? " nav-tab--active" : ""}`}
                  onClick={() => setActiveEdition(edition.slug)}
                >
                  <span className="nav-tab__inner">
                    <EditionIcon slug={edition.slug} size={14} />
                    {edition.label}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Dateline — desktop only */}
          <span className="nav-dateline-inline" aria-hidden="true" suppressHydrationWarning>
            {mounted ? `${getEditionTimeOfDay(activeEdition)} Edition` : "Edition"}
            <span className="nav-dateline-inline__sep">&middot;</span>
            {mounted ? formatDateCompact() : ""}
            <span className="nav-dateline-inline__sep">&middot;</span>
            <span className="nav-dateline-inline__time">{mounted ? getEditionTimestamp(activeEdition) : ""}</span>
          </span>

          <div className="nav-right">
            <PageToggle activePage="sources" />
            <ThemeToggle />
          </div>
        </nav>
      </header>

      {/* Mobile bottom nav — edition switching */}
      <nav className="nav-bottom" aria-label="Edition navigation">
        {EDITIONS.map((edition) => (
          <button
            key={`mobile-${edition.slug}`}
            aria-current={activeEdition === edition.slug ? "page" : undefined}
            className={`nav-bottom-tab${activeEdition === edition.slug ? " nav-bottom-tab--active" : ""}`}
            onClick={() => setActiveEdition(edition.slug)}
          >
            <span className="nav-tab__inner">
              <EditionIcon slug={edition.slug} size={18} />
              {edition.label}
            </span>
          </button>
        ))}
      </nav>

      <main id="main-content" className="page-main sources-page">
        {/* ---- Toolbar: title + lean filter ---- */}
        <div className="sources-toolbar">
          <div className="sources-toolbar__text">
            <h1 className="sources-toolbar__title" title="void --sources">
              <span className="sources-toolbar__count">{totalCount}</span> Sources
            </h1>
          </div>
          <div
            className="sources-leans"
            role="radiogroup"
            aria-label="Filter by lean"
            ref={leanGroupRef}
            onKeyDown={handleRadioGroupKeyDown}
          >
            {LEAN_FILTERS.map((lean) => {
              const checked = activeLean === lean;
              return (
                <button
                  key={lean}
                  role="radio"
                  aria-checked={checked}
                  tabIndex={checked ? 0 : -1}
                  className={`sources-edition-chip${checked ? " sources-edition-chip--active" : ""}`}
                  onClick={() => handleLeanTap(lean)}
                >
                  <span
                    className="filter-chip__dot"
                    style={{ backgroundColor: LEAN_DOT_COLOR[lean] }}
                    aria-hidden="true"
                  />
                  {lean}
                </button>
              );
            })}
          </div>
        </div>

        {/* ---- Loading state ---- */}
        {isLoading && (
          <div className="sources-loading" aria-label="Loading sources">
            <div className="sources-loading__bar skeleton" />
            <div className="sources-loading__logos">
              {Array.from({ length: 12 }).map((_, i) => (
                <div
                  key={i}
                  className="sources-loading__logo skeleton"
                  style={{ animationDelay: `${i * 60}ms` }}
                />
              ))}
            </div>
          </div>
        )}

        {/* ---- Error state ---- */}
        {error && !isLoading && (
          <div className="empty-state">
            <h2 className="text-xl empty-state__title">
              Could not load sources
            </h2>
            <p className="text-base empty-state__body">
              {error}
            </p>
            <button
              className="btn-primary"
              onClick={() => window.location.reload()}
            >
              Try again
            </button>
          </div>
        )}

        {/* ---- Empty state ---- */}
        {!isLoading && !error && sources.length === 0 && (
          <div className="empty-state">
            <LogoIcon size={48} animation="analyzing" />
            <h2 className="text-xl empty-state__title">
              No sources found
            </h2>
            <p className="text-base empty-state__body--no-margin">
              Sources will appear once the pipeline syncs them to the database.
            </p>
          </div>
        )}

        {/* ---- Spectrum visualization ---- */}
        {!isLoading && !error && filteredSources.length > 0 && (
          <>
            <SpectrumChart sources={filteredSources} />
            <div style={{ textAlign: "right", marginTop: "var(--space-2)", marginBottom: "var(--space-3)" }}>
              <a href="#methodology" style={{ fontFamily: "var(--font-meta)", fontSize: "var(--text-xs)", color: "var(--fg-tertiary)", textDecoration: "none", letterSpacing: "0.04em", textTransform: "uppercase" }}>
                How we score &darr;
              </a>
            </div>
          </>
        )}

        {!isLoading && !error && filteredSources.length === 0 && sources.length > 0 && (
          <div className="empty-state empty-state--inline">
            <p className="text-base empty-state__body--no-margin">
              No sources match the current filters.
            </p>
            <button
              className="btn-secondary"
              onClick={() => { setActiveEdition("world"); setActiveLean("All"); }}
            >
              Clear filters
            </button>
          </div>
        )}

        {/* ---- Methodology (trust anchor) ---- */}
        {!isLoading && !error && sources.length > 0 && (
          <Methodology />
        )}
      </main>

      <Footer />
    </div>
  );
}

export default function SourcesPage() {
  return (
    <ErrorBoundary>
      <SourcesPageInner />
    </ErrorBoundary>
  );
}
