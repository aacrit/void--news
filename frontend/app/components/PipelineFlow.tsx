/* ==========================================================================
   PipelineFlow — Static pipeline visualization
   Server component (no 'use client'). Renders every step of the 3x-daily
   Python pipeline in a dark terminal aesthetic.
   ========================================================================== */

import Link from "next/link";

/* --------------------------------------------------------------------------
   Data
   -------------------------------------------------------------------------- */

interface Axis {
  num: string;
  name: string;
  detail: string;
  color: string;
}

interface Signal {
  label: string;
  w: number;
}

interface Step {
  num: string;
  title: string;
  detail: string;
  file?: string;
  badge?: string;
  badgeActive?: boolean;
  badgeDisabled?: boolean;
  highlight?: boolean;
  type?: "axes" | "pools" | "signals";
  axes?: Axis[];
  signals?: Signal[];
}

interface Phase {
  id: string;
  label: string;
  icon: string;
  color: string;
  desc: string;
  steps: Step[];
}

const PHASES: Phase[] = [
  {
    id: "ingestion",
    label: "INGESTION",
    icon: "\u2193",
    color: "#C47A2A",
    desc: "Fetch articles from 1,013 sources",
    steps: [
      {
        num: "1",
        title: "Load Sources",
        detail:
          "1,013 sources \u00b7 3 tiers (us_major / international / independent) \u00b7 158 countries",
        file: "sources.json",
      },
      {
        num: "2",
        title: "Create Pipeline Run",
        detail:
          "Supabase pipeline_runs record \u2014 enables health monitoring and duration tracking",
      },
      {
        num: "3",
        title: "Fetch RSS Feeds",
        detail:
          "30 articles/feed cap \u00b7 8 parallel workers \u00b7 30s timeout per feed",
        file: "fetchers/",
      },
      {
        num: "3b",
        title: "URL Dedup",
        detail:
          "Skip URLs already in DB \u2014 avoids re-scraping on subsequent daily runs",
      },
      {
        num: "4",
        title: "Scrape Full Text",
        detail:
          "Parallel extraction across workers \u00b7 graceful timeout fallback \u00b7 metadata extraction",
        file: "fetchers/",
      },
      {
        num: "4b",
        title: "Content Dedup",
        detail:
          "Fuzzy title + body overlap detection prevents duplicate articles entering clustering",
        file: "deduplicator.py",
      },
    ],
  },
  {
    id: "analysis",
    label: "ANALYSIS",
    icon: "\u26a1",
    color: "#4A7FA5",
    desc: "Rule-based NLP \u00b7 $0 \u00b7 per-article \u00b7 5 axes",
    steps: [
      {
        num: "5",
        title: "5-Axis Bias Analysis",
        detail:
          "Rule-based NLP only. Zero LLM calls. Zero cost. Per-article scoring 0\u2013100 on each axis.",
        file: "analyzers/",
        type: "axes",
        axes: [
          {
            num: "1",
            name: "Political Lean",
            detail:
              "Keyword lexicons + entity sentiment (NER + TextBlob) + framing phrases + source baseline blending",
            color: "#6490B8",
          },
          {
            num: "2",
            name: "Sensationalism",
            detail:
              "Clickbait patterns + superlative density (word-boundary regex) + TextBlob polarity extremity + partisan attack density (cap 30pts)",
            color: "#C07A6A",
          },
          {
            num: "3",
            name: "Opinion vs Fact",
            detail:
              "First-person pronouns + TextBlob subjectivity + attribution density (24 investigative patterns) + value judgments + rhetorical questions",
            color: "#7BA070",
          },
          {
            num: "4",
            name: "Factual Rigor",
            detail:
              "Named sources (NER + verbs) + org citations + data patterns (numbers, dates, stats) + quote density + vague-source penalty",
            color: "#9A8060",
          },
          {
            num: "5",
            name: "Framing",
            detail:
              "Charged synonym pairs (50+) + cluster-aware omission detection + headline-body sentiment divergence + passive voice (cap 30)",
            color: "#9070C0",
          },
        ],
      },
    ],
  },
  {
    id: "clustering",
    label: "CLUSTERING",
    icon: "\u25c9",
    color: "#5B8A5B",
    desc: "Group related articles into stories",
    steps: [
      {
        num: "6",
        title: "Cluster Articles",
        detail:
          "TF-IDF cosine similarity \u00b7 titles + first 500 words \u00b7 agglomerative clustering + entity-overlap merge pass",
        file: "story_cluster.py",
      },
      {
        num: "6+",
        title: "Orphan Wrapping",
        detail:
          "Single articles wrapped as 1-source clusters \u2014 ensures all articles are addressable in the feed",
      },
      {
        num: "6b",
        title: "Re-Frame (cluster-aware)",
        detail:
          "Framing axis re-run with full cluster context \u2014 omission detection needs to see what other articles in the cluster covered",
        file: "framing.py",
      },
      {
        num: "6c",
        title: "Gemini Reasoning",
        detail:
          "Contextual bias score adjustments \u00b7 story type flags: incremental_update (0.75\u00d7) and ceremonial (0.82\u00d7) \u00b7 has_binding_consequences flag",
        file: "gemini_reasoning.py",
        badge: "25 calls/run",
        badgeDisabled: true,
      },
    ],
  },
  {
    id: "ranking",
    label: "RANKING v6.0",
    icon: "\u2191",
    color: "#A05A20",
    desc: "Score, summarize, and order every story \u00b7 bias-blind",
    steps: [
      {
        num: "7b",
        title: "Gemini Summarization",
        detail:
          "3-pool selection \u00b7 50-call cap/run \u00b7 pool-1 failures clear summaries (no fallback text reaches the frontend)",
        file: "cluster_summarizer.py",
        badge: "50 calls/run",
        badgeActive: true,
        highlight: true,
        type: "pools",
      },
      {
        num: "7",
        title: "Categorize + Rank",
        detail:
          "10 weighted signals (sum = 1.00) \u00b7 7 multiplicative gates \u00b7 OUTPUT: headline_rank 0\u2013100 \u00b7 BIAS-BLIND (lean not used for placement)",
        file: "importance_ranker.py",
        type: "signals",
        signals: [
          { label: "Source coverage breadth", w: 20 },
          { label: "Story maturity", w: 16 },
          { label: "Tier diversity", w: 13 },
          { label: "Consequentiality", w: 10 },
          { label: "Perspective diversity", w: 9 },
          { label: "Institutional authority", w: 8 },
          { label: "Factual density", w: 8 },
          { label: "Divergence", w: 7 },
          { label: "Geographic impact", w: 6 },
          { label: "Velocity", w: 3 },
        ],
      },
      {
        num: "7c",
        title: "Editorial Triage",
        detail:
          "Gemini reorders top 10 per section by editorial priority \u2014 currently disabled via DISABLE_EDITORIAL_TRIAGE env var",
        file: "edition_ranker.py",
        badge: "5 calls/run",
        badgeDisabled: true,
      },
      {
        num: "7d",
        title: "Daily Brief (void --onair)",
        detail:
          "TL;DR (150\u2013220 words) + Opinion (lean rotates L/C/R daily) + BBC two-host audio broadcast \u00b7 5 rotating host pairs \u00b7 MP3 96k mono \u2192 Supabase Storage",
        file: "daily_brief_generator.py",
        badge: "9 calls/run",
        badgeActive: true,
      },
    ],
  },
  {
    id: "storage",
    label: "STORAGE",
    icon: "\u25a4",
    color: "#7060A0",
    desc: "Persist to Supabase \u00b7 edition ranks \u00b7 global re-rank",
    steps: [
      {
        num: "8",
        title: "Store Clusters",
        detail:
          "Upsert story_clusters + cluster_articles \u00b7 writes per-edition ranks (rank_world, rank_us, rank_europe, rank_south_asia) via edition_ranker.py",
      },
      {
        num: "8b",
        title: "Cluster Dedup",
        detail:
          "Article-overlap >30% + title-overlap >40% removes old clusters superseded by updated stories",
      },
      {
        num: "8c",
        title: "Holistic Re-Rank",
        detail:
          "Re-score ALL clusters in DB with v6.0 \u2014 old clusters compete against new ones on identical criteria \u00b7 runs importance_ranker + edition_ranker on every cluster",
        file: "rerank.py",
      },
    ],
  },
  {
    id: "enrichment",
    label: "ENRICHMENT",
    icon: "\u25c8",
    color: "#3A8A8A",
    desc: "Aggregated bias stats \u00b7 memory \u00b7 topic EMA",
    steps: [
      {
        num: "9",
        title: "Bias Enrichment RPC",
        detail:
          "refresh_cluster_enrichment() \u2014 aggregated bias stats per cluster (mean lean, spread, confidence) for frontend Sigil display",
      },
      {
        num: "9a",
        title: "Memory Engine",
        detail:
          "Tracks top story per run \u00b7 detects narrative shifts \u00b7 live polling between pipeline runs",
        file: "memory_orchestrator.py",
      },
      {
        num: "9b",
        title: "Article Categories",
        detail:
          "Populates article_categories junction table for category-based feed filtering in the frontend",
      },
      {
        num: "9c",
        title: "Topic-Outlet Tracking (Axis 6)",
        detail:
          "Per-source per-topic EMA \u2014 adaptive alpha 0.3 (new outlets, <10 articles) / 0.15 (established) \u00b7 stored in source_topic_lean table",
        file: "topic_outlet_tracker.py",
      },
    ],
  },
  {
    id: "cleanup",
    label: "CLEANUP",
    icon: "\u2715",
    color: "#888880",
    desc: "IP compliance + data retention policies",
    steps: [
      {
        num: "10",
        title: "Truncate Full Text",
        detail:
          "IP compliance \u2014 article body reduced to 300-char excerpts \u00b7 opinion articles preserved (original text required for display)",
      },
      {
        num: "\u221e",
        title: "Retention Policy",
        detail:
          "Clusters: 2 days \u00b7 Articles: 8 days \u00b7 Briefs: 8 days \u00b7 Empty clusters: RPC cleanup \u00b7 Stuck pipeline runs: RPC cleanup",
      },
    ],
  },
];

