-- Migration: Add completion_date column to courses table
-- This migration adds a completion_date field to track when badges were earned
-- Date: 2025-01-XX

-- Add completion_date column to courses table
ALTER TABLE courses 
ADD COLUMN IF NOT EXISTS completion_date DATE;

-- Create index for performance
CREATE INDEX IF NOT EXISTS idx_courses_completion_date ON courses(completion_date);

-- Add comment
COMMENT ON COLUMN courses.completion_date IS 'Date when the badge was earned/completed (extracted from badge page)';

