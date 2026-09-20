"use client";

import { useAudio } from "../../components/AudioProvider";
import type { AudioChapter } from "../../lib/types";

/* ===========================================================================
   HeroListen — the hero's Listen button.

   One of the Hearing's three client islands, and the only reason the hero is
   not pure server markup: playHistory() loads this event into the shared
   void --onair player, which lives in React state above the route. Everything
   else in the hero (image, date, title, subtitle, attribution) is rendered on
   the server.

   An event with no episode renders the pending line instead, on the server,
   so this component never mounts for it.
   =========================================================================== */

/* Floor-based clock so a float duration reads "4:30", not "4:30.3000001". */
function formatClock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

interface HeroListenProps {
  id: string;
  title: string;
  subtitle: string;
  audioUrl: string;
  durationSeconds: number;
  chapters: AudioChapter[] | null;
  accountCount: number;
}

export default function HeroListen({
  id,
  title,
  subtitle,
  audioUrl,
  durationSeconds,
  chapters,
  accountCount,
}: HeroListenProps) {
  const { playHistory } = useAudio();
  return (
    <button
      type="button"
      className="hist-hero-listen"
      onClick={() =>
        playHistory({ id, title, subtitle, audioUrl, durationSeconds, chapters })
      }
      aria-label={`Listen to ${title}, ${accountCount} accounts`}
    >
      <svg
        width="12"
        height="14"
        viewBox="0 0 12 14"
        fill="currentColor"
        aria-hidden="true"
        className="hist-hero-listen__icon"
      >
        <path d="M1 1.5v11l10-5.5z" />
      </svg>
      <span className="hist-hero-listen__label">Listen</span>
      <span className="hist-hero-listen__meta">
        {accountCount} accounts · {formatClock(durationSeconds)}
      </span>
    </button>
  );
}
