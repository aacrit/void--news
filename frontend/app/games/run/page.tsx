import type { Metadata } from "next";
import VoidRun from "./VoidRun";

export const metadata: Metadata = {
  title: "VOID RUN \u2014 run until the signal breaks | void --games",
  description:
    "An infinite side-scrolling runner. You are the signal. The corridor is language. The obstacles are noise. Survive as long as possible.",
};

export default function VoidRunPage() {
  return <VoidRun />;
}
