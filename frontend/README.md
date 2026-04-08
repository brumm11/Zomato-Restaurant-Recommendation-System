# Frontend UI (Phase 7)

This folder now contains the Phase 7 presentation layer:

- `index.html`: preference form + results panel
- `styles.css`: layout and visual states
- `app.js`: API integration with `POST /recommendations`

Implemented UX states:
- idle
- loading
- error
- empty results
- fallback indicator (`rule_based_fallback`)

## Vercel Deployment

This frontend is static and can be deployed directly on Vercel.

Important:
- `app.js` calls `${BACKEND_BASE_URL}/recommendations` and expects **JSON**.
- If the backend URL serves HTML (for example a Streamlit UI page), frontend API calls will fail with a non-JSON error.

Current default backend URL in `app.js`:
- `https://zomato-restaurant-recommendation-system-nv8cnjoe2ecuqug9opoq62.streamlit.app`

For production-grade frontend integration, point `BACKEND_BASE_URL` to a deployed API endpoint that exposes `POST /recommendations` as JSON.
