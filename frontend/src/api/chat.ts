import { post } from '@/utils/request'
import type { ChatResponseData } from '@/types'

export function askApi(message: string): Promise<ChatResponseData> {
  return post<ChatResponseData>('/chat/ask', { message })
}
