# Divination Backend (MVP)

## Features in this MVP
- FastAPI service with MySQL persistence
- User profile creation
- Divination session and record persistence
- Unified reading endpoint for all modules
- Basic lot draw endpoint (guanyin / yuelao / generic)

## Quick start
1. Copy `.env.example` to `.env` and fill your MySQL password and API key.
2. Create database:
   - `CREATE DATABASE divination CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
3. Install deps:
   - `pip install -r requirements.txt`
4. Run service:
   - `uvicorn app.main:app --reload --port 8000`
5. Open docs:
   - `http://127.0.0.1:8000`

## Important endpoints
- `POST /api/v1/users`
- `POST /api/v1/readings/{module}`
- `POST /api/v1/lots/{lot_type}/reading`
- `GET /api/v1/history/session/{session_id}`

## Notes
- This MVP stores all user-filled inputs into `input_payload` JSON in `divination_records`.
- For lot drawing, RNG seed is stored in `random_traces` for reproducibility.
