# Master Class Import - Quick Reference Card

## 📋 Required Excel Headers

**⚠️ Note:** Do NOT include "Master Class Name" in your Excel - it's selected via dropdown!

```
Platform | Link | Total Duration (mins) | Started At | Updated At | 
Watched Duration Updated At | Name | Email | Watch Time(mins) | Live | Recorded
```

**💡 Time Format:** Watch Time and Total Duration can be in `MM:SS` format (e.g., `72:26`) or simple integers (e.g., `72`). The system auto-converts!

---

## 🔑 Key Rules

### Live & Recorded Values
- **TRUE** = Verified ✅
- **FALSE** = Invalid ❌  
- **-** (dash) = Pending/Null ⏳

### Protection Logic
| Current Value | Can Overwrite? |
|---------------|----------------|
| TRUE | ❌ NO - Protected |
| FALSE | ✅ YES - Can update |
| NULL (-) | ✅ YES - Can set |

### Mutual Exclusivity
**⚠️ If Live = TRUE, then Recorded cannot be TRUE**
- System automatically sets Recorded = NULL if both are TRUE

---

## 🚀 Import Steps

1. **Run Migration** (first time only):
   ```powershell
   database\run_migration_masterclass_v2.bat
   ```

2. **Prepare Excel File** with required headers (NO master class name column!)

3. **Web Interface**:
   - Login → Import page
   - Upload Excel file
   - Select sheet (if multiple)
   - Choose table: `master_classes`
   - **📋 SELECT MASTER CLASS** from dropdown ← NEW!
     - 6 options total (1 per track): AI/ML, Data, Dev Ops, Security, Networking, Serverless
     - Example: "AI/ML Track - Master Class"
   - Map columns to database fields (master_class_name is auto-injected)
   - Operation mode: **Create & Update**
   - Update keys: `email`
   - Execute Import

---

## 📊 Column Mapping

**⚠️ `master_class_name` is NOT mapped - it's auto-injected from dropdown selection!**

| Excel Column | Maps To → | Database Column |
|--------------|-----------|-----------------|
| Email | → | email |
| Platform | → | platform |
| Link | → | link |
| Total Duration (mins) | → | total_duration |
| Watch Time(mins) | → | watch_time |
| Live | → | live |
| Recorded | → | recorded |
| Started At | → | started_at |
| Updated At | → | updated_at |
| Watched Duration Updated At | → | watched_duration_updated_at |

---

## 🎯 Common Scenarios

### Scenario 1: First Import
```
Data:     Live = TRUE, Recorded = -
Result:   ✅ Live Verified (protected now)
```

### Scenario 2: Update Failed to Verified
```
Before:   Live = FALSE
Data:     Live = TRUE
Result:   ✅ Updated to TRUE
```

### Scenario 3: Both TRUE (Not Allowed)
```
Data:     Live = TRUE, Recorded = TRUE
Result:   Live = TRUE, Recorded = NULL (auto-corrected)
Reason:   Can't have both verified
```

### Scenario 4: Update Protected Field
```
Before:   Live = TRUE
Data:     Live = FALSE
Result:   Live = TRUE (unchanged - protected)
```

---

## 🏷️ Profile Display Badges

| Status | Badge | Meaning |
|--------|-------|---------|
| Live = TRUE | ✅ Live Verified | Green |
| Recorded = TRUE | 🎥 Recorded Verified | Blue |
| Live = FALSE or Recorded = FALSE | ❌ Invalid | Red |
| Both NULL | ⏳ Pending Verification | Gray |

---

## ⚠️ Important Notes

1. **Email must exist** in `user_pii` table
2. **Use consistent names** for master classes (e.g., "Master Class 1")
3. **Verified records (TRUE)** are **protected** from overwrites
4. **Invalid records (FALSE)** can be updated
5. **"-" becomes NULL** automatically during import

---

## 🔍 Quick Verification

After import, check:
- Import statistics (Created/Updated/Skipped)
- User profiles → Master class section
- Database query:
  ```sql
  SELECT COUNT(*) FROM master_classes WHERE live = TRUE;
  ```

---

## 📞 Need Help?

See full documentation: `docs/MASTERCLASS_SYSTEM_GUIDE.md`

