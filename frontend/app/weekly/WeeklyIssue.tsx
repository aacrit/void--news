"use client";

/* ---------------------------------------------------------------------------
   void --weekly — one issue, composed.

   THE RUNNING ORDER. A magazine has a spine, and this one comes out of the
   generator's own editorial logic rather than being imposed on it: opinions 1
   and 2 argue about cover feature 1, so the argument belongs directly after
   the reporting it argues with.

       Cover              full screen, nameplate + art + coverlines
       Contents           the issue at a glance
       Feature 1          the lead essay
       The Argument       left vs right, facing columns, the same story
       Feature 2          the second essay
       Other Lenses       the remaining opinions
       Technology         written every week, stored by nothing until now
       Sports & Culture   likewise
       The Editorial      Void's own argued column
       The Week in Bias   generated every week, rendered nowhere until now
       Week in Brief      ten short items, in columns
       Back Issues        real, linkable past issues

   PROPS, NOT FETCH. This used to fetch weekly.json in a useEffect, so the
   served HTML was an empty shell with no content and no per-issue metadata —
   all eight issues shared one OG card. The page above is a server component
   that reads the issue at build; ~70 lines of loading state, error state and
   `digest &&` guards are gone with the fetch, including a nine-line apology
   for nothing contentful painting at first paint.
   --------------------------------------------------------------------------- */

import { useEffect } from "react";
import Link from "next/link";
import type { WeeklyDigestData, WeeklyIssueSummary, WeeklyOpinion } from "./types";
import { AUDIO_ENABLED } from "../lib/audioGate";
import { useAudio, type EpisodeMeta } from "../components/AudioProvider";
import Footer from "../components/Footer";
import ThemeToggle from "../components/ThemeToggle";
import SigilWordmark from "../components/SigilWordmark";
import { formatWeekRange, weeklyDisplayNo, clip, essayParagraphs } from "./format";
import { InkRule, RevealFlourish } from "./components/furniture";
import CinematicCover from "./components/CinematicCover";
import Contents, { type ContentsEntry } from "./components/Contents";
import CoverOpening from "./components/CoverOpening";
import Feature from "./components/Feature";
import { TheArgument, MoreLenses } from "./components/Perspectives";
import DepartmentEssay from "./components/DepartmentEssay";
import Editorial from "./components/Editorial";
import BiasReport from "./components/BiasReport";
import BriefList from "./components/BriefList";
import BackIssues from "./components/BackIssues";

/** Every opinion, whichever vintage of the data this issue was written with. */
function allOpinions(issue: WeeklyDigestData): WeeklyOpinion[] {
  if (issue.opinions && issue.opinions.length > 0) return issue.opinions;
  // Snapshots published before the flat array existed. The three lean buckets
  // are a lossy partition of it — centre-left, centre and centre-right all land
  // in `opinion_center` — but they still hold every essay.
  return [
    ...(issue.opinion_left || []),
    ...(issue.opinion_center || []),
    ...(issue.opinion_right || []),
  ];
}

