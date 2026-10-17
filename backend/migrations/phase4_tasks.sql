-- Phase 4: optional manual run (the app also does this automatically at startup).
-- Safe to run more than once. PostgreSQL / Neon.
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS requirement_id  VARCHAR(40);
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS estimate_points INTEGER;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS depends_on      JSON;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS srs_id          INTEGER;
