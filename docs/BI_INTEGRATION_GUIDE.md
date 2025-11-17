# BI Integration Guide

## GenAI Academy 2.0 - Looker Studio & Power BI Integration

This guide explains how to connect Looker Studio and Power BI to the Academy PostgreSQL database for creating dashboards and reports.

---

## Database Connection Details

- **Host:** `192.168.1.60` (remote PostgreSQL server)
- **Port:** `5432`
- **Database Name:** `academy2_0`
- **Username:** `postgres` (or as configured in `.env`)
- **Password:** As set in `.env` file

---

## Looker Studio Integration

### Step 1: Add PostgreSQL Data Source

1. Go to [Looker Studio](https://lookerstudio.google.com/)
2. Click **Create** → **Data Source**
3. Search for and select **PostgreSQL** connector
4. Enter connection details:
   - **Host name or IP:** `192.168.1.60`
   - **Port:** `5432`
   - **Database:** `academy2_0`
   - **Username:** Your PostgreSQL username
   - **Password:** Your PostgreSQL password
5. Enable **SSL** if your PostgreSQL is configured for it (optional for local)
6. Click **Authenticate**

### Step 2: Select Tables/Views

Choose from the following tables and views:

**Primary Tables:**
- `user_pii` - User personal information
- `courses` - Course badge submissions
- `skillboost_profile` - Skillboost profile links
- `master_classes` - Masterclass attendance

**Pre-built Views (Recommended):**
- `v_user_summary` - User summary with course and masterclass counts
- `v_course_verification_status` - Course-wise verification statistics
- `v_masterclass_attendance` - Masterclass attendance summary
- `v_track_completion` - Track-wise completion status
- `v_certificate_eligible` - Users eligible for certificates

### Step 3: Create Reports

**Recommended Visualizations:**

1. **User Overview Dashboard**
   - Total users (scorecard)
   - Users by location (geo map using country/state)
   - Users by occupation (pie chart)
   - Registration trend (time series)

2. **Course Progress Dashboard**
   - Course verification status (bar chart)
   - Pending vs Verified badges (gauge chart)
   - Top courses by submissions (bar chart)
   - Verification success rate (scorecard)

3. **Masterclass Analytics**
   - Total attendance (scorecard)
   - Live vs Recorded viewers (pie chart)
   - Attendance by masterclass (bar chart)
   - Engagement trend (time series)

### Step 4: Schedule Refresh

- Looker Studio can auto-refresh data
- For real-time dashboards, set refresh interval to 15-30 minutes
- For daily reports, schedule once per day

---

## Power BI Integration

### Step 1: Install PostgreSQL Connector

1. Power BI Desktop includes PostgreSQL connector by default
2. If not available, download from Power BI marketplace

### Step 2: Connect to Database

1. Open Power BI Desktop
2. Click **Get Data** → **Database** → **PostgreSQL database**
3. Enter server details:
   - **Server:** `192.168.1.60:5432`
   - **Database:** `academy2_0`
4. Choose **DirectQuery** (recommended) or **Import**
   - **DirectQuery:** Real-time data, queries run on database
   - **Import:** Faster performance, but data needs manual refresh
5. Click **OK**

### Step 3: Enter Credentials

1. Select **Database** authentication
2. Enter username and password
3. Click **Connect**

### Step 4: Select Tables

From the Navigator window, select:

**Recommended Tables/Views:**
- `v_user_summary`
- `v_course_verification_status`
- `v_masterclass_attendance`
- `v_track_completion`

You can also select base tables (`user_pii`, `courses`, etc.) for custom relationships.

### Step 5: Create Relationships (if using multiple tables)

Power BI should auto-detect relationships. Verify:
- `user_pii.email` ↔ `courses.email`
- `user_pii.email` ↔ `master_classes.email`
- `user_pii.email` ↔ `skillboost_profile.email`

### Step 6: Build Visualizations

**Sample Measures (DAX):**

```dax
Total Users = COUNT(user_pii[email])

Verified Badges = 
CALCULATE(
    COUNT(courses[email]),
    courses[valid] = TRUE
)

Verification Rate = 
DIVIDE([Verified Badges], COUNT(courses[email]), 0)

Avg Courses Per User = 
DIVIDE(
    COUNT(courses[problem_statement]),
    DISTINCTCOUNT(courses[email]),
    0
)
```

**Sample Visuals:**
1. Card - Total Users
2. Card - Total Verified Badges
3. Bar Chart - Courses by Verification Status
4. Map - Users by Location
5. Table - Top Users by Course Completion
6. Line Chart - Registration Trend

### Step 7: Publish to Power BI Service

1. Click **Publish** in Power BI Desktop
2. Select workspace
3. Configure scheduled refresh (if using Import mode)
4. Share dashboard with team

---

## Database Views Reference

### v_user_summary
Complete user profile with aggregated course and masterclass data.

**Columns:**
- `email`, `name`, `phone_number`
- `country`, `state`, `city`
- `designation`, `occupation`
- `courses_completed` - Total courses submitted
- `courses_verified` - Verified courses only
- `masterclasses_attended` - Total masterclasses

**Use Case:** User overview dashboards, user listings

---

### v_course_verification_status
Course-wise verification statistics.

**Columns:**
- `problem_statement` - Course name
- `total_submissions` - Total submissions
- `verified` - Count of verified submissions
- `failed` - Count of failed verifications
- `pending` - Count of pending verifications

**Use Case:** Course performance analysis, verification monitoring

---

### v_masterclass_attendance
Masterclass attendance summary.

**Columns:**
- `master_class_name`
- `total_attendees`
- `live_attendees`
- `recorded_attendees`

**Use Case:** Masterclass engagement analysis

---

### v_track_completion
Individual user track completion status.

**Columns:**
- `email`, `name`
- `track_id`, `track_name`
- `total_courses_in_track`
- `completed_courses`
- `track_completed` (boolean)

**Use Case:** Track progress monitoring, certificate eligibility

---

### v_certificate_eligible
Users who completed all courses in at least one track.

**Columns:**
- `email`, `name`
- `track_id`, `track_name`
- `completed_courses`, `total_courses_in_track`

**Use Case:** Certificate issuance, achievement tracking

---

## Network Configuration

### For Remote Access (Team Access)

If team members need to access dashboards that connect to your local database:

**Windows Firewall:**
1. Open Windows Defender Firewall
2. Click "Advanced settings"
3. Click "Inbound Rules" → "New Rule"
4. Select "Port" → Next
5. Select "TCP" and enter port `5432`
6. Allow the connection
7. Apply to Domain, Private, and Public (as needed)
8. Name it "PostgreSQL Academy"

**PostgreSQL Configuration:**

Edit `postgresql.conf` (usually in `C:\Program Files\PostgreSQL\XX\data\`):
```
listen_addresses = '*'
```

Edit `pg_hba.conf`:
```
# Allow connections from local network
host    academy2_0    postgres    192.168.1.0/24    md5
```

Restart PostgreSQL service.

**Find Your IP Address:**
```powershell
ipconfig
```
Look for "IPv4 Address" under your active network adapter.

---

## Security Best Practices

1. **Use Read-Only Database User for BI Tools**
   ```sql
   CREATE USER bi_readonly WITH PASSWORD 'secure_password';
   GRANT CONNECT ON DATABASE academy2_0 TO bi_readonly;
   GRANT USAGE ON SCHEMA public TO bi_readonly;
   GRANT SELECT ON ALL TABLES IN SCHEMA public TO bi_readonly;
   GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO bi_readonly;
   ```

2. **Use VPN** if accessing from outside your local network

3. **Enable SSL** for PostgreSQL connections

4. **Regular Password Rotation** for database users

5. **Monitor Access Logs** in PostgreSQL

---

## Troubleshooting

### Cannot Connect to Database

**Issue:** "Could not connect to server"

**Solutions:**
- Verify PostgreSQL service is running
- Check firewall rules
- Verify IP address is correct
- Test connection using `psql` command line
- Ensure `listen_addresses` is set correctly

### Data Not Refreshing

**Looker Studio:**
- Check data source credentials
- Manually trigger refresh
- Verify database is accessible

**Power BI:**
- Update credentials in Power BI Service
- Check scheduled refresh settings
- Verify gateway configuration (if using)

### Slow Performance

**Solutions:**
- Use DirectQuery instead of Import (Power BI)
- Create indexes on frequently queried columns
- Use pre-built views instead of complex joins
- Limit date ranges in filters
- Aggregate data in database views

---

## Sample Queries for Custom Views

If you want to create additional custom views:

```sql
-- Users with most course completions
CREATE VIEW v_top_performers AS
SELECT 
    u.email,
    u.name,
    COUNT(c.problem_statement) as total_courses,
    COUNT(CASE WHEN c.valid = TRUE THEN 1 END) as verified_courses
FROM user_pii u
LEFT JOIN courses c ON u.email = c.email
GROUP BY u.email, u.name
HAVING COUNT(c.problem_statement) > 0
ORDER BY verified_courses DESC;

-- Weekly registration trend
CREATE VIEW v_registration_trend AS
SELECT 
    DATE_TRUNC('week', created_at) as week,
    COUNT(*) as new_users
FROM user_pii
GROUP BY DATE_TRUNC('week', created_at)
ORDER BY week;
```

---

## Support

For additional assistance:
1. Check database logs: `data/postgresql.log`
2. Test connection: `python app/database.py`
3. Review network configuration
4. Consult PostgreSQL documentation

