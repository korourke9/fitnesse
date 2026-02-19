import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import AppShell from '../components/Layout/AppShell';
import { useAppState, type PlanViewResponse } from '../lib/state';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../lib/api';
import ChatContainer from '../components/Chat/ChatContainer';

function todayISODate() {
  return new Date().toISOString().slice(0, 10);
}

export default function Training() {
  const { data, isLoading, isError } = useAppState();
  const hasWorkoutPlan = data?.training.has_plan ?? false;
  const planId = data?.training.plan_id ?? null;
  const onboardingComplete = data?.onboarding_complete ?? false;
  const summary = data?.training.summary ?? null;
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [isExpanded, setIsExpanded] = React.useState(false);

  // Always include details for day view - no extra API call needed
  const { data: todayView } = useQuery({
    queryKey: ['planView', planId, todayISODate()],
    queryFn: async (): Promise<PlanViewResponse> => {
      const res = await apiClient.get(`/api/plans/${planId}/view`, {
        params: { date: todayISODate(), include_detail: true },
      });
      return res.data as PlanViewResponse;
    },
    enabled: Boolean(planId),
    staleTime: 60_000,
  });

  const generateMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/api/plans/workout', { duration_days: 30 });
      return res.data as unknown;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['appState'] });
    },
  });

  return (
    <AppShell title="Training">
      {isError ? (
        <div className="mb-6 rounded-2xl border border-red-100 bg-red-50 p-4 text-sm text-red-800">
          Couldn't load your training state. Try refreshing the page.
        </div>
      ) : null}

      {!isLoading && !onboardingComplete ? (
        <div className="mb-6 rounded-2xl border border-amber-100 bg-amber-50 p-4 text-sm text-amber-900 flex items-center justify-between gap-4">
          <div>
            Complete onboarding to generate a plan and start logging workouts.
          </div>
          <button
            type="button"
            onClick={() => navigate('/onboarding')}
            className="px-4 py-2 rounded-xl bg-primary-600 text-white font-semibold shadow-soft"
          >
            Go to Onboarding
          </button>
        </div>
      ) : null}

      {/* Single chat at top – log workouts and ask questions in one place */}
      <section className="mb-6 bg-white rounded-2xl border border-gray-100 shadow-soft-lg overflow-hidden">
        <div className="h-[380px] min-h-[320px] flex flex-col">
          <ChatContainer
            showAgentSwitcher={false}
            initialAgent="trainer"
            lockAgent={true}
          />
        </div>
      </section>

      {/* Today view (or plan CTA) below */}
      <section className="bg-white rounded-2xl border border-gray-100 shadow-soft-lg overflow-hidden">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Today</h2>
              <p className="text-sm text-gray-500 mt-1">
                {isLoading ? 'Loading…' : hasWorkoutPlan ? (todayView ? new Date(todayView.date).toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' }) : 'Your workout plan') : 'No workout plan yet.'}
              </p>
            </div>
            <span
              className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                hasWorkoutPlan ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'
              }`}
            >
              {isLoading ? 'Loading…' : hasWorkoutPlan ? 'Plan ready' : 'Needs plan'}
            </span>
          </div>
        </div>

        <div className="p-6">
          {!hasWorkoutPlan ? (
            <div className="rounded-xl bg-gradient-to-br from-amber-50 to-white border border-amber-100 p-5">
              <p className="text-sm text-gray-700">
                Generate a workout plan to unlock workout logging and plan adjustments.
              </p>
              {generateMutation.isError ? (
                <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                  <p className="font-medium">Failed to generate workout plan</p>
                  <p className="mt-1 text-xs">
                    {generateMutation.error instanceof Error
                      ? generateMutation.error.message
                      : 'An error occurred while generating your plan. Please try again.'}
                  </p>
                </div>
              ) : null}
              <button
                type="button"
                className="mt-4 inline-flex items-center justify-center px-4 py-2 rounded-xl bg-gradient-to-r from-orange-500 to-orange-600 text-white font-semibold shadow-soft hover:shadow-soft-lg transition-all"
                disabled={!onboardingComplete || generateMutation.isPending}
                onClick={() => generateMutation.mutate()}
                title={!onboardingComplete ? 'Complete onboarding first' : undefined}
              >
                {generateMutation.isPending ? 'Generating…' : 'Generate workout plan'}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Today's workout */}
              {todayView?.workout ? (
                <div className="rounded-xl border border-gray-100 bg-gray-50 overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="w-full p-4 text-left hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1">
                        <div className="text-xs text-gray-500 mb-1">Today&apos;s workout</div>
                        <div className="text-lg font-semibold text-gray-900">{todayView.workout.type}</div>
                        {todayView.workout.description ? (
                          <p className="mt-1 text-sm text-gray-700">{todayView.workout.description}</p>
                        ) : null}
                        {!isExpanded && todayView.exercises && todayView.exercises.length > 0 ? (
                          <ul className="mt-3 list-disc list-inside text-sm text-gray-600 space-y-0.5">
                            {todayView.exercises.map((ex, i) => (
                              <li key={i}>{ex}</li>
                            ))}
                          </ul>
                        ) : null}
                      </div>
                      <svg
                        className={`w-5 h-5 text-gray-400 transition-transform flex-shrink-0 ${isExpanded ? 'rotate-180' : ''}`}
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </div>
                  </button>
                  {isExpanded && todayView.exercise_details && todayView.exercise_details.length > 0 && (
                    <div className="px-4 pb-4 pt-2 border-t border-gray-200 space-y-3">
                      <div className="text-xs font-medium text-gray-500 mb-2">Exercise Details</div>
                      <ul className="space-y-3">
                        {todayView.exercise_details.map((ex, i) => (
                          <li key={i} className="text-sm">
                            <div className="font-medium text-gray-900">{ex.name}</div>
                            <div className="mt-1 text-gray-600 space-y-0.5">
                              {ex.exercise_type === 'strength' && (
                                <>
                                  <div>Sets: {ex.sets}</div>
                                  <div>Reps: {ex.reps}</div>
                                  <div>Weight: {ex.weight}</div>
                                </>
                              )}
                              {ex.exercise_type === 'cardio' && (
                                <>
                                  <div>Duration: {ex.duration}</div>
                                  {ex.distance && <div>Distance: {ex.distance}</div>}
                                  <div>Intensity: {ex.intensity}</div>
                                </>
                              )}
                              {ex.exercise_type === 'flexibility' && (
                                <div>Duration: {ex.duration}</div>
                              )}
                              {ex.notes && <div className="text-xs italic mt-1">{ex.notes}</div>}
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {isExpanded && (!todayView.exercise_details || todayView.exercise_details.length === 0) && todayView.exercises && todayView.exercises.length > 0 && (
                    <div className="px-4 pb-4 pt-2 border-t border-gray-200">
                      <ul className="list-disc list-inside text-sm text-gray-600 space-y-0.5">
                        {todayView.exercises.map((ex, i) => (
                          <li key={i}>{ex}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
                  <div className="text-sm text-gray-600">No specific workout for today. Rest or light activity.</div>
                </div>
              )}

              {summary?.notes ? (
                <div className="rounded-xl border border-gray-100 bg-white p-4">
                  <div className="text-xs text-gray-500">Notes</div>
                  <div className="mt-1 text-sm text-gray-700 whitespace-pre-wrap">{summary.notes}</div>
                </div>
              ) : null}

              <p className="text-xs text-gray-500">
                Log workouts in the chat above — describe what you did and confirm to save.
              </p>
            </div>
          )}
        </div>
      </section>

      <div className="mt-6 text-sm text-gray-500">
        <Link to="/dashboard" className="text-primary-700 hover:text-primary-800 font-medium">
          ← Back to dashboard
        </Link>
      </div>
    </AppShell>
  );
}
