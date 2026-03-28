import { createFileRoute, Link, Outlet, useChildMatches } from '@tanstack/react-router'
import { useQueries } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { useRunsStore } from '@/store/runsStore'
import { getBacktestRun } from '@/api/backtests'
import { formatUtcTimestamp } from '@/lib/formatters'

export const Route = createFileRoute('/runs')({
  component: RunsPage,
})

function RunsPage() {
  const childMatches = useChildMatches()
  const { runs, updateRunStatus } = useRunsStore()

  const queries = useQueries({
    queries: runs.map((run) => ({
      queryKey: ['run', run.runId],
      queryFn: () => getBacktestRun(run.runId),
      staleTime: run.status === 'succeeded' || run.status === 'failed' ? Infinity : 0,
      enabled: run.status !== 'succeeded' && run.status !== 'failed',
    })),
  })

  if (childMatches.length > 0) return <Outlet />

  function handleRefresh() {
    queries.forEach((q, i) => {
      q.refetch().then((res) => {
        if (res.data) updateRunStatus(runs[i].runId, res.data.status)
      })
    })
  }

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-zinc-100">Backtest Runs</h1>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Run History</CardTitle>
            <Button variant="outline" size="sm" onClick={handleRefresh}>Refresh Statuses</Button>
          </div>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Run ID</TableHead>
                <TableHead>Symbol</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-zinc-500">No runs yet.</TableCell>
                </TableRow>
              ) : (
                runs.map((run) => (
                  <TableRow key={run.runId}>
                    <TableCell className="font-mono text-xs">{run.runId.slice(0, 8)}…</TableCell>
                    <TableCell>{run.symbol}</TableCell>
                    <TableCell><StatusBadge state={run.status} /></TableCell>
                    <TableCell className="text-xs">{formatUtcTimestamp(run.createdAt)}</TableCell>
                    <TableCell>
                      <Link
                        to="/runs/$runId"
                        params={{ runId: run.runId }}
                        className="text-xs text-blue-400 hover:underline"
                      >
                        View
                      </Link>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
