"""
Data Processor for Nutrition IR Agent
--------------------------------------
Cleans and standardizes food data from USDA Foundation Foods CSV,
extracts macronutrients (energy, protein, carbs, fat), identifies
common allergens and dietary classifications, and formats text for dense embedding.
"""

import re
import pathlib
from typing import List, Dict, Any, Optional
import pandas as pd

# Allergen keyword mappings for automated tagging
ALLERGEN_MAP = {
    "peanut": ["peanut", "groundnut", "peanut butter"],
    "tree_nut": ["almond", "walnut", "cashew", "pecan", "pistachio", "hazelnut", "macadamia", "brazil nut", "chestnut", "pine nut"],
    "dairy": ["milk", "cheese", "yogurt", "butter", "cream", "whey", "casein", "ricotta", "cheddar", "mozzarella", "parmesan"],
    "egg": ["egg", "egg white", "egg yolk", "albumin", "mayonnaise"],
    "fish": ["salmon", "tuna", "cod", "tilapia", "trout", "halibut", "mackerel", "sardine", "anchovy", "snapper", "bass"],
    "shellfish": ["shrimp", "prawn", "crab", "lobster", "clam", "mussel", "oyster", "scallop", "squid", "calamari"],
    "wheat": ["wheat", "flour", "bread", "pasta", "gluten", "semolina", "spelt", "rye", "barley", "bulgur", "couscous"],
    "soy": ["soy", "soya", "tofu", "tempeh", "edamame", "soybean", "miso", "tamari"],
    "sesame": ["sesame", "tahini"],
}

# Non-vegetarian / non-vegan keyword indicators
MEAT_KEYWORDS = ["beef", "pork", "chicken", "turkey", "lamb", "bacon", "sausage", "ham", "steak", "frankfurter", "duck", "veal", "mutton"]
POULTRY_KEYWORDS = ["chicken", "turkey", "duck", "poultry", "quail"]
FISH_KEYWORDS = ["salmon", "tuna", "cod", "tilapia", "trout", "halibut", "mackerel", "sardine", "anchovy", "snapper", "bass", "shrimp", "prawn", "crab", "lobster", "clam", "mussel", "oyster", "scallop", "fish", "shellfish"]

