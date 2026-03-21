"use client";

import { useState, useEffect, useCallback } from "react";
import type {
  Edition,
  Category,
  Story,
  BiasScores,
  BiasSpread,
  ThreeLensData,
  OpinionLabel,
  SigilData,
} from "../lib/types";
import { supabase } from "../lib/supabase";
import {
  type ArticleTier,
  type FillerItem,
  assignTier,
  generateDecks,
  getDateline,
  truncateSummary,
  distributeStories,
  getSectionConfig,
  capitalize,
  editionSubtitle,
} from "./paperUtils";
import "./paper.css";

/* ---------------------------------------------------------------------------
   E-Paper Edition — 1924 New York Times Broadsheet
   8-column broadsheet. Zero whitespace. CSS multi-column flow.
   Period typography. Full summaries. Bias as editorial prose.
   --------------------------------------------------------------------------- */

// --- Helpers (duplicated from HomeContent to keep blast radius zero) ---

function parseBiasDiversity(raw: unknown): Record<string, unknown> | null {
  if (raw == null) return null;
  if (typeof raw !== "object" || Array.isArray(raw)) return null;
  return raw as Record<string, unknown>;
}

function safeNum(
  bd: Record<string, unknown>,
  key: string,
  fallback: number,
): number {
  const v = bd[key];
  if (typeof v === "number" && !Number.isNaN(v)) return v;
  return fallback;
}

function safeTierBreakdown(
  bd: Record<string, unknown>,
): Record<string, number> | undefined {
  const raw = bd["tier_breakdown"];
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return undefined;
  const result: Record<string, number> = {};
  for (const [k, v] of Object.entries(raw as Record<string, unknown>)) {
    if (typeof v === "number" && Number.isFinite(v)) result[k] = v;
  }
  return Object.keys(result).length > 0 ? result : undefined;
}

function deriveOpinionLabel(score: number): OpinionLabel {
  if (score <= 25) return "Reporting";
  if (score <= 50) return "Analysis";
  if (score <= 75) return "Opinion";
  return "Editorial";
}

function deriveCoverageScore(
  sourceCount: number,
  factualRigor: number,
  confidence: number,
): number {
  const sourceNorm = Math.min(1.0, sourceCount / 10.0);
  const rigorNorm = factualRigor / 100.0;
  const confNorm = Math.min(1.0, confidence);
  return Math.round(
    (sourceNorm * 0.35 + 0.2 + confNorm * 0.2 + rigorNorm * 0.25) * 100,
  );
}

