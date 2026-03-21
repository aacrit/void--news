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

/**
 * M002: Runtime guard for bias_diversity JSONB from Supabase.
 * Returns null if the value is not a plain object.
 */
function parseBiasDiversity(raw: unknown): Record<string, unknown> | null {
  if (raw == null) return null;
  if (typeof raw !== "object" || Array.isArray(raw)) return null;
  return raw as Record<string, unknown>;
}

function safeNum(bd: Record<string, unknown>, key: string, fallback: number): number {
  const v = bd[key];
  if (typeof v === "number" && !Number.isNaN(v)) return v;
  return fallback;
}

function safeTierBreakdown(bd: Record<string, unknown>): Record<string, number> | undefined {
  const raw = bd["tier_breakdown"];
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return undefined;
  const result: Record<string, number> = {};
  for (const [k, v] of Object.entries(raw as Record<string, unknown>)) {
    if (typeof v === "number" && Number.isFinite(v)) result[k] = v;
  }
  return Object.keys(result).length > 0 ? result : undefined;
}

function capitalize(s: string): string {
  if (!s) return s;
  const map: Record<string, string> = {
    politics: "Politics", economy: "Economy", science: "Science",
    health: "Health", culture: "Culture",
    conflict: "Politics", tech: "Science", technology: "Science",
    environment: "Health", sports: "Culture",
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
// Modelled on authentic 1920s NYT front page structure:
//   [motto ear left | — | copyright ear right]
//   [thick rule]
//   [nameplate — Chomsky blackletter, English Textura style]
//   [thick rule]
//   [No. {issueNo} | DATE IN FULL CAPS | Free of Charge]
//   [thin rule]

function Masthead({ lastUpdated }: { lastUpdated: string | null }) {
  const now = new Date();

  const dateStr = now.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  }).toUpperCase();

  // Issue number counts days since launch — shown as plain Arabic numeral.
  // Real newspapers earned volume numbers over decades; we don't pretend.
  const epoch = new Date("2026-03-01T00:00:00Z");
  const issueNo = Math.max(1, Math.floor((now.getTime() - epoch.getTime()) / 86400000));

  // Copyright year for right ear
  const year = now.getFullYear();

  // "Press closed" time for right ear — falls back to launch date if no run yet
  const pressTime = lastUpdated
    ? new Date(lastUpdated).toLocaleString("en-US", {
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      })
    : null;

  return (
    <header className="np-masthead">
      {/* Top ears — motto left, copyright right, ruled box around each */}
      <div className="np-masthead__ears">
        <div className="np-masthead__ear np-masthead__ear--left">
          <span className="np-masthead__ear-text">
            &ldquo;All the Bias That&rsquo;s Fit to Print&rdquo;
          </span>
        </div>
        <div className="np-masthead__ear np-masthead__ear--right">
          <span className="np-masthead__ear-text">
            Copyright {year}, Void News
            {pressTime && (
              <> &mdash; Press closed {pressTime}</>
            )}
          </span>
        </div>
      </div>

      {/* Top rule — thick, ink-black */}
      <hr className="np-masthead__top-rule" />

      {/* Nameplate — Chomsky blackletter */}
      <h1 className="np-masthead__nameplate">Void News.</h1>

      {/* Sub-nameplate rule — double rule, thick over thin */}
      <hr className="np-double-rule" aria-hidden="true" />

      {/* Info bar — No. / Date / Price — authentic three-column layout */}
      <div className="np-masthead__info">
        <span className="np-masthead__info-left">
          No.&thinsp;{issueNo}
        </span>
        <span className="np-masthead__info-center">{dateStr}</span>
        <span className="np-masthead__info-right">Free of Charge</span>
      </div>

      {/* Closing rule under info bar */}
      <hr className="np-double-rule" aria-hidden="true" />
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

function articleByline(sourceCount: number, tierBreakdown?: Record<string, number>): string {
  if (sourceCount === 1) {
    // Describe the single source by its tier
    if (tierBreakdown?.us_major) return "From a major U.S. outlet";
    if (tierBreakdown?.international) return "From an international bureau";
    if (tierBreakdown?.independent) return "From an independent outlet";
    return "From a single report";
  }
  if (sourceCount <= 3) return `Compiled from ${sourceCount} sources`;
  return `From multiple outlets \u2014 ${sourceCount} Sources`;
}

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
        {articleByline(story.source.count, story.sigilData.tierBreakdown)}
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

// --- Data fetching & story building (duplicated from HomeContent) ---

/* eslint-disable @typescript-eslint/no-explicit-any */
function buildStory(cluster: any, usingEnriched: boolean): Story {
  // M002: Runtime-validate bias_diversity JSONB before any property access.
  const bd = usingEnriched ? parseBiasDiversity(cluster.bias_diversity) : null;
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

  const biasSpread: BiasSpread | undefined = bd && bd["lean_spread"] != null
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
  const opinionLabel = (bd?.["avg_opinion_label"] as OpinionLabel) ?? deriveOpinionLabel(biasScores.opinionFact);
  const lensData: ThreeLensData = {
    lean: biasScores.politicalLean,
    coverage: bd ? safeNum(bd, "coverage_score", deriveCoverageScore(
      sourceCount, biasScores.factualRigor, biasSpread?.aggregateConfidence ?? 0.5,
    )) : deriveCoverageScore(sourceCount, biasScores.factualRigor, 0.5),
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
    publishedAt: cluster.first_published || cluster.last_updated || new Date().toISOString(),
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
      try {
        const enrichedFields = `id,title,summary,category,section,sections,importance_score,source_count,first_published,last_updated,divergence_score,headline_rank,coverage_velocity,bias_diversity,consensus_points,divergence_points`;

        let worldClusters: any[] = [];
        let usClusters: any[] = [];

        const [worldRes, usRes] = await Promise.all([
          supabase
            .from("story_clusters")
            .select(enrichedFields)
            .contains("sections", ["world"])
            .order("headline_rank", { ascending: false })
            .limit(100),
          supabase
            .from("story_clusters")
            .select(enrichedFields)
            .contains("sections", ["us"])
            .order("headline_rank", { ascending: false })
            .limit(100),
        ]);

        worldClusters = worldRes.data || [];
        usClusters = usRes.data || [];

        // Deduplicate
        const seen = new Set<string>();
        const stories: Story[] = [];
        for (const c of [...worldClusters, ...usClusters]) {
          if (!seen.has(c.id)) {
            seen.add(c.id);
            stories.push(buildStory(c, true));
          }
        }
        stories.sort((a, b) => b.headlineRank - a.headlineRank);

        setAllStories(stories);
      } catch (err) {
        console.error("Paper page load failed:", err);
      } finally {
        setIsLoading(false);
      }

      // Pipeline timestamp (fire-and-forget)
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
    }

    load();
  }, []);

  // --- Section derivation — realistic broadsheet count ---
  // A real 1920s front page had ~15-20 stories total, not 100+.
  // Keep only the highest-ranked stories for a readable edition.
  const FRONT_PAGE_COUNT = 3;
  const SECTION_CAP = 50;      // max news stories per section

  const frontPage = allStories.slice(0, FRONT_PAGE_COUNT);
  const lead = frontPage[0];
  const primaryLeft = frontPage[1];
  const primaryRight = frontPage[2];
  const frontPageIds = new Set(frontPage.map((s) => s.id));

  const worldStories = allStories
    .filter((s) => s.section === "world" && !frontPageIds.has(s.id))
    .slice(0, SECTION_CAP);

  const usStories = allStories
    .filter((s) => s.section === "us" && !frontPageIds.has(s.id))
    .slice(0, SECTION_CAP);

  const hour = new Date().getUTCHours();
  const editionName = hour < 17 ? "Morning" : "Evening";

  return (
    <div className="np-root">
      <Masthead lastUpdated={lastUpdated} />

      {isLoading && (
        <p className="np-loading">Setting type &mdash; your edition is being prepared&hellip;</p>
      )}

      {/* Front Page — 3-column hero layout, or single-column if primary stories missing */}
      {!isLoading && lead && (
        <div className={`np-broadsheet ${
          (primaryLeft || primaryRight) ? 'np-broadsheet--front' : 'np-broadsheet--lead-only'
        }`}>
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

      {/* World News */}
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

      {/* Domestic */}
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
