import { useEffect, useRef, useState } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import { apiClient } from '../../lib/api';

const STORAGE_KEYS: Record<AgentType, string> = {
  onboarding: 'fitnesse_chat_onboarding_id',
  coordination: 'fitnesse_chat_coordination_id',
  nutritionist: 'fitnesse_chat_nutrition_id',
  trainer: 'fitnesse_chat_training_id',
};

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

type AgentType = 'onboarding' | 'coordination' | 'nutritionist' | 'trainer';

interface ChatContainerProps {
  conversationId?: string;
  onConversationStart?: (conversationId: string) => void;
  onMetadata?: (metadata: unknown) => void;
  showAgentSwitcher?: boolean;
  initialAgent?: AgentType;
  /** When true, do not change agent from server metadata (e.g. stay on nutritionist/trainer; redirect via links only). */
  lockAgent?: boolean;
}

const agentInfo: Record<AgentType, { title: string; icon: string; color: string; description: string }> = {
  onboarding: { title: 'Onboarding', icon: '📋', color: 'from-primary-500 to-primary-600', description: 'Get started' },
  coordination: { title: 'Coordinator', icon: '🏠', color: 'from-primary-500 to-primary-600', description: 'Navigate app' },
  nutritionist: { title: 'Nutritionist', icon: '🥗', color: 'from-green-500 to-green-600', description: 'Meal tracking' },
  trainer: { title: 'Personal Trainer', icon: '💪', color: 'from-orange-500 to-orange-600', description: 'Workout tracking' },
};

const agentOrder: AgentType[] = ['onboarding', 'coordination', 'nutritionist', 'trainer'];

