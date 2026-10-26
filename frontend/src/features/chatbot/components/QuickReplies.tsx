import React from 'react';

interface QuickRepliesProps {
  suggestions?: string[];
  onSelect: (text: string) => void;
  disabled?: boolean;
}

export const QuickReplies: React.FC<QuickRepliesProps> = ({
  suggestions,
  onSelect,
  disabled,
}) => {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div className="py-2 px-3 flex items-center gap-1.5 overflow-x-auto scrollbar-none border-t border-slate-100 dark:border-slate-800/80 bg-slate-50/50 dark:bg-slate-900/50">
      {suggestions.map((text, idx) => (
        <button
          key={idx}
          onClick={() => onSelect(text)}
          disabled={disabled}
          className="text-xs whitespace-nowrap px-3 py-1.5 rounded-full bg-white dark:bg-slate-800 text-teal-700 dark:text-teal-300 font-medium border border-teal-200/80 dark:border-teal-900/60 shadow-xs hover:bg-teal-50 dark:hover:bg-teal-950/40 hover:border-teal-300 transition-all focus:outline-none focus:ring-1 focus:ring-teal-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {text}
        </button>
      ))}
    </div>
  );
};
