import { useState, useRef } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';

type ThemeColor = 'primary' | 'green' | 'orange';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled?: boolean;
  placeholder?: string;
  /** Match send button to agent theme (green=nutritionist, orange=trainer). */
  theme?: ThemeColor;
}

const themeClasses: Record<ThemeColor, string> = {
  primary: 'bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700',
  green: 'bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700',
  orange: 'bg-gradient-to-r from-orange-500 to-orange-600 hover:from-orange-600 hover:to-orange-700',
};

export default function ChatInput({ 
  onSendMessage, 
  disabled = false,
  placeholder = "Type your message...",
  theme = 'primary',
}: ChatInputProps) {
  const [message, setMessage] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
      textareaRef.current?.focus();
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessage(e.target.value);
    // Auto-resize textarea
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative border-t border-gray-100 bg-gradient-to-r from-gray-50 to-white p-4">
      <div className="flex items-end gap-3 relative">
        {/* Input container with gradient border effect */}
        <div className={`flex-1 relative transition-all duration-300 ${
          isFocused ? 'scale-[1.01]' : 'scale-100'
        }`}>
          <div className={`absolute inset-0 rounded-xl transition-all duration-300 ${
            isFocused 
              ? 'bg-gradient-to-r from-primary-400 to-accent-400 opacity-100 blur-sm' 
              : 'bg-gray-200 opacity-0'
          }`} />
          
          <div className="relative">
            <textarea
              ref={textareaRef}
              value={message}
              onChange={handleInput}
              onKeyDown={handleKeyDown}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder={placeholder}
              disabled={disabled}
              rows={1}
              wrap="soft"
              className={`w-full px-5 py-3.5 text-[15px] bg-white border-2 rounded-xl transition-all duration-300 placeholder:text-gray-400 disabled:bg-gray-50 disabled:cursor-not-allowed resize-none overflow-hidden break-words whitespace-pre-wrap ${
                isFocused
                  ? 'border-transparent shadow-soft-lg'
                  : 'border-gray-200 shadow-soft hover:border-gray-300'
              } focus:outline-none`}
              style={{ minHeight: '48px', maxHeight: '120px', wordWrap: 'break-word', overflowWrap: 'break-word' }}
            />
          </div>
        </div>

        {/* Send button with gradient */}
        <button
          type="submit"
          disabled={disabled || !message.trim()}
          className={`relative px-6 py-3.5 rounded-xl font-medium text-white text-[15px] transition-all duration-300 overflow-hidden group ${
            disabled || !message.trim()
              ? 'bg-gray-300 cursor-not-allowed'
              : `${themeClasses[theme]} shadow-soft hover:shadow-lg hover:scale-105 active:scale-95`
          }`}
        >
          {/* Shine effect on hover */}
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-0 group-hover:opacity-20 group-hover:animate-[shimmer_1.5s_ease-in-out] -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
          
          <span className="relative flex items-center gap-2">
            Send
            <svg className="w-4 h-4 transition-transform group-hover:translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </span>
        </button>
      </div>
      
      {/* Helper text */}
      <div className="mt-2 px-1 text-xs text-gray-400 flex items-center gap-1">
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Press Enter to send, Shift+Enter for new line
      </div>
    </form>
  );
}
