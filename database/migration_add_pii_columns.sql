-- Migration: Add 5 new PII columns to user_pii table
-- Date: 2026-01-21
-- Columns: organization_name, class_stream (update), domain, designation_years_exp, degree_passout_year (update)

-- Add organization_name column (College/School/Company/Startup Name)
ALTER TABLE user_pii 
ADD COLUMN IF NOT EXISTS organization_name VARCHAR(1000);

-- Update class_stream column to VARCHAR(1000) if it exists, otherwise add it
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_pii' AND column_name = 'class_stream') THEN
        ALTER TABLE user_pii ALTER COLUMN class_stream TYPE VARCHAR(1000);
    ELSE
        ALTER TABLE user_pii ADD COLUMN class_stream VARCHAR(1000);
    END IF;
END $$;

-- Add domain column
ALTER TABLE user_pii 
ADD COLUMN IF NOT EXISTS domain VARCHAR(1000);

-- Add designation_years_exp column (Designation with Year of experience)
ALTER TABLE user_pii 
ADD COLUMN IF NOT EXISTS designation_years_exp VARCHAR(1000);

-- Update degree_passout_year column to VARCHAR(1000) if it exists, otherwise add it
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'user_pii' AND column_name = 'degree_passout_year') THEN
        ALTER TABLE user_pii ALTER COLUMN degree_passout_year TYPE VARCHAR(1000);
    ELSE
        ALTER TABLE user_pii ADD COLUMN degree_passout_year VARCHAR(1000);
    END IF;
END $$;

-- Add indexes for new columns (optional, for faster queries)
CREATE INDEX IF NOT EXISTS idx_user_pii_organization ON user_pii(organization_name);
CREATE INDEX IF NOT EXISTS idx_user_pii_domain ON user_pii(domain);

-- Verify columns were added
SELECT column_name, data_type, character_maximum_length 
FROM information_schema.columns 
WHERE table_name = 'user_pii' 
AND column_name IN ('organization_name', 'class_stream', 'domain', 'designation_years_exp', 'degree_passout_year');

-- Comments on new columns
COMMENT ON COLUMN user_pii.organization_name IS 'College/School/Company/Startup Name';
COMMENT ON COLUMN user_pii.class_stream IS 'Class or Stream of study';
COMMENT ON COLUMN user_pii.domain IS 'Domain of expertise or study';
COMMENT ON COLUMN user_pii.designation_years_exp IS 'Designation with years of experience';
COMMENT ON COLUMN user_pii.degree_passout_year IS 'Degree name with passout year';

