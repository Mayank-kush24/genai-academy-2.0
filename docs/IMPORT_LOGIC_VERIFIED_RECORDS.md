# Import Logic: Protecting Verified Records

## Overview
Special import logic implemented for `courses` and `skillboost_profile` tables to prevent overwriting already-verified records.

---

## 🎯 The Problem
- Users might submit multiple badge/profile links over time
- Once a link is verified as `valid = TRUE`, we don't want to overwrite it with a potentially invalid new submission
- But if a link failed verification (`valid = FALSE`), we want to allow users to resubmit with a corrected link

---

## ✅ The Solution

### **For Both Tables: `courses` and `skillboost_profile`**

**Rule:** Only update records that are **unverified** or **failed verification**

```python
IF existing record has valid = TRUE:
    → Skip update (keep the verified record)
    → Log: "Skipped: Already verified as valid"

ELSE IF existing record has valid = FALSE or NULL:
    → Allow update (accept the latest submission)
    → Reset valid = NULL and remarks = NULL for re-verification
```

---

## 📊 Detailed Logic

### **1. Course Badges (`courses` table)**

**Composite Primary Key:** `(email, problem_statement)`

```python
def _import_course(session, row_dict):
    # 1. Check by composite primary key
    existing = session.query(Course).filter_by(
        email=row_dict['email'],
        problem_statement=row_dict['problem_statement']
    ).first()
    
    # 2. If record exists
    if existing:
        # 2a. Check verification status
        if existing.valid is True:
            # ✗ Already verified - don't update
            skip_record()
            log("[DEBUG IMPORT] Skipped course badge: Already verified as valid")
            return
        
        # 2b. Failed or pending verification - allow update
        if operation_mode in ['update', 'create_update']:
            update_record(row_dict)
            # Reset validation for re-verification
            existing.valid = None
            existing.remarks = None
            existing.updated_at = NOW
    
    # 3. If record doesn't exist - create new
    else:
        if operation_mode in ['create', 'create_update']:
            create_new_record(row_dict)
```

### **2. Skillboost Profiles (`skillboost_profile` table)**

**Composite Primary Key:** `(email, google_cloud_skills_boost_profile_link)`

```python
def _import_skillboost_profile(session, row_dict):
    # 1. Check by composite primary key
    existing = session.query(SkillboostProfile).filter_by(
        email=row_dict['email'],
        google_cloud_skills_boost_profile_link=row_dict['google_cloud_skills_boost_profile_link']
    ).first()
    
    # 2. If record exists
    if existing:
        # 2a. Check verification status
        if existing.valid is True:
            # ✗ Already verified - don't update
            skip_record()
            log("[DEBUG IMPORT] Skipped skillboost profile: Already verified as valid")
            return
        
        # 2b. Failed or pending verification - allow update
        if operation_mode in ['update', 'create_update']:
            update_record(row_dict)
            # Reset validation for re-verification
            existing.valid = None
            existing.remarks = None
            existing.updated_at = NOW
    
    # 3. If record doesn't exist - create new
    else:
        if operation_mode in ['create', 'create_update']:
            create_new_record(row_dict)
```

---

## 📋 Example Scenarios

### **Scenario 1: New Submission (No existing record)**
```
CSV Data:
  email: user@example.com
  problem_statement: "Build a Website"
  badge_link: "https://www.skills.google/badge/abc123"

Database: No existing record

Result: ✅ CREATE new record
Status: valid = NULL (pending verification)
```

---

### **Scenario 2: Re-submission with Failed Link (valid = FALSE)**
```
Existing Record:
  email: user@example.com
  problem_statement: "Build a Website"
  badge_link: "https://www.skills.google/badge/wrong-link"
  valid: FALSE
  remarks: "Badge not found or inaccessible"

CSV Data (new submission):
  email: user@example.com
  problem_statement: "Build a Website"
  badge_link: "https://www.skills.google/badge/corrected-link"

Result: ✅ UPDATE record with new link
Action:
  - Update badge_link to new URL
  - Reset valid = NULL
  - Reset remarks = NULL
  - Set updated_at = NOW
Reason: Previous link failed, allow user to submit corrected link
```

---

### **Scenario 3: Re-submission with Verified Link (valid = TRUE)**
```
Existing Record:
  email: user@example.com
  problem_statement: "Build a Website"
  badge_link: "https://www.skills.google/badge/verified-link"
  valid: TRUE
  remarks: "Valid Badge"

CSV Data (new submission):
  email: user@example.com
  problem_statement: "Build a Website"
  badge_link: "https://www.skills.google/badge/new-link"

Result: ✗ SKIP (do not update)
Log: "[DEBUG IMPORT] Skipped course badge for user@example.com: Already verified as valid"
Reason: Keep the already-verified link, ignore new submission
```

---

### **Scenario 4: Pending Verification (valid = NULL)**
```
Existing Record:
  email: user@example.com
  problem_statement: "Build a Website"
  badge_link: "https://www.skills.google/badge/pending-link"
  valid: NULL
  remarks: NULL

CSV Data (new submission):
  email: user@example.com
  problem_statement: "Build a Website"
  badge_link: "https://www.skills.google/badge/updated-link"

Result: ✅ UPDATE record with new link
Action:
  - Update badge_link to new URL
  - Keep valid = NULL
  - Keep remarks = NULL
  - Set updated_at = NOW
Reason: Not yet verified, allow user to submit updated link
```

---

