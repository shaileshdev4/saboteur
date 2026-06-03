# Deployment

The app runs as two services: **backend** on Render (Python + SQLite on a persistent disk) and **frontend** on Vercel (static Vite build).

## Backend (Render)

1. Connect this repository on Render: **New → Blueprint** and select `deploy/render.yaml`.
2. Set environment variable `LLM_API_KEY` if you want LLM narration and explanations.
3. After deploy, confirm health: `curl https://<your-service>.onrender.com/health` → `{"ok":true,...}`.

**Render notes**

- Free tier may sleep when idle; the first request after sleep can take ~30s.
- `SABOTEUR_DB_PATH` points at `/var/data/saboteur.sqlite3` on the mounted disk so data survives restarts.

## Frontend (Vercel)

1. **Add New Project** and import the repository.
2. **Root Directory:** `frontend` (Vite app only — backend is on Railway). Config: `frontend/vercel.json`. Do not use the FastAPI/Python preset.
3. Environment variable:
   - `VITE_API_BASE` = your Render backend URL (e.g. `https://saboteur-backend.onrender.com`, no trailing slash)
4. Deploy and open the site; the client creates a session on first load.

There is only one Vercel config file: **`frontend/vercel.json`**. It must live next to `package.json` because Vercel’s project root is the `frontend/` folder.

## Local development (both services)

```bash
# Terminal 1 — from repo root
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001

# Terminal 2
cd frontend
npm install
npm run dev
```

The dev server proxies `/api` to `VITE_API_PROXY_TARGET` (default `http://127.0.0.1:8001` in `frontend/.env.development`).

## CORS

`backend/main.py` currently allows all origins (`*`). For a locked-down production setup, restrict to your Vercel origin:

```python
allow_origins=["https://your-app.vercel.app"]
```
