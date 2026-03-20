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
import { supabase, fetchOpinionArticles } from "../lib/supabase";
import "./paper.css";

// --- Op-ed article type (individual source articles, not cluster summaries) ---
interface OpEdArticle {
  id: string;
  title: string;       // Original source headline
  summary: string;     // Full article summary — shown without truncation
  url: string;         // Source link
  sourceName: string;  // e.g., "The Washington Post"
  sourceTier: string;  // us_major, international, independent
  publishedAt: string;
  opinionLabel: OpinionLabel;
  politicalLean: number;
  sensationalism: number;
}

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

function isOpinionPiece(label: OpinionLabel): boolean {
  return label === "Opinion" || label === "Editorial";
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
  const opinion = isOpinionPiece(story.sigilData.opinionLabel);

  return (
    <article className={`np-article np-article--${size}${opinion ? " np-article--opinion" : ""}`}>
      {opinion && (
        <p className="np-article__opinion-label">{story.sigilData.opinionLabel}</p>
      )}
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

// --- Op-Ed Article Component ---
// Renders individual opinion/editorial pieces from a single source.
// No dateline — the source attribution IS the provenance.

function OpEdArticleComponent({ oped }: { oped: OpEdArticle }) {
  return (
    <article className="np-article np-article--secondary np-article--opinion np-article--oped">
      <p className="np-article__opinion-label">{oped.opinionLabel}</p>
      <h2 className="np-article__headline">{oped.title}</h2>
      <p className="np-article__byline">From {oped.sourceName}</p>
      <p className="np-article__summary">{oped.summary}</p>
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
  const [worldOpEds, setWorldOpEds] = useState<OpEdArticle[]>([]);
  const [usOpEds, setUsOpEds] = useState<OpEdArticle[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const enrichedFields = `id,title,summary,category,section,content_type,importance_score,source_count,first_published,last_updated,divergence_score,headline_rank,coverage_velocity,bias_diversity,consensus_points,divergence_points`;

      // Fetch all stories and op-eds in parallel
      const [worldRes, usRes, worldOpEdRaw, usOpEdRaw] = await Promise.all([
        supabase
          .from("story_clusters")
          .select(enrichedFields)
          .contains("sections", ["world"])
          // Exclude opinion clusters — those appear as individual op-eds below
          .neq("content_type", "opinion")
          .order("headline_rank", { ascending: false })
          .limit(25),
        supabase
          .from("story_clusters")
          .select(enrichedFields)
          .contains("sections", ["us"])
          .neq("content_type", "opinion")
          .order("headline_rank", { ascending: false })
          .limit(25),
        fetchOpinionArticles("world"),
        fetchOpinionArticles("us"),
      ]);

      const worldClusters = worldRes.data || [];
      const usClusters = usRes.data || [];

      // Deduplicate — a cluster with multiple sections can appear in both queries
      const seen = new Set<string>();
      const stories: Story[] = [];
      for (const c of [...worldClusters, ...usClusters]) {
        if (!seen.has(c.id)) {
          seen.add(c.id);
          stories.push(buildStory(c, true));
        }
      }
      stories.sort((a, b) => b.headlineRank - a.headlineRank);

      // Map OpinionArticle → OpEdArticle
      function mapOpEd(raw: typeof worldOpEdRaw[number]): OpEdArticle {
        const opinionScore = 65; // fetchOpinionArticles only returns opinion clusters
        return {
          id: raw.id,
          title: raw.title,
          summary: raw.summary,
          url: raw.url,
          sourceName: raw.sourceName,
          sourceTier: raw.sourceTier,
          publishedAt: raw.publishedAt,
          opinionLabel: deriveOpinionLabel(opinionScore),
          politicalLean: raw.politicalLean,
          sensationalism: raw.sensationalism,
        };
      }

      setAllStories(stories);
      setWorldOpEds(worldOpEdRaw.map(mapOpEd));
      setUsOpEds(usOpEdRaw.map(mapOpEd));
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

  // --- Section derivation — realistic broadsheet count ---
  // A real 1920s front page had ~15-20 stories total, not 100+.
  // Keep only the highest-ranked stories for a readable edition.
  const FRONT_PAGE_COUNT = 3;
  const SECTION_CAP = 8;       // max news stories per section
  const OPED_CAP = 3;          // max op-eds per section

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

  // --- Interleave op-eds into a story list ---
  // Returns a flat array of tagged items: cluster stories with an op-ed
  // inserted after every 4th cluster story. Op-eds are consumed in order.
  type SectionItem =
    | { kind: "story"; story: Story }
    | { kind: "oped"; oped: OpEdArticle };

  function interleave(stories: Story[], opeds: OpEdArticle[]): SectionItem[] {
    const result: SectionItem[] = [];
    let opedIndex = 0;
    for (let i = 0; i < stories.length; i++) {
      result.push({ kind: "story", story: stories[i] });
      // After every 4th story, insert the next op-ed if available
      if ((i + 1) % 4 === 0 && opedIndex < opeds.length) {
        result.push({ kind: "oped", oped: opeds[opedIndex++] });
      }
    }
    // Append any remaining op-eds at the end of the section
    while (opedIndex < opeds.length) {
      result.push({ kind: "oped", oped: opeds[opedIndex++] });
    }
    return result;
  }

  const worldItems = interleave(worldStories, worldOpEds.slice(0, OPED_CAP));
  const usItems = interleave(usStories, usOpEds.slice(0, OPED_CAP));

  const hour = new Date().getUTCHours();
  const editionName = hour < 17 ? "Morning" : "Evening";

  return (
    <div className="np-root">
      <Masthead lastUpdated={lastUpdated} />

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

      {/* World News — cluster stories interleaved with op-eds */}
      {!isLoading && worldItems.length > 0 && (
        <>
          <SectionLabel label="WORLD NEWS" />
          <div className="np-broadsheet">
            {worldItems.map((item) =>
              item.kind === "story" ? (
                <div key={item.story.id} className="np-col">
                  <Article story={item.story} size="secondary" />
                </div>
              ) : (
                <div key={`oped-${item.oped.id}`} className="np-col">
                  <OpEdArticleComponent oped={item.oped} />
                </div>
              )
            )}
          </div>
        </>
      )}

      {/* Domestic — cluster stories interleaved with op-eds */}
      {!isLoading && usItems.length > 0 && (
        <>
          <SectionLabel label="DOMESTIC" />
          <div className="np-broadsheet">
            {usItems.map((item) =>
              item.kind === "story" ? (
                <div key={item.story.id} className="np-col">
                  <Article story={item.story} size="secondary" />
                </div>
              ) : (
                <div key={`oped-${item.oped.id}`} className="np-col">
                  <OpEdArticleComponent oped={item.oped} />
                </div>
              )
            )}
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
