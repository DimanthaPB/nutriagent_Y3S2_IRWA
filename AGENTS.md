# NutriAgent — System Context for AI Coding Agents

This document exists to give an AI coding assistant (Antigravity, Claude
Code, or similar) full context on this codebase before making changes. Read
this in full before editing any agent.

---

## 1. What this project is

NutriAgent is a **multi-agent AI nutrition advisor**, built as a university
project (IT3041 — Information Retrieval & Web Analytics, SLIIT). It takes a
user's free-text description of their goals/allergies/conditions and
returns a personalized, explainable meal plan, grounded in real nutrition
data rather than model-invented numbers.

The system is deliberately split into **4 independent microservices
("agents")**, each owned by a different team member, communicating over
plain HTTP with a shared JSON contract. There is no orchestrator process —
each agent calls the next one directly and the response flows back up the
same chain it came down.

**Current status:** the full pipeline runs end-to-end today, but every
agent's core logic is a **simplified stub**, not the final implementation.
The purpose of the current code is to prove the architecture and contracts
work, so each team member can now replace their own stub independently
without breaking anyone else's agent — as long as the shared schema is
respected.

---

## 2. Architecture

```
Client
  |
  v
Security & Validation Agent   (port 8001) — auth, input sanitization, gateway
  |
  v
Intake & Profile Agent        (port 8002) — free text -> structured UserProfile
  |
  +--> Nutrition IR Agent      (port 8003) — retrieves grounded food/nutrition data
  |         |
  |         v
  +--> Meal Planning Agent    (port 8004) — reasons over profile + retrieved data
            |
            v
      Final MealPlan response flows back up: Planning -> Intake -> Security -> Client
```