CURATED_PREPARED_MEALS: List[Dict[str, Any]] = [
    {
        "name": "Grilled Lemon Herb Chicken Breast with Quinoa and Steamed Broccoli",
        "category": "Prepared Meals / Entrees",
        "calories": 420.0,
        "protein_g": 42.0,
        "carbs_g": 35.0,
        "fat_g": 10.0,
        "allergens": [],
        "dietary_flags": ["high-protein", "dairy-free", "gluten-free", "clean-eating"]
    },
    {
        "name": "Baked Atlantic Salmon Fillet with Roasted Asparagus and Sweet Potato",
        "category": "Prepared Meals / Entrees",
        "calories": 480.0,
        "protein_g": 38.0,
        "carbs_g": 32.0,
        "fat_g": 20.0,
        "allergens": ["fish"],
        "dietary_flags": ["pescatarian", "high-protein", "gluten-free", "dairy-free", "omega-3-rich"]
    },
    {
        "name": "Chickpea and Spinach Coconut Curry with Brown Basmati Rice",
        "category": "Prepared Meals / Entrees",
        "calories": 430.0,
        "protein_g": 16.0,
        "carbs_g": 62.0,
        "fat_g": 12.0,
        "allergens": [],
        "dietary_flags": ["vegan", "vegetarian", "plant-based", "dairy-free", "gluten-free", "high-fiber"]
    },
    {
        "name": "High Protein Tofu and Mixed Vegetable Stir Fry with Sesame Garlic Sauce",
        "category": "Prepared Meals / Entrees",
        "calories": 360.0,
        "protein_g": 24.0,
        "carbs_g": 28.0,
        "fat_g": 16.0,
        "allergens": ["soy", "sesame"],
        "dietary_flags": ["vegan", "vegetarian", "plant-based", "high-protein", "dairy-free"]
    },
    {
        "name": "Lentil and Vegetable Dhal with Turmeric and Steamed Jasmine Rice",
        "category": "Prepared Meals / Entrees",
        "calories": 390.0,
        "protein_g": 19.0,
        "carbs_g": 65.0,
        "fat_g": 6.0,
        "allergens": [],
        "dietary_flags": ["vegan", "vegetarian", "plant-based", "high-fiber", "dairy-free", "gluten-free"]
    },
    {
        "name": "Classic Greek Yogurt Parfait with Mixed Berries, Chia Seeds, and Honey",
        "category": "Breakfast / Snacks",
        "calories": 280.0,
        "protein_g": 22.0,
        "carbs_g": 34.0,
        "fat_g": 5.0,
        "allergens": ["dairy"],
        "dietary_flags": ["vegetarian", "high-protein", "gluten-free"]
    },
    {
        "name": "Rolled Oatmeal Bowl with Almond Butter, Sliced Banana, and Cinnamon",
        "category": "Breakfast / Snacks",
        "calories": 370.0,
        "protein_g": 13.0,
        "carbs_g": 52.0,
        "fat_g": 14.0,
        "allergens": ["tree_nut", "wheat"],
        "dietary_flags": ["vegan", "vegetarian", "plant-based", "dairy-free", "high-fiber"]
    },
    {
        "name": "Egg White and Spinach Scramble with Whole Wheat Toast and Avocado",
        "category": "Breakfast / Snacks",
        "calories": 320.0,
        "protein_g": 26.0,
        "carbs_g": 24.0,
        "fat_g": 12.0,
        "allergens": ["egg", "wheat"],
        "dietary_flags": ["vegetarian", "high-protein", "dairy-free"]
    },
    {
        "name": "Avocado and Roasted Chickpea Salad Bowl with Lemon Tahini Dressing",
        "category": "Salads / Light Meals",
        "calories": 380.0,
        "protein_g": 14.0,
        "carbs_g": 38.0,
        "fat_g": 20.0,
        "allergens": ["sesame"],
        "dietary_flags": ["vegan", "vegetarian", "plant-based", "gluten-free", "dairy-free", "high-fiber"]
    },
    {
        "name": "Lean Grass-Fed Beef Sirloin Steak with Roasted Brussels Sprouts and Mashed Sweet Potato",
        "category": "Prepared Meals / Entrees",
        "calories": 490.0,
        "protein_g": 46.0,
        "carbs_g": 28.0,
        "fat_g": 18.0,
        "allergens": [],
        "dietary_flags": ["high-protein", "dairy-free", "gluten-free", "iron-rich"]
    },
    {
        "name": "Mediterranean Tuna Salad with Olive Oil, Cucumber, Cherry Tomatoes, and Red Onion",
        "category": "Salads / Light Meals",
        "calories": 310.0,
        "protein_g": 34.0,
        "carbs_g": 8.0,
        "fat_g": 15.0,
        "allergens": ["fish"],
        "dietary_flags": ["pescatarian", "high-protein", "low-carb", "keto-friendly", "gluten-free", "dairy-free"]
    },
    {
        "name": "Peanut Butter and Banana Protein Smoothie with Soy Milk and Plant Protein",
        "category": "Beverages / Smoothies",
        "calories": 360.0,
        "protein_g": 28.0,
        "carbs_g": 38.0,
        "fat_g": 12.0,
        "allergens": ["peanut", "soy"],
        "dietary_flags": ["vegan", "vegetarian", "high-protein", "dairy-free"]
    },
    {
        "name": "Keto Avocado and Boiled Egg Salad with Extra Virgin Olive Oil and Walnuts",
        "category": "Salads / Light Meals",
        "calories": 410.0,
        "protein_g": 16.0,
        "carbs_g": 6.0,
        "fat_g": 36.0,
        "allergens": ["egg", "tree_nut"],
        "dietary_flags": ["vegetarian", "keto-friendly", "low-carb", "gluten-free", "dairy-free"]
    }
]


def detect_allergens(name: str, category: str = "") -> List[str]:
    """Detect potential allergens present in food name or category."""
    text = f"{name} {category}".lower()
    allergens = set()
    for allergen, keywords in ALLERGEN_MAP.items():
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}", text):
                allergens.add(allergen)
                break
    return sorted(list(allergens))


