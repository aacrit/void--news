import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://xryzskhgfuafyotrcdvj.supabase.co';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhyeXpza2hnZnVhZnlvdHJjZHZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4MTI4NTYsImV4cCI6MjA4OTM4ODg1Nn0._AnBvpTBUa7sqyU_T49bPGi-YOKDkiSptVPGn6YHpRE';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

export async function fetchStories() {
  const { data: clusters, error: clusterError } = await supabase
    .from('story_clusters')
    .select(`
      id,
      title,
      summary,
      category,
      section,
      importance_score,
      source_count,
      first_published,
      last_updated,
      divergence_score,
      headline_rank,
      coverage_velocity,
      bias_diversity
    `)
    .order('headline_rank', { ascending: false })
    .limit(30);

  if (clusterError || !clusters?.length) {
    return null;
  }

  return clusters;
}

/**
 * Fetch aggregated bias scores for multiple clusters in a single query.
 * Uses the cluster_bias_summary view to avoid N+1 queries.
 */
export async function fetchClusterBiasSummary(clusterIds: string[]) {
  const { data, error } = await supabase
    .from('cluster_bias_summary')
    .select('*')
    .in('cluster_id', clusterIds);

  if (error) {
    // View may not be deployed yet — return empty
    console.warn('cluster_bias_summary query failed:', error.message);
    return null;
  }

  // Index by cluster_id for O(1) lookup
  const map: Record<string, {
    avg_political_lean: number;
    avg_sensationalism: number;
    avg_opinion_fact: number;
    avg_factual_rigor: number;
    avg_framing: number;
    lean_spread: number;
    framing_spread: number;
    lean_range: number;
    sensationalism_spread: number;
    opinion_spread: number;
    aggregate_confidence: number;
    analyzed_article_count: number;
  }> = {};

  for (const row of (data || [])) {
    map[row.cluster_id] = row;
  }

  return map;
}

export async function fetchArticlesForCluster(clusterId: string) {
  const { data, error } = await supabase
    .from('cluster_articles')
    .select(`
      article:articles (
        id,
        title,
        url,
        summary,
        author,
        published_at,
        source:sources (
          name,
          tier,
          political_lean_baseline
        ),
        bias_scores (
          political_lean,
          sensationalism,
          opinion_fact,
          factual_rigor,
          framing,
          confidence
        )
      )
    `)
    .eq('cluster_id', clusterId);

  if (error) return null;
  return data;
}

export async function fetchDeepDiveData(clusterId: string) {
  const { data, error } = await supabase
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
          framing
        )
      )
    `)
    .eq('cluster_id', clusterId);

  if (error) return null;
  return data;
}

export async function fetchLastPipelineRun() {
  const { data, error } = await supabase
    .from('pipeline_runs')
    .select('completed_at, articles_fetched, status')
    .eq('status', 'completed')
    .order('completed_at', { ascending: false })
    .limit(1)
    .single();

  if (error) return null;
  return data;
}
