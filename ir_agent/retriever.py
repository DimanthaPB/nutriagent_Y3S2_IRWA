"""
Retriever and Safety Filter Engine for Nutrition IR Agent
----------------------------------------------------------
Performs two-stage retrieval:
  Stage 1: Semantic similarity vector search via ChromaDB & dense embeddings.
  Stage 2: Deterministic hard-constraint filtering (allergens, dietary restrictions, conditions).
"""

import re
from typing import List, Dict, Any, Optional
from shared.schemas import UserProfile, FoodItem
from ir_agent.vector_store import VectorStore


# Goal keyword expansions for query enrichment
GOAL_EXPANSIONS = {
    "weight loss": "low calorie lean nutrient dense high fiber",
    "lose weight": "low calorie lean nutrient dense high fiber",
    "muscle gain": "high protein muscle building lean protein",
    "build muscle": "high protein muscle building lean protein",
    "maintenance": "balanced healthy whole foods nutrition",
    "energy": "complex carbohydrates balanced energy",
    "endurance": "carbohydrates stamina electrolyte rich",
    "heart health": "omega-3 rich low saturated fat fiber antioxidant",
}

# Diet type exclusions
DIET_RESTRICTIONS = {
    "vegan": {"meat", "poultry", "fish", "shellfish", "dairy", "egg"},
    "vegetarian": {"meat", "poultry", "fish", "shellfish"},
    "pescatarian": {"meat", "poultry"},
    "dairy-free": {"dairy"},
    "gluten-free": {"wheat"},
}

ALLERGEN_SYNONYMS = {
    "peanut": ["peanut", "peanuts", "groundnut", "peanut butter"],
    "peanuts": ["peanut", "peanuts", "groundnut", "peanut butter"],
    "tree nut": ["almond", "walnut", "cashew", "pecan", "pistachio", "hazelnut", "macadamia", "pine nut", "brazil nut"],
    "tree nuts": ["almond", "walnut", "cashew", "pecan", "pistachio", "hazelnut", "macadamia", "pine nut", "brazil nut"],
    "nuts": ["peanut", "peanuts", "almond", "walnut", "cashew", "pecan", "pistachio", "hazelnut", "macadamia", "pine nut", "brazil nut"],
    "nut": ["peanut", "peanuts", "almond", "walnut", "cashew", "pecan", "pistachio", "hazelnut", "macadamia", "pine nut", "brazil nut"],
    "dairy": ["milk", "cheese", "yogurt", "butter", "cream", "whey", "casein", "ricotta", "cheddar", "mozzarella", "parmesan"],
    "milk": ["milk", "cheese", "yogurt", "butter", "cream", "whey", "casein", "ricotta", "cheddar", "mozzarella", "parmesan"],
    "egg": ["egg", "eggs", "egg white", "egg yolk", "albumin", "mayonnaise"],
    "eggs": ["egg", "eggs", "egg white", "egg yolk", "albumin", "mayonnaise"],
    "fish": ["salmon", "tuna", "cod", "tilapia", "trout", "halibut", "mackerel", "sardine", "anchovy", "snapper", "bass", "fish"],
    "shellfish": ["shrimp", "prawn", "prawns", "crab", "lobster", "clam", "mussel", "oyster", "scallop", "squid", "calamari", "shellfish"],
    "wheat": ["wheat", "flour", "bread", "pasta", "gluten", "semolina", "spelt", "rye", "barley", "bulgur", "couscous"],
    "gluten": ["wheat", "flour", "bread", "pasta", "gluten", "semolina", "spelt", "rye", "barley", "bulgur", "couscous"],
    "soy": ["soy", "soya", "tofu", "tempeh", "edamame", "soybean", "miso", "tamari"],
    "sesame": ["sesame", "tahini"],
}


