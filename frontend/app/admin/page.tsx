'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { DataTable, type Column } from '@/components/domain/DataTable'
import { listApiKeys, createApiKey, deleteApiKey } from '@/lib/api/admin'
import { formatUtcTimestamp } from '@/lib/formatters'
import type { ApiKeyListItem, CreateApiKeyResponse } from '@/lib/api/types'

const columns: Column<ApiKeyListItem>[] = [
  { key: 'name', header: 'Name', cell: (row) => <span>{row.name}</span> },
  {
    key: 'key_preview',
    header: 'Key',
    cell: (row) => <code className="font-mono text-xs text-muted-foreground">{row.key_preview}</code>,
  },
  {
    key: 'created_at',
    header: 'Created',
    cell: (row) => <span className="text-xs">{formatUtcTimestamp(row.created_at)}</span>,
  },
]

export default function AdminPage() {
  const queryClient = useQueryClient()
  const [newKeyName, setNewKeyName] = useState('')
  const [createdKey, setCreatedKey] = useState<CreateApiKeyResponse | null>(null)
  const [copied, setCopied] = useState(false)

  const { data: keys = [], isLoading } = useQuery({
    queryKey: ['admin', 'keys'],
    queryFn: listApiKeys,
  })

  const createMutation = useMutation({
    mutationFn: (name: string) => createApiKey(name),
    onSuccess: (data) => {
      setCreatedKey(data)
      setNewKeyName('')
      queryClient.invalidateQueries({ queryKey: ['admin', 'keys'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (keyId: string) => deleteApiKey(keyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'keys'] })
    },
  })

  function handleCreate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const name = newKeyName.trim()
    if (name) createMutation.mutate(name)
  }

  function handleCopy() {
    if (createdKey) {
      navigator.clipboard.writeText(createdKey.key)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="API Key Management" description="Generate and manage API keys" />

      {createdKey && (
        <Card className="border-success/30 bg-success/5">
          <CardHeader><CardTitle className="text-success">New API Key Created</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            <p className="text-xs text-success">Copy this key now — it will not be shown again.</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded bg-success/10 px-3 py-2 font-mono text-sm text-foreground break-all">
                {createdKey.key}
              </code>
              <Button size="sm" variant="outline" onClick={handleCopy}>
                {copied ? 'Copied!' : 'Copy'}
              </Button>
            </div>
            <Button size="sm" variant="ghost" className="text-xs text-muted-foreground" onClick={() => setCreatedKey(null)}>
              Dismiss
            </Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader><CardTitle>Generate New Key</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="flex items-end gap-3">
            <div className="flex-1 space-y-1">
              <Label htmlFor="keyName">Key Name</Label>
              <Input id="keyName" placeholder="e.g. Trading Bot" value={newKeyName} onChange={(e) => setNewKeyName(e.target.value)} required />
            </div>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Generating...' : 'Generate Key'}
            </Button>
          </form>
          {createMutation.isError && (
            <p className="mt-2 text-xs text-danger">Failed to create key.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Active Keys</CardTitle></CardHeader>
        <CardContent>
          {keys.length === 0 && !isLoading ? (
            <p className="text-xs text-muted-foreground">
              No keys managed here yet. Keys set via <code className="text-foreground">TRADING_SYSTEM_ALLOWED_API_KEYS</code> in <code className="text-foreground">.env</code> always work.
            </p>
          ) : (
            <DataTable
              columns={[
                ...columns,
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
        </CardContent>
      </Card>
    </div>
  )
}
