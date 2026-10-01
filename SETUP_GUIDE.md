# VideoAI Setup Guide

## Overview
This is a **completely free, local-first** AI video creation pipeline that:
- Generates viral short-form content ideas using local LLMs (Ollama)
- Creates videos using local AI video generation (ComfyUI + AnimateDiff/SVD)
- Adds voiceover using local TTS (Coqui/Bark/Windows built-in)
- Assembles final videos with captions using FFmpeg
- Posts to YouTube Shorts, Instagram Reels, Facebook Reels
- Tracks analytics in local SQLite database
- Runs on a schedule - zero ongoing costs

## Prerequisites

### 1. Hardware Requirements
- **NVIDIA GPU with 8GB+ VRAM** (RTX 3070/4070 or better recommended)
- 16GB+ system RAM
- 50GB+ free disk space for models

### 2. Software Requirements
- **Windows 10/11** (this guide)
- **Python 3.10 or 3.11** (not 3.12+ yet for some packages)
- **Git** for cloning repositories
- **FFmpeg** in system PATH

## Installation Steps

### Step 1: Install FFmpeg
```powershell
# Option A: winget (recommended)
winget install Gyan.FFmpeg

# Option B: Chocolatey
choco install ffmpeg

# Option C: Manual - download from https://ffmpeg.org/download.html
# Extract and add bin folder to system PATH
```
Verify: `ffmpeg -version`

### Step 2: Install Ollama
1. Download from https://ollama.ai/download/windows
2. Install and run Ollama
3. Pull a model (choose one):
   ```powershell
   ollama pull llama3.1:8b      # Best balance (4.7GB)
   ollama pull mistral:7b       # Good alternative (4.1GB)
   ollama pull phi3:3.8b        # Smallest, fastest (2.3GB)
   ```
4. Verify: `ollama list` and `curl http://localhost:11434/api/tags`

### Step 3: Install ComfyUI
```powershell
# Clone ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI

# Install dependencies
pip install -r requirements.txt

# Install AnimateDiff custom node (required for video)
git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved custom_nodes/ComfyUI-AnimateDiff-Evolved
cd custom_nodes/ComfyUI-AnimateDiff-Evolved
pip install -r requirements.txt

# Install VideoHelperSuite (for video output)
cd ../..
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite custom_nodes/ComfyUI-VideoHelperSuite
cd custom_nodes/ComfyUI-VideoHelperSuite
pip install -r requirements.txt
```

### Step 4: Download Models for ComfyUI
Place in `ComfyUI/models/checkpoints/`:
- **SDXL Base**: `sd_xl_base_1.0.safetensors` (from Hugging Face)

Place in `ComfyUI/models/animatediff/`:
- **AnimateDiff v1.5 v2**: `animatediff_motion_module_v15_v2.ckpt` (from Hugging Face)

Place in `ComfyUI/models/vae/`:
- **SDXL VAE**: `sdxl_vae.safetensors` (optional, uses built-in if missing)

### Step 5: Setup VideoAI Project
```powershell
# Navigate to project
cd C:\Projects\VideoAI

# Run setup script
.\setup.bat

# Or manually:
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Step 6: Configure Credentials

#### YouTube API
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project → Enable YouTube Data API v3
2. Create OAuth 2.0 credentials (Desktop app)
3. Download JSON → Save as `credentials/youtube_client_secrets.json`
4. First run will create `youtube_token.json` automatically

#### Instagram (Meta Graph API)
1. Create [Meta Developer App](https://developers.facebook.com/)
2. Add Instagram Basic Display + Instagram Content Publishing
3. Get long-lived access token (60 days, refreshable)
4. Save token to `credentials/ig_access_token.txt`
5. Get Instagram Business Account ID → Update `config.yaml`

#### Facebook
1. Same Meta App → Add Facebook Pages permissions
2. Get Page Access Token (long-lived)
3. Save to `credentials/fb_access_token.txt`
4. Get Page ID → Update `config.yaml`

### Step 7: Configure config.yaml
Edit `config.yaml` with your settings:
- Ollama model (llama3.1:8b recommended)
- ComfyUI host/port (default localhost:8188)
- Social media credentials paths
- Schedule time
- Niches/topics

### Step 8: Start Services
```powershell
# Terminal 1: Start Ollama (if not running as service)
ollama serve

