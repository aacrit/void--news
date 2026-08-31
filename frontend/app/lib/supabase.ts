import { createClient, type SupabaseClient, type RealtimeChannel } from '@supabase/supabase-js';
import type { Edition, ShipRequest, ShipReply } from './types';
import { BASE_PATH } from './utils';

// ---------------------------------------------------------------------------
// Static-JSON reads (2026-08-30 Cloudflare migration).
//
// All READ data (feed, brief, deep dive, weekly, sources methodology) is now
// regenerated as static JSON by the pipeline each run and served from the CDN,
// so the browser never hits a metered database. These helpers replace the old
// supabase-js read queries. The Supabase client below is retained ONLY for the
// ship board write path, which moves to a Cloudflare Worker in a later step.
// ---------------------------------------------------------------------------

/** Fetch a static JSON snapshot from /data/<relPath>. Returns null on any error
 *  (missing file, offline, parse failure) so callers degrade gracefully. */
async function getStaticJson<T>(relPath: string): Promise<T | null> {
  try {
    const res = await fetch(`${BASE_PATH}/data/${relPath}`, { cache: 'no-cache' });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

// Supabase project credentials — must be set via environment variables.
// Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in .env.local
// (dev) or as GitHub Actions secrets (CI/CD deploy).
//
// If credentials are absent the client is null and all data functions return
// empty results. The UI shows "Unable to connect to data source" rather than
// crashing. This prevents a module-load throw from breaking the entire app.

let _client: SupabaseClient | null = null;
let _clientError: string | null = null;

try {
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseAnonKey) {
    _clientError =
      'Unable to connect to data source. Configuration is missing.';
  } else {
    _client = createClient(supabaseUrl, supabaseAnonKey);
  }
} catch (err) {
  _clientError =
    err instanceof Error ? err.message : 'Unable to connect to data source.';
}

/** Possibly-null Supabase client. Always check before use. */
export const supabase: SupabaseClient | null = _client;

/** Non-null when credentials are absent or client creation failed. */
export const supabaseError: string | null = _clientError;

export async function fetchDeepDiveData(clusterId: string) {
  // Static export: per-cluster deep-dive roster emitted as
  // /data/deepdive/<clusterId>.json (same shape the old cluster_articles join
  // returned). Clusters outside the emitted displayed set resolve to null.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = await getStaticJson<any[]>(`deepdive/${clusterId}.json`);
  if (!data) return null;

  // The rationale may be stored as a JSON string; parse it client-side so the
  // rationale object is accessible for BiasLens popups in the Deep Dive view.
  if (data) {
    for (const row of data) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const article = row.article as any;
      if (!article?.bias_scores) continue;

      // bias_scores may be an object (one-to-one) or array (one-to-many)
      const scores = Array.isArray(article.bias_scores)
        ? article.bias_scores
        : [article.bias_scores];

      for (const score of scores) {
        if (typeof score.rationale === 'string') {
          try {
            score.rationale = JSON.parse(score.rationale);
          } catch {
            score.rationale = null;
          }
        }
      }

      // Normalize to array for consistent downstream access
      article.bias_scores = scores;
    }
  }

  return data;
}

/** Lightweight fetch: political_lean values for all articles in a cluster.
 *  Used by the Sigil popup to compute real KDE matching the DeepDive spectrum.
 *  Much cheaper than fetchDeepDiveData — only the lean column, no joins on sources/rationale. */
export async function fetchSourceLeans(clusterId: string): Promise<number[]> {
  // Derived from the same static deep-dive roster as fetchDeepDiveData.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = await getStaticJson<any[]>(`deepdive/${clusterId}.json`);
  if (!data) return [];
  const leans: number[] = [];
  for (const row of data) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const article = row.article as any;
    if (!article) continue;
    const biasRaw = article.bias_scores;
    const bias = Array.isArray(biasRaw) ? biasRaw[0] : biasRaw;
    const lean = bias?.political_lean as number;
    if (typeof lean === "number") leans.push(lean);
  }
  return leans;
}

/** Fetch the best image URL for a cluster.
 *  Priority 1: cached_image_url on the cluster (Supabase Storage, no hotlink issues).
 *  Priority 2: og:image from articles, tier-ranked (us_major > international > independent).
 *  cached_image_url is populated by the pipeline's step 8e (cluster_image_cacher.py). */
export async function fetchClusterLeadImage(clusterId: string): Promise<string | null> {
  // Static export: derive the best og:image from the deep-dive roster, tier-
  // ranked (us_major > international > independent). The retired cluster_image
  // cacher means there is no cached_image_url to prefer.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = await getStaticJson<any[]>(`deepdive/${clusterId}.json`);
  if (!data) return null;

  const tierRank: Record<string, number> = { us_major: 3, international: 2, independent: 1 };
  let best: { url: string; rank: number } | null = null;

  for (const row of data) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const article = row.article as any;
    if (!article?.image_url) continue;
    const url = article.image_url as string;
    if (url.startsWith('data:') || url.length < 20 || /logo|icon|favicon|pixel|spacer|tracker|1x1|blank|placeholder|default-og|brand/i.test(url)) continue;
    const tier = article.source?.tier as string ?? 'independent';
    const rank = tierRank[tier] ?? 0;
    if (!best || rank > best.rank) {
      best = { url, rank };
    }
  }

  return best?.url ?? null;
}

