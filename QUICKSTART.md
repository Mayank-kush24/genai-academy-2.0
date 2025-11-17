# Quick Start Guide

Get the GenAI Academy 2.0 Records Management System up and running in 15 minutes.

---

## Prerequisites

- Windows 10/11
- PostgreSQL 15+ installed
- Python 3.9+ installed

---

## 5-Step Setup

### 1. Create Database (on 192.168.1.60)

```powershell
psql -h 192.168.1.60 -U postgres
CREATE DATABASE academy2_0;
\q
```

### 2. Load Schema

```powershell
cd "D:\Academy 2.0"
psql -h 192.168.1.60 -U postgres -d academy2_0 -f database/schema.sql
psql -h 192.168.1.60 -U postgres -d academy2_0 -f database/reference_data.sql
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure

```powershell
copy .env.example .env
notepad .env
```

Edit `.env` - Set your PostgreSQL password:
```
DB_PASSWORD=your_password_here
```

Save and close.

### 5. Import Data & Start

```powershell
# Import your data
python scripts/import_csv.py --file your_data_file.xlsx

# Start web server
python app/main.py
```

**Access:** `http://localhost:5000`

---

## Weekly Workflow

```powershell
# 1. Import new data
python scripts/import_csv.py --file weekly_data.csv

# 2. Run verification
python scripts/verify_skillboost.py

# 3. Access via browser
# http://localhost:5000
```

---

## Team Access

1. Find your IP:
   ```powershell
   ipconfig
   ```

2. Add firewall rule (as Administrator):
   ```powershell
   New-NetFirewallRule -DisplayName "Academy Web App" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
   ```

3. Share with team: `http://YOUR-IP:5000`

---

## Common Commands

```powershell
# Search user
# Visit: http://localhost:5000

# Export data
# Visit: http://localhost:5000/export

# Check certificates
python scripts/calculate_certificates.py

# View reports
# Visit: http://localhost:5000/reports
```

---

## Troubleshooting

**Can't connect to database?**
- Check PostgreSQL service is running
- Verify password in `.env`

**Port 5000 in use?**
- Change `FLASK_PORT=5001` in `.env`

**Import failed?**
- Use full file path
- Check file format (CSV or XLSX)

---

## Need More Help?

See complete guides:
- [README.md](README.md) - Full documentation
- [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) - Step-by-step deployment
- [docs/BI_INTEGRATION_GUIDE.md](docs/BI_INTEGRATION_GUIDE.md) - BI tool setup

---

**That's it!** You're ready to manage Academy records efficiently.

