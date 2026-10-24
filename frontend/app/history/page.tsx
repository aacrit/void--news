/* ===========================================================================
   /history — the route. Server Component, so it can own its metadata AND,
   since this pass, its content.

   The whole landing was a Client Component, which cannot export metadata at
   all; that is why every History share showed the generic site title and card.
   The interactive tree is unchanged, one level down.

   It then still fetched /data/history.json in an effect, so the served <main>
   was one italic line ("Opening the archive...") and nothing else: no heading,
   no event titles, no links. A crawler saw an empty section and a reader saw a
   blank screen until the round trip landed. The catalogue is read at build
   here, exactly as /history/[slug] and the sitemap already read it, and handed
   down as a prop. The client keeps every piece of its interactivity; it simply
   starts with the archive already in hand.
   =========================================================================== */

import type { Metadata } from "next";
import { getHistoryCatalog, getHistoryRows } from "../lib/historyCatalog";
import { landingMetadata } from "./historyMeta";
import { mapRow } from "./data";
import { REDACTED_EVENTS } from "./mockData";
import type { HistoricalEvent } from "./types";
import HistoryClient from "./HistoryClient";

export function generateMetadata(): Metadata {
  return landingMetadata(getHistoryCatalog().length);
}

export default function HistoryPage() {
  /* Empty when the snapshot is missing (a contributor who has never run the
     pipeline). The client then falls back to its own fetch and, failing that,
     to mock data, which is the behaviour this route has always had. */
  const rows = getHistoryRows();
  const events: HistoricalEvent[] = rows.map((row) => mapRow(row, rows));

  return <HistoryClient events={events} redacted={REDACTED_EVENTS} />;
}
