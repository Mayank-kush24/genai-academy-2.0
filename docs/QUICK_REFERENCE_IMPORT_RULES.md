# Quick Reference: Import Rules for Verified Records

## 🎯 One-Line Summary
**Verified records (`valid = TRUE`) cannot be overwritten during import.**

---

## 📊 Decision Table

| Existing Record Status | New Data in CSV | Action Taken | Why? |
|------------------------|-----------------|--------------|------|
| **Does not exist** | ✅ New data | **CREATE** new record | No conflict |
| **valid = TRUE** | 🔄 Updated data | **SKIP** (keep old) | Protect verified data |
| **valid = FALSE** | 🔄 Updated data | **UPDATE** (use new) | Allow corrections |
| **valid = NULL** | 🔄 Updated data | **UPDATE** (use new) | Pending verification |

---

## 🔍 Which Tables?

This logic applies to:
- ✅ **`courses`** (Course Badges)
- ✅ **`skillboost_profile`** (Skillboost Profiles)

Standard update logic for:
- ⚪ `user_pii` (User Information)
- ⚪ `master_classes` (Attendance)

---

## 💡 Quick Examples

### Example 1: Verified Badge (Protected)
```
Database:
  john@example.com | Build Website | badge-link-1 | valid=TRUE ✅

CSV Import:
  john@example.com | Build Website | badge-link-2 | (new link)

Result: ✗ SKIPPED (keeps badge-link-1)
Message: "Already verified as valid"
```

### Example 2: Failed Badge (Updatable)
```
Database:
  john@example.com | Build Website | badge-link-1 | valid=FALSE ❌

CSV Import:
  john@example.com | Build Website | badge-link-2 | (corrected)

Result: ✅ UPDATED (uses badge-link-2)
Action: Reset valid=NULL for re-verification
```

### Example 3: Different Course (New Entry)
```
Database:
  john@example.com | Build Website | badge-link-1 | valid=TRUE ✅

CSV Import:
  john@example.com | Build Mobile App | badge-link-2 | (different course!)

Result: ✅ CREATED (new course badge)
Reason: Different primary key
```

---

## 🎮 Operation Modes

All three modes respect the verified record protection:

### **Create Mode**
- Creates new records only
- Skips ALL existing records (verified or not)

### **Update Mode**
- Updates failed/pending records only
- Skips verified records AND new records

### **Create & Update Mode** ⭐ (Recommended)
- Creates new records
- Updates failed/pending records
- Skips verified records

---

## 📝 What Gets Reset on Update?

When updating a failed/pending record:

```python
existing.badge_link = new_link      # ✅ Updated
existing.valid = None               # ✅ Reset (needs re-verification)
existing.remarks = None             # ✅ Reset
existing.updated_at = NOW           # ✅ Updated
```

---

## 🔑 Primary Keys

**Courses Table:**
```
Primary Key = (email + problem_statement)
```
- Same email + same problem statement = Same record
- Same email + different problem statement = Different record

**Skillboost Profile Table:**
```
Primary Key = (email + profile_link)
```
- Same email + same profile link = Same record
- Same email + different profile link = Different record

---

## 📊 Import Results Example

```
Import Completed!
├─ Created: 450 records      ← New submissions
├─ Updated: 120 records      ← Failed/pending links (corrected)
├─ Skipped: 230 records      ← Verified links (protected)
└─ Errors: 2 records         ← Data validation errors
```

---

## 🔧 How to Force Update a Verified Record?

If you REALLY need to update a verified record:

**Option 1: SQL Update**
```sql
-- Reset verification status for specific record
UPDATE courses
SET valid = NULL, remarks = NULL
WHERE email = 'user@example.com' 
  AND problem_statement = 'Build Website';

-- Then re-import CSV
```

**Option 2: Delete & Recreate**
```sql
-- Delete the verified record
DELETE FROM courses
WHERE email = 'user@example.com' 
  AND problem_statement = 'Build Website';

-- Then re-import CSV
```

---

## ⚠️ Important Notes

1. **Only Link Updates Are Blocked**
   - This protection only applies when the PRIMARY KEY matches
   - Different problem statement = Different record (new entry)

2. **Verification Reset**
   - When updating failed/pending records, `valid` is reset to NULL
   - This triggers re-verification by the verification script

3. **Email Normalization**
   - All emails are automatically lowercased and trimmed
   - `John@Example.COM` becomes `john@example.com`

4. **Debug Logging**
   - Check console output for skip messages:
     ```
     [DEBUG IMPORT] Skipped course badge for john@example.com: Already verified as valid
     ```

---

## 📞 Common Questions

**Q: Why was my updated badge link not imported?**
A: The previous badge is already verified (`valid = TRUE`). Verified records are protected.

**Q: How can users correct a wrong submission?**
A: Failed submissions (`valid = FALSE`) can be updated by re-importing with corrected data.

**Q: What if a user submits a badge for a different course?**
A: That's a new record (different primary key), so it will be created normally.

**Q: Can I see which records were skipped?**
A: Yes, check the console output for `[DEBUG IMPORT] Skipped...` messages.

**Q: Does this affect user_pii table?**
A: No, only `courses` and `skillboost_profile` tables have this protection.

---

## 🎯 Best Practices

1. **Always use "Create & Update" mode** for most imports
2. **Run verification script** after imports to validate new/updated records
3. **Check import statistics** to see how many were skipped
4. **Review debug logs** to understand why records were skipped
5. **Reset failed records** before allowing user re-submissions

---

## 📅 Version

- **Implemented:** November 2025
- **Applies To:** GenAI Academy 2.0 Records Management System
- **Files Modified:** `app/csv_import.py`

