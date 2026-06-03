# Deployment

| Service           | Platform    | Root / config                                       |
| ----------------- | ----------- | --------------------------------------------------- |
| Backend (FastAPI) | **Railway** | Repo root + `railway.toml`                          |
| Frontend (Vite)   | **Vercel**  | Root Directory = `frontend`, `frontend/vercel.json` |

Do **not** deploy the frontend on Railway as FastAPI -delete any extra Railway “frontend” service.

---

## Backend -Railway

### Service settings

- **Root directory:** `.` (repository root, not `backend/` alone -imports need `engine/`)
- **Start command** (also in `railway.toml`):  
  `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- **Build:** `pip install -r backend/requirements.txt`

### Environment variables

Copy from `backend/.env.example`. Minimum for production:

| Variable           | Value                                                                    |
| ------------------ | ------------------------------------------------------------------------ |
| `SABOTEUR_DB_PATH` | `/data/saboteur.sqlite3` (with Volume mounted at `/data`)                |
| `LLM_CACHE_PATH`   | `/data/llm_cache.json` (same volume, optional but recommended with Groq) |
| `LLM_API_KEY`      | Groq key (`gsk_...`) -optional                                           |
| `LLM_API_BASE`     | `https://api.groq.com/openai/v1`                                         |
| `LLM_API_MODEL`    | e.g. `llama-3.3-70b-versatile` or `llama-3.1-8b-instant`                 |

Without `LLM_API_KEY`, the API still runs; steps use short rule-based phrases and reveal text uses the misconception library.

Optional (image upload only):

| Variable                             | Purpose                                   |
| ------------------------------------ | ----------------------------------------- |
| `MULTIMODAL_API_KEY`                 | Vision transcribe for `/image/transcribe` |
| `MATHPIX_APP_ID` / `MATHPIX_APP_KEY` | Alternative OCR                           |

### Database (SQLite)

All persistent app data lives in one SQLite file:

- **Sessions** -calibration state, display name prefs
- **Rounds** -ground truth for grading (never sent to the client before grade)
- **Hints** -tier usage per round
- Leaderboard / achievements read from the same DB via `backend/persistence.py`

Path is controlled by **`SABOTEUR_DB_PATH`** (default: `saboteur.sqlite3` in the working directory).

**On Railway without a Volume:** the file lives on the container filesystem and is **lost on redeploy**.

**Recommended:** Railway → your backend service → **Volumes** → mount e.g. `/data`, then set:

```
SABOTEUR_DB_PATH=/data/saboteur.sqlite3
LLM_CACHE_PATH=/data/llm_cache.json
```

`init_db()` runs at startup and creates tables if missing (no separate migration step).

### Health check

```bash
curl https://<your-railway-app>.up.railway.app/health
```

### CORS

Lock `allow_origins` in `backend/main.py` to your Vercel URL when you go public.

---

## Frontend -Vercel

1. **Root Directory:** `frontend`
2. **Env (build time):** `VITE_API_BASE` = Railway backend URL (no trailing slash)
3. Config file: `frontend/vercel.json`

Redeploy after changing `VITE_API_BASE`.

---

## Local development

```bash
# Terminal 1 -repo root
pip install -r backend/requirements.txt
# optional: cp backend/.env.example backend/.env and fill Groq key
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001

# Terminal 2
cd frontend
npm install
npm run dev
```

Vite proxies `/api` to `http://127.0.0.1:8001` via `frontend/.env.development`.

---

## Optional: Render

`deploy/render.yaml` is an alternate backend host (persistent disk at `/var/data`). Use Railway **or** Render, not both for the same app.
