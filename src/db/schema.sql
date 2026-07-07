-- Big-D-Agent — reference schema (kept in sync with src/db/models.py).
-- The app creates these automatically via SQLAlchemy on startup; this file is
-- for manual inspection / bootstrapping outside the app.

CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username    VARCHAR(255),
    plan        VARCHAR(32) NOT NULL DEFAULT 'free',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users (telegram_id);

CREATE TABLE IF NOT EXISTS tasks (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users (id),
    intent     VARCHAR(32) NOT NULL,
    skill      VARCHAR(64),
    prompt     TEXT NOT NULL,
    status     VARCHAR(16) NOT NULL DEFAULT 'done',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks (user_id);

CREATE TABLE IF NOT EXISTS schedules (
    id           SERIAL PRIMARY KEY,
    telegram_id  BIGINT NOT NULL,
    chat_id      BIGINT NOT NULL,
    prompt       TEXT NOT NULL,
    trigger_type VARCHAR(16) NOT NULL,   -- interval | daily | cron
    trigger_arg  VARCHAR(64) NOT NULL,
    active       BOOLEAN NOT NULL DEFAULT true,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_run     TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_schedules_telegram_id ON schedules (telegram_id);
