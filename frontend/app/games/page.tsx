import type { Metadata } from "next";
import GamesHub from "./GamesHub";
import { pageMetadata } from "../lib/siteMeta";

export const metadata: Metadata = pageMetadata({
  title: "Games | Void News",
  description:
    "Media literacy puzzles from Void News. Cultural subtext, political framing, language patterns. Every text has a tide.",
  path: "/games/",
});

export default function GamesPage() {
  return <GamesHub />;
}