Call pattern: **synchronous HTTP, chained**. The Security Agent calls
Intake and returns its response. Intake calls IR, then calls Planning
(passing IR's output in), and returns Planning's response. There is no
message queue, no async event bus, and no separate orchestrator — this is
intentional for simplicity at this stage of the project.

---

## 3. Repository layout

```
nutriagent/
  shared/
    schemas.py        <- THE CONTRACT. Every agent imports these pydantic
                          models instead of defining its own. Changing a
                          field here affects all 4 agents — coordinate with
                          the team before editing.
  security_agent/
    main.py            <- FastAPI app, port 8001
    requirements.txt
  intake_agent/
    main.py            <- FastAPI app, port 8002
    requirements.txt
  ir_agent/
    main.py            <- FastAPI app, port 8003
    requirements.txt
  planning_agent/
    main.py            <- FastAPI app, port 8004
    requirements.txt
  README.md            <- setup/run instructions + per-member next-steps checklist
```

Each agent folder is a self-contained Python package (has `__init__.py`)
and imports `shared.schemas` via a `sys.path` insert in `main.py` pointing
at the repo root — this only works correctly if `uvicorn` is launched
**from the repo root**, e.g. `uvicorn security_agent.main:app --port 8001`.

There is **no Docker** in this project by design (kept simple for a
university team project) — agents are run directly with `uvicorn`, one per
terminal, or via a process manager if that's added later.

---

## 4. The shared contract (`shared/schemas.py`)

This is the single source of truth for all inter-agent JSON. Key models:

- `UserProfile` — user_id, goals, allergies, conditions, diet_type, calorie_target, preferences
- `SecurityRequest` — what the client sends in (user_id, raw_text, token)
- `IntakeRequest` — what Security forwards to Intake (user_id, raw_text)
- `FoodItem` — name, calories, macros, source
- `IRRequest` / `IRResponse` — profile+query in, list of FoodItem out
- `PlanningRequest` — profile + retrieved_items
- `MealPlan` — final response: user_id, list of MealRecommendation, disclaimer

**Rule for future changes:** if a field needs to change, change it here
first, then update every agent that touches it. Do not create parallel/local
copies of these models inside an agent folder — that's how the contract
drifts and agents silently break against each other.

---

## 5. Per-agent current state and what's real vs. stubbed

### Security & Validation Agent (`security_agent/main.py`)
- **Real:** FastAPI app, `/health` endpoint, regex-based rejection of a
  small list of prompt-injection/malicious patterns, forwarding to Intake.
- **Stubbed:** `authenticate()` always returns `True` — no real JWT check
  yet. No encryption of stored data (nothing is persisted here yet anyway).
  No rate limiting. No structured trace-ID logging.
- **To extend:** add real JWT verification, `cryptography.fernet` for
  encrypting any health data before storage, `slowapi` for rate limiting,
  and per-request trace IDs propagated to downstream agents via a header.

### Intake & Profile Agent (`intake_agent/main.py`)
- **Real:** FastAPI app, calls IR then Planning and returns the final
  result.
- **Stubbed:** `extract_profile()` does keyword/substring matching against
  hardcoded lists (`KNOWN_ALLERGIES`, `KNOWN_CONDITIONS`, `KNOWN_GOALS`) —
  this is not real NLP.
- **To extend:** replace with spaCy NER or an LLM-based extraction call
  that returns JSON validated against `UserProfile`. No persistence layer
  exists yet — profiles are rebuilt from scratch on every request.

### Nutrition IR Agent (`ir_agent/main.py`)
- **Real:** FastAPI app, returns nutrition data filtered by allergy
  substring match.
- **Stubbed:** `MOCK_FOOD_DB` is a 5-item hardcoded Python list, not a real
  dataset. There is no embedding or similarity search — the "retrieval" is
  just a full-list filter.
- **To extend:** load a real dataset (USDA FoodData Central is the
  team's intended source), embed items with `sentence-transformers`, index
  in `chromadb` or `faiss`, and do actual similarity search on
  `request.query` before applying the allergy/diet hard filter.

### Meal Planning Agent (`planning_agent/main.py`)
- **Real:** FastAPI app, returns a `MealPlan` shape.
- **Stubbed:** no LLM call at all — it relabels the top 3 retrieved items
  with a templated `reason` string. This is the least-implemented agent.
- **To extend:** call an LLM (Anthropic or OpenAI SDK — a commented example
  using the Anthropic SDK is already in the file) with a prompt that passes
  in `request.profile` and `request.retrieved_items` explicitly, constrains
  the model to only reason about those items, and requires each
  recommendation's `reason` to tie back to a specific profile field. Then
  validate the LLM's output against `MealPlan` before returning it — do not
  trust raw LLM JSON output without validation.

---

## 6. Running and testing (for the agent to verify its own changes)

```bash
# from repo root, one venv is enough
python3 -m venv .venv && source .venv/bin/activate
pip install -r security_agent/requirements.txt
pip install -r intake_agent/requirements.txt
pip install -r ir_agent/requirements.txt
pip install -r planning_agent/requirements.txt

# 4 separate terminals, all from repo root:
uvicorn ir_agent.main:app --port 8003
uvicorn planning_agent.main:app --port 8004
uvicorn intake_agent.main:app --port 8002
uvicorn security_agent.main:app --port 8001
```

End-to-end smoke test:
```bash
curl -X POST http://localhost:8001/process \
  -H "Content-Type: application/json" \
  -d '{"user_id": "u123", "raw_text": "I want to lose weight, I am allergic to peanuts"}'
```
Expected: a `MealPlan` JSON with `meals` that exclude anything containing
"peanut" in the name, each with a non-empty `reason`. Every agent also
exposes `/health` for isolated checks and `/docs` (FastAPI's auto-generated
Swagger UI) for manual testing of a single agent.

**When making changes:** always re-run this smoke test after editing an
agent, since a change to `shared/schemas.py` or to one agent's response
shape can silently break a downstream agent that assumes the old shape.

---

## 7. Conventions to preserve when extending this codebase

- New/changed fields go in `shared/schemas.py` first, never duplicated locally.
- Every agent keeps a `/health` endpoint returning `{"status": "ok", "agent": "<name>"}`.
- Agent-to-agent URLs are read from environment variables with
  `localhost:<port>` defaults (see `os.getenv(...)` calls in each
  `main.py`) — don't hardcode URLs without an env override, since this is
  what will let the team later run agents on different hosts if needed.
- Each stub is marked with `# TODO` comments explaining exactly what real
  implementation should replace it — search for `TODO` across the repo
  before assuming something is unimplemented.
- No Docker, no message queue, no orchestrator — keep the architecture this
  simple unless the team explicitly decides to add that complexity; this is
  a course project with a Week 10 deadline, not a production system.

---

## 8. Known limitations / explicitly out of scope for now

- No database — nothing persists between requests.
- No real authentication, encryption, or rate limiting yet (Security Agent
  is a partial implementation).
- No automated test suite yet (manual `curl`/`/docs` testing only).
- No frontend client exists yet — the system is API-only.
- Nutrition data is a 5-item mock list, not a real dataset.
