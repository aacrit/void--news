"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import LeanLabelLegend from "./LeanLabelLegend";
import { ROSTER_SOURCES_TEXT } from "../lib/rosterConfig";

/* ---------------------------------------------------------------------------
   FirstVisitNote: one sentence under the dateline, on a first visit.

   A first-time reader was never told what Void is or how to read a card: at
   375 the first screen was the wordmark, the edition time, the Brief and the
   top story, "bias" first appeared 8,581 characters in, and the legend sat
   behind a 14px icon (audit 2 F6). This says it once, in the house voice,
   with the legend and /about one press away.

   Not personalization: every reader is shown the same sentence over the same
   twenty stories. It remembers only that THIS browser has seen it, under the
   void-news-* key pattern, and every read and write is guarded, so a browser
   that blocks storage simply sees the note.

   Zero layout shift either way. The note is prerendered into the page, and
   the inline bootstrap in app/layout.tsx sets html[data-fv-seen] before
   first paint for a returning reader, which hides it in CSS (no flash, no
   reflow). For a first visit it is in the page from the first byte.

   It stays for the first twelve hours, so a reader who reloads to look again
   still has it, and goes for good when dismissed.
   --------------------------------------------------------------------------- */

export const FIRST_VISIT_KEY = "void-news-first-visit";
/** How long after the first sighting the note keeps showing undismissed. The
 *  same constant is inlined in the app/layout.tsx bootstrap. */
export const FIRST_VISIT_WINDOW_MS = 12 * 60 * 60 * 1000;

function seenBefore(): boolean {
  try {
    const v = localStorage.getItem(FIRST_VISIT_KEY);
    if (!v) {
      localStorage.setItem(FIRST_VISIT_KEY, String(Date.now()));
      return false;
    }
    if (v === "dismissed") return true;
    const t = Number(v);
    return !Number.isFinite(t) || Date.now() - t > FIRST_VISIT_WINDOW_MS;
  } catch {
    return false;
  }
}

export default function FirstVisitNote() {
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (seenBefore()) setHidden(true);
  }, []);

  if (hidden) return null;

  const dismiss = () => {
    try { localStorage.setItem(FIRST_VISIT_KEY, "dismissed"); } catch { /* storage blocked */ }
    try { document.documentElement.setAttribute("data-fv-seen", ""); } catch { /* no DOM */ }
    setHidden(true);
  };

  return (
    <aside className="fv-note" aria-label="About Void News">
      <p className="fv-note__text">
        {`Void News sets ${ROSTER_SOURCES_TEXT} outlets side by side; the seven strokes under each headline count a story’s articles at each point from far left to far right.`}
      </p>
      <p className="fv-note__links">
        <span className="fv-note__legend">
          <LeanLabelLegend trigger="How to read a card" />
        </span>
        <Link href="/about" className="fv-note__link">About Void News</Link>
        <button type="button" className="fv-note__close" onClick={dismiss}>
          Dismiss
        </button>
      </p>
    </aside>
  );
}
