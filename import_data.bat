@echo off
echo ============================================================
echo GenAI Academy 2.0 - Data Import
echo ============================================================
echo.

cd /d "%~dp0"

if "%~1"=="" (
    echo ERROR: No file specified
    echo.
    echo Usage: import_data.bat path\to\datafile.csv
    echo Example: import_data.bat data\weekly_submissions.xlsx
    echo.
    pause
    exit /b 1
)

echo Importing from: %~1
echo.
echo This may take several minutes...
echo.

python scripts/import_csv.py --file "%~1"

echo.
echo ============================================================
echo Import completed! Check the report in reports\ folder
echo ============================================================
pause

