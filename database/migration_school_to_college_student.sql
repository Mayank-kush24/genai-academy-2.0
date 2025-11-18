-- Migration: Consolidate SCHOOL_STUDENT to COLLEGE_STUDENT
-- This migration updates all records with occupation = 'SCHOOL_STUDENT' to 'COLLEGE_STUDENT'
-- Date: 2025-01-XX

-- Update all user_pii records
UPDATE user_pii 
SET occupation = 'COLLEGE_STUDENT',
    updated_at = CURRENT_TIMESTAMP
WHERE occupation = 'SCHOOL_STUDENT';

-- Show summary of changes
SELECT 
    'Before migration' as status,
    COUNT(*) as school_student_count
FROM user_pii 
WHERE occupation = 'SCHOOL_STUDENT'
UNION ALL
SELECT 
    'After migration' as status,
    COUNT(*) as college_student_count
FROM user_pii 
WHERE occupation = 'COLLEGE_STUDENT';

-- Verify no SCHOOL_STUDENT records remain
SELECT 
    CASE 
        WHEN COUNT(*) = 0 THEN 'Migration successful: No SCHOOL_STUDENT records found'
        ELSE 'WARNING: ' || COUNT(*) || ' SCHOOL_STUDENT records still exist'
    END as migration_status
FROM user_pii 
WHERE occupation = 'SCHOOL_STUDENT';

