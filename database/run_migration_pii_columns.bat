@echo off
REM Migration script to add 5 new PII columns to user_pii table
REM Run this script to add: organization_name, domain, designation_years_exp
REM and update: class_stream, degree_passout_year to VARCHAR(1000)

echo ========================================
echo GenAI Academy 2.0 - PII Columns Migration
echo ========================================
echo.

REM Load environment variables from .env file if it exists
if exist "..\\.env" (
    for /f "tokens=1,2 delims==" %%a in (..\.env) do (
        set %%a=%%b
    )
)

REM Check if psql is available
where psql >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: psql command not found. Please ensure PostgreSQL is installed and in PATH.
    pause
    exit /b 1
)

echo Running migration to add PII columns...
echo.

REM Run migration SQL
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -f migration_add_pii_columns.sql

if %errorlevel% equ 0 (
    echo.
    echo ========================================
    echo Migration completed successfully!
    echo ========================================
    echo.
    echo New columns added:
    echo   - organization_name (College/School/Company/Startup Name)
    echo   - domain (Domain)
    echo   - designation_years_exp (Designation with Years of Experience)
    echo.
    echo Updated columns:
    echo   - class_stream (now VARCHAR 1000)
    echo   - degree_passout_year (now VARCHAR 1000)
    echo.
) else (
    echo.
    echo ERROR: Migration failed. Please check the error messages above.
)

pause

