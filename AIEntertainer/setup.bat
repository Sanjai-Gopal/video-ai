@echo off
REM AIEntertainer Setup Script for Windows
REM Run as Administrator for best results

echo ========================================
echo AIEntertainer - Automated Roaster Channel
echo ========================================
echo.

REM Check Python version
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python not found. Please install Python 3.11 from python.org
    pause
    exit /b 1
)

echo.
echo [1/7] Creating virtual environment...
python -m venv venv
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo.
echo [2/7] Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [3/7] Upgrading pip...
python -m pip install --upgrade pip

echo.
echo [4/7] Installing Python dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo WARNING: Some packages failed. Check output above.
)

echo.
echo [5/7] Checking FFmpeg...
where ffmpeg >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo FFmpeg not found in PATH.
    echo Install: winget install Gyan.FFmpeg
) else (
    echo FFmpeg found:
    ffmpeg -version | findstr "ffmpeg version"
)

echo.
echo [6/7] Checking Ollama...
ollama --version >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Ollama not found. Install from https://ollama.ai/download/windows
) else (
    echo Ollama found.
    echo Pulling llama3.1:8b model...
    ollama pull llama3.1:8b
)

echo.
echo [7/7] Creating credentials directory structure...
if not exist credentials mkdir credentials
echo.
echo REQUIRED: Add your API credentials to credentials/ folder:
echo.
echo   YouTube (Google Cloud Console):
echo     - youtube_client_secrets.json (OAuth 2.0 Desktop app)
echo     - youtube_token.json (auto-created on first run)
echo.
echo   Instagram (Meta Developer):
echo     - ig_access_token.txt (long-lived access token)
echo     - Update config.yaml with YOUR_IG_BUSINESS_ACCOUNT_ID
echo.
echo   TikTok (TikTok Developer):
echo     - tiktok_access_token.txt
echo     - tiktok_client_key.txt
echo     - tiktok_client_secret.txt
echo.
echo COMFYUI SETUP (separate):
echo   1. git clone https://github.com/comfyanonymous/ComfyUI
echo   2. cd ComfyUI && pip install -r requirements.txt
echo   3. Install custom nodes:
echo      git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved custom_nodes/ComfyUI-AnimateDiff-Evolved
echo      git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite custom_nodes/ComfyUI-VideoHelperSuite
echo   4. Download models to ComfyUI/models/:
echo      - checkpoints/sd_xl_base_1.0.safetensors
echo      - animatediff/animatediff_motion_module_v15.ckpt
echo   5. Run: python main.py --listen 127.0.0.1 --port 8188
echo.

echo ========================================
echo Setup complete!
echo ========================================
echo.
echo NEXT STEPS:
echo 1. Add credentials to credentials/ folder
echo 2. Update config.yaml with your Instagram Business Account ID
echo 3. Start Ollama: ollama serve
echo 4. Start ComfyUI (in separate terminal)
echo 5. Test: python main.py test-script
echo 6. Run once: python main.py run
echo 7. Schedule: python main.py schedule
echo.
pause