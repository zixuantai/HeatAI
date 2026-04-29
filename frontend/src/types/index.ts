// 前端全局类型定义
export interface UserInfo {
  id: string
  username: string
  email: string | null
  phone: string | null
  nickname: string | null
  role: string
  status: string
  created_at: string
}

export interface UpdateUserRequest {
  username?: string | null
  email?: string | null
  phone?: string | null
  nickname?: string | null
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  password: string
  password_confirm: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface RefreshResponse {
  access_token: string
  token_type: string
  expires_in: number
}

export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: number
}

export interface ChatResponseData {
  answer: string
  model: string
  session_id: string
}

export interface SessionInfo {
  id: string
  title: string
  message_count: number
  created_at: string
  updated_at: string
}

export interface SessionDetail extends SessionInfo {
  messages: MessageRecord[]
}

export interface MessageRecord {
  id: string
  role: string
  content: string
  created_at: string
}