// FUTURE: Op-Ed feature — commented out for redesign
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchOpinionArticles(_section: Edition): Promise<any[]> {
  return [];
}

export async function fetchLastPipelineRun(): Promise<{
  completed_at: string;
  articles_fetched?: number;
  status?: string;
} | null> {
  // Static export: the edition build time is prerendered into the page from
  // build-data/feed.json (serverFeed). The client no longer queries pipeline_runs;
  // callers that used this for a "last updated" line receive it server-side.
  return null;
}

/**
 * Fetch recent articles with bias scores for methodology live autopsy.
 * Returns 10 most recent articles that have non-null bias_scores.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchMethodologyArticles(): Promise<any[]> {
  // Static export: 10 recent bias-scored articles emitted as /data/methodology.json.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const data = await getStaticJson<any[]>('methodology.json');
  if (!data) return [];

  // Parse rationale strings into objects (same pattern as fetchDeepDiveData)
  for (const row of data) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const scores = (row as any).bias_scores;
    if (!scores) continue;
    const arr = Array.isArray(scores) ? scores : [scores];
    for (const score of arr) {
      if (typeof score.rationale === 'string') {
        try {
          score.rationale = JSON.parse(score.rationale);
        } catch {
          score.rationale = null;
        }
      }
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (row as any).bias_scores = arr;
  }

  return data;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchDailyBrief(_edition: string): Promise<any | null> {
  // Static export: the latest daily brief is emitted as /data/brief.json.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const d = await getStaticJson<any>('brief.json');
  if (!d) return null;

  // Defensive: coerce text fields to strings — a corrupted/JSONB field can be an
  // object, which crashes React when rendered as children (#310).
  if (d.tldr_text && typeof d.tldr_text !== "string") d.tldr_text = String(d.tldr_text);
  if (d.opinion_text && typeof d.opinion_text !== "string") d.opinion_text = String(d.opinion_text);
  if (d.tldr_headline && typeof d.tldr_headline !== "string") d.tldr_headline = String(d.tldr_headline);
  if (d.opinion_headline && typeof d.opinion_headline !== "string") d.opinion_headline = String(d.opinion_headline);
  return d;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchPreviousEpisodes(_edition: string, _limit = 9): Promise<any[]> {
  // Static export: only the latest edition is snapshotted (/data/brief.json).
  // A rolling multi-day audio archive can be reintroduced by emitting an
  // episodes.json list from the pipeline if the On Air back-catalogue returns.
  return [];
}

/* ---------------------------------------------------------------------------
   Weekly Digest — void --weekly
   --------------------------------------------------------------------------- */

/**
 * Fetch the latest weekly digest for a given edition.
 * Falls back to any edition if none exists for the requested one.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchWeeklyDigest(_edition: string): Promise<any | null> {
  // Static export: latest weekly digest emitted as /data/weekly.json (JSONB
  // fields already parsed by the emitter).
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const d = await getStaticJson<Record<string, any>>('weekly.json');
  if (!d) return null;
  // Belt-and-suspenders: parse any JSONB field that arrived as a string.
  const jsonFields = ['cover_text', 'recap_stories', 'opinion_left', 'opinion_center', 'opinion_right', 'opinion_headlines', 'bias_report_data'];
  for (const field of jsonFields) {
    if (typeof d[field] === 'string') {
      try { d[field] = JSON.parse(d[field]); } catch { d[field] = null; }
    }
  }
  return d;
}

/**
 * Fetch all weekly digests (for archive listing).
 * Returns id, edition, week_start, week_end, issue_number, created_at.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchWeeklyArchive(_edition?: string): Promise<any[]> {
  // Static export: only the latest issue is snapshotted (/data/weekly.json). A
  // full weekly archive list can be emitted as weekly_archive.json if needed.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const d = await getStaticJson<Record<string, any>>('weekly.json');
  return d ? [d] : [];
}

/* ---------------------------------------------------------------------------
   void --ship — Feature/Bug Request Tracker
   --------------------------------------------------------------------------- */

