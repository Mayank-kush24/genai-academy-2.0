# Master Class System Guide

## Overview

The Master Class system tracks student attendance and viewing records for **6 master classes** (1 per track) with validation for both **Live** and **Recorded** attendance.

---

## Master Classes

There are **6 master classes total** - one for each track:

1. **AI/ML Track - Master Class**
2. **Data Track - Master Class**
3. **Dev Ops Track - Master Class**
4. **Security Track - Master Class**
5. **Networking Track - Master Class**
6. **Serverless Track - Master Class**

**Total: 6 master classes (1 per track)**

---

## Data Structure

### Excel File Format

Prepare your master class data in an Excel file with the following headers:

**⚠️ Note:** You do **NOT** need to include a "Master Class Name" column in your Excel file. This will be selected via a dropdown during the import process.

| Column Name | Description | Data Type | Example |
|------------|-------------|-----------|---------|
| **Platform** | Hosting platform | Text | YouTube, Zoom, Teams |
| **Link** | Recording/session link | URL | https://youtube.com/watch?v=... |
| **Total Duration (mins)** | Full master class duration | Integer or MM:SS | 90 or 90:00 |
| **Started At** | When class started | Timestamp | 2025-11-01 14:00:00 |
| **Updated At** | Last update timestamp | Timestamp | 2025-11-05 10:30:00 |
| **Watched Duration Updated At** | When watch time was updated | Timestamp | 2025-11-05 10:30:00 |
| **Name** | Student name (optional) | Text | John Doe |
| **Email** | Student email **(FK to user_pii)** | Email | student@example.com |
| **Watch Time(mins)** | How long student watched | Integer or MM:SS | 85 or 72:26 |
| **Live** | Live attendance validation | TRUE/FALSE/- | TRUE, FALSE, or - |
| **Recorded** | Recorded viewing validation | TRUE/FALSE/- | TRUE, FALSE, or - |

### Special Values for Live and Recorded

These columns accept three values:
- **TRUE** = Verified/Valid attendance
- **FALSE** = Invalid/Failed verification
- **-** (dash) = Empty/Null/Pending verification

### Time Format Auto-Conversion

**Watch Time** and **Total Duration** columns support multiple formats:
- **Simple Integer**: `85` = 85 minutes
- **MM:SS Format**: `72:26` = 72 minutes (seconds are ignored)
- **HH:MM:SS Format**: `1:30:00` = 90 minutes (converted to total minutes)

The system automatically converts time formats during import, so you can use whichever format your data source provides!

---

## Import Logic & Protection Rules

### 1. **Composite Primary Key**
Records are uniquely identified by: `(email, master_class_name)`

### 2. **Protection Logic**

#### Live Field:
- ✅ **If Live = TRUE**: Field is **PROTECTED** - will NOT be overwritten on re-import
- ⚠️ **If Live = FALSE**: Field can be overwritten with new data
- 🔄 **If Live = NULL (-)**: Field can be set/updated

#### Recorded Field:
- ✅ **If Recorded = TRUE**: Field is **PROTECTED** - will NOT be overwritten on re-import
- ⚠️ **If Recorded = FALSE**: Field can be overwritten with new data
- 🔄 **If Recorded = NULL (-)**: Field can be set/updated

### 3. **Mutual Exclusivity Rule**

**⚠️ IMPORTANT**: A user **CANNOT** have both `Live = TRUE` AND `Recorded = TRUE` for the same master class.

**Enforcement:**
- If import data has both Live and Recorded set to TRUE, the system will automatically set `Recorded = NULL` and keep `Live = TRUE`
- Reasoning: If someone attended live, they don't need to watch the recording

### 4. **Update Behavior Examples**

| Existing Record | New Import Data | Result | Explanation |
|----------------|----------------|--------|-------------|
| Live = TRUE, Recorded = NULL | Live = FALSE, Recorded = TRUE | Live = TRUE, Recorded = TRUE | Live is protected, Recorded can be set |
| Live = FALSE, Recorded = NULL | Live = TRUE, Recorded = NULL | Live = TRUE, Recorded = NULL | Live can be updated (was FALSE) |
| Live = NULL, Recorded = TRUE | Live = TRUE, Recorded = FALSE | Live = TRUE, Recorded = TRUE | Recorded is protected, Live can be set |
| Live = TRUE, Recorded = FALSE | Live = FALSE, Recorded = TRUE | Live = TRUE, Recorded = NULL | Live protected, Recorded updated but set to NULL (mutual exclusivity) |

