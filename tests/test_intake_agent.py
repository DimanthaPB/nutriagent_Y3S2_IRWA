import tempfile
import unittest
from pathlib import Path

from intake_agent.main import ProfileStore, classify_intent, extract_profile, merge_profiles


class IntakeExtractionTests(unittest.TestCase):
    def test_extracts_multiple_profile_fields(self):
        profile = extract_profile(
            "u123", "I want to build muscle on a vegetarian high protein diet. I am allergic to peanuts and eggs, have high blood pressure, and need 2200 calories."
        )
        self.assertEqual(profile.goals, ["muscle_gain"])
        self.assertEqual(profile.allergies, ["peanut", "eggs"])
        self.assertEqual(profile.conditions, ["hypertension"])
        self.assertEqual(profile.diet_type, "vegetarian")
        self.assertEqual(profile.preferences, ["high_protein"])
        self.assertEqual(profile.calorie_target, 2200)

    def test_negated_allergy_is_not_added(self):
        self.assertEqual(extract_profile("u124", "I have no dairy allergy but I avoid gluten.").allergies, ["gluten"])

    def test_intent_and_persisted_updates(self):
        self.assertEqual(classify_intent("Please update my diet to vegan"), "profile_update")
        self.assertEqual(classify_intent("What meal should I eat tonight?"), "one_off_query")
        with tempfile.TemporaryDirectory() as directory:
            store = ProfileStore(str(Path(directory) / "profiles.sqlite3"))
            store.save(extract_profile("u125", "I am allergic to soy"))
            merged = merge_profiles(store.get("u125"), extract_profile("u125", "I want to lose weight"))
            store.save(merged)
            self.assertEqual(store.get("u125").allergies, ["soy"])
            self.assertEqual(store.get("u125").goals, ["weight_loss"])


if __name__ == "__main__":
    unittest.main()
