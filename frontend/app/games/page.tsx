import type { Metadata } from "next";
import GamesHub from "./GamesHub";

export const metadata: Metadata = {
  title: "void --games | Read the World Differently",
  description:
    "Media literacy puzzles from void --news. Test your ability to see through the frame.",
};

export default function GamesPage() {
  return <GamesHub />;
}
