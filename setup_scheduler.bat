@echo off
setlocal

set TASK_NAME=AI Daily News Roundup
set TASK_DIR=C:\Users\seand\AI daily news\AI-daily-news-roundup
set LOG_DIR=%TASK_DIR%\logs

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

schtasks /delete /tn "%TASK_NAME%" /f 2>nul

schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "cmd /c \"cd /d \"%TASK_DIR%\" && python main.py >> \"%LOG_DIR%\scheduler.log\" 2>&1\"" ^
  /sc daily ^
  /st 20:00 ^
  /ru "%USERNAME%" ^
  /rl HIGHEST ^
  /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Task created successfully.
    echo Runs every day at 8:00 PM Philippine Time.
    echo Logs saved to: %LOG_DIR%\scheduler.log
) else (
    echo.
    echo Failed to create task. Make sure you ran this as Administrator.
)

pause
