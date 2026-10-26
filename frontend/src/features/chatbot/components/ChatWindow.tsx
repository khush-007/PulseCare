import React, { useState, useRef, useEffect } from 'react';
import { ChatMessage } from '../types/chatbot';
import { ChatMessageItem } from './ChatMessageItem';
import { QuickReplies } from './QuickReplies';

interface ChatWindowProps {
  messages: ChatMessage[];
  isLoading: boolean;
  isStreaming: boolean;
  suggestedActions: string[];
  onSendMessage: (text: string) => void;
  onFeedback: (messageId: string | number, rating: 'thumbs_up' | 'thumbs_down', comment?: string) => void;
  onClearHistory: () => void;
  onClose: () => void;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  isLoading,
  isStreaming,
  suggestedActions,
  onSendMessage,
  onFeedback,
  onClearHistory,
  onClose,
}) => {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom whenever messages change or stream updates
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    const trimmed = inputText.trim();
    if (!trimmed || isLoading || isStreaming) return;
    onSendMessage(trimmed);
    setInputText('');
  };

  return (
    <div
      className="flex flex-col w-[380px] sm:w-[420px] h-[600px] max-h-[85vh] bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200/90 dark:border-slate-800 overflow-hidden transition-all duration-200 z-50 font-sans"
      role="region"
      aria-label="PulseCare Healthcare Chat Window"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-teal-700 via-teal-600 to-cyan-600 text-white shadow-md">
        <div className="flex items-center gap-2.5">
          <div className="relative">
            <div className="w-8 h-8 rounded-full bg-white/20 backdrop-blur-md flex items-center justify-center font-bold text-sm shadow-inner">
              ❤️
            </div>
            <span
              className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-400 border-2 border-teal-700 rounded-full animate-pulse"
              title="Online and active"
            />
          </div>
          <div>
            <h2 className="text-sm font-semibold tracking-tight leading-tight">
              PulseCare Assistant
            </h2>
            <p className="text-[10px] text-teal-100 flex items-center gap-1 font-medium">
              Verified Healthcare Intelligence
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          {/* Clear History Button */}
          <button
            onClick={() => {
              if (window.confirm('Clear your conversation history?')) {
                onClearHistory();
              }
            }}
            className="p-1.5 rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition focus:outline-none focus:ring-1 focus:ring-white"
            title="Clear Chat History"
            aria-label="Clear Chat History"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>

          {/* Close Window Button */}
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition focus:outline-none focus:ring-1 focus:ring-white"
            title="Minimize Assistant"
            aria-label="Close Assistant"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 p-3.5 overflow-y-auto bg-slate-50/40 dark:bg-slate-950/40 space-y-1">
        {messages.map((msg) => (
          <ChatMessageItem
            key={msg.id}
            message={msg}
            onFeedback={onFeedback}
          />
        ))}

        {isLoading && !isStreaming && (
          <div className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500 pl-1 py-1">
            <span className="w-2 h-2 rounded-full bg-teal-500 animate-bounce" />
            <span className="w-2 h-2 rounded-full bg-teal-500 animate-bounce [animation-delay:0.2s]" />
            <span className="w-2 h-2 rounded-full bg-teal-500 animate-bounce [animation-delay:0.4s]" />
            <span className="text-[11px] font-medium ml-1">Consulting PulseCare records...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Replies Row */}
      <QuickReplies
        suggestions={suggestedActions}
        onSelect={(actionText) => onSendMessage(actionText)}
        disabled={isLoading || isStreaming}
      />

      {/* Input Bar */}
      <div className="p-3 bg-white dark:bg-slate-900 border-t border-slate-200/80 dark:border-slate-800">
        <div className="flex items-end gap-2 bg-slate-100 dark:bg-slate-800 rounded-xl p-1.5 border border-slate-200/60 dark:border-slate-700/60 focus-within:ring-2 focus-within:ring-teal-500/50">
          <textarea
            ref={inputRef}
            rows={1}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about doctors, visits, medicines, or symptoms..."
            disabled={isLoading || isStreaming}
            className="flex-1 bg-transparent text-xs p-1.5 max-h-24 resize-none text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none disabled:opacity-60"
            aria-label="Message Input"
          />
          <button
            onClick={handleSend}
            disabled={!inputText.trim() || isLoading || isStreaming}
            className="p-2 rounded-lg bg-teal-600 text-white font-medium hover:bg-teal-700 disabled:opacity-40 disabled:cursor-not-allowed shadow-xs transition-colors flex-shrink-0"
            aria-label="Send message"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </button>
        </div>

        {/* Persistent Legal & Safety Disclaimer */}
        <p className="text-[10px] text-slate-400 dark:text-slate-500 text-center mt-2 leading-tight px-2">
          PulseCare AI is for informational purposes only. In a life-threatening emergency, call 911 immediately.
        </p>
      </div>
    </div>
  );
};
