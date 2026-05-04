-- P0 Security: Revoke anon/authenticated EXECUTE on destructive RPC functions
-- These functions perform DELETE/UPDATE and must only be callable by service_role (pipeline)
REVOKE EXECUTE ON FUNCTION cleanup_stale_clusters(INT) FROM anon, authenticated;
REVOKE EXECUTE ON FUNCTION cleanup_stuck_pipeline_runs(INT) FROM anon, authenticated;
REVOKE EXECUTE ON FUNCTION refresh_cluster_enrichment(UUID) FROM anon, authenticated;
REVOKE EXECUTE ON FUNCTION update_updated_at_column() FROM anon, authenticated;

-- Clean up dangling references before adding FK constraints
UPDATE daily_briefs SET opinion_cluster_id = NULL
  WHERE opinion_cluster_id IS NOT NULL
  AND opinion_cluster_id NOT IN (SELECT id FROM story_clusters);

UPDATE story_clusters SET story_memory_id = NULL
  WHERE story_memory_id IS NOT NULL
  AND story_memory_id NOT IN (SELECT id FROM story_memory);

-- P0 Data Integrity: Add FK for opinion_cluster_id on daily_briefs
-- SET NULL on delete so older briefs gracefully lose their opinion link when clusters are pruned
ALTER TABLE daily_briefs
  ADD CONSTRAINT fk_daily_briefs_opinion_cluster
  FOREIGN KEY (opinion_cluster_id) REFERENCES story_clusters(id)
  ON DELETE SET NULL;

-- P1 Data Integrity: Add FK for story_memory_id on story_clusters
ALTER TABLE story_clusters
  ADD CONSTRAINT fk_story_clusters_story_memory
  FOREIGN KEY (story_memory_id) REFERENCES story_memory(id)
  ON DELETE SET NULL;
