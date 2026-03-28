import { createFileRoute, Outlet, useChildMatches } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { PatternTrainForm } from '@/components/patterns/PatternTrainForm'
import { PatternSetsTable } from '@/components/patterns/PatternSetsTable'
import { listPatternSets } from '@/api/patterns'

export const Route = createFileRoute('/patterns')({
  component: PatternsPage,
})

function PatternsPage() {
  const childMatches = useChildMatches()
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['patterns'],
    queryFn: listPatternSets,
  })

  if (childMatches.length > 0) return <Outlet />

  return (
    <div className="space-y-4">
      <h1 className="text-lg font-semibold text-zinc-100">Pattern Management</h1>
      <Card>
        <CardHeader><CardTitle>Train Pattern Set</CardTitle></CardHeader>
        <CardContent><PatternTrainForm /></CardContent>
      </Card>
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Saved Pattern Sets</CardTitle>
            <Button variant="outline" size="sm" onClick={() => refetch()}>Refresh</Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading
            ? <p className="text-xs text-zinc-500">Loading...</p>
            : <PatternSetsTable patternSets={data ?? []} />
          }
        </CardContent>
      </Card>
    </div>
  )
}
