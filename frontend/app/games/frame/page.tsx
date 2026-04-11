import type { Metadata } from "next";
import FrameGame from "./FrameGame";

export const metadata: Metadata = {
  title: "THE FRAME \u2014 Daily Media Literacy Puzzle | void --games",
  description:
    "Four outlets. One story. Order them left to right on the political spectrum. A daily challenge from void --news.",
};

export default function FramePage() {
  return <FrameGame />;
}
