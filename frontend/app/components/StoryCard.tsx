"use client";

import type { Story } from "../lib/types";
import { timeAgo } from "../lib/mockData";
import { ArrowSquareOut, Stack } from "@phosphor-icons/react";
import BiasStamp from "./BiasStamp";

interface StoryCardProps {
  story: Story;
  index: number;
  onStoryClick?: (story: Story) => void;
}

/* ---------------------------------------------------------------------------
   StoryCard — Newspaper-style article card
   Desktop: horizontal layout with inline metadata
   Mobile: vertical stack
   Entrance animation: fadeInUp with stagger
   --------------------------------------------------------------------------- */

export default function StoryCard({ story, index, onStoryClick }: StoryCardProps) {
  return (
    <article
      role="button"
      tabIndex={0}
      aria-label={`Read deep dive: ${story.title}`}
      style={{
        padding: "var(--space-5) 0",
        borderBottom: "var(--rule-thin)",
        animation: `fadeInUp var(--dur-normal) var(--ease-out) both`,
        animationDelay: `${index * 40}ms`,
        cursor: "pointer",
        transition: "background-color var(--dur-fast) var(--ease-out)",
      }}
      onClick={() => onStoryClick?.(story)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onStoryClick?.(story);
        }
      }}
      onMouseEnter={(e) => {
        (e.currentTarget as HTMLElement).style.backgroundColor =
          "var(--bg-secondary)";
      }}
      onMouseLeave={(e) => {
        (e.currentTarget as HTMLElement).style.backgroundColor = "transparent";
      }}
    >
      {/* Category tag + time */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--space-3)",
          marginBottom: "var(--space-2)",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-structural)",
            fontSize: "var(--text-xs)",
            fontWeight: 500,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
            color: "var(--fg-tertiary)",
          }}
        >
          {story.category}
        </span>
        <span
          style={{
            fontFamily: "var(--font-data)",
            fontSize: "var(--text-xs)",
            color: "var(--fg-muted)",
            fontFeatureSettings: '"tnum" 1',
          }}
        >
          {timeAgo(story.publishedAt)}
        </span>
      </div>

      {/* Headline */}
      <h3
        style={{
          fontFamily: "var(--font-editorial)",
          fontSize: "var(--text-xl)",
          fontWeight: 700,
          lineHeight: 1.15,
          letterSpacing: "-0.005em",
          color: "var(--fg-primary)",
          marginBottom: "var(--space-2)",
          display: "flex",
          alignItems: "flex-start",
          gap: "var(--space-1)",
        }}
      >
        <span style={{ flex: 1 }}>{story.title}</span>
        <ArrowSquareOut
          size={14}
          weight="light"
          aria-hidden="true"
          style={{ flexShrink: 0, marginTop: "0.15em", color: "var(--fg-muted)" }}
        />
      </h3>

      {/* Summary */}
      <p
        style={{
          fontFamily: "var(--font-structural)",
          fontSize: "var(--text-base)",
          lineHeight: 1.6,
          color: "var(--fg-secondary)",
          maxWidth: "65ch",
          marginBottom: "var(--space-3)",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}
      >
        {story.summary}
      </p>

      {/* Source count + dot matrix */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--space-4)",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-data)",
            fontSize: "var(--text-sm)",
            color: "var(--fg-tertiary)",
            fontFeatureSettings: '"tnum" 1',
            display: "flex",
            alignItems: "center",
            gap: "var(--space-1)",
          }}
        >
          <Stack size={14} weight="light" aria-hidden="true" />
          {story.source.count} sources
        </span>
        <BiasStamp scores={story.biasScores} />
      </div>
    </article>
  );
}
