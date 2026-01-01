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


