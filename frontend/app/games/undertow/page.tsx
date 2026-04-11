import type { Metadata } from "next";
import UndertowGame from "./UndertowGame";

export const metadata: Metadata = {
  title: "void --undertow \u2014 every text has a tide",
  description:
    "Four cultural artifacts. One axis. Order them from pole to pole. A daily cultural subtext puzzle from void --news.",
};

export default function UndertowPage() {
  return <UndertowGame />;
}
