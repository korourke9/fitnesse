"""Pydantic schema for meal parsing outputs.

Uses MealEntry from the meal plan schema (core meal info only).
MealRecipe (with ingredients/instructions) is used for planning,
but logging only needs MealEntry (name, nutrition, meal_type, portion).
"""
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from app.services.nutritionist.planning.meal_plan_schema import (
    MealEntry,
    MacroEstimate,
)


class MealParseResult(BaseModel):
    """Structured result of parsing a meal description."""
    normalized_text: str = Field(..., description="Normalized/cleaned meal description")
    estimate: MacroEstimate = Field(default_factory=MacroEstimate, description="Overall macro estimate for the meal")
    items: List[MealEntry] = Field(default_factory=list, description="Individual meal entries (core info only - no ingredients/instructions)")
    confidence: float = Field(..., ge=0, le=1)
    questions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Re-export for consumers that need the shared types
__all__ = [
    "MealParseResult",
    "MealEntry",
    "MacroEstimate",
]
