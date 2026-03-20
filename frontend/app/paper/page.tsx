"use client";

import { useState, useEffect } from "react";
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
import "./paper.css";

/* ---------------------------------------------------------------------------
   E-Paper Edition — 1930s Static Broadsheet Newspaper
   Full-size broadsheet. All stories. Full summaries. Bias as editorial prose.
   No interactivity. Period typography. Aged paper texture.
   --------------------------------------------------------------------------- */

// --- Helpers (duplicated from HomeContent to keep blast radius zero) ---

function capitalize(s: string): string {
  if (!s) return s;
  const map: Record<string, string> = {
    politics: "Politics", economy: "Economy", tech: "Tech", technology: "Tech",
    health: "Health", environment: "Environment", conflict: "Conflict",
    science: "Science", culture: "Culture", sports: "Sports",
  };
  return map[s.toLowerCase()] || s.charAt(0).toUpperCase() + s.slice(1);
}

function deriveOpinionLabel(score: number): OpinionLabel {
  if (score <= 25) return "Reporting";
  if (score <= 50) return "Analysis";
  if (score <= 75) return "Opinion";
  return "Editorial";
}

function deriveCoverageScore(sourceCount: number, factualRigor: number, confidence: number): number {
  const sourceNorm = Math.min(1.0, sourceCount / 10.0);
  const rigorNorm = factualRigor / 100.0;
  const confNorm = Math.min(1.0, confidence);
  return Math.round((sourceNorm * 0.35 + 0.2 + confNorm * 0.20 + rigorNorm * 0.25) * 100);
}

// --- Datelines (section-aware: US cities for US news, international for world) ---

const US_DATELINES: Record<string, string> = {
  Politics: "WASHINGTON, D.C.",
  Economy: "NEW YORK",
  Conflict: "WASHINGTON, D.C.",
  Tech: "SAN FRANCISCO",
  Health: "WASHINGTON, D.C.",
  Environment: "WASHINGTON, D.C.",
  Science: "BOSTON",
  Culture: "NEW YORK",
  Sports: "NEW YORK",
};

const WORLD_DATELINES: Record<string, string> = {
  Politics: "LONDON",
  Economy: "LONDON",
  Conflict: "BEIRUT",
  Tech: "TOKYO",
  Health: "GENEVA",
  Environment: "NAIROBI",
  Science: "GENEVA",
  Culture: "PARIS",
  Sports: "LAUSANNE",
};

// --- Masthead ---

function Masthead({ lastUpdated, storyCount }: { lastUpdated: string | null; storyCount: number }) {
  const now = new Date();
  const hour = now.getUTCHours();
  const edition = hour < 17 ? "Morning" : "Evening";

  const dateStr = now.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  }).toUpperCase();

  const epoch = new Date("2026-03-01T00:00:00Z");
  const issueNo = Math.max(1, Math.floor((now.getTime() - epoch.getTime()) / 86400000));

  return (
    <header className="np-masthead">
      <hr className="np-masthead__motto-rule" />
      <p className="np-masthead__motto">&ldquo;All the Bias That&rsquo;s Fit to Print&rdquo;</p>
      <hr className="np-masthead__thick-rule" />
      <h1 className="np-masthead__nameplate">void news</h1>
      <hr className="np-double-rule" aria-hidden="true" />
      <div className="np-masthead__info">
        <span className="np-masthead__info-left">
          Vol. I &middot; No. {issueNo}
        </span>
        <span className="np-masthead__info-center">{dateStr}</span>
        <span className="np-masthead__info-right">Gratis</span>
      </div>
      <hr className="np-thin-rule" />
      <div className="np-masthead__edition-bar">
        <span>{edition.toUpperCase()} EDITION</span>
        <span>{storyCount > 0 ? `${storyCount} STORIES` : "200 SOURCES"}</span>
      </div>
      <hr className="np-double-rule" aria-hidden="true" />
    </header>
  );
}

// --- Section Label ---

function SectionLabel({ label }: { label: string }) {
  return (
    <div className="np-section-label" role="separator">
      <hr className="np-section-label__rule-top" />
      <p className="np-section-label__text">&starf; &ensp;{label}&ensp; &starf;</p>
      <hr className="np-section-label__rule-bottom" />
    </div>
  );
}

// --- Article ---

