-- AI Personal Safety Assistant Schema

CREATE TABLE IF NOT EXISTS public.assistant_sessions (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    status VARCHAR(50) DEFAULT 'active', -- active, ended, escalated
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    last_known_lat DOUBLE PRECISION,
    last_known_lng DOUBLE PRECISION,
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS public.journey_monitoring (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES public.assistant_sessions(session_id) ON DELETE CASCADE,
    lat DOUBLE PRECISION NOT NULL,
    lng DOUBLE PRECISION NOT NULL,
    speed_kmh DOUBLE PRECISION,
    safety_score DOUBLE PRECISION,
    recorded_at TIMESTAMPTZ DEFAULT NOW(),
    environmental_context JSONB DEFAULT '{}'::jsonb -- weather, traffic, etc.
);

CREATE TABLE IF NOT EXISTS public.assistant_recommendations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES public.assistant_sessions(session_id) ON DELETE CASCADE,
    recommendation_text TEXT NOT NULL,
    context_trigger VARCHAR(255), -- e.g., 'weather', 'crime_zone'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    ai_confidence DOUBLE PRECISION,
    read_by_user BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS public.assistant_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES public.assistant_sessions(session_id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL, -- 'unexpected_stop', 'route_deviation'
    description TEXT,
    detected_at TIMESTAMPTZ DEFAULT NOW(),
    severity VARCHAR(50) -- 'low', 'medium', 'high'
);

CREATE TABLE IF NOT EXISTS public.journey_checkins (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES public.assistant_sessions(session_id) ON DELETE CASCADE,
    prompted_at TIMESTAMPTZ DEFAULT NOW(),
    responded_at TIMESTAMPTZ,
    response_status VARCHAR(50), -- 'safe', 'need_help', 'emergency', 'timeout'
    escalated BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS public.assistant_alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES public.assistant_sessions(session_id) ON DELETE CASCADE,
    alert_type VARCHAR(100) NOT NULL, -- 'auto_sos', 'trusted_contact_notify'
    triggered_at TIMESTAMPTZ DEFAULT NOW(),
    payload JSONB DEFAULT '{}'::jsonb
);

-- RLS Policies can be added below if needed
