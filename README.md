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

Every agent already calls the next one in the chain, so the full pipeline
runs end-to-end today with stub logic. Your job now is to replace the
stubs (each file has `# TODO` comments marking exactly where) with real
implementations.

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

## 2. Running all four agents

Open **4 terminals**, activate the same venv in each, and run one agent per
terminal **from the repo root** (important - this is what makes `from
shared.schemas import ...` work):

```bash
# terminal 1
uvicorn security_agent.main:app --reload --port 8001

# terminal 2
uvicorn intake_agent.main:app --reload --port 8002

# terminal 3
uvicorn ir_agent.main:app --reload --port 8003

# terminal 4
uvicorn planning_agent.main:app --reload --port 8004
```

Each agent also exposes interactive API docs at e.g. `http://localhost:8001/docs`.

## 3. Testing the full pipeline

Hit the Security Agent (the front door) - it will call Intake, which calls
IR and Planning, and the final meal plan comes all the way back:

```bash
curl -X POST http://localhost:8001/process \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "u123",
    "raw_text": "I want to lose weight, I am allergic to peanuts"
  }'
```

You should get back a JSON meal plan with `meals` referencing food items
that avoid peanuts, each with a `reason`.

Each agent also has its own `/health` endpoint and can be tested in
isolation via its `/docs` page - useful for proving your agent works even
before the others are ready.

---

## 4. Next steps - per agent

### Member 1: Security & Validation Agent (`security_agent/`)
Currently: sanitizes obviously malicious text with regex, forwards to
Intake. Auth is stubbed to always pass.
- [ ] Implement real JWT verification (`python-jose` or `pyjwt`) - issue a
  token on a mock `/login` endpoint, require it on `/process`.
- [ ] Add field-level encryption for any health data before it's stored
  anywhere (use `cryptography.fernet` - straightforward symmetric encryption).
- [ ] Add rate limiting (`slowapi` is a simple drop-in for FastAPI).
- [ ] Add structured logging: generate a trace ID per request, log it (and
  which agent handled the request, and when) without logging raw sensitive
  content.
- [ ] Expand `BLOCKED_PATTERNS` with more prompt-injection test cases -
  write a few adversarial test inputs and confirm they're rejected.

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
