import type { Metadata } from "next";
import UndertowGame from "./UndertowGame";

export const metadata: Metadata = {
  title: "UNDERTOW: Daily Cultural Subtext Puzzle | Games",
  description:
    "Four cultural artifacts. One conceptual axis. Order them from pole to pole. Decode the subtext. A daily challenge from Void News.",
};

export default function UndertowPage() {
  return <UndertowGame />;
}
