# Detailed Phase-Wise Architecture

## Project Context

This document expands the architecture for the AI-Powered Restaurant Recommendation System described in `Docs/problemstatement.md`.

Primary objective:
- Accept user preferences (location, budget, cuisine, rating, optional notes)
- Retrieve relevant restaurants from Zomato dataset
- Use an LLM to rank and explain recommendations
- Return clean, user-friendly output

---

## Phase 1: Foundation and Environment Setup

### 1.1 Objectives
- Establish a maintainable project skeleton
- Define contracts between components early
- Enable reproducible local development

### 1.2 Suggested Logical Components
- `frontend` (UI for preference input and results display)
- `backend/api` (REST API endpoints and orchestration)
- `backend/recommendation` (filtering, scoring, ranking prep)
- `backend/llm` (prompt generation, model call, output parsing)
- `backend/data` (ingestion, preprocessing, storage interface)
- `tests` (unit + integration suites)

### 1.3 Non-Functional Baseline
- Configuration via environment variables (see root `.env.example` for names and placeholders):
  - Groq LLM credentials and model (used from Phase 3 onward; see Phase 3)
  - `DATA_SOURCE`
  - `APP_ENV`
- Structured logging format (request id, latency, status)
- Standard error response schema for all APIs

### 1.4 Outputs of Phase 1
- Running app skeleton
- Health endpoint (`GET /health`)
- Basic CI checks (lint + test placeholder)

---

## Phase 2: Data Ingestion, Cleaning, and Canonical Modeling

### 2.1 Objectives
- Pull Zomato dataset from Hugging Face
- Normalize noisy fields into canonical schema
- Persist data in query-friendly form

### 2.2 Ingestion Pipeline Stages
1. **Fetch Stage**
   - Download/load dataset from source
   - Version stamp dataset snapshot date
2. **Validation Stage**
   - Verify expected columns exist
   - Reject malformed records
3. **Normalization Stage**
   - Canonicalize text fields:
     - location/city aliases (e.g., Bengaluru/Bangalore)
     - cuisine naming consistency
   - Convert ratings and cost fields to numeric formats
4. **Enrichment Stage**
   - Derive budget tier from cost (low/medium/high)
   - Generate keyword tags from metadata
5. **Persistence Stage**
   - Save as normalized table/file (`restaurants_normalized`)

### 2.3 Canonical Restaurant Schema
- `restaurant_id` (string)
- `name` (string)
- `city` (string)
- `area` (string, optional)
- `cuisines` (array of strings)
- `avg_cost_for_two` (number)
- `budget_tier` (`low` | `medium` | `high`)
- `rating` (number, nullable)
- `votes` (number, optional)
- `tags` (array of strings, optional)
- `source_last_updated` (datetime)

### 2.4 Data Quality Rules
- Drop rows with missing name/city
- Keep missing rating rows but mark `rating = null`
- Clamp invalid ratings outside 0-5
- Remove duplicates by `(name, city, area, cuisines)`

### 2.5 Outputs of Phase 2
- Data ingestion script/job
- Normalized dataset artifact
- Data quality report (row count, null count, duplicates removed)

---

## Phase 3: User Input and Preference Modeling

### 3.1 Objectives
- Capture user intent with strong validation
- Translate natural inputs into machine-friendly criteria

### 3.1a LLM provider: Groq
- This phase introduces **Groq** as the LLM provider for any preference-related intelligence (e.g. parsing or enriching free-text preferences, optional validation hints).
- **API key**: configure the Groq API key via environment variables documented in **`.env.example`** at the project root. Developers copy `.env.example` to `.env` and fill in real values locally; the example file lists the variable names (e.g. `GROQ_API_KEY`) and a safe placeholder—**do not commit real secrets**.
- **Model**: set the Groq model identifier in `.env.example` (e.g. `GROQ_MODEL` or aligned `LLM_MODEL` if you keep a single naming convention).

### 3.2 Input Contract (`POST /recommendations`)
- `location` (required string)
- `budget` (optional enum: low/medium/high)
- `cuisine` (optional string or array)
- `min_rating` (optional float: 0.0-5.0)
- `additional_preferences` (optional free text)
- `top_k` (optional integer, default 5, max 10)

