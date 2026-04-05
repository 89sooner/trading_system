import { requestJson } from './client'
import type { ApiKeyListItem, CreateApiKeyResponse } from './types'

export const listApiKeys = () =>
  requestJson<ApiKeyListItem[]>('/admin/keys')

export const createApiKey = (name: string) =>
  requestJson<CreateApiKeyResponse>('/admin/keys', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })

export const deleteApiKey = (keyId: string) =>
  requestJson<void>(`/admin/keys/${encodeURIComponent(keyId)}`, { method: 'DELETE' })
