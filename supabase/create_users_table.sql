-- Create users table
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add row level security
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Create policy to allow users to see only their own data
CREATE POLICY user_policy ON public.users
    USING (auth.uid() = id);

-- Allow anyone to register
CREATE POLICY user_insert_policy ON public.users
    FOR INSERT WITH CHECK (true);