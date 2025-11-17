-- Migration: Change degree_passout_year from INTEGER to TEXT
-- This allows storing full degree information including the year
-- e.g., "Bachelor of Technology (B.Tech)( 2028 )"

ALTER TABLE user_pii 
ALTER COLUMN degree_passout_year TYPE TEXT;

-- Optional: If you want to rename the column to be more descriptive
-- ALTER TABLE user_pii RENAME COLUMN degree_passout_year TO degree_info;

COMMENT ON COLUMN user_pii.degree_passout_year IS 'Degree information including name and passout year';