/* eslint-disable @typescript-eslint/no-explicit-any */
function buildStory(cluster: any, usingEnriched: boolean): Story {
  const bd = usingEnriched
    ? parseBiasDiversity(cluster.bias_diversity)
    : null;
  const hasBiasData = !!(bd && bd["avg_political_lean"] != null);

  const biasScores: BiasScores = hasBiasData
    ? {
        politicalLean: safeNum(bd!, "avg_political_lean", 50),
        sensationalism: safeNum(bd!, "avg_sensationalism", 30),
        opinionFact: safeNum(bd!, "avg_opinion_fact", 25),
        factualRigor: safeNum(bd!, "avg_factual_rigor", 75),
        framing: safeNum(bd!, "avg_framing", 40),
      }
    : {
        politicalLean: 50,
        sensationalism: 30,
        opinionFact: 25,
        factualRigor: 75,
        framing: 40,
      };

  const biasSpread: BiasSpread | undefined =
    bd && bd["lean_spread"] != null
      ? {
          leanSpread: safeNum(bd, "lean_spread", 0),
          framingSpread: safeNum(bd, "framing_spread", 0),
          leanRange: safeNum(bd, "lean_range", 0),
          sensationalismSpread: safeNum(bd, "sensationalism_spread", 0),
          opinionSpread: safeNum(bd, "opinion_spread", 0),
          aggregateConfidence: safeNum(bd, "aggregate_confidence", 0),
          analyzedCount: safeNum(bd, "analyzed_count", 0),
        }
      : undefined;

  const sourceCount = cluster.source_count || 1;
  const opinionLabel =
    (bd?.["avg_opinion_label"] as OpinionLabel) ??
    deriveOpinionLabel(biasScores.opinionFact);
  const lensData: ThreeLensData = {
    lean: biasScores.politicalLean,
    coverage: bd
      ? safeNum(
          bd,
          "coverage_score",
          deriveCoverageScore(
            sourceCount,
            biasScores.factualRigor,
            biasSpread?.aggregateConfidence ?? 0.5,
          ),
        )
      : deriveCoverageScore(sourceCount, biasScores.factualRigor, 0.5),
    sourceCount,
    tierBreakdown: bd ? safeTierBreakdown(bd) : undefined,
    opinion: biasScores.opinionFact,
    opinionLabel,
    pending: !hasBiasData,
  };
  const sigilData: SigilData = {
    politicalLean: biasScores.politicalLean,
    sensationalism: biasScores.sensationalism,
    opinionFact: biasScores.opinionFact,
    factualRigor: biasScores.factualRigor,
    framing: biasScores.framing,
    agreement: cluster.divergence_score || 0,
    sourceCount,
    tierBreakdown: bd ? safeTierBreakdown(bd) : undefined,
    biasSpread,
    pending: !hasBiasData,
    opinionLabel,
  };

  const rawConsensus = usingEnriched ? cluster.consensus_points : null;
  const rawDivergence = usingEnriched ? cluster.divergence_points : null;

  return {
    id: cluster.id,
    title: cluster.title,
    summary: cluster.summary || "",
    source: { name: "Multiple Sources", count: sourceCount },
    category: capitalize(cluster.category || "politics") as Category,
    publishedAt:
      cluster.first_published ||
      cluster.last_updated ||
      new Date().toISOString(),
    biasScores,
    biasSpread,
    lensData,
    sigilData,
    section: (cluster.section || "world") as Edition,
    sections: (cluster.sections || [cluster.section || "world"]) as Edition[],
    importance: cluster.headline_rank || cluster.importance_score || 50,
    divergenceScore: cluster.divergence_score || 0,
    headlineRank: cluster.headline_rank || cluster.importance_score || 50,
    coverageVelocity: cluster.coverage_velocity || 0,
    deepDive:
      (Array.isArray(rawConsensus) && rawConsensus.length > 0) ||
      (Array.isArray(rawDivergence) && rawDivergence.length > 0)
        ? {
            consensus: Array.isArray(rawConsensus) ? rawConsensus : [],
            divergence: Array.isArray(rawDivergence) ? rawDivergence : [],
            sources: [],
          }
        : undefined,
  };
}
/* eslint-enable @typescript-eslint/no-explicit-any */

// --- Byline ---

function articleByline(
  sourceCount: number,
  tierBreakdown?: Record<string, number>,
): string {
  if (sourceCount === 1) {
    if (tierBreakdown?.us_major) return "From a major U.S. outlet";
    if (tierBreakdown?.international) return "From an international bureau";
    if (tierBreakdown?.independent) return "From an independent outlet";
    return "From a single report";
  }
  if (sourceCount <= 3) return `Compiled from ${sourceCount} sources`;
  return `From multiple outlets \u2014 ${sourceCount} sources`;
}

// ===== COMPONENTS =====

// --- Masthead ---

function Masthead({
  lastUpdated,
  edition,
}: {
  lastUpdated: string | null;
  edition: Edition;
}) {
  const now = new Date();

  const dateStr = now
    .toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    })
    .toUpperCase();

  const epoch = new Date("2026-03-01T00:00:00Z");
  const issueNo = Math.max(
    1,
    Math.floor((now.getTime() - epoch.getTime()) / 86400000),
  );
  const year = now.getFullYear();

  const pressTime = lastUpdated
    ? new Date(lastUpdated).toLocaleString("en-US", {
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      })
    : null;

  const subtitle = editionSubtitle(edition);
  const basePath = "/void--news/paper";

  return (
    <header className="np-masthead">
      <div className="np-masthead__ears">
        <div className="np-masthead__ear np-masthead__ear--left">
          <span className="np-masthead__ear-text">
            An ode to simpler times. A quiet pursuit of balance.
          </span>
        </div>
        <div className="np-masthead__ear np-masthead__ear--right">
          <span className="np-masthead__ear-text">
            Copyright {year}, Void News
            {pressTime && <> &mdash; Press closed {pressTime}</>}
          </span>
        </div>
      </div>

      <hr className="np-masthead__top-rule" />

      <h1 className="np-masthead__nameplate">Void News.</h1>
      {subtitle && (
        <p className="np-masthead__edition-subtitle">{subtitle}</p>
      )}

      <hr className="np-double-rule" aria-hidden="true" />

      <div className="np-masthead__info">
        <span className="np-masthead__info-left">
          No.&thinsp;{issueNo}
        </span>
        <span className="np-masthead__info-center">{dateStr}</span>
        <span className="np-masthead__info-right">Free of Charge</span>
      </div>

      <hr className="np-double-rule" aria-hidden="true" />

      <nav className="np-edition-nav" aria-label="Edition">
        <a
          href={basePath}
          className={edition === "world" ? "np-edition-nav__active" : ""}
        >
          World Edition
        </a>
        {" \u00B7 "}
        <a
          href={`${basePath}/us`}
          className={edition === "us" ? "np-edition-nav__active" : ""}
        >
          United States
        </a>
        {" \u00B7 "}
        <a
          href={`${basePath}/india`}
          className={edition === "india" ? "np-edition-nav__active" : ""}
        >
          India
        </a>
      </nav>
    </header>
  );
}

