import type { Metadata } from "next";
import AboutExperience from "../components/about/AboutExperience";
import { pageMetadata } from "../lib/siteMeta";

/* /about — the unified interactive experience (page presentation).
   The same component powers the first-visit onboarding overlay.

   This route wrapper is a Server Component (no "use client") so it can export
   per-route metadata; AboutExperience remains a client component and keeps all
   its interactivity. */
export const metadata: Metadata = pageMetadata({
  title: "About | Void News",
  description:
    "Why Void News exists, how the six-axis bias engine reads every article, and what makes a newsroom with no paywall and no feed tuned to you.",
  path: "/about/",
});

export default function AboutPage() {
  return <AboutExperience presentation="page" />;
}
