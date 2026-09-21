"""NutriAgent Intake & Profile Agent.

Extracts a structured ``UserProfile`` from free text, stores the latest
profile for returning users, then sends the profile to the IR and planning
agents. The public request and response contracts live in ``shared.schemas``.
"""

import os
import pathlib
import re
import sqlite3
import sys
from typing import Iterable, Literal

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

import httpx
import spacy
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

from shared.schemas import IntakeRequest, UserProfile

# Load root .env if present
load_dotenv(dotenv_path=pathlib.Path(__file__).resolve().parent.parent / ".env")

app = FastAPI(title="NutriAgent - Intake & Profile Agent")

IR_AGENT_URL = os.getenv("IR_AGENT_URL", "http://localhost:8003")
PLANNING_AGENT_URL = os.getenv("PLANNING_AGENT_URL", "http://localhost:8004")
PROFILE_DB_PATH = os.getenv(
    "PROFILE_DB_PATH", str(pathlib.Path(__file__).with_name("profiles.sqlite3"))
)

# EntityRuler gives transparent, deterministic NER without requiring a
# separately downloaded language model. A trained spaCy NER component can be
# added later without changing this API or the shared schema.
ENTITY_VALUES = {

    "ALLERGY": {
    "peanut": [
        "peanut",
        "peanuts",
        "peanut allergy",
        "peanut allergies",
    ],
    "tree_nuts": [
        "tree nut",
        "tree nuts",
        "tree nut allergy",
        "almond",
        "almonds",
        "cashew",
        "cashews",
        "walnut",
        "walnuts",
        "pistachio",
        "pistachios",
        "hazelnut",
        "hazelnuts",
    ],
    "shellfish": [
        "shellfish",
        "shellfish allergy",
        "shrimp",
        "prawn",
        "prawns",
        "crab",
        "lobster",
    ],
    "fish": [
        "fish",
        "fish allergy",
    ],
    "dairy": [
        "dairy",
        "dairy allergy",
        "milk",
        "milk allergy",
    ],
    "gluten": [
        "gluten",
        "gluten allergy",
        "wheat",
        "wheat allergy",
    ],
    "eggs": [
        "egg",
        "eggs",
        "egg allergy",
        "egg allergies",
    ],
    "soy": [
        "soy",
        "soya",
        "soy allergy",
        "soya allergy",
    ],
    "sesame": [
        "sesame",
        "sesame allergy",
    ],
    },

    "CONDITION": {
    "diabetes": [
        "diabetes",
        "diabetic",
        "type 1 diabetes",
        "type 2 diabetes",
        "type 1 diabetic",
        "type 2 diabetic",
    ],
    "hypertension": [
        "hypertension",
        "high blood pressure",
        "blood pressure",
    ],
    "lactose_intolerance": [
        "lactose intolerant",
        "lactose intolerance",
        "intolerant to lactose",
        "cannot tolerate lactose",
        "can't tolerate lactose",
    ],
    "celiac_disease": [
        "celiac",
        "coeliac",
        "celiac disease",
        "coeliac disease",
    ],
    "kidney_disease": [
        "kidney disease",
        "renal disease",
        "kidney problems",
        "kidney condition",
    ],
    },

    "GOAL": {
    "weight_loss": [
        "lose weight",
        "weight loss",
        "lose fat",
        "fat loss",
        "slim down",
        "reduce my weight",
        "drop weight",
        "burn fat",
        "get lean",
        "get leaner",
    ],
    "muscle_gain": [
        "gain muscle",
        "build muscle",
        "muscle gain",
        "bulk up",
        "increase muscle",
        "build up muscle",
        "muscle building",
        "gain strength",
    ],
    "general_health": [
        "general health",
        "general health meals",
        "improve my health",
        "eat healthier",
        "healthy eating",
        "maintain my health",
        "eat healthy",
        "healthy diet",
        "healthier diet",
        "improve overall health",
    ],
    "maintenance": [
        "maintain weight",
        "weight maintenance",
        "maintain my weight",
        "keep my weight",
        "maintain current weight",
        "maintain my current weight",
        "keep my current weight",
    ],
    },

    "DIET": {
    "vegan": [
        "vegan",
        "plant based",
        "plant-based",
        "plant based diet",
        "plant-based diet",
    ],
    "vegetarian": [
        "vegetarian",
        "vegetarian diet",
        "veggie",
        "meat free",
        "meat-free",
    ],
    "pescatarian": [
        "pescatarian",
        "pescetarian",
        "pescatarian diet",
        "pescetarian diet",
    ],
    "keto": [
        "keto",
        "ketogenic",
        "ketogenic diet",
        "keto diet",
    ],
    "halal": [
        "halal",
        "halal diet",
        "halal food",
    ],
    },

    "PREFERENCE": {
    "high_protein": [
        "high protein",
        "high-protein",
        "protein rich",
        "protein-rich",
        "more protein",
        "protein rich meals",
        "high protein meals",
    ],
    "low_carb": [
        "low carb",
        "low-carb",
        "low carbohydrate",
        "low carbohydrate meals",
        "reduced carbohydrate",
        "fewer carbs",
    ],
    "low_sodium": [
        "low sodium",
        "low-sodium",
        "low salt",
        "reduced sodium",
        "reduced salt",
        "less salt",
    ],
    "quick_meals": [
        "quick meals",
        "quick meal",
        "easy meals",
        "easy meal",
        "fast meals",
        "fast meal",
        "quick to prepare",
        "easy to prepare",
        "easy to cook",
    ],
    },



}


