interface ChatMessageProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export default function ChatMessage({ role, content, timestamp }: ChatMessageProps) {
  const isUser = role === 'user';
  
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 message-appear`}>
      <div className={`flex items-end gap-3 max-w-[85%] md:max-w-[75%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* Avatar */}
        <div className={`flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center transition-all duration-300 ${
          isUser 
            ? 'bg-gradient-to-br from-accent-400 to-accent-600 shadow-soft' 
            : 'bg-gradient-to-br from-primary-500 to-primary-700 shadow-soft'
        }`}>
          {isUser ? (
            <svg className="w-5 h-5 text-white drop-shadow-sm" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
            </svg>
          ) : (
            <svg className="w-5 h-5 text-white drop-shadow-sm" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
            </svg>
          )}
        </div>
        
        {/* Message bubble */}
        <div className="flex flex-col gap-1.5">
          <div className={`group relative rounded-2xl px-4 py-3 transition-all duration-200 ${
            isUser 
              ? 'bg-gradient-to-br from-accent-400 to-accent-600 text-white shadow-soft hover:shadow-lg hover:scale-[1.02]' 
              : 'bg-gradient-to-br from-primary-500 to-primary-600 text-white shadow-soft hover:shadow-lg hover:scale-[1.02]'
          } ${isUser ? 'rounded-br-md' : 'rounded-bl-md'}`}>
            <p className="text-[15px] leading-relaxed whitespace-pre-wrap break-words">
              {content}
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
                : 'text-left text-primary-600'
            }`}>
              {new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
