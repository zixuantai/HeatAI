import { get } from '@/utils/request'
import type { UserStats } from '@/types'

export function getUserStatsApi(): Promise<UserStats> {
  return get<UserStats>('/stats/user')
}