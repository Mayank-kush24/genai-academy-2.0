@echo off
REM Setup RBAC System for GenAI Academy 2.0

echo ============================================================
echo GenAI Academy 2.0 - RBAC System Setup
echo ============================================================
echo.

echo Step 1: Creating system_users table...
echo Please run the following SQL script manually:
echo   database/schema_users_rbac.sql
echo.
echo Press any key after you've run the SQL script...
pause >nul

echo.
echo Step 2: Creating default users...
python scripts\create_default_users.py

echo.
echo ============================================================
echo RBAC Setup Complete!
echo ============================================================
echo.
echo Default Login Credentials:
echo   Admin:   admin / Admin@123
echo   Manager: manager / Manager@123
echo   Viewer:  viewer / Viewer@123
echo.
echo Access the login page at:
echo   http://192.168.1.60:5000/login
echo.
echo IMPORTANT: Change default passwords after first login!
echo.
echo For detailed documentation, see:
echo   docs/RBAC_USER_MANAGEMENT_GUIDE.md
echo.
echo ============================================================
pause

