import type { Metadata } from "next";
import { THREADS } from "../threads";
import { threadsMetadata } from "../historyMeta";
import ThreadsPageClient from "./ThreadsPageClient";

/* ===========================================================================
   /history/threads — Thematic Threads across the archive.

   A thin server page that owns the metadata; the client tree below keeps the
   fetch and the feature gate. The route was "use client" and so exported no
   metadata at all: the served page carried the root layout's title and the
   site-wide card.
   =========================================================================== */

export function generateMetadata(): Metadata {
  return threadsMetadata(THREADS.length);
}

export default function ThreadsPage() {
  return <ThreadsPageClient />;
}
