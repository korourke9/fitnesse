import { useEffect, useRef, useState } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import { apiClient } from '../../lib/api';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

interface ChatContainerProps {
  conversationId?: string;
  onConversationStart?: (conversationId: string) => void;
}

export default function ChatContainer({ 
  conversationId: initialConversationId,
  onConversationStart 
}: ChatContainerProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>(initialConversationId);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (message: string) => {
    setIsLoading(true);
    
    try {
      const response = await apiClient.post('/api/chat/onboarding', {
        message,
        conversation_id: conversationId,
      });

      const { conversation_id, user_message, assistant_message } = response.data;

      // Update conversation ID if this is a new conversation
      if (!conversationId && conversation_id) {
        setConversationId(conversation_id);
        onConversationStart?.(conversation_id);
      }

      // Add both messages to the chat
      setMessages((prev) => [
        ...prev,
        {
          id: user_message.id,
          role: 'user' as const,
          content: user_message.content,
          created_at: user_message.created_at,
        },
        {
          id: assistant_message.id,
          role: 'assistant' as const,
          content: assistant_message.content,
          created_at: assistant_message.created_at,
        },
      ]);
    } catch (error) {
      console.error('Error sending message:', error);
      // TODO: Show error message to user
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl shadow-soft-lg overflow-hidden border border-gray-100">
      {/* Chat Header */}
      <div className="relative bg-gradient-to-r from-primary-500 to-primary-600 px-6 py-4 border-b border-primary-700/20">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-white/90 flex items-center justify-center shadow-soft">
            <svg className="w-6 h-6 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="text-white font-semibold text-lg">Health Assistant</h3>
          </div>
        </div>
        
        {/* Decorative gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-white/10 to-transparent pointer-events-none" />
      </div>
      
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 bg-gradient-to-br from-gray-50 via-white to-primary-50/30">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full animate-fade-in">
            <div className="text-center max-w-md px-4">
              <div className="relative inline-flex items-center justify-center w-20 h-20 mb-6">
                {/* Animated rings */}
                <div className="absolute inset-0 bg-gradient-to-br from-primary-400 to-accent-400 rounded-full opacity-20 animate-ping"></div>
                <div className="absolute inset-2 bg-gradient-to-br from-primary-500 to-accent-500 rounded-full opacity-30 animate-pulse-slow"></div>
                <div className="relative w-16 h-16 bg-gradient-to-br from-primary-500 to-primary-600 rounded-full flex items-center justify-center shadow-soft-lg">
                  <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
              </div>
              <h4 className="text-xl font-semibold text-gray-800 mb-2">Welcome to Your Health Journey</h4>
              <p className="text-gray-500 text-sm leading-relaxed">
                Share your health goals, dietary preferences, exercise habits, biometric data you're comfortable with, cooking budget, or any other information to help me create a personalized plan for you.
              </p>
              
              {/* Suggested prompts */}
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {['👋 Say hello', '💪 Fitness tips', '🥗 Nutrition advice'].map((prompt, i) => (
                  <button
                    key={i}
                    className="px-4 py-2 bg-white border border-gray-200 rounded-full text-sm text-gray-600 hover:border-primary-400 hover:text-primary-600 hover:shadow-soft transition-all duration-200 hover:scale-105"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
        <div className="space-y-2">
          {messages.map((message) => (
            <ChatMessage
              key={message.id}
              role={message.role}
              content={message.content}
              timestamp={message.created_at}
            />
          ))}
          {isLoading && (
            <div className="flex justify-start message-appear">
              <div className="flex items-end gap-3">
                <div className="flex-shrink-0 w-9 h-9 rounded-full bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-soft">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                  </svg>
                </div>
                <div className="bg-gradient-to-br from-primary-500 to-primary-600 rounded-2xl rounded-bl-md px-5 py-4 shadow-soft">
                  <div className="flex space-x-2">
                    <div className="w-2.5 h-2.5 bg-white/90 rounded-full typing-dot"></div>
                    <div className="w-2.5 h-2.5 bg-white/90 rounded-full typing-dot"></div>
                    <div className="w-2.5 h-2.5 bg-white/90 rounded-full typing-dot"></div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
        <div ref={messagesEndRef} />
      </div>
      
      {/* Input Area */}
      <ChatInput 
        onSendMessage={handleSendMessage} 
        disabled={isLoading}
        placeholder="Type your message..."
      />
    </div>
  );
}
