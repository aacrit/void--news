import { createClient, type SupabaseClient, type RealtimeChannel } from '@supabase/supabase-js';
import type { Edition, ShipRequest, ShipReply } from './types';

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
  if (!_client) return null;
  const { data, error } = await _client
    .from('cluster_articles')
    .select(`
      article:articles (
        id,
        title,
        url,
        summary,
        published_at,
        image_url,
        source:sources (
          name,
          tier,
          url
        ),
        bias_scores (
          political_lean,
          sensationalism,
          opinion_fact,
          factual_rigor,
          framing,
          confidence,
          rationale
        )
      )
    `)
    .eq('cluster_id', clusterId);

  if (error) return null;

  // The rationale column may be stored as a JSON string (text) rather than
  // jsonb, so PostgREST returns it as a raw string that needs JSON.parse().
  // Parse it client-side on each bias_score to ensure the rationale object
  // is accessible for BiasLens popups in the Deep Dive view.
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
  if (!_client) return [];
  const { data, error } = await _client
    .from("cluster_articles")
    .select("article:articles(bias_scores(political_lean))")
    .eq("cluster_id", clusterId);
  if (error || !data) return [];
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
  if (!_client) return null;

  // Check cached Supabase Storage image first — guaranteed no hotlink protection
  const { data: clusterRow } = await _client
    .from('story_clusters')
    .select('cached_image_url')
    .eq('id', clusterId)
    .single();

  if (clusterRow?.cached_image_url) {
    return clusterRow.cached_image_url as string;
  }

  // Fallback: og:image from cluster articles (may be blocked by CDN hotlinking)
  const { data, error } = await _client
    .from('cluster_articles')
    .select(`
      article:articles (
        image_url,
        source:sources ( tier )
      )
    `)
    .eq('cluster_id', clusterId);

  if (error || !data) return null;

  // Rank by source tier: us_major > international > independent
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

export async function fetchLastPipelineRun() {
  if (!_client) return null;
  const { data, error } = await _client
    .from('pipeline_runs')
    .select('completed_at, articles_fetched, status')
    .eq('status', 'completed')
    .order('completed_at', { ascending: false })
    .limit(1)
    .single();

  if (error) return null;
  return data;
}

/**
 * Fetch recent articles with bias scores for methodology live autopsy.
 * Returns 10 most recent articles that have non-null bias_scores.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchMethodologyArticles(): Promise<any[]> {
  if (!_client) return [];
  const { data, error } = await _client
    .from('articles')
    .select('id, title, published_at, excerpt, source:sources(name, slug, url), bias_scores(political_lean, sensationalism, opinion_fact, factual_rigor, framing, rationale)')
    .not('bias_scores', 'is', null)
    .order('published_at', { ascending: false })
    .limit(10);

  if (error || !data) return [];

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
export async function fetchDailyBrief(edition: string): Promise<any | null> {
  if (!_client) return null;

  const cols = 'tldr_headline, tldr_text, opinion_text, opinion_headline, opinion_lean, audio_url, audio_duration_seconds, opinion_start_seconds, audio_voice_label, audio_voice, audio_script, top_cluster_ids, created_at';

  // Try requested edition first, then fall back to any edition
  let res = await _client
    .from('daily_briefs')
    .select(cols)
    .eq('edition', edition)
    .order('created_at', { ascending: false })
    .limit(1)
    .single();

  if (res.error || !res.data) {
    // No brief for this edition — fall back to most recent brief from any edition
    res = await _client
      .from('daily_briefs')
      .select(cols)
      .order('created_at', { ascending: false })
      .limit(1)
      .single();
  }

  if (res.error || !res.data) return null;

  // Defensive: coerce text fields to strings — Supabase JSONB or corrupted
  // data can return objects, which crash React when rendered as children (#310).
  const d = res.data;
  if (d.tldr_text && typeof d.tldr_text !== "string") d.tldr_text = String(d.tldr_text);
  if (d.opinion_text && typeof d.opinion_text !== "string") d.opinion_text = String(d.opinion_text);
  if (d.tldr_headline && typeof d.tldr_headline !== "string") d.tldr_headline = String(d.tldr_headline);
  if (d.opinion_headline && typeof d.opinion_headline !== "string") d.opinion_headline = String(d.opinion_headline);
  return d;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchPreviousEpisodes(edition: string, limit = 9): Promise<any[]> {
  if (!_client) return [];

  const cols = 'id, edition, tldr_headline, tldr_text, opinion_headline, opinion_text, opinion_lean, audio_url, audio_duration_seconds, opinion_start_seconds, audio_voice_label, audio_voice, created_at';

  // Fetch last 3 days: up to `limit` briefs with audio for this edition
  const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString();

  const { data, error } = await _client
    .from('daily_briefs')
    .select(cols)
    .eq('edition', edition)
    .not('audio_url', 'is', null)
    .gte('created_at', threeDaysAgo)
    .order('created_at', { ascending: false })
    .limit(limit);

  if (error || !data) return [];
  return data;
}

/* ---------------------------------------------------------------------------
   Weekly Digest — void --weekly
   --------------------------------------------------------------------------- */

