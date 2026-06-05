-- PeopleOS Brief — Supabase Schema v2
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New Query)
-- If upgrading from v1, see MIGRATION section at the bottom.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- TABLE: subscribers
-- ============================================================
CREATE TABLE IF NOT EXISTS subscribers (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email              TEXT NOT NULL UNIQUE,
    status             TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'unsubscribed')),
    unsubscribe_token  TEXT NOT NULL UNIQUE,
    source             TEXT,
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    updated_at         TIMESTAMPTZ DEFAULT NOW(),
    unsubscribed_at    TIMESTAMPTZ
);

-- ============================================================
-- TABLE: newsletter_issues
-- Stores one row per date. sections JSONB holds structured content.
-- ============================================================
CREATE TABLE IF NOT EXISTS newsletter_issues (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_date        DATE NOT NULL UNIQUE,
    subject           TEXT NOT NULL,
    preheader         TEXT,
    executive_summary TEXT,
    html              TEXT NOT NULL,
    text              TEXT NOT NULL,
    sections          JSONB NOT NULL DEFAULT '[]'::jsonb,
    sources           JSONB,
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    sent_at           TIMESTAMPTZ
);

-- ============================================================
-- TABLE: send_log
-- ============================================================
CREATE TABLE IF NOT EXISTS send_log (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    issue_id            UUID REFERENCES newsletter_issues(id) ON DELETE CASCADE,
    subscriber_id       UUID REFERENCES subscribers(id) ON DELETE CASCADE,
    issue_date          DATE,
    send_type           TEXT NOT NULL DEFAULT 'live' CHECK (send_type IN ('live', 'test')),
    email               TEXT NOT NULL,
    status              TEXT NOT NULL CHECK (status IN ('sent', 'failed', 'skipped')),
    resend_message_id   TEXT,
    error_message       TEXT,
    sent_at             TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (issue_id, subscriber_id)
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_subscribers_email             ON subscribers (email);
CREATE INDEX IF NOT EXISTS idx_subscribers_unsubscribe_token ON subscribers (unsubscribe_token);
CREATE INDEX IF NOT EXISTS idx_subscribers_status            ON subscribers (status);
CREATE INDEX IF NOT EXISTS idx_newsletter_issues_date        ON newsletter_issues (issue_date);
CREATE INDEX IF NOT EXISTS idx_newsletter_issues_sent_at     ON newsletter_issues (sent_at);
CREATE INDEX IF NOT EXISTS idx_send_log_issue_id             ON send_log (issue_id);
CREATE INDEX IF NOT EXISTS idx_send_log_subscriber_id        ON send_log (subscriber_id);

-- ============================================================
-- FUNCTION: upsert_subscriber
-- ============================================================
CREATE OR REPLACE FUNCTION upsert_subscriber(
    p_email TEXT,
    p_token TEXT,
    p_source TEXT DEFAULT NULL
) RETURNS TABLE (
    subscriber_id UUID,
    is_new BOOLEAN,
    was_reactivated BOOLEAN,
    already_active BOOLEAN
) LANGUAGE plpgsql AS $$
DECLARE
    v_existing subscribers%ROWTYPE;
BEGIN
    SELECT * INTO v_existing FROM subscribers WHERE email = p_email;
    IF NOT FOUND THEN
        INSERT INTO subscribers (email, unsubscribe_token, source)
        VALUES (p_email, p_token, p_source)
        RETURNING id INTO v_existing.id;
        RETURN QUERY SELECT v_existing.id, TRUE, FALSE, FALSE;
    ELSIF v_existing.status = 'unsubscribed' THEN
        UPDATE subscribers
        SET status = 'active', unsubscribe_token = p_token,
            updated_at = NOW(), unsubscribed_at = NULL
        WHERE id = v_existing.id;
        RETURN QUERY SELECT v_existing.id, FALSE, TRUE, FALSE;
    ELSE
        RETURN QUERY SELECT v_existing.id, FALSE, FALSE, TRUE;
    END IF;
END;
$$;

-- ============================================================
-- RLS NOTES
-- ============================================================
-- RLS is intentionally disabled for MVP.
-- Service role key bypasses RLS. Frontend never touches Supabase directly.
-- To enable RLS later:
--   ALTER TABLE subscribers ENABLE ROW LEVEL SECURITY;
--   ALTER TABLE newsletter_issues ENABLE ROW LEVEL SECURITY;
--   ALTER TABLE send_log ENABLE ROW LEVEL SECURITY;

-- ============================================================
-- MIGRATION: Upgrading from v1
-- Run ONLY if you already have newsletter_issues from v1.
-- ============================================================
-- ALTER TABLE newsletter_issues ADD COLUMN IF NOT EXISTS sections JSONB NOT NULL DEFAULT '[]'::jsonb;
-- ALTER TABLE newsletter_issues ADD COLUMN IF NOT EXISTS executive_summary TEXT;
-- UPDATE newsletter_issues SET sections = '[]'::jsonb WHERE sections IS NULL;

-- ============================================================
-- MIGRATION v3: Analytics & Admin Notifications (idempotent)
-- Run in Supabase SQL Editor to enable visitor counters,
-- subscriber notifications, and admin subscriber list.
-- ============================================================

-- Add missing columns to subscribers (safe — IF NOT EXISTS)
ALTER TABLE public.subscribers ADD COLUMN IF NOT EXISTS last_email_sent_at TIMESTAMPTZ;

-- TABLE: site_analytics (visit events, no raw PII)
CREATE TABLE IF NOT EXISTS public.site_analytics (
    id               BIGSERIAL PRIMARY KEY,
    event_type       TEXT NOT NULL,
    page_path        TEXT,
    referrer         TEXT,
    user_agent_hash  TEXT,
    visitor_hash     TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_site_analytics_event_type  ON public.site_analytics (event_type);
CREATE INDEX IF NOT EXISTS idx_site_analytics_created_at  ON public.site_analytics (created_at);
CREATE INDEX IF NOT EXISTS idx_site_analytics_visitor     ON public.site_analytics (visitor_hash);

-- TABLE: admin_notification_state (single-row state for bell badge)
CREATE TABLE IF NOT EXISTS public.admin_notification_state (
    id                       TEXT PRIMARY KEY,
    last_seen_subscriber_at  TIMESTAMPTZ,
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed default state row (upsert-safe)
INSERT INTO public.admin_notification_state (id, last_seen_subscriber_at)
VALUES ('default', NOW())
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- MIGRATION v4: send_log issue_date + send_type (idempotent)
-- ============================================================
ALTER TABLE public.send_log ADD COLUMN IF NOT EXISTS issue_date DATE;
ALTER TABLE public.send_log ADD COLUMN IF NOT EXISTS send_type TEXT NOT NULL DEFAULT 'live'
    CHECK (send_type IN ('live', 'test'));

CREATE INDEX IF NOT EXISTS idx_send_log_issue_date ON public.send_log (issue_date);
CREATE INDEX IF NOT EXISTS idx_send_log_send_type  ON public.send_log (send_type);

-- Backfill issue_date from newsletter_issues join
UPDATE public.send_log sl
SET issue_date = ni.issue_date
FROM public.newsletter_issues ni
WHERE sl.issue_id = ni.id AND sl.issue_date IS NULL;

-- ============================================================
-- MIGRATION v5: Action logs (idempotent)
-- Run in Supabase SQL Editor to enable admin action logging.
-- ============================================================
CREATE TABLE IF NOT EXISTS public.action_logs (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_name      TEXT NOT NULL,
    action_type      TEXT,
    status           TEXT NOT NULL,
    request_payload  JSONB,
    response_payload JSONB,
    error_message    TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_action_logs_action_name ON public.action_logs (action_name);
CREATE INDEX IF NOT EXISTS idx_action_logs_created_at  ON public.action_logs (created_at);
CREATE INDEX IF NOT EXISTS idx_action_logs_status      ON public.action_logs (status);
