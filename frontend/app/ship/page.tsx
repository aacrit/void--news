import type { Metadata } from "next";
import ShipBoard from "../components/ShipBoard";

export const metadata: Metadata = {
  title: "void --ship | Request, Vote, Watch It Deploy",
  description:
    "Submit bugs and feature requests. Vote on what matters. Watch it ship in hours.",
};

export default function ShipPage() {
  return <ShipBoard />;
}
