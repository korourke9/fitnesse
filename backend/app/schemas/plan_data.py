"""Canonical schemas for plan content (meal and workout).

Plans are stored as JSON in Plan.plan_data. These models define the single
shape we use per plan type so view and summary logic can read without fallbacks.

Legacy data (e.g. meal plans with only sample_meals, no weekly_schedule) is
normalized via from_stored() so existing DB rows keep working.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --- Meal plan ---


class MealEntry(BaseModel):
    """A single meal in a day (e.g. breakfast, lunch)."""
    meal_type: str  # breakfast, lunch, dinner, snacks
    name: str
    nutrition: Optional[Dict[str, Any]] = None


class DayMeals(BaseModel):
    """Meals for one day of the week (day 1 = Monday .. 7 = Sunday)."""
    day: int = Field(..., ge=1, le=7)
    meals: List[MealEntry] = Field(default_factory=list)


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
        """Build from DB plan_data. Normalizes legacy shape (sample_meals only) into weekly_schedule."""
        if not isinstance(data, dict):
            return cls(weekly_schedule=_empty_week_meals())

        weekly = data.get("weekly_schedule")
        if isinstance(weekly, list) and len(weekly) == 7:
            # Already canonical (or at least 7 entries)
            day_meals = []
            for entry in weekly:
                if isinstance(entry, dict) and "day" in entry:
                    meals_raw = entry.get("meals") or entry.get("meal_plan") or []
                    meals = [
                        MealEntry(
                            meal_type=m.get("meal_type") or m.get("type") or "meal",
                            name=m.get("name") or m.get("description") or "—",
                            nutrition=m.get("nutrition") if isinstance(m, dict) else None,
                        )
                        if isinstance(m, dict)
                        else MealEntry(meal_type="meal", name=str(m))
                        for m in meals_raw
                        if m is not None
                    ]
                    day_meals.append(DayMeals(day=entry["day"], meals=meals))
                elif isinstance(entry, dict):
                    day = entry.get("day", 1)
                    day_meals.append(DayMeals(day=day, meals=[]))
            if len(day_meals) == 7:
                return cls(
                    daily_calories=data.get("daily_calories"),
                    macros=data.get("macros"),
                    meals_per_day=data.get("meals_per_day"),
                    guidelines=data.get("guidelines") or [],
                    notes=data.get("notes"),
                    weekly_schedule=sorted(day_meals, key=lambda d: d.day),
                )

        # Legacy: build weekly_schedule from sample_meals (same meals every day)
        sample = data.get("sample_meals")
        if isinstance(sample, dict):
            meals_list: List[MealEntry] = []
            for meal_type, options in [
                ("breakfast", sample.get("breakfast")),
                ("lunch", sample.get("lunch")),
                ("dinner", sample.get("dinner")),
                ("snacks", sample.get("snacks")),
            ]:
                if isinstance(options, list) and options and isinstance(options[0], str):
                    meals_list.append(MealEntry(meal_type=meal_type, name=options[0]))
            week = [DayMeals(day=d, meals=meals_list) for d in range(1, 8)]
        else:
            week = _empty_week_meals()

        return cls(
            daily_calories=data.get("daily_calories"),
            macros=data.get("macros"),
            meals_per_day=data.get("meals_per_day"),
            guidelines=data.get("guidelines") or [],
            notes=data.get("notes"),
            weekly_schedule=week,
        )


def _empty_week_meals() -> List[DayMeals]:
    return [DayMeals(day=d, meals=[]) for d in range(1, 8)]


# --- Workout plan ---


class DayWorkout(BaseModel):
    """One day in the weekly workout schedule (day 1 = Monday .. 7 = Sunday)."""
    day: int = Field(..., ge=1, le=7)
    type: str = "Rest"
    description: str = ""
    exercises: List[str] = Field(default_factory=list)


class WorkoutPlanData(BaseModel):
    """Canonical workout plan content. Always has weekly_schedule (7 days)."""
    workouts_per_week: Optional[int] = None
    workout_duration_minutes: Optional[int] = None
    focus_areas: List[str] = Field(default_factory=list)
    guidelines: List[str] = Field(default_factory=list)
    sample_exercises: Dict[str, List[str]] = Field(default_factory=dict)
    notes: Optional[str] = None
    weekly_schedule: List[DayWorkout] = Field(default_factory=list)

    @classmethod
    def from_stored(cls, data: Any) -> "WorkoutPlanData":
        """Build from DB plan_data. Normalizes legacy/missing schedule into 7 days."""
        if not isinstance(data, dict):
            return cls(weekly_schedule=_empty_week_workouts())

        weekly = data.get("weekly_schedule")
        if isinstance(weekly, list):
            day_entries = []
            for entry in weekly:
                if isinstance(entry, dict):
                    day = entry.get("day", 1)
                    ex = entry.get("exercises") or entry.get("exercise_list") or []
                    exercises = [e if isinstance(e, str) else str(e) for e in ex]
                    day_entries.append(
                        DayWorkout(
                            day=day,
                            type=entry.get("type") or "Rest",
                            description=entry.get("description") or "",
                            exercises=exercises,
                        )
                    )
            # Fill missing days with rest
            by_day = {e.day: e for e in day_entries}
            schedule = [
                by_day.get(d, DayWorkout(day=d, type="Rest", description=""))
                for d in range(1, 8)
            ]
        else:
            schedule = _empty_week_workouts()

        return cls(
            workouts_per_week=data.get("workouts_per_week"),
            workout_duration_minutes=data.get("workout_duration_minutes"),
            focus_areas=data.get("focus_areas") or [],
            guidelines=data.get("guidelines") or [],
            sample_exercises=data.get("sample_exercises") or {},
            notes=data.get("notes"),
            weekly_schedule=schedule,
        )


def _empty_week_workouts() -> List[DayWorkout]:
    return [DayWorkout(day=d, type="Rest", description="") for d in range(1, 8)]
