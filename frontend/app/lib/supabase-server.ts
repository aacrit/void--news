import "server-only";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/* ---------------------------------------------------------------------------
   Server-only Supabase client (service role).
   Used by routes that must bypass RLS (the IG renderer, the /admin/ig page,
   and any Server Actions that mutate ig_posts state).

   Read access to ig_posts is blocked for anon (see migration 052), so the
   public client in `./supabase.ts` cannot be used here.

   Env vars:
     SUPABASE_URL              (note: not the NEXT_PUBLIC_ one — server only)
     SUPABASE_SERVICE_ROLE_KEY (NEVER ship to the client; server-only import
                                enforced by `server-only` above)

   This file MUST NOT be imported from any client component or `lib/supabase`.
   --------------------------------------------------------------------------- */

let _server: SupabaseClient | null = null;

function getClient(): SupabaseClient | null {
  if (_server) return _server;

  const url = process.env.SUPABASE_URL ?? process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return null;

  _server = createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  return _server;
}

export type IgPostState =
  | "draft"
  | "rendering"
  | "render_failed"
  | "captioning"
  | "caption_review"
  | "approved"
  | "posting"
  | "posted"
  | "failed"
  | "rejected";

export type IgPillar = "vision" | "method" | "example" | "history" | "weekly";

export interface IgPostRow {
  id: string;
  created_at: string;
  updated_at: string;
  state: IgPostState;
  scheduled_for: string;
  pillar: IgPillar;
  surface: "feed" | "story" | "reel";
  launch_slot: number | null;
  slide_specs: SlideSpec[];
  caption: string | null;
  hashtags: string[] | null;
  image_urls: string[] | null;
  ig_media_id: string | null;
  ig_permalink: string | null;
  posted_at: string | null;
  bluesky_uri: string | null;
  metrics: Record<string, unknown> | null;
  metrics_updated_at: string | null;
  error: string | null;
  retry_count: number;
}

/* ---------------------------------------------------------------------------
   Slide spec shapes — three launch pillars, each a 3-slide carousel.
   Discriminated by `kind`; the `variant` selects the slide within a carousel
   (hook -> substance -> cta). The pipeline generator emits EXACTLY these shapes.

   Track 1 — "Void News Social" (the daily trio):
     VISION  (evergreen manifesto)     hook | stance | cta
     METHOD  (evergreen bias explainer) hook | sample | cta
     EXAMPLE (dynamic real top story)  hook | spectrum | cta
   Track 2 — "Void History Social" (adhoc, umber):
     HISTORY  hook | perspectives | cta
   Track 3 — "Void Weekly Social" (adhoc, red):
     WEEKLY   hook | stories | cta
   --------------------------------------------------------------------------- */
export type SlideSpec =
  | VisionSlideSpec
  | MethodSlideSpec
  | ExampleSlideSpec
  | HistorySlideSpec
  | WeeklySlideSpec;

/** One outlet's take on a shared event — reused by EXAMPLE spectrum + hook. */
export interface OutletHeadline {
  outlet: string;
  /** 0 (far left) .. 50 (center) .. 100 (far right). Drives dot position + colour. */
  lean_score: number;
  headline: string;
}

/* ── VISION ────────────────────────────────────────────────────────────────
   hook:   kicker + headline (the provocation about the algorithmic feed)
   stance: kicker + headline (short) + body (the core principle)
   cta:    headline (the sign-off) + url                                       */
export interface VisionSlideSpec {
  kind: "vision";
  variant: "hook" | "stance" | "cta";
  /** small-caps label. hook + stance. */
  kicker?: string;
  /** hook: the provocation. stance: short lead line. cta: the sign-off line. */
  headline?: string;
  /** stance: the principle paragraph. */
  body?: string;
  /** cta: the site URL, e.g. "void-news.pages.dev". */
  url?: string;
}

/* ── METHOD ────────────────────────────────────────────────────────────────
   hook:   kicker + headline ("Bias isn't the outlet. It's the words.")
   sample: axis_name + sample{text,highlights} + score + lean_label + principle
   cta:    headline + url                                                       */
export interface MethodSlideSpec {
  kind: "method";
  variant: "hook" | "sample" | "cta";
  kicker?: string;
  /** hook + cta headline. */
  headline?: string;
  /** sample: the bias axis being demonstrated, e.g. "Political Lean". */
  axis_name?: string;
  /** sample: the real sentence; highlight ranges become terracotta <mark> spans. */
  sample?: { text: string; highlights?: Array<{ start: number; end: number }> };
  /** sample: 0..100 lean score for the chip; coloured on the --bias-* scale. */
  score?: number;
  /** sample: human label for the score, e.g. "Center-left". */
  lean_label?: string;
  /** sample: one-line principle under the sample. */
  principle?: string;
  /** cta: the site URL. */
  url?: string;
}

/* ── EXAMPLE ───────────────────────────────────────────────────────────────
   hook:     topic + headline (the real event) + outlet_count
   spectrum: topic + headlines[] (each outlet plotted on the lean axis)
   cta:      headline + url                                                     */