---

## Step-by-Step Import Process

### Step 1: Run Database Migration

**First time only** - adds the new columns to the master_classes table:

```powershell
cd "D:\Academy 2.0"
database\run_migration_masterclass_v2.bat
```

This will add these columns:
- platform
- link
- total_duration
- watched_duration_updated_at
- watch_time
- live
- recorded

### Step 2: Prepare Your Excel File

1. Create an Excel file with the required headers
2. Fill in master class attendance data
3. **Important**: Ensure email addresses match those in the `user_pii` table
4. Use `-` (dash) for empty Live/Recorded values

**Example Row:**
```
Platform: YouTube
Link: https://youtube.com/watch?v=abc123
Total Duration (mins): 90
Started At: 2025-11-01 14:00:00
Updated At: 2025-11-05 10:30:00
Watched Duration Updated At: 2025-11-05 10:30:00
Name: John Doe
Email: john.doe@example.com
Watch Time(mins): 85
Live: TRUE
Recorded: -
```

### Step 3: Import via Web Interface

1. **Login** to the system
2. Navigate to **Import** page (`/import`)
3. **Upload** your Excel file
4. **Select the correct sheet** (if multiple sheets exist)
5. **Select target table**: `master_classes`
6. **📋 SELECT MASTER CLASS** (NEW STEP):
   - A dropdown will appear with 6 master classes (1 per track)
   - **Tracks available**: AI/ML, Data, Dev Ops, Security, Networking, Serverless
   - **Select which master class** this data is for (e.g., "AI/ML Track - Master Class")
   - This value will be automatically applied to **all rows** in the import
   - ⚠️ This step is **required** for master class imports
7. **Map columns**:
   - Drag CSV columns to database columns
   - **Note:** You won't see `master_class_name` in the mapping - it's auto-injected!
   - Ensure proper mapping:
     - `Email` → `email`
     - `Watch Time(mins)` → `watch_time`
     - `Live` → `live`
     - `Recorded` → `recorded`
     - `Platform` → `platform`
     - `Link` → `link`
     - `Total Duration (mins)` → `total_duration`
     - etc.
8. **Choose operation mode**:
   - **Create & Update** (recommended) - allows both new records and updates
   - **Create Only** - only adds new records
   - **Update Only** - only updates existing records
9. **Select update keys**: 
   - Use `email` (master_class_name is auto-managed)
10. **Review and Execute Import**

### Step 4: Verify Import

After import completes:
- Check the import statistics (Created/Updated/Skipped counts)
- Review any error messages
- Visit user profiles to see master class attendance

---

## User Profile Display

Master class attendance appears on each user's profile page with:

### Visual Indicators

**✅ Live Verified** (Green Badge)
- `live = TRUE`

**🎥 Recorded Verified** (Blue Badge)
- `recorded = TRUE`

**❌ Invalid** (Red Badge)
- `live = FALSE` or `recorded = FALSE`

**⏳ Pending Verification** (Gray Badge)
- Both `live` and `recorded` are NULL

### Information Displayed

For each master class, the profile shows:
- Master class name
- Platform (if available)
- Verification status (Live/Recorded/Pending/Invalid)
- Watch time vs. total duration
- Link to recording (if available)
- Attendance date

**Example Display:**
```
AI/ML Track - Master Class
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📡 Platform: YouTube
✅ Live Verified
⏰ Watch Time: 85 mins / 90 mins
🔗 View Recording
📅 2025-11-01
```

---

## Common Scenarios

### Scenario 1: First-Time Import
**Data:** Live = TRUE, Recorded = -
**Result:** User is marked as verified live attendee
**Future Imports:** Live field is now protected and won't change

### Scenario 2: Update Failed Live to Verified
**Existing:** Live = FALSE
**New Data:** Live = TRUE
**Result:** Successfully updates to Live = TRUE
**Reason:** FALSE values can be overwritten

### Scenario 3: Adding Recorded After Live
**Existing:** Live = TRUE, Recorded = NULL
**New Data:** Live = TRUE, Recorded = TRUE
**Result:** Live = TRUE, Recorded = NULL (stays NULL)
**Reason:** Mutual exclusivity - can't have both

### Scenario 4: Re-importing Same Data
**Existing:** Live = TRUE, Recorded = FALSE
**New Data:** Live = FALSE, Recorded = TRUE
**Result:** Live = TRUE, Recorded = TRUE
**Reason:** Live is protected (was TRUE), Recorded can be updated (was FALSE)

