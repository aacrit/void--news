-- Sources table
CREATE TABLE sources (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  rss_url TEXT,
  scrape_config JSONB DEFAULT '{}',
  tier TEXT NOT NULL CHECK (tier IN ('us_major', 'international', 'independent')),
  country TEXT NOT NULL,
  type TEXT NOT NULL,
  political_lean_baseline TEXT CHECK (political_lean_baseline IN ('left', 'center-left', 'center', 'center-right', 'right', 'varies')),
  credibility_notes TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Articles table
CREATE TABLE articles (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  source_id UUID NOT NULL REFERENCES sources(id),
  url TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  summary TEXT,
  full_text TEXT,
  author TEXT,
  published_at TIMESTAMPTZ,
  fetched_at TIMESTAMPTZ DEFAULT now(),
  section TEXT CHECK (section IN ('world', 'us', 'other')),
  image_url TEXT,
  word_count INTEGER,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Bias scores (per-article, 6 axes)
CREATE TABLE bias_scores (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  article_id UUID UNIQUE NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  political_lean SMALLINT CHECK (political_lean BETWEEN 0 AND 100),
  sensationalism SMALLINT CHECK (sensationalism BETWEEN 0 AND 100),
  opinion_fact SMALLINT CHECK (opinion_fact BETWEEN 0 AND 100),
  factual_rigor SMALLINT CHECK (factual_rigor BETWEEN 0 AND 100),
  framing SMALLINT CHECK (framing BETWEEN 0 AND 100),
  confidence REAL DEFAULT 0.5,
  analyzed_at TIMESTAMPTZ DEFAULT now()
);

-- Story clusters
CREATE TABLE story_clusters (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  title TEXT NOT NULL,
  summary TEXT,
  consensus_points JSONB DEFAULT '[]',
  divergence_points JSONB DEFAULT '[]',
  category TEXT,
  section TEXT CHECK (section IN ('world', 'us')),
  importance_score REAL DEFAULT 0,
  source_count INTEGER DEFAULT 0,
  first_published TIMESTAMPTZ,
  last_updated TIMESTAMPTZ DEFAULT now(),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Junction: articles <-> clusters
CREATE TABLE cluster_articles (
  cluster_id UUID NOT NULL REFERENCES story_clusters(id) ON DELETE CASCADE,
  article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  PRIMARY KEY (cluster_id, article_id)
);

-- Categories
CREATE TABLE categories (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  slug TEXT UNIQUE NOT NULL
);

-- Junction: articles <-> categories
CREATE TABLE article_categories (
  article_id UUID NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
  PRIMARY KEY (article_id, category_id)
);

-- Pipeline run tracking
CREATE TABLE pipeline_runs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  started_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ,
  status TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
  articles_fetched INTEGER DEFAULT 0,
  articles_analyzed INTEGER DEFAULT 0,
  clusters_created INTEGER DEFAULT 0,
  errors JSONB DEFAULT '[]',
  duration_seconds REAL
);

-- Indexes
CREATE INDEX idx_articles_source ON articles(source_id);
CREATE INDEX idx_articles_published ON articles(published_at DESC);
CREATE INDEX idx_articles_section ON articles(section);
CREATE INDEX idx_bias_scores_article ON bias_scores(article_id);
CREATE INDEX idx_clusters_importance ON story_clusters(importance_score DESC);
CREATE INDEX idx_clusters_section ON story_clusters(section);
CREATE INDEX idx_cluster_articles_cluster ON cluster_articles(cluster_id);
CREATE INDEX idx_cluster_articles_article ON cluster_articles(article_id);

-- Insert default categories
-- Slugs must match the pipeline auto_categorize.py output keys.
-- Display names must match the frontend Category type in types.ts.
INSERT INTO categories (name, slug) VALUES
  ('Politics', 'politics'),
  ('Economy', 'economy'),
  ('Tech', 'technology'),
  ('Health', 'health'),
  ('Environment', 'environment'),
  ('Conflict', 'conflict'),
  ('Science', 'science'),
  ('Culture', 'culture'),
  ('Sports', 'sports');

-- Enable RLS
ALTER TABLE sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE bias_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE story_clusters ENABLE ROW LEVEL SECURITY;
ALTER TABLE cluster_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_categories ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;

-- Public read access policies (anon can read everything)
CREATE POLICY "Public read sources" ON sources FOR SELECT USING (true);
CREATE POLICY "Public read articles" ON articles FOR SELECT USING (true);
CREATE POLICY "Public read bias_scores" ON bias_scores FOR SELECT USING (true);
CREATE POLICY "Public read story_clusters" ON story_clusters FOR SELECT USING (true);
CREATE POLICY "Public read cluster_articles" ON cluster_articles FOR SELECT USING (true);
CREATE POLICY "Public read categories" ON categories FOR SELECT USING (true);
CREATE POLICY "Public read article_categories" ON article_categories FOR SELECT USING (true);
CREATE POLICY "Public read pipeline_runs" ON pipeline_runs FOR SELECT USING (true);
