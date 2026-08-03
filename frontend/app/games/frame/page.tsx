import type { Metadata } from "next";
import FrameGame from "./FrameGame";

export const metadata: Metadata = {
  title: "THE FRAME: Daily Media Literacy Puzzle | Games",
  description:
    "Four outlets. One story. Order them left to right on the political spectrum. A daily challenge from Void News.",
};

export default function FramePage() {
  return <FrameGame />;
}
