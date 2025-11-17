@echo off
echo ============================================================
echo GenAI Academy 2.0 - Database Backup
echo ============================================================
echo.

cd /d "%~dp0"

:: Create backup directory if it doesn't exist
if not exist "backups" mkdir backups

:: Generate filename with timestamp
set TIMESTAMP=%date:~-4,4%%date:~-10,2%%date:~-7,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%
set FILENAME=academy2_0_%TIMESTAMP%.sql

echo Backing up database from remote server (192.168.1.60) to: backups\%FILENAME%
echo.

:: Run pg_dump with remote host (adjust path if PostgreSQL is installed elsewhere)
"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe" -h 192.168.1.60 -U postgres -d academy2_0 -f "backups\%FILENAME%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo Backup completed successfully!
    echo File: backups\%FILENAME%
    echo ============================================================
) else (
    echo.
    echo ============================================================
    echo Backup failed! Please check PostgreSQL is running
    echo and the path to pg_dump.exe is correct.
    echo ============================================================
)

pause

