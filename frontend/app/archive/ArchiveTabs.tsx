"use client";

import { useCallback, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { HistoricalEvent, RedactedEvent } from "../history/types";
import HistoryLanding from "../history/components/HistoryLanding";
import RevoltLanding from "../revolt/components/RevoltLanding";
/* Both landings normally get their CSS from their own route layouts. On
   /archive there is no such layout, so pull their stylesheets in here alongside
   the tab chrome. */
import "../styles/history.css";
import "../styles/revolt.css";
import "../styles/archive.css";

/* ---------------------------------------------------------------------------
   ArchiveTabs — the client shell for /archive. Two tabs, History and Revolt,
   each mounting the existing landing unchanged. Tab state lives in the ?tab=
   query param (history default). Keyboard: arrows/Home/End move between tabs
   per the WAI-ARIA tablist pattern.
   --------------------------------------------------------------------------- */

type Tab = "history" | "revolt";

const TABS: { key: Tab; label: string; sub: string }[] = [
  { key: "history", label: "History", sub: "void --history" },
  { key: "revolt", label: "Revolt", sub: "void --revolt" },
];

interface ArchiveTabsProps {
  events: HistoricalEvent[];
  redacted: RedactedEvent[];
  loading: boolean;
}

export default function ArchiveTabs({ events, redacted, loading }: ArchiveTabsProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const active: Tab = searchParams.get("tab") === "revolt" ? "revolt" : "history";
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const selectTab = useCallback(
    (tab: Tab) => {
      router.replace(tab === "revolt" ? "/archive?tab=revolt" : "/archive", {
        scroll: false,
      });
    },
    [router]
  );

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent, idx: number) => {
      let next = idx;
      switch (e.key) {
        case "ArrowLeft":
          next = (idx - 1 + TABS.length) % TABS.length;
          break;
        case "ArrowRight":
          next = (idx + 1) % TABS.length;
          break;
        case "Home":
          next = 0;
          break;
        case "End":
          next = TABS.length - 1;
          break;
        default:
          return;
      }
      e.preventDefault();
      tabRefs.current[next]?.focus();
      selectTab(TABS[next].key);
    },
    [selectTab]
  );

  return (
    <div className="arch-shell">
      <div className="arch-topbar">
        <p className="arch-kicker">void --archive</p>
        <div className="arch-tabs" role="tablist" aria-label="Archive sections">
          {TABS.map((t, i) => (
            <button
              key={t.key}
              ref={(el) => {
                tabRefs.current[i] = el;
              }}
              id={`arch-tab-${t.key}`}
              type="button"
              role="tab"
              aria-selected={active === t.key}
              aria-controls={`arch-panel-${t.key}`}
              tabIndex={active === t.key ? 0 : -1}
              className="arch-tab"
              onClick={() => selectTab(t.key)}
              onKeyDown={(e) => onKeyDown(e, i)}
            >
              {t.label}
              <span className="arch-tab__sub">{t.sub}</span>
            </button>
          ))}
        </div>
      </div>

      <div
        id="arch-panel-history"
        role="tabpanel"
        aria-labelledby="arch-tab-history"
        hidden={active !== "history"}
        className="arch-panel"
      >
        {active === "history" &&
          (loading ? (
            <p className="arch-loading">Opening the archive...</p>
          ) : (
            <HistoryLanding events={events} redacted={redacted} />
          ))}
      </div>

      <div
        id="arch-panel-revolt"
        role="tabpanel"
        aria-labelledby="arch-tab-revolt"
        hidden={active !== "revolt"}
        className="arch-panel"
      >
        {active === "revolt" && <RevoltLanding />}
      </div>
    </div>
  );
}
