-- Create tables for KidSpark AI agent system

-- Table for storing agent traces
CREATE TABLE IF NOT EXISTS public.agent_traces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id VARCHAR(255) NOT NULL,  -- Session/conversation ID
    agent_id VARCHAR(255) NOT NULL, -- Which agent generated this trace
    user_id UUID REFERENCES public.users(id),
    message_type VARCHAR(50) NOT NULL, -- 'human', 'ai', 'tool', etc.
    failure_mode VARCHAR(50),          -- If the agent hit a guardrail
    tool_call_info JSONB,              -- Tools called if any
    content TEXT NOT NULL,             -- Message content
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_traces_run_id ON public.agent_traces(run_id);
CREATE INDEX IF NOT EXISTS idx_agent_traces_user_id ON public.agent_traces(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_traces_agent_id ON public.agent_traces(agent_id);

-- Add row level security
ALTER TABLE public.agent_traces ENABLE ROW LEVEL SECURITY;

-- Create policy to allow users to see only their own traces
CREATE POLICY agent_traces_policy ON public.agent_traces
    USING (auth.uid() = user_id);

-- Table for storing intent detection logs
CREATE TABLE IF NOT EXISTS public.intent_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id VARCHAR(255) NOT NULL,
    user_id UUID REFERENCES public.users(id),
    primary_intent VARCHAR(50) NOT NULL,
    confidence FLOAT NOT NULL,
    detection_method VARCHAR(50) NOT NULL,
    raw_input TEXT NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_intent_logs_user_id ON public.intent_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_intent_logs_primary_intent ON public.intent_logs(primary_intent);

-- Add row level security
ALTER TABLE public.intent_logs ENABLE ROW LEVEL SECURITY;

-- Create policy to allow users to see only their own intent logs
CREATE POLICY intent_logs_policy ON public.intent_logs
    USING (auth.uid() = user_id);