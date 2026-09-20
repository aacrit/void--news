/* ===========================================================================
   /history — the route. Server Component, so it can own its metadata.

   The whole landing was a Client Component, which cannot export metadata at
   all; that is why every History share showed the generic site title and card.
   The interactive tree is unchanged, one level down.
   =========================================================================== */

import type { Metadata } from "next";
import { getHistoryCatalog } from "../lib/historyCatalog";
import { landingMetadata } from "./historyMeta";
import HistoryClient from "./HistoryClient";

export function generateMetadata(): Metadata {
  return landingMetadata(getHistoryCatalog().length);
}

export default function HistoryPage() {
  return <HistoryClient />;
}
