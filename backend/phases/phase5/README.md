# Phase 5: LLM Prompt Engineering and Ranking Layer

## Implemented

- Consumes Phase 4 candidates and user preferences.
- Builds a constrained prompt with candidate data and strict output schema.
- Calls Groq chat completions for ranking + explanations.
- Validates parsed JSON output and enforces candidate-list-only guardrail.
- Retries once when output format is invalid.
- Falls back to deterministic Phase 4 ordering when LLM fails.

## Output schema

Each recommendation returns:
- `rank`
- `restaurant_id`
- `restaurant_name`
- `cuisine`
- `rating`
- `estimated_cost`
- `ai_explanation`
- `fit_highlights`
# Phase 5: LLM Prompting and Ranking

Reserved for:
- prompt templates and builders
- LLM client and response parsing
- ranking explanation generation
