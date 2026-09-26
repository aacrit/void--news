import Link from "next/link";
import type { Metadata } from "next";
import LogoFull from "./components/LogoFull";
import "./styles/prose-page.css";

/* The 404. Until 2026-09-21 a mistyped URL got the framework default: white
   page, Helvetica, "This page could not be found." Every other route on the
   site carries the wordmark, so this one does too, and then gets out of the
   way. One line (the page's h1, so it has one like every other page), one
   link, and the three sections a reader who typed a URL was most likely
   looking for. No apology. */
export const metadata: Metadata = {
  title: "Not found | Void News",
  robots: { index: false, follow: false },
};

export default function NotFound() {
  return (
    <main className="notfound" id="main-content">
      <Link href="/" className="notfound__mark" aria-label="Void News, back to the front page">
        <LogoFull height={34} />
      </Link>
      <h1 className="notfound__line">Nothing here. The front page is one tap away.</h1>
      <Link href="/" className="notfound__link">
        Go to today&rsquo;s front page
      </Link>
      <nav className="notfound__sections" aria-label="Sections">
        <Link href="/history">History</Link>
        <Link href="/weekly">Weekly</Link>
        <Link href="/onair">On Air</Link>
      </nav>
    </main>
  );
}
