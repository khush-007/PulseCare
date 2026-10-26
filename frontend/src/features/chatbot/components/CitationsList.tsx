import React, { useState } from 'react';
import { Citation } from '../types/chatbot';

interface CitationsListProps {
  citations?: Citation[];
}

export const CitationsList: React.FC<CitationsListProps> = ({ citations }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!citations || citations.length === 0) return null;

  return (
    <div className="mt-2.5 pt-2 border-t border-slate-200/60 dark:border-slate-700/60 text-xs">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 text-teal-600 dark:text-teal-400 hover:text-teal-700 font-medium transition-colors focus:outline-none focus:ring-1 focus:ring-teal-500 rounded px-1.5 py-0.5"
        aria-expanded={isOpen}
      >
        <svg
          className={`w-3.5 h-3.5 transition-transform duration-200 ${isOpen ? 'rotate-90' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
        </svg>
        <span>
          {citations.length} Verified {citations.length === 1 ? 'Source' : 'Sources'} & Citations
        </span>
      </button>

      {isOpen && (
        <div className="mt-2 space-y-2 pl-2">
          {citations.map((c, idx) => (
            <div
              key={idx}
              className="p-2.5 bg-slate-50 dark:bg-slate-800/80 rounded-lg border border-slate-200 dark:border-slate-700 shadow-sm"
            >
              <div className="flex items-center justify-between text-slate-800 dark:text-slate-200 font-medium">
                <span className="truncate">{c.title}</span>
                {c.last_updated && (
                  <span className="text-[10px] text-slate-400 font-normal ml-2 flex-shrink-0">
                    Updated: {c.last_updated}
                  </span>
                )}
              </div>
              <div className="text-[11px] text-teal-600 dark:text-teal-400 mt-0.5">
                Section: {c.section}
              </div>
              {c.snippet && (
                <div className="text-[11px] text-slate-600 dark:text-slate-300 mt-1 italic line-clamp-2">
                  "{c.snippet}"
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
