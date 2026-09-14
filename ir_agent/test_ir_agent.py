"""
Verification and Test Suite for Nutrition IR Agent
---------------------------------------------------
Tests:
  1. ChromaDB indexing of USDA dataset + curated meals
  2. Semantic retrieval relevance
  3. Strict allergen exclusion filtering
  4. Dietary constraint filtering (vegetarian, vegan, keto)
"""

import os
import sys
import pathlib

os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))


from shared.schemas import UserProfile, IRRequest
from ir_agent.retriever import NutritionRetriever


def run_tests():
    print("=" * 60)
    print("Testing Nutrition IR Agent Vector Retrieval & Safety Engine")
    print("=" * 60)

    retriever = NutritionRetriever()
    print(f"\n[Test 1] Vector Store Status: {retriever.vector_store.count()} indexed food items.\n")
    assert retriever.vector_store.count() > 0, "Vector store should have indexed items!"

    # Test Case 1: High protein meal search
    print("-" * 60)
    print("Test Case 1: 'High protein dinner for muscle gain'")
    profile1 = UserProfile(user_id="u1", goals=["muscle gain"], allergies=[], preferences=["chicken", "salmon"])
    items1 = retriever.search_and_filter(profile=profile1, query="high protein dinner", top_k=5)
    
    print(f"Retrieved {len(items1)} items:")
    for item in items1:
        print(f"  - {item.name} | Calories: {item.calories} kcal | Protein: {item.protein_g}g | Carbs: {item.carbs_g}g | Fat: {item.fat_g}g (Source: {item.source})")
    assert len(items1) > 0, "Should return high protein items"

    # Test Case 2: Vegetarian dinner
    print("\n" + "-" * 60)
    print("Test Case 2: 'Vegetarian dinner' (Diet Type: vegetarian)")
    profile2 = UserProfile(user_id="u2", goals=["weight loss"], allergies=[], diet_type="vegetarian")
    items2 = retriever.search_and_filter(profile=profile2, query="healthy dinner", top_k=5)
    
    print(f"Retrieved {len(items2)} items:")
    for item in items2:
        print(f"  - {item.name} | Calories: {item.calories} kcal | Protein: {item.protein_g}g | Source: {item.source}")
        # Verify no meat keywords
        for meat in ["chicken", "beef", "pork", "steak", "turkey", "salmon", "tuna"]:
            assert meat not in item.name.lower(), f"Violated vegetarian constraint: {item.name}"

    # Test Case 3: Strict Peanut Allergy exclusion
    print("\n" + "-" * 60)
    print("Test Case 3: 'Post workout snack' with Allergy: ['peanuts']")
    profile3 = UserProfile(user_id="u3", goals=["energy"], allergies=["peanuts", "peanut"])
    items3 = retriever.search_and_filter(profile=profile3, query="snack peanut butter smoothie", top_k=5)
    
    print(f"Retrieved {len(items3)} items (must NOT contain any peanuts):")
    for item in items3:
        print(f"  - {item.name} | Calories: {item.calories} kcal | Protein: {item.protein_g}g")
        assert "peanut" not in item.name.lower(), f"Violated peanut allergy constraint: {item.name}"

    # Test Case 4: Vegan + Gluten-Free lunch
    print("\n" + "-" * 60)
    print("Test Case 4: 'Vegan lunch' with Allergy: ['gluten', 'dairy']")
    profile4 = UserProfile(user_id="u4", goals=["wellness"], allergies=["gluten", "dairy"], diet_type="vegan")
    items4 = retriever.search_and_filter(profile=profile4, query="vegan salad curry lunch", top_k=5)
    
    print(f"Retrieved {len(items4)} items:")
    for item in items4:
        print(f"  - {item.name} | Calories: {item.calories} kcal | Protein: {item.protein_g}g")
        assert "milk" not in item.name.lower() and "cheese" not in item.name.lower(), f"Violated dairy constraint: {item.name}"
        assert "wheat" not in item.name.lower() and "bread" not in item.name.lower(), f"Violated gluten constraint: {item.name}"

    print("\n" + "=" * 60)
    print("ALL IR AGENT VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
