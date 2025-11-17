# Deployment Guide

Complete step-by-step guide for deploying the GenAI Academy 2.0 Records Management System on your local machine.

---

## Prerequisites Checklist

- [ ] Windows 10/11 PC with administrator access
- [ ] At least 4GB RAM available
- [ ] 10GB free disk space
- [ ] Stable internet connection (for initial setup and verification)
- [ ] Administrator rights to install software and configure firewall

---

## Part 1: Software Installation

### Step 1: Install PostgreSQL

1. **Download PostgreSQL**
   - Go to https://www.postgresql.org/download/windows/
   - Download PostgreSQL 15 or 16 installer (latest stable version)
   - File size: ~350 MB

2. **Run Installer**
   - Double-click the downloaded `.exe` file
   - Click "Next" through welcome screen
   
3. **Select Components**
   - Keep all default components selected:
     - [x] PostgreSQL Server
     - [x] pgAdmin 4
     - [x] Command Line Tools
   - Click "Next"

4. **Choose Installation Directory**
   - Default: `C:\Program Files\PostgreSQL\15\`
   - Click "Next"

5. **Set Password**
   - **IMPORTANT:** Set a strong password for `postgres` user
   - **WRITE IT DOWN** - You'll need this in `.env` file
   - Click "Next"

6. **Port Number**
   - Keep default: `5432`
   - Click "Next"

7. **Locale**
   - Keep default locale
   - Click "Next"

8. **Complete Installation**
   - Click "Next" → "Next" → "Finish"
   - Uncheck "Stack Builder" (not needed)

9. **Verify Installation**
   ```powershell
   # Open PowerShell or Command Prompt
   psql --version
   ```
   Should show: `psql (PostgreSQL) 15.x`

### Step 2: Install Python

1. **Download Python**
   - Go to https://www.python.org/downloads/
   - Download Python 3.11 or 3.12 (latest stable)

2. **Run Installer**
   - **IMPORTANT:** Check "Add Python to PATH" at the bottom
   - Click "Install Now"
   - Wait for completion
   - Click "Close"

3. **Verify Installation**
   ```powershell
   python --version
   pip --version
   ```

---

## Part 2: Database Setup

### Step 1: Create Database (on Remote Server 192.168.1.60)

```powershell
# Open PowerShell as Administrator
# Navigate to project directory
cd "D:\Academy 2.0"

# Connect to PostgreSQL remote server (enter password when prompted)
psql -h 192.168.1.60 -U postgres

# You should see: postgres=#
# Create the database
CREATE DATABASE academy2_0;

# Verify it was created
\l

# Exit psql
\q
```

### Step 2: Create Schema

```powershell
# Run schema creation script
psql -h 192.168.1.60 -U postgres -d academy2_0 -f database/schema.sql

# Expected output: CREATE TABLE, CREATE INDEX, CREATE TRIGGER messages
```

### Step 3: Load Reference Data

```powershell
# Run reference data script
psql -h 192.168.1.60 -U postgres -d academy2_0 -f database/reference_data.sql

# Expected output: INSERT statements
```

### Step 4: Verify Database Setup

```powershell
# Connect to database
psql -h 192.168.1.60 -U postgres -d academy2_0

# Check tables exist
\dt

# Should show:
#  user_pii
#  courses
#  skillboost_profile
#  master_classes
#  master_log
#  tracks
#  course_definitions
#  masterclass_definitions

# Check views
\dv

# Exit
\q
```

---

## Part 3: Application Setup

### Step 1: Install Python Dependencies

```powershell
# In project directory
cd "D:\Academy 2.0"

# Upgrade pip
python -m pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Wait for all packages to install (2-3 minutes)
```

**Expected Packages:**
- Flask
- SQLAlchemy
- pandas
- requests
- beautifulsoup4
- psycopg2-binary
- openpyxl
- python-dotenv

### Step 2: Configure Environment

```powershell
# Create .env file from example
copy .env.example .env

# Edit .env file
notepad .env
```

**Edit the following values:**

```env
# Change this to your PostgreSQL password
DB_PASSWORD=your_postgresql_password_here

