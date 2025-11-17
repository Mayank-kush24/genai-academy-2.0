# GenAI Academy 2.0 - Records Management System

A comprehensive system for managing user records, course completions, and masterclass attendance for GenAI Exchange Academy 2.0.

## Features

- **User PII Management** - Store and manage personal information for 100K+ users
- **Course Tracking** - Track 14 courses across 5 tracks with badge verification
- **Skillboost Verification** - Automated verification of Google Cloud Skills Boost badges and profiles
- **Masterclass Tracking** - Monitor attendance for 14 masterclasses (live/recorded)
- **Web Dashboard** - User-friendly interface for searching and viewing records
- **Automated Audit Trail** - Database triggers automatically log all changes
- **BI Integration** - Direct connections for Looker Studio and Power BI
- **Data Export** - Export data as CSV for external analysis

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     PostgreSQL Database                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │user_pii  │  │ courses  │  │skillboost│  │  master  │   │
│  │          │  │          │  │ profile  │  │ classes  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│                    │                                         │
│              ┌─────▼─────┐                                  │
│              │master_log │  (Auto-populated by triggers)    │
│              └───────────┘                                  │
└─────────────────────────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   ┌────▼─────┐   ┌─────▼──────┐   ┌────▼────┐
   │  Flask   │   │   CSV      │   │Skillboost│
   │  Web App │   │  Import    │   │Verifier │
   └──────────┘   └────────────┘   └──────────┘
        │
   ┌────▼────┐
   │  Team   │
   │ Access  │
   └─────────┘
```

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 14+
- Windows 10/11 (for local hosting)

### Installation

1. **Clone/Download the repository**

2. **Install PostgreSQL**
   - Download from [postgresql.org](https://www.postgresql.org/download/windows/)
   - Install with default settings
   - Remember the password you set for `postgres` user

3. **Create Database** (on remote server 192.168.1.60)
   ```powershell
   # Connect to remote PostgreSQL server
   psql -h 192.168.1.60 -U postgres
   
   # Create database
   CREATE DATABASE academy2_0;
   
   # Exit psql
   \q
   ```

4. **Run Database Schema**
   ```powershell
   psql -h 192.168.1.60 -U postgres -d academy2_0 -f database/schema.sql
   psql -h 192.168.1.60 -U postgres -d academy2_0 -f database/reference_data.sql
   ```

5. **Install Python Dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

6. **Configure Environment**
   ```powershell
   # Copy example env file
   copy .env.example .env
   
   # Edit .env and set your PostgreSQL password
   notepad .env
   ```

7. **Test Database Connection**
   ```powershell
   python -c "from app.database import db_manager; db_manager.initialize(); print('✓ Database connection successful!')"
   ```

## Usage

### 1. Import Initial Data

```powershell
python scripts/import_csv.py --file actioncenter_genaiacademy2_data_center_submissions_all.xlsx
```

This will:
- Import all user PII data
- Process course badge submissions
- Process Skillboost profile links
- Record masterclass attendance
- Generate import report in `reports/` folder

### 2. Run Verification

```powershell
# Verify all unverified records
python scripts/verify_skillboost.py

# Verify only badges
python scripts/verify_skillboost.py --badges-only

# Verify only profiles
python scripts/verify_skillboost.py --profiles-only

# Limit to first 100 records (for testing)
python scripts/verify_skillboost.py --limit 100
```

**Note:** Verification includes rate limiting (2.5 seconds between requests) to avoid being blocked by Google. For 1000 records, expect ~40-50 minutes.

### 3. Start Web Application

```powershell
python app/main.py
```

Access the application at: `http://localhost:5000`

**For team access:** Share your IP address (find with `ipconfig`), e.g., `http://192.168.1.100:5000`

### 4. Calculate Track Certificates

```powershell
# Get all certificate-eligible users
python scripts/calculate_certificates.py

# Check progress for specific user
python scripts/calculate_certificates.py --email user@example.com
```

## Weekly Workflow

### Step 1: Download New Submissions
Download the latest CSV/Excel file with weekly submissions from your data source.

### Step 2: Import Data
```powershell
cd "D:\Academy 2.0"
python scripts/import_csv.py --file data/weekly_submissions_2024_11_13.csv --verify
```

The `--verify` flag automatically runs verification after import.

### Step 3: Review Results
1. Check the import report in `reports/` folder
2. Open web application: `http://localhost:5000`
3. Go to **Verification Queue** to see pending/failed verifications
4. Review any errors or mismatches

### Step 4: Export for Dashboards (Optional)
If you update Looker Studio/Power BI manually:
1. Go to `http://localhost:5000/export`
2. Download latest CSV files
3. Upload to your BI tool

If using direct database connection, data updates automatically!

## Web Application Features

### Search Page (`/`)
- Search users by name, email, or phone
- Quick statistics dashboard
- Links to all features

### User Profile (`/user/<email>`)
- Complete user information
- All course badge submissions with verification status
- Skillboost profile links
- Masterclass attendance history

### Verification Queue (`/verification-queue`)
- Pending verifications (badges and profiles)
- Failed verifications with reasons
- Quick access to review items

### Reports (`/reports`)
- Overall statistics
- Course-wise verification status
- Masterclass attendance breakdown
- Recent database changes (audit log)

### Export (`/export`)
- Export users summary as CSV
- Export all course submissions
- Export masterclass attendance
- Ready for Excel, Google Sheets, or BI tools

## Configuration

### Environment Variables (`.env`)

