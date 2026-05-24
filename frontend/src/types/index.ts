// 前端全局类型定义
export interface UserInfo {
  id: string
  username: string
  email: string | null
  phone: string | null
  nickname: string | null
  avatar: string | null
  role: string
  status: string
  created_at: string
  organizations?: any[] | null
}

export interface UpdateUserRequest {
  username?: string | null
  email?: string | null
  phone?: string | null
  nickname?: string | null
  avatar?: string | null
}

export interface DeleteAccountRequest {
  password: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  password: string
  password_confirm: string
  role?: string
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

export interface SourceRef {
  title: string
  document_id: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  timestamp: number
  toolCalls?: ToolCallInfo[]
  toolResults?: ToolResultInfo[]
  images?: string[]
  sources?: SourceRef[]
}

export interface ToolCallInfo {
  tool_name: string
  tool_args: Record<string, unknown>
  tool_call_id: string
}

export interface ToolResultInfo {
  tool_name: string
  result: string
  tool_call_id: string
}

export interface ToolCallDef {
  id: string
  type: string
  function: {
    name: string
    arguments: string
  }
}

export interface ChatResponseData {
  answer: string
  model: string
  session_id: string
  tool_calls?: ToolCallDef[]
}

export interface SessionInfo {
  id: string
  title: string
  message_count: number
  is_pinned: boolean
  knowledge_base_id: string | null
  knowledge_base_name: string | null
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

export interface DocumentInfo {
  id: string
  filename: string
  original_filename: string
  file_type: string
  file_size: number
  chunk_count: number
  status: string
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface DocumentListResponse {
  total: number
  items: DocumentInfo[]
}

export interface ChunkInfo {
  id: string
  content: string
  chunk_index: number
  title: string
  source: string
}

export interface DocumentChunksResponse {
  document: DocumentInfo
  chunks: ChunkInfo[]
}

export interface SearchRequest {
  query: string
  top_k: number
}

export interface SearchResult {
  content: string
  source: string
  title: string
  document_id: string
  chunk_index: number
  score: number
}

export interface SearchResponse {
  query: string
  results: SearchResult[]
}

export interface DocTypeStat {
  type: string
  count: number
}

export interface CategoryStat {
  category: string
  count: number
}

export interface DocumentStats {
  total: number
  by_file_type: DocTypeStat[]
  by_category: CategoryStat[]
}

export interface Organization {
  id: string
  name: string
  description: string | null
  avatar: string | null
  phone: string | null
  email: string | null
  invite_code: string
  created_by: string
  created_at: string
  updated_at: string
  member_count: number
}

export interface OrganizationMember {
  id: string
  organization_id: string
  user_id: string
  role: 'owner' | 'admin'
  joined_at: string
  username?: string
  nickname?: string
  avatar?: string | null
}

export interface InviteCode {
  id: string
  organization_id: string
  code: string
  created_by: string
  max_uses: number | null
  use_count: number
  expires_at: string | null
  is_active: boolean
  created_at: string
}

export interface CreateOrganizationRequest {
  name: string
  description?: string
  avatar?: string
  phone?: string
  email?: string
}

export interface JoinByInviteCodeRequest {
  code: string
}

export interface CreateInviteCodeRequest {
  max_uses?: number
  expires_at?: string
}

export interface UpdateMemberRoleRequest {
  role: string
}

export interface KnowledgeBase {
  id: string
  name: string
  description: string | null
  avatar: string | null
  cover_color: string | null
  owner_id: string
  owner_name: string | null
  owner_avatar: string | null
  status: string
  doc_count: number
  view_count: number
  like_count: number
  favorite_count: number
  is_recommended: boolean
  is_liked: boolean
  is_favorited: boolean
  is_joined: boolean
  member_count: number
  quick_questions: string[]
  created_at: string
  updated_at: string
}

export interface KnowledgeBaseListResponse {
  total: number
  items: KnowledgeBase[]
}

export interface CreateKnowledgeBaseRequest {
  name: string
  description?: string
  avatar?: string
  cover_color?: string
  quick_questions?: string[]
}

export interface UpdateKnowledgeBaseRequest {
  name?: string
  description?: string
  avatar?: string
  cover_color?: string
  quick_questions?: string[]
  is_recommended?: boolean
}

export interface KBStatsEntry {
  kb_id: string
  kb_name: string
  count: number
}

export interface UserStats {
  total_count: number
  general_count: number
  kb_breakdown: KBStatsEntry[]
  exceed_percentage: number
}
