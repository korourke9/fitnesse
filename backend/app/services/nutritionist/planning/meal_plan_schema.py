"""Meal plan schema - canonical structure for meal plan content.

Plans are stored as JSON in Plan.plan_data. This model defines the single
shape we use for meal plans.

- MealEntry: Core meal info (name, nutrition, meal_type, portion) - used in logging
- MealRecipe: Composes MealEntry with ingredients/instructions - used in planning
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MacroEstimate(BaseModel):
    """Structured nutrition information (shared between planning and logging)."""
    calories: Optional[float] = Field(None, ge=0)
    protein_g: Optional[float] = Field(None, ge=0)
    carbs_g: Optional[float] = Field(None, ge=0)
    fat_g: Optional[float] = Field(None, ge=0)


class MealEntry(BaseModel):
    """Core meal entry (used in both planning and logging).
    
    Contains only the essential meal information. For planning, use MealRecipe
    which extends this with recipe details (ingredients, instructions).
    """
    name: str
    nutrition: Optional[MacroEstimate] = None
    meal_type: Optional[str] = None  # breakfast, lunch, dinner, snacks (set for planning, optional for logging)
    portion: Optional[str] = None  # e.g. '1 bowl', '2 slices' (logging-specific)


class MealRecipe(BaseModel):
    """Meal recipe (contains MealEntry plus cooking details for planning).
    
    Used in meal plans. Composes MealEntry with ingredients and instructions.
    Access core meal info via .meal property.
    """
    meal: MealEntry  # Core meal information
    ingredients: Optional[List[str]] = None
    instructions: Optional[str] = None

    @property
    def name(self) -> str:
        """Convenience access to meal name."""
        return self.meal.name

    @property
    def nutrition(self) -> Optional[MacroEstimate]:
        """Convenience access to meal nutrition."""
        return self.meal.nutrition

    @property
    def meal_type(self) -> Optional[str]:
        """Convenience access to meal type."""
        return self.meal.meal_type

    @classmethod
    def from_meal_entry(cls, entry: MealEntry, ingredients: Optional[List[str]] = None, instructions: Optional[str] = None) -> "MealRecipe":
        """Create a MealRecipe from a MealEntry."""
        if entry.meal_type is None:
            raise ValueError("meal_type is required for MealRecipe")
        return cls(
            meal=entry,
            ingredients=ingredients,
            instructions=instructions,
        )


class DayMeals(BaseModel):
    """Meals for one day of the week (day 1 = Monday .. 7 = Sunday)."""
    day: int = Field(..., ge=1, le=7)
    meals: List[MealRecipe] = Field(default_factory=list)


class MealPlanData(BaseModel):
    """Canonical meal plan content. Always has weekly_schedule (7 days)."""
    daily_calories: Optional[float] = None
    macros: Optional[Dict[str, Any]] = None
    meals_per_day: Optional[int] = None
    guidelines: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    weekly_schedule: List[DayMeals] = Field(default_factory=list)

    @classmethod
    def from_stored(cls, data: Any) -> "MealPlanData":
        """Build from DB plan_data. Expects canonical JSON (raises ValidationError if invalid)."""
        return cls.model_validate(data)