/** Generate a browser fingerprint for vote dedup */
export function generateFingerprint(): string {
  const nav = typeof navigator !== 'undefined' ? navigator : null;
  const raw = [
    nav?.userAgent || '',
    nav?.language || '',
    screen?.width || 0,
    screen?.height || 0,
    Intl?.DateTimeFormat()?.resolvedOptions()?.timeZone || '',
  ].join('|');
  let h = 0x811c9dc5;
  for (let i = 0; i < raw.length; i++) {
    h ^= raw.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(16).padStart(8, '0');
}

/** Fetch all ship requests */
export async function fetchShipRequests(): Promise<ShipRequest[]> {
  if (!_client) return [];
  // Explicit column list (omits device_info + ip_hash, which are revoked from
  // anon in migration 068 — they are collected for rate limiting only).
  const { data, error } = await _client
    .from('ship_requests')
    .select(
      'id,title,description,category,area,edition_context,status,priority,votes,ceo_response,claude_branch,shipped_commit,shipped_diff_summary,created_at,triaged_at,shipped_at,updated_at'
    )
    .order('created_at', { ascending: false });
  if (error || !data) return [];
  return data as ShipRequest[];
}

/** Submit a new ship request */
export async function submitShipRequest(req: {
  title: string;
  description: string;
  category: string;
  area: string;
  edition_context?: string | null;
  device_info?: string | null;
  ip_hash?: string | null;
}): Promise<ShipRequest | null> {
  if (!_client) return null;
  const { data, error } = await _client
    .from('ship_requests')
    .insert([req])
    .select()
    .single();
  if (error || !data) return null;
  return data as ShipRequest;
}

/** Vote on a ship request. Returns the authoritative new vote count, or null
 *  if the vote did not count.
 *  F07: vote dedup is enforced server-side by unique(request_id, fingerprint)
 *  on ship_votes. The previous read-then-write on ship_requests.votes was
 *  silently blocked by RLS (migration 037 grants UPDATE to service_role only),
 *  so the counter never incremented for anon voters. sync_ship_votes (migration
 *  062) is a SECURITY DEFINER function that recounts ship_votes for the request,
 *  writes the count to ship_requests.votes, and returns the new count. */
export async function voteOnShipRequest(requestId: string, fingerprint: string): Promise<number | null> {
  if (!_client) return null;
  const { error: voteError } = await _client
    .from('ship_votes')
    .insert([{ request_id: requestId, fingerprint }]);
  if (voteError) return null;
  // Recount + persist server-side (bypasses the service_role-only UPDATE RLS).
  const { data: newCount, error: rpcError } = await _client
    .rpc('sync_ship_votes', { p_request_id: requestId });
  if (rpcError) return null;
  return typeof newCount === 'number' ? newCount : null;
}

/** Subscribe to realtime changes on ship_requests */
export function subscribeToShipRequests(
  onUpdate: (payload: { eventType: string; new: ShipRequest; old: Partial<ShipRequest> }) => void
): (() => void) {
  if (!_client) return () => {};
  const channel: RealtimeChannel = _client
    .channel('ship-requests-realtime')
    .on(
      'postgres_changes',
      { event: '*', schema: 'public', table: 'ship_requests' },
      (payload) => {
        onUpdate({
          eventType: payload.eventType,
          new: payload.new as ShipRequest,
          old: payload.old as Partial<ShipRequest>,
        });
      }
    )
    .subscribe();
  return () => { channel.unsubscribe(); };
}

/** Fetch ship request counts by status (for Command Center) */
export async function fetchShipStats(): Promise<Record<string, number>> {
  if (!_client) return {};
  const { data, error } = await _client
    .from('ship_requests')
    .select('status');
  if (error || !data) return {};
  const counts: Record<string, number> = { submitted: 0, triaged: 0, building: 0, shipped: 0, wontship: 0 };
  for (const row of data) {
    counts[row.status] = (counts[row.status] || 0) + 1;
  }
  return counts;
}

/** Fetch replies for a ship request */
export async function fetchShipReplies(requestId: string): Promise<ShipReply[]> {
  if (!_client) return [];
  const { data, error } = await _client
    .from('ship_replies')
    .select('*')
    .eq('request_id', requestId)
    .order('created_at', { ascending: true });
  if (error || !data) return [];
  return data as ShipReply[];
}

/** Submit a reply to a ship request */
export async function submitShipReply(requestId: string, body: string, fingerprint: string): Promise<ShipReply | null> {
  if (!_client) return null;
  const { data, error } = await _client
    .from('ship_replies')
    .insert([{ request_id: requestId, body, fingerprint }])
    .select()
    .single();
  if (error || !data) return null;
  return data as ShipReply;
}

/** Subscribe to realtime changes on ship_replies */
export function subscribeToShipReplies(
  onInsert: (reply: ShipReply) => void
): (() => void) {
  if (!_client) return () => {};
  const channel: RealtimeChannel = _client
    .channel('ship-replies-realtime')
    .on(
      'postgres_changes',
      { event: 'INSERT', schema: 'public', table: 'ship_replies' },
      (payload) => { onInsert(payload.new as ShipReply); }
    )
    .subscribe();
  return () => { channel.unsubscribe(); };
}
