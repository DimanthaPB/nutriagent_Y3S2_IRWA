"""
Nutrition Information Retrieval (IR) Agent
--------------------------------------------
The "ground truth" layer. Given a profile and a query, retrieves real
nutrition data (calories, protein, carbs, fat) from USDA and curated sources
via dense semantic vector search (ChromaDB + sentence-transformers)
and applies deterministic allergy and dietary safety filters.
"""

import sys
import pathlib
from contextlib import asynccontextmanager

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from shared.schemas import IRRequest, IRResponse
from ir_agent.retriever import NutritionRetriever

retriever: NutritionRetriever = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global retriever
    print("[IR Agent] Initializing Nutrition Vector Retrieval Engine...")
    retriever = NutritionRetriever()
    print(f"[IR Agent] Ready! Total indexed items in vector database: {retriever.vector_store.count()}")
    yield


app = FastAPI(title="NutriAgent - Nutrition IR Agent", lifespan=lifespan)


@app.get("/health")
def health():
    count = retriever.vector_store.count() if retriever else 0
    return {
        "status": "ok",
        "agent": "ir",
        "indexed_items": count
    }


@app.post("/process", response_model=IRResponse)
async def process(request: IRRequest):
    """
    1. Embeds query augmented by user profile (goals, preferences, diet type).
    2. Performs vector similarity search over USDA and curated nutrition data.
    3. Strictly enforces hard allergy exclusions and dietary restrictions.
    4. Returns grounded, fact-checked FoodItem records to the planning pipeline.
    """
    global retriever
    if retriever is None:
        retriever = NutritionRetriever()

    items = retriever.search_and_filter(
        profile=request.profile,
        query=request.query,
        top_k=10
    )
    return IRResponse(items=items)

