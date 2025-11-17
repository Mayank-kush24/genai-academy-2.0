# Remote Database Configuration

Your PostgreSQL database is hosted on a **remote server** at `192.168.1.60:5432`.

## Important Notes

### 1. Database Connection

Since the database is remote, all connections use the IP address instead of `localhost`:

```
Host: 192.168.1.60
Port: 5432
Database: academy2_0
```

### 2. Configuration File

Your `.env` file should be configured as:

```env
DB_HOST=192.168.1.60
DB_PORT=5432
DB_NAME=academy2_0
DB_USER=postgres
DB_PASSWORD=your_actual_password
```

### 3. PostgreSQL Commands

When running PostgreSQL commands, always include the `-h 192.168.1.60` parameter:

```powershell
# Connect to database
psql -h 192.168.1.60 -U postgres -d academy2_0

# Run schema
psql -h 192.168.1.60 -U postgres -d academy2_0 -f database/schema.sql

# Check connection
psql -h 192.168.1.60 -U postgres -c "SELECT version();"
```

### 4. Network Requirements

For the system to work properly:

✅ **Your machine must have network access to 192.168.1.60:5432**
- Verify connectivity: `Test-NetConnection -ComputerName 192.168.1.60 -Port 5432`
- If blocked, check firewalls on both machines

✅ **PostgreSQL server must allow remote connections**
- Server's `postgresql.conf` must have: `listen_addresses = '*'` or include your IP
- Server's `pg_hba.conf` must allow your IP:
  ```
  host    academy2_0    postgres    192.168.1.0/24    md5
  ```

✅ **Both machines should be on the same network** (192.168.1.x)

### 5. Testing Connection

Test the database connection:

```powershell
# Using test script
python scripts/test_connection.py

# Using psql
psql -h 192.168.1.60 -U postgres -c "SELECT 1;"
```

Expected output: Connection successful

### 6. Firewall Configuration

**Your Local Machine (where the app runs):**
- No special PostgreSQL firewall rules needed
- Only need Flask port 5000 open for team access:
  ```powershell
  New-NetFirewallRule -DisplayName "Academy Web App" -Direction Inbound -LocalPort 5000 -Protocol TCP -Action Allow
  ```

**Remote PostgreSQL Server (192.168.1.60):**
- Must allow incoming connections on port 5432
- From your IP or entire subnet (192.168.1.0/24)

### 7. Application Usage

Once configured, all application scripts work normally:

```powershell
# Import data (connects to remote DB automatically)
python scripts/import_csv.py --file data.csv

# Verify badges (connects to remote DB automatically)
python scripts/verify_skillboost.py

# Start web server (connects to remote DB automatically)
python app/main.py
```

The application reads `DB_HOST=192.168.1.60` from `.env` and handles the remote connection transparently.

### 8. BI Tool Configuration

When connecting Looker Studio or Power BI:

**Looker Studio:**
- Host: `192.168.1.60`
- Port: `5432`
- Database: `academy2_0`

**Power BI:**
- Server: `192.168.1.60:5432`
- Database: `academy2_0`

### 9. Performance Considerations

Remote database connections are slightly slower than localhost due to network latency:

- **Import:** May take 5-10% longer
- **Web UI:** Minimal impact (queries are fast)
- **Verification:** No impact (rate-limited by Google, not database)

For optimal performance:
- Ensure stable network connection
- Use wired connection if possible (not WiFi)
- Keep both machines on same local network

### 10. Backup Strategy

Since database is remote, you have two backup options:

**Option A: Remote Backup (on database server)**
```powershell
# SSH or RDP to 192.168.1.60
pg_dump -U postgres -d academy2_0 -f backup_$(date +%Y%m%d).sql
```

**Option B: Local Backup (from your machine)**
```powershell
# Run from your machine, saves locally
"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe" -h 192.168.1.60 -U postgres -d academy2_0 -f backups\backup_%date%.sql
```

The `backup_database.bat` script has been set up but you'll need to update it with the `-h 192.168.1.60` parameter.

### 11. Common Issues

**Issue:** "could not connect to server"
- **Check:** Network connectivity to 192.168.1.60
- **Check:** PostgreSQL service running on remote server
- **Check:** Firewall allows port 5432

**Issue:** "password authentication failed"
- **Check:** Correct password in `.env`
- **Check:** User has access rights on remote server

**Issue:** "no pg_hba.conf entry for host"
- **Fix:** Remote server's `pg_hba.conf` needs to allow your IP
- **Admin task:** Done on 192.168.1.60 server

### 12. Security Notes

🔒 **Important Security Considerations:**

1. **Network Security**
   - Database is accessible over network
   - Ensure you're on a trusted network (not public WiFi)
   - Use VPN if accessing from outside local network

2. **Credentials**
   - Keep `.env` file secure
   - Never commit `.env` to version control
   - Use strong PostgreSQL passwords

3. **Access Control**
   - Only authorized users should have database credentials
   - Consider read-only users for BI tools
   - Monitor database access logs

---

## Quick Reference

```
Database Server: 192.168.1.60:5432
Database Name: academy2_0
Application: Your machine (D:\Academy 2.0\)
Web Access: http://YOUR-LOCAL-IP:5000
```

**All systems are configured to use this remote database setup.**

