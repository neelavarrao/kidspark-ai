-- Create table to track which stories have been shown to which users
CREATE TABLE IF NOT EXISTS public.user_story_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) NOT NULL,
    story_id INTEGER REFERENCES public.stories(id) NOT NULL,
    shown_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    user_rating SMALLINT,  -- Optional: Allow users to rate stories (1-5)
    UNIQUE(user_id, story_id)  -- Prevent duplicate entries for the same story/user
);

-- Create index for faster lookups by user
CREATE INDEX IF NOT EXISTS idx_user_story_history_user_id ON public.user_story_history(user_id);

-- Create index for faster lookups by story
CREATE INDEX IF NOT EXISTS idx_user_story_history_story_id ON public.user_story_history(story_id);

-- Add row level security
ALTER TABLE public.user_story_history ENABLE ROW LEVEL SECURITY;

-- Create policy to allow users to see only their own history
CREATE POLICY user_story_history_policy ON public.user_story_history
    USING (auth.uid() = user_id);

-- Create view for analytics (admin access only)
CREATE OR REPLACE VIEW story_popularity AS
SELECT
    s.id,
    s.story_title,
    COUNT(ush.id) AS view_count,
    AVG(ush.user_rating) AS avg_rating,
    s.age_range_min,
    s.age_range_max
FROM
    public.stories s
LEFT JOIN
    public.user_story_history ush ON s.id = ush.story_id
GROUP BY
    s.id, s.story_title, s.age_range_min, s.age_range_max
ORDER BY
    view_count DESC;

-- Secure the view with RLS
ALTER VIEW story_popularity SECURITY INVOKER;