def determine_dietary_flags(name: str, category: str, protein: float, carbs: float, fat: float, allergens: List[str]) -> List[str]:
    """Classify dietary attributes based on food profile and ingredients."""
    text = f"{name} {category}".lower()
    flags = []

    has_meat = any(re.search(rf"\b{re.escape(kw)}", text) for kw in MEAT_KEYWORDS)
    has_poultry = any(re.search(rf"\b{re.escape(kw)}", text) for kw in POULTRY_KEYWORDS)
    has_fish = any(re.search(rf"\b{re.escape(kw)}", text) for kw in FISH_KEYWORDS)
    has_dairy = "dairy" in allergens
    has_egg = "egg" in allergens

    is_vegan = not (has_meat or has_poultry or has_fish or has_dairy or has_egg)
    is_vegetarian = not (has_meat or has_poultry or has_fish)
    is_pescatarian = not (has_meat or has_poultry)

    if is_vegan:
        flags.append("vegan")
    if is_vegetarian:
        flags.append("vegetarian")
    if is_pescatarian and not is_vegetarian:
        flags.append("pescatarian")

    if not has_dairy:
        flags.append("dairy-free")
    if "wheat" not in allergens:
        flags.append("gluten-free")

    # Macro-based classifications
    if protein >= 18.0:
        flags.append("high-protein")
    if carbs <= 10.0 and fat >= 8.0:
        flags.append("keto-friendly")
    if carbs <= 15.0:
        flags.append("low-carb")
    if fat <= 3.0 and protein >= 5.0:
        flags.append("low-fat")

    return flags


def clean_food_name(raw_name: str) -> str:
    """Format and clean raw USDA food description strings."""
    if not isinstance(raw_name, str):
        return ""
    name = raw_name.strip()
    # Normalize common USDA casing like 'HUMMUS, COMMERCIAL' -> 'Hummus, commercial'
    if name.isupper():
        name = name.capitalize()
    return name


