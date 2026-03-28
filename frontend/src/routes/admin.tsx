import { createFileRoute } from '@tanstack/react-router'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { listApiKeys, createApiKey, deleteApiKey } from '@/api/admin'
import { formatUtcTimestamp } from '@/lib/formatters'
import type { CreateApiKeyResponse } from '@/api/types'

export const Route = createFileRoute('/admin')({
  component: AdminPage,
})

function AdminPage() {
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

  function handleCreate(e: React.SyntheticEvent<HTMLFormElement>) {
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
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-zinc-100">API Key Management</h1>

      {createdKey && (
        <Card className="border-green-800 bg-green-950">
          <CardHeader><CardTitle className="text-green-300">New API Key Created</CardTitle></CardHeader>
          <CardContent className="space-y-2">
            <p className="text-xs text-green-400">Copy this key now — it will not be shown again.</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 rounded bg-green-900 px-3 py-2 font-mono text-sm text-green-100 break-all">
                {createdKey.key}
              </code>
              <Button size="sm" variant="outline" onClick={handleCopy}>
                {copied ? 'Copied!' : 'Copy'}
              </Button>
            </div>
            <Button size="sm" variant="ghost" className="text-xs text-zinc-400" onClick={() => setCreatedKey(null)}>
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
              <Input
                id="keyName"
                placeholder="e.g. Trading Bot"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                required
              />
            </div>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Generating…' : 'Generate Key'}
            </Button>
          </form>
          {createMutation.isError && (
            <p className="mt-2 text-xs text-red-400">Failed to create key.</p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Active Keys</CardTitle></CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-xs text-zinc-500">Loading...</p>
          ) : keys.length === 0 ? (
            <p className="text-xs text-zinc-500">
              No keys managed here yet. Keys set via <code className="text-zinc-400">TRADING_SYSTEM_ALLOWED_API_KEYS</code> in <code className="text-zinc-400">.env</code> always work.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Key</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {keys.map((k) => (
                  <TableRow key={k.key_id}>
                    <TableCell>{k.name}</TableCell>
                    <TableCell><code className="font-mono text-xs text-zinc-400">{k.key_preview}</code></TableCell>
                    <TableCell className="text-xs">{formatUtcTimestamp(k.created_at)}</TableCell>
                    <TableCell>
                      <Button
                        size="sm"
                        variant="destructive"
                        disabled={deleteMutation.isPending}
                        onClick={() => deleteMutation.mutate(k.key_id)}
                      >
                        Revoke
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
