# Zomato Restaurant Recommendation System

AI-powered restaurant recommendation platform with phase-based architecture:

- Phase 1: backend foundation + health endpoint
- Phase 2: data ingestion and normalization
- Phase 3: user preference modeling and validation
- Phase 4: deterministic filtering and candidate scoring
- Phase 5: Groq LLM ranking and explanations
- Phase 6: orchestration, retries, timeouts, fallback
- Phase 7: frontend UI and flow states

## Project Structure

- `backend/phases/`: phase-wise backend implementation
- `frontend/`: UI assets (HTML/CSS/JS)
- `Docs/`: architecture and problem statement
- `tests/`: phase-wise test coverage

## Local Setup

1. Install dependencies:
   - `python -m pip install -r requirements.txt`
2. Configure env:
   - copy `.env.example` to `.env`
   - add `GROQ_API_KEY`
3. Run backend:
   - `python -m backend.main`
4. Open:
   - `http://127.0.0.1:8000/`

## Data Ingestion (Phase 2)

Generate normalized data before recommendation testing:

- `python -m backend.phases.phase2.data.run_ingestion`

This writes:
- `artifacts/data/restaurants_normalized.jsonl`
- `artifacts/data/data_quality_report.json`

## Streamlit Backend Deployment

- Entry app: `backend/streamlit_app.py`
- Run locally:
  - `streamlit run backend/streamlit_app.py`
- Deployment secrets template:
  - `.streamlit/secrets.toml.example`