"use client";

import Sigil from "./Sigil";
import type { OpinionArticle } from "../lib/types";
import type { SigilData } from "../lib/types";
import { timeAgo } from "../lib/utils";

/* --------------------------------------------------------------------------
   OpinionCard — individual opinion/editorial article card
   No deep dive, no clustering. Headline links to original article.
   Left border accent: blue (left lean) | gray (center) | red (right lean)
   -------------------------------------------------------------------------- */

interface OpinionCardProps {
  article: OpinionArticle;
  featured?: boolean;
}

function leanBorderColor(lean: number): string {
  if (lean <= 40) return "var(--bias-left, #3B82F6)";
  if (lean <= 60) return "var(--bias-center, #9CA3AF)";
  return "var(--bias-right, #EF4444)";
}

function buildSigilData(article: OpinionArticle): SigilData {
  return {
    politicalLean: article.politicalLean,
    sensationalism: article.sensationalism,
    opinionFact: 75, // these are opinion articles by definition
    factualRigor: 50,
    framing: 50,
    agreement: 0,
    sourceCount: 1,
    pending: false,
    opinionLabel: "Opinion",
  };
}

function tierLabel(tier: OpinionArticle["sourceTier"]): string {
  if (tier === "us_major") return "US Major";
  if (tier === "international") return "Intl";
  return "Independent";
}

export default function OpinionCard({ article, featured = false }: OpinionCardProps) {
  const excerpt =
    article.summary.length > 200
      ? article.summary.slice(0, 200).replace(/\s+\S*$/, "") + "\u2026"
      : article.summary;

  const borderColor = leanBorderColor(article.politicalLean);
  const sigilData = buildSigilData(article);

  return (
    <article
      className={`opinion-card${featured ? " opinion-card--featured" : ""}`}
      style={{ borderLeftColor: borderColor }}
    >
      {/* Byline row: source · author · time */}
      <div className="opinion-card__byline">
        <span className="opinion-card__source">
          {article.sourceName}
          <span className="opinion-card__tier">{tierLabel(article.sourceTier)}</span>
        </span>
        {article.author && (
          <span className="opinion-card__author">{article.author}</span>
        )}
        <span className="opinion-card__time">{timeAgo(article.publishedAt)}</span>
      </div>

      {/* Headline — links to original article */}
      <h3 className="opinion-card__headline">
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="opinion-card__headline-link"
        >
          {article.title}
        </a>
      </h3>

      {/* Excerpt */}
      {excerpt && (
        <p className="opinion-card__excerpt">{excerpt}</p>
      )}

      {/* Bias indicator row */}
      <div className="opinion-card__footer">
        <Sigil data={sigilData} mode="oped" size="sm" />
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="opinion-card__read-link"
          tabIndex={-1}
          aria-hidden="true"
        >
          Read at {article.sourceName} &#8599;
        </a>
      </div>
    </article>
  );
}
