import { useState } from 'react';
import ChatContainer from '../components/Chat/ChatContainer';

export default function Onboarding() {
  const [conversationId, setConversationId] = useState<string | undefined>();

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
          />
        </div>
      </main>
    </div>
  );
}