function Article({
  story,
  size,
}: {
  story: Story;
  size: "lead" | "primary" | "secondary";
}) {
  const datelineMap = story.section === "us" ? US_DATELINES : WORLD_DATELINES;
  const dateline = datelineMap[story.category] || (story.section === "us" ? "WASHINGTON, D.C." : "LONDON");

  return (
    <article className={`np-article np-article--${size}`}>
      <h2 className="np-article__headline">{story.title}</h2>
      <p className="np-article__byline">
        By Our Correspondents &mdash; {story.source.count} {story.source.count === 1 ? "Source" : "Sources"}
      </p>
      <p className="np-article__summary">
        <span className="np-article__dateline">{dateline} &mdash; </span>
        {story.summary}
      </p>
    </article>
  );
}

// --- Classifieds ---

function Classifieds({ lastUpdated, storyCount }: { lastUpdated: string | null; storyCount: number }) {
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
          <span className="np-classified-ad__heading">Public Notice &mdash;</span>
          This edition compiled from {storyCount} stories across 200 curated news
          organisations. All bias assessments computed algorithmically by rule-based
          natural language processing. No editorial judgments were made in the
          preparation of this broadsheet.
        </div>
        <div className="np-classified-ad">
          <span className="np-classified-ad__heading">Free of Charge &mdash;</span>
          This publication costs nothing. It will always cost nothing. No subscription
          required. No advertisements placed. No data collected from readers. This is
          not a trick. Enquiries to the publisher.
        </div>
        <div className="np-classified-ad">
          <span className="np-classified-ad__heading">Last Dispatch &mdash;</span>
          Press closed: {closedTime}. Next edition at dawn. Weather forecast: partly
          cloudy with a high probability of framing divergence across the major wire
          services. Outlook: contested.
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
        void --news &middot; The {edition} Edition &middot; {dateStr}
      </p>
      <p>
        Printed on digital presses &middot; 200 curated sources &middot; 6-axis bias analysis
      </p>
      <p>
        <a href="/void--news/" className="np-colophon__link">
          Return to the Digital Edition
        </a>
      </p>
    </footer>
  );
}

// --- Data fetching & story building (duplicated from HomeContent) ---

/* eslint-disable @typescript-eslint/no-explicit-any */
function buildStory(cluster: any, usingEnriched: boolean): Story {
  const bd = usingEnriched ? cluster.bias_diversity : null;
  const hasBiasData = !!(bd && bd.avg_political_lean != null);

  const biasScores: BiasScores = hasBiasData
    ? {
        politicalLean: bd.avg_political_lean ?? 50,
        sensationalism: bd.avg_sensationalism ?? 30,
        opinionFact: bd.avg_opinion_fact ?? 25,
        factualRigor: bd.avg_factual_rigor ?? 75,
        framing: bd.avg_framing ?? 40,
      }
    : {
        politicalLean: 50,
        sensationalism: 30,
        opinionFact: 25,
        factualRigor: 75,
        framing: 40,
      };

  const biasSpread: BiasSpread | undefined = bd && bd.lean_spread != null
    ? {
        leanSpread: bd.lean_spread ?? 0,
        framingSpread: bd.framing_spread ?? 0,
        leanRange: bd.lean_range ?? 0,
        sensationalismSpread: bd.sensationalism_spread ?? 0,
        opinionSpread: bd.opinion_spread ?? 0,
        aggregateConfidence: bd.aggregate_confidence ?? 0,
        analyzedCount: bd.analyzed_count ?? 0,
      }
    : undefined;

  const sourceCount = cluster.source_count || 1;
  const opinionLabel = (bd?.avg_opinion_label as OpinionLabel) ?? deriveOpinionLabel(biasScores.opinionFact);
  const lensData: ThreeLensData = {
    lean: biasScores.politicalLean,
    coverage: bd?.coverage_score ?? deriveCoverageScore(
      sourceCount, biasScores.factualRigor, biasSpread?.aggregateConfidence ?? 0.5,
    ),
    sourceCount,
    tierBreakdown: bd?.tier_breakdown,
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
    tierBreakdown: bd?.tier_breakdown,
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
    publishedAt: cluster.first_published || cluster.last_updated || new Date().toISOString(),
    biasScores,
    biasSpread,
    lensData,
    sigilData,
    section: (cluster.section || "world") as Edition,
    importance: cluster.headline_rank || cluster.importance_score || 50,
    divergenceScore: cluster.divergence_score || 0,
    headlineRank: cluster.headline_rank || cluster.importance_score || 50,
    coverageVelocity: cluster.coverage_velocity || 0,
    deepDive: (Array.isArray(rawConsensus) && rawConsensus.length > 0) || (Array.isArray(rawDivergence) && rawDivergence.length > 0)
      ? {
          consensus: Array.isArray(rawConsensus) ? rawConsensus : [],
          divergence: Array.isArray(rawDivergence) ? rawDivergence : [],
          sources: [],
        }
      : undefined,
  };
}
/* eslint-enable @typescript-eslint/no-explicit-any */

