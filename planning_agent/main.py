"""
Meal Planning Agent
---------------------
The reasoning layer. Takes a UserProfile and the food items retrieved by
the IR Agent, and produces a final, explainable meal plan.

Current implementation is a rule-based STUB (no LLM call yet) so the
pipeline is fully runnable without needing an API key. See TODOs for
where the real LLM call goes.

NOT yet implemented (see "Next steps" in the README for this agent):
  - Actual LLM call (Claude/OpenAI) with a constrained prompt
  - Structured-output validation of the LLM's response against MealPlan
  - A basic content filter to refuse anything resembling medical diagnosis
"""

import sys
import pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from fastapi import FastAPI

from shared.schemas import PlanningRequest, MealPlan, MealRecommendation

app = FastAPI(title="NutriAgent - Meal Planning Agent")


@app.get("/health")
def health():
    return {"status": "ok", "agent": "planning"}


@app.post("/process", response_model=MealPlan)
async def process(request: PlanningRequest):
    # TODO: replace this rule-based stub with a real LLM call, e.g.:
    #
    #   from anthropic import Anthropic
    #   client = Anthropic()  # reads ANTHROPIC_API_KEY from env
    #   prompt = build_prompt(request.profile, request.retrieved_items)
    #   response = client.messages.create(
    #       model="claude-sonnet-5",
    #       max_tokens=1000,
    #       messages=[{"role": "user", "content": prompt}],
    #   )
    #   # then parse response into MealPlan - validate it, don't trust it blindly
    #
    # Keep the instruction to the LLM constrained: only reason about the
    # foods in request.retrieved_items, and require a "reason" tied to a
    # specific field of the profile for every recommendation (explainability).

    goals = request.profile.goals or ["general health"]
    allergies = request.profile.allergies or []

    meals = [
        MealRecommendation(
            name=item.name,
            calories=item.calories,
            reason=(
                f"Fits goal(s) {', '.join(goals)}"
                + (f"; avoids allergen(s) {', '.join(allergies)}" if allergies else "")
            ),
            source=item.source,
        )
        for item in request.retrieved_items[:3]
    ]

    return MealPlan(user_id=request.profile.user_id, meals=meals)
