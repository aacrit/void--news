import type { Metadata } from "next";
import WireGame from "./WireGame";
import { pageMetadata, sectionTitle } from "../../lib/siteMeta";

/* Not on the hub yet ("coming soon"); public/_redirects sends /games/wire to
   /games/ until it launches. */
export const metadata: Metadata = pageMetadata({
  title: sectionTitle("The Wire", "Games"),
  description:
    "An intercepted transmission. Four hidden words. One connection. A puzzle from a fixed set of five that repeats.",
  path: "/games/wire/",
});

export default function WirePage() {
  return <WireGame />;
}
