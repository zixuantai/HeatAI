import { request } from '@/utils/request'
import type { ChatResponseData } from '@/types'

export function askApi(message: string): Promise<ChatResponseData> {
  return request<ChatResponseData>({
    method: 'POST',
    url: '/chat/ask',
    data: { message },
    timeout: 120000
  })
}
