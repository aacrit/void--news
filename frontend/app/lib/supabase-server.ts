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

export type IgPillar = "receipt" | "method" | "history" | "brief" | "bts" | "heatmap";

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

/* Slide spec shapes — discriminated by pillar. See plan §5. */
export type SlideSpec =
  | ReceiptSlideSpec
  | MethodSlideSpec
  | HistorySlideSpec
  | BriefSlideSpec
  | HeatmapSlideSpec;

export interface ReceiptSlideSpec {
  kind: "receipt";
  topic: string;
  headlines: Array<{
    outlet: string;
    lean_score: number;
    framing_score?: number;
    headline: string;
  }>;
  caption?: string;
}

export interface MethodSlideSpec {
  kind: "method";
  axis_name: string;
  brief: string;
  signals?: string;
  sample?: { text: string; highlights?: Array<{ start: number; end: number }> };
  principle?: string;
}

export interface HistorySlideSpec {
  kind: "history";
  event_slug: string;
  date: string;
  lead_fact?: string;
  perspective?: { lens: string; voice: string };
  image_url?: string;
  cta?: string;
}

export interface BriefSlideSpec {
  kind: "brief";
  variant: "pullquote" | "bts" | "manifesto";
  content: string;
  attribution?: string;
  stats?: Record<string, string | number>;
}

export interface HeatmapSlideSpec {
  kind: "heatmap";
  topic: string;
  countries: Array<{ code: string; lean: number; source_count: number }>;
  caption?: string;
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

// Post IDs the capture step renders. Used by the IG render route's
// generateStaticParams in dev so these are valid params under dynamicParams=false.
// Mirrors the state set in pipeline/social/ig_capture.py::_fetch_targets.
export async function listRenderablePostIds(): Promise<string[]> {
  const c = getClient();
  if (!c) return [];
  const { data, error } = await c
    .from("ig_posts")
    .select("id")
    .in("state", ["draft", "render_failed"])
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