def build_nlp():
    nlp = spacy.blank("en")
    ruler = nlp.add_pipe("entity_ruler", config={"phrase_matcher_attr": "LOWER"})
    patterns = []
    for label, canonical_values in ENTITY_VALUES.items():
        for canonical, phrases in canonical_values.items():
            patterns.extend({"label": label, "pattern": phrase, "id": canonical} for phrase in phrases)
    ruler.add_patterns(patterns)
    return nlp


NLP = build_nlp()

CALORIE_TARGET_PATTERN = re.compile(
    r"(?:about|around|roughly|approximately|at most|under|up to|no more than|maximum of|less than)?"
    r"\s*(\d{3,4})\s*(?:kcal|calories|cals)(?:\s*(?:per day|a day|daily))?",
    re.IGNORECASE,
)

NEGATION_PATTERN = re.compile(
    r"\b(?:no|not\s+allergic\s+to|no\s+allerg(?:y|ies)\s+to|without)\s+$", re.I
)

HAVE_ALLERGY_NEGATION_PATTERN = re.compile(
    r"\b(?:don't|do\s+not)\s+have\s+(?:an?\s+)?[^.?!,;]{0,32}\ballerg(?:y|ies)\b", re.I
)


def _is_negated(text: str, start: int) -> bool:
    """Avoid treating statements such as 'no dairy allergy' as restrictions."""
    before_entity = text[max(0, start - 32):start]
    entity_context = text[max(0, start - 32):min(len(text), start + 48)]
    return bool(
        NEGATION_PATTERN.search(before_entity)
        or HAVE_ALLERGY_NEGATION_PATTERN.search(entity_context)
    )


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def classify_intent(text: str) -> Literal["new_profile", "profile_update", "one_off_query"]:
    """Classify a request for observability and future tailored behaviour."""
    value = text.lower()
    if re.search(r"\b(update|change|add|remove|instead|now|started|stopped)\b", value):
        return "profile_update"
    if "?" in value or re.search(r"\b(what|suggest|recommend|recipe|meal idea)\b", value):
        return "one_off_query"
    return "new_profile"


def extract_profile(user_id: str, text: str) -> UserProfile:
    """Use spaCy entities and numeric parsing to create a validated profile."""
    doc = NLP(text)
    extracted = {label: [] for label in ENTITY_VALUES}
    for entity in doc.ents:
        if not _is_negated(text, entity.start_char):
            extracted[entity.label_].append(entity.ent_id_)

    calorie_match = CALORIE_TARGET_PATTERN.search(text)
    return UserProfile(
        user_id=user_id,
        allergies=_unique(extracted["ALLERGY"]), conditions=_unique(extracted["CONDITION"]),
        goals=_unique(extracted["GOAL"]), diet_type=next(iter(_unique(extracted["DIET"])), None),
        calorie_target=int(calorie_match.group(1)) if calorie_match else None,
        preferences=_unique(extracted["PREFERENCE"]),
    )


def merge_profiles(existing: UserProfile, update: UserProfile) -> UserProfile:
    """Keep previous facts when a returning user provides a partial update."""
    return UserProfile(
        user_id=existing.user_id, goals=_unique([*existing.goals, *update.goals]),
        allergies=_unique([*existing.allergies, *update.allergies]),
        conditions=_unique([*existing.conditions, *update.conditions]),
        diet_type=update.diet_type or existing.diet_type,
        calorie_target=update.calorie_target or existing.calorie_target,
        preferences=_unique([*existing.preferences, *update.preferences]),
    )


class ProfileStore:
    """Small local persistence layer; its database path is configurable."""

    def __init__(self, database_path: str = PROFILE_DB_PATH):
        self.database_path = database_path
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute("CREATE TABLE IF NOT EXISTS profiles (user_id TEXT PRIMARY KEY, profile_json TEXT NOT NULL)")
            connection.commit()
        finally:
            connection.close()

    def get(self, user_id: str) -> UserProfile | None:
        connection = sqlite3.connect(self.database_path)
        try:
            row = connection.execute("SELECT profile_json FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
        finally:
            connection.close()
        return UserProfile.model_validate_json(row[0]) if row else None

    def save(self, profile: UserProfile) -> None:
        connection = sqlite3.connect(self.database_path)
        try:
            connection.execute(
                "INSERT INTO profiles(user_id, profile_json) VALUES(?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET profile_json = excluded.profile_json",
                (profile.user_id, profile.model_dump_json()),
            )
            connection.commit()
        finally:
            connection.close()


profile_store = ProfileStore()


@app.get("/health")
def health():
    return {"status": "ok", "agent": "intake"}

@app.get("/profile/{user_id}", response_model=UserProfile)
def get_profile(user_id: str):
    profile = profile_store.get(user_id)

    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found.")

    return profile

@app.post("/process")
async def process(request: IntakeRequest):
    extracted_profile = extract_profile(request.user_id, request.raw_text)
    existing_profile = profile_store.get(request.user_id)
    profile = merge_profiles(existing_profile, extracted_profile) if existing_profile else extracted_profile
    profile_store.save(profile)

    try:
        async with httpx.AsyncClient() as client:
            ir_response = await client.post(
                f"{IR_AGENT_URL}/process", json={"profile": profile.model_dump(), "query": request.raw_text}, timeout=30.0
            )
            ir_response.raise_for_status()
            retrieved_items = ir_response.json()["items"]
            planning_response = await client.post(
                f"{PLANNING_AGENT_URL}/process",
                json={"profile": profile.model_dump(), "retrieved_items": retrieved_items}, timeout=30.0,
            )
            planning_response.raise_for_status()
    except (httpx.HTTPError, KeyError) as error:
        raise HTTPException(status_code=502, detail="A downstream nutrition service is unavailable.") from error

    return planning_response.json()