/* --------------------------------------------------------------------------
   Sub-components
   -------------------------------------------------------------------------- */

function AxesExpansion({ axes }: { axes: Axis[] }) {
  return (
    <div className="pf-axes">
      {axes.map((axis) => (
        <div key={axis.num} className="pf-axis">
          <span
            className="pf-axis__num"
            style={{ background: axis.color }}
            aria-hidden="true"
          >
            {axis.num}
          </span>
          <span className="pf-axis__name">{axis.name}</span>
          <span className="pf-axis__detail">{axis.detail}</span>
        </div>
      ))}
    </div>
  );
}

function PoolsDiagram() {
  return (
    <div className="pf-pools" role="figure" aria-label="3-pool Gemini call allocation diagram">
      <div className="pf-pools__header">
        3-Pool Selection &middot; 50 Calls/Run Max
      </div>

      {/* P1 */}
      <div className="pf-pool">
        <div className="pf-pool__top">
          <span className="pf-pool__tag pf-pool__tag--p1">P1</span>
          <span className="pf-pool__name">Priority Queue</span>
          <span className="pf-pool__count">30 clusters</span>
        </div>
        <div className="pf-pool__bar-wrap">
          <div className="pf-pool__bar pf-pool__bar--p1" />
        </div>
        <div className="pf-pool__detail">
          Sorted by headline_rank &middot; Gemini REQUIRED &middot; failure
          clears summary (no fallback text)
        </div>
      </div>

      {/* P2 */}
      <div className="pf-pool">
        <div className="pf-pool__top">
          <span className="pf-pool__tag pf-pool__tag--p2">P2</span>
          <span className="pf-pool__name">Edition Balance</span>
          <span className="pf-pool__count">&le;10 clusters</span>
          <div className="pf-pool__chips">
            {["world", "us", "europe", "south-asia"].map((e) => (
              <span key={e} className="pf-pool__chip">
                {e}
              </span>
            ))}
          </div>
        </div>
        <div className="pf-pool__bar-wrap">
          <div className="pf-pool__bar pf-pool__bar--p2" />
        </div>
        <div className="pf-pool__detail">
          Round-robin across editions &middot; best by headline_rank &middot; no
          duplicates from P1
        </div>
      </div>

      {/* P3 */}
      <div className="pf-pool">
        <div className="pf-pool__top">
          <span className="pf-pool__tag pf-pool__tag--p3">P3</span>
          <span className="pf-pool__name">Topic Coverage</span>
          <span className="pf-pool__count">&le;10 clusters</span>
          <div className="pf-pool__chips">
            {[
              "politics",
              "conflict",
              "economy",
              "science",
              "health",
              "environment",
              "culture",
            ].map((t) => (
              <span key={t} className="pf-pool__chip">
                {t}
              </span>
            ))}
          </div>
        </div>
        <div className="pf-pool__bar-wrap">
          <div className="pf-pool__bar pf-pool__bar--p3" />
        </div>
        <div className="pf-pool__detail">
          1 per desk minimum &middot; fill remaining from most
          underrepresented
        </div>
      </div>

      {/* Total bar */}
      <div className="pf-pools__total">
        <div className="pf-pools__total-bar">
          <div className="pf-pools__total-seg pf-pools__total-seg--p1" />
          <div className="pf-pools__total-seg pf-pools__total-seg--p2" />
          <div className="pf-pools__total-seg pf-pools__total-seg--p3" />
        </div>
        <div className="pf-pools__total-legend">
          <span className="pf-pools__total-item">
            <span
              className="pf-pools__total-dot"
              style={{ background: "#22c55e" }}
            />
            P1 (30)
          </span>
          <span className="pf-pools__total-item">
            <span
              className="pf-pools__total-dot"
              style={{ background: "#4A7FA5" }}
            />
            P2 (&le;10)
          </span>
          <span className="pf-pools__total-item">
            <span
              className="pf-pools__total-dot"
              style={{ background: "#A05A20" }}
            />
            P3 (&le;10)
          </span>
          <span className="pf-pools__total-arrow">
            &rarr; up to 50 Gemini calls/run
          </span>
        </div>
      </div>
    </div>
  );
}

