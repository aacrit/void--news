import type { Metadata } from "next";
import PipelineFlow from "../components/PipelineFlow";

export const metadata: Metadata = {
  title: "Pipeline Flow — void --news",
  description:
    "Every step of the 3x-daily Python pipeline: ingestion, analysis, clustering, ranking, storage, enrichment, and cleanup.",
};

export default function PipelinePage() {
  return <PipelineFlow />;
}