// --- Section Label ---

function SectionLabel({ label }: { label: string }) {
  return (
    <div className="np-section-label" role="separator">
      <hr className="np-section-label__rule-top" />
      <p className="np-section-label__text">{label}</p>
      <hr className="np-section-label__rule-bottom" />
    </div>
  );
}

// --- Article ---

function Article({
  story,
  tier,
  edition,
}: {
  story: Story;
  tier: ArticleTier;
  edition: Edition;
}) {
  const dateline = getDateline(story, edition);
  const decks = generateDecks(story.summary, tier);

  // Extract remaining summary after decks for body text
  let bodyText = truncateSummary(story.summary, tier);
  if (decks.length > 0) {
    let remaining = story.summary;
    for (const deck of decks) {
      const deckPos = remaining.indexOf(deck);
      if (deckPos !== -1) {
        remaining = remaining.slice(deckPos + deck.length).replace(/^[.!?\s]+/, "");
      }
    }
    bodyText = truncateSummary(remaining || bodyText, tier);
  }

  return (
    <article className={`np-article np-article--${tier}`}>
      {/* Headline + Decks */}
      {decks.length > 0 ? (
        <div className="np-headline-deck">
          <h2 className="np-article__headline">{story.title}</h2>
          {decks.map((deck, i) => (
            <p
              key={i}
              className={`np-headline-deck__sub np-headline-deck__sub--${i + 1}`}
            >
              {deck}
            </p>
          ))}
        </div>
      ) : (
        <h2 className="np-article__headline">{story.title}</h2>
      )}

      <p className="np-article__byline">
        {articleByline(story.source.count, story.sigilData.tierBreakdown)}
      </p>

      <p className="np-article__summary">
        <span className="np-article__dateline">{dateline} &mdash; </span>
        {bodyText}
      </p>
    </article>
  );
}

// --- Filler ---

function Filler({ item }: { item: FillerItem }) {
  return (
    <div className="np-filler">
      {item.heading && <p className="np-filler__heading">{item.heading}</p>}
      <p className="np-filler__text">{item.text}</p>
    </div>
  );
}

// --- Classifieds ---

function Classifieds({
  lastUpdated,
  storyCount,
}: {
  lastUpdated: string | null;
  storyCount: number;
}) {
  const closedTime = lastUpdated
    ? new Date(lastUpdated).toLocaleString("en-US", {
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
        month: "short",
        day: "numeric",
      })
    : "twice daily";

  return (
    <div className="np-classifieds">
      <div className="np-classifieds__grid">
        <div className="np-classified-ad">
          <span className="np-classified-ad__heading">
            Public Notice &mdash;
          </span>
          This edition compiled from {storyCount} stories across 200 curated
          news organisations. All bias assessments computed algorithmically by
          rule-based natural language processing. No editorial judgments were
          made in the preparation of this broadsheet.
        </div>
        <div className="np-classified-ad">
          <span className="np-classified-ad__heading">
            Free of Charge &mdash;
          </span>
          This publication costs nothing. It will always cost nothing. No
          subscription required. No advertisements placed. No data collected
          from readers. This is not a trick. Enquiries to the publisher.
        </div>
        <div className="np-classified-ad">
          <span className="np-classified-ad__heading">
            Last Dispatch &mdash;
          </span>
          Press closed: {closedTime}. Next edition at dawn. Weather forecast:
          partly cloudy with a high probability of framing divergence across
          the major wire services. Outlook: contested.
        </div>
      </div>
    </div>
  );
}

// --- Colophon ---

function Colophon({ edition }: { edition: string }) {
  const now = new Date();
  const dateStr = now.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  return (
    <footer className="np-colophon">
      <hr className="np-colophon__rule" />
      <p>
        Void News &middot; The {edition} Edition &middot; {dateStr}
      </p>
      <p>
        <a href="/void--news/" className="np-colophon__link">
          Return to the Digital Edition
        </a>
      </p>
    </footer>
  );
}