### 3.3 Validation and Canonicalization
- Trim and lowercase text fields
- Map city aliases to canonical city
- Normalize cuisine tokens (e.g., "north indian" == "north-indian")
- Convert budget tier to cost range constraints
- Extract preference keywords from free text (e.g., "family-friendly")

### 3.4 Failure Modes and API Behavior
- Invalid input -> `400` with field-level errors
- No matching location -> `404` with suggested locations
- Missing optional fields -> use sensible defaults

### 3.5 Outputs of Phase 3
- `UserPreference` domain model
- Validation middleware
- Standard request/response examples
- Groq-backed configuration wired from `.env` / `.env.example` for Phase 3 LLM usage

---

## Phase 4: Retrieval, Filtering, and Candidate Scoring

### 4.1 Objectives
- Perform deterministic filtering before LLM use
- Minimize token cost while preserving relevance

### 4.2 Retrieval Pipeline
1. **Location filter** (strict city match first, then fallback fuzzy)
2. **Budget filter** (map tier to numeric cost band)
3. **Cuisine filter** (exact + partial cuisine token matching)
4. **Rating filter** (`rating >= min_rating`, if provided)
5. **Preference-tag matching** (keywords from additional preferences)

### 4.3 Deterministic Scoring Formula (Pre-LLM)
Example weighted score:
- `0.40 * rating_score`
- `0.25 * cuisine_match_score`
- `0.20 * budget_fit_score`
- `0.15 * preference_match_score`

Where:
- `rating_score`: normalized rating (0-1)
- `cuisine_match_score`: overlap ratio between requested and restaurant cuisines
- `budget_fit_score`: 1.0 when in tier, decays by distance
- `preference_match_score`: keyword/tag overlap ratio

### 4.4 Candidate Selection Strategy
- Rank by deterministic score
- Keep top 15-30 candidates for LLM
- Attach concise metadata for prompting

### 4.5 Outputs of Phase 4
- `CandidateRestaurant[]` list
- Deterministic ranking explanation trace
- Fallback results if LLM is unavailable

---

## Phase 5: LLM Prompt Engineering and Ranking Layer

### 5.1 Objectives
- Convert candidate list into personalized final ranking
- Produce high-quality natural-language reasons
- Use the same **Groq** provider and credentials as configured in Phase 3 (see `.env.example` for `GROQ_API_KEY` / model variables)

### 5.2 Prompt Architecture
- **System message**
  - Role, constraints, and anti-hallucination rule
- **User preference block**
  - Structured summary of validated preferences
- **Candidate block**
  - Compact list of candidate restaurants with key fields
- **Instruction block**
  - Ask for ranked top K and reasons
  - Force strict JSON output schema

### 5.3 Guardrails
- "Use only restaurants in candidate list"
- "Do not invent missing values"
- "If data is missing, state uncertainty explicitly"
- Validate schema after generation; retry once with correction prompt on parse failure

### 5.4 LLM Output Schema
- `rank` (integer)
- `restaurant_name` (string)
- `cuisine` (string or list)
- `rating` (number or null)
- `estimated_cost` (string/number)
- `ai_explanation` (string)
- `fit_highlights` (array of strings)

### 5.5 Outputs of Phase 5
- Ranked recommendations with explanations
- Structured parseable response artifact
- Prompt + response logs for tuning (without sensitive keys)

---

## Phase 6: Orchestration API and Service Workflow

### 6.1 Objectives
- Build reliable end-to-end recommendation endpoint
- Centralize control flow and resilience behavior

### 6.2 Runtime Sequence (`POST /recommendations`)
1. Receive request and validate payload
2. Build canonical preference model
3. Retrieve and score candidate restaurants
4. Generate LLM prompt from candidates + preferences
5. Invoke LLM and parse output
6. Merge model output with source metadata
7. Return final recommendations payload

### 6.3 Resilience and Reliability
- Timeout boundaries:
  - Retrieval timeout
  - LLM call timeout
- Retry policy:
  - 1 controlled retry for transient LLM failure
- Fallback policy:
  - Return deterministic top-K if LLM fails
- Response consistency:
  - Always include source of ranking (`llm` or `rule_based_fallback`)

### 6.4 API Response Contract
- `request_id`
- `applied_preferences`
- `recommendations` (list)
- `ranking_source`
- `latency_ms`
- `warnings` (optional)

### 6.5 Outputs of Phase 6
- Production-grade orchestration endpoint
- Error catalog and status-code mapping
- Observability hooks (metrics + traces)

