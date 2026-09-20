/* ---------------------------------------------------------------------------
   void --weekly — the issue's data shape.

   Moved out of lib/types.ts in the 2026-09-20 magazine rebuild, mirroring
   app/history/types.ts. lib/types.ts re-exports these names so AudioProvider
   and DailyBrief keep their existing imports.

   These types now describe what the pipeline ACTUALLY writes. Three of them
   used to describe something else entirely, harmlessly only because nothing
   rendered the fields:

   - `opinion_headlines` was typed `string[]`; the generator writes a map keyed
     by topic. Deleted outright — it is derivable from `opinions`, and nothing
     has ever rendered it.
   - `WeeklyBiasReportData` declared `aggregate` and `{headline, lean_spread,
     avg_lean}`; the generator has ALWAYS written `stats` and `{title,
     divergence}`. No row anywhere carries the old shape, so there is no shim.
   - `contested_stories` had no column in any schema, in Postgres or SQLite, so
     the "Most Contested" section could never render. Deleted, along with its
     component, which had no CSS either.
   --------------------------------------------------------------------------- */

import type { OpinionLean } from "../lib/types";

export interface WeeklyCoverStory {
  headline: string;
  text: string;
  timeline?: WeeklyTimelineDay[];
  numbers?: WeeklyCoverNumber[];
  /* Illustration, from a freely licensed source only (Wikimedia Commons, or
     Unsplash/Pexels when a key is configured). A publisher's og:image is never
     used: it is usually a wire photograph and grants nothing to whoever
     scrapes it. */
  image_url?: string;
  image_attribution?: string;
  image_caption?: string;
  cluster_id?: string;
}

export interface WeeklyTimelineDay {
  date?: string;          // "Fri Sep 18"
  date_iso?: string;      // "2026-09-18"
  title?: string;         // the day's cluster headline
  source_count?: number;
  cluster_id?: string;
  /* Legacy shapes from earlier generator versions. */
  day?: string;
  note?: string;
  event?: string;
  development?: string;
}

export interface WeeklyCoverNumber {
  // Generator emits {stat, context}; older rows used {value, label}.
  stat?: string;
  context?: string;
  value?: string;
  label?: string;
}

export interface WeeklyRecapStory {
  headline: string;
  summary: string;
  /* The cluster's category, carried through as a department kicker. */
  section?: string;
  image_url?: string;
  image_attribution?: string;
  image_caption?: string;
}

export interface WeeklyOpinion {
  headline: string;
  text: string;
  lean: string;
  topic?: string;
  cluster_id?: string;
  /* The dialectic, stated rather than implied. The generator writes essays 1
     and 2 as opposing columns on the SAME cover story, each told in its prompt
     that the other exists. Two entries sharing a `pair_id` are that pair. */
  paired?: boolean;
  pair_id?: string;
  position?: number;
}

/* A front-of-book department essay: Technology, Sports & Culture. Generated
   every week since the section was written, and persisted by nothing until
   2026-09-20. */
export interface WeeklyDepartment {
  slug: string;
  label: string;
  headline: string;
  text: string;
  cluster_id?: string | null;
  image_url?: string | null;
  image_attribution?: string | null;
  image_caption?: string | null;
}

export interface WeeklyBiasReportData {
  most_polarized?: Array<{ title: string; divergence: number }>;
  stats?: {
    total_scored: number;
    avg_lean: number;
    avg_sensationalism: number;
    avg_rigor: number;
    lean_std: number;
    /* True only when the scorer's page ceiling was hit. Issue #26 published
       "3,000 articles scored", which was a query cap, not a count. */
    truncated?: boolean;
  };
}

export interface WeeklyDigestData {
  id: string;
  edition: string;
  week_start: string;
  week_end: string;
  issue_number: number;
  cover_headline: string;
  cover_image_url: string | null;
  cover_image_attribution: string | null;
  cover_image_source: string | null;
  cover_text: WeeklyCoverStory[];
  cover_numbers: WeeklyCoverNumber[] | null;
  recap_stories: WeeklyRecapStory[];
  departments?: WeeklyDepartment[] | null;
  /* The real opinion shape. The three lean buckets below are a lossy partition
     of it, kept only so snapshots published before 2026-09-20 still render;
     the exporter drops them once `opinions` is present. */
  opinions?: WeeklyOpinion[] | null;
  opinion_left?: WeeklyOpinion[] | null;
  opinion_center?: WeeklyOpinion[] | null;
  opinion_right?: WeeklyOpinion[] | null;
  opinion_topic: string | null;
  bias_report_text: string | null;
  bias_report_data: WeeklyBiasReportData | null;
  audio_url: string | null;
  audio_duration_seconds: number | null;
  /* The weekly editorial: one argued week-in-review column. Distinct from the
     three-lens Perspectives above. */
  opinion_text: string | null;
  opinion_headline: string | null;
  opinion_lean: OpinionLean | null;
  opinion_audio_script?: string | null;
  opinion_start_seconds: number | null;
  audio_voice: string | null;
  audio_voice_label: string | null;
  total_articles: number | null;
  total_clusters: number | null;
  created_at: string;
}

/* One row of the back-issue index (public/data/weekly-archive.json). */
export interface WeeklyIssueSummary {
  id: string;
  issue_number: number;
  edition: string;
  week_start: string;
  week_end: string;
  cover_headline: string | null;
  cover_image_url: string | null;
  audio_url: string | null;
  audio_duration_seconds: number | null;
  created_at: string | null;
}
