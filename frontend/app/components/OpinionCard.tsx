"use client";

import { useState } from "react";
import Sigil from "./Sigil";
import type { OpinionArticle } from "../lib/types";
import type { SigilData } from "../lib/types";
import { timeAgo } from "../lib/utils";

/* --------------------------------------------------------------------------
   OpinionCard — individual opinion/editorial article card
   Shows inline text (10-12 lines collapsed, expandable to full).
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
    opinionFact: 75,
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
  const [expanded, setExpanded] = useState(false);
  const borderColor = leanBorderColor(article.politicalLean);
  const sigilData = buildSigilData(article);

  const fullText = article.summary || "";
  const isLong = fullText.length > 400;

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

      {/* Headline */}
      <h3 className="opinion-card__headline">
        <span className="opinion-card__headline-link">{article.title}</span>
      </h3>

      {/* Inline article text — 10-12 lines collapsed, expandable */}
      {fullText && (
        <div
          className={`opinion-card__text${expanded ? " opinion-card__text--expanded" : ""}${isLong && !expanded ? " opinion-card__text--truncated" : ""}`}
        >
          <p className="opinion-card__text-content">{fullText}</p>
        </div>
      )}

      {/* Expand / collapse + source link row */}
      <div className="opinion-card__footer">
        <Sigil data={sigilData} size="sm" />

        <div className="opinion-card__actions">
          {isLong && (
            <button
              className="opinion-card__expand-btn"
              onClick={() => setExpanded(!expanded)}
              aria-expanded={expanded}
            >
              {expanded ? "Show less" : "Read more"}
            </button>
          )}
          <a
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="opinion-card__read-link"
          >
            Source &#8599;
          </a>
        </div>
      </div>
    </article>
  );
}
