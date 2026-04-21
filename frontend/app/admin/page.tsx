'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { KeyRound, RefreshCw, Shield, ShieldCheck } from 'lucide-react'
import { DataTable, type Column } from '@/components/domain/DataTable'
import { PageHeader } from '@/components/layout/PageHeader'
import { SurfacePanel } from '@/components/layout/SurfacePanel'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { createApiKey, deleteApiKey, listApiKeys, updateApiKey } from '@/lib/api/admin'
import { userMessageForError } from '@/lib/api/client'
import { formatUtcTimestamp } from '@/lib/formatters'
import type { ApiKeyListItem, CreateApiKeyResponse } from '@/lib/api/types'

const columns: Column<ApiKeyListItem>[] = [
  { key: 'label', header: 'Label', cell: (row) => <span>{row.label}</span> },
  {
    key: 'key_preview',
    header: 'Key',
    cell: (row) => (
      <code className="font-mono text-xs text-muted-foreground">{row.key_preview}</code>
    ),
  },
  {
    key: 'created_at',
    header: 'Created',
    cell: (row) => <span className="text-xs">{formatUtcTimestamp(row.created_at)}</span>,
  },
  {
    key: 'last_used_at',
    header: 'Last Used',
    cell: (row) => (
      <span className="text-xs text-muted-foreground">
        {row.last_used_at ? formatUtcTimestamp(row.last_used_at) : 'Never'}
      </span>
    ),
  },
  {
    key: 'disabled',
    header: 'State',
    cell: (row) => (
      <Badge variant={row.disabled ? 'secondary' : 'outline'}>
        {row.disabled ? 'disabled' : 'active'}
      </Badge>
    ),
  },
]

export default function AdminPage() {
  const queryClient = useQueryClient()
  const [newKeyLabel, setNewKeyLabel] = useState('')
  const [createdKey, setCreatedKey] = useState<CreateApiKeyResponse | null>(null)
  const [copied, setCopied] = useState(false)

  const { data: keys = [], isLoading } = useQuery({
    queryKey: ['admin', 'keys'],
    queryFn: listApiKeys,
  })

  const createMutation = useMutation({
    mutationFn: (label: string) => createApiKey(label),
    onSuccess: (data) => {
      setCreatedKey(data)
      setNewKeyLabel('')
      queryClient.invalidateQueries({ queryKey: ['admin', 'keys'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (keyId: string) => deleteApiKey(keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'keys'] })
    },
  })

  const toggleMutation = useMutation({
    mutationFn: ({ keyId, disabled }: { keyId: string; disabled: boolean }) =>
      updateApiKey(keyId, disabled),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'keys'] })
    },
  })

  function handleCreate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const label = newKeyLabel.trim()
    if (label) createMutation.mutate(label)
  }

  function handleCopy() {
    if (!createdKey) return
    navigator.clipboard.writeText(createdKey.key)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="API Key Management"
        description="Generate, review, and revoke API keys used by operators and internal clients."
        actions={
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">One-time reveal</Badge>
            <Badge variant="outline">Repository-managed keys</Badge>
            <Badge variant="outline">Manual revoke</Badge>
          </div>
        }
      />

      {createdKey ? (
        <SurfacePanel
          eyebrow="New Secret"
          title="API key created"
          description="Copy this value now. It is shown once and then removed from the screen."
          action={<ShieldCheck className="h-4 w-4 text-success" />}
        >
          <div className="rounded-xl border border-success/25 bg-success/5 p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-success">
              Copy before dismissing
            </p>
            <div className="mt-3 flex flex-col gap-3 lg:flex-row lg:items-center">
              <code className="flex-1 rounded-lg border border-success/20 bg-background px-3 py-3 font-mono text-sm break-all">
                {createdKey.key}
              </code>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={handleCopy}>
                  {copied ? 'Copied!' : 'Copy'}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setCreatedKey(null)}>
                  Dismiss
                </Button>
              </div>
            </div>
          </div>
        </SurfacePanel>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
        <SurfacePanel
          eyebrow="Provisioning"
          title="Generate a new key"
          description="Create a named API key for an operator or internal client integration."
          action={<KeyRound className="h-4 w-4 text-muted-foreground" />}
        >
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              <div className="space-y-1">
                <Label htmlFor="keyName">Key Label</Label>
                <Input
                  id="keyName"
                  placeholder="e.g. Trading Bot"
                  value={newKeyLabel}
                  onChange={(e) => setNewKeyLabel(e.target.value)}
                  required
                />
              </div>
            </div>
            <div className="flex items-center justify-between gap-3 border-t border-border/80 pt-4">
              <p className="text-xs text-muted-foreground">
                Generated keys are immediately available to the backend repository.
              </p>
              <Button type="submit" disabled={createMutation.isPending}>
                {createMutation.isPending ? 'Generating...' : 'Generate Key'}
              </Button>
            </div>
            {createMutation.isError ? (
              <p className="text-sm text-danger">{userMessageForError(createMutation.error)}</p>
            ) : null}
          </form>
        </SurfacePanel>

        <SurfacePanel
          eyebrow="Security"
          title="Operator notes"
          description="Keep API key usage explicit and revocable."
          action={<Shield className="h-4 w-4 text-muted-foreground" />}
        >
          <div className="space-y-3 text-sm text-muted-foreground">
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              Keys shown here are repository-managed. Environment keys configured through{' '}
              <code className="text-foreground">TRADING_SYSTEM_ALLOWED_API_KEYS</code> remain valid separately.
            </div>
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              Use names that reveal ownership and purpose. That makes later review and revoke decisions much easier.
            </div>
            <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
              Revoke old keys instead of reusing them across multiple tools or operators.
            </div>
          </div>
        </SurfacePanel>
      </div>

      <SurfacePanel
        eyebrow="Active Keys"
        title="Current keys"
        description="The currently managed API keys available from the repository-backed admin path."
        action={
          <Button
            variant="outline"
            size="sm"
            onClick={() => queryClient.invalidateQueries({ queryKey: ['admin', 'keys'] })}
          >
            <RefreshCw className="mr-1 h-3 w-3" /> Refresh
          </Button>
        }
      >
        {keys.length === 0 && !isLoading ? (
          <div className="rounded-xl border border-border/80 bg-muted/20 p-4">
            <p className="text-sm text-muted-foreground">
              No keys managed here yet. Keys set via{' '}
              <code className="text-foreground">TRADING_SYSTEM_ALLOWED_API_KEYS</code> in{' '}
              <code className="text-foreground">.env</code> always work.
            </p>
          </div>
        ) : (
          <DataTable
            columns={[
              ...columns,
              {
                key: 'toggle',
                header: '',
                cell: (row) => (
                  <Button
                    size="sm"
                    variant={row.disabled ? 'outline' : 'secondary'}
                    disabled={toggleMutation.isPending}
                    onClick={() =>
                      toggleMutation.mutate({ keyId: row.key_id, disabled: !row.disabled })
                    }
                  >
                    {row.disabled ? 'Enable' : 'Disable'}
                  </Button>
                ),
              },
              {
                key: 'revoke',
                header: '',
                cell: (row) => (
                  <Button
                    size="sm"
                    variant="destructive"
                    disabled={deleteMutation.isPending}
                    onClick={() => deleteMutation.mutate(row.key_id)}
                  >
                    Revoke
                  </Button>
                ),
              },
            ]}
            data={keys}
            keyExtractor={(row) => row.key_id}
            loading={isLoading}
            emptyMessage="No keys."
          />
        )}
      </SurfacePanel>
    </div>
  )
}
