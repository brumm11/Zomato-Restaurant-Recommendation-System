const form = document.getElementById("pref-form");
const statusText = document.getElementById("status-text");
const submitBtn = document.getElementById("submit-btn");
const cards = document.getElementById("cards");
const meta = document.getElementById("meta");
const warnings = document.getElementById("warnings");
const fallbackNote = document.getElementById("fallback-note");
const emptyState = document.getElementById("empty-state");

const BACKEND_BASE_URL =
  window.BACKEND_BASE_URL ||
  "https://zomato-restaurant-recommendation-system-nv8cnjoe2ecuqug9opoq62.streamlit.app";

function setStatus(text) {
  statusText.textContent = text;
}

function clearResults() {
  cards.innerHTML = "";
  warnings.classList.add("hidden");
  fallbackNote.classList.add("hidden");
  emptyState.classList.add("hidden");
  meta.textContent = "";
}

function renderRecommendations(data) {
  clearResults();

  meta.textContent = `Request: ${data.request_id} | Latency: ${data.latency_ms}ms | Source: ${data.ranking_source}`;

  if (data.ranking_source === "rule_based_fallback") {
    fallbackNote.textContent = "Fallback active: rule-based ranking used.";
    fallbackNote.classList.remove("hidden");
  }

  if (data.warnings && data.warnings.length > 0) {
    warnings.textContent = `Warnings: ${data.warnings.join(" | ")}`;
    warnings.classList.remove("hidden");
  }

  if (!data.recommendations || data.recommendations.length === 0) {
    emptyState.classList.remove("hidden");
    return;
  }

  data.recommendations.forEach((item) => {
    const card = document.createElement("article");
    card.className = "card";
    card.innerHTML = `
      <h3>#${item.rank} ${item.restaurant_name}</h3>
      <p class="row"><strong>Cuisine:</strong> ${Array.isArray(item.cuisine) ? item.cuisine.join(", ") : ""}</p>
      <p class="row"><strong>Rating:</strong> ${item.rating ?? "N/A"}</p>
      <p class="row"><strong>Estimated Cost:</strong> ${item.estimated_cost ?? "N/A"}</p>
      <p class="row"><strong>Explanation:</strong> ${item.ai_explanation}</p>
      <p class="row"><strong>Highlights:</strong> ${(item.fit_highlights || []).join(", ")}</p>
    `;
    cards.appendChild(card);
  });
}

function buildPayload() {
  const payload = {
    location: document.getElementById("location").value.trim(),
    budget: document.getElementById("budget").value || null,
    cuisine: document.getElementById("cuisine").value.trim() || null,
    min_rating: document.getElementById("min_rating").value ? Number(document.getElementById("min_rating").value) : null,
    additional_preferences: document.getElementById("additional_preferences").value.trim() || null,
    top_k: Number(document.getElementById("top_k").value || 5),
  };
  return payload;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  clearResults();
  submitBtn.disabled = true;
  setStatus("Loading: fetching recommendations...");

  try {
    const response = await fetch(`${BACKEND_BASE_URL.replace(/\/$/, "")}/recommendations`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(buildPayload()),
    });
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
      setStatus("Error: backend returned non-JSON response.");
      warnings.textContent =
        "Configured backend URL does not expose JSON API at /recommendations. " +
        "Deploy FastAPI backend endpoint and point frontend to that URL.";
      warnings.classList.remove("hidden");
      return;
    }
    const data = await response.json();

    if (!response.ok) {
      setStatus("Error: request failed.");
      warnings.textContent = `Error: ${JSON.stringify(data)}`;
      warnings.classList.remove("hidden");
      return;
    }

    setStatus("Success: recommendations received.");
    renderRecommendations(data);
  } catch (err) {
    setStatus("Error: unable to connect to API.");
    warnings.textContent = String(err);
    warnings.classList.remove("hidden");
  } finally {
    submitBtn.disabled = false;
  }
});
