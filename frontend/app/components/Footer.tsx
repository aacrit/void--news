"use client";

import { GithubLogo } from "@phosphor-icons/react";

/* ---------------------------------------------------------------------------
   Footer — Newspaper-style footer
   "void --news" masthead, tagline, source count, GitHub link.
   Thin top rule, generous padding.
   --------------------------------------------------------------------------- */

export default function Footer() {
  return (
    <footer
      style={{
        borderTop: "1px solid var(--divider)",
        marginTop: "var(--space-6)",
        padding: "var(--space-6) var(--space-7)",
      }}
    >
      <div
        style={{
          maxWidth: 1280,
          margin: "0 auto",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "var(--space-3)",
          textAlign: "center",
        }}
      >
        {/* Masthead */}
        <div
          style={{
            fontFamily: "var(--font-editorial)",
            fontSize: "var(--text-lg)",
            fontWeight: 700,
            letterSpacing: "-0.01em",
            color: "var(--fg-primary)",
            lineHeight: 1,
            display: "flex",
            alignItems: "center",
            gap: "var(--space-2)",
          }}
        >
          void{" "}
          <span
            style={{
              fontFamily: "var(--font-data)",
              fontWeight: 400,
              fontSize: "0.85em",
            }}
          >
            --news
          </span>
        </div>

        {/* Tagline */}
        <p
          style={{
            fontFamily: "var(--font-structural)",
            fontSize: "var(--text-sm)",
            color: "var(--fg-secondary)",
            lineHeight: 1.5,
          }}
        >
          Free, transparent news bias analysis
        </p>

        {/* Source count + update frequency */}
        <p
          style={{
            fontFamily: "var(--font-data)",
            fontSize: "var(--text-xs)",
            color: "var(--fg-tertiary)",
            fontFeatureSettings: '"tnum" 1',
            fontVariantNumeric: "tabular-nums",
          }}
        >
          90 curated sources &middot; Updated twice daily
        </p>

        {/* GitHub link */}
        <a
          href="https://github.com/aacrit/void-news"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="View source on GitHub"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "var(--space-2)",
            fontFamily: "var(--font-structural)",
            fontSize: "var(--text-xs)",
            color: "var(--fg-tertiary)",
            padding: "var(--space-2) var(--space-3)",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-subtle)",
            transition:
              "color var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out)",
            minHeight: 36,
            textDecoration: "none",
          }}
        >
          <GithubLogo size={16} weight="light" aria-hidden="true" />
          Source
        </a>

        {/* Built with transparency */}
        <p
          style={{
            fontFamily: "var(--font-structural)",
            fontSize: "var(--text-xs)",
            color: "var(--fg-muted)",
            marginTop: "var(--space-2)",
          }}
        >
          Built with transparency in mind
        </p>
      </div>
    </footer>
  );
}
