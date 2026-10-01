@echo off
REM Quick run script for AIEntertainer

cd /d "%~dp0"

if not exist venv (
    echo Virtual environment not found. Run setup.bat first.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

echo.
echo AIEntertainer - Choose an option:
echo.
echo 1. Test script generation only
echo 2. Run one cycle (create + post 1 video)
echo 3. Run daily batch (4 videos)
echo 4. Start scheduler (runs 4x/day automatically)
echo 5. View weekly analytics report
echo 6. View monthly analytics report
echo 7. Update analytics from APIs
echo.

set /p choice="Enter choice (1-7): "

if "%choice%"=="1" python main.py test-script
if "%choice%"=="2" python main.py run
if "%choice%"=="3" python main.py batch
if "%choice%"=="4" python main.py schedule
if "%choice%"=="5" python main.py report weekly
if "%choice%"=="6" python main.py report monthly
if "%choice%"=="7" python main.py update-analytics

echo.
pause