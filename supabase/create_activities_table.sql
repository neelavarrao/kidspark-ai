-- Create activities table with schema based on the JSON structure
CREATE TABLE activities (
  id SERIAL PRIMARY KEY,
  activity_name TEXT NOT NULL,
  activity_category TEXT NOT NULL,
  materials JSONB NOT NULL,
  age_range_min INTEGER NOT NULL,
  age_range_max INTEGER NOT NULL,
  duration_minutes INTEGER NOT NULL,
  prep_time_minutes INTEGER NOT NULL,
  description TEXT NOT NULL,
  parent_instruction TEXT NOT NULL,
  variations JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);