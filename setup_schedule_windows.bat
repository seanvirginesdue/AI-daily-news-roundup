@echo off
REM ============================================================
REM  AI Daily News Roundup — Windows Task Scheduler Setup
REM  Runs main.py every day at 8:00 AM
REM  Run this file ONCE as Administrator
REM ============================================================

set TASK_NAME=AI-Daily-News-Roundup
set SCRIPT_DIR=%~dp0
set PYTHON_PATH=python

REM Delete old task if it exists
schtasks /Delete /TN "%TASK_NAME%" /F 2>nul

REM Create new daily task at 08:00
schtasks /Create ^
  /TN "%TASK_NAME%" ^
  /TR "\"%PYTHON_PATH%\" \"%SCRIPT_DIR%main.py\"" ^
  /SC DAILY ^
  /ST 08:00 ^
  /RU "%USERNAME%" ^
  /RL HIGHEST ^
  /F

echo.
echo Task "%TASK_NAME%" created successfully.
echo It will run every day at 08:00 AM.
echo.
pause
