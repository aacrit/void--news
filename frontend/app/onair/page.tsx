import type { Metadata } from "next";
import "../styles/onair.css";
import OnAirPage from "../components/OnAirPage";

export const metadata: Metadata = {
  title: "On Air | Void News",
  description:
    "Today's brief, read aloud in two voices. The day in five minutes, then the argument worth having.",
};

export default function OnAirRoute() {
  return <OnAirPage />;
}
