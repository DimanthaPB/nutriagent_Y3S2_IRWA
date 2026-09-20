"""
Shared data contracts between all NutriAgent agents.

Every agent imports these models instead of defining its own, so the JSON
each agent sends/receives is guaranteed to match across the team. If you
need to change a field, change it here and tell the team - don't fork it
inside your own agent folder.
"""

from typing import List, Optional
from pydantic import BaseModel


class UserProfile(BaseModel):
    user_id: str
    goals: List[str] = []
    allergies: List[str] = []
    conditions: List[str] = []
    diet_type: Optional[str] = None
    calorie_target: Optional[int] = None
    preferences: List[str] = []


class SecurityRequest(BaseModel):
    """What the client sends to the Security & Validation Agent."""
    user_id: str
    raw_text: str
    token: Optional[str] = None


class IntakeRequest(BaseModel):
    """What the Security Agent forwards to the Intake Agent."""
    user_id: str
    raw_text: str


class FoodItem(BaseModel):
    name: str
    calories: float
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    source: str = "mock_dataset"


class IRRequest(BaseModel):
    """What the Intake Agent sends to the IR Agent."""
    profile: UserProfile
    query: str


class IRResponse(BaseModel):
    items: List[FoodItem]


class PlanningRequest(BaseModel):
    """What the Intake Agent sends to the Planning Agent."""
    profile: UserProfile
    retrieved_items: List[FoodItem]


class MealRecommendation(BaseModel):
    name: str
    calories: float
    reason: str
    source: str
    protein_g: Optional[float] = None
    carbs_g: Optional[float] = None
    fat_g: Optional[float] = None
    ingredients: List[str] = []
    prep_tip: Optional[str] = None
    allergen_safety_note: Optional[str] = None


class MealPlan(BaseModel):
    """Final response returned all the way back up the chain to the client."""
    user_id: str
    meals: List[MealRecommendation]
    disclaimer: str = "This is AI-generated guidance, not medical advice."
    intro_message: Optional[str] = None
