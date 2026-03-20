import { createClient } from '@supabase/supabase-js';

// Supabase project credentials (public anon key — safe for client-side use)
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://xryzskhgfuafyotrcdvj.supabase.co';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhyeXpza2hnZnVhZnlvdHJjZHZqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM4MTI4NTYsImV4cCI6MjA4OTM4ODg1Nn0._AnBvpTBUa7sqyU_T49bPGi-YOKDkiSptVPGn6YHpRE';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

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

export async function fetchOpinionArticles(section: "world" | "us" | "india") {
  // Use the opinion clusters approach: query story_clusters with
  // content_type=opinion, then fetch their linked articles for metadata.
  // This avoids the large .in() URL problem with 180+ article UUIDs.
  const { data: clusters } = await supabase
    .from("story_clusters")
    .select("id, title, summary, source_count, first_published, headline_rank, bias_diversity")
    .contains("sections", [section])
    .eq("content_type", "opinion")
    .order("headline_rank", { ascending: false })
    .limit(50);

  if (!clusters || clusters.length === 0) return [];

  // Fetch linked articles for author/URL/source info
  const clusterIds = clusters.map((c) => c.id);

  // Batch in chunks of 20 to stay within URL limits
  const allLinks: { cluster_id: string; article_id: string }[] = [];
  for (let i = 0; i < clusterIds.length; i += 20) {
    const chunk = clusterIds.slice(i, i + 20);
    const { data: links } = await supabase
      .from("cluster_articles")
      .select("cluster_id, article_id")
      .in("cluster_id", chunk);
    if (links) allLinks.push(...links);
  }

  const articleIds = [...new Set(allLinks.map((l) => l.article_id))];
  if (articleIds.length === 0) return [];

  // Fetch articles in chunks
  const allArticles: Record<string, any>[] = [];
  for (let i = 0; i < articleIds.length; i += 30) {
    const chunk = articleIds.slice(i, i + 30);
    const { data: arts } = await supabase
      .from("articles")
      .select("id, title, summary, full_text, author, url, source_id, published_at")
      .in("id", chunk);
    if (arts) allArticles.push(...arts);
  }
  const articleMap = new Map(allArticles.map((a) => [a.id, a]));

  // Map cluster→first article for author/URL
  const clusterArticleMap = new Map<string, string>();
  for (const link of allLinks) {
    if (!clusterArticleMap.has(link.cluster_id)) {
      clusterArticleMap.set(link.cluster_id, link.article_id);
    }
  }

  // Fetch source metadata
  const sourceIds = [...new Set(allArticles.map((a) => a.source_id).filter(Boolean))];
  const allSources: Record<string, any>[] = [];
  for (let i = 0; i < sourceIds.length; i += 30) {
    const chunk = sourceIds.slice(i, i + 30);
    const { data: srcs } = await supabase
      .from("sources")
      .select("id, name, slug, tier")
      .in("id", chunk);
    if (srcs) allSources.push(...srcs);
  }
  const sourceMap = new Map(allSources.map((s) => [s.id, s]));

  /* eslint-disable @typescript-eslint/no-explicit-any */
  const normalized = clusters.map((cluster: any) => {
    const artId = clusterArticleMap.get(cluster.id);
    const art = artId ? articleMap.get(artId) : null;
    const src = art ? sourceMap.get(art.source_id) : null;
    const bd = cluster.bias_diversity || {};

    return {
      id: cluster.id as string,
      // Prefer the original article's headline and text over cluster summary
      title: (art?.title || cluster.title) as string,
      summary: (art?.full_text || art?.summary || cluster.summary || "") as string,
      author: (art?.author || null) as string | null,
      url: art?.url || "" as string,
      publishedAt: (art?.published_at || cluster.first_published || "") as string,
      sourceName: (src?.name || "Unknown") as string,
      sourceSlug: (src?.slug || "") as string,
      sourceTier: (src?.tier || "independent") as "us_major" | "international" | "independent",
      section: section as "world" | "us",
      politicalLean: Number(bd.avg_political_lean ?? 50),
      sensationalism: Number(bd.avg_sensationalism ?? 30),
      confidence: Number(bd.aggregate_confidence ?? 0.5),
    };
  });

  // Per-outlet cap: max 3 per source_slug
  const slugCount: Record<string, number> = {};
  const capped = normalized.filter((a) => {
    const n = (slugCount[a!.sourceSlug] || 0);
    if (n >= 3) return false;
    slugCount[a!.sourceSlug] = n + 1;
    return true;
  });

  // No aggressive spectrum balance filter — show all opinion pieces.
  // The per-outlet cap already prevents any single outlet from dominating.
  return capped.slice(0, 50);
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
