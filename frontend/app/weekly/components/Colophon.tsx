"use client";

/* ---------------------------------------------------------------------------
   The colophon.

   A magazine prints how it was made, and this one can print something no
   masthead ever could: the actual cost of the issue, measured rather than
   claimed. Every figure here was already stored on the row and rendered
   nowhere. Zero LLM cost to produce, because it is arithmetic over fields the
   generator writes as a by-product of running.

   It is also the honest place for the `truncated` flag. The Week in Bias says
   "more than 3,000 articles" when the scorer hit its page ceiling; the
   colophon says how many the WEEK actually carried, which is a different
   number and a smaller one.
   --------------------------------------------------------------------------- */

import type React from "react";
import type { WeeklyDigestData } from "../types";
import { groupDigits } from "../format";
import { useScrollReveal } from "../hooks";

/** "3m 04s". A duration a reader can hold, not 184.2. */
function duration(seconds?: number | null): string | null {
  if (!seconds || !Number.isFinite(seconds) || seconds <= 0) return null;
  const s = Math.round(seconds);
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}m ${String(s % 60).padStart(2, "0")}s`;
}

/** The engine string, as a reader would say it. */
function voices(audioVoice?: string | null): string | null {
  if (!audioVoice) return null;
  // "kokoro:bm_lewis+am_michael+af_heart" -> three voices.
  const n = audioVoice.split(":").pop()?.split("+").length ?? 0;
  if (n >= 3) return "three voices";
  if (n === 2) return "two voices";
  return n === 1 ? "one voice" : null;
}

export default function Colophon({ issue }: { issue: WeeklyDigestData }) {
  const [ref, visible] = useScrollReveal(0.1);

  const articles = issue.total_articles;
  const clusters = issue.total_clusters;
  const calls = issue.gemini_calls_used;
  const took = duration(issue.generation_duration_seconds);
  const read = voices(issue.audio_voice);

  // Nothing measured means nothing to print. A colophon that says "assembled
  // from null articles" is worse than no colophon.
  if (!articles && !clusters && !calls) return null;

  return (
    <aside
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-colophon wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-label="How this issue was made"
    >
      <span className="wk-colophon__label">How this issue was made</span>
      <p className="wk-colophon__line">
        {!!articles && (
          <>
            Assembled from <strong>{groupDigits(articles)}</strong> articles
            {!!clusters && (
              <> in <strong>{groupDigits(clusters)}</strong> story clusters</>
            )}
            .{" "}
          </>
        )}
        {!!calls && (
          <>
            <strong>{calls}</strong> model {calls === 1 ? "call" : "calls"}
            {took && <>, {took}</>}.{" "}
          </>
        )}
        {read && <>Read aloud in {read}. </>}
        No advertising, no paywall, and no story chosen for you.
      </p>
    </aside>
  );
}
