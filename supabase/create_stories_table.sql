-- Create stories table with schema based on the JSON structure and add embedding column
CREATE TABLE stories (
  id SERIAL PRIMARY KEY,
  story_title TEXT NOT NULL,
  moral_lesson TEXT NOT NULL,
  lesson_summary TEXT NOT NULL,
  age_range_min INTEGER NOT NULL,
  age_range_max INTEGER NOT NULL,
  characters JSONB NOT NULL,
  setting TEXT NOT NULL,
  duration_minutes INTEGER NOT NULL,
  story_text TEXT NOT NULL,
  discussion_questions JSONB NOT NULL,
  embedding VECTOR(1536),  -- OpenAI embeddings are 1536 dimensions
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create a function to generate a vector from the text fields
CREATE OR REPLACE FUNCTION match_stories(query_embedding VECTOR(1536), match_threshold FLOAT, match_count INT)
RETURNS TABLE (
  id INT,
  story_title TEXT,
  moral_lesson TEXT,
  similarity FLOAT
)
LANGUAGE sql stable
AS $$
BEGIN
  SELECT
    stories.id,
    stories.story_title,
    stories.moral_lesson,
    1 - (stories.embedding <=> query_embedding) AS similarity
  FROM stories
  WHERE 1 - (stories.embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;

-- Create an index for faster similarity searches
CREATE INDEX ON stories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);