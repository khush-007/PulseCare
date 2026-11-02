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

function getChatStorageScope(authToken?: string): string {
  if (!authToken) return 'guest';

  try {
    const payload = authToken.split('.')[1];
    if (!payload) return 'authenticated';
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/');
    const claims = JSON.parse(window.atob(normalized));
    if (typeof claims.sub === 'string' && claims.sub.length > 0) {
      return `user-${claims.sub}`;
    }
  } catch {
    // An unreadable token is still kept separate from the guest cache.
  }

  return 'authenticated';
}

function loadChatMessages(storageScope: string): ChatMessage[] {
  const saved = localStorage.getItem(`pulsecare_chat_history:${storageScope}`);
  if (!saved) return [DEFAULT_WELCOME_MESSAGE];
  try {
    return JSON.parse(saved);
  } catch {
    return [DEFAULT_WELCOME_MESSAGE];
  }
}

function loadChatSessionId(storageScope: string): string | null {
  return localStorage.getItem(`pulsecare_session_id:${storageScope}`);
}

export function useChatbot(authToken?: string) {
  const storageScope = getChatStorageScope(authToken);
  const [activeStorageScope, setActiveStorageScope] = useState(storageScope);
  const [messages, setMessages] = useState<ChatMessage[]>(() => loadChatMessages(storageScope));

  const [sessionId, setSessionId] = useState<string | null>(() => loadChatSessionId(storageScope));

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestedActions, setSuggestedActions] = useState<string[]>(
    DEFAULT_WELCOME_MESSAGE.suggested_actions || []
  );

  // Switch local cache when the authenticated identity changes. A JWT subject
  // is used only as a cache namespace; the server remains the authority.
  useEffect(() => {
    if (activeStorageScope === storageScope) return;
    setMessages(loadChatMessages(storageScope));
    setSessionId(loadChatSessionId(storageScope));
    setSuggestedActions(DEFAULT_WELCOME_MESSAGE.suggested_actions || []);
    setError(null);
    setActiveStorageScope(storageScope);
  }, [activeStorageScope, storageScope]);

  // Keep each account's browser cache and session ID in its own namespace.
  useEffect(() => {
    if (activeStorageScope !== storageScope) return;
    try {
      localStorage.setItem(`pulsecare_chat_history:${storageScope}`, JSON.stringify(messages));
    } catch (e) {
      console.warn('Storage sync error', e);
    }
  }, [activeStorageScope, messages, storageScope]);

  useEffect(() => {
    if (activeStorageScope !== storageScope) return;
    const key = `pulsecare_session_id:${storageScope}`;
    if (sessionId) localStorage.setItem(key, sessionId);
    else localStorage.removeItem(key);
  }, [activeStorageScope, sessionId, storageScope]);

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
    localStorage.removeItem(`pulsecare_chat_history:${storageScope}`);
    localStorage.removeItem(`pulsecare_session_id:${storageScope}`);
    setSessionId(null);
    setMessages([DEFAULT_WELCOME_MESSAGE]);
    setSuggestedActions(DEFAULT_WELCOME_MESSAGE.suggested_actions || []);
  }, [sessionId, authToken, storageScope]);

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
