import { get, post, put, del } from '@/utils/request'
import type {
  Organization,
  OrganizationMember,
  InviteCode,
  CreateOrganizationRequest,
  JoinByInviteCodeRequest,
  CreateInviteCodeRequest,
  UpdateMemberRoleRequest,
} from '@/types'

export function createOrganizationApi(data: CreateOrganizationRequest): Promise<Organization> {
  return post<Organization>('/organizations', data)
}

export function getMyOrganizationsApi(): Promise<Organization[]> {
  return get<Organization[]>('/organizations')
}

export function getOrganizationDetailApi(orgId: string): Promise<Organization> {
  return get<Organization>(`/organizations/${orgId}`)
}

export function joinByInviteCodeApi(data: JoinByInviteCodeRequest): Promise<Organization> {
  return post<Organization>('/organizations/join', data)
}

export function getMembersApi(orgId: string): Promise<OrganizationMember[]> {
  return get<OrganizationMember[]>(`/organizations/${orgId}/members`)
}

export function updateMemberRoleApi(orgId: string, userId: string, data: UpdateMemberRoleRequest): Promise<null> {
  return put<null>(`/organizations/${orgId}/members/${userId}`, data)
}

export function removeMemberApi(orgId: string, userId: string): Promise<null> {
  return del<null>(`/organizations/${orgId}/members/${userId}`)
}

export function createInviteCodeApi(orgId: string, data: CreateInviteCodeRequest): Promise<InviteCode> {
  return post<InviteCode>(`/organizations/${orgId}/invite-codes`, data)
}

export function getInviteCodesApi(orgId: string): Promise<InviteCode[]> {
  return get<InviteCode[]>(`/organizations/${orgId}/invite-codes`)
}

export function deactivateInviteCodeApi(codeId: string): Promise<null> {
  return del<null>(`/organizations/invite-codes/${codeId}`)
}