class NutritionRetriever:
    def __init__(self, vector_store: Optional[VectorStore] = None):
        if vector_store is None:
            self.vector_store = VectorStore()
        else:
            self.vector_store = vector_store

    def build_enriched_query(self, profile: UserProfile, query: str) -> str:
        """
        Enrich raw search query with contextual profile metadata (goals, preferences, diet type)
        to maximize vector semantic relevance.
        """
        query_parts = [query.strip()] if query else []

        # Add diet type
        if profile.diet_type and profile.diet_type.lower() not in query.lower():
            query_parts.append(profile.diet_type)

        # Add goal expansions
        for goal in profile.goals:
            goal_lower = goal.lower().strip()
            if goal_lower in GOAL_EXPANSIONS:
                query_parts.append(GOAL_EXPANSIONS[goal_lower])
            elif goal_lower not in query.lower():
                query_parts.append(goal_lower)

        # Add preferences
        for pref in profile.preferences:
            if pref.lower() not in query.lower():
                query_parts.append(pref)

        return " ".join(query_parts)

    def is_allergen_free(self, item: Dict[str, Any], allergies: List[str]) -> bool:
        """
        Check if food candidate is strictly free from user allergies.
        Applies both tag matching and name regex check.
        """
        if not allergies:
            return True

        item_allergens = set(item.get("allergens", []))
        item_name = item.get("name", "").lower()

        for user_allergy in allergies:
            allergy_clean = user_allergy.lower().strip()
            
            # 1. Direct tag match
            if allergy_clean in item_allergens:
                return False

            # 2. Synonym / expanded allergen check
            synonyms = ALLERGEN_SYNONYMS.get(allergy_clean, [allergy_clean])
            for syn in synonyms:
                if syn in item_allergens:
                    return False
                if re.search(rf"\b{re.escape(syn)}", item_name):
                    return False

        return True

    def matches_diet_type(self, item: Dict[str, Any], diet_type: Optional[str]) -> bool:
        """Verify food item satisfies dietary restrictions (e.g. vegan, vegetarian, gluten-free)."""
        if not diet_type:
            return True

        diet_lower = diet_type.lower().strip()
        item_flags = set(item.get("dietary_flags", []))
        item_allergens = set(item.get("allergens", []))
        item_name = item.get("name", "").lower()

        if diet_lower in ["vegan", "plant-based"]:
            return "vegan" in item_flags

        if diet_lower in ["vegetarian", "veg"]:
            return "vegetarian" in item_flags

        if diet_lower == "pescatarian":
            return "pescatarian" in item_flags or "vegetarian" in item_flags

        if diet_lower in ["dairy-free", "lactose-free"]:
            return "dairy-free" in item_flags or "dairy" not in item_allergens

        if diet_lower == "gluten-free":
            return "gluten-free" in item_flags or "wheat" not in item_allergens

        if diet_lower in ["keto", "ketogenic", "low-carb"]:
            return "keto-friendly" in item_flags or "low-carb" in item_flags

        return True

    def search_and_filter(
        self,
        profile: UserProfile,
        query: str,
        top_k: int = 10,
        n_candidates: int = 40
    ) -> List[FoodItem]:
        """
        Execute semantic vector search, followed by deterministic safety filtering.
        Returns a list of validated FoodItem objects.
        """
        # Step 1: Query enrichment
        enriched_query = self.build_enriched_query(profile, query)

        # Step 2: Vector search candidate retrieval
        candidates = self.vector_store.search(enriched_query, n_results=n_candidates)

        # Step 3: Hard constraint safety filtering
        valid_items: List[FoodItem] = []
        seen_names = set()

        for candidate in candidates:
            name = candidate.get("name", "")
            if not name or name in seen_names:
                continue

            # Check 1: Allergen safety filter (STRICT - NEVER BYPASS)
            if not self.is_allergen_free(candidate, profile.allergies):
                continue

            # Check 2: Dietary preference filter
            if not self.matches_diet_type(candidate, profile.diet_type):
                continue

            seen_names.add(name)
            valid_items.append(
                FoodItem(
                    name=name,
                    calories=float(candidate.get("calories", 0.0)),
                    protein_g=float(candidate.get("protein_g", 0.0)),
                    carbs_g=float(candidate.get("carbs_g", 0.0)),
                    fat_g=float(candidate.get("fat_g", 0.0)),
                    source=candidate.get("source", "usda_fooddata_central")
                )
            )

            if len(valid_items) >= top_k:
                break

        return valid_items
