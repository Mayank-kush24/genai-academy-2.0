-- ============================================
-- Migration: Update master_classes table for v2.0
-- Adds new columns for comprehensive master class tracking
-- ============================================

-- Add new columns to master_classes table
ALTER TABLE master_classes 
ADD COLUMN IF NOT EXISTS platform VARCHAR(100),
ADD COLUMN IF NOT EXISTS link TEXT,
ADD COLUMN IF NOT EXISTS total_duration INTEGER, -- in minutes
ADD COLUMN IF NOT EXISTS watched_duration_updated_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS watch_time INTEGER, -- in minutes
ADD COLUMN IF NOT EXISTS live BOOLEAN DEFAULT NULL, -- TRUE = valid, FALSE = invalid, NULL = not set
ADD COLUMN IF NOT EXISTS recorded BOOLEAN DEFAULT NULL; -- TRUE = valid, FALSE = invalid, NULL = not set

-- Add comments for clarity
COMMENT ON COLUMN master_classes.platform IS 'Platform where master class was hosted (e.g., YouTube, Zoom)';
COMMENT ON COLUMN master_classes.link IS 'Link to the master class recording/session';
COMMENT ON COLUMN master_classes.total_duration IS 'Total duration of master class in minutes';
COMMENT ON COLUMN master_classes.watched_duration_updated_at IS 'Timestamp when watch duration was last updated';
COMMENT ON COLUMN master_classes.watch_time IS 'Actual watch time by user in minutes';
COMMENT ON COLUMN master_classes.live IS 'Validation status for live attendance: TRUE = verified live, FALSE = invalid, NULL = pending';
COMMENT ON COLUMN master_classes.recorded IS 'Validation status for recorded viewing: TRUE = verified recorded, FALSE = invalid, NULL = pending';
COMMENT ON COLUMN master_classes.valid IS 'Deprecated - use live or recorded instead';

-- Add index for live/recorded filtering
CREATE INDEX IF NOT EXISTS idx_master_classes_live ON master_classes(live) WHERE live IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_master_classes_recorded ON master_classes(recorded) WHERE recorded IS NOT NULL;

-- Update existing records to have NULL for new columns (they're already NULL by default)
UPDATE master_classes 
SET 
    live = NULL,
    recorded = NULL
WHERE live IS NULL AND recorded IS NULL;

COMMENT ON TABLE master_classes IS 'Master class attendance tracking with live and recorded validation';

