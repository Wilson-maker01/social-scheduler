-- Social Media Scheduler schema

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE social_accounts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL CHECK (platform IN ('twitter', 'instagram', 'facebook', 'linkedin')),
    platform_account_id TEXT NOT NULL,
    display_name TEXT,
    access_token_encrypted TEXT NOT NULL,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (platform, platform_account_id)
);

CREATE TABLE posts (
    id SERIAL PRIMARY KEY,
    social_account_id INTEGER REFERENCES social_accounts(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    media_type TEXT CHECK (media_type IN ('none', 'image', 'video', 'carousel')) DEFAULT 'none',
    media_urls TEXT[],
    hashtags TEXT[],
    link_url TEXT,
    scheduled_time TIMESTAMPTZ NOT NULL,
    status TEXT CHECK (status IN ('scheduled', 'publishing', 'published', 'failed', 'cancelled')) DEFAULT 'scheduled',
    predicted_engagement FLOAT,
    prediction_source TEXT CHECK (prediction_source IN ('heuristic', 'model')),
    model_version_id INTEGER,
    platform_post_id TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    published_at TIMESTAMPTZ
);

CREATE INDEX idx_posts_scheduled ON posts (status, scheduled_time);

CREATE TABLE post_metrics (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES posts(id) ON DELETE CASCADE,
    measured_offset_hours INTEGER NOT NULL, -- e.g. 1, 24, 168
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    engagement_score FLOAT, -- normalized composite metric, used as ML target
    measured_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (post_id, measured_offset_hours)
);

CREATE TABLE model_versions (
    id SERIAL PRIMARY KEY,
    social_account_id INTEGER REFERENCES social_accounts(id) ON DELETE CASCADE,
    trained_at TIMESTAMPTZ DEFAULT now(),
    training_rows INTEGER,
    validation_mae FLOAT,
    heuristic_mae FLOAT, -- baseline comparison at training time
    promoted BOOLEAN DEFAULT false,
    artifact_path TEXT NOT NULL
);
