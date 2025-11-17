@echo off
echo ============================================================
echo GenAI Academy 2.0 - Skillboost Verification (Parallel)
echo ============================================================
echo.

cd /d "%~dp0"

echo Starting parallel verification process...
echo Using 10 parallel workers for faster processing
echo Estimated time: 5-10 minutes for ~1000 records
echo (with intelligent rate limiting)
echo.
echo You can stop anytime with Ctrl+C
echo Progress is saved - you can resume later
echo.
echo ============================================================
echo.

python scripts/verify_skillboost.py --workers 10

echo.
echo ============================================================
echo Verification completed!
echo ============================================================
pause

