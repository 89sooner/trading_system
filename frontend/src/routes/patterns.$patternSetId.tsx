import { createFileRoute } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { StatTile } from '@/components/shared/StatTile'
import { PatternPreviewTable } from '@/components/patterns/PatternPreviewTable'
import { ErrorBanner } from '@/components/shared/ErrorBanner'
import { getPatternSet } from '@/api/patterns'

export const Route = createFileRoute('/patterns/$patternSetId')({
  component: PatternDetailPage,
})

function PatternDetailPage() {
  const { patternSetId } = Route.useParams()

  const { data, isLoading, error } = useQuery({
    queryKey: ['pattern', patternSetId],
    queryFn: () => getPatternSet(patternSetId),
    staleTime: Infinity,
  })

  if (isLoading) return <p className="text-sm text-zinc-400">Loading...</p>
  if (error) return <ErrorBanner error={error} />
  if (!data) return null

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-zinc-100">{data.name}</h1>
        <p className="font-mono text-xs text-zinc-400">{data.pattern_set_id}</p>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <StatTile label="Symbol" value={data.symbol} />
        <StatTile label="Threshold" value={String(data.default_threshold)} />
        <StatTile label="Examples" value={String(data.examples_count)} />
        <StatTile label="Patterns" value={String(data.patterns.length)} />
      </div>
      <Card>
        <CardHeader><CardTitle>Patterns</CardTitle></CardHeader>
        <CardContent><PatternPreviewTable patterns={data.patterns} /></CardContent>
      </Card>
    </div>
  )
}
