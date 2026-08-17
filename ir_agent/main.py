"""
Nutrition Information Retrieval (IR) Agent
--------------------------------------------
The "ground truth" layer. Given a profile and a query, returns real
nutrition data - never invented numbers - for the Planning Agent to reason
over.

Current implementation uses a small in-memory MOCK_FOOD_DB and simple
allergy filtering, standing in for real retrieval (see TODOs).

NOT yet implemented (see "Next steps" in the README for this agent):
  - Loading a real dataset (USDA FoodData Central or similar)
  - Embedding food items and indexing them in a vector DB (chromadb/faiss)
  - Embedding the incoming query and doing similarity search instead of
    returning the whole mock list
"""

import sys
import pathlib

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from fastapi import FastAPI

from shared.schemas import IRRequest, IRResponse, FoodItem

app = FastAPI(title="NutriAgent - Nutrition IR Agent")

# TODO: replace with a real dataset loaded from USDA FoodData Central (or
# similar) and indexed in a vector store (chromadb / faiss-cpu) using
# sentence-transformers embeddings. This mock list exists so the rest of
# the pipeline has real data to pass around while that's being built.
MOCK_FOOD_DB = [
    FoodItem(name="Lentil and spinach curry", calories=420, protein_g=22, carbs_g=48, fat_g=10),
    FoodItem(name="Grilled chicken breast", calories=280, protein_g=35, carbs_g=0, fat_g=8),
    FoodItem(name="Chickpea salad", calories=310, protein_g=14, carbs_g=40, fat_g=9),
    FoodItem(name="Peanut butter toast", calories=350, protein_g=12, carbs_g=30, fat_g=18),
    FoodItem(name="Greek yogurt with berries", calories=190, protein_g=17, carbs_g=20, fat_g=4),
]


@app.get("/health")
def health():
    return {"status": "ok", "agent": "ir"}


@app.post("/process", response_model=IRResponse)
async def process(request: IRRequest):
    # TODO: replace this hard filter + full-list return with:
    #   1. embed request.query
    #   2. similarity search against the vector index
    #   3. THEN apply the allergy/diet hard filters below to the top-k results
    allergies = {a.lower() for a in request.profile.allergies}
    filtered = [
        item for item in MOCK_FOOD_DB
        if not any(allergen in item.name.lower() for allergen in allergies)
    ]
    return IRResponse(items=filtered)