export default function ChatContainer({ 
  conversationId: initialConversationId,
  onConversationStart,
  onMetadata,
  showAgentSwitcher = true,
  initialAgent = 'onboarding',
  lockAgent = false,
}: ChatContainerProps) {
  const storageKey = STORAGE_KEYS[initialAgent];
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversationId, setConversationId] = useState<string | undefined>(() => {
    if (initialConversationId) return initialConversationId;
    if (typeof window !== 'undefined' && storageKey) {
      return localStorage.getItem(storageKey) ?? undefined;
    }
    return undefined;
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [currentAgent, setCurrentAgent] = useState<AgentType>(initialAgent);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const fetchedConversationIdRef = useRef<string | null>(null);

  // Load conversation history when we have a conversationId we haven't fetched yet
  useEffect(() => {
    const id = conversationId;
    if (!id || fetchedConversationIdRef.current === id) return;
    fetchedConversationIdRef.current = id;
    setIsLoadingHistory(true);
    apiClient
      .get(`/api/chat/conversations/${id}/messages`)
      .then((res) => {
        const list = res.data?.messages ?? [];
        setMessages(
          list.map((m: { id: string; role: string; content: string; created_at: string }) => ({
            id: m.id,
            role: m.role as 'user' | 'assistant',
            content: m.content,
            created_at: m.created_at,
          }))
        );
      })
      .catch((err) => {
        fetchedConversationIdRef.current = null;
        if (err.response?.status === 404 && storageKey && typeof window !== 'undefined') {
          localStorage.removeItem(storageKey);
          setConversationId(undefined);
        }
      })
      .finally(() => setIsLoadingHistory(false));
  }, [conversationId]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleAgentSwitch = (agent: AgentType) => {
    setCurrentAgent(agent);
    setIsDropdownOpen(false);
    // Agent type will be sent with the next message
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (message: string) => {
    // Optimistically add user message immediately for better UX
    const tempUserMessageId = `temp-${Date.now()}`;
    const optimisticUserMessage: Message = {
      id: tempUserMessageId,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    };
    
    setMessages((prev) => [...prev, optimisticUserMessage]);
    setIsLoading(true);
    
    try {
      const response = await apiClient.post('/api/chat', {
        message,
        conversation_id: conversationId,
        agent_type: currentAgent,  // Already lowercase
      });

      const { conversation_id, user_message, assistant_message, metadata } = response.data;
      onMetadata?.(metadata);
      
      // Update current agent if it changed (unless lockAgent: redirect via links only)
      if (!lockAgent && metadata?.agent_type) {
        setCurrentAgent(metadata.agent_type as AgentType);
      }

      // Update conversation ID if this is a new conversation; persist for this agent
      if (!conversationId && conversation_id) {
        setConversationId(conversation_id);
        onConversationStart?.(conversation_id);
        const key = STORAGE_KEYS[currentAgent];
        if (key && typeof window !== 'undefined') {
          localStorage.setItem(key, conversation_id);
        }
      }

      // Replace optimistic message with real messages from server
      setMessages((prev) => {
        // Remove the temporary optimistic message
        const withoutTemp = prev.filter((msg) => msg.id !== tempUserMessageId);
        // Add the real messages from server
        return [
          ...withoutTemp,
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
        ];
      });
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages((prev) => prev.filter((msg) => msg.id !== tempUserMessageId));
      const msg = (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Something went wrong. Try again.';
      setMessages((prev) => [...prev, { id: `error-${Date.now()}`, role: 'assistant', content: `⚠️ ${msg}`, created_at: new Date().toISOString() }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl shadow-soft-lg overflow-hidden border border-gray-100">
      {/* Chat Header - theme matches agent (green=nutritionist, orange=trainer) */}
      <div className={`relative bg-gradient-to-r ${agentInfo[currentAgent].color} px-6 py-4 border-b border-black/10 transition-all duration-300`}>
        <div className="flex items-center gap-3">
          {showAgentSwitcher ? (
            // Clickable agent icon with dropdown
            <div className="relative" ref={dropdownRef}>
              <button
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                className="w-10 h-10 rounded-full bg-white/90 flex items-center justify-center shadow-soft text-2xl hover:bg-white hover:scale-105 transition-all duration-200 cursor-pointer"
                title="Switch agent"
              >
                {agentInfo[currentAgent].icon}
              </button>
              
              {/* Dropdown menu */}
              {isDropdownOpen && (
                <div className="absolute top-12 left-0 z-50 bg-white rounded-xl shadow-lg border border-gray-200 py-2 min-w-[200px] animate-fade-in">
                  {agentOrder.map((agent) => (
                    <button
                      key={agent}
                      onClick={() => handleAgentSwitch(agent)}
                      className={`w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-colors ${
                        currentAgent === agent ? 'bg-primary-50' : ''
                      }`}
                    >
                      <span className="text-2xl">{agentInfo[agent].icon}</span>
                      <div className="text-left">
                        <div className={`font-medium ${currentAgent === agent ? 'text-primary-600' : 'text-gray-800'}`}>
                          {agentInfo[agent].title}
                        </div>
                        <div className="text-xs text-gray-500">{agentInfo[agent].description}</div>
                      </div>
                      {currentAgent === agent && (
                        <span className="ml-auto text-primary-500">✓</span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            // Static icon (no switching)
            <div className="w-10 h-10 rounded-full bg-white/90 flex items-center justify-center shadow-soft text-2xl">
              {agentInfo[currentAgent].icon}
            </div>
          )}
          
          <div className="flex-1">
            <h3 className="text-white font-semibold text-lg">{agentInfo[currentAgent].title}</h3>
            {currentAgent !== 'onboarding' && (
              <p className="text-white/70 text-xs">Say "help" to see options</p>
            )}
          </div>
          
          {/* Dropdown indicator */}
          {showAgentSwitcher ? (
            <button
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className="text-white/70 hover:text-white transition-colors"
              title="Switch agent"
            >
              <svg className={`w-5 h-5 transition-transform ${isDropdownOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          ) : null}
        </div>
        
        {/* Decorative gradient overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-white/10 to-transparent pointer-events-none" />
      </div>
      
      {/* Messages Area - scrollbar theme matches agent */}
      <div
        className="flex-1 overflow-y-auto px-4 sm:px-6 py-6 bg-gradient-to-br from-gray-50 via-white to-primary-50/30 chat-messages"
        data-chat-theme={currentAgent === 'nutritionist' ? 'green' : currentAgent === 'trainer' ? 'orange' : undefined}
      >
        {isLoadingHistory && (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500 text-sm">Loading conversation...</p>
          </div>
        )}
        {!isLoadingHistory && messages.length === 0 && (
          <div className="flex items-center justify-center h-full animate-fade-in">
            <div className="text-center max-w-md px-4">
              <div className={`relative inline-flex items-center justify-center w-16 h-16 mb-4 rounded-full bg-gradient-to-br ${agentInfo[currentAgent].color} shadow-soft-lg`}>
                <span className="text-3xl">{agentInfo[currentAgent].icon}</span>
              </div>
              <p className="text-gray-500 text-sm">
                {showAgentSwitcher
                  ? 'Share your goals, preferences, and habits to get started.'
                  : 'Ask about your plan or give feedback. Type a message below.'}
              </p>
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
              assistantTheme={currentAgent === 'nutritionist' ? 'green' : currentAgent === 'trainer' ? 'orange' : 'primary'}
            />
          ))}
          {isLoading && (
            <div className="flex justify-start message-appear">
              <div className="flex items-end gap-3">
                <div className={`flex-shrink-0 w-9 h-9 rounded-full bg-gradient-to-br ${agentInfo[currentAgent].color} flex items-center justify-center shadow-soft`}>
                  <span className="text-lg">{agentInfo[currentAgent].icon}</span>
                </div>
                <div className={`bg-gradient-to-br ${agentInfo[currentAgent].color} rounded-2xl rounded-bl-md px-5 py-4 shadow-soft`}>
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
      
      {/* Input Area - theme matches agent when single-agent (nutritionist=green, trainer=orange) */}
      <ChatInput 
        onSendMessage={handleSendMessage} 
        disabled={isLoading || isLoadingHistory}
        placeholder="Type your message..."
        theme={currentAgent === 'nutritionist' ? 'green' : currentAgent === 'trainer' ? 'orange' : 'primary'}
      />
    </div>
  );
}
