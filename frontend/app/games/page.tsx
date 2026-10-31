import type { Metadata } from "next";
import GamesHub from "./GamesHub";
import { pageMetadata, sectionTitle } from "../lib/siteMeta";

export const metadata: Metadata = pageMetadata({
  title: sectionTitle("Games"),
  description:
    "Games from Void News. UNDERTOW, a daily puzzle in reading subtext, and VOID RUN, an endless runner.",
  path: "/games/",
});

export default function GamesPage() {
  return <GamesHub />;
}