---

## Validation Rules Summary

### ✅ Always Allowed
- Setting NULL fields to TRUE or FALSE
- Updating FALSE to TRUE
- Updating FALSE to NULL

### ❌ Never Allowed
- Updating TRUE to FALSE (protected)
- Updating TRUE to NULL (protected)
- Having both Live = TRUE AND Recorded = TRUE

### ⚙️ Automatically Handled
- Converting "-" strings to NULL
- Email normalization (lowercase, trimmed)
- Mutual exclusivity enforcement
- Update timestamp management

---

## Database Schema

### Table: `master_classes`

```sql
CREATE TABLE master_classes (
    email VARCHAR(255) PRIMARY KEY,
    master_class_name VARCHAR(255) PRIMARY KEY,
    platform VARCHAR(100),
    link TEXT,
    total_duration INTEGER,
    watch_time INTEGER,
    live BOOLEAN DEFAULT NULL,
    recorded BOOLEAN DEFAULT NULL,
    watched_duration_updated_at TIMESTAMP,
    started_at TIMESTAMP,
    updated_at TIMESTAMP,
    time_watched VARCHAR(50),  -- Legacy
    valid BOOLEAN DEFAULT TRUE, -- Legacy
    PRIMARY KEY (email, master_class_name),
    FOREIGN KEY (email) REFERENCES user_pii(email)
);
```

---

## Best Practices

### 1. Data Preparation
- Always verify email addresses exist in `user_pii` table first
- Use consistent master class names selected from dropdown (e.g., "AI/ML Track - Master Class")
- Keep platform names consistent (e.g., always "YouTube" not "youtube" or "YT")

### 2. Import Strategy
- **Initial Import**: Use "Create & Update" mode
- **Regular Updates**: Use "Create & Update" mode
- **New Classes Only**: Use "Create Only" mode
- **Corrections Only**: Use "Update Only" mode

### 3. Verification Workflow
1. Import data with Live/Recorded = NULL (pending)
2. Verify attendance manually or via automated process
3. Re-import with Live/Recorded = TRUE for verified attendees
4. Re-import with Live/Recorded = FALSE for failed verifications
5. Verified records (TRUE) are now protected from accidental overwrites

### 4. Maintenance
- Regularly backup data before mass imports
- Use "Create & Update" mode for flexibility
- Monitor import statistics for errors
- Check user profiles after import to verify display

---

## Troubleshooting

### Problem: Records Not Importing
**Cause:** Email doesn't exist in `user_pii` table
**Solution:** Import user PII data first, then master class data

### Problem: Live Field Not Updating
**Cause:** Existing Live = TRUE (protected)
**Solution:** This is by design. Manually update in database if needed.

### Problem: Both Live and Recorded Are TRUE
**Cause:** Data was set before migration or manual database edit
**Solution:** Next import will enforce mutual exclusivity and set Recorded to NULL

### Problem: "-" Values Not Becoming NULL
**Cause:** Column not mapped correctly
**Solution:** Ensure Live and Recorded columns are mapped in import interface

### Problem: Watch Time Not Showing on Profile
**Cause:** watch_time column not mapped or is NULL
**Solution:** Map "Watch Time(mins)" to "watch_time" during import

---

## SQL Queries for Reporting

### Count Verified Live Attendees
```sql
SELECT master_class_name, COUNT(*) as verified_live
FROM master_classes
WHERE live = TRUE
GROUP BY master_class_name
ORDER BY master_class_name;
```

### Count Verified Recorded Viewers
```sql
SELECT master_class_name, COUNT(*) as verified_recorded
FROM master_classes
WHERE recorded = TRUE
GROUP BY master_class_name
ORDER BY master_class_name;
```

### Find Pending Verifications
```sql
SELECT email, master_class_name, watch_time
FROM master_classes
WHERE live IS NULL AND recorded IS NULL
ORDER BY master_class_name, email;
```

### Average Watch Time Per Class
```sql
SELECT master_class_name, 
       AVG(watch_time) as avg_watch_time,
       MAX(total_duration) as total_duration
FROM master_classes
WHERE watch_time IS NOT NULL
GROUP BY master_class_name
ORDER BY master_class_name;
```

---

## Support

For issues or questions:
1. Check import error messages in the web interface
2. Review this documentation
3. Check database migration was successful
4. Verify email addresses match user_pii table
5. Contact system administrator if problems persist

---

**Last Updated:** November 2025  
**Version:** 2.0

