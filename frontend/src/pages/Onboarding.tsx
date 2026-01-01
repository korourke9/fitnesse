import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ChatContainer from '../components/Chat/ChatContainer';

export default function Onboarding() {
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [isComplete, setIsComplete] = useState(false);
  const navigate = useNavigate();

  const canContinue = useMemo(() => isComplete, [isComplete]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-gray-50">
      {/* Simple header */}
      <header className="border-b border-gray-100 bg-white/80 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-primary-500 to-primary-600 rounded-lg flex items-center justify-center shadow-sm">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
            </div>
            <span className="text-xl font-semibold text-gray-900">Fitnesse</span>
          </div>
        </div>
      </header>

      {/* Main content - just the chat */}
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="h-[calc(100vh-120px)] max-h-[900px]">
          <ChatContainer 
            conversationId={conversationId}
            onConversationStart={setConversationId}
            onMetadata={(metadata) => {
              const md = metadata as { is_complete?: boolean } | undefined;
              if (md?.is_complete) setIsComplete(true);
            }}
            showAgentSwitcher={false}
            initialAgent="onboarding"
          />
        </div>

        {canContinue ? (
          <div className="fixed inset-x-0 bottom-0 pb-6 px-4 sm:px-6">
            <div className="max-w-5xl mx-auto">
              <div className="bg-white/90 backdrop-blur-sm border border-gray-200 rounded-2xl shadow-soft-lg p-4 flex items-center justify-between gap-4">
                <div>
                  <div className="text-sm font-semibold text-gray-900">Onboarding complete</div>
                  <div className="text-xs text-gray-500 mt-0.5">
                    Next: generate your meal plan and workout plan from the dashboard.
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => navigate('/dashboard', { replace: true })}
                  className="inline-flex items-center justify-center px-4 py-2 rounded-xl bg-primary-600 text-white font-semibold shadow-soft hover:shadow-soft-lg transition-all"
                >
                  Continue to Dashboard
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
}