### **Scenario 5: Different Problem Statement (Different Primary Key)**
```
Existing Record:
  email: user@example.com
  problem_statement: "Build a Website"
  badge_link: "https://www.skills.google/badge/link-1"
  valid: TRUE

CSV Data (new submission):
  email: user@example.com
  problem_statement: "Build a Mobile App"  ← Different!
  badge_link: "https://www.skills.google/badge/link-2"

Result: ✅ CREATE new record
Reason: Different problem_statement means different primary key
This is a separate course badge, not an update to the existing one
```

---

## 🔍 Key Points

### **1. Composite Primary Keys**
Both tables use composite primary keys:
- **Courses:** `(email, problem_statement)`
- **Skillboost Profile:** `(email, google_cloud_skills_boost_profile_link)`

### **2. Verification Protection**
- `valid = TRUE` → **Protected** (cannot be updated)
- `valid = FALSE` → **Updatable** (allow corrections)
- `valid = NULL` → **Updatable** (pending verification)

### **3. Validation Reset on Update**
When updating failed/pending records:
- Reset `valid = NULL`
- Reset `remarks = NULL`
- Update `updated_at = NOW`

This ensures the new link will be re-verified by the verification script.

### **4. Email Normalization**
All emails are normalized:
```python
row_dict['email'] = str(row_dict['email']).strip().lower()
```

### **5. Debug Logging**
Import process logs when verified records are skipped:
```
[DEBUG IMPORT] Skipped course badge for user@example.com: Already verified as valid
[DEBUG IMPORT] Skipped skillboost profile for user@example.com: Already verified as valid
```

---

## 📊 Import Statistics

The import stats will reflect this logic:

```
Import Results:
  Created: 250 records    ← New submissions
  Updated: 150 records    ← Failed/pending re-submissions
  Skipped: 100 records    ← Already verified + operation mode restrictions
  Errors: 5 records       ← Data validation errors
```

**Note:** "Skipped" includes:
- Records with `valid = TRUE` (protected)
- Records excluded by operation mode (e.g., 'create' mode skips existing records)
- Records with missing required fields

---

## 🔄 Workflow Example

### **Complete User Journey:**

**Step 1: Initial Submission**
```sql
-- User submits badge
INSERT INTO courses (email, problem_statement, badge_link, valid)
VALUES ('user@example.com', 'Build a Website', 'https://...', NULL);

-- Status: Pending verification
```

**Step 2: Verification Script Runs**
```sql
-- Verification fails
UPDATE courses
SET valid = FALSE, remarks = 'Badge not found or inaccessible'
WHERE email = 'user@example.com' AND problem_statement = 'Build a Website';
```

**Step 3: User Re-submits (Corrected Link)**
```
CSV Import:
  email: user@example.com
  problem_statement: Build a Website
  badge_link: https://corrected-link

Result: ✅ UPDATED (because valid = FALSE)
```

**Step 4: Verification Script Runs Again**
```sql
-- Verification succeeds
UPDATE courses
SET valid = TRUE, remarks = 'Valid Badge'
WHERE email = 'user@example.com' AND problem_statement = 'Build a Website';
```

**Step 5: User Tries to Re-submit Again**
```
CSV Import:
  email: user@example.com
  problem_statement: Build a Website
  badge_link: https://different-link

Result: ✗ SKIPPED (because valid = TRUE)
Log: "Already verified as valid"
```

---

## 🎯 Benefits

1. **Data Integrity**
   - Verified records are protected from accidental overwrites
   - Users can correct failed submissions

2. **Audit Trail**
   - `updated_at` tracks when re-submissions occurred
   - Master log maintains full history of changes

3. **User Experience**
   - Users can resubmit failed links without admin intervention
   - Once verified, submissions are locked in

4. **Verification Efficiency**
   - Only new/updated records need verification
   - Verified records are never re-checked unnecessarily

---

## 🛠️ Implementation Details

**File:** `app/csv_import.py`

**Modified Methods:**
1. `_import_course(session, row_dict)` - Lines 188-235
2. `_import_skillboost_profile(session, row_dict)` - Lines 237-284

**Key Changes:**
- Always check by composite primary key (not user-selected update keys)
- Add `existing.valid is True` check before updates
- Reset validation fields when updating failed/pending records
- Add debug logging for skipped verified records

**No Database Schema Changes Required** ✅
- Logic works with existing schema
- Uses existing `valid` and `remarks` columns

---

## 📝 Testing Checklist

- [ ] Import new badges (should create)
- [ ] Import duplicate badges (should skip if verified)
- [ ] Import updated badge for failed verification (should update)
- [ ] Import updated badge for pending verification (should update)
- [ ] Verify validation fields are reset on update
- [ ] Check debug logs for skip messages
- [ ] Verify import statistics are accurate
- [ ] Test with different operation modes (create/update/create_update)

---

## 🔧 Configuration

**No Configuration Changes Needed**

This logic is **automatic** and works with all operation modes:
- **Create Mode:** Creates new, skips existing (including verified)
- **Update Mode:** Updates failed/pending, skips verified
- **Create & Update Mode:** Creates new, updates failed/pending, skips verified

---

## 📞 Support

If you need to manually update a verified record:
1. Use SQL to set `valid = NULL` for that record
2. Re-import the CSV
3. Run verification script

```sql
-- Reset specific record for re-import
UPDATE courses
SET valid = NULL, remarks = NULL, updated_at = CURRENT_TIMESTAMP
WHERE email = 'user@example.com' AND problem_statement = 'Build a Website';
```

Or reset all failed records:
```sql
-- Reset all failed records
UPDATE courses
SET valid = NULL, remarks = NULL, updated_at = CURRENT_TIMESTAMP
WHERE valid = FALSE;
```

