import { post, get, put } from '@/utils/request'
import type { LoginRequest, RegisterRequest, TokenResponse, UserInfo, RefreshResponse, UpdateUserRequest } from '@/types'

export function loginApi(data: LoginRequest): Promise<TokenResponse> {
  return post<TokenResponse>('/auth/login', data)
}

export function registerApi(data: RegisterRequest): Promise<null> {
  return post<null>('/auth/register', data)
}

export function refreshTokenApi(): Promise<RefreshResponse> {
  return post<RefreshResponse>('/auth/refresh')
}

export function getCurrentUserApi(): Promise<UserInfo> {
  return get<UserInfo>('/auth/me')
}

export function updateCurrentUserApi(data: UpdateUserRequest): Promise<UserInfo> {
  return put<UserInfo>('/auth/me', data)
}

export function logoutApi(): Promise<null> {
  return post<null>('/auth/logout')
}
