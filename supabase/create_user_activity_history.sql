-- Create user_activity_history table to track which activities have been shown to users
-- This prevents showing the same activity repeatedly

CREATE TABLE IF NOT EXISTS user_activity_history (
  id SERIAL PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  activity_id INT NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
  shown_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, activity_id)
);

-- Create index for faster lookups by user_id
CREATE INDEX IF NOT EXISTS idx_user_activity_history_user_id ON user_activity_history(user_id);

-- Create index for faster lookups by activity_id
CREATE INDEX IF NOT EXISTS idx_user_activity_history_activity_id ON user_activity_history(activity_id);

-- Enable Row Level Security
ALTER TABLE user_activity_history ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own activity history
CREATE POLICY "Users can view own activity history"
  ON user_activity_history
  FOR SELECT
  USING (auth.uid() = user_id);

-- Policy: Users can insert their own activity history
CREATE POLICY "Users can insert own activity history"
  ON user_activity_history
  FOR INSERT
  WITH CHECK (auth.uid() = user_id);

-- Grant necessary permissions
GRANT SELECT, INSERT ON user_activity_history TO authenticated;
GRANT USAGE, SELECT ON SEQUENCE user_activity_history_id_seq TO authenticated;
