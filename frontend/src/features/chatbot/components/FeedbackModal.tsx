import React, { useState } from 'react';

interface FeedbackModalProps {
  isOpen: boolean;
  messageId: string | number;
  initialRating: 'thumbs_up' | 'thumbs_down';
  onClose: () => void;
  onSubmit: (messageId: string | number, rating: 'thumbs_up' | 'thumbs_down', comment: string) => void;
}

export const FeedbackModal: React.FC<FeedbackModalProps> = ({
  isOpen,
  messageId,
  initialRating,
  onClose,
  onSubmit,
}) => {
  const [comment, setComment] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(messageId, initialRating, comment.trim());
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="feedback-title"
    >
      <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 max-w-sm w-full p-5 transition-all">
        <h3 id="feedback-title" className="text-base font-semibold text-slate-900 dark:text-slate-100 mb-2">
          {initialRating === 'thumbs_up' ? 'What went well?' : 'How can we improve?'}
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
          Your feedback helps our clinical AI engineering team ensure responses remain safe, accurate, and helpful.
        </p>

        <form onSubmit={handleSubmit} className="space-y-3">
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder={
              initialRating === 'thumbs_up'
                ? 'Optional: What was most helpful about this response?'
                : 'Optional: What was inaccurate or missing?'
            }
            rows={3}
            className="w-full text-xs p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-800 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500"
          />

          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="text-xs px-3 py-1.5 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
            >
              Skip
            </button>
            <button
              type="submit"
              className="text-xs px-3.5 py-1.5 rounded-lg bg-teal-600 text-white font-medium hover:bg-teal-700 shadow-sm transition"
            >
              Submit Feedback
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
