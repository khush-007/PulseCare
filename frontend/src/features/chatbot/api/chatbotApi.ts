import { FeedbackPayload, Citation, ChatStreamEventMetadata } from '../types/chatbot';

const BASE_URL = '/api/chatbot';

export async function sendMessageApi(
  message: string,
  sessionId?: string,
  token?: string
): Promise<{
  session_id: string;
  message_id: number;
  content: string;
  info_badge: 'verified' | 'general';
  citations: Citation[];
  route: string;
  latency_ms: number;
  is_emergency: boolean;
  suggested_actions: string[];
}> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}/message`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ message, session_id: sessionId || null }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || `Server error: ${res.status}`);
  }

  return res.json();
}

export async function streamMessageApi(
  message: string,
  sessionId: string | null,
  token: string | undefined,
  callbacks: {
    onMetadata: (meta: ChatStreamEventMetadata) => void;
    onToken: (token: string) => void;
    onCitations: (citations: Citation[]) => void;
    onDone: (data: { message_id: number; latency_ms: number }) => void;
    onError: (error: Error) => void;
  }
): Promise<void> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  try {
    const res = await fetch(`${BASE_URL}/stream`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ message, session_id: sessionId || null }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Streaming failed' }));
      throw new Error(err.detail || `HTTP Error ${res.status}`);
    }

    if (!res.body) {
      throw new Error('Response body is missing for streaming');
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const block of lines) {
        if (!block.trim()) continue;
        const eventMatch = block.match(/event:\s*([a-zA-Z0-9_-]+)/);
        const dataMatch = block.match(/data:\s*(.+)/s);

        if (eventMatch && dataMatch) {
          const eventType = eventMatch[1];
          const rawData = dataMatch[1];

          try {
            const parsed = JSON.parse(rawData);
            if (eventType === 'metadata') {
              callbacks.onMetadata(parsed);
            } else if (eventType === 'token') {
              callbacks.onToken(parsed.token);
            } else if (eventType === 'citations') {
              callbacks.onCitations(parsed);
            } else if (eventType === 'done') {
              callbacks.onDone(parsed);
            }
          } catch (e) {
            console.error('SSE parse error:', e, rawData);
          }
        }
      }
    }
  } catch (err: any) {
    callbacks.onError(err);
  }
}

export async function submitFeedbackApi(payload: FeedbackPayload, token?: string): Promise<void> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  await fetch(`${BASE_URL}/feedback`, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });
}

export async function clearSessionApi(sessionId: string, token?: string): Promise<void> {
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  await fetch(`${BASE_URL}/sessions/${sessionId}`, {
    method: 'DELETE',
    headers,
  });
}
