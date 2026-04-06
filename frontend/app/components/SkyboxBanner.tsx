"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { CaretRight } from "@phosphor-icons/react";
import type { DailyBriefState } from "./DailyBrief";
import LogoIcon from "./LogoIcon";
import { hapticLight } from "../lib/haptics";
import { timeAgo } from "../lib/utils";

type ExpandedSection = null | "tldr" | "opinion";

export default function SkyboxBanner({ state }: { state: DailyBriefState }) {
  const { brief } = state;

  const [expandedSection, setExpandedSection] = useState<ExpandedSection>(null);
  const [announcement, setAnnouncement] = useState("");
  const hasExpandedOnce = useRef(false);

  // Focus management refs
  const collapseRef = useRef<HTMLButtonElement>(null);
  const expandTldrRef = useRef<HTMLDivElement>(null);
  const expandOpinionRef = useRef<HTMLDivElement>(null);
  const prevSectionRef = useRef<ExpandedSection>(null);

  useEffect(() => {
    const prev = prevSectionRef.current;
    if (expandedSection && !prev) {
      requestAnimationFrame(() => collapseRef.current?.focus());
    } else if (!expandedSection && prev) {
      requestAnimationFrame(() => {
        if (prev === "tldr") expandTldrRef.current?.focus();
        else expandOpinionRef.current?.focus();
      });
    }
    prevSectionRef.current = expandedSection;
  }, [expandedSection]);

  // IMPORTANT: All hooks must be called before any conditional return.
  // These useCallback hooks were previously below the `if (!brief) return`
  // guard, causing React error #310: "Rendered more hooks than during the
  // previous render" when brief transitioned from null to loaded.
  const toggleSection = useCallback((section: "tldr" | "opinion") => {
    hapticLight();
    setExpandedSection(prev => {
      const next = prev === section ? null : section;
      if (next) {
        hasExpandedOnce.current = true;
        setAnnouncement(`Daily brief expanded, showing ${next === "tldr" ? "news brief" : "editorial opinion"}.`);
      } else {
        setAnnouncement("Daily brief collapsed.");
      }
      return next;
    });
  }, []);

  const collapseAll = useCallback(() => {
    hapticLight();
    setExpandedSection(null);
    setAnnouncement("Daily brief collapsed.");
  }, []);

  if (!brief) return (
    <div className="skb skb--compact anim-cold-open-skybox" role="complementary" aria-label="Daily Brief">
      <div className="skb__compact">
        <div className="skb__compact-header">
          <div className="skb__compact-cols">
            <div className="skb__compact-col">
              <div className="skb__compact-label">
                <LogoIcon size={16} animation="analyzing" />
                <span className="skb__compact-human">News Brief</span>
                <span className="skb__compact-cmd">void --tl;dr</span>
              </div>
              <span className="skb__compact-loading">Loading today&rsquo;s brief&hellip;</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );

  const leanLabel = brief.opinion_lean === "left" ? "Progressive"
    : brief.opinion_lean === "right" ? "Conservative" : "Pragmatic";
  const leanMod = brief.opinion_lean === "left" ? "skb-lean--left"
    : brief.opinion_lean === "right" ? "skb-lean--right" : "skb-lean--center";

  const isCompact = expandedSection === null;

  const rootClass = [
    "skb",
    !hasExpandedOnce.current ? "anim-cold-open-skybox" : "",
    isCompact ? "skb--compact" : "skb--section-open",
    expandedSection ? `skb--show-${expandedSection}` : "",
  ].filter(Boolean).join(" ");

  return (
    <>
      <div aria-live="polite" className="sr-only">{announcement}</div>

      <div className={rootClass} role="complementary" aria-label="Daily Brief">

        {/* ── COMPACT MODE ── */}
        {isCompact && (
          <div className="skb__compact">
              <div className={`skb__compact-cols${!brief.opinion_text ? " skb__compact-cols--single" : ""}`}>
                {/* TL;DR column — entire column is clickable to expand.
                    Uses div[role=button] instead of <button> because <button> cannot
                    contain block-level elements (<h3>, <p>) — browser parser restructures
                    the DOM, causing React hydration mismatch (error #310). */}
                <div
                  ref={expandTldrRef}
                  className="skb__compact-col skb__compact-col--tldr"
                  onClick={() => toggleSection("tldr")}
                  onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggleSection("tldr"); } }}
                  role="button"
                  tabIndex={0}
                  aria-expanded={false}
                  aria-label="Expand news brief"
                >
                  <div className="skb__compact-label">
                    <LogoIcon size={16} animation="idle" className="skb__compact-logo" />
                    <span className="skb__compact-human">News Brief</span>
                    <span className="skb__compact-cmd">void --tl;dr</span>
                    {brief.created_at && <span className="skb__compact-time">{timeAgo(brief.created_at)}</span>}
                  </div>
                  {brief.tldr_headline && <h3 className="skb__compact-hl skb__compact-hl--tldr">{String(brief.tldr_headline)}</h3>}
                  <p className="skb__compact-preview skb__compact-preview--tldr">{String(brief.tldr_text)}</p>
                  <span className="skb__compact-expand" aria-hidden="true"><CaretRight size={14} weight="bold" /></span>
                </div>

                {/* Organic firewall rule between columns */}
                {brief.opinion_text && (
                  <svg className="skb__firewall skb__firewall--vertical" viewBox="0 0 4 600" preserveAspectRatio="none" aria-hidden="true">
                    <path d="M2,0 C0.5,50 3.5,100 2,150 C0.5,200 3,250 2,300 C1,350 3.5,400 2,450 C0.5,500 3,550 2,600" />
                  </svg>
                )}

                {/* Opinion column — entire column is clickable to expand */}
                {brief.opinion_text && (
                  <div
                    ref={expandOpinionRef}
                    className={`skb__compact-col skb__compact-col--opinion ${leanMod}`}
                    onClick={() => toggleSection("opinion")}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggleSection("opinion"); } }}
                    role="button"
                    tabIndex={0}
                    aria-expanded={false}
                    aria-label="Expand editorial opinion"
                  >
                    <div className="skb__compact-label">
                      <LogoIcon size={16} animation="idle" className="skb__compact-logo" />
                      <span className="skb__compact-human">Editorial</span>
                      <span className="skb__compact-cmd">void --opinion</span>
                      {brief.opinion_lean && <span className={`skb__lean-badge ${leanMod}`}>{leanLabel}</span>}
                    </div>
                    {brief.opinion_headline && <h3 className="skb__compact-hl skb__compact-hl--opinion">{String(brief.opinion_headline)}</h3>}
                    <p className="skb__compact-preview skb__compact-preview--opinion">{String(brief.opinion_text)}</p>
                    <span className="skb__compact-expand" aria-hidden="true"><CaretRight size={14} weight="bold" /></span>
                  </div>
                )}
              </div>

          </div>
        )}

        {/* ── EXPANDED MODE — expands in place, no topbar/tabs ── */}
        {!isCompact && (
          <div className="skb__section-content">
            {expandedSection === "tldr" && (
              <div className="skb__section skb__section--tldr">
                <div className="skb__section-label">
                  <LogoIcon size={16} animation="idle" />
                  <span className="skb__section-label-human">News Brief</span>
                  <span className="skb__section-label-cmd">void --tl;dr</span>
                  {brief.created_at && <span className="skb__section-label-time">{timeAgo(brief.created_at)}</span>}
                  <button
                    ref={collapseRef}
                    className="skb__collapse-inline"
                    onClick={collapseAll}
                    type="button"
                    aria-label="Collapse news brief"
                  >
                    <CaretRight size={14} weight="bold" />
                  </button>
                </div>
                {brief.tldr_headline && <h3 className="skb__section-hl skb__section-hl--tldr">{String(brief.tldr_headline)}</h3>}
                <div className="skb__section-body skb__section-body--tldr">
                  {String(brief.tldr_text).split(/\n\n+/).map((para, i) => <p key={i}>{para}</p>)}
                </div>
              </div>
            )}

            {expandedSection === "opinion" && (
              <div className={`skb__section skb__section--opinion ${leanMod}`}>
                <div className="skb__section-label">
                  <LogoIcon size={16} animation="idle" />
                  <span className="skb__section-label-human">Editorial</span>
                  <span className="skb__section-label-cmd">void --opinion</span>
                  {brief.opinion_lean && <span className={`skb__lean-badge ${leanMod}`}>{leanLabel}</span>}
                  <button
                    ref={collapseRef}
                    className="skb__collapse-inline"
                    onClick={collapseAll}
                    type="button"
                    aria-label="Collapse editorial"
                  >
                    <CaretRight size={14} weight="bold" />
                  </button>
                </div>
                {brief.opinion_headline && <h3 className="skb__section-hl skb__section-hl--opinion">{String(brief.opinion_headline)}</h3>}
                <div className="skb__section-body skb__section-body--opinion">
                  {String(brief.opinion_text || "").split(/\n\n+/).map((para, i) => <p key={i}>{para}</p>)}
                </div>
              </div>
            )}

            {/* Previous episodes removed from Skybox — lives in onair pill only */}
          </div>
        )}
      </div>
    </>
  );
}
