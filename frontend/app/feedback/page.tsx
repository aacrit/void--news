import type { Metadata } from "next";
import Link from "next/link";
import FeedbackForm from "../components/FeedbackForm";

export const metadata: Metadata = {
  title: "Feedback | void --news",
  description:
    "void --news is experimental. Tell us what breaks, what is missing, or what would make it better. No account needed.",
};

/* ===========================================================================
   /feedback — the retired void --ship, now a single calm form. Submissions
   still write to ship_requests; the CEO reads them in Supabase directly.
   =========================================================================== */

export default function FeedbackPage() {
  return (
    <main id="main-content" className="fb-page">
      <nav className="fb-back">
        <Link href="/" className="fb-back__link">
          &larr; void --news
        </Link>
      </nav>

      <header className="fb-header">
        <p className="fb-kicker">void --feedback</p>
        <h1 className="fb-title">Tell us what breaks.</h1>
        <p className="fb-intro">
          void --news is experimental. Every note lands in front of the person building
          it. Report a bug, ask for a feature, or say what felt off. No account needed.
        </p>
      </header>

      <FeedbackForm />
    </main>
  );
}
