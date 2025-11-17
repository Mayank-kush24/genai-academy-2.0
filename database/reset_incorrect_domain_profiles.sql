-- Reset Skillboost profiles that failed due to "Incorrect Domain" error
-- These profiles likely have the new www.skills.google domain which is now supported

-- Step 1: Check how many profiles failed with domain error
SELECT 
    COUNT(*) as total_incorrect_domain,
    COUNT(CASE WHEN google_cloud_skills_boost_profile_link LIKE '%www.skills.google%' THEN 1 END) as new_domain_count,
    COUNT(CASE WHEN google_cloud_skills_boost_profile_link LIKE '%www.cloudskillsboost.google%' THEN 1 END) as old_domain_count
FROM skillboost_profile 
WHERE valid = FALSE 
AND remarks LIKE '%Incorrect Domain%';

-- Step 2: See sample profiles with the new domain
SELECT 
    email,
    google_cloud_skills_boost_profile_link,
    remarks,
    updated_at
FROM skillboost_profile 
WHERE valid = FALSE 
AND remarks LIKE '%Incorrect Domain%'
AND google_cloud_skills_boost_profile_link LIKE '%www.skills.google%'
LIMIT 10;

-- Step 3: Reset profiles with incorrect domain error to pending for re-verification
UPDATE skillboost_profile 
SET 
    valid = NULL, 
    remarks = NULL, 
    updated_at = CURRENT_TIMESTAMP 
WHERE valid = FALSE 
AND remarks LIKE '%Incorrect Domain%';

-- Step 4: Verify the reset
SELECT 
    COUNT(*) as profiles_reset_to_pending
FROM skillboost_profile 
WHERE valid IS NULL;