```env
# Database (Remote PostgreSQL Server)
DB_HOST=192.168.1.60
DB_PORT=5432
DB_NAME=academy2_0
DB_USER=postgres
DB_PASSWORD=your_password

# Flask
FLASK_PORT=5000
FLASK_SECRET_KEY=your_secret_key

# Verification
RATE_LIMIT_DELAY=2.5          # Seconds between requests
VERIFICATION_RETRY_ATTEMPTS=3
VERIFICATION_TIMEOUT=10

# Logging
LOG_LEVEL=INFO
```

### Firewall Configuration (for team access)

**Windows Firewall Rule:**
```powershell
# Run as Administrator
New-NetFirewallRule -DisplayName "Academy Web App" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
```

**PostgreSQL Access (for BI tools):**
```powershell
New-NetFirewallRule -DisplayName "PostgreSQL Academy" -Direction Inbound -LocalPort 5432 -Protocol TCP -Action Allow
```

## BI Integration

See [docs/BI_INTEGRATION_GUIDE.md](docs/BI_INTEGRATION_GUIDE.md) for detailed instructions on connecting Looker Studio and Power BI.

**Quick Setup:**
- **Host:** `192.168.1.60` (remote PostgreSQL server)
- **Port:** `5432`
- **Database:** `academy2_0`
- **User:** `postgres`
- **Tables to use:** `v_user_summary`, `v_course_verification_status`, `v_masterclass_attendance`

## Database Schema

### Main Tables

1. **user_pii** - Personal information (email, name, phone, location, etc.)
2. **courses** - Course badge submissions with verification status
3. **skillboost_profile** - Google Cloud Skills Boost profile links
4. **master_classes** - Masterclass attendance (live/recorded)
5. **master_log** - Automated audit trail (triggers auto-populate)

### Views for BI

- `v_user_summary` - User overview with counts
- `v_course_verification_status` - Course-wise stats
- `v_masterclass_attendance` - Masterclass stats
- `v_track_completion` - Track progress per user
- `v_certificate_eligible` - Users eligible for certificates

## File Structure

```
D:\Academy 2.0\
├── app/
│   ├── database.py              # SQLAlchemy models
│   ├── main.py                  # Flask web application
│   ├── queries.py               # Database queries
│   └── templates/               # HTML templates
│       ├── base.html
│       ├── index.html
│       ├── search_results.html
│       ├── user_profile.html
│       ├── verification_queue.html
│       ├── reports.html
│       ├── export.html
│       └── error.html
├── database/
│   ├── schema.sql               # Database schema with triggers
│   └── reference_data.sql       # Tracks, courses, masterclass definitions
├── scripts/
│   ├── import_csv.py            # CSV import script
│   ├── verify_skillboost.py    # Verification script
│   └── calculate_certificates.py # Certificate calculation
├── docs/
│   └── BI_INTEGRATION_GUIDE.md  # BI integration documentation
├── data/                        # Place CSV files here
├── reports/                     # Generated reports
├── config.py                    # Configuration class
├── requirements.txt             # Python dependencies
├── .env                         # Environment variables (create from .env.example)
└── README.md                    # This file
```

## Troubleshooting

### Cannot Connect to Database

**Error:** `psycopg2.OperationalError: could not connect to server`

**Solutions:**
1. Verify PostgreSQL service is running:
   - Open Services (Win + R → `services.msc`)
   - Look for "postgresql-x64-XX"
   - Ensure it's "Running"

2. Check `.env` file has correct password

3. Test connection:
   ```powershell
   psql -U postgres -d academy2_0
   ```

### Import Errors

**Error:** `No module named 'pandas'`

**Solution:**
```powershell
pip install -r requirements.txt
```

**Error:** `FileNotFoundError: [Errno 2] No such file or directory`

**Solution:** Provide full path to CSV file
```powershell
python scripts/import_csv.py --file "D:\Downloads\data.csv"
```

### Verification Timeout

**Error:** `requests.exceptions.Timeout`

**Solution:**
- Increase timeout in `.env`: `VERIFICATION_TIMEOUT=20`
- Check your internet connection
- Some badge pages may be slow to load - these will be retried

### Web App Port Already in Use

**Error:** `Address already in use`

**Solution:**
1. Change port in `.env`: `FLASK_PORT=5001`
2. Or kill process using port 5000:
   ```powershell
   netstat -ano | findstr :5000
   taskkill /PID <PID> /F
   ```

## Maintenance

### Database Backup

```powershell
# Manual backup
pg_dump -U postgres -d academy2_0 -f "backup_academy2_0_%date:~-4,4%%date:~-10,2%%date:~-7,2%.sql"

# Schedule weekly backups using Windows Task Scheduler
```

### Clean Old Logs

```powershell
# Delete reports older than 30 days
forfiles /P reports /M *.txt /D -30 /C "cmd /c del @path"
```

### Update Course/Masterclass Definitions

Edit `database/reference_data.sql` and re-run:
```powershell
psql -U postgres -d academy2_0 -f database/reference_data.sql
```

## Security Best Practices

1. **Change Default Password** - Don't use default PostgreSQL password
2. **Firewall Rules** - Only allow connections from trusted IPs
3. **Regular Backups** - Schedule weekly database backups
4. **Keep Updated** - Update Python packages regularly
5. **Limit Access** - Create read-only database users for BI tools
6. **Monitor Logs** - Review `master_log` table regularly

## Support

For issues or questions:

1. Check this README
2. Review [BI_INTEGRATION_GUIDE.md](docs/BI_INTEGRATION_GUIDE.md)
3. Check database logs
4. Test individual components:
   - Database: `python -c "from app.database import db_manager; db_manager.test_connection()"`
   - Import: Run with `--limit 10` for testing
   - Web app: Check console output for errors

## License

Internal use for GenAI Exchange Academy 2.0

---

**Version:** 1.0  
**Last Updated:** November 2024

