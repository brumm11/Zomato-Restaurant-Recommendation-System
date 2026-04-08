# Phase 4: Retrieval, Filtering, and Candidate Scoring

## Implemented

- Loads normalized restaurants from `settings.normalized_data_path` (default `artifacts/data/restaurants_normalized.jsonl`).
- Applies deterministic filters:
  - city match
  - budget tier match (when user provides budget)
  - cuisine overlap match (when user provides cuisines)
  - minimum rating threshold (when provided)
- Scores remaining candidates using the architecture weights:
  - `0.40 * rating_score`
  - `0.25 * cuisine_match_score`
  - `0.20 * budget_fit_score`
  - `0.15 * preference_match_score`
- Returns top candidates (default pool size 30) with a per-candidate `score_trace`.

## API integration

`POST /recommendations` now returns:
- `candidates`
- `ranking_source` (currently `rule_based_fallback`)
- `warnings` (e.g., missing normalized dataset)

## Next

Phase 5 will consume `candidates` for Groq ranking + explanations.
