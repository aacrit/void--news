"use client";

import type { Story } from "../lib/types";
import { timeAgo } from "../lib/mockData";
import DotMatrix from "./DotMatrix";

interface LeadStoryProps {
  story: Story;
}

/* ---------------------------------------------------------------------------
   LeadStory — Hero treatment for the most important story
   Larger typography, more prominent layout, bigger dot matrix.
   Desktop: 2/3 width. Mobile: full-width.
   --------------------------------------------------------------------------- */

export default function LeadStory({ story }: LeadStoryProps) {
  return (
    <article
      style={{
        padding: "var(--space-6) 0",
        borderBottom: "var(--rule-strong)",
        animation: `fadeInUp var(--dur-normal) var(--ease-out) both`,
        cursor: "pointer",
      }}
    >
      {/* Category tag + time */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--space-3)",
          marginBottom: "var(--space-3)",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-structural)",
            fontSize: "var(--text-sm)",
            fontWeight: 600,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
            color: "var(--fg-tertiary)",
          }}
        >
          {story.category}
        </span>
        <span
          style={{
            width: 3,
            height: 3,
            borderRadius: "50%",
            backgroundColor: "var(--fg-muted)",
            flexShrink: 0,
          }}
          aria-hidden="true"
        />
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

      {/* Hero headline */}
      <h2
        style={{
          fontFamily: "var(--font-editorial)",
          fontSize: "var(--text-hero)",
          fontWeight: 700,
          lineHeight: 1.1,
          letterSpacing: "-0.01em",
          color: "var(--fg-primary)",
          marginBottom: "var(--space-3)",
        }}
      >
        {story.title}
      </h2>

      {/* Extended summary — 3-4 lines for lead story */}
      <p
        style={{
          fontFamily: "var(--font-structural)",
          fontSize: "var(--text-base)",
          lineHeight: 1.7,
          color: "var(--fg-secondary)",
          maxWidth: "65ch",
          marginBottom: "var(--space-4)",
        }}
      >
        {story.summary}
      </p>

      {/* Source count + large dot matrix */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "var(--space-5)",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-data)",
            fontSize: "var(--text-base)",
            color: "var(--fg-secondary)",
            fontWeight: 500,
            fontFeatureSettings: '"tnum" 1',
          }}
        >
          {story.source.count} sources
        </span>
        <DotMatrix scores={story.biasScores} size="lg" />
      </div>
    </article>
  );
}
