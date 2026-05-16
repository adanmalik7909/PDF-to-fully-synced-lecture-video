# SmartStudyInstructor MVP

An integrated classroom monitoring and intelligent tutoring system for FYP (Final Year Project).

## Features

- **Role-based Authentication**: Admin, Teacher, Student (JWT tokens)
- **PDF Knowledge Base (RAG)**: Upload PDFs → Auto-generate lecture scripts & quizzes
- **Classroom LED Mode**: Projector-based lecture player with live monitoring
- **Phone Detection**: YOLO-based cheating detection with evidence snapshots
- **Teacher Dashboard**: Session reports with cheating events & timestamps
- **Student Personal Tuition**: Q&A, quizzes, notes & summaries

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

The `.env` file is pre-configured. For production, change:
```
JWT_SECRET_KEY=your-secure-random-key-here
```

### 3. Start Backend

```bash
python run.py
```

Backend will run at: `http://localhost:8000`

API Docs: `http://localhost:8000/docs`

### 4. Test Authentication (Optional)

```bash
# In another terminal, from backend directory
python test_auth.py
```

### 5. Enable LLM Generation (Phase 4) - Optional but Recommended

**Option A: Use Gemini AI (Free - Recommended)**

1. Get free API key: https://makersuite.google.com/app/apikey
2. Add to `.env`:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```
3. Restart server
4. Test endpoints with `python test_llm.py`

**Option B: Use Mock Mode (No Setup)**

- Skip GEMINI_API_KEY - system automatically uses realistic mock responses
- Good for testing without API key

### 6. Test LLM Features (Phase 4)

```bash
# Test Q&A, lecture generation, quiz generation
python test_llm.py
```

### 7. Open Frontend

Open `frontend/index.html` in a web browser.

## Demo Credentials

```
Teacher:  username: teacher01  password: Teacher@123
Student:  username: student01  password: Student@123
Admin:    username: admin01    password: Admin@123
```

## Project Structure

```
SmartStudyInstructor/
├── backend/              # FastAPI backend
│   ├── app/             # Main application code
│   │   ├── auth/        # JWT & password handling
│   │   ├── database/    # SQLAlchemy models & schemas
│   │   ├── routes/      # API endpoints
│   │   ├── rag/         # RAG pipeline (Phase 3)
│   │   ├── vision/      # YOLO detection (Phase 7)
│   │   └── utils/       # Logging, file handling
│   ├── static/          # Uploads & models
│   ├── schema.sql       # SQLite schema
│   ├── requirements.txt # Dependencies
│   ├── run.py           # Startup script
│   └── test_auth.py     # Auth testing
├── frontend/            # Web UI (HTML/CSS/JS)
│   ├── index.html       # Login page
│   ├── register.html    # Registration page
│   ├── dashboard.html   # Teacher dashboard (Phase 8)
│   ├── classroom.html   # Classroom player (Phase 6)
│   ├── student_tuition.html  # Student mode (Phase 9)
│   ├── css/
│   │   └── style.css    # Global styles
│   └── js/
│       ├── api.js       # API client
│       ├── auth.js      # Auth logic
│       └── dashboard.js # Dashboard logic
└── ARCHITECTURE.md      # Detailed architecture

```

## API Documentation

Once backend is running, visit: `http://localhost:8000/docs`

### Authentication Endpoints

#### Register
```
POST /api/auth/register
Body: {
  "username": "teacher01",
  "email": "teacher@example.com",
  "password": "SecurePassword123",
  "role": "teacher"  // admin, teacher, or student
}
Response: { user_id, username, email, role, message }
```

#### Login
```
POST /api/auth/login
Body: { "username": "teacher01", "password": "SecurePassword123" }
Response: { user_id, username, email, role, access_token, token_type }
```

#### Get Profile
```
GET /api/auth/me
Headers: Authorization: Bearer <token>
Response: { id, username, email, role, is_active, created_at }
```

### RAG Pipeline Endpoints (NEW - Phase 3)

#### Upload PDF
```
POST /api/content/upload
Headers: Authorization: Bearer <token>
Body: multipart/form-data (PDF file)
Response: { content_id, filename, file_size, message }
```

#### Check Ingestion Status
```
GET /api/content/rag/status/{content_id}
Headers: Authorization: Bearer <token>
Response: { content_id, filename, status, total_chunks, embedding_model }
```

Status values: `pending`, `processing`, `completed`, `failed`

#### Query Knowledge Base
```
POST /api/rag/query
Headers: Authorization: Bearer <token>
Body: {
  "content_id": 1,
  "query": "What is machine learning?",
  "num_results": 5
}
Response: { query, content_id, chunks[], total_chunks_available }
```

#### List User's Contents
```
GET /api/content/list
Headers: Authorization: Bearer <token>
Response: [{ id, filename, file_size, rag_status, total_chunks }]
```

#### RAG Service Health
```
GET /api/rag/health
Response: { status, embeddings_model, vector_store, collections_count }
```

### LLM Integration Endpoints (NEW - Phase 4)

#### Ask Question (RAG-based Q&A)
```
POST /api/rag/ask
Headers: Authorization: Bearer <token>
Body: {
  "question": "What is machine learning?",
  "content_id": 1,
  "num_results": 5
}
Response: { question, answer, context_chunks[], sources_used, content_title }
```

#### Generate Lecture Script
```
POST /api/lecture/generate
Headers: Authorization: Bearer <token> (Teacher only)
Body: {
  "content_id": 1,
  "objectives": ["Understand concepts", "Apply techniques"],
  "title": "Optional title"
}
Response: { content_id, lecture_script{}, generation_time_seconds, model_used }
```

