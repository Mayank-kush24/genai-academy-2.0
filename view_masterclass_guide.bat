@echo off
REM Quick access to Master Class documentation

echo.
echo ================================================================
echo Master Class System Documentation
echo ================================================================
echo.
echo 1. Quick Reference Card
echo 2. Full System Guide
echo 3. Exit
echo.
choice /C 123 /N /M "Select option: "

if errorlevel 3 exit
if errorlevel 2 goto fullguide
if errorlevel 1 goto quickref

:quickref
cls
type docs\MASTERCLASS_QUICK_REFERENCE.md
echo.
echo.
pause
exit

:fullguide
start docs\MASTERCLASS_SYSTEM_GUIDE.md
exit

