"use client";

import { useEffect, useState } from "react";

/**
 * The reader's UTC day ("YYYY-MM-DD"), or null before mount.
 *
 * Null on the server and on the first client render, so anything derived
 * from it renders identically in the static HTML and at hydration; the real
 * day arrives in an effect. Used where a label may say "Today" only when it
 * is true (chapters.ts `chapterTitle`).
 */
export function useTodayUTC(): string | null {
  const [today, setToday] = useState<string | null>(null);
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setToday(new Date().toISOString().slice(0, 10));
  }, []);
  return today;
}
