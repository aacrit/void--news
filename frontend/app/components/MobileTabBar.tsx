"use client";

import { useCallback, useState, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { hapticMicro } from "../lib/haptics";
import { useAudio } from "./AudioProvider";
import { BASE_PATH } from "../lib/utils";

/* ---------------------------------------------------------------------------
   MobileTabBar — Persistent bottom tab bar (mobile only, <768px).
   4 tabs: Feed, History, OnAir, More.
   "More" toggles MobileSidePanel (callback from parent).
   "OnAir" triggers audio playback via AudioProvider.
   Hidden on desktop via CSS.
   --------------------------------------------------------------------------- */

interface MobileTabBarProps {
  onMoreTap: () => void;
  moreOpen: boolean;
}

/* -- SVG Icons — 20x20, currentColor -- */

function FeedIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="3" width="14" height="14" rx="2" />
      <line x1="3" y1="8" x2="17" y2="8" />
      <line x1="8" y1="8" x2="8" y2="17" />
    </svg>
  );
}

function HistoryIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="2" width="14" height="4" rx="1" />
      <rect x="4" y="8" width="12" height="4" rx="1" />
      <rect x="5" y="14" width="10" height="4" rx="1" />
    </svg>
  );
}

function OnAirIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="8" y="6" width="4" height="8" rx="2" />
      <path d="M5 10a5 5 0 0 0 10 0" />
      <line x1="10" y1="14" x2="10" y2="17" />
      <line x1="7" y1="17" x2="13" y2="17" />
    </svg>
  );
}

function MoreIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <line x1="3" y1="5" x2="17" y2="5" />
      <line x1="3" y1="10" x2="17" y2="10" />
      <line x1="3" y1="15" x2="17" y2="15" />
    </svg>
  );
}

type TabDef = {
  key: string;
  label: string;
  Icon: () => React.JSX.Element;
  href: string | null;
  action?: "onair";
};

const TABS: TabDef[] = [
  { key: "feed", label: "feed", Icon: FeedIcon, href: "/" },
  { key: "history", label: "history", Icon: HistoryIcon, href: "/history" },
  { key: "onair", label: "onair", Icon: OnAirIcon, href: null, action: "onair" },
  { key: "more", label: "more", Icon: MoreIcon, href: null },
];

export default function MobileTabBar({ onMoreTap, moreOpen }: MobileTabBarProps) {
  const pathname = usePathname();
  const audio = useAudio();
  const [onairMsg, setOnairMsg] = useState<string | null>(null);
  const onairMsgTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const isActive = useCallback(
    (key: string): boolean => {
      const p = pathname.replace(BASE_PATH, "") || "/";
      switch (key) {
        case "feed":
          return p === "/" || p === "" || /^\/(world)\/?$/.test(p);
        case "history":
          return p.startsWith("/history");
        case "onair":
          return audio.isPlaying;
        case "more":
          return moreOpen;
        default:
          return false;
      }
    },
    [pathname, moreOpen, audio.isPlaying]
  );

  const showOnairMsg = useCallback((msg: string) => {
    setOnairMsg(msg);
    if (onairMsgTimer.current) clearTimeout(onairMsgTimer.current);
    onairMsgTimer.current = setTimeout(() => setOnairMsg(null), 2000);
  }, []);

  const handleOnAirTap = useCallback(() => {
    hapticMicro();
    if (audio.isPlaying) {
      audio.setPlayerVisible(true);
      audio.setExpanded(true);
      return;
    }
    if (audio.brief?.audio_url) {
      audio.setPlayerVisible(true);
      audio.handlePlayPause();
      return;
    }
    const briefPill = document.querySelector(".mbp, .skybox");
    if (briefPill) {
      briefPill.scrollIntoView({ behavior: "smooth", block: "center" });
      showOnairMsg("brief above ↑");
    } else {
      showOnairMsg("loading soon");
    }
  }, [audio, showOnairMsg]);

  return (
    <nav className="mtb" aria-label="Mobile navigation">
      {TABS.map(({ key, label, Icon, href, action }) => {
        const active = isActive(key);
        if (href) {
          return (
            <Link
              key={key}
              href={href}
              className={`mtb__tab${active ? " mtb__tab--active" : ""}`}
              aria-current={active ? "page" : undefined}
              onClick={() => hapticMicro()}
            >
              <Icon />
              <span className="mtb__label">{label}</span>
            </Link>
          );
        }
        if (action === "onair") {
          return (
            <button
              key={key}
              type="button"
              className={`mtb__tab${active ? " mtb__tab--active" : ""}`}
              aria-label="Play audio brief"
              onClick={handleOnAirTap}
            >
              <span className="mtb__onair-wrap">
                <Icon />
                {onairMsg && (
                  <span className="mtb__onair-msg" role="status" aria-live="polite">
                    {onairMsg}
                  </span>
                )}
              </span>
              <span className="mtb__label">{label}</span>
            </button>
          );
        }
        return (
          <button
            key={key}
            type="button"
            className={`mtb__tab${active ? " mtb__tab--active" : ""}`}
            aria-expanded={moreOpen}
            aria-label="More options"
            onClick={() => {
              hapticMicro();
              onMoreTap();
            }}
          >
            <Icon />
            <span className="mtb__label">{label}</span>
          </button>
        );
      })}
    </nav>
  );
}
