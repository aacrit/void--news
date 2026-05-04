import type { Metadata } from "next";
import GamesHub from "./GamesHub";

export const metadata: Metadata = {
  title: "void --games | every text has a tide",
  description:
    "Media literacy puzzles from void --news. Cultural subtext, political framing, language patterns.",
};

export default function GamesPage() {
  return <GamesHub />;
}