function SignalChart({ signals }: { signals: Signal[] }) {
  /* Opacity: 100% at weight 20, down to 40% at weight 3 */
  const maxW = 20;
  const minW = 3;

  return (
    <div className="pf-signals" role="figure" aria-label="Ranking signal weights">
      {signals.map((s) => {
        const barWidth = s.w * 5;
        const opacity =
          0.4 + 0.6 * ((s.w - minW) / (maxW - minW));
        return (
          <div key={s.label} className="pf-signal">
            <span className="pf-signal__label">{s.label}</span>
            <div className="pf-signal__bar-wrap">
              <div
                className="pf-signal__bar"
                style={{ width: `${barWidth}%`, opacity }}
              />
            </div>
            <span className="pf-signal__pct">{s.w}%</span>
          </div>
        );
      })}
      <div className="pf-signals__note">
        + 7 multiplicative gates (recency, source count, maturity, dupe, stale,
        short, orphan)
      </div>
    </div>
  );
}

function StepRow({ step }: { step: Step }) {
  return (
    <div className="pf-step">
      {/* Rail */}
      <div className="pf-step__rail">
        <span
          className={`pf-step__num${
            step.highlight ? " pf-step__num--highlight" : ""
          }`}
        >
          {step.num}
        </span>
      </div>

      {/* Body */}
      <div className="pf-step__body">
        <div
          className={`pf-step__title${
            step.highlight ? " pf-step__title--highlight" : ""
          }`}
        >
          {step.title}
        </div>
        <div className="pf-step__detail">{step.detail}</div>

        {/* Meta row */}
        <div className="pf-step__meta">
          {step.file && (
            <span className="pf-step__file">{step.file}</span>
          )}
          {step.badge && step.badgeActive && (
            <span className="pf-step__badge pf-step__badge--active">
              {step.badge}
            </span>
          )}
          {step.badge && step.badgeDisabled && (
            <span className="pf-step__badge pf-step__badge--disabled">
              {step.badge}
              <span className="pf-step__badge-suffix">
                {" "}
                &middot; disabled
              </span>
            </span>
          )}
        </div>

        {/* Expanded sections */}
        {step.type === "axes" && step.axes && (
          <AxesExpansion axes={step.axes} />
        )}
        {step.type === "pools" && <PoolsDiagram />}
        {step.type === "signals" && step.signals && (
          <SignalChart signals={step.signals} />
        )}
      </div>
    </div>
  );
}

