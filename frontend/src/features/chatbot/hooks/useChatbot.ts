import { useState, useEffect, useCallback } from 'react';
import { ChatMessage, Citation, ChatStreamEventMetadata } from '../types/chatbot';
import { streamMessageApi, submitFeedbackApi, clearSessionApi } from '../api/chatbotApi';

const DEFAULT_WELCOME_MESSAGE: ChatMessage = {
  id: 'welcome-0',
  role: 'assistant',
  content: 'Hello! I am PulseCare\'s AI Healthcare Assistant. I can help you find specialists, view your appointments, explore medical services, or provide clinical triage guidance. How can I assist you today?',
  info_badge: 'verified',
  citations: [],
  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  suggested_actions: [
    'Find a Cardiologist',
    'What insurance is accepted?',
    'Show my appointments',
    'Amoxicillin details',
  ],
};

export function useChatbot(authToken?: string) {
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const saved = localStorage.getItem('pulsecare_chat_history');
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch (e) {
        return [DEFAULT_WELCOME_MESSAGE];
      }
    }
    return [DEFAULT_WELCOME_MESSAGE];
  });

  const [sessionId, setSessionId] = useState<string | null>(() => {
    return localStorage.getItem('pulsecare_session_id') || null;
  });

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestedActions, setSuggestedActions] = useState<string[]>(
    DEFAULT_WELCOME_MESSAGE.suggested_actions || []
  );

  // Sync to local storage
  useEffect(() => {
    try {
      localStorage.setItem('pulsecare_chat_history', JSON.stringify(messages));
    } catch (e) {
      console.warn('Storage sync error', e);
    }
  }, [messages]);

  useEffect(() => {
    if (sessionId) {
      localStorage.setItem('pulsecare_session_id', sessionId);
    }
  }, [sessionId]);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isLoading || isStreaming) return;

      setError(null);
      const userMsgId = `user-${Date.now()}`;
      const userMessage: ChatMessage = {
        id: userMsgId,
        role: 'user',
        content: trimmed,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);
      setIsStreaming(true);

      const botMsgId = `bot-${Date.now()}`;
      let accumulatedContent = '';

      // Create placeholder assistant message
      setMessages((prev) => [
        ...prev,
        {
          id: botMsgId,
          role: 'assistant',
          content: '',
          info_badge: 'general',
          citations: [],
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        },
      ]);

      await streamMessageApi(trimmed, sessionId, authToken, {
        onMetadata: (meta: ChatStreamEventMetadata) => {
          setSessionId(meta.session_id);
          if (meta.suggested_actions && meta.suggested_actions.length > 0) {
            setSuggestedActions(meta.suggested_actions);
          }
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botMsgId
                ? {
                    ...m,
                    info_badge: meta.info_badge,
                    is_emergency: meta.is_emergency,
                    route: meta.route,
                  }
                : m
            )
          );
        },
        onToken: (token: string) => {
          setIsLoading(false);
          accumulatedContent += token;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botMsgId ? { ...m, content: accumulatedContent } : m
            )
          );
        },
        onCitations: (citations: Citation[]) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botMsgId ? { ...m, citations } : m
            )
          );
        },
        onDone: (data) => {
          setIsStreaming(false);
          setIsLoading(false);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botMsgId ? { ...m, id: data.message_id } : m
            )
          );
        },
        onError: (err: Error) => {
          setIsStreaming(false);
          setIsLoading(false);
          setError(err.message || 'Failed to receive response from PulseCare Assistant.');
          setMessages((prev) =>
            prev.map((m) =>
              m.id === botMsgId
                ? {
                    ...m,
                    content:
                      m.content ||
                      'Sorry, I encountered an issue connecting to the PulseCare server. Please try again or call our clinic at 1-800-PULSE-CARE.',
                  }
                : m
            )
          );
        },
      });
    },
    [sessionId, authToken, isLoading, isStreaming]
  );

  const giveFeedback = useCallback(
    async (messageId: number | string, rating: 'thumbs_up' | 'thumbs_down', comment?: string) => {
      try {
        const numericId = typeof messageId === 'number' ? messageId : parseInt(String(messageId), 10);
        if (!isNaN(numericId)) {
          await submitFeedbackApi({ message_id: numericId, rating, comment }, authToken);
        }
        setMessages((prev) =>
          prev.map((m) => (m.id === messageId ? { ...m, feedbackGiven: rating } : m))
        );
      } catch (e) {
        console.error('Feedback error:', e);
      }
    },
    [authToken]
  );

  const clearHistory = useCallback(async () => {
    if (sessionId) {
      try {
        await clearSessionApi(sessionId, authToken);
      } catch (e) {
        console.warn('Backend clear session error:', e);
      }
    }
    localStorage.removeItem('pulsecare_chat_history');
    localStorage.removeItem('pulsecare_session_id');
    setSessionId(null);
    setMessages([DEFAULT_WELCOME_MESSAGE]);
    setSuggestedActions(DEFAULT_WELCOME_MESSAGE.suggested_actions || []);
  }, [sessionId, authToken]);

  return {
    messages,
    sessionId,
    isLoading,
    isStreaming,
    error,
    suggestedActions,
    sendMessage,
    giveFeedback,
    clearHistory,
  };
}
