"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { MagnifyingGlass } from "@phosphor-icons/react";
import ThemeToggle from "./ThemeToggle";
import LogoFull from "./LogoFull";
import ExperimentalBadge from "./ExperimentalBadge";
import { useAudio } from "./AudioProvider";
import { BASE_PATH, getEditionTimestampLocal, getEditionDatelineUTC } from "../lib/utils";

/* ---------------------------------------------------------------------------
   NavBar: the one masthead, mounted once in the root layout.

   Every route wears the same bar. A section (History, Weekly, Paper) does not
   get its own topbar any more; it gets a nameplate beside the wordmark and an
   accent, the way the floating player is skinned per section by swapping one
   variable. The section is read from the pathname on the server and on the
   client alike, so the served HTML already carries the right nameplate and
   the right aria-current, with no flash.

   Row: wordmark [+ nameplate | tagline] | dateline | sections | pages | search | theme

   The search button renders only on the front page. It raises a DOM event
   (SEARCH_EVENT) that HomeContent listens for, so the masthead does not need
   to know about the feed's state.
   --------------------------------------------------------------------------- */

export const SEARCH_EVENT = "void:search";

export type Section =
  | "news"
  | "history"
  | "weekly"
  | "paper"
  | "onair"
  | "listen"
  | "sources"
  | "ship"
  | "about"
  | "press"
  | "privacy"
  | "story"
  | "other";

/** Section for a route path (BASE_PATH already stripped). */
export function sectionForPath(path: string): Section {
  const p = path || "/";
  if (p === "/") return "news";
  const head = p.split("/").filter(Boolean)[0];
  switch (head) {
    case "history": return "history";
    case "weekly": return "weekly";
    case "paper": return "paper";
    case "onair": return "onair";
    case "listen": return "listen";
    case "sources": return "sources";
    case "ship":
    case "feedback": return "ship";
    case "about": return "about";
    case "press": return "press";
    case "privacy": return "privacy";
    case "story": return "story";
    default: return "other";
  }
}

/** Sections that carry a nameplate beside the wordmark. */
const NAMEPLATES: Partial<Record<Section, { href: string; label: string }>> = {
  history: { href: "/history", label: "History" },
  weekly: { href: "/weekly", label: "Weekly" },
  paper: { href: "/paper", label: "Paper" },
};

/** The section links. Order is the reading order of the product: the daily
 *  broadcast, then the two slower sections, then the feeds. */
const SECTION_LINKS: { href: string; label: string; section: Section }[] = [
  { href: "/onair", label: "On Air", section: "onair" },
  { href: "/history", label: "History", section: "history" },
  { href: "/weekly", label: "Weekly", section: "weekly" },
  { href: "/listen", label: "Listen", section: "listen" },
];

const PAGE_LINKS: { href: string; label: string; section: Section; title: string }[] = [
  { href: "/sources", label: "Sources", section: "sources", title: "Every outlet Void News reads" },
  { href: "/ship", label: "Feedback", section: "ship", title: "Tell us what to build or fix" },
  { href: "/about", label: "About", section: "about", title: "About Void News" },
];

/** Sections whose masthead shows the daily edition dateline. The others are
 *  not daily, so a daily date beside their nameplate would be a false signal. */
const DATED_SECTIONS: ReadonlySet<Section> = new Set(["news", "onair", "sources", "story"]);

interface NavBarProps {
  onSearchClick?: () => void;
  /** Edition build time (pipeline completed_at, ISO). Drives the masthead
      "as of" time, rendered in the viewer's local zone after mount. */
  editionBuiltAt?: string | null;
  /** Deterministic, preformatted edition DATE, computed once at build time in
      UTC. Renders byte-identically on server and client. When absent the
      masthead shows no date rather than the viewer's clock: a date the build
      did not supply is not a fact the masthead may claim. */
  editionDateline?: string;
  /** Explicit literal override for the "as of" TIME node. Pass "" to
      suppress the time entirely. */
  editionTimestamp?: string;
}

