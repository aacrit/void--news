import type { Metadata } from "next";
import WireGame from "./WireGame";

export const metadata: Metadata = {
  title: "THE WIRE: Daily Word Puzzle | Games",
  description:
    "An intercepted transmission. Four hidden words. One secret connection. Find the words, find the frequency. A daily challenge from Void News.",
};

export default function WirePage() {
  return <WireGame />;
}