/**
 * Fetch the latest weekly digest for a given edition.
 * Falls back to any edition if none exists for the requested one.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchWeeklyDigest(edition: string): Promise<any | null> {
  if (!_client) return null;

  const cols = 'id, edition, week_start, week_end, issue_number, cover_headline, cover_text, cover_numbers, cover_image_url, cover_image_attribution, cover_image_source, recap_stories, opinion_left, opinion_center, opinion_right, opinion_headlines, opinion_topic, bias_report_text, bias_report_data, audio_url, audio_duration_seconds, total_articles, total_clusters, created_at';

  let res = await _client
    .from('weekly_digests')
    .select(cols)
    .eq('edition', edition)
    .order('created_at', { ascending: false })
    .limit(1)
    .single();

  if (res.error || !res.data) {
    // Fall back to most recent from any edition
    res = await _client
      .from('weekly_digests')
      .select(cols)
      .order('created_at', { ascending: false })
      .limit(1)
      .single();
  }

  if (res.error || !res.data) return null;

  // Parse JSONB fields that may arrive as strings
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const d = res.data as Record<string, any>;
  const jsonFields = ['cover_text', 'cover_numbers', 'recap_stories', 'opinion_left', 'opinion_center', 'opinion_right', 'opinion_headlines', 'bias_report_data'];
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
export async function fetchWeeklyArchive(edition?: string): Promise<any[]> {
  if (!_client) return [];

  const cols = 'id, edition, week_start, week_end, issue_number, cover_headline, created_at';

  let query = _client
    .from('weekly_digests')
    .select(cols)
    .order('created_at', { ascending: false })
    .limit(52);

  if (edition) {
    query = query.eq('edition', edition);
  }

  const { data, error } = await query;
  if (error || !data) return [];
  return data;
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
  const { data, error } = await _client
    .from('ship_requests')
    .select('*')
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

/** Vote on a ship request. Returns true if vote counted.
 *  F07: vote dedup is enforced server-side by unique(request_id, fingerprint)
 *  on ship_votes. The read-then-write on ship_requests.votes has a minor race
 *  window under concurrent votes; acceptable at current traffic levels.
 *  TODO: replace with an RPC (SELECT ... FOR UPDATE) if vote volume grows. */
export async function voteOnShipRequest(requestId: string, fingerprint: string): Promise<boolean> {
  if (!_client) return false;
  const { error: voteError } = await _client
    .from('ship_votes')
    .insert([{ request_id: requestId, fingerprint }]);
  if (voteError) return false;
  // Increment vote count (read-then-write; see F07 note above)
  const { data: current } = await _client
    .from('ship_requests')
    .select('votes')
    .eq('id', requestId)
    .single();
  if (current) {
    await _client
      .from('ship_requests')
      .update({ votes: (current.votes || 0) + 1 })
      .eq('id', requestId);
  }
  return true;
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