// --- PDF Export ---

function PdfExportButton() {
  const handleExport = useCallback(() => {
    window.print();
  }, []);

  return (
    <div className="np-pdf-action">
      <button
        type="button"
        className="np-pdf-btn"
        onClick={handleExport}
        title="Export to PDF via browser print dialog"
      >
        PDF
      </button>
    </div>
  );
}

// ===== MAIN PAGE COMPONENT =====

export default function PaperContent({ edition }: { edition: Edition }) {
  const [allStories, setAllStories] = useState<Story[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const enrichedFields = `id,title,summary,category,section,sections,importance_score,source_count,first_published,last_updated,divergence_score,headline_rank,coverage_velocity,bias_diversity,consensus_points,divergence_points`;

        const { data: clusters } = await supabase
          .from("story_clusters")
          .select(enrichedFields)
          .contains("sections", [edition])
          .order("headline_rank", { ascending: false })
          .limit(150);

        const stories = (clusters || []).map((c) => buildStory(c, true));
        stories.sort((a, b) => b.headlineRank - a.headlineRank);
        setAllStories(stories);
      } catch (err) {
        console.error("Paper page load failed:", err);
      } finally {
        setIsLoading(false);
      }

      // Pipeline timestamp
      try {
        const { data: run } = await supabase
          .from("pipeline_runs")
          .select("completed_at")
          .eq("status", "completed")
          .order("completed_at", { ascending: false })
          .limit(1)
          .single();
        if (run?.completed_at) setLastUpdated(run.completed_at);
      } catch {
        /* ignore */
      }
    }

    load();
  }, [edition]);

  // --- Distribute stories into zones ---
  const layout = distributeStories(allStories, edition);
  const sectionConfig = getSectionConfig(edition);

  const hour = new Date().getUTCHours();
  const editionDisplayName =
    edition === "us"
      ? "United States"
      : edition === "india"
        ? "India"
        : hour < 17
          ? "Morning"
          : "Evening";

  return (
    <div className="np-root">
      <Masthead lastUpdated={lastUpdated} edition={edition} />

      {isLoading && (
        <p className="np-loading">
          Setting type &mdash; your edition is being prepared&hellip;
        </p>
      )}

      {/* ===== FRONT PAGE — 3-Zone Layout ===== */}
      {!isLoading && allStories.length > 0 && (
        <div className="np-front">
          {/* Zone A — Left columns */}
          <div className="np-front__zone-a">
            {layout.zoneA.map((story, i) => (
              <Article
                key={story.id}
                story={story}
                tier={assignTier(i === 0 ? 2 : 4 + i, story)}
                edition={edition}

              />
            ))}
          </div>

          {/* Zone B — Center (Lead) */}
          <div className="np-front__zone-b">
            {layout.zoneB.map((story, i) => (
              <Article
                key={story.id}
                story={story}
                tier={i === 0 ? "banner" : "standard"}
                edition={edition}

              />
            ))}
          </div>

          {/* Zone C — Right columns */}
          <div className="np-front__zone-c">
            {layout.zoneC.map((story, i) => (
              <Article
                key={story.id}
                story={story}
                tier={assignTier(i === 0 ? 1 : 4 + i, story)}
                edition={edition}

              />
            ))}
          </div>
        </div>
      )}

      {/* ===== ORNAMENTAL RULE ===== */}
      {!isLoading && allStories.length > 0 && (
        <hr className="np-ornamental-rule" aria-hidden="true" />
      )}

      {/* ===== SECTION FLOW — CSS Multi-Column ===== */}
      {!isLoading && layout.sectionStories.length > 0 && (
        <>
          <SectionLabel label={sectionConfig.primary} />
          <div className="np-section-flow">
            {layout.sectionStories.map((story, i) => (
              <Article
                key={story.id}
                story={story}
                tier={assignTier(8 + i, story)}
                edition={edition}
              />
            ))}
            {/* Fillers fill remaining column space */}
            {layout.fillers.map((filler, i) => (
              <Filler key={`filler-${i}`} item={filler} />
            ))}
          </div>
        </>
      )}

      {/* ===== CLASSIFIEDS ===== */}
      {!isLoading && allStories.length > 0 && (
        <Classifieds
          lastUpdated={lastUpdated}
          storyCount={allStories.length}
        />
      )}

      {/* ===== COLOPHON ===== */}
      {!isLoading && <Colophon edition={editionDisplayName} />}

      {/* ===== PDF EXPORT (subtle, outside canvas) ===== */}
      <PdfExportButton />
    </div>
  );
}
