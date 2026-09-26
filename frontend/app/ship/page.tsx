import type { Metadata } from "next";
import Link from "next/link";
import FeedbackForm from "../components/FeedbackForm";
import { pageMetadata } from "../lib/siteMeta";

export const metadata: Metadata = pageMetadata({
  title: "Feedback | Void News",
  description:
    "Tell us what to build or what is broken. Every note lands with the team. No account required.",
  path: "/ship/",
});

/* Ship board reverted to the simple feedback form for launch (2026-08-05).
   ShipBoard.tsx was never re-rendered after that and was deleted on
   2026-09-21 (brand audit B-03); git history holds it if the transparency
   board comes back. The /ship route + ship_requests linkage are unchanged so
   existing links keep working. */
export default function ShipPage() {
  return (
    <main className="fb-page">
      <div className="fb-back">
        <Link href="/" className="fb-back__link">
          &larr; Back to the feed
        </Link>
      </div>
      <header className="fb-header">
        <p className="fb-kicker">Feedback</p>
        <h1 className="fb-title">Tell us what to build or fix</h1>
        <p className="fb-intro">
          Void News is experimental. If something broke, felt off, or is missing,
          send a note. We read every one.
        </p>
      </header>
      <FeedbackForm />
    </main>
  );
}
