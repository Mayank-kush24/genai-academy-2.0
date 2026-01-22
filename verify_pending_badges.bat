@echo off
echo ============================================================
echo GenAI Academy 2.0 - Verify PENDING Skill Badges Only
echo ============================================================
echo.
echo This will:
echo   1. Mark all pending records with "-" links as invalid
echo   2. Verify ONLY PENDING badges (valid is NULL)
echo   3. Skip already verified or failed badges
echo.
cd /d "%~dp0"

echo Starting verification of pending badges...
echo Using 10 parallel workers for faster processing
echo.
echo You can stop anytime with Ctrl+C
echo Progress is saved - you can resume later
echo.
echo ============================================================
echo.

python scripts/verify_skillboost.py --badges-only --pending-only --workers 10

echo.
echo ============================================================
echo Verification completed!
echo ============================================================
pause