// --- Main Page ---

export default function PaperPage() {
  const [allStories, setAllStories] = useState<Story[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const enrichedFields = `id,title,summary,category,section,content_type,importance_score,source_count,first_published,last_updated,divergence_score,headline_rank,coverage_velocity,bias_diversity,consensus_points,divergence_points`;

      // Fetch all stories from both sections
      const [worldRes, usRes] = await Promise.all([
        supabase
          .from("story_clusters")
          .select(enrichedFields)
          .eq("section", "world")
          .order("headline_rank", { ascending: false })
          .limit(100),
        supabase
          .from("story_clusters")
          .select(enrichedFields)
          .eq("section", "us")
          .order("headline_rank", { ascending: false })
          .limit(100),
      ]);

      const worldClusters = worldRes.data || [];
      const usClusters = usRes.data || [];

      const stories = [
        ...worldClusters.map((c) => buildStory(c, true)),
        ...usClusters.map((c) => buildStory(c, true)),
      ].sort((a, b) => b.headlineRank - a.headlineRank);

      setAllStories(stories);
      setIsLoading(false);

      const { data: run } = await supabase
        .from("pipeline_runs")
        .select("completed_at")
        .eq("status", "completed")
        .order("completed_at", { ascending: false })
        .limit(1)
        .single();

      if (run?.completed_at) setLastUpdated(run.completed_at);
    }

    load();
  }, []);

  // --- Section derivation — show ALL stories ---
  const frontPage = allStories.slice(0, 3);
  const lead = frontPage[0];
  const primaryLeft = frontPage[1];
  const primaryRight = frontPage[2];

  // All remaining stories split by section
  const worldStories = allStories
    .filter((s) => s.section === "world")
    .filter((s) => !frontPage.includes(s));

  const usStories = allStories
    .filter((s) => s.section === "us")
    .filter((s) => !frontPage.includes(s));

  const hour = new Date().getUTCHours();
  const editionName = hour < 17 ? "Morning" : "Evening";

  return (
    <div className="np-root">
      <Masthead lastUpdated={lastUpdated} storyCount={allStories.length} />

      {isLoading && (
        <p className="np-loading">Setting type &mdash; your edition is being prepared&hellip;</p>
      )}

      {/* Front Page — 3-column hero layout */}
      {!isLoading && lead && (
        <div className="np-broadsheet np-broadsheet--front">
          {primaryLeft && (
            <div className="np-col">
              <Article story={primaryLeft} size="primary" />
            </div>
          )}
          <div className="np-col">
            <Article story={lead} size="lead" />
          </div>
          {primaryRight && (
            <div className="np-col">
              <Article story={primaryRight} size="primary" />
            </div>
          )}
        </div>
      )}

      {/* World News — all stories */}
      {!isLoading && worldStories.length > 0 && (
        <>
          <SectionLabel label="WORLD NEWS" />
          <div className="np-broadsheet">
            {worldStories.map((story) => (
              <div key={story.id} className="np-col">
                <Article story={story} size="secondary" />
              </div>
            ))}
          </div>
        </>
      )}

      {/* Domestic — all stories */}
      {!isLoading && usStories.length > 0 && (
        <>
          <SectionLabel label="DOMESTIC" />
          <div className="np-broadsheet">
            {usStories.map((story) => (
              <div key={story.id} className="np-col">
                <Article story={story} size="secondary" />
              </div>
            ))}
          </div>
        </>
      )}

      {/* Classifieds & Notices */}
      {!isLoading && allStories.length > 0 && (
        <Classifieds lastUpdated={lastUpdated} storyCount={allStories.length} />
      )}

      {/* Colophon */}
      {!isLoading && <Colophon edition={editionName} />}
    </div>
  );
}
