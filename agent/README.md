# AI Multi-Day Trip Designer

An agentic service that generates grounded, group-aware multi-day road-trip
itineraries. Built on CrewAI. Runs locally on Ollama or on a cheap cloud model
via a single config switch, and deploys as a FastAPI service that your
`aurelia-travel-backend` can call over the internet.

## Why this is structured the way it is

| Concern | Where it lives | Why |
|---|---|---|
| Settings / secrets | `app/config/settings.py` + `.env` | Switch model or data source without code edits |
| Data schemas | `app/models/schemas.py` | One source of truth for API + CLI |
| Grounding (real data) | `app/tools/` | Web search, aurelia backend, maps — all swappable |
| LLM selection | `app/services/llm_factory.py` | ollama / openai / gemini behind one function |
| Agents & tasks | `app/agents/`, `app/tasks/` | Your two-agent design, config-driven tools |
| Orchestration | `app/services/trip_designer.py` | The reliability brain (see below) |
| Delivery | `app/api/main.py` (HTTP), `app/cli.py` (terminal) | Same service, two front doors |

## The reliability strategy (the important part)

Small local models break when asked to emit a deep nested JSON tree in one shot.
So we don't ask them to:

1. **One route per LLM call.** Each call fills a single shallow `RouteOption`.
   The 3 routes are assembled in Python afterward.
2. **Validation-retry.** If output fails Pydantic validation, we retry up to
   `MAX_VALIDATION_RETRIES` times before giving up on that route.
3. **Deterministic map URLs.** The LLM never writes the Google Maps URL — Python
   builds it from the town names, so it's always valid.
4. **Fail-soft grounding.** If web search or the backend is down, the agent
   degrades gracefully instead of crashing.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # adjust as needed
```

### Model choice for a 4GB RTX 3050
`llama3.1` (8B) is large for 4GB VRAM and weak at deep JSON. Recommended:

```
ollama pull qwen2.5:7b      # strong at structured output
# or
ollama pull mistral         # fast, clean JSON
```
Set `LLM_MODEL=ollama/qwen2.5:7b`. Use `Q4_K_M` quant to fit VRAM.

### Switching to cheap cloud (for reliable demos)
```
LLM_PROVIDER=gemini
LLM_MODEL=gemini/gemini-2.0-flash
GEMINI_API_KEY=...
```

## Run

```bash
# Terminal (your original interactive flow)
python -m app.cli

# API service (deploy this; aurelia calls it)
uvicorn app.api.main:app --reload --port 8000
# -> POST http://localhost:8000/design-trip   (docs at /docs)

# Tests (the deterministic, no-LLM logic)
pytest -q
```

## Connecting to aurelia-travel-backend

1. Set `ENABLE_AURELIA_BACKEND=true` and `AURELIA_BASE_URL` in `.env`.
2. Implement `GET /api/hotels/availability?town=&checkIn=&group=` on the Node
   side, returning `{ "hotels": [{ name, roomConfiguration, pricePerNight, capacityNote }] }`.
3. Adjust field names in `app/tools/aurelia_backend.py` to match your real API.

Once enabled, the agent grounds hotels/rooms/prices in your real, bookable
inventory instead of inferring them from web snippets.

## Roadmap

- [ ] Caching layer (your aurelia project already uses Redis — reuse it)
- [ ] Real Google Maps geocoding/validation via `GOOGLE_MAPS_API_KEY`
- [ ] Streaming progress to the client during generation
- [ ] Containerize (`Dockerfile`) for deployment
