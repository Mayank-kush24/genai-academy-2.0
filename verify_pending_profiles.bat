@echo off
echo ============================================================
echo GenAI Academy 2.0 - Verify PENDING Skill Boost Profiles Only
echo ============================================================
echo.
echo This will:
echo   1. Mark all pending records with "-" links as invalid
echo   2. Verify ONLY PENDING profiles (valid is NULL)
echo   3. Skip already verified or failed profiles
echo.
cd /d "%~dp0"

echo Starting verification of pending profiles...
echo Using 10 parallel workers for faster processing
echo.
echo You can stop anytime with Ctrl+C
echo Progress is saved - you can resume later
echo.
echo ============================================================
echo.

python scripts/verify_skillboost.py --profiles-only --pending-only --workers 10

echo.
echo ============================================================
echo Verification completed!
echo ============================================================
pause

