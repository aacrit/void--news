import type { Metadata } from "next";
import UndertowGame from "./UndertowGame";
import { pageMetadata, sectionTitle } from "../../lib/siteMeta";

export const metadata: Metadata = pageMetadata({
  title: sectionTitle("Undertow", "Games"),
  description:
    "Four texts. One axis. Order them from pole to pole, then read why. A daily puzzle from a fixed set that repeats.",
  path: "/games/undertow/",
});

export default function UndertowPage() {
  return <UndertowGame />;
}
