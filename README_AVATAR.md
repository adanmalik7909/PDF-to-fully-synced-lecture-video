# OmniAvatar Integration — Setup Guide

## SmartStudyInstructor × OmniAvatar 1.3B

Generate AI talking-head lecture videos using **OmniAvatar 1.3B** — a free, open-source audio-driven avatar model running on Google Colab T4 GPU.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              GOOGLE COLAB (T4 GPU, 15GB VRAM)           │
│                                                         │
│  ┌─────────────┐   ┌───────────────┐   ┌────────────┐  │
│  │ Wan2.1-T2V  │   │ OmniAvatar    │   │ wav2vec2   │  │
│  │ 1.3B Base   │──▶│ 1.3B Weights  │◀──│ Audio Enc  │  │
│  └─────────────┘   └───────┬───────┘   └────────────┘  │
│                            │                            │
│                    ┌───────▼───────┐                    │
│                    │  FastAPI      │                    │
│                    │  Server:8000  │                    │
│                    └───────┬───────┘                    │
│                            │                            │
│                    ┌───────▼───────┐                    │
│                    │    ngrok      │                    │
│                    │   tunnel      │                    │
│                    └───────┬───────┘                    │
└────────────────────────────┼────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────┐
│           LOCAL MACHINE (Your Computer)                  │
│                                                         │
│  ┌──────────────────┐                                   │
│  │  .env             │ COLAB_AVATAR_URL=https://...     │
│  └────────┬─────────┘                                   │
│           ▼                                             │
│  ┌──────────────────┐   ┌─────────────────────┐        │
│  │ avatar_service.py│──▶│ OmniAvatar Colab    │        │
│  │ (HTTP client)    │   │ (POST /generate)     │        │
│  └────────┬─────────┘   └─────────────────────┘        │
│           ▼                                             │
│  ┌──────────────────┐                                   │
│  │ avatar_routes.py │  /api/avatar/generate-lecture-video│
│  │ (API endpoints)  │  /api/avatar/lecture-status/{id}  │
│  └────────┬─────────┘  /api/avatar/video/{id}/{file}   │
│           ▼                                             │
│  ┌──────────────────┐                                   │
│  │ FastAPI app      │  http://localhost:8000             │
│  │ (main.py)        │                                   │
│  └────────┬─────────┘                                   │
└───────────┼─────────────────────────────────────────────┘
            │ HTTP
            ▼
┌─────────────────────────────────────────────────────────┐
│                    BROWSER                               │
│                                                         │
│  http://localhost:8000/lecture-player                    │
│                                                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │  1. Connect Colab (paste ngrok URL)             │    │
│  │  2. Upload audio + avatar image                 │    │
│  │  3. Click Generate → polls status every 5s      │    │
│  │  4. Watch video in custom player                │    │
│  │  5. Ask questions via Q&A chat                  │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Step 1: Start Google Colab Notebook

1. Open `OmniAvatar_SmartStudy_Colab.ipynb` in Google Colab
2. Go to **Runtime → Change runtime type → T4 GPU**
3. Run **ALL cells** from top to bottom (Cell 1 through Cell 5)
4. Wait for models to download (~10-15 minutes first time)
5. **Copy the ngrok URL** printed in Cell 4

### Step 2: Configure Local App

**Option A: Via .env file**
```bash
# In backend/.env, set:
COLAB_AVATAR_URL=https://xxxx-xx-xx-xxx-xxx.ngrok-free.app
```

**Option B: Via Browser UI**
- Open `http://localhost:8000/lecture-player`
- Paste the ngrok URL in the "Colab GPU Connection" field
- Click "Connect"

### Step 3: Start FastAPI Backend

```bash
cd SmartStudyInstructor/backend
python -m uvicorn app.main:app --reload --port 8000
```

### Step 4: Generate Lecture Video

1. Open **http://localhost:8000/lecture-player**
2. Upload audio (WAV/MP3) or enter lecture text
3. Optionally upload a teacher photo
4. Enter the lecture topic
5. Click **"Generate OmniAvatar Lecture Video"**
6. Wait 3-8 minutes for video generation
7. Watch the result in the built-in player!

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/avatar/set-colab-url` | Set OmniAvatar Colab ngrok URL |
| `GET` | `/api/avatar/colab-status` | Check connection status |
| `GET` | `/api/avatar/colab-health` | Deep health check with GPU info |
| `POST` | `/api/avatar/generate-lecture-video` | Start video generation |
| `GET` | `/api/avatar/lecture-status/{job_id}` | Poll generation progress |
| `GET` | `/api/avatar/video/{job_id}/{filename}` | Stream video (supports Range) |

---

## Test Commands

```bash
# 1. Check if backend is running
curl http://localhost:8000/health

# 2. Check OmniAvatar Colab connection
curl http://localhost:8000/api/avatar/colab-status

# 3. Set Colab URL
curl -X POST http://localhost:8000/api/avatar/set-colab-url \
  -F "url=https://your-ngrok-url.ngrok-free.app"

# 4. Deep health check
curl http://localhost:8000/api/avatar/colab-health

# 5. Generate video with text (auto TTS)
curl -X POST http://localhost:8000/api/avatar/generate-lecture-video \
  -F "text=Machine learning is a subset of artificial intelligence..." \
  -F "topic=Introduction to Machine Learning"

# 6. Generate video with uploaded files
curl -X POST http://localhost:8000/api/avatar/generate-lecture-video \
  -F "audio=@lecture.wav" \
  -F "image=@teacher.jpg" \
  -F "topic=Data Structures"

# 7. Poll status
curl http://localhost:8000/api/avatar/lecture-status/avatar_1234567890
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "No GPU detected" in Colab | Runtime → Change runtime type → T4 GPU |
| ngrok URL not working | Restart Cell 4, ensure notebook is still running |
| OOM (Out of Memory) | Already using `num_persistent_param_in_dit=0`. Try restarting runtime. |
| Video generation timeout | Audio may be too long. Try < 60 seconds of audio. |
| "Colab not connected" locally | Paste the ngrok URL in .env or the UI. Check if Colab is still running. |
| Empty video file | Check Colab notebook logs. Model may not have generated output. |
| Slow generation | Normal! 1.3B model on T4 takes 3-8 minutes per video. |

---

## Files Added/Modified

### New Files
- `backend/app/utils/avatar_service.py` — OmniAvatar Colab client service
- `backend/app/routes/avatar_routes.py` — API endpoints for video generation
- `frontend/lecture_video_player.html` — Video player page
- `OmniAvatar_SmartStudy_Colab.ipynb` — Colab notebook (in Prototype/)

### Modified Files
- `backend/app/config.py` — Added `COLAB_AVATAR_URL`, `AVATAR_IMAGE_PATH`, `VIDEO_OUTPUT_DIR`
- `backend/app/main.py` — Added `avatar_routes` router + startup init + `/lecture-player` route
- `backend/.env` — Added OmniAvatar URL settings
- `backend/.env.example` — Added OmniAvatar URL settings
- `backend/requirements.txt` — Added `aiofiles`

### Unchanged Files
- All RAG, auth, video_routes, pipeline, and existing frontend code is **untouched**