# Generate a random secret key for Flask
FLASK_SECRET_KEY=generate_random_string_here
```

**Save and close the file.**

### Step 3: Test Database Connection

```powershell
# Test connection
python -c "from app.database import db_manager; db_manager.initialize(); print('✓ Connection successful!')"
```

**Expected Output:** `✓ Connection successful!`

If you see an error, check:
- PostgreSQL service is running
- Password in `.env` is correct
- Database name is `academy2_0`

---

## Part 4: Initial Data Import

### Step 1: Prepare Data File

1. Place your Excel/CSV file in the project directory
2. For this example, we'll use: `actioncenter_genaiacademy2_data_center_submissions_all.xlsx`

### Step 2: Run Import

```powershell
# Import without verification (faster for initial load)
python scripts/import_csv.py --file actioncenter_genaiacademy2_data_center_submissions_all.xlsx

# Or with verification (takes much longer)
python scripts/import_csv.py --file actioncenter_genaiacademy2_data_center_submissions_all.xlsx --verify
```

**What happens:**
1. Reads Excel/CSV file
2. Extracts user PII data → `user_pii` table
3. Extracts course submissions → `courses` table
4. Extracts Skillboost profiles → `skillboost_profile` table
5. Extracts masterclass attendance → `master_classes` table
6. Generates report in `reports/` folder

**Expected Time:**
- Import only: 2-5 minutes for 100K records
- Import + verification: 40-60 minutes (due to rate limiting)

### Step 3: Review Import Report

```powershell
# Open latest report
notepad reports\import_report_*.txt
```

Check for:
- Number of users inserted/updated
- Number of courses, profiles, masterclasses imported
- Any errors

---

## Part 5: Run Verification (If Not Done During Import)

```powershell
# Verify all unverified records
python scripts/verify_skillboost.py

# Monitor progress in terminal
```

**Note:** This process:
- Checks each Skillboost profile URL
- Verifies each course badge URL
- Matches badge with expected course
- Updates `valid` field in database
- Rate-limited to 2.5 seconds per request

**For 1000 records:** ~40-50 minutes

---

## Part 6: Start Web Application

### Step 1: Launch Server

```powershell
# Start Flask application
python app/main.py
```

**Expected Output:**
```
============================================================
GenAI Academy 2.0 Records Management System
============================================================
Starting Flask server on port 5000...
Access the application at: http://localhost:5000
============================================================
 * Running on http://0.0.0.0:5000
```

**Leave this PowerShell window open!** The server must keep running.

### Step 2: Test Locally

1. Open web browser
2. Go to: `http://localhost:5000`
3. You should see the Academy home page
4. Try searching for a user

---

## Part 7: Configure Network Access (For Team)

### Step 1: Find Your IP Address

```powershell
ipconfig
```

Look for "IPv4 Address" under your network adapter (e.g., `192.168.1.100`)

### Step 2: Configure Windows Firewall

**Option A: Using GUI**

1. Open "Windows Defender Firewall with Advanced Security"
2. Click "Inbound Rules" in left panel
3. Click "New Rule..." in right panel
4. Select "Port" → Next
5. Select "TCP", enter "5000" → Next
6. Select "Allow the connection" → Next
7. Check Domain, Private, Public (as needed) → Next
8. Name: "Academy Web App" → Finish

**Option B: Using PowerShell (As Administrator)**

```powershell
# Allow Flask application
New-NetFirewallRule -DisplayName "Academy Web App" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow

# Allow PostgreSQL (for BI tools)
New-NetFirewallRule -DisplayName "PostgreSQL Academy" -Direction Inbound -LocalPort 5432 -Protocol TCP -Action Allow
```

### Step 3: Configure PostgreSQL for Remote Access

**Edit postgresql.conf:**

```powershell
# Find PostgreSQL data directory
# Usually: C:\Program Files\PostgreSQL\15\data\

# Open config file
notepad "C:\Program Files\PostgreSQL\15\data\postgresql.conf"
```

Find line with `listen_addresses` and change to:
```
listen_addresses = '*'
```

**Edit pg_hba.conf:**

```powershell
notepad "C:\Program Files\PostgreSQL\15\data\pg_hba.conf"
```

Add at the end:
```
# Allow local network
host    academy2_0    postgres    192.168.1.0/24    md5
```

**Restart PostgreSQL Service:**

1. Open Services (Win + R → `services.msc`)
2. Find "postgresql-x64-15"
3. Right-click → Restart

### Step 4: Test Team Access

From another computer on the same network:
1. Open browser
2. Go to: `http://192.168.1.100:5000` (use your IP)
3. Should see Academy home page

---

## Part 8: BI Tool Configuration

See [BI_INTEGRATION_GUIDE.md](BI_INTEGRATION_GUIDE.md) for complete instructions.

**Quick Setup for Looker Studio:**
- Data Source: PostgreSQL
- Host: `192.168.1.100` (your IP)
- Port: `5432`
- Database: `academy2_0`
- Username: `postgres`
- Password: (your PostgreSQL password)