#### Generate Quiz
```
POST /api/quiz/generate
Headers: Authorization: Bearer <token> (Teacher only)
Body: {
  "content_id": 1,
  "num_questions": 10,
  "difficulty": "medium"
}
Response: { content_id, quiz{}, generation_time_seconds, model_used }
```

#### LLM Service Health
```
GET /api/health/llm
Response: { status, llm_type, model, message }
```

## Technology Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Backend | FastAPI | Light, fast, async |
| Database | SQLite | No server needed, embedded |
| Auth | JWT + bcrypt | Stateless, secure |
| Embeddings | sentence-transformers | Free, offline |
| Vector Store | ChromaDB | Lightweight, in-memory |
| Vision | YOLOv8n | Nano model, real-time detection |
| Frontend | Vanilla JS | No npm build, direct HTML/JS |

## Development Status

- [x] Phase 1: Project Setup & Infrastructure
- [x] Phase 2: Authentication System (JWT + Registration/Login)
- [x] Phase 3: RAG Pipeline (ChromaDB + embeddings + PDF extraction)
- [x] Phase 4: LLM Integration (Lecture & quiz generation) ⭐ NEW
- [ ] Phase 5: Document Management (PDF upload UI)
- [ ] Phase 6: Classroom Sessions (LED player)
- [ ] Phase 7: Vision Pipeline (YOLO phone detection)
- [ ] Phase 8: Dashboard (Reports & analytics)
- [ ] Phase 9: Student Tuition (Q&A + notes)
- [ ] Phase 10: Frontend Integration
- [ ] Phase 11: Testing & Refinement
- [ ] Phase 12: Deployment Prep

## Database Schema

14 tables with full relationships:
- **users** - Role-based user accounts
- **contents** - Uploaded PDFs/documents
- **knowledge_bases** - ChromaDB vector mappings
- **sessions** - Classroom & tuition sessions
- **vision_events** - Phone detection records (snapshot + confidence + timestamp)
- **assessments** - Quiz metadata
- **questions** - Individual questions
- **submissions** - Student quiz responses
- **answers** - Individual answers
- **notes** - Student personal notes
- **summaries** - AI-generated summaries
- **logs** - Audit trail

See [schema.sql](backend/schema.sql) for full details.

## Key Implementation Details

### JWT Authentication
- **Token Lifetime**: 24 hours (configurable in .env)
- **Algorithm**: HS256
- **Secret Key**: Change in production (.env file)
- **Payload**: { sub: user_id, role: user_role, exp: expiration_time }

### Password Security
- **Algorithm**: Bcrypt (passlib)
- **Automatic Hashing**: On registration
- **Verification**: Constant-time comparison

### Database
- **Type**: SQLite3
- **Init**: Automatic on app startup
- **File**: `smart_study.db` in backend root

## Testing

### Unit Tests
```bash
pytest backend/tests/
```

### API Tests
```bash
# Auth endpoints
python backend/test_auth.py

# RAG pipeline (Phase 3)
python backend/test_rag.py
```

### Manual Testing
1. Open `frontend/index.html`
2. Register new account or login with demo credentials
3. Check API docs at `http://localhost:8000/docs`

## Troubleshooting

### "Address already in use" error
```bash
# Kill process on port 8000
# Windows: netstat -ano | findstr :8000
# Linux/Mac: lsof -i :8000 | grep LISTEN | awk '{print $2}' | xargs kill
```

### Database locked error
```bash
# Delete smart_study.db and restart
rm backend/smart_study.db
python backend/run.py
```

### Token expired
- Login again to get a new token
- Token validity: 24 hours

### CORS errors
- Ensure backend is running
- Check API_BASE_URL in frontend/js/api.js

## License

MIT - Final Year Project

## Notes

- MVP focuses on end-to-end pipeline over accuracy
- All free/open-source tools used
- Single integrated application (one backend + simple web UI)
- Runs on any laptop with Python 3.8+
- No external service dependencies
- No external service dependencies

## DEMO Quick Run (DEMO_MODE)

This project includes a lightweight demo mode that avoids heavy native dependencies and ML binaries. Use these steps for a fast local demo.

1. From the repository backend folder create/activate a venv (optional but recommended):

```powershell
cd "c:\Users\PMLS\Desktop\Prototype\SmartStudyInstructor\backend"
python -m venv ..\.venv
& "C:/Users/PMLS/Desktop/Prototype/.venv/Scripts/Activate.ps1"
```

2. Install the demo dependency set:

```powershell
pip install -r requirements_demo.txt
```

3. Seed demo data (creates demo user and sample content):

```powershell
$env:DEMO_MODE='1'; python .\scripts\seed_demo.py
```

4. Start the backend in demo mode:

```powershell
$env:DEMO_MODE='1'; & "C:/Users/PMLS/Desktop/Prototype/.venv/Scripts/python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

5. Open URLs in browser:

- Student UI: http://127.0.0.1:8000/tuition/student/ui
- API docs:   http://127.0.0.1:8000/docs

Automated smoke test

```powershell
& "C:/Users/PMLS/Desktop/Prototype/.venv/Scripts/python.exe" scripts/test_demo_endpoints.py
```

Notes
- If you need full RAG and vision features, install the full `requirements.txt` and follow `RUNNING.md` for persistence and agent setup.
- If package builds fail on Windows, prefer `DEMO_MODE=1` for a friction-free local demo.
