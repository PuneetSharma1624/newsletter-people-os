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