export default function NavBar({
  onSearchClick,
  editionBuiltAt,
  editionDateline,
  editionTimestamp,
}: NavBarProps) {
  const pathname = usePathname() || "/";
  const route = pathname.replace(BASE_PATH, "") || "/";
  const section = sectionForPath(route);
  const nameplate = NAMEPLATES[section];
  const dated = DATED_SECTIONS.has(section);

  const [mounted, setMounted] = useState(false);
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setMounted(true); }, []);

  // DATE: the build-time UTC string wins. Without it, the masthead shows the
  // date only once the build time is known on the client; it never shows
  // "now". (The old fallback to the viewer's clock put "Sep 21 · as of 2:00
  // AM" above a card dated September 20.)
  const dateline = editionDateline ?? (mounted && editionBuiltAt ? getEditionDatelineUTC(editionBuiltAt) : "");
  const timestamp =
    editionTimestamp !== undefined
      ? editionTimestamp
      : mounted && editionBuiltAt
        ? getEditionTimestampLocal(editionBuiltAt)
        : "";

  /* Scroll-compact masthead: data-scroll-compact past 80px, off at 40px. */
  const [scrollCompact, setScrollCompact] = useState(false);
  useEffect(() => {
    let ticking = false;
    let compact = false;
    const update = () => {
      ticking = false;
      const y = window.scrollY;
      if (!compact && y > 80) { compact = true; setScrollCompact(true); }
      else if (compact && y <= 40) { compact = false; setScrollCompact(false); }
    };
    const onScroll = () => {
      if (!ticking) { ticking = true; window.requestAnimationFrame(update); }
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const openSearch = () => {
    if (onSearchClick) onSearchClick();
    else window.dispatchEvent(new CustomEvent(SEARCH_EVENT));
  };

  /* While the shared player is playing, the wordmark's beam rocks in brass
     (brand.css, "On air"). The attribute is the only thing the bar does with
     audio; the player owns the rest. */
  const { isPlaying } = useAudio();

  return (
    <header
      className="nav-header anim-cold-open-nav"
      data-section={section}
      data-scroll-compact={scrollCompact ? "true" : undefined}
      data-playing={isPlaying ? "true" : undefined}
    >
      <nav className="nav-inner" aria-label="Main navigation">
        <div className="nav-left">
          <Link href="/" aria-label="Void News home" className="nav-logo si-hoverable">
            <LogoFull responsive className="nav-logo-mark" />
          </Link>
          {nameplate ? (
            <Link
              href={nameplate.href}
              className="nav-nameplate"
              aria-current={route === nameplate.href || route === `${nameplate.href}/` ? "page" : undefined}
            >
              {nameplate.label}
            </Link>
          ) : (
            <>
              <ExperimentalBadge />
              <span className="nav-tagline" aria-hidden="true">See through the void.</span>
            </>
          )}
        </div>

        {dated && (
          <span className="nav-dateline-line" aria-hidden="true" suppressHydrationWarning>
            <span className="nav-dateline-line__date">{dateline}</span>
            {timestamp && (
              <>
                <span className="nav-dateline-line__sep">&middot;</span>
                <span className="nav-dateline-line__time"><span className="nav-asof">as of </span>{timestamp}</span>
              </>
            )}
          </span>
        )}

        <div className="nav-right">
          <nav className="nav-sections" aria-label="Sections">
            {SECTION_LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="nav-page"
                data-section={l.section}
                aria-current={section === l.section ? "page" : undefined}
              >
                {l.label}
              </Link>
            ))}
          </nav>
          <nav className="nav-pages" aria-label="Pages">
            {PAGE_LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="nav-page"
                title={l.title}
                aria-current={section === l.section ? "page" : undefined}
              >
                {l.label}
              </Link>
            ))}
          </nav>

          {section === "news" && (
            <button
              type="button"
              className="nav-search-btn"
              onClick={openSearch}
              aria-label="Search stories (Ctrl+K)"
              title="Search (Ctrl+K)"
            >
              <MagnifyingGlass size={18} weight="regular" aria-hidden="true" />
            </button>
          )}

          <ThemeToggle />
        </div>
      </nav>
    </header>
  );
}
