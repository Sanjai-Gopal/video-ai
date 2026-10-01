@echo off
REM VideoAI Setup Script for Windows
REM Run as Administrator for best results

echo ========================================
echo VideoAI - Fully Local Free Content Pipeline
echo ========================================
echo.

REM Check Python version
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found. Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

echo.
echo [1/6] Creating virtual environment...
python -m venv venv
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo.
echo [2/6] Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [3/6] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo [4/6] Installing Python dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Some packages failed to install. Check output above.
)

echo.
echo [5/6] Checking FFmpeg...
where ffmpeg >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo FFmpeg not found in PATH.
    echo Please install FFmpeg from https://ffmpeg.org/download.html
    echo Add it to your system PATH.
    echo.
    echo You can also install via winget: winget install Gyan.FFmpeg
    echo Or chocolatey: choco install ffmpeg
) else (
    echo FFmpeg found: 
    ffmpeg -version | findstr "ffmpeg version"
)

echo.
echo [6/6] Creating credentials directory...
if not exist credentials mkdir credentials
echo.
echo Please add your OAuth credentials to the credentials/ folder:
echo   - youtube_client_secrets.json (from Google Cloud Console)
echo   - youtube_token.json (will be created on first run)
echo   - ig_access_token.txt (Instagram long-lived access token)
echo   - fb_access_token.txt (Facebook page access token)
echo.
echo See SETUP_GUIDE.md for detailed instructions.

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo Next steps:
echo 1. Install Ollama: https://ollama.ai
echo 2. Pull a model: ollama pull llama3.1:8b
echo 3. Install ComfyUI: git clone https://github.com/comfyanonymous/ComfyUI
echo 4. Install ComfyUI dependencies and AnimateDiff custom nodes
echo 5. Configure config.yaml with your settings
echo 6. Run: python src\orchestrator.py test-concept
echo.
pause