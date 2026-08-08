import type { Metadata } from "next";
import GamesHub from "./GamesHub";

export const metadata: Metadata = {
  title: "Games | every text has a tide",
  description:
    "Media literacy puzzles from Void News. Cultural subtext, political framing, language patterns.",
};

export default function GamesPage() {
  return <GamesHub />;
}
