# Phase 6: Orchestration API and Service Workflow

## Implemented

- Centralized orchestration in `backend/phases/phase6/service.py`.
- Runtime sequence:
  1. Validate payload and canonicalize preferences
  2. Retrieve/select Phase 4 candidates
  3. Invoke Phase 5 LLM ranking
  4. Merge outputs and return final contract
- Resilience:
  - Retrieval timeout boundary (5s)
  - LLM timeout boundary (20s call, 25s orchestration guard)
  - One controlled retry remains in Phase 5 parsing logic
  - Deterministic fallback when LLM fails/timeouts
- Response contract includes:
  - `request_id`
  - `applied_preferences`
  - `recommendations`
  - `ranking_source`
  - `latency_ms`
  - `warnings`

## Streamlit Deployment (Backend Target)

- Entry app: `backend/streamlit_app.py`
- Local run:
  - `streamlit run backend/streamlit_app.py`
- Streamlit Cloud:
  - add secrets in `.streamlit/secrets.toml` (use `.streamlit/secrets.toml.example` as template)
  - include `streamlit` in `requirements.txt`
- The Streamlit app provides:
  - ingestion trigger (Phase 2)
  - orchestration execution UI (Phases 3-6)
  - JSON output for debugging deployed backend behavior
