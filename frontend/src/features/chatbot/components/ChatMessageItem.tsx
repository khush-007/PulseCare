import React, { useState } from 'react';
import { ChatMessage } from '../types/chatbot';
import { CitationsList } from './CitationsList';
import { FeedbackModal } from './FeedbackModal';

interface ChatMessageItemProps {
  message: ChatMessage;
  onFeedback: (messageId: string | number, rating: 'thumbs_up' | 'thumbs_down', comment?: string) => void;
}

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({
  message,
  onFeedback,
}) => {
  const isUser = message.role === 'user';
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedRating, setSelectedRating] = useState<'thumbs_up' | 'thumbs_down'>('thumbs_up');

  const handleFeedbackClick = (rating: 'thumbs_up' | 'thumbs_down') => {
    setSelectedRating(rating);
    setModalOpen(true);
  };

  const isVerified = message.info_badge === 'verified';

  // Render markdown text formatting (bold, bullet points, links)
  const renderFormattedContent = (content: string) => {
    const lines = content.split('\n');
    return lines.map((line, idx) => {
      // Bold rendering
      let formattedLine = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
      // Link rendering [text](url)
      formattedLine = formattedLine.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-teal-600 underline font-medium hover:text-teal-700" target="_blank" rel="noopener noreferrer">$1</a>');

      if (line.startsWith('• ') || line.startsWith('- ')) {
        return (
          <li
            key={idx}
            className="ml-3 list-disc my-0.5 leading-relaxed"
            dangerouslySetInnerHTML={{ __html: formattedLine.replace(/^[•-]\s*/, '') }}
          />
        );
      }
      if (line.startsWith('### ')) {
        return (
          <h4
            key={idx}
            className="text-xs font-bold text-slate-800 dark:text-slate-100 mt-2 mb-1"
            dangerouslySetInnerHTML={{ __html: formattedLine.replace(/^###\s*/, '') }}
          />
        );
      }
      if (line.trim() === '---') {
        return <hr key={idx} className="my-2 border-slate-200 dark:border-slate-700" />;
      }
      if (!line.trim()) {
        return <div key={idx} className="h-1.5" />;
      }
      return (
        <p
          key={idx}
          className="my-0.5 leading-relaxed text-xs"
          dangerouslySetInnerHTML={{ __html: formattedLine }}
        />
      );
    });
  };

  return (
    <div className={`flex w-full mb-3.5 ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex gap-2.5 max-w-[85%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        {/* Avatar */}
        <div
          className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-semibold shadow-xs ${
            isUser
              ? 'bg-slate-700 text-white'
              : 'bg-teal-600 text-white shadow-teal-500/20'
          }`}
          aria-hidden="true"
        >
          {isUser ? 'You' : 'PC'}
        </div>

        {/* Message Bubble */}
        <div className="flex flex-col">
          {!isUser && (
            <div className="flex items-center gap-2 mb-1 pl-1">
              <span className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                PulseCare Assistant
              </span>
              {/* Visible Verified / General Information Badge */}
              <span
                className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-medium ${
                  isVerified
                    ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300 border border-emerald-200/80 dark:border-emerald-800'
                    : 'bg-blue-50 text-blue-700 dark:bg-blue-950/60 dark:text-blue-300 border border-blue-200/80 dark:border-blue-800'
                }`}
                title={
                  isVerified
                    ? 'Information verified from PulseCare clinical database or verified hospital guidelines'
                    : 'General educational guidance. Consult a doctor for personalized care.'
                }
              >
                {isVerified ? (
                  <>
                    <svg className="w-2.5 h-2.5 text-emerald-600 dark:text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    Verified Data
                  </>
                ) : (
                  <>
                    <svg className="w-2.5 h-2.5 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                    </svg>
                    General Info
                  </>
                )}
              </span>
            </div>
          )}

          <div
            className={`p-3 rounded-2xl shadow-xs text-xs ${
              isUser
                ? 'bg-teal-600 text-white rounded-tr-none'
                : 'bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 text-slate-800 dark:text-slate-100 rounded-tl-none'
            }`}
          >
            {renderFormattedContent(message.content)}
            <CitationsList citations={message.citations} />
          </div>

          {/* Footer with Timestamp and Feedback buttons for Assistant */}
          <div className="flex items-center justify-between text-[10px] text-slate-400 dark:text-slate-500 mt-1 px-1">
            <span>{message.timestamp}</span>
            {!isUser && (
              <div className="flex items-center gap-1.5 ml-3">
                <button
                  onClick={() => handleFeedbackClick('thumbs_up')}
                  disabled={!!message.feedbackGiven}
                  className={`p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition ${
                    message.feedbackGiven === 'thumbs_up' ? 'text-teal-600 font-bold' : 'text-slate-400'
                  }`}
                  aria-label="Helpful response"
                  title="Helpful response"
                >
                  👍
                </button>
                <button
                  onClick={() => handleFeedbackClick('thumbs_down')}
                  disabled={!!message.feedbackGiven}
                  className={`p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition ${
                    message.feedbackGiven === 'thumbs_down' ? 'text-rose-600 font-bold' : 'text-slate-400'
                  }`}
                  aria-label="Inaccurate or unhelpful response"
                  title="Inaccurate or unhelpful response"
                >
                  👎
                </button>
                {message.feedbackGiven && (
                  <span className="text-[9px] text-teal-600 font-medium">Feedback saved</span>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      <FeedbackModal
        isOpen={modalOpen}
        messageId={message.id}
        initialRating={selectedRating}
        onClose={() => setModalOpen(false)}
        onSubmit={(mid, rating, comment) => onFeedback(mid, rating, comment)}
      />
    </div>
  );
};
