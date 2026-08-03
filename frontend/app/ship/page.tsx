import type { Metadata } from "next";
import ShipBoard from "../components/ShipBoard";

export const metadata: Metadata = {
  title: "Ship",
  description:
    "Request, vote, watch it ship. Requests move submitted to triaged to building to shipped, and the ones we won't build get an honest status.",
};

export default function ShipPage() {
  return <ShipBoard />;
}