export default function WeeklyIssue({
  issue,
  archive,
}: {
  issue: WeeklyDigestData;
  archive: WeeklyIssueSummary[];
}) {
  const { playWeekly } = useAudio();

  /* Hand this issue to the shared On Air player, recoloured to the weekly
     accent. Previous issues with audio become the playlist — which was empty
     for as long as fetchWeeklyArchive returned only the current issue. */
  useEffect(() => {
    if (!AUDIO_ENABLED || !issue.audio_url) return;
    const episodes: EpisodeMeta[] = archive
      .filter((i) => !!i.audio_url && i.week_start !== issue.week_start)
      .map((i) => ({
        id: i.id,
        edition: i.edition,
        tldr_headline: i.cover_headline ?? "",
        tldr_text: "",
        opinion_headline: null,
        opinion_text: null,
        opinion_lean: null,
        audio_url: i.audio_url ?? null,
        audio_duration_seconds: i.audio_duration_seconds ?? null,
        opinion_start_seconds: null,
        audio_voice_label: null,
        audio_voice: null,
        // A weekly issue is one continuous read: no chapter rail.
        audio_chapters: null,
        news_start_seconds: null,
        created_at: i.created_at ?? "",
      }));
    playWeekly(issue, episodes);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [issue.id, archive]);

  const weekRange = formatWeekRange(issue.week_start, issue.week_end);
  const covers = (issue.cover_text || []).filter((c) => c?.text);
  const lead = covers[0];
  const second = covers[1];
  const departments = issue.departments || [];
  const opinions = allOpinions(issue);
  const hasArgument = opinions.some((o) => o.paired) || opinions.length >= 2;
  const issueNo = weeklyDisplayNo(issue.issue_number);

  const coverHeadline = issue.cover_headline || lead?.headline || "";
  /* The deck: the lede's first sentence, set in italic serif under the
     headline. A magazine's deck is drawn from the piece, not written twice. */
  const leadParas = essayParagraphs(lead?.text || "");
  const deck = leadParas[0] ? clip(leadParas[0], 190) : undefined;

  /* Coverlines teaser the OTHER pieces in the issue, never the lead. */
  const coverlines: string[] = [];
  {
    const seen = new Set([coverHeadline.trim().toLowerCase()]);
    const candidates = [
      second?.headline,
      ...departments.map((d) => d.headline),
      ...(issue.recap_stories || []).map((s) => s.headline),
    ];
    for (const c of candidates) {
      const t = (c ?? "").trim();
      if (!t || seen.has(t.toLowerCase())) continue;
      seen.add(t.toLowerCase());
      coverlines.push(t);
      if (coverlines.length >= 3) break;
    }
  }

  /* The running order, numbered once, so the contents, the plates and the
     folios can never disagree about where a department sits. */
  let folio = 0;
  const page = () => ++folio;
  const leadPage = page();
  const argumentPage = hasArgument ? page() : 0;
  const secondPage = second ? page() : 0;
  const lensesPage = opinions.length > (hasArgument ? 2 : 0) ? page() : 0;
  const deptPages = departments.map(() => page());
  const editorialPage = issue.opinion_text ? page() : 0;
  const biasPage = issue.bias_report_data?.stats ? page() : 0;
  const briefPage = (issue.recap_stories || []).length > 0 ? page() : 0;
  const archivePage = archive.length > 1 ? page() : 0;

  const contents: ContentsEntry[] = [];
  if (lead) contents.push({ label: "The Cover", title: coverHeadline, href: "#wk-feature-1", page: leadPage });
  if (argumentPage) contents.push({ label: "The Argument", title: "Two columnists, one story", href: "#wk-argument", page: argumentPage });
  if (second) contents.push({ label: "Second Feature", title: second.headline || "", href: "#wk-feature-2", page: secondPage });
  if (lensesPage) contents.push({ label: "Other Lenses", title: "The week from three more angles", href: "#wk-perspectives", page: lensesPage });
  departments.forEach((d, i) => contents.push({ label: d.label, title: d.headline || "", href: `#wk-dept-${d.slug}`, page: deptPages[i] }));
  if (editorialPage) contents.push({ label: "The Editorial", title: issue.opinion_headline || "", href: "#wk-editorial", page: editorialPage });
  if (biasPage) contents.push({ label: "The Week in Bias", title: "The week's coverage, measured", href: "#wk-bias", page: biasPage });
  if (briefPage) contents.push({ label: "Week in Brief", title: `${issue.recap_stories.length} stories in short`, href: "#wk-brief", page: briefPage });

  return (
    <div className="wk-page">
      <CinematicCover
        nameplate={<SigilWordmark product="WEEKLY" height={44} accent="var(--palette-weekly)" />}
        issueLine={`Issue #${issueNo} · ${weekRange}`}
        headline={coverHeadline}
        coverlines={coverlines}
        imageUrl={issue.cover_image_url}
        imageCaption={lead?.image_caption}
        imageAttribution={issue.cover_image_attribution}
      />

      <div id="wk-page-1" className="wk-page-anchor" aria-hidden="true" />

      {/* Compact sticky three-zone topbar, matching void --history:
          back-to-parent mark, centred product logo, theme toggle. */}
      <div className="wk-topbar">
        <div className="wk-topbar__left">
          <Link href="/" className="wk-back" aria-label="Back to Void News">
            <span className="wk-back__arrow" aria-hidden="true">&larr;</span>
            <span className="wk-back__word">
              <SigilWordmark product="NEWS" height={14} />
            </span>
          </Link>
        </div>
        <Link href="/weekly" className="wk-topbar__brand" aria-label="Void Weekly home">
          <span className="wk-topbar__brand-lg">
            <SigilWordmark product="WEEKLY" height={26} accent="var(--palette-weekly)" />
          </span>
          <span className="wk-topbar__brand-sm">
            <SigilWordmark product="WEEKLY" height={21} accent="var(--palette-weekly)" />
          </span>
        </Link>
        <div className="wk-topbar__actions">
          <ThemeToggle />
        </div>
      </div>

      <main id="main-content" className="wk-main">
        <Contents entries={contents} issueNumber={issue.issue_number} />

        {lead && (
          <>
            <CoverOpening
              kicker="The Cover"
              headline={coverHeadline}
              deck={deck}
              dateline={weekRange}
              sources={lead.timeline?.reduce((n, e) => n + (e.source_count || 0), 0) || null}
            />
            <Feature story={lead} id="wk-feature-1" lead />
          </>
        )}

        {argumentPage > 0 && (
          <>
            <RevealFlourish />
            <TheArgument
              opinions={opinions}
              issueNumber={issue.issue_number}
              page={argumentPage}
            />
          </>
        )}

        {second && (
          <>
            <RevealFlourish />
            <div className="wk-second-feature">
              <CoverOpening
                kicker="Second Feature"
                headline={second.headline || ""}
                deck={
                  essayParagraphs(second.text || "")[0]
                    ? clip(essayParagraphs(second.text || "")[0], 190)
                    : undefined
                }
                dateline={weekRange}
                sources={second.timeline?.reduce((n, e) => n + (e.source_count || 0), 0) || null}
              />
              <Feature story={second} id="wk-feature-2" />
            </div>
          </>
        )}

        {lensesPage > 0 && (
          <>
            <RevealFlourish />
            <MoreLenses
              opinions={opinions}
              issueNumber={issue.issue_number}
              page={lensesPage}
            />
          </>
        )}

        {departments.map((d, i) => (
          <div key={d.slug}>
            <RevealFlourish />
            <DepartmentEssay
              department={d}
              issueNumber={issue.issue_number}
              page={deptPages[i]}
            />
          </div>
        ))}

        {editorialPage > 0 && issue.opinion_text && (
          <>
            <RevealFlourish />
            <Editorial
              headline={issue.opinion_headline}
              text={issue.opinion_text}
              lean={issue.opinion_lean}
              issueNumber={issue.issue_number}
              page={editorialPage}
            />
          </>
        )}

        {biasPage > 0 && (
          <>
            <RevealFlourish />
            <BiasReport
              data={issue.bias_report_data}
              totalClusters={issue.total_clusters}
              issueNumber={issue.issue_number}
              page={biasPage}
            />
          </>
        )}

        {briefPage > 0 && (
          <>
            <RevealFlourish />
            <BriefList
              stories={issue.recap_stories}
              issueNumber={issue.issue_number}
              page={briefPage}
            />
          </>
        )}

        {archivePage > 0 && (
          <>
            <InkRule />
            <BackIssues
              entries={archive}
              currentWeek={issue.week_start}
              issueNumber={issue.issue_number}
              page={archivePage}
            />
          </>
        )}
      </main>

      <Footer />
    </div>
  );
}
