import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import type { Edition } from './types';

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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export async function fetchDailyBrief(edition: string): Promise<any | null> {
  if (!_client) return null;
  const { data, error } = await _client
    .from('daily_briefs')
    .select('tldr_headline, tldr_text, opinion_text, opinion_headline, opinion_lean, opinion_start_seconds, audio_url, audio_duration_seconds, created_at')
    .eq('edition', edition)
    .order('created_at', { ascending: false })
    .limit(1)
    .single();

  if (error || !data) return null;
  return data;
}