export interface ExampleSlideSpec {
  kind: "example";
  variant: "hook" | "spectrum" | "cta";
  /** hook + spectrum kicker: the event topic, e.g. "SUPREME COURT". */
  topic?: string;
  /** hook: the event line. cta: the sign-off line. */
  headline?: string;
  /** hook: number of outlets covering the event (for "N outlets"). */
  outlet_count?: number;
  /** spectrum: the outlets to plot (recommend 4-6 for legibility). */
  headlines?: OutletHeadline[];
  /**
   * spectrum: the FULL per-article political-lean distribution (0..100) for the
   * event, one value per contributing article. When present it drives the KDE
   * ridge exactly as the in-app Deep Dive spectrum does; when absent the ridge
   * falls back to the shown `headlines[].lean_score` values. The generator
   * populates this from the cluster's per-article bias scores.
   */
  lean_values?: number[];
  /** cta: the site URL. */
  url?: string;
}

/* ── HISTORY (adhoc track, umber) ────────────────────────────────────────────
   hook:         date + headline (the event title)
   perspectives: perspectives[] (each lens + its account — no winner declared)
   cta:          headline (sign-off) + url                                      */
export interface HistorySlideSpec {
  kind: "history";
  variant: "hook" | "perspectives" | "cta";
  /** optional slug for provenance / caption linkage. */
  event_slug?: string;
  /** hook: the dateline, e.g. "August 1947". */
  date?: string;
  /** hook: the event title. cta: the sign-off line. */
  headline?: string;
  /** perspectives: each historiographic lens and its one-line account. */
  perspectives?: Array<{ lens: string; voice: string }>;
  /** cta: the site URL. */
  url?: string;
}

/* ── WEEKLY (adhoc track, red) ───────────────────────────────────────────────
   hook:    issue_number + headline (cover headline) + deck
   stories: stories[] (the week's key / most-contested stories)
   cta:     headline (sign-off) + url                                           */
export interface WeeklySlideSpec {
  kind: "weekly";
  variant: "hook" | "stories" | "cta";
  /** hook: the issue number, e.g. 14. */
  issue_number?: number;
  /** hook: the cover headline. cta: the sign-off line. */
  headline?: string;
  /** hook: the cover deck / standfirst under the headline. */
  deck?: string;
  /** stories: the week's key stories, one per row. `tag` e.g. "Most contested". */
  stories?: Array<{ headline: string; tag?: string }>;
  /** cta: the site URL. */
  url?: string;
}

export async function fetchIgPost(id: string): Promise<IgPostRow | null> {
  const c = getClient();
  if (!c) return null;
  const { data, error } = await c.from("ig_posts").select("*").eq("id", id).single();
  if (error || !data) return null;
  return data as IgPostRow;
}

export async function listIgPostsForReview(): Promise<IgPostRow[]> {
  const c = getClient();
  if (!c) return [];
  const { data, error } = await c
    .from("ig_posts")
    .select("*")
    .in("state", ["draft", "caption_review", "render_failed", "captioning", "rendering"])
    .order("scheduled_for", { ascending: true });
  if (error || !data) return [];
  return data as IgPostRow[];
}

// Post IDs the capture step may render. Used by the IG render route's
// generateStaticParams in dev so these are valid params under dynamicParams=false.
// 'rendering' MUST be included: ig_capture sets a post to 'rendering' right
// before requesting its render URL, and Next evaluates generateStaticParams
// lazily on that first request — so the in-progress post must still be
// enumerable, or it 404s.
export async function listRenderablePostIds(): Promise<string[]> {
  const c = getClient();
  if (!c) return [];
  const { data, error } = await c
    .from("ig_posts")
    .select("id")
    .in("state", ["draft", "render_failed", "rendering"])
    .order("scheduled_for", { ascending: true })
    .limit(100);
  if (error || !data) return [];
  return (data as Array<{ id: string }>).map((r) => r.id);
}

export async function listIgPostsPosted(limit = 50): Promise<IgPostRow[]> {
  const c = getClient();
  if (!c) return [];
  const { data, error } = await c
    .from("ig_posts")
    .select("*")
    .eq("state", "posted")
    .order("posted_at", { ascending: false })
    .limit(limit);
  if (error || !data) return [];
  return data as IgPostRow[];
}

export async function approveIgPost(id: string): Promise<boolean> {
  const c = getClient();
  if (!c) return false;
  const { error } = await c
    .from("ig_posts")
    .update({ state: "approved" })
    .eq("id", id)
    .in("state", ["draft", "caption_review"]);
  return !error;
}

export async function rejectIgPost(id: string): Promise<boolean> {
  const c = getClient();
  if (!c) return false;
  const { error } = await c
    .from("ig_posts")
    .update({ state: "rejected" })
    .eq("id", id);
  return !error;
}

export async function updateIgCaption(
  id: string,
  caption: string,
  hashtags: string[]
): Promise<boolean> {
  const c = getClient();
  if (!c) return false;
  const { error } = await c
    .from("ig_posts")
    .update({ caption, hashtags })
    .eq("id", id);
  return !error;
}
