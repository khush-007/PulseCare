export type InfoBadge = 'verified' | 'general';

export interface Citation {
  title: string;
  section: string;
  source_url?: string;
  last_updated?: string;
  snippet?: string;
}

export interface ChatMessage {
  id: string | number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  info_badge?: InfoBadge;
  citations?: Citation[];
  timestamp: string;
  route?: string;
  is_emergency?: boolean;
  suggested_actions?: string[];
  feedbackGiven?: 'thumbs_up' | 'thumbs_down';
}

export interface ChatSession {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatStreamEventMetadata {
  session_id: string;
  route: string;
  info_badge: InfoBadge;
  is_emergency: boolean;
  suggested_actions?: string[];
}

export interface FeedbackPayload {
  message_id: number;
  rating: 'thumbs_up' | 'thumbs_down';
  comment?: string;
}
