-- Create chat_messages table
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users(id),
    content TEXT NOT NULL,
    sender VARCHAR(50) NOT NULL, -- 'user' or 'assistant'
    timestamp TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_user
        FOREIGN KEY(user_id)
        REFERENCES public.users(id)
        ON DELETE CASCADE
);1

-- Add row level security
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

-- Create policy to allow users to see only their own messages
CREATE POLICY chat_message_policy ON public.chat_messages
    USING (auth.uid() = user_id);

-- Allow users to insert their own messages
CREATE POLICY chat_message_insert_policy ON public.chat_messages
    FOR INSERT WITH CHECK (auth.uid() = user_id);