import { useApiStore } from '@/store/apiStore'

export class ApiError extends Error {
  kind: 'network' | 'validation' | 'server' | 'http'
  status: number | null
  payload: unknown

  constructor(
    kind: 'network' | 'validation' | 'server' | 'http',
    message: string,
    status: number | null = null,
    payload: unknown = null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.kind = kind
    this.status = status
    this.payload = payload
  }
}

export async function requestJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const { baseUrl, apiKey } = useApiStore.getState()
  const url = `${baseUrl}${path}`

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (apiKey) headers['X-API-Key'] = apiKey

  let response: Response
  try {
    const { headers: callerHeaders, ...restOptions } = options
    const mergedHeaders = { ...headers, ...(callerHeaders as Record<string, string>) }
    response = await fetch(url, { headers: mergedHeaders, ...restOptions })
  } catch {
    throw new ApiError('network', 'Cannot reach backend API. Check host/port.')
  }

  const rawBody = await response.text()
  let parsed: unknown = null
  if (rawBody) {
    try {
      parsed = JSON.parse(rawBody)
    } catch {
      parsed = null
    }
  }

  if (response.ok) return parsed as T

  if (response.status >= 400 && response.status < 500) {
    const p = parsed as Record<string, string> | null
    throw new ApiError('validation', p?.message || p?.detail || 'Validation error.', response.status, parsed)
  }
  if (response.status >= 500) {
    const p = parsed as Record<string, string> | null
    throw new ApiError('server', p?.message || p?.detail || 'Server error.', response.status, parsed)
  }
  throw new ApiError('http', `Unexpected HTTP status: ${response.status}`, response.status, parsed)
}

export function userMessageForError(error: unknown): string {
  if (!(error instanceof ApiError)) return 'Unexpected error occurred.'
  if (error.kind === 'network') return 'Network error: cannot reach backend server.'
  if (error.kind === 'validation') return `Validation error (4xx): ${error.message}`
  if (error.kind === 'server') return `Server error (5xx): ${error.message}`
  return `HTTP error: ${error.message}`
}
