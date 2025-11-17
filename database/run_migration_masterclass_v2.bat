@echo off
REM Run master classes v2.0 migration
REM Adds new columns for comprehensive master class tracking

echo ================================================================
echo Running Master Classes V2.0 Migration
echo ================================================================
echo.
echo This will add new columns to the master_classes table:
echo - platform
echo - link
echo - total_duration
echo - watched_duration_updated_at
echo - watch_time
echo - live (validation status)
echo - recorded (validation status)
echo.
echo Press Ctrl+C to cancel or
pause

REM Load environment variables
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if "%%a"=="DB_HOST" set DB_HOST=%%b
    if "%%a"=="DB_PORT" set DB_PORT=%%b
    if "%%a"=="DB_NAME" set DB_NAME=%%b
    if "%%a"=="DB_USER" set DB_USER=%%b
    if "%%a"=="DB_PASSWORD" set DB_PASSWORD=%%b
)

echo.
echo Connecting to database: %DB_NAME% at %DB_HOST%:%DB_PORT%
echo.

REM Run migration
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f "database\migration_master_classes_v2.sql"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================================
    echo Migration completed successfully!
    echo ================================================================
    echo.
    echo The master_classes table has been updated.
    echo You can now import master class data with the new columns.
) else (
    echo.
    echo ================================================================
    echo Migration failed!
    echo ================================================================
    echo.
    echo Please check the error messages above.
)

echo.
pause

