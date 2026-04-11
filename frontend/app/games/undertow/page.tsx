import type { Metadata } from "next";
import UndertowGame from "./UndertowGame";

export const metadata: Metadata = {
  title: "UNDERTOW \u2014 Daily Cultural Subtext Puzzle | void --games",
  description:
    "Four cultural artifacts. One conceptual axis. Order them from pole to pole. Decode the subtext. A daily challenge from void --news.",
};

export default function UndertowPage() {
  return <UndertowGame />;
}
