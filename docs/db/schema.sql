-- ============================================================
-- SynQ Database Schema
-- PostgreSQL / Supabase
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- STOCKS
-- Reference table for ticker metadata and validation
-- ============================================================
CREATE TABLE stocks (
    ticker TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    sector TEXT,
    industry TEXT,
    market_cap BIGINT,
    exchange TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_price FLOAT,
    last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- PROFILES
-- Extends Supabase auth.users with app-specific data
-- ============================================================
CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    full_name TEXT,
    subscription_tier TEXT NOT NULL DEFAULT 'free'
        CHECK (subscription_tier IN ('free', 'pro', 'elite')),
    analyses_used_today INT NOT NULL DEFAULT 0,
    analyses_reset_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Auto-create profile on signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, full_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ============================================================
-- ANALYSES
-- Stock analysis results (async job with three-layer output)
-- ============================================================
CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL REFERENCES stocks(ticker),
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),

    -- Layer 1: Agent Analysis
    agent_result JSONB,  -- { fundamental: {...}, sentiment: {...}, news: {...} }

    -- Layer 2: GraphRAG
    graphrag_result JSONB,  -- { entities: [...], relationships: [...], report: "..." }

    -- Layer 3: Swing Indicator
    indicator_result JSONB,  -- { momentum: {...}, volume: {...}, structure: {...}, signal: "..." }

    -- Confluence
    confluence_score FLOAT CHECK (confluence_score >= 0 AND confluence_score <= 100),
    signal TEXT CHECK (signal IN ('strong_buy', 'buy', 'neutral', 'sell', 'strong_sell')),

    -- Metadata
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processing_started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ
);

-- Fast lookups for watchlist and history
CREATE INDEX idx_analyses_user_id ON analyses(user_id);
CREATE INDEX idx_analyses_ticker ON analyses(ticker);
CREATE INDEX idx_analyses_user_ticker ON analyses(user_id, ticker);
CREATE INDEX idx_analyses_created_at ON analyses(created_at DESC);

-- ============================================================
-- WATCHLIST
-- Tracked stocks with alert thresholds
-- ============================================================
CREATE TABLE watchlist (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL REFERENCES stocks(ticker),
    notes TEXT,
    alert_threshold FLOAT DEFAULT 10.0,  -- notify when score changes by this much
    last_analyzed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One entry per ticker per user
    CONSTRAINT unique_user_ticker UNIQUE (user_id, ticker)
);

CREATE INDEX idx_watchlist_user_id ON watchlist(user_id);

-- ============================================================
-- ALERTS
-- Notification rules
-- ============================================================
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL REFERENCES stocks(ticker),
    alert_type TEXT NOT NULL
        CHECK (alert_type IN (
            'score_change',      -- confluence score changes by threshold
            'signal_change',     -- signal flips (buy <-> sell)
            'price_target',      -- price hits target
            'earnings_warning',  -- earnings approaching
            'news_spike'         -- unusual news activity
        )),
    threshold FLOAT,  -- for score_change: minimum change to trigger
    target_price FLOAT,  -- for price_target: the target price
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alerts_user_id ON alerts(user_id);
CREATE INDEX idx_alerts_ticker ON alerts(ticker);
CREATE INDEX idx_alerts_active ON alerts(is_active) WHERE is_active = TRUE;

-- ============================================================
-- ANALYSIS SNAPSHOTS
-- Historical confluence scores for backtesting
-- ============================================================
CREATE TABLE analysis_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL REFERENCES stocks(ticker),
    confluence_score FLOAT NOT NULL,
    signal TEXT NOT NULL,
    agent_score FLOAT,
    graphrag_score FLOAT,
    indicator_score FLOAT,
    snapshot_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_snapshots_ticker ON analysis_snapshots(ticker);
CREATE INDEX idx_snapshots_time ON analysis_snapshots(snapshot_at DESC);

-- ============================================================
-- ROW LEVEL SECURITY
-- Users can only see their own data
-- ============================================================
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE watchlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_snapshots ENABLE ROW LEVEL SECURITY;

-- Stocks: public read, admin write (or service role)
ALTER TABLE stocks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Anyone can view stocks"
    ON stocks FOR SELECT
    USING (true);

-- Profiles: users can read/update their own
CREATE POLICY "Users can view own profile"
    ON profiles FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile"
    ON profiles FOR UPDATE
    USING (auth.uid() = id);

-- Analyses: users can CRUD their own
CREATE POLICY "Users can view own analyses"
    ON analyses FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can create own analyses"
    ON analyses FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own analyses"
    ON analyses FOR UPDATE
    USING (auth.uid() = user_id);

-- Watchlist: users can CRUD their own
CREATE POLICY "Users can view own watchlist"
    ON watchlist FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own watchlist"
    ON watchlist FOR ALL
    USING (auth.uid() = user_id);

-- Alerts: users can CRUD their own
CREATE POLICY "Users can view own alerts"
    ON alerts FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can manage own alerts"
    ON alerts FOR ALL
    USING (auth.uid() = user_id);

-- Snapshots: users can read their own
CREATE POLICY "Users can view own snapshots"
    ON analysis_snapshots FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM analyses
            WHERE analyses.id = analysis_snapshots.analysis_id
            AND analyses.user_id = auth.uid()
        )
    );

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Update updated_at on profile changes
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER watchlist_updated_at
    BEFORE UPDATE ON watchlist
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Check and increment daily analysis count
CREATE OR REPLACE FUNCTION check_analysis_limit()
RETURNS TRIGGER AS $$
DECLARE
    daily_limit INT;
    current_count INT;
BEGIN
    -- Set limit based on tier
    SELECT CASE
        WHEN subscription_tier = 'free' THEN 5
        WHEN subscription_tier = 'pro' THEN 100
        WHEN subscription_tier = 'elite' THEN 999
        ELSE 5
    END INTO daily_limit
    FROM profiles WHERE id = NEW.user_id;

    -- Reset counter if day has passed
    UPDATE profiles
    SET analyses_used_today = 0,
        analyses_reset_at = NOW()
    WHERE id = NEW.user_id
    AND analyses_reset_at < NOW() - INTERVAL '1 day';

    -- Get current count
    SELECT analyses_used_today INTO current_count
    FROM profiles WHERE id = NEW.user_id;

    -- Check limit
    IF current_count >= daily_limit THEN
        RAISE EXCEPTION 'Daily analysis limit reached for % tier', (
            SELECT subscription_tier FROM profiles WHERE id = NEW.user_id
        );
    END IF;

    -- Increment counter
    UPDATE profiles
    SET analyses_used_today = analyses_used_today + 1
    WHERE id = NEW.user_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER check_analysis_limit
    BEFORE INSERT ON analyses
    FOR EACH ROW EXECUTE FUNCTION check_analysis_limit();
