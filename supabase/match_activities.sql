-- Function for activity matching with optional filtering by age, duration, and category
-- This function returns activities matching the given criteria

CREATE OR REPLACE FUNCTION match_activities(
  child_age INT DEFAULT NULL,
  max_duration INT DEFAULT NULL,
  category TEXT DEFAULT NULL,
  match_count INT DEFAULT 10
)
RETURNS TABLE (
  id INT,
  activity_name TEXT,
  activity_category TEXT,
  materials JSONB,
  age_range_min INT,
  age_range_max INT,
  duration_minutes INT,
  prep_time_minutes INT,
  description TEXT,
  parent_instruction TEXT,
  variations JSONB
)
LANGUAGE plpgsql
STABLE
AS $$
BEGIN
  RETURN QUERY
  SELECT
    a.id,
    a.activity_name,
    a.activity_category,
    a.materials,
    a.age_range_min,
    a.age_range_max,
    a.duration_minutes,
    a.prep_time_minutes,
    a.description,
    a.parent_instruction,
    a.variations
  FROM activities a
  WHERE
    -- Age filter: child's age must fall within activity's age range
    (child_age IS NULL OR (a.age_range_min <= child_age AND a.age_range_max >= child_age))
    -- Duration filter: activity duration must be at or below max
    AND (max_duration IS NULL OR a.duration_minutes <= max_duration)
    -- Category filter: activity must match specified category
    AND (category IS NULL OR a.activity_category = category)
  ORDER BY RANDOM()  -- Randomize results for variety
  LIMIT match_count;
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION match_activities TO authenticated;
GRANT EXECUTE ON FUNCTION match_activities TO anon;
