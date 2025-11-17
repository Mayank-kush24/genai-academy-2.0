@echo off
echo ============================================================
echo GenAI Academy 2.0 - System Test
echo ============================================================
echo.

cd /d "%~dp0"

echo Running system diagnostics...
echo.

python scripts/test_connection.py

pause