**Recommended Tables:**
- `v_user_summary`
- `v_course_verification_status`
- `v_masterclass_attendance`

---

## Part 9: Schedule Weekly Tasks

### Task 1: Data Import

**Create Batch File:** `import_weekly.bat`

```batch
@echo off
cd "D:\Academy 2.0"
python scripts/import_csv.py --file data\weekly_latest.csv --verify
pause
```

**Schedule in Task Scheduler:**
1. Open Task Scheduler
2. Create Basic Task
3. Name: "Academy Weekly Import"
4. Trigger: Weekly (e.g., Monday 9 AM)
5. Action: Start a program
6. Program: `D:\Academy 2.0\import_weekly.bat`

### Task 2: Database Backup

**Create Batch File:** `backup_database.bat`

```batch
@echo off
set BACKUP_DIR=D:\Academy 2.0\backups
set FILENAME=academy2_0_%date:~-4,4%%date:~-10,2%%date:~-7,2%.sql

mkdir %BACKUP_DIR% 2>nul
"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe" -U postgres -d academy2_0 -f "%BACKUP_DIR%\%FILENAME%"
echo Backup completed: %FILENAME%
pause
```

**Schedule:** Weekly (e.g., Sunday 11 PM)

---

## Part 10: Maintenance

### Regular Tasks

**Daily:**
- Ensure web server is running
- Check for any errors in console

**Weekly:**
- Import new data
- Review verification queue
- Check failed verifications
- Export data for reporting

**Monthly:**
- Database backup
- Clean old reports (`reports/` folder)
- Review disk space
- Update Python packages: `pip install --upgrade -r requirements.txt`

### Monitoring

**Check Database Size:**
```sql
psql -U postgres -d academy2_0 -c "SELECT pg_size_pretty(pg_database_size('academy2_0'));"
```

**Check Table Sizes:**
```sql
psql -U postgres -d academy2_0 -c "\dt+"
```

**View Recent Logs:**
```sql
psql -U postgres -d academy2_0 -c "SELECT * FROM master_log ORDER BY changed_at DESC LIMIT 20;"
```

---

## Troubleshooting

### Server Won't Start

**Issue:** Port 5000 already in use

**Solution:**
```powershell
# Find what's using port 5000
netstat -ano | findstr :5000

# Kill the process (replace <PID> with actual process ID)
taskkill /PID <PID> /F

# Or change port in .env
# FLASK_PORT=5001
```

### Database Connection Failed

**Checklist:**
- [ ] PostgreSQL service running? (Check Services)
- [ ] Password correct in `.env`?
- [ ] Database `academy2_0` exists? (Check with `\l` in psql)
- [ ] Firewall blocking connection?

### Import Fails

**Common Issues:**
1. File not found → Use full path
2. Encoding errors → Try opening Excel file and saving as CSV UTF-8
3. Memory error → Process file in chunks (contact for assistance)

### Web Page Not Loading

**Checklist:**
- [ ] Flask server running?
- [ ] Correct URL? (Check IP address)
- [ ] Firewall rule added?
- [ ] Browser cache cleared?

---

## Security Checklist

- [ ] Strong PostgreSQL password set
- [ ] Firewall rules configured
- [ ] PostgreSQL only accessible from local network
- [ ] Regular backups scheduled
- [ ] `.env` file not shared/committed
- [ ] Only trusted users have database access

---

## Next Steps

After deployment:

1. **Test thoroughly** with sample data
2. **Train team** on using web interface
3. **Set up BI dashboards** using provided views
4. **Schedule weekly imports** 
5. **Monitor verification queue** regularly
6. **Review reports** for insights

---

## Support

If you encounter issues:

1. Check error messages in PowerShell/terminal
2. Review logs in `reports/` folder
3. Verify all steps were completed
4. Check database with `psql`
5. Restart PostgreSQL and Flask services

## Appendix: Common Commands

```powershell
# Database
psql -U postgres -d academy2_0
\dt                          # List tables
\dv                          # List views
SELECT COUNT(*) FROM user_pii;  # Count users

# Import
python scripts/import_csv.py --file data.csv

# Verify
python scripts/verify_skillboost.py --limit 100

# Web Server
python app/main.py

# Certificates
python scripts/calculate_certificates.py

# Test Connection
python -c "from app.database import db_manager; db_manager.test_connection()"
```

---

**Deployment Complete!** 🎉

Your GenAI Academy 2.0 Records Management System is now ready to use.

