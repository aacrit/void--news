import type { Metadata } from "next";
import "../styles/onair.css";
import OnAirPage from "../components/OnAirPage";
import { pageMetadata } from "../lib/siteMeta";

export const metadata: Metadata = pageMetadata({
  title: "On Air | Void News",
  description:
    "Today's brief, read aloud in two voices. The day in five minutes, then the argument worth having.",
  path: "/onair/",
});

export default function OnAirRoute() {
  return <OnAirPage />;
}
