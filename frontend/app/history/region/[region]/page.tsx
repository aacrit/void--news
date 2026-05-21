import { REGIONS } from "../../types";
import RegionPageClient from "./RegionPageClient";

/* ===========================================================================
   /history/region/[region] — Region explorer page
   generateStaticParams for all regions. Client component handles data.
   =========================================================================== */

export function generateStaticParams() {
  return REGIONS.filter((r) => r.id !== "global").map((r) => ({ region: r.id }));
}

export default function RegionPage({ params }: { params: Promise<{ region: string }> }) {
  return <RegionPageClient regionPromise={params} />;
}
