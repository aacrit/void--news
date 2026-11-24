"use client";

/* ===========================================================================
   Deep Dive history: an open story has an address.

   Opening a story on the front page pushes the story's own permalink
   (/story/<id>/, the prerendered static page) as a shallow history entry and
   sets the title that page serves. So the address bar, a reload, a copied URL
   and the Back button all behave as they would on the story's page, while the
   feed stays mounted underneath (Next's app router patches pushState and keeps
   the current tree; measured 2026-09-26: no refetch, no remount).

   Walking to the previous or next story REPLACES the entry, so one Back always
   returns to the feed. The entry carries `voidStory: <id>` so a popstate can
   tell ours from anyone else's.

   Before this, the desktop Deep Dive changed neither URL nor title, Back left
   the site, and the mobile one pushed an entry with no URL at all.
   =========================================================================== */

import type { Story } from "./types";
import { BASE_PATH } from "./utils";

let feedTitle: string | null = null;

/** The address a story's Deep Dive wears: its permalink, or the ?story=
 *  deep link the front page already understands when it has none. */
export function deepDiveUrl(story: Story): string {
  if (story.permalink) return `${BASE_PATH}${story.permalink}`;
  return `${BASE_PATH}/?story=${encodeURIComponent(story.id)}`;
}

/** The title the story's own page serves (story/[id]/page.tsx). */
export function deepDiveTitle(story: Story): string {
  return `${story.title} | Void News`;
}

function feedUrl(): string {
  return `${BASE_PATH}/`;
}

/** The story id our entry carries, or null when the current entry is not ours. */
export function currentDeepDiveId(): string | null {
  if (typeof window === "undefined") return null;
  const st = window.history.state as { voidStory?: unknown } | null;
  return typeof st?.voidStory === "string" ? st.voidStory : null;
}

function keepNextState(extra: Record<string, unknown>): Record<string, unknown> {
  /* Next stores its router tree on the entry; carry it so its own popstate
     handling sees a state it recognises. */
  const st = (window.history.state ?? {}) as Record<string, unknown>;
  return { ...st, ...extra };
}

/** Open: push the story's address. */
export function pushDeepDive(story: Story): void {
  if (typeof window === "undefined") return;
  if (currentDeepDiveId() === null) feedTitle = document.title;
  window.history.pushState(keepNextState({ voidStory: story.id }), "", deepDiveUrl(story));
  document.title = deepDiveTitle(story);
}

/** Previous / next: swap the address without adding an entry. */
export function replaceDeepDive(story: Story): void {
  if (typeof window === "undefined") return;
  if (currentDeepDiveId() === null) {
    pushDeepDive(story);
    return;
  }
  window.history.replaceState(keepNextState({ voidStory: story.id }), "", deepDiveUrl(story));
  document.title = deepDiveTitle(story);
}

/** Close from a control (Close, Back to feed, Esc). When the entry is ours the
 *  browser goes back, which fires popstate and the listener closes the story;
 *  otherwise the address is set back to the feed in place. Returns true when a
 *  popstate will follow. */
export function closeDeepDive(): boolean {
  if (typeof window === "undefined") return false;
  if (currentDeepDiveId() !== null) {
    window.history.back();
    return true;
  }
  restoreFeedAddress();
  return false;
}

/** Put the feed's address and title back without touching history depth. */
export function restoreFeedAddress(): void {
  if (typeof window === "undefined") return;
  const path = window.location.pathname;
  if (path !== feedUrl() && path.includes("/story/")) {
    const st = { ...((window.history.state ?? {}) as Record<string, unknown>) };
    delete st.voidStory;
    window.history.replaceState(st, "", feedUrl());
  }
  restoreFeedTitle();
}

export function restoreFeedTitle(): void {
  if (typeof document === "undefined") return;
  if (feedTitle !== null) document.title = feedTitle;
}
