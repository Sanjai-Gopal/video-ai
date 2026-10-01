@echo off
REM Quick run script for VideoAI

cd /d "%~dp0"

if not exist venv (
    echo Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo.
echo VideoAI - Choose an option:
echo.
echo 1. Test content generation only
echo 2. Run one full cycle (create + post)
echo 3. Run scheduler (daily at 10 AM)
echo 4. View weekly analytics report
echo 5. View monthly analytics report
echo 6. Update analytics from APIs
echo.

set /p choice="Enter choice (1-6): "

if "%choice%"=="1" python src\orchestrator.py test-concept
if "%choice%"=="2" python src\orchestrator.py run
if "%choice%"=="3" python src\orchestrator.py schedule
if "%choice%"=="4" python src\orchestrator.py report weekly
if "%choice%"=="5" python src\orchestrator.py report monthly
if "%choice%"=="6" python src\orchestrator.py update-analytics

echo.
pause