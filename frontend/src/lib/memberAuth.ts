import { apiGet } from './api'

export interface MemberAuthStatus {
  enabled: boolean
}

export const memberAuthStatusQueryKey = ['member-auth-status'] as const

export async function getMemberAuthStatus(): Promise<MemberAuthStatus> {
  return apiGet<MemberAuthStatus>('/api/v1/members/auth-status')
}
