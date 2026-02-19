import { useQuery } from '@tanstack/react-query';
import { apiClient } from './api';

export interface PlanSummary {
  start_date?: string;
  end_date?: string;
  duration_days?: number;
  daily_calories?: number;
  macros?: Record<string, unknown>;
  workouts_per_week?: number;
  notes?: string;
}

/** Response from GET /api/plans/:id/view?date= */
export interface PlanViewMeal {
  meal_type: string;
  name: string;
  nutrition?: Record<string, unknown> | null;
  ingredients?: string[] | null;
  instructions?: string | null;
}

export interface PlanViewStrengthExercise {
  exercise_type: 'strength';
  name: string;
  sets: number;
  reps: string;
  weight: string;
  notes?: string | null;
}

export interface PlanViewCardioExercise {
  exercise_type: 'cardio';
  name: string;
  duration: string;
  distance?: string | null;
  intensity: string;
  notes?: string | null;
}

export interface PlanViewFlexibilityExercise {
  exercise_type: 'flexibility';
  name: string;
  duration: string;
  notes?: string | null;
}

export type PlanViewExerciseDetail = PlanViewStrengthExercise | PlanViewCardioExercise | PlanViewFlexibilityExercise;

export interface PlanViewWorkout {
  type: string;
  description: string;
}

export interface PlanViewResponse {
  date: string;
  plan_type: string;
  targets?: { daily_calories?: number; macros?: Record<string, unknown> } | null;
  meals?: PlanViewMeal[];
  workout?: PlanViewWorkout | null;
  exercises?: string[];
  exercise_details?: PlanViewExerciseDetail[] | null;
}

export interface SectionState {
  has_plan: boolean;
  plan_id?: string | null;
  summary?: PlanSummary | null;
}

export interface AppStateResponse {
  user_id: string;
  onboarding_complete: boolean;
  nutrition: SectionState;
  training: SectionState;
}

export function useAppState() {
  return useQuery({
    queryKey: ['appState'],
    queryFn: async () => {
      const res = await apiClient.get<AppStateResponse>('/api/state');
      return res.data;
    },
    staleTime: 10_000,
    retry: 1,
  });
}


