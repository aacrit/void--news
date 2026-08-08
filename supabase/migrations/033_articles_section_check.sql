-- Fix articles section check constraint to allow europe and south-asia editions
ALTER TABLE articles
    DROP CONSTRAINT IF EXISTS articles_section_check;

ALTER TABLE articles
    ADD CONSTRAINT articles_section_check
    CHECK (section IN ('world', 'us', 'europe', 'south-asia', 'uk', 'india', 'canada'));
