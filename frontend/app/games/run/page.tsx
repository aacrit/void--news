import type { Metadata } from "next";
import VoidRun from "./VoidRun";
import { pageMetadata, sectionTitle } from "../../lib/siteMeta";

export const metadata: Metadata = pageMetadata({
  title: sectionTitle("Void Run", "Games"),
  description:
    "An endless side-scrolling runner. You are the signal. The corridor is language. The obstacles are noise.",
  path: "/games/run/",
});

export default function VoidRunPage() {
  return <VoidRun />;
}
