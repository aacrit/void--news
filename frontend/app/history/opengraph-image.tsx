import { getHistoryCatalog } from "../lib/historyCatalog";
import { landingCard } from "./ogCard";
import { size, contentType } from "./ogCard";

// Required under `output: export`: without it the image is treated as a
// dynamic route handler and the build refuses to collect it.
export const dynamic = "force-static";
export { size, contentType };
export const alt = "Void History: one event, every side";

export default function Image() {
  return landingCard(getHistoryCatalog().length);
}