---

## Phase 7: Presentation Layer (Frontend / UX)

### 7.1 Objectives
- Provide simple preference capture
- Display recommendations with decision transparency

### 7.2 UI Modules
- **Preference Form**
  - location, budget, cuisine, min rating, additional preferences
- **Results Panel**
  - top K cards or table
- **Recommendation Card**
  - restaurant name
  - cuisine
  - rating
  - estimated cost
  - AI explanation
  - highlight tags

### 7.3 UX States
- Idle state (input form)
- Loading state (while fetching recommendations)
- Empty state (no match)
- Error state (API/LLM issue)
- Fallback indicator ("rule-based ranking used")

### 7.4 Accessibility and Clarity
- Keyboard navigable form controls
- Clear labels and validation messages
- Color + text for rating/priority (not color-only)

### 7.5 Outputs of Phase 7
- End-user interface with complete flow
- User-friendly formatting and messaging

---

## Phase 8: Testing, Evaluation, and Iterative Improvement

### 8.1 Objectives
- Guarantee correctness, stability, and recommendation quality
- Build confidence for deployment

### 8.2 Testing Strategy
- **Unit tests**
  - budget mapping
  - filter logic
  - score calculation
  - schema parsing
- **Integration tests**
  - full endpoint path with mocked LLM
- **Prompt regression tests**
  - fixed candidates + preferences -> schema-valid stable output

### 8.3 Quality Metrics
- Technical:
  - p95 latency
  - LLM parse success rate
  - fallback rate
- Product:
  - click-through on recommendations
  - user feedback rating on usefulness

### 8.4 Optimization Backlog
- Candidate caching per common queries
- Hybrid ranking: blend deterministic and LLM score
- Personalized memory (repeat-user preferences)
- Optional vector search for free-text preference matching

### 8.5 Outputs of Phase 8
- Test suite and CI quality gates
- Evaluation dashboard and improvement roadmap

---

## Cross-Cutting Concerns

### Security
- Keep API keys in environment only
- Do not log secrets
- Rate limit recommendation endpoint

### Observability
- Correlated request ids across layers
- Metrics for each phase stage
- Error-class dashboards

### Governance
- Track prompt versions
- Track model versions
- Maintain reproducible dataset version metadata

---

## Deployment Architecture

### Deployment Targets
- **Backend deployment: Streamlit**
  - Host the backend service logic (ingestion-trigger hooks, recommendation orchestration, LLM integration, API-style handlers).
  - Keep all runtime secrets in Streamlit environment/secrets configuration (`GROQ_API_KEY`, model names, dataset paths).
  - Configure health and basic observability logs for runtime debugging.
- **Frontend deployment: Vercel**
  - Host the presentation layer (form UI, loading/error/empty/fallback states, recommendation cards).
  - Configure frontend environment variable for backend base URL (Streamlit-hosted endpoint).
  - Enable production-safe error display and request timeout handling in client code.

### Environment and Config Mapping
- Backend (Streamlit):
  - `GROQ_API_KEY`
  - `GROQ_MODEL` / `LLM_MODEL`
  - `DATA_SOURCE`
  - `APP_ENV=production`
- Frontend (Vercel):
  - `NEXT_PUBLIC_API_BASE_URL` (or equivalent frontend runtime variable)

### Deployment Flow
1. Build and deploy backend service to Streamlit.
2. Verify backend health and recommendation endpoint behavior in deployed environment.
3. Deploy frontend to Vercel with backend URL configured.
4. Validate end-to-end user journey (input -> recommendations -> explanation rendering).
5. Monitor fallback rate, latency, and API error rate after go-live.

### Production Notes
- CORS should allow Vercel frontend domain to call the Streamlit backend.
- Never expose API keys in frontend bundles; keep keys backend-only.
- If traffic grows, introduce caching for repeated queries and warm candidate retrieval.

---

## Final End-to-End Data Flow

1. User submits preferences via UI
2. API validates and canonicalizes preferences
3. Retrieval engine filters and scores restaurants
4. Top candidates are sent to LLM prompt layer
5. LLM returns ranked recommendations with reasons
6. API validates response and returns final payload
7. UI renders recommendations and explanations

This architecture keeps hard constraints deterministic and uses the LLM for nuanced ranking and natural explanation, delivering relevance, clarity, and operational reliability.
