# The Saboteur

STEM learning game: the AI shows you a worked solution that may contain a planted mistake. You **Trust** or **Flag** each step, then see whether you were right. Over time you build a **calibration score** — how well your trust matches when the AI is actually wrong.

**Core idea:** You audit the machine; the machine does not grade you. SymPy and per-domain verifiers decide correctness. A misconception library injects errors at known steps. An optional LLM only narrates steps and explains mistakes after reveal (prompts forbid judging correctness; output is filtered).

---

## How it works

1. **Session** — `POST /session` creates a player session (persisted in SQLite; frontend also keeps `session_id` in `localStorage`).
2. **Round** — `GET /session/{id}/round` picks a problem in a domain (algebra, geometry, calculus, statistics), builds a canonical solution, and may sabotage one step using a registered misconception.
3. **Play** — You review steps and submit **Trust** or **Flag** (and optional misconception id when flagging).
4. **Grade** — `POST /grade` compares your choices to ground truth, updates points, per-domain calibration, and per-misconception stats.
5. **Reveal** — Response includes whether the round was clean, which step was wrong, and an optional LLM explanation of the misconception.

**Optional mechanics**

- **Hints** — Three tiers (`POST /hint`), each costs points; tier 3 names the misconception category.
- **Step propagation** — `?propagate=true` on round generation so a corrupted step affects later steps (more realistic error chains).
- **Modes** — Solo play, BYOAI (paste external AI work), universal auditor, classroom aggregates, multiplayer matches, leaderboards, achievements.

---

## Architecture

```
Domain (algebra | geometry | calculus | statistics)
  → generator + misconceptions + verifier
       ↓
Sabotage engine (select misconception, optional propagation)
       ↓
Presentation (optional LLM narration — not authoritative)
       ↓
Player Trust / Flag
       ↓
Grader + per-domain calibration + persistence
```

New subjects: implement the `Domain` interface in `engine/domain.py` and register in `engine/domains/`. See existing modules under `engine/domains/`.

---

## Repository layout

```
saboteur/
├── engine/          # Grading, domains, misconceptions, sabotage, hints
├── backend/         # FastAPI API, SQLite persistence, tests/
├── frontend/        # React + Vite + Tailwind UI
├── deploy/          # Deploy notes (backend Railway/Render)
│   └── (see frontend/vercel.json for Vercel)
└── README.md
```

---

## Requirements

- Python 3.11+ (backend + engine)
- Node 18+ (frontend)
- Optional: `LLM_API_KEY` for step narration and post-reveal explanations

---

## Local development

From the repo root:

```bash
# Backend
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` to the backend (`frontend/.env.development` sets `VITE_API_PROXY_TARGET=http://127.0.0.1:8001`).

Override env locally: copy `frontend/.env.example` to `frontend/.env.local`.

---

## Testing

Backend tests use a temporary SQLite file (see `backend/tests/conftest.py`).

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/ -q
```

Or:

```bash
cd backend
python run_tests.py
```

Smoke-check the running API:

```bash
curl http://127.0.0.1:8001/health
```

Expect `ok: true` and counts for loaded domains and misconceptions.

---

## Configuration

Backend template: **`backend/.env.example`** (Groq + SQLite paths for Railway).

| Variable | Where | Purpose |
|----------|--------|---------|
| `SABOTEUR_DB_PATH` | Railway / local backend | SQLite file path (sessions, rounds, hints) |
| `LLM_CACHE_PATH` | Railway (optional) | Cached LLM responses JSON, same volume as DB |
| `LLM_API_KEY` | Railway | Groq `gsk_...` — optional; enables narration + reveal copy |
| `LLM_API_BASE` | Railway | `https://api.groq.com/openai/v1` |
| `LLM_API_MODEL` | Railway | e.g. `llama-3.3-70b-versatile` |
| `VITE_API_BASE` | Vercel build | Railway backend URL (no trailing slash) |
| `VITE_API_PROXY_TARGET` | Frontend dev only | Backend URL for Vite proxy |

**Database:** single SQLite file via `backend/persistence.py`. Tables are created on startup (`init_db`). Use a Railway **Volume** at `/data` and set `SABOTEUR_DB_PATH=/data/saboteur.sqlite3` so data survives redeploys.

---

## HTTP API (summary)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service status and engine load counts |
| GET | `/domains` | List domains |
| GET | `/domains/{id}/misconceptions` | Misconceptions for one domain |
| POST | `/session` | Create session |
| GET | `/session/{id}/round` | New round (`domain_id`, `corrupt_prob`, `propagate`, …) |
| POST | `/grade` | Submit Trust/Flag decisions |
| POST | `/hint` | Request hint tier for a round |
| GET | `/session/{id}/dashboard` | Calibration, stats, per-domain breakdown |
| GET | `/session/{id}/achievements` | Unlocked achievements |
| GET | `/leaderboard` | Rankings (filters: period, domain, class) |
| POST | `/byoai` | Grade pasted AI solution |
| POST | `/audit` | Universal auditor on free-form work |
| POST | `/class`, `/class/join`, … | Classroom mode |
| POST | `/match`, `/match/join`, … | Multiplayer |
| POST | `/image/transcribe` | OCR pipeline for uploaded work |

Interactive docs when the server is running: http://127.0.0.1:8001/docs

---

## Deployment

- **Backend:** Railway — repo root, `railway.toml`, env from `backend/.env.example`
- **Frontend:** Vercel — Root Directory `frontend`, `VITE_API_BASE` → Railway URL

Details: [deploy/README.md](deploy/README.md)
