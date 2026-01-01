import { Link, useNavigate } from 'react-router-dom';
import AppShell from '../components/Layout/AppShell';
import { useAppState } from '../lib/state';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../lib/api';
import { useMemo, useState } from 'react';

type MealParseResult = {
  normalized_text?: string;
  estimate?: {
    calories?: number | null;
    protein_g?: number | null;
    carbs_g?: number | null;
    fat_g?: number | null;
  };
  confidence?: number;
  questions?: string[];
};

export default function Nutrition() {
  const { data, isLoading, isError } = useAppState();
  const hasMealPlan = data?.nutrition.has_plan ?? false;
  const onboardingComplete = data?.onboarding_complete ?? false;
  const summary = data?.nutrition.summary ?? null;
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [mealText, setMealText] = useState('');
  const [parsed, setParsed] = useState<MealParseResult | null>(null);
  const [confirmed, setConfirmed] = useState<{ calories?: number; protein_g?: number; carbs_g?: number; fat_g?: number }>({});
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  const canLogMeal = useMemo(() => hasMealPlan && !isLoading, [hasMealPlan, isLoading]);

  const generateMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/api/plans/meal', { duration_days: 30 });
      return res.data as unknown;
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['appState'] });
    },
  });

  const parseMealMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/api/logs/meals/parse', {
        text: mealText,
        logged_at: new Date().toISOString(),
      });
      return res.data as { parsed: MealParseResult };
    },
    onSuccess: (data) => {
      setSavedMessage(null);
      setParsed(data.parsed);
      const est = data.parsed?.estimate ?? {};
      setConfirmed({
        calories: est.calories ?? undefined,
        protein_g: est.protein_g ?? undefined,
        carbs_g: est.carbs_g ?? undefined,
        fat_g: est.fat_g ?? undefined,
      });
    },
  });

  const saveMealMutation = useMutation({
    mutationFn: async () => {
      const confirmed_data = {
        normalized_text: parsed?.normalized_text ?? mealText.trim(),
        ...confirmed,
      };
      const res = await apiClient.post('/api/logs/meals', {
        raw_text: mealText,
        parsed_data: parsed,
        confirmed_data,
        logged_at: new Date().toISOString(),
      });
      return res.data as { id: string };
    },
    onSuccess: async () => {
      setSavedMessage('Saved meal log.');
      setMealText('');
      setParsed(null);
      setConfirmed({});
      await queryClient.invalidateQueries({ queryKey: ['appState'] });
    },
  });

  return (
    <AppShell title="Nutrition">
      {isError ? (
        <div className="mb-6 rounded-2xl border border-red-100 bg-red-50 p-4 text-sm text-red-800">
          Couldn’t load your nutrition state. Try refreshing the page.
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <section className="lg:col-span-2 bg-white rounded-2xl border border-gray-100 shadow-soft-lg overflow-hidden">
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
                        ? `${String((summary.macros as any).protein ?? '—')} / ${String((summary.macros as any).carbs ?? '—')} / ${String((summary.macros as any).fat ?? '—')}`
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

                <div className="text-xs text-gray-500">
                  Full plan viewer coming next. For now, you can start logging meals.
                </div>
              </div>
            )}
          </div>
        </section>

        <aside className="space-y-6">
          <div className="bg-white rounded-2xl border border-gray-100 shadow-soft-lg p-6">
            <h3 className="font-semibold text-gray-900">Log a meal</h3>
            <p className="text-sm text-gray-500 mt-1">
              {hasMealPlan ? 'Describe what you ate.' : 'Generate a plan first.'}
            </p>
            {savedMessage ? (
              <div className="mt-3 rounded-xl border border-green-100 bg-green-50 px-4 py-3 text-sm text-green-800">
                {savedMessage}
              </div>
            ) : null}
            <textarea
              className="mt-4 w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-green-500/30 focus:border-green-400 disabled:opacity-60"
              placeholder="e.g., Chipotle bowl with chicken, rice, beans, guac"
              rows={4}
              disabled={!canLogMeal || parseMealMutation.isPending || saveMealMutation.isPending}
              value={mealText}
              onChange={(e) => setMealText(e.target.value)}
            />
            <button
              type="button"
              className="mt-3 w-full inline-flex items-center justify-center px-4 py-2 rounded-xl bg-gray-900 text-white font-semibold shadow-soft disabled:opacity-60"
              disabled={!canLogMeal || mealText.trim().length === 0 || parseMealMutation.isPending || saveMealMutation.isPending}
              title={!hasMealPlan ? 'Generate a meal plan first' : undefined}
              onClick={() => parseMealMutation.mutate()}
            >
              {parseMealMutation.isPending ? 'Parsing…' : 'Log meal'}
            </button>

            {parsed ? (
              <div className="mt-4 rounded-2xl border border-gray-100 bg-white p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="text-xs text-gray-500">Parsed</div>
                    <div className="mt-1 text-sm text-gray-900 whitespace-pre-wrap">
                      {parsed.normalized_text ?? '—'}
                    </div>
                  </div>
                  <div className="text-xs text-gray-500">
                    Confidence: {typeof parsed.confidence === 'number' ? Math.round(parsed.confidence * 100) : '—'}%
                  </div>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3">
                  {[
                    { key: 'calories', label: 'Calories' },
                    { key: 'protein_g', label: 'Protein (g)' },
                    { key: 'carbs_g', label: 'Carbs (g)' },
                    { key: 'fat_g', label: 'Fat (g)' },
                  ].map((f) => (
                    <label key={f.key} className="block">
                      <div className="text-xs text-gray-500">{f.label}</div>
                      <input
                        type="number"
                        inputMode="decimal"
                        className="mt-1 w-full rounded-xl border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-green-500/30 focus:border-green-400"
                        value={(confirmed as any)[f.key] ?? ''}
                        onChange={(e) =>
                          setConfirmed((prev) => ({
                            ...prev,
                            [f.key]: e.target.value === '' ? undefined : Number(e.target.value),
                          }))
                        }
                      />
                    </label>
                  ))}
                </div>

                {parsed.questions?.length ? (
                  <div className="mt-4">
                    <div className="text-xs text-gray-500">Questions</div>
                    <ul className="mt-1 list-disc pl-5 text-sm text-gray-700">
                      {parsed.questions.map((q, i) => (
                        <li key={i}>{q}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                <div className="mt-4 flex items-center gap-2">
                  <button
                    type="button"
                    className="flex-1 inline-flex items-center justify-center px-4 py-2 rounded-xl bg-green-600 text-white font-semibold shadow-soft disabled:opacity-60"
                    disabled={saveMealMutation.isPending}
                    onClick={() => saveMealMutation.mutate()}
                  >
                    {saveMealMutation.isPending ? 'Saving…' : 'Confirm & Save'}
                  </button>
                  <button
                    type="button"
                    className="px-4 py-2 rounded-xl border border-gray-200 text-gray-700 font-semibold bg-white hover:bg-gray-50"
                    onClick={() => setParsed(null)}
                    disabled={saveMealMutation.isPending}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : null}
          </div>

          <div className="bg-white rounded-2xl border border-gray-100 shadow-soft-lg p-6">
            <h3 className="font-semibold text-gray-900">Change my plan</h3>
            <p className="text-sm text-gray-500 mt-1">
              {hasMealPlan ? 'Tell us what to adjust.' : 'Generate a plan first.'}
            </p>
            <textarea
              className="mt-4 w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400 disabled:opacity-60"
              placeholder="e.g., I don’t like breakfast—shift calories to lunch/dinner"
              rows={4}
              disabled={!hasMealPlan || isLoading}
            />
            <button
              type="button"
              className="mt-3 w-full inline-flex items-center justify-center px-4 py-2 rounded-xl bg-primary-600 text-white font-semibold shadow-soft disabled:opacity-60"
              disabled={!hasMealPlan || isLoading}
              title={!hasMealPlan ? 'Generate a meal plan first' : undefined}
            >
              Send feedback
            </button>
          </div>

          <div className="text-sm text-gray-500">
            <Link to="/dashboard" className="text-primary-700 hover:text-primary-800 font-medium">
              ← Back to dashboard
            </Link>
          </div>
        </aside>
      </div>
    </AppShell>
  );
}


