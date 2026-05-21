import "server-only";
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

/* IG engagement (comments, DMs, mentions, hashtag candidates) reads.
   Server-only. RLS denies anon; we use the service-role key. */

let _server: SupabaseClient | null = null;

function getClient(): SupabaseClient | null {
  if (_server) return _server;
  const url = process.env.SUPABASE_URL ?? process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return null;
  _server = createClient(url, key, { auth: { persistSession: false } });
  return _server;
}

export interface IgComment {
  id: string;
  ig_comment_id: string;
  ig_media_id: string;
  ig_username: string | null;
  text: string;
  is_reply: boolean;
  score: number;
  auto_replied: boolean;
  reply_drafted: string | null;
  reply_sent_at: string | null;
  created_at: string;
}

export interface IgDm {
  id: string;
  ig_thread_id: string;
  ig_username: string | null;
  text: string | null;
  priority: "press" | "inbox" | "noise";
  matched_keywords: string[] | null;
  first_touch_sent: boolean;
  read_by_admin: boolean;
  created_at: string;
}

export interface IgMention {
  id: string;
  ig_media_id: string;
  ig_username: string | null;
  caption: string | null;
  permalink: string | null;
  is_seed_list: boolean;
  archived: boolean;
  created_at: string;
}

export interface IgHashtagCandidate {
  id: string;
  hashtag: string;
  ig_media_id: string;
  ig_username: string | null;
  caption: string | null;
  permalink: string | null;
  engagement_score: number;
  dismissed: boolean;
  acted_on: boolean;
  created_at: string;
}

export async function listIgComments(limit = 30): Promise<IgComment[]> {
  const c = getClient();
  if (!c) return [];
  const { data } = await c
    .from("ig_comments")
    .select("*")
    .eq("hidden_or_deleted", false)
    .is("reply_sent_at", null)
    .eq("auto_replied", false)
    .order("score", { ascending: false })
    .order("created_at", { ascending: false })
    .limit(limit);
  return (data ?? []) as IgComment[];
}

export async function listIgDms(limit = 30): Promise<IgDm[]> {
  const c = getClient();
  if (!c) return [];
  const { data } = await c
    .from("ig_dms")
    .select("*")
    .eq("inbound", true)
    .eq("read_by_admin", false)
    .order("priority", { ascending: true })   // 'inbox' < 'noise' < 'press' alphabetically — fix below
    .order("created_at", { ascending: false })
    .limit(limit);
  // Reorder: press first, then inbox, then noise.
  const all = (data ?? []) as IgDm[];
  const order = { press: 0, inbox: 1, noise: 2 } as const;
  return all.sort((a, b) => (order[a.priority] - order[b.priority]) || (a.created_at < b.created_at ? 1 : -1));
}

export async function listIgMentions(limit = 30): Promise<IgMention[]> {
  const c = getClient();
  if (!c) return [];
  const { data } = await c
    .from("ig_mentions")
    .select("*")
    .eq("archived", false)
    .order("created_at", { ascending: false })
    .limit(limit);
  return (data ?? []) as IgMention[];
}

export async function listIgHashtagCandidates(limit = 30): Promise<IgHashtagCandidate[]> {
  const c = getClient();
  if (!c) return [];
  const { data } = await c
    .from("ig_hashtag_candidates")
    .select("*")
    .eq("dismissed", false)
    .eq("acted_on", false)
    .order("engagement_score", { ascending: false })
    .order("created_at", { ascending: false })
    .limit(limit);
  return (data ?? []) as IgHashtagCandidate[];
}