function FrontendOutput() {
  const gridRanks = [1, 2, 3, 4, 5, 6, 7, 8, 9];

  return (
    <div className="pf-output" role="figure" aria-label="Frontend output mapping">
      <div className="pf-output__header">
        Frontend Output &rarr; void --news
      </div>

      {/* Hero slot */}
      <div className="pf-output__hero">
        <div className="pf-output__hero-box">
          <div className="pf-output__hero-label">
            Rank 0 &middot; LeadStory
          </div>
          <div className="pf-output__hero-detail">
            Front-page image treatment &middot; headline + summary + full Sigil
            bias display
          </div>
        </div>
      </div>

      {/* Grid mockup */}
      <div className="pf-output__grid">
        <div className="pf-output__grid-cards">
          {gridRanks.map((r) => (
            <div key={r} className="pf-output__card">
              <span className="pf-output__card-rank">{r}</span>
              <span className="pf-output__card-label">StoryCard</span>
            </div>
          ))}
          <div className="pf-output__card pf-output__card--ellipsis">
            <span className="pf-output__card-label">&hellip;</span>
          </div>
        </div>
        <div className="pf-output__grid-note">
          ranks 1&ndash;29 &middot; all identical StoryCard treatment &middot;
          headline + summary + Sigil
        </div>
      </div>
    </div>
  );
}

