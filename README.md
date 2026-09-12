# NutriAgent

A multi-agent AI nutrition advisor. Four independent FastAPI services
(agents), each owned by one team member, connected by plain HTTP calls.

This starter has **no Docker** - each agent runs directly with `uvicorn`
in its own terminal. That's enough for local dev and for the mid-eval demo.

```
nutriagent/
  shared/             <- schemas.py: the JSON contract every agent imports
  security_agent/     <- Member 1
  intake_agent/        <- Member 2
  ir_agent/             <- Member 3
  planning_agent/       <- Member 4
  README.md
  .gitignore
```

Every agent already calls the next one in the chain. The Security Agent
has implemented authentication, validation, rate limiting, tracing, and
encryption utilities, with 89 passing tests at final verification. It is
ready for integration testing; the other agents' next steps are listed below.

---

## 1. One-time setup

You can share a single virtual environment for the whole repo (simplest for
a small project like this):

```bash
git clone <your-repo-url>
cd nutriagent
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r security_agent/requirements.txt
pip install -r intake_agent/requirements.txt
pip install -r ir_agent/requirements.txt
pip install -r planning_agent/requirements.txt
```

For Security, use Python 3.12 and configure the variables listed in
`.env.example` through your local environment or an ignored root `.env`.
Keep existing local settings private; never commit real credentials or keys.
Set `JWT_SECRET` to a generated random secret (at least 32 UTF-8 bytes for
HS256), and set `DEMO_USER_ID` and `DEMO_PASSWORD` for the mock login.
Missing, known placeholder, and undersized JWT secrets fail configuration
loading. `FERNET_KEY` is required only when calling the encryption utilities.

## 2. Running all four agents

Open **4 terminals**, activate the same venv in each, and run one agent per
terminal **from the repo root** (important - this is what makes `from
shared.schemas import ...` work):

```bash
# terminal 1
python -m uvicorn security_agent.main:app --reload --port 8001

# terminal 2
uvicorn intake_agent.main:app --reload --port 8002

# terminal 3
uvicorn ir_agent.main:app --reload --port 8003

# terminal 4
uvicorn planning_agent.main:app --reload --port 8004
```

Each agent also exposes interactive API docs at e.g. `http://localhost:8001/docs`.

## 3. Testing the full pipeline

With all four services running, first log in through Security on port 8001.
The examples below use `demo` as the configured `DEMO_USER_ID`; substitute
your configured ID in both requests. Replace the password and token
placeholders locally. Credentials belong in the JSON body, not the URL.

1. Send `POST /login`:

```bash
curl -X POST http://localhost:8001/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"<configured-demo-password>"}'
```

2. Receive the JWT in `access_token`:

```json
{"access_token":"<returned-jwt>","token_type":"bearer"}
```

3. Send `POST /process` with that token and the matching user ID:

```bash
curl -X POST http://localhost:8001/process \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "demo",
    "raw_text": "I want to lose weight, I am allergic to peanuts",
    "token": "<returned-jwt>"
  }'
```

Security validates the request and forwards only `user_id` and trimmed,
plaintext `raw_text` to Intake. Intake calls IR and Planning. The expected
successful integration response is a JSON meal plan with `meals` that avoid
peanuts, each with a `reason`.

Each agent also has its own `/health` endpoint and can be tested in
isolation via its `/docs` page - useful for proving your agent works even
before the others are ready.

---

## 4. Next steps - per agent

### Member 1: Security & Validation Agent (`security_agent/`)

Implemented and verified on Python 3.12; the service runs on port **8001**.

| Endpoint | Behavior | Default rate limit per client IP |
| --- | --- | --- |
| `GET /health` | Returns `{"status":"ok","agent":"security"}` without authentication | Unrestricted |
| `POST /login` | Accepts JSON `username` and `password`; returns `access_token` and `token_type` | `5/minute` via `LOGIN_RATE_LIMIT` |
| `POST /process` | Requires the JSON `token` field and validates text before calling Intake | `10/minute` via `PROCESS_RATE_LIMIT` |

JWTs require a valid signature, nonempty subject (`sub`), and expiration
(`exp`). `JWT_ALGORITHM` defaults to `HS256`, and `JWT_EXPIRE_MINUTES`
defaults to `30`. The verified subject must equal `request.user_id`.
The token is not forwarded to Intake.

Input validation rejects empty/whitespace-only text and `raw_text` longer
than **5,000 characters**, counting leading/trailing whitespace. Accepted
input is trimmed while internal whitespace is preserved. Deterministic
regex checks block obvious instruction overrides such as "ignore all
previous instructions", "disregard previous instructions", and "forget
previous rules", system-prompt requests, script tags, and `DROP TABLE`
payloads. Checks handle case variations and extra whitespace.

SlowAPI quota checks run before body validation on both POST endpoints.
Malformed JSON, empty bodies, missing fields, and failed authentication
attempts also consume quota. Valid requests count once. Invalid rate-limit
configuration falls back to the defaults above.

