import type { Metadata } from "next";
import PaperContent from "./PaperContent";
import { pageMetadata } from "../lib/siteMeta";

export const metadata: Metadata = pageMetadata({
  title: "The Paper | Void News",
  description:
    "Today's edition laid out as a broadsheet. The same stories, the same order, read like a front page.",
  path: "/paper/",
});

/* World edition is the default at /paper */
export default function PaperPage() {
  return <PaperContent edition="world" />;
}
