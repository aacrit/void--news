"use client";

import { useState, useEffect, useRef, useCallback } from "react";
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
  assignTier,
  getDateline,
  distributeStories,
  getSectionConfig,
  capitalize,
  editionSubtitle,
} from "./paperUtils";
import "./paper.css";

/* ---------------------------------------------------------------------------
   E-Paper Edition — Modern Broadsheet
   Clean 4-column layout. Playfair/Inter/JetBrains typography.
   Full summaries. No decks, no fillers, no costume.
   --------------------------------------------------------------------------- */

// --- Helpers ---

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

/** Strip trailing ellipsis from RSS fallback summaries */
function cleanSummary(text: string): string {
  let cleaned = text
    .replace(/[\s.]*\.{2,}$/, "")
    .replace(/\u2026$/, "")
    .trimEnd();
  if (cleaned && !/[.!?"]$/.test(cleaned)) cleaned += ".";
  return cleaned;
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

// --- Lean label ---

function leanLabel(score: number): string {
  if (score <= 15) return "Far Left";
  if (score <= 30) return "Left";
  if (score <= 42) return "Center-Left";
  if (score <= 58) return "Center";
  if (score <= 70) return "Center-Right";
  if (score <= 85) return "Right";
  return "Far Right";
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

  const subtitle = editionSubtitle(edition);
  const basePath = "/void--news/paper";

  return (
    <header className="np-masthead">
      <hr className="np-masthead__rule-top" />

      <h1 className="np-masthead__nameplate">Void News.</h1>
      <p className="np-masthead__date">
        {dateStr}
        {subtitle && <> &middot; {subtitle}</>}
        {lastUpdated && (
          <>
            {" "}&middot; Updated{" "}
            {new Date(lastUpdated).toLocaleString("en-US", {
              hour: "numeric",
              minute: "2-digit",
              hour12: true,
            })}
          </>
        )}
      </p>

      <hr className="np-masthead__rule-bottom" />

      <nav className="np-edition-nav" aria-label="Edition">
        <a
          href={basePath}
          className={edition === "world" ? "np-edition-nav__active" : ""}
        >
          World
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
    <div className="np-section-label">
      <p className="np-section-label__text">{label}</p>
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
  const bodyText = cleanSummary(story.summary);

  return (
    <article className={`np-article np-article--${tier}`}>
      <h2 className="np-article__headline">{story.title}</h2>

      <p className="np-article__byline">
        {story.source.count} {story.source.count === 1 ? "source" : "sources"}
        {" \u00B7 "}
        {leanLabel(story.biasScores.politicalLean)}
      </p>

      <p className="np-article__summary">
        <span className="np-article__dateline">{dateline} &mdash; </span>
        {bodyText}
      </p>
    </article>
  );
}

// --- Colophon ---

function Colophon({ edition, storyCount }: { edition: string; storyCount: number }) {
  const now = new Date();
  const dateStr = now.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  return (
    <footer className="np-colophon">
      <p>
        Void News &middot; {edition} Edition &middot; {dateStr}
        &middot; {storyCount} stories from 200+ sources
      </p>
      <p>
        <a href="/void--news/" className="np-colophon__link">
          Return to the Digital Edition
        </a>
      </p>
    </footer>
  );
}

// --- Export Button — PNG snapshot ---

function ExportButton({
  targetRef,
  edition,
}: {
  targetRef: React.RefObject<HTMLDivElement | null>;
  edition: Edition;
}) {
  const [exporting, setExporting] = useState(false);

  const handleExport = useCallback(async () => {
    if (!targetRef.current || exporting) return;
    setExporting(true);

    try {
      const html2canvas = (await import("html2canvas")).default;
      const canvas = await html2canvas(targetRef.current, {
        scale: 2,
        useCORS: true,
        backgroundColor: "#F8F6F1",
        logging: false,
        ignoreElements: (el: Element) => el.classList?.contains("np-pdf-action"),
      });

      canvas.toBlob(
        (blob) => {
          if (!blob) return;
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          const date = new Date().toISOString().slice(0, 10);
          a.href = url;
          a.download = `void-news-${edition}-${date}.png`;
          a.click();
          URL.revokeObjectURL(url);
          setExporting(false);
        },
        "image/png",
        1.0,
      );
    } catch (err) {
      console.error("Export failed:", err);
      setExporting(false);
    }
  }, [targetRef, edition, exporting]);

  return (
    <div className="np-pdf-action">
      <button
        type="button"
        className="np-pdf-btn"
        onClick={handleExport}
        disabled={exporting}
        title="Download as PNG image"
      >
        {exporting ? "Exporting\u2026" : "PNG"}
      </button>
    </div>
  );
}

// ===== MAIN COMPONENT =====

export default function PaperContent({ edition }: { edition: Edition }) {
  const rootRef = useRef<HTMLDivElement>(null);
  const [allStories, setAllStories] = useState<Story[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [tldr, setTldr] = useState<string | null>(null);
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
          .limit(500);

        const stories = (clusters || []).map((c) => buildStory(c, true));
        stories.sort((a, b) => b.headlineRank - a.headlineRank);
        setAllStories(stories);
      } catch (err) {
        console.error("Paper page load failed:", err);
      } finally {
        setIsLoading(false);
      }

      // Pipeline timestamp + TL;DR
      try {
        const { data: run } = await supabase
          .from("pipeline_runs")
          .select("completed_at")
          .eq("status", "completed")
          .order("completed_at", { ascending: false })
          .limit(1)
          .single();
        if (run?.completed_at) setLastUpdated(run.completed_at);
      } catch { /* ignore */ }

      try {
        const { data: brief } = await supabase
          .from("daily_briefs")
          .select("tldr_text")
          .eq("edition", edition)
          .order("created_at", { ascending: false })
          .limit(1)
          .single();
        if (brief?.tldr_text) setTldr(brief.tldr_text);
      } catch { /* ignore */ }
    }

    load();
  }, [edition]);

  const layout = distributeStories(allStories);
  const sectionConfig = getSectionConfig(edition);

  const editionDisplayName =
    edition === "us"
      ? "United States"
      : edition === "india"
        ? "India"
        : "World";

  return (
    <div className="np-root" ref={rootRef}>
      <Masthead lastUpdated={lastUpdated} edition={edition} />

      {isLoading && (
        <p className="np-loading">Loading edition&hellip;</p>
      )}

      {/* ===== TODAY'S BRIEF ===== */}
      {!isLoading && tldr && (
        <div className="np-brief">
          <p className="np-brief__label">Today&rsquo;s Brief</p>
          <p className="np-brief__text">{tldr}</p>
        </div>
      )}

      {/* ===== LEAD STORY ===== */}
      {!isLoading && layout.leadStory && (
        <div className="np-lead">
          <Article
            story={layout.leadStory}
            tier="lead"
            edition={edition}
          />
        </div>
      )}

      {/* ===== TOP STORIES — 2-column grid ===== */}
      {!isLoading && layout.topStories.length > 0 && (
        <div className="np-top-grid">
          {layout.topStories.map((story) => (
            <Article
              key={story.id}
              story={story}
              tier="standard"
              edition={edition}
            />
          ))}
        </div>
      )}

      {/* ===== REMAINING — 4-column flow ===== */}
      {!isLoading && layout.remaining.length > 0 && (
        <>
          <SectionLabel label={sectionConfig.primary} />
          <div className="np-section-flow">
            {layout.remaining.map((story, i) => (
              <Article
                key={story.id}
                story={story}
                tier={assignTier(5 + i, story)}
                edition={edition}
              />
            ))}
          </div>
        </>
      )}

      {/* ===== COLOPHON ===== */}
      {!isLoading && (
        <Colophon
          edition={editionDisplayName}
          storyCount={allStories.length}
        />
      )}

      {/* ===== PNG EXPORT ===== */}
      <ExportButton targetRef={rootRef} edition={edition} />
    </div>
  );
}
