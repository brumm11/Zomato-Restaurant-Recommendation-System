import os
import sys
from pathlib import Path

import streamlit as st

# Ensure repository root is importable on Streamlit Cloud.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def _bootstrap_env_from_secrets() -> None:
    # Ensure pydantic settings can read deployment secrets on Streamlit Cloud.
    for key in (
        "APP_NAME",
        "APP_ENV",
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "LLM_API_KEY",
        "LLM_MODEL",
        "DATA_SOURCE",
        "NORMALIZED_DATA_PATH",
    ):
        if key in st.secrets and key not in os.environ:
            os.environ[key] = str(st.secrets[key])


_bootstrap_env_from_secrets()

from backend.phases.phase2.data.run_ingestion import main as run_phase2_ingestion
from backend.phases.phase3.models import RecommendationRequest
from backend.phases.phase6.service import orchestrate_recommendations


st.set_page_config(page_title="Restaurant Backend (Streamlit)", layout="wide")
st.title("Restaurant Recommendation Backend")
st.caption("Streamlit deployment wrapper for backend phases 2-6")

with st.sidebar:
    st.subheader("Admin Actions")
    if st.button("Run Phase 2 Ingestion"):
        with st.spinner("Running ingestion..."):
            try:
                run_phase2_ingestion()
                st.success("Ingestion completed. Normalized dataset refreshed.")
            except Exception as exc:  # noqa: BLE001
                st.error(f"Ingestion failed: {exc}")

st.subheader("Test Orchestration")
col1, col2, col3 = st.columns(3)

location = col1.text_input("Location", value="bangalore")
budget = col2.selectbox("Budget", options=["", "low", "medium", "high"], index=0)
min_rating = col3.number_input("Min Rating", min_value=0.0, max_value=5.0, value=0.0, step=0.1)

cuisine = st.text_input("Cuisine (comma separated)", value="")
additional_preferences = st.text_input("Additional Preferences", value="")
top_k = st.number_input("Top K", min_value=1, max_value=10, value=5, step=1)

if st.button("Run Recommendation Flow", type="primary"):
    try:
        payload = RecommendationRequest(
            location=location,
            budget=budget or None,
            cuisine=cuisine or None,
            min_rating=min_rating if min_rating > 0 else None,
            additional_preferences=additional_preferences or None,
            top_k=int(top_k),
        )
        with st.spinner("Running orchestration..."):
            result = orchestrate_recommendations(payload)
        st.success("Flow completed")
        st.json(result.model_dump())
    except Exception as exc:  # noqa: BLE001
        detail = getattr(exc, "detail", None)
        st.error(detail if detail else f"Request failed: {exc}")
