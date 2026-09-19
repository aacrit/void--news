import type { Metadata } from "next";
import CommandCenter from "../components/CommandCenter";

export const metadata: Metadata = {
  title: "Command Center | Void News",
  description: "CEO operational dashboard for Void News pipeline, bias engine, and source monitoring.",
};

export default function CommandCenterPage() {
  return <CommandCenter />;
}
