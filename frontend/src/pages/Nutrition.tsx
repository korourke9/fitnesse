import { Link, useNavigate } from 'react-router-dom';
import AppShell from '../components/Layout/AppShell';
import { useAppState } from '../lib/state';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../lib/api';
import ChatContainer from '../components/Chat/ChatContainer';

export default function Nutrition() {
  const { data, isLoading, isError } = useAppState();
  const hasMealPlan = data?.nutrition.has_plan ?? false;
  const onboardingComplete = data?.onboarding_complete ?? false;
  const summary = data?.nutrition.summary ?? null;
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const generateMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/api/plans/meal', { duration_days: 30 });
      return res.data as unknown;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['appState'] });
    },
  });

  return (
    <AppShell title="Nutrition">
      {isError ? (
        <div className="mb-6 rounded-2xl border border-red-100 bg-red-50 p-4 text-sm text-red-800">
          Couldn't load your nutrition state. Try refreshing the page.
        </div>
      ) : null}

      {!isLoading && !onboardingComplete ? (
        <div className="mb-6 rounded-2xl border border-amber-100 bg-amber-50 p-4 text-sm text-amber-900 flex items-center justify-between gap-4">
          <div>
            Complete onboarding to generate a plan and start logging meals.
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

      {/* Single chat at top – log meals and ask questions in one place */}
      <section className="mb-6 bg-white rounded-2xl border border-gray-100 shadow-soft-lg overflow-hidden">
        <div className="h-[380px] min-h-[320px] flex flex-col">
          <ChatContainer
            showAgentSwitcher={false}
            initialAgent="nutritionist"
            lockAgent={true}
          />
        </div>
      </section>

      {/* Plan summary below */}
      <section className="bg-white rounded-2xl border border-gray-100 shadow-soft-lg overflow-hidden">
        <div className="p-6 border-b border-gray-100">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Meal Plan</h2>
              <p className="text-sm text-gray-500 mt-1">
                {isLoading ? 'Loading…' : hasMealPlan ? 'Your meal plan is ready.' : 'No meal plan yet.'}
              </p>
            </div>
            <span
              className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                hasMealPlan ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'
              }`}
            >
              {isLoading ? 'Loading…' : hasMealPlan ? 'Plan ready' : 'Needs plan'}
            </span>
          </div>
        </div>

        <div className="p-6">
          {!hasMealPlan ? (
            <div className="rounded-xl bg-gradient-to-br from-amber-50 to-white border border-amber-100 p-5">
              <p className="text-sm text-gray-700">
                Generate a meal plan to unlock meal logging and plan adjustments.
              </p>
              <button
                type="button"
                className="mt-4 inline-flex items-center justify-center px-4 py-2 rounded-xl bg-gradient-to-r from-green-500 to-green-600 text-white font-semibold shadow-soft hover:shadow-soft-lg transition-all"
                disabled={!onboardingComplete || generateMutation.isPending}
                onClick={() => generateMutation.mutate()}
                title={!onboardingComplete ? 'Complete onboarding first' : undefined}
              >
                {generateMutation.isPending ? 'Generating…' : 'Generate meal plan'}
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
                  <div className="text-xs text-gray-500">Daily calories</div>
                  <div className="mt-1 text-lg font-semibold text-gray-900">
                    {summary?.daily_calories ? Math.round(summary.daily_calories) : '—'}
                  </div>
                </div>
                <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
                  <div className="text-xs text-gray-500">Protein / Carbs / Fat</div>
                  <div className="mt-1 text-sm font-semibold text-gray-900">
                    {summary?.macros && typeof summary.macros === 'object'
                      ? `${String((summary.macros as Record<string, unknown>).protein ?? '—')} / ${String((summary.macros as Record<string, unknown>).carbs ?? '—')} / ${String((summary.macros as Record<string, unknown>).fat ?? '—')}`
                      : '—'}
                    <span className="text-gray-500 font-normal"> g</span>
                  </div>
                </div>
                <div className="rounded-xl border border-gray-100 bg-gray-50 p-4">
                  <div className="text-xs text-gray-500">Plan length</div>
                  <div className="mt-1 text-lg font-semibold text-gray-900">
                    {summary?.duration_days ?? '—'}<span className="text-gray-500 font-normal text-sm"> days</span>
                  </div>
                </div>
              </div>

              {summary?.notes ? (
                <div className="rounded-xl border border-gray-100 bg-white p-4">
                  <div className="text-xs text-gray-500">Notes</div>
                  <div className="mt-1 text-sm text-gray-700 whitespace-pre-wrap">{summary.notes}</div>
                </div>
              ) : null}

              <p className="text-xs text-gray-500">
                Log meals in the chat above — describe what you ate and confirm to save.
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
