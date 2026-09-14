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

**Current Security status:** the Security & Validation Agent has implemented
JWT authentication, input validation, rate limiting, structured tracing, and
Fernet utilities. Final verification passed 89 tests on Python 3.12; Security
is ready for integration testing. Preserve the chained architecture and
shared schemas when extending any agent. Other agents' current states and
next steps are documented in their sections below.

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
    auth.py            <- JWT creation and verification
    validation.py      <- Text limits and deterministic rejection rules
    rate_limiting.py   <- SlowAPI checks before body validation
    logging_config.py  <- Structured request logs and UUID4 trace headers
    encryption.py      <- Standalone Fernet utilities for future storage
    tests/             <- Security unit and mocked gateway tests
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

- **Endpoints (port 8001):** unrestricted `GET /health` returns
  `{"status":"ok","agent":"security"}`. `POST /login` accepts JSON
  `username` and `password` and returns `access_token` plus `token_type`.
  `POST /process` accepts the existing shared `SecurityRequest` body.
- **Authentication:** login checks the configured `DEMO_USER_ID` and
  `DEMO_PASSWORD`. JWT signature, nonempty `sub`, and `exp` are verified.
  Invalid credentials or missing/invalid/expired JWTs return `401`;
  a verified subject different from `request.user_id` returns `403`.
  Malformed fields and invalid Unicode credentials return sanitized `422`.
  Missing demo credentials return `503`.
- **Configuration:** root `.env` loading for authentication is explicit;
  existing environment variables take precedence. Never inspect or expose
  local secrets. `JWT_SECRET` must not be empty, a known placeholder, or
  shorter than 32/48/64 UTF-8 bytes for HS256/HS384/HS512 respectively.
  Invalid JWT configuration fails at load time. Defaults are HS256 and
  `JWT_EXPIRE_MINUTES=30`; configuration names are listed in `.env.example`.
- **Validation:** authentication and identity checks precede text validation,
  which precedes forwarding. Empty/whitespace-only text, input over 5,000
  characters (including padding), and blocked patterns return `400`.
  Trimming preserves internal whitespace. Case-insensitive regexes handle
  extra whitespace in obvious prompt-injection commands (ignore/disregard/
  forget/override instructions or rules), system-prompt references, script
  tags, and `DROP TABLE` payloads. Normal nutrition requests remain allowed.
- **Rate limiting:** SlowAPI uses separate per-client-IP quotas for `/login`
  (`LOGIN_RATE_LIMIT=5/minute`) and `/process`
  (`PROCESS_RATE_LIMIT=10/minute`). The route wrapper checks quota before
  body parsing, so malformed JSON, empty bodies, missing fields, and failed
  authentication consume quota. Valid requests count once; excess requests
  return `429`. Invalid configured limits fall back to defaults. `/health`
  is unrestricted.
- **Logging and tracing:** one structured JSON request record contains UTC
  timestamp, `trace_id`, agent `security`, method, route path, status, and
  duration. Never log bodies, query strings, passwords, JWTs, keys, or health
  text. Accept a single canonical UUID4 `X-Trace-ID`, otherwise generate a
  UUID4. Return it in response headers, including handled errors and 429s,
  and forward the same header to Intake. Unexpected unhandled 500s may lack
  the response header.
- **Gateway contract:** send exactly `{"user_id": ..., "raw_text": ...}`
  to Intake, using trimmed **plaintext** text. Do not forward JWTs or add
  trace IDs to the JSON body. Intake connection/protocol failures,
  unsuccessful HTTP statuses, and invalid JSON return sanitized `502`;
  timeouts return sanitized `504`, with trace headers and no exception details.
- **Fernet:** `encrypt_sensitive_data(str) -> str` and
  `decrypt_sensitive_data(str) -> str` in `encryption.py` read `FERNET_KEY`
  lazily from configuration. They support UTF-8 and reject missing/invalid
  keys and invalid/tampered ciphertext safely. They are for future persisted
  allergies, conditions, and health fields. Security stores no health data;
  do not connect encryption to current forwarding, JWTs, or passwords.
- **Limitations:** login remains one mock university-project account; regex
  rules do not detect every prompt injection; counters are in-memory and
  per-process and reset on restart; 5,000 characters is an application-level
  check, not an HTTP request-size limit. Fernet is not connected to persistence.
- **Verification:** 89 Security tests passed at final verification, using
  dummy configuration and mocked Intake. Live integration remains to be run.

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
python -m uvicorn security_agent.main:app --port 8001
```

Before starting Security, configure JWT and mock-login variables locally as
described in the Security section. Keep `.env` ignored and use only
placeholders in shared examples. `FERNET_KEY` is needed only for utility calls.

Security-only tests (from the repository root, Intake mocked):

```bash
python -B -m unittest discover -s security_agent/tests -v
```

End-to-end smoke test with all four agents running:

1. Log in with JSON credentials. Replace the example username with your
   configured `DEMO_USER_ID` and use your configured password locally.

```bash
curl -X POST http://localhost:8001/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"<configured-demo-password>"}'
```

2. Receive `{"access_token":"<returned-jwt>","token_type":"bearer"}`.
3. Send the returned token and the same user ID to `/process`:

```bash
curl -X POST http://localhost:8001/process \
  -H "Content-Type: application/json" \
  -d '{"user_id":"demo","raw_text":"I want to lose weight, I am allergic to peanuts","token":"<returned-jwt>"}'
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
- Security implements JWT verification, rate limiting, structured tracing,
  and standalone Fernet utilities; login is still a mock account and no
  health data is persisted or encrypted in the active forwarding pipeline.
- Security has automated tests with mocked Intake; use the authenticated
  smoke test above for live integration verification.
- No frontend client exists yet — the system is API-only.
- Nutrition data is a 5-item mock list, not a real dataset.
