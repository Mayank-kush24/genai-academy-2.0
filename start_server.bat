@echo off
echo ============================================================
echo GenAI Academy 2.0 Records Management System
echo ============================================================
echo.
echo Starting Flask web server...
echo Access at: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server
echo ============================================================
echo.

cd /d "%~dp0"
python app/main.py

pause

