-- Enhanced function for story matching with full data and optional age filtering
-- This function returns complete story data for reranking by the StoryAgent

CREATE OR REPLACE FUNCTION match_stories_enhanced(
  query_embedding VECTOR(1536),
  match_threshold FLOAT DEFAULT 0.7,
  match_count INT DEFAULT 5,
  min_age INT DEFAULT NULL,
  max_age INT DEFAULT NULL
)
RETURNS TABLE (
  id INT,
  story_title TEXT,
  moral_lesson TEXT,
  lesson_summary TEXT,
  age_range_min INT,
  age_range_max INT,
  characters JSONB,
  setting TEXT,
  duration_minutes INT,
  story_text TEXT,
  discussion_questions JSONB,
  similarity FLOAT
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  RETURN QUERY
  SELECT
    s.id,
    s.story_title,
    s.moral_lesson,
    s.lesson_summary,
    s.age_range_min,
    s.age_range_max,
    s.characters,
    s.setting,
    s.duration_minutes,
    s.story_text,
    s.discussion_questions,
    1 - (s.embedding <=> query_embedding) AS similarity
  FROM stories s
  WHERE
    1 - (s.embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION match_stories_enhanced TO authenticated;
GRANT EXECUTE ON FUNCTION match_stories_enhanced TO anon;