# Terminal 2: Start ComfyUI
cd ComfyUI
python main.py --listen 127.0.0.1 --port 8188

# Terminal 3: Test VideoAI
cd C:\Projects\VideoAI
.\venv\Scripts\activate
python src\orchestrator.py test-concept
```

## Running the Pipeline

### One-time run
```powershell
python src\orchestrator.py run
```

### Scheduled daily runs
```powershell
python src\orchestrator.py schedule
```

### View analytics report
```powershell
python src\orchestrator.py report weekly
python src\orchestrator.py report monthly
```

## Monetization Strategy (Student-Friendly)

### Immediate (0 subscribers):
1. **Affiliate Marketing** - Add affiliate links in descriptions
   - AI tools (Notion, Jasper, etc.) - 20-30% recurring
   - Student finance apps (YNAB, Mint alternatives)
   - Tech gear (Amazon Associates 1-4%)

2. **Lead Generation** - Build email list for future products
   - Free PDF: "10 AI Tools for Student Productivity"
   - Free course: "How to Study with AI"

### Medium-term (1k+ subscribers):
3. **YouTube Partner Program** - Ad revenue from Shorts
   - Need 10M Shorts views OR 1k subs + 4k watch hours
   - CPM: $0.01-$0.05 per 1000 views (Shorts)

4. **Sponsorships** - AI tool companies pay $50-500/video

### Long-term:
5. **Digital Products** - Courses, templates, Notion systems
6. **Consulting** - AI workflow automation for businesses

## Recommended Niches for Students (High CPM + Affiliate Friendly)
1. **AI Productivity Tools** - Review new AI tools weekly
2. **Student Finance** - Budgeting, side hustles, investing
3. **Tech Career Prep** - Resume building, interviews, skills
4. **Study Hacks** - AI-assisted learning, focus techniques
5. **Remote Work/Freelancing** - Upwork, Fiverr, client acquisition

## Troubleshooting

### ComfyUI Out of Memory
- Reduce `width`/`height` in config.yaml (576x1024 → 512x896)
- Use `--lowvram` flag when starting ComfyUI
- Close other GPU apps

### Ollama Slow
- Use smaller model: `phi3:3.8b` or `gemma2:2b`
- Ensure GPU acceleration: `ollama run llama3.1:8b --verbose`

### YouTube Upload Fails
- Check OAuth token validity (re-run to refresh)
- Verify video meets Shorts requirements (<60s, 9:16)

### Instagram/Facebook Post Fails
- Tokens expire - regenerate long-lived tokens
- Check Business Account ID and Page ID are correct

## Cost Breakdown
| Component | Cost |
|-----------|------|
| Ollama (LLM) | FREE |
| ComfyUI (Video) | FREE |
| Coqui TTS (Voice) | FREE |
| FFmpeg (Assembly) | FREE |
| YouTube/IG/FB APIs | FREE |
| **Total Monthly** | **$0** |

## Expected Timeline
- **Week 1**: Setup, test pipeline, first 3-5 videos
- **Month 1**: 30 videos, ~100-500 views each, first affiliate clicks
- **Month 3**: 90 videos, ~1k-5k views each, $50-200/mo affiliate
- **Month 6**: 180 videos, compounding views, $200-1000/mo
- **Year 1**: 365+ videos, potential YPP eligibility, $500-5000/mo

## Support
- Check `data/logs/videoai.log` for errors
- ComfyUI logs in its console
- Ollama logs: `ollama serve` output

## License
MIT - Free to use, modify, distribute