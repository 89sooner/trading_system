'use client'

import { useEffect, useState } from 'react'
import { useApiStore } from '@/store/apiStore'
import { Button } from '@/components/ui/button'
import { StatusIndicator } from '@/components/domain/StatusIndicator'
import { Settings } from 'lucide-react'

type AuthProbeState =
  | { variant: 'online' | 'offline' | 'warning' | 'error'; label: string }

function localBaseUrl(): string {
  if (typeof window === 'undefined') return 'http://localhost:8000/api/v1'
  const { protocol, hostname } = window.location
  return `${protocol}//${hostname}:8000/api/v1`
}

export function ApiSettingsBar() {
  const { baseUrl, apiKey, setBaseUrl, setApiKey } = useApiStore()
  const [open, setOpen] = useState(false)
  const [urlDraft, setUrlDraft] = useState(baseUrl)
  const [keyDraft, setKeyDraft] = useState(apiKey)
  const [probe, setProbe] = useState<AuthProbeState>({
    variant: 'offline',
    label: 'Checking',
  })

  useEffect(() => {
    const controller = new AbortController()

    async function probeAuth() {
      setProbe({ variant: 'offline', label: 'Checking' })
      const normalizedBaseUrl = baseUrl.replace(/\/$/, '')
      const authHeaders: HeadersInit = apiKey ? { 'X-API-Key': apiKey } : {}
      try {
        const healthResponse = await fetch(`${normalizedBaseUrl}/health`, {
          method: 'GET',
          headers: authHeaders,
          signal: controller.signal,
        })
        if (!healthResponse.ok && healthResponse.status !== 401 && healthResponse.status !== 403) {
          setProbe({ variant: 'error', label: `Backend HTTP ${healthResponse.status}` })
          return
        }

        const response = await fetch(`${normalizedBaseUrl}/backtests?page_size=1`, {
          method: 'GET',
          headers: authHeaders,
          signal: controller.signal,
        })
        if (response.ok) {
          setProbe({
            variant: 'online',
            label: apiKey ? 'Authenticated' : 'Connected',
          })
          return
        }
        if (response.status === 401) {
          setProbe({
            variant: 'warning',
            label: apiKey ? 'Backend reachable · invalid key' : 'Backend reachable · key required',
          })
          return
        }
        setProbe({ variant: 'error', label: `HTTP ${response.status}` })
      } catch (error) {
        if ((error as Error).name === 'AbortError') return
        setProbe({ variant: 'error', label: 'Network/CORS blocked' })
      }
    }

    void probeAuth()
    return () => controller.abort()
  }, [apiKey, baseUrl])

  useEffect(() => {
    setUrlDraft(baseUrl)
  }, [baseUrl])

  useEffect(() => {
    setKeyDraft(apiKey)
  }, [apiKey])

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-2 text-xs text-muted-foreground transition-colors hover:text-foreground"
      >
        <Settings className="h-3 w-3" />
        API
        <StatusIndicator variant={probe.variant} label={probe.label} />
      </button>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <input
        value={urlDraft}
        onChange={(e) => setUrlDraft(e.target.value)}
        placeholder="API base URL"
        className="h-7 w-64 rounded border border-input bg-background px-2 text-xs"
      />
      <input
        value={keyDraft}
        onChange={(e) => setKeyDraft(e.target.value)}
        placeholder="API Key (optional)"
        type="password"
        className="h-7 w-40 rounded border border-input bg-background px-2 text-xs"
      />
      <Button
        size="sm"
        className="h-7 text-xs"
        onClick={() => {
          setBaseUrl(urlDraft)
          setApiKey(keyDraft)
          setOpen(false)
        }}
      >
        Save
      </Button>
      <Button
        size="sm"
        variant="outline"
        className="h-7 text-xs"
        onClick={() => {
          const next = localBaseUrl()
          setUrlDraft(next)
          setBaseUrl(next)
        }}
      >
        Local
      </Button>
      <StatusIndicator variant={probe.variant} label={probe.label} />
      <button onClick={() => setOpen(false)} className="text-xs text-muted-foreground hover:text-foreground">
        X
      </button>
    </div>
  )
}
