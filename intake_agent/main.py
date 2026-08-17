"""
Intake & Profile Agent
-----------------------
Turns messy free-text input into a structured UserProfile, then kicks off
the rest of the pipeline (IR Agent, then Planning Agent) and returns the
final result back up to the Security Agent.

Current implementation is a keyword-matching STUB standing in for real NLP
(see TODOs). It's good enough to prove the pipeline connects end-to-end.

NOT yet implemented (see "Next steps" in the README for this agent):
  - Real NER (spaCy model or an LLM extraction call)
  - Intent classification (new profile vs. update vs. one-off query)
  - Persisting the profile to a database
"""

import os
import sys
import pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

import httpx
from fastapi import FastAPI

from shared.schemas import IntakeRequest, UserProfile

app = FastAPI(title="NutriAgent - Intake & Profile Agent")

IR_AGENT_URL = os.getenv("IR_AGENT_URL", "http://localhost:8003")
PLANNING_AGENT_URL = os.getenv("PLANNING_AGENT_URL", "http://localhost:8004")

# TODO: replace this with a real NER model / LLM extraction call.
# This is a placeholder so the pipeline has something to pass downstream.
KNOWN_ALLERGIES = ["peanuts", "shellfish", "dairy", "gluten", "eggs", "soy"]
KNOWN_CONDITIONS = ["diabetes", "lactose intolerant", "hypertension"]
KNOWN_GOALS = {
    "lose weight": "weight_loss",
    "gain muscle": "muscle_gain",
    "eat healthier": "general_health",
}


def extract_profile(user_id: str, text: str) -> UserProfile:
    text_lower = text.lower()
    allergies = [a for a in KNOWN_ALLERGIES if a in text_lower]
    conditions = [c for c in KNOWN_CONDITIONS if c in text_lower]
    goals = [tag for phrase, tag in KNOWN_GOALS.items() if phrase in text_lower]
    return UserProfile(
        user_id=user_id,
        allergies=allergies,
        conditions=conditions,
        goals=goals,
    )


@app.get("/health")
def health():
    return {"status": "ok", "agent": "intake"}


@app.post("/process")
async def process(request: IntakeRequest):
    profile = extract_profile(request.user_id, request.raw_text)

    async with httpx.AsyncClient() as client:
        ir_response = await client.post(
            f"{IR_AGENT_URL}/process",
            json={"profile": profile.model_dump(), "query": request.raw_text},
            timeout=30.0,
        )
        ir_response.raise_for_status()
        retrieved_items = ir_response.json()["items"]

        planning_response = await client.post(
            f"{PLANNING_AGENT_URL}/process",
            json={
                "profile": profile.model_dump(),
                "retrieved_items": retrieved_items,
            },
            timeout=30.0,
        )
        planning_response.raise_for_status()

    return planning_response.json()
