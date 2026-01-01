"""Pydantic schema for meal parsing outputs."""
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class MealItem(BaseModel):
    name: str = Field(..., description="Item name, e.g. chicken burrito bowl")
    portion: Optional[str] = Field(None, description="Optional portion, e.g. '1 bowl', '2 slices'")


class MacroEstimate(BaseModel):
    calories: Optional[float] = Field(None, ge=0)
    protein_g: Optional[float] = Field(None, ge=0)
    carbs_g: Optional[float] = Field(None, ge=0)
    fat_g: Optional[float] = Field(None, ge=0)


class MealParseResult(BaseModel):
    normalized_text: str = Field(..., description="Normalized/cleaned meal description")
    estimate: MacroEstimate = Field(default_factory=MacroEstimate)
    items: List[MealItem] = Field(default_factory=list)
    confidence: float = Field(..., ge=0, le=1)
    questions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