/* --------------------------------------------------------------------------
   Main Component
   -------------------------------------------------------------------------- */

export default function PipelineFlow() {
  return (
    <div className="pf-root">
      {/* ---- 1. Sticky Header ---- */}
      <header className="pf-header" role="banner">
        <div className="pf-header__left">
          <span className="pf-header__title">void --pipeline</span>
          <span className="pf-header__sep" aria-hidden="true" />
          <span className="pf-header__meta">
            3x daily &middot; 25&ndash;35 min &middot; GitHub Actions
          </span>
        </div>
        <Link href="/void--news/command-center" className="pf-header__back">
          &larr; Command Center
        </Link>
      </header>

      {/* ---- 2. Gemini RPD Budget Bar ---- */}
      <div className="pf-rpd" role="figure" aria-label="Gemini API daily budget allocation">
        <div className="pf-rpd__inner">
          <div className="pf-rpd__title">
            Gemini Free Tier &mdash; 250 RPD Limit
          </div>
          <div className="pf-rpd__bar" aria-hidden="true">
            <div className="pf-rpd__segment pf-rpd__segment--summarization" />
            <div className="pf-rpd__segment pf-rpd__segment--briefs" />
            <div className="pf-rpd__segment pf-rpd__segment--triage" />
            <div className="pf-rpd__segment pf-rpd__segment--buffer" />
          </div>
          <div className="pf-rpd__legend">
            <span className="pf-rpd__legend-item">
              <span
                className="pf-rpd__legend-dot"
                style={{ background: "#22c55e" }}
              />
              Summarization &middot; 150
            </span>
            <span className="pf-rpd__legend-item">
              <span
                className="pf-rpd__legend-dot"
                style={{ background: "#C8956C" }}
              />
              Briefs &middot; 27
            </span>
            <span className="pf-rpd__legend-item">
              <span
                className="pf-rpd__legend-dot"
                style={{ background: "#3A3630" }}
              />
              <span className="pf-rpd__legend-disabled">
                Triage &middot; 15 (disabled)
              </span>
            </span>
            <span className="pf-rpd__legend-item">
              <span
                className="pf-rpd__legend-dot"
                style={{ background: "#1A1816" }}
              />
              Buffer &middot; 58
            </span>
            <span className="pf-rpd__legend-total">
              192 / 250 RPD &middot; 23% buffer
            </span>
          </div>
        </div>
      </div>

      {/* ---- 3. Phase Flow ---- */}
      <main className="pf-flow" id="main-content">
        {PHASES.map((phase, i) => (
          <div key={phase.id}>
            {/* Arrow connector between phases */}
            {i > 0 && (
              <div className="pf-connector" aria-hidden="true">
                &#9660;
              </div>
            )}

            {/* Phase block */}
            <section
              className={`pf-phase pf-phase--${phase.id}`}
              aria-label={`${phase.label} phase`}
            >
              <div className="pf-phase__header">
                <span className="pf-phase__icon" aria-hidden="true">
                  {phase.icon}
                </span>
                <span className="pf-phase__label">{phase.label}</span>
                <span className="pf-phase__desc">{phase.desc}</span>
              </div>

              {phase.steps.map((step) => (
                <StepRow key={step.num} step={step} />
              ))}
            </section>
          </div>
        ))}

        {/* ---- 4. Frontend Output ---- */}
        <div className="pf-connector" aria-hidden="true">
          &#9660;
        </div>
        <FrontendOutput />
      </main>
    </div>
  );
}
