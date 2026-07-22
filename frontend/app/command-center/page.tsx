import type { Metadata } from "next";
import CommandCenter from "../components/CommandCenter";

export const metadata: Metadata = {
  title: "Command Center — void --news",
  description: "CEO operational dashboard for void --news pipeline, bias engine, and source monitoring.",
};

export default function CommandCenterPage() {
  return <CommandCenter />;
}
