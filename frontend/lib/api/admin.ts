import { requestJson } from './client'
import type { ApiKeyListItem, CreateApiKeyResponse } from './types'

export const listApiKeys = () =>
  requestJson<ApiKeyListItem[]>('/admin/keys')

export const createApiKey = (label: string) =>
  requestJson<CreateApiKeyResponse>('/admin/keys', {
    method: 'POST',
    body: JSON.stringify({ label, name: label }),
  })

export const deleteApiKey = (keyId: string) =>
  requestJson<void>(`/admin/keys/${encodeURIComponent(keyId)}`, { method: 'DELETE' })

export const updateApiKey = (keyId: string, disabled: boolean) =>
  requestJson<ApiKeyListItem>(`/admin/keys/${encodeURIComponent(keyId)}`, {
    method: 'PATCH',
    body: JSON.stringify({ disabled }),
  })
