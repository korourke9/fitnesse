import React from 'react';
import { useNavigate } from 'react-router-dom';

export type AssistantTheme = 'primary' | 'green' | 'orange';

interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  /** Assistant bubble/avatar theme (green=nutritionist, orange=trainer). Ignored for user messages. */
  assistantTheme?: AssistantTheme;
}

function parseMessageLinks(text: string, navigate: (path: string) => void): React.ReactNode[] {
  // Parse markdown-style links: [text](/path)
  const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match;
  let key = 0;

  while ((match = linkRegex.exec(text)) !== null) {
    // Add text before the link
    if (match.index > lastIndex) {
      parts.push(
        <span key={`text-${key++}`}>{text.substring(lastIndex, match.index)}</span>
      );
    }

    // Add the link
    const linkText = match[1];
    const path = match[2];
    parts.push(
      <a
        key={`link-${key++}`}
        href={path}
        onClick={(e) => {
          e.preventDefault();
          navigate(path);
        }}
        className="inline-flex items-center gap-1 text-white/90 hover:text-white font-medium underline decoration-2 decoration-white/40 hover:decoration-white/60 underline-offset-2 transition-all hover:scale-105"
      >
        {linkText}
        <svg className="w-3.5 h-3.5 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
        </svg>
      </a>
    );

    lastIndex = linkRegex.lastIndex;
  }

  // Add remaining text after the last link
  if (lastIndex < text.length) {
    parts.push(<span key={`text-${key++}`}>{text.substring(lastIndex)}</span>);
  }

  return parts.length > 0 ? parts : [<span key="text-0">{text}</span>];
}

const assistantThemeClasses: Record<AssistantTheme, { gradient: string; timestamp: string }> = {
  primary: { gradient: 'bg-gradient-to-br from-primary-500 to-primary-600', timestamp: 'text-primary-600' },
  green: { gradient: 'bg-gradient-to-br from-green-500 to-green-600', timestamp: 'text-green-600' },
  orange: { gradient: 'bg-gradient-to-br from-orange-500 to-orange-600', timestamp: 'text-orange-600' },
};

const assistantIcons: Record<AssistantTheme, string> = {
  primary: '📋',
  green: '🥗',
  orange: '💪',
};

export default function ChatMessage({ role, content, timestamp, assistantTheme = 'primary' }: ChatMessageProps) {
  const isUser = role === 'user';
  const navigate = useNavigate();
  const theme = assistantThemeClasses[assistantTheme];
  const icon = assistantIcons[assistantTheme];
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 message-appear`}>
      <div className={`flex items-end gap-3 max-w-[85%] md:max-w-[75%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-all duration-300 ${
          isUser 
            ? 'bg-gradient-to-br from-accent-400 to-accent-600 shadow-soft' 
            : `${theme.gradient} shadow-soft`
        }`}>
          {isUser ? (
            <svg className="w-5 h-5 text-white drop-shadow-sm" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
            </svg>
          ) : (
            <span className="text-lg drop-shadow-sm">{icon}</span>
          )}
        </div>
        
        {/* Message bubble */}
        <div className="flex flex-col gap-1.5">
          <div className={`group relative rounded-2xl px-4 py-3 transition-all duration-200 ${
            isUser 
              ? 'bg-gradient-to-br from-accent-400 to-accent-600 text-white shadow-soft hover:shadow-lg hover:scale-[1.02]' 
              : `${theme.gradient} text-white shadow-soft hover:shadow-lg hover:scale-[1.02]`
          } ${isUser ? 'rounded-br-md' : 'rounded-bl-md'}`}>
            <p className="text-[15px] leading-relaxed whitespace-pre-wrap break-words">
              {parseMessageLinks(content, navigate)}
            </p>
            
            {/* Subtle gradient overlay on hover */}
            <div className={`absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-10 transition-opacity duration-200 pointer-events-none ${
              isUser ? 'rounded-br-md bg-white' : 'rounded-bl-md bg-white'
            }`} />
          </div>
          
          {timestamp && (
            <span className={`text-xs px-1 font-medium transition-opacity duration-200 ${
              isUser 
                ? 'text-right text-accent-600' 
                : `text-left ${theme.timestamp}`
            }`}>
              {new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
