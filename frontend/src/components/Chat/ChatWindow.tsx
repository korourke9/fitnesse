import { useEffect, useRef } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

interface ChatWindowProps {
  messages: Message[];
  onSendMessage: (message: string) => void;
  isLoading?: boolean;
}

function ChatWindow({ messages, onSendMessage, isLoading }: ChatWindowProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-lg">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            <p>Start the conversation by saying hello!</p>
          </div>
        )}
        {messages.map((message) => (
          <ChatMessage
            key={message.id}
            role={message.role}
            content={message.content}
            timestamp={message.created_at}
          />
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-200 rounded-lg px-4 py-2">
              <p className="text-sm text-gray-600">Thinking...</p>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <ChatInput onSendMessage={onSendMessage} disabled={isLoading} />
    </div>
  );
}

export default ChatWindow;