| Status | Meaning |
| --- | --- |
| `400` | Empty, oversized, or unsafe text |
| `401` | Invalid login credentials, or missing/invalid/expired JWT on `/process` |
| `403` | JWT subject differs from `user_id` |
| `422` | Malformed request or invalid fields, including invalid Unicode credentials; errors omit submitted values |
| `429` | Rate limit exceeded, including by malformed requests |
| `502` | Sanitized Intake connection/protocol failure, unsuccessful downstream status, or invalid downstream JSON |
| `503` | Mock login credentials are not configured |
| `504` | Sanitized Intake timeout |

Request logs are structured JSON containing timestamp, trace ID, agent
(`security`), method, route path, response status, and duration. They omit
bodies, query strings, passwords, JWTs, keys, and sensitive health text.
Security preserves a single canonical UUID4 `X-Trace-ID` header when valid;
otherwise it generates a UUID4. The ID is returned in response headers
(including handled errors and 429s) and forwarded to Intake as `X-Trace-ID`.
This does not add a field to the JSON contract. Unexpected unhandled 500s
may lack the response header; downstream failures above are handled.

`security_agent/encryption.py` exposes `encrypt_sensitive_data(str) -> str`
and `decrypt_sensitive_data(str) -> str` using `cryptography.fernet` and
`FERNET_KEY` from configuration. The utilities support UTF-8 and reject
missing/malformed keys and invalid/tampered ciphertext without disclosure.
They are intended for future persisted allergies, medical conditions, or
other sensitive health fields. Security does not store health data, so the
utilities are not connected to persistence. `raw_text` remains plaintext
when sent to Intake; JWTs and passwords are not encrypted with Fernet.

Run the Security Agent test suite from the repository root:

```bash
python -B -m unittest discover -s security_agent/tests -v
```

At final verification: **89 passed, 0 failed**. Tests use dummy configuration
and mocked Intake; they do not require port 8002 or real secrets. Live
four-agent integration testing is the next step.

Limitations:

- Login uses one mock university-project account, not production user management.
- Regex protection does not detect every possible prompt injection.
- Rate-limit counters are in-memory/per-process, are not shared across workers, and reset on restart.
- The 5,000-character check is application-level validation, not an HTTP request-size limit.
- Fernet utilities are available for future storage; no health-data persistence exists in Security.

### Member 2: Intake & Profile Agent (`intake_agent/`)
Currently: keyword-matches against hardcoded allergy/condition/goal lists.
- [ ] Replace `extract_profile()` with real NER. Two options:
  - **spaCy**: load a base model, add a custom entity ruler or train on a
    small labeled set of allergy/condition phrases.
  - **LLM-based extraction**: send the raw text to an LLM with a prompt
    that returns strict JSON matching `UserProfile`, then validate it with
    the existing pydantic model.
- [ ] Add intent classification (new profile vs. update vs. one-off query)
  if you want the agent to behave differently for repeat users.
- [ ] Persist profiles somewhere (even a simple SQLite file to start) so a
  returning user doesn't have to re-describe themselves every time.
- [ ] Write test cases: a sentence with multiple allergies, a sentence with
  no extractable info, a sentence with a goal phrased differently than your
  keyword list expects (this will show you where the stub breaks and real
  NLP is needed).

### Member 3: Nutrition IR Agent (`ir_agent/`)
Currently: filters a 5-item mock list by allergy substring match.
- [ ] Download or connect to a real dataset - USDA FoodData Central has a
  free API and downloadable CSVs. Decide as a team which you're using.
- [ ] Load it into a vector store (`chromadb` is the easiest to start with)
  using `sentence-transformers` embeddings (e.g. `all-MiniLM-L6-v2`).
- [ ] Replace the full-list-filter logic with: embed `request.query` ->
  similarity search -> take top-k -> then apply the allergy/diet hard
  filter on those results (filtering should happen on real data, not just
  the mock list).
- [ ] Test retrieval quality: does "high protein vegetarian dinner" actually
  return sensible matches?

### Member 4: Meal Planning Agent (`planning_agent/`)
Currently: a rule-based stub that just relabels the retrieved items with a
generic reason - no LLM call yet.
- [ ] Pick an LLM provider and get an API key (this is often the slowest
  step for the team, so do it early). The commented-out example in
  `main.py` shows the Anthropic SDK shape.
- [ ] Write the prompt: pass in `request.profile` and
  `request.retrieved_items` explicitly, and instruct the model to only
  recommend from the given items, with a `reason` tied to a specific
  profile field for each one (this is what makes the output explainable
  rather than a black box).
- [ ] Validate the LLM's response against the `MealPlan` pydantic model
  before returning it - don't trust raw LLM output blindly, this is also a
  Responsible AI point you can raise in the viva.
- [ ] Add a basic content filter: if the model's output starts drifting
  into medical-diagnosis territory, refuse and fall back to a safe default
  message.

---

## 5. Team-wide checklist before final submission

- [ ] Every agent's stub logic replaced with the real implementation above
- [ ] End-to-end test run recorded (for the Gen AI video)
- [ ] Each member's section of this README updated to reflect what was
  actually built vs. planned (useful for the individual-contribution
  question in the viva)
