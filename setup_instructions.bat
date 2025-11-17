@echo off
echo ============================================================
echo GenAI Academy 2.0 - Quick Setup Instructions
echo ============================================================
echo.
echo IMPORTANT: Your database is on a REMOTE SERVER
echo Database: 192.168.1.60:5432
echo.
echo ============================================================
echo STEP-BY-STEP SETUP
echo ============================================================
echo.
echo 1. Verify Network Connectivity
echo    PowerShell^> Test-NetConnection -ComputerName 192.168.1.60 -Port 5432
echo.
echo 2. Configure .env file
echo    - Copy .env.example to .env (or edit existing .env)
echo    - Set DB_HOST=192.168.1.60
echo    - Set DB_PASSWORD=your_actual_password
echo.
echo 3. Install Python Dependencies
echo    pip install -r requirements.txt
echo.
echo 4. Create Database (if not exists)
echo    psql -h 192.168.1.60 -U postgres -c "CREATE DATABASE academy2_0;"
echo.
echo 5. Load Database Schema
echo    psql -h 192.168.1.60 -U postgres -d academy2_0 -f database\schema.sql
echo    psql -h 192.168.1.60 -U postgres -d academy2_0 -f database\reference_data.sql
echo.
echo 6. Test System
echo    test_system.bat
echo.
echo 7. Import Data
echo    import_data.bat your_data_file.xlsx
echo.
echo 8. Start Web Server
echo    start_server.bat
echo.
echo ============================================================
echo For detailed instructions, see:
echo - README.md
echo - QUICKSTART.md
echo - REMOTE_DB_SETUP.md
echo ============================================================
pause

