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
  // Step 1: Find article IDs with opinion_fact > 50
  const { data: biasRows } = await supabase
    .from("bias_scores")
    .select("article_id, political_lean, sensationalism, opinion_fact, confidence")
    .gt("opinion_fact", 50);

  if (!biasRows || biasRows.length === 0) return [];

  const biasMap = new Map(biasRows.map((b) => [b.article_id, b]));
  const articleIds = biasRows.map((b) => b.article_id);

  // Step 2: Fetch articles for those IDs in the right section
  const { data: articles } = await supabase
    .from("articles")
    .select("id, title, summary, author, url, published_at, section, source_id")
    .in("id", articleIds)
    .eq("section", section)
    .order("published_at", { ascending: false })
    .limit(200);

  if (!articles || articles.length === 0) return [];

  // Step 3: Fetch source metadata
  const sourceIds = [...new Set(articles.map((a) => a.source_id).filter(Boolean))];
  const { data: sources } = await supabase
    .from("sources")
    .select("id, name, slug, tier")
    .in("id", sourceIds);

  const sourceMap = new Map((sources || []).map((s) => [s.id, s]));

  /* eslint-disable @typescript-eslint/no-explicit-any */
  const normalized = articles.map((row: any) => {
    const src = sourceMap.get(row.source_id);
    const bs = biasMap.get(row.id);
    if (!src || !bs) return null;
    return {
      id: row.id as string,
      title: row.title as string,
      summary: (row.summary || "") as string,
      author: (row.author || null) as string | null,
      url: row.url as string,
      publishedAt: row.published_at as string,
      sourceName: src.name as string,
      sourceSlug: src.slug as string,
      sourceTier: src.tier as "us_major" | "international" | "independent",
      section: row.section as "world" | "us",
      politicalLean: Number(bs.political_lean ?? 50),
      sensationalism: Number(bs.sensationalism ?? 30),
      confidence: Number(bs.confidence ?? 0.5),
    };
  }).filter(Boolean);

  // Per-outlet cap: max 2 per source_slug
  const slugCount: Record<string, number> = {};
  const capped = normalized.filter((a) => {
    const n = (slugCount[a!.sourceSlug] || 0);
    if (n >= 2) return false;
    slugCount[a!.sourceSlug] = n + 1;
    return true;
  });

  // Spectrum balance: in every 5 positions, max 2 from same lean bucket
  const leanBucket = (lean: number) =>
    lean < 41 ? "L" : lean <= 60 ? "C" : "R";

  const balanced: typeof capped = [];
  const windowBuckets: string[] = [];
  for (const a of capped) {
    const bucket = leanBucket(a!.politicalLean);
    const windowStart = Math.max(0, windowBuckets.length - 4);
    const recentWindow = windowBuckets.slice(windowStart);
    const bucketCount = recentWindow.filter((b) => b === bucket).length;
    if (bucketCount >= 2) continue;
    balanced.push(a);
    windowBuckets.push(bucket);
    if (balanced.length >= 30) break;
  }

  return balanced;
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
