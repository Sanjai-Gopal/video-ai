# AIEntertainer - Fully Automated Roaster/Commentator Channel

**Creates and posts 4 roast videos/day to YouTube Shorts, Instagram Reels, TikTok — completely free, runs on your 8GB GPU.**

## What It Does

```
┌─────────────────────────────────────────────────────────────┐
│  DAILY AUTOMATED PIPELINE (4 videos/day)                   │
├─────────────────────────────────────────────────────────────┤
│  1. FINDS TRENDING CRINGE → 2. WRITES ROAST SCRIPT         │
│  3. GENERATES AI VIDEO CLIPS → 4. EDITS WITH CAPTIONS      │
│  5. POSTS TO YT/IG/TIKTOK → 6. TRACKS ANALYTICS            │
└─────────────────────────────────────────────────────────────┘
```

## Character: **RoastBot** 🤖
- Cynical Indian Gen Z with glasses & hoodie
- Roasts: fake gurus, Bollywood logic, influencer scams, viral challenges
- Hinglish (Hindi + English), savage but relatable
- Catchphrases: *"Bhai kya dekh raha hai"*, *"Yeh kya bakwas hai"*

## Requirements

| Component | Spec |
|-----------|------|
| **GPU** | NVIDIA 8GB+ VRAM (RTX 3070/4070+) |
| **RAM** | 16GB+ |
| **Storage** | 50GB free |
| **OS** | Windows 10/11 |
| **Python** | 3.11 (not 3.12+) |

## Quick Start

```powershell
# 1. Clone & setup
cd C:\Projects
git clone <this-repo> AIEntertainer
cd AIEntertainer
.\setup.bat

# 2. Add API credentials to credentials/ folder (see below)

# 3. Start services (3 terminals):
# Terminal 1: Ollama
ollama serve

# Terminal 2: ComfyUI
cd C:\Projects\ComfyUI
python main.py --listen 127.0.0.1 --port 8188

# Terminal 3: Test AIEntertainer
cd C:\Projects\AIEntertainer
.\run.bat
# Choose option 1: Test script generation
# Choose option 2: Run one cycle
# Choose option 4: Start scheduler (runs forever)
```

## Required API Credentials

### YouTube (Required)
1. [Google Cloud Console](https://console.cloud.google.com/) → New Project
2. Enable **YouTube Data API v3**
3. Create **OAuth 2.0 Client ID** (Desktop app)
4. Download JSON → `credentials/youtube_client_secrets.json`
5. First run creates `youtube_token.json` automatically

### Instagram (Required)
1. [Meta Developer](https://developers.facebook.com/) → Create App
2. Add **Instagram Basic Display** + **Instagram Content Publishing**
3. Get **long-lived access token** (60 days)
4. Save to `credentials/ig_access_token.txt`
5. Get **Instagram Business Account ID** → update `config.yaml`

### TikTok (Required)
1. [TikTok Developer](https://developers.tiktok.com/) → Create App
2. Add **Video Upload** scope
3. Get access token, client key, client secret
4. Save to `credentials/tiktok_access_token.txt`, `tiktok_client_key.txt`, `tiktok_client_secret.txt`

## ComfyUI Setup (Separate Folder)

```powershell
# 1. Clone
git clone https://github.com/comfyanonymous/ComfyUI
cd ComfyUI

# 2. Install deps (use CUDA PyTorch!)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt

# 3. Custom nodes
git clone https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved custom_nodes/ComfyUI-AnimateDiff-Evolved
git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite custom_nodes/ComfyUI-VideoHelperSuite
pip install -r custom_nodes/ComfyUI-VideoHelperSuite/requirements.txt

# 4. Models (download in browser, place in ComfyUI/models/)
# checkpoints/sd_xl_base_1.0.safetensors
#   https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors
# animatediff/animatediff_motion_module_v15.ckpt
#   https://huggingface.co/guoyww/animatediff/resolve/main/animatediff_motion_module_v15.ckpt

# 5. Run
python main.py --listen 127.0.0.1 --port 8188
```

## Commands

```bash
python main.py test-script      # Test script generation
python main.py run              # Create & post 1 video
python main.py batch            # Create & post 4 videos (daily)
python main.py schedule         # Start auto-scheduler (4x/day at 9AM, 1PM, 6PM, 9PM)
python main.py report weekly    # Analytics report
python main.py update-analytics # Fetch view counts
```

## Monetization

| Timeline | Revenue Source | Target |
|----------|---------------|--------|
| Month 1 | Affiliate links (VPN, courses, tools) | ₹10-30k |
| Month 2 | Brand deals (50k+ followers) | ₹40-80k |
| Month 3 | YouTube AdSense + Sponsorships | ₹1L+ |

**Affiliate triggers built-in:** VPN, courses, tools — auto-inserted in descriptions

## Cost Breakdown

| Component | Cost |
|-----------|------|
| Ollama (LLM) | FREE |
| ComfyUI + AnimateDiff | FREE |
| Coqui TTS / Windows TTS | FREE |
| FFmpeg | FREE |
| YouTube/IG/TikTok APIs | FREE |
| **Total Monthly** | **₹0** |

## Project Structure

```
AIEntertainer/
├── config.yaml              # All settings
├── main.py                  # Entry point
├── run.bat                  # Easy menu
├── setup.bat                # One-click install
├── requirements.txt
├── src/
│   ├── character/           # Character consistency (ControlNet/IP-Adapter ready)
│   ├── content/             # Roast script generator
│   ├── video/               # ComfyUI video generation
│   ├── editor/              # FFmpeg auto-editor
│   ├── poster/              # Multi-platform posting
│   ├── analytics/           # SQLite + reports
│   └── scheduler/           # Main orchestrator
├── comfyui_workflows/       # AnimateDiff workflow (8GB optimized)
├── credentials/             # API keys (gitignored)
├── data/
│   ├── videos/              # Generated videos
│   ├── logs/                # Pipeline logs
│   ├── analytics/           # SQLite DB
│   └── character/           # Character refs
└── templates/               # Editor templates
```

## Customization

Edit `config.yaml` to change:
- Character personality, catchphrases, visual style
- Roast categories & topics
- Posting schedule (default: 9AM, 1PM, 6PM, 9PM)
- Caption style, watermark, music
- Affiliate links & CTAs

## Troubleshooting

| Issue | Fix |
|-------|-----|
| CUDA not found | Reinstall PyTorch: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121` |
| ComfyUI OOM | Reduce `width`/`height` in config, add `--lowvram` flag |
| Ollama slow | Use `phi3:3.8b` instead of `llama3.1:8b` |
| TikTok upload fails | Check token expiry, re-authenticate |
| Low views | Test 3 thumbnails per video, post at peak hours |

## License

MIT — Free to use, modify, distribute

---

**Built for students who want revenue while studying.** Run `python main.py schedule` before sleep, wake up to posted videos + analytics.