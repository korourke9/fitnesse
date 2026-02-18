import { useMemo, useState } from 'react';
import AppShell from '../components/Layout/AppShell';
import ChatContainer from '../components/Chat/ChatContainer';
import { useAppState } from '../lib/state';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../lib/api';

type GoalSummary = {
  id: string;
  goal_type: string;
  description: string;
  target: string;
  target_value?: number | null;
  target_date?: string | null;
};

type GoalCheckIn = {
  id: string;
  text: string;
  logged_at: string;
};

export default function Goals() {
  const { data, isLoading, isError } = useAppState();
  const onboardingComplete = data?.onboarding_complete ?? false;
  const goals = ((data as any)?.goals ?? []) as GoalSummary[];
  const recentCheckIns = (((data as any)?.recent_goal_checkins ?? []) as GoalCheckIn[]) ?? [];

  const [conversationId, setConversationId] = useState<string | undefined>();
  const [chatComplete, setChatComplete] = useState(false);
  const [checkInText, setCheckInText] = useState('');
  const queryClient = useQueryClient();

  const shouldShowChat = useMemo(
    () => !isLoading && (!onboardingComplete || !chatComplete),
    [isLoading, onboardingComplete, chatComplete]
  );

  const createCheckInMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/api/logs/goals', {
        text: checkInText,
        logged_at: new Date().toISOString(),
      });
      return res.data as unknown;
    },
    onSuccess: async () => {
      setCheckInText('');
      await queryClient.invalidateQueries({ queryKey: ['appState'] });
    },
  });

  return (
    <AppShell title="Goals">
      {isError ? (
        <div className="mb-6 rounded-2xl border border-red-100 bg-red-50 p-4 text-sm text-red-800">
          Couldn’t load your goals. Try refreshing the page.
        </div>
      ) : null}

      {shouldShowChat ? (
        <div className="h-[calc(100vh-220px)] max-h-[900px]">
          <ChatContainer
            conversationId={conversationId}
            onConversationStart={setConversationId}
            onMetadata={(metadata) => {
              const md = metadata as { is_complete?: boolean } | undefined;
              if (md?.is_complete) setChatComplete(true);
            }}
            showAgentSwitcher={false}
            initialAgent="onboarding"
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <section className="lg:col-span-2 bg-white rounded-2xl border border-gray-100 shadow-soft-lg overflow-hidden">
            <div className="p-6 border-b border-gray-100">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-lg font-semibold text-gray-900">Your Goals</h2>
                  <p className="text-sm text-gray-500 mt-1">
                    Track what matters, then iterate.
                  </p>
                </div>
                <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-primary-50 text-primary-700">
                  {goals.length} active
                </span>
              </div>
            </div>

            <div className="p-6 space-y-3">
              {goals.length === 0 ? (
                <div className="rounded-xl border border-amber-100 bg-amber-50 p-4 text-sm text-amber-900">
                  No goals found. If you expected goals here, try continuing onboarding in the chat above.
                </div>
              ) : (
                goals.map((g) => (
                  <div key={g.id} className="rounded-xl border border-gray-100 bg-gray-50 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="text-xs text-gray-500">{g.goal_type}</div>
                        <div className="text-sm font-semibold text-gray-900 mt-1">{g.description}</div>
                        <div className="text-sm text-gray-700 mt-1">
                          Target: <span className="font-medium">{g.target}</span>
                          {typeof g.target_value === 'number' ? ` (${g.target_value})` : ''}
                          {g.target_date ? ` by ${g.target_date}` : ''}
                        </div>
                      </div>
                      <button
                        type="button"
                        className="px-3 py-2 rounded-xl border border-gray-200 bg-white text-sm font-semibold text-gray-700"
                        disabled
                        title="Goal editing coming soon"
                      >
                        Edit
                      </button>
                    </div>
                  </div>
                ))
              )}
              <div className="text-xs text-gray-500">
                Goal updates/editing will be enabled next (this page is now the “home” for onboarding + goals).
              </div>
            </div>
          </section>

          <aside className="space-y-6">
            <div className="bg-white rounded-2xl border border-gray-100 shadow-soft-lg p-6">
              <h3 className="font-semibold text-gray-900">Progress check-in</h3>
              <p className="text-sm text-gray-500 mt-1">
                Log how you’re doing in plain language.
              </p>
              <textarea
                className="mt-4 w-full rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500/30 focus:border-primary-400"
                placeholder='e.g., "Weight is down 1 lb this week, energy feels better"'
                rows={4}
                value={checkInText}
                onChange={(e) => setCheckInText(e.target.value)}
              />
              <button
                type="button"
                className="mt-3 w-full inline-flex items-center justify-center px-4 py-2 rounded-xl bg-primary-600 text-white font-semibold shadow-soft disabled:opacity-60"
                disabled={checkInText.trim().length === 0 || createCheckInMutation.isPending}
                onClick={() => createCheckInMutation.mutate()}
              >
                {createCheckInMutation.isPending ? 'Saving…' : 'Save check-in'}
              </button>
            </div>

            <div className="bg-white rounded-2xl border border-gray-100 shadow-soft-lg p-6">
              <h3 className="font-semibold text-gray-900">Recent check-ins</h3>
              <div className="mt-3 space-y-3">
                {recentCheckIns.length === 0 ? (
                  <div className="text-sm text-gray-500">No check-ins yet.</div>
                ) : (
                  recentCheckIns.map((c) => (
                    <div key={c.id} className="rounded-xl border border-gray-100 bg-gray-50 p-3">
                      <div className="text-xs text-gray-500">{new Date(c.logged_at).toLocaleString()}</div>
                      <div className="mt-1 text-sm text-gray-800 whitespace-pre-wrap">{c.text}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </aside>
        </div>
      )}
    </AppShell>
  );
}


