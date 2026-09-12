import { ERAS } from "../../types";
import EraPageClient from "./EraPageClient";

/* ===========================================================================
   /history/era/[era] — Era browser page
   generateStaticParams for all 6 eras. Client component handles data.
   =========================================================================== */

export function generateStaticParams() {
  return ERAS.map((e) => ({ era: e.id }));
}

export default function EraPage({ params }: { params: Promise<{ era: string }> }) {
  return <EraPageClient eraPromise={params} />;
}
