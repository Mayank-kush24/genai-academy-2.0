@echo off
echo ============================================================
echo GenAI Academy 2.0 - Firewall Configuration
echo ============================================================
echo.
echo This script will configure Windows Firewall to allow:
echo   - Flask web app (port 5000)
echo   - PostgreSQL database (port 5432)
echo.
echo NOTE: This requires Administrator privileges
echo.
pause

echo.
echo Creating firewall rules...
echo.

:: Create rule for Flask app
netsh advfirewall firewall add rule name="Academy Web App" dir=in action=allow protocol=TCP localport=5000

:: Create rule for PostgreSQL
netsh advfirewall firewall add rule name="PostgreSQL Academy" dir=in action=allow protocol=TCP localport=5432

echo.
echo ============================================================
echo Firewall rules created successfully!
echo.
echo Team members can now access:
echo   - Web App: http://YOUR-IP:5000
echo   - Database: YOUR-IP:5432
echo.
echo To find your IP address, run: ipconfig
echo ============================================================
pause

