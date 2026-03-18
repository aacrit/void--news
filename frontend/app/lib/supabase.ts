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
      last_updated
    `)
    .order('importance_score', { ascending: false })
    .limit(30);

  if (clusterError || !clusters?.length) {
    return null;
  }

  return clusters;
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