def load_and_process_epicurious_recipes(csv_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Loads Epicurious 20k recipes dataset (epi_r.csv), filters outliers,
    derives macronutrients and dietary tags, and formats rich semantic text.
    """
    if csv_path is None:
        base_dir = pathlib.Path(__file__).resolve().parent
        csv_path = str(base_dir / "data" / "epi_r.csv")

    path = pathlib.Path(csv_path)
    if not path.exists():
        return []

    print(f"[DataProcessor] Loading Epicurious recipes from {csv_path}...")
    try:
        df = pd.read_csv(str(path), low_memory=False)
    except Exception as e:
        print(f"[Warning] Could not read Epicurious CSV from {csv_path}: {e}")
        return []

    # Drop rows without complete primary macros
    df_clean = df.dropna(subset=["calories", "protein", "fat"]).copy()

    # Filter out extreme outliers / whole batch roasts
    df_clean = df_clean[
        (df_clean["calories"] >= 20.0) & (df_clean["calories"] <= 2500.0) &
        (df_clean["protein"] >= 0.0) & (df_clean["protein"] <= 200.0) &
        (df_clean["fat"] >= 0.0) & (df_clean["fat"] <= 150.0)
    ]

    # Deduplicate by recipe title
    df_clean = df_clean.drop_duplicates(subset=["title"])

    tag_cols = [c for c in df_clean.columns if c not in ["title", "rating", "calories", "protein", "fat", "sodium"]]

    processed_recipes: List[Dict[str, Any]] = []

    for _, row in df_clean.iterrows():
        raw_title = str(row["title"]).strip()
        # Clean title encoding artifacts
        clean_title = re.sub(r"[^\x20-\x7E]+", " ", raw_title).strip()
        if not clean_title or len(clean_title) < 2:
            continue

        cal = round(float(row["calories"]), 1)
        prot = round(float(row["protein"]), 1)
        fat = round(float(row["fat"]), 1)
        # Carbohydrate energy balance estimation: (Calories - 4*P - 9*F) / 4
        carbs = round(max(0.0, (cal - (prot * 4.0) - (fat * 9.0)) / 4.0), 1)

        # Extract active boolean tags
        active_tags = [c for c in tag_cols if row.get(c, 0.0) == 1.0]

        # Categorize meal based on tags
        cat = "Prepared Meals / Entrees"
        if any(t in active_tags for t in ["breakfast", "brunch"]):
            cat = "Breakfast & Brunch"
        elif any(t in active_tags for t in ["soup/stew", "soup", "stew", "chowder"]):
            cat = "Soups & Stews"
        elif any(t in active_tags for t in ["salad"]):
            cat = "Salads & Bowls"
        elif any(t in active_tags for t in ["sandwich", "burger", "wrap"]):
            cat = "Sandwiches & Wraps"
        elif any(t in active_tags for t in ["pasta", "noodle", "pizza"]):
            cat = "Pasta & Grains"
        elif any(t in active_tags for t in ["dessert", "cookie", "cake", "snack", "appetizer"]):
            cat = "Healthy Snacks & Treats"

        # Allergens
        allergens = detect_allergens(clean_title, cat)
        if "peanut free" in active_tags and "peanut" in allergens:
            allergens.remove("peanut")
        if "dairy free" in active_tags and "dairy" in allergens:
            allergens.remove("dairy")
        if any(t in active_tags for t in ["wheat/gluten-free", "gluten-free"]) and "wheat" in allergens:
            allergens.remove("wheat")

        # Dietary classifications
        diet_flags = determine_dietary_flags(clean_title, cat, prot, carbs, fat, allergens)
        if "vegan" in active_tags and "vegan" not in diet_flags:
            diet_flags.append("vegan")
        if "vegetarian" in active_tags and "vegetarian" not in diet_flags:
            diet_flags.append("vegetarian")
        if "pescatarian" in active_tags and "pescatarian" not in diet_flags:
            diet_flags.append("pescatarian")
        if "dairy free" in active_tags and "dairy-free" not in diet_flags:
            diet_flags.append("dairy-free")
        if any(t in active_tags for t in ["wheat/gluten-free", "gluten-free"]) and "gluten-free" not in diet_flags:
            diet_flags.append("gluten-free")
        if "high fiber" in active_tags and "high-fiber" not in diet_flags:
            diet_flags.append("high-fiber")
        if "low cal" in active_tags and "low-calorie" not in diet_flags:
            diet_flags.append("low-calorie")

        # Format semantic embedding document
        doc_text = (
            f"{clean_title} | Category: {cat} | "
            f"Calories: {cal:.1f} kcal | Protein: {prot:.1f}g | "
            f"Carbohydrates: {carbs:.1f}g | Fat: {fat:.1f}g | "
            f"Dietary: {', '.join(diet_flags)} | "
            f"Allergens: {', '.join(allergens) if allergens else 'none'} | "
            f"Source: Epicurious Recipes"
        )

        processed_recipes.append({
            "name": clean_title,
            "category": cat,
            "calories": cal,
            "protein_g": prot,
            "carbs_g": carbs,
            "fat_g": fat,
            "allergens": allergens,
            "dietary_flags": sorted(list(set(diet_flags))),
            "document_text": doc_text,
            "source": "epicurious_recipes"
        })

    print(f"[DataProcessor] Successfully processed {len(processed_recipes)} recipes from Epicurious dataset.")
    return processed_recipes


def load_and_process_dataset(foods_csv_path: Optional[str] = None, recipes_csv_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Loads and merges:
    1. Curated benchmark meals (13 items)
    2. USDA Foundation & Whole Food ingredients (from foods.csv)
    3. Epicurious prepared recipes (from epi_r.csv)
    """
    base_dir = pathlib.Path(__file__).resolve().parent
    if foods_csv_path is None:
        foods_csv_path = str(base_dir / "data" / "foods.csv")
    if recipes_csv_path is None:
        recipes_csv_path = str(base_dir / "data" / "epi_r.csv")

    processed_foods: List[Dict[str, Any]] = []
    seen_names = set()

    # 1. Load curated meals first
    for meal in CURATED_PREPARED_MEALS:
        norm_name = meal["name"].lower()
        if norm_name not in seen_names:
            seen_names.add(norm_name)
            doc_text = (
                f"{meal['name']} | Category: {meal['category']} | "
                f"Calories: {meal['calories']} kcal | Protein: {meal['protein_g']}g | "
                f"Carbohydrates: {meal['carbs_g']}g | Fat: {meal['fat_g']}g | "
                f"Dietary: {', '.join(meal['dietary_flags'])} | "
                f"Allergens: {', '.join(meal['allergens']) if meal['allergens'] else 'none'}"
            )
            item = dict(meal)
            item["document_text"] = doc_text
            item["source"] = "usda_curated_nutrition_db"
            processed_foods.append(item)

    # 2. Parse Epicurious Recipes CSV (if present)
    epicurious_foods = load_and_process_epicurious_recipes(recipes_csv_path)
    for recipe in epicurious_foods:
        norm_key = recipe["name"].lower()
        if norm_key not in seen_names:
            seen_names.add(norm_key)
            processed_foods.append(recipe)

    # 3. Parse USDA CSV
    path = pathlib.Path(foods_csv_path)
    if path.exists():
        try:
            df = pd.read_csv(str(path), low_memory=False)

            # Fast pre-filtering: remove empty descriptions
            desc_col = "description" if "description" in df.columns else df.columns[0]
            cat_col = "food_category" if "food_category" in df.columns else None

            # Prioritize complete foundation foods and rows with non-empty nutrient data
            if "data_type" in df.columns:
                df = df[df["data_type"].isin(["foundation_food", "sample_food", "agricultural_acquisition"])]
            
            # Energy columns
            energy_col = None
            for col_candidate in ["Energy (KCAL)", "Energy (Atwater Specific Factors) (KCAL)", "Energy (Atwater General Factors) (KCAL)", "Energy (kJ)"]:
                if col_candidate in df.columns:
                    energy_col = col_candidate
                    break

            protein_col = "Protein (G)" if "Protein (G)" in df.columns else None
            fat_col = "Total lipid (fat) (G)" if "Total lipid (fat) (G)" in df.columns else None
            carb_col = "Carbohydrate, by difference (G)" if "Carbohydrate, by difference (G)" in df.columns else None

            # Use to_dict('records') to preserve original column names with spaces and symbols
            records = df.to_dict("records")
            for row_dict in records:
                raw_name = row_dict.get(desc_col, "")
                if pd.isna(raw_name) or not str(raw_name).strip():
                    continue

                clean_name = clean_food_name(str(raw_name))
                norm_key = clean_name.lower()
                if norm_key in seen_names:
                    continue

                category = str(row_dict.get(cat_col, "Whole Foods & Ingredients")) if cat_col and pd.notna(row_dict.get(cat_col)) else "Whole Foods"

                calories = 0.0
                if energy_col and pd.notna(row_dict.get(energy_col)):
                    try:
                        calories = float(row_dict.get(energy_col))
                    except (ValueError, TypeError):
                        calories = 0.0

                protein = 0.0
                if protein_col and pd.notna(row_dict.get(protein_col)):
                    try:
                        protein = float(row_dict.get(protein_col))
                    except (ValueError, TypeError):
                        protein = 0.0

                fat = 0.0
                if fat_col and pd.notna(row_dict.get(fat_col)):
                    try:
                        fat = float(row_dict.get(fat_col))
                    except (ValueError, TypeError):
                        fat = 0.0

                carbs = 0.0
                if carb_col and pd.notna(row_dict.get(carb_col)):
                    try:
                        carbs = float(row_dict.get(carb_col))
                    except (ValueError, TypeError):
                        carbs = 0.0

                if calories <= 0.0 and protein <= 0.0 and fat <= 0.0 and carbs <= 0.0:
                    continue

                if calories <= 0.0 and (protein > 0 or carbs > 0 or fat > 0):
                    calories = round((protein * 4.0) + (carbs * 4.0) + (fat * 9.0), 1)

                allergens = detect_allergens(clean_name, category)
                diet_flags = determine_dietary_flags(clean_name, category, protein, carbs, fat, allergens)

                doc_text = (
                    f"{clean_name} | Category: {category} | "
                    f"Calories: {calories:.1f} kcal | Protein: {protein:.1f}g | "
                    f"Carbohydrates: {carbs:.1f}g | Fat: {fat:.1f}g | "
                    f"Dietary: {', '.join(diet_flags)} | "
                    f"Allergens: {', '.join(allergens) if allergens else 'none'} | "
                    f"Source: USDA FoodData Central"
                )

                seen_names.add(norm_key)
                processed_foods.append({
                    "name": clean_name,
                    "category": category,
                    "calories": round(calories, 1),
                    "protein_g": round(protein, 1),
                    "carbs_g": round(carbs, 1),
                    "fat_g": round(fat, 1),
                    "allergens": allergens,
                    "dietary_flags": diet_flags,
                    "document_text": doc_text,
                    "source": "usda_fooddata_central"
                })

        except Exception as e:
            print(f"[Warning] Error loading CSV from {foods_csv_path}: {e}")

    print(f"[DataProcessor] Total consolidated food records ready for indexing: {len(processed_foods)}")
    return processed_foods


if __name__ == "__main__":
    foods = load_and_process_dataset()
    print(f"Total processed foods loaded: {len(foods)}")
    if foods:
        print("\nSample food record:")
        print(foods[0])
        print("\nLast processed item:")
        print(foods[-1])

