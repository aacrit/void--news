import type { Metadata } from "next";
import WireGame from "./WireGame";

export const metadata: Metadata = {
  title: "THE WIRE \u2014 Daily Word Puzzle | void --games",
  description:
    "An intercepted transmission. Four hidden words. One secret connection. Find the words, find the frequency. A daily challenge from void --news.",
};

export default function WirePage() {
  return <WireGame />;
}
