import React, { useState, useEffect } from 'react';
import { useChatbot } from '../hooks/useChatbot';
import { ChatWindow } from './ChatWindow';

interface ChatWidgetProps {
  authToken?: string;
  initialOpen?: boolean;
}

export const ChatWidget: React.FC<ChatWidgetProps> = ({
  authToken,
  initialOpen = false,
}) => {
  const [isOpen, setIsOpen] = useState(initialOpen);
  const {
    messages,
    isLoading,
    isStreaming,
    suggestedActions,
    sendMessage,
    giveFeedback,
    clearHistory,
  } = useChatbot(authToken);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col items-end">
      {/* Floating Chat Modal */}
      {isOpen && (
        <div className="mb-3 animate-in fade-in slide-in-from-bottom-5 duration-200">
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            isStreaming={isStreaming}
            suggestedActions={suggestedActions}
            onSendMessage={sendMessage}
            onFeedback={giveFeedback}
            onClearHistory={clearHistory}
            onClose={() => setIsOpen(false)}
          />
        </div>
      )}

      {/* Floating Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="group relative flex items-center justify-center w-14 h-14 rounded-full bg-gradient-to-r from-teal-600 to-cyan-600 text-white shadow-xl hover:shadow-teal-500/30 hover:scale-105 active:scale-95 transition-all duration-200 focus:outline-none focus:ring-4 focus:ring-teal-400/40"
        aria-label={isOpen ? 'Close PulseCare Assistant' : 'Open PulseCare Assistant'}
        aria-expanded={isOpen}
      >
        {isOpen ? (
          <svg className="w-6 h-6 transition-transform group-hover:rotate-90 duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M6 18L18 6M6 6l12 12" />
          </svg>
        ) : (
          <div className="relative flex items-center justify-center">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
            {/* Live Status Pulse */}
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500 border-2 border-white" />
            </span>
          </div>
        )}
      </button>
    </div>
  );
};
export default ChatWidget;
