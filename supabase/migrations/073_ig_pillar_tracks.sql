-- 073_ig_pillar_tracks.sql
-- Widen ig_posts.pillar to the three-track slide_specs contract.
--
-- The generator was rebuilt into three tracks (void = vision/method/example,
-- history, weekly). The 052 CHECK only allowed the retired launch pillars
-- ('receipt','method','history','brief','bts','heatmap'), so vision / example
-- / weekly inserts would fail. The new set matches IgPillar in
-- frontend/app/lib/supabase-server.ts exactly.
--
-- The union keeps the four retired labels valid so historical rows already in
-- the table do not violate the new constraint.

ALTER TABLE ig_posts DROP CONSTRAINT IF EXISTS ig_posts_pillar_check;

ALTER TABLE ig_posts
  ADD CONSTRAINT ig_posts_pillar_check
  CHECK (pillar IN (
    -- current three-track contract (IgPillar)
    'vision', 'method', 'example', 'history', 'weekly',
    -- retired launch pillars, kept valid for historical rows
    'receipt', 'brief', 'bts', 'heatmap'
  ));

COMMENT ON COLUMN ig_posts.slide_specs IS
  'Array of 3 slide spec objects (hook -> substance -> cta), discriminated by `kind` and matching the pillar template. See frontend/app/lib/supabase-server.ts SlideSpec: vision {kicker,headline,body,url}, method {axis_name,sample,score,lean_label,principle,url}, example {topic,headline,outlet_count,headlines[],url}, history {date,headline,perspectives[],url}, weekly {issue_number,headline,deck,stories[],url}.';
