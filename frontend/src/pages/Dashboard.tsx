import { Link } from 'react-router-dom';
import AppShell from '../components/Layout/AppShell';
import { useAppState } from '../lib/state';

export default function Dashboard() {
  const { data, isLoading, isError } = useAppState();
  const nutrition = { hasPlan: data?.nutrition.has_plan ?? false };
  const training = { hasPlan: data?.training.has_plan ?? false };

  return (
    <AppShell title="Dashboard">
      {isError ? (
        <div className="mb-6 rounded-2xl border border-red-100 bg-red-50 p-4 text-sm text-red-800">
          Couldn’t load your state. Try refreshing the page.
        </div>
      ) : null}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Link
          to="/nutrition"
          className="group bg-white rounded-2xl border border-gray-100 shadow-soft-lg hover:shadow-soft-xl transition-shadow overflow-hidden"
        >
          <div className="p-6 border-b border-gray-100">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-green-500 to-green-600 text-white flex items-center justify-center text-xl shadow-soft">
                    🥗
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">Nutrition</h2>
                    <p className="text-sm text-gray-500 mt-0.5">
                      Meal plan, logging, and adjustments
                    </p>
                  </div>
                </div>
              </div>
              <span
                className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                  nutrition.hasPlan ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'
                }`}
              >
                {isLoading ? 'Loading…' : nutrition.hasPlan ? 'Plan ready' : 'Needs plan'}
              </span>
            </div>
          </div>
          <div className="p-6">
            <p className="text-sm text-gray-700">
              {isLoading
                ? 'Loading your nutrition state…'
                : nutrition.hasPlan
                ? 'View your meal plan and start logging meals.'
                : 'Generate a meal plan to unlock meal logging.'}
            </p>
            <div className="mt-4 inline-flex items-center gap-2 text-primary-700 font-semibold text-sm">
              Open Nutrition
              <span className="transition-transform group-hover:translate-x-0.5">→</span>
            </div>
          </div>
        </Link>

        <Link
          to="/training"
          className="group bg-white rounded-2xl border border-gray-100 shadow-soft-lg hover:shadow-soft-xl transition-shadow overflow-hidden"
        >
          <div className="p-6 border-b border-gray-100">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500 to-orange-600 text-white flex items-center justify-center text-xl shadow-soft">
                    💪
                  </div>
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">Training</h2>
                    <p className="text-sm text-gray-500 mt-0.5">
                      Workout plan, logging, and adjustments
                    </p>
                  </div>
                </div>
              </div>
              <span
                className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium ${
                  training.hasPlan ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'
                }`}
              >
                {isLoading ? 'Loading…' : training.hasPlan ? 'Plan ready' : 'Needs plan'}
              </span>
            </div>
          </div>
          <div className="p-6">
            <p className="text-sm text-gray-700">
              {isLoading
                ? 'Loading your training state…'
                : training.hasPlan
                ? 'View your workout plan and start logging workouts.'
                : 'Generate a workout plan to unlock workout logging.'}
            </p>
            <div className="mt-4 inline-flex items-center gap-2 text-primary-700 font-semibold text-sm">
              Open Training
              <span className="transition-transform group-hover:translate-x-0.5">→</span>
            </div>
          </div>
        </Link>
      </div>

      {data ? (
        <div className="mt-8 text-xs text-gray-500">
          Signed in as <span className="font-medium text-gray-700">{data.user_id}</span>
        </div>
      ) : null}
    </AppShell>
  );
}

