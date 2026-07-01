import type { Metadata } from "next";
import "../styles/onair.css";
import OnAirPage from "../components/OnAirPage";

export const metadata: Metadata = {
  title: "void --onair — The Broadcast",
  description:
    "Today's brief, read aloud in two voices. The day in five minutes, then the argument worth having.",
};

export default function OnAirRoute() {
  return <OnAirPage />;
}
