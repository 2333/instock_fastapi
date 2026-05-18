BEGIN;

ALTER TABLE stocks
    ADD COLUMN IF NOT EXISTS industry_label VARCHAR(50),
    ADD COLUMN IF NOT EXISTS industry_taxonomy VARCHAR(80),
    ADD COLUMN IF NOT EXISTS industry_source VARCHAR(20),
    ADD COLUMN IF NOT EXISTS industry_updated_at TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE daily_bars
    ADD COLUMN IF NOT EXISTS source VARCHAR(20);

ALTER TABLE attention
    ADD COLUMN IF NOT EXISTS "group" VARCHAR(50),
    ADD COLUMN IF NOT EXISTS notes TEXT,
    ADD COLUMN IF NOT EXISTS alert_conditions JSONB;

ALTER TABLE attention
    ALTER COLUMN "group" SET DEFAULT 'watch';

UPDATE attention
SET "group" = 'watch'
WHERE "group" IS NULL;

ALTER TABLE attention
    ALTER COLUMN "group" SET NOT NULL;

ALTER TABLE user_events
    ADD COLUMN IF NOT EXISTS event_version INTEGER;

UPDATE user_events
SET event_version = 1
WHERE event_version IS NULL;

ALTER TABLE user_events
    ALTER COLUMN event_version SET DEFAULT 1,
    ALTER COLUMN event_version SET NOT NULL,
    ALTER COLUMN page TYPE VARCHAR(120),
    ALTER COLUMN referrer TYPE VARCHAR(255);

CREATE INDEX IF NOT EXISTS ix_user_events_event_type_created
    ON user_events (event_type, created_at);

COMMIT;
