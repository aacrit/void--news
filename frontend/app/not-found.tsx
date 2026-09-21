import Link from "next/link";
import LogoFull from "./components/LogoFull";
import "./styles/prose-page.css";

/* The 404. Until 2026-09-21 a mistyped URL got the framework default: white
   page, Helvetica, "This page could not be found." Every other route on the
   site carries the wordmark, so this one does too, and then gets out of the
   way. One line, one link, no apology. */
export default function NotFound() {
  return (
    <main className="notfound">
      <Link href="/" className="notfound__mark" aria-label="Void News, back to the front page">
        <LogoFull height={34} />
      </Link>
      <p className="notfound__line">Nothing here. The front page is one tap away.</p>
      <Link href="/" className="notfound__link">
        Go to today&rsquo;s front page
      </Link>
    </main>
  );
}
