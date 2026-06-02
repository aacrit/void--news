"use client";

import type { PrimarySource } from "../types";

/* ===========================================================================
   PrimarySourceBlock — Typewritten primary source citation
   IBM Plex Mono 300, laid paper texture background, archival document edge.
   =========================================================================== */

interface PrimarySourceBlockProps {
  source: PrimarySource;
}

export default function PrimarySourceBlock({ source }: PrimarySourceBlockProps) {
  return (
    <blockquote className="hist-source-block" cite={source.work}>
      <p className="hist-source-block__text">&ldquo;{source.text}&rdquo;</p>
      <footer className="hist-source-block__citation">
        <span className="hist-source-block__citation-author">{source.author}</span>
        {" \u2014 "}
        <cite>{source.work}</cite>
        {source.date && ` (${source.date})`}
      </footer>
    </blockquote>
  );
}
