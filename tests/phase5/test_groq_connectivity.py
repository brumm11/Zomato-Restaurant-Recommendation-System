import json
import os

import httpx


GROQ_BASE_URL = "https://api.groq.com/openai/v1"

_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "restaurant-recommendation-service/1.0 (tests)",
}


def _api_key() -> str:
    return os.getenv("GROQ_API_KEY", "") or os.getenv("LLM_API_KEY", "")


def _model_name() -> str:
    return os.getenv("GROQ_MODEL", "") or os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")


def _client() -> httpx.Client:
    token = _api_key()
    headers = {**_HEADERS, "Authorization": f"Bearer {token}"}
    return httpx.Client(timeout=30.0, headers=headers)


def _post_json(url: str, payload: dict) -> dict:
    with _client() as client:
        response = client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


def _get_json(url: str) -> dict:
    with _client() as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()


def test_01_api_key_is_available() -> None:
    key = _api_key()
    assert key, "No API key found. Set GROQ_API_KEY (or LLM_API_KEY) in .env."


def test_02_models_endpoint_reachable() -> None:
    data = _get_json(f"{GROQ_BASE_URL}/models")
    assert "data" in data
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0


def test_03_chat_completion_returns_text() -> None:
    payload = {
        "model": _model_name(),
        "messages": [{"role": "user", "content": "Reply with exactly: CONNECTED"}],
        "temperature": 0,
        "max_tokens": 10,
    }
    data = _post_json(f"{GROQ_BASE_URL}/chat/completions", payload)
    assert "choices" in data and len(data["choices"]) > 0
    content = data["choices"][0]["message"]["content"]
    assert isinstance(content, str)
    assert content.strip() != ""


def test_04_chat_completion_format_check() -> None:
    payload = {
        "model": _model_name(),
        "messages": [
            {"role": "system", "content": "Return strict JSON only."},
            {"role": "user", "content": 'Return {"status":"ok"}'},
        ],
        "temperature": 0,
        "max_tokens": 40,
    }
    data = _post_json(f"{GROQ_BASE_URL}/chat/completions", payload)
    content = data["choices"][0]["message"]["content"].strip()
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AssertionError(f"Model did not return valid JSON: {content}") from exc
    assert parsed.get("status") == "ok"